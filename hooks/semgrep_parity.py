#!/usr/bin/env python3
"""Paridade das regras do Semgrep com o CodeQL, nos testes do próprio CodeQL.

Cada pasta de `semgrep/test/vendor/codeql/` é um teste do CodeQL: o `.expected` lista, na seção
`#select`, o arquivo e a linha de cada alerta que a consulta dá. As regras geradas
(`semgrep/rules/`) rodam sobre a pasta, e cada achado é atribuído à consulta pelo `metadata.codeql`
da regra. O que o CodeQL acusa e a regra ainda não pega, e o que a regra acusa a mais, são as
pendências conhecidas, uma lista só (`semgrep/test/pending.json`): o teste reprova o que fugir
dela, nos dois sentidos, para que nenhuma regressão passe e nenhuma pendência resolvida fique na
lista.

O achado conta para o alerta com folga de uma linha, porque o CodeQL marca o nó e o Semgrep o
trecho. Roda o motor Pro (fluxo entre arquivos), que exige o login do Semgrep.

Uso: `semgrep_parity.py --write-pending`, na raiz do standards, regrava as pendências a partir do
que as regras pegam hoje.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from semgrep_files import codeql_ids

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "semgrep" / "rules"
VENDOR = ROOT / "semgrep" / "test" / "vendor" / "codeql"
MANIFEST = VENDOR / "queries.json"
PENDING = ROOT / "semgrep" / "test" / "pending.json"
# Folga, em linhas, entre o alerta do CodeQL e o trecho do achado.
TOLERANCE = 1
# A largura de linha do Prettier do padrão (`prettier/index.mjs`), a do `pending.json`.
PRINT_WIDTH = 100
# Execuções do Semgrep ao mesmo tempo: mais que isso disputa memória e o motor Pro erra resultado.
WORKERS = 3
# Os campos da linha de localização do CodeQL: `arquivo:linha:coluna:linha:coluna`.
LOCATION_FIELDS = 5


@dataclass(frozen=True)
class Finding:
    """Um achado do Semgrep numa pasta de teste, já atribuído à consulta do CodeQL."""

    query: str
    path: str
    start: int
    end: int


@dataclass(frozen=True)
class Pending:
    """As pendências de uma consulta: o que falta e o que sobra, como `pasta/arquivo:linha`."""

    missing: frozenset[str]
    extra: frozenset[str]


def expected_alerts(text: str) -> set[tuple[str, int]]:
    """Os alertas de um `.expected`: arquivo e linha de cada linha da seção `#select`.

    Nos `.expected` de consulta de caminho, o `#select` pode vir antes de `edges`, `nodes` e
    `subpaths`, que são nós do caminho, não alertas: a seção acaba na primeira linha que não é de
    tabela. Sem `#select`, o arquivo inteiro é a seção (consulta simples), a não ser que só tenha
    as seções do caminho.
    """
    lines = text.splitlines()
    if "#select" in lines:
        lines = lines[lines.index("#select") + 1 :]
    elif any(line.startswith(("edges", "nodes", "subpaths")) for line in lines):
        return set()
    alerts: set[tuple[str, int]] = set()
    for line in lines:
        if not line.startswith("| "):
            if alerts:
                break
            continue
        location = line[2:].split(" | ", 1)[0].strip()
        parts = location.rsplit(":", LOCATION_FIELDS - 1)
        if len(parts) == LOCATION_FIELDS and parts[1].isdigit():
            alerts.add((parts[0], int(parts[1])))
    return alerts


def rule_files() -> dict[str, list[Path]]:
    """Consulta do CodeQL → arquivos de regra que a portam (pelo `metadata.codeql`)."""
    found: dict[str, list[Path]] = {}
    for path in sorted(RULES.rglob("*.yaml")):
        for query in codeql_ids(path):
            found.setdefault(query, []).append(path)
    return found


def parse_findings(output: str) -> list[Finding]:
    """Os achados da saída JSON do Semgrep, pela consulta do `metadata.codeql` de cada regra."""
    document: object = json.loads(output)
    results = document.get("results") if isinstance(document, dict) else None
    findings: list[Finding] = []
    for result in results if isinstance(results, list) else []:
        if not isinstance(result, dict):
            continue
        extra, start, end = result.get("extra"), result.get("start"), result.get("end")
        metadata = extra.get("metadata") if isinstance(extra, dict) else None
        query = metadata.get("codeql") if isinstance(metadata, dict) else None
        path = result.get("path")
        start_line = start.get("line") if isinstance(start, dict) else None
        end_line = end.get("line") if isinstance(end, dict) else None
        if (
            isinstance(query, str)
            and isinstance(path, str)
            and isinstance(start_line, int)
            and isinstance(end_line, int)
        ):
            findings.append(Finding(query, path.removeprefix("./"), start_line, end_line))
    return findings


def run_semgrep(folder: Path, rules: list[Path]) -> list[Finding]:
    """Roda as regras sobre uma pasta de teste, copiada para fora do repo.

    Dentro do standards, o ignore padrão do Semgrep (`test/`, `vendor/`) cobriria a pasta inteira.
    O `.` com o processo na cópia deixa os caminhos relativos a ela, como os do CodeQL.
    """
    semgrep = shutil.which("semgrep")
    if semgrep is None:
        message = "semgrep não encontrado: rode pelo ambiente do standards (`uv run`)"
        raise RuntimeError(message)
    configs = [arg for rule in rules for arg in ("--config", str(rule))]
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / folder.name
        shutil.copytree(folder, target)
        result = subprocess.run(  # noqa: S603 - o semgrep do ambiente, com as regras do standards
            [semgrep, "scan", "--pro", "--metrics=off", "--quiet", "--json",
             "--disable-version-check", *configs, "."],
            capture_output=True, text=True, check=False, cwd=target,
        )  # fmt: skip
    if not result.stdout:
        message = f"o semgrep falhou em {folder.name}: {result.stderr.strip()[-500:]}"
        raise RuntimeError(message)
    return parse_findings(result.stdout)


def near(line: int, start: int, end: int) -> bool:
    return start - TOLERANCE <= line <= end + TOLERANCE


def compare(
    folder: str, expected: set[tuple[str, int]], findings: list[Finding]
) -> tuple[set[str], set[str]]:
    """O que a regra perdeu e o que acusou a mais, numa pasta, como `pasta/arquivo:linha`."""
    missing = {
        f"{folder}/{path}:{line}"
        for path, line in expected
        if not any(f.path == path and near(line, f.start, f.end) for f in findings)
    }
    extra = {
        f"{folder}/{f.path}:{f.start}"
        for f in findings
        if not any(f.path == path and near(line, f.start, f.end) for path, line in expected)
    }
    return missing, extra


def load_manifest(text: str) -> dict[str, dict[str, str]]:
    """O `queries.json`: pasta de teste → consulta → nome do `.expected` dela."""
    document: object = json.loads(text)
    manifest: dict[str, dict[str, str]] = {}
    for folder, queries in document.items() if isinstance(document, dict) else []:
        if isinstance(folder, str) and isinstance(queries, dict):
            manifest[folder] = {
                query: name
                for query, name in queries.items()
                if isinstance(query, str) and isinstance(name, str)
            }
    return manifest


def load_pending(text: str) -> dict[str, Pending]:
    """O `pending.json`: consulta → pendências."""
    document: object = json.loads(text)
    pending: dict[str, Pending] = {}
    for query, entry in document.items() if isinstance(document, dict) else []:
        if isinstance(query, str) and isinstance(entry, dict):
            pending[query] = Pending(strings(entry.get("missing")), strings(entry.get("extra")))
    return pending


def strings(value: object) -> frozenset[str]:
    return (
        frozenset(item for item in value if isinstance(item, str))
        if isinstance(value, list)
        else frozenset()
    )


def folder_result(
    folder: str, queries: dict[str, str], findings: list[Finding]
) -> dict[str, tuple[set[str], set[str]]]:
    """Consulta → (perdidos, a mais) numa pasta de teste."""
    result: dict[str, tuple[set[str], set[str]]] = {}
    for query, expected_name in queries.items():
        expected_file = VENDOR / folder / expected_name
        expected = (
            expected_alerts(expected_file.read_text(encoding="utf-8"))
            if expected_file.exists()
            else set()
        )
        mine = [finding for finding in findings if finding.query == query]
        result[query] = compare(folder, expected, mine)
    return result


def problems(
    folder: str, result: dict[str, tuple[set[str], set[str]]], pending: dict[str, Pending]
) -> list[str]:
    """O que foge das pendências numa pasta: regressão, achado novo a mais e pendência resolvida."""
    found: list[str] = []
    prefix = f"{folder}/"
    for query, (missing, extra) in sorted(result.items()):
        known = pending.get(query, Pending(frozenset(), frozenset()))
        known_missing = {item for item in known.missing if item.startswith(prefix)}
        known_extra = {item for item in known.extra if item.startswith(prefix)}
        found.extend(f"{query}: deixou de pegar {item}" for item in sorted(missing - known_missing))
        found.extend(f"{query}: acusa a mais {item}" for item in sorted(extra - known_extra))
        found.extend(
            f"{query}: {item} já é pego; tire do `missing` do pending.json"
            for item in sorted(known_missing - missing)
        )
        found.extend(
            f"{query}: {item} não é mais acusado; tire do `extra` do pending.json"
            for item in sorted(known_extra - extra)
        )
    return found


def scan_folder(
    folder: str, queries: dict[str, str], rules: dict[str, list[Path]]
) -> list[Finding]:
    """Roda numa pasta as regras de todas as consultas que ela testa, numa execução só."""
    files = sorted({path for query in queries for path in rules.get(query, [])})
    return run_semgrep(VENDOR / folder, files) if files else []


def pending_document(results: dict[str, dict[str, tuple[set[str], set[str]]]]) -> str:
    """O `pending.json` a partir dos resultados de todas as pastas, em ordem estável."""
    merged: dict[str, dict[str, set[str]]] = {}
    for result in results.values():
        for query, (missing, extra) in result.items():
            entry = merged.setdefault(query, {"missing": set(), "extra": set()})
            entry["missing"] |= missing
            entry["extra"] |= extra
    document = {
        query: {"missing": sorted(entry["missing"]), "extra": sorted(entry["extra"])}
        for query, entry in sorted(merged.items())
        if entry["missing"] or entry["extra"]
    }
    return prettier_json(document)


def prettier_json(document: dict[str, dict[str, list[str]]]) -> str:
    """O JSON no formato que o Prettier deixa: a lista que cabe na linha fica numa linha só.

    O hook do Prettier reformata o `pending.json`; escrito já assim, regravar sem mudança de
    pendência não muda o arquivo.
    """
    lines = ["{"]
    for index, (query, entry) in enumerate(document.items()):
        lines.append(f"  {json.dumps(query, ensure_ascii=False)}: {{")
        for position, (key, items) in enumerate(entry.items()):
            comma = "," if position < len(entry) - 1 else ""
            inline = f"    {json.dumps(key)}: {json.dumps(items, ensure_ascii=False)}{comma}"
            if len(inline) <= PRINT_WIDTH:
                lines.append(inline)
                continue
            lines.append(f"    {json.dumps(key)}: [")
            lines.extend(
                f"      {json.dumps(item, ensure_ascii=False)}{',' if n < len(items) - 1 else ''}"
                for n, item in enumerate(items)
            )
            lines.append(f"    ]{comma}")
        lines.append("  }," if index < len(document) - 1 else "  }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(args: list[str]) -> int:
    if args != ["--write-pending"]:
        sys.stderr.write("uso: semgrep_parity.py --write-pending\n")
        return 2
    manifest = load_manifest(MANIFEST.read_text(encoding="utf-8"))
    rules = rule_files()

    def measure(item: tuple[str, dict[str, str]]) -> dict[str, tuple[set[str], set[str]]]:
        folder, queries = item
        return folder_result(folder, queries, scan_folder(folder, queries, rules))

    with ThreadPoolExecutor(WORKERS) as pool:
        measured = list(pool.map(measure, manifest.items()))
    results = dict(zip(manifest, measured, strict=True))
    PENDING.write_text(pending_document(results), encoding="utf-8")
    total = sum(len(q) for q in manifest.values())
    sys.stdout.write(f"{len(manifest)} pastas, {total} pares pasta-consulta\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

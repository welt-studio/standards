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

Os testes próprios (`semgrep/test/own/<linguagem>/`) cobrem o que os do CodeQL quase não cobrem:
o alarme falso. Cada arquivo declara as consultas que testa (`own-test: js/xss, ...`), e cada linha
que tem de alertar leva a marca do CodeQL, `$ Alert[consulta]`. Todas as regras rodam sobre a pasta;
das consultas declaradas, qualquer achado fora de uma linha marcada reprova, assim como a linha
marcada que a consulta não pega. Não há lista de pendências: o teste próprio não aceita exceção.

Uso: `semgrep_parity.py --write-pending`, na raiz do standards, regrava as pendências a partir do
que as regras pegam hoje.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from semgrep_files import codeql_ids
from semgrep_pending import (
    LIMITS_DIR,
    PENDING,
    RULES,
    TEST_NAMES,
    Pending,
    classify,
    load_pending,
    overfit_names,
    read_test_names,
    render,
    strings,
)

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "semgrep" / "test" / "vendor" / "codeql"
MANIFEST = VENDOR / "queries.json"
OWN = ROOT / "semgrep" / "test" / "own"
# A marca de alerta dos testes do CodeQL, nos testes próprios: `$ Alert[consulta, ...]`.
ALERT_MARK = re.compile(r"\$ Alert\[([^\]]+)\]")
# As consultas que um arquivo de teste próprio cobre: `own-test: js/xss, js/code-injection`.
OWN_QUERIES = re.compile(r"own-test:\s*([\w/.,\s-]+?)\s*$")
# Folga, em linhas, entre o alerta do CodeQL e o trecho do achado.
TOLERANCE = 1
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


def parse_findings(output: str, *, by_query: bool = True) -> list[Finding]:
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
        if not by_query:
            query = ""
        if (
            isinstance(query, str)
            and isinstance(path, str)
            and isinstance(start_line, int)
            and isinstance(end_line, int)
        ):
            findings.append(Finding(query, path.removeprefix("./"), start_line, end_line))
    return findings


def run_semgrep(folder: Path, rules: list[Path], *, by_query: bool = True) -> list[Finding]:
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
    engine_errors = engine_failures(result.stdout)
    if engine_errors:
        # O motor que quebra devolve zero achados para a pasta inteira: o silêncio passaria por
        # "nada a acusar". Erro de nível `error` reprova; aviso (arquivo que não parseia) não.
        message = f"o motor do semgrep falhou em {folder.name}: {engine_errors[0][:500]}"
        raise RuntimeError(message)
    return parse_findings(result.stdout, by_query=by_query)


def engine_failures(output: str) -> list[str]:
    """As mensagens dos erros de nível `error` da saída JSON do Semgrep."""
    document: object = json.loads(output)
    errors = document.get("errors") if isinstance(document, dict) else None
    return [
        str(error.get("message", error.get("type", "")))
        for error in (errors if isinstance(errors, list) else [])
        if isinstance(error, dict) and error.get("level") == "error"
    ]


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
        known = pending.get(query, Pending())
        known_missing = {item for item in known.known_missing() if item.startswith(prefix)}
        known_extra = {item for item in known.known_extra() if item.startswith(prefix)}
        found.extend(f"{query}: deixou de pegar {item}" for item in sorted(missing - known_missing))
        found.extend(f"{query}: acusa a mais {item}" for item in sorted(extra - known_extra))
        found.extend(
            f"{query}: {item} já é pego; tire do pending.json"
            for item in sorted(known_missing - missing)
        )
        found.extend(
            f"{query}: {item} não é mais acusado; tire do pending.json"
            for item in sorted(known_extra - extra)
        )
    return found


def scan_folder(
    folder: str, queries: dict[str, str], rules: dict[str, list[Path]]
) -> list[Finding]:
    """Roda numa pasta as regras de todas as consultas que ela testa, numa execução só."""
    files = sorted({path for query in queries for path in rules.get(query, [])})
    return run_semgrep(VENDOR / folder, files) if files else []


def still_missed(name: str, limit: dict[str, object]) -> list[str]:
    """As linhas que a reprodução de um limite diz que o Semgrep devia acusar e ele ainda não acusa.
    Vazio quer dizer que o limite caiu: o Semgrep passou a pegar."""
    folder = LIMITS_DIR / name
    findings = run_semgrep(folder, [folder / "rule.yaml"], by_query=False)
    expected = strings(limit.get("should_find"))
    caught = {
        item
        for item in expected
        for finding in findings
        if item.rpartition(":")[0] == finding.path
        and near(int(item.rpartition(":")[2]), finding.start, finding.end)
    }
    return sorted(expected - caught)


@dataclass(frozen=True)
class OwnCases:
    """Os testes próprios de uma pasta: as consultas de cada arquivo e os alertas exigidos."""

    queries: dict[str, frozenset[str]]
    expected: frozenset[tuple[str, str, int]]


def own_cases(folder: Path) -> OwnCases:
    """As consultas declaradas (`own-test:`) e as marcas de cada arquivo de teste próprio."""
    queries: dict[str, frozenset[str]] = {}
    expected: set[tuple[str, str, int]] = set()
    for path in sorted(item for item in folder.rglob("*") if item.is_file()):
        relative = path.relative_to(folder).as_posix()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        declared = {
            query.strip()
            for line in lines
            for match in OWN_QUERIES.findall(line)
            for query in match.split(",")
            if query.strip()
        }
        queries[relative] = frozenset(declared)
        for number, line in enumerate(lines, start=1):
            for mark in ALERT_MARK.findall(line):
                expected.update((query.strip(), relative, number) for query in mark.split(","))
    return OwnCases(queries, frozenset(expected))


def own_problems(cases: OwnCases, findings: list[Finding]) -> list[str]:
    """O que o teste próprio reprova: o arquivo sem consulta declarada, a marca de consulta que o
    arquivo não declara, a linha marcada que a consulta não pega e qualquer achado da consulta
    declarada fora de uma linha marcada."""
    expected = cases.expected
    undeclared = [
        f"{path}: falta a linha `own-test:` com as consultas que o arquivo testa"
        for path, queries in sorted(cases.queries.items())
        if not queries
    ]
    unmarked = sorted(
        {
            f"{path}:{line}: a marca {query} não está no `own-test:` do arquivo"
            for query, path, line in expected
            if query not in cases.queries.get(path, frozenset())
        }
    )
    findings = [f for f in findings if f.query in cases.queries.get(f.path, frozenset())]
    missing = [
        f"{query}: deixou de pegar {path}:{line}"
        for query, path, line in sorted(expected)
        if not any(
            f.query == query and f.path == path and near(line, f.start, f.end) for f in findings
        )
    ]
    extra = sorted(
        {
            f"{f.query}: acusa a mais {f.path}:{f.start}"
            for f in findings
            if not any(
                f.query == query and f.path == path and near(line, f.start, f.end)
                for query, path, line in expected
            )
        }
    )
    return [*undeclared, *unmarked, *missing, *extra]


def scan_own(folder: Path) -> list[Finding]:
    """Roda todas as regras sobre uma pasta de testes próprios."""
    return run_semgrep(folder, sorted(RULES.rglob("*.yaml")))


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
    merged: dict[str, tuple[set[str], set[str]]] = {}
    for result in measured:
        for query, (missing, extra) in result.items():
            all_missing, all_extra = merged.setdefault(query, (set(), set()))
            all_missing |= missing
            all_extra |= extra
    previous = load_pending(PENDING.read_text(encoding="utf-8")) if PENDING.exists() else {}
    overfit = overfit_names(RULES, read_test_names(TEST_NAMES))
    queries = set(merged) | set(overfit)
    pending = {
        query: classify(
            *merged.get(query, (set(), set())),
            overfit.get(query, set()),
            previous.get(query, Pending()),
        )
        for query in queries
    }
    PENDING.write_text(render(pending), encoding="utf-8")
    total = sum(len(q) for q in manifest.values())
    sys.stdout.write(f"{len(manifest)} pastas, {total} pares pasta-consulta\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

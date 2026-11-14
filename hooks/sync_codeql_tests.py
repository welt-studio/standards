#!/usr/bin/env python3
"""Copia os testes do CodeQL das consultas portadas para `semgrep/test/vendor/codeql/`.

As regras do Semgrep em `semgrep/rules/` portam a suíte padrão do CodeQL, e a paridade é medida
nos testes do próprio CodeQL (`tests/test_semgrep_parity.py`): cada pasta de teste cujo `.qlref`
aponta para uma consulta portada vem inteira, sem mudança, com o `.expected` que diz onde o CodeQL
acusa. As consultas são as que algum arquivo de `semgrep/queries/` declara em `metadata.codeql`, e o
commit do CodeQL é o do `SOURCE`, a única declaração dele.

O script não usa rede: recebe um clone do `github/codeql` já no commit do `SOURCE` (as pastas
`<linguagem>/ql/src` e `<linguagem>/ql/test`, e o `LICENSE`), e recusa outro commit. Além das
pastas, escreve o `queries.json` (que consultas cada pasta testa, e o `.expected` de cada uma) e
copia o `LICENSE` (MIT) do CodeQL.

Uso: `sync_codeql_tests.py <clone do github/codeql>`, na raiz do standards.
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from semgrep_files import codeql_ids

ROOT = Path(__file__).resolve().parent.parent
QUERIES = ROOT / "semgrep" / "queries"
VENDOR = ROOT / "semgrep" / "test" / "vendor" / "codeql"
SOURCE = VENDOR / "SOURCE"
MANIFEST = VENDOR / "queries.json"
# As linguagens portadas, pelo nome da pasta no clone do CodeQL.
LANGUAGES = ("python", "javascript", "actions")
# O que o script escreve e mantém na raiz do vendor, fora das pastas de teste.
KEPT = frozenset({"SOURCE", "LICENSE", "README.md", "queries.json"})
QUERY_ID = re.compile(r"@id\s+(\S+)")


def declared_ids(queries: Path) -> set[str]:
    """Os ids do CodeQL que as consultas portadas declaram em `metadata.codeql`."""
    return {query for path in sorted(queries.rglob("*.yaml")) for query in codeql_ids(path)}


def query_paths(clone: Path, language: str, ids: set[str]) -> dict[str, str]:
    """Caminho da consulta (relativo a `ql/src`) → id, para os ids portados."""
    src = clone / language / "ql" / "src"
    found: dict[str, str] = {}
    for ql in sorted(src.rglob("*.ql")):
        header = ql.read_text(encoding="utf-8", errors="replace").split("*/", 1)[0]
        match = QUERY_ID.search(header)
        if match and match.group(1) in ids:
            found[ql.relative_to(src).as_posix()] = match.group(1)
    return found


def referenced_query(qlref_text: str, paths: dict[str, str]) -> str | None:
    """O id que um `.qlref` testa: o caminho da consulta, sozinho ou como `query: <caminho>`."""
    tokens = qlref_text.replace(":", " ").split()
    for path, query_id in paths.items():
        if path in tokens:
            return query_id
    return None


def test_folders(clone: Path, language: str, paths: dict[str, str]) -> dict[str, dict[str, str]]:
    """Pasta de teste (relativa a `ql/test`) → id → nome do `.expected` dele (o do `.qlref`)."""
    test_root = clone / language / "ql" / "test"
    folders: dict[str, dict[str, str]] = {}
    for qlref in sorted(test_root.rglob("*.qlref")):
        query_id = referenced_query(qlref.read_text(encoding="utf-8", errors="replace"), paths)
        if query_id is not None:
            folder = qlref.parent.relative_to(test_root).as_posix()
            folders.setdefault(folder, {})[query_id] = qlref.with_suffix(".expected").name
    return folders


def clone_commit(clone: Path) -> str | None:
    git = shutil.which("git")
    if git is None:
        return None
    result = subprocess.run(  # noqa: S603 - o git do PATH, sobre o clone que o usuário passou
        [git, "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def sync(clone: Path, vendor: Path, ids: set[str]) -> dict[str, dict[str, str]]:
    """Recria as pastas de teste no `vendor` e devolve o manifesto (pasta → id → `.expected`)."""
    for entry in vendor.iterdir():
        if entry.name not in KEPT:
            shutil.rmtree(entry)
    manifest: dict[str, dict[str, str]] = {}
    for language in LANGUAGES:
        paths = query_paths(clone, language, ids)
        for folder, folder_ids in test_folders(clone, language, paths).items():
            source = clone / language / "ql" / "test" / folder
            # Pasta de teste dentro de outra (a de fora já trouxe a de dentro): mesmo destino.
            shutil.copytree(source, vendor / language / folder, dirs_exist_ok=True)
            manifest[f"{language}/{folder}"] = dict(sorted(folder_ids.items()))
    shutil.copyfile(clone / "LICENSE", vendor / "LICENSE")
    return dict(sorted(manifest.items()))


def main(args: list[str]) -> int:
    if len(args) != 1:
        sys.stderr.write("uso: sync_codeql_tests.py <clone do github/codeql>\n")
        return 2
    clone = Path(args[0])
    expected = SOURCE.read_text(encoding="utf-8").strip()
    actual = clone_commit(clone)
    if actual != expected:
        sys.stderr.write(f"o clone está em {actual}, e o `SOURCE` pede {expected}\n")
        return 1
    ids = declared_ids(QUERIES)
    manifest = sync(clone, VENDOR, ids)
    covered = {query_id for folder_ids in manifest.values() for query_id in folder_ids}
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for query_id in sorted(ids - covered):
        sys.stderr.write(f"aviso: {query_id} não tem pasta de teste no CodeQL\n")
    sys.stdout.write(f"{len(manifest)} pastas de teste, {len(covered)}/{len(ids)} consultas\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

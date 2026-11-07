"""Ferramenta rodada fora do lock (`uvx <nome>@<versão>`) tem uma versão só no repo inteiro.

O Renovate sobe todas juntas (regex do `renovate/default.json5`); este teste pega a que alguém
escrever à mão diferente das outras. O pre-commit não roda pelo `uvx`: a versão dele é a do
`uv.lock` (`uv run pre-commit`), e o Python dos hooks é o desse ambiente. `uv run pytest` na raiz
deste repo.
"""

import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIPPED = {".git", ".venv", "node_modules"}
UVX = re.compile(r"uvx (?P<name>[A-Za-z0-9_.-]+)@(?P<version>\d+(?:\.\d+)+)")


def documents() -> list[Path]:
    return [
        path
        for pattern in ("*.md", "*.yml", "*.yaml")
        for path in ROOT.rglob(pattern)
        if not SKIPPED.intersection(path.relative_to(ROOT).parts)
    ]


def test_each_tool_has_one_version() -> None:
    versions: dict[str, set[str]] = defaultdict(set)
    for path in documents():
        for match in UVX.finditer(path.read_text(encoding="utf-8")):
            versions[match["name"]].add(match["version"])
    assert "pre-commit" not in versions
    assert {name: found for name, found in versions.items() if len(found) > 1} == {}

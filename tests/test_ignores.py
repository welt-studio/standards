"""A lista comum de ignores do padrão é uma só: `uv run pytest` na raiz deste repo.

A declaração é `eslint/ignores.json`, dentro do pacote de ESLint porque ele a lê em runtime (o
projeto instala só a pasta `eslint/`). As outras ferramentas leem a lista em arquivo próprio, no
formato delas, e não importam JSON: este teste confere que cada uma tem exatamente a lista comum
mais o que é só dela, e reprova na divergência (padrão novo numa cópia sem passar pela declaração,
ou o contrário).
"""

import json
import tomllib
from pathlib import Path

import pytest

import check_pyright

ROOT = Path(__file__).resolve().parent.parent


def common_ignores() -> list[str]:
    declared = json.loads((ROOT / "eslint" / "ignores.json").read_text(encoding="utf-8"))
    return [pattern for group in declared.values() for pattern in group]


def gitignore_as_glob(pattern: str) -> str:
    """No `.gitignore` (e no `.prettierignore`), padrão sem `/` casa em qualquer pasta: `**/`."""
    return pattern if "/" in pattern.rstrip("/") else f"**/{pattern}"


def prettier_ignores() -> list[str]:
    lines = (ROOT / "prettier" / "ignore").read_text(encoding="utf-8").splitlines()
    return [gitignore_as_glob(line.strip()) for line in lines if line.strip() and line[0] != "#"]


def jscpd_ignores(name: str) -> list[str]:
    return json.loads((ROOT / "jscpd" / name).read_text(encoding="utf-8"))["ignore"]


def ruff_ignores() -> list[str]:
    return tomllib.loads((ROOT / "ruff" / "base.toml").read_text(encoding="utf-8"))[
        "extend-exclude"
    ]


# O que é só de uma ferramenta, além da lista comum. O ESLint não aparece: ele importa a declaração.
PRETTIER_ONLY = [
    # Lockfiles: o gerenciador de pacotes os escreve no formato dele.
    "**/pnpm-lock.yaml",
    "**/package-lock.json",
    "**/yarn.lock",
    # Templates Jinja/Django, que o Prettier estragaria.
    "**/templates/**/*.html",
]
# O relatório semântico não olha os testes.
SEMANTIC_ONLY = [
    "**/tests/**",
    "**/__tests__/**",
    "**/test/**",
    "**/e2e/**",
    "**/*.test.*",
    "**/*.spec.*",
    "**/test_*.py",
    "**/conftest.py",
    "**/tests.rs",
]

TOOLS = {
    "prettier/ignore": (prettier_ignores, PRETTIER_ONLY),
    "jscpd/base.json": (lambda: jscpd_ignores("base.json"), []),
    "jscpd/semantic.json": (lambda: jscpd_ignores("semantic.json"), SEMANTIC_ONLY),
    "ruff/base.toml": (ruff_ignores, []),
    # A mesma leitura que o hook `pyright-base` faz da base (JSONC).
    "pyright/base.json": (check_pyright.base_ignores, []),
}


def test_common_list_has_no_duplicates() -> None:
    common = common_ignores()
    assert len(common) == len(set(common))


@pytest.mark.parametrize("tool", TOOLS)
def test_tool_list_is_the_common_list_plus_its_own(tool: str) -> None:
    read, own = TOOLS[tool]
    found = read()
    assert len(found) == len(set(found)), f"{tool}: padrão repetido"
    missing = sorted(set(common_ignores()) - set(found))
    extra = sorted(set(found) - set(common_ignores()) - set(own))
    assert (missing, extra) == ([], []), (
        f"{tool} diverge de eslint/ignores.json: falta {missing}, sobra {extra}"
    )


@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("yarn.lock", "**/yarn.lock"),
        ("dist/", "**/dist/"),
        ("**/vendor/**", "**/vendor/**"),
        ("apps/web/out", "apps/web/out"),
    ],
)
def test_gitignore_pattern_as_glob(pattern: str, expected: str) -> None:
    assert gitignore_as_glob(pattern) == expected

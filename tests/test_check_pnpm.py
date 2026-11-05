"""Testes do hook `pnpm-base` (`hooks/check_pnpm.py`): `uv run pytest` na raiz deste repo."""

import json
from pathlib import Path

import pytest

import check_pnpm
from parsed import Table

WORKSPACE = """\
packages:
  - apps/*

# Nenhum script de instalação de dependência roda.
strictDepBuilds: false # só avisa

catalog:
  vitest: 5.0.5
"""
PACKAGE: Table = {
    "packageManager": "pnpm@12.14.0",
    "devEngines": {"packageManager": {"name": "pnpm", "onFail": "error"}},
}


def test_complete_project_passes() -> None:
    assert check_pnpm.workspace_problems(WORKSPACE) == []
    assert check_pnpm.package_problems(PACKAGE) == []


@pytest.mark.parametrize("value", ["true", ""])
def test_strict_dep_builds_must_be_false(value: str) -> None:
    text = WORKSPACE.replace("strictDepBuilds: false # só avisa", f"strictDepBuilds: {value}")
    assert check_pnpm.workspace_problems(text) == ["pnpm-workspace.yaml: `strictDepBuilds: false`"]


def test_missing_strict_dep_builds_fails() -> None:
    text = WORKSPACE.replace("strictDepBuilds: false # só avisa\n", "")
    assert check_pnpm.workspace_problems(text) == ["pnpm-workspace.yaml: `strictDepBuilds: false`"]


@pytest.mark.parametrize(
    "block",
    [
        "allowBuilds:\n  esbuild: false\n",
        "allowBuilds:\n  unrs-resolver: set this to true or false\n",
        "onlyBuiltDependencies:\n  - esbuild\n",
        "dangerouslyAllowAllBuilds: true\n",
        "ignoreScripts: true\n",
    ],
)
def test_replaced_settings_fail(block: str) -> None:
    found = check_pnpm.workspace_problems(WORKSPACE + block)
    assert len(found) == 1
    assert block.split(":", maxsplit=1)[0] in found[0]


def test_nested_key_is_not_top_level() -> None:
    text = WORKSPACE + "overrides:\n  allowBuilds: x\n"
    assert check_pnpm.workspace_problems(text) == []


@pytest.mark.parametrize(
    "package",
    [
        {},
        {"devEngines": {"runtime": {"name": "node"}}},
        {"devEngines": {"packageManager": {"name": "pnpm"}}},
        {"devEngines": {"packageManager": {"name": "npm", "onFail": "error"}}},
        {"devEngines": {"packageManager": {"name": "pnpm", "onFail": "warn"}}},
    ],
)
def test_package_manager_must_be_pnpm_with_error(package: Table) -> None:
    assert len(check_pnpm.package_problems(package)) == 1


def test_main_reads_the_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "pnpm-workspace.yaml").write_text(
        WORKSPACE + "ignoreScripts: true\n", encoding="utf-8"
    )
    (tmp_path / "package.json").write_text(json.dumps(PACKAGE), encoding="utf-8")
    assert check_pnpm.main([str(tmp_path)]) == 1
    assert "ignoreScripts" in capsys.readouterr().err


def test_main_passes_on_complete_folder(tmp_path: Path) -> None:
    (tmp_path / "pnpm-workspace.yaml").write_text(WORKSPACE, encoding="utf-8")
    (tmp_path / "package.json").write_text(json.dumps(PACKAGE), encoding="utf-8")
    assert check_pnpm.main([str(tmp_path)]) == 0


def test_main_without_files_fails(tmp_path: Path) -> None:
    assert check_pnpm.main([str(tmp_path)]) == 1


def test_main_reports_invalid_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "pnpm-workspace.yaml").write_text(WORKSPACE, encoding="utf-8")
    (tmp_path / "package.json").write_text('{"devEngines": }', encoding="utf-8")
    assert check_pnpm.main([str(tmp_path)]) == 1
    assert "não é JSON válido" in capsys.readouterr().err

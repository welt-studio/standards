"""Testes do hook `ruff-base` (`hooks/check_ruff.py`): `uv run pytest` na raiz deste repo."""

import json
from pathlib import Path, PurePosixPath

import pytest

import check_ruff
import repo
from comments import source_comments
from gitrepo import git, write
from parsed import Table

COPY = PurePosixPath("ruff-base.toml")
CONFIG = PurePosixPath("backend/ruff.toml")
BASE: Table = {"extend": "../ruff-base.toml"}
BANNED = check_ruff.base_banned_api()


def config_problems(ruff: Table, *, extends_base: bool = True) -> list[str]:
    return check_ruff.ruff_problems(ruff, CONFIG, extends_base=extends_base, banned_api=BANNED)


def test_project_facts_pass() -> None:
    ruff: Table = {
        **BASE,
        "src": ["app"],
        "lint": {"extend-select": ["TID253"], "per-file-ignores": {"x.py": ["E501"]}},
    }
    assert config_problems(ruff) == []


def test_without_the_base_fails() -> None:
    found = config_problems(BASE, extends_base=False)
    assert len(found) == 1
    assert "extend" in found[0]


@pytest.mark.parametrize("section", ["top", "lint"])
def test_own_select_fails(section: str) -> None:
    select: Table = {"select": ["E"]}
    ruff: Table = {**BASE, **select} if section == "top" else {**BASE, "lint": select}
    found = config_problems(ruff)
    assert len(found) == 1
    assert "extend-select" in found[0]


@pytest.mark.parametrize(
    "ruff",
    [{"exclude": ["app"]}, {"extend-exclude": ["tests"]}, {"include": ["*.py"]}],
)
def test_file_selection_fails(ruff: Table) -> None:
    found = config_problems({**BASE, **ruff})
    assert len(found) == 1
    assert "tira arquivos" in found[0]


def test_lint_exclude_fails() -> None:
    found = config_problems({**BASE, "lint": {"exclude": ["app/**"]}})
    assert found == [f"{CONFIG}: `lint.exclude` tira arquivos do lint"]


@pytest.mark.parametrize(
    "lint",
    [
        {"ignore": ["TID251"]},
        {"extend-ignore": ["tid"]},
        {"ignore": ["T"]},
        {"ignore": ["ALL"]},
        {"ignore": ["PGH004"]},
        {"extend-ignore": ["PGH"]},
        {"per-file-ignores": {"tests/**": ["TID25"]}},
        {"extend-per-file-ignores": {"x.py": ["E501", "PGH004"]}},
    ],
)
def test_turning_off_a_protected_rule_fails(lint: Table) -> None:
    found = config_problems({**BASE, "lint": lint})
    assert found == [f"{CONFIG}: desliga o {check_ruff.PROTECTED_REASON}"]


@pytest.mark.parametrize("code", ["TID252", "TID2510", "PGH003", "", 251, "E501"])
def test_other_codes_do_not_cover_a_protected_rule(code: object) -> None:
    assert check_ruff.covers_protected(code) is False


def test_banned_api_without_the_base_items_fails() -> None:
    tidy: Table = {"banned-api": {"requests": {"msg": "Use httpx."}}}
    found = config_problems({**BASE, "lint": {"flake8-tidy-imports": tidy}})
    assert len(found) == 1
    assert "typing.Any" in found[0]


def test_banned_api_with_the_base_items_passes() -> None:
    banned: Table = {api: {"msg": "base"} for api in BANNED}
    banned["requests"] = {"msg": "Use httpx."}
    tidy: Table = {"banned-api": banned}
    assert config_problems({**BASE, "lint": {"flake8-tidy-imports": tidy}}) == []


def test_base_banned_api_has_any_and_cast() -> None:
    assert {"typing.Any", "typing.cast"} <= set(BANNED)


def chain(configs: dict[str, str | None]) -> dict[PurePosixPath, Table]:
    return {
        PurePosixPath(path): ({} if extend is None else {"extend": extend})
        for path, extend in configs.items()
    }


@pytest.mark.parametrize(
    ("config", "configs", "expected"),
    [
        ("ruff.toml", {"ruff.toml": "ruff-base.toml"}, True),
        ("api/ruff.toml", {"api/ruff.toml": "../ruff-base.toml"}, True),
        # Por outra config do projeto, que chega à cópia.
        (
            "services/api/ruff.toml",
            {"services/api/ruff.toml": "../../ruff.toml", "ruff.toml": "./ruff-base.toml"},
            True,
        ),
        ("api/ruff.toml", {"api/ruff.toml": "../other.toml"}, False),
        ("api/ruff.toml", {"api/ruff.toml": None}, False),
        # O `..` além da raiz não é a cópia do repo, mesmo com o mesmo nome.
        ("ruff.toml", {"ruff.toml": "../ruff-base.toml"}, False),
        ("a/ruff.toml", {"a/ruff.toml": "../b/ruff.toml", "b/ruff.toml": "../a/ruff.toml"}, False),
    ],
)
def test_extend_chain_reaches_the_copy(
    config: str, configs: dict[str, str | None], expected: bool
) -> None:
    assert check_ruff.reaches_copy(PurePosixPath(config), chain(configs), COPY) is expected


def noqa_problems(source: str) -> list[str]:
    found = [check_ruff.noqa_problem(text) for _, text in source_comments(source)]
    return [problem for problem in found if problem]


@pytest.mark.parametrize(
    "comment",
    [
        "# noqa: TID251",
        "# noqa: E501, tid251",
        "# noqa:TID",
        "# noqa: PGH004",
        "# ruff: noqa: TID251",
        "# flake8: noqa: TID251",
        "# ruff: noqa",
        "# flake8: noqa",
        "# pyright: ignore[reportMissingTypeStubs]  # noqa: TID251",
    ],
)
def test_noqa_of_a_protected_rule_fails(comment: str) -> None:
    assert len(noqa_problems(f"from typing import Any  {comment}\n")) == 1


@pytest.mark.parametrize(
    "source",
    [
        "x = 1  # noqa: E501\n",
        "# ruff: noqa: E501\n",
        "# flake8: noqa: F401, E501\n",
        "# Texto que fala de noqa em prosa.\n",
        'TEXT = """\n# noqa: TID251\n"""\n',
    ],
)
def test_other_noqa_prose_and_strings_pass(source: str) -> None:
    assert noqa_problems(source) == []


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Um repo git com a cópia da base em dia e um `backend/ruff.toml` no padrão."""
    git(tmp_path, "init", "-q")
    write(tmp_path / "backend" / "ruff.toml", 'extend = "../ruff-base.toml"\n')
    write(tmp_path / "backend" / "pyproject.toml", '[project]\nname = "app"\n')
    write(tmp_path / "backend" / "app.py", "x = 1  # noqa: E501\n")
    git(tmp_path, "add", ".")
    monkeypatch.chdir(tmp_path)
    check_ruff.main([])
    return tmp_path


def test_project_in_the_standard_passes(project: Path) -> None:
    assert check_ruff.main([]) == 0
    assert (project / "ruff-base.toml").is_file()


def test_bypasses_in_versioned_configs_fail(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        project / "backend" / "ruff.toml",
        'extend = "../ruff-base.toml"\n[lint]\nextend-ignore = ["TID251"]\n',
    )
    write(project / "scripts" / ".ruff.toml", '[lint]\nselect = ["E"]\n')
    write(project / "api" / "pyproject.toml", '[tool.ruff.lint]\nignore = ["TID"]\n')
    # `[tool.ruff]` vazio já é a config da pasta para o Ruff, sem a base.
    write(project / "empty" / "pyproject.toml", '[project]\nname = "x"\n[tool.ruff]\n')
    write(project / "vendor" / "lib" / "ruff.toml", '[lint]\nignore = ["ALL"]\n')
    write(project / "draft" / "ruff.toml", '[lint]\nignore = ["ALL"]\n')
    git(project, "add", "backend", "scripts", "api", "empty", "vendor")
    assert check_ruff.main([]) == 1
    err = capsys.readouterr().err
    assert "backend/ruff.toml: desliga o TID251" in err
    assert "scripts/.ruff.toml: `select`" in err
    assert "scripts/.ruff.toml: `extend`" in err
    assert "api/pyproject.toml: desliga o TID251" in err
    assert "empty/pyproject.toml: `extend`" in err
    # Terceiros (o `ignore` comum) e o que não está no git ficam fora.
    assert "vendor" not in err
    assert "draft" not in err


def test_noqa_in_sources_fails(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(project / "backend" / "app.py", "from typing import Any  # noqa: TID251\n")
    write(project / "backend" / "client.pyi", "# flake8: noqa\nfrom typing import Any\n")
    notebook = {
        "cells": [{"cell_type": "code", "source": ["import os\n", "x = 1  # noqa: PGH004\n"]}]
    }
    write(project / "backend" / "explore.ipynb", json.dumps(notebook))
    write(project / "vendor" / "lib.py", "from typing import Any  # noqa: TID251\n")
    git(project, "add", ".")
    assert check_ruff.main([]) == 1
    err = capsys.readouterr().err
    assert "backend/app.py:1:" in err
    assert "backend/client.pyi:1:" in err
    assert "backend/explore.ipynb:2:" in err
    assert "vendor" not in err


def test_pyproject_without_ruff_is_not_a_ruff_config(project: Path) -> None:
    write(project / "pyproject.toml", '[project]\nname = "root"\n')
    git(project, "add", "pyproject.toml")
    assert check_ruff.main([]) == 0


def test_invalid_toml_fails(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(project / "backend" / "ruff.toml", "extend = \n")
    assert check_ruff.main([]) == 1
    assert "não é TOML válido" in capsys.readouterr().err


def test_files_deleted_from_the_working_tree_are_skipped(project: Path) -> None:
    (project / "backend" / "pyproject.toml").unlink()
    (project / "backend" / "app.py").unlink()
    assert check_ruff.main([]) == 0


def test_outdated_copy_is_restored_and_fails(project: Path) -> None:
    (project / "ruff-base.toml").write_text("\n", encoding="utf-8")
    assert check_ruff.main([]) == 1
    assert check_ruff.main([]) == 0


def test_folder_argument_moves_the_copy(project: Path) -> None:
    write(project / "backend" / "ruff.toml", 'extend = "ruff-base.toml"\n')
    git(project, "add", ".")
    check_ruff.main(["backend"])
    assert (project / "backend" / "ruff-base.toml").is_file()
    assert check_ruff.main(["backend"]) == 0


def test_without_git_fails(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(repo.shutil, "which", lambda _name: None)
    assert check_ruff.main([]) == 1
    assert "git não encontrado" in capsys.readouterr().err


def test_outside_git_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert check_ruff.main([]) == 1
    assert "falhou" in capsys.readouterr().err


def test_wrong_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_ruff.main(["a", "b"]) == 2
    assert "uso:" in capsys.readouterr().err


def test_missing_folder_stops_at_the_copy(project: Path) -> None:
    assert check_ruff.main(["nope"]) == 1

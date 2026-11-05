"""Testes do hook `pyright-base` (`hooks/check_pyright.py`): `uv run pytest` na raiz deste repo."""

import subprocess
from pathlib import Path, PurePosixPath

import pytest

import check_pyright
from parsed import Table

# Um `pyrightconfig.json` no padrão: só fatos do projeto, com comentário e vírgula sobrando (JSONC),
# inclusive uma vírgula seguida de comentário antes do fecho.
CONFIG = """\
{
  // Só fatos do projeto.
  "extends": "./pyright-base.json",
  "include": ["backend"],
  "venvPath": "backend",
  "venv": ".venv",
  "executionEnvironments": [{ "root": "backend", "extraPaths": ["backend/src"] }],
  // fim
}
"""
FACTS: Table = {
    "extends": "./pyright-base.json",
    "include": ["backend"],
    "venvPath": "backend",
    "venv": ".venv",
}


def test_project_facts_pass() -> None:
    assert check_pyright.config_problems(FACTS) == []


def test_schema_is_editor_metadata() -> None:
    config = {**FACTS, "$schema": "https://example.com/pyrightconfig.schema.json"}
    assert check_pyright.config_problems(config) == []


@pytest.mark.parametrize(
    "key",
    ["strict", "typeCheckingMode", "ignore", "reportUnknownMemberType", "strictListInference"],
)
def test_rule_keys_fail(key: str) -> None:
    found = check_pyright.config_problems({**FACTS, key: ["backend/app"]})
    assert found == [f"pyrightconfig.json: `{key}` é regra, e regra vem da base"]


def test_rule_inside_execution_environment_fails() -> None:
    environments = [{"root": "backend"}, {"root": "tests", "reportPrivateUsage": "error"}]
    found = check_pyright.config_problems({**FACTS, "executionEnvironments": environments})
    assert len(found) == 1
    assert "`executionEnvironments[1].reportPrivateUsage` é regra" in found[0]


@pytest.mark.parametrize("extends", ["./pyright-base.json", "pyright-base.json"])
def test_extends_to_the_copy_passes(extends: str) -> None:
    assert check_pyright.config_problems({**FACTS, "extends": extends}) == []


@pytest.mark.parametrize("extends", [None, "./other.json", "../pyright-base.json", 3])
def test_extends_elsewhere_fails(extends: object) -> None:
    config = {key: value for key, value in FACTS.items() if key != "extends"}
    if extends is not None:
        config["extends"] = extends
    found = check_pyright.config_problems(config)
    assert len(found) == 1
    assert "extends" in found[0]


@pytest.mark.parametrize(
    "comment",
    [
        "# pyright: strict",
        "# pyright: basic",
        "#pyright:standard",
        "# pyright: reportPrivateUsage=false",
    ],
)
def test_pyright_file_comment_is_found_anywhere(comment: str) -> None:
    assert check_pyright.file_comments(f"import os\n{comment}\nos.getcwd()\n") == [2]


@pytest.mark.parametrize(
    ("source", "line"),
    [
        ("# type: ignore[reportMissingParameterType]\ndef f(a): ...\n", 1),
        ("#!/usr/bin/env python3\n# coding: utf-8\n\n#type:ignore\nx = 1\n", 4),
    ],
)
def test_type_ignore_before_the_code_is_found(source: str, line: int) -> None:
    assert check_pyright.file_comments(source) == [line]


@pytest.mark.parametrize(
    "source",
    [
        "x = f()  # pyright: ignore\n",
        "x = f()  # pyright: ignore[reportCallIssue]\n",
        "x = f()  # type: ignore[reportCallIssue]\n",
        '"""Doc."""\n# type: ignore[reportMissingParameterType]\n',
        "import os\n# type: ignore[reportMissingParameterType]\n",
        'TEXT = "# pyright: strict"\n',
        'TEXT = """\n# pyright: strict\n"""\n',
        "# pyrightish: strict\n",
    ],
)
def test_line_ignores_late_type_ignore_and_strings_pass(source: str) -> None:
    assert check_pyright.file_comments(source) == []


def test_source_that_does_not_tokenize_is_left_to_the_other_tools() -> None:
    assert check_pyright.file_comments('x = """sem fim\n') == []


@pytest.mark.parametrize(
    ("path", "config", "expected"),
    [
        ("app/models.py", {}, True),
        ("app/models.py", {"include": ["."]}, True),
        ("backend/app/models.py", {"include": ["backend"]}, True),
        ("infra/deploy.py", {"include": ["backend"]}, False),
        ("backend/app/models.py", {"include": ["backend/*/models.py"]}, True),
        ("backend/app/views.py", {"include": ["backend/*/models.py"]}, False),
        ("backend/scripts/x.py", {"include": ["backend"], "exclude": ["**/scripts"]}, False),
        # O `exclude` do projeto substitui o padrão do Pyright (que tira as pastas com ponto).
        ("backend/.venv/lib/x.py", {"include": ["backend"]}, False),
        ("backend/.venv/lib/x.py", {"include": ["backend"], "exclude": ["dist"]}, True),
        # O `ignore` da base: gerado e de terceiros.
        ("vendor/lib.py", {}, False),
        ("backend/vendor/lib.py", {}, False),
        ("backend/app/migrations/0001_initial.py", {}, False),
        ("backend/app/vendored.py", {}, True),
    ],
)
def test_only_what_pyright_analyzes_is_checked(path: str, config: Table, expected: bool) -> None:
    analyzed = check_pyright.analyzed(PurePosixPath(path), config, check_pyright.base_ignores())
    assert analyzed is expected


def git(folder: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=folder, check=True, capture_output=True)  # noqa: S603, S607


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Um repo git com a cópia da base em dia e um `pyrightconfig.json` no padrão."""
    git(tmp_path, "init", "-q")
    write(tmp_path / "pyrightconfig.json", CONFIG)
    write(tmp_path / "backend" / "app.py", "x = 1\n")
    git(tmp_path, "add", ".")
    monkeypatch.chdir(tmp_path)
    check_pyright.main([])
    return tmp_path


def test_project_in_the_standard_passes(project: Path) -> None:
    assert check_pyright.main([]) == 0
    assert (project / "pyright-base.json").is_file()


def test_strict_list_and_file_comments_fail(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        project / "pyrightconfig.json",
        CONFIG.replace('"venv": ".venv",', '"venv": ".venv",\n  "strict": ["backend"],'),
    )
    write(project / "backend" / "app.py", "# pyright: strict\nx = 1\n")
    write(project / "backend" / "service.py", "# type: ignore[reportPrivateUsage]\nx = 1\n")
    write(project / "backend" / "vendor" / "lib.py", "# pyright: basic\n")
    write(project / "infra" / "deploy.py", "# pyright: basic\n")
    git(project, "add", ".")
    assert check_pyright.main([]) == 1
    err = capsys.readouterr().err
    assert "`strict` é regra" in err
    assert "backend/app.py:1:" in err
    assert "backend/service.py:1:" in err
    assert "vendor" not in err
    assert "infra" not in err


def test_untracked_file_is_not_checked(project: Path) -> None:
    write(project / "backend" / "draft.py", "# pyright: basic\n")
    assert check_pyright.main([]) == 0


def test_outdated_copy_is_restored_and_fails(project: Path) -> None:
    (project / "pyright-base.json").write_text("{}\n", encoding="utf-8")
    assert check_pyright.main([]) == 1
    assert check_pyright.main([]) == 0


def test_missing_config_fails(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / "pyrightconfig.json").unlink()
    assert check_pyright.main([]) == 1
    assert "pyrightconfig.json não existe" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"{", "não é JSON válido"),
        ('{"extends": "./pyright-base.json"}'.encode("utf-16"), "não é JSON válido"),
        (b"[]", "não é um objeto JSON"),
    ],
)
def test_invalid_config_fails(
    project: Path, capsys: pytest.CaptureFixture[str], content: bytes, message: str
) -> None:
    (project / "pyrightconfig.json").write_bytes(content)
    assert check_pyright.main([]) == 1
    assert message in capsys.readouterr().err


def test_outside_git_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path / "pyrightconfig.json", CONFIG)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert check_pyright.main([]) == 1
    assert "git grep falhou" in capsys.readouterr().err


def test_without_git_fails(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(check_pyright.shutil, "which", lambda _name: None)
    assert check_pyright.main([]) == 1
    assert "git não encontrado" in capsys.readouterr().err


def test_folder_argument_scopes_config_and_files(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    api = project / "api"
    write(api / "pyrightconfig.json", '{"extends": "./pyright-base.json", "include": ["app"]}')
    write(api / "app" / "models.py", "# pyright: basic\n")
    write(api / "scripts" / "seed.py", "# pyright: basic\n")
    write(project / "backend" / "app.py", "# pyright: basic\n")
    git(project, "add", ".")
    check_pyright.main(["api"])
    assert (api / "pyright-base.json").is_file()
    capsys.readouterr()
    assert check_pyright.main(["api"]) == 1
    err = capsys.readouterr().err
    assert "api/app/models.py:1:" in err
    assert "seed" not in err
    assert "backend" not in err


def test_wrong_usage(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_pyright.main(["a", "b"]) == 2
    assert "uso:" in capsys.readouterr().err


def test_missing_folder_stops_at_the_copy(project: Path) -> None:
    assert check_pyright.main(["nope"]) == 1

"""Testes do hook `pyright-base` (`hooks/check_pyright.py`): `uv run pytest` na raiz deste repo."""

from pathlib import Path, PurePosixPath

import pytest

import check_pyright
import repo
from comments import source_comments
from gitrepo import git, write
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


def problems(source: str) -> list[tuple[int, str]]:
    """Linha e motivo de cada comentário de `source` que o hook reprova."""
    found = [(line, check_pyright.comment_problem(text)) for line, text in source_comments(source)]
    return [(line, problem) for line, problem in found if problem]


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
    found = problems(f"import os\n{comment}\nos.getcwd()\n")
    assert [line for line, _ in found] == [2]
    assert "de arquivo" in found[0][1]


@pytest.mark.parametrize(
    "comment",
    [
        "# type: ignore",
        "#type:ignore[reportCallIssue]",
        "# type: ignore[reportMissingParameterType]",
        "# noqa: E501  # type: ignore[reportCallIssue]",
    ],
)
def test_every_type_ignore_fails(comment: str) -> None:
    found = problems(f"x = f()  {comment}\n")
    assert [line for line, _ in found] == [1]
    assert "type: ignore" in found[0][1]


@pytest.mark.parametrize(
    "comment",
    [
        "# pyright: ignore",
        "# pyright: ignore[reportCallIssue]",
        "# pyright: ignore[reportMissingTypeStubs, reportCallIssue]",
    ],
)
def test_pyright_ignore_other_than_the_stubs_marker_fails(comment: str) -> None:
    found = problems(f"x = f()  {comment}\n")
    assert len(found) == 1
    assert "reportMissingTypeStubs" in found[0][1]


@pytest.mark.parametrize(
    "source",
    [
        "import weasyprint  # pyright: ignore[reportMissingTypeStubs]  # sem stubs publicados\n",
        "import weasyprint  # pyright: ignore[ reportMissingTypeStubs ]\n",
        "x = 1  # noqa: E501\n",
        "# Texto que cita `type: ignore` e `pyright: ignore` em crase.\n",
        'TEXT = "# pyright: strict"\n',
        'TEXT = """\n# type: ignore\n"""\n',
        "# pyrightish: strict\n",
    ],
)
def test_stubs_marker_prose_and_strings_pass(source: str) -> None:
    assert problems(source) == []


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
    write(project / "backend" / "client.pyi", "def get() -> int: ...  # type: ignore\n")
    write(project / "backend" / "vendor" / "lib.py", "# pyright: basic\n")
    write(project / "infra" / "deploy.py", "# pyright: basic\n")
    git(project, "add", ".")
    assert check_pyright.main([]) == 1
    err = capsys.readouterr().err
    assert "`strict` é regra" in err
    assert "backend/app.py:1:" in err
    assert "backend/service.py:1:" in err
    assert "backend/client.pyi:1:" in err
    # Fora do `include` do Pyright e no `ignore` da base (terceiros), nada.
    assert "infra" not in err
    assert "vendor" not in err


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
    monkeypatch.setattr(repo.shutil, "which", lambda _name: None)
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

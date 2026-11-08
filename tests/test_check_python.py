"""Testes do hook `python-base` (`hooks/check_python.py`): `uv run pytest` na raiz deste repo."""

from pathlib import Path

import pytest

import check_python
from gitrepo import git, write

VERSION = check_python.standard_version()
REQUIRES = f"=={check_python.minor(VERSION)}.*"
UV = "0.13.1"
PYPROJECT = (
    f'[project]\nname = "api"\nrequires-python = "{REQUIRES}"\n'
    f'\n[tool.uv]\nrequired-version = "=={UV}"\n'
)
DOCKERFILE = f"FROM ghcr.io/astral-sh/uv:{UV}-trixie-slim\nRUN uv sync --locked\n"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Projeto no padrão, com o pacote em `api/` e a cópia já criada."""
    write(tmp_path / ".pre-commit-config.yaml", "default_stages: [pre-commit]\nrepos: []\n")
    write(tmp_path / "api/pyproject.toml", PYPROJECT)
    write(tmp_path / "api/.python-version", f"{VERSION}\n")
    write(tmp_path / "api/Dockerfile", DOCKERFILE)
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_minor_of_the_version() -> None:
    assert check_python.minor("3.14.8") == "3.14"


def test_project_in_the_standard_passes(project: Path) -> None:
    assert check_python.main(["api"]) == 0


def test_missing_copy_is_created(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / "api/.python-version").unlink()
    assert check_python.main(["api"]) == 1
    assert (project / "api/.python-version").read_text(encoding="utf-8") == f"{VERSION}\n"
    assert "criado" in capsys.readouterr().out


def test_edited_copy_is_restored(project: Path) -> None:
    write(project / "api/.python-version", "3.12\n")
    assert check_python.main(["api"]) == 1
    assert check_python.main(["api"]) == 0


@pytest.mark.parametrize(
    "config",
    [
        "default_language_version:\n  python: python3.14\nrepos: []\n",
        "default_language_version:\n  node: '24'\n  'python': python3.14\nrepos: []\n",
        "default_language_version: {python: python3.14}\nrepos: []\n",
        "default_language_version:\n# o dos hooks\n\n  python: python3.14\nrepos: []\n",
    ],
)
def test_python_in_the_pre_commit_config_fails(
    project: Path, config: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write(project / ".pre-commit-config.yaml", config)
    assert check_python.main(["api"]) == 1
    assert "default_language_version.python" in capsys.readouterr().err


@pytest.mark.parametrize(
    "config",
    [
        "default_language_version:\n  node: '24'\nrepos: []\n",
        "default_language_version:\n  node: '24'\nrepos:\n  - repo: local\n    python: x\n",
        "# default_language_version:\n#   python: python3.14\nrepos: []\n",
    ],
)
def test_other_languages_and_comments_pass(project: Path, config: str) -> None:
    write(project / ".pre-commit-config.yaml", config)
    assert check_python.main(["api"]) == 0


def test_project_without_pre_commit_config_passes(project: Path) -> None:
    (project / ".pre-commit-config.yaml").unlink()
    assert check_python.main(["api"]) == 0


@pytest.mark.parametrize(
    ("line", "found"), [('requires-python = ">=3.12"\n', "`>=3.12`"), ("", "ausente")]
)
def test_requires_python_off_the_minor_fails(
    project: Path, line: str, found: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write(project / "api/pyproject.toml", f'[project]\nname = "api"\n{line}')
    assert check_python.main(["api"]) == 1
    err = capsys.readouterr().err
    assert found in err
    assert f"`{REQUIRES}`" in err


def test_missing_pyproject_fails(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / "api/pyproject.toml").unlink()
    assert check_python.main(["api"]) == 1
    assert "não existe" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("path", "line"),
    [
        ("api/Dockerfile", "FROM python:3.14.8-slim"),
        ("docker/api/Dockerfile", "from --platform=linux/amd64 python:3.14 AS base"),
        ("Dockerfile.dev", "FROM docker.io/library/python@sha256:abc"),
        ("api/app.dockerfile", "FROM python"),
        ("api/Dockerfile", "FROM mirror.gcr.io/library/python:3.14.8-slim"),
        ("api/Dockerfile", "FROM public.ecr.aws/docker/library/python:3.14"),
        ("api/Dockerfile", "FROM ghcr.io/astral-sh/uv:0.13.1-python3.14-bookworm-slim"),
        ("api/Dockerfile", "FROM ghcr.io/astral-sh/uv:python3.14-trixie AS base"),
    ],
)
def test_python_image_fails(
    project: Path, path: str, line: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write(project / path, f"{line}\nRUN true\n")
    git(project, "add", ".")
    assert check_python.main(["api"]) == 1
    assert f"{path}:1:" in capsys.readouterr().err


def test_other_images_and_unversioned_dockerfiles_pass(project: Path) -> None:
    write(project / "api/Dockerfile", "FROM python-builder:1\nFROM pythonista/x\n" + DOCKERFILE)
    git(project, "add", ".")
    write(project / "scratch/Dockerfile", "FROM python:3.14\n")
    assert check_python.main(["api"]) == 0


@pytest.mark.parametrize(
    "path",
    ["docs/Dockerfile.md", "Dockerfiles/README.txt", "api/vendor/pkg/Dockerfile"],
)
def test_docs_and_third_party_dockerfiles_pass(project: Path, path: str) -> None:
    write(project / path, "FROM python:3.14\n")
    git(project, "add", "-f", ".")
    assert check_python.main(["api"]) == 0


def test_dockerfile_deleted_from_the_working_tree_passes(project: Path) -> None:
    (project / "api/Dockerfile").unlink()
    assert check_python.main(["api"]) == 0


def test_dockerfile_named_folder_passes(project: Path) -> None:
    write(project / "Dockerfile.d/notes", "FROM python:3.14\n")
    git(project, "add", ".")
    assert check_python.main(["api"]) == 0


def test_every_problem_shows_with_an_unreadable_pyproject(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(project / "api/pyproject.toml", "[project\n")
    write(project / ".pre-commit-config.yaml", "default_language_version:\n  python: x\n")
    write(project / "api/Dockerfile", "FROM python:3.14\n")
    assert check_python.main(["api"]) == 1
    err = capsys.readouterr().err
    assert "não é TOML válido" in err
    assert "default_language_version.python" in err
    assert "api/Dockerfile:1:" in err


@pytest.mark.parametrize(
    "line",
    [
        "FROM ghcr.io/astral-sh/uv:0.13.1",
        "FROM ghcr.io/astral-sh/uv:0.13.1-trixie-slim@sha256:abc AS base",
        "COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /usr/local/bin/uv",
        "# FROM ghcr.io/astral-sh/uv:0.1.0",
    ],
)
def test_uv_image_on_the_required_version_passes(project: Path, line: str) -> None:
    write(project / "api/Dockerfile", f"{line}\nRUN uv sync --locked\n")
    assert check_python.main(["api"]) == 0


@pytest.mark.parametrize(
    ("line", "found"),
    [
        ("FROM ghcr.io/astral-sh/uv:0.13.2-trixie-slim", "diverge"),
        ("FROM ghcr.io/astral-sh/uv:0.13.10", "diverge"),
        ("COPY --from=ghcr.io/astral-sh/uv:${UV_VERSION} /uv /bin/uv", "por variável"),
        ("FROM ghcr.io/astral-sh/uv AS base", "sem tag"),
    ],
)
def test_uv_image_off_the_required_version_fails(
    project: Path, line: str, found: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write(project / "api/Dockerfile", f"{line}\nRUN uv sync --locked\n")
    assert check_python.main(["api"]) == 1
    err = capsys.readouterr().err
    assert "api/Dockerfile:1:" in err
    assert found in err


@pytest.mark.parametrize("uv", ["", '\n[tool.uv]\nrequired-version = ">=0.13"\n'])
def test_uv_image_without_an_exact_required_version_fails(
    project: Path, uv: str, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        project / "api/pyproject.toml",
        f'[project]\nname = "api"\nrequires-python = "{REQUIRES}"\n{uv}',
    )
    assert check_python.main(["api"]) == 1
    assert "`==<versão>` exata" in capsys.readouterr().err


def test_without_the_uv_image_the_required_version_is_free(project: Path) -> None:
    write(project / "api/Dockerfile", "FROM debian:trixie-slim\n")
    write(
        project / "api/pyproject.toml", f'[project]\nname = "api"\nrequires-python = "{REQUIRES}"\n'
    )
    assert check_python.main(["api"]) == 0


def test_missing_folder_fails(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check_python.main(["backend"]) == 1
    assert "não existe" in capsys.readouterr().err


@pytest.mark.parametrize("args", [[], ["api", "extra"]])
def test_wrong_usage(args: list[str]) -> None:
    assert check_python.main(args) == 2

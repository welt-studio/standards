"""Testes do hook `gitignore-base` (`hooks/check_gitignore.py`): `uv run pytest` na raiz."""

from pathlib import Path

import pytest

import check_gitignore
from gitrepo import git, write

SETTINGS = ".claude/settings.local.json"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    git(tmp_path, "init", "--quiet")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_required_list_skips_blank_lines_and_comments() -> None:
    text = "# comentário\n\n.claude/settings.local.json\n  .env.local  \n"
    assert check_gitignore.required_paths(text) == [SETTINGS, ".env.local"]


def test_standard_list_has_claude_local_settings() -> None:
    text = check_gitignore.REQUIRED.read_text(encoding="utf-8")
    assert SETTINGS in check_gitignore.required_paths(text)


def test_ignored_path_passes(project: Path) -> None:
    write(project / ".gitignore", f"{SETTINGS}\n")
    assert check_gitignore.main([]) == 0


def test_ignored_by_folder_pattern_passes(project: Path) -> None:
    write(project / ".gitignore", ".claude/*.local.json\n")
    assert check_gitignore.main([]) == 0


def test_missing_from_gitignore_fails(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(project / ".gitignore", "node_modules/\n")
    assert check_gitignore.main([]) == 1
    assert f"{SETTINGS}: falta no `.gitignore`" in capsys.readouterr().err


def test_global_exclude_does_not_count(
    project: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    excludes = tmp_path_factory.mktemp("global") / "ignore"
    write(excludes, f"{SETTINGS}\n")
    git(project, "config", "core.excludesFile", str(excludes))
    assert check_gitignore.main([]) == 1


def test_tracked_file_fails_even_when_ignored(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(project / SETTINGS, "{}\n")
    git(project, "add", "--force", SETTINGS)
    write(project / ".gitignore", f"{SETTINGS}\n")
    assert check_gitignore.main([]) == 1
    assert f"{SETTINGS}: está versionado" in capsys.readouterr().err


def test_problems_lists_each_case() -> None:
    assert check_gitignore.problems(["a", "b"], ["a"], ["a"]) == [
        "b: falta no `.gitignore`",
        "a: está versionado (`git rm --cached a`)",
    ]


def test_arguments_are_refused(project: Path) -> None:
    assert check_gitignore.main(["backend"]) == 2


def test_outside_a_repository_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    assert check_gitignore.main([]) == 1
    assert "git check-ignore falhou" in capsys.readouterr().err

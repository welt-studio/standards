"""Testes dos hooks de cópia (`hooks/sync_base.py`): `uv run pytest` na raiz deste repo."""

from pathlib import Path

import pytest

import sync_base


def standard(source: str) -> str:
    return (sync_base.ROOT / source).read_text(encoding="utf-8")


def test_missing_copy_is_created_with_header(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert sync_base.main(["ruff", str(tmp_path)]) == 1
    copy = (tmp_path / "ruff-base.toml").read_text(encoding="utf-8")
    assert copy == sync_base.header("ruff", "ruff/base.toml", "#") + standard("ruff/base.toml")
    assert "criado" in capsys.readouterr().out


def test_edited_copy_is_restored(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    sync_base.main(["pyright", str(tmp_path)])
    copy = tmp_path / "pyright-base.json"
    copy.write_text("{}\n", encoding="utf-8")
    capsys.readouterr()
    assert sync_base.main(["pyright", str(tmp_path)]) == 1
    assert copy.read_text(encoding="utf-8").endswith(standard("pyright/base.json"))
    assert "restaurado" in capsys.readouterr().out


def test_copy_equal_to_the_standard_passes(tmp_path: Path) -> None:
    sync_base.main(["prettier", str(tmp_path)])
    assert sync_base.main(["prettier", str(tmp_path)]) == 0


def test_format_without_comments_gets_no_header(tmp_path: Path) -> None:
    assert sync_base.main(["jscpd", str(tmp_path)]) == 1
    assert (tmp_path / ".jscpd.json").read_text(encoding="utf-8") == standard("jscpd/base.json")


def test_copy_goes_to_the_project_root_without_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert sync_base.main(["prettier"]) == 1
    assert (tmp_path / ".prettierignore").is_file()


def test_missing_folder_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    folder = tmp_path / "frontend"
    assert sync_base.main(["prettier", str(folder)]) == 1
    assert f"a pasta {folder} (args do hook) não existe" in capsys.readouterr().err
    assert not folder.exists()


@pytest.mark.parametrize("args", [[], ["eslint"], ["ruff", "a", "b"]])
def test_usage_error(args: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert sync_base.main(args) == 2
    assert "uso:" in capsys.readouterr().err

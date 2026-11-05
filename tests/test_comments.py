"""Testes da leitura de comentários (`hooks/comments.py`): `uv run pytest` na raiz deste repo."""

import json
from pathlib import Path

from comments import file_comments, notebook_comments, source_comments


def test_only_real_comments_count() -> None:
    source = 'x = 1  # um\nTEXT = "# não é comentário"\nDOC = """\n# nem este\n"""\n# dois\n'
    assert source_comments(source) == [(1, "# um"), (6, "# dois")]


def test_source_that_does_not_tokenize_has_no_comments() -> None:
    assert source_comments('x = """sem fim\n') == []


def notebook(*cells: tuple[str, list[str]]) -> str:
    return json.dumps({"cells": [{"cell_type": kind, "source": source} for kind, source in cells]})


def test_notebook_comments_come_from_code_cells_with_the_line_in_the_notebook() -> None:
    text = notebook(
        ("code", ["import os\n", "x = 1  # primeira\n"]),
        ("markdown", ["# título, não comentário\n"]),
        ("code", ["# segunda\n"]),
    )
    assert notebook_comments(text) == [(2, "# primeira"), (3, "# segunda")]


def test_invalid_notebook_has_no_comments() -> None:
    assert notebook_comments("{") == []


def test_file_comments_reads_by_suffix(tmp_path: Path) -> None:
    (tmp_path / "a.pyi").write_text("def f() -> int: ...  # stub\n", encoding="utf-8")
    (tmp_path / "b.ipynb").write_text(notebook(("code", ["y = 2  # célula\n"])), encoding="utf-8")
    assert file_comments(tmp_path / "a.pyi") == [(1, "# stub")]
    assert file_comments(tmp_path / "b.ipynb") == [(1, "# célula")]

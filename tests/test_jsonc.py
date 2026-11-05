"""Testes da leitura de JSONC (`hooks/jsonc.py`): `uv run pytest` na raiz deste repo."""

import json

import pytest

import jsonc
import sync_base


def test_comments_and_trailing_commas_are_dropped() -> None:
    text = """\
// Comentário de linha inteira
{
  "a": 1, // no fim da linha
  /* de bloco,
     em várias linhas */
  "b": [1, 2,],
}
"""
    assert jsonc.loads(text) == {"a": 1, "b": [1, 2]}


@pytest.mark.parametrize(
    "text", ['{"a": 1, // fim\n}', '{"a": 1, /* fim */ }', '{"a": 1,\n  // um\n  // dois\n}']
)
def test_trailing_comma_before_a_comment_is_dropped(text: str) -> None:
    assert jsonc.loads(text) == {"a": 1}


def test_comment_markers_inside_strings_are_kept() -> None:
    text = r'{"url": "https://x//y", "glob": "**/*.min.js", "comma": ",}", "quote": "a\"//b"}'
    assert jsonc.loads(text) == {
        "url": "https://x//y",
        "glob": "**/*.min.js",
        "comma": ",}",
        "quote": 'a"//b',
    }


def test_the_standard_base_is_read() -> None:
    base = jsonc.loads((sync_base.ROOT / "pyright" / "base.json").read_text(encoding="utf-8"))
    assert isinstance(base, dict)
    assert "**/vendor/**" in base["ignore"]


def test_invalid_jsonc_raises() -> None:
    with pytest.raises(json.JSONDecodeError):
        jsonc.loads('{"a": }')

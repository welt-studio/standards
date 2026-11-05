"""Os comentários de um arquivo Python como o Pyright e o Ruff os leem, comum aos hooks que reprovam
diretiva de contorno (`check_pyright`, `check_ruff`): só comentário de verdade conta, o mesmo texto
dentro de uma string não. Python stdlib, sem dependências.
"""

import io
import json
import tokenize
from pathlib import Path

from parsed import items, table


def source_comments(source: str) -> list[tuple[int, str]]:
    """Linha e texto (com o `#`) de cada comentário de `source`. Código que não tokeniza fica sem
    comentários: ele já reprova no Ruff e no Pyright, com a causa."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError, SyntaxError:
        return []
    return [(token.start[0], token.string) for token in tokens if token.type == tokenize.COMMENT]


def notebook_comments(text: str) -> list[tuple[int, str]]:
    """Os comentários das células de código de um `.ipynb` (que o Ruff também confere), com a linha
    contada no notebook inteiro, célula após célula. JSON inválido fica sem comentários."""
    try:
        notebook = table(json.loads(text))
    except json.JSONDecodeError:
        return []
    found: list[tuple[int, str]] = []
    offset = 0
    for cell in items(notebook.get("cells")):
        cell_table = table(cell)
        if cell_table.get("cell_type") != "code":
            continue
        lines = [line for line in items(cell_table.get("source")) if isinstance(line, str)]
        found.extend((offset + line, comment) for line, comment in source_comments("".join(lines)))
        offset += len(lines)
    return found


def file_comments(path: Path) -> list[tuple[int, str]]:
    """Os comentários do arquivo em `path` (`.py`, `.pyi` ou `.ipynb`)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return notebook_comments(text) if path.suffix == ".ipynb" else source_comments(text)

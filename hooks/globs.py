"""Glob de caminho como o Pyright e o Ruff o leem (`**` atravessa pastas, `*` e `?` ficam numa só),
comum aos hooks que decidem se um arquivo do projeto está dentro ou fora de uma lista de padrões.

Python stdlib, sem dependências.
"""

import posixpath
import re
from pathlib import PurePosixPath


def glob_regex(pattern: str) -> re.Pattern[str] | None:
    """`pattern` como regex de caminho; `None` quando o padrão é a própria pasta do projeto. O `**`
    do fim sai: casar a pasta basta, porque `matches` também tenta cada pasta acima do arquivo."""
    segments = [s for s in posixpath.normpath(pattern).split("/") if s not in ("", ".")]
    while segments and segments[-1] == "**":
        segments.pop()
    if not segments:
        return None
    parts: list[str] = []
    for index, segment in enumerate(segments):
        if segment == "**":
            parts.append("(?:[^/]+/)*")
            continue
        translated = "".join(
            "[^/]*" if char == "*" else "[^/]" if char == "?" else re.escape(char)
            for char in segment
        )
        parts.append(translated if index == len(segments) - 1 else translated + "/")
    return re.compile("".join(parts))


def inside(path: PurePosixPath, folder: PurePosixPath) -> PurePosixPath | None:
    """`path` (relativo à raiz) relativo a `folder`; `None` quando está fora dela. A raiz (`.`)
    contém tudo."""
    if folder == PurePosixPath():
        return path
    return path.relative_to(folder) if path.is_relative_to(folder) else None


def matches(path: PurePosixPath, pattern: str) -> bool:
    """`path` casa `pattern`, ele mesmo ou alguma pasta acima dele (como no `include`/`exclude`)."""
    regex = glob_regex(pattern)
    if regex is None:
        return True
    candidates = [path, *path.parents[:-1]]
    return any(regex.fullmatch(str(candidate)) for candidate in candidates)

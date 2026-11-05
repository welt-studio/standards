"""Leitura de JSONC, o JSON com comentários e vírgula sobrando que o Pyright e o TypeScript aceitam
(`pyrightconfig.json`, `tsconfig.json`). Python stdlib, sem dependências.
"""

import json
import re

# Um texto entre aspas (com escapes): vem primeiro nas duas regex, então `//` e `,}` dentro de aspas
# ficam como estão.
STRING = r'"(?:\\.|[^"\\])*"'
# Comentário de linha (`// …` até o fim) ou de bloco (`/* … */`).
COMMENT = re.compile(rf"{STRING}|//[^\n]*|/\*.*?\*/", re.DOTALL)
# Vírgula seguida só de espaço e do fecho do objeto ou da lista. Roda depois dos comentários: num
# `,  // x\n}` a vírgula só fica colada ao fecho quando o comentário já saiu.
TRAILING_COMMA = re.compile(rf"{STRING}|,(?=\s*[}}\]])")


def keep_strings(match: re.Match[str]) -> str:
    return match[0] if match[0].startswith('"') else ""


def strip(text: str) -> str:
    """`text` sem comentários e sem vírgula sobrando: JSON que o `json` lê."""
    return TRAILING_COMMA.sub(keep_strings, COMMENT.sub(keep_strings, text))


def loads(text: str) -> object:
    """O valor do JSONC em `text`; `json.JSONDecodeError` quando não é JSONC válido."""
    return json.loads(strip(text))

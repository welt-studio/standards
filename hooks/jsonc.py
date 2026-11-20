"""Leitura de JSONC, o JSON com comentários e vírgula sobrando que o Pyright e o TypeScript aceitam
(`pyrightconfig.json`, `tsconfig.json`), e do JSON5 do preset do Renovate
(`renovate/default.json5`), que acrescenta a chave sem aspas e o texto em aspas simples. Python
stdlib, sem dependências.
"""

import json
import re

# Um texto entre aspas (com escapes): vem primeiro nas regex, então `//` e `,}` dentro de aspas
# ficam como estão. As aspas simples são do JSON5 (o Prettier as usa no preset quando o texto tem
# aspas duplas); no JSONC válido toda aspa simples já está dentro de um texto ou de um comentário.
STRING = r""""(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'"""
# Dentro do texto em aspas simples: o escape e a aspa dupla, que no JSON muda de forma.
SINGLE_QUOTED_PART = re.compile(r'\\.|"')
# Comentário de linha (`// …` até o fim) ou de bloco (`/* … */`).
COMMENT = re.compile(rf"{STRING}|//[^\n]*|/\*.*?\*/", re.DOTALL)
# Vírgula seguida só de espaço e do fecho do objeto ou da lista. Roda depois dos comentários: num
# `,  // x\n}` a vírgula só fica colada ao fecho quando o comentário já saiu.
TRAILING_COMMA = re.compile(rf"{STRING}|,(?=\s*[}}\]])")
# Chave de objeto sem aspas (JSON5), logo depois do `{` ou da `,`. Roda depois dos comentários, que
# podem ficar entre a vírgula e a chave.
BARE_KEY = re.compile(rf"{STRING}|(?<=[{{,])(?P<space>\s*)(?P<key>[A-Za-z_$][\w$]*)(?=\s*:)")


def keep_strings(match: re.Match[str]) -> str:
    return match[0] if match[0].startswith(("'", '"')) else ""


def strip(text: str) -> str:
    """`text` sem comentários e sem vírgula sobrando: JSON que o `json` lê."""
    return TRAILING_COMMA.sub(keep_strings, COMMENT.sub(keep_strings, text))


def loads(text: str) -> object:
    """O valor do JSONC em `text`; `json.JSONDecodeError` quando não é JSONC válido."""
    return json.loads(strip(text))


def json_part(match: re.Match[str]) -> str:
    return {"\\'": "'", '"': '\\"'}.get(match[0], match[0])


def quote_key(match: re.Match[str]) -> str:
    """A chave sem aspas ganha aspas duplas; o texto em aspas simples passa para aspas duplas."""
    if match["key"] is not None:
        return f'{match["space"]}"{match["key"]}"'
    if match[0].startswith("'"):
        return f'"{SINGLE_QUOTED_PART.sub(json_part, match[0][1:-1])}"'
    return match[0]


def loads_json5(text: str) -> object:
    """O valor do JSON5 do preset em `text`: o JSONC com chave sem aspas e texto em aspas simples.
    O resto do JSON5 (número hexadecimal, texto em várias linhas) o preset não usa, e o teste que
    lê o preset inteiro pega o que entrar; `json.JSONDecodeError` quando não é esse JSON5."""
    return json.loads(BARE_KEY.sub(quote_key, strip(text)))

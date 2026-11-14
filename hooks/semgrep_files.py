"""Os arquivos de regra do Semgrep do standards (`semgrep/queries/`, `semgrep/rules/`): um jeito só
de ler a consulta do CodeQL que cada regra porta (o `metadata.codeql`) e os nomes que os padrões
citam (o gerador e a trava contra regra presa ao teste usam os mesmos)."""

import re
from pathlib import Path

import yaml

# Palavras que não nomeiam API: as da linguagem (Python, JavaScript) e as do que se escreve nos
# padrões do Semgrep. O que sobra de um padrão, sem metavariável, texto entre aspas e reticências, é
# nome de API (`request.GET`, `fs.readFile`, `innerHTML`).
KEYWORDS = frozenset(
    {"def", "async", "await", "function", "return", "if", "else", "elif", "for", "while", "in"}
    | {"not", "and", "or", "is", "import", "from", "as", "class", "lambda", "const", "let", "var"}
    | {"new", "typeof", "instanceof", "this", "self", "true", "false", "null", "None", "True"}
    | {"False", "try", "except", "finally", "with", "throw", "raise", "yield", "pass", "del"}
    | {"global", "delete", "void", "do", "switch", "case", "break", "continue", "of", "export"}
    | {"default"}
)
METAVARIABLE = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*")
LITERAL = re.compile(r"\"[^\"\n]*\"|'[^'\n]*'|`[^`\n]*`")
IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def bare_names(pattern: str) -> list[str]:
    """Os nomes que um padrão cita, sem metavariável e sem texto entre aspas."""
    return IDENTIFIER.findall(METAVARIABLE.sub(" ", LITERAL.sub(" ", pattern)))


def pattern_names(node: object) -> set[str]:
    """Os nomes citados nos padrões de uma regra (as chaves `pattern*`), fora as palavras da
    linguagem; regex (`pattern-regex`, `regex`) não entra, porque não é nome de código."""
    names: set[str] = set()
    if isinstance(node, list):
        for item in node:
            names |= pattern_names(item)
    elif isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str) and isinstance(value, str):
                if key.startswith("pattern") and key != "pattern-regex":
                    names.update(name for name in bare_names(value) if name not in KEYWORDS)
            else:
                names |= pattern_names(value)
    return names


def codeql_ids(path: Path) -> list[str]:
    """As consultas do CodeQL que as regras do arquivo declaram em `metadata.codeql`, na ordem."""
    document: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    rules = document.get("rules") if isinstance(document, dict) else None
    ids: list[str] = []
    for rule in rules if isinstance(rules, list) else []:
        metadata = rule.get("metadata") if isinstance(rule, dict) else None
        codeql = metadata.get("codeql") if isinstance(metadata, dict) else None
        if isinstance(codeql, str) and codeql not in ids:
            ids.append(codeql)
    return ids

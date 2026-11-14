"""Os arquivos de regra do Semgrep do standards (`semgrep/queries/`, `semgrep/rules/`): um jeito só
de ler a consulta do CodeQL que cada regra porta, o `metadata.codeql`."""

from pathlib import Path

import yaml


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

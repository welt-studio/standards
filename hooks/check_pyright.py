#!/usr/bin/env python3
"""Hook `pyright-base`: mantém a cópia do padrão Pyright no projeto e confere que nada a contorna.

A cópia (`pyright-base.json`) é a do `sync_base.py`. Depois, o hook reprova o que religaria ou
trocaria as regras da base sem aparecer nela (README, "Pyright"):

- no `pyrightconfig.json`, qualquer chave além dos fatos do projeto (caminhos, ambiente, versão do
  Python) e um `extends` que não seja a cópia. A lista `strict` é o caso que motivou a trava: no
  Pyright ela religa toda regra do strict que a base desliga, como as `reportUnknown*`;
- nos `.py` e `.pyi` que o Pyright analisa, o comentário de arquivo `# pyright: <modo ou regra>`
  (`strict`, `basic`, `reportX=false`), que faz o mesmo num arquivo só;
- nos mesmos arquivos, o que cala um erro em vez de corrigi-lo (decisão do PO, 2026-11-05): todo
  `# type: ignore` (a base já o desliga, e o comentário ficaria mentindo) e todo `# pyright: ignore`
  fora o marcador de lib sem stubs publicados (`[reportMissingTypeStubs]`, sozinho).

O `noqa` que fura a lista de APIs proibidas do Ruff é do hook `ruff-base`. Python stdlib, sem
dependências.

Uso: `check_pyright.py [pasta]`, com a pasta do `pyrightconfig.json` (relativa à raiz) quando ele
não está na raiz.
"""

import json
import posixpath
import re
import sys
from pathlib import Path, PurePosixPath

import jsonc
import sync_base
from comments import file_comments
from globs import matches
from parsed import Table, items, table
from repo import git_paths

TOOL = "pyright"
HOOK = sync_base.hook_id(TOOL)
BASE_COPY = sync_base.copy_name(TOOL)
CONFIG = "pyrightconfig.json"
# O que o Pyright analisa.
SOURCES = ("*.py", "*.pyi")

# Os fatos do projeto: o resto das chaves do `pyrightconfig.json` (modo, `strict`, `ignore`,
# `report*`, as inferências estritas) é regra, e regra vem da base. Lista de permitidas, não de
# proibidas: chave nova do Pyright entra reprovada até alguém decidir onde ela mora. O `$schema`
# só serve ao editor (completar as chaves), não muda o que o Pyright faz.
FACT_KEYS = frozenset(
    {
        "$schema",
        "extends",
        "include",
        "exclude",
        "executionEnvironments",
        "extraPaths",
        "stubPath",
        "typeshedPath",
        "venvPath",
        "venv",
        "pythonVersion",
        "pythonPlatform",
        "defineConstant",
        "verboseOutput",
    }
)
ENVIRONMENT_FACT_KEYS = frozenset({"root", "extraPaths", "pythonVersion", "pythonPlatform"})

# O que o Pyright deixa de fora quando o projeto não declara `exclude`.
DEFAULT_EXCLUDE = ("**/node_modules", "**/__pycache__", "**/.*")

# Comentário de arquivo do Pyright: `# pyright:` seguido de qualquer coisa que não seja o `ignore` de
# uma linha (sozinho ou com as regras entre colchetes). O espaço fica dentro do lookahead: fora
# dele, o `\s*` recuaria e o ` ignore` passaria pela negação.
PYRIGHT_FILE_COMMENT = re.compile(r"#\s*pyright:(?!\s*ignore(?:\[|\s|$))")
# As diretivas de linha como o Pyright as acha no texto do comentário (sem o `#` do começo): no
# início ou depois de outro `#` do mesmo comentário, e só quando o `ignore` termina ali ou abre a
# lista de regras (em crase dentro de uma frase, não conta).
TYPE_IGNORE = re.compile(r"(?:^|#)\s*type:\s*ignore(?:\[[\s\w,-]*\]|\s|$)")
PYRIGHT_IGNORE = re.compile(r"(?:^|#)\s*pyright:\s*ignore(?:\[(?P<rules>[\s\w,-]*)\]|\s|$)")
# O único `# pyright: ignore` do padrão: o import de lib sem stubs publicados.
ALLOWED_PYRIGHT_IGNORE = ["reportMissingTypeStubs"]
# Pré-filtro do `git grep` (ERE): só os arquivos com um desses textos são lidos.
CANDIDATE = r"pyright:|type:[[:space:]]*ignore"


def extends_problem(value: object) -> str | None:
    if isinstance(value, str) and posixpath.normpath(value) == BASE_COPY:
        return None
    return f'{CONFIG}: `"extends": "./{BASE_COPY}"` (sem ele, a base não vale)'


def config_problems(config: Table) -> list[str]:
    problem = extends_problem(config.get("extends"))
    problems = [problem] if problem else []
    problems.extend(
        f"{CONFIG}: `{key}` é regra, e regra vem da base"
        for key in sorted(config.keys() - FACT_KEYS)
    )
    for index, environment in enumerate(items(config.get("executionEnvironments"))):
        problems.extend(
            f"{CONFIG}: `executionEnvironments[{index}].{key}` é regra, e regra vem da base"
            for key in sorted(table(environment).keys() - ENVIRONMENT_FACT_KEYS)
        )
    return problems


def comment_problem(comment: str) -> str | None:
    """O que `comment` (um comentário inteiro, com o `#`) contorna na base; `None` quando nada."""
    if PYRIGHT_FILE_COMMENT.match(comment):
        return "`# pyright:` de arquivo troca as regras da base"
    text = comment[1:]
    if TYPE_IGNORE.search(text):
        return "`# type: ignore` cala o erro em vez de corrigi-lo (e a base não o lê)"
    pyright_ignore = PYRIGHT_IGNORE.search(text)
    if pyright_ignore:
        rules = [rule.strip() for rule in (pyright_ignore["rules"] or "").split(",")]
        if rules != ALLOWED_PYRIGHT_IGNORE:
            return "`# pyright: ignore` só no import de lib sem stubs (`[reportMissingTypeStubs]`)"
    return None


def strings(value: object) -> list[str]:
    return [item for item in items(value) if isinstance(item, str)]


def base_ignores() -> list[str]:
    """O `ignore` da base: o que o Pyright não acusa, e onde o comentário não muda nada."""
    base = table(
        jsonc.loads((sync_base.ROOT / "pyright" / "base.json").read_text(encoding="utf-8"))
    )
    return strings(base.get("ignore"))


def analyzed(path: PurePosixPath, config: Table, ignores: list[str]) -> bool:
    """O Pyright acusa algo em `path` (relativo à pasta do `pyrightconfig.json`)."""
    include = strings(config.get("include")) or ["."]
    exclude = strings(config.get("exclude")) if "exclude" in config else list(DEFAULT_EXCLUDE)
    if not any(matches(path, pattern) for pattern in include):
        return False
    return not any(matches(path, pattern) for pattern in [*exclude, *ignores])


def comment_problems(paths: list[str], folder: Path, config: Table) -> list[str]:
    """Os comentários que contornam a base nos `paths` (relativos à raiz) que o Pyright analisa."""
    ignores = base_ignores()
    root = PurePosixPath(folder.as_posix())
    problems: list[str] = []
    for path in paths:
        relative = PurePosixPath(path)
        if root != PurePosixPath():
            if not relative.is_relative_to(root):
                continue
            relative = relative.relative_to(root)
        if not analyzed(relative, config, ignores):
            continue
        for line, comment in file_comments(Path(path)):
            problem = comment_problem(comment)
            if problem:
                problems.append(f"{path}:{line}: {problem}")
    return problems


def candidate_files() -> list[str] | None:
    """Os arquivos do git (relativos à raiz) com uma das diretivas no texto; `None`, com o motivo
    no stderr, fora de um repo git."""
    args = ["grep", "-l", "-z", "-I", "-E", "-e", CANDIDATE, "--", *SOURCES]
    return git_paths(HOOK, args, empty_ok=True)


def load_config(path: Path) -> Table | None:
    """O `pyrightconfig.json` em `path`; `None`, com o motivo no stderr, se falta ou é inválido."""
    if not path.is_file():
        sys.stderr.write(f'{HOOK}: {path} não existe (com `"extends": "./{BASE_COPY}"`)\n')
        return None
    try:
        value = jsonc.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        sys.stderr.write(f"{HOOK}: {path} não é JSON válido em UTF-8: {error}\n")
        return None
    if not isinstance(value, dict):
        sys.stderr.write(f"{HOOK}: {path} não é um objeto JSON\n")
        return None
    return table(value)


def main(args: list[str]) -> int:
    if len(args) > 1:
        sys.stderr.write("uso: check_pyright.py [pasta]\n")
        return 2
    synced = sync_base.main([TOOL, *args])
    if synced == 2:  # noqa: PLR2004 - o código de uso errado do sync_base
        return synced
    folder = Path(*args)
    config = load_config(folder / CONFIG)
    if config is None:
        return 1
    paths = candidate_files()
    if paths is None:
        return 1
    found = config_problems(config) + comment_problems(paths, folder, config)
    if found:
        sys.stderr.write(f"{HOOK}: fora do padrão Pyright da Welt Studio:\n")
        sys.stderr.writelines(f"  - {item}\n" for item in found)
        return 1
    return synced


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

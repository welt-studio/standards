#!/usr/bin/env python3
"""Hook `pyright-base`: mantém a cópia do padrão Pyright no projeto e confere que nada a contorna.

A cópia (`pyright-base.json`) é a do `sync_base.py`. Depois, o hook reprova o que religaria ou
trocaria as regras da base sem aparecer nela (README, "Pyright"):

- no `pyrightconfig.json`, qualquer chave além dos fatos do projeto (caminhos, ambiente, versão do
  Python) e um `extends` que não seja a cópia. A lista `strict` é o caso que motivou a trava: no
  Pyright ela religa toda regra do strict que a base desliga, como as `reportUnknown*`;
- nos `.py` que o Pyright analisa, o comentário de arquivo `# pyright: <modo ou regra>` (`strict`,
  `basic`, `reportX=false`), que faz o mesmo num arquivo só, e o `# type: ignore` antes de qualquer
  código, que silencia o arquivo inteiro. O `ignore` de uma linha passa.

Python stdlib, sem dependências.

Uso: `check_pyright.py [pasta]`, com a pasta do `pyrightconfig.json` (relativa à raiz) quando ele
não está na raiz.
"""

import io
import json
import posixpath
import re
import shutil
import subprocess
import sys
import tokenize
from pathlib import Path, PurePosixPath

import jsonc
import sync_base
from parsed import Table, items, table

CONFIG = "pyrightconfig.json"
BASE_COPY = "pyright-base.json"

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
# `# type: ignore` (com ou sem regras): antes de qualquer código, vale para o arquivo inteiro.
TYPE_IGNORE = re.compile(r"#\s*type:\s*ignore\b")
# O que pode vir antes do código sem tirar do `# type: ignore` o efeito de arquivo.
PREAMBLE = frozenset({tokenize.ENCODING, tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE})
# Pré-filtro do `git grep` (ERE): só os arquivos com um dos dois textos são tokenizados.
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


def file_comments(source: str) -> list[int]:
    """Linhas de `source` com comentário que troca as regras do arquivo: `# pyright: <modo ou
    regra>` em qualquer lugar, `# type: ignore` antes do código. Só comentários de verdade contam: o
    mesmo texto dentro de uma string não é lido pelo Pyright."""
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except tokenize.TokenError, SyntaxError:
        # Arquivo que não tokeniza já reprova no Ruff e no Pyright, com a causa.
        return []
    lines: list[int] = []
    preamble = True
    for token in tokens:
        preamble = preamble and token.type in PREAMBLE
        if token.type != tokenize.COMMENT:
            continue
        if PYRIGHT_FILE_COMMENT.match(token.string) or (
            preamble and TYPE_IGNORE.match(token.string)
        ):
            lines.append(token.start[0])
    return lines


def glob_regex(pattern: str) -> re.Pattern[str] | None:
    """O glob do Pyright (`**` atravessa pastas, `*` e `?` ficam numa só) como regex de caminho;
    `None` quando o padrão é a própria pasta do projeto. O `**` do fim sai: casar a pasta já basta,
    porque `matches` também tenta cada pasta acima do arquivo."""
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


def matches(path: PurePosixPath, pattern: str) -> bool:
    """`path` casa `pattern`, ele mesmo ou alguma pasta acima dele (como no `include`/`exclude`)."""
    regex = glob_regex(pattern)
    if regex is None:
        return True
    candidates = [path, *path.parents[:-1]]
    return any(regex.fullmatch(str(candidate)) for candidate in candidates)


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
    """Os comentários que trocam regra nos `paths` (relativos à raiz) que o Pyright analisa."""
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
        source = Path(path).read_text(encoding="utf-8", errors="replace")
        problems.extend(
            f"{path}:{line}: comentário de arquivo troca as regras da base"
            for line in file_comments(source)
        )
    return problems


def candidate_files() -> list[str] | None:
    """Os `.py` do git (relativos à raiz) com `pyright:` ou `type: ignore` no texto; `None`, com o
    motivo no stderr, fora de um repo git."""
    git = shutil.which("git")
    if git is None:
        sys.stderr.write("pyright-base: git não encontrado\n")
        return None
    result = subprocess.run(  # noqa: S603 - argumentos fixos, sem entrada do usuário
        [git, "grep", "-l", "-z", "-I", "-E", "-e", CANDIDATE, "--", "*.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    # O `git grep` sai com 1 quando nenhum arquivo casa: não é erro.
    if result.returncode not in (0, 1) or result.stderr:
        sys.stderr.write(f"pyright-base: git grep falhou: {result.stderr.strip()}\n")
        return None
    return [path for path in result.stdout.split("\0") if path]


def load_config(path: Path) -> Table | None:
    """O `pyrightconfig.json` em `path`; `None`, com o motivo no stderr, se falta ou é inválido."""
    if not path.is_file():
        sys.stderr.write(f'pyright-base: {path} não existe (com `"extends": "./{BASE_COPY}"`)\n')
        return None
    try:
        value = jsonc.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        sys.stderr.write(f"pyright-base: {path} não é JSON válido em UTF-8: {error}\n")
        return None
    if not isinstance(value, dict):
        sys.stderr.write(f"pyright-base: {path} não é um objeto JSON\n")
        return None
    return table(value)


def main(args: list[str]) -> int:
    if len(args) > 1:
        sys.stderr.write("uso: check_pyright.py [pasta]\n")
        return 2
    synced = sync_base.main(["pyright", *args])
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
        sys.stderr.write("pyright-base: fora do padrão Pyright da Welt Studio:\n")
        sys.stderr.writelines(f"  - {item}\n" for item in found)
        return 1
    return synced


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

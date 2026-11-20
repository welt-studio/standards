"""Os Dockerfiles versionados do projeto e as tags das imagens que eles usam, comum aos hooks que
conferem uma versão repetida numa imagem (`python-base`: a do uv; `pnpm-base`: a do pnpm).

A tag da imagem é cópia de uma versão que o Renovate sobe no mesmo PR: a do pnpm é o
`packageManager`; a do uv é o `version` do `astral-sh/setup-uv` dos workflows (o `required-version`
é só a mínima do terminal; ver `check_python.py`). O hook reprova a cópia que alguém escrever à mão
diferente, a tag por variável (que o Renovate não lê) e a imagem sem tag (a `latest`, que muda
sozinha). Python stdlib, sem dependências.
"""

import re
from pathlib import Path, PurePosixPath

from check_ruff import common_ignores, ignored
from repo import git_paths

# O que o `git ls-files` lista (o pathspec também pega `docs/Dockerfile.md`, que o nome tira).
PATHSPECS = ("*Dockerfile*", "*.dockerfile")
NAME = re.compile(r"Dockerfile(\.[^/]+)?|[^/]+\.[Dd]ockerfile")
DOCS = (".md", ".txt", ".rst")


def is_dockerfile(path: str, ignores: list[str]) -> bool:
    """Dockerfile do projeto: pelo nome, fora gerado e terceiros, e no working tree (apagado e ainda
    no índice do git, ou um submódulo com o nome, não há o que ler)."""
    name = PurePosixPath(path).name
    return (
        NAME.fullmatch(name) is not None
        and not name.endswith(DOCS)
        and not ignored(path, ignores)
        and Path(path).is_file()
    )


def dockerfile_paths(hook: str) -> list[str] | None:
    """Os Dockerfiles versionados (relativos à raiz); `None`, com o motivo no stderr, sem git."""
    paths = git_paths(hook, ["ls-files", "-z", "--", *PATHSPECS])
    if paths is None:
        return None
    ignores = common_ignores()
    return [path for path in paths if is_dockerfile(path, ignores)]


def lines(path: str) -> list[tuple[int, str]]:
    """As linhas de instrução (numeradas a partir de 1), sem as de comentário."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return [
        (number, line)
        for number, line in enumerate(text.splitlines(), start=1)
        if not line.lstrip().startswith("#")
    ]


def tags(paths: list[str], image: str) -> list[tuple[str, int, str | None]]:
    """Cada uso de `image` (`FROM`, `COPY --from=`, `--mount=from=`): o Dockerfile, a linha e a tag
    (`None` sem tag)."""
    usage = re.compile(rf"(?<![\w./-]){re.escape(image)}(?::(?P<tag>[^\s@]+))?")
    return [
        (path, number, match["tag"])
        for path in paths
        for number, line in lines(path)
        for match in usage.finditer(line)
    ]


def tag_version(tag: str) -> str:
    """A versão da tag, sem o sufixo de variante (`0.13.1-trixie-slim` → `0.13.1`)."""
    return tag.split("-", 1)[0]


def literal_tags(
    paths: list[str], image: str, hint: str
) -> tuple[list[tuple[str, str]], list[str]]:
    """As tags escritas de `image`, com onde cada uma está (`Dockerfile:linha`), e os usos sem tag
    ou com tag por variável, que o Renovate não sobe. `hint` diz que versão escrever."""
    literal: list[tuple[str, str]] = []
    problems: list[str] = []
    for path, number, tag in tags(paths, image):
        where = f"{path}:{number}"
        if tag is None:
            problems.append(f"{where}: `{image}` sem tag; escreva {hint}")
        elif "$" in tag:
            problems.append(f"{where}: `{image}`:{tag} por variável; escreva {hint}")
        else:
            literal.append((where, tag))
    return literal, problems


def tag_problems(paths: list[str], image: str, version: str, source: str) -> list[str]:
    """Cada uso de `image` cuja tag não é `version` (com sufixo de variante, como `-trixie-slim`, ou
    digest depois: `tag_version`). `source` diz onde a versão mora."""
    literal, problems = literal_tags(paths, image, f"a `{version}` do {source}")
    return problems + [
        f"{where}: `{image}`:{tag} diverge da `{version}` do {source}"
        for where, tag in literal
        if tag_version(tag) != version
    ]

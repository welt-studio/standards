"""Os Dockerfiles versionados do projeto e as tags das imagens que eles usam, comum aos hooks que
conferem uma versão repetida numa imagem (`python-base`: a do uv; `pnpm-base`: a do pnpm).

A versão tem uma declaração (o `required-version` do uv, o `packageManager` do pnpm), e a tag da
imagem é a cópia que o Renovate sobe no mesmo PR. O hook reprova a cópia que alguém escrever à mão
diferente, a tag por variável (que nenhum dos dois lê) e a imagem sem tag (a `latest`, que muda
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


def tag_problems(paths: list[str], image: str, version: str, source: str) -> list[str]:
    """Cada uso de `image` (`FROM`, `COPY --from=`, `--mount=from=`) cuja tag não é `version` (com
    sufixo de variante, como `-trixie-slim`, ou digest depois). `source` diz onde a versão mora."""
    usage = re.compile(rf"(?<![\w./-]){re.escape(image)}(?::(?P<tag>[^\s@]+))?")
    problems: list[str] = []
    for path in paths:
        for number, line in lines(path):
            for match in usage.finditer(line):
                tag = match["tag"]
                where = f"{path}:{number}: `{image}`"
                if tag is None:
                    problems.append(f"{where} sem tag; use a `{version}` do {source}")
                elif "$" in tag:
                    problems.append(f"{where}:{tag} por variável; escreva `{version}` ({source})")
                elif tag != version and not tag.startswith(f"{version}-"):
                    problems.append(f"{where}:{tag} diverge da `{version}` do {source}")
    return problems

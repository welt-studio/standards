#!/usr/bin/env python3
"""Hook `python-base`: o Python do projeto vem só do standards, e nada o declara de novo.

A cópia (`.python-version` na pasta do pacote) é a do `sync_base.py`, do `python/.python-version`
deste repo no `rev` declarado. Depois, o hook reprova a segunda declaração do Python (README,
"Python"):

- `default_language_version.python` no `.pre-commit-config.yaml`: os hooks herdam o Python que roda
  o pre-commit (`uv run pre-commit`, no ambiente do pacote), e a linha seria uma cópia que nada
  atualiza;
- `requires-python` do `pyproject.toml` do pacote diferente de `==<minor>.*` do minor da cópia: o
  uv recusa o Python da cópia (ou resolve o lock para outro);
- a imagem do Python num Dockerfile versionado (fora gerado e terceiros): a oficial (`python`, de
  qualquer registro) e a do uv com Python embutido (`uv:<versão>-python3.14-…`). A imagem parte do
  uv sem Python, e o `uv sync` instala o da cópia;
- o uv exato fora do lugar: o `[tool.uv] required-version` do pacote é a mínima do terminal
  (`>=<versão>`); a exata mora no `version` de cada `astral-sh/setup-uv` dos workflows e na tag da
  imagem do uv (`ghcr.io/astral-sh/uv`), cópias que o Renovate sobe juntas. O hook reprova a
  `==` (ou nenhuma) no `required-version`, o `setup-uv` que o Renovate não lê (`workflows.py`), a
  imagem sem tag ou por variável, cópias em versões diferentes (todas listadas, sem eleger a certa)
  e a exata menor que a mínima, que o `uv` recusaria.

Python stdlib, sem dependências.

Uso: `check_python.py <pasta>`, com a pasta (relativa à raiz) do pacote Python (`.` na raiz).
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import dockerfiles
import pyproject
import sync_base
import workflows
from parsed import Table, table

TOOL = "python"
HOOK = sync_base.hook_id(TOOL)
PRE_COMMIT_CONFIG = Path(".pre-commit-config.yaml")
UV_IMAGE = "ghcr.io/astral-sh/uv"
# O `required-version` é a mínima: no terminal vale qualquer uv a partir dela.
MINIMUM = re.compile(r">=(?P<version>\d+\.\d+\.\d+)")
# A versão literal, como o `setup-uv` e a tag a escrevem.
LITERAL_VERSION = re.compile(r"\d+\.\d+\.\d+")
# A chave de topo e o `python` dentro dela, em bloco ou na forma `{python: ...}`.
LANGUAGE_VERSION_KEY = re.compile(r"^default_language_version\s*:(?P<inline>.*)$")
PYTHON_KEY = re.compile(r"(^\s+|[{,]\s*)['\"]?python['\"]?\s*:")
# A imagem que traz o Python, depois das opções (`--platform`): a `python` de qualquer registro
# (`mirror.gcr.io/library/python`) e a do uv com Python na tag (`uv:0.13.1-python3.14-…`).
PYTHON_IMAGE = re.compile(
    r"^\s*FROM\s+(?:--\S+\s+)*"
    r"(?:(?:[^\s/]+/)*python(?:[:@\s]|$)|\S*/uv:\S*python\d)",
    re.IGNORECASE,
)


def standard_version() -> str:
    """A versão do Python do padrão (`3.14.8`)."""
    source = sync_base.BASES[TOOL][0]
    return (sync_base.ROOT / source).read_text(encoding="utf-8").strip()


def minor(version: str) -> str:
    """O minor de uma versão (`3.14.8` → `3.14`)."""
    return ".".join(version.split(".")[:2])


def declares_python(config: str) -> bool:
    """Se o `.pre-commit-config.yaml` tem `default_language_version.python`."""
    lines = config.splitlines()
    for index, line in enumerate(lines):
        match = LANGUAGE_VERSION_KEY.match(line)
        if match is None:
            continue
        if PYTHON_KEY.search(match["inline"]):
            return True
        for child in lines[index + 1 :]:
            # Linha vazia e comentário (mesmo na coluna 0) não fecham o bloco.
            stripped = child.strip()
            if stripped and not stripped.startswith("#") and not child[0].isspace():
                break
            if PYTHON_KEY.match(child):
                return True
    return False


def requires_python_problem(value: object, expected: str, path: Path) -> str | None:
    if value == expected:
        return None
    found = f"`{value}`" if isinstance(value, str) else "ausente"
    return (
        f"{path}: `requires-python` é {found}, e o Python do padrão pede `{expected}` "
        "(depois de trocar, rode `uv lock`)"
    )


def python_image_problems(paths: list[str]) -> list[str]:
    return [
        f"{path}:{number}: a imagem declara o Python de novo; parta da imagem do uv sem Python e "
        "deixe o `uv sync` instalar o do `.python-version`"
        for path in paths
        for number, line in dockerfiles.lines(path)
        if PYTHON_IMAGE.match(line)
    ]


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def minimum_problems(config: Table, config_path: Path) -> tuple[str | None, list[str]]:
    """A mínima do `required-version`; ou nenhuma, com o problema."""
    required = table(table(config.get("tool")).get("uv")).get("required-version")
    match = MINIMUM.fullmatch(required) if isinstance(required, str) else None
    if match is not None:
        return match["version"], []
    found = f"`{required}`" if isinstance(required, str) else "ausente"
    message = (
        f"{config_path}: `[tool.uv] required-version` é {found}, e o padrão pede a mínima "
        "`>=<versão>`; a exata é a do `version` do `astral-sh/setup-uv` dos workflows"
    )
    return None, [message]


def exact_copies(
    pins: list[workflows.Pin], dockerfile_paths: list[str]
) -> tuple[dict[str, list[str]], list[str]]:
    """Cada versão exata do uv e onde ela está (os `setup-uv` lidos e as tags literais da imagem);
    e os problemas de cada cópia que não dá uma versão."""
    copies: dict[str, list[str]] = defaultdict(list)
    found = [
        f"{pin.path}:{pin.line}: `astral-sh/setup-uv` sem a versão que o Renovate lê; escreva "
        '`version: "X.Y.Z"` como a primeira chave do `with:` logo abaixo do `uses:` (sem '
        "`version-file` nem variável)"
        for pin in pins
        if pin.version is None
    ]
    for pin in pins:
        if pin.version is not None:
            copies[pin.version].append(f"{pin.path}:{pin.line}")
    hint = "a versão exata do uv, a do `version` do `setup-uv`"
    literal, problems = dockerfiles.literal_tags(dockerfile_paths, UV_IMAGE, hint)
    for where, tag in literal:
        version = dockerfiles.tag_version(tag)
        if LITERAL_VERSION.fullmatch(version):
            copies[version].append(where)
        else:
            problems.append(f"{where}: `{UV_IMAGE}`:{tag} não começa pela versão; escreva {hint}")
    return copies, found + problems


def uv_problems(
    config: Table | None,
    config_path: Path,
    dockerfile_paths: list[str],
    pins: list[workflows.Pin],
) -> list[str]:
    """O uv mínimo no `required-version` e o exato igual em todo `setup-uv` e imagem do uv."""
    minimum, found = minimum_problems(config, config_path) if config is not None else (None, [])
    copies, problems = exact_copies(pins, dockerfile_paths)
    found += problems
    versions = sorted(copies, key=version_key)
    if len(versions) > 1:
        listed = "; ".join(f"`{version}` em {', '.join(copies[version])}" for version in versions)
        found.append(f"o uv exato precisa ser um só, e as cópias divergem: {listed}")
    if minimum is not None and versions and version_key(versions[0]) < version_key(minimum):
        found.append(
            f"{config_path}: a mínima `>={minimum}` do `required-version` passa da `{versions[0]}` "
            f"em {', '.join(copies[versions[0]])}, que o `uv` recusaria"
        )
    return found


def main(args: list[str]) -> int:
    if len(args) != 1:
        sys.stderr.write("uso: check_python.py <pasta>\n")
        return 2
    synced = sync_base.main([TOOL, *args])
    folder = Path(args[0])
    if not folder.is_dir():
        return synced
    found: list[str] = []
    if PRE_COMMIT_CONFIG.is_file() and declares_python(
        PRE_COMMIT_CONFIG.read_text(encoding="utf-8")
    ):
        found.append(
            f"{PRE_COMMIT_CONFIG}: `default_language_version.python` declara o Python de novo; "
            "tire a linha (os hooks usam o Python do `uv run pre-commit`)"
        )
    # Uma falha de leitura (`pyproject.toml`, git) já foi ao stderr; as outras conferências seguem,
    # para tudo aparecer numa rodada só.
    config_path = folder / "pyproject.toml"
    config = pyproject.load(config_path, HOOK)
    paths = dockerfiles.dockerfile_paths(HOOK)
    pins = workflows.pins(HOOK)
    if config is not None:
        expected = f"=={minor(standard_version())}.*"
        problem = requires_python_problem(
            table(config.get("project")).get("requires-python"), expected, config_path
        )
        if problem:
            found.append(problem)
    if paths is not None:
        found += python_image_problems(paths)
        if pins is not None:
            found += uv_problems(config, config_path, paths, pins)
    unreadable = config is None or paths is None or pins is None
    if found:
        sys.stderr.write(f"{HOOK}: fora do padrão Python da Welt Studio:\n")
        sys.stderr.writelines(f"  - {item}\n" for item in found)
    return 1 if found or unreadable else synced


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

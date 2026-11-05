#!/usr/bin/env python3
"""Hooks `ruff`, `ruff-format` e `pyright`: rodam a ferramenta do projeto (a versão do `uv.lock` do
pacote Python, pelo `uv run`) nos arquivos do commit.

O commit que muda uma config (a cópia do padrão, a config do projeto) ou o `uv.lock` (a versão da
ferramenta, os stubs) muda o resultado de todo arquivo do pacote sem tocar nenhum deles: nesse caso
a ferramenta roda no pacote inteiro. Sem arquivo nenhum (o projeto declara `pass_filenames: false`,
como o Pyright de quem não tem fila), também. Python stdlib, sem dependências.

O Ruff roda de dentro do pacote (`uv run --directory`), como na CI: ele acha a config de cada
arquivo como sempre acha (inclusive a de uma subpasta) e aplica as exclusões do padrão. O Pyright
roda da raiz, com o `pyrightconfig.json` da raiz, ou o do pacote quando a raiz não tem.

Uso: `run_python_tool.py <ruff|ruff-format|pyright> <pasta do pacote> [arquivos...]`. A pasta vem
do `args:` do hook no projeto (`.` quando o pacote é a raiz); os arquivos, do pre-commit.
"""

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path, PurePosixPath

import check_pyright
import check_ruff
from globs import inside

# Os ids dos hooks no `.pre-commit-hooks.yaml`, que são também o modo do script.
RUFF = "ruff"
RUFF_FORMAT = "ruff-format"
PYRIGHT = "pyright"
MODES = (RUFF, RUFF_FORMAT, PYRIGHT)

LOCK = "uv.lock"
# Os arquivos que, no commit, levam a ferramenta a rodar no pacote inteiro (fora o `uv.lock`, que
# vale para todas). O `files` de cada hook no `.pre-commit-hooks.yaml` precisa casar com todos
# (`tests/test_run_python_tool.py` confere).
RUFF_CONFIGS = (check_ruff.BASE_COPY, *check_ruff.CONFIG_NAMES)
PYRIGHT_CONFIGS = (check_pyright.CONFIG, check_pyright.BASE_COPY)
CONFIGS = {RUFF: RUFF_CONFIGS, RUFF_FORMAT: RUFF_CONFIGS, PYRIGHT: PYRIGHT_CONFIGS}

# As extensões que cada ferramenta confere (as mesmas do hook `*-base` dela).
SOURCES = {
    RUFF: check_ruff.SOURCES,
    RUFF_FORMAT: check_ruff.SOURCES,
    PYRIGHT: check_pyright.SOURCES,
}
# O subcomando de cada modo. O `ruff` corrige o que sabe (`--fix`) e reprova o resto.
SUBCOMMANDS = {
    RUFF: ["ruff", "check", "--fix"],
    RUFF_FORMAT: ["ruff", "format"],
    PYRIGHT: ["pyright"],
}


def is_source(mode: str, path: PurePosixPath) -> bool:
    return any(path.match(pattern) for pattern in SOURCES[mode])


def is_package_lock(path: PurePosixPath, package: PurePosixPath) -> bool:
    """`path` é o `uv.lock` do pacote: o dele, ou o de uma pasta acima (o do workspace)."""
    return path.name == LOCK and inside(package, path.parent) is not None


def configures_ruff(path: str) -> bool:
    """O `pyproject.toml` só configura o Ruff com `[tool.ruff]`: sem ela (dependência que o
    Renovate subiu), ele não muda o resultado. Apagado ou inválido, conta: o Ruff vai dizer."""
    if PurePosixPath(path).name != "pyproject.toml":
        return True
    try:
        return check_ruff.ruff_table(Path(path)) is not None
    except OSError, tomllib.TOMLDecodeError, UnicodeDecodeError:
        return True


def changes_ruff(path: PurePosixPath, package: PurePosixPath) -> bool:
    """`path` muda o resultado do Ruff no pacote inteiro: a cópia do padrão, onde estiver, ou uma
    config do Ruff dentro do pacote."""
    if path.name == check_ruff.BASE_COPY:
        return True
    return (
        path.name in check_ruff.CONFIG_NAMES
        and inside(path, package) is not None
        and configures_ruff(path.as_posix())
    )


def ruff_command(mode: str, package: Path, files: list[str]) -> list[str]:
    root = PurePosixPath(package.as_posix())
    paths = [PurePosixPath(path) for path in files]
    run = ["run", "--directory", package.as_posix(), *SUBCOMMANDS[mode]]
    if not paths or any(changes_ruff(path, root) or is_package_lock(path, root) for path in paths):
        return [*run, "."]
    # Os caminhos do pre-commit são da raiz; o Ruff roda de dentro do pacote.
    relative = [inside(path, root) for path in paths if is_source(mode, path)]
    targets = [path.as_posix() for path in relative if path is not None]
    return [*run, *targets] if targets else []


def pyright_folder(package: Path) -> Path:
    """A pasta do `pyrightconfig.json`: a raiz, ou a do pacote quando a raiz não tem."""
    if Path(check_pyright.CONFIG).is_file():
        return Path()
    return package


def pyright_command(package: Path, files: list[str]) -> list[str] | None:
    """`None`, com o motivo no stderr, quando o `pyrightconfig.json` falta ou é inválido."""
    folder = pyright_folder(package)
    config = check_pyright.load_config(folder / check_pyright.CONFIG, PYRIGHT)
    if config is None:
        return None
    run = ["run", "--project", package.as_posix(), *SUBCOMMANDS[PYRIGHT]]
    if folder != Path():
        run = [*run, "--project", folder.as_posix()]
    root = PurePosixPath(package.as_posix())
    paths = [PurePosixPath(path) for path in files]
    if not paths or any(
        path.name in PYRIGHT_CONFIGS or is_package_lock(path, root) for path in paths
    ):
        return run
    # Só o que o `pyrightconfig.json` manda analisar: o de fora (outra pasta, migrations) passado
    # pelo nome seria conferido mesmo assim.
    ignores = check_pyright.base_ignores()
    config_root = PurePosixPath(folder.as_posix())
    targets: list[str] = []
    for path in paths:
        relative = inside(path, config_root)
        if (
            is_source(PYRIGHT, path)
            and relative is not None
            and check_pyright.analyzed(relative, config, ignores)
        ):
            targets.append(path.as_posix())
    return [*run, *targets] if targets else []


def command(mode: str, package: Path, files: list[str]) -> list[str] | None:
    """Os argumentos do `uv` para o commit com `files`; vazio quando não há o que conferir; `None`,
    com o motivo no stderr, quando a config falta."""
    if mode == PYRIGHT:
        return pyright_command(package, files)
    return ruff_command(mode, package, files)


def main(args: list[str]) -> int:
    if len(args) < 2 or args[0] not in MODES:  # noqa: PLR2004 - o modo e a pasta
        sys.stderr.write(f"uso: run_python_tool.py <{'|'.join(MODES)}> <pasta> [arquivos...]\n")
        return 2
    mode, folder, *files = args
    package = Path(folder)
    # A pasta vem do `args` do hook no projeto: errada, o hook diz qual é.
    if not package.is_dir():
        sys.stderr.write(f"{mode}: a pasta {package} (args do hook) não existe\n")
        return 1
    uv_args = command(mode, package, files)
    if uv_args is None:
        return 1
    if not uv_args:
        return 0
    uv = shutil.which("uv")
    if uv is None:
        sys.stderr.write(f"{mode}: uv não encontrado\n")
        return 1
    return subprocess.run(  # noqa: S603 - o uv do PATH, com argumentos do hook
        [uv, *uv_args], check=False
    ).returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

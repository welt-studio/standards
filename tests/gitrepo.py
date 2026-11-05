"""Repo git de mentira para os testes dos hooks que leem os arquivos versionados (`check_pyright`,
`check_ruff`): um jeito só de rodar o git e de escrever um arquivo do projeto."""

import subprocess
from pathlib import Path


def git(folder: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=folder, check=True, capture_output=True)  # noqa: S603, S607


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")

#!/usr/bin/env python3
"""Hook `gitignore-base`: os caminhos do `gitignore/required` do padrão ficam fora do git.

Cada caminho da lista (arquivo local de ferramenta, que pode levar segredo) precisa ser ignorado
pelo `.gitignore` do projeto e não pode estar versionado. O exclude global da máquina
(`core.excludesFile`) não conta: ele não existe na CI nem na máquina de outra pessoa, e um commit lá
levaria o arquivo. Python stdlib, sem dependências.

Uso: `check_gitignore.py`, na raiz do projeto.
"""

import os
import sys
from pathlib import Path

from repo import git_paths

HOOK = "gitignore-base"
REQUIRED = Path(__file__).resolve().parent.parent / "gitignore" / "required"


def required_paths(text: str) -> list[str]:
    """Os caminhos da lista: uma linha cada, sem as vazias e os comentários."""
    stripped = (line.strip() for line in text.splitlines())
    return [line for line in stripped if line and not line.startswith("#")]


def problems(required: list[str], ignored: list[str], tracked: list[str]) -> list[str]:
    found = [f"{path}: falta no `.gitignore`" for path in required if path not in ignored]
    found.extend(f"{path}: está versionado (`git rm --cached {path}`)" for path in tracked)
    return found


def main(args: list[str]) -> int:
    if args:
        sys.stderr.write("uso: check_gitignore.py\n")
        return 2
    required = required_paths(REQUIRED.read_text(encoding="utf-8"))
    # `--no-index`: o arquivo versionado também é conferido contra o `.gitignore` (sem a flag, o git
    # responde que ele não é ignorado, porque está no índice). O `check-ignore` só aceita `-z` com
    # `--stdin`: a saída vem uma por linha, e os caminhos da lista não têm quebra de linha.
    output = git_paths(
        HOOK,
        ["-c", f"core.excludesFile={os.devnull}", "check-ignore", "--no-index", "--", *required],
        empty_ok=True,
    )
    tracked = git_paths(HOOK, ["ls-files", "-z", "--", *required])
    if output is None or tracked is None:
        return 1
    ignored = [path for chunk in output for path in chunk.splitlines()]
    found = problems(required, ignored, tracked)
    if found:
        sys.stderr.write(f"{HOOK}: fora do padrão de `.gitignore` da Welt Studio:\n")
        sys.stderr.writelines(f"  - {item}\n" for item in found)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

"""O git do projeto, comum aos hooks que leem os arquivos versionados (`git ls-files`, `git grep`):
um jeito só de achar o executável, rodar e relatar a falha. Python stdlib, sem dependências.
"""

import shutil
import subprocess
import sys


def git_paths(hook: str, args: list[str], *, empty_ok: bool = False) -> list[str] | None:
    """Os caminhos (relativos à raiz) que `git <args>` lista com `-z`; `None`, com o motivo no
    stderr, sem git ou fora de um repo. `empty_ok`: a saída 1 é "nada casou" (o `git grep`)."""
    git = shutil.which("git")
    if git is None:
        sys.stderr.write(f"{hook}: git não encontrado\n")
        return None
    result = subprocess.run(  # noqa: S603 - o git do PATH, com argumentos dos hooks
        [git, *args], capture_output=True, text=True, check=False
    )
    accepted = (0, 1) if empty_ok else (0,)
    if result.returncode not in accepted or result.stderr:
        sys.stderr.write(f"{hook}: git {args[0]} falhou: {result.stderr.strip()}\n")
        return None
    return [path for path in result.stdout.split("\0") if path]

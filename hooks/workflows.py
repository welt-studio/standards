"""Os workflows do GitHub Actions versionados e o uv exato de cada `astral-sh/setup-uv` neles (hook
`python-base`).

A versão exata do uv da CI mora no `version` de cada `setup-uv`: uma cópia por step, que o Renovate
sobe junto da tag da imagem do uv (regex do `renovate/default.json5`). O hook lê a versão com a
mesma regex, tirada do preset do `rev`, a partir de cada `uses:`: o step que o Renovate não leria
(`version-file`, versão por variável, `version` que não é a primeira chave do `with:`) reprova, em
vez de ficar para trás sem ninguém ver.

Só os workflows da pasta: o `setup-uv` de uma action composta (`.github/actions/*/action.yml`) o
Renovate também não lê (o `managerFilePatterns` do preset). Python stdlib, sem dependências.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import jsonc
import sync_base
from parsed import items, table
from repo import git_paths

# O GitHub só lê os workflows da própria pasta, sem subpasta (o pathspec do git pega subpasta).
FOLDER = PurePosixPath(".github/workflows")
PATHSPECS = (f"{FOLDER}/*.yml", f"{FOLDER}/*.yaml")
PRESET = Path("renovate/default.json5")
ACTION = "astral-sh/setup-uv@"
# Cada step que usa a action, fora de comentário. A regex do preset é aplicada a partir da chave.
USES = re.compile(
    rf"^[ \t]*(?:-[ \t]+)?(?P<key>uses):[ \t]*[\"']?{re.escape(ACTION)}", re.MULTILINE
)
# Grupo nomeado do JavaScript (`(?<nome>`), que o `re` escreve `(?P<nome>`.
JS_GROUP = re.compile(r"\(\?<(?=[A-Za-z])")


@dataclass(frozen=True)
class Pin:
    """Um `setup-uv`: o workflow, a linha do `uses:` e a versão que o Renovate lê (ou nenhuma)."""

    path: str
    line: int
    version: str | None


def workflow_paths(hook: str) -> list[str] | None:
    """Os workflows versionados (relativos à raiz); `None`, com o motivo no stderr, sem git."""
    paths = git_paths(hook, ["ls-files", "-z", "--", *PATHSPECS])
    if paths is None:
        return None
    return [path for path in paths if PurePosixPath(path).parent == FOLDER and Path(path).is_file()]


def preset_pattern() -> re.Pattern[str]:
    """A regex do `setup-uv` no preset do Renovate (a única declaração do formato que ele lê).
    `ValueError` quando o preset não tem exatamente uma ou não é JSON5 (`JSONDecodeError`);
    `OSError` sem o arquivo; `re.error` quando ela não compila."""
    preset = table(jsonc.loads_json5((sync_base.ROOT / PRESET).read_text(encoding="utf-8")))
    (pattern,) = (
        found
        for manager in items(preset.get("customManagers"))
        for found in items(table(manager).get("matchStrings"))
        if isinstance(found, str) and ACTION in found
    )
    return re.compile(JS_GROUP.sub("(?P<", pattern))


def pins(hook: str) -> list[Pin] | None:
    """Cada `setup-uv` dos workflows, com a versão que a regex do preset lê a partir do `uses:`;
    `None`, com o motivo no stderr, sem git ou quando o preset não se lê. Sem `setup-uv`, o preset
    nem é lido."""
    paths = workflow_paths(hook)
    if paths is None:
        return None
    steps = [
        (path, text, match)
        for path in paths
        for text in [Path(path).read_text(encoding="utf-8", errors="replace")]
        for match in USES.finditer(text)
    ]
    if not steps:
        return []
    try:
        pattern = preset_pattern()
    except (OSError, ValueError, re.error) as error:
        sys.stderr.write(f"{hook}: a regex do `setup-uv` em {PRESET} não se lê: {error}\n")
        return None
    found: list[Pin] = []
    for path, text, match in steps:
        read = pattern.match(text, match.start("key"))
        line = text.count("\n", 0, match.start()) + 1
        found.append(Pin(path, line, read["currentValue"] if read else None))
    return found

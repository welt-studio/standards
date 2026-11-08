#!/usr/bin/env python3
"""Hook `pnpm-base`: confere no projeto a política de scripts de instalação do padrão.

Nenhuma dependência roda script de instalação e o projeto só se instala pelo pnpm, com duas
declarações (README, "pnpm: scripts de instalação das dependências"): `strictDepBuilds: false` no
`pnpm-workspace.yaml`, sem `allowBuilds`, e `devEngines.packageManager` com o pnpm e
`onFail: "error"` no `package.json`. O hook reprova, com o motivo, quando uma delas falta ou quando
volta o que elas substituem.

A versão do pnpm é a do `packageManager` do mesmo `package.json` (`pnpm@<versão>`). A tag da imagem
`ghcr.io/pnpm/pnpm` nos Dockerfiles versionados é a cópia dela: o hook reprova a que divergir, a
tag por variável e a imagem sem tag. Python stdlib, sem dependências.

Uso: `check_pnpm.py [pasta]`, com a pasta do `pnpm-workspace.yaml` (relativa à raiz) quando ele não
está na raiz, como em `frontend/`.
"""

import json
import re
import sys
from pathlib import Path

import dockerfiles
from parsed import Table, table

HOOK = "pnpm-base"
PNPM_IMAGE = "ghcr.io/pnpm/pnpm"
# `pnpm@12.14.0`, com ou sem o hash que o Corepack acrescenta (`+sha512.…`).
PACKAGE_MANAGER = re.compile(r"pnpm@(?P<version>\d+\.\d+\.\d+)(?:\+\S+)?")

# Chave de primeiro nível do YAML (coluna 0), com o valor e um comentário opcional. O
# `pnpm-workspace.yaml` só precisa ser lido nas chaves de primeiro nível, e a stdlib não tem YAML.
TOP_LEVEL_KEY = re.compile(r"^(?P<key>[A-Za-z][\w-]*):(?P<value>[^#]*)")

# O que a política substitui: lista de pacotes (cada `true` liberaria as versões futuras), e os
# desligamentos que pulam também os scripts do projeto sem avisar o que foi pulado.
FORBIDDEN_KEYS = {
    "allowBuilds": "sem `allowBuilds`: pacote fora dele nunca roda script",
    "onlyBuiltDependencies": "sem `onlyBuiltDependencies` (a lista antiga, removida no pnpm 11)",
    "dangerouslyAllowAllBuilds": "sem `dangerouslyAllowAllBuilds`: liberaria todo script",
    "ignoreScripts": "sem `ignoreScripts`: o `strictDepBuilds: false` já não roda nada e avisa",
}


def top_level_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for line in text.splitlines():
        match = TOP_LEVEL_KEY.match(line)
        if match:
            keys[match["key"]] = match["value"].strip()
    return keys


def workspace_problems(text: str) -> list[str]:
    keys = top_level_keys(text)
    problems: list[str] = []
    if keys.get("strictDepBuilds") != "false":
        problems.append("pnpm-workspace.yaml: `strictDepBuilds: false`")
    problems.extend(
        f"pnpm-workspace.yaml: {reason}" for key, reason in FORBIDDEN_KEYS.items() if key in keys
    )
    return problems


def package_problems(package: Table) -> list[str]:
    manager = table(table(package.get("devEngines")).get("packageManager"))
    if manager.get("name") == "pnpm" and manager.get("onFail") == "error":
        return []
    expected = '{ "name": "pnpm", "onFail": "error" }'
    return [f"package.json: `devEngines.packageManager` = {expected} (o npm recusa o projeto)"]


def image_problems(paths: list[str], package: Table, package_path: Path) -> list[str]:
    """A tag da imagem do pnpm contra o `packageManager`, quando a imagem é usada."""
    if not any(PNPM_IMAGE in line for path in paths for _, line in dockerfiles.lines(path)):
        return []
    declared = package.get("packageManager")
    match = PACKAGE_MANAGER.fullmatch(declared) if isinstance(declared, str) else None
    if match is None:
        message = (
            f"{package_path}: `packageManager` = `pnpm@<versão>`: os Dockerfiles usam a "
            f"`{PNPM_IMAGE}`, e a tag dela é a cópia dessa versão"
        )
        return [message]
    source = f"`packageManager` de {package_path}"
    return dockerfiles.tag_problems(paths, PNPM_IMAGE, match["version"], source)


def main(args: list[str]) -> int:
    if len(args) > 1:
        sys.stderr.write("uso: check_pnpm.py [pasta]\n")
        return 2
    folder = Path(*args)
    workspace = folder / "pnpm-workspace.yaml"
    package = folder / "package.json"
    missing = [str(path) for path in (workspace, package) if not path.is_file()]
    if missing:
        sys.stderr.write(f"{HOOK}: não existe: {', '.join(missing)}\n")
        return 1
    try:
        manifest = table(json.loads(package.read_text(encoding="utf-8")))
    except json.JSONDecodeError as error:
        sys.stderr.write(f"{HOOK}: {package} não é JSON válido: {error}\n")
        return 1
    found = workspace_problems(workspace.read_text(encoding="utf-8")) + package_problems(manifest)
    if found:
        sys.stderr.write(f"{HOOK}: fora do padrão de scripts de instalação da Welt Studio:\n")
        sys.stderr.writelines(f"  - falta {item}\n" for item in found)
    paths = dockerfiles.dockerfile_paths(HOOK)
    images = [] if paths is None else image_problems(paths, manifest, package)
    if images:
        sys.stderr.write(f"{HOOK}: imagem do pnpm fora da versão do projeto:\n")
        sys.stderr.writelines(f"  - {item}\n" for item in images)
    return 1 if found or images or paths is None else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Hook `ruff-base`: mantém a cópia do padrão Ruff no projeto e confere que nada a contorna.

A cópia (`ruff-base.toml`) é a do `sync_base.py`. Depois, o hook reprova o que desligaria a base sem
aparecer nela (README, "Ruff"):

- em toda config de Ruff versionada (`ruff.toml`, `.ruff.toml` e o `[tool.ruff]` de um
  `pyproject.toml`, mesmo vazio, que já é a config da pasta para o Ruff):
  - sem `extend` que chegue à cópia, direto ou por outra config do projeto;
  - `select` próprio, que substitui a lista da base (regra a mais entra pelo `extend-select`);
  - `exclude`, `extend-exclude` ou `include`, que tiram arquivos do Ruff inteiro (o que não é nosso
    está na lista comum de ignores da base);
  - `ignore`/`per-file-ignores` que desliguem uma regra protegida, pelo código, por um prefixo ou
    pelo `ALL`: o `TID251` (a lista de APIs proibidas, com `Any` e `cast`) e o `PGH004` (sem ele, o
    `noqa` sem código calaria o `TID251`);
  - `banned-api` redefinido sem os itens da base (a tabela do projeto substitui a da base inteira);
- nos `.py`, `.pyi` e `.ipynb` versionados, o `noqa` que desliga uma regra protegida na linha, e o
  `noqa` de arquivo (`ruff: noqa`, `flake8: noqa`) sem códigos ou com uma delas.

Python stdlib, sem dependências.

Uso: `check_ruff.py [pasta]`, com a pasta (relativa à raiz) onde a cópia vai, quando não é a raiz.
"""

import json
import posixpath
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath

import sync_base
from comments import file_comments
from globs import matches
from parsed import Table, items, table
from repo import git_paths

TOOL = "ruff"
HOOK = sync_base.hook_id(TOOL)
BASE_COPY = sync_base.copy_name(TOOL)
BANNED_API_RULE = "TID251"
BLANKET_NOQA_RULE = "PGH004"
# O que nenhuma config ou `noqa` do projeto desliga.
PROTECTED_RULES = (BANNED_API_RULE, BLANKET_NOQA_RULE)
PROTECTED_REASON = f"{BANNED_API_RULE} (`Any` e `cast` proibidos) ou {BLANKET_NOQA_RULE}"
# As listas de regras desligadas, no nível de cima (forma antiga) e no `[lint]`.
IGNORE_KEYS = ("ignore", "extend-ignore")
PER_FILE_KEYS = ("per-file-ignores", "extend-per-file-ignores")
# A seleção de arquivos: é da base (a lista comum de ignores), não do projeto.
FILE_SELECTION_KEYS = ("exclude", "extend-exclude", "include")
CONFIG_NAMES = ("ruff.toml", ".ruff.toml", "pyproject.toml")
# O que o Ruff confere.
SOURCES = ("*.py", "*.pyi", "*.ipynb")
# O `noqa` como o Ruff o acha no texto do comentário (sem o `#` do começo): de arquivo com o prefixo
# (`ruff:` ou `flake8:`), de linha sem ele, com ou sem a lista de códigos. Os exemplos ficam nos
# testes: escritos aqui, num comentário, seriam o próprio contorno.
NOQA = re.compile(
    r"(?:^|#)\s*(?P<file>(?:ruff|flake8)\s*:\s*)?noqa(?:\s*:\s*(?P<codes>[\w\s,]+))?",
    re.IGNORECASE,
)


def covers(code: object, rule: str) -> bool:
    """`code` desliga `rule`: ele mesmo, um prefixo dele (`TID`, `T`) ou o `ALL`."""
    if not isinstance(code, str):
        return False
    code = code.strip().upper()
    return code == "ALL" or (code != "" and rule.startswith(code))


def covers_protected(code: object) -> bool:
    return any(covers(code, rule) for rule in PROTECTED_RULES)


def sections(ruff: Table) -> list[Table]:
    """O nível de cima e o `[lint]`: o Ruff aceita as opções de lint nos dois."""
    return [ruff, table(ruff.get("lint"))]


def base_banned_api() -> list[str]:
    """Os itens do `banned-api` da base: a declaração é o `ruff/base.toml` deste repo."""
    base = tomllib.loads((sync_base.ROOT / "ruff" / "base.toml").read_text(encoding="utf-8"))
    tidy = table(table(base.get("lint")).get("flake8-tidy-imports"))
    return sorted(table(tidy.get("banned-api")).keys())


def extend_target(ruff: Table, config: PurePosixPath) -> PurePosixPath | None:
    """O arquivo que o `extend` de `config` aponta, relativo à raiz; `None` sem `extend` ou fora do
    repo (um `..` além da raiz)."""
    extend = ruff.get("extend")
    if not isinstance(extend, str):
        return None
    target = posixpath.normpath(posixpath.join(config.parent.as_posix(), extend))
    if target == ".." or target.startswith("../") or posixpath.isabs(target):
        return None
    return PurePosixPath(target)


def reaches_copy(
    config: PurePosixPath, configs: dict[PurePosixPath, Table], copy: PurePosixPath
) -> bool:
    """A cadeia de `extend` que sai de `config` chega à cópia, só por configs do projeto."""
    seen: set[PurePosixPath] = set()
    current = config
    while current not in seen:
        seen.add(current)
        target = extend_target(configs[current], current)
        if target == copy:
            return True
        if target is None or target not in configs:
            return False
        current = target
    return False


def ruff_problems(
    ruff: Table, config: PurePosixPath, *, extends_base: bool, banned_api: list[str]
) -> list[str]:
    problems: list[str] = []
    if not extends_base:
        problems.append(f"{config}: `extend` que chegue a `{BASE_COPY}` (sem ele, a base não vale)")
    problems.extend(
        f"{config}: `{key}` tira arquivos do Ruff (o que não é nosso está nos ignores da base)"
        for key in FILE_SELECTION_KEYS
        if key in ruff
    )
    if "exclude" in table(ruff.get("lint")):
        problems.append(f"{config}: `lint.exclude` tira arquivos do lint")
    for section in sections(ruff):
        if "select" in section:
            problems.append(f"{config}: `select` substitui a lista da base (use `extend-select`)")
        ignored = [code for key in IGNORE_KEYS for code in items(section.get(key))]
        per_file = [
            code
            for key in PER_FILE_KEYS
            for codes in table(section.get(key)).values()
            for code in items(codes)
        ]
        if any(covers_protected(code) for code in [*ignored, *per_file]):
            problems.append(f"{config}: desliga o {PROTECTED_REASON}")
        tidy = table(section.get("flake8-tidy-imports"))
        if "banned-api" in tidy:
            missing = [api for api in banned_api if api not in table(tidy["banned-api"])]
            if missing:
                problems.append(
                    f"{config}: `banned-api` sem os itens da base: {', '.join(missing)}"
                )
    return problems


def ruff_table(path: Path) -> Table | None:
    """A config de Ruff em `path` (o `[tool.ruff]` de um `pyproject.toml`, mesmo vazio); `None`
    quando o arquivo não configura o Ruff. `tomllib.TOMLDecodeError` quando não é TOML."""
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    if path.name == "pyproject.toml":
        tool = table(config.get("tool"))
        return table(tool["ruff"]) if "ruff" in tool else None
    return config


def common_ignores() -> list[str]:
    """Gerado e de terceiros: a lista comum do padrão (`eslint/ignores.json`, a declaração)."""
    declared = table(json.loads((sync_base.ROOT / "eslint" / "ignores.json").read_text("utf-8")))
    return [
        pattern
        for group in declared.values()
        for pattern in items(group)
        if isinstance(pattern, str)
    ]


def ignored(path: str, ignores: list[str]) -> bool:
    return any(matches(PurePosixPath(path), pattern) for pattern in ignores)


def load_configs(
    paths: list[str], ignores: list[str]
) -> tuple[dict[PurePosixPath, Table], list[str]]:
    """As configs de Ruff versionadas (fora gerado e terceiros), e o problema de cada uma que não é
    TOML."""
    configs: dict[PurePosixPath, Table] = {}
    problems: list[str] = []
    for path in paths:
        relative = PurePosixPath(path)
        # Apagado no working tree e ainda no índice do git: não há o que o Ruff leia.
        if relative.name not in CONFIG_NAMES or ignored(path, ignores) or not Path(path).is_file():
            continue
        try:
            ruff = ruff_table(Path(path))
        except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
            problems.append(f"{path}: não é TOML válido: {error}")
            continue
        if ruff is not None:
            configs[relative] = ruff
    return configs, problems


def config_problems(paths: list[str], copy: PurePosixPath, ignores: list[str]) -> list[str]:
    configs, problems = load_configs(paths, ignores)
    banned_api = base_banned_api()
    for config, ruff in configs.items():
        extends_base = reaches_copy(config, configs, copy)
        problems.extend(
            ruff_problems(ruff, config, extends_base=extends_base, banned_api=banned_api)
        )
    return problems


def noqa_problem(comment: str) -> str | None:
    """O `noqa` de `comment` (com o `#`) que desliga uma regra protegida; `None` quando nenhum."""
    for noqa in NOQA.finditer(comment[1:]):
        codes = [code for code in re.split(r"[\s,]+", noqa["codes"] or "") if code]
        if noqa["file"] and not codes:
            return "`noqa` de arquivo sem códigos desliga todo o lint do arquivo"
        if any(covers_protected(code) for code in codes):
            return f"`noqa` desliga o {PROTECTED_REASON}"
    return None


def comment_problems(paths: list[str], ignores: list[str]) -> list[str]:
    problems: list[str] = []
    for path in paths:
        if ignored(path, ignores) or not Path(path).is_file():
            continue
        for line, comment in file_comments(Path(path)):
            problem = noqa_problem(comment)
            if problem:
                problems.append(f"{path}:{line}: {problem}")
    return problems


def main(args: list[str]) -> int:
    if len(args) > 1:
        sys.stderr.write("uso: check_ruff.py [pasta]\n")
        return 2
    synced = sync_base.main([TOOL, *args])
    if synced == 2:  # noqa: PLR2004 - o código de uso errado do sync_base
        return synced
    config_paths = git_paths(HOOK, ["ls-files", "-z", "--", *(f"*{n}" for n in CONFIG_NAMES)])
    source_paths = git_paths(
        HOOK, ["grep", "-l", "-z", "-I", "-i", "-e", "noqa", "--", *SOURCES], empty_ok=True
    )
    if config_paths is None or source_paths is None:
        return 1
    ignores = common_ignores()
    copy = PurePosixPath(posixpath.normpath(posixpath.join(*args, BASE_COPY)))
    found = config_problems(config_paths, copy, ignores) + comment_problems(source_paths, ignores)
    if found:
        sys.stderr.write(f"{HOOK}: fora do padrão Ruff da Welt Studio:\n")
        sys.stderr.writelines(f"  - {item}\n" for item in found)
        return 1
    return synced


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

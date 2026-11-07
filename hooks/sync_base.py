#!/usr/bin/env python3
"""Hooks `ruff-base`, `pyright-base`, `prettier-base`, `jscpd-base` e `python-base`: mantêm no
projeto a cópia do padrão da tag.

O Ruff (`extend`) e o Pyright (`extends`) só leem arquivo local, e o Prettier e o jscpd não herdam
config de pacote, então o padrão chega ao projeto como cópia (e a config do projeto, quando há,
herda dela). O hook roda da cópia deste repo que o pre-commit baixou no `rev` declarado: a versão do
padrão fica só nesse `rev`. Como um formatter, reescreve a cópia quando ela diverge (ou não existe)
e sai com 1; a segunda rodada passa. O `ruff-base`, o `pyright-base` e o `python-base` chegam aqui
pelo `check_ruff.py`, pelo `check_pyright.py` e pelo `check_python.py`, que depois conferem o que
contornaria a cópia. Python stdlib, sem dependências.

Uso: `sync_base.py <ruff|pyright|prettier|jscpd|python> [pasta]`. A cópia vai na raiz do projeto,
ou na `pasta` (relativa à raiz) quando a ferramenta roda de dentro dela, como o Prettier em
`frontend/`.
"""

import sys
from pathlib import Path

# A raiz deste repo, onde estão os padrões (`ruff/`, `pyright/`, ...); o script mora em `hooks/`.
ROOT = Path(__file__).resolve().parent.parent

# Padrão: as cópias, cada uma (arquivo do padrão neste repo, nome da cópia no projeto, marca de
# comentário). Sem marca (`None`), o formato não aceita comentário nem chave a mais (o JSON do
# jscpd avisa campo desconhecido a cada execução): a cópia sai sem o aviso de "gerado", que fica no
# comentário do hook no `.pre-commit-config.yaml` do projeto.
BASES: dict[str, tuple[tuple[str, str, str | None], ...]] = {
    "ruff": (("ruff/base.toml", "ruff-base.toml", "#"),),
    "pyright": (("pyright/base.json", "pyright-base.json", "//"),),
    "prettier": (("prettier/ignore", ".prettierignore", "#"),),
    "jscpd": (
        ("jscpd/base.json", ".jscpd.json", None),
        ("jscpd/semantic.json", ".jscpd-semantic.json", None),
    ),
    # O `.python-version` vai na pasta do pacote Python, onde o uv o procura. Sem cabeçalho: não é
    # garantido que cada leitor do arquivo pule comentário.
    "python": (("python/.python-version", ".python-version", None),),
}


def hook_id(name: str) -> str:
    """O id do hook de `name` no `.pre-commit-hooks.yaml` (`ruff` → `ruff-base`): a declaração que
    as mensagens dos hooks usam."""
    return f"{name}-base"


def copy_name(name: str) -> str:
    """O nome da (primeira) cópia de `name` no projeto (`ruff` → `ruff-base.toml`)."""
    return BASES[name][0][1]


def header(name: str, source: str, comment: str) -> str:
    lines = (
        f"GERADO pelo hook `{hook_id(name)}` de github.com/welt-studio/standards ({source}).",
        "NÃO EDITE: o hook desfaz qualquer mudança. A versão do padrão é o `rev` desse hook no",
        ".pre-commit-config.yaml; regra nova entra no standards, para todos os projetos.",
    )
    return "".join(f"{comment} {line}\n" for line in lines) + "\n"


def sync(name: str, source: str, target: Path, comment: str | None) -> bool:
    """Deixa `target` igual ao padrão; diz se precisou escrever."""
    text = (ROOT / source).read_text(encoding="utf-8")
    expected = text if comment is None else header(name, source, comment) + text
    current = target.read_text(encoding="utf-8") if target.exists() else None
    if current == expected:
        return False
    target.write_text(expected, encoding="utf-8", newline="\n")
    action = "criado" if current is None else "restaurado"
    hook = hook_id(name)
    sys.stdout.write(
        f"{hook}: {target} {action} a partir do padrão (standards). Adicione-o ao commit.\n"
    )
    return True


def main(args: list[str]) -> int:
    if len(args) not in (1, 2) or args[0] not in BASES:
        sys.stderr.write(f"uso: sync_base.py <{'|'.join(BASES)}> [pasta]\n")
        return 2
    name = args[0]
    folder = Path(*args[1:])
    # A pasta vem do `args` do hook no projeto: errada (digitada errado, ou movida), o hook diz qual
    # é em vez de cair num traceback do `write_text`.
    if not folder.is_dir():
        sys.stderr.write(f"{hook_id(name)}: a pasta {folder} (args do hook) não existe\n")
        return 1
    # Todas as cópias são conferidas, mesmo depois da primeira que divergir.
    written = [
        sync(name, source, folder / target, comment) for source, target, comment in BASES[name]
    ]
    return 1 if any(written) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

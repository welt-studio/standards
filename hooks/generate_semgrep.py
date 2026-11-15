#!/usr/bin/env python3
"""Gerador das regras do Semgrep: `semgrep/models/` + `semgrep/queries/` -> `semgrep/rules/`.

As regras portam a suíte padrão do CodeQL, uma consulta por arquivo. O que se repete entre elas
(fontes, sumidouros, sanitizadores, propagadores, membros de `patterns`/`pattern-either` e regex)
mora uma vez só, em um modelo, e as consultas o referenciam. Este script expande as referências e
escreve as regras que o Semgrep lê; `semgrep/rules/` é saída e nunca se edita à mão. Requer PyYAML
(grupo `dev` do `pyproject.toml`): roda só neste repo, não nos projetos.

Estrutura (tudo em `semgrep/`):

- `models/<grupo>/<nome>.yaml`: um modelo. O arquivo é uma lista (um trecho de lista, de itens) ou
  um texto (uma regex). O nome do modelo é o caminho sem o `.yaml`: `python/django-sources`.
- `queries/<linguagem>/<consulta>.yaml`: as regras de uma consulta do CodeQL, no formato do Semgrep
  (`rules:`), com as partes compartilhadas trocadas por referência. `<linguagem>` é `python`,
  `javascript` ou `actions`, e `<consulta>` é o id do CodeQL sem o prefixo da linguagem, com `/`
  trocada por `__` (`js/xss-through-dom` -> `javascript/xss-through-dom`).
- `rules/<linguagem>/<consulta>.yaml`: a saída, com o mesmo caminho da consulta.

Sintaxe das referências (um mapa de uma chave só):

- `{$model: javascript/express-sources}`, como elemento de uma lista: expande no lugar, e os itens
  da lista do modelo entram na posição dele (um modelo pode referenciar outro).
- `{$text: common/sensitive-names}`, como valor inteiro: vira o texto do modelo (uma regex).

Só vira modelo o item que nomeia uma API (`names_api`: um padrão com ao menos um nome que não é
metavariável nem palavra da linguagem) e a regex; item só de metavariável e sintaxe fica inline.

Erros (saída 1, todos listados): referência desconhecida ou do tipo errado, ciclo entre modelos,
modelo vazio, modelo que ninguém usa, modelo usado por uma consulta só (não há o que
compartilhar), item que nomeia API (ou regex) repetido em dois arquivos sem estar em um modelo,
regra sem
`metadata.codeql` coerente com o caminho, e fonte definida a partir de outra fonte: um
`metavariable-pattern` dentro de `pattern-sources` que referencia um modelo de fonte imita, por
forma de código, um fluxo que o motor não segue (o valor de uma fonte chegando a outro ponto); o
caminho é um propagador ou um limite provado (`semgrep/test/limits.json`). A saída já sai no
formato que o Prettier deixa (aspas duplas, listas em bloco), para o hook dele não reescrever o
arquivo.

Uso: `generate_semgrep.py` escreve as regras; `generate_semgrep.py --check` só confere, e sai com 1,
listando os arquivos, quando `semgrep/rules/` está desatualizada. Erro de uso sai com 2.
"""

import json
import re
import sys
from pathlib import Path

import yaml

from semgrep_files import KEYWORDS, bare_names

HOOK = "generate-semgrep"
REGENERATE = "rode `uv run hooks/generate_semgrep.py`"
ROOT = Path(__file__).resolve().parent.parent / "semgrep"
MODELS = "models"
QUERIES = "queries"
RULES = "rules"

# Pasta da linguagem na consulta -> prefixo do id dela no CodeQL (`py/use-of-input`).
CODEQL_PREFIX = {"python": "py", "javascript": "js", "actions": "actions"}

# Chaves cujos elementos de lista são "itens" compartilháveis, e chaves cujo valor é uma regex.
ITEM_LISTS = frozenset(
    {"pattern-sources", "pattern-sinks", "pattern-sanitizers", "pattern-propagators"}
    | {"patterns", "pattern-either"}
)
REGEX_KEYS = frozenset({"regex", "pattern-regex"})

MODEL_KEY = "$model"
TEXT_KEY = "$text"

# Um modelo só se justifica quando mais de um arquivo o usa.
MIN_USERS = 2

HEADER = (
    "# GERADO por `hooks/generate_semgrep.py` a partir de `semgrep/models/` e `semgrep/queries/`.\n"
    "# NÃO EDITE: edite o modelo ou a consulta e rode `uv run hooks/generate_semgrep.py`.\n"
)

# Um valor de YAML (o que o `safe_load` devolve para este formato): a árvore das regras.
type Node = bool | int | float | str | list[Node] | dict[str, Node] | None


class GeneratorError(Exception):
    """Falha de leitura ou de expansão, com a mensagem pronta para o usuário."""


def to_node(value: object, where: str) -> Node:
    """`value` (o que o `yaml.safe_load` devolve) como `Node`; chave que não é texto reprova."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list):
        return [to_node(item, where) for item in value]
    if isinstance(value, dict):
        result: dict[str, Node] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                message = f"{where}: chave que não é texto: {key!r}"
                raise GeneratorError(message)
            result[key] = to_node(item, where)
        return result
    message = f"{where}: valor sem equivalente em YAML simples: {value!r}"
    raise GeneratorError(message)


def read_tree(folder: Path) -> dict[str, Node]:
    """Os arquivos `.yaml` da pasta (e subpastas), por nome: o caminho relativo sem a extensão."""
    found: dict[str, Node] = {}
    for path in sorted(folder.rglob("*.yaml")):
        name = path.relative_to(folder).with_suffix("").as_posix()
        try:
            loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            message = f"{path}: YAML inválido: {error}"
            raise GeneratorError(message) from error
        found[name] = to_node(loaded, str(path))
    return found


def reference(node: Node, key: str) -> str | None:
    """O nome referenciado quando `node` é uma referência `{key: nome}`; `None` nos outros casos."""
    if isinstance(node, dict) and len(node) == 1:
        name = node.get(key)
        if isinstance(name, str):
            return name
    return None


def is_reference(node: Node) -> bool:
    return reference(node, MODEL_KEY) is not None or reference(node, TEXT_KEY) is not None


def references(node: Node, where: str) -> list[tuple[str, str]]:
    """Cada referência de `node`, na ordem do arquivo: (`$model` ou `$text`, nome)."""
    found: list[tuple[str, str]] = []
    if isinstance(node, list):
        for item in node:
            model = reference(item, MODEL_KEY)
            if model is None:
                found.extend(references(item, where))
            else:
                found.append((MODEL_KEY, model))
    elif isinstance(node, dict):
        text = reference(node, TEXT_KEY)
        if text is not None:
            found.append((TEXT_KEY, text))
            return found
        if MODEL_KEY in node:
            message = f"{where}: `{MODEL_KEY}` só vale como elemento de lista"
            raise GeneratorError(message)
        for value in node.values():
            found.extend(references(value, where))
    return found


def expand(node: Node, models: dict[str, Node], stack: tuple[str, ...], where: str) -> Node:
    """`node` com as referências trocadas pelo conteúdo dos modelos. `stack`: os modelos em
    expansão, para reprovar o ciclo."""
    if isinstance(node, list):
        result: list[Node] = []
        for item in node:
            model = reference(item, MODEL_KEY)
            if model is None:
                result.append(expand(item, models, stack, where))
            else:
                body = expand_model(model, MODEL_KEY, models, stack, where)
                if not isinstance(body, list):
                    message = f"{where}: `{MODEL_KEY}: {model}` aponta para um texto, não uma lista"
                    raise GeneratorError(message)
                result.extend(body)
        return result
    if isinstance(node, dict):
        text = reference(node, TEXT_KEY)
        if text is not None:
            body = expand_model(text, TEXT_KEY, models, stack, where)
            if not isinstance(body, str):
                message = f"{where}: `{TEXT_KEY}: {text}` aponta para uma lista, não um texto"
                raise GeneratorError(message)
            return body
        if MODEL_KEY in node:
            message = f"{where}: `{MODEL_KEY}` só vale como elemento de lista"
            raise GeneratorError(message)
        return {key: expand(value, models, stack, where) for key, value in node.items()}
    return node


def expand_model(
    name: str, kind: str, models: dict[str, Node], stack: tuple[str, ...], where: str
) -> Node:
    if name not in models:
        message = f"{where}: `{kind}: {name}` não existe em `{MODELS}/`"
        raise GeneratorError(message)
    if name in stack:
        cycle = " -> ".join((*stack, name))
        message = f"{where}: ciclo entre modelos: {cycle}"
        raise GeneratorError(message)
    return expand(models[name], models, (*stack, name), f"{MODELS}/{name}.yaml")


def sharing_errors(models: dict[str, Node], queries: dict[str, Node]) -> list[str]:
    """Modelo que ninguém usa e modelo usado (direta ou indiretamente) por uma consulta só."""
    users: dict[str, set[str]] = {name: set() for name in models}
    for owner, tree in [(f"{MODELS}/{n}", t) for n, t in models.items()] + [
        (f"{QUERIES}/{n}", t) for n, t in queries.items()
    ]:
        for _, name in references(tree, owner):
            if name in users:
                users[name].add(owner)

    def reached(name: str, seen: frozenset[str]) -> set[str]:
        """As consultas que chegam em `name`, passando por outros modelos."""
        found: set[str] = set()
        for owner in users[name]:
            if owner.startswith(f"{QUERIES}/"):
                found.add(owner)
            elif owner not in seen:
                found |= reached(owner.removeprefix(f"{MODELS}/"), seen | {owner})
        return found

    errors: list[str] = []
    for name in sorted(models):
        if models[name] in ([], None, ""):
            errors.append(f"{MODELS}/{name}.yaml: modelo vazio (apague e tire as referências)")
        elif not users[name]:
            errors.append(f"{MODELS}/{name}.yaml: modelo sem uso (apague ou use)")
        elif len(reached(name, frozenset())) < MIN_USERS:
            errors.append(
                f"{MODELS}/{name}.yaml: usado por uma consulta só (deixe inline na consulta)"
            )
    return errors


def names_api_text(text: str) -> bool:
    """O padrão `text` cita ao menos um nome que não é metavariável, palavra da linguagem nem texto
    entre aspas."""
    return any(word not in KEYWORDS for word in bare_names(text))


def names_api(node: Node) -> bool:
    """O item (ou parte dele) tem um padrão que nomeia uma API. Regex não conta: ela é tratada à
    parte, como texto."""
    if isinstance(node, list):
        return any(names_api(item) for item in node)
    if isinstance(node, dict):
        for key, value in node.items():
            if key in REGEX_KEYS:
                continue
            if isinstance(value, str):
                if key.startswith("pattern") and names_api_text(value):
                    return True
            elif names_api(value):
                return True
    return False


def names_api_expanded(item: Node, models: dict[str, Node]) -> bool:
    """`names_api` do item com as referências expandidas; item com referência quebrada não conta
    (o erro da referência já é apontado à parte)."""
    try:
        return names_api(expand(item, models, (), ""))
    except GeneratorError:
        return False


def shareable(node: Node, models: dict[str, Node], key: str | None = None) -> list[str]:
    """Os itens (elementos das listas de `ITEM_LISTS`) que nomeiam uma API e as regex de `node`
    que não são referência, em JSON canônico: o que, repetido entre arquivos, tem de morar em um
    modelo. Item só de metavariável e sintaxe (`$X`, `$F(...)`) pode se repetir à vontade."""
    found: list[str] = []
    if isinstance(node, list):
        for item in node:
            if key in ITEM_LISTS and not is_reference(item) and names_api_expanded(item, models):
                found.append(json.dumps(item, sort_keys=True, ensure_ascii=False))
            found.extend(shareable(item, models, key))
    elif isinstance(node, dict):
        for name, value in node.items():
            if name in REGEX_KEYS and isinstance(value, str):
                found.append(json.dumps(value, ensure_ascii=False))
            else:
                found.extend(shareable(value, models, name))
    return found


def duplicate_errors(models: dict[str, Node], queries: dict[str, Node]) -> list[str]:
    """Item ou regex que aparece em dois arquivos (consulta ou modelo) e não está em um modelo."""
    owners: dict[str, set[str]] = {}
    trees = [(f"{MODELS}/{n}.yaml", t) for n, t in models.items()]
    trees += [(f"{QUERIES}/{n}.yaml", t) for n, t in queries.items()]
    for owner, tree in trees:
        for item in shareable(tree, models):
            owners.setdefault(item, set()).add(owner)
    errors: list[str] = []
    for item, files in sorted(owners.items()):
        if len(files) >= MIN_USERS:
            where = ", ".join(sorted(files))
            errors.append(f"repetido em {where} e fora de um modelo: {item[:100]}")
    return errors


def model_closure(names: set[str], models: dict[str, Node]) -> set[str]:
    """Os modelos `names` e os que eles referenciam, direta ou indiretamente."""
    found: set[str] = set()
    pending = list(names)
    while pending:
        name = pending.pop()
        if name in found or name not in models:
            continue
        found.add(name)
        pending.extend(ref for _, ref in references(models[name], f"{MODELS}/{name}.yaml"))
    return found


def source_items(queries: dict[str, Node]) -> list[tuple[str, Node]]:
    """Cada item de `pattern-sources` das consultas, com o arquivo dele."""
    items: list[tuple[str, Node]] = []
    for name, tree in queries.items():
        rules = tree.get("rules") if isinstance(tree, dict) else None
        for rule in rules if isinstance(rules, list) else []:
            sources = rule.get("pattern-sources") if isinstance(rule, dict) else None
            items.extend(
                (f"{QUERIES}/{name}.yaml", item)
                for item in (sources if isinstance(sources, list) else [])
            )
    return items


def metavariable_pattern_refs(node: Node, where: str) -> set[str]:
    """Os modelos referenciados dentro dos `metavariable-pattern` de `node`."""
    found: set[str] = set()
    if isinstance(node, list):
        for item in node:
            found |= metavariable_pattern_refs(item, where)
    elif isinstance(node, dict):
        for key, value in node.items():
            if key == "metavariable-pattern":
                found |= {ref for kind, ref in references(value, where) if kind == MODEL_KEY}
            else:
                found |= metavariable_pattern_refs(value, where)
    return found


def derived_source_errors(models: dict[str, Node], queries: dict[str, Node]) -> list[str]:
    """Fonte definida a partir de outra fonte (ver o docstring do módulo)."""
    items = source_items(queries)
    direct = {reference(item, MODEL_KEY) for _, item in items}
    sources = model_closure({name for name in direct if name is not None}, models)
    errors: list[str] = []
    for where, item in items:
        used = model_closure(metavariable_pattern_refs(item, where), models) & sources
        if used:
            errors.append(
                f"{where}: fonte definida a partir de outra fonte ({', '.join(sorted(used))}):"
                " imita fluxo; use um propagador ou registre o limite"
            )
    return sorted(set(errors))


def codeql_id(name: str) -> str | None:
    """O id do CodeQL que o caminho da consulta declara (`javascript/a__b` -> `js/a/b`)."""
    folder, _, query = name.partition("/")
    prefix = CODEQL_PREFIX.get(folder)
    return None if prefix is None else f"{prefix}/{query.replace('__', '/')}"


def rule_errors(name: str, tree: Node) -> list[str]:
    """A consulta tem `rules:` e cada regra declara `metadata.codeql` igual ao id do caminho."""
    where = f"{QUERIES}/{name}.yaml"
    expected = codeql_id(name)
    if expected is None:
        return [f"{where}: pasta de linguagem desconhecida (use {', '.join(CODEQL_PREFIX)})"]
    rules = tree.get("rules") if isinstance(tree, dict) else None
    if not isinstance(rules, list) or not rules:
        return [f"{where}: falta a lista `rules`"]
    errors: list[str] = []
    for rule in rules:
        metadata = rule.get("metadata") if isinstance(rule, dict) else None
        declared = metadata.get("codeql") if isinstance(metadata, dict) else None
        if declared != expected:
            errors.append(f"{where}: `metadata.codeql` deve ser `{expected}` (veio {declared!r})")
    return errors


# O que o Prettier não reescreve de um escalar: texto simples (sem aspas) só nestes casos.
PLAIN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:[ ./-][A-Za-z0-9_]+)*")
RESERVED = frozenset({"true", "false", "null", "yes", "no", "on", "off", "y", "n", "nan", "inf"})
ESCAPE = re.compile(r'\\[^"]')


def scalar(value: str) -> str:
    """Um texto de uma linha como o Prettier o deixa: simples quando dá, senão entre aspas. Aspas
    duplas, salvo quando o texto tem `"` e nenhuma barra invertida (aí, simples)."""
    if PLAIN.fullmatch(value) and value.lower() not in RESERVED:
        return value
    raw = json.dumps(value, ensure_ascii=False)
    if not ESCAPE.search(raw) and '"' in value:
        return "'" + value.replace("'", "''") + "'"
    return raw


def block_scalar(value: str) -> tuple[str, list[str]] | None:
    """Um texto de várias linhas como bloco literal (`|`): o cabeçalho e as linhas. `None` quando o
    bloco não representa o texto sem ambiguidade (espaço no fim ou no começo, linha vazia na ponta,
    caractere de controle): aí o texto sai entre aspas."""
    body = value.removesuffix("\n")
    lines = body.split("\n")
    printable = all(ch in {"\n", "\t"} or ch.isprintable() for ch in value)
    if (
        not printable
        or value.endswith("\n\n")
        or lines[0] == ""
        or lines[0][0] in " \t"
        or any(line != line.rstrip() for line in lines)
    ):
        return None
    return ("|" if value.endswith("\n") else "|-"), lines


def render_scalar(value: Node, indent: int) -> tuple[str, list[str]]:
    """O escalar como (texto depois de `chave:` ou `-`, linhas que seguem, já com a indentação)."""
    if value is None:
        return "null", []
    if isinstance(value, bool):
        return ("true" if value else "false"), []
    if isinstance(value, int | float):
        return repr(value), []
    if not isinstance(value, str):
        return ("[]" if isinstance(value, list) else "{}"), []
    if "\n" in value:
        block = block_scalar(value)
        if block is not None:
            header, lines = block
            pad = " " * (indent + 2)
            return header, [(pad + line) if line else "" for line in lines]
    return scalar(value), []


def render_lines(node: Node, indent: int) -> list[str]:
    """`node` (lista ou mapa não vazio) em YAML de bloco, indentado em `indent`."""
    pad = " " * indent
    lines: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            lines.extend(render_entry(f"{pad}{scalar(key)}:", value, indent))
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, dict | list) and item:
                inner = render_lines(item, indent + 2)
                lines.append(f"{pad}- {inner[0][indent + 2 :]}")
                lines.extend(inner[1:])
            else:
                lines.extend(render_entry(f"{pad}-", item, indent))
    return lines


def render_entry(prefix: str, value: Node, indent: int) -> list[str]:
    """Uma entrada (`chave:` ou `-`) com o valor: na mesma linha, ou nas linhas de baixo."""
    if isinstance(value, dict | list) and value:
        nested = render_lines(value, indent + 2)
        return [prefix, *nested]
    text, rest = render_scalar(value, indent)
    return [f"{prefix} {text}", *rest]


def render(tree: Node) -> str:
    """O arquivo de regras: o cabeçalho de gerado e o YAML da árvore, com `\\n` no fim."""
    return HEADER + "\n".join(render_lines(tree, 0)) + "\n"


def generate(root: Path) -> tuple[dict[str, str], list[str]]:
    """As regras que `root` (`semgrep/`) gera, por caminho relativo a `rules/`, e os erros."""
    try:
        models = read_tree(root / MODELS)
        queries = read_tree(root / QUERIES)
    except GeneratorError as error:
        return {}, [str(error)]
    errors: list[str] = []
    outputs: dict[str, str] = {}
    for name, tree in queries.items():
        errors.extend(rule_errors(name, tree))
        try:
            outputs[f"{name}.yaml"] = render(expand(tree, models, (), f"{QUERIES}/{name}.yaml"))
        except GeneratorError as error:
            errors.append(str(error))
    try:
        errors.extend(sharing_errors(models, queries))
    except GeneratorError as error:
        errors.append(str(error))
    errors.extend(duplicate_errors(models, queries))
    errors.extend(derived_source_errors(models, queries))
    return outputs, errors


def stale_files(root: Path, outputs: dict[str, str]) -> list[str]:
    """Os arquivos de `rules/` que diferem do gerado: ausentes, diferentes ou que sobraram."""
    rules = root / RULES
    stale = [
        name
        for name, text in sorted(outputs.items())
        if not (rules / name).is_file() or (rules / name).read_text(encoding="utf-8") != text
    ]
    if rules.is_dir():
        present = {path.relative_to(rules).as_posix() for path in rules.rglob("*.yaml")}
        stale.extend(sorted(present - outputs.keys()))
    return sorted(stale)


def write_rules(root: Path, outputs: dict[str, str], stale: list[str]) -> None:
    """Grava o que mudou e apaga o que sobrou de consulta que não existe mais."""
    rules = root / RULES
    for name in stale:
        path = rules / name
        if name in outputs:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(outputs[name], encoding="utf-8", newline="\n")
        else:
            path.unlink()


def run(root: Path, *, check: bool) -> int:
    outputs, errors = generate(root)
    if errors:
        sys.stderr.write(f"{HOOK}: erros nos modelos e nas consultas:\n")
        sys.stderr.writelines(f"  - {error}\n" for error in errors)
        return 1
    stale = stale_files(root, outputs)
    if check:
        if stale:
            sys.stderr.write(f"{HOOK}: `semgrep/rules/` desatualizada ({REGENERATE}):\n")
            sys.stderr.writelines(f"  - {name}\n" for name in stale)
        return 1 if stale else 0
    write_rules(root, outputs, stale)
    return 0


def main(args: list[str]) -> int:
    if args not in ([], ["--check"]):
        sys.stderr.write("uso: generate_semgrep.py [--check]\n")
        return 2
    return run(ROOT, check=bool(args))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

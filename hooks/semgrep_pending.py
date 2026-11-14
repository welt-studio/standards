"""As pendências da paridade com o CodeQL (`semgrep/test/pending.json`) e a evidência de cada uma.

Por consulta, seis listas, como `pasta/arquivo:linha` dentro de `semgrep/test/vendor/codeql/`:

- `missing`: o CodeQL acusa e a regra ainda não pega. A paridade é esta lista vazia.
- `spurious`: o CodeQL acusa, mas o próprio teste dele marca a linha como alarme falso (`SPURIOUS`,
  ou `OK` sem `NOT`). Não pegar é o certo.
- `limited`: o CodeQL acusa e o Semgrep não tem como pegar; aponta para um limite provado em
  `semgrep/test/limits.json`, com a reprodução mínima em `semgrep/test/limits/<limite>/`.
- `extra`: a regra acusa onde o CodeQL não acusa. A paridade é esta lista vazia.
- `accepted`: acusa a mais, mas o teste do CodeQL marca a linha como vulnerável e o CodeQL não pega
  (`MISSING`, `NOT OK`, `BAD`, `$ Alert`): o acerto é nosso.
- `overfit`: nomes que o padrão da regra cita e que só o teste do CodeQL inventa
  (`test-names.txt`): a regra está presa ao teste, não a uma API. A paridade é esta lista vazia.

A evidência das categorias aceitas é conferida aqui, sobre os arquivos do teste: nenhum aceite passa
sem a marca do CodeQL na linha, nenhum limite sem a reprodução.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from semgrep_files import codeql_ids, pattern_names

ROOT = Path(__file__).resolve().parent.parent
VENDOR = ROOT / "semgrep" / "test" / "vendor" / "codeql"
PENDING = ROOT / "semgrep" / "test" / "pending.json"
LIMITS = ROOT / "semgrep" / "test" / "limits.json"
LIMITS_DIR = ROOT / "semgrep" / "test" / "limits"
TEST_NAMES = VENDOR / "test-names.txt"
RULES = ROOT / "semgrep" / "rules"
# A largura de linha do Prettier do padrão (`prettier/index.mjs`), a do `pending.json`.
PRINT_WIDTH = 100
# As marcas dos testes do CodeQL, na linha do caso ou na de cima.
SPURIOUS_MARK = re.compile(r"SPURIOUS|(?<!NOT )(?<!NOT_)\bOK\b")
VULNERABLE_MARK = re.compile(r"MISSING|NOT[ _]OK|\bBAD\b|\$\s*Alert")
CATEGORIES = ("missing", "spurious", "limited", "extra", "accepted", "overfit")


@dataclass(frozen=True)
class Pending:
    """As pendências de uma consulta (ver o docstring do módulo)."""

    missing: frozenset[str] = frozenset()
    spurious: frozenset[str] = frozenset()
    limited: dict[str, str] = field(default_factory=dict[str, str])
    extra: frozenset[str] = frozenset()
    accepted: frozenset[str] = frozenset()
    overfit: frozenset[str] = frozenset()

    def known_missing(self) -> set[str]:
        """O que o CodeQL acusa e a regra não pega, em qualquer das categorias."""
        return set(self.missing | self.spurious | self.limited.keys())

    def known_extra(self) -> set[str]:
        return set(self.extra | self.accepted)


def strings(value: object) -> frozenset[str]:
    if not isinstance(value, list):
        return frozenset()
    return frozenset(item for item in value if isinstance(item, str))


def string_map(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {k: v for k, v in value.items() if isinstance(k, str) and isinstance(v, str)}


def load_pending(text: str) -> dict[str, Pending]:
    """O `pending.json`: consulta → pendências."""
    document: object = json.loads(text)
    pending: dict[str, Pending] = {}
    for query, entry in document.items() if isinstance(document, dict) else []:
        if isinstance(query, str) and isinstance(entry, dict):
            pending[query] = Pending(
                missing=strings(entry.get("missing")),
                spurious=strings(entry.get("spurious")),
                limited=string_map(entry.get("limited")),
                extra=strings(entry.get("extra")),
                accepted=strings(entry.get("accepted")),
                overfit=strings(entry.get("overfit")),
            )
    return pending


def classify(missing: set[str], extra: set[str], overfit: set[str], previous: Pending) -> Pending:
    """As pendências medidas agora, mantendo a categoria que cada caso já tinha (o alarme falso do
    CodeQL, o limite, o acerto nosso). Caso novo entra como `missing` ou `extra`."""
    return Pending(
        missing=frozenset(
            item
            for item in missing
            if item not in previous.spurious and item not in previous.limited
        ),
        spurious=frozenset(missing & previous.spurious),
        limited={item: name for item, name in previous.limited.items() if item in missing},
        extra=frozenset(extra - previous.accepted),
        accepted=frozenset(extra & previous.accepted),
        overfit=frozenset(overfit),
    )


def render_value(key: str, value: frozenset[str] | dict[str, str], comma: str) -> list[str]:
    """Uma categoria no formato do Prettier: lista que cabe numa linha fica numa linha só; objeto
    sempre aberto (o Prettier mantém aberto o que já vem aberto)."""
    name = json.dumps(key)
    if isinstance(value, dict):
        items = sorted(value.items())
        lines = [f"    {name}: {{"]
        lines.extend(
            f"      {json.dumps(k)}: {json.dumps(v)}{',' if n < len(items) - 1 else ''}"
            for n, (k, v) in enumerate(items)
        )
        return [*lines, f"    }}{comma}"]
    ordered = sorted(value)
    inline = f"    {name}: {json.dumps(ordered, ensure_ascii=False)}{comma}"
    if len(inline) <= PRINT_WIDTH:
        return [inline]
    lines = [f"    {name}: ["]
    lines.extend(
        f"      {json.dumps(item, ensure_ascii=False)}{',' if n < len(ordered) - 1 else ''}"
        for n, item in enumerate(ordered)
    )
    return [*lines, f"    ]{comma}"]


def render(pending: dict[str, Pending]) -> str:
    """O `pending.json` no formato que o Prettier deixa, em ordem estável e sem categoria vazia:
    regravar sem mudança de pendência não muda o arquivo."""
    entries = [(query, entry) for query, entry in sorted(pending.items()) if any_pending(entry)]
    lines = ["{"]
    for index, (query, entry) in enumerate(entries):
        lines.append(f"  {json.dumps(query, ensure_ascii=False)}: {{")
        filled = [(key, getattr(entry, key)) for key in CATEGORIES if getattr(entry, key)]
        for position, (key, value) in enumerate(filled):
            lines.extend(render_value(key, value, "," if position < len(filled) - 1 else ""))
        lines.append("  }," if index < len(entries) - 1 else "  }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def any_pending(entry: Pending) -> bool:
    return any(getattr(entry, key) for key in CATEGORIES)


def case_lines(case: str, vendor: Path) -> list[str]:
    """A linha do caso e a de cima, no arquivo do teste (`pasta/arquivo:linha`)."""
    path, _, line = case.rpartition(":")
    target = vendor / path
    if not line.isdigit() or not target.is_file():
        return []
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    number = int(line)
    return lines[max(number - 2, 0) : number]


def load_limits(text: str) -> dict[str, dict[str, object]]:
    """O `limits.json`: limite → capacidade que falta, recursos tentados, linhas que deviam sair."""
    document: object = json.loads(text)
    if not isinstance(document, dict):
        return {}
    return {k: v for k, v in document.items() if isinstance(k, str) and isinstance(v, dict)}


def limit_problems(limits: dict[str, dict[str, object]], limits_dir: Path) -> list[str]:
    """Todo limite tem a capacidade que falta, os recursos tentados, as linhas que o Semgrep devia
    acusar e a reprodução (`rule.yaml` mais o código) na pasta dele."""
    found: list[str] = []
    for name, limit in sorted(limits.items()):
        if not isinstance(limit.get("capability"), str) or not limit.get("capability"):
            found.append(f"limite {name}: falta `capability`")
        if not strings(limit.get("tried")):
            found.append(f"limite {name}: falta `tried`")
        if not strings(limit.get("should_find")):
            found.append(f"limite {name}: falta `should_find`")
        if not (limits_dir / name / "rule.yaml").is_file():
            found.append(
                f"limite {name}: falta a reprodução em semgrep/test/limits/{name}/rule.yaml"
            )
    return found


def evidence_problems(
    pending: dict[str, Pending], vendor: Path, limits: dict[str, dict[str, object]]
) -> list[str]:
    """O aceite sem evidência: alarme falso sem a marca do CodeQL, acerto nosso sem a marca de
    vulnerável, limite que não existe."""
    found: list[str] = []
    for query, entry in sorted(pending.items()):
        found.extend(
            f"{query}: {case} não tem a marca de alarme falso do CodeQL"
            for case in sorted(entry.spurious)
            if not marked(SPURIOUS_MARK, case, vendor)
        )
        found.extend(
            f"{query}: {case} não tem a marca de vulnerável do CodeQL"
            for case in sorted(entry.accepted)
            if not marked(VULNERABLE_MARK, case, vendor)
        )
        found.extend(
            f"{query}: {case} aponta para o limite {name}, que não existe"
            for case, name in sorted(entry.limited.items())
            if name not in limits
        )
    return found


def marked(mark: re.Pattern[str], case: str, vendor: Path) -> bool:
    return any(mark.search(line) for line in case_lines(case, vendor))


def overfit_names(rules: Path, test_names: set[str]) -> dict[str, set[str]]:
    """Consulta → nomes dos padrões das regras dela que só o teste do CodeQL inventa."""
    found: dict[str, set[str]] = {}
    for path in sorted(rules.rglob("*.yaml")):
        document: object = yaml.safe_load(path.read_text(encoding="utf-8"))
        names = pattern_names(document) & test_names
        if names:
            for query in codeql_ids(path):
                found.setdefault(query, set()).update(names)
    return found


def read_test_names(path: Path) -> set[str]:
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}

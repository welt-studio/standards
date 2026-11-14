"""As pendências da paridade com o CodeQL (`hooks/semgrep_pending.py`): `uv run pytest` na raiz.

Além dos casos de unidade, confere os arquivos reais sem rodar o Semgrep: a evidência de cada aceite
(`spurious`, `accepted`, `limited`), os limites bem formados, os nomes presos ao teste batendo com
o `overfit` e o `pending.json` no formato estável.
"""

import json
from pathlib import Path

import semgrep_pending
from gitrepo import write
from semgrep_pending import Pending


def test_load_pending_reads_every_category() -> None:
    text = json.dumps(
        {
            "q": {
                "missing": ["a:1", 2],
                "spurious": ["b:1"],
                "limited": {"c:1": "lim", "d:1": 3},
                "threat_model": {"g:1": "local"},
                "extra": ["e:1"],
                "accepted": ["f:1"],
                "overfit": ["promisifiedExec"],
            },
            "r": [],
        }
    )
    assert semgrep_pending.load_pending(text) == {
        "q": Pending(
            missing=frozenset({"a:1"}),
            spurious=frozenset({"b:1"}),
            limited={"c:1": "lim"},
            threat_model={"g:1": "local"},
            extra=frozenset({"e:1"}),
            accepted=frozenset({"f:1"}),
            overfit=frozenset({"promisifiedExec"}),
        )
    }
    assert semgrep_pending.load_pending("[]") == {}


def test_classify_keeps_the_known_category() -> None:
    previous = Pending(
        spurious=frozenset({"s:1"}),
        limited={"l:1": "lim", "gone:1": "lim"},
        threat_model={"t:1": "local", "gone:2": "local"},
        accepted=frozenset({"a:1"}),
    )
    assert semgrep_pending.classify(
        {"s:1", "l:1", "t:1", "new:1"}, {"a:1", "x:1"}, {"n"}, previous
    ) == Pending(
        missing=frozenset({"new:1"}),
        spurious=frozenset({"s:1"}),
        limited={"l:1": "lim"},
        threat_model={"t:1": "local"},
        extra=frozenset({"x:1"}),
        accepted=frozenset({"a:1"}),
        overfit=frozenset({"n"}),
    )


def test_render_in_prettier_layout() -> None:
    long_item = "javascript/query-tests/Security/CWE-079/" + "x" * 60 + ".js:1"
    pending = {
        "q": Pending(missing=frozenset({"a.js:1"}), limited={"b.js:2": "lim"}),
        "r": Pending(extra=frozenset({long_item, "c.js:3"})),
        "empty": Pending(),
    }
    assert semgrep_pending.render(pending) == (
        "{\n"
        '  "q": {\n'
        '    "missing": ["a.js:1"],\n'
        '    "limited": {\n'
        '      "b.js:2": "lim"\n'
        "    }\n"
        "  },\n"
        '  "r": {\n'
        '    "extra": [\n'
        '      "c.js:3",\n'
        f'      "{long_item}"\n'
        "    ]\n"
        "  }\n"
        "}\n"
    )


def test_evidence_needs_the_codeql_mark(tmp_path: Path) -> None:
    write(
        tmp_path / "js/T/a.js",
        "x(); // $ SPURIOUS: Alert\ny();\n// NOT OK\nz();\nw(); // OK\nv();\n",
    )
    pending = {
        "q": Pending(
            spurious=frozenset({"js/T/a.js:1", "js/T/a.js:2", "js/T/a.js:5", "js/T/a.js:4"}),
            accepted=frozenset({"js/T/a.js:4", "js/T/a.js:6", "js/T/missing.js:1", "js/T/a.js:x"}),
            limited={"js/T/a.js:2": "real", "js/T/a.js:3": "ghost"},
        )
    }
    assert semgrep_pending.evidence_problems(pending, tmp_path, {"real": {}}) == [
        "q: js/T/a.js:4 não tem a marca de alarme falso do CodeQL",
        "q: js/T/a.js:6 não tem a marca de vulnerável do CodeQL",
        "q: js/T/a.js:x não tem a marca de vulnerável do CodeQL",
        "q: js/T/missing.js:1 não tem a marca de vulnerável do CodeQL",
        "q: js/T/a.js:3 aponta para o limite ghost, que não existe",
    ]


def test_threat_model_needs_the_test_config(tmp_path: Path) -> None:
    write(tmp_path / "js/On/a.js", "x();\n")
    write(tmp_path / "js/On/inner/b.js", "x();\n")
    write(
        tmp_path / "js/On/Q.ext.json",
        '{"extensions": [{"addsTo": {"extensible": "threatModelConfiguration"},'
        ' "data": [["local", true, 0], ["response", false, 0]]}, {"addsTo": {"extensible": "x"},'
        ' "data": [["environment", true, 0]]}, "junk"]}',
    )
    write(
        tmp_path / "py/Yml/Q.ext.yml",
        "extensions:\n  - addsTo: {extensible: threatModelConfiguration}\n"
        "    data:\n      - [remote, true, 0]\n      - [environment, true, 0]\n",
    )
    write(tmp_path / "py/Yml/t.py", "x()\n")
    write(tmp_path / "js/Off/c.js", "x();\n")
    pending = {
        "q": Pending(
            threat_model={
                "js/On/a.js:1": "local",
                "js/On/inner/b.js:1": "local",
                "js/On/a.js:2": "response",
                "js/On/a.js:3": "environment",
                "js/Off/c.js:1": "local",
                "py/Yml/t.py:1": "environment",
                "py/Yml/t.py:2": "remote",
            }
        )
    }
    message = "que a pasta do teste não liga"
    assert semgrep_pending.evidence_problems(pending, tmp_path, {}) == [
        f"q: js/Off/c.js:1 aponta para o modelo de ameaça local, {message}",
        f"q: js/On/a.js:2 aponta para o modelo de ameaça response, {message}",
        f"q: js/On/a.js:3 aponta para o modelo de ameaça environment, {message}",
        f"q: py/Yml/t.py:2 aponta para o modelo de ameaça remote, {message}",
    ]
    assert semgrep_pending.threat_models(["not", "a", "mapping"]) == set()


def test_limit_needs_capability_tries_lines_and_repro(tmp_path: Path) -> None:
    write(tmp_path / "ok/rule.yaml", "rules: []\n")
    limits: dict[str, dict[str, object]] = {
        "ok": {"capability": "x", "tried": ["y"], "should_find": ["a.js:1"]},
        "bad": {"capability": "", "tried": [], "should_find": "a.js:1"},
    }
    assert semgrep_pending.limit_problems(limits, tmp_path) == [
        "limite bad: falta `capability`",
        "limite bad: falta `tried`",
        "limite bad: falta `should_find`",
        "limite bad: falta a reprodução em semgrep/test/limits/bad/rule.yaml",
    ]
    assert semgrep_pending.load_limits('{"a": {"x": 1}, "b": 2}') == {"a": {"x": 1}}
    assert semgrep_pending.load_limits("[]") == {}


def test_overfit_names_by_query(tmp_path: Path) -> None:
    write(
        tmp_path / "javascript/cmd.yaml",
        "rules:\n  - id: r\n    metadata: {codeql: js/cmd}\n"
        "    pattern-sinks:\n      - pattern: promisifiedExec($X)\n      - pattern: exec($X)\n",
    )
    write(tmp_path / "javascript/clean.yaml", "rules:\n  - id: c\n    pattern: exec($X)\n")
    test_names = {"promisifiedExec", "unused"}
    assert semgrep_pending.overfit_names(tmp_path, test_names) == {"js/cmd": {"promisifiedExec"}}


def test_read_test_names(tmp_path: Path) -> None:
    write(tmp_path / "names.txt", "a\n\n b \n")
    assert semgrep_pending.read_test_names(tmp_path / "names.txt") == {"a", "b"}


def _real_pending() -> dict[str, Pending]:
    return semgrep_pending.load_pending(semgrep_pending.PENDING.read_text(encoding="utf-8"))


def _real_limits() -> dict[str, dict[str, object]]:
    return semgrep_pending.load_limits(semgrep_pending.LIMITS.read_text(encoding="utf-8"))


def test_every_accepted_case_has_evidence() -> None:
    problems = semgrep_pending.evidence_problems(
        _real_pending(), semgrep_pending.VENDOR, _real_limits()
    )
    assert problems == []


def test_every_limit_is_proven() -> None:
    assert semgrep_pending.limit_problems(_real_limits(), semgrep_pending.LIMITS_DIR) == []


def test_overfit_list_matches_the_rules() -> None:
    """Nome preso ao teste novo reprova; o que saiu da regra tem de sair da lista."""
    found = semgrep_pending.overfit_names(
        semgrep_pending.RULES, semgrep_pending.read_test_names(semgrep_pending.TEST_NAMES)
    )
    listed = {
        query: set(entry.overfit) for query, entry in _real_pending().items() if entry.overfit
    }
    assert listed == found


def test_pending_file_is_in_the_stable_layout() -> None:
    text = semgrep_pending.PENDING.read_text(encoding="utf-8")
    assert semgrep_pending.render(semgrep_pending.load_pending(text)) == text

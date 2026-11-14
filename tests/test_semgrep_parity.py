"""Paridade das regras do Semgrep com o CodeQL (`hooks/semgrep_parity.py`).

Os testes de unidade rodam no `uv run pytest` de sempre. Os de paridade (marca `semgrep`) rodam o
motor Pro sobre cada pasta de teste do CodeQL e reprovam o que fugir do `semgrep/test/pending.json`:
`uv run pytest -m semgrep --no-cov -n 3`, com o login do Semgrep.
"""

import json
from pathlib import Path

import pytest

import semgrep_parity
from semgrep_parity import Finding, Pending

PATH_PROBLEM = """#select
| a.js:3:5:3:9 | x | y | z |
| b.js:10:1:10:2 | x | y | z |
edges
| a.js:1:1:1:2 | a.js:3:5:3:9 |
nodes
| a.js:1:1:1:2 | semmle.label | x |
"""


def test_expected_stops_at_the_end_of_select() -> None:
    assert semgrep_parity.expected_alerts(PATH_PROBLEM) == {("a.js", 3), ("b.js", 10)}


def test_expected_after_edges_section() -> None:
    text = "edges\n| a.js:1:1:1:2 | a.js:3:1:3:2 |\n#select\n| a.js:3:1:3:2 | m |\n"
    assert semgrep_parity.expected_alerts(text) == {("a.js", 3)}


def test_expected_without_select() -> None:
    assert semgrep_parity.expected_alerts("| t.py:7:1:7:4 | m |\n") == {("t.py", 7)}
    assert semgrep_parity.expected_alerts("edges\n| t.py:1:1:1:2 | t.py:2:1:2:2 |\n") == set()


def test_expected_skips_rows_without_location() -> None:
    assert semgrep_parity.expected_alerts("#select\n| not a location | m |\n") == set()


def test_parse_findings_by_codeql_metadata() -> None:
    output = json.dumps(
        {
            "results": [
                {
                    "path": "./a.js",
                    "start": {"line": 3},
                    "end": {"line": 4},
                    "extra": {"metadata": {"codeql": "js/xss"}},
                },
                {"path": "b.js", "start": {"line": 1}, "end": {"line": 1}, "extra": {}},
                "not a result",
            ]
        }
    )
    assert semgrep_parity.parse_findings(output) == [Finding("js/xss", "a.js", 3, 4)]


def test_compare_with_one_line_of_tolerance() -> None:
    expected = {("a.js", 3), ("a.js", 20)}
    findings = [Finding("q", "a.js", 4, 4), Finding("q", "a.js", 9, 9)]
    missing, extra = semgrep_parity.compare("js/T", expected, findings)
    assert missing == {"js/T/a.js:20"}
    assert extra == {"js/T/a.js:9"}


def test_problems_follow_the_pending_list() -> None:
    result = {"q": ({"js/T/a.js:1", "js/T/a.js:2"}, {"js/T/a.js:9"})}
    pending = {"q": Pending(frozenset({"js/T/a.js:1", "js/T/a.js:5"}), frozenset({"js/T/a.js:7"}))}
    assert semgrep_parity.problems("js/T", result, pending) == [
        "q: deixou de pegar js/T/a.js:2",
        "q: acusa a mais js/T/a.js:9",
        "q: js/T/a.js:5 já é pego; tire do `missing` do pending.json",
        "q: js/T/a.js:7 não é mais acusado; tire do `extra` do pending.json",
    ]


def test_problems_ignore_pending_of_other_folders() -> None:
    pending = {"q": Pending(frozenset({"js/Other/a.js:1"}), frozenset())}
    assert semgrep_parity.problems("js/T", {"q": (set(), set())}, pending) == []


def test_manifest_and_pending_loading() -> None:
    manifest = '{"js/T": {"js/xss": "Xss.expected", "bad": 1}, "x": []}'
    assert semgrep_parity.load_manifest(manifest) == {"js/T": {"js/xss": "Xss.expected"}}
    pending = '{"q": {"missing": ["a", 1], "extra": "no"}, "r": []}'
    assert semgrep_parity.load_pending(pending) == {"q": Pending(frozenset({"a"}), frozenset())}


def test_pending_document_merges_folders_in_order() -> None:
    results = {
        "js/B": {"q": ({"js/B/b.js:1"}, set()), "r": (set(), set())},
        "js/A": {"q": (set(), {"js/A/a.js:2"})},
    }
    assert json.loads(semgrep_parity.pending_document(results)) == {
        "q": {"missing": ["js/B/b.js:1"], "extra": ["js/A/a.js:2"]}
    }


def test_folder_result_reads_the_expected_of_each_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "js/T").mkdir(parents=True)
    (tmp_path / "js/T/Xss.expected").write_text("| a.js:3:1:3:2 | m |\n", encoding="utf-8")
    monkeypatch.setattr(semgrep_parity, "VENDOR", tmp_path)
    queries = {"js/xss": "Xss.expected", "js/none": "Missing.expected"}
    findings = [Finding("js/xss", "a.js", 3, 3), Finding("js/none", "a.js", 8, 8)]
    assert semgrep_parity.folder_result("js/T", queries, findings) == {
        "js/xss": (set(), set()),
        "js/none": (set(), {"js/T/a.js:8"}),
    }


def test_scan_folder_without_rules_runs_nothing() -> None:
    assert semgrep_parity.scan_folder("js/T", {"js/xss": "Xss.expected"}, {}) == []


def test_main_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert semgrep_parity.main([]) == 2
    assert "uso:" in capsys.readouterr().err


def _folders() -> list[str]:
    if not semgrep_parity.MANIFEST.exists():
        return []
    return sorted(semgrep_parity.load_manifest(semgrep_parity.MANIFEST.read_text(encoding="utf-8")))


@pytest.mark.semgrep
@pytest.mark.timeout(900)
@pytest.mark.parametrize("folder", _folders())
def test_parity_with_codeql(folder: str) -> None:
    manifest = semgrep_parity.load_manifest(semgrep_parity.MANIFEST.read_text(encoding="utf-8"))
    pending = semgrep_parity.load_pending(semgrep_parity.PENDING.read_text(encoding="utf-8"))
    queries = manifest[folder]
    findings = semgrep_parity.scan_folder(folder, queries, semgrep_parity.rule_files())
    result = semgrep_parity.folder_result(folder, queries, findings)
    assert semgrep_parity.problems(folder, result, pending) == []


def test_pending_is_written_in_prettier_layout() -> None:
    long_item = "javascript/query-tests/Security/CWE-079/" + "x" * 60 + ".js:1"
    document = {"q": {"missing": ["a.js:1"], "extra": [long_item, "b.js:2"]}, "r": {"missing": []}}
    assert semgrep_parity.prettier_json(document) == (
        "{\n"
        '  "q": {\n'
        '    "missing": ["a.js:1"],\n'
        '    "extra": [\n'
        f'      "{long_item}",\n'
        '      "b.js:2"\n'
        "    ]\n"
        "  },\n"
        '  "r": {\n'
        '    "missing": []\n'
        "  }\n"
        "}\n"
    )

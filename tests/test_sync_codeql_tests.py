"""Testes da cópia dos testes do CodeQL (`hooks/sync_codeql_tests.py`): `uv run pytest` na raiz."""

import json
from pathlib import Path

import pytest

import sync_codeql_tests
from gitrepo import git, write

QUERY = """/**
 * @name Exemplo
 * @id py/example
 */
select 1
"""


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    """Um CodeQL de mentira: uma consulta portada, uma que não é, e as pastas de teste delas."""
    root = tmp_path / "codeql"
    write(root / "LICENSE", "MIT License\n")
    write(root / "python/ql/src/Security/Example.ql", QUERY)
    write(root / "python/ql/src/Security/Other.ql", QUERY.replace("py/example", "py/other"))
    write(root / "python/ql/test/Example/Example.qlref", "Security/Example.ql\n")
    write(root / "python/ql/test/Example/Example.expected", "| test.py:3:1:3:5 | x |\n")
    write(root / "python/ql/test/Example/test.py", "a = 1\n")
    write(root / "python/ql/test/Example/inner/Example.qlref", "query: Security/Example.ql\n")
    write(root / "python/ql/test/Other/Other.qlref", "Security/Other.ql\n")
    git(root, "init", "--quiet")
    git(root, "add", ".")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "--quiet", "-m", "c")
    return root


def test_declared_ids_reads_codeql_metadata(tmp_path: Path) -> None:
    write(
        tmp_path / "python/a.yaml",
        "rules:\n  - id: a\n    metadata: {codeql: py/example}\n  - id: b\n    metadata: {}\n",
    )
    write(tmp_path / "javascript/b.yaml", "rules: []\n")
    write(tmp_path / "broken.yaml", "- not a mapping\n")
    assert sync_codeql_tests.declared_ids(tmp_path) == {"py/example"}


def test_referenced_query_needs_the_full_path() -> None:
    paths = {"Security/Example.ql": "py/example"}
    assert sync_codeql_tests.referenced_query("Security/Example.ql\n", paths) == "py/example"
    assert sync_codeql_tests.referenced_query("query: Security/Example.ql", paths) == "py/example"
    assert sync_codeql_tests.referenced_query("Example.ql", paths) is None


def test_sync_copies_only_ported_folders(clone: Path, tmp_path: Path) -> None:
    vendor = tmp_path / "vendor"
    write(vendor / "SOURCE", "x\n")
    write(vendor / "stale/old.py", "")
    manifest = sync_codeql_tests.sync(clone, vendor, {"py/example"})
    assert manifest == {
        "python/Example": {"py/example": "Example.expected"},
        "python/Example/inner": {"py/example": "Example.expected"},
    }
    assert (vendor / "python/Example/test.py").exists()
    assert not (vendor / "python/Other").exists()
    assert not (vendor / "stale").exists()
    assert (vendor / "SOURCE").exists()
    assert (vendor / "LICENSE").read_text(encoding="utf-8") == "MIT License\n"


def test_main_refuses_another_commit(
    clone: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    vendor = tmp_path / "vendor"
    write(vendor / "SOURCE", "0" * 40 + "\n")
    monkeypatch.setattr(sync_codeql_tests, "SOURCE", vendor / "SOURCE")
    assert sync_codeql_tests.main([str(clone)]) == 1
    assert "pede" in capsys.readouterr().err


def test_main_writes_manifest_and_warns(
    clone: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    vendor = tmp_path / "vendor"
    queries = tmp_path / "queries"
    write(
        queries / "a.yaml",
        "rules:\n  - id: a\n    metadata: {codeql: py/example}\n"
        "  - id: b\n    metadata: {codeql: py/untested}\n",
    )
    commit = sync_codeql_tests.clone_commit(clone)
    assert commit is not None
    write(vendor / "SOURCE", f"{commit}\n")
    monkeypatch.setattr(sync_codeql_tests, "SOURCE", vendor / "SOURCE")
    monkeypatch.setattr(sync_codeql_tests, "VENDOR", vendor)
    monkeypatch.setattr(sync_codeql_tests, "MANIFEST", vendor / "queries.json")
    monkeypatch.setattr(sync_codeql_tests, "TEST_NAMES", vendor / "test-names.txt")
    monkeypatch.setattr(sync_codeql_tests, "QUERIES", queries)
    assert sync_codeql_tests.main([str(clone)]) == 0
    manifest = json.loads((vendor / "queries.json").read_text(encoding="utf-8"))
    assert list(manifest) == ["python/Example", "python/Example/inner"]
    output = capsys.readouterr()
    assert "py/untested não tem pasta de teste" in output.err
    assert "2 pastas de teste, 1/2 consultas" in output.out
    # `a` é declarado no teste (`a = 1`) e nenhum modelo do clone de mentira o cita.
    assert (vendor / "test-names.txt").read_text(encoding="utf-8") == "a\n"


def test_main_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert sync_codeql_tests.main([]) == 2
    assert "uso:" in capsys.readouterr().err


def test_clone_commit_outside_a_repo(tmp_path: Path) -> None:
    assert sync_codeql_tests.clone_commit(tmp_path) is None

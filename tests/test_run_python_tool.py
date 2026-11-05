"""Testes dos hooks `ruff`, `ruff-format` e `pyright` (`hooks/run_python_tool.py`): `uv run pytest`
na raiz deste repo. O `uv` não roda: o `subprocess.run` do script é trocado por um que só anota.
"""

import re
import subprocess
from pathlib import Path

import pytest

import run_python_tool
import sync_base
from gitrepo import write

PYRIGHT_CONFIG = '{ "extends": "./pyright-base.json", "include": ["backend"] }\n'


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Um monorepo com o pacote Python em `backend/` e o `pyrightconfig.json` na raiz."""
    write(tmp_path / "backend" / "ruff.toml", 'extend = "../ruff-base.toml"\n')
    write(tmp_path / "pyrightconfig.json", PYRIGHT_CONFIG)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def command(mode: str, files: list[str], package: str = "backend") -> list[str] | None:
    return run_python_tool.command(mode, Path(package), files)


RUFF_CHECK = ["run", "--directory", "backend", "ruff", "check", "--fix"]
PYRIGHT = ["run", "--project", "backend", "pyright"]


@pytest.mark.usefixtures("project")
def test_ruff_checks_the_commit_sources_from_inside_the_package() -> None:
    files = ["backend/app/main.py", "backend/app/types.pyi", "frontend/x.ts", "scripts/tool.py"]
    assert command("ruff", files) == [*RUFF_CHECK, "app/main.py", "app/types.pyi"]


@pytest.mark.usefixtures("project")
def test_ruff_format_uses_the_format_subcommand() -> None:
    assert command("ruff-format", ["backend/app/main.py"]) == [
        "run",
        "--directory",
        "backend",
        "ruff",
        "format",
        "app/main.py",
    ]


@pytest.mark.usefixtures("project")
@pytest.mark.parametrize(
    "trigger",
    [
        "ruff-base.toml",
        "backend/ruff.toml",
        "backend/tests/.ruff.toml",
        "backend/uv.lock",
        "uv.lock",
    ],
)
def test_ruff_trigger_in_the_commit_checks_the_whole_package(trigger: str) -> None:
    assert command("ruff", [trigger, "backend/app/main.py"]) == [*RUFF_CHECK, "."]


def test_pyproject_triggers_ruff_only_with_ruff_table(project: Path) -> None:
    write(project / "backend" / "pyproject.toml", '[project]\nname = "app"\n')
    files = ["backend/pyproject.toml", "backend/app.py"]
    assert command("ruff", files) == [*RUFF_CHECK, "app.py"]
    write(project / "backend" / "pyproject.toml", "[tool.ruff]\n")
    assert command("ruff", files) == [*RUFF_CHECK, "."]


@pytest.mark.usefixtures("project")
@pytest.mark.parametrize("pyproject", ["backend/pyproject.toml", "backend/bad/pyproject.toml"])
def test_deleted_or_invalid_pyproject_triggers_ruff(project: Path, pyproject: str) -> None:
    if "bad" in pyproject:
        write(project / pyproject, "[tool.ruff\n")
    assert command("ruff", [pyproject]) == [*RUFF_CHECK, "."]


@pytest.mark.usefixtures("project")
@pytest.mark.parametrize("other", ["frontend/ruff.toml", "frontend/pyproject.toml", "web/uv.lock"])
def test_config_of_another_folder_does_not_trigger_ruff(project: Path, other: str) -> None:
    write(project / other, "[tool.ruff]\n")
    assert command("ruff", [other]) == []


@pytest.mark.usefixtures("project")
def test_no_files_checks_the_whole_package() -> None:
    assert command("ruff", []) == [*RUFF_CHECK, "."]
    assert command("pyright", []) == PYRIGHT


@pytest.mark.usefixtures("project")
def test_nothing_of_the_tool_in_the_commit_runs_nothing() -> None:
    assert command("ruff", ["scripts/tool.py"]) == []
    assert command("pyright", ["scripts/tool.py"]) == []


@pytest.mark.usefixtures("project")
def test_package_at_the_root() -> None:
    assert command("ruff", ["tool.py", "a/b.py"], package=".") == [
        "run",
        "--directory",
        ".",
        "ruff",
        "check",
        "--fix",
        "tool.py",
        "a/b.py",
    ]


@pytest.mark.usefixtures("project")
def test_pyright_checks_the_commit_files_it_analyzes() -> None:
    files = ["backend/app.py", "backend/stubs.pyi", "scripts/tool.py", "backend/nb.ipynb"]
    assert command("pyright", files) == [*PYRIGHT, "backend/app.py", "backend/stubs.pyi"]


@pytest.mark.usefixtures("project")
@pytest.mark.parametrize("trigger", ["pyrightconfig.json", "pyright-base.json", "uv.lock"])
def test_pyright_trigger_in_the_commit_checks_the_whole_project(trigger: str) -> None:
    assert command("pyright", [trigger, "backend/app.py"]) == PYRIGHT


def test_pyright_config_in_the_package(project: Path) -> None:
    """Sem `pyrightconfig.json` na raiz, vale o do pacote (o `pyright-base` com `args`), e o
    `include` dele é relativo a ele."""
    (project / "pyrightconfig.json").unlink()
    write(project / "backend" / "pyrightconfig.json", '{ "include": ["app"] }\n')
    files = ["backend/app/main.py", "backend/scripts/tool.py"]
    assert command("pyright", files) == [*PYRIGHT, "--project", "backend", "backend/app/main.py"]
    assert command("pyright", []) == [*PYRIGHT, "--project", "backend"]


def test_pyright_without_config_fails(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / "pyrightconfig.json").unlink()
    assert command("pyright", ["backend/app.py"]) is None
    err = capsys.readouterr().err
    assert err.startswith("pyright: backend/pyrightconfig.json não existe")


class Recorder:
    """O `subprocess.run` do script: anota o comando e devolve o código pedido."""

    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        assert not check
        self.calls.append(args)
        return subprocess.CompletedProcess(args, self.returncode)


@pytest.fixture
def recorder(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    recorded = Recorder(returncode=1)
    monkeypatch.setattr(run_python_tool.subprocess, "run", recorded)
    monkeypatch.setattr(run_python_tool.shutil, "which", lambda _name: "/bin/uv")
    return recorded


@pytest.mark.usefixtures("project")
def test_main_runs_uv_and_returns_its_code(recorder: Recorder) -> None:
    assert run_python_tool.main(["pyright", "backend", "backend/app.py"]) == 1
    assert recorder.calls == [["/bin/uv", *PYRIGHT, "backend/app.py"]]


@pytest.mark.usefixtures("project")
def test_main_without_anything_to_check_does_not_run_uv(recorder: Recorder) -> None:
    assert run_python_tool.main(["ruff", "backend", "scripts/tool.py"]) == 0
    assert recorder.calls == []


@pytest.mark.usefixtures("project")
def test_main_without_config_does_not_run_uv(recorder: Recorder) -> None:
    Path("pyrightconfig.json").unlink()
    assert run_python_tool.main(["pyright", "backend", "backend/app.py"]) == 1
    assert recorder.calls == []


@pytest.mark.usefixtures("project")
def test_main_without_uv_fails(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(run_python_tool.shutil, "which", lambda _name: None)
    assert run_python_tool.main(["ruff", "backend", "backend/app.py"]) == 1
    assert "uv não encontrado" in capsys.readouterr().err


@pytest.mark.usefixtures("project")
def test_main_with_missing_package_fails(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_python_tool.main(["ruff", "api", "api/app.py"]) == 1
    assert "a pasta api (args do hook) não existe" in capsys.readouterr().err


@pytest.mark.parametrize("args", [[], ["ruff"], ["mypy", "backend"]])
def test_main_usage(args: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    assert run_python_tool.main(args) == 2
    assert "uso: run_python_tool.py" in capsys.readouterr().err


def hooks_in(name: str) -> dict[str, dict[str, str]]:
    """Os hooks de um YAML do pre-commit deste repo, com as chaves de valor simples (sem YAML na
    stdlib: cada item de lista vira um bloco, e o de `id` é um hook; vale o primeiro de cada id)."""
    text = (sync_base.ROOT / name).read_text(encoding="utf-8")
    hooks: dict[str, dict[str, str]] = {}
    for block in re.split(r"^\s*- ", text, flags=re.MULTILINE)[1:]:
        fields = dict(re.findall(r"^\s*(\w+): (.*)$", f"  {block}", flags=re.MULTILINE))
        if "id" in fields:
            hooks.setdefault(fields["id"], fields)
    return hooks


def manifest_hooks() -> dict[str, dict[str, str]]:
    return hooks_in(".pre-commit-hooks.yaml")


@pytest.mark.parametrize("mode", run_python_tool.MODES)
def test_own_config_runs_the_published_hook(mode: str) -> None:
    """O `.pre-commit-config.yaml` deste repo roda o script do working tree com o mesmo `entry` e o
    mesmo `files` do hook publicado."""
    published = manifest_hooks()[mode]
    local = hooks_in(".pre-commit-config.yaml")[mode]
    assert {key: local.get(key) for key in ("entry", "files")} == {
        key: published[key] for key in ("entry", "files")
    }


@pytest.mark.parametrize("mode", run_python_tool.MODES)
def test_manifest_hook_runs_its_mode(mode: str) -> None:
    hook = manifest_hooks()[mode]
    assert hook["entry"] == f"hooks/run_python_tool.py {mode}"
    assert hook["language"] == "script"


@pytest.mark.parametrize("mode", run_python_tool.MODES)
def test_manifest_files_trigger_on_every_config_and_source(mode: str) -> None:
    files = re.compile(manifest_hooks()[mode]["files"])
    triggers = [*run_python_tool.CONFIGS[mode], run_python_tool.LOCK]
    configs = [*triggers, *(f"api/{name}" for name in triggers)]
    sources = [f"api/app{pattern.removeprefix('*')}" for pattern in run_python_tool.SOURCES[mode]]
    assert [path for path in [*configs, *sources] if not files.search(path)] == []
    assert [path for path in ("README.md", "api/x.ts", "api/py.json") if files.search(path)] == []

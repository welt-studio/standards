"""Testes do hook `pytest-base` (`hooks/check_pytest.py`): `uv run pytest` na raiz deste repo."""

import copy
from pathlib import Path
from typing import Any

import pytest

import check_pytest

# `Any`: é o TOML lido, que o hook confere sem confiar no tipo; os testes o editam por chave.
COMPLETE: dict[str, Any] = {
    "dependency-groups": {
        "dev": [
            "pytest==9.1.1",
            "pytest-cov==7.1.0",
            "pytest_xdist>=3.8",
            "pytest-randomly==5.0.0",
            "pytest-timeout==2.5.0",
            "pytest-socket==0.8.1",
            "time-machine==3.5.1",
        ]
    },
    "tool": {
        "pytest": {
            "ini_options": {
                "strict": True,
                "filterwarnings": [
                    "error",
                    "default",
                    "error::pytest.PytestWarning",
                    "error::ResourceWarning",
                    r"error:::(.+\.)?(test_\w*|conftest)$",
                    r"error:::app(\.|$)",
                ],
                "python_files": ["test_*.py"],
                "addopts": "-n 4 --cov --disable-socket --allow-hosts=127.0.0.1,localhost",
                "timeout": check_pytest.TIMEOUT_SECONDS,
            }
        },
        "coverage": {
            "run": {"branch": True, "source": ["app"]},
            "report": {"fail_under": check_pytest.COVERAGE_FLOOR},
        },
    },
}


COMPLETE_WARNINGS: list[str] = COMPLETE["tool"]["pytest"]["ini_options"]["filterwarnings"]
# O que vem depois do `"error"`, e o mesmo sem a linha do pacote (a última).
BOUNDARY = COMPLETE_WARNINGS[1:]
WITHOUT_PACKAGE = COMPLETE_WARNINGS[:-1]


def without(path: tuple[str, ...]) -> dict[str, Any]:
    config = copy.deepcopy(COMPLETE)
    node = config
    for key in path[:-1]:
        node = node[key]
    del node[path[-1]]
    return config


def test_complete_config_passes() -> None:
    assert check_pytest.problems(COMPLETE) == []


def test_addopts_as_list_passes() -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["pytest"]["ini_options"]["addopts"] = [
        "--cov=app",
        "--disable-socket",
        "--allow-hosts=::1",
    ]
    assert check_pytest.problems(config) == []


@pytest.mark.parametrize("addopts", ["--disable-socket --allow-hosts=::1", "--cov-report=term"])
def test_coverage_flag_is_required(addopts: str) -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["pytest"]["ini_options"]["addopts"] = addopts
    found = check_pytest.problems(config)
    assert "[tool.pytest.ini_options] addopts com --cov (o fail_under só vale com ele)" in found


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (("tool", "pytest", "ini_options", "strict"), "strict = true"),
        (("tool", "pytest", "ini_options", "filterwarnings"), "filterwarnings"),
        (("tool", "pytest", "ini_options", "python_files"), "python_files"),
        (("tool", "pytest", "ini_options", "timeout"), "timeout = 60"),
        (("tool", "coverage", "run", "branch"), "branch = true"),
        (("tool", "coverage", "run", "source"), "source"),
        (("tool", "coverage", "report", "fail_under"), "fail_under = 80"),
    ],
)
def test_each_missing_option_is_reported(path: tuple[str, ...], expected: str) -> None:
    found = check_pytest.problems(without(path))
    assert len(found) == 1
    assert expected in found[0]


def test_warnings_not_starting_with_error_fail() -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["pytest"]["ini_options"]["filterwarnings"] = ["ignore", "error"]
    assert check_pytest.problems(config) == [
        '[tool.pytest.ini_options] filterwarnings começando por "error"'
    ]


def test_error_alone_passes() -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["pytest"]["ini_options"]["filterwarnings"] = ["error"]
    assert check_pytest.problems(config) == []


def test_boundary_order_after_default_is_free() -> None:
    config = copy.deepcopy(COMPLETE)
    options = config["tool"]["pytest"]["ini_options"]
    options["filterwarnings"] = options["filterwarnings"][:2] + options["filterwarnings"][:1:-1]
    assert check_pytest.problems(config) == []


@pytest.mark.parametrize(
    ("sources", "packages"),
    [(["app/core", "tools"], [r"app\.core", "tools"]), (["app.core"], [r"app\.core"])],
)
def test_boundary_has_one_filter_per_source(sources: list[str], packages: list[str]) -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["coverage"]["run"]["source"] = sources
    config["tool"]["pytest"]["ini_options"]["filterwarnings"] = [
        *WITHOUT_PACKAGE,
        *(rf"error:::{package}(\.|$)" for package in packages),
    ]
    assert check_pytest.problems(config) == []


@pytest.mark.parametrize(
    "boundary",
    [
        ["ignore"],
        ["ignore::DeprecationWarning:thirdparty"],
        ["default"],
        # Fronteira incompleta: cada linha que vem depois do `default` faltando.
        *([entry for entry in BOUNDARY if entry != missing] for missing in BOUNDARY[1:]),
        # Pacote que não é o do `source`, ou sem o fim (pegaria a lib `apprise`).
        [*WITHOUT_PACKAGE[1:], r"error:::zzz(\.|$)"],
        [*WITHOUT_PACKAGE[1:], "error:::app"],
        # Exceção a mais, ou o `default` fora do lugar.
        [*BOUNDARY, "ignore:some message"],
        [*BOUNDARY[1:], "default"],
        ["always", *BOUNDARY[1:]],
    ],
)
def test_warnings_exceptions_fail(boundary: list[str]) -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["pytest"]["ini_options"]["filterwarnings"] = ["error", *boundary]
    found = check_pytest.problems(config)
    assert len(found) == 1
    assert found[0].startswith(check_pytest.BOUNDARY_PROBLEM)


def test_boundary_needs_import_names_in_source() -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["coverage"]["run"]["source"] = ["."]
    found = check_pytest.problems(config)
    assert len(found) == 1
    assert found[0].startswith(check_pytest.PACKAGES_PROBLEM)


@pytest.mark.parametrize(
    "flags",
    [
        ["-W", "ignore::DeprecationWarning"],
        ["-Wignore"],
        ["--pythonwarnings=ignore"],
        ["-p", "no:warnings"],
        ["-pno:warnings"],
    ],
)
def test_command_line_warning_filters_fail(flags: list[str]) -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["pytest"]["ini_options"]["addopts"] = [
        "--cov",
        "--disable-socket",
        "--allow-hosts=::1",
        *flags,
    ]
    assert check_pytest.problems(config) == [check_pytest.WARNINGS_FLAGS_PROBLEM]


def test_network_flags_are_required() -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["pytest"]["ini_options"]["addopts"] = "-n 4 --cov"
    found = check_pytest.problems(config)
    assert len(found) == 2
    assert "--disable-socket" in found[0]
    assert "--allow-hosts" in found[1]


def test_other_floor_or_timeout_fails() -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["coverage"]["report"]["fail_under"] = 70
    config["tool"]["pytest"]["ini_options"]["timeout"] = 300
    assert len(check_pytest.problems(config)) == 2


def test_omit_fails() -> None:
    config = copy.deepcopy(COMPLETE)
    config["tool"]["coverage"]["run"]["omit"] = ["*/routes/*"]
    found = check_pytest.problems(config)
    assert len(found) == 1
    assert "sem omit" in found[0]


def test_missing_plugins_are_listed() -> None:
    config = copy.deepcopy(COMPLETE)
    config["dependency-groups"]["dev"] = ["pytest==9.1.1", "pytest-cov==7.1.0"]
    found = check_pytest.problems(config)
    missing = "pytest-xdist, pytest-randomly, pytest-timeout, pytest-socket, time-machine"
    assert found == [f"[dependency-groups] dev com: {missing}"]


def test_main_reads_the_package_folder(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    assert check_pytest.main([str(tmp_path)]) == 1
    assert "strict = true" in capsys.readouterr().err


def test_main_without_pyproject_fails(tmp_path: Path) -> None:
    assert check_pytest.main([str(tmp_path)]) == 1


def test_main_reports_invalid_toml(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.pytest\n", encoding="utf-8")
    assert check_pytest.main([str(tmp_path)]) == 1
    assert "não é TOML válido" in capsys.readouterr().err

"""Exceções do `ruff/base.toml` para padrão de lib: `uv run pytest` na raiz deste repo.

Cada caso roda o Ruff do `uv.lock` como num projeto (a cópia `ruff-base.toml` e um `ruff.toml` que a
estende) num arquivo só, e confere o lado que a exceção libera e o que continua reprovando.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def ruff_codes(project: Path, relative: str, source: str) -> set[str]:
    base = (ROOT / "ruff" / "base.toml").read_text(encoding="utf-8")
    (project / "ruff-base.toml").write_text(base, encoding="utf-8")
    (project / "ruff.toml").write_text('extend = "ruff-base.toml"\n', encoding="utf-8")
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")
    result = subprocess.run(  # noqa: S603 - o Ruff do venv, com argumentos do teste
        [sys.executable, "-m", "ruff", "check", "--no-cache", "--output-format", "json", relative],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )
    findings: object = json.loads(result.stdout)
    assert isinstance(findings, list), result.stderr
    codes: set[str] = set()
    for finding in findings:
        assert isinstance(finding, dict)
        code = finding.get("code")
        if isinstance(code, str):
            codes.add(code)
    return codes


BOTO3_STUB = """\
class FakeS3:
    def put_object(self, Bucket: str, Key: str, Body: bytes) -> None:
        self.saved = (Bucket, Key, Body)
"""

DJANGO_META = """\
from django.db.models import Model


def field_names(model: type[Model]) -> list[str]:
    return [field.name for field in model._meta.get_fields()]
"""

PRIVATE_MEMBER = """\
class Counter:
    _total = 0


def total(counter: Counter) -> int:
    return counter._total
"""


@pytest.mark.parametrize(
    ("relative", "source", "code", "reported"),
    [
        # Dublê de lib no teste recebe os argumentos com o nome dela; no código do projeto, não.
        ("tests/test_store.py", BOTO3_STUB, "N803", False),
        ("app/store.py", BOTO3_STUB, "N803", True),
        # `_meta` do Django é API pública; outro membro privado continua cobrado.
        ("app/seed.py", DJANGO_META, "SLF001", False),
        ("app/counter.py", PRIVATE_MEMBER, "SLF001", True),
    ],
)
def test_excecao_da_base(
    tmp_path: Path, relative: str, source: str, code: str, reported: bool
) -> None:
    assert (code in ruff_codes(tmp_path, relative, source)) is reported

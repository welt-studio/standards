"""Testes do gerador das regras do Semgrep (`hooks/generate_semgrep.py`): `uv run pytest`."""

from pathlib import Path

import pytest
import yaml

import generate_semgrep as gen


def rule(extra: str = "", codeql: str = "js/xss") -> str:
    """Uma consulta mínima com uma regra: `extra` entra dentro da regra, o resto é fixo."""
    return f"rules:\n  - id: r\n    metadata:\n      codeql: {codeql}\n{extra}"


def build(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def two_queries(models: dict[str, str]) -> dict[str, str]:
    """Duas consultas que usam, juntas, todos os modelos de `models` (para passar o "uso")."""
    uses = "".join(f"      - $model: {name.removesuffix('.yaml')}\n" for name in models)
    body = f"    patterns:\n{uses}"
    return {
        **{f"models/{name}": text for name, text in models.items()},
        "queries/javascript/xss.yaml": rule(body),
        "queries/javascript/xss-through-dom.yaml": rule(body, "js/xss-through-dom"),
    }


def loaded(text: str) -> object:
    return yaml.safe_load(text)


# --- expansão ---------------------------------------------------------------------------------


def generated_rule(root: Path, files: dict[str, str]) -> object:
    """A primeira regra gerada da consulta `javascript/xss`, sem o `id` e o `metadata`."""
    outputs, errors = gen.generate(build(root, files))
    assert errors == []
    parsed = loaded(outputs["javascript/xss.yaml"])
    assert isinstance(parsed, dict)
    first = parsed["rules"][0]
    assert isinstance(first, dict)
    assert first.pop("id") == "r"
    assert first.pop("metadata") == {"codeql": "js/xss"}
    return first


def test_model_reference_expands_in_place(tmp_path: Path) -> None:
    files = two_queries({"a/sinks.yaml": "- pattern: eval($X)\n- pattern: exec($X)\n"})
    files["queries/javascript/xss.yaml"] = rule(
        "    patterns:\n      - pattern: first\n      - $model: a/sinks\n      - pattern: last\n"
    )
    assert generated_rule(tmp_path, files) == {
        "patterns": [
            {"pattern": "first"},
            {"pattern": "eval($X)"},
            {"pattern": "exec($X)"},
            {"pattern": "last"},
        ]
    }


def test_text_reference_becomes_the_string(tmp_path: Path) -> None:
    body = "    pattern-regex:\n      $text: common/names\n"
    files = {
        "models/common/names.yaml": '"^(pass|secret)$"\n',
        "queries/javascript/xss.yaml": rule(body),
        "queries/javascript/xss-through-dom.yaml": rule(body, "js/xss-through-dom"),
    }
    assert generated_rule(tmp_path, files) == {"pattern-regex": "^(pass|secret)$"}


def test_model_can_reference_another_model(tmp_path: Path) -> None:
    files = two_queries({"a/outer.yaml": "- $model: a/inner\n- pattern: b\n"})
    files["models/a/inner.yaml"] = "- pattern: a\n"
    assert generated_rule(tmp_path, files) == {"patterns": [{"pattern": "a"}, {"pattern": "b"}]}


# --- erros ------------------------------------------------------------------------------------


def errors_of(root: Path, files: dict[str, str]) -> str:
    _, errors = gen.generate(build(root, files))
    return "\n".join(errors)


def test_unknown_model_is_an_error(tmp_path: Path) -> None:
    files = {"queries/javascript/xss.yaml": rule("    patterns:\n      - $model: a/missing\n")}
    assert "`$model: a/missing` não existe em `models/`" in errors_of(tmp_path, files)


def test_unknown_text_is_an_error(tmp_path: Path) -> None:
    files = {"queries/javascript/xss.yaml": rule("    regex:\n      $text: a/missing\n")}
    assert "`$text: a/missing` não existe" in errors_of(tmp_path, files)


def test_model_reference_to_a_text_is_an_error(tmp_path: Path) -> None:
    files = two_queries({"a/names.yaml": "abc\n"})
    assert "aponta para um texto, não uma lista" in errors_of(tmp_path, files)


def test_text_reference_to_a_list_is_an_error(tmp_path: Path) -> None:
    files = {
        "models/a/list.yaml": "- pattern: a\n",
        "queries/javascript/xss.yaml": rule("    regex:\n      $text: a/list\n"),
        "queries/javascript/xss-through-dom.yaml": rule(
            "    regex:\n      $text: a/list\n", "js/xss-through-dom"
        ),
    }
    assert "aponta para uma lista, não um texto" in errors_of(tmp_path, files)


def test_cycle_between_models_is_an_error(tmp_path: Path) -> None:
    files = two_queries({"a/one.yaml": "- $model: a/two\n"})
    files["models/a/two.yaml"] = "- $model: a/one\n"
    assert "ciclo entre modelos: a/one -> a/two -> a/one" in errors_of(tmp_path, files)


def test_model_key_outside_a_list_is_an_error(tmp_path: Path) -> None:
    files = {"queries/javascript/xss.yaml": rule("    pattern-either:\n      $model: a/x\n")}
    assert "só vale como elemento de lista" in errors_of(tmp_path, files)


def test_model_key_with_siblings_is_an_error(tmp_path: Path) -> None:
    files = {
        "queries/javascript/xss.yaml": rule("    patterns:\n      - $model: a/x\n        id: 1\n")
    }
    assert "só vale como elemento de lista" in errors_of(tmp_path, files)


def test_unused_model_is_an_error(tmp_path: Path) -> None:
    files = two_queries({"a/used.yaml": "- pattern: a\n"})
    files["models/a/orphan.yaml"] = "- pattern: b\n"
    message = errors_of(tmp_path, files)
    assert "models/a/orphan.yaml: modelo sem uso" in message
    assert "used.yaml" not in message


def test_model_used_by_one_query_is_an_error(tmp_path: Path) -> None:
    files = {
        "models/a/single.yaml": "- pattern: a\n",
        "queries/javascript/xss.yaml": rule("    patterns:\n      - $model: a/single\n"),
        "queries/javascript/xss-through-dom.yaml": rule(
            "    patterns:\n      - pattern: other\n", "js/xss-through-dom"
        ),
    }
    assert "models/a/single.yaml: usado por uma consulta só" in errors_of(tmp_path, files)


def test_model_reached_by_two_queries_through_another_model_is_fine(tmp_path: Path) -> None:
    files = two_queries({"a/outer.yaml": "- $model: a/inner\n- pattern: b\n"})
    files["models/a/inner.yaml"] = "- pattern: a\n"
    assert errors_of(tmp_path, files) == ""


def test_item_repeated_in_two_files_must_be_a_model(tmp_path: Path) -> None:
    body = "    pattern-sinks:\n      - pattern: eval($X)\n"
    files = {
        "queries/javascript/xss.yaml": rule(body),
        "queries/javascript/xss-through-dom.yaml": rule(body, "js/xss-through-dom"),
    }
    message = errors_of(tmp_path, files)
    assert "repetido em queries/javascript/xss-through-dom.yaml" in message
    assert "e fora de um modelo" in message


def test_regex_repeated_in_two_files_must_be_a_model(tmp_path: Path) -> None:
    body = "    pattern-regex: abc+\n"
    files = {
        "queries/javascript/xss.yaml": rule(body),
        "queries/javascript/xss-through-dom.yaml": rule(body, "js/xss-through-dom"),
    }
    assert "repetido em" in errors_of(tmp_path, files)


def test_item_repeated_inside_one_file_is_fine(tmp_path: Path) -> None:
    body = "    pattern-sinks:\n      - pattern: a\n      - pattern: a\n"
    assert errors_of(tmp_path, {"queries/javascript/xss.yaml": rule(body)}) == ""


@pytest.mark.parametrize(
    ("name", "text", "expected"),
    [
        ("python/xss", rule(codeql="js/xss"), "`metadata.codeql` deve ser `py/xss`"),
        ("javascript/a__b", rule(codeql="js/a/c"), "deve ser `js/a/b`"),
        ("javascript/xss", "rules:\n  - id: r\n", "(veio None)"),
        ("javascript/xss", "other: 1\n", "falta a lista `rules`"),
        ("rust/xss", rule(), "pasta de linguagem desconhecida"),
    ],
)
def test_query_must_declare_its_codeql_id(
    tmp_path: Path, name: str, text: str, expected: str
) -> None:
    assert expected in errors_of(tmp_path, {f"queries/{name}.yaml": text})


def test_codeql_id_of_a_nested_query_name() -> None:
    assert gen.codeql_id("actions/cache-poisoning__direct-cache") == (
        "actions/cache-poisoning/direct-cache"
    )


def test_invalid_yaml_is_an_error(tmp_path: Path) -> None:
    assert "YAML inválido" in errors_of(tmp_path, {"models/a/x.yaml": "a: [\n"})


def test_non_text_key_is_an_error(tmp_path: Path) -> None:
    assert "chave que não é texto" in errors_of(tmp_path, {"models/a/x.yaml": "1: a\n"})


def test_value_without_plain_equivalent_is_an_error(tmp_path: Path) -> None:
    assert "valor sem equivalente" in errors_of(tmp_path, {"models/a/x.yaml": "a: 2024-01-01\n"})


# --- saída ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("abc", "abc"),
        ("a b-c.d/e", "a b-c.d/e"),
        ("true", '"true"'),
        ("$X", '"$X"'),
        ("a: b", '"a: b"'),
        ('say "hi" it\'s', "'say \"hi\" it''s'"),
        ('a\\b "c"', '"a\\\\b \\"c\\""'),
        ("accent: ação", '"accent: ação"'),
    ],
)
def test_scalar_follows_the_prettier_style(value: str, expected: str) -> None:
    assert gen.scalar(value) == expected


def test_render_uses_block_style_and_block_scalars() -> None:
    tree: gen.Node = {
        "rules": [
            {
                "id": "r",
                "languages": ["python"],
                "patterns": [{"pattern": "a\n  b\n"}, {"pattern": "a\nb"}],
                "empty": [],
                "none": {},
                "flag": True,
                "other": False,
                "nothing": None,
                "count": 3,
                "ratio": 0.5,
                "nested": [["x", "y"], {"k": "v"}],
            }
        ]
    }
    text = gen.render(tree)
    assert text.startswith(gen.HEADER)
    assert text.endswith("\n")
    assert loaded(text) == tree
    assert "    languages:\n      - python\n" in text
    assert "pattern: |\n" in text
    assert "pattern: |-\n" in text
    assert "- - x\n" in text


@pytest.mark.parametrize("value", ["a \nb", " a\nb", "\na", "a\n\n", "a\tb\x00\nc", "a\nb \n"])
def test_awkward_multiline_text_falls_back_to_quotes(value: str) -> None:
    text = gen.render({"k": value})
    assert loaded(text) == {"k": value}
    assert "|" not in text


def test_block_scalar_keeps_blank_lines() -> None:
    text = gen.render({"k": "a\n\nb\n"})
    assert "k: |\n  a\n\n  b\n" in text
    assert loaded(text) == {"k": "a\n\nb\n"}


# --- escrita e --check ------------------------------------------------------------------------


def valid_project(root: Path) -> Path:
    return build(root, two_queries({"a/sinks.yaml": "- pattern: eval($X)\n"}))


def test_run_writes_the_rules_and_check_passes_after(tmp_path: Path) -> None:
    root = valid_project(tmp_path)
    assert gen.run(root, check=False) == 0
    assert (root / "rules/javascript/xss.yaml").read_text(encoding="utf-8").startswith("# GERADO")
    assert gen.run(root, check=True) == 0


def test_check_lists_missing_changed_and_orphan_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = valid_project(tmp_path)
    gen.run(root, check=False)
    (root / "rules/javascript/xss.yaml").write_text("changed\n", encoding="utf-8")
    (root / "rules/javascript/xss-through-dom.yaml").unlink()
    (root / "rules/javascript/old.yaml").write_text("old\n", encoding="utf-8")
    assert gen.run(root, check=True) == 1
    err = capsys.readouterr().err
    assert "desatualizada" in err
    for name in ("xss.yaml", "xss-through-dom.yaml", "old.yaml"):
        assert f"  - javascript/{name}\n" in err


def test_check_does_not_write(tmp_path: Path) -> None:
    root = valid_project(tmp_path)
    assert gen.run(root, check=True) == 1
    assert not (root / "rules").exists()


def test_run_fixes_stale_files_and_removes_orphans(tmp_path: Path) -> None:
    root = valid_project(tmp_path)
    gen.run(root, check=False)
    (root / "rules/javascript/xss.yaml").write_text("changed\n", encoding="utf-8")
    (root / "rules/javascript/old.yaml").write_text("old\n", encoding="utf-8")
    assert gen.run(root, check=False) == 0
    assert not (root / "rules/javascript/old.yaml").exists()
    assert gen.run(root, check=True) == 0


def test_output_is_deterministic(tmp_path: Path) -> None:
    first = gen.generate(valid_project(tmp_path / "a"))
    second = gen.generate(valid_project(tmp_path / "b"))
    assert first == second


def test_errors_stop_the_write(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root = valid_project(tmp_path)
    build(root, {"models/a/orphan.yaml": "- pattern: z\n"})
    assert gen.run(root, check=False) == 1
    assert "models/a/orphan.yaml" in capsys.readouterr().err
    assert not (root / "rules").exists()


def test_read_failure_is_reported(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    build(tmp_path, {"models/a/x.yaml": "a: [\n"})
    assert gen.run(tmp_path, check=False) == 1
    assert "YAML inválido" in capsys.readouterr().err


# --- main -------------------------------------------------------------------------------------


def test_arguments_are_refused() -> None:
    assert gen.main(["--oops"]) == 2
    assert gen.main(["--check", "extra"]) == 2


def test_main_runs_on_the_semgrep_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gen, "ROOT", valid_project(tmp_path))
    assert gen.main(["--check"]) == 1
    assert gen.main([]) == 0
    assert gen.main(["--check"]) == 0


# --- o repo -----------------------------------------------------------------------------------


def test_repository_sources_have_no_errors() -> None:
    _, errors = gen.generate(gen.ROOT)
    assert errors == []


def test_repository_rules_are_up_to_date() -> None:
    outputs, _ = gen.generate(gen.ROOT)
    assert outputs
    assert gen.stale_files(gen.ROOT, outputs) == [], "rode `uv run hooks/generate_semgrep.py`"


# --- o que vira modelo ------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    ["request.GET", "fs.readFile($X, ...)", "$E.innerHTML = $X", "child_process", "$X.length"],
)
def test_pattern_naming_an_api(text: str) -> None:
    assert gen.names_api_text(text)


@pytest.mark.parametrize(
    "text",
    [
        "$X",
        "$F(...)",
        "$X = $Y; ...",
        "typeof $X",
        '"$P" + $X',
        "return $X",
        "$O.$N(...)",
        "`...${$X}...`",
    ],
)
def test_pattern_without_api_name(text: str) -> None:
    assert not gen.names_api_text(text)


def test_names_api_looks_inside_items_and_skips_regex() -> None:
    nested: gen.Node = {
        "patterns": [{"pattern": "$X"}, {"pattern-inside": "if (isElement($X)) {...}"}]
    }
    only_regex: gen.Node = {"metavariable-regex": {"metavariable": "$N", "regex": "^abc$"}}
    assert gen.names_api(nested)
    assert not gen.names_api(only_regex)
    assert not gen.names_api({"pattern-regex": "abc"})
    assert not gen.names_api([{"focus-metavariable": "$X"}, {"pattern": "$F(...)"}])


def test_trivial_item_may_repeat_across_files(tmp_path: Path) -> None:
    body = "    patterns:\n      - pattern: $X\n      - focus-metavariable: $X\n"
    files = {
        "queries/javascript/xss.yaml": rule(body),
        "queries/javascript/xss-through-dom.yaml": rule(body, "js/xss-through-dom"),
    }
    assert errors_of(tmp_path, files) == ""


def test_item_with_a_reference_to_an_api_must_be_a_model(tmp_path: Path) -> None:
    body = "    patterns:\n      - patterns:\n          - $model: a/api\n          - pattern: $X\n"
    files = {
        "models/a/api.yaml": "- pattern: eval($X)\n",
        "queries/javascript/xss.yaml": rule(body),
        "queries/javascript/xss-through-dom.yaml": rule(body, "js/xss-through-dom"),
    }
    assert "repetido em" in errors_of(tmp_path, files)


def test_item_with_a_broken_reference_is_left_to_the_reference_error(tmp_path: Path) -> None:
    body = "    patterns:\n      - patterns:\n          - $model: a/missing\n"
    files = {
        "queries/javascript/xss.yaml": rule(body),
        "queries/javascript/xss-through-dom.yaml": rule(body, "js/xss-through-dom"),
    }
    message = errors_of(tmp_path, files)
    assert "não existe" in message
    assert "repetido em" not in message

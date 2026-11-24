"""Tests for ``itpra_onto.lint``: the ontology's own rules, one implementation (ADR 0042 D1, D5).

Every rule is proven on a small vocabulary written under ``tmp_path``; the real vocabulary lints clean; the
file set equals the emitter's; the rule ids equal the register's Table A rows.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from itpra_onto import emit, lint, parity
from itpra_onto.config import load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCHEMA = {
    "schema_version": 1,
    "ontology_version": "1.2.3",
    "id": {"pattern": r"^[A-Za-z][A-Za-z0-9_.-]*$"},
    "types": ["EntityType", "RelationshipType", "Capability", "Function", "QualityAttribute", "Concept"],
    "relationships": ["supports", "derived_from", "depends_on"],
    "fields": {
        k: {}
        for k in ("id", "term", "type", "definition", "aliases", "deprecated", "relates_to", "source", "retired", "replaced_by")
    },
}
CLEAN_TERMS = [
    {"id": "CAP-X-1", "term": "Alpha", "type": "Capability", "definition": "A capability.", "source": "ADR 0001"},
    {"id": "FUNC-x", "term": "Beta", "type": "Function", "definition": "A function.",
     "relates_to": [{"rel": "supports", "target": "CAP-X-1"}], "source": "ADR 0001 (amended by ADR 0002)"},
    {"id": "QA", "term": "Quality", "type": "QualityAttribute", "definition": "A quality attribute."},
]


def _write(root: Path, *, schema=SCHEMA, terms=CLEAN_TERMS, raw_terms: str | None = None, decisions=("0001", "0002")):
    root.mkdir(parents=True, exist_ok=True)
    (root / "schema.yaml").write_text(yaml.safe_dump(schema, sort_keys=False), encoding="utf-8")
    (root / "terms").mkdir(exist_ok=True)
    (root / "terms" / "terms.yaml").write_text(raw_terms if raw_terms is not None else yaml.safe_dump(terms, sort_keys=False), encoding="utf-8")
    (root / "decisions").mkdir(exist_ok=True)
    for n in decisions:
        (root / "decisions" / f"{n}-a-decision.md").write_text("# a decision\n", encoding="utf-8")
    return root


def _rules(findings) -> list[str]:
    return sorted(f["rule"] for f in findings)


def _mutated(tmp_path: Path, mutate) -> list[dict]:
    terms = [dict(t) for t in CLEAN_TERMS]
    mutate(terms)
    findings, _ = lint.lint_vocabulary(_write(tmp_path / "v", terms=terms))
    return findings


# ---------------------------------------------------------------------------------------------------
# a clean vocabulary, and the real one


def test_clean_vocabulary_has_no_findings(tmp_path: Path):
    findings, vocab = lint.lint_vocabulary(_write(tmp_path / "v"))
    assert findings == []
    assert set(vocab.terms) == {"CAP-X-1", "FUNC-x", "QA"}
    assert vocab.quality_attributes == {"QA"}
    assert vocab.ontology_version == "1.2.3"
    assert vocab.decisions == {"0001", "0002"}
    assert vocab.files["FUNC-x"] == "terms/terms.yaml"


def test_the_real_vocabulary_lints_clean():
    findings, vocab = lint.lint_vocabulary(emit.ontology_dir(load_config()))
    assert lint.errors(findings) == [], findings[:5]
    assert len(vocab.terms) > 1000 and vocab.quality_attributes


def test_vocabulary_files_equal_the_emitters_file_set():
    config = load_config()
    assert lint.vocabulary_files(emit.ontology_dir(config)) == emit.term_files(config)


def test_core_rule_ids_equal_the_registers_table_a_rows():
    assert set(lint.CORE_RULE_IDS) == set(parity.parse_table_a(shapes_dir=None))


def test_file_labels_are_relative_to_rel_to(tmp_path: Path):
    root = _write(tmp_path / "repo" / "01-ontology", terms=[dict(CLEAN_TERMS[0], type="Nope")])
    findings, _ = lint.lint_vocabulary(root, rel_to=tmp_path / "repo")
    assert findings[0]["file"] == "01-ontology/terms/terms.yaml"


# ---------------------------------------------------------------------------------------------------
# one rule at a time (the subject is the record id, as the shapes report it)


def test_field_missing_counts_whitespace_as_absent(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[0].update(definition="   "))
    assert [(f["rule"], f["subject"]) for f in findings] == [("field-missing", "CAP-X-1")]


def test_field_unknown(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[0].update(owner="x"))
    assert [(f["rule"], f["subject"]) for f in findings] == [("field-unknown", "CAP-X-1")]


def test_id_duplicate_names_both_files(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts.append(dict(ts[0])))
    assert _rules(findings) == ["id-duplicate"] and "terms/terms.yaml" in findings[0]["message"]


def test_id_pattern(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[2].update(id="1-BAD"))
    assert [(f["rule"], f["subject"]) for f in findings] == [("id-pattern", "1-BAD")]


def test_type_unknown(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[2].update(type="Widget"))
    assert [(f["rule"], f["subject"]) for f in findings] == [("type-unknown", "QA")]


def test_relates_to_malformed_does_not_crash_on_a_scalar_or_a_nested_mapping(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[1].update(relates_to=["supports", {"rel": "supports", "target": {"id": "CAP-X-1"}}]))
    assert _rules(findings) == ["relates-to-malformed", "target-unresolved"]
    assert {f["subject"] for f in findings} == {"FUNC-x"}


def test_verb_unknown_and_target_unresolved(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[1].update(relates_to=[{"rel": "enables", "target": "CAP-NOPE"}]))
    assert _rules(findings) == ["target-unresolved", "verb-unknown"]


def test_function_derived_from(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[1].update(relates_to=[{"rel": "derived_from", "target": "CAP-X-1"}]))
    assert _rules(findings) == ["function-derived-from"]


def test_source_grammar_and_unresolved_decision(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: (ts[0].update(source="ADR-0001"), ts[1].update(source="ADR 0099")))
    assert [(f["rule"], f["subject"]) for f in findings] == [("source-grammar", "CAP-X-1"), ("source-adr-unresolved", "FUNC-x")]


def test_source_with_a_url_is_external_whatever_it_mentions(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[0].update(source="see ADR 0099 at https://example.org/adr/99"))
    assert findings == []


def test_a_retired_record_with_a_successor_is_clean(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[0].update(retired="1.2.0", replaced_by="QA"))
    assert findings == []


@pytest.mark.parametrize("value", ["1.2", "v1.2.3", "1.2.3-rc1", " 1.2.3", 1.2])
def test_retired_format(tmp_path: Path, value):
    findings = _mutated(tmp_path, lambda ts: ts[0].update(retired=value))
    assert [(f["rule"], f["subject"]) for f in findings] == [("retired-format", "CAP-X-1")]


@pytest.mark.parametrize("value", ["CAP-NOPE", "CAP-X-1", ["QA"]])
def test_replaced_by_unresolved_or_naming_its_own_record(tmp_path: Path, value):
    findings = _mutated(tmp_path, lambda ts: ts[0].update(retired="1.2.0", replaced_by=value))
    assert [(f["rule"], f["subject"]) for f in findings] == [("replaced-by-unresolved", "CAP-X-1")]


def test_replaced_by_without_retired(tmp_path: Path):
    findings = _mutated(tmp_path, lambda ts: ts[0].update(replaced_by="QA"))
    assert [(f["rule"], f["subject"]) for f in findings] == [("replaced-by-without-retired", "CAP-X-1")]


def test_version_format(tmp_path: Path):
    schema = dict(SCHEMA, ontology_version="4.0", schema_version="1")
    findings, _ = lint.lint_vocabulary(_write(tmp_path / "v", schema=schema))
    assert _rules(findings) == ["version-format", "version-format"]


def test_schema_types_missing_is_a_warning(tmp_path: Path):
    schema = {k: v for k, v in SCHEMA.items() if k != "types"}
    findings, _ = lint.lint_vocabulary(_write(tmp_path / "v", schema=schema))
    assert [(f["rule"], f["severity"]) for f in findings] == [("schema-types-missing", "warning")]


def test_file_shape_rules(tmp_path: Path):
    findings, _ = lint.lint_vocabulary(_write(tmp_path / "a", raw_terms="id: CAP-X-1\n"))
    assert _rules(findings) == ["termfile-not-list"]
    findings, _ = lint.lint_vocabulary(_write(tmp_path / "b", raw_terms="- just a string\n- id: QA\n  term: Q\n  type: QualityAttribute\n  definition: d\n"))
    assert _rules(findings) == ["record-not-mapping"]
    findings, _ = lint.lint_vocabulary(_write(tmp_path / "c", raw_terms="- id: [unclosed\n"))
    assert _rules(findings) == ["yaml-parse-error"]


# ---------------------------------------------------------------------------------------------------
# the command


def test_cli_lint_json_over_a_broken_vocabulary(tmp_path: Path):
    root = _write(tmp_path / "v", terms=[dict(CLEAN_TERMS[0], type="Widget")])
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "lint", "--root", str(root), "--json"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 1
    assert [f["rule"] for f in json.loads(result.stdout)] == ["type-unknown"]


def test_cli_lint_defaults_to_the_configured_vocabulary():
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "lint"], cwd=PROJECT_ROOT, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("itpra-onto lint:") and "OK: 0 error(s)" in result.stdout


def test_the_module_imports_without_the_rdf_dependencies(tmp_path: Path):
    """The linter imports with only the standard library and PyYAML (ADR 0042 D5)."""
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); import itpra_onto.lint as m; "
        "banned = {'rdflib', 'pyoxigraph', 'pyshacl', 'linkml', 'linkml_runtime'}; "
        "print(sorted(banned & set(sys.modules)))"
    )
    result = subprocess.run([sys.executable, "-I", "-c", code, str(PROJECT_ROOT / "src")], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"

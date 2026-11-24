"""Tests for ``itpra_onto.parity`` (``itpra-onto parity``; ADR 0042 D5).

Covers, in order: (a) :func:`parity.parse_table_a` and the comparable / emit-time-mapped / outside-scope id
sets it derives, including the ways the register parser must fail; (b) the real-tree comparison (the
acceptance criterion: an EMPTY symmetric difference); (c) the ``--fixtures`` comparison (every fixture's
verdict); (d) the CLI.

Every test reads the real vocabulary files: nothing here is ever written to them — ``--fixtures``
materialises each mutation into a fresh temporary directory, never into the real tree.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from itpra_onto import emit, fixtures, lint, parity
from itpra_onto.config import Config, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPARABLE = {"field-missing", "id-pattern", "target-unresolved", "function-derived-from"}
EMIT_MAPPED = {"type-unknown", "verb-unknown", "relates-to-malformed"}
OUTSIDE_SCOPE = {
    "yaml-parse-error",
    "termfile-not-list",
    "record-not-mapping",
    "field-unknown",
    "id-duplicate",
    "schema-types-missing",
    "source-grammar",
    "source-adr-unresolved",
    "version-format",
}


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


# ---------------------------------------------------------------------------------------------------
# (a) parse_table_a() and the derived id sets


def test_table_a_lists_exactly_the_linters_rule_ids():
    mechanisms = parity.parse_table_a()
    assert set(mechanisms) == set(lint.CORE_RULE_IDS)
    assert len(mechanisms) == len(lint.CORE_RULE_IDS) == 16


def test_table_a_splits_into_comparable_emit_time_and_outside_scope():
    mechanisms = parity.parse_table_a()
    assert set(parity.comparable_rule_ids(mechanisms)) == COMPARABLE
    assert set(parity.emit_time_mapped_rule_ids(mechanisms)) == EMIT_MAPPED
    assert set(parity.outside_scope_rule_ids(mechanisms)) == OUTSIDE_SCOPE
    assert COMPARABLE | EMIT_MAPPED | OUTSIDE_SCOPE == set(mechanisms)


def _register_copy(tmp_path: Path, old: str, new: str) -> Path:
    text = parity.REGISTER_MD.read_text(encoding="utf-8")
    assert old in text, f"test setup: {old!r} not in the register"
    path = tmp_path / "REGISTER.md"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return path


def _register_row(prefix: str) -> str:
    text = parity.REGISTER_MD.read_text(encoding="utf-8")
    return next(line for line in text.splitlines() if line.startswith(prefix))


def test_parse_table_a_accepts_an_unmodified_copy(tmp_path: Path):
    path = _register_copy(tmp_path, "", "")
    assert parity.parse_table_a(path) == parity.parse_table_a()


def test_parse_table_a_raises_on_a_changed_header_row(tmp_path: Path):
    path = _register_copy(tmp_path, parity.TABLE_A_HEADER, "| rule | sev | check | family | mechanism | target | notes |")
    with pytest.raises(parity.ParityError, match="header row"):
        parity.parse_table_a(path, shapes_dir=None)


def test_parse_table_a_raises_when_the_row_count_disagrees_with_the_counts_line(tmp_path: Path):
    path = _register_copy(tmp_path, "**Table A rows:** 16", "**Table A rows:** 15")
    with pytest.raises(parity.ParityError, match="16 rows but the Counts section states 15"):
        parity.parse_table_a(path, shapes_dir=None)


def test_parse_table_a_raises_when_a_row_is_dropped(tmp_path: Path):
    path = _register_copy(tmp_path, _register_row("| `id-duplicate` |") + "\n", "")
    with pytest.raises(parity.ParityError, match="15 rows but the Counts section states 16"):
        parity.parse_table_a(path, shapes_dir=None)


def test_parse_table_a_raises_without_a_counts_line(tmp_path: Path):
    path = _register_copy(tmp_path, "**Table A rows:** 16", "Table A rows: 16")
    with pytest.raises(parity.ParityError, match="states no"):
        parity.parse_table_a(path, shapes_dir=None)


def test_parse_table_a_raises_on_an_unknown_mechanism(tmp_path: Path):
    row = _register_row("| `yaml-parse-error` |")
    path = _register_copy(tmp_path, row, row.replace("| `python`", "| `manual`", 1))
    with pytest.raises(parity.ParityError, match="has mechanism 'manual'"):
        parity.parse_table_a(path, shapes_dir=None)


def test_parse_table_a_raises_without_a_table_a_section(tmp_path: Path):
    register = tmp_path / "REGISTER.md"
    register.write_text("# a register with no tables\n", encoding="utf-8")
    with pytest.raises(parity.ParityError, match="could not locate"):
        parity.parse_table_a(register)


def test_parse_table_a_raises_when_a_comparable_id_has_no_shape(tmp_path: Path):
    """`yaml-parse-error` relabelled `core` makes it comparable; no shape carries that ruleId."""
    row = _register_row("| `yaml-parse-error` |")
    path = _register_copy(tmp_path, row, row.replace("| `python`", "| `core`", 1))
    with pytest.raises(parity.ParityError, match=r"\['yaml-parse-error'\] are no itpra-o:ruleId"):
        parity.parse_table_a(path)


def test_parse_table_a_raises_when_a_shape_rule_id_is_in_no_table(tmp_path: Path):
    """Drop the B-22 row from Table B: the generated shapes still carry ruleId B-22."""
    path = _register_copy(tmp_path, _register_row("| B-22 |") + "\n", "")
    with pytest.raises(parity.ParityError, match=r"\['B-22'\] in the shapes .* appear in neither Table A nor Table B"):
        parity.parse_table_a(path)


def test_parse_table_b_ids_includes_the_hyphen_suffixed_and_b22_rows():
    ids = parity.parse_table_b_ids()
    assert {"B-2", "B-2-supports", "B-3-belongs-to-service-domain", "B-8-pref-label-unique", "B-22"} <= ids


def test_every_shape_rule_id_is_registered_and_every_comparable_id_is_shaped():
    in_shapes = parity.shape_rule_ids()
    mechanisms = parity.parse_table_a()
    assert set(parity.comparable_rule_ids(mechanisms)) <= in_shapes
    assert in_shapes <= set(mechanisms) | parity.parse_table_b_ids()
    assert "B-22" in in_shapes


# ---- which fixture verdicts fail ------------------------------------------------------------------------


def _verdict(verdict: str, comparable: bool) -> parity.FixtureVerdict:
    return parity.FixtureVerdict(
        fixture="x.yaml", nominal_rule="r", focus="F", shacl_caught=verdict in ("both", "shacl-only"),
        shacl_rule_seen=None, linter_caught=verdict in ("both", "linter-only"), linter_rules_seen=(),
        verdict=verdict, comparable=comparable,
    )


@pytest.mark.parametrize(
    ("verdict", "comparable", "fails"),
    [
        ("both", True, False),
        ("shacl-only", True, False),
        ("shacl-only", False, False),
        ("linter-only", True, True),
        ("neither", True, True),
        ("neither", False, True),
    ],
)
def test_fixture_failures(verdict: str, comparable: bool, fails: bool):
    assert bool(parity.fixture_failures([_verdict(verdict, comparable)])) is fails


# ---------------------------------------------------------------------------------------------------
# (b) real-tree comparison: the acceptance criterion is an EMPTY symmetric difference


@pytest.fixture(scope="module")
def real_tree(config: Config) -> parity.RealTreeComparison:
    return parity.run_real_tree(config=config)


def test_real_tree_symmetric_difference_is_empty(real_tree: parity.RealTreeComparison):
    assert real_tree.emit_errors == ()
    assert real_tree.linter_only == () and real_tree.shacl_only == (), (real_tree.linter_only, real_tree.shacl_only)
    assert real_tree.passed


def test_real_tree_compares_the_comparable_rules_and_reports_the_rest(real_tree: parity.RealTreeComparison):
    assert set(real_tree.comparable_rules) == COMPARABLE
    assert set(real_tree.outside_scope) == OUTSIDE_SCOPE


def test_real_tree_stricter_findings_are_empty_on_the_clean_vocabulary(real_tree: parity.RealTreeComparison):
    assert real_tree.stricter_findings == ()


def test_real_tree_excludes_linter_meta_edge_findings_on_entity_type_records(monkeypatch: pytest.MonkeyPatch, config: Config):
    """The linter's target-unresolved / verb-unknown on an EntityType record (a meta-edge the emitter
    never projects) is excluded from the comparison and reported, while the same id on a term still counts."""
    fake = [
        {"rule": "target-unresolved", "subject": "CAPABILITY", "severity": "error", "message": "meta-edge"},
        {"rule": "target-unresolved", "subject": "CAP-ITO-FND-1", "severity": "error", "message": "real"},
    ]
    monkeypatch.setattr(parity, "lint_findings", lambda config=None, **kwargs: fake)
    comparison = parity.run_real_tree(config=config)
    assert comparison.meta_edge_excluded == (("target-unresolved", "CAPABILITY", "error"),)
    assert comparison.linter_only == (("target-unresolved", "CAP-ITO-FND-1", "error"),)
    assert not comparison.passed


def test_real_tree_turns_an_emit_error_into_a_finding(monkeypatch: pytest.MonkeyPatch, config: Config):
    """The emitter refusing the inputs yields one `emit-error` finding (on the record the error names)
    and a failing comparison — no traceback. `emit.load_inputs` is monkeypatched to return a mutated copy
    (the input-path guard, ADR 0043 D1, forbids pointing the emitter at a scratch tree outside the repository)."""
    real = emit.load_inputs(config)
    fixture = fixtures.load_fixture(parity.FIXTURES_DIR / "structural" / "relates-to-malformed.yaml")
    mutated = fixtures.apply_fixture(real, fixture)
    monkeypatch.setattr(emit, "load_inputs", lambda config=None: mutated)
    monkeypatch.setattr(parity, "lint_findings", lambda config=None, **kwargs: [])
    comparison = parity.run_real_tree(config=config)
    assert len(comparison.emit_errors) == 1
    error = comparison.emit_errors[0]
    assert error["rule"] == "emit-error" and error["subject"] == "CAP-ITO-FND-1" and error["severity"] == "error"
    assert error["message"].startswith("EmitError: ")
    assert not comparison.passed
    assert parity.comparison_as_dict(comparison)["emit_errors"] == [error]


def test_lint_findings_over_a_scratch_copy_label_files_from_the_repository_root(tmp_path: Path, config: Config):
    """The scratch copy mirrors the real layout, so the labels equal the real run's and a focus id matches."""
    scratch = tmp_path / "scratch"
    copied = parity.copy_ontology_dir(scratch, config)
    assert copied == parity.scratch_path(scratch, emit.ontology_dir(config), config.repo_root)
    real = parity.lint_findings(config)
    scratch_findings = parity.lint_findings(config, ontology_dir=copied)
    assert lint.errors(real) == [] and lint.errors(scratch_findings) == []


# ---------------------------------------------------------------------------------------------------
# (c) --fixtures comparison (one module-scoped run: a scratch copy and a lint run per fixture)


@pytest.fixture(scope="module")
def verdicts(config: Config) -> list[parity.FixtureVerdict]:
    return parity.run_fixtures(config=config)


def test_run_fixtures_only_considers_count_ge_1_fixtures(verdicts: list[parity.FixtureVerdict]):
    """A `count: 0` clean-case fixture proves a shape does NOT fire: there is nothing for the linter to confirm."""
    names = {v.fixture for v in verdicts}
    expected = {
        path.relative_to(parity.FIXTURES_DIR).as_posix()
        for path in parity.FIXTURES_DIR.glob("*/*.yaml")
        if fixtures.load_fixture(path).count >= 1
    }
    assert names == expected
    assert {"structural/B-2-supports.yaml", "structural/B-8-pref-label-unique.yaml", "crossfield/B-13.yaml"}.isdisjoint(names)


def test_no_fixture_verdict_fails(verdicts: list[parity.FixtureVerdict]):
    """`neither` on any fixture, or `linter-only` on a comparable or emit-mapped rule, is a failure."""
    assert verdicts, "no fixtures ran"
    assert parity.fixture_failures(verdicts) == []
    assert not [v.fixture for v in verdicts if v.verdict == "neither"]


def test_fixtures_the_linter_can_prove_are_caught_on_both_sides(verdicts: list[parity.FixtureVerdict]):
    by_rule: dict[str, set[str]] = {}
    for v in verdicts:
        by_rule.setdefault(v.nominal_rule, set()).add(v.verdict)
    for rule in COMPARABLE | EMIT_MAPPED:
        assert by_rule.get(rule) == {"both"}, (rule, by_rule.get(rule))


def test_every_table_b_fixture_is_shacl_only(verdicts: list[parity.FixtureVerdict]):
    """A Table B id is stricter than the linter by construction: the linter has no such rule."""
    stricter = [v for v in verdicts if not v.comparable]
    assert stricter, "expected at least one Table B fixture with expect.count >= 1"
    for v in stricter:
        assert v.nominal_rule.startswith("B-"), v.fixture
        assert v.verdict == "shacl-only" and not v.linter_caught, (v.fixture, v.verdict)


def test_emit_time_mapping_recovers_the_rule_id_from_an_emit_error(verdicts: list[parity.FixtureVerdict]):
    """An `emit-error` synthetic finding is recovered to its Table A id and confirmed by the linter's own
    same-named rule on the same focus."""
    by_fixture = {v.fixture: v for v in verdicts}
    for rule in sorted(EMIT_MAPPED):
        verdict = by_fixture[f"structural/{rule}.yaml"]
        assert verdict.nominal_rule == rule
        assert verdict.shacl_rule_seen == "emit-error"
        assert verdict.linter_caught, f"{rule}: the linter must report it itself"
        assert verdict.verdict == "both"


def test_b13_emit_guard_recovers_to_b13_not_a_literal_filename(verdicts: list[parity.FixtureVerdict]):
    """`nominal_rule_id` strips the `-emit-guard` suffix rather than treating the whole filename as the id."""
    b13 = {v.fixture: v for v in verdicts}["crossfield/B-13-emit-guard.yaml"]
    assert b13.nominal_rule == "B-13"
    assert b13.verdict == "shacl-only"


# ---------------------------------------------------------------------------------------------------
# (d) the CLI


def _cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "parity", *args],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    )


def test_cli_parity_json_is_valid_json_and_the_only_stdout():
    result = _cli("--json")
    assert result.returncode == 0, result.stdout + result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1, result.stdout
    payload = json.loads(lines[0])
    assert set(payload) == {
        "comparable_rules",
        "linter",
        "shacl",
        "linter_only",
        "shacl_only",
        "stricter_findings",
        "outside_scope",
        "meta_edge_excluded",
        "emit_errors",
    }
    assert set(payload["comparable_rules"]) == COMPARABLE
    assert payload["linter_only"] == [] and payload["shacl_only"] == [] and payload["emit_errors"] == []


def test_cli_parity_plain_reports_an_empty_difference():
    result = _cli()
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Traceback" not in result.stdout + result.stderr

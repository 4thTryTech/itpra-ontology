"""Tests for ``itpra_onto.parity`` (``itpra-onto parity``; ADR 0042 D5).

Covers, in order: (a) :func:`parity.parse_table_a` and the comparable/emit-time-mapped/outside-scope id
sets it derives; (b) the real-tree comparison (the acceptance criterion: an EMPTY symmetric difference —
if this is ever not empty, the assertion below reports every item with its cause rather than being
weakened); (c) the ``--fixtures`` comparison (every comparable fixture's verdict); (d) the CLI (`--json`
validity/exclusivity, exit codes); (e) timing (printed with ``-s``, not asserted beyond a generous bound).

Every test reads the REAL input files, exactly like ``test_shacl.py``/``test_emit.py``: nothing here is
ever written to the vocabulary or the consumer's registries — ``--fixtures`` materialises into a fresh
``tempfile.TemporaryDirectory()`` per fixture (``itpra_onto.parity``'s own module docstring), never into
the real tree.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from itpra_onto import parity
from itpra_onto.config import Config, load_config

pytestmark = pytest.mark.overlay  # needs the consumer's registries / linter

PROJECT_ROOT = Path(__file__).resolve().parents[1]

_MODULE_STARTED = time.perf_counter()


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


# ---------------------------------------------------------------------------------------------------
# (a) parse_table_a() and the derived id sets


def test_parse_table_a_finds_the_twenty_two_rows():
    mechanisms = parity.parse_table_a()
    assert len(mechanisms) == 22, f"expected the 22-row 'A/C' sub-table, parsed {len(mechanisms)}: {sorted(mechanisms)}"


def test_comparable_rule_ids_are_at_least_eight_and_exclude_relates_to_malformed():
    mechanisms = parity.parse_table_a()
    comparable = parity.comparable_rule_ids(mechanisms)
    assert len(comparable) >= 8, comparable
    assert "relates-to-malformed" not in comparable, "the erratum must exclude relates-to-malformed from the comparable set"
    # the exact set this register's content yields today (a regression here means the register's Table A
    # mechanism column changed — investigate before touching this list)
    assert set(comparable) == {
        "field-missing",
        "id-pattern",
        "target-unresolved",
        "function-derived-from",
        "req-id-format",
        "req-qa-unresolved",
        "req-statement-missing",
        "req-target-unresolved",
    }


def test_emit_time_mapped_rule_ids_are_the_generated_plus_emit_time_python_ids():
    mechanisms = parity.parse_table_a()
    emit_mapped = parity.emit_time_mapped_rule_ids(mechanisms)
    assert set(emit_mapped) == {
        "type-unknown",
        "verb-unknown",
        "req-type-invalid",
        "relates-to-malformed",
        "req-link-malformed",
    }


def test_outside_scope_rule_ids_are_the_remaining_nine_python_ac_ids():
    mechanisms = parity.parse_table_a()
    comparable = set(parity.comparable_rule_ids(mechanisms))
    emit_mapped = set(parity.emit_time_mapped_rule_ids(mechanisms))
    outside = parity.outside_scope_rule_ids(mechanisms)
    assert set(outside) == set(mechanisms) - comparable - emit_mapped
    assert set(outside) == {
        "yaml-parse-error",
        "termfile-not-list",
        "record-not-mapping",
        "id-duplicate",
        "schema-types-missing",
        "req-file-missing",
        "req-file-malformed",
        "doc-idlike-unresolved",
        "field-unknown",
    }


# ---- the register parser fails loudly (mutated copies of the real register in tmp_path) ----------------


def _register_copy(tmp_path: Path, old: str, new: str) -> Path:
    text = parity.REGISTER_MD.read_text(encoding="utf-8")
    assert old in text, f"test setup: {old!r} not in the register"
    path = tmp_path / "REGISTER.md"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return path


def test_parse_table_a_accepts_an_unmodified_copy(tmp_path: Path):
    path = _register_copy(tmp_path, "", "")
    assert parity.parse_table_a(path) == parity.parse_table_a()


def test_parse_table_a_raises_on_a_changed_header_row(tmp_path: Path):
    path = _register_copy(tmp_path, parity.TABLE_A_HEADER, "| rule | sev | check | family | mechanism | target | notes |")
    with pytest.raises(parity.ParityError, match="header row"):
        parity.parse_table_a(path, shapes_dir=None)


def test_parse_table_a_raises_when_the_row_count_disagrees_with_the_counts_line(tmp_path: Path):
    path = _register_copy(tmp_path, "**Table A 'A/C' sub-table rows:** 22", "**Table A 'A/C' sub-table rows:** 21")
    with pytest.raises(parity.ParityError, match="22 rows but the Counts section states 21"):
        parity.parse_table_a(path, shapes_dir=None)


def test_parse_table_a_raises_when_a_row_is_dropped(tmp_path: Path):
    text = parity.REGISTER_MD.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| `id-duplicate` |"))
    path = _register_copy(tmp_path, row + "\n", "")
    with pytest.raises(parity.ParityError, match="21 rows but the Counts section states 22"):
        parity.parse_table_a(path, shapes_dir=None)


def test_parse_table_a_raises_without_a_counts_line(tmp_path: Path):
    path = _register_copy(tmp_path, "**Table A 'A/C' sub-table rows:** 22", "Table A rows: 22")
    with pytest.raises(parity.ParityError, match="states no"):
        parity.parse_table_a(path, shapes_dir=None)


def test_parse_table_a_raises_when_a_comparable_id_has_no_shape(tmp_path: Path):
    """`yaml-parse-error` relabelled `core` makes it comparable; no shape carries that ruleId."""
    text = parity.REGISTER_MD.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| `yaml-parse-error` |"))
    path = _register_copy(tmp_path, row, row.replace("| `python` —", "| `core` —", 1))
    with pytest.raises(parity.ParityError, match=r"\['yaml-parse-error'\] are no itpra-o:ruleId"):
        parity.parse_table_a(path)


def test_parse_table_a_raises_when_a_shape_rule_id_is_in_no_table(tmp_path: Path):
    """Drop the B-22 row from Table B: the generated shapes still carry ruleId B-22."""
    text = parity.REGISTER_MD.read_text(encoding="utf-8")
    row = next(line for line in text.splitlines() if line.startswith("| B-22 |"))
    path = _register_copy(tmp_path, row + "\n", "")
    with pytest.raises(parity.ParityError, match=r"\['B-22'\] in the shapes .* appear in neither Table A nor Table B"):
        parity.parse_table_a(path)


def test_parse_table_b_ids_includes_the_hyphen_suffixed_and_b22_rows():
    ids = parity.parse_table_b_ids()
    assert {"B-1", "B-21", "B-2-supports", "B-3-belongs-to-service-domain", "B-8-pref-label-unique", "B-22"} <= ids


def test_every_shape_rule_id_is_registered_and_every_comparable_id_is_shaped():
    in_shapes = parity.shape_rule_ids()
    mechanisms = parity.parse_table_a()
    assert set(parity.comparable_rule_ids(mechanisms)) <= in_shapes
    assert in_shapes <= set(mechanisms) | parity.parse_table_b_ids()
    assert "B-22" in in_shapes


# ---- literals the consumer's linter duplicates must equal the pipeline's -------------------------------


def _linter_constant(name: str):
    import ast

    tree = ast.parse(parity.linter_script().read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} not found in {parity.linter_script()}")


def test_linter_requirement_id_patterns_equal_the_schema_and_the_shapes():
    from itpra_onto import schema_loading, shacl

    patterns = _linter_constant("REQ_ID_PATTERNS")
    sv = schema_loading.load_schema_view()
    for cls in ("FR", "NFR"):
        schema_pattern = sv.induced_slot("id", cls).pattern
        assert patterns[cls] == schema_pattern, cls
    shapes_text = (shacl.SHAPES_DIR / "requirements.ttl").read_text(encoding="utf-8")
    assert f'sh:pattern "{patterns["FR"]}"' in shapes_text
    assert f'sh:pattern "{patterns["NFR"]}"' in shapes_text


def test_linter_instance_prefixes_equal_the_req_target_unresolved_shape():
    import re as _re

    from itpra_onto import shacl

    prefixes = _linter_constant("INSTANCE_PREFIXES")
    shapes_text = (shacl.SHAPES_DIR / "requirements.ttl").read_text(encoding="utf-8")
    match = _re.search(r'"\^\(([A-Z|]+)\)\(-\|\$\)"', shapes_text)
    assert match, "the req-target-unresolved prefix regex was not found in requirements.ttl"
    assert tuple(match.group(1).split("|")) == tuple(prefixes)


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


# ---- EntityType meta-edges are excluded; an EmitError is a finding, not a traceback --------------------


def test_real_tree_excludes_linter_meta_edge_findings_on_entity_type_records(monkeypatch: pytest.MonkeyPatch, config: Config):
    """The linter's target-unresolved / verb-unknown on an EntityType record (a meta-edge the emitter
    never projects) is excluded from the comparison and reported, while the same id on a term still counts."""
    fake = [
        {"rule": "target-unresolved", "subject": "CAPABILITY", "severity": "error", "message": "meta-edge"},
        {"rule": "target-unresolved", "subject": "CAP-FND-1", "severity": "error", "message": "real"},
    ]
    monkeypatch.setattr(parity, "run_linter", lambda sub: fake)
    comparison = parity.run_real_tree(subs=["ITO"], config=config)
    assert comparison.meta_edge_excluded == (("target-unresolved", "CAPABILITY", "error"),)
    assert comparison.linter_only == (("target-unresolved", "CAP-FND-1", "error"),)
    assert not comparison.passed


def test_real_tree_turns_an_emit_error_into_a_finding(monkeypatch: pytest.MonkeyPatch, config: Config):
    """The emitter refusing the inputs yields one `emit-error` finding (on the record the error names)
    and a failing comparison — no traceback. `emit.load_inputs` is monkeypatched to return a mutated copy
    (the input-path guard, ADR 0043 D1, forbids pointing the emitter at a scratch tree outside the repository)."""
    from itpra_onto import emit, fixtures

    real = emit.load_inputs(config)
    fixture = fixtures.load_fixture(parity.FIXTURES_DIR / "structural" / "relates-to-malformed.yaml")
    mutated = fixtures.apply_fixture(real, fixture)
    monkeypatch.setattr(emit, "load_inputs", lambda config=None: mutated)
    monkeypatch.setattr(parity, "run_linter", lambda sub: [])
    comparison = parity.run_real_tree(subs=["ITO"], config=config)
    assert len(comparison.emit_errors) == 1
    error = comparison.emit_errors[0]
    assert error["rule"] == "emit-error" and error["subject"] == "CAP-FND-1" and error["severity"] == "error"
    assert error["message"].startswith("EmitError: ")
    assert not comparison.passed
    assert parity.comparison_as_dict(comparison)["emit_errors"] == [error]


def test_parse_table_a_raises_on_a_missing_erratum_marker(tmp_path: Path):
    register = tmp_path / "REGISTER.md"
    register.write_text("### A/C — ontology term integrity\n| id |\n|---|\n### B — derived-package\n", encoding="utf-8")
    with pytest.raises(parity.ParityError):
        parity.parse_table_a(register)


def test_parse_table_a_raises_on_a_missing_ac_section(tmp_path: Path):
    register = tmp_path / "REGISTER.md"
    register.write_text(parity._ERRATUM_MARKER + " ... no A/C section here", encoding="utf-8")
    with pytest.raises(parity.ParityError):
        parity.parse_table_a(register)


# ---------------------------------------------------------------------------------------------------
# (b) real-tree comparison: the acceptance criterion is an EMPTY symmetric difference
#
# run_real_tree() over every registry is not cheap (one linter subprocess per registry + one whole-tree
# SHACL validate — ~15s measured); every test in this section shares ONE module-scoped run rather than
# repeating it, so the suite's wall time stays dominated by --fixtures (by far the more expensive half)
# rather than by redundant real-tree re-runs.


@pytest.fixture(scope="module")
def real_tree_comparison() -> parity.RealTreeComparison:
    return parity.run_real_tree()


def test_real_tree_symmetric_difference_is_empty(real_tree_comparison: parity.RealTreeComparison):
    """The acceptance criterion (ADR 0042 D5). If this ever fails, DO NOT weaken it:
    report every differing item and its likely cause (a linter warning with no shape at all — a `python`
    row misclassified as comparable — or a focus-subject naming mismatch between the two sides) rather than
    dropping or loosening the assertion."""
    if not real_tree_comparison.empty_symmetric_difference:
        lines = ["Non-empty symmetric difference between the linter and SHACL over the comparable rule set:"]
        for f in real_tree_comparison.linter_only:
            lines.append(f"  linter-only: rule={f[0]!r} subject={f[1]!r} severity={f[2]!r}")
        for f in real_tree_comparison.shacl_only:
            lines.append(f"  shacl-only:  rule={f[0]!r} subject={f[1]!r} severity={f[2]!r}")
        pytest.fail("\n".join(lines))


def test_real_tree_comparable_rules_matches_parse_table_a(real_tree_comparison: parity.RealTreeComparison):
    mechanisms = parity.parse_table_a()
    assert set(real_tree_comparison.comparable_rules) == set(parity.comparable_rule_ids(mechanisms))


def test_real_tree_restricted_to_one_registry_still_runs(config: Config):
    """`--sub` restricts the linter side to fewer invocations; SHACL always validates the whole tree
    regardless (module docstring: no per-registry partitioning), so this must still produce a
    well-formed comparison (not necessarily an empty difference, since the SHACL side may see requirement
    findings from OTHER registries that ITO's own linter run never reports). A separate, smaller run
    (single registry) — not the shared module-scoped fixture, since restricting `subs` is the very thing
    under test here."""
    comparison = parity.run_real_tree(subs=["ITO"], config=config)
    assert comparison.comparable_rules
    assert comparison.linter_count >= 0
    assert comparison.shacl_count >= 0


def test_real_tree_stricter_findings_are_empty_on_the_clean_corpus(real_tree_comparison: parity.RealTreeComparison):
    """Informational, but worth asserting: on today's clean corpus no Table B ('stricter') shape fires at
    all over the real tree (README.md's own "0 findings" claim for `itpra-onto validate`)."""
    assert real_tree_comparison.stricter_findings == ()


# ---------------------------------------------------------------------------------------------------
# (c) --fixtures comparison


_ALL_COMPARABLE_FIXTURE_VERDICTS = None
_FIXTURES_ELAPSED = None


def _fixture_verdicts() -> list[parity.FixtureVerdict]:
    """Cached at module (in fact process) scope: ``run_fixtures()`` spins up a fresh scratch tree and a
    linter subprocess per fixture (~20+ fixtures), by far the most expensive call in this test module — every
    test in section (c) below shares this ONE run rather than repeating it."""
    global _ALL_COMPARABLE_FIXTURE_VERDICTS, _FIXTURES_ELAPSED
    if _ALL_COMPARABLE_FIXTURE_VERDICTS is None:
        started = time.perf_counter()
        _ALL_COMPARABLE_FIXTURE_VERDICTS = parity.run_fixtures()
        _FIXTURES_ELAPSED = time.perf_counter() - started
    return _ALL_COMPARABLE_FIXTURE_VERDICTS


@pytest.fixture(scope="module")
def fixture_verdicts() -> list[parity.FixtureVerdict]:
    return _fixture_verdicts()


def test_run_fixtures_only_considers_count_ge_1_fixtures(fixture_verdicts: list[parity.FixtureVerdict]):
    # 25 fixtures total (shapes/README.md); count:0 clean-case fixtures (B-2-supports, B-8-pref-label-unique,
    # crossfield/B-13) are excluded — module docstring.
    assert len(fixture_verdicts) >= 20
    names = {v.fixture for v in fixture_verdicts}
    assert "structural/B-2-supports.yaml" not in names
    assert "structural/B-8-pref-label-unique.yaml" not in names
    assert "crossfield/B-13.yaml" not in names


def test_every_comparable_fixture_is_both_or_shacl_only(fixture_verdicts: list[parity.FixtureVerdict]):
    """Every fixture whose nominal rule is comparable or emit-time-mapped must be caught by AT LEAST the
    shape (`neither` would mean the shape itself regressed — a real failure). No comparable fixture is a
    documented `shacl-only` exception (the stricter typed check lives in B-22)."""
    failures = []
    for v in fixture_verdicts:
        if not v.comparable:
            continue
        if v.verdict not in ("both", "shacl-only"):
            failures.append(v)
    assert not failures, "\n".join(
        f"{v.fixture}: nominal_rule={v.nominal_rule!r} verdict={v.verdict!r} "
        f"shacl_caught={v.shacl_caught} linter_caught={v.linter_caught} linter_rules_seen={v.linter_rules_seen}"
        for v in failures
    )


def test_no_fixture_verdict_is_neither(fixture_verdicts: list[parity.FixtureVerdict]):
    """`neither` (module docstring) is always a bug regardless of comparability — nothing under test should
    go completely unnoticed by both sides."""
    neither = [v for v in fixture_verdicts if v.verdict == "neither"]
    assert not neither, [v.fixture for v in neither]


def test_every_table_b_stricter_fixture_is_shacl_only(fixture_verdicts: list[parity.FixtureVerdict]):
    """Every fixture whose nominal rule is NOT comparable/emit-time-mapped (i.e. a genuine Table B
    'stricter than the linter' id) must verdict `shacl-only` — the linter has no concept of it at all, by
    construction, so `linter_caught` must always be False for these."""
    stricter = [v for v in fixture_verdicts if not v.comparable]
    assert stricter, "expected at least one Table B (stricter) fixture with expect.count >= 1"
    for v in stricter:
        assert v.verdict == "shacl-only", f"{v.fixture}: nominal_rule={v.nominal_rule!r} expected shacl-only, got {v.verdict!r}"
        assert not v.linter_caught, f"{v.fixture}: the linter unexpectedly reported nominal_rule {v.nominal_rule!r}"


def test_emit_time_mapping_is_exercised_by_type_unknown_and_relates_to_malformed(fixture_verdicts: list[parity.FixtureVerdict]):
    """The emit-time mapping (module docstring) must actually be tested end to end: an `emit-error`
    synthetic finding recovered to its real Table A id, independently confirmed by the linter's OWN
    same-named rule on the same focus."""
    by_fixture = {v.fixture: v for v in fixture_verdicts}
    type_unknown = by_fixture["structural/type-unknown.yaml"]
    assert type_unknown.nominal_rule == "type-unknown"
    assert type_unknown.shacl_rule_seen == "emit-error"
    assert type_unknown.linter_caught, "the real linter must independently report type-unknown for this mutation"
    assert type_unknown.verdict == "both"

    relates_to_malformed = by_fixture["structural/relates-to-malformed.yaml"]
    assert relates_to_malformed.nominal_rule == "relates-to-malformed"
    assert relates_to_malformed.shacl_rule_seen == "emit-error"
    assert relates_to_malformed.linter_caught
    assert relates_to_malformed.verdict == "both"

    # verb-unknown on a Capability (not an EntityType record) and req-link-malformed
    for name, rule in (("structural/verb-unknown.yaml", "verb-unknown"), ("structural/req-link-malformed.yaml", "req-link-malformed")):
        verdict = by_fixture[name]
        assert verdict.nominal_rule == rule
        assert verdict.shacl_rule_seen == "emit-error"
        assert verdict.linter_caught, f"{name}: the linter must report {rule} itself"
        assert verdict.verdict == "both"


def test_no_fixture_verdict_fails(fixture_verdicts: list[parity.FixtureVerdict]):
    """The CLI's own failure rule (`linter-only` on a comparable/emit-mapped rule is a failure,
    `neither` always is) finds nothing."""
    assert parity.fixture_failures(fixture_verdicts) == []


def test_b22_fixtures_are_shacl_only(fixture_verdicts: list[parity.FixtureVerdict]):
    b22 = [v for v in fixture_verdicts if v.nominal_rule == "B-22"]
    assert len(b22) == 4, [v.fixture for v in b22]
    assert all(v.verdict == "shacl-only" and not v.comparable for v in b22)


def test_req_target_unresolved_fixture_is_now_caught_by_both(fixture_verdicts: list[parity.FixtureVerdict]):
    """The shape mirrors the linter, so its fixture is `both`, not a documented exception."""
    by_fixture = {v.fixture: v for v in fixture_verdicts}
    assert by_fixture["requirements/req-target-unresolved.yaml"].verdict == "both"


def test_b13_emit_guard_recovers_to_b13_not_a_literal_filename(fixture_verdicts: list[parity.FixtureVerdict]):
    """`_nominal_rule_id` must strip the `-emit-guard` suffix, not treat the whole filename as the id."""
    by_fixture = {v.fixture: v for v in fixture_verdicts}
    b13 = by_fixture["crossfield/B-13-emit-guard.yaml"]
    assert b13.nominal_rule == "B-13"
    assert b13.verdict == "shacl-only"


# ---------------------------------------------------------------------------------------------------
# (d) the CLI


def test_cli_parity_json_on_the_real_tree_is_valid_json_and_the_only_stdout():
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "parity", "--json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
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
    passed = not payload["linter_only"] and not payload["shacl_only"] and not payload["emit_errors"]
    assert result.returncode == (0 if passed else 1)


def test_cli_parity_sub_restricts_to_the_named_registries_plain_mode():
    """One `--sub`-restricted (cheap: a single linter invocation, not one per registry) plain-mode CLI run,
    black-box confirming the exit-code/summary-line contract without paying for a second full real-tree
    subprocess."""
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "parity", "--sub", "ITO"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), (result.stdout, result.stderr)
    assert "comparable rule id(s)" in result.stdout


# ---------------------------------------------------------------------------------------------------
# (e) timing


def test_zz_parity_fixtures_timing(fixture_verdicts: list[parity.FixtureVerdict]):
    print(f"\nparity.run_fixtures() over {len(fixture_verdicts)} fixture(s): {_FIXTURES_ELAPSED:.3f}s")


def test_zz_parity_real_tree_timing():
    started = time.perf_counter()
    comparison = parity.run_real_tree()
    elapsed = time.perf_counter() - started
    print(
        f"\nparity.run_real_tree() over {len(parity.default_registries())} registry(ies): {elapsed:.3f}s, "
        f"empty_symmetric_difference={comparison.empty_symmetric_difference}"
    )
    assert elapsed < 120, f"run_real_tree() took {elapsed:.1f}s — investigate before the corpus grows further"


def test_zzz_parity_suite_timing():
    elapsed = time.perf_counter() - _MODULE_STARTED
    print(f"\ntest_parity.py module wall time so far: {elapsed:.3f}s")

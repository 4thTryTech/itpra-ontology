"""Tests for the `structural` shape file (``shapes/REGISTER.md``'s grouping table): ``shapes/structural.ttl``
+ one fixture per rule id under ``fixtures/structural/``.

Parametrised over every fixture file (each proves exactly one rule id, ``fixtures.py``'s
``assert_fixture()``), plus whole-file checks: every shape carries ``itpra-o:ruleId`` and ``sh:severity``;
the file's rule ids are a subset of ``shapes/REGISTER.md``'s own ids, except two ids
(``B-3-belongs-to-service-domain``, ``B-2-supports`` — declared cardinalities from the same ``itpra_verb``
annotations as the registered B-2/B-3 rows) that DO have their own `shapes/REGISTER.md` Table B row but that
``_register_rule_ids()``'s own regex below cannot detect: it matches only a bare ``B-<digits>`` id, never a
hyphen-suffixed family name like these two, so they still need this module's own
``NEW_UNREGISTERED_RULE_IDS`` allow-list even though they are, in fact, registered; no base-IRI literal (the
real scan-test coverage is
``test_shacl.py::test_no_base_iri_literal_in_any_ttl_under_shapes_or_the_smoke_dir``, which already globs
``shapes/*.ttl`` — this module repeats a narrower version directly against ``structural.ttl`` alone, so a
failure here points straight at this file); and clean (unmutated) data conforms with zero Violations and
exactly the Warning set this module documents (the real corpus already satisfies the three B-5/B-6/B-7
declared-advisory minimums — built as ``sh:Warning``, ADR 0042 D3 — so that set is expected to be empty).
"""

from __future__ import annotations

import re
from pathlib import Path

import pyoxigraph as ox
import pytest

from itpra_onto import emit, fixtures, rules, shacl
from itpra_onto.config import Config, load_config

PROJECT_DIR = Path(__file__).resolve().parents[1]  # the package root
SHAPES_DIR = shacl.SHAPES_DIR
STRUCTURAL_SHAPE_FILE = SHAPES_DIR / "structural.ttl"
FIXTURES_DIR = fixtures.FIXTURES_DIR / "structural"
REGISTER_MD = SHAPES_DIR / "REGISTER.md"

# Rule ids that ARE a shapes/REGISTER.md Table B row but that `_register_rule_ids()`'s regex below cannot
# parse out of that file — it only matches a bare `B-<digits>` id, never a hyphen-suffixed family name.
# Both are declared cardinalities read off the
# SAME itpra_verb annotations that already authorise the registered B-2/B-3 rows (belongs_to_service_domain's
# and supports's own `cardinality` lists in schema/itpra.linkml.yaml), named in that family on purpose.
NEW_UNREGISTERED_RULE_IDS = {"B-3-belongs-to-service-domain", "B-2-supports"}

RULE_ID_PROP_LOCAL = "ruleId"


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


@pytest.fixture(scope="module")
def inputs(config: Config) -> emit.Inputs:
    return emit.load_inputs(config)


@pytest.fixture(scope="module")
def clean_dataset(config: Config, inputs: emit.Inputs) -> ox.Dataset:
    asserted = emit.emit(inputs, config)
    return rules.apply_rules(asserted, config).dataset


@pytest.fixture(scope="module")
def structural_shapes(config: Config) -> ox.Dataset:
    """Only ``structural.ttl`` — never the whole ``shapes/`` directory, so this module's own assertions
    about "structural.ttl's rule ids" are not polluted by the other shape files that share the directory."""
    return shacl.load_shapes(SHAPES_DIR, config=config) if _only_structural(SHAPES_DIR) else _load_only_structural(config)


def _only_structural(shapes_dir: Path) -> bool:
    return shacl.shape_files(shapes_dir) == [STRUCTURAL_SHAPE_FILE]


def _load_only_structural(config: Config) -> ox.Dataset:
    """Copies just `structural.ttl` into an isolated temp dir so `shacl.load_shapes` globs it alone
    (`crossfield.ttl` shares shapes/ with it)."""
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        shutil.copy(STRUCTURAL_SHAPE_FILE, tmp_path / "structural.ttl")
        return shacl.load_shapes(tmp_path, config=config)


# ---------------------------------------------------------------------------------------------------
# Per-fixture: assert_fixture() over every fixtures/structural/*.yaml file


FIXTURE_FILES = fixtures.fixture_files(FIXTURES_DIR)


@pytest.mark.parametrize("fixture_path", FIXTURE_FILES, ids=[p.stem for p in FIXTURE_FILES])
def test_structural_fixture(fixture_path: Path):
    assert FIXTURE_FILES, "fixtures/structural/ must not be empty"
    fixtures.assert_fixture(fixture_path, SHAPES_DIR)


def test_every_rule_id_this_group_owns_has_a_fixture():
    """Every distinct itpra-o:ruleId `structural.ttl` declares has a same-named fixture file. Two of this
    group's ids get their proof a different way than a plain count-1 fixture:

    - ``relates-to-malformed`` never appears as an ``itpra-o:ruleId`` in `structural.ttl` at all (it folds
      into the SAME shape as `target-unresolved` once `relates_to` is pivoted — shapes/REGISTER.md's own
      text for that row); its own proof lives at `fixtures/structural/relates-to-malformed.yaml`, whose
      `rule:` is the synthetic `emit-error` (`emit._verb_edges` raises `EmitError` for a malformed entry
      instead of letting an uncaught `TypeError`/`KeyError` escape).
    - ``B-2-supports`` is causally coupled to B-18 on the same focus (`itpra-o:inDomain` is entirely
      derived from `itpra-o:supports`, so no mutation can zero one without the other on the same Function
      — B-18.yaml's own comment) and so has no isolatable count-1 fixture; it instead has a `count: 0`
      clean-case fixture (`fixtures/structural/B-2-supports.yaml`) proving the shape does not misfire.
    """
    rule_ids_in_shapes = _all_rule_ids(STRUCTURAL_SHAPE_FILE)
    fixture_rule_ids = {p.stem for p in FIXTURE_FILES}
    missing = rule_ids_in_shapes - fixture_rule_ids
    assert missing == set(), f"rule id(s) with no fixture and no documented reason: {missing}"


def _all_rule_ids(shape_file: Path) -> set[str]:
    text = shape_file.read_text(encoding="utf-8")
    return set(re.findall(r'itpra-o:ruleId\s+"([^"]+)"', text))


# ---------------------------------------------------------------------------------------------------
# Whole-file checks: every shape carries ruleId + severity


def test_every_shape_in_structural_ttl_carries_a_rule_id_and_a_severity(config: Config, structural_shapes: ox.Dataset):
    sh_node_shape = ox.NamedNode(shacl.SH + "NodeShape")
    sh_property_shape = ox.NamedNode(shacl.SH + "PropertyShape")
    sh_severity = ox.NamedNode(shacl.SH + "severity")
    rule_id_prop = ox.NamedNode(config.iri.onto_ns + RULE_ID_PROP_LOCAL)
    shapes_prefixes = ox.NamedNode(config.iri.onto_ns + "shapesPrefixes")

    shape_subjects = {
        quad.subject.value
        for quad in structural_shapes.quads_for_predicate(emit.RDF_TYPE)
        if quad.object in (sh_node_shape, sh_property_shape) and quad.subject.value != shapes_prefixes.value
    }
    assert shape_subjects, "structural.ttl declared no shapes at all"

    rule_id_subjects = {quad.subject.value for quad in structural_shapes.quads_for_predicate(rule_id_prop)}
    severity_subjects = {quad.subject.value for quad in structural_shapes.quads_for_predicate(sh_severity)}

    assert shape_subjects - rule_id_subjects == set(), "shape(s) with no itpra-o:ruleId"
    assert shape_subjects - severity_subjects == set(), "shape(s) with no sh:severity"


def test_every_rule_id_in_structural_ttl_has_a_valid_severity(config: Config, structural_shapes: ox.Dataset):
    sh_severity = ox.NamedNode(shacl.SH + "severity")
    valid = {ox.NamedNode(shacl.SH + "Violation"), ox.NamedNode(shacl.SH + "Warning")}
    for quad in structural_shapes.quads_for_predicate(sh_severity):
        assert quad.object in valid, f"{quad.subject}: sh:severity {quad.object} is neither sh:Violation nor sh:Warning"


# ---------------------------------------------------------------------------------------------------
# structural.ttl's rule ids are a subset of shapes/REGISTER.md's own ids (+ the two documented new ones)


def _register_rule_ids(register_md: Path) -> set[str]:
    """Every id in Table A (backtick-quoted, first column) and Table B (bare ``B-<n>``, first column) of
    ``shapes/REGISTER.md``. Parsed from the file directly rather than hand-duplicated here, so a future
    register edit cannot silently desync this test."""
    text = register_md.read_text(encoding="utf-8")
    table_a_ids = set(re.findall(r"^\|\s*`([a-z0-9][a-z0-9-]*)`\s*\|", text, flags=re.MULTILINE))
    table_b_ids = set(re.findall(r"^\|\s*(B-\d+)\s*\|", text, flags=re.MULTILINE))
    return table_a_ids | table_b_ids


def test_structural_rule_ids_are_a_subset_of_the_register_plus_the_two_new_ones(structural_shapes: ox.Dataset):
    register_ids = _register_rule_ids(REGISTER_MD)
    assert register_ids, "could not parse any ids out of shapes/REGISTER.md — parser or file drifted"
    file_ids = _all_rule_ids(STRUCTURAL_SHAPE_FILE)
    unexplained = file_ids - register_ids - NEW_UNREGISTERED_RULE_IDS
    assert unexplained == set(), f"rule id(s) in structural.ttl not in REGISTER.md and not a documented new id: {unexplained}"
    # every structural id the register assigns to this file really is present (shapes/REGISTER.md's own
    # grouping table)
    assigned = {
        "field-missing",
        "id-pattern",
        "target-unresolved",
        "function-derived-from",
        "B-2",
        "B-3",
        "B-12",
        "B-18",
        "B-19",
    }
    assert assigned <= file_ids, f"missing assigned rule id(s): {assigned - file_ids}"


# ---------------------------------------------------------------------------------------------------
# No base IRI literal in structural.ttl (narrower repeat of test_shacl.py's own directory-wide scan)


def test_no_base_iri_literal_in_structural_ttl(config: Config):
    base = config.iri.base
    text = STRUCTURAL_SHAPE_FILE.read_text(encoding="utf-8")
    assert base not in text


# ---------------------------------------------------------------------------------------------------
# Clean data: zero Violations, and exactly the expected (empty) Warning set


def test_clean_data_conforms_with_zero_violations(structural_shapes: ox.Dataset, clean_dataset: ox.Dataset, config: Config):
    report = shacl.validate(clean_dataset, structural_shapes, config=config)
    violations = [f for f in report.findings if f.severity == "Violation"]
    assert violations == [], fixtures._format_findings(violations)


def test_clean_data_warning_set_is_exactly_empty(structural_shapes: ox.Dataset, clean_dataset: ox.Dataset, config: Config):
    """B-5/B-6/B-7 are advisory (sh:Warning, ADR 0042 D3) candidate minimums the register's own text says
    "the data satisfies... but nothing declares" — so clean data is expected to raise NONE of them. If this
    fails, the printed findings name exactly which real records lack a consumed_by/realized_in/depends_on
    edge today (report them — do not silently relax the shape)."""
    report = shacl.validate(clean_dataset, structural_shapes, config=config)
    warnings = [f for f in report.findings if f.severity == "Warning"]
    assert warnings == [], fixtures._format_findings(warnings)

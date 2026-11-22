"""Tests for the `requirements` shape file (``shapes/requirements.ttl``; ``shapes/REGISTER.md``'s grouping
table -> ``requirements`` row) -- registry and traceability shapes over ``req/*``, mixed SHACL Core and
SHACL-SPARQL.

Every test in this module runs ``shapes/requirements.ttl`` in ISOLATION from ``shapes/structural.ttl`` and
``shapes/crossfield.ttl`` (this module's own ``tmp_path`` copy holding only this one shape file): each
hand-written shape file owns a disjoint set of rules (ADR 0042 D2; ``shapes/README.md``'s layout table), and
this keeps every assertion below independent of the other two files' content. ``itpra-onto validate`` (the
CLI, no ``--shapes`` override) is what assembles and runs all of them together against the real corpus -- a
test asserting a specific finding COUNT against all files combined would be coupled to content this module
does not own.

Every test reads the consumer's REAL requirement registries (``[overlay] requirements_glob``), exactly like
``test_shacl.py``/``test_emit.py``/``test_rules.py``: nothing here is ever written to them.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pyoxigraph as ox
import pytest

from itpra_onto import emit, fixtures, rules, shacl
from itpra_onto.config import Config, load_config

pytestmark = pytest.mark.overlay  # needs the consumer's registries

GROUP_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "requirements"
SHAPE_FILE = shacl.SHAPES_DIR / "requirements.ttl"

EXPECTED_RULE_IDS = {
    "req-id-format",
    "req-qa-unresolved",
    "req-statement-missing",
    "req-target-unresolved",
    "B-1",
    "B-4",  # B-4 is also a graph shape (requirements.ttl), not only `generated`
    # (fixtures/requirements/README.md's own account of the gap this closes).
}

_MODULE_STARTED = time.perf_counter()


def _fmt(findings) -> str:
    return "\n".join(f"  {f.severity:9} {f.rule_id!r:22} {f.focus!r:60} {f.message}" for f in findings) or "  (none)"


# ---------------------------------------------------------------------------------------------------
# fixtures shared by this module


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


@pytest.fixture(scope="module")
def shapes_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A tmp dir holding ONLY ``shapes/requirements.ttl`` -- isolates this module from
    ``shapes/structural.ttl``/``shapes/crossfield.ttl`` (module docstring)."""
    directory = tmp_path_factory.mktemp("requirements-shapes")
    shutil.copy(SHAPE_FILE, directory / "requirements.ttl")
    return directory


@pytest.fixture(scope="module")
def inputs(config: Config) -> emit.Inputs:
    return emit.load_inputs(config)


@pytest.fixture(scope="module")
def clean_dataset(config: Config, inputs: emit.Inputs) -> ox.Dataset:
    asserted = emit.emit(inputs, config)
    return rules.apply_rules(asserted, config).dataset


@pytest.fixture(scope="module")
def group_shapes(shapes_dir: Path, config: Config) -> ox.Dataset:
    return shacl.load_shapes(shapes_dir, config=config)


# ---------------------------------------------------------------------------------------------------
# shapes/requirements.ttl exists, has the six expected rule ids, and every shape is fully annotated


def test_shape_file_exists_and_is_not_empty():
    assert SHAPE_FILE.is_file(), f"{SHAPE_FILE} missing"
    assert SHAPE_FILE.read_text(encoding="utf-8").strip()


def test_rule_ids_present_are_exactly_the_six_shape_bearing_ids(config: Config, group_shapes: ox.Dataset):
    rule_id_prop = ox.NamedNode(config.iri.onto_ns + "ruleId")
    rule_ids = {q.object.value for q in group_shapes.quads_for_predicate(rule_id_prop)}
    assert rule_ids == EXPECTED_RULE_IDS


def test_every_shape_in_this_group_carries_a_rule_id_and_a_severity(config: Config, group_shapes: ox.Dataset):
    rule_id_prop = ox.NamedNode(config.iri.onto_ns + "ruleId")
    sh_severity = ox.NamedNode(shacl.SH + "severity")
    sh_node_shape = ox.NamedNode(shacl.SH + "NodeShape")
    sh_property_shape = ox.NamedNode(shacl.SH + "PropertyShape")
    prefixes_resource = config.iri.onto_ns + "shapesPrefixes"

    shape_subjects = {
        q.subject.value
        for q in group_shapes.quads_for_predicate(emit.RDF_TYPE)
        if q.object in (sh_node_shape, sh_property_shape) and q.subject.value != prefixes_resource
    }
    rule_id_subjects = {q.subject.value for q in group_shapes.quads_for_predicate(rule_id_prop)}
    severity_subjects = {q.subject.value for q in group_shapes.quads_for_predicate(sh_severity)}

    assert shape_subjects, "shapes/requirements.ttl declares no sh:NodeShape/sh:PropertyShape"
    assert shape_subjects - rule_id_subjects == set(), "shape(s) missing itpra-o:ruleId"
    assert shape_subjects - severity_subjects == set(), "shape(s) missing sh:severity"


def test_every_sparql_constraint_sets_sh_prefixes(group_shapes: ox.Dataset):
    """Every ``sh:sparql``/``sh:SPARQLConstraint`` node must set ``sh:prefixes`` (shacl.py's module
    docstring, point (c)) -- checked against the LOADED shapes graph (not the raw file text, which would
    also match this module's own doc-comment prose mentioning the convention by name)."""
    sh_sparql_constraint = ox.NamedNode(shacl.SH + "SPARQLConstraint")
    sh_prefixes = ox.NamedNode(shacl.SH + "prefixes")
    constraint_nodes = {q.subject for q in group_shapes.quads_for_predicate(emit.RDF_TYPE) if q.object == sh_sparql_constraint}
    assert constraint_nodes, "no sh:SPARQLConstraint found -- expected req-target-unresolved (x2) and B-1"
    nodes_with_prefixes = {q.subject for q in group_shapes.quads_for_predicate(sh_prefixes)}
    assert constraint_nodes - nodes_with_prefixes == set(), "sh:SPARQLConstraint node(s) missing sh:prefixes"


# ---------------------------------------------------------------------------------------------------
# clean (unmutated) data conforms to every shape in this group


def test_clean_corpus_raises_zero_findings_from_requirements_shapes(
    config: Config, clean_dataset: ox.Dataset, group_shapes: ox.Dataset
):
    report = shacl.validate(clean_dataset, group_shapes, config=config)
    assert report.findings == (), _fmt(report.findings)
    assert report.conforms


def test_clean_corpus_raises_zero_b1_findings_across_all_166_nfrs(
    config: Config, clean_dataset: ox.Dataset, group_shapes: ox.Dataset
):
    """B-1 (NFR id embeds its qa) is a genuine DATA check, not a structural one -- verified explicitly against
    the full 166-NFR corpus, with any firing reported as a data finding rather than silently weakened. None
    do, confirmed both here and independently in Python (shapes/requirements.ttl's own header comment)."""
    report = shacl.validate(clean_dataset, group_shapes, config=config)
    b1_findings = [f for f in report.findings if f.rule_id == "B-1"]
    assert b1_findings == [], (
        "B-1 fired on live data -- this is a DATA FINDING, not something to silence:\n"
        + _fmt(b1_findings)
    )


# ---------------------------------------------------------------------------------------------------
# positive controls (shapes/REGISTER.md; the consumer's registry counts at the time of writing)


def test_positive_control_572_requirements_typed(config: Config, clean_dataset: ox.Dataset):
    requirement_class = ox.NamedNode(config.iri.id_ns + "REQUIREMENT")
    count = sum(1 for q in clean_dataset if q.predicate == emit.RDF_TYPE and q.object == requirement_class)
    assert count == 572


def test_positive_control_406_fr_and_166_nfr(config: Config, clean_dataset: ox.Dataset):
    fr_class = ox.NamedNode(config.iri.id_ns + "FR")
    nfr_class = ox.NamedNode(config.iri.id_ns + "NFR")
    fr_count = sum(1 for q in clean_dataset if q.predicate == emit.RDF_TYPE and q.object == fr_class)
    nfr_count = sum(1 for q in clean_dataset if q.predicate == emit.RDF_TYPE and q.object == nfr_class)
    assert fr_count == 406
    assert nfr_count == 166


def test_positive_control_166_nfrs_have_categorized_as(config: Config, clean_dataset: ox.Dataset):
    predicate = ox.NamedNode(config.iri.onto_ns + "categorizedAs")
    count = sum(1 for q in clean_dataset if q.predicate == predicate)
    assert count == 166


# ---------------------------------------------------------------------------------------------------
# fixtures: one deliberately broken record per rule id (fixtures/requirements/*.yaml)


FIXTURE_FILES = fixtures.fixture_files(GROUP_DIR)


def test_one_fixture_file_per_shape_bearing_rule_id():
    rule_ids = set()
    for path in FIXTURE_FILES:
        rule_ids.add(fixtures.load_fixture(path).rule)
    assert rule_ids == EXPECTED_RULE_IDS


@pytest.mark.parametrize("fixture_path", FIXTURE_FILES, ids=lambda p: p.stem)
def test_fixture(fixture_path: Path, shapes_dir: Path):
    fixtures.assert_fixture(fixture_path, shapes_dir)


# ---------------------------------------------------------------------------------------------------
# timing (run with -s to see the printed lines)


def test_zz_requirements_shapes_validate_timing(config: Config, clean_dataset: ox.Dataset, group_shapes: ox.Dataset):
    total_triples = sum(1 for _ in clean_dataset)
    started = time.perf_counter()
    report = shacl.validate(clean_dataset, group_shapes, config=config)
    elapsed = time.perf_counter() - started
    print(
        f"\nshacl.validate() over {total_triples} triples (shapes/requirements.ttl only): "
        f"{elapsed:.3f}s, conforms={report.conforms}"
    )
    assert elapsed < 60, f"validate() took {elapsed:.1f}s over {total_triples} triples -- investigate"


def test_zzz_requirements_suite_timing():
    elapsed = time.perf_counter() - _MODULE_STARTED
    print(f"\ntest_shapes_requirements.py module wall time so far: {elapsed:.3f}s")

"""The ``crossfield`` shape file (SHACL-SPARQL): ``shapes/crossfield.ttl`` + ``fixtures/crossfield/``.

Rules (``shapes/REGISTER.md`` Tables A and B, severities per Table C): **replaced-by-unresolved** (a retired
record's ``dcterms:isReplacedBy`` names another record — ADR 0048), **B-8** (an alias equal to its own
subject's prefLabel, case-insensitively — ADR 0007), **B-8-pref-label-unique** (at most one prefLabel per
language tag per subject — SKOS S14), **B-13** (every ``decidedIn``/``amendedBy``/``extendedBy`` object is an
``ADR-NNNN`` node in the id namespace). B-9 is "no rule, by design" and is asserted absent.

B-13 and B-8-pref-label-unique are defence in depth: no authoring-YAML mutation can make the emitter produce
the defect they catch (``source`` is parsed by a strict grammar and zero-padded; ``term`` is a scalar), so they
are proven here by injecting bad quads straight into an emitted dataset, bypassing the emitter. Each also
carries a ``count: 0`` clean-case fixture (``fixtures/crossfield/B-13.yaml``,
``fixtures/crossfield/B-8-pref-label-unique.yaml`` — fixtures.py's ``count: 0`` grammar) documenting the
nearest an authoring mutation can get without tripping the rule. B-13's own emit-time-guard fixture — a
``source`` value the grammar refuses outright — lives at ``fixtures/crossfield/B-13-emit-guard.yaml``
(its ``rule`` is the synthetic ``emit-error``, never ``B-13`` itself).

Every test reads the REAL input files; nothing is written outside pytest's ``tmp_path``.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pyoxigraph as ox
import pytest
import rdflib

from itpra_onto import emit, fixtures, rules, shacl
from itpra_onto.config import Config, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHAPES_DIR = shacl.SHAPES_DIR
CROSSFIELD_TTL = SHAPES_DIR / "crossfield.ttl"
FIXTURES_DIR = fixtures.FIXTURES_DIR / "crossfield"
FIXTURE_FILES = fixtures.fixture_files(FIXTURES_DIR)

RULE_IDS = {"replaced-by-unresolved", "B-8", "B-8-pref-label-unique", "B-13"}
SH = rdflib.Namespace(shacl.SH)


# ---------------------------------------------------------------------------------------------------
# module fixtures


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


@pytest.fixture(scope="module")
def clean_dataset(config: Config) -> ox.Dataset:
    return rules.apply_rules(emit.emit(emit.load_inputs(config), config), config).dataset


@pytest.fixture(scope="module")
def crossfield_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A shapes directory holding ONLY crossfield.ttl, so this file's findings are isolated from the
    other shape files that share shapes/."""
    directory = tmp_path_factory.mktemp("crossfield-shapes")
    shutil.copy(CROSSFIELD_TTL, directory / CROSSFIELD_TTL.name)
    return directory


@pytest.fixture(scope="module")
def crossfield_shapes(config: Config, crossfield_dir: Path) -> ox.Dataset:
    return shacl.load_shapes(crossfield_dir, config=config)


@pytest.fixture(scope="module")
def shapes_graph(config: Config, crossfield_shapes: ox.Dataset) -> rdflib.Graph:
    graph = rdflib.Graph()
    graph.parse(data=shacl._shapes_turtle_bytes(crossfield_shapes, config), format="turtle")
    return graph


def _copy(dataset: ox.Dataset) -> ox.Dataset:
    out = ox.Dataset()
    for quad in dataset:
        out.add(quad)
    return out


def _findings(report: shacl.ValidationReport, rule_id: str) -> list[shacl.Finding]:
    return [f for f in report.findings if f.rule_id == rule_id]


# ---------------------------------------------------------------------------------------------------
# fixtures/crossfield/*.yaml -> assert_fixture (against the REAL shapes/ dir: integration with every shape file)


def test_fixture_directory_is_populated():
    assert {p.name for p in FIXTURE_FILES} == {
        "B-8.yaml",
        "B-8-pref-label-unique.yaml",
        "B-13.yaml",
        "B-13-emit-guard.yaml",
        "replaced-by-unresolved.yaml",
    }


@pytest.mark.parametrize("fixture_path", FIXTURE_FILES, ids=[p.stem for p in FIXTURE_FILES])
def test_fixture(fixture_path: Path):
    fixtures.assert_fixture(fixture_path, SHAPES_DIR)


def test_b8_fixture_message_names_the_offending_alias(config: Config):
    report, _expected = fixtures.run_fixture(FIXTURES_DIR / "B-8.yaml", SHAPES_DIR, config=config)
    [finding] = _findings(report, "B-8")
    assert "platform configuration source of truth" in finding.message
    assert finding.path == emit.SKOS + "altLabel"


def test_replaced_by_unresolved_fires_on_a_record_naming_itself(config: Config, crossfield_dir: Path):
    """The self-reference arm (the fixture proves the dangling arm): a retired record whose ``replaced_by`` is
    its own id resolves, but names no OTHER record."""
    fixture = fixtures.load_fixture(FIXTURES_DIR / "replaced-by-unresolved.yaml")
    inputs = fixtures.apply_fixture(emit.load_inputs(config), fixture)
    terms = tuple(
        emit.TermRecord({**t.record, "replaced_by": fixture.focus}, t.file) if t.record.get("id") == fixture.focus else t
        for t in inputs.terms
    )
    dataset = rules.apply_rules(emit.emit(emit.Inputs(terms, inputs.ontology_version), config), config).dataset
    report = shacl.validate(dataset, shacl.load_shapes(crossfield_dir, config=config), config=config)
    [finding] = report.findings
    assert finding.rule_id == "replaced-by-unresolved" and finding.severity == "Violation"
    assert finding.focus == config.iri.id_ns + fixture.focus


# ---------------------------------------------------------------------------------------------------
# clean data


def test_clean_corpus_raises_zero_crossfield_findings(config: Config, clean_dataset: ox.Dataset, crossfield_shapes: ox.Dataset):
    report = shacl.validate(clean_dataset, crossfield_shapes, config=config)
    assert report.findings == (), "\n".join(f"{f.rule_id} {f.focus} {f.message}" for f in report.findings)
    assert report.conforms


def test_b13_positive_control_real_corpus_has_adr_nodes_and_zero_findings(
    config: Config, clean_dataset: ox.Dataset, crossfield_shapes: ox.Dataset
):
    """The shape is not vacuously silent: the real corpus carries decidedIn edges to dozens of distinct ADR
    nodes (over thirty of the ontology's own records), every one of which passes."""
    decided_in = ox.NamedNode(config.iri.onto_ns + emit.DECIDED_IN)
    adr_nodes = {quad.object.value for quad in clean_dataset.quads_for_predicate(decided_in)}
    print(f"\ndistinct decidedIn ADR nodes in the real corpus: {len(adr_nodes)}")
    assert len(adr_nodes) >= 30
    report = shacl.validate(clean_dataset, crossfield_shapes, config=config)
    assert _findings(report, "B-13") == []


def test_b13_well_formed_unpadded_source_is_padded_by_the_emitter_and_passes(config: Config, crossfield_dir: Path):
    """The real ``B-13.yaml`` clean-case fixture (``count: 0``): `source: "ADR 12"` is legal grammar; the
    emitter zero-pads it to ADR-0012, and B-13 raises nothing. Loads the actual committed fixture file
    (fixtures.py's ``count: 0`` support) rather than constructing an
    equivalent ``Fixture`` by hand, then additionally inspects the intermediate emitted quad — beyond what
    ``assert_fixture()`` itself checks — to confirm the padding actually happened, not merely that no
    finding fired."""
    fixture = fixtures.load_fixture(FIXTURES_DIR / "B-13.yaml")
    assert fixture.count == 0
    inputs = emit.load_inputs(config)
    dataset = emit.emit(fixtures.apply_fixture(inputs, fixture), config)
    focus = ox.NamedNode(config.iri.id_ns + "CAP-ITO-FND-1")
    decided_in = ox.NamedNode(config.iri.onto_ns + emit.DECIDED_IN)
    objects = {q.object.value for q in dataset.quads_for_subject(focus) if q.predicate == decided_in}
    assert objects == {config.iri.id_ns + "ADR-0012"}
    dataset = rules.apply_rules(dataset, config).dataset
    report = shacl.validate(dataset, shacl.load_shapes(crossfield_dir, config=config), config=config)
    assert _findings(report, "B-13") == []


# ---------------------------------------------------------------------------------------------------
# direct injection (bypassing the emitter) -- the defence-in-depth rules


def test_b13_fires_on_injected_malformed_adr_nodes(config: Config, clean_dataset: ox.Dataset, crossfield_shapes: ox.Dataset):
    t1 = ox.NamedNode(config.iri.graph_ns + "t1")
    focus = ox.NamedNode(config.iri.id_ns + "CAP-ITO-FND-1")
    decided_in = ox.NamedNode(config.iri.onto_ns + emit.DECIDED_IN)
    amended_by = ox.NamedNode(config.iri.onto_ns + emit.AMENDED_BY)
    extended_by = ox.NamedNode(config.iri.onto_ns + emit.EXTENDED_BY)
    bad = {
        # (predicate, object) -> why it is bad
        (decided_in, ox.NamedNode(config.iri.id_ns + "ADR-12")): "three digits",
        (decided_in, ox.Literal("ADR-0001")): "a literal, not an IRI",
        (amended_by, ox.NamedNode("https://elsewhere.example/ADR-0001")): "outside the id namespace",
        (extended_by, ox.NamedNode(config.iri.id_ns + "ADR-00012")): "five digits",
    }
    dataset = _copy(clean_dataset)
    for predicate, obj in bad:
        dataset.add(ox.Quad(focus, predicate, obj, t1))

    report = shacl.validate(dataset, crossfield_shapes, config=config)
    found = _findings(report, "B-13")
    assert len(found) == len(bad), "\n".join(f.message for f in found)
    assert all(f.severity == "Violation" and f.focus == focus.value for f in found)
    for (predicate, obj), _why in bad.items():
        assert any(f.path == predicate.value and obj.value in f.message for f in found), (predicate, obj)
    # nothing else fired: the clean ADR-0001 decidedIn edge CAP-ITO-FND-1 already carries still passes
    assert {f.rule_id for f in report.findings} == {"B-13"}


def test_b13_amended_by_without_its_decided_in_twin_is_still_targeted(config: Config, clean_dataset: ox.Dataset, crossfield_shapes: ox.Dataset):
    """A subject with ONLY an amendedBy edge (an emitter regression dropping the decidedIn twin) is still a
    B-13 focus node: the shape targets all three properties' subjects, not decidedIn's alone."""
    t1 = ox.NamedNode(config.iri.graph_ns + "t1")
    focus = ox.NamedNode(config.iri.id_ns + "CAP-FIXTURE-AMENDED-ONLY")
    dataset = _copy(clean_dataset)
    dataset.add(ox.Quad(focus, ox.NamedNode(config.iri.onto_ns + emit.AMENDED_BY), ox.NamedNode(config.iri.id_ns + "ADR-7"), t1))
    report = shacl.validate(dataset, crossfield_shapes, config=config)
    found = _findings(report, "B-13")
    assert [f.focus for f in found] == [focus.value]


def test_pref_label_unique_fires_per_surplus_label_in_one_language(config: Config, clean_dataset: ox.Dataset, crossfield_shapes: ox.Dataset):
    t1 = ox.NamedNode(config.iri.graph_ns + "t1")
    focus = ox.NamedNode(config.iri.id_ns + "CAP-ITO-FND-1")
    pref = ox.NamedNode(emit.SKOS + "prefLabel")
    dataset = _copy(clean_dataset)
    dataset.add(ox.Quad(focus, pref, ox.Literal("Second preferred label", language="en"), t1))
    report = shacl.validate(dataset, crossfield_shapes, config=config)
    found = _findings(report, "B-8-pref-label-unique")
    assert len(found) == 2  # one per label value in the colliding pair
    assert all(f.focus == focus.value and f.severity == "Violation" and f.path == pref.value for f in found)
    assert all("Second preferred label" in f.message and "Platform Configuration Source of Truth" in f.message for f in found)
    assert {f.rule_id for f in report.findings} == {"B-8-pref-label-unique"}


def test_pref_label_unique_allows_one_label_per_language(config: Config, clean_dataset: ox.Dataset, crossfield_shapes: ox.Dataset):
    t1 = ox.NamedNode(config.iri.graph_ns + "t1")
    focus = ox.NamedNode(config.iri.id_ns + "CAP-ITO-FND-1")
    dataset = _copy(clean_dataset)
    dataset.add(ox.Quad(focus, ox.NamedNode(emit.SKOS + "prefLabel"), ox.Literal("Source de vérité", language="fr"), t1))
    report = shacl.validate(dataset, crossfield_shapes, config=config)
    assert report.findings == ()


# ---------------------------------------------------------------------------------------------------
# shape-file conventions


def _rule_bearing_shapes(graph: rdflib.Graph, config: Config) -> set[rdflib.term.Node]:
    rule_id = rdflib.URIRef(config.iri.onto_ns + shacl.RULE_ID_LOCAL)
    return set(graph.subjects(rule_id, None))


def test_rule_ids_are_exactly_the_crossfield_group(config: Config, shapes_graph: rdflib.Graph):
    rule_id = rdflib.URIRef(config.iri.onto_ns + shacl.RULE_ID_LOCAL)
    ids = {str(o) for o in shapes_graph.objects(None, rule_id)}
    assert ids == RULE_IDS
    assert "B-9" not in ids  # REGISTER.md: "no rule, by design"


def test_every_shape_is_named_and_carries_rule_id_and_severity(config: Config, shapes_graph: rdflib.Graph):
    prefixes_node = rdflib.URIRef(config.iri.onto_ns + shacl.PREFIXES_RESOURCE_LOCAL)
    shapes = {
        s
        for cls in (SH.NodeShape, SH.PropertyShape)
        for s in shapes_graph.subjects(rdflib.RDF.type, cls)
        if s != prefixes_node
    }
    assert shapes == _rule_bearing_shapes(shapes_graph, config)
    for shape in shapes:
        assert isinstance(shape, rdflib.URIRef), shape
        assert shapes_graph.value(shape, SH.severity) == SH.Violation, shape  # Table C: every crossfield rule is a Violation


def test_every_sparql_constraint_uses_the_injected_prefixes_and_names_the_value(config: Config, shapes_graph: rdflib.Graph):
    prefixes_node = rdflib.URIRef(config.iri.onto_ns + shacl.PREFIXES_RESOURCE_LOCAL)
    constraints = list(shapes_graph.objects(None, SH.sparql))
    assert len(constraints) == len(RULE_IDS)
    for constraint in constraints:
        assert shapes_graph.value(constraint, SH.prefixes) == prefixes_node
        message = str(shapes_graph.value(constraint, SH.message))
        select = str(shapes_graph.value(constraint, SH.select))
        assert "{?value}" in message and "{$this}" in message, message
        assert "$this" in select and "?value" in select
        assert "VALUES" not in select.upper().replace("?VALUE", "")  # SHACL-SPARQL forbids VALUES
        assert "GRAPH" not in select.upper()  # validate() flattens the selected graphs into one


def test_no_prefix_declarations_or_base_iri_in_the_shape_file(config: Config):
    text = CROSSFIELD_TTL.read_text(encoding="utf-8")
    code_lines = [line.strip() for line in text.splitlines() if not line.strip().startswith("#")]
    assert not any(line.lower().startswith(("@prefix", "prefix ")) for line in code_lines)
    assert config.iri.base not in text


# ---------------------------------------------------------------------------------------------------
# timing (-s to see)


def test_zz_crossfield_validation_timing(config: Config, clean_dataset: ox.Dataset, crossfield_shapes: ox.Dataset):
    concepts = {q.subject for q in clean_dataset.quads_for_predicate(emit.RDF_TYPE) if q.object == emit.SKOS_CONCEPT}
    started = time.perf_counter()
    report = shacl.validate(clean_dataset, crossfield_shapes, config=config)
    elapsed = time.perf_counter() - started
    print(f"\ncrossfield.ttl over the real corpus: {len(concepts)} skos:Concept focus nodes, {elapsed:.3f}s, conforms={report.conforms}")
    assert elapsed < 60

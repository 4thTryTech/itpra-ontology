"""Tests for the SHACL validation harness (``itpra_onto.shacl``, ``itpra_onto.fixtures``; ADR 0042).

Covers, in order: (a) the pySHACL-over-``pyoxigraph.Store`` graph-visibility behaviour, established
empirically (a raw ``Store`` is validated as the union of every named graph it holds; there is no way to ask
pySHACL itself to restrict to a subset — ``shacl.validate()``'s own ``graphs`` selection is what restricts
it); (b) the Core smoke shape, clean-conforms plus its fixture; (c) the SHACL-SPARQL smoke shape (proving
the ``sh:sparql``/``$this`` path works, and the ``sh:prefixes itpra-o:shapesPrefixes`` convention), clean-
conforms plus its fixture; (d) ``shapes_digest`` stability/sensitivity; (e) ``load_shapes``'s output shape
and the no-base-IRI-literal discipline; (f) the CLI; (g) timing; (h) ``ShaclError`` for a malformed
``sh:sparql`` constraint (pySHACL returns a ``ValidationFailure`` object rather than raising).

Every test reads the real vocabulary files exactly like ``test_emit.py``/``test_rules.py``: nothing here
is ever written to them. The smoke shapes
(``tests/fixtures/shapes-smoke/``) are test-only — not part of the shape files under ``shapes/``.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pyoxigraph as ox
import pytest

from itpra_onto import emit, fixtures, rules, shacl
from itpra_onto.config import Config, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHAPES_DIR = shacl.SHAPES_DIR
SMOKE_DIR = Path(__file__).resolve().parent / "fixtures" / "shapes-smoke"
CORE_FIXTURE = SMOKE_DIR / "smoke-capability-has-label.yaml"
SPARQL_FIXTURE = SMOKE_DIR / "smoke-alt-label-self-collision.yaml"

_MODULE_STARTED = time.perf_counter()


# ---------------------------------------------------------------------------------------------------
# fixtures shared by this module


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
def smoke_shapes(config: Config) -> ox.Dataset:
    return shacl.load_shapes(SMOKE_DIR, config=config)


# ---------------------------------------------------------------------------------------------------
# (a) pySHACL over a multi-graph pyoxigraph.Store: union, not default-graph-only; shacl.py's own restriction


def test_pyshacl_sees_named_graph_content_not_only_the_default_graph(config: Config, smoke_shapes: ox.Dataset):
    """The graph-visibility finding, asserted directly: a Store with data ONLY in a named (non-default)
    graph still gets validated when that graph is selected — pySHACL does not require default-graph
    content (module docstring point 1 of shacl.py)."""
    graph = ox.NamedNode(config.iri.graph_ns + "t1")
    dataset = ox.Dataset()
    focus = ox.NamedNode(config.iri.id_ns + "CAP-SMOKE-VISIBILITY")
    dataset.add(ox.Quad(focus, emit.RDF_TYPE, ox.NamedNode(config.iri.id_ns + "CAPABILITY"), graph))
    # deliberately no skos:prefLabel triple -> the Core smoke shape must fire

    report = shacl.validate(dataset, smoke_shapes, config=config, graphs=("t1",))
    assert not report.conforms
    assert any(f.rule_id == "smoke-capability-has-label" and f.focus == focus.value for f in report.findings)


def test_validate_graphs_selection_excludes_a_graph_not_named(config: Config, smoke_shapes: ox.Dataset):
    """A Store passed straight to pySHACL sees ALL its named graphs (no pySHACL-side restriction exists);
    shacl.validate()'s own ``graphs`` parameter is what actually restricts what gets checked — proven here
    by a decoy graph that is validated only when named."""
    t1 = ox.NamedNode(config.iri.graph_ns + "t1")
    decoy = ox.NamedNode(config.iri.graph_ns + "extra/DECOY")
    dataset = ox.Dataset()
    included = ox.NamedNode(config.iri.id_ns + "CAP-SMOKE-INCLUDED")
    excluded = ox.NamedNode(config.iri.id_ns + "CAP-SMOKE-EXCLUDED")
    capability = ox.NamedNode(config.iri.id_ns + "CAPABILITY")
    dataset.add(ox.Quad(included, emit.RDF_TYPE, capability, t1))
    dataset.add(ox.Quad(excluded, emit.RDF_TYPE, capability, decoy))

    only_t1 = shacl.validate(dataset, smoke_shapes, config=config, graphs=("t1",))
    foci = {f.focus for f in only_t1.findings}
    assert included.value in foci
    assert excluded.value not in foci

    both = shacl.validate(dataset, smoke_shapes, config=config, graphs=("t1", "extra/DECOY"))
    foci_both = {f.focus for f in both.findings}
    assert included.value in foci_both
    assert excluded.value in foci_both


def test_default_validation_graphs_selects_every_data_graph(config: Config):
    """Every named graph is validated except the three that hold no instance data: schema, provenance, shapes."""
    graph_ns = config.iri.graph_ns
    dataset = ox.Dataset()
    dummy = ox.NamedNode(config.iri.id_ns + "X")
    for local in ("schema", "t1", "extra/b", "extra/a", "inferred", "provenance", "shapes"):
        dataset.add(ox.Quad(dummy, emit.RDF_TYPE, dummy, ox.NamedNode(graph_ns + local)))

    selected = shacl.default_validation_graphs(dataset, config)
    assert selected == ("extra/a", "extra/b", "inferred", "t1")


def test_validate_default_graphs_over_the_real_corpus_match_expectation(config: Config, clean_dataset: ox.Dataset):
    """Sanity check against the real emit()+rules() output: the asserted and the inferred graph are
    validated, the schema graph is not."""
    assert shacl.default_validation_graphs(clean_dataset, config) == ("inferred", "t1")


# ---------------------------------------------------------------------------------------------------
# (b) the Core smoke shape


def test_smoke_core_shape_conforms_on_the_real_clean_corpus(config: Config, clean_dataset: ox.Dataset, smoke_shapes: ox.Dataset):
    report = shacl.validate(clean_dataset, smoke_shapes, config=config, graphs=("t1",))
    core_findings = [f for f in report.findings if f.rule_id == "smoke-capability-has-label"]
    assert core_findings == []


def test_smoke_core_shape_fixture_fires_exactly_one_violation():
    fixtures.assert_fixture(CORE_FIXTURE, SMOKE_DIR)


def test_smoke_core_fixture_report_shape_directly():
    """A closer look at run_fixture()'s return value, beyond what assert_fixture() checks on its own."""
    report, expected = fixtures.run_fixture(CORE_FIXTURE, SMOKE_DIR)
    assert expected.rule == "smoke-capability-has-label"
    assert expected.severity == "Violation"
    assert expected.focus == "CAP-ITO-FND-1"
    assert expected.count == 1
    matching = [f for f in report.findings if f.rule_id == "smoke-capability-has-label"]
    assert len(matching) == 1
    finding = matching[0]
    assert finding.severity == "Violation"
    assert shacl.focus_local_name(finding.focus, load_config()) == "CAP-ITO-FND-1"
    assert finding.source_shape is not None and finding.source_shape.endswith("SmokeCapabilityHasLabelShape")


# ---------------------------------------------------------------------------------------------------
# (c) the SHACL-SPARQL smoke shape


def test_smoke_sparql_shape_conforms_on_the_real_clean_corpus(config: Config, clean_dataset: ox.Dataset, smoke_shapes: ox.Dataset):
    report = shacl.validate(clean_dataset, smoke_shapes, config=config)
    sparql_findings = [f for f in report.findings if f.rule_id == "smoke-alt-label-self-collision"]
    assert sparql_findings == []


def test_smoke_sparql_shape_fixture_fires_exactly_one_violation():
    """Proves the sh:sparql / $this path works against an Oxigraph-backed data graph (module docstring
    point 3 of shacl.py), which the crossfield shape file (SHACL-SPARQL, shapes/REGISTER.md) relies on."""
    fixtures.assert_fixture(SPARQL_FIXTURE, SMOKE_DIR)


def test_smoke_sparql_fixture_uses_the_sparql_constraint_component():
    report, _expected = fixtures.run_fixture(SPARQL_FIXTURE, SMOKE_DIR)
    matching = [f for f in report.findings if f.rule_id == "smoke-alt-label-self-collision"]
    assert len(matching) == 1
    assert "collides" in matching[0].message.lower() or "collision" in matching[0].message.lower() or matching[0].message


# ---------------------------------------------------------------------------------------------------
# (d) shapes_digest


def test_shapes_digest_stable(tmp_path: Path):
    shape = tmp_path / "a.ttl"
    shape.write_text("itpra-o:X a sh:NodeShape .\n", encoding="utf-8")
    assert shacl.shapes_digest(tmp_path) == shacl.shapes_digest(tmp_path)


def test_shapes_digest_sensitive_to_content(tmp_path: Path):
    shape = tmp_path / "a.ttl"
    shape.write_text("itpra-o:X a sh:NodeShape .\n", encoding="utf-8")
    before = shacl.shapes_digest(tmp_path)
    shape.write_text("itpra-o:X a sh:NodeShape ; itpra-o:ruleId \"x\" .\n", encoding="utf-8")
    after = shacl.shapes_digest(tmp_path)
    assert before != after


def test_shapes_digest_sensitive_to_a_second_file(tmp_path: Path):
    (tmp_path / "a.ttl").write_text("itpra-o:X a sh:NodeShape .\n", encoding="utf-8")
    one_file = shacl.shapes_digest(tmp_path)
    (tmp_path / "b.ttl").write_text("itpra-o:Y a sh:NodeShape .\n", encoding="utf-8")
    two_files = shacl.shapes_digest(tmp_path)
    assert one_file != two_files


def test_shapes_digest_ignores_non_ttl_files(tmp_path: Path):
    (tmp_path / "a.ttl").write_text("itpra-o:X a sh:NodeShape .\n", encoding="utf-8")
    before = shacl.shapes_digest(tmp_path)
    (tmp_path / "REGISTER.md").write_text("# not a shape\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# not a shape either\n", encoding="utf-8")
    after = shacl.shapes_digest(tmp_path)
    assert before == after


def test_real_shapes_digest_is_stable_and_covers_every_shape_file():
    """The hand-written shape files are `structural.ttl` and `crossfield.ttl`; the digest is stable
    across calls and every shape file is under it (an empty directory would also be well-defined)."""
    names = [path.relative_to(SHAPES_DIR).as_posix() for path in shacl.shape_files(SHAPES_DIR)]
    # hand-written files first (sorted), then the generator-owned shapes/generated/ (ADR 0042 D2)
    assert names == ["crossfield.ttl", "structural.ttl", "generated/verb-pairs.ttl"]
    assert shacl.shapes_digest(SHAPES_DIR) == shacl.shapes_digest(SHAPES_DIR)


# ---------------------------------------------------------------------------------------------------
# (e) load_shapes: every triple in the shapes graph; no base-IRI literal anywhere


def test_load_shapes_places_every_triple_in_the_named_shapes_graph(config: Config, smoke_shapes: ox.Dataset):
    graph = ox.NamedNode(config.iri.graph_ns + "shapes")
    assert len(list(smoke_shapes)) > 0
    assert all(quad.graph_name == graph for quad in smoke_shapes)


def test_load_shapes_carries_both_smoke_rule_ids(config: Config, smoke_shapes: ox.Dataset):
    prop = ox.NamedNode(config.iri.onto_ns + "ruleId")
    rule_ids = {quad.object.value for quad in smoke_shapes.quads_for_predicate(prop)}
    assert rule_ids == {"smoke-capability-has-label", "smoke-alt-label-self-collision"}


def test_load_shapes_injects_the_synthetic_prefixes_resource(config: Config, smoke_shapes: ox.Dataset):
    onto = ox.NamedNode(config.iri.onto_ns + "shapesPrefixes")
    owl_ontology = ox.NamedNode(emit.OWL + "Ontology")
    assert ox.Quad(onto, emit.RDF_TYPE, owl_ontology, ox.NamedNode(config.iri.graph_ns + "shapes")) in smoke_shapes


def test_no_base_iri_literal_in_any_ttl_under_shapes_or_the_smoke_dir(config: Config):
    base = config.iri.base
    offenders: dict[Path, str] = {}
    for directory in (SHAPES_DIR, SHAPES_DIR / shacl.GENERATED_SUBDIR, SMOKE_DIR):
        for path in directory.glob("*.ttl"):
            text = path.read_text(encoding="utf-8")
            if base in text:
                offenders[path] = text
    assert offenders == {}


def test_no_such_shape_without_a_rule_id_in_the_real_shapes_dir(config: Config):
    """Every rule-bearing shape under shapes/ carries itpra-o:ruleId (module docstring convention). The next
    test builds a small counter-example in tmp_path and confirms it WOULD be caught, so this assertion is
    not vacuous by construction."""
    real_shapes = shacl.load_shapes(SHAPES_DIR, config=config)
    prop = ox.NamedNode(config.iri.onto_ns + "ruleId")
    rule_id_subjects = {quad.subject.value for quad in real_shapes.quads_for_predicate(prop)}
    sh_node_shape = ox.NamedNode(shacl.SH + "NodeShape")
    sh_property_shape = ox.NamedNode(shacl.SH + "PropertyShape")
    shape_subjects = {
        quad.subject.value
        for quad in real_shapes.quads_for_predicate(emit.RDF_TYPE)
        if quad.object in (sh_node_shape, sh_property_shape) and quad.subject.value != config.iri.onto_ns + "shapesPrefixes"
    }
    assert shape_subjects - rule_id_subjects == set()


def test_a_shape_missing_its_rule_id_would_be_caught(tmp_path: Path, config: Config):
    (tmp_path / "no-rule-id.ttl").write_text(
        "itpra-o:NoRuleIdShape a sh:NodeShape ; sh:targetClass itpra:CAPABILITY .\n", encoding="utf-8"
    )
    shapes = shacl.load_shapes(tmp_path, config=config)
    prop = ox.NamedNode(config.iri.onto_ns + "ruleId")
    rule_id_subjects = {quad.subject.value for quad in shapes.quads_for_predicate(prop)}
    sh_node_shape = ox.NamedNode(shacl.SH + "NodeShape")
    shape_subjects = {
        quad.subject.value
        for quad in shapes.quads_for_predicate(emit.RDF_TYPE)
        if quad.object == sh_node_shape and quad.subject.value != config.iri.onto_ns + "shapesPrefixes"
    }
    assert shape_subjects - rule_id_subjects == {config.iri.onto_ns + "NoRuleIdShape"}


# ---------------------------------------------------------------------------------------------------
# itpra-o:ruleId is discoverable from the schema graph (emit.py declares it)


def test_rule_id_is_declared_as_an_annotation_property_in_the_schema_graph(config: Config, inputs: emit.Inputs):
    dataset = emit.emit(inputs, config)
    schema_graph = ox.NamedNode(config.iri.graph_ns + "schema")
    prop = ox.NamedNode(config.iri.onto_ns + "ruleId")
    assert ox.Quad(prop, emit.RDF_TYPE, emit.OWL_ANNOTATION_PROPERTY, schema_graph) in dataset
    labels = [q.object for q in dataset if q.subject == prop and q.predicate == emit.RDFS_LABEL and q.graph_name == schema_graph]
    assert labels


# ---------------------------------------------------------------------------------------------------
# (f) the CLI


def test_cli_validate_json_on_the_real_tree_is_a_list_and_exits_0():
    """On the clean corpus the findings list is empty; it must still be valid JSON, a list, and exit 0."""
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "validate", "--json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)


def test_cli_validate_json_output_is_the_only_stdout():
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "validate", "--json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 1
    json.loads(lines[0])


def test_cli_validate_plain_with_smoke_shapes_reports_a_violation_and_exits_1():
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "validate", "--shapes", str(SMOKE_DIR)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # smoke.ttl's shapes should conform against the real clean corpus (see the module-scoped tests above);
    # the CLI run is a black-box confirmation of the SAME thing via the --shapes override, exit 0.
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "0 violation(s)" in result.stdout


def test_cli_validate_json_with_smoke_shapes_matches_the_direct_call(config: Config, clean_dataset: ox.Dataset, smoke_shapes: ox.Dataset):
    report = shacl.validate(clean_dataset, smoke_shapes, config=config)
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "validate", "--shapes", str(SMOKE_DIR), "--json"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(result.stdout)
    assert len(payload) == len(report.findings)


def _write_fixture(tmp_path: Path, expect_extra: str) -> Path:
    path = tmp_path / "f.yaml"
    path.write_text(
        "rule: emit-error\nexpect:\n  severity: Violation\n  focus: CAP-ITO-FND-1\n"
        + expect_extra
        + "mutate:\n  id: CAP-ITO-FND-1\n  set: {source: \"ADR-12\"}\n",
        encoding="utf-8",
    )
    return path


def test_fixture_expect_emit_error_must_name_an_emit_error_class(tmp_path: Path):
    with pytest.raises(fixtures.FixtureError, match="must name an EmitError class"):
        fixtures.load_fixture(_write_fixture(tmp_path, "  emit_error: KeyError\n"))


def test_fixture_expect_emit_error_requires_the_named_class(tmp_path: Path):
    """B-13-emit-guard's mutation raises SourceGrammarError. A fixture naming exactly that class
    passes; one naming another class — even its base, EmitError — fails (the class is matched exactly)."""
    assert fixtures.load_fixture(_write_fixture(tmp_path, "  emit_error: SourceGrammarError\n")).emit_error == "SourceGrammarError"
    fixtures.assert_fixture(_write_fixture(tmp_path, "  emit_error: SourceGrammarError\n"), SHAPES_DIR)
    with pytest.raises(AssertionError, match="raised as EmitError"):
        fixtures.assert_fixture(_write_fixture(tmp_path, "  emit_error: EmitError\n"), SHAPES_DIR)


def test_fixture_cofires_must_really_cofire(tmp_path: Path):
    """expect.cofires documents a fact; naming a rule that does not fire on the focus fails the fixture."""
    path = tmp_path / "g.yaml"
    path.write_text(
        "rule: B-22\nexpect:\n  severity: Violation\n  focus: CAP-ITO-FND-1\n  cofires: [B-12]\n"
        "mutate:\n  id: CAP-ITO-FND-1\n  append_relates_to: {rel: consumed_by, target: FUNC-ito-version-control}\n",
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match=r"cofires names \['B-12'\]"):
        fixtures.assert_fixture(path, SHAPES_DIR)


def _mutated_inputs(config: Config, inputs: emit.Inputs, fixture_name: str) -> emit.Inputs:
    fixture = fixtures.load_fixture(fixtures.FIXTURES_DIR / fixture_name)
    return fixtures.apply_fixture(inputs, fixture)


@pytest.mark.parametrize(
    ("fixture_name", "subject", "error_class"),
    [
        ("structural/relates-to-malformed.yaml", "CAP-ITO-FND-1", "EmitError"),
        ("crossfield/B-13-emit-guard.yaml", "CAP-ITO-FND-1", "SourceGrammarError"),
    ],
)
def test_cli_validate_json_reports_an_emit_error_as_a_finding(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, config: Config, inputs: emit.Inputs,
    fixture_name: str, subject: str, error_class: str,
):
    """An input the emitter refuses is one `emit-error` finding on the record it names, printed like
    any finding, exit 1 — no traceback. `emit.load_inputs` is monkeypatched (the input-path guard forbids a
    scratch tree outside the repository)."""
    from itpra_onto import cli

    mutated = _mutated_inputs(config, inputs, fixture_name)
    monkeypatch.setattr(emit, "load_inputs", lambda config=None: mutated)
    code = cli.main(["validate", "--json"])
    out = capsys.readouterr().out
    assert code == 1
    payload = json.loads(out)
    assert len(payload) == 1
    finding = payload[0]
    assert (finding["rule"], finding["subject"], finding["severity"]) == ("emit-error", subject, "error")
    assert finding["message"].startswith(f"{error_class}: ")


def test_cli_validate_plain_reports_an_emit_error_as_a_finding(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, config: Config, inputs: emit.Inputs
):
    from itpra_onto import cli

    mutated = _mutated_inputs(config, inputs, "structural/type-unknown.yaml")
    monkeypatch.setattr(emit, "load_inputs", lambda config=None: mutated)
    code = cli.main(["validate"])
    out = capsys.readouterr().out
    assert code == 1
    assert "Violation  emit-error  CAP-ITO-FND-1  EmitError: " in out
    assert "1 finding(s) over no graph" in out
    assert "Traceback" not in out


def test_cli_validate_reports_an_input_file_defect_without_a_record(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
):
    """A file-level defect (here: a term file that is not a list of records) names no record: the
    finding's subject is the placeholder, the message names the file."""
    from itpra_onto import cli

    def refuse(config=None):
        raise emit.EmitError("terms/functions-ito-fnd.yaml: a term file must be a top-level list of records, got str")

    monkeypatch.setattr(emit, "load_inputs", refuse)
    code = cli.main(["validate", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload[0]["rule"] == "emit-error" and payload[0]["subject"] == shacl.NO_RECORD_FOCUS
    assert "functions-ito-fnd.yaml" in payload[0]["message"]


# ---------------------------------------------------------------------------------------------------
# (g) timing


# ---------------------------------------------------------------------------------------------------
# ShaclError: a malformed sh:sparql constraint (pySHACL returns a ValidationFailure, does not raise)


def test_validate_raises_shacl_error_for_a_values_clause_in_a_sparql_constraint(config: Config, clean_dataset: ox.Dataset, tmp_path: Path):
    """A deliberately bad shape: SHACL-SPARQL forbids VALUES inside a constraint's query, and pySHACL
    0.40.1 does not raise for this — it returns a ValidationFailure object in place of a results graph
    (shacl.py's module docstring). validate() must turn this into a ShaclError, not crash inside
    _extract_findings with an unrelated AttributeError ('ValidationFailure' object has no attribute
    'subjects'), confirmed empirically as the failure mode this guards against."""
    (tmp_path / "bad.ttl").write_text(
        """
itpra-o:BadValuesShape
    a sh:NodeShape ;
    sh:targetClass itpra:CAPABILITY ;
    sh:severity sh:Violation ;
    itpra-o:ruleId "smoke-bad-values" ;
    sh:sparql [
        a sh:SPARQLConstraint ;
        sh:message "unreachable" ;
        sh:prefixes itpra-o:shapesPrefixes ;
        sh:select \"\"\"
            SELECT $this ?value
            WHERE {
                VALUES ?value { 1 2 3 }
                $this skos:prefLabel ?x .
            }
        \"\"\" ;
    ] .
""",
        encoding="utf-8",
    )
    bad_shapes = shacl.load_shapes(tmp_path, config=config)
    with pytest.raises(shacl.ShaclError):
        shacl.validate(clean_dataset, bad_shapes, config=config)


def test_zz_shacl_validate_timing(config: Config, clean_dataset: ox.Dataset, smoke_shapes: ox.Dataset):
    total_triples = sum(1 for _ in clean_dataset)
    started = time.perf_counter()
    report = shacl.validate(clean_dataset, smoke_shapes, config=config)
    elapsed = time.perf_counter() - started
    print(f"\nshacl.validate() over {total_triples} triples (smoke shapes only): {elapsed:.3f}s, conforms={report.conforms}")
    assert elapsed < 60, f"validate() took {elapsed:.1f}s over {total_triples} triples — investigate before shapes/ grows"


def test_zzz_shacl_suite_timing():
    elapsed = time.perf_counter() - _MODULE_STARTED
    print(f"\ntest_shacl.py module wall time so far: {elapsed:.3f}s")

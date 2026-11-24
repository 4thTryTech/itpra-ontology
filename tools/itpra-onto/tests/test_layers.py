"""Tests for ``itpra_onto.layers`` (ADR 0043 D2): what a layer adds to a build, and that a build without one
is the vocabulary's own.

The layer under test lives in ``tests/fixtures/layer/``: one input file of notes about terms, one rule and
one shape. It names its own things under ``https://example.org/layer#`` and puts its quads in the graph
``notes``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pyoxigraph as ox
import pytest
import yaml

from itpra_onto import build as build_module
from itpra_onto import cli, emit, layers, rules, shacl
from itpra_onto.config import Config, load_config
from itpra_onto.layers import Layer

LAYER_DIR = Path(__file__).resolve().parent / "fixtures" / "layer"
NOTES_FILE = LAYER_DIR / "notes.yaml"
EX = "https://example.org/layer#"
NOTES_GRAPH_LOCAL = "notes"
RDFS_COMMENT = ox.NamedNode(emit.RDFS + "comment")


def _notes() -> list[dict]:
    return yaml.safe_load(NOTES_FILE.read_text(encoding="utf-8"))


def _emit_notes(dataset: ox.Dataset, config: Config, *, notes: list[dict] | None = None) -> None:
    graph = ox.NamedNode(config.iri.graph_ns + NOTES_GRAPH_LOCAL)
    for note in notes if notes is not None else _notes():
        subject = ox.NamedNode(EX + note["id"])
        dataset.add(ox.Quad(subject, emit.RDF_TYPE, ox.NamedNode(EX + "Note"), graph))
        dataset.add(ox.Quad(subject, ox.NamedNode(EX + "about"), ox.NamedNode(config.iri.id_ns + note["about"]), graph))
        if note.get("text"):
            dataset.add(ox.Quad(subject, RDFS_COMMENT, ox.Literal(note["text"]), graph))


NOTES = Layer(
    name="notes",
    emit=_emit_notes,
    input_files=lambda config: [NOTES_FILE],
    rules_dir=LAYER_DIR / "rules",
    shapes_dir=LAYER_DIR / "shapes",
)


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


@pytest.fixture(scope="module")
def plain(config: Config) -> layers.Assembled:
    return layers.assemble(config)


@pytest.fixture(scope="module")
def layered(config: Config) -> layers.Assembled:
    return layers.assemble(config, [NOTES])


def _graph(dataset: ox.Dataset, config: Config, local: str) -> set[ox.Triple]:
    graph = ox.NamedNode(config.iri.graph_ns + local)
    return {ox.Triple(q.subject, q.predicate, q.object) for q in dataset.quads_for_graph_name(graph)}


def _graph_locals(dataset: ox.Dataset, config: Config) -> set[str]:
    return {q.graph_name.value.removeprefix(config.iri.graph_ns) for q in dataset}


# ---------------------------------------------------------------------------------------------------
# without a layer: the vocabulary alone


def test_without_a_layer_the_assembly_is_emit_then_the_vocabularys_rules(config: Config, plain: layers.Assembled):
    expected = rules.apply_rules(emit.emit(emit.load_inputs(config), config), config)
    assert set(plain.dataset) == set(expected.dataset)
    assert plain.rule_counts == expected.counts
    assert _graph_locals(plain.dataset, config) == {"schema", "t1", "inferred"}


def test_without_a_layer_nothing_is_added_to_the_provenance_inputs(config: Config):
    assert layers.input_files(config) == []
    assert layers.shapes_dirs() == []
    assert layers.code_files() == []
    assert layers.rules_version(config) == rules.rules_digest(config)
    assert build_module.input_files(config) == build_module.input_files(config, ())


# ---------------------------------------------------------------------------------------------------
# with a layer: its graph, its rule, and the vocabulary's graphs untouched


def test_a_layer_adds_its_own_graph_and_leaves_the_vocabularys_graphs_alone(
    config: Config, plain: layers.Assembled, layered: layers.Assembled
):
    assert _graph_locals(layered.dataset, config) == {"schema", "t1", "inferred", NOTES_GRAPH_LOCAL}
    assert len(_graph(layered.dataset, config, NOTES_GRAPH_LOCAL)) == 3 * len(_notes())
    for local in ("schema", "t1"):
        assert _graph(layered.dataset, config, local) == _graph(plain.dataset, config, local), local


def test_a_layers_rules_run_after_the_vocabularys_and_write_to_inferred(
    config: Config, plain: layers.Assembled, layered: layers.Assembled
):
    assert list(layered.rule_counts)[: len(plain.rule_counts)] == list(plain.rule_counts)
    assert layered.rule_counts == {**plain.rule_counts, "noted-term": len(_notes())}
    added = _graph(layered.dataset, config, "inferred") - _graph(plain.dataset, config, "inferred")
    assert added == {
        ox.Triple(ox.NamedNode(config.iri.id_ns + note["about"]), ox.NamedNode(EX + "notedBy"), ox.NamedNode(EX + note["id"]))
        for note in _notes()
    }


def test_a_rule_id_already_in_use_is_refused(config: Config):
    clash = Layer(name="clash", rules_dir=rules.RULES_DIR)
    with pytest.raises(layers.LayerError, match="layer 'clash': rule id"):
        layers.assemble(config, [clash])


def test_layers_apply_in_the_order_given(config: Config, tmp_path: Path):
    """A second layer sees what the first one emitted."""
    seen: list[int] = []

    def count_notes(dataset: ox.Dataset, cfg: Config) -> None:
        seen.append(len(_graph(dataset, cfg, NOTES_GRAPH_LOCAL)))

    layers.assemble(config, [NOTES, Layer(name="after", emit=count_notes)])
    layers.assemble(config, [Layer(name="before", emit=count_notes), NOTES])
    assert seen == [3 * len(_notes()), 0]


# ---------------------------------------------------------------------------------------------------
# build: base files, provenance, --check


@pytest.fixture(scope="module")
def builds(config: Config, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    plain_out = tmp_path_factory.mktemp("plain") / "rdf"
    layered_out = tmp_path_factory.mktemp("layered") / "rdf"
    build_module.build(config, plain_out, load_store=False)
    build_module.build(config, layered_out, load_store=False, layers=[NOTES])
    return plain_out, layered_out


def _base_files(out: Path) -> set[str]:
    base = out / build_module.BASE_DIRNAME
    return {p.relative_to(base).as_posix() for p in base.rglob("*.ttl")}


def test_build_writes_one_base_file_per_asserted_graph(builds: tuple[Path, Path]):
    plain_out, layered_out = builds
    assert _base_files(plain_out) == {"schema.ttl", "t1.ttl"}
    assert _base_files(layered_out) == {"schema.ttl", "t1.ttl", "notes.ttl"}
    for name in ("schema.ttl", "t1.ttl"):
        assert (layered_out / build_module.BASE_DIRNAME / name).read_bytes() == (
            plain_out / build_module.BASE_DIRNAME / name
        ).read_bytes(), name
    manifest = json.loads((layered_out / build_module.BASE_DIRNAME / build_module.MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["notes.ttl"]["quads"] == 3 * len(_notes())


def test_provenance_covers_the_layers_inputs_and_rules(config: Config, plain: layers.Assembled):
    without = build_module.compute_provenance(config, plain.inputs)
    with_layer = build_module.compute_provenance(config, plain.inputs, [NOTES])
    label = emit._repo_relative(NOTES_FILE, config.repo_root)
    assert label not in dict(without.input_files)
    assert set(dict(with_layer.input_files)) == set(dict(without.input_files)) | {label}
    assert with_layer.input_hash != without.input_hash
    assert with_layer.rules_version != without.rules_version
    assert with_layer.rules_version == layers.rules_version(config, [NOTES])
    # the layer names no code_dir, the vocabulary and the pipeline are the same: these stay equal
    assert with_layer.code_hash == without.code_hash
    assert with_layer.schema_hash == without.schema_hash
    assert with_layer.ontology_version == without.ontology_version


def test_a_layers_code_joins_the_code_hash_under_its_name(tmp_path: Path):
    code_dir = tmp_path / "code"
    (code_dir / "sub").mkdir(parents=True)
    (code_dir / "a.py").write_text("A = 1\n", encoding="utf-8")
    (code_dir / "sub" / "b.py").write_text("B = 1\n", encoding="utf-8")
    (code_dir / "notes.txt").write_text("not code\n", encoding="utf-8")
    layer = Layer(name="mine", code_dir=code_dir)
    assert [label for label, _path in layers.code_files([layer])] == ["mine/a.py", "mine/sub/b.py"]

    before = build_module._code_hash([layer])
    assert before != build_module._code_hash()
    (code_dir / "a.py").write_text("A = 2\n", encoding="utf-8")
    assert build_module._code_hash([layer]) != before


def test_check_compares_like_with_like(config: Config, builds: tuple[Path, Path]):
    plain_out, layered_out = builds
    assert build_module.check(config, plain_out) == []
    assert build_module.check(config, layered_out, layers=[NOTES]) == []
    assert "missing: notes.ttl" in build_module.check(config, layered_out)
    assert "unexpected: notes.ttl" in build_module.check(config, plain_out, layers=[NOTES])


# ---------------------------------------------------------------------------------------------------
# validate: a layer's shapes run beside the vocabulary's, over its graph too


def test_a_layers_graph_is_validated_and_its_shapes_are_loaded(config: Config, layered: layers.Assembled):
    assert shacl.default_validation_graphs(layered.dataset, config) == ("inferred", NOTES_GRAPH_LOCAL, "t1")
    shapes = shacl.load_shapes(config=config, extra_dirs=layers.shapes_dirs([NOTES]))
    assert "note-text-missing" in shacl._shape_rule_ids(shapes, config).values()
    report = shacl.validate(layered.dataset, shapes, config=config)
    assert report.conforms, report.results_text


def test_a_layers_shape_fires_on_the_layers_own_data(config: Config):
    silent = [*_notes(), {"id": "NOTE-SILENT", "about": "CAP-ITO-FND-1"}]
    layer = Layer(
        name="notes",
        emit=lambda dataset, cfg: _emit_notes(dataset, cfg, notes=silent),
        shapes_dir=LAYER_DIR / "shapes",
    )
    assembled = layers.assemble(config, [layer])
    shapes = shacl.load_shapes(config=config, extra_dirs=layers.shapes_dirs([layer]))
    report = shacl.validate(assembled.dataset, shapes, config=config)
    assert [(f.rule_id, f.focus) for f in report.findings] == [("note-text-missing", EX + "NOTE-SILENT")]


# ---------------------------------------------------------------------------------------------------
# the command line: main(argv, layers=...)


def test_cli_build_and_check_take_layers(tmp_path: Path, capsys: pytest.CaptureFixture):
    out = tmp_path / "rdf"
    assert cli.main(["build", "--out", str(out), "--no-store"], layers=[NOTES]) == 0
    assert _base_files(out) == {"schema.ttl", "t1.ttl", "notes.ttl"}
    assert cli.main(["build", "--check", "--out", str(out)], layers=[NOTES]) == 0
    assert cli.main(["build", "--check", "--out", str(out)]) == cli.CHECK_FAILED_EXIT
    assert "missing: notes.ttl" in capsys.readouterr().err


def test_cli_validate_takes_layers(capsys: pytest.CaptureFixture):
    assert cli.main(["validate", "--json"], layers=[NOTES]) == 0
    assert json.loads(capsys.readouterr().out) == []


def test_cli_validate_reports_a_layers_emit_error_as_a_finding(capsys: pytest.CaptureFixture):
    def refuse(dataset: ox.Dataset, config: Config) -> None:
        raise emit.EmitError("notes.yaml: a note names no term", record_id="NOTE-9")

    assert cli.main(["validate", "--json"], layers=[Layer(name="notes", emit=refuse)]) == cli.VALIDATE_FAILED_EXIT
    (finding,) = json.loads(capsys.readouterr().out)
    assert (finding["rule"], finding["severity"]) == ("emit-error", "error")
    assert "a note names no term" in finding["message"]

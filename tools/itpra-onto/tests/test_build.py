"""Tests for the canonical output and load (``itpra_onto.build``, ``itpra-onto build``; ADR 0041 D5, ADR 0043).

Every test that needs real ontology content reads the REAL input files, exactly like
``test_emit.py``/``test_rules.py``: nothing is ever written to the vocabulary or the registries. Alternative
configs (store/dist isolation) are written to ``tmp_path`` only, always pointing ``ontology_dir``/
``requirements_glob`` back at the real inputs so the emitted content itself is unaffected.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pyoxigraph as ox
import pytest

from itpra_onto import build as build_module
from itpra_onto import emit, rules
from itpra_onto.config import DEFAULT_CONFIG_PATH, Config, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SUB_PROJECTS = 11

_DATE_RE = re.compile(r"20\d\d-\d\d-\d\d")
_TIME_RE = re.compile(r"T\d\d:\d\d")
_GIT_SHA_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{40}(?![0-9a-fA-F])")
_ABS_PATH_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/home/|/Users/")


# ---------------------------------------------------------------------------------------------------
# fixtures and helpers


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


def _write_config(tmp_path: Path, **paths: str) -> Path:
    """A temp copy of the shipped itpra-onto.toml with the named [paths] keys replaced (test_emit.py's
    helper, reused here so ontology_dir/requirements_glob can be pinned to the real inputs while
    store_dir/dist_dir are isolated under tmp_path)."""
    text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
    for key, value in paths.items():
        text, count = re.subn(rf'^{key} = "[^"]*"', f'{key} = "{value}"', text, count=1, flags=re.M)
        assert count == 1, key
    path = tmp_path / "itpra-onto.toml"
    path.write_text(text, encoding="utf-8")
    return path


def _real_input_paths() -> dict[str, str]:
    """The shipped config's inputs as absolute paths: ontology_dir always, requirements_glob only when the
    shipped config has an overlay (so a temp config outside the package still reads the real content)."""
    shipped = load_config()
    paths = {"ontology_dir": emit.ontology_dir(shipped).as_posix()}
    if shipped.overlay is not None and shipped.overlay.requirements_glob:
        paths["requirements_glob"] = os.path.abspath(shipped.config_path.parent / shipped.overlay.requirements_glob)
    return paths


def _isolated_config(tmp_path: Path) -> Config:
    """A config whose ontology_dir/requirements_glob still resolve to the real inputs, but
    whose dist_dir/store_dir are absolute paths under tmp_path (pathlib: joining an absolute path onto
    any base replaces it, so these are fully isolated regardless of the config file's own location)."""
    config_path = _write_config(
        tmp_path,
        **_real_input_paths(),
        dist_dir=(tmp_path / "dist").as_posix(),
        store_dir=(tmp_path / "store").as_posix(),
    )
    return load_config(config_path)


def _iter_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file())


# ---------------------------------------------------------------------------------------------------
# (a) determinism: two build() calls into two tmp dirs are byte-identical, file for file


def test_build_is_byte_identical_across_two_runs(tmp_path: Path, config: Config):
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    build_module.build(config=config, out_dir=out1, load_store=False)
    build_module.build(config=config, out_dir=out2, load_store=False)

    rel1 = [p.relative_to(out1) for p in _iter_files(out1)]
    rel2 = [p.relative_to(out2) for p in _iter_files(out2)]
    assert rel1 == rel2
    assert rel1  # non-empty
    for rel in rel1:
        assert (out1 / rel).read_bytes() == (out2 / rel).read_bytes(), f"{rel} differs between builds"


# ---------------------------------------------------------------------------------------------------
# (b) full/itpra.nq line count equals the dataset quad count == asserted + inferred + provenance


def test_full_nquads_line_count_matches_report_and_graphs(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    report = build_module.build(config=config, out_dir=out, load_store=False)

    full_path = out / build_module.FULL_DIRNAME / build_module.FULL_FILENAME
    line_count = len(full_path.read_bytes().splitlines())
    assert line_count == report.total_quads
    assert sum(report.graph_counts.values()) == report.total_quads

    inputs = emit.load_inputs(config)
    asserted = emit.emit(inputs, config)
    rule_report = rules.apply_rules(asserted, config)
    provenance_local = config.iri.graph_ns + build_module.PROVENANCE_GRAPH_LOCAL
    provenance_count = report.graph_counts[provenance_local]
    assert report.total_quads == len(rule_report.dataset) + provenance_count


# ---------------------------------------------------------------------------------------------------
# (c) base/ contains exactly schema.ttl, t1.ttl and one req/*.ttl per registry; re-parsed triples == asserted count


@pytest.mark.overlay  # needs the consumer's registries
def test_base_files_are_exactly_schema_t1_and_eleven_req(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    build_module.build(config=config, out_dir=out, load_store=False)
    base_dir = out / build_module.BASE_DIRNAME

    ttl_files = [p for p in base_dir.rglob("*.ttl")]
    rel_names = sorted(p.relative_to(base_dir).as_posix() for p in ttl_files)
    req_names = [n for n in rel_names if n.startswith("req/")]
    assert "schema.ttl" in rel_names
    assert "t1.ttl" in rel_names
    assert len(req_names) == EXPECTED_SUB_PROJECTS
    assert len(rel_names) == 2 + EXPECTED_SUB_PROJECTS
    assert (base_dir / build_module.MANIFEST_FILENAME).exists()


def test_base_turtle_triple_total_equals_asserted_quad_count(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    build_module.build(config=config, out_dir=out, load_store=False)
    base_dir = out / build_module.BASE_DIRNAME

    total_triples = 0
    for path in base_dir.rglob("*.ttl"):
        total_triples += len(list(ox.parse(path=path, format=ox.RdfFormat.TURTLE)))

    inputs = emit.load_inputs(config)
    asserted = emit.emit(inputs, config)
    assert total_triples == len(asserted)


def test_manifest_counts_and_hashes_match_the_files(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    build_module.build(config=config, out_dir=out, load_store=False)
    base_dir = out / build_module.BASE_DIRNAME
    manifest = json.loads((base_dir / build_module.MANIFEST_FILENAME).read_bytes())

    for rel, entry in manifest.items():
        data = (base_dir / rel).read_bytes()
        assert entry["sha256"] == hashlib.sha256(data).hexdigest(), rel
        assert entry["quads"] == len(list(ox.parse(input=data, format=ox.RdfFormat.TURTLE))), rel


# ---------------------------------------------------------------------------------------------------
# (d) no timestamp, no T\d\d:\d\d, no 40-hex SHA, no absolute path in any output file


def test_no_output_file_carries_a_timestamp_sha_or_absolute_path(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    build_module.build(config=config, out_dir=out, load_store=False)

    offenders: dict[str, list[str]] = {}
    for path in _iter_files(out):
        text = path.read_text(encoding="utf-8", errors="strict")
        hits = [
            line
            for line in text.splitlines()
            if _DATE_RE.search(line) or _TIME_RE.search(line) or _GIT_SHA_RE.search(line) or _ABS_PATH_RE.search(line)
        ]
        if hits:
            offenders[str(path.relative_to(out))] = hits
    assert offenders == {}, offenders


# ---------------------------------------------------------------------------------------------------
# (e) build.json: exact key set; input_hash traceable to compute_input_hash / hash_contributions


def test_build_json_has_exactly_the_documented_keys(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    build_module.build(config=config, out_dir=out, load_store=False)
    record = json.loads((out / build_module.BUILD_FILENAME).read_bytes())
    assert set(record.keys()) == set(build_module.BUILD_JSON_KEYS)
    for key in build_module.BUILD_JSON_KEYS:
        assert isinstance(record[key], str) and record[key]


def test_build_json_is_sorted_keys_indent_2_lf(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    build_module.build(config=config, out_dir=out, load_store=False)
    raw = (out / build_module.BUILD_FILENAME).read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r\n" not in raw
    text = raw.decode("utf-8")
    reparsed = json.dumps(json.loads(text), sort_keys=True, indent=2) + "\n"
    assert text == reparsed


def test_input_hash_matches_a_fresh_recomputation_from_the_same_real_files(config: Config):
    inputs = emit.load_inputs(config)
    provenance = build_module.compute_provenance(config, inputs)
    recomputed = build_module.compute_input_hash(build_module.input_files(config))
    assert provenance.input_hash == recomputed


def test_hash_contributions_changes_when_bytes_change():
    a = build_module.hash_contributions([("x.yaml", b"one")])
    b = build_module.hash_contributions([("x.yaml", b"two")])
    assert a != b


def test_hash_contributions_changes_when_label_changes_but_bytes_do_not():
    """A rename alone (same bytes, different path label) must change the digest."""
    a = build_module.hash_contributions([("a.yaml", b"same")])
    b = build_module.hash_contributions([("b.yaml", b"same")])
    assert a != b


def test_hash_contributions_is_deterministic_and_order_sensitive():
    x = build_module.hash_contributions([("a", b"1"), ("b", b"2")])
    y = build_module.hash_contributions([("a", b"1"), ("b", b"2")])
    z = build_module.hash_contributions([("b", b"2"), ("a", b"1")])
    assert x == y
    assert x != z


# ---------------------------------------------------------------------------------------------------
# (e2) provenance hashes do not depend on the checkout's line endings


def test_normalised_bytes_collapses_crlf_to_lf():
    assert build_module.normalised_bytes(b"a\r\nb\r\n") == b"a\nb\n"
    assert build_module.normalised_bytes(b"a\nb\n") == b"a\nb\n"  # already-LF content is unchanged


def test_crlf_and_lf_variants_of_the_same_content_hash_equal():
    """A checkout can hold files that are CRLF in the working tree but LF in the git index
    (``core.autocrlf=input``) for the same commit -- a CI checkout of that same commit must compute the same
    ``input_hash`` either way."""
    lf = build_module.hash_contributions([("x.yaml", build_module.normalised_bytes(b"a: 1\nb: 2\n"))])
    crlf = build_module.hash_contributions([("x.yaml", build_module.normalised_bytes(b"a: 1\r\nb: 2\r\n"))])
    assert lf == crlf


def test_uv_lock_hash_and_schema_hash_normalise_line_endings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """:func:`build_module._uv_lock_hash` and :func:`build_module._schema_hash` must hash the SAME digest
    whether their source files are LF or CRLF on disk."""
    project_lf = tmp_path / "lf"
    project_crlf = tmp_path / "crlf"
    for project in (project_lf, project_crlf):
        (project / "schema" / "generated").mkdir(parents=True)
    newline = b"\n"
    content = b"a: 1\nname: x\n"
    (project_lf / "uv.lock").write_bytes(content)
    (project_crlf / "uv.lock").write_bytes(content.replace(b"\n", b"\r\n"))
    for path in build_module.SCHEMA_HASH_FILES:
        (project_lf / path).write_bytes(content)
        (project_crlf / path).write_bytes(content.replace(b"\n", b"\r\n"))
    del newline

    monkeypatch.setattr(build_module, "PROJECT_DIR", project_lf)
    lf_uv, lf_schema = build_module._uv_lock_hash(), build_module._schema_hash()
    monkeypatch.setattr(build_module, "PROJECT_DIR", project_crlf)
    crlf_uv, crlf_schema = build_module._uv_lock_hash(), build_module._schema_hash()

    assert lf_uv == crlf_uv
    assert lf_schema == crlf_schema


# ---------------------------------------------------------------------------------------------------
# (e3) code_hash identifies the pipeline's own source code (ADR 0043 D3)


def test_code_hash_is_stable_and_covers_the_package(config: Config):
    inputs = emit.load_inputs(config)
    a = build_module.compute_provenance(config, inputs).code_hash
    b = build_module.compute_provenance(config, inputs).code_hash
    assert a == b
    assert re.fullmatch(r"[0-9a-f]{64}", a)


def test_code_hash_changes_when_pipeline_source_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    src_root = tmp_path / "src" / "itpra_onto"
    src_root.mkdir(parents=True)
    (src_root / "a.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr(build_module, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(build_module, "REPO_ROOT", tmp_path)  # _repo_relative() labels against REPO_ROOT
    before = build_module._code_hash()

    (src_root / "a.py").write_text("x = 2\n", encoding="utf-8")
    after = build_module._code_hash()
    assert before != after


def test_build_json_includes_code_hash(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    build_module.build(config=config, out_dir=out, load_store=False)
    record = json.loads((out / build_module.BUILD_FILENAME).read_bytes())
    assert "code_hash" in record
    assert re.fullmatch(r"[0-9a-f]{64}", record["code_hash"])


# ---------------------------------------------------------------------------------------------------
# (e4) the documented store/total-quads equality is actually enforced


def test_build_raises_when_store_quad_count_disagrees_with_total(
    tmp_path: Path, config: Config, monkeypatch: pytest.MonkeyPatch
):
    """README/module-docstring claim this equality is asserted before ``build()`` returns; simulate a
    store-load bug (e.g. a truncated ``bulk_load``) by monkeypatching ``_load_store`` to lie about the
    count, and confirm ``build()`` actually refuses rather than silently returning a wrong report."""
    monkeypatch.setattr(build_module, "_load_store", lambda _config, _path: -1)
    with pytest.raises(build_module.BuildError, match="store quad count"):
        build_module.build(config=config, out_dir=tmp_path / "out", load_store=True)


# ---------------------------------------------------------------------------------------------------
# (f) store round-trip: reopen after build(); a second build drops and rebuilds without error


def test_store_round_trip(tmp_path: Path):
    config = _isolated_config(tmp_path)
    report = build_module.build(config=config, load_store=True)

    target = build_module.store_dir(config)
    assert target.exists()
    full_path = report.out_dir / build_module.FULL_DIRNAME / build_module.FULL_FILENAME
    line_count = len(full_path.read_bytes().splitlines())
    assert report.store_quad_count == line_count

    reopened = ox.Store(target)
    rows = list(reopened.query("SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } }"))
    assert int(rows[0]["n"].value) == line_count
    del reopened

    # A second build drops and rebuilds the same store directory without error.
    report2 = build_module.build(config=config, load_store=True)
    assert report2.store_quad_count == line_count


def test_no_store_skips_the_store(tmp_path: Path):
    config = _isolated_config(tmp_path)
    report = build_module.build(config=config, load_store=False)
    assert report.store_quad_count is None
    assert not build_module.store_dir(config).exists()


# ---------------------------------------------------------------------------------------------------
# (g) build --check: 0 right after a build, 1 after a base file is altered


def test_check_passes_after_build_and_fails_after_mutation(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    build_module.build(config=config, out_dir=out, load_store=False)
    assert build_module.check(config=config, out_dir=out) == []

    target = next((out / build_module.BASE_DIRNAME).rglob("*.ttl"))
    target.write_bytes(target.read_bytes() + b"\n# test mutation\n")
    diffs = build_module.check(config=config, out_dir=out)
    assert diffs


def test_check_reports_missing_base_dir(tmp_path: Path, config: Config):
    out = tmp_path / "never-built"
    diffs = build_module.check(config=config, out_dir=out)
    assert diffs


# ---------------------------------------------------------------------------------------------------
# (h) provenance graph: one prov:wasDerivedFrom per input file


def test_provenance_graph_has_one_derived_from_per_input_file(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    build_module.build(config=config, out_dir=out, load_store=False)
    full_bytes = (out / build_module.FULL_DIRNAME / build_module.FULL_FILENAME).read_bytes()
    quads = list(ox.parse(input=full_bytes, format=ox.RdfFormat.N_QUADS))

    provenance_graph = config.iri.graph_ns + build_module.PROVENANCE_GRAPH_LOCAL
    dataset_node = build_module._dataset_node(config)  # noqa: SLF001 - testing the documented node shape
    derived_from = [
        q
        for q in quads
        if q.graph_name.value == provenance_graph
        and q.predicate == build_module.PROV_WAS_DERIVED_FROM
        and q.subject == dataset_node
    ]
    expected = len(emit.term_files(config)) + len(emit.registry_files(config)) + 1
    assert len(derived_from) == expected

    # Every input entity is typed prov:Entity and carries dcterms:identifier + itpra-o:sha256.
    by_subject: dict[ox.NamedNode, list[ox.Quad]] = {}
    for quad in quads:
        by_subject.setdefault(quad.subject, []).append(quad)
    sha256_predicate = ox.NamedNode(config.iri.onto_ns + "sha256")
    for edge in derived_from:
        node = edge.object
        node_quads = by_subject.get(node, [])
        assert any(q.predicate == emit.RDF_TYPE and q.object == build_module.PROV_ENTITY for q in node_quads), node
        identifiers = [q.object.value for q in node_quads if q.predicate == build_module.DCTERMS_IDENTIFIER]
        shas = [q.object.value for q in node_quads if q.predicate == sha256_predicate]
        assert len(identifiers) == 1
        assert len(shas) == 1
        assert re.fullmatch(r"[0-9a-f]{64}", shas[0])


def test_dataset_node_carries_the_seven_scalars(tmp_path: Path, config: Config):
    out = tmp_path / "out"
    report = build_module.build(config=config, out_dir=out, load_store=False)
    full_bytes = (out / build_module.FULL_DIRNAME / build_module.FULL_FILENAME).read_bytes()
    quads = list(ox.parse(input=full_bytes, format=ox.RdfFormat.N_QUADS))
    dataset_node = build_module._dataset_node(config)  # noqa: SLF001

    def literal_for(local: str) -> str | None:
        prop = ox.NamedNode(config.iri.onto_ns + local)
        values = [q.object.value for q in quads if q.subject == dataset_node and q.predicate == prop]
        return values[0] if values else None

    assert literal_for("inputHash") == report.input_hash
    assert literal_for("rulesVersion") == report.rules_version
    assert literal_for("schemaHash") is not None
    assert literal_for("pipelineVersion") is not None
    assert literal_for("uvLockHash") is not None
    assert literal_for("codeHash") is not None
    version_info = [
        q.object.value for q in quads if q.subject == dataset_node and q.predicate == emit.OWL_VERSION_INFO
    ]
    assert version_info == [report.ontology_version]


# ---------------------------------------------------------------------------------------------------
# schema graph: the provenance datatype properties are declared (emit.py addition)


def test_provenance_properties_declared_as_datatype_properties_in_schema_graph(config: Config):
    dataset = emit.emit(config=config)
    schema_graph = ox.NamedNode(config.iri.graph_ns + "schema")
    for local in emit.PROVENANCE_PROPERTY_LABELS:
        prop = ox.NamedNode(config.iri.onto_ns + local)
        assert ox.Quad(prop, emit.RDF_TYPE, emit.OWL_DATATYPE_PROPERTY, schema_graph) in dataset, local


# ---------------------------------------------------------------------------------------------------
# CLI


def test_cli_build_no_store(tmp_path: Path):
    config_path = _write_config(
        tmp_path,
        **_real_input_paths(),
        dist_dir=(tmp_path / "dist").as_posix(),
        store_dir=(tmp_path / "store").as_posix(),
    )
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "build", "--no-store"],
        cwd=PROJECT_ROOT,
        env={**os.environ, "ITPRA_ONTO_CONFIG": str(config_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (tmp_path / "store").exists()
    assert (tmp_path / "dist" / "rdf" / "full" / "itpra.nq").exists()
    assert "quads total" in result.stdout


def test_cli_build_check_on_the_real_tree():
    """Exercises the real, committed config end to end (`itpra-onto build`, then `build --check`), writing
    into the real (gitignored) dist/rdf/."""
    build_module.build(load_store=False)
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "build", "--check"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

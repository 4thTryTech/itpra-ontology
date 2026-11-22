"""Smoke tests: the pinned libraries do what the pipeline relies on.

Each test exercises the pinned library directly rather than merely importing
it, and settles (or re-confirms) one of three load-bearing questions:

* Does pyshacl 0.40.1 validate directly against a ``pyoxigraph.Store``?
  (test_pyshacl_validates_pyoxigraph_store_directly)
* What is the explicit (non-"unstable") RDFC-1.0 canonicalisation API in
  pyoxigraph 0.5.11? (test_pyoxigraph_dataset_canonicalize_rdfc_1_0_is_deterministic)
* Does ``linkml-validate --target-class Term`` accept a bare top-level list
  (the shape terms/*.yaml actually uses), or does it require a
  tree_root container wrapper? (test_linkml_bare_list_target_class_spike)
"""

from __future__ import annotations

import importlib.metadata
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pyoxigraph as ox
import pyshacl

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


# --- (a) pyoxigraph: in-memory Store, two quads in a named graph, SPARQL COUNT ---


def test_pyoxigraph_store_add_and_sparql_count():
    store = ox.Store()
    graph = ox.NamedNode("https://example.test/ns/itpra/graph/t1")
    store.add(
        ox.Quad(
            ox.NamedNode("https://example.test/ns/itpra/id/CAP-TEST-1"),
            ox.NamedNode("https://example.test/ns/itpra/onto#groupedBy"),
            ox.NamedNode("https://example.test/ns/itpra/id/FND"),
            graph,
        )
    )
    store.add(
        ox.Quad(
            ox.NamedNode("https://example.test/ns/itpra/id/CAP-TEST-1"),
            ox.NamedNode("https://example.test/ns/itpra/onto#consumedBy"),
            ox.NamedNode("https://example.test/ns/itpra/id/PERSONA-test"),
            graph,
        )
    )

    results = store.query(
        "SELECT (COUNT(*) AS ?n) WHERE { GRAPH <https://example.test/ns/itpra/graph/t1> { ?s ?p ?o } }"
    )
    rows = list(results)
    assert len(rows) == 1
    count_literal = rows[0]["n"]
    assert int(count_literal.value) == 2


# --- (b) pyoxigraph: explicit RDFC-1.0 canonicalisation, byte-identical N-Quads ---


def _build_blank_node_free_dataset() -> ox.Dataset:
    """A small, blank-node-free Dataset (the smoke test only needs determinism,
    not RDFC-1.0's blank-node-relabelling behaviour itself)."""
    dataset = ox.Dataset()
    graph = ox.NamedNode("https://example.test/ns/itpra/graph/t1")
    dataset.add(
        ox.Quad(
            ox.NamedNode("https://example.test/ns/itpra/id/CAP-TEST-1"),
            ox.NamedNode("http://www.w3.org/2004/02/skos/core#prefLabel"),
            ox.Literal("Test Capability One", language="en"),
            graph,
        )
    )
    dataset.add(
        ox.Quad(
            ox.NamedNode("https://example.test/ns/itpra/id/CAP-TEST-1"),
            ox.NamedNode("https://example.test/ns/itpra/onto#groupedBy"),
            ox.NamedNode("https://example.test/ns/itpra/id/FND"),
            graph,
        )
    )
    return dataset


def _sorted_nquads(dataset: ox.Dataset) -> bytes:
    raw = ox.serialize(dataset, format=ox.RdfFormat.N_QUADS)
    lines = raw.decode("utf-8").splitlines(keepends=True)
    return "".join(sorted(lines)).encode("utf-8")


def test_pyoxigraph_dataset_canonicalize_rdfc_1_0_is_deterministic():
    # The explicit RDFC-1.0 member of pyoxigraph.CanonicalizationAlgorithm
    # (added at pyoxigraph 0.5.4) -- NOT CanonicalizationAlgorithm.UNSTABLE,
    # the default/example algorithm shown in pyoxigraph's own docstring.
    algorithm = ox.CanonicalizationAlgorithm.RDFC_1_0
    assert algorithm is not ox.CanonicalizationAlgorithm.UNSTABLE

    dataset_1 = _build_blank_node_free_dataset()
    dataset_2 = _build_blank_node_free_dataset()
    dataset_1.canonicalize(algorithm)
    dataset_2.canonicalize(algorithm)

    # Empirically: canonicalize() fixes blank-node labels but
    # does NOT fix quad *iteration order* -- two independently built,
    # content-identical Datasets serialise to N-Quads with their quads in a
    # different order call to call (observed to vary across 5 fresh builds in
    # this same test run). serialize() on the SAME already-canonicalized
    # object twice is trivially byte-identical (no reordering happens between
    # calls), which is not a meaningful determinism test on its own. A plain
    # line-sort after serialisation *is* byte-identical across independent
    # builds -- exactly the build's canonicalise-then-sort step (ADR 0041
    # D5), so this confirms that step is load-bearing, not just cautious
    # wording.
    nquads_1 = ox.serialize(dataset_1, format=ox.RdfFormat.N_QUADS)
    nquads_2 = ox.serialize(dataset_2, format=ox.RdfFormat.N_QUADS)
    same_object_twice = ox.serialize(dataset_1, format=ox.RdfFormat.N_QUADS)
    assert nquads_1 == same_object_twice  # reserialising one object is stable

    sorted_1 = _sorted_nquads(dataset_1)
    sorted_2 = _sorted_nquads(dataset_2)
    assert sorted_1 == sorted_2
    assert sorted_1  # non-empty


# --- (c) pySHACL against a pyoxigraph.Store directly ---


_SHAPES_TTL = """
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix ex: <https://example.test/ns/itpra/onto#> .

ex:CapabilityShape
    a sh:NodeShape ;
    sh:targetClass ex:Capability ;
    sh:property [
        sh:path ex:groupedBy ;
        sh:minCount 1 ;
    ] .
"""

_VIOLATING_DATA_TTL = """
@prefix ex: <https://example.test/ns/itpra/onto#> .
@prefix id: <https://example.test/ns/itpra/id/> .

id:CAP-TEST-1 a ex:Capability .
"""


def test_pyshacl_validates_pyoxigraph_store_directly():
    """Does pySHACL 0.40.1's validate() accept a raw pyoxigraph.Store as the
    data graph? Confirmed: yes, entrypoints.py checks
    `isinstance(data_graph, ox_Store)` and wraps it in its DataGraph
    abstraction internally -- pyshacl[oxigraph] is required for this path,
    matching the extra pinned in pyproject.toml."""
    store = ox.Store()
    store.load(
        _VIOLATING_DATA_TTL.encode("utf-8"),
        format=ox.RdfFormat.TURTLE,
        base_iri="https://example.test/ns/itpra/id/",
        to_graph=ox.DefaultGraph(),
    )

    conforms, _results_graph, results_text = pyshacl.validate(
        store,
        shacl_graph=_SHAPES_TTL,
        shacl_graph_format="turtle",
    )

    assert conforms is False
    assert "MinCountConstraintComponent" in results_text


# --- (d) LinkML: tree_root container validation, positive and negative fixtures ---


def _run_linkml_validate(*args: str) -> subprocess.CompletedProcess[str]:
    # linkml-validate's console-script entry point is linkml.validator.cli:cli
    # (a click command); `linkml.validator` itself is not runnable with -m.
    return subprocess.run(
        [sys.executable, "-c", "from linkml.validator.cli import cli; cli()", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_linkml_validate_tree_root_container_passes():
    result = _run_linkml_validate(
        "--schema",
        str(FIXTURES_DIR / "mini.linkml.yaml"),
        "--target-class",
        "TermFile",
        str(FIXTURES_DIR / "mini-terms.yaml"),
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_linkml_validate_tree_root_container_fails_on_bad_id():
    result = _run_linkml_validate(
        "--schema",
        str(FIXTURES_DIR / "mini.linkml.yaml"),
        "--target-class",
        "TermFile",
        str(FIXTURES_DIR / "mini-terms-bad-id.yaml"),
    )
    assert result.returncode != 0
    assert "1-BAD-ID" in (result.stdout + result.stderr)


def test_linkml_bare_list_target_class_spike():
    """Does `linkml-validate --target-class Term` alone, pointed at a bare
    list-of-Term YAML file with no wrapping key, validate each list element?

    Empirically, on linkml 1.11.1: YES, it validates each element -- a
    TermFile/tree_root wrapper class is NOT required to validate a bare
    top-level list (the shape terms/*.yaml actually uses) against
    a plain (non-container) class via --target-class. Confirmed both ways:
    a clean bare list passes, and a bare list with one invalid id fails with
    the expected per-element error.
    """
    good = _run_linkml_validate(
        "--schema",
        str(FIXTURES_DIR / "mini.linkml.yaml"),
        "--target-class",
        "Term",
        str(FIXTURES_DIR / "mini-terms-bare-list.yaml"),
    )
    assert good.returncode == 0, good.stdout + good.stderr

    bad = _run_linkml_validate(
        "--schema",
        str(FIXTURES_DIR / "mini.linkml.yaml"),
        "--target-class",
        "Term",
        str(FIXTURES_DIR / "mini-terms-bare-list-bad.yaml"),
    )
    assert bad.returncode != 0
    assert "1-BAD-ID" in (bad.stdout + bad.stderr)


# --- (e) `release` refusal ---


def test_release_refuses_on_placeholder_base_iri(tmp_path):
    """``release`` refuses while ``[iri] base`` is the reserved-domain placeholder (ADR 0004). The shipped
    itpra-onto.toml carries the published base IRI, so the refusal is exercised through a temporary config
    whose host is the placeholder -- assembled by concatenation so this file does not itself match
    test_iri_config.py's project-wide placeholder scan."""
    import os

    from itpra_onto.config import load_config

    shipped = load_config()
    placeholder_base = "https://" + "placeholder" + ".invalid" + "/ns/itpra/"
    alt = tmp_path / "itpra-onto.toml"
    alt.write_text(
        "[iri]\n"
        f'base = "{placeholder_base}"\n'
        'id_path = "id/"\nonto_path = "onto#"\ngraph_path = "graph/"\n\n'
        "[paths]\n"
        f'ontology_dir = "{(PROJECT_ROOT / shipped.paths.ontology_dir).resolve().as_posix()}"\n'
        'dist_dir = "dist"\nstore_dir = ".store"\n\n[python]\npinned = "3.12"\n',
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "release"],
        cwd=PROJECT_ROOT,
        env={**os.environ, "ITPRA_ONTO_CONFIG": str(alt)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "placeholder" in result.stderr.lower()
    assert placeholder_base in result.stderr


def test_validate_and_parity_are_implemented():
    """``build`` (test_build.py), plain ``validate`` without ``--authoring`` (test_shacl.py) and ``parity``
    (test_parity.py) are implemented; this is only a smoke check that ``parity`` does not print the
    not-implemented message ``release`` still prints."""
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "parity", "--sub", "ITO"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode in (0, 1), (result.stdout, result.stderr)
    assert "not implemented yet" not in result.stdout


# --- (f) version pin test ---


def _load_pinned_versions() -> dict[str, str]:
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    pins: dict[str, str] = {}
    for dep in pyproject["project"]["dependencies"]:
        match = re.match(r"^([A-Za-z0-9_.-]+)(\[[A-Za-z0-9_,.-]+\])?==([A-Za-z0-9_.+-]+)$", dep)
        assert match is not None, f"dependency not exact-pinned: {dep!r}"
        name, _extra, version = match.groups()
        pins[name.lower()] = version
    for dep in pyproject["dependency-groups"]["dev"]:
        match = re.match(r"^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)$", dep)
        assert match is not None, f"dev dependency not exact-pinned: {dep!r}"
        name, version = match.groups()
        pins[name.lower()] = version
    return pins


def test_installed_versions_match_pyproject_pins():
    pins = _load_pinned_versions()

    for distribution_name in ("pyyaml", "rdflib", "pyoxigraph", "pyshacl", "linkml", "linkml-runtime", "pytest"):
        pinned = pins[distribution_name]
        installed = importlib.metadata.version(distribution_name)
        assert installed == pinned, f"{distribution_name}: installed {installed!r} != pinned {pinned!r}"

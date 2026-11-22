"""Canonical output and load: ``itpra-onto build``.

Pipeline: :func:`itpra_onto.emit.load_inputs` -> :func:`itpra_onto.emit.emit` -> :func:`itpra_onto.rules.apply_rules`
(into ``inferred``) -> a provenance record appended as a fourth graph (``inferred`` plus ``provenance`` are
never asserted by ``emit.py`` itself) -> RDFC-1.0 canonicalisation and a sorted-lines pass
(:mod:`itpra_onto.canon`) -> two artefact shapes written under ``<out>``
(``config.paths.dist_dir`` resolved against ``config.config_path.parent``, then ``rdf/`` — i.e.
``dist/rdf/``, gitignored, always rebuilt, never touching the sibling ``dist/schema/`` ``gen-artifacts`` owns) -> an
optional load into the disposable Oxigraph store (``config.paths.store_dir``, ADR 0041 D5: dropped and
rebuilt on every run, never committed, never migrated in place).

**Provenance, without timestamps** (ADR 0043 D3): every build computes ``input_hash``
(sha256 over every input file's bytes, each contribution prefixed by its repo-relative path so a rename
alone changes the hash — see :func:`hash_contributions`), ``pipeline_version`` (this distribution's own
version), ``uv_lock_hash`` (sha256 of ``uv.lock``), ``rules_version`` (:func:`itpra_onto.rules.rules_digest`),
``ontology_version`` (the vocabulary's ``schema.yaml``), ``schema_hash`` (sha256 of the hand-authored LinkML
schema plus its two generated fragments) and ``code_hash`` (sha256 over every ``src/itpra_onto/**/*.py``
file, sorted repo-relative path — the pipeline's own code, not just its inputs). No commit SHA
(ADR 0043 D3: a commit SHA is circular if the output is ever committed) and no wall-clock timestamp
anywhere in any output file. Every one of these seven scalars is hashed over **line-ending-normalised**
bytes (:func:`normalised_bytes`: CRLF collapsed to LF) rather than the file's raw bytes, so the same commit
hashes identically whether checked out with ``core.autocrlf=input``/``true`` or on a platform that never
touches line endings — a checkout with CRLF in the working tree and LF in the index would otherwise disagree
with a CI runner on ``input_hash`` alone. The record is written
twice, once machine-readable (``<out>/build.json``) and once as RDF: the dataset's own node
(``<base>dataset`` — a plain resource directly under the base IRI, distinct from any term or requirement id
under ``<base>id/``, any schema vocabulary term under ``<base>onto#`` and any named graph under
``<base>graph/``) carries the seven scalars as literals plus one ``prov:wasDerivedFrom`` per input file, each
input a ``prov:Entity`` of its own carrying ``dcterms:identifier`` (its repo-relative path) and
``itpra-o:sha256`` (that one file's own, line-ending-normalised hash). ``prov:wasDerivedFrom`` is the right
predicate for dataset-to-input provenance (``itpra-o:decidedIn`` is reserved for a term's link to its
decision record, a different relation entirely; ADR 0041 D2). All of this lands in a fourth named graph,
``<graph_ns>provenance``, alongside ``schema``/``t1``/``req/<X>``/``inferred``.

**Canonical outputs** under ``<out>``:

* ``full/itpra.nq`` — sorted canonical N-Quads of every graph, including ``inferred`` and ``provenance``.
* ``base/<graph>.ttl`` — one Turtle file per *asserted* graph, excluding ``inferred`` and ``provenance``:
  ``schema.ttl``, ``t1.ttl``, ``req/<X>.ttl`` (one per registry, in a ``req/`` subdirectory). Turtle
  determinism is an empirical finding, not an assumption: ``ox.serialize()`` given a plain
  Python list of :class:`pyoxigraph.Triple` serialises that list in exactly the order given (confirmed
  empirically — unlike a :class:`pyoxigraph.Dataset`/:class:`pyoxigraph.Store`, whose internal storage
  reorders quads on iteration in a way that varies build to build, which is exactly why ``canon.py``'s
  N-Quads recipe needs its own sort step). So the per-graph Turtle is built by re-parsing the already
  globally-sorted canonical N-Quads text (:func:`itpra_onto.canon.canonical_nquads`) back into quads —
  preserving that sorted order — grouping by graph name with the graph name then dropped (Turtle has no
  named graphs; ``ox.serialize`` raises ``ValueError`` if a graph name survives), and serialising each
  group's ordered triple list directly: no second sort is needed, because the input order is already
  canonical. ``ox.serialize(..., format=TURTLE, prefixes=...)`` also accepts a ``prefixes`` mapping and
  applies it deterministically (confirmed empirically); this pipeline's three prefixes
  (``itpra:``/``itpra-o:``/``itpra-g:``, from :class:`itpra_onto.config.IriConfig`) plus the standard ones
  (``rdf``, ``rdfs``, ``owl``, ``skos``, ``dcterms``, ``prov``) are always passed.
* ``base/manifest.json`` — every base file's sha256 and quad count, sorted keys.
* ``<out>/build.json`` — the provenance record (the seven scalars above only; no input-file list, no
  timestamp).

Old contents of ``<out>`` are removed before writing (only the ``rdf/`` subtree under ``dist/`` — never
``dist/schema/``, ``gen-artifacts``' own output).

**Store** (ADR 0041 D5): ``config.paths.store_dir`` resolved against ``config.config_path.parent``
(``.store/`` at the package root by default) is dropped entirely (``shutil.rmtree``) and rebuilt from
``full/itpra.nq`` with ``Store.bulk_load`` on every build unless ``load_store=False``. After loading, the
store is queried for its own quad count (one SPARQL query, ``SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s
?p ?o } }`` — every quad this pipeline ever writes lives in a named graph, so this counts everything) and
that count is asserted to equal ``full/itpra.nq``'s line count before :func:`build` returns.
:class:`pyoxigraph.Store` (0.5.11) has no context-manager protocol and no explicit ``close``; ``flush()``
is called and the local reference is then dropped (``del``) so the RocksDB lock is released before this
function returns — load-bearing for a caller (or test) that immediately reopens the same path.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import shutil
import tempfile
import time
import tomllib
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pyoxigraph as ox

from itpra_onto import canon, emit, rules
from itpra_onto.config import Config, load_config

PROJECT_DIR = Path(__file__).resolve().parents[2]  # the package root
REPO_ROOT = emit.REPO_ROOT

DISTRIBUTION_NAME = "itpra-onto"  # pyproject.toml [project] name

FULL_DIRNAME = "full"
FULL_FILENAME = "itpra.nq"
BASE_DIRNAME = "base"
MANIFEST_FILENAME = "manifest.json"
BUILD_FILENAME = "build.json"
REQ_SUBDIRNAME = "req"

PROVENANCE_GRAPH_LOCAL = "provenance"
DATASET_LOCAL = "dataset"  # <base>dataset — see module docstring for why this shape, not <graph_ns>dataset
INPUT_NODE_LOCAL_PREFIX = "input/"  # <graph_ns>input/<repo-relative path>

# Standard vocabulary this module needs beyond what itpra_onto.emit already exposes as constants
# (only the base IRI is a configuration item, ADR 0004; W3C/DCMI vocabularies are literal constants).
DCTERMS = "http://purl.org/dc/terms/"
DCTERMS_IDENTIFIER = ox.NamedNode(DCTERMS + "identifier")
PROV_ENTITY = ox.NamedNode(emit.PROV + "Entity")
PROV_WAS_DERIVED_FROM = ox.NamedNode(emit.PROV + "wasDerivedFrom")

# schema/itpra.linkml.yaml plus its two generated fragments, hashed for the provenance record's
# `schema_hash` (package-relative paths, not repo-relative -- these files live inside this package).
SCHEMA_HASH_FILES = (
    Path("schema") / "itpra.linkml.yaml",
    Path("schema") / "generated" / "itpra-enums.linkml.yaml",
    Path("schema") / "generated" / "itpra-prefixes.linkml.yaml",
)

BUILD_JSON_KEYS = (
    "code_hash",
    "input_hash",
    "ontology_version",
    "pipeline_version",
    "rules_version",
    "schema_hash",
    "uv_lock_hash",
)


class BuildError(RuntimeError):
    """A build precondition failed (a malformed base graph name; a generator or store contract violated)."""


# =====================================================================================================
# Paths


def dist_rdf_dir(config: Config | None = None) -> Path:
    """``<dist_dir>/rdf`` — the default ``out_dir`` (``dist/rdf/``, gitignored)."""
    config = config if config is not None else load_config()
    return (config.config_path.parent / config.paths.dist_dir).resolve() / "rdf"


def store_dir(config: Config | None = None) -> Path:
    """``config.paths.store_dir`` resolved against the config file's own directory (ADR 0041 D5)."""
    config = config if config is not None else load_config()
    return (config.config_path.parent / config.paths.store_dir).resolve()


def _repo_relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


# =====================================================================================================
# Provenance (ADR 0043 D3)


@dataclass(frozen=True)
class Provenance:
    input_hash: str
    pipeline_version: str
    uv_lock_hash: str
    rules_version: str
    ontology_version: str
    schema_hash: str
    code_hash: str
    input_files: tuple[tuple[str, str], ...]  # (repo-relative path, that file's own sha256), sorted


def normalised_bytes(data: bytes) -> bytes:
    """Collapse every CRLF to LF before hashing.

    A checkout configured with ``core.autocrlf=input`` normalises line endings going INTO the git index but
    leaves whatever the working tree already had on disk, so input files can be CRLF in the working tree
    while the index — and therefore any checkout on a platform that does not rewrite line endings, e.g. a
    Linux CI runner — holds them LF, for the exact same commit. Hashing raw bytes would then make
    ``input_hash``/``schema_hash``/``uv_lock_hash``/``code_hash`` depend on which machine and checkout mode
    produced the working tree, not on the content those hashes exist to fingerprint. Applied at the point
    each file's bytes are read for hashing, never to bytes this pipeline itself writes to disk (those are
    always emitted with explicit ``\\n``, see :func:`itpra_onto.canon.write_bytes`).
    """
    return data.replace(b"\r\n", b"\n")


def hash_contributions(contributions: Iterable[tuple[str, bytes]]) -> str:
    """sha256 over ``(label, bytes)`` pairs, each prefixed by its label — so a label (path) change alone
    changes the digest even when the bytes are identical (a rename). Pure and filesystem-free: the unit
    under test for :func:`compute_input_hash`, which supplies the labels and bytes from real files."""
    digest = hashlib.sha256()
    for label, data in contributions:
        digest.update(label.encode("utf-8"))
        digest.update(b"\0")
        digest.update(data)
    return digest.hexdigest()


def compute_input_hash(paths: Iterable[Path]) -> str:
    """:func:`hash_contributions` over ``paths``, labelled by repo-relative posix path, in the given order,
    over each file's line-ending-normalised bytes (:func:`normalised_bytes`).

    Callers pass an already-deterministically-ordered ``paths`` (:func:`input_files` sorts by that same
    label) so the digest does not depend on filesystem iteration order.
    """
    return hash_contributions((_repo_relative(p), normalised_bytes(p.read_bytes())) for p in paths)


def input_files(config: Config | None = None) -> list[Path]:
    """Every file the build hashes for provenance: every term file, every registry file (as
    :mod:`itpra_onto.emit` reads them) and the vocabulary's ``schema.yaml`` itself — sorted by repo-relative
    posix path, the fixed order :func:`compute_input_hash` and the provenance graph's
    ``prov:wasDerivedFrom`` edges both rely on."""
    config = config if config is not None else load_config()
    paths = [*emit.term_files(config), *emit.registry_files(config), emit.schema_file(config)]
    return sorted(paths, key=_repo_relative)


def _pipeline_version() -> str:
    try:
        return importlib.metadata.version(DISTRIBUTION_NAME)
    except importlib.metadata.PackageNotFoundError:
        # Not installed as a distribution (e.g. run straight from a checkout): fall back to the source of
        # truth importlib.metadata would otherwise read.
        data = tomllib.loads((PROJECT_DIR / "pyproject.toml").read_text(encoding="utf-8"))
        return str(data["project"]["version"])


def _uv_lock_hash() -> str:
    return hashlib.sha256(normalised_bytes((PROJECT_DIR / "uv.lock").read_bytes())).hexdigest()


def _schema_hash() -> str:
    return hash_contributions(
        (path.as_posix(), normalised_bytes((PROJECT_DIR / path).read_bytes())) for path in SCHEMA_HASH_FILES
    )


def _code_files() -> list[Path]:
    """Every ``.py`` file of the pipeline itself, sorted by repo-relative posix path."""
    return sorted((PROJECT_DIR / "src" / "itpra_onto").rglob("*.py"), key=_repo_relative)


def _code_hash() -> str:
    """sha256 over every pipeline ``.py`` file's line-ending-normalised bytes, path-prefixed exactly like
    :func:`compute_input_hash` — the provenance record's identity for the CODE that produced a build, not
    just the data it was run against (a bug fix with unchanged inputs must still change this)."""
    return hash_contributions((_repo_relative(p), normalised_bytes(p.read_bytes())) for p in _code_files())


def compute_provenance(config: Config, inputs: emit.Inputs) -> Provenance:
    paths = input_files(config)
    return Provenance(
        input_hash=compute_input_hash(paths),
        pipeline_version=_pipeline_version(),
        uv_lock_hash=_uv_lock_hash(),
        rules_version=rules.rules_digest(config),
        ontology_version=inputs.ontology_version,
        schema_hash=_schema_hash(),
        code_hash=_code_hash(),
        input_files=tuple(
            (_repo_relative(p), hashlib.sha256(normalised_bytes(p.read_bytes())).hexdigest()) for p in paths
        ),
    )


def _dataset_node(config: Config) -> ox.NamedNode:
    """``<base>dataset`` — see the module docstring for why this shape was chosen over ``<graph_ns>dataset``."""
    return ox.NamedNode(config.iri.base + DATASET_LOCAL)


def _input_node(config: Config, repo_relative_path: str) -> ox.NamedNode:
    return ox.NamedNode(config.iri.graph_ns + INPUT_NODE_LOCAL_PREFIX + repo_relative_path)


def _provenance_quads(config: Config, provenance: Provenance) -> list[ox.Quad]:
    graph = ox.NamedNode(config.iri.graph_ns + PROVENANCE_GRAPH_LOCAL)
    dataset_node = _dataset_node(config)

    def onto(local: str) -> ox.NamedNode:
        return ox.NamedNode(config.iri.onto_ns + local)

    triples: list[tuple[ox.NamedNode, ox.NamedNode, ox.NamedNode | ox.Literal]] = [
        (dataset_node, emit.RDF_TYPE, PROV_ENTITY),
        (dataset_node, onto("inputHash"), ox.Literal(provenance.input_hash)),
        (dataset_node, onto("pipelineVersion"), ox.Literal(provenance.pipeline_version)),
        (dataset_node, onto("uvLockHash"), ox.Literal(provenance.uv_lock_hash)),
        (dataset_node, onto("rulesVersion"), ox.Literal(provenance.rules_version)),
        (dataset_node, emit.OWL_VERSION_INFO, ox.Literal(provenance.ontology_version)),
        (dataset_node, onto("schemaHash"), ox.Literal(provenance.schema_hash)),
        (dataset_node, onto("codeHash"), ox.Literal(provenance.code_hash)),
    ]
    for repo_relative_path, sha256_hex in provenance.input_files:
        node = _input_node(config, repo_relative_path)
        triples.append((dataset_node, PROV_WAS_DERIVED_FROM, node))
        triples.append((node, emit.RDF_TYPE, PROV_ENTITY))
        triples.append((node, DCTERMS_IDENTIFIER, ox.Literal(repo_relative_path)))
        triples.append((node, onto("sha256"), ox.Literal(sha256_hex)))
    return [ox.Quad(s, p, o, graph) for s, p, o in triples]


def _build_record_bytes(provenance: Provenance) -> bytes:
    record = {
        "code_hash": provenance.code_hash,
        "input_hash": provenance.input_hash,
        "ontology_version": provenance.ontology_version,
        "pipeline_version": provenance.pipeline_version,
        "rules_version": provenance.rules_version,
        "schema_hash": provenance.schema_hash,
        "uv_lock_hash": provenance.uv_lock_hash,
    }
    if set(record) != set(BUILD_JSON_KEYS):
        raise BuildError(f"build.json: keys {sorted(record)} do not match the documented set {sorted(BUILD_JSON_KEYS)}")
    return (json.dumps(record, sort_keys=True, indent=2) + "\n").encode("utf-8")


# =====================================================================================================
# Canonical output: full/itpra.nq (every graph) and base/<graph>.ttl (asserted graphs only)


def _turtle_prefixes(config: Config) -> dict[str, str]:
    return {
        "itpra": config.iri.id_ns,
        "itpra-o": config.iri.onto_ns,
        "itpra-g": config.iri.graph_ns,
        "rdf": emit.RDF,
        "rdfs": emit.RDFS,
        "owl": emit.OWL,
        "skos": emit.SKOS,
        "dcterms": DCTERMS,
        "prov": emit.PROV,
    }


def _base_graph_filename(graph_local: str) -> str:
    if graph_local in ("schema", "t1"):
        return f"{graph_local}.ttl"
    if graph_local.startswith("req/"):
        return f"{REQ_SUBDIRNAME}/{graph_local.removeprefix('req/')}.ttl"
    raise BuildError(f"build: unexpected asserted graph {graph_local!r} — not schema, t1 or req/<X>")


def _base_turtle_files(full_nquads: bytes, config: Config) -> dict[str, tuple[bytes, int]]:
    """Turtle-serialise every asserted graph (excluding ``inferred``/``provenance``) found in the already
    sorted canonical N-Quads bytes, preserving that sorted order (see the module docstring's Turtle-
    determinism finding). Returns ``{relative_path: (turtle_bytes, triple_count)}``."""
    graph_ns = config.iri.graph_ns
    excluded = {rules.INFERRED_GRAPH_LOCAL, PROVENANCE_GRAPH_LOCAL}
    by_graph: dict[str, list[ox.Triple]] = {}
    if full_nquads:
        for quad in ox.parse(input=full_nquads, format=ox.RdfFormat.N_QUADS):
            graph_value = quad.graph_name.value
            if not graph_value.startswith(graph_ns):
                continue
            local = graph_value[len(graph_ns) :]
            if local in excluded:
                continue
            by_graph.setdefault(local, []).append(ox.Triple(quad.subject, quad.predicate, quad.object))

    prefixes = _turtle_prefixes(config)
    files: dict[str, tuple[bytes, int]] = {}
    for local, triples in by_graph.items():
        data = ox.serialize(triples, format=ox.RdfFormat.TURTLE, prefixes=prefixes)
        if not data.endswith(b"\n"):
            data += b"\n"
        files[_base_graph_filename(local)] = (data, len(triples))
    return files


def _manifest_bytes(base_files: dict[str, tuple[bytes, int]]) -> bytes:
    manifest = {
        rel: {"quads": count, "sha256": hashlib.sha256(data).hexdigest()}
        for rel, (data, count) in base_files.items()
    }
    return (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")


# =====================================================================================================
# Store (ADR 0041 D5)


def _load_store(config: Config, full_nquads_path: Path) -> int:
    target = store_dir(config)
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    store = ox.Store(target)
    store.bulk_load(path=full_nquads_path, format=ox.RdfFormat.N_QUADS)
    store.flush()
    rows = list(store.query("SELECT (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?s ?p ?o } }"))
    count = int(rows[0]["n"].value)
    store.flush()
    del store  # releases the RocksDB lock immediately (0.5.11 has no context manager / close())
    return count


# =====================================================================================================
# BuildReport and build()


@dataclass(frozen=True)
class BuildReport:
    out_dir: Path
    graph_counts: dict[str, int]  # full graph IRI -> quad count, every graph incl. inferred/provenance
    inferred_counts: dict[str, int]  # per-rule triple counts (rules.RuleReport.counts)
    total_quads: int
    store_quad_count: int | None
    input_hash: str
    rules_version: str
    ontology_version: str
    elapsed: dict[str, float]  # emit, rules, canonicalise, write, load (seconds)


def build(config: Config | None = None, out_dir: Path | str | None = None, *, load_store: bool = True) -> BuildReport:
    """Emit, apply the rules, add a provenance graph, write the canonical artefacts, and (by default) load
    the disposable store. See the module docstring for the full recipe and every determinism finding."""
    config = config if config is not None else load_config()
    resolved_out = Path(out_dir).resolve() if out_dir is not None else dist_rdf_dir(config)
    timings: dict[str, float] = {}

    started = time.perf_counter()
    inputs = emit.load_inputs(config)
    asserted = emit.emit(inputs, config)
    timings["emit"] = time.perf_counter() - started

    started = time.perf_counter()
    rule_report = rules.apply_rules(asserted, config)
    timings["rules"] = time.perf_counter() - started

    started = time.perf_counter()
    provenance = compute_provenance(config, inputs)
    full_dataset = ox.Dataset()
    for quad in rule_report.dataset:
        full_dataset.add(quad)
    for quad in _provenance_quads(config, provenance):
        full_dataset.add(quad)

    graph_counts = dict(Counter(q.graph_name.value for q in full_dataset))
    total_quads = sum(graph_counts.values())

    full_bytes = canon.canonical_nquads(full_dataset)  # mutates full_dataset in place (RDFC-1.0); no blank
    # nodes are ever emitted by this pipeline (ADR 0041 D2), so canonicalisation only relabels nothing and
    # the counts taken above stay correct.
    base_files = _base_turtle_files(full_bytes, config)
    manifest_bytes = _manifest_bytes(base_files)
    build_record = _build_record_bytes(provenance)
    timings["canonicalise"] = time.perf_counter() - started

    started = time.perf_counter()
    if resolved_out.exists():
        shutil.rmtree(resolved_out)
    full_path = resolved_out / FULL_DIRNAME / FULL_FILENAME
    canon.write_bytes(full_path, full_bytes)
    for rel_path, (data, _count) in base_files.items():
        canon.write_bytes(resolved_out / BASE_DIRNAME / rel_path, data)
    canon.write_bytes(resolved_out / BASE_DIRNAME / MANIFEST_FILENAME, manifest_bytes)
    canon.write_bytes(resolved_out / BUILD_FILENAME, build_record)
    timings["write"] = time.perf_counter() - started

    store_quad_count: int | None = None
    started = time.perf_counter()
    if load_store:
        store_quad_count = _load_store(config, full_path)
        # The README documents this equality as asserted before build() returns, so it is enforced here:
        # a store-load bug (e.g. a bulk_load truncation) must not pass silently. store_quad_count is the
        # store's own post-load COUNT(*); total_quads is summed from the in-memory dataset that
        # full/itpra.nq was serialised from -- they must agree exactly.
        if store_quad_count != total_quads:
            raise BuildError(
                f"build: store quad count ({store_quad_count}) does not equal the {total_quads} total quads "
                f"written to {full_path}"
            )
    timings["load"] = time.perf_counter() - started

    return BuildReport(
        out_dir=resolved_out,
        graph_counts=graph_counts,
        inferred_counts=dict(rule_report.counts),
        total_quads=total_quads,
        store_quad_count=store_quad_count,
        input_hash=provenance.input_hash,
        rules_version=provenance.rules_version,
        ontology_version=provenance.ontology_version,
        elapsed=timings,
    )


# =====================================================================================================
# --check (the local form of the CI drift check)


def _tree_diff(reference_dir: Path, candidate_dir: Path) -> list[str]:
    """Human-readable differences between two directory trees (empty = identical). Mirrors
    ``itpra_onto.gen_artifacts._tree_matches``'s contract for the analogous ``gen-artifacts --check``."""
    if not reference_dir.exists():
        return [f"{reference_dir} is missing"]
    reference_files = {p.relative_to(reference_dir) for p in reference_dir.rglob("*") if p.is_file()}
    candidate_files = {p.relative_to(candidate_dir) for p in candidate_dir.rglob("*") if p.is_file()}
    diffs = [f"missing: {rel.as_posix()}" for rel in sorted(reference_files - candidate_files)]
    diffs += [f"unexpected: {rel.as_posix()}" for rel in sorted(candidate_files - reference_files)]
    for rel in sorted(reference_files & candidate_files):
        if (reference_dir / rel).read_bytes() != (candidate_dir / rel).read_bytes():
            diffs.append(f"stale: {rel.as_posix()}")
    return diffs


def check(config: Config | None = None, out_dir: Path | str | None = None) -> list[str]:
    """Build into a fresh temp directory (never touching the store) and diff its ``base/`` against
    ``<out>/base/``. Returns the list of differences (empty = up to date) — the local, filesystem form of
    the CI drift check (a plain directory diff, since ``dist/rdf/`` is never committed — ADR 0043 D5)."""
    config = config if config is not None else load_config()
    target_out = Path(out_dir).resolve() if out_dir is not None else dist_rdf_dir(config)
    with tempfile.TemporaryDirectory(prefix="itpra-onto-build-check-") as tmp:
        fresh_out = Path(tmp) / "rdf"
        build(config=config, out_dir=fresh_out, load_store=False)
        return _tree_diff(target_out / BASE_DIRNAME, fresh_out / BASE_DIRNAME)

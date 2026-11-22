"""Generate the derived LinkML schema artefacts (ADR 0041 D5).

From the LinkML authoring schema — loaded through :func:`itpra_onto.schema_loading.load_schema_definition`,
never from ``schema/itpra.linkml.yaml``'s path directly, because that module is where the schema's
sentinel ``id:`` is substituted for the value ``itpra-onto.toml`` ``[iri]`` computes (ADR 0004) — this
module writes five derived artefacts under ``<dist_dir>/schema/``
(``config.paths.dist_dir`` resolved against ``config.config_path.parent``, i.e. ``dist/schema/``;
``dist/`` is gitignored, never committed, always rebuilt):

* ``itpra.schema.json``  — LinkML's JSON Schema generator, re-serialised by this pipeline (sorted keys).
* ``itpra_models.py``    — LinkML's Pydantic generator, with the one non-deterministic field it embeds
                            (an absolute filesystem path) stripped — see :func:`_render_pydantic`.
* ``itpra.owl.nt``       — LinkML's OWL generator, canonicalised (RDFC-1.0) and sorted by this pipeline.
* ``itpra.shacl.nt``     — LinkML's SHACL generator, canonicalised the same way. gen-shacl 1.11.1 is
                            known to drop the schema's ``has_member`` / ``all_members`` JSON-Schema-only
                            checks (the "at least one grouped_by", "no derived_from on Function" rules) —
                            expected: the hand-written SHACL-SPARQL under ``shapes/`` covers them
                            (ADR 0042 D2), not this generator.
* ``doc/``               — LinkML's markdown documentation generator, one directory. Verified to already
                            emit deterministically for this schema (no timestamp, no path, byte-identical
                            across independent processes) — no post-processing needed.

**``itpra.owl.nt``/``itpra.shacl.nt`` describe the AUTHORING shape, not the emitted projection**
(ADR 0042 D2): they carry the range/cardinality axioms ADR 0041 D2 deliberately excludes from the published
ontology (:mod:`itpra_onto.emit`'s own ``schema`` graph asserts none of these), and the generated SHACL does
not validate the graph :func:`itpra_onto.emit.emit` actually produces (closed shapes, the ``relates_to``
pivot ``emit.py`` performs, ``xsd:string`` where the emitted graph carries ``@en``). The hand-written shapes
under ``shapes/`` are what validates the emitted graph; these two files document the authoring schema and
are not published as the ontology.

ADR 0041 D5: no released LinkML version (1.11.1) produces deterministic generator output on its own —
**this pipeline owns determinism**, not LinkML. That means checking each generator's raw output for
anything that varies run to run or machine to machine and neutralising it before anything is written;
this module's docstrings on ``_render_pydantic``, ``_render_owl`` and
``_deterministic_rdflib_blank_nodes`` record exactly what each generator needed and why -- most notably,
canonicalise-then-sort (the recipe ``tests/test_smoke.py`` established for blank-node-free data) is
NOT sufficient on its own for a graph with automorphic blank-node substructure: pyoxigraph 0.5.11's
RDFC-1.0 canonicalisation was found, empirically, to still depend on the *raw* (pre-canonicalisation)
blank node labels for such graphs (``itpra.shacl.nt`` has hundreds, mostly RDF-list nodes from repeated
identical ``sh:ignoredProperties`` / ``sh:in`` lists), even though it is a pure function of its input
(confirmed by canonicalising the same fixed raw text three times in three separate processes: always
byte-identical). LinkML's OWL/SHACL generators draw every blank node's label from ``rdflib.BNode()``,
which is ``uuid4().hex`` -- fresh and random every call -- so the fix is at the source, not after it:
``_deterministic_rdflib_blank_nodes()`` replaces that randomness with a monotonic counter for the
duration of one generator call, making the raw output (and therefore the canonicalised output) a
function of the schema alone. A second, independent source of the same symptom was found in
``ShaclGenerator._build_ignored_properties`` itself: it converts a Python ``set`` of property IRIs to a
``list`` with no sort before handing it to ``rdflib.collection.Collection`` (which encodes list *order*
as real RDF structure, one ``rdf:first``/``rdf:rest`` pair per position) — so a class with more than one
ignored property (e.g. ``skos:Concept``, base of all 13 term subclasses) gets its ``sh:ignoredProperties``
list in whatever order Python's per-process hash-randomised ``str`` iteration happens to produce, not
merely a relabelling difference. ``_deterministic_shacl_ignored_properties()`` patches that one method
for the duration of SHACL generation to sort before building the list; :func:`_render_shacl` applies both
context managers.

CLI: ``itpra-onto gen-artifacts [--check]`` (``src/itpra_onto/cli.py``, lazy import like the other
``gen-*`` subcommands). ``--check`` regenerates into a temp directory and exits 1 if anything differs
from (or ``dist/schema/`` is missing relative to) the committed... except ``dist/schema/`` is never
committed, so in practice ``--check`` compares against whatever was last generated on disk — the same
contract ``gen-enums --check`` / ``gen-prefixes --check`` have for their (committed) generated files,
reused here for a derived, gitignored directory instead.
"""

from __future__ import annotations

import contextlib
import itertools
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

import pyoxigraph as ox
from linkml.generators.docgen import DocGenerator
from linkml.generators.jsonschemagen import JsonSchemaGenerator
from linkml.generators.owlgen import OwlSchemaGenerator
from linkml.generators.pydanticgen import PydanticGenerator
from linkml.generators.shaclgen import ShaclGenerator
from linkml_runtime.utils.schemaview import SchemaView

from itpra_onto import canon, schema_loading
from itpra_onto.config import Config, load_config

PACKAGE_DIR = Path(__file__).resolve().parent  # src/itpra_onto: the package's own code and data

JSON_SCHEMA_FILENAME = "itpra.schema.json"
PYDANTIC_FILENAME = "itpra_models.py"
OWL_FILENAME = "itpra.owl.nt"
SHACL_FILENAME = "itpra.shacl.nt"
DOC_DIRNAME = "doc"

# LinkML's OwlSchemaGenerator (1.11.1) builds an enum permissible-value's IRI as
# f"{enum_class_uri}{enum_iri_separator}{permissible_value_name}", defaulting enum_iri_separator to "#".
# This pipeline's onto namespace (itpra-o:, <base>onto#) is itself hash-shaped, so an enum class's own
# class_uri is already .../onto#EntityTypeEnum; appending the default "#" again produces
# .../onto#EntityTypeEnum#Capability -- two unescaped "#" characters, which is not a valid IRI (RFC 3986:
# "#" may start a fragment at most once) and pyoxigraph's Turtle parser rejects it ("Invalid IRI code
# point '#'"). Confirmed empirically. "/" keeps the fragment single and valid:
# .../onto#EntityTypeEnum/Capability.
_OWL_ENUM_IRI_SEPARATOR = "/"

# PydanticGenerator (1.11.1) echoes SchemaDefinition.source_file back into the module-level `linkml_meta`
# dict verbatim. schema_loading.load_schema_definition() sets source_file to schema/itpra.linkml.yaml's
# own absolute path (so LinkML resolves its relative `imports:`) -- an absolute filesystem path that
# varies by machine/worktree, the one non-deterministic field this generator's raw output carries for
# this schema (confirmed empirically: no timestamp, no other absolute path, byte-identical otherwise
# across independent processes). pprint (which PydanticGenerator uses to render linkml_meta) never
# splits a single atomic string across lines, so the entry is always exactly one line; matched loosely
# enough (either quote style) to fail loudly via the call-site count check rather than silently no-op if
# a future linkml version changes the formatting.
_SOURCE_FILE_LINE = re.compile(r"^[ \t]*'source_file':\s*(['\"]).*?\1,[ \t]*\r?\n", re.MULTILINE)


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return str(path)


def dist_schema_dir(config: Config | None = None) -> Path:
    config = config if config is not None else load_config()
    return (config.config_path.parent / config.paths.dist_dir).resolve() / "schema"


class _CounterHex:
    """Stands in for ``uuid4()``'s return value: only ``.hex`` is read by ``rdflib.BNode.__new__``."""

    __slots__ = ("_n",)

    def __init__(self, n: int) -> None:
        self._n = n

    @property
    def hex(self) -> str:
        return f"{self._n:032x}"


@contextlib.contextmanager
def _deterministic_rdflib_blank_nodes():
    """Make every ``rdflib.BNode()`` created during the block deterministic (a monotonic counter in
    place of ``uuid4().hex``), then restore ``rdflib.term.uuid4`` on exit.

    LinkML's ``OwlSchemaGenerator`` / ``ShaclGenerator`` build their output as an in-memory ``rdflib.Graph``
    and mint a fresh ``rdflib.BNode()`` (``uuid4().hex`` -- random, every call) for every unnamed schema
    element (OWL restrictions, SHACL property shapes, RDF list nodes for ``sh:in`` / ``sh:ignoredProperties``).
    For a schema with automorphic blank-node substructure -- confirmed present in ``itpra.shacl.nt`` (many
    structurally-identical RDF-list nodes, e.g. every closed shape's ``sh:ignoredProperties ( rdf:type )``) --
    canonicalise-then-sort alone (the recipe ``canon.py`` otherwise relies on) is not sufficient: pyoxigraph
    0.5.11's RDFC-1.0 canonicalisation of such a graph was found to still vary with the *raw* blank node
    labels it was given, even though canonicalising the same fixed input text is itself perfectly
    reproducible (checked directly: the same raw Turtle canonicalises byte-identically across three separate
    processes). Removing the randomness at its source -- so the same schema always mints blank nodes in the
    same order with the same labels -- removes the dependency on canonicalisation resolving the automorphism
    at all.
    """
    import rdflib.term as rdflib_term

    counter = itertools.count()
    original_uuid4 = rdflib_term.uuid4
    rdflib_term.uuid4 = lambda: _CounterHex(next(counter))
    try:
        yield
    finally:
        rdflib_term.uuid4 = original_uuid4


@contextlib.contextmanager
def _deterministic_shacl_ignored_properties():
    """Patch ``ShaclGenerator._build_ignored_properties`` to sort before building the RDF list.

    The stock 1.11.1 implementation collects a class's ignored properties into a Python ``set`` of
    ``URIRef`` and hands ``list(that_set)`` straight to ``rdflib.collection.Collection`` — which encodes
    list membership *and order* as real ``rdf:first``/``rdf:rest`` triples. Python randomises ``str``
    hashing per process by default, so for any class with more than one ignored property (``skos:Concept``,
    the class every one of this schema's 13 term subclasses shares, is one: it picks up ``qa`` from ``NFR``
    among others) the list's element order — not just pyoxigraph's blank-node canonicalisation of it —
    varies from run to run. Confirmed empirically: pinning ``PYTHONHASHSEED`` made the
    raw generator output stable; sorting here removes the dependency on that environment variable instead
    of relying on it.
    """
    from rdflib import BNode, RDF, URIRef
    from rdflib.collection import Collection

    def patched(self, g, c):  # noqa: ANN001 - mirrors ShaclGenerator._build_ignored_properties's signature
        def collect_child_properties(class_name: str, output: set) -> None:
            for child_name in self.schemaview.class_children(class_name, imports=True, mixins=False, is_a=True):
                output.update(
                    URIRef(self.schemaview.get_uri(prop, expand=True))
                    for prop in self.schemaview.class_slots(child_name)
                )
                collect_child_properties(child_name, output)

        child_properties: set = set()
        collect_child_properties(c.name, child_properties)
        class_slot_uris = {
            URIRef(self.schemaview.get_uri(prop, expand=True)) for prop in self.schemaview.class_slots(c.name)
        }
        ignored_properties = child_properties.difference(class_slot_uris)
        list_node = BNode()
        ignored_properties.add(RDF.type)
        Collection(g, list_node, sorted(ignored_properties))
        return list_node

    original = ShaclGenerator._build_ignored_properties
    ShaclGenerator._build_ignored_properties = patched
    try:
        yield
    finally:
        ShaclGenerator._build_ignored_properties = original


def _merged_schemaview(config: Config) -> SchemaView:
    """A fresh ``SchemaView`` with its imports merged onto the ``SchemaDefinition`` in place.

    Only OWL generation needs this (see :func:`_render_owl`); every other generator is handed the plain
    schema straight from :func:`schema_loading.load_schema_definition`.
    """
    schema_definition = schema_loading.load_schema_definition(config=config)
    schema_view = SchemaView(schema_definition)
    schema_view.merge_imports()
    return schema_view


def _render_json_schema(config: Config) -> bytes:
    schema_definition = schema_loading.load_schema_definition(config=config)
    raw = JsonSchemaGenerator(schema_definition).serialize()
    data = json.loads(raw)
    text = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False)
    return (text + "\n").encode("utf-8")


def _render_pydantic(config: Config) -> bytes:
    schema_definition = schema_loading.load_schema_definition(config=config)
    raw = PydanticGenerator(schema_definition).serialize()
    cleaned, count = _SOURCE_FILE_LINE.subn("", raw)
    if count != 1:
        raise RuntimeError(
            "gen-artifacts: expected exactly one 'source_file' line in PydanticGenerator output "
            f"(found {count}) -- linkml's generator output shape may have changed; re-check "
            "itpra_onto.gen_artifacts._render_pydantic and its docstring"
        )
    if not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned.encode("utf-8")


def _render_owl(config: Config) -> bytes:
    schema_view = _merged_schemaview(config)
    # linkml 1.11.1's OwlSchemaGenerator prints (to stderr, via warnings.warn) DeprecationWarnings for
    # three flags that will default to True in a future release (skip_vacuous_min_zero_cardinality_axioms,
    # skip_vacuous_local_range_axioms, consolidate_cardinality_axioms); its own Deprecation.warn() forces
    # `warnings.filterwarnings("default", category=DeprecationWarning)` immediately before warning, so a
    # caller-side filter cannot silence it. Harmless noise, not part of the generated bytes: this pipeline
    # pins linkml==1.11.1 (pyproject.toml) and keeps today's defaults deliberately -- a version bump is its
    # own re-verification event (README "Dependency pins"), not something to silently opt into here.
    with _deterministic_rdflib_blank_nodes():
        raw = OwlSchemaGenerator(
            schema_view.schema,
            schemaview=schema_view,
            enum_iri_separator=_OWL_ENUM_IRI_SEPARATOR,
            # OwlSchemaGenerator's default (use_native_uris=True) MINTS a fresh IRI for every
            # class/slot from its Python name (e.g. onto#grouped_by -> onto#groupedBy would instead have
            # been left as-is, or worse, a slot whose slot_uri differs from its name would get an IRI
            # nothing else in this pipeline ever uses). False makes it use the schema's own DECLARED
            # class_uri/slot_uri throughout -- the same IRIs emit.py and every other generator use --
            # instead of a second, parallel OWL-only vocabulary.
            use_native_uris=False,
        ).serialize()
    return canon.canonical_ntriples(raw, ox.RdfFormat.TURTLE)


def _render_shacl(config: Config) -> bytes:
    schema_definition = schema_loading.load_schema_definition(config=config)
    with _deterministic_rdflib_blank_nodes(), _deterministic_shacl_ignored_properties():
        raw = ShaclGenerator(schema_definition).serialize()
    return canon.canonical_ntriples(raw, ox.RdfFormat.TURTLE)


def _write_doc(config: Config, doc_dir: Path) -> list[Path]:
    schema_definition = schema_loading.load_schema_definition(config=config)
    if doc_dir.exists():
        shutil.rmtree(doc_dir)
    doc_dir.mkdir(parents=True)
    DocGenerator(schema_definition, directory=str(doc_dir)).serialize(directory=str(doc_dir))
    return sorted(path for path in doc_dir.rglob("*") if path.is_file())


def generate(config: Config | None = None, out_dir: Path | None = None) -> list[Path]:
    """Write the five derived schema artefacts and return every file written, sorted.

    ``out_dir`` defaults to :func:`dist_schema_dir` (``dist/schema/``); a caller passes an explicit
    ``out_dir`` to generate into an isolated directory instead (tests; ``--check``).
    """
    config = config if config is not None else load_config()
    schema_dir = out_dir if out_dir is not None else dist_schema_dir(config)

    written: list[Path] = []

    json_schema_path = schema_dir / JSON_SCHEMA_FILENAME
    canon.write_bytes(json_schema_path, _render_json_schema(config))
    written.append(json_schema_path)

    pydantic_path = schema_dir / PYDANTIC_FILENAME
    canon.write_bytes(pydantic_path, _render_pydantic(config))
    written.append(pydantic_path)

    owl_path = schema_dir / OWL_FILENAME
    canon.write_bytes(owl_path, _render_owl(config))
    written.append(owl_path)

    shacl_path = schema_dir / SHACL_FILENAME
    canon.write_bytes(shacl_path, _render_shacl(config))
    written.append(shacl_path)

    written.extend(_write_doc(config, schema_dir / DOC_DIRNAME))

    return sorted(written)


def _tree_matches(reference_dir: Path, candidate_dir: Path) -> list[str]:
    """Return a list of human-readable differences (empty = identical trees)."""
    if not reference_dir.exists():
        return [f"{_relative(reference_dir)} is missing"]
    reference_files = {p.relative_to(reference_dir) for p in reference_dir.rglob("*") if p.is_file()}
    candidate_files = {p.relative_to(candidate_dir) for p in candidate_dir.rglob("*") if p.is_file()}
    diffs = [f"missing: {rel.as_posix()}" for rel in sorted(reference_files - candidate_files)]
    diffs += [f"unexpected: {rel.as_posix()}" for rel in sorted(candidate_files - reference_files)]
    for rel in sorted(reference_files & candidate_files):
        if (reference_dir / rel).read_bytes() != (candidate_dir / rel).read_bytes():
            diffs.append(f"stale: {rel.as_posix()}")
    return diffs


def main(check_only: bool = False) -> int:
    config = load_config()
    schema_dir = dist_schema_dir(config)

    if not check_only:
        written = generate(config, schema_dir)
        for path in written:
            print(f"gen-artifacts: wrote {_relative(path)}")
        return 0

    with tempfile.TemporaryDirectory(prefix="itpra-onto-gen-artifacts-check-") as tmp:
        fresh_dir = Path(tmp) / "schema"
        generate(config, fresh_dir)
        diffs = _tree_matches(schema_dir, fresh_dir)

    if diffs:
        print(
            f"gen-artifacts: {_relative(schema_dir)} is STALE or missing - run `itpra-onto gen-artifacts`",
            file=sys.stderr,
        )
        for line in diffs:
            print(f"  {line}", file=sys.stderr)
        return 1
    print(f"gen-artifacts: {_relative(schema_dir)} is up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main("--check" in sys.argv[1:]))

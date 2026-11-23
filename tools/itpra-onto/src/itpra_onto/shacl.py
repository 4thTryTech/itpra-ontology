"""SHACL validation harness (ADR 0042; ``shapes/REGISTER.md`` is the rule register the shapes implement).

This module is the *machinery* the three hand-written shape files (``structural``, ``crossfield``,
``requirements``; disjoint ownership, ADR 0042 D2) and the generated verb-pair file plug into. It creates
no shapes of its own beyond the tiny smoke pair under ``tests/fixtures/shapes-smoke/`` this package's own
tests use.

**Shape-file convention (every ``shapes/*.ttl`` file, and every ``tests/fixtures/shapes-smoke/*.ttl``
file, follows this — ``tests/test_iri_config.py``'s base-IRI literal scan already covers ``.ttl``):**

* A shape file declares **no** ``@prefix`` for ``itpra:``/``itpra-o:``/``itpra-g:`` (ADR 0004, the same
  discipline ``rules/*.rq`` already keeps): :func:`load_shapes` computes that block from
  :func:`itpra_onto.config.load_config` at load time and prepends it before parsing. A shape file also
  needs no ``@prefix`` for ``sh:``/``rdf:``/``rdfs:``/``skos:``/``owl:``/``xsd:``/``dcterms:``/``prov:`` —
  :func:`load_shapes` prepends those too (they are W3C/DCMI constants, not the base IRI, so ADR 0004
  does not forbid writing them literally, but supplying them centrally keeps every shape file identical in
  shape and lets a reviewer diff *content*, not boilerplate).
* **Every rule-bearing shape is a single, named (non-blank) node** carrying its target (``sh:targetClass``
  / ``sh:targetSubjectsOf`` / …), its path (if any), its constraint, ``sh:severity``, and
  ``itpra-o:ruleId`` directly — never nested inside a ``sh:property [ … ]`` blank node. This is a load-
  bearing convention, not a style preference: SHACL's own validation-report vocabulary
  (``sh:sourceShape``) names the shape that *declares* the firing constraint, and this harness reads
  ``itpra-o:ruleId`` off exactly that node (:func:`_extract_findings`). Confirmed empirically: a
  ``sh:sourceShape`` triple in pySHACL 0.40.1's results graph points at a named
  ``sh:PropertyShape``/``sh:NodeShape`` that carries ``sh:path`` and ``sh:targetClass`` directly, not at an
  anonymous ``sh:property [...]`` wrapper. A shape whose constraint genuinely needs a blank node
  (``sh:sparql [ a sh:SPARQLConstraint ; … ]``, the SHACL-SPARQL extension mechanism) still carries
  ``itpra-o:ruleId`` on the *outer* named shape — confirmed empirically that ``sh:sourceShape`` for a
  ``sh:sparql`` violation is that outer shape, not the ``sh:sparql`` blank node itself.
* **Every ``sh:sparql``/``sh:SPARQLConstraint`` node must set ``sh:prefixes`` to *something*** (any value —
  even a value with no ``sh:declare`` triples of its own). This is a pySHACL implementation detail, found
  empirically and worth stating plainly because it is easy to miss reading the SHACL
  spec alone: pySHACL's ``collect_prefixes()`` only augments the constraint's default ``rdf:``/``rdfs:``/
  ``owl:`` prefix set *at all* when the constraint node has an ``sh:prefixes`` triple present — and once it
  does, it pulls in the ``sh:declare`` triples of **every** ``owl:Ontology``-typed subject anywhere in the
  shapes graph, not just the one ``sh:prefixes`` names. :func:`load_shapes` exploits exactly this: it
  injects one synthetic ``owl:Ontology`` node (``itpra-o:shapesPrefixes``, never written to any ``.ttl``
  file — see below) carrying ``sh:declare`` triples for ``itpra:``/``itpra-o:``/``itpra-g:`` (computed from
  config, so the base IRI still names no shape file) plus the W3C constants, so **every** SPARQL constraint
  in the assembled shapes graph gets every one of these prefixes automatically, as long as it sets
  ``sh:prefixes`` to any node at all. The convention for a shape author: write
  ``sh:prefixes itpra-o:shapesPrefixes ;`` on every ``sh:sparql`` node (the node need not exist — this
  package injects it at load time; a shape file that already carries the real thing, e.g. because a test
  fixture doubles as documentation, still works).
* ``itpra-o:ruleId`` is the register's rule id (``shapes/REGISTER.md`` Table A, shared with the consumer's
  linter) or a Table-B id (``B-n``); ``sh:severity`` follows Table C (``sh:Violation`` for linter ``err``,
  ``sh:Warning`` for ``warn`` and the
  advisory candidate minimums). ``sh:message`` is free text for humans; ``itpra-o:ruleId`` is what
  ``itpra-onto parity`` compares.

**Shapes graph.** :func:`load_shapes` places every triple — from every ``shapes/*.ttl`` file (sorted by
name; ``REGISTER.md``/``README.md`` are not ``.ttl`` so the glob already excludes them) plus the synthetic
prefixes-declare resource — into the named graph ``<graph_ns>shapes`` (``shapes/REGISTER.md``'s "Shapes
graph" note). **Blank nodes are allowed inside shape files** (SHACL needs
them for ``sh:sparql [...]``, ``sh:in (...)``, etc.); each file is parsed with pyoxigraph's own
``rename_blank_nodes=True`` option (its documented purpose: "avoiding identifier conflicts when merging
graphs together"), so two shape files independently using an anonymous ``[...]`` can never collide once
merged into the shared shapes graph. **The shapes graph is therefore excluded from the RDFC
determinism claims ``itpra_onto.build`` makes for ``base/``** (ADR 0041 D2's "no blank nodes" is a
*data*-graph promise; shapes are validation inputs, versioned in git as their own source of truth, not
data) — ``build`` never writes the shapes graph into ``full/itpra.nq`` either:
shapes gain nothing by being canonicalised and re-serialised (they are already git-tracked Turtle, byte-
identical between two checkouts of the same commit), and ``validate`` loads them fresh, on demand, from
``shapes/*.ttl`` every run — never from a build artefact.

**pySHACL / multi-graph pyoxigraph.Store, resolved empirically:**

1. A raw :class:`pyoxigraph.Store` passed as pySHACL's ``data_graph`` is seen as the **union of every named
   graph it holds** — pySHACL does not restrict validation to the store's default graph, and there is no
   ``validate()`` parameter to restrict it to a *subset* of named graphs either (confirmed: a decoy graph
   left in the store is validated right alongside the intended one). So :func:`validate`'s ``graphs``
   selection is implemented by this module, not by pySHACL: :func:`_scratch_data_store` copies exactly the
   wanted named graphs' quads into a **fresh** :class:`pyoxigraph.Store`'s **default** graph (confirmed:
   pySHACL validates a store's default-graph content the same way as named-graph content — the "union"
   finding above holds regardless of which graph a triple started in) before handing that scratch store to
   pySHACL. Default selection (``graphs=None``): every graph locally named ``t1``, ``inferred``, or
   matching ``req/*`` that the input actually carries (``shapes/REGISTER.md``: shapes
   target ``t1``, ``req/*``, and, for the two ``inferred``-graph rows (B-18/B-19), ``inferred`` — never
   ``schema``: a shape's ``sh:targetClass`` matches on the ``rdf:type`` triples already asserted in the
   *data*, which needs no class-declaration triples from ``schema`` present at all, confirmed empirically).
2. pySHACL's ``shacl_graph`` parameter does **not** accept a raw :class:`pyoxigraph.Store`/``Dataset`` whose
   shapes live in a *named* (non-default) graph — it raises ``ValueError: Cannot determine the format of
   the input graph``. :func:`validate` instead serialises the assembled shapes graph to Turtle bytes
   (:func:`_shapes_turtle_bytes`) and passes those, with ``shacl_graph_format="turtle"`` — the one shape of
   ``shacl_graph`` confirmed to work cleanly against an Oxigraph-backed data graph.
3. ``advanced=True`` is required for ``sh:sparql``/``sh:SPARQLConstraint`` shapes to be evaluated at all
   (SHACL-SPARQL is part of the SHACL-Advanced Features engine in pySHACL's implementation, regardless of
   the 2017 Recommendation's own Core/SPARQL split); it is harmless to pass for a data graph with none.
   ``inference="none"`` always (ADR 0041 D4: no reasoner).

**A malformed ``sh:sparql`` query does not raise — pySHACL swallows it into a ``ValidationFailure`` object
in place of a results graph** (found empirically): a
``SHACL-SPARQL`` constraint's ``sh:select``/``sh:ask`` text may not contain a ``VALUES`` clause — pySHACL
rejects it with a SPARQL parse error — and ``pyshacl.validate()``'s own top-level ``try/except
ValidationFailure`` (``pyshacl/entrypoints.py``) turns that parse error into a *return value*, not a raised
exception: it returns ``(False, <ValidationFailure instance>, "Validation Failure - ...")`` instead of
``(conforms, <rdflib.Graph>, results_text)``. Confirmed empirically: an ``sh:select`` containing
``VALUES ?value { 1 2 3 }`` makes :func:`_extract_findings` crash with
``AttributeError: 'ValidationFailure' object has no attribute 'subjects'`` the moment it calls
``results_graph.subjects(...)`` on what it assumed was a graph. :func:`validate` checks for this case right
after calling ``pyshacl.validate()`` and raises :class:`ShaclError` with the failure's own message instead,
so a malformed shape file fails loudly and specifically rather than crashing inside result-extraction with
an unrelated ``AttributeError``. Write ``FILTER(?x IN (...))`` instead of ``VALUES`` in any
``sh:sparql``/``sh:SPARQLConstraint`` query in this package's shapes (``shapes/crossfield.ttl``'s
``B-13`` shape is the worked example).

**SHACL Core's ``sh:message`` is never placeholder-substituted by pySHACL 0.40.1 — only a
``sh:sparql``/``sh:SPARQLConstraint``'s own ``sh:message`` is.** Found empirically: pySHACL
only passes ``bound_vars`` (the values that fill in ``{?value}``/``{$this}`` etc.) to
``make_v_result`` when evaluating a ``SPARQLConstraintComponent``; no Core constraint component (``sh:minCount``,
``sh:pattern``, ``sh:class``, …) does the same, so a Core shape's ``sh:message`` containing a literal
``{?value}`` would render that placeholder text unsubstituted in the finding. Every Core shape in this
package's ``shapes/*.ttl`` therefore writes plain text naming the *field*, not the value (the finding's own
``sh:focusNode``/``sh:value`` already carry the offending id) — only a ``sh:sparql`` shape's ``sh:message``
uses ``{?value}``/``{$this}`` templating.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pyoxigraph as ox
import pyshacl
import rdflib
from pyshacl.errors import ValidationFailure as _PyshaclValidationFailure

from itpra_onto import emit
from itpra_onto.build import hash_contributions, normalised_bytes
from itpra_onto.config import Config, load_config

PACKAGE_DIR = Path(__file__).resolve().parent  # src/itpra_onto: the package's own code and data
SHAPES_DIR = PACKAGE_DIR / "shapes"

SHAPES_GRAPH_LOCAL = "shapes"
RULE_ID_LOCAL = "ruleId"  # itpra-o:ruleId — declared as an owl:AnnotationProperty in emit.py's schema graph
PREFIXES_RESOURCE_LOCAL = "shapesPrefixes"  # itpra-o:shapesPrefixes — synthetic owl:Ontology, sh:declare only

SH = "http://www.w3.org/ns/shacl#"
XSD = "http://www.w3.org/2001/XMLSchema#"
DCTERMS = "http://purl.org/dc/terms/"

# Every graph a default (graphs=None) validate() call includes: an exact-match local name, or a prefix.
_DEFAULT_EXACT_GRAPHS = ("t1", "inferred")
_DEFAULT_GRAPH_PREFIX = "req/"

# Severity local names (Table C) -> the consumer's linter's vocabulary ("error"/"warning"), so
# findings_as_set() is directly comparable to its `--json` (rule, subject, severity) rows.
SEVERITY_TO_LINTER = {"Violation": "error", "Warning": "warning", "Info": "info"}


class ShaclError(RuntimeError):
    """A shape file, or the shapes graph assembled from it, is malformed."""


# =====================================================================================================
# Loading shape files into the shapes graph


GENERATED_SUBDIR = "generated"  # shapes/generated/ — owned by itpra_onto.gen_verb_shapes


OVERLAY_SHAPE_FILES = frozenset({"requirements.ttl"})  # target req/*: loaded only with an [overlay] (ADR 0043 D1)


def shape_files(shapes_dir: Path = SHAPES_DIR, *, overlay: bool = True) -> list[Path]:
    """Every ``*.ttl`` file directly under ``shapes_dir`` (sorted by name), then every ``*.ttl`` file directly
    under ``shapes_dir/generated/`` (sorted by name).

    ``REGISTER.md``/``README.md`` are not ``.ttl`` so the glob excludes them without a separate allow-list.
    Not otherwise recursive: each hand-written shape file owns its rules outright (``shapes/REGISTER.md``;
    ADR 0042 D2), and ``generated/`` holds the files a generator owns
    (``generated/verb-pairs.ttl``, written by :mod:`itpra_onto.gen_verb_shapes` from the schema's
    ``itpra_verb`` annotations). A generated file follows the same conventions as a hand-written one — no
    ``@prefix`` block, no base IRI; this loader prepends both.
    """
    top = sorted(p for p in shapes_dir.glob("*.ttl") if overlay or p.name not in OVERLAY_SHAPE_FILES)
    return top + sorted((shapes_dir / GENERATED_SUBDIR).glob("*.ttl"))


def _standard_prefixes(config: Config) -> dict[str, str]:
    iri = config.iri
    return {
        "itpra": iri.id_ns,
        "itpra-o": iri.onto_ns,
        "itpra-g": iri.graph_ns,
        "sh": SH,
        "rdf": emit.RDF,
        "rdfs": emit.RDFS,
        "skos": emit.SKOS,
        "owl": emit.OWL,
        "xsd": XSD,
        "dcterms": DCTERMS,
        "prov": emit.PROV,
    }


def _turtle_prefix_block(prefixes: dict[str, str]) -> str:
    return "".join(f"@prefix {prefix}: <{ns}> .\n" for prefix, ns in prefixes.items())


def _prefix_declare_triples(config: Config, prefixes: dict[str, str]) -> list[tuple]:
    """The synthetic ``itpra-o:shapesPrefixes`` ``owl:Ontology`` node's ``sh:declare`` triples (module
    docstring point (c)): every one of :func:`_standard_prefixes`, computed from ``config`` — never written
    to any ``.ttl`` file, only injected here, into the in-memory shapes graph."""
    onto = ox.NamedNode(config.iri.onto_ns + PREFIXES_RESOURCE_LOCAL)
    rdf_type = ox.NamedNode(emit.RDF + "type")
    owl_ontology = ox.NamedNode(emit.OWL + "Ontology")
    sh_declare = ox.NamedNode(SH + "declare")
    sh_prefix = ox.NamedNode(SH + "prefix")
    sh_namespace = ox.NamedNode(SH + "namespace")
    xsd_any_uri = ox.NamedNode(XSD + "anyURI")
    triples: list[tuple] = [(onto, rdf_type, owl_ontology)]
    for prefix, ns in prefixes.items():
        bnode = ox.BlankNode()
        triples.append((onto, sh_declare, bnode))
        triples.append((bnode, sh_prefix, ox.Literal(prefix)))
        triples.append((bnode, sh_namespace, ox.Literal(ns, datatype=xsd_any_uri)))
    return triples


def load_shapes(shapes_dir: Path = SHAPES_DIR, config: Config | None = None) -> ox.Dataset:
    """Parse every ``shapes_dir/*.ttl`` and ``shapes_dir/generated/*.ttl`` file (:func:`shape_files`) plus the
    synthetic prefixes-declare resource into one :class:`pyoxigraph.Dataset`, every triple in the named graph
    ``<graph_ns>shapes``.

    The ``@prefix`` block (:func:`_standard_prefixes`) is prepended to each file's text before parsing —
    no shape file declares it (module docstring). Each file is parsed with ``rename_blank_nodes=True``
    (pyoxigraph's own documented mechanism for "avoiding identifier conflicts when merging graphs
    together"), so two shape files independently using an anonymous ``[...]`` can never collide once
    merged into the one shared shapes graph (module docstring).
    """
    config = config if config is not None else load_config()
    prefixes = _standard_prefixes(config)
    prefix_block = _turtle_prefix_block(prefixes)
    graph = ox.NamedNode(config.iri.graph_ns + SHAPES_GRAPH_LOCAL)

    dataset = ox.Dataset()
    for s, p, o in _prefix_declare_triples(config, prefixes):
        dataset.add(ox.Quad(s, p, o, graph))

    for path in shape_files(shapes_dir, overlay=config.overlay is not None):
        text = prefix_block + path.read_text(encoding="utf-8")
        try:
            parsed = ox.parse(
                input=text.encode("utf-8"),
                format=ox.RdfFormat.TURTLE,
                base_iri=config.iri.base,
                rename_blank_nodes=True,
            )
        except SyntaxError as exc:
            raise ShaclError(f"{path}: not valid Turtle: {exc}") from exc
        for quad in parsed:
            dataset.add(ox.Quad(quad.subject, quad.predicate, quad.object, graph))
    return dataset


def _shapes_turtle_bytes(shapes: ox.Dataset, config: Config) -> bytes:
    """Every triple in ``shapes``'s ``<graph_ns>shapes`` graph, as graph-less Turtle bytes — the one shape
    of pySHACL's ``shacl_graph`` parameter confirmed (module docstring point 2) to work against an
    Oxigraph-backed data graph."""
    graph = ox.NamedNode(config.iri.graph_ns + SHAPES_GRAPH_LOCAL)
    triples = [ox.Triple(q.subject, q.predicate, q.object) for q in shapes if q.graph_name == graph]
    return ox.serialize(triples, format=ox.RdfFormat.TURTLE, prefixes=_standard_prefixes(config))


def shapes_digest(shapes_dir: Path = SHAPES_DIR) -> str:
    """sha256 over the sorted shape files' bytes, LF-normalised, path-prefixed (:func:`hash_contributions`,
    the same recipe ``itpra_onto.build`` uses for ``input_hash``/``schema_hash``/``code_hash``) — the
    "shapes version" a future provenance record can carry."""
    return hash_contributions(
        (path.relative_to(shapes_dir).as_posix(), normalised_bytes(path.read_bytes())) for path in shape_files(shapes_dir)
    )


# =====================================================================================================
# Restricting the data graph pySHACL sees (module docstring point 1)


def _iter_all_quads(dataset_or_store: ox.Dataset | ox.Store):
    if isinstance(dataset_or_store, ox.Store):
        return dataset_or_store.quads_for_pattern(None, None, None, None)
    return iter(dataset_or_store)


def _graph_locals_present(dataset_or_store: ox.Dataset | ox.Store, config: Config) -> set[str]:
    graph_ns = config.iri.graph_ns
    locals_: set[str] = set()
    for quad in _iter_all_quads(dataset_or_store):
        graph_name = quad.graph_name
        if isinstance(graph_name, ox.NamedNode) and graph_name.value.startswith(graph_ns):
            locals_.add(graph_name.value[len(graph_ns) :])
    return locals_


def default_validation_graphs(dataset_or_store: ox.Dataset | ox.Store, config: Config | None = None) -> tuple[str, ...]:
    """Every named graph ``validate(graphs=None)`` includes: locally named ``t1``/``inferred``, or matching
    ``req/*`` — never ``schema``/``provenance`` (module docstring point 1)."""
    config = config if config is not None else load_config()
    present = _graph_locals_present(dataset_or_store, config)
    selected = {g for g in present if g in _DEFAULT_EXACT_GRAPHS or g.startswith(_DEFAULT_GRAPH_PREFIX)}
    return tuple(sorted(selected))


def _scratch_data_store(dataset_or_store: ox.Dataset | ox.Store, config: Config, graph_locals: Sequence[str]) -> ox.Store:
    """A fresh :class:`pyoxigraph.Store` holding exactly ``graph_locals``' quads, all in the default graph
    (module docstring point 1: pySHACL validates a store's default-graph content exactly like named-graph
    content, so this is a restriction mechanism, not a behavioural change)."""
    graph_ns = config.iri.graph_ns
    wanted = {graph_ns + local for local in graph_locals}
    scratch = ox.Store()
    for quad in _iter_all_quads(dataset_or_store):
        graph_name = quad.graph_name
        if isinstance(graph_name, ox.NamedNode) and graph_name.value in wanted:
            scratch.add(ox.Quad(quad.subject, quad.predicate, quad.object, ox.DefaultGraph()))
    return scratch


# =====================================================================================================
# Findings


@dataclass(frozen=True)
class Finding:
    rule_id: str | None
    focus: str
    severity: str  # "Violation" | "Warning" | "Info" (sh:resultSeverity's local name)
    message: str
    source_shape: str | None
    path: str | None


@dataclass(frozen=True)
class ValidationReport:
    conforms: bool
    findings: tuple[Finding, ...]
    results_text: str
    graphs: tuple[str, ...]  # the named graphs actually validated (module docstring point 1)


def focus_local_name(focus: str, config: Config | None = None) -> str:
    """``focus`` with the id namespace stripped, if it starts with one — the parity-comparable subject form
    (matching the consumer's linter's bare ids in its ``--json`` output)."""
    config = config if config is not None else load_config()
    id_ns = config.iri.id_ns
    return focus.removeprefix(id_ns) if focus.startswith(id_ns) else focus


_SH_RDF_TYPE = rdflib.RDF.type
_SH_VALIDATION_RESULT = rdflib.URIRef(SH + "ValidationResult")
_SH_FOCUS_NODE = rdflib.URIRef(SH + "focusNode")
_SH_RESULT_SEVERITY = rdflib.URIRef(SH + "resultSeverity")
_SH_RESULT_MESSAGE = rdflib.URIRef(SH + "resultMessage")
_SH_SOURCE_SHAPE = rdflib.URIRef(SH + "sourceShape")
_SH_RESULT_PATH = rdflib.URIRef(SH + "resultPath")


def _shape_rule_ids(shapes: ox.Dataset, config: Config) -> dict[str, str]:
    """``shape IRI -> its itpra-o:ruleId`` for every shape that has one, read off ``shapes`` directly (not
    off pySHACL's results graph, which never repeats a shape's own annotation triples)."""
    prop = ox.NamedNode(config.iri.onto_ns + RULE_ID_LOCAL)
    return {quad.subject.value: quad.object.value for quad in shapes.quads_for_predicate(prop)}


def _severity_local_name(uri: rdflib.URIRef | None) -> str:
    if uri is None:
        return "Violation"  # SHACL's own default (module docstring; matches sh:Violation's status as default)
    return str(uri).rsplit("#", 1)[-1]


def _extract_findings(results_graph: rdflib.Graph, shapes: ox.Dataset, config: Config) -> list[Finding]:
    shape_rule_ids = _shape_rule_ids(shapes, config)
    findings: list[Finding] = []
    for result in results_graph.subjects(_SH_RDF_TYPE, _SH_VALIDATION_RESULT):
        focus = results_graph.value(result, _SH_FOCUS_NODE)
        severity = results_graph.value(result, _SH_RESULT_SEVERITY)
        message = results_graph.value(result, _SH_RESULT_MESSAGE)
        source_shape = results_graph.value(result, _SH_SOURCE_SHAPE)
        path = results_graph.value(result, _SH_RESULT_PATH)
        rule_id = shape_rule_ids.get(str(source_shape)) if source_shape is not None else None
        findings.append(
            Finding(
                rule_id=rule_id,
                focus=str(focus) if focus is not None else "",
                severity=_severity_local_name(severity),
                message=str(message) if message is not None else "",
                source_shape=str(source_shape) if source_shape is not None else None,
                path=str(path) if path is not None else None,
            )
        )
    return findings


EMIT_ERROR_RULE_ID = "emit-error"
NO_RECORD_FOCUS = "(no record)"


def emit_error_finding(exc: emit.EmitError, config: Config | None = None, *, focus_id: str | None = None) -> Finding:
    """The synthetic finding an :class:`itpra_onto.emit.EmitError` becomes: rule ``emit-error``,
    severity ``Violation``, focus the offending record (``focus_id`` when given, else the error's own
    ``record_id``, else :data:`NO_RECORD_FOCUS`), message ``"<ExceptionClass>: <text>"`` — the class name is
    part of the message so a fixture can require a specific emit-time guard (``expect.emit_error``), not just
    any emit error on the same subject."""
    config = config if config is not None else load_config()
    record_id = focus_id if focus_id is not None else getattr(exc, "record_id", None)
    focus = config.iri.id_ns + record_id if record_id else NO_RECORD_FOCUS
    return Finding(
        rule_id=EMIT_ERROR_RULE_ID,
        focus=focus,
        severity="Violation",
        message=f"{type(exc).__name__}: {exc}",
        source_shape=None,
        path=None,
    )


def findings_as_set(report: ValidationReport, config: Config | None = None) -> set[tuple[str | None, str, str]]:
    """``report.findings`` as ``{(rule_id, focus_local_name, severity)}`` — the parity-comparable form,
    matching the consumer's linter's ``(rule, subject, severity)`` ``--json`` rows (``severity`` mapped
    through :data:`SEVERITY_TO_LINTER` to the linter's ``"error"``/``"warning"`` vocabulary, since that is
    what ``itpra-onto parity`` sets its identity test against)."""
    config = config if config is not None else load_config()
    return {
        (finding.rule_id, focus_local_name(finding.focus, config), SEVERITY_TO_LINTER.get(finding.severity, finding.severity.lower()))
        for finding in report.findings
    }


# =====================================================================================================
# validate()


def validate(
    dataset_or_store: ox.Dataset | ox.Store,
    shapes: ox.Dataset | None = None,
    *,
    config: Config | None = None,
    graphs: Sequence[str] | None = None,
) -> ValidationReport:
    """Run pySHACL over ``dataset_or_store`` restricted to ``graphs`` (default: :func:`default_validation_graphs`)
    against ``shapes`` (default: :func:`load_shapes` from :data:`SHAPES_DIR`).

    ``advanced=True`` (SHACL-SPARQL), ``inference="none"`` (ADR 0041 D4: no reasoner) — see the module
    docstring's three numbered empirical findings for why the implementation looks like this.
    """
    config = config if config is not None else load_config()
    if shapes is None:
        shapes = load_shapes(config=config)
    graph_locals = tuple(graphs) if graphs is not None else default_validation_graphs(dataset_or_store, config)

    scratch = _scratch_data_store(dataset_or_store, config, graph_locals)
    shapes_bytes = _shapes_turtle_bytes(shapes, config)

    conforms, results_graph, results_text = pyshacl.validate(
        scratch,
        shacl_graph=shapes_bytes,
        shacl_graph_format="turtle",
        advanced=True,
        inference="none",
    )
    if isinstance(results_graph, _PyshaclValidationFailure):
        # pySHACL does not raise for a malformed shape (e.g. VALUES inside a SHACL-SPARQL constraint) — it
        # returns a ValidationFailure object in place of a results graph (module docstring). Raise here,
        # with the failure's own message, instead of letting _extract_findings crash on
        # `results_graph.subjects(...)` with an unrelated AttributeError.
        raise ShaclError(str(results_graph))
    findings = _extract_findings(results_graph, shapes, config)
    return ValidationReport(conforms=conforms, findings=tuple(findings), results_text=results_text, graphs=graph_locals)

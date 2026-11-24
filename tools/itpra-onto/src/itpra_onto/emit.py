"""Emit the authored YAML as RDF quads in named graphs (ADR 0041).

Modelling (ADR 0041 D2): every term record is a ``skos:Concept`` in one concept scheme, with
its authored fields as literals; the EntityType records form a thin ``owl:Class`` layer; each relationship
verb is an ``owl:ObjectProperty`` and every ``relates_to`` edge becomes one triple on that predicate; a
record's ``source`` is kept verbatim and the ``ADR NNNN`` references in it (the grammar is ADR 0005's) become
``itpra-o:decidedIn`` links; a retired record (ADR 0048) keeps every triple and gains ``owl:deprecated``, the
version that retired it and its successor; no blank node is ever emitted. EntityType ``relates_to`` entries are schema
statements (ADR 0008) and are never emitted. Identifiers (ADR 0004): ``<base>id/<id>`` for records,
``<base>onto#`` for the schema vocabulary, ``<base>graph/`` for the named graphs.

Inputs (read-only): the vocabulary's term files under ``[paths] ontology_dir`` (:func:`term_files`) and
``schema.yaml`` itself (only for ``ontology_version``). Every path passes :func:`guard_input_path` before it
is opened (ADR 0043 D1).

Output: an in-memory :class:`pyoxigraph.Dataset`; nothing is written to disk here (that is ``build``).
Graphs (ADR 0041 D3): ``<graph_ns>schema`` (thin OWL) and ``<graph_ns>t1`` (every term record). The
default graph stays empty; ``inferred`` is written only by :mod:`itpra_onto.rules`.

IRI discipline (ADR 0004): no base IRI appears in this module. Record, schema-vocabulary and graph IRIs
come from :class:`itpra_onto.config.IriConfig`; every predicate and class for an authored field or verb is
the ``slot_uri`` / ``class_uri`` the LinkML schema declares, expanded through its namespace map. Only the
W3C/DCMI vocabularies below are module constants.
"""

from __future__ import annotations

import glob
import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyoxigraph as ox
import yaml
from linkml_runtime.utils.schemaview import SchemaView

from itpra_onto import schema_loading
from itpra_onto.authoring import TERM_BASE_CLASS, discriminator_map
from itpra_onto.config import Config, load_config


# ---- standard vocabularies (W3C/DCMI constants, not the base IRI; ADR 0004) ----------------------------
RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
RDFS = "http://www.w3.org/2000/01/rdf-schema#"
OWL = "http://www.w3.org/2002/07/owl#"
SKOS = "http://www.w3.org/2004/02/skos/core#"
PROV = "http://www.w3.org/ns/prov#"
DCTERMS = "http://purl.org/dc/terms/"
XSD = "http://www.w3.org/2001/XMLSchema#"

RDF_TYPE = ox.NamedNode(RDF + "type")
RDFS_LABEL = ox.NamedNode(RDFS + "label")
RDFS_COMMENT = ox.NamedNode(RDFS + "comment")
RDFS_SUBCLASS_OF = ox.NamedNode(RDFS + "subClassOf")
RDFS_SUBPROPERTY_OF = ox.NamedNode(RDFS + "subPropertyOf")
RDFS_SEE_ALSO = ox.NamedNode(RDFS + "seeAlso")
OWL_ONTOLOGY = ox.NamedNode(OWL + "Ontology")
OWL_CLASS = ox.NamedNode(OWL + "Class")
OWL_OBJECT_PROPERTY = ox.NamedNode(OWL + "ObjectProperty")
OWL_ANNOTATION_PROPERTY = ox.NamedNode(OWL + "AnnotationProperty")
OWL_DATATYPE_PROPERTY = ox.NamedNode(OWL + "DatatypeProperty")
OWL_VERSION_IRI = ox.NamedNode(OWL + "versionIRI")
OWL_VERSION_INFO = ox.NamedNode(OWL + "versionInfo")
OWL_DEPRECATED = ox.NamedNode(OWL + "deprecated")
SKOS_CONCEPT = ox.NamedNode(SKOS + "Concept")
SKOS_CONCEPT_SCHEME = ox.NamedNode(SKOS + "ConceptScheme")
SKOS_IN_SCHEME = ox.NamedNode(SKOS + "inScheme")
PROV_WAS_INFLUENCED_BY = ox.NamedNode(PROV + "wasInfluencedBy")
DCTERMS_LICENSE = ox.NamedNode(DCTERMS + "license")
TRUE = ox.Literal("true", datatype=ox.NamedNode(XSD + "boolean"))

# The licence of the vocabulary and every projection of it (ADR 0002), declared in each projection's header:
# the ontology and concept-scheme nodes here, the dataset node of a build's provenance graph.
LICENCE = ox.NamedNode("https://creativecommons.org/licenses/by/4.0/")

LANG = "en"  # labels, definitions and statements are English; nothing else is tagged

# ---- names this module adds under itpra-o: (not LinkML slots; declared in the schema graph) --------------
DECIDED_IN = "decidedIn"
AMENDED_BY = "amendedBy"
EXTENDED_BY = "extendedBy"
AUTHORING_FILE = "authoringFile"

# ---- rule-derived vocabulary (ADR 0041 D4) — declared here so it is discoverable from the schema graph,
# but NEVER asserted by this module: only rules/*.rq mints these, into the `inferred` graph. Each rule id
# below is the manifest entry (rules/manifest.yaml) that produces the property or class of the same key.
DERIVED_PROPERTY_RULES = {
    "inPlane": ("in plane", "capability-in-plane"),
    "inServiceDomain": ("in service domain", "capability-in-service-domain"),
    "inDomain": ("in domain", "function-in-domain"),
}
BOUNDARY_GOVERNED_FUNCTION = "BoundaryGovernedFunction"
BOUNDARY_GOVERNED_FUNCTION_RULE = "boundary-governed-function"
DERIVED_COMMENT = "derived by rule {rule}; never asserted"

# ---- provenance vocabulary (ADR 0043 D3) — declared here so the datatype
# properties a built dataset's provenance record (<graph_ns>provenance) carries are discoverable from the
# schema graph, but NEVER asserted by this module: only itpra_onto.build writes them, and only into the
# provenance graph, at build time.
PROVENANCE_PROPERTY_LABELS = {
    "sha256": "sha256",
    "inputHash": "input hash",
    "pipelineVersion": "pipeline version",
    "environmentHash": "environment hash",
    "rulesVersion": "rules version",
    "schemaHash": "schema hash",
    "codeHash": "code hash",  # identifies the pipeline code itself, not just its inputs
}

# ---- validation vocabulary (shapes/REGISTER.md) — declared here so it is discoverable from the schema
# graph like every other predicate this pipeline mints, but NEVER asserted by this module: only
# shapes/*.ttl carries itpra-o:ruleId triples, on shape nodes, never on data.
RULE_ID = "ruleId"

SCHEME_LOCAL = "scheme/t1"  # safe because no record id contains "/" (the id pattern, ADR 0004)
ADR_LOCAL_PREFIX = "ADR-"  # schema.yaml id.conventions.adr_instance "ADR-<NNNN>"; reserved prefix ADR
META_SUBJECT_TYPE = "EntityType"  # relates_to on these records are meta-edges (schema statements), never emitted
ENTITY_TYPE_CLASS = "EntityType"
RELATIONSHIP_TYPE_CLASS = "RelationshipType"

ONTOLOGY_LABEL = "ITPRA ontology"
SCHEMA_LABELS = {  # English rdfs:label for schema-namespace terms that have no authored term record
    ENTITY_TYPE_CLASS: "entity type",
    RELATIONSHIP_TYPE_CLASS: "relationship type",
    "deprecated": "banned label",
    DECIDED_IN: "decided in",
    AMENDED_BY: "amended by",
    EXTENDED_BY: "extended by",
    AUTHORING_FILE: "authoring file",
    "retired": "retired in",
}

try:  # the C loader parses the same YAML 1.1 as SafeLoader, several times faster
    _YAML_LOADER: type = yaml.CSafeLoader
except AttributeError:  # pragma: no cover - pyyaml built without libyaml
    _YAML_LOADER = yaml.SafeLoader


# =====================================================================================================
# Input-path guard (ADR 0043 D1: the build reads the inputs it is given, under the repository root)

# Generated output is never an input: dist/, public/ and __pycache__/ are refused at ANY depth, matched
# case-insensitively against every directory component. A caller may name further directories to refuse.
FORBIDDEN_DIR_NAMES = frozenset({"dist", "public", "__pycache__"})


class InputPathError(RuntimeError):
    """An input path the emitter must not read (ADR 0043 D1): generated output, a hidden tree, or an
    excluded directory."""


class EmitError(RuntimeError):
    """The authored data or the schema cannot be projected as specified (a bug or a stale schema).

    ``record_id`` names the offending record when the defect belongs to one, so a caller that
    turns the error into a finding (``itpra-onto validate``, ``itpra-onto parity``, the fixture harness) can
    report it on that subject; ``None`` for a file-level or schema-level defect."""

    def __init__(self, message: str, *, record_id: str | None = None) -> None:
        super().__init__(message)
        self.record_id = record_id


class SourceGrammarError(EmitError):
    """A ``source`` item naming ``ADR`` does not match the strict grammar ADR 0005 states."""


def guard_input_path(path: Path, *, repo_root: Path, is_file: bool = True, excluded: Iterable[str] = ()) -> Path:
    """Return ``path`` resolved, or raise :class:`InputPathError` naming the path and the violated rule.

    Rules (ADR 0043 D1): (a) under ``repo_root`` (``Config.repo_root``); (b) no component, relative to the
    root, beginning with ``.`` (``.git/``, ``.venv/``, ``.store/``, worktrees); (c) not under any directory
    named (case-insensitively) ``dist``, ``public`` or ``__pycache__``, nor one of ``excluded``, at ANY
    depth; (d) a file must be ``.yaml``. Directories and glob patterns are checked against (a)–(c).
    """
    resolved = Path(os.path.abspath(path)) if _is_glob(path) else path.resolve()
    repo_root = repo_root.resolve()
    if not resolved.is_relative_to(repo_root):
        raise InputPathError(f"{resolved}: rule (a) - input lies outside the repository root {repo_root}")
    parts = resolved.relative_to(repo_root).parts
    dirs = parts[:-1] if is_file else parts
    hidden = [p for p in parts if p.startswith(".")]
    if hidden:
        raise InputPathError(f"{resolved}: rule (b) - path component {hidden[0]!r} begins with '.'")
    refused = FORBIDDEN_DIR_NAMES | {name.lower() for name in excluded}
    offending = next((p for p in dirs if p.lower() in refused), None)
    if offending is not None:
        raise InputPathError(f"{resolved}: rule (c) - input lies under a directory named {offending!r}")
    if is_file and resolved.suffix != ".yaml":
        raise InputPathError(f"{resolved}: rule (d) - input is not a .yaml file")
    return resolved


def _is_glob(path: Path) -> bool:
    return glob.has_magic(str(path))


# =====================================================================================================
# Inputs


@dataclass(frozen=True)
class TermRecord:
    """One record of a term file of the vocabulary, tagged with its authoring file: the file's path relative
    to the vocabulary's directory (:func:`vocabulary_label`), the same wherever the vocabulary is checked out
    or vendored."""

    record: dict[str, Any]
    file: str


@dataclass(frozen=True)
class Inputs:
    terms: tuple[TermRecord, ...]
    ontology_version: str


def _config_relative(config: Config, configured: str) -> Path:
    """Resolve a ``[paths]`` value against the config file's directory, as :mod:`itpra_onto.authoring` does."""
    return config.config_path.parent / configured


def ontology_dir(config: Config) -> Path:
    return guard_input_path(_config_relative(config, config.paths.ontology_dir), repo_root=config.repo_root, is_file=False)


def schema_file(config: Config) -> Path:
    """``schema.yaml`` of the vocabulary, guarded."""
    return guard_input_path(ontology_dir(config) / "schema.yaml", repo_root=config.repo_root)


def term_files(config: Config | None = None) -> list[Path]:
    """The vocabulary's files (ontology ADR 0007): every ``*.yaml`` directly under the ontology dir except
    ``schema.yaml`` and ``PIN.yaml`` (the pin file of a vendored copy, ADR 0003), then every ``*.yaml`` under
    ``terms/``. Not recursive beyond that, so an ontology dir that is a repository root does not sweep up
    tooling."""
    config = config if config is not None else load_config()
    root = ontology_dir(config)
    top = sorted(p for p in root.glob("*.yaml") if p.name not in ("schema.yaml", "PIN.yaml"))
    terms = sorted((root / "terms").glob("*.yaml")) if (root / "terms").is_dir() else []
    return [guard_input_path(p, repo_root=config.repo_root) for p in top + terms]


def _load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.load(fh, Loader=_YAML_LOADER)  # noqa: S506 - a safe loader


def _repo_relative(path: Path, repo_root: Path) -> str:
    """``path`` as the posix label relative to ``repo_root`` (:attr:`Config.repo_root`)."""
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def vocabulary_label(path: Path, config: Config) -> str:
    """``path`` — a file of the vocabulary — as its posix path relative to the vocabulary's directory
    (``terms/planes.yaml``, ``schema.yaml``). This is the label a record's ``authoringFile`` and the build's
    provenance carry: it does not depend on where a consumer keeps its copy, so a build of a vendored copy
    reproduces the published one (ADR 0043 D3-D4)."""
    return path.resolve().relative_to(ontology_dir(config).resolve()).as_posix()


def _shown(path: Path, repo_root: Path | None) -> str:
    """``path`` repo-relative when it is inside the repository (every guarded input is), else as given."""
    if repo_root is None:
        return str(path)
    resolved = path.resolve()
    root = repo_root.resolve()
    return resolved.relative_to(root).as_posix() if resolved.is_relative_to(root) else str(path)


def _term_file_records(path: Path, repo_root: Path | None = None) -> list[dict[str, Any]]:
    """The records of one term file: a file whose top level is not a list, or a list entry that is not a
    mapping, is an :class:`EmitError` naming the file (never a ``TypeError`` from iterating a mapping key
    by key)."""
    data = _load_yaml(path)
    if data is None:
        return []
    if not isinstance(data, list):
        raise EmitError(f"{_shown(path, repo_root)}: a term file must be a top-level list of records, got {type(data).__name__}")
    for index, record in enumerate(data):
        if not isinstance(record, dict):
            raise EmitError(f"{_shown(path, repo_root)}: record [{index}] is not a mapping: {record!r}")
    return data


def load_inputs(config: Config | None = None) -> Inputs:
    """Read every term record, each tagged with its authoring file."""
    config = config if config is not None else load_config()
    root = config.repo_root
    terms = tuple(
        TermRecord(record, vocabulary_label(path, config))
        for path in term_files(config)
        for record in _term_file_records(path, root)
    )
    version = str(_load_yaml(schema_file(config))["ontology_version"])
    return Inputs(terms=terms, ontology_version=version)


# =====================================================================================================
# The `source` grammar (schema.yaml `fields.source` comment; ADR 0005)

_ADR_REF = re.compile(r"\bADR (\d+)\b")
_TAIL = re.compile(r"\((amended|extended) by ([^)]*)\)")

# ADR 0005 states a grammar for a `source` item that names an ADR: exactly ``ADR NNNN``, optionally
# followed by ONE amend/extend tail listing one or more further ADRs by number, comma-separated.
# `_ITEM_MENTIONS_ADR` is the loose, case-insensitive substring test that decides whether an item is even a
# candidate ADR reference (vs. an external citation, which is never checked against the strict grammar);
# `_STRICT_ADR_ITEM` is the grammar itself, checked with `fullmatch` against the item's own text (already
# whitespace-normalised and stripped). A hyphen (`ADR-0012`), a plural (`ADRs 0012`), a bare parenthetical
# with no leading `ADR NNNN` (`(superseded by ADR 0099)`, `(Amended by ADR 0012)`), or two tails mixed by a
# semicolon INSIDE the parens (`ADR 0007 (amended by ADR 0012; extended by ADR 0041)` -- the semicolon here
# is not a top-level item separator, see `_split_top_level_items`) all fail this grammar and are refused
# loudly rather than silently parsed as an external citation or silently dropped.
_ITEM_MENTIONS_ADR = re.compile(r"adr", re.IGNORECASE)
# A record of ANOTHER project -- another repository's decision record included -- is cited as any citable
# reference would be: free text carrying its URL (ADR 0005). Such an item is external in its
# entirety, is never a `decidedIn` link, and is exempt from the strict local grammar whatever it mentions.
# A bare `ADR NNNN` therefore always means the record of that number in the repository the file lives in.
_EXTERNAL_URL = re.compile(r"https?://\S+")
_STRICT_ADR_ITEM = re.compile(r"^ADR \d+(?: \((?:amended|extended) by ADR \d+(?:, ADR \d+)*\))?$")


def _split_top_level_items(text: str) -> list[str]:
    """Split ``text`` on ``;`` at paren-depth 0 only, so a ``;`` inside an amend/extend tail's parenthetical
    never splits one item into two (the grammar's ``;``-separated items are always top-level)."""
    items: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        if ch == ";" and depth == 0:
            items.append("".join(current))
            current = []
        else:
            current.append(ch)
    items.append("".join(current))
    return [item.strip() for item in items if item.strip()]


@dataclass(frozen=True)
class ParsedSource:
    """ADR links found in one ``source`` string, as ``ADR-NNNN`` local names, in order of first mention.

    ``decided_in`` holds every ADR mentioned anywhere (ADR 0041 D2: a justification link);
    ``amended_by`` / ``extended_by`` hold those named inside an "(amended by …)" / "(extended by …)" tail;
    ``external`` holds the ``;``-separated items that cite no local ADR -- an industry framework or standard,
    or another project's record carrying its URL (ADR 0005); they stay in ``dcterms:source`` only.
    """

    decided_in: tuple[str, ...] = ()
    amended_by: tuple[str, ...] = ()
    extended_by: tuple[str, ...] = ()
    external: tuple[str, ...] = ()


def adr_local_name(number: str) -> str:
    """``ADR-`` + the decision number zero-padded to four digits (schema.yaml ``adr_instance``)."""
    return f"{ADR_LOCAL_PREFIX}{int(number):04d}"


def _adrs_in(text: str) -> list[str]:
    return [adr_local_name(n) for n in _ADR_REF.findall(text)]


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def parse_source(text: str, *, record_id: str | None = None) -> ParsedSource:
    """Parse a ``source`` value: ``;``-separated items, each ``ADR NNNN`` with an optional amend/extend tail,
    or a free-text external citation (which may itself carry a parenthetical).

    Every item that mentions ``ADR`` (case-insensitive, anywhere in the item) must match the strict
    ``ADR NNNN`` grammar (ADR 0005) exactly, or :class:`SourceGrammarError` is raised naming ``record_id``
    (when given) and the offending item verbatim -- an item is never silently reclassified as
    an external citation just because it fails the grammar.
    """
    text = normalise_text(text)
    items = _split_top_level_items(text)
    local_items: list[str] = []
    external_items: list[str] = []
    for item in items:
        if _EXTERNAL_URL.search(item):
            external_items.append(item)  # another project's record, cited with its URL (ADR 0005)
            continue
        if _ITEM_MENTIONS_ADR.search(item) and not _STRICT_ADR_ITEM.fullmatch(item):
            where = f"{record_id}: " if record_id else ""
            raise SourceGrammarError(
                f"{where}source item {item!r} does not match the strict ADR grammar (ADR 0005): "
                r"expected 'ADR NNNN' (a record of this repository's own decision sequence) optionally followed by one "
                r"'(amended|extended by ADR NNNN[, ADR NNNN...])' tail; another project's record is cited as free text "
                r"carrying its URL",
                record_id=record_id,
            )
        (local_items if _ADR_REF.search(item) else external_items).append(item)
    local_text = "; ".join(local_items)
    tails: dict[str, list[str]] = {"amended": [], "extended": []}
    for kind, names in _TAIL.findall(local_text):
        tails[kind].extend(_adrs_in(names))
    return ParsedSource(
        decided_in=_unique(_adrs_in(local_text)),
        amended_by=_unique(tails["amended"]),
        extended_by=_unique(tails["extended"]),
        external=tuple(external_items),
    )


def normalise_text(value: Any) -> str:
    """Collapse every whitespace run (incl. newlines from folded scalars) to one space, then strip."""
    return " ".join(str(value).split())


# =====================================================================================================
# Vocabulary: every itpra IRI, read from the config and the LinkML schema


class Vocabulary:
    """Predicates, classes and graph names for one config (ADR 0004) and one schema view.

    Field predicates and verb properties are the ``slot_uri`` the schema declares; the term ``type`` ->
    class table pins each value to a ``Term`` subclass exactly as the authoring validator dispatches
    records, then takes that subclass's ``class_uri`` (never a string transform of the value).
    """

    def __init__(self, config: Config, schema_view: SchemaView) -> None:
        self.config = config
        self.sv = schema_view
        self.sv.imports_closure()
        self._check_namespaces()
        self.term_class = self._class_table(TERM_BASE_CLASS, "type")
        self.verb_slots = sorted(n for n, s in self.sv.all_slots().items() if "verbs" in (s.in_subset or []))
        self.verb = {name: self.slot_iri(name) for name in self.verb_slots}

    def _check_namespaces(self) -> None:
        namespaces = self.sv.namespaces()
        iri = self.config.iri
        expected = {"itpra": iri.id_ns, "itpra-o": iri.onto_ns, "itpra-g": iri.graph_ns}
        stale = {k: namespaces.get(k) for k, v in expected.items() if namespaces.get(k) != v}
        if stale:
            raise EmitError(
                f"schema prefixes {stale} differ from {self.config.config_path} [iri]; run `itpra-onto gen-prefixes`"
            )

    def expand(self, curie: str) -> ox.NamedNode:
        expanded = self.sv.expand_curie(curie)
        if expanded == curie:
            raise EmitError(f"cannot expand {curie!r} through the schema's namespace map")
        return ox.NamedNode(expanded)

    def slot_iri(self, slot_name: str) -> ox.NamedNode:
        return self.expand(self.sv.get_slot(slot_name).slot_uri)

    def class_iri(self, class_name: str) -> ox.NamedNode:
        return self.expand(self.sv.get_class(class_name).class_uri)

    def _class_table(self, base_class: str, slot_name: str) -> dict[str, ox.NamedNode]:
        pins = discriminator_map(self.sv, base_class, slot_name)
        return {value: self.class_iri(cls_name) for value, cls_name in pins.items()}

    def id(self, local: str) -> ox.NamedNode:
        return ox.NamedNode(self.config.iri.id_ns + local)

    def onto(self, local: str) -> ox.NamedNode:
        return ox.NamedNode(self.config.iri.onto_ns + local)

    def graph(self, local: str) -> ox.NamedNode:
        return ox.NamedNode(self.config.iri.graph_ns + local)

    @property
    def scheme(self) -> ox.NamedNode:
        return self.id(SCHEME_LOCAL)

    @property
    def ontology(self) -> ox.NamedNode:
        return ox.NamedNode(self.config.iri.onto_ns.removesuffix("#"))


# Characters that cannot appear in an IRI (RFC 3987 excludes controls, space and <>"{}|\^`). A
# record id or reference containing one is refused as an EmitError before a NamedNode is minted, instead of
# pyoxigraph's bare ValueError escaping. This is deliberately NOT the schema's full id pattern: an id that is
# IRI-safe but breaks the pattern (e.g. a leading digit, or a "/") must still reach the graph, where the
# `id-pattern` shape reports it exactly as the linter does (shapes/REGISTER.md Table A).
_IRI_UNSAFE = re.compile(r'[\x00-\x20<>"{}|\\^`\x7f]')


def _required_string(rec: dict[str, Any], field: str, *, where: str) -> str:
    """``rec[field]`` when it is a non-empty string; otherwise :class:`EmitError` (a missing or non-string
    ``id``/``type`` must not escape as a bare ``KeyError``/``TypeError``)."""
    value = rec.get(field)
    if not isinstance(value, str) or not value.strip():
        shown = rec.get("id") if isinstance(rec.get("id"), str) and rec.get("id") else None
        who = f"{shown}: " if shown else ""
        raise EmitError(f"{where}: {who}record has no string `{field}` (got {value!r})", record_id=shown)
    return value


def record_node(vocab: Vocabulary, value: Any, *, where: str, record_id: str | None = None) -> ox.NamedNode:
    """The id-namespace IRI for a record id or reference ``value``, or :class:`EmitError` naming ``where``
    when ``value`` is not a non-empty string or cannot be an IRI local name. ``record_id`` is
    the record the error is reported against (the referring record, for a reference)."""
    if not isinstance(value, str) or not value:
        raise EmitError(f"{where}: id reference {value!r} is not a non-empty string", record_id=record_id)
    bad = _IRI_UNSAFE.search(value)
    if bad:
        raise EmitError(
            f"{where}: {value!r} cannot be an IRI local name (character {bad.group(0)!r})", record_id=record_id
        )
    try:
        return vocab.id(value)
    except ValueError as exc:
        raise EmitError(f"{where}: {value!r} cannot be an IRI local name ({exc})", record_id=record_id) from exc


def check_term_record(term: TermRecord) -> None:
    """Input-shape guard for one term record: string ``id`` and ``type``."""
    _required_string(term.record, "id", where=term.file)
    _required_string(term.record, "type", where=term.file)


def _en(value: Any) -> ox.Literal:
    return ox.Literal(normalise_text(value), language=LANG)


def _plain(value: Any) -> ox.Literal:
    return ox.Literal(normalise_text(value))


def _as_list(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    return value if isinstance(value, list) else [value]


# =====================================================================================================
# t1 — one term record -> triples (ADR 0041 D2)

Triple = tuple[ox.NamedNode, ox.NamedNode, ox.NamedNode | ox.Literal]


def term_triples(term: TermRecord, vocab: Vocabulary) -> Iterator[Triple]:
    """Triples for one term record: types, labels, scheme, provenance, verb edges, ``source`` links."""
    rec = term.record
    check_term_record(term)
    subject = record_node(vocab, rec["id"], where=term.file, record_id=rec["id"])
    cls = vocab.term_class.get(rec["type"])
    if cls is None:
        raise EmitError(
            f"{term.file}: {rec['id']} has type {rec['type']!r}, which no Term subclass pins", record_id=rec["id"]
        )
    yield subject, RDF_TYPE, cls
    yield subject, RDF_TYPE, SKOS_CONCEPT
    yield subject, vocab.slot_iri("id"), ox.Literal(str(rec["id"]))
    # `term`/`definition` absent reaches the graph fine, no crash (shapes/REGISTER.md Table A, `field-missing`
    # row: id/type absence crashes the emitter, but term/definition reach the graph if absent — the emitter
    # omits the triple and the `field-missing` shape reports it), the same `.get()` tolerance
    # `aliases`/`deprecated`/`source` below have.
    if rec.get("term") is not None and normalise_text(rec["term"]):
        yield subject, vocab.slot_iri("term"), _en(rec["term"])
    if rec.get("definition") is not None and normalise_text(rec["definition"]):
        yield subject, vocab.slot_iri("definition"), _en(rec["definition"])
    for alias in _as_list(rec.get("aliases")):
        yield subject, vocab.slot_iri("aliases"), _en(alias)
    for banned in _as_list(rec.get("deprecated")):
        yield subject, vocab.slot_iri("deprecated"), _en(banned)
    yield from _retirement_triples(subject, rec, vocab)
    yield subject, SKOS_IN_SCHEME, vocab.scheme
    yield subject, vocab.onto(AUTHORING_FILE), ox.Literal(term.file)
    if rec["type"] != META_SUBJECT_TYPE:  # EntityType relates_to entries are schema statements, never emitted
        yield from _verb_edges(subject, rec, vocab)
    if rec.get("source") is not None:
        yield from source_triples(subject, rec["source"], vocab, record_id=rec["id"])


def _verb_edges(subject: ox.NamedNode, rec: dict[str, Any], vocab: Vocabulary) -> Iterator[Triple]:
    """Pivot each ``relates_to`` {rel, target} onto the verb's own predicate (ADR 0041 D2): repeated triples.

    Every ``relates_to`` entry must be a mapping carrying both ``rel`` and ``target``
    (``shapes/REGISTER.md``'s ``relates-to-malformed`` row): a malformed entry raises ``EmitError`` naming
    the record id and the offending entry — never an uncaught ``TypeError`` (a non-mapping entry, e.g. a
    bare string) or ``KeyError`` (a mapping missing ``target``).
    """
    record_id = rec["id"]
    for edge in rec.get("relates_to") or []:
        if not isinstance(edge, dict):
            raise EmitError(f"{record_id}: relates_to entry is not a mapping: {edge!r}", record_id=record_id)
        if "rel" not in edge or "target" not in edge:
            raise EmitError(f"{record_id}: relates_to entry is missing 'rel' or 'target': {edge!r}", record_id=record_id)
        predicate = vocab.verb.get(edge["rel"]) if isinstance(edge["rel"], str) else None
        if predicate is None:
            raise EmitError(
                f"{record_id}: relates_to verb {edge['rel']!r} is not a slot in the verbs subset", record_id=record_id
            )
        target = record_node(vocab, edge["target"], where=f"{record_id}: relates_to target", record_id=record_id)
        yield subject, predicate, target


def _retirement_triples(subject: ox.NamedNode, rec: dict[str, Any], vocab: Vocabulary) -> Iterator[Triple]:
    """A retired record (ADR 0048): ``owl:deprecated true`` and ``itpra-o:retiredIn`` the version, verbatim (its
    format is the ``retired-format`` shape's to check); ``replaced_by`` as ``dcterms:isReplacedBy`` its
    successor, whether or not that resolves (``replaced-by-unresolved``) or the record is retired
    (``replaced-by-without-retired``)."""
    if rec.get("retired") is not None:
        yield subject, OWL_DEPRECATED, TRUE
        yield subject, vocab.slot_iri("retired"), ox.Literal(str(rec["retired"]))
    if rec.get("replaced_by") is not None:
        where = f"{rec['id']}: replaced_by"
        yield subject, vocab.slot_iri("replaced_by"), record_node(vocab, rec["replaced_by"], where=where, record_id=rec["id"])


def source_triples(
    subject: ox.NamedNode, source: Any, vocab: Vocabulary, *, record_id: str | None = None
) -> Iterator[Triple]:
    """``dcterms:source`` verbatim (normalised, untagged) plus the parsed ADR links (ADR 0041 D2; grammar: ADR 0005)."""
    yield subject, vocab.slot_iri("source"), _plain(source)
    parsed = parse_source(str(source), record_id=record_id)
    for local_names, predicate in (
        (parsed.decided_in, DECIDED_IN),
        (parsed.amended_by, AMENDED_BY),
        (parsed.extended_by, EXTENDED_BY),
    ):
        for local in local_names:
            yield subject, vocab.onto(predicate), vocab.id(local)


# =====================================================================================================
# schema — thin OWL (ADR 0041 D2: no domain, range, inverse or functional axioms)


def schema_triples(inputs: Inputs, vocab: Vocabulary) -> Iterator[Triple]:
    yield from _ontology_header(inputs.ontology_version, vocab)
    yield from _class_declarations(inputs, vocab)
    yield from _verb_declarations(inputs, vocab)
    yield from _annotation_declarations(vocab)
    yield from _derived_declarations(vocab)
    yield from _provenance_declarations(vocab)
    yield from _validation_declarations(vocab)


def _ontology_header(version: str, vocab: Vocabulary) -> Iterator[Triple]:
    onto = vocab.ontology
    yield onto, RDF_TYPE, OWL_ONTOLOGY
    yield onto, OWL_VERSION_IRI, ox.NamedNode(f"{onto.value}/{version}")
    yield onto, OWL_VERSION_INFO, ox.Literal(version)
    yield onto, RDFS_LABEL, _en(ONTOLOGY_LABEL)
    yield onto, DCTERMS_LICENSE, LICENCE
    yield vocab.scheme, RDF_TYPE, SKOS_CONCEPT_SCHEME
    yield vocab.scheme, DCTERMS_LICENSE, LICENCE


def _class_declarations(inputs: Inputs, vocab: Vocabulary) -> Iterator[Triple]:
    """Each EntityType record is an ``owl:Class ⊑ skos:Concept`` (punning, ADR 0041 D2)."""
    for term in inputs.terms:
        if term.record.get("type") == META_SUBJECT_TYPE:
            node = record_node(vocab, term.record.get("id"), where=term.file, record_id=term.record.get("id"))
            yield from _owl_class(node, term.record.get("term"))
    for class_name in (ENTITY_TYPE_CLASS, RELATIONSHIP_TYPE_CLASS):
        yield from _owl_class(vocab.class_iri(class_name), SCHEMA_LABELS[class_name])


def _owl_class(iri: ox.NamedNode, label: Any) -> Iterator[Triple]:
    yield iri, RDF_TYPE, OWL_CLASS
    yield iri, RDFS_SUBCLASS_OF, SKOS_CONCEPT
    if label is not None and normalise_text(label):  # a missing `term` is field-missing's to report
        yield iri, RDFS_LABEL, _en(label)


def _verb_declarations(inputs: Inputs, vocab: Vocabulary) -> Iterator[Triple]:
    """Each verb slot: ``owl:ObjectProperty``, ``rdfs:seeAlso`` its RelationshipType record, and the record's
    ``term`` as label. The ``itpra_verb`` annotations feed the SHACL shapes (rule B-22), not OWL axioms
    (ADR 0041 D2)."""
    verb_labels = {
        t.record.get("id"): t.record.get("term")
        for t in inputs.terms
        if t.record.get("type") == RELATIONSHIP_TYPE_CLASS
    }
    for name in vocab.verb_slots:
        prop = vocab.verb[name]
        if name not in verb_labels:
            raise EmitError(f"verb slot {name!r} has no RelationshipType record")
        yield prop, RDF_TYPE, OWL_OBJECT_PROPERTY
        for see_also in vocab.sv.get_slot(name).see_also:
            yield prop, RDFS_SEE_ALSO, vocab.expand(see_also)
        label = verb_labels[name]
        if label is not None and normalise_text(label):  # a missing `term` is field-missing's to report
            yield prop, RDFS_LABEL, _en(label)


def _annotation_declarations(vocab: Vocabulary) -> Iterator[Triple]:
    """bannedLabel ⊑ skos:hiddenLabel (its ``broad_mappings``); decidedIn ⊑ prov:wasInfluencedBy with
    amendedBy/extendedBy ⊑ decidedIn (ADR 0041 D2); authoringFile; retiredIn (ADR 0048)."""
    prop = vocab.slot_iri("deprecated")
    yield prop, RDF_TYPE, OWL_ANNOTATION_PROPERTY
    for broader in vocab.sv.get_slot("deprecated").broad_mappings:
        yield prop, RDFS_SUBPROPERTY_OF, vocab.expand(broader)
    yield prop, RDFS_LABEL, _en(SCHEMA_LABELS["deprecated"])
    decided_in = vocab.onto(DECIDED_IN)
    for local, parent in ((DECIDED_IN, PROV_WAS_INFLUENCED_BY), (AMENDED_BY, decided_in), (EXTENDED_BY, decided_in)):
        yield vocab.onto(local), RDF_TYPE, OWL_OBJECT_PROPERTY
        yield vocab.onto(local), RDFS_SUBPROPERTY_OF, parent
        yield vocab.onto(local), RDFS_LABEL, _en(SCHEMA_LABELS[local])
    authoring_file = vocab.onto(AUTHORING_FILE)
    yield authoring_file, RDF_TYPE, OWL_ANNOTATION_PROPERTY
    yield authoring_file, RDFS_LABEL, _en(SCHEMA_LABELS[AUTHORING_FILE])
    retired_in = vocab.slot_iri("retired")
    yield retired_in, RDF_TYPE, OWL_ANNOTATION_PROPERTY
    yield retired_in, RDFS_LABEL, _en(SCHEMA_LABELS["retired"])


def _derived_declarations(vocab: Vocabulary) -> Iterator[Triple]:
    """The rule-derived vocabulary's schema declarations (ADR 0041 D4): three ``owl:ObjectProperty`` roll-up
    predicates and one ``owl:Class`` (``BoundaryGovernedFunction ⊑ FUNCTION``), each carrying an
    ``rdfs:comment`` naming the rule that mints it and stating it is never asserted by this emitter — only
    ``rules/*.rq`` produces these triples, into the ``inferred`` graph."""
    for local, (label, rule_id) in DERIVED_PROPERTY_RULES.items():
        prop = vocab.onto(local)
        yield prop, RDF_TYPE, OWL_OBJECT_PROPERTY
        yield prop, RDFS_LABEL, _en(label)
        yield prop, RDFS_COMMENT, _en(DERIVED_COMMENT.format(rule=rule_id))
    boundary_cls = vocab.onto(BOUNDARY_GOVERNED_FUNCTION)
    yield boundary_cls, RDF_TYPE, OWL_CLASS
    yield boundary_cls, RDFS_SUBCLASS_OF, vocab.class_iri("Function")
    yield boundary_cls, RDFS_LABEL, _en("boundary-governed function")
    yield boundary_cls, RDFS_COMMENT, _en(DERIVED_COMMENT.format(rule=BOUNDARY_GOVERNED_FUNCTION_RULE))


def _provenance_declarations(vocab: Vocabulary) -> Iterator[Triple]:
    """The datatype properties a built dataset's provenance record carries (ADR 0043 D3):
    ``itpra-o:sha256``, ``inputHash``, ``pipelineVersion``, ``environmentHash``,
    ``rulesVersion``, ``schemaHash``. Declared here, as ``owl:DatatypeProperty``, so they are
    discoverable from the schema graph like every other predicate this pipeline mints; asserted only by
    ``itpra_onto.build``, only into ``<graph_ns>provenance``, never here."""
    for local, label in PROVENANCE_PROPERTY_LABELS.items():
        prop = vocab.onto(local)
        yield prop, RDF_TYPE, OWL_DATATYPE_PROPERTY
        yield prop, RDFS_LABEL, _en(label)


def _validation_declarations(vocab: Vocabulary) -> Iterator[Triple]:
    """``itpra-o:ruleId`` (``shapes/REGISTER.md``): the annotation property a SHACL shape node carries,
    naming the register rule id it enforces (Table A, shared with the linter, or a Table-B addition).
    Declared here so it is discoverable from the schema graph like every other predicate this pipeline
    mints; never asserted here — only ``shapes/*.ttl`` (and the test fixtures under
    ``tests/fixtures/shapes-smoke/``) carry ``itpra-o:ruleId`` triples, always on a shape node, never on
    data."""
    prop = vocab.onto(RULE_ID)
    yield prop, RDF_TYPE, OWL_ANNOTATION_PROPERTY
    yield prop, RDFS_LABEL, _en("rule id")


# =====================================================================================================
# Assembly


def _add(dataset: ox.Dataset, triples: Iterable[Triple], graph: ox.NamedNode) -> None:
    for s, p, o in triples:
        dataset.add(ox.Quad(s, p, o, graph))


def emit(inputs: Inputs | None = None, config: Config | None = None) -> ox.Dataset:
    """Project ``inputs`` (default: :func:`load_inputs`) into an in-memory dataset of named graphs (ADR 0041 D3)."""
    config = config if config is not None else load_config()
    inputs = inputs if inputs is not None else load_inputs(config)
    vocab = Vocabulary(config, schema_loading.load_schema_view(config=config))
    # Every input-shape defect is an EmitError, raised before the schema graph (which already reads every
    # term's `type`/`id`) is built — never a KeyError/TypeError from deep inside a generator.
    for term in inputs.terms:
        check_term_record(term)
    dataset = ox.Dataset()
    _add(dataset, schema_triples(inputs, vocab), vocab.graph("schema"))
    t1 = vocab.graph("t1")
    for term in inputs.terms:
        _add(dataset, term_triples(term, vocab), t1)
    return dataset


def dangling_object_iris(dataset: ox.Dataset, config: Config | None = None) -> set[str]:
    """Object IRIs in the id namespace that are no subject in any record graph (every named graph but
    ``schema``).

    ADR nodes (``decidedIn`` targets, which have no record of their own) and the concept scheme are excluded.
    """
    config = config if config is not None else load_config()
    id_ns, graph_ns = config.iri.id_ns, config.iri.graph_ns
    record_quads = [
        q for q in dataset
        if isinstance(q.graph_name, ox.NamedNode) and q.graph_name.value != graph_ns + "schema"
    ]
    subjects = {q.subject.value for q in record_quads}
    excluded_prefixes = (id_ns + ADR_LOCAL_PREFIX,)
    return {
        q.object.value
        for q in record_quads
        if isinstance(q.object, ox.NamedNode)
        and q.object.value.startswith(id_ns)
        and q.object.value not in subjects
        and q.object.value != id_ns + SCHEME_LOCAL
        and not q.object.value.startswith(excluded_prefixes)
    }

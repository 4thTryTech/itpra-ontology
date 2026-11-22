"""Generate the verb domain/range shapes from the ``itpra_verb`` annotations (rule ``B-22``).

``schema/itpra.linkml.yaml`` carries one ``itpra_verb`` annotation per verb slot (the ``verbs`` subset). Its
``pairs`` list is "the ALLOWED (subject, object) combinations" for that verb (the schema's own annotation
grammar), and those annotations are the governing statement of each verb's domain and range (ADR 0008; the
authored statement wins over any derived artefact, ADR 0041 D1). This module turns them into SHACL, so the
shape can never drift from the annotation it enforces: it writes ``shapes/generated/verb-pairs.ttl``, which
:func:`itpra_onto.shacl.load_shapes` loads alongside the hand-written ``shapes/*.ttl`` files.
``shapes/generated/`` is owned by this generator; nothing in it is edited by hand.

One ``sh:NodeShape`` per verb slot (every evidence class — ``data``, ``meta-only`` and ``definition`` alike:
a verb with zero instances today still binds its declared pairs), each:

* ``sh:targetSubjectsOf`` the predicate the emitter writes for that verb (the verb slot's ``slot_uri`` for a
  ``carried_by: relates_to`` verb; the named slot's ``slot_uri`` for ``carried_by: slot:<name>``);
* a ``sh:sparql`` constraint selecting every ``($this, ?value)`` edge whose object is a resolved record
  (typed with one of the record classes — a dangling object is ``target-unresolved``'s /
  ``req-target-unresolved``'s business, never this rule's) and for which NO allowed pair ``(S, O)`` has
  ``$this`` typed ``S`` and ``?value`` typed ``O``. The test is set membership over each node's types, not
  equality with one class: every record is also typed ``skos:Concept`` (and a requirement also
  ``itpra:REQUIREMENT``, a Function perhaps also the derived ``BoundaryGovernedFunction``), and only the
  record classes are compared;
* ``sh:severity sh:Violation``, ``itpra-o:ruleId "B-22"``, and a message naming the verb, the subject class
  and the object class.

Class names in ``pairs`` resolve through the schema's class table — the classes :class:`itpra_onto.emit.
Vocabulary` pins a ``type`` value to (the ``Term`` subclasses, ``EntityType`` -> ``itpra-o:EntityType``
included) plus the ``Requirement`` subclasses (``FR`` -> ``itpra:FR``, ``NFR`` -> ``itpra:NFR``). A pair
naming something that is not such a class (the annotation grammar allows an UPPER_SNAKE EntityType id
"only where no `type` value (hence no class) exists": ``ADR``, ``SERVICE``) can match no record and is
listed in the generated file's header as unresolvable; the verb's other pairs still bind, and a verb whose
pairs are all unresolvable allows no edge at all.

The file carries no base IRI and no ``@prefix`` block (the loader prepends both, exactly as for the
hand-written files — :mod:`itpra_onto.shacl`'s module docstring). Output is deterministic: verbs sorted by
name, pairs in annotation order, LF newlines, UTF-8, no timestamps.

``--check`` regenerates in memory and exits non-zero when the committed file differs.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonasobj2 import JsonObj, as_dict
from linkml_runtime.utils.schemaview import SchemaView

from itpra_onto import schema_loading
from itpra_onto.authoring import REQUIREMENT_BASE_CLASS, TERM_BASE_CLASS
from itpra_onto.config import Config, load_config

PROJECT_DIR = Path(__file__).resolve().parents[2]  # the package root
GENERATED_SHAPES_DIR = PROJECT_DIR / "shapes" / "generated"
VERB_PAIRS_PATH = GENERATED_SHAPES_DIR / "verb-pairs.ttl"

RULE_ID = "B-22"
VERBS_SUBSET = "verbs"
ANNOTATION = "itpra_verb"
CARRIED_BY_RELATES_TO = "relates_to"
CARRIED_BY_SLOT_PREFIX = "slot:"

_HEADER = """\
# GENERATED FILE - DO NOT EDIT BY HAND.
# Source:     schema/itpra.linkml.yaml - the `itpra_verb` annotation of every slot in the `verbs` subset;
#             `pairs` = the ALLOWED (subject, object) combinations (ADR 0041 D1, ADR 0042 D2).
# Generator:  src/itpra_onto/gen_verb_shapes.py
# Regenerate: itpra-onto gen-verb-shapes
# Check:      itpra-onto gen-verb-shapes --check
#
# Rule B-22 (shapes/REGISTER.md Table B): an edge whose object is a resolved record, and whose (subject
# class, object class) is not among the verb's allowed pairs, is a Violation. Dangling objects are left to
# target-unresolved / req-target-unresolved. No @prefix block and no base IRI: itpra_onto.shacl.load_shapes
# prepends both at load time, as for the hand-written shapes/*.ttl files.
"""


class VerbShapeError(RuntimeError):
    """The schema's verb annotations cannot be turned into shapes (a malformed annotation)."""


@dataclass(frozen=True)
class VerbPairs:
    """One verb slot's generated-shape inputs."""

    verb: str
    predicate: str  # CURIE of the predicate the emitter writes for this verb
    evidence: str
    pairs: tuple[tuple[str, str], ...]  # (subject CURIE, object CURIE), resolvable pairs only
    pair_names: tuple[tuple[str, str], ...]  # (subject class name, object class name), resolvable only
    unresolved: tuple[tuple[str, str], ...]  # (subject name, object name) pairs naming no record class


def _plain(value: Any) -> Any:
    return as_dict(value) if isinstance(value, JsonObj) else value


def record_classes(sv: SchemaView) -> dict[str, str]:
    """``class name -> class_uri CURIE`` for every record class: the ``Term`` and ``Requirement`` subclasses
    (the classes ``emit.Vocabulary``'s type -> class table pins a record to)."""
    names = [*sv.class_descendants(TERM_BASE_CLASS, reflexive=False), *sv.class_descendants(REQUIREMENT_BASE_CLASS, reflexive=False)]
    out: dict[str, str] = {}
    for name in sorted(set(names)):
        cls = sv.get_class(name)
        if cls.abstract:
            continue
        if not cls.class_uri:
            raise VerbShapeError(f"class {name!r} has no class_uri")
        out[name] = cls.class_uri
    return out


def _verb_annotation(sv: SchemaView, verb: str) -> dict[str, Any]:
    slot = sv.get_slot(verb)
    annotation = slot.annotations.get(ANNOTATION) if slot.annotations else None
    if annotation is None:
        raise VerbShapeError(f"verb slot {verb!r} carries no {ANNOTATION} annotation")
    value = _plain(annotation.value)
    if not isinstance(value, dict):
        raise VerbShapeError(f"verb slot {verb!r}: {ANNOTATION} value is not a mapping")
    return value


def _predicate_curie(sv: SchemaView, verb: str, carried_by: str) -> str:
    if carried_by == CARRIED_BY_RELATES_TO:
        slot_name = verb
    elif isinstance(carried_by, str) and carried_by.startswith(CARRIED_BY_SLOT_PREFIX):
        slot_name = carried_by.removeprefix(CARRIED_BY_SLOT_PREFIX)
    else:
        raise VerbShapeError(f"verb slot {verb!r}: unrecognised carried_by {carried_by!r}")
    slot_uri = sv.get_slot(slot_name).slot_uri if sv.get_slot(slot_name) else None
    if not slot_uri:
        raise VerbShapeError(f"verb slot {verb!r}: carried_by slot {slot_name!r} has no slot_uri")
    return slot_uri


def read_verb_pairs(sv: SchemaView | None = None, config: Config | None = None) -> list[VerbPairs]:
    """Every verb slot's allowed pairs, resolved to record-class CURIEs, sorted by verb name."""
    config = config if config is not None else load_config()
    sv = sv if sv is not None else schema_loading.load_schema_view(config=config)
    classes = record_classes(sv)
    verbs = sorted(name for name, slot in sv.all_slots().items() if VERBS_SUBSET in (slot.in_subset or []))
    if not verbs:
        raise VerbShapeError(f"no slot is in the {VERBS_SUBSET!r} subset")
    out: list[VerbPairs] = []
    for verb in verbs:
        value = _verb_annotation(sv, verb)
        predicate = _predicate_curie(sv, verb, value.get("carried_by"))
        raw_pairs = value.get("pairs")
        if not isinstance(raw_pairs, list) or not raw_pairs:
            raise VerbShapeError(f"verb slot {verb!r}: {ANNOTATION}.pairs is missing or empty")
        pairs: list[tuple[str, str]] = []
        names: list[tuple[str, str]] = []
        unresolved: list[tuple[str, str]] = []
        for raw in raw_pairs:
            pair = _plain(raw)
            if not isinstance(pair, dict) or "subject" not in pair or "object" not in pair:
                raise VerbShapeError(f"verb slot {verb!r}: malformed pair {pair!r}")
            subject, obj = str(pair["subject"]), str(pair["object"])
            if subject in classes and obj in classes:
                pairs.append((classes[subject], classes[obj]))
                names.append((subject, obj))
            else:
                unresolved.append((subject, obj))
        out.append(
            VerbPairs(
                verb=verb,
                predicate=predicate,
                evidence=str(value.get("evidence")),
                pairs=tuple(pairs),
                pair_names=tuple(names),
                unresolved=tuple(unresolved),
            )
        )
    return out


def _shape_name(verb: str) -> str:
    return "VerbPairs" + "".join(part.capitalize() for part in verb.split("_")) + "Shape"


def _render_shape(entry: VerbPairs, class_curies: list[str]) -> str:
    known = ", ".join(class_curies)
    if entry.pairs:
        allowed = " ||\n                        ".join(f"(?s = {s} && ?o = {o})" for s, o in entry.pairs)
    else:
        allowed = "false"
    allowed_text = ", ".join(f"({s}, {o})" for s, o in entry.pair_names) or "none"
    message = (
        f"B-22: {entry.verb} edge {{$this}} -> {{?value}}: subject class {{?subjectClass}} with object class "
        f"{{?objectClass}} is not an allowed pair for {entry.verb} (itpra_verb pairs: {allowed_text})"
    )
    lines = [
        f"# {entry.verb} (evidence: {entry.evidence}; predicate {entry.predicate}); allowed pairs: {allowed_text}"
        + (
            "; unresolvable (no record class): " + ", ".join(f"({s}, {o})" for s, o in entry.unresolved)
            if entry.unresolved
            else ""
        ),
        f"itpra-o:{_shape_name(entry.verb)}",
        "    a sh:NodeShape ;",
        f"    sh:targetSubjectsOf {entry.predicate} ;",
        "    sh:severity sh:Violation ;",
        f'    itpra-o:ruleId "{RULE_ID}" ;',
        "    sh:sparql [",
        "        a sh:SPARQLConstraint ;",
        f'        sh:message "{message}" ;',
        "        sh:prefixes itpra-o:shapesPrefixes ;",
        '        sh:select """',
        "            SELECT DISTINCT $this ?value ?subjectClass ?objectClass",
        "            WHERE {",
        f"                $this {entry.predicate} ?value .",
        "                $this rdf:type ?subjectClass .",
        f"                FILTER(?subjectClass IN ({known}))",
        "                ?value rdf:type ?objectClass .",
        f"                FILTER(?objectClass IN ({known}))",
        "                FILTER NOT EXISTS {",
        "                    $this rdf:type ?s .",
        "                    ?value rdf:type ?o .",
        "                    FILTER(",
        f"                        {allowed}",
        "                    )",
        "                }",
        "            }",
        '        """ ;',
        "    ] .",
    ]
    return "\n".join(lines) + "\n"


def render(entries: list[VerbPairs], sv: SchemaView) -> str:
    class_curies = sorted(record_classes(sv).values())
    body = "\n".join(_render_shape(entry, class_curies) for entry in entries)
    return _HEADER + "\n" + body


def generate(config: Config | None = None) -> str:
    config = config if config is not None else load_config()
    sv = schema_loading.load_schema_view(config=config)
    return render(read_verb_pairs(sv, config), sv)


def write(text: str, path: Path = VERB_PAIRS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def check(path: Path = VERB_PAIRS_PATH, config: Config | None = None) -> bool:
    """True when the file at ``path`` equals a fresh generation byte for byte."""
    if not path.exists():
        return False
    return path.read_bytes() == generate(config).encode("utf-8")


def main(check_only: bool = False) -> int:
    rel = VERB_PAIRS_PATH.relative_to(PROJECT_DIR).as_posix()
    if check_only:
        if check():
            print(f"gen-verb-shapes: {rel} is up to date")
            return 0
        print(f"gen-verb-shapes: {rel} is STALE or missing - run `itpra-onto gen-verb-shapes`", file=sys.stderr)
        return 1
    write(generate())
    print(f"gen-verb-shapes: wrote {rel}")
    return 0

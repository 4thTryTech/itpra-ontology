"""Apply the versioned SPARQL materialisation rules to an emitted dataset (ADR 0041 D4).

ADR 0041 D4: versioned ``CONSTRUCT`` rules kept in git, run in a stated order into a separate ``inferred``
graph; no reasoner; **no named inverse properties are minted** — the rule slot exists and stays empty. The
requirement-meets rule reads a consumer's ``req/*`` graphs and runs only with an ``[overlay]``.

Rules live under this package's ``rules/``: one ``.rq`` file per rule (the graphs :mod:`itpra_onto.emit`
asserts are the only thing they read) plus an ordered ``manifest.yaml`` (:func:`load_manifest`). A rule file
contains no ``PREFIX`` line for ``itpra:``/``itpra-o:``/``itpra-g:`` and no base IRI (ADR 0004): this
module computes that ``PREFIX`` block from :func:`itpra_onto.config.load_config` at run
time (:func:`prefix_block`) and prepends it to every rule's text before running it. A rule's ``CONSTRUCT``
template has no ``GRAPH`` clause (not legal SPARQL 1.1); :func:`apply_rules` places every triple a rule
constructs into ``<graph_ns>inferred`` itself, in both the working store (so a later rule may read an earlier
rule's output — manifest order matters even where no shipped rule yet depends on another) and the returned
dataset. A rule file with no ``CONSTRUCT`` at all (the empty inverse slot, ``90-inverses.rq``) is skipped and
contributes zero triples; it is not an error.

:func:`rules_digest` hashes the manifest and every rule file's bytes, in manifest order — the "rules version"
a built dataset's provenance record carries (ADR 0043 D3), with no timestamp so it is reproducible from
source alone.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyoxigraph as ox
import yaml

from itpra_onto.config import Config, load_config

PACKAGE_DIR = Path(__file__).resolve().parent  # src/itpra_onto: the package's own code and data
RULES_DIR = PACKAGE_DIR / "rules"
MANIFEST_NAME = "manifest.yaml"
INFERRED_GRAPH_LOCAL = "inferred"

# A rule file with no CONSTRUCT query is the deliberately empty slot (90-inverses.rq): skipped, not an
# error. Its header comment names the keyword too (to explain the slot), so detection first strips every
# `#`-to-end-of-line comment (SPARQL's only comment syntax; none of these rules use `#` inside a string or
# IRI) and only then looks for the keyword — a comment mentioning CONSTRUCT must not count as a query.
_COMMENT_RE = re.compile(r"#[^\n]*")
_CONSTRUCT_RE = re.compile(r"\bCONSTRUCT\b", re.IGNORECASE)


def _strip_comments(text: str) -> str:
    return _COMMENT_RE.sub("", text)


class RuleError(RuntimeError):
    """The rule manifest or a rule file is malformed."""


@dataclass(frozen=True)
class Rule:
    """One manifest entry, resolved to its file on disk."""

    id: str
    file: str
    description: str
    reads: tuple[str, ...]
    produces: str
    path: Path
    overlay: bool = False

    @property
    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    @property
    def has_construct(self) -> bool:
        return bool(_CONSTRUCT_RE.search(_strip_comments(self.text)))


@dataclass(frozen=True)
class RuleReport:
    """The result of :func:`apply_rules`: the new dataset plus per-rule triple counts."""

    dataset: ox.Dataset
    counts: dict[str, int]
    total: int
    elapsed: float


def load_manifest(config: Config | None = None, *, rules_dir: Path = RULES_DIR, all_rules: bool = False) -> list[Rule]:
    """Read ``rules_dir/manifest.yaml`` in file order and resolve each entry's rule file.

    A rule marked ``overlay: true`` reads the consumer's ``req/*`` graphs and is left out when the
    configuration has no ``[overlay]`` (ADR 0043 D1), unless ``all_rules`` is set — the rules
    digest hashes every shipped rule whatever the configuration. The manifest and rule files name no base
    IRI; :func:`prefix_block` and :func:`apply_rules` are what consume ``config``'s IRIs.
    """
    config = config if config is not None else load_config()
    manifest_path = rules_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise RuleError(f"{manifest_path}: manifest file does not exist")
    with manifest_path.open(encoding="utf-8") as fh:
        raw: Any = yaml.safe_load(fh) or []
    if not isinstance(raw, list):
        raise RuleError(f"{manifest_path}: expected a top-level list of rule entries")

    rules: list[Rule] = []
    seen_ids: set[str] = set()
    for entry in raw:
        if not isinstance(entry, dict):
            raise RuleError(f"{manifest_path}: entry {entry!r} is not a mapping")
        missing = [key for key in ("id", "file", "description", "produces") if key not in entry]
        if missing:
            raise RuleError(f"{manifest_path}: entry {entry!r} is missing required key(s) {missing}")
        rule_id = str(entry["id"])
        if rule_id in seen_ids:
            raise RuleError(f"{manifest_path}: duplicate rule id {rule_id!r}")
        seen_ids.add(rule_id)
        path = rules_dir / str(entry["file"])
        if not path.exists():
            raise RuleError(f"{manifest_path}: rule {rule_id!r} names a file that does not exist: {path}")
        rules.append(
            Rule(
                overlay=bool(entry.get("overlay", False)),
                id=rule_id,
                file=str(entry["file"]),
                description=str(entry["description"]),
                reads=tuple(entry.get("reads") or ()),
                produces=str(entry["produces"]),
                path=path,
            )
        )
    if not all_rules and config.overlay is None:
        rules = [rule for rule in rules if not rule.overlay]
    return rules


def prefix_block(config: Config | None = None) -> str:
    """The ``PREFIX`` lines for ``itpra:``/``itpra-o:``/``itpra-g:`` computed from ``config`` (ADR 0004).

    Prepended to every rule's text before it runs; never written into a ``.rq`` file on disk: no rule file
    names a base IRI, so a rule reads the same whatever base a configuration sets.
    """
    config = config if config is not None else load_config()
    iri = config.iri
    return (
        f"PREFIX itpra: <{iri.id_ns}>\n"
        f"PREFIX itpra-o: <{iri.onto_ns}>\n"
        f"PREFIX itpra-g: <{iri.graph_ns}>\n"
    )


def apply_rules(dataset: ox.Dataset, config: Config | None = None, *, rules_dir: Path = RULES_DIR) -> RuleReport:
    """Run every rule in manifest order and return the new dataset plus per-rule triple counts.

    Loads ``dataset`` into an in-memory :class:`pyoxigraph.Store` (0.5.11's ``Dataset`` has no ``query``;
    ``Store.extend`` accepts any iterable of quads). Each rule's ``CONSTRUCT`` runs against the store as it
    stands *at that point* — the asserted graphs plus every triple an earlier rule in this run already
    produced — so a later rule may read an earlier rule's output (manifest order matters). Every constructed
    triple becomes a quad in ``<graph_ns>inferred``, added to both the store (so the next rule sees it) and
    a fresh :class:`pyoxigraph.Dataset` this function returns; ``dataset`` itself, and the store built from
    it, are never mutated in a way that changes an asserted graph — only ``inferred`` quads are ever added.
    A rule file with no ``CONSTRUCT`` (:attr:`Rule.has_construct` false — the empty inverse slot) is skipped
    and contributes zero triples, not an error.
    """
    config = config if config is not None else load_config()
    started = time.perf_counter()

    store = ox.Store()
    store.extend(dataset)

    inferred_graph = ox.NamedNode(config.iri.graph_ns + INFERRED_GRAPH_LOCAL)
    prefixes = prefix_block(config)

    counts: dict[str, int] = {}
    inferred_quads: list[ox.Quad] = []
    for rule in load_manifest(config, rules_dir=rules_dir):
        if not rule.has_construct:
            counts[rule.id] = 0
            continue
        query_text = prefixes + rule.text
        triples = list(store.query(query_text))
        quads = [ox.Quad(t.subject, t.predicate, t.object, inferred_graph) for t in triples]
        counts[rule.id] = len(quads)
        for quad in quads:
            store.add(quad)
        inferred_quads.extend(quads)

    result = ox.Dataset()
    for quad in dataset:
        result.add(quad)
    for quad in inferred_quads:
        result.add(quad)

    elapsed = time.perf_counter() - started
    return RuleReport(dataset=result, counts=counts, total=sum(counts.values()), elapsed=elapsed)


def rules_digest(config: Config | None = None, *, rules_dir: Path = RULES_DIR) -> str:
    """sha256 over the manifest's bytes and every rule file's bytes, in manifest order.

    No timestamp: this is the "rules version" a built dataset's provenance record carries (ADR 0043 D3),
    and it must be reproducible from source alone. ``config`` is accepted for
    calling-convention parity with the rest of this module (see :func:`load_manifest`); it plays no part
    in the digest, since prefixes are injected at run time and never appear in the hashed bytes.
    """
    manifest_path = rules_dir / MANIFEST_NAME
    digest = hashlib.sha256()
    digest.update(manifest_path.read_bytes())
    for rule in load_manifest(config, rules_dir=rules_dir):
        digest.update(rule.path.read_bytes())
    return digest.hexdigest()

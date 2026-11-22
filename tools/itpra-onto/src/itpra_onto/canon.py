"""Canonicalisation helpers for the ITPRA ontology-as-code pipeline.

ADR 0041 D5: no released LinkML version (1.11.1 current) produces deterministic generator output —
**the pipeline owns determinism**, not LinkML. For RDF-shaped generator output (OWL, SHACL) that means:
parse the generator's raw text into an in-memory graph, apply pyoxigraph's explicit RDFC-1.0
canonicalisation algorithm (fixes blank-node labelling; confirmed in ``tests/test_smoke.py``,
``test_pyoxigraph_dataset_canonicalize_rdfc_1_0_is_deterministic``, to NOT also fix quad/triple
*iteration order* — an independently-built, content-identical graph serialises with its statements in a
different order call to call), then sort the serialised lines. That combination — canonicalise, then sort
— is what makes two independent generator runs byte-identical, not either step alone.

This module is deliberately small and reusable: ``itpra-onto build``'s canonical N-Quads output and
``gen-artifacts``' RDF-shaped artefacts go through the same two functions rather than re-implementing the
canonicalise-then-sort recipe.
"""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox

__all__ = ["canonical_nquads", "canonical_ntriples", "write_bytes"]


def _sorted_lines_bytes(raw: bytes) -> bytes:
    """Decode ``raw`` as UTF-8, split into lines, sort them, and rejoin with LF.

    An empty input yields empty output (no trailing LF invented out of nothing); any non-empty input's
    output always ends in exactly one LF, regardless of what line-ending the serialiser used.
    """
    text = raw.decode("utf-8")
    lines = text.splitlines()
    if not lines:
        return b""
    return ("\n".join(sorted(lines)) + "\n").encode("utf-8")


def canonical_nquads(dataset: ox.Dataset) -> bytes:
    """Canonicalise ``dataset`` in place (RDFC-1.0) and return sorted, LF-terminated N-Quads.

    ``dataset.canonicalize()`` relabels blank nodes deterministically but does not fix statement
    iteration order (empirically confirmed, ``tests/test_smoke.py``); this function sorts the serialised
    lines itself, which is what actually makes two independently built, content-identical datasets
    serialise byte-identically.
    """
    dataset.canonicalize(ox.CanonicalizationAlgorithm.RDFC_1_0)
    raw = ox.serialize(dataset, format=ox.RdfFormat.N_QUADS)
    return _sorted_lines_bytes(raw)


def canonical_ntriples(graph_source: bytes | str, format: ox.RdfFormat) -> bytes:  # noqa: A002 - matches spec
    """Parse ``graph_source`` (in ``format``) into a fresh default-graph :class:`pyoxigraph.Dataset`,
    canonicalise it (RDFC-1.0), and return sorted, LF-terminated N-Triples.

    Every quad ``pyoxigraph.parse`` yields for a graph-less format (Turtle, RDF/XML, N-Triples) carries
    ``DefaultGraph`` as its graph name, so building a :class:`~pyoxigraph.Dataset` straight from the
    parse iterator puts every statement in the default graph, matching what generators such as LinkML's
    ``OwlSchemaGenerator`` / ``ShaclGenerator`` emit (a single graph, no named graphs).
    """
    if isinstance(graph_source, str):
        graph_source = graph_source.encode("utf-8")
    quads = ox.parse(input=graph_source, format=format)
    dataset = ox.Dataset(quads)
    dataset.canonicalize(ox.CanonicalizationAlgorithm.RDFC_1_0)
    raw = ox.serialize(dataset, format=ox.RdfFormat.N_TRIPLES)
    return _sorted_lines_bytes(raw)


def write_bytes(path: Path, data: bytes) -> None:
    """Create ``path``'s parent directories and write ``data`` exactly (no newline translation)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

"""Tests for ``itpra_onto.canon``: the pipeline's canonicalisation helpers.

ADR 0041 D5 -- LinkML does not produce deterministic generator output; **the pipeline owns
determinism**. ``canon.py`` is the shared recipe (canonicalise RDFC-1.0, then sort the serialised
lines) that ``gen_artifacts.py`` and ``itpra-onto build`` both build on. These tests exercise it
directly, independent of any LinkML generator, with a blank node deliberately in the fixture so the
canonicalisation step (not just the sort) is actually exercised.
"""

from __future__ import annotations

from pathlib import Path

import pyoxigraph as ox

from itpra_onto import canon

# A fake host (never the shipped placeholder -- tests/test_iri_config.py's project-wide scan would flag
# that literal in a .py file outside its explicit allow-list).
EX = "https://example.test/ns/itpra-canon/"


def _quad(s: str, p: str, o) -> ox.Quad:
    graph = ox.NamedNode(EX + "graph/t1")
    return ox.Quad(ox.NamedNode(s), ox.NamedNode(p), o, graph)


def _dataset_order_a() -> ox.Dataset:
    """A dataset with one blank node, built with statements added in one order."""
    blank = ox.BlankNode()
    dataset = ox.Dataset()
    dataset.add(_quad(EX + "id/CAP-1", EX + "onto#groupedBy", ox.NamedNode(EX + "id/ITO-FND")))
    dataset.add(_quad(EX + "id/CAP-1", EX + "onto#hasNote", blank))
    dataset.add(ox.Quad(blank, ox.NamedNode(EX + "onto#text"), ox.Literal("hello", language="en"), ox.NamedNode(EX + "graph/t1")))
    return dataset


def _dataset_order_b() -> ox.Dataset:
    """The same graph as :func:`_dataset_order_a`, built with a different blank node identity and a
    different statement-insertion order -- an independent build, not a copy."""
    blank = ox.BlankNode()
    dataset = ox.Dataset()
    dataset.add(ox.Quad(blank, ox.NamedNode(EX + "onto#text"), ox.Literal("hello", language="en"), ox.NamedNode(EX + "graph/t1")))
    dataset.add(_quad(EX + "id/CAP-1", EX + "onto#hasNote", blank))
    dataset.add(_quad(EX + "id/CAP-1", EX + "onto#groupedBy", ox.NamedNode(EX + "id/ITO-FND")))
    return dataset


def test_canonical_nquads_is_byte_identical_across_differently_ordered_blank_node_builds():
    out_a = canon.canonical_nquads(_dataset_order_a())
    out_b = canon.canonical_nquads(_dataset_order_b())
    assert out_a == out_b
    assert out_a  # non-empty


def test_canonical_nquads_ends_with_lf_and_is_idempotent():
    out = canon.canonical_nquads(_dataset_order_a())
    assert out.endswith(b"\n")
    assert not out.endswith(b"\n\n")
    # Re-canonicalising an already-canonical dataset built fresh from the same content is stable.
    again = canon.canonical_nquads(_dataset_order_a())
    assert out == again


def test_canonical_nquads_empty_dataset_is_empty_bytes():
    assert canon.canonical_nquads(ox.Dataset()) == b""


TTL_ORDER_A = f"""
@prefix ex: <{EX}onto#> .
@prefix id: <{EX}id/> .

id:CAP-1 ex:groupedBy id:ITO-FND .
id:CAP-1 ex:hasNote [ ex:text "hello"@en ] .
"""

TTL_ORDER_B = f"""
@prefix ex: <{EX}onto#> .
@prefix id: <{EX}id/> .

_:zzz ex:text "hello"@en .
id:CAP-1 ex:hasNote _:zzz .
id:CAP-1 ex:groupedBy id:ITO-FND .
"""


def test_canonical_ntriples_is_byte_identical_across_differently_ordered_turtle_text():
    out_a = canon.canonical_ntriples(TTL_ORDER_A, ox.RdfFormat.TURTLE)
    out_b = canon.canonical_ntriples(TTL_ORDER_B, ox.RdfFormat.TURTLE)
    assert out_a == out_b
    assert out_a.endswith(b"\n")


def test_canonical_ntriples_accepts_bytes_or_str():
    out_str = canon.canonical_ntriples(TTL_ORDER_A, ox.RdfFormat.TURTLE)
    out_bytes = canon.canonical_ntriples(TTL_ORDER_A.encode("utf-8"), ox.RdfFormat.TURTLE)
    assert out_str == out_bytes


def test_canonical_ntriples_sorted_lines_are_actually_sorted():
    out = canon.canonical_ntriples(TTL_ORDER_A, ox.RdfFormat.TURTLE)
    lines = out.decode("utf-8").splitlines()
    assert lines == sorted(lines)
    assert len(lines) == 3


def test_write_bytes_creates_parents_and_writes_exact_bytes(tmp_path: Path):
    target = tmp_path / "nested" / "dir" / "out.nt"
    data = b"line one\nline two\n"
    canon.write_bytes(target, data)
    assert target.read_bytes() == data


def test_write_bytes_overwrites_existing_file(tmp_path: Path):
    target = tmp_path / "out.nt"
    canon.write_bytes(target, b"first\n")
    canon.write_bytes(target, b"second\n")
    assert target.read_bytes() == b"second\n"


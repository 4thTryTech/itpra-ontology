# `shapes/` — the SHACL shapes

[`REGISTER.md`](REGISTER.md) is the contract (ADR 0042 D1): every linter rule id mapped to one enforcement
mechanism, and every rule the shapes add beyond the linter, grouped into the shape files below. How a shape
file is loaded, the convention a rule-bearing shape follows, the fixture format and `itpra-onto validate`
are `../shacl.py` and `../fixtures.py`; `shacl.py`'s module docstring is the
full convention and [`../README.md`](../../../README.md)'s "Validation" section the shorter tour. Read both before
adding a shape file here.

## Layout

| Shape file | Fixture directory | Mechanism | Targets |
|---|---|---|---|
| `structural.ttl` | `../fixtures/structural/` | SHACL Core | `t1`, `inferred` |
| `crossfield.ttl` | `../fixtures/crossfield/` | SHACL-SPARQL | `t1` |
| `generated/verb-pairs.ttl` | `../fixtures/structural/B-22-*.yaml` | **generated** by `itpra-onto gen-verb-shapes` from the schema's `itpra_verb` annotations (rule `B-22`); never edit by hand — `gen-verb-shapes --check` detects drift | `t1` |

Ownership is disjoint (ADR 0042 D2): each rule id has a shape in exactly one file. `REGISTER.md`'s "Counts"
section holds the per-file and per-mechanism arithmetic; `itpra-onto parity` parses that file at run time
and fails if its tables and the loaded shapes disagree.

`../fixtures/` is a sibling of `shapes/`, not a subdirectory: `itpra_onto.shacl.shape_files()` globs only
`shapes/*.ttl` and `shapes/generated/*.ttl`, so a fixture directory nested under `shapes/` could never be
parsed as a shape file.

A fixture count can exceed a file's shape-bearing rule-id count. Some rule ids get more than one fixture: a
positive, count-1 fixture proving the rule fires, plus a `count: 0` clean-case fixture documenting a
mutation that deliberately does *not* trigger it (`fixtures.py`'s module docstring has the grammar; e.g.
`crossfield/B-13.yaml` and `B-13-emit-guard.yaml` — one exercises the emitter's `source`-grammar guard, the
other a legal-but-unpadded `source` that stays silent). A fixture for a rule enforced before emission
(`type-unknown`, `verb-unknown`, `relates-to-malformed`) expects the synthetic
`rule: emit-error` finding and names its guard with `expect.emit_error`; `itpra_onto.parity` recovers the
real rule id from the fixture's filename, stripping a trailing `-emit-guard`.

Only `REGISTER.md` rows marked mechanism `core` or `sparql` get a shape here. `generated` rows are closed
before emission by the authoring schema; `emit` rows are refused by the emitter — `relates-to-malformed` is
an `EmitError` raised by `emit.py`'s `_verb_edges` and is proven by a fixture, not by a shape; `python` rows
stay in code.

## Before adding a shape here

1. Read `shacl.py`'s module docstring in full — in particular the "single, named (non-blank) shape node"
   convention and the `sh:prefixes itpra-o:shapesPrefixes` convention every `sh:sparql` node needs. Both
   are load-bearing, not style: get them wrong and `itpra-o:ruleId` extraction, or the embedded SPARQL
   query's prefixes, silently fail.
2. Every rule-bearing shape carries `itpra-o:ruleId "<id>"` (a Table A linter id or a Table B `B-n` id) and
   `sh:severity` per `REGISTER.md` Table C.
3. One fixture per rule id, at `fixtures/<group>/<rule-id>.yaml` — the grammar is documented in full at the
   top of `fixtures.py`; `assert_fixture()` is the one call a test module needs.
4. Clean (unmutated) data must still pass your shape file untouched — `fixtures.py`'s `_clean_report()`
   (used by every `assert_fixture()` call) proves this automatically per rule id.
5. A `sh:sparql`/`sh:SPARQLConstraint` query may **not** contain a `VALUES` clause — SHACL-SPARQL forbids
   it, and pySHACL 0.40.1 does not raise for this: `pyshacl.validate()` returns a `ValidationFailure`
   object in place of a results graph, which `shacl.py`'s `validate()` turns into a `ShaclError` rather than
   letting it crash `_extract_findings`. Write `FILTER(?x IN (...))` instead (`crossfield.ttl`'s `B-13`
   shape is the worked example).
6. SHACL **Core**'s `sh:message` is never placeholder-substituted by pySHACL 0.40.1 — only a
   `sh:sparql`/`sh:SPARQLConstraint`'s own `sh:message` gets `{?value}`/`{$this}` filled in. Write plain
   text naming the field in a Core shape's `sh:message` (the finding's own `sh:focusNode`/`sh:value`
   already carry the offending id); reserve `{?value}`/`{$this}` templating for SPARQL constraints.

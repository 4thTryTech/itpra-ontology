# ADR 0042 — Validation parity: one rule register, shapes beside the linter, fixtures, the parity check

Status: Accepted  
Date: 2026-11-22  
Supersedes: —  
Superseded by: —  

Origin: Consolidates the validation decisions of 2026-09 for the pipeline under `tools/`.

## Context

Two checks read the vocabulary: the linter over the YAML, the shapes over the emitted graphs. They drift apart
unless one register says where each rule lives, every rule is proven to fire, and one command compares them.

## Decision

1. One register maps every linter rule to one mechanism: `generated` (the authoring schema refuses it), `core`
   (a SHACL Core shape), `sparql` (a `sh:SPARQLConstraint`) or `python` (the linter keeps it); a second table lists
   rules only the shapes have; error maps to `sh:Violation`, warning to `sh:Warning`; a rule enforced before any
   graph exists reports as `emit-error`.
2. Shapes are hand-written in files with disjoint ownership — structural and cross-field — plus one generated
   file with a shape per verb for the class pairs the authoring schema declares (ADR 0008). Shapes carry a rule
   id and a severity and no base IRI; schema-generated SHACL and OWL document the authoring shape only.
3. Shapes may be stricter than the linter where the vocabulary states a rule it never checked — label integrity,
   one authoring file per record, resolving decision links, single-valued roll-ups, allowed edge pairs. A minimum
   the data satisfies but no rule states stays a warning until a record promotes it.
4. Every rule has a fixture: one broken record, applied in memory, fires exactly that rule on that focus with no
   cascade, while clean data fires nothing; a rule no mutation reaches is proven by quad injection.
5. `parity` runs the linter and the shapes over the same tree and compares the `core` and `sparql` ids as
   `(rule, subject, severity)`; stricter rules are tested by fixture alone; `python` rules are reported, never
   compared.
6. On conflict the rule text — `schema.yaml`, the authoring schema, a decision record — wins; the fix goes to the
   check that misreads it, never to the data.
7. Outside the graph: file structure, id uniqueness before emission and prose checks.

## Consequences

- A rule is written once and proven twice; a mutation caught by neither check is a register gap.
- Linter and shapes can each be replaced without touching the other.
- Fixtures double the test surface; the register keeps it enumerable.

## Alternatives

- Shapes generated wholesale from the schema — structural only; cross-field rules have no home.
- One checker — a graph check cannot see files, a file check cannot see derived graphs.
- Fixing the data so the checks agree — hides the disagreement.

## Sources

- https://www.w3.org/TR/shacl/ · core and SPARQL constraints, severities, reports · accessed 2026-09-23
- https://www.w3.org/TR/skos-reference/ · label integrity conditions · accessed 2026-09-23
- https://github.com/RDFLib/pySHACL · the validator used · accessed 2026-09-23

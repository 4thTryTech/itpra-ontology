# ADR 0048 — Retirement: a retired record stays, marked, and names its successor

Status: Accepted  
Date: 2026-11-24  
Supersedes: —  
Superseded by: —  

## Context

ADR 0003 makes a retirement MINOR because the id and its IRI stay, and ADR 0041 has a retired id keep
resolving; a record needs a way to say it is retired. The `deprecated` field is taken: it lists banned
synonyms (ADR 0007).

## Decision

1. A record is retired by the optional field `retired`, whose value is the `ontology_version` that retired it.
   The record keeps its id, label, definition, relations and file.
2. The optional field `replaced_by` holds the id of the record that succeeds it. It is allowed only on a
   retired record, resolves to another record and never names the record itself.
3. The two fields change the shape of a record: `schema_version` is 3.
4. The projection marks a retired record `owl:deprecated` with the version that retired it, and states
   `replaced_by` as `dcterms:isReplacedBy`; the record keeps resolving at its IRI (ADR 0041 rule 6).
5. The linter refuses a `retired` value that is not a version, a `replaced_by` that does not resolve or names
   its own record, and a `replaced_by` on a record that is not retired (ADR 0042).
6. Retirement is for a term that was released and defined something. A record is removed only in a MAJOR
   release, by a record that says why (ADR 0046).
7. An id that must keep resolving under a new name is retired with `replaced_by`. A rename of many ids at once
   is MAJOR and carried by a migration file (ADR 0045).

## Consequences

- A MINOR release can end a term without breaking a reference a consumer holds.
- A consumer learns of a retirement, and of the successor where there is one, from the data.
- Retired records accumulate: the vocabulary carries terms it no longer recommends until a MAJOR release
  removes them.
- A parser that refuses unknown fields must learn two more; the `schema_version` step says so.

## Alternatives

- Reuse `deprecated` — one field with two meanings; it already lists banned synonyms.
- A status enumeration — one state is needed, and a field for it is simpler to check.
- Remove the record and list it in a migration file — breaks every holder of the id in a MINOR release.

## Sources

- https://semver.org/ · a deprecation is announced in a minor release before removal in a major one · accessed 2026-11-08
- https://www.w3.org/TR/owl2-syntax/#Ontology_IRI_and_Version_IRI · the OWL 2 annotation vocabulary, `owl:deprecated` among it · accessed 2026-11-21
- https://www.w3.org/TR/cooluris/ · an IRI that keeps resolving · accessed 2026-09-19

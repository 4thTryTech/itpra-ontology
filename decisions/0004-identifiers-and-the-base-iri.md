# ADR 0004 — Identifiers and the base IRI

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Every term needs an identifier that is stable across releases, readable in a document, legal in a file name and in an
IRI, and unique across all term files. The scheme grew with the vocabulary; this record states it as it stands and
fixes the web address under which terms are published.

## Decision

1. An id matches `^[A-Za-z][A-Za-z0-9_.-]*$`, is unique across the whole vocabulary and never changes once released.
2. The kind of a term is its prefix: `CAP-` capability, `FUNC-` function, `PERSONA-`, `JRN-` journey, `WF-` workflow,
   `JG-` journey group, `PLANE-`, `SD-` service domain, `SDP-` placement, `GC-` governance construct, `ENV-DIM-`,
   `TEN-DIM-` and `MAT-STAGE-` dimensions, `AREA-` coverage area, `AUTON-` autonomy concept. A capability domain's id
   is its code. Entity types are `UPPER_SNAKE`, verbs `lower_snake`, quality attributes an `UPPER` token.
3. Each of the ten later service domains has a code — EUC, SVD, FLD, ADM, DCF, NET, GRC, ITSM, BIA, DXC — that every
   one of its terms carries after the kind prefix (`CAP-EUC-DEV-1`, `FUNC-euc-device-enrollment`). The first domain, IT
   Operations, keeps bare codes (`CAP-FND-1`): the one exception, kept for stability.
4. A capability id is `CAP-<CODE>-<n>`; a decomposed child is `CAP-<CODE>-<n>.<m>`, the dot being legal in an IRI path.
5. Requirement ids `FR-<CODE>-<n>`, `NFR-<QA>-<n>` and `NFR-<CODE>_<QA>-<n>` are reserved for consumers' registries; an
   NFR id embeds its quality attribute. `SVC-`, `OQ-` and `ADR-` are reserved prefixes with no term records.
6. The base IRI is `https://itpra.4thtry.tech/`. A term resolves at `<base>id/<ID>`, the schema at `<base>onto#`, a
   named graph at `<base>graph/<name>`, the ontology at `<base>onto` and a version at `<base>onto/<X.Y.Z>`.
7. The base is set in one configuration item and is the same in every environment; a change of base is MAJOR.

## Consequences

- An id can be read, searched, used as a file name and dereferenced without translation.
- Two id styles coexist, bare and coded, and a reader must know the exception; renaming the first domain's terms would
  be MAJOR for no consumer benefit.
- The underscore in a coded requirement id keeps the id to one hyphen-separated segment, so one rule parses every id.
- Minting IRIs commits the publisher to keeping them resolvable for as long as any consumer may hold them.
- A dedicated host with an empty path keeps every IRI short.

## Alternatives

- Opaque numeric ids with labels — stable but unreadable in documents, where the vocabulary is mostly used.
- Hash IRIs for terms (`onto#CAP-FND-1`) — one document for the whole vocabulary; slash IRIs let a term resolve alone.
- A shared or vendor host for the base — ties the IRIs to a service the publisher does not control.

## Sources

- https://www.w3.org/TR/cooluris/ · slash IRIs that resolve individually · accessed 2026-09-19
- https://www.w3.org/TR/owl2-syntax/#Ontology_IRI_and_Version_IRI · the ontology IRI and the version IRI · accessed 2026-11-21

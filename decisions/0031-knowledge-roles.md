# ADR 0031 — Knowledge roles

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Knowledge is usually held in separate stores: a service knowledge base, an ontology maintained elsewhere, a
retrieval index built from both. The vocabulary names stores and retrieval but not the governed meaning between
them, nor the obligations that carry meaning and restrictions from source to reader.

## Decision

1. `KNOWLEDGE-ROLE` "Knowledge role" is a Concept with no service domain: the partition of an organisation's
   knowledge by the role a body of knowledge plays, whether held in one store or several.
2. Three roles: the authoritative source, the record that is the source of truth for what it states, maintained
   by its owner; the governing semantic model, the vocabulary and ontology that content and instances conform to
   and take their meaning from; the derived retrieval representation, an index, embedding set, graph or cache
   built from the other two for humans and delegated actors to find and use.
3. A derived representation is never authoritative: where it disagrees with its source, the source prevails, and
   it inherits its sources' access restrictions, erasure and retention decisions and traceability.
4. The role is a property of the deployment, never of the store type; one store may play several. Store counts,
   refresh and which systems play which role are scenario decisions.
5. One concept, in the shape of ADR 0028: no role needs relationships of its own, and a role one store can play
   twice is a partition, not a capability. Edges: `applies_to` `CAP-BIA-GOV-7`, `CAP-ITO-DATA-1`, `CAP-ITO-GOV-9`,
   `CAP-ITO-GOV-4`, `AUTON-ACTOR`.
6. No verb and no quality attribute is added (ADR 0008, ADR 0016): conformance, derivation and authority are
   instance-level obligations, carried by the definition and by functions (ADR 0038).
7. Conformance is a rule source for existing checks (`FUNC-bia-quality-profiling` at authoring time,
   `CAP-ADM-ENG-7` guardrails at answer time), not a function. Also not minted: a thesaurus stage, a
   knowledge-graph capability, retrieval-augmented generation as a term, graph-backed retrieval as a function,
   standards or versions in any term.
8. `FUNC-bia-golden-record`, `FUNC-dxc-identity-resolution` and `FUNC-itsm-record-reconciliation` name one
   behaviour over different populations; they cross-reference each other and are not merged (MAJOR, ADR 0003).

## Consequences

- Store topology is expressible without asserting a store count; obligations follow the role, not the box.
- Source-over-derivative authority is stated once, at the root.
- Trade-off: obligations in definition text are less machine-checkable than edges.

## Alternatives

- Three sibling concepts — no role carries relationships of its own.
- A knowledge-graph capability — names the fastest-moving part and leaves governed meaning unnamed.
- New verbs `conforms_to`, `derived_representation_of`, `authoritative_over` — instance-level facts, not
  term-level.

## Sources

- https://dl.acm.org/doi/10.14778/3718057.3718067 · knowledge-graph ecosystems with distinct sources, schema and derived artefacts · accessed 2026-09-14
- https://truto.one/blog/how-to-maintain-document-level-rbac-in-enterprise-rag-pipelines/ · a retrieval index carries the access restrictions of its source documents · accessed 2026-09-14

# ADR 0041 — The RDF projection: the YAML stays authoritative; emitted graphs are derived

Status: Accepted  
Date: 2026-11-22  
Supersedes: —  
Superseded by: —  

Origin: Consolidates the projection decisions of 2026-09 to 2026-11 for the pipeline under `tools/`.

## Context

People edit the vocabulary as YAML; machines want resolvable IRIs, a concept scheme, graph queries and shape
checks. The projection must not become a second source of truth and must be rebuildable from the files alone.

## Decision

1. Knowledge roles: the YAML is authoritative and governing; the authoring schema's per-verb domain, range and
   cardinality (ADR 0008) govern those facts only; linter and shapes are checks; everything emitted is derived —
   rebuilt on every run, never edited, inheriting its sources' obligations (ADR 0038).
2. Modelling: every term is a `skos:Concept` in one scheme; entity types are a thin OWL class layer (`owl:Class` ⊑
   `skos:Concept`) punned on entity-type ids only; verbs are object properties in the schema namespace, linked to
   their `RelationshipType` records by `rdfs:seeAlso`. `grouped_by` is membership, not `skos:broader`; `deprecated`
   is a hidden-label sub-property; labels and definitions carry `@en`; `source:` is a justification link
   (⊑ `prov:wasInfluencedBy`) plus `dcterms:source`. No blank nodes; no domain, range, inverse or functional axioms.
3. Identifiers and graphs follow ADR 0004: named graphs `schema`, `t1` and `inferred`; a layer adds graphs of
   its own (ADR 0043). Queries name graphs; none reads their union.
4. Derivation: versioned SPARQL `CONSTRUCT` rules, in a stated order, write only into `inferred` — roll-ups to
   plane and service domain, function to domain, the boundary-governed functions. No reasoner; no inverse
   property is minted.
5. Schema source: type and verb lists stay in `schema.yaml`, enumerations are generated from them, every other
   schema fact lives once in the authoring schema; generated files are canonicalised (RDFC-1.0, then a line sort);
   dependencies are pinned exactly. The store is embedded, in process, loaded from the build, never committed.
6. Retirement is not erasure: a retired id keeps resolving with `owl:deprecated` and `dcterms:isReplacedBy` (the
   YAML `deprecated` field is a banned synonym — ADR 0007); content that must go is withdrawn and re-released.

## Consequences

- One build reproduces the graphs byte for byte; a graph that disagrees with the YAML is a pipeline defect.
- A query names its graphs and reads exactly what it asked for.
- Canonicalisation and exact pins make upgrades deliberate: the price of determinism.

## Alternatives

- OWL reasoning for roll-ups — unordered, hard to version, mints inverses.
- `skos:broader` for membership — a member is not a narrower concept.
- A hosted triple store as the source — not reviewable as a file is.

## Sources

- https://www.w3.org/TR/skos-reference/ · concept schemes, labels, `skos:broader` · accessed 2026-09-23
- https://www.w3.org/TR/shacl/ · constraints as shapes rather than axioms · accessed 2026-09-23
- https://www.w3.org/TR/prov-o/ · `prov:wasInfluencedBy` versus `prov:wasDerivedFrom` · accessed 2026-09-23
- https://www.w3.org/TR/rdf-canon/ · RDFC-1.0 canonicalisation · accessed 2026-11-22
- https://github.com/oxigraph/oxigraph · the embedded store and its Python binding · accessed 2026-09-23

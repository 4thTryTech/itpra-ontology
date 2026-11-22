# ADR 0043 — Builds, artefacts and the consumer overlay: the core from the vocabulary alone

Status: Accepted  
Date: 2026-11-22  
Supersedes: —  
Superseded by: —  

Origin: Consolidates the build and publication decisions taken between 2026-09 and 2026-11 for the pipeline under `tools/`.

## Context

The vocabulary is published on its own (ADR 0001, ADR 0003), yet its first consumer projects eleven requirement
registries and architecture documents beside it. The pipeline must build the public projection from the vocabulary
alone, let a consumer layer its own graphs on a pinned release, and make every artefact identifiable.

## Decision

1. Core and overlay: the **core** is built from `schema.yaml`, `entities.yaml`, `relationships.yaml` and `terms/`
   — the `schema`, `t1` and `inferred` graphs, the structural, cross-field and verb-pair shapes, the generated
   schema artefacts. What a consumer adds is an **overlay** it configures: its registries become `req/<X>` graphs,
   its requirement rule and shapes load, its linter is what `parity` compares against. Without an overlay none of
   that exists and `parity` refuses to run.
2. A consumer layers its overlay on the released core artefact of the version it pins (ADR 0003) and never rebuilds
   the core. The public projection is the core; overlay graphs are the consumer's to publish or keep.
3. Provenance without timestamps: every build records the `ontology_version`, a content hash of its inputs, the
   pipeline version, the lockfile hash and the rules version; each term carries its authoring file;
   `prov:wasDerivedFrom` is reserved for dataset-to-input provenance.
4. Artefacts are built once, addressed by digest and attached to the immutable release; a second build of the same
   inputs reproduces the first byte for byte. One base IRI in every environment (ADR 0004); a deployment promotes
   the identical digest and nothing is rebuilt.
5. Generated files and stores are never committed; a freshness check fails when a committed generated file is stale.
6. The documentation site and the resolvable IRIs are served from released artefacts; the term explorer is a
   generated page, not a source file.

## Consequences

- The public build has no path into a consumer's documents, so the publication boundary holds by construction.
- A change in the core reaches a consumer only through a re-pin.
- Content-hash provenance compares builds across machines; a commit hash would be circular once published.
- An upgrade that changes output bytes is a release event.

## Alternatives

- One build for vocabulary and consumer content — ties the public projection to a private repository.
- Committing canonical RDF — duplicates the files, rewrites every line on a base change, invites edits.
- Timestamps in provenance — defeat byte-identical builds.

## Sources

- https://www.w3.org/TR/prov-o/ · derivation and influence relations · accessed 2026-09-23
- https://www.w3.org/TR/vocab-dcat-3/ · describing a dataset release and its distributions · accessed 2026-09-23
- https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/ · digest-pinned release assets · accessed 2026-11-08
- https://reproducible-builds.org/docs/definition/ · the byte-identical rebuild test · accessed 2026-09-23

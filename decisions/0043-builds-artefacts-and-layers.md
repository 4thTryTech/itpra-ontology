# ADR 0043 — Builds, artefacts and layers: the build reads the vocabulary alone

Status: Accepted  
Date: 2026-11-22  
Supersedes: —  
Superseded by: —  

Origin: Consolidates the build and publication decisions taken between 2026-09 and 2026-11 for the pipeline under `tools/`.

## Context

The vocabulary is published on its own (ADR 0001, ADR 0003). Its projection must be buildable from the
vocabulary's files alone, open to extension without changing what it builds, and identifiable artefact by
artefact.

## Decision

1. Inputs: a build reads the vocabulary alone — `schema.yaml`, `entities.yaml`, `relationships.yaml` and
   `terms/` — and projects it to the `schema`, `t1` and `inferred` graphs, checked by the structural, cross-field
   and verb-pair shapes. Every input is a YAML file under the configured repository root, outside hidden, output
   and cache directories; anything else is refused by name.
2. Layers: a build can take layers. A layer adds named graphs of its own, rules that run after the vocabulary's
   and write to `inferred`, and shapes checked beside the vocabulary's; its input files and code join the
   provenance record. A build without a layer is the published projection.
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

- The published build reads nothing outside the vocabulary, so what is published is what the repository holds.
- A layer is built on a pinned release (ADR 0003); a vocabulary change reaches it only through a re-pin.
- Content-hash provenance compares builds across machines; a commit hash would be circular once published.
- An upgrade that changes output bytes is a release event.

## Alternatives

- Extension by editing the pipeline — every extension becomes a fork of the build.
- Committing canonical RDF — duplicates the files, rewrites every line on a base change, invites edits.
- Timestamps in provenance — defeat byte-identical builds.

## Sources

- https://www.w3.org/TR/prov-o/ · derivation and influence relations · accessed 2026-09-23
- https://www.w3.org/TR/vocab-dcat-3/ · describing a dataset release and its distributions · accessed 2026-09-23
- https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/ · digest-pinned release assets · accessed 2026-11-08
- https://reproducible-builds.org/docs/definition/ · the byte-identical rebuild test · accessed 2026-09-23

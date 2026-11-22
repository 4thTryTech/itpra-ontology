# Changelog

Changes to the vocabulary, newest first. Versions follow [ADR 0003](decisions/0003-versioning-releases-and-pinning.md).

## Unreleased

No vocabulary change. The ontology-as-code pipeline joins the repository as `tools/itpra-onto/`
([ADR 0041](decisions/0041-the-rdf-projection-roles-modelling-and-derivation.md),
[ADR 0042](decisions/0042-validation-parity-register-shapes-fixtures-and-the-parity-check.md),
[ADR 0043](decisions/0043-builds-artefacts-and-the-consumer-overlay.md)): the vocabulary projected to RDF in named
graphs, SPARQL derivation rules, SHACL shapes with a fixture per rule, a reproducible build and a second CI job that
runs them. Its generated artefacts are not yet released assets.

## 4.0.0 — 2026-11-21

First public release of the ITPRA ontology as its own repository. The content equals `3.16.3`; what changes is the
consumption contract: a public location, the CC BY 4.0 and Apache-2.0 licences, identifiers minted under
`https://itpra.4thtry.tech/`, and the obligation to pin a release.

Contents: `schema.yaml`, `entities.yaml`, `relationships.yaml`, `terms/` (1,594 records), `decisions/` (0001–0040),
the six CI checks under `tools/` with their tests, and the `release` workflow, which builds the source archive
`itpra-ontology-X.Y.Z.tar.gz` with its `sha256` from the tag and publishes the immutable release.

## Before 4.0.0

The vocabulary's history from 1.0.0 (2026-05-21) to 3.16.3 is summarised in [README.md](README.md#history-before-publication);
the decision records consolidate what was decided in that period.

# Changelog

Changes to the vocabulary, newest first. Versions follow [ADR 0003](decisions/0003-versioning-releases-and-pinning.md).

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

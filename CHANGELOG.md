# Changelog

Changes to the vocabulary, newest first. Versions follow [ADR 0003](decisions/0003-versioning-releases-and-pinning.md).

## 4.0.1 — 2026-11-23

No vocabulary change: every term, id and verb equals `4.0.0`. The first release that carries tooling (ADR 0044): one
tag covers the vocabulary, the decision records and the pipeline package, and a release with only tooling or record
changes is a PATCH.

The ontology-as-code pipeline joins the repository as `tools/itpra-onto/` (ADR 0041, ADR 0042, ADR 0043): the
vocabulary projected to RDF in named graphs, SPARQL derivation rules, SHACL shapes with a fixture per rule, a
reproducible build and a second CI job that runs them. It installs as the `itpra-onto` package from this tag, with its
rules, shapes, schema and fixtures inside; the vocabulary's own lint rules now live in it and `tools/ontology-lint.py`
runs them. Its generated artefacts are not yet released assets.

Contents beyond `4.0.0`: `decisions/` 0041–0044 and `tools/itpra-onto/`. Nothing a consumer of the vocabulary files
relies on changes; a consumer of the package pins this tag for both.

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

# Changelog

Changes to the vocabulary, newest first. Versions follow [ADR 0003](decisions/0003-versioning-releases-and-pinning.md).

## 5.0.0 — 2026-11-24

**MAJOR: ids renamed.** IT Operations takes the code `ITO` on every id and file name, as the ten other service domains
carry theirs (ADR 0045, amending ADR 0004, 0007, 0010, 0011, 0012 and 0017). No term is added or removed and no
label, definition or relation changes meaning; 356 records change id and 26 files change name.

| Kind | Before | From 5.0.0 |
|---|---|---|
| Capability domain (11) | `FND`, `SEC`, `OBS`, … | `ITO-FND`, `ITO-SEC`, `ITO-OBS`, … |
| Capability (83) | `CAP-FND-1` | `CAP-ITO-FND-1` |
| Function (224) | `FUNC-version-control` | `FUNC-ito-version-control` |
| Persona (3) | `PERSONA-platform-team` | `PERSONA-ito-platform-team` |
| Journey (18), workflow (17) | `JRN-onboard-consumer`, `WF-onboard-consumer` | `JRN-ito-onboard-consumer`, `WF-ito-onboard-consumer` |
| Files | `domains.yaml`, `capabilities-foundation.yaml`, `functions-foundation.yaml`, `personas.yaml`, `journeys.yaml`, `workflows.yaml` | `domains-ito.yaml`, `capabilities-ito-fnd.yaml`, `functions-ito-fnd.yaml`, `personas-ito.yaml`, `journeys-ito.yaml`, `workflows-ito.yaml` |

Migrating: `migrations/5.0.0.yaml` lists every old id and file with its successor. Rewrite each reference a registry,
document or pin holds (`met_by`, `verified_by`, `derived_from`, required functions), then re-pin; an IRI
`<base>id/<old>` becomes `<base>id/<new>`. Requirement ids are the consumer's own and need not change: the coded
forms `FR-<CODE>-<n>` and `NFR-<CODE>_<QA>-<n>` are now the form for every domain, and the uncoded forms still parse.

Also in this release: every renamed record's `source` adds `ADR 0045`; `SD-IT-OPERATIONS` gains the alias `ITO`;
`schema.yaml` states the coded id forms and drops the first-domain exception; the `FUNCTION` and `FR` entity
definitions and the `belongs_to_service_domain` definition lose their wording of that exception; references to the
renamed ids in other domains' definitions and comments follow. The pipeline's fixtures and tests use the new ids.
Decision records before 0045 keep their text: an id written there without the code reads as its coded successor.

Tooling: `tools/itpra-onto/` now builds, validates and compares the vocabulary alone, and a build can take layers
(`itpra_onto.layers`; ADR 0043). The `[overlay]` configuration table and the requirement classes, rule, shapes and
fixtures that went with it leave the package, so a configuration or caller that used them changes with this release.
The built `schema` graph no longer declares `FR` and `NFR` under `REQUIREMENT`, nor the `statement`, `target` and
`meets` properties. ADR 0041, ADR 0042 and ADR 0043 are reworded to match; ADR 0043 has a new title and file name.

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

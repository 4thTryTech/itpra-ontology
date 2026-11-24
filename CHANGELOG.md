# Changelog

Changes to the vocabulary, newest first. Versions follow [ADR 0003](decisions/0003-versioning-releases-and-pinning.md).

## 5.0.0 — 2026-11-24

**MAJOR: ids renamed, records removed.** The first release prepared for use outside the project that wrote it. Three
changes can break a consumer; `migrations/5.0.0.yaml` lists every id and file they touch.

**1. IT Operations takes the code `ITO`** on every id and file name, as the ten other service domains carry theirs
(ADR 0045). 339 records change id and 25 files change name; labels and relations are as they were.

| Kind | Before | From 5.0.0 |
|---|---|---|
| Capability domain (11) | `FND`, `SEC`, `OBS`, … | `ITO-FND`, `ITO-SEC`, `ITO-OBS`, … |
| Capability (83) | `CAP-FND-1` | `CAP-ITO-FND-1` |
| Function (224) | `FUNC-version-control` | `FUNC-ito-version-control` |
| Persona (3) | `PERSONA-platform-team` | `PERSONA-ito-platform-team` |
| Journey (18) | `JRN-onboard-consumer` | `JRN-ito-onboard-consumer` |
| Files | `domains.yaml`, `capabilities-foundation.yaml`, `functions-foundation.yaml`, `personas.yaml`, `journeys.yaml` | `domains-ito.yaml`, `capabilities-ito-fnd.yaml`, `functions-ito-fnd.yaml`, `personas-ito.yaml`, `journeys-ito.yaml` |

**2. Records without content leave** (ADR 0046). The 30 `Workflow` records catalogued diagrams the vocabulary does not
hold, and the 4 placements (`SDP-…`) stood in for capability domains that now exist: all 34 are removed, with
`terms/workflows.yaml`, `terms/workflows-itsm.yaml` and `terms/service-domain-placements.yaml`, and have no successor.
The vocabulary holds 1,560 records. The `WORKFLOW` entity type, the `Workflow` type, the id form `WF-<code>-<slug>` and
the verb `realized_in` stay for a consumer's own diagrams. The placements' market words are now aliases: unified
endpoint management (UEM, MDM, EMM) on `EUC-DEV`, product analytics on `BIA-PRD`, digital experience management (DXM)
on `SD-DIGITAL-EXPERIENCE`; robotic process automation has no record. `SVC-` is no longer a reserved prefix, and the
reserved requirement-id forms are `FR-<CODE>-<n>` and `NFR-<CODE>_<QA>-<n>` only.

**3. Service domains read as peers** (ADR 0047). The 16 `interfaces_with` edges from a service domain to a plane are
removed; the verb and its declared pair stay, with no instance in the vocabulary. The eleven service-domain
definitions state what each domain is and owns in its own right, and the planes, quality attributes, governance
constructs, journey groups, entity types and verbs are worded to hold for all eleven; "the infrastructure platform"
names what IT Operations owns. No id, label or other relation changes, and each reworded record's `source` names
ADR 0047.

Migrating: rewrite each reference a registry, document or pin holds (`met_by`, `verified_by`, `derived_from`, required
functions) with the `ids` map, drop references to the ids under `removed`, then re-pin; an IRI `<base>id/<old>` becomes
`<base>id/<new>`. Requirement ids are the consumer's own.

Also in this release:

- **Retirement** (ADR 0048): a record can carry `retired`, the version that retired it, and `replaced_by`, its
  successor's id; `schema_version` is 3. The projection marks a retired record `owl:deprecated` with
  `dcterms:isReplacedBy`. No record is retired in this release.
- **Records** (ADR 0049): a decision record states its rules as they stand. Records 0001–0045 cite current ids, and a
  rule a later record amends is restated in place and names that record.
- **Term files** open with what they hold, their type, id form and deciding record; working notes leave the comments.
  `JRN-ito-run-delegated-actor` and `JRN-adm-build-model-grounded-behaviour` cite the records that decided them
  (ADR 0033, ADR 0034). Every renamed record's `source` adds `ADR 0045`; `SD-IT-OPERATIONS` gains the alias `ITO`.

Tooling (`tools/itpra-onto/`), which changes output and a consumer's configuration:

- The package builds, validates and compares the vocabulary alone, and a build can take layers (`itpra_onto.layers`;
  ADR 0043). The `[overlay]` configuration table and the requirement classes, rule, shapes and fixtures that went with
  it leave the package. The built `schema` graph no longer declares `FR` and `NFR` under `REQUIREMENT`, nor the
  `statement`, `target` and `meets` properties.
- The built graphs state their licence (`dcterms:license`, CC BY 4.0; ADR 0002) and project the retirement fields.
- The package's version is the release's: `5.0.0`, and `pipeline_version` in a build's provenance with it.
- The `itpra-onto release` command, which did nothing, is removed.
- The version-bump check lets a vocabulary change join a version that is on `master` but not tagged yet, and asks
  for a bump once the tag exists.
- The release carries the RDF projection built from the tag, `itpra-ontology-5.0.0-rdf.tar.gz`, with its `sha256`,
  beside the source archive (ADR 0043).

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

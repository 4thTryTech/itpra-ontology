# ITPRA ontology

The controlled vocabulary of the IT Platform Reference Architecture (ITPRA): the service domains, planes, capability
domains, capabilities, functions, personas, journeys, workflows, dimensions, governance constructs, quality attributes
and cross-cutting concepts an enterprise IT platform is described with. Tool-agnostic, neutral to any operating model,
and machine-readable so that architecture documents can be checked against it ([ADR 0001](decisions/0001-purpose-scope-and-tier-neutrality.md)).

**Status:** first public release `4.0.0` in preparation. The content is at `3.16.3`, which is what `4.0.0` publishes.

## What is here

| Path | Contents |
|---|---|
| `schema.yaml` | The meta-schema: record fields, allowed `type` values, relationship verbs, id conventions and the two version numbers |
| `entities.yaml` · `relationships.yaml` | The entity types and the relationship verbs, each a term of its own ([ADR 0008](decisions/0008-entity-types-and-relationship-verbs.md)) |
| `terms/` | The vocabulary, split by kind and service domain: `domains-*`, `capabilities-*`, `functions-*`, `personas-*`, `journeys-*`, `workflows-*` and the shared concept files ([ADR 0007](decisions/0007-term-records-files-and-aliases.md)) |
| `decisions/` | The decision records that shape the vocabulary, numbered from 0001 in reading order ([index](decisions/README.md)) |
| `tools/` · `tests/` | The checks that run in CI |

## Reading the vocabulary

- A term is one YAML record: `id`, `term`, `type` and `definition`, with optional `aliases`, `deprecated`, `relates_to` and
  `source`. Aliases are the words a reader may search for; the id never changes once released.
- The prefix tells the kind: `CAP-` capability, `FUNC-` function, `PERSONA-`, `JRN-` journey, `WF-` workflow, `PLANE-`,
  `SD-` service domain, `GC-` governance construct, `AUTON-` autonomy concept, and so on. Each of the ten later service
  domains carries its code (`CAP-EUC-DEV-1`); the first domain's ids are bare (`CAP-FND-1`) ([ADR 0004](decisions/0004-identifiers-and-the-base-iri.md)).
- `source:` names the decision that minted or changed the record as `ADR NNNN`, always a record in `decisions/`
  ([ADR 0005](decisions/0005-decision-records-citations-and-the-writing-standard.md)).
- A term resolves on the web at `https://itpra.4thtry.tech/id/<ID>`; the schema at `https://itpra.4thtry.tech/onto#`.

## Using and pinning it

`schema.yaml` carries two numbers: `schema_version`, the shape of a record, and `ontology_version`, the content, under
Semantic Versioning. A MAJOR change can break a consumer's checks; MINOR adds; PATCH is editorial
([ADR 0003](decisions/0003-versioning-releases-and-pinning.md)). Consume a **release**: vendor the release archive and
record its version, tag, commit and hash; pin a package dependency to the tag; or name the version IRI. Do not track
`master`.

Describe a scenario or an implementation with this vocabulary, and keep your own terms, requirements and
operating-model mappings in your own repository. Cite a record here by its URL.

## Changing it

Pull requests are welcome. A term change lands together with the decision record that decides it and the version bump
it requires. The backbone — the schema, entity types and verbs, planes, quality attributes, journey groups, governance
constructs, dimension values and the service-domain set — needs a record and a maintainer's review. Commits carry a
Developer Certificate of Origin sign-off. See [CONTRIBUTING.md](CONTRIBUTING.md) and [GOVERNANCE.md](GOVERNANCE.md)
([ADR 0006](decisions/0006-governance-and-contribution.md)).

## Licence and citation

The vocabulary, its generated projections and the decision records are licensed under
[Creative Commons Attribution 4.0 International](LICENSE); the code under [Apache License 2.0](LICENSE-CODE)
([ADR 0002](decisions/0002-licence-and-attribution.md)). Cite the vocabulary as [CITATION.cff](CITATION.cff) states.

## History before publication

The vocabulary was developed from 2026-05 inside a private reference-architecture repository and became its own
repository at `4.0.0`. The decision records consolidate what was decided in that period, one decision per record.

| Version | Date | What changed |
|---|---|---|
| 1.0.0 – 2.5.0 | 2026-05 | First versioned baseline: the first service domain's eleven capability domains, personas, journeys, dimensions and governance constructs; the function layer (2.2 – 2.4); service domains, single-valued attribution and placements (2.5) |
| 3.0.0 | 2026-05-29 | Function layer simplified: no tier field, no function `derived_from` (MAJOR); the ten further service domains' taxonomies followed |
| 3.1.0 – 3.2.0 | 2026-06 | The automation boundary; coverage areas |
| 3.3.0 | 2026-08-21 | The telemetry control plane |
| 3.4.0 – 3.10.0 | 2026-09-11 | The agentic vocabulary: delegated actor, harness and in-flight control; agentic execution, agent state and the model gateway; model-grounded engineering and evaluation; delegated authority and AI-system risk; four quality attributes; attribution through the delegated-authority chain |
| 3.11.0 – 3.13.0 | 2026-09 | The boundary becomes area-aware; generative-content provenance; knowledge roles, the semantic progression and the obligations of derived knowledge |
| 3.14.0 – 3.15.0 | 2026-09 | Durable execution; agentic execution explainability |
| 3.16.0 | 2026-09-24 | Schema formalisation: verbs declared with domain, range and cardinality; `CONCEPT` and `FR` entity types; id and `source` conventions |
| 3.16.1 – 3.16.3 | 2026-11-21 | Preparation for publication: the base IRI; citations re-pointed to these records; comments scrubbed; three engineering definitions complete the durable-execution obligations |
| 4.0.0 | pending | First public release: a new location, the licences, minted IRIs and the pinning contract; no term changes |

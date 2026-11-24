# Decision records

The decisions that shape this vocabulary: one decision per record, numbered from 0001 in reading order. A term's `source:`
cites the record that minted or changed it as `ADR NNNN`. From outside this repository a record is cited by its URL.

## Conventions

- One decision per record, written to [the template](0000-template.md); `tools/adr-lint.py` enforces the shape and runs in CI.
- Statuses: Accepted · Superseded (names its successor) · Deprecated · Rejected. A record is proposed as a pull request, together
  with the change it decides, and lands Accepted. Nothing else reaches `master`.
- Short: at most 60 lines and 500 words (hard limit 80 / 700). Context in six lines; Decision as numbered rules in the present
  tense; Consequences in three to six bullets with at least one trade-off; Alternatives one line each (name — why not); Sources as
  URL · what it supports · accessed date.
- Neutral: a record names no product and uses no operating-model process vocabulary in Context, Decision or Consequences. A
  standard is named only where the standard is the behaviour. Market words appear as aliases, never as ids.
- Self-contained: links stay inside this folder or point to the web; grounding is listed under Sources, never linked as files.
- Records consolidated before publication carry an `Origin:` line and start Accepted on the import date.

## Index

| ADR | Title | Status | Date |
|---|---|---|---|
| 0001 | [Purpose, scope and tier neutrality](0001-purpose-scope-and-tier-neutrality.md) | Accepted | 2026-11-21 |
| 0002 | [Licence and attribution](0002-licence-and-attribution.md) | Accepted | 2026-11-21 |
| 0003 | [Versioning, releases and pinning](0003-versioning-releases-and-pinning.md) | Accepted | 2026-11-21 |
| 0004 | [Identifiers and the base IRI](0004-identifiers-and-the-base-iri.md) | Accepted | 2026-11-21 |
| 0005 | [Decision records, citations and the writing standard](0005-decision-records-citations-and-the-writing-standard.md) | Accepted | 2026-11-21 |
| 0006 | [Governance and contribution](0006-governance-and-contribution.md) | Accepted | 2026-11-21 |
| 0007 | [Term records, files and aliases](0007-term-records-files-and-aliases.md) | Accepted | 2026-11-21 |
| 0008 | [Entity types and relationship verbs](0008-entity-types-and-relationship-verbs.md) | Accepted | 2026-11-21 |
| 0009 | [Service domains — eleven peers, attribution and placement](0009-service-domains-eleven-peers-attribution-and-placement.md) | Accepted | 2026-11-21 |
| 0010 | [Planes and capability domains](0010-planes-and-capability-domains.md) | Accepted | 2026-11-21 |
| 0011 | [The function layer](0011-the-function-layer.md) | Accepted | 2026-11-21 |
| 0012 | [Personas](0012-personas.md) | Accepted | 2026-11-21 |
| 0013 | [Journeys, journey groups and workflows](0013-journeys-journey-groups-and-workflows.md) | Accepted | 2026-11-21 |
| 0014 | [Environment, tenancy and maturity dimensions](0014-environment-tenancy-and-maturity-dimensions.md) | Accepted | 2026-11-21 |
| 0015 | [Governance constructs](0015-governance-constructs.md) | Accepted | 2026-11-21 |
| 0016 | [Quality attributes](0016-quality-attributes.md) | Accepted | 2026-11-21 |
| 0017 | [IT Operations (ITO) — capability domains](0017-it-operations-ito-capability-domains.md) | Accepted | 2026-11-21 |
| 0018 | [End-User Computing (EUC) — capability domains and boundary](0018-end-user-computing-euc-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0019 | [Service Desk (SVD) — capability domains and boundary](0019-service-desk-svd-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0020 | [Onsite / Field Support (FLD) — capability domains and boundary](0020-onsite-field-support-fld-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0021 | [Application Development & Maintenance (ADM) — capability domains and boundary](0021-application-development-and-maintenance-adm-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0022 | [Data Center & Facilities (DCF) — capability domains and boundary](0022-data-center-and-facilities-dcf-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0023 | [Network & Connectivity (NET) — capability domains and boundary](0023-network-and-connectivity-net-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0024 | [Enterprise Security, Risk & Compliance (GRC) — capability domains and boundary](0024-enterprise-security-risk-and-compliance-grc-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0025 | [IT Service Management & Integration (ITSM) — capability domains and boundary](0025-it-service-management-and-integration-itsm-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0026 | [Business Intelligence & Analytics (BIA) — capability domains and boundary](0026-business-intelligence-and-analytics-bia-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0027 | [Digital Experience & Channels (DXC) — capability domains and boundary](0027-digital-experience-and-channels-dxc-capability-domains-and-boundary.md) | Accepted | 2026-11-21 |
| 0028 | [The automation boundary](0028-the-automation-boundary.md) | Accepted | 2026-11-21 |
| 0029 | [Coverage areas](0029-coverage-areas.md) | Accepted | 2026-11-21 |
| 0030 | [Delegated actor, agent harness and in-flight control](0030-delegated-actor-agent-harness-and-in-flight-control.md) | Accepted | 2026-11-21 |
| 0031 | [Knowledge roles](0031-knowledge-roles.md) | Accepted | 2026-11-21 |
| 0032 | [Telemetry control plane](0032-telemetry-control-plane.md) | Accepted | 2026-11-21 |
| 0033 | [Agentic execution, agent state and the model gateway](0033-agentic-execution-agent-state-and-the-model-gateway.md) | Accepted | 2026-11-21 |
| 0034 | [Model-grounded engineering and evaluation](0034-model-grounded-engineering-and-evaluation.md) | Accepted | 2026-11-21 |
| 0035 | [Delegated authority — governance, runtime attribution and AI-system risk](0035-delegated-authority-governance-runtime-attribution-and-ai-system-risk.md) | Accepted | 2026-11-21 |
| 0036 | [Generative-content provenance](0036-generative-content-provenance.md) | Accepted | 2026-11-21 |
| 0037 | [The semantic progression](0037-the-semantic-progression.md) | Accepted | 2026-11-21 |
| 0038 | [Obligations of derived knowledge](0038-obligations-of-derived-knowledge.md) | Accepted | 2026-11-21 |
| 0039 | [Durable execution](0039-durable-execution.md) | Accepted | 2026-11-21 |
| 0040 | [Agentic execution explainability](0040-agentic-execution-explainability.md) | Accepted | 2026-11-21 |
| 0041 | [The RDF projection: the YAML stays authoritative; emitted graphs are derived](0041-the-rdf-projection-roles-modelling-and-derivation.md) | Accepted | 2026-11-22 |
| 0042 | [Validation parity: one rule register, shapes beside the linter, fixtures, the parity check](0042-validation-parity-register-shapes-fixtures-and-the-parity-check.md) | Accepted | 2026-11-22 |
| 0043 | [Builds, artefacts and layers: the build reads the vocabulary alone](0043-builds-artefacts-and-layers.md) | Accepted | 2026-11-22 |
| 0044 | [One release for the vocabulary and its tooling](0044-one-release-for-the-vocabulary-and-its-tooling.md) | Accepted | 2026-11-23 |
| 0045 | [IT Operations carries its code: one id and file form for all eleven service domains](0045-it-operations-carries-its-code.md) | Accepted | 2026-11-23 |

# ADR 0026 — Business Intelligence & Analytics (BIA) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Business analytics shares words with the platform's operational Data & Analytics (`DATA`), Observability (`OBS`)
and Infrastructure Substrate (`SUB`) and with the enterprise control authority. The Business Intelligence &
Analytics domain (`SD-BUSINESS-ANALYTICS`, ADR 0009) needs capability domains on its two planes and a boundary
that keeps it the business side of the data value chain.

## Decision

1. `SD-BUSINESS-ANALYTICS` has seven capability domains: the data-supply-and-govern domains on the Resource plane
   — `BIA-INT` Data Integration & Ingestion, `BIA-WHS` Data Warehouse, Lakehouse & Modeling, `BIA-GOV` Data
   Governance, Quality & Master Data — and the insight domains on the Experience plane — `BIA-SEM` Semantic Layer
   & Self-Service Analytics, `BIA-RPT` Reporting & Visualization, `BIA-SCI` Data Science & Advanced Analytics,
   `BIA-PRD` Product & User-Behavior Analytics. Capability ids are `CAP-BIA-<GRP>-<n>` (ADR 0004).
2. Reporting stays separate from the semantic layer — governed metric definition versus rendered, distributed
   output — and product analytics from data science.
3. Five personas (ADR 0012) add two specialist-producer archetypes: Insight Consumer, Data & Analytics Engineering
   Team, Data Scientist & Advanced Analyst, Product Analytics Team, Data Steward & Governance Owner. A sixth,
   Semantic Modeller & Ontology Owner, is added by ADR 0037.
4. The domain owns the business data-and-insight value chain and consumes the platform's data substrate: `BIA-INT`
   and `BIA-WHS` use the pipelines, streaming and storage of `DATA` and `SUB` as the business side of the boundary
   integration `CAP-DATA-5`, and operate no infrastructure.
5. The seams: `BIA-PRD` measures how people use products for business optimisation, distinct from detecting
   anomalous user and entity behaviour (`CAP-SEC-7`); `BIA-SCI` builds business models, distinct from analytics
   over operational telemetry (`CAP-OBS-6`); `BIA-GOV` governs business data, distinct from platform data
   governance (`CAP-DATA-4`), and applies the enterprise control catalogue (`SD-SECURITY-GRC`) without authoring
   it; `BIA-SEM` and `BIA-RPT` serve insight without owning the platform's consumer surface (`EXP`).

## Consequences

- ADR 0009's headline distinction — business insight versus the platform's operational data and telemetry — holds
  at every capability, not only at the domain.
- Four of seven domains sit on the Experience plane: the domain serves insight, and its plane mix is less even
  than the platform's.
- Consuming the substrate leaves the analytical store's availability and cost with the platform; the domain owns
  the models, semantics and governed offering on top.

## Alternatives

- Fold reporting into the semantic layer — different consumers and lifecycles; regulatory reporting carries its
  own evidence obligations.
- Own the analytical store's compute and storage — that substrate is the platform's (`DATA`, `SUB`); the domain
  owns the models and semantics on it.

## Sources

- https://dama.org/dmbok2r-infographics/ · data-management knowledge areas framing the value chain and the governance centre (BIA-GOV) · accessed 2026-05-30
- https://www.ibm.com/think/topics/user-behavior-analytics · business user-behaviour analytics vs security entity-behaviour detection · accessed 2026-05-30

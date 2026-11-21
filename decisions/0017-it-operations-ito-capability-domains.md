# ADR 0017 — IT Operations (ITO) — capability domains

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The IT Operations service domain (`SD-IT-OPERATIONS`) owns and operates the infrastructure platform. Its capabilities
need a top-level grouping that spans infrastructure, delivery, data and neutral governance and is stable enough for
capability ids to hang off it.

## Decision

1. IT Operations has eleven capability domains, each `grouped_by` one plane (ADR 0010): `FND` Platform Foundation
   (Foundation); `SUB` Infrastructure Substrate (Resource); `AUT` Provisioning & Automation (Delivery); `DEL` Software
   Delivery (Delivery); `SEC` Security & Identity (Security); `OBS` Observability & Operations (Operations); `RES`
   Resilience & Continuity (Operations); `COST` Cost & Capacity (Operations); `DATA` Data & Analytics (Resource);
   `EXP` Consumer Experience (Experience); `GOV` Governance & Service Management (Governance).
2. A domain's id is its code; capability ids are `CAP-<CODE>-<n>`, children `CAP-<CODE>-<n>.<m>`. These codes are
   bare, the one exception to the prefixed form of every later service domain (ADR 0004).
3. Every domain carries `belongs_to_service_domain → SD-IT-OPERATIONS` (ADR 0009).
4. Personas are the three archetypes of ADR 0012: Platform Team, Platform Consumer and Security & Compliance.
5. IT Operations owns the platform; it interfaces with, and does not manage, end-user devices (ADR 0018), application
   logic (ADR 0021), the facility (ADR 0022), the enterprise network beyond its substrate (ADR 0023) and the enterprise
   security functions that set its guardrails (ADR 0024).
6. `GOV` holds the platform's self-analytics — usage, adoption, value and decision metrics — as a
   measurement-and-insight capability fed by `OBS` telemetry and `COST` financials, not as a domain.
7. `DATA` covers the platform's and IT's own data and analytics services and their governance; feeds to an enterprise
   data lake or business analytics are boundary integrations (ADR 0026).
8. A domain boundary changes only by a record superseding this one, never by editing a definition.

## Consequences

- Every capability traces to a domain, every domain to its plane and service domain.
- Eleven domains is broader than five planes, and neighbours overlap at their edges (provisioning against delivery;
  data governance across `DATA`, `SEC` and `GOV`) — accepted because each has its own lifecycle and owner.
- Bare and prefixed codes coexist; a reader must know the exception (ADR 0004).
- Later IT Operations terms are minted by their own records (ADR 0032, ADR 0033, ADR 0038, ADR 0039).

## Alternatives

- A developer platform's five planes as the domains — omits the substrate, resilience, cost, data and governance an
  infrastructure platform must cover.
- Data and analytics under substrate or experience — data services carry their own lifecycle and governance; a data
  platform offered as a paved road is first-class.

## Sources

- https://tag-app-delivery.cncf.io/whitepapers/platforms/ · a platform as a set of capability domains · accessed 2026-05-20
- https://platformengineering.org/blog/create-your-own-platform-engineering-reference-architectures · the five planes the eleven domains extend · accessed 2026-05-20
- https://developer.humanitec.com/training/master-your-internal-developer-platform/structure-and-integration-points/ · plane structure and integration points · accessed 2026-05-20

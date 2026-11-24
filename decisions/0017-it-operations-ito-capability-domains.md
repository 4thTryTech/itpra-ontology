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

1. IT Operations has eleven capability domains, each `grouped_by` one plane (ADR 0010): `ITO-FND` Platform Foundation
   (Foundation); `ITO-SUB` Infrastructure Substrate (Resource); `ITO-AUT` Provisioning & Automation (Delivery); `ITO-DEL` Software
   Delivery (Delivery); `ITO-SEC` Security & Identity (Security); `ITO-OBS` Observability & Operations (Operations); `ITO-RES`
   Resilience & Continuity (Operations); `ITO-COST` Cost & Capacity (Operations); `ITO-DATA` Data & Analytics (Resource);
   `ITO-EXP` Consumer Experience (Experience); `ITO-GOV` Governance & Service Management (Governance).
2. A domain's id is its code, `ITO-<GRP>`; capability ids are `CAP-ITO-<GRP>-<n>`, children `CAP-ITO-<GRP>-<n>.<m>`,
   the form of every service domain, per ADR 0004 (amended by ADR 0045).
3. Every domain carries `belongs_to_service_domain → SD-IT-OPERATIONS` (ADR 0009).
4. Personas are the three archetypes of ADR 0012: Platform Team, Platform Consumer and Security & Compliance.
5. IT Operations owns the infrastructure platform; end-user devices (ADR 0018), application logic (ADR 0021), the
   facility (ADR 0022), the enterprise network beyond its substrate (ADR 0023) and the enterprise security functions
   that set its guardrails (ADR 0024) belong to peer domains it does not manage (amended by ADR 0047).
6. `ITO-GOV` holds the platform's self-analytics — usage, adoption, value and decision metrics — as a
   measurement-and-insight capability fed by `ITO-OBS` telemetry and `ITO-COST` financials, not as a domain.
7. `ITO-DATA` covers the platform's and IT's own data and analytics services and their governance; feeds to an enterprise
   data lake or business analytics are boundary integrations (ADR 0026).
8. A domain boundary changes only by a record that amends this one, never by editing a definition (amended by
   ADR 0049).

## Consequences

- Every capability traces to a domain, every domain to its plane and service domain.
- Eleven domains is broader than five planes, and neighbours overlap at their edges (provisioning against delivery;
  data governance across `ITO-DATA`, `ITO-SEC` and `ITO-GOV`) — accepted because each has its own lifecycle and owner.
- Every IT Operations id carries `ITO`, so its terms read as one domain's among eleven, not as shared ones.
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

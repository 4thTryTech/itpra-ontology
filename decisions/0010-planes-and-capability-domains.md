# ADR 0010 — Planes and capability domains

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Capabilities need a grouping coarser than a capability and finer than a service domain, and every service
domain needs the same grouping so that its capability domains can be read side by side. The nearest industry
structure is the five-plane developer-platform model; an enterprise platform is wider.

## Decision

1. A capability is `grouped_by` exactly one capability domain (`DOMAIN`, `type: Domain`) and a capability
   domain by exactly one plane (`PLANE`, `type: Plane`): Capability → Domain → Plane.
2. There are seven planes: Experience (`PLANE-EXPERIENCE`), Delivery (`PLANE-DELIVERY`), Resource
   (`PLANE-RESOURCE`), Foundation (`PLANE-FOUNDATION`), Operations (`PLANE-OPERATIONS`), Security
   (`PLANE-SECURITY`) and Governance (`PLANE-GOVERNANCE`). Five correspond to the developer-platform planes,
   with monitoring broadened to operations.
3. Foundation and Governance are added because an enterprise platform is a superset of a developer platform:
   Foundation is the backbone every other plane reconciles against (source of truth, secrets, registry,
   policy, provenance); Governance is the management wrapper of neutral constructs, tenancy, service
   lifecycle, evidence and measurement.
4. The same seven planes group every service domain's capability domains; no service domain adds a plane.
5. Each capability domain carries one `grouped_by` edge and one `belongs_to_service_domain` edge (ADR 0009).
   Its id is its code, `<SD>-<GRP>` in every service domain (`ITO-OBS`, `EUC-DEV`), and the code is the domain
   segment of its capability ids, per ADR 0004 (amended by ADR 0045).
6. Security, Operations and Governance are planes in their own right, not a cross-cutting set; interaction
   between domains is expressed by `depends_on` edges between capabilities, never by the grouping. A
   capability domain's boundary changes only by a record, never by a silent edit.

## Consequences

- Any capability is located in three hops: its domain, its plane, its service domain.
- One plane per domain forces a choice where a domain spans concerns (data services sit in Resource though
  data governance touches Governance); the dependency edges carry the rest.
- A plane is a grouping only: it carries no ownership, maturity or operating-model meaning, which bind below
  the reference tier; in return a plane reads across all eleven service domains.

## Alternatives

- Five planes with security, operations and governance as cross-cutting concerns — hides three concerns that
  have capability domains of their own and leaves the backbone and the wrapper unplaced.
- A plane set per service domain — eleven incomparable groupings; the plane exists for comparison.
- Domains without planes — too many to read across eleven service domains unaided.

## Sources

- https://thenewstack.io/build-your-idp-at-light-speed-with-a-platform-reference-architecture/ · the five-plane developer-platform reference architecture · accessed 2026-05-22
- https://platformengineering.org/blog/create-your-own-platform-engineering-reference-architectures · planes as the structuring device; observability, security and data as first-class capabilities · accessed 2026-05-22
- https://www.facets.cloud/blog/ipe-gartner-2025 · infrastructure-platform engineering as a superset of the developer-platform scope · accessed 2026-05-22

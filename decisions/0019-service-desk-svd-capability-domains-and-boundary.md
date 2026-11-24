# ADR 0019 — Service Desk (SVD) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The Service Desk service domain (`SD-SERVICE-DESK`) is the single point of contact through which users report
disruptions and raise requests. Its vocabulary must say what the desk owns and what it only coordinates, and fit both
ways the industry organises resolution beyond the first line.

## Decision

1. The Service Desk has seven capability domains, each `grouped_by` Experience or Governance, per
   ADR 0010 (amended by ADR 0047): `SVD-CON` Contact & Intake Channels (Experience); `SVD-TRI` Triage,
   Classification & Routing (Governance); `SVD-KNW` Knowledge & Self-Service Enablement (Experience); `SVD-HDL`
   Front-line Incident & Request Handling (Governance); `SVD-MAJ` Major-Incident Coordination & Escalation
   (Governance); `SVD-COM` Customer Communication & Satisfaction (Experience); `SVD-PRF` Support Performance & Insight
   (Governance).
2. Ids carry the `SVD` code (`CAP-SVD-<GRP>-<n>`; ADR 0004); every domain carries
   `belongs_to_service_domain → SD-SERVICE-DESK`.
3. Personas are four coarse archetypes (ADR 0012): Service Desk Requester (consumer), Service Desk Agent (front-line
   provider), Service Desk Coordinator (orchestration and assurance) and Resolver Group Liaison (the adjacent provider
   the desk hands off to).
4. The desk owns the contact and its front-line handling — intake, triage, first-line resolve-or-coordinate,
   communication, closure — and coordinates but does not perform the deeper work: the resolving domains own fulfilment
   and the fix (ADR 0017, ADR 0018, ADR 0020, ADR 0021), IT Service Management & Integration the system of record and
   supplier integration (ADR 0025), the identity authority the directory (ADR 0024).
5. `SVD-MAJ` is its own domain, not a cluster inside `SVD-HDL`: a major disruption demands a coordination intensity
   and coordinator-led response ordinary handling does not; it wraps, never performs, the fix.
6. `SVD-COM` (the outward relationship with users) and `SVD-PRF` (the inward analysis of the desk) stay separate:
   different owners, different quality attributes.
7. `SVD-HDL` names only the outcomes common to tiered and swarming support — first-line resolution, handoff with
   context and retained ownership, one accountable owner (`CAP-SVD-HDL-1`, `-3`, `-4`); the agent persona stays coarse
   and the model is bound below the reference tier.

## Consequences

- Resolvers behind the hand-off can change without changing the front line; the vocabulary fits tiered, swarming and
  hybrid support.
- The single point of contact adds a hand-off; triage, routing and retained ownership offset the latency.
- The handover-delay versus coordination-overhead trade-off appears only once a model is bound.

## Alternatives

- Fold major-incident coordination into front-line handling — its coordination intensity and coordinator-led personas
  warrant a domain.
- Standardise on tiered escalation or on swarming — either excludes organisations running the other, and tier
  numbering collides with the reserved operations-support tiers (ADR 0001).

## Sources

- https://www.exin.com/article/what-is-siam-and-why-its-important/ · a single point of contact across many providers · accessed 2026-05-30
- https://advisera.com/20000academy/knowledgebase/service-desk-single-point-contact/ · owns the contact, not the fix · accessed 2026-05-30
- https://www.freshworks.com/explore-it/three-tier-support-vs-swarming/ · tiered and swarming support as competing models · accessed 2026-05-30

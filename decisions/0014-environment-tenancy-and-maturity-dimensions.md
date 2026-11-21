# ADR 0014 — Environment, tenancy and maturity dimensions

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

A reference-tier capability must hold across hosting models and workload forms, across tenants sharing one
platform and across organisations at different stages of maturity, while naming no runtime, no isolation
mechanism and no threshold. The three concerns need one method and a small controlled vocabulary each.

## Decision

1. One method serves all three: a small controlled `Concept` vocabulary with its allowed values in the
   definition, not in a field; the reference tier declares the variation point, a scenario narrows it, an
   implementation binds it.
2. Environment dimensions (`ENV-DIM-*`, `applies_to` the entity `ENVIRONMENT`): hosting model
   (`ENV-DIM-HOSTING`: public, private, hybrid) and workload form (`ENV-DIM-WORKLOAD`: container, VM,
   serverless). The outcome holds across every value; how it is realised is the variation point.
3. The tenant (entity `TENANT`) is the unit of isolation — a team, business unit, project or estate (a platform
   or application landscape governed as one) — and cannot read, alter, infer, reach or degrade another tenant
   beyond explicitly granted policy.
4. Five isolation dimensions (`TEN-DIM-*`, `applies_to` `TENANT`): data (`TEN-DIM-DATA`), network
   (`TEN-DIM-NETWORK`), compute/runtime (`TEN-DIM-RUNTIME`), identity and access (`TEN-DIM-IDENTITY`) and
   operational — quota, blast radius, noisy neighbour (`TEN-DIM-OPERATIONAL`).
5. Isolation strength (`TEN-ISOLATION-STRENGTH`) is a mechanism-free spectrum — shared, logical, dedicated — that
   may differ per dimension and per tenant; a variation point selected per scenario and realised below it.
6. Four ordered maturity stages (`MAT-STAGE-*`, `applies_to` `CAPABILITY`) — Initial (`MAT-STAGE-INITIAL`),
   Managed (`MAT-STAGE-MANAGED`), Scaled (`MAT-STAGE-SCALED`), Optimizing (`MAT-STAGE-OPTIMIZING`) — correspond
   in their definitions, not as aliases, to the CNCF platform maturity stages and to CMMI.
7. Maturity is assessed per capability through a few neutral, observable cues read against the ladder; cues are
   self-assessment, not obligations; rubric and thresholds bind below the reference tier.

## Consequences

- The sets are finite — two environment axes, five isolation dimensions, four stages; a new value or axis needs
  a record (ADR 0006).
- Naming the dimension, not the mechanism, tells a scenario what is isolated and how strongly without pre-empting
  its choice.
- Light cues are coarser than a full rubric; that precision is left to the scenario that needs it.

## Alternatives

- Free prose per capability — inconsistent, uncheckable, drifts into mechanism assumptions.
- A distribution-topology dimension (single or multi-region, edge) — no capability needed it.
- A strength spectrum without isolation dimensions — loses what is isolated.
- An isolation quality attribute — the boundary is a functional outcome with strength as its target.

## Sources

- https://tag-app-delivery.cncf.io/whitepapers/platform-eng-maturity-model/ · the four maturity stages · accessed 2026-05-20
- https://resources.sei.cmu.edu/asset_files/whitepaper/2001_019_001_29620.pdf · variation points and binding time · accessed 2026-05-20
- https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/the-bridge-model.html · silo, pool and bridge isolation models · accessed 2026-05-21
- https://learn.microsoft.com/en-us/azure/architecture/guide/multitenant/considerations/tenancy-models · isolation decided per architectural domain · accessed 2026-05-21

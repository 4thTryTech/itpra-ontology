# ADR 0016 — Quality attributes

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Non-functional requirements in consuming registries name the quality they constrain, so the vocabulary needs a
controlled set of quality attributes covering what industry and regulators name without turning any into an
obligation or growing by one name per nuance.

## Decision

1. A quality attribute (type `QualityAttribute`, id an `UPPER` token; ADR 0004) names a category of quality a
   requirement may constrain; a consuming registry's requirement id embeds it.
2. Eighteen attributes: `AVAILABILITY`, `RESILIENCE`, `SCALABILITY`, `PERFORMANCE`, `SECURITY`, `COMPLIANCE`
   (compliance and auditability), `OBSERVABILITY`, `OPERABILITY`, `MAINTAINABILITY`, `PORTABILITY`,
   `INTEROPERABILITY`, `COST_EFFICIENCY`, `USABILITY` (usability and developer experience), `RECOVERABILITY`,
   `SAFETY`, `EXPLAINABILITY` (explainability and transparency), `VALIDITY` (validity and output fitness) and
   `FAIRNESS` (fairness and bias management).
3. The first fourteen draw on the ISO/IEC 25010 product quality model and cloud well-architected frameworks;
   `SAFETY` follows the 2023 edition of ISO/IEC 25010, which added safety; `EXPLAINABILITY`, `VALIDITY` and
   `FAIRNESS` follow the NIST AI RMF trustworthiness characteristics and the ISO/IEC 25059 AI quality model.
4. Attributes are vocabulary, not obligations: whether an architecture carries a requirement against one is a
   scope decision below the reference tier. `FAIRNESS` binds where a system materially affects people;
   `VALIDITY` where fitness is a threshold over a scored sample rather than an assertion.
5. `EXPLAINABILITY` is distinct from `OBSERVABILITY`: the one accounts for a particular outcome to those
   accountable for or affected by it; the other determines system state from emitted telemetry.
6. Of the NIST characteristics, secure and resilient map to `SECURITY` and `RESILIENCE`; accountable maps to
   `GC-OWNERSHIP` (ADR 0015), not to an attribute.
7. Declined: `PRIVACY`, carried by `SECURITY`, `COMPLIANCE`, the data capabilities and `TEN-DIM-DATA`
   (ADR 0014); `DURABILITY`, because `RECOVERABILITY` and `RESILIENCE` are measured by the identical test
   (ADR 0039); an attribute for derived knowledge, which `VALIDITY`, `EXPLAINABILITY` and `INTEROPERABILITY`
   already express (ADR 0031).
8. An attribute is added only when an obligation cannot be written against the existing set.

## Consequences

- The vocabulary names what standards and regulators name, so an obligation is never unstatable for want of a
  word.
- `VALIDITY` is the most debatable: for deterministic behaviour correctness is functional; the attribute earns
  its place only where fitness is a degree.
- Some attributes stay unused in a given scenario.
- An attribute id change is MAJOR (ADR 0003), because consuming requirement ids embed it.

## Alternatives

- The ISO/IEC 25010 characteristics verbatim — a software product model lacking cost, observability, operability and recoverability.
- A `PRIVACY` attribute — arguable, but already carried by four terms.
- One attribute per NIST characteristic — accountability is a governance construct; security and resilience already exist.

## Sources

- https://www.iso.org/standard/78176.html · ISO/IEC 25010:2023 product quality model, second edition, safety added · accessed 2026-11-21
- https://www.nist.gov/itl/ai-risk-management-framework · the seven AI trustworthiness characteristics · accessed 2026-09-11

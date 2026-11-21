# ADR 0025 — IT Service Management & Integration (ITSM) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Service management shares its vocabulary with the governance constructs every domain uses and with the platform's
own `GOV` domain, which holds them for the platform. The IT Service Management & Integration domain
(`SD-SERVICE-MGMT`, ADR 0009) needs domains that coordinate across providers without restating any provider's
governance, named in no operating model's vocabulary.

## Decision

1. `SD-SERVICE-MGMT` has seven capability domains, all `grouped_by` the Governance plane: `ITSM-CAT` Service
   Catalog & Portfolio Coordination; `ITSM-REQ` Cross-Domain Request & Fulfillment Orchestration; `ITSM-CHG`
   Cross-Domain Change Coordination; `ITSM-INC` Cross-Domain Incident & Problem Coordination; `ITSM-SLM`
   Service-Level & Supplier/Provider Management; `ITSM-CFG` System-of-Record & Configuration Integration;
   `ITSM-VAL` Service Performance & Value Insight. Capability ids are `CAP-ITSM-<GRP>-<n>` (ADR 0004).
2. Each domain is bound to the constructs it coordinates (ADR 0015) — `ITSM-CAT`: `GC-CATALOG`, `GC-OWNERSHIP`,
   `GC-RECORD`; `ITSM-REQ`: `GC-REQUEST`, `GC-APPROVAL`, `GC-RECORD`; `ITSM-CHG`: `GC-CHANGE`, `GC-APPROVAL`,
   `GC-RECORD`; `ITSM-INC`: `GC-INCIDENT`, `GC-PROBLEM`, `GC-RECORD`; `ITSM-SLM`: `GC-SERVICE-LEVEL`,
   `GC-OWNERSHIP`, `GC-FEEDBACK`; `ITSM-CFG`: `GC-RECORD`; `ITSM-VAL`: `GC-SERVICE-LEVEL`, `GC-FEEDBACK`; none is
   minted.
3. Four personas (ADR 0012) add a coordinated-party archetype: Service Integrator, Service / Domain Provider,
   Service Owner & Portfolio, Service Consumer; the integrator's sourcing is decided below the reference tier, not
   a capability difference.
4. The domain owns the cross-provider coordination wrapper; each provider keeps its own constructs, record and
   response, so a construct appears twice — as a provider's own and as this domain's coordination of it:
   `ITSM-REQ` routes steps `CAP-GOV-1` fulfils for the platform; `ITSM-CHG` authorises change spanning providers,
   `CAP-GOV-2` the platform's own; `ITSM-INC` coordinates across boundaries, `CAP-GOV-3` within; `ITSM-CFG`
   federates authoritative sources, `CAP-GOV-4` among them, replacing none.
5. The user contact channel is `SD-SERVICE-DESK` (ADR 0019), not this domain.
6. Named service-management concepts are restated as outcomes: `ITSM-CFG` is federated system-of-record
   integration; `ITSM-SLM` is the commitment chain — what a consumer is given, the internal alignments supporting
   it, the supplier commitments underpinning it; `ITSM-VAL` is service value and experience measurement;
   `ITSM-REQ`, `ITSM-CHG` and `ITSM-INC` are cross-provider coordination of their constructs; the integrator is
   the Service Integrator persona.

## Consequences

- Every provider's governance maps into the wrapper without being replaced.
- The Governance plane carries all seven domains: dense, but the wrapper is governance by nature.
- The prose is more abstract than a reader used to one operating model expects; familiar process names appear
  only once an operating model is bound.

## Alternatives

- The named frameworks' vocabulary (ITIL, SIAM) — CMDB, SLA/OLA/UC, XLA, the incident, change and request
  processes and the retained organisation are what rule 6 restates; the names bind the reference tier to one model.
- Fold the wrapper into `GOV` — `GOV` governs one provider; this domain coordinates many.

## Sources

- https://www.scopism.com/what-is-service-integration-and-management-siam/ · integrator coordinates across providers; does not replace provider-internal processes · accessed 2026-05-30
- https://www.dmtf.org/standards/cmdbf · federation of configuration records across authoritative sources (ITSM-CFG) · accessed 2026-05-30

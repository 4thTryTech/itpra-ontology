# ADR 0020 — Onsite / Field Support (FLD) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The Onsite / Field Support service domain (`SD-FIELD-SUPPORT`) is the hands-on support needed where remote and
automated action ends. Its vocabulary must separate the hands and their coordination from the authorities that direct
and record the work.

## Decision

1. Field Support has seven capability domains, each `grouped_by` Operations or Resource, the planes its service domain
   interfaces with (ADR 0009, ADR 0010): `FLD-DISP` Dispatch & Scheduling (Operations); `FLD-DESK` Deskside / On-site
   Assistance (Operations); `FLD-IMAC` Install · Move · Add · Change (Resource); `FLD-FIX` Hardware Break-Fix & Depot
   Repair (Resource); `FLD-LOG` Spares, Stock & Logistics (Resource); `FLD-SAFE` On-site Safety, Access & Escort
   (Operations); `FLD-PERF` Field Performance & Insight (Operations).
2. Coordinated-service work sits in Operations and physical-estate work in Resource: an Operations-weighted placement,
   accepted as honest.
3. Ids carry the `FLD` code (`CAP-FLD-<GRP>-<n>`; ADR 0004); every domain carries
   `belongs_to_service_domain → SD-FIELD-SUPPORT`.
4. Personas are five coarse archetypes (ADR 0012): Field Technician (the hands), Field Operations Coordinator
   (dispatch), Field Support Lead (provider as product owner), Site & Safety Custodian (assurance) and Field Service
   Requestor (consumer); hands and coordination are separate concerns.
5. Field Support owns the hands at a location and the coordination, spares and safety around them; it performs and
   reports but does not own the change authority and asset record (ADR 0017, ADR 0018, ADR 0022), warranty
   entitlement, inventory finance, the site's access controls and safety policy (ADR 0022, ADR 0024) or the disposal
   standard. `FLD-PERF` observes the visit and the service commitment, not the platform (`OBS`) or the endpoint
   (`EUC-DEX`); site connectivity is Network & Connectivity's (ADR 0023).
6. Dispatch is a Field Support domain, not the desk's: the desk routes a request (ADR 0019); Field Support qualifies
   it, assigns by skill and credential and tracks the visit — the reciprocal of End-User Computing's hand-off of
   physical work (ADR 0018).

## Consequences

- The field reports into records it does not own, so a visit never creates a second source of truth.
- Four of seven domains in Operations reads as unbalanced; a plane of its own is excluded by ADR 0010.
- The desk-to-field seam is route versus execute; the endpoint-to-field seam is remote versus physical.

## Alternatives

- Dispatch inside the Service Desk — the desk is cross-domain contact and triage; dispatch is credential-gated
  field-execution coordination with its own owner.
- Field Support owns the asset record it updates — the record of truth and the authority to change belong to the
  asset-owning domains.

## Sources

- https://www.techtarget.com/searchdatacenter/definition/remote-hands · directed versus skilled hands under the asset owner's direction · accessed 2026-05-30
- https://blog.invgate.com/imacd · the install, move, add, change, dispose process; approval sits elsewhere · accessed 2026-05-30
- https://learn.microsoft.com/en-us/compliance/assurance/assurance-datacenter-physical-access-security · the site owns the access controls visiting staff operate within · accessed 2026-05-30

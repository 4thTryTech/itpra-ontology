# ADR 0022 — Data Center & Facilities (DCF) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The physical hosting environment shares words with the logical substrate provisioned on top of it, with the
enterprise network, with workload security, observability and resilience, and with deskside hardware support. The
Data Center & Facilities domain (`SD-DATACENTER`, ADR 0009) needs capability domains on the existing planes
(ADR 0010) and a boundary between what it owns and what it interfaces with.

## Decision

1. `SD-DATACENTER` has seven capability domains, each `grouped_by` an existing plane: `DCF-SPC` Facility Space &
   Capacity · Resource; `DCF-PWR` Power & Energy Distribution · Resource; `DCF-COOL` Cooling & Environmental
   Control · Resource; `DCF-CAB` Cabling & Physical Connectivity · Resource; `DCF-SEC` Physical Security & Access
   Control · Security; `DCF-MON` Facility Monitoring & Management · Operations; `DCF-RES` Facility Resilience &
   Continuity · Resource. Capability ids are `CAP-DCF-<GRP>-<n>` (ADR 0004).
2. Four personas (ADR 0012) follow the provider, consumer and assurance pattern and add a physical-security
   operations archetype: Facility Tenant, Facilities Engineering Team, Physical Security Officer, Facility
   Compliance & Assurance.
3. The domain owns the physical hosting environment — white space, electrical plant, cooling, passive cabling and
   cross-connects, physical access, facility monitoring and resilience — and `interfaces_with` adjacent domains
   rather than containing them.
4. The seams: the facility provides space, power, cooling and cabling on which the Infrastructure Substrate
   (`SUB`) provisions logical resources; `DCF-CAB` is the physical medium under the logical network
   (`SD-NETWORK`) and the platform's virtual networking; `DCF-SEC` controls physical access and supplies its
   evidence, owning neither logical identity (`SEC`) nor the control catalogue (`SD-SECURITY-GRC`); `DCF-MON`
   observes the plant, not the workloads on it (`OBS`); `DCF-RES` is facility availability that workload
   resilience (`RES`) consumes; `DCF-SPC` installs and decommissions equipment in the facility and hands deskside
   hardware to `SD-FIELD-SUPPORT`.

## Consequences

- The physical/logical seam with `SUB` is drawn once: the facility provides, the platform provisions, and neither
  restates the other.
- Five of seven domains sit on the Resource plane; the domain is physical and resource-heavy, and the planes are
  not extended for it.
- Power, cooling and resilience interrelate tightly but stay separate domains: more cross-references, clearer
  ownership and assurance.
- Redundancy topology, set-points, cabling grades and efficiency targets are decided below the reference tier.

## Alternatives

- Fold the facility into the Infrastructure Substrate (`SUB`) — the building, power and cooling have a different
  owner, lifecycle and consumer from the logical resources provisioned on them.
- One data-center operations domain — loses the separately staffed physical-security and monitoring concerns.

## Sources

- https://uptimeinstitute.com/tiers · facility availability tiers behind DCF-RES and DCF-PWR redundancy · accessed 2026-05-30
- https://www.cky.com.tw/en/insights/ashrae-tc9-datacenter-thermal-guidelines · recommended thermal envelope (DCF-COOL) · accessed 2026-05-30
- https://www.dataplugs.com/en/physical-security-layers-modern-data-centers/ · physical access as a layered, logged concern distinct from logical identity · accessed 2026-05-30

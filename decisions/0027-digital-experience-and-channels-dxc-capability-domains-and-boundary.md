# ADR 0027 — Digital Experience & Channels (DXC) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The customer-facing digital experience shares words with the platform's Consumer Experience (`ITO-EXP`), which serves
internal consumers, with Digital Experience Monitoring (`CAP-ITO-OBS-9`), with business analytics of customer data and
with the identity and privacy authorities. The Digital Experience & Channels domain (`SD-DIGITAL-EXPERIENCE`,
ADR 0009) needs capability domains on its two planes and a boundary that keeps its consumer the external customer.

## Decision

1. `SD-DIGITAL-EXPERIENCE` has seven capability domains: the consumer-facing surfaces on the Experience plane —
   `DXC-CNT` Content Management & Composition, `DXC-PER` Personalization & Targeting, `DXC-CDP` Customer Data &
   Profiles, `DXC-COM` Digital Commerce — and those that provision and ship the running experience on the Delivery
   plane — `DXC-JRN` Customer Journey Orchestration, `DXC-EXP` Experimentation & Optimization, `DXC-CHN` Channel
   Delivery & Experience Insight. Capability ids are `CAP-DXC-<GRP>-<n>` (ADR 0004).
2. `DXC-EXP` and `DXC-JRN` are domain codes; the platform domain `ITO-EXP` and journey prefix `JRN-` are other id
   families (ADR 0004).
3. `DXC-PER` and `DXC-CDP` stay separate: the consented data tier and the targeting that consumes it have different
   owners, and consent is a distinct mandate. Digital commerce is a reference-tier domain, not a retail
   specialisation.
4. Four personas (ADR 0012) add an author/operator archetype: Digital Customer, Digital Experience Engineering
   Team, Experience Practitioner, Experience Governance & Privacy; the consumer is the external customer, not a
   workforce member.
5. The domain owns the customer-facing experience — content, personalisation, journeys, profile and consent,
   experimentation, commerce, channel delivery with outcome insight — runs on the infrastructure platform, which
   does not own its experience logic, and meets each other service domain at a boundary between peers, containing
   none (amended by ADR 0047).
6. The seams: `CAP-DXC-CHN-5` is customer-outcome insight — engagement, conversion, friction — consuming, not
   duplicating, the technical monitoring of `CAP-ITO-OBS-9`; `DXC-CDP` consumes the identity of record and applies the
   privacy control catalogue (`SD-SECURITY-GRC`), owning neither; operational, real-time use of customer data is
   this domain, analytical use is `SD-BUSINESS-ANALYTICS` (ADR 0026); `DXC-CHN` serves external customers while
   `ITO-EXP` serves internal consumers and `ITO-SUB` hosts both.

## Consequences

- ADR 0009's monitoring-versus-outcome distinction reaches the capability set: `CAP-DXC-CHN-5` cannot be read as
  monitoring.
- Separating profile from personalisation costs a cross-domain dependency and buys a single owner for consent.
- Commerce widens the reference tier for organisations that sell nothing online; they leave the domain out when
  deriving.

## Alternatives

- Fold customer data into `SD-BUSINESS-ANALYTICS` — the operational profile and consent experience activate
  personalisation in real time; analytical use is the adjacent domain.
- Own Digital Experience Monitoring — page performance is `CAP-ITO-OBS-9`; this domain owns the customer-outcome view,
  a different subject.

## Sources

- https://cdp.com/basics/what-is-a-customer-data-platform-cdp/ · identity resolution, unified profile and consent as one tier (DXC-CDP) · accessed 2026-05-30
- https://cdp.com/glossary/identity-resolution/ · customer profile/identity resolution as the experience tier that consumes an identity of record · accessed 2026-05-30

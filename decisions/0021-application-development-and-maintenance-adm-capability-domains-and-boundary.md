# ADR 0021 — Application Development & Maintenance (ADM) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The Application Development & Maintenance service domain (`SD-APP-DEV`) builds and maintains the business applications
that run on the infrastructure platform. It shares the Delivery plane with IT Operations' Software Delivery domain,
so its vocabulary must draw the consumer-versus-provider line precisely.

## Decision

1. Application Development & Maintenance has seven capability domains, each `grouped_by` Delivery or Experience, per
   ADR 0010 (amended by ADR 0047): `ADM-APM` Application Portfolio & Lifecycle
   Management (Delivery); `ADM-ENG` Application Build & Engineering Practice (Delivery); `ADM-QAT` Application Quality
   & Testing (Delivery); `ADM-REL` Application Release Coordination (Delivery); `ADM-SUP` Application Support &
   Maintenance Modes (Experience); `ADM-DEX` Developer Enablement & Experience (Experience); `ADM-VAL` Application
   Performance & Value Insight (Experience).
2. Ids carry the `ADM` code (`CAP-ADM-<GRP>-<n>`; ADR 0004); every domain carries
   `belongs_to_service_domain → SD-APP-DEV`.
3. Personas are four coarse archetypes (ADR 0012): Application Engineering Team (provider), Application Business Owner
   (consumer), Application Support Specialist (assistance) and Application Quality & Assurance (assurance); ADR 0034
   adds two more.
4. The domain owns the application as a product and all its team does to build, assure, release, support and
   improve it; it consumes, not owns, the runtime (`ITO-SUB`), developer platform (`ITO-EXP`, `ITO-DEL`) and
   observability (`ITO-OBS`) of `SD-IT-OPERATIONS`, the contact channel (ADR 0019) and the control catalog (ADR 0024),
   and supplies application data and experiences to ADR 0026 and ADR 0027 (amended by ADR 0047).
5. `ADM-REL` is the application's and `ITO-DEL` the platform's: the team plans what ships and when, coordinates
   dependencies, gates readiness and rolls its application out; the pipeline that executes build and deploy, and the
   supply-chain controls, are the platform's.
6. `ADM-SUP` expresses maintenance as the four modes of ISO/IEC 14764 — corrective, adaptive, perfective, preventive —
   under the named-standard rule (ADR 0011), plus support triage and the support model; it owns application
   resolution.

## Consequences

- Application side and platform share the Delivery plane without an overlapping capability.
- `ADM-ENG` is the single reference-tier home for engineering practice: another domain's own engineering work is an
  instance of it derived below the reference tier, never a duplicated capability, so its definitions must stay general
  enough to instantiate beyond business applications.
- Consume-not-own runs both ways: the application side consumes the platform's pipeline; other domains consume its
  engineering practice.

## Alternatives

- Fold release coordination into the platform's `ITO-DEL` — consumer-side planning, readiness and rollout have a different
  owner from the pipeline that executes them.
- Widen `ADM-ENG` to any engineering by anyone — collapses the line that keeps the two from overlapping on the
  Delivery plane.

## Sources

- https://cdn.standards.iteh.ai/samples/80710/9a26fc3a1a464fa286fb85d6c1eeed31/ISO-IEC-IEEE-14764-2022.pdf · the four maintenance modes · accessed 2026-05-30
- https://martinfowler.com/bliki/TeamTopologies.html · a platform team provides, stream-aligned teams consume · accessed 2026-05-30
- https://www.apwide.com/release-management-kpis/ · release coordination on the application side; deployment in the pipeline · accessed 2026-05-30

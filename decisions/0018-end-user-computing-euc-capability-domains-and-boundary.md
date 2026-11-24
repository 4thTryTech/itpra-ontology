# ADR 0018 — End-User Computing (EUC) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The End-User Computing service domain (`SD-END-USER`) is the workforce computing experience:
endpoints, workspaces and the tooling people use. Its vocabulary overlaps with the infrastructure platform's security,
observability and substrate, the enterprise identity authority and the service desk, so each domain needs a stated boundary.

## Decision

1. End-User Computing has eight capability domains, each `grouped_by` an existing plane (ADR 0010): `EUC-DEV` Device
   Lifecycle & Provisioning (Resource); `EUC-WSP` Workspace & Productivity Services (Experience); `EUC-SEC` Endpoint
   Security & Compliance Posture (Security); `EUC-IAM` Workforce Identity & Access (Security); `EUC-MOB` Mobility &
   BYOD (Resource); `EUC-VRW` Virtual & Remote Workspace (Delivery); `EUC-SUP` End-User Support Experience &
   Self-Service (Experience); `EUC-DEX` Endpoint Observability & Digital Employee Experience (Operations).
2. Ids carry the `EUC` code (`CAP-EUC-<GRP>-<n>`, `FUNC-euc-<slug>`; ADR 0004); every domain carries
   `belongs_to_service_domain → SD-END-USER` (ADR 0009).
3. Personas are four coarse archetypes (ADR 0012): Workforce User (consumer), Workplace Engineering Team (provider),
   End-User Support Agent (assistance, first-class here) and Workplace Security & Compliance (assurance).
4. End-User Computing owns the person-facing computing experience: the device in the user's hands, the workspace, the
   sign-in and posture-conditioned access experience, personal devices, virtual-workspace delivery, workplace
   resolution and the observation of the user's device and experience.
5. It consumes, it does not own: `EUC-SEC` applies enterprise policy to endpoints and supplies compliance evidence,
   distinct from platform security (`ITO-SEC`, ADR 0017) and the control catalog (ADR 0024); `EUC-IAM` consumes the
   identity of record, owning neither directory nor workload identity; `EUC-VRW` delivers the workspace the substrate
   (`ITO-SUB`) runs; `EUC-SUP` resolves what the desk routes (ADR 0019); `EUC-DEX` observes the endpoint, not the platform
   (`ITO-OBS`). Physical work hands to Field Support (ADR 0020), endpoint connectivity to Network & Connectivity (ADR 0023).
6. `EUC-SEC` and `EUC-IAM` stay separate although both sit in the Security plane: posture is an assurance concern,
   access an experience concern, with different owners.

## Consequences

- No End-User Computing capability duplicates a platform, identity or desk capability; the adjacent domains state the
  reciprocal view (ADR 0019, ADR 0020, ADR 0024).
- Splitting posture from access leaves two closely related Security-plane domains; accepted for ownership clarity.
- The workplace spans five planes and has none of its own (ADR 0010).

## Alternatives

- Fold endpoint posture into the platform's `ITO-SEC` — the device in the user's hands has its own owner, lifecycle and
  consumer.
- One endpoint-management domain for lifecycle, posture and observability — loses the posture and experience concerns
  that are first-class today.

## Sources

- https://www.omnissa.com/glossary/unified-endpoint-management/ · the endpoint lifecycle set behind `EUC-DEV` · accessed 2026-05-30
- https://learn.microsoft.com/en-us/security/zero-trust/deploy/identity · identity of record is enterprise-wide; posture-conditioned access behind `EUC-IAM` · accessed 2026-05-30
- https://www.forrester.com/blogs/clarifying-the-digital-workplace-dex-and-the-rise-of-dexops/ · the user's endpoint as a subject distinct from platform observability · accessed 2026-05-30

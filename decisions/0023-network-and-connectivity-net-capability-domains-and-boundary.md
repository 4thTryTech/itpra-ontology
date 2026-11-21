# ADR 0023 — Network & Connectivity (NET) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The enterprise network shares words with the platform's in-fabric networking, with workload security and
observability, and with the enterprise identity and control authorities. The Network & Connectivity domain
(`SD-NETWORK`, ADR 0009) needs capability domains on the existing planes (ADR 0010) and a boundary that keeps it
beyond the substrate, consuming what the authorities hold.

## Decision

1. `SD-NETWORK` has seven capability domains, each `grouped_by` an existing plane: `NET-CON` Connectivity
   Provisioning & WAN · Resource; `NET-SEG` Network Security & Segmentation · Security; `NET-RAX` Remote & Secure
   Access · Security; `NET-DDI` Naming, Addressing & DNS (DDI) · Resource; `NET-QOS` Network Performance & Quality
   of Service · Operations; `NET-OBS` Network Observability & Assurance · Operations; `NET-RES` Network Resilience
   & Continuity · Resource. Capability ids are `CAP-NET-<GRP>-<n>` (ADR 0004).
2. `NET-SEG` and `NET-RAX` stay separate although both sit on the Security plane: the posture enforced on the path
   and the access path have different owners.
3. Five personas (ADR 0012) add operate and planning archetypes: Network Consumer, Network Engineering Team,
   Network Operations, Network Security & Compliance, Network Architect & Planner.
4. The domain owns the enterprise network beyond the platform's own substrate networking — in-fabric networking,
   addressing and service discovery are the Infrastructure Substrate (`SUB`) — and `interfaces_with` adjacent
   domains rather than containing them.
5. The seams: `NET-SEG` applies the control catalogue and threat intelligence of `SD-SECURITY-GRC` on the network
   path and supplies evidence, authoring neither; `NET-RAX` consumes identity of record (`SD-SECURITY-GRC`),
   device posture (`SD-END-USER`) and workload identity (`SEC`), providing the path, not the directory or device;
   `NET-OBS` observes the network path, not the platform (`OBS`) or the end user (`SD-END-USER`); `NET-RES` is
   path resilience, distinct from `DCF-RES` and `RES`.
6. The Service Desk (`SD-SERVICE-DESK`, ADR 0019) is the contact channel that routes a connectivity issue; Network
   Operations resolves it.

## Consequences

- The enterprise-versus-substrate line is drawn once; no capability has to say which side of the fabric it is on.
- Two Security-plane and two Operations-plane domains cost some disambiguation and buy clear ownership of posture
  versus path and performance versus assurance.
- `NET-OBS`, `NET-RES` and `NET-SEG` parallel the platform's `OBS`, `RES` and `SEC`; the subject, the enterprise
  network path, tells them apart.

## Alternatives

- Fold network-edge security into `SEC` or `SD-SECURITY-GRC` — enforcement on the path has a distinct owner and
  lifecycle from host security and from authoring the catalogue.
- One network domain owning in-fabric networking too — in-fabric networking is coupled to the substrate and
  belongs with it.

## Sources

- https://www.microsoft.com/en-us/security/business/security-101/what-is-zero-trust-network-access-ztna · zero-trust network access as the direction of remote access (NET-RAX) · accessed 2026-05-30
- https://www.cloudflare.com/learning/access-management/security-service-edge-sse/ · policy applied on the network path, separate from authoring the control catalog · accessed 2026-05-30

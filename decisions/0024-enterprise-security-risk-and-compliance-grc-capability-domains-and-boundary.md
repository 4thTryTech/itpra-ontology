# ADR 0024 — Enterprise Security, Risk & Compliance (GRC) — capability domains and boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Enterprise security, risk and compliance shares words with the platform's security, foundation, governance and
observability capabilities and with the workforce identity and endpoint posture of `SD-END-USER`. The Enterprise
Security, Risk & Compliance domain (`SD-SECURITY-GRC`, ADR 0009) needs capability domains on its two planes and a
boundary that keeps it an authority over estates, not a copy of their controls.

## Decision

1. `SD-SECURITY-GRC` has seven capability domains, each `grouped_by` the Security or Governance plane: `GRC-SOC`
   Security Operations & Threat Response · Security; `GRC-IAM` Corporate Identity & Access Authority · Security;
   `GRC-RISK` Enterprise Vulnerability, Threat & Risk Management · Governance; `GRC-CMP` Compliance, Audit &
   Evidence · Governance; `GRC-POL` Policy, Standards & Control Governance · Governance; `GRC-AWR` Security
   Awareness & Human Risk Assurance · Security; `GRC-INS` Security & Risk Posture Insight · Governance. Capability
   ids are `CAP-GRC-<GRP>-<n>` (ADR 0004).
2. Four personas (ADR 0012): Security & Risk Leadership; Security Operations & Response; Risk, Compliance & Audit;
   Identity & Access Governance.
3. The domain is the enterprise authority; a platform is one governed estate: the authority authors the guardrails
   and owns the enterprise registers; estates implement, enforce, scan, detect and supply evidence. The estate — a
   platform, an application landscape or a business unit — is the tenant unit (ADR 0014).
4. The seams: `GRC-SOC` correlates what estates feed up and coordinates enterprise response; estate detection and
   response stay with `CAP-ITO-SEC-6`, `CAP-ITO-SEC-7`, `CAP-ITO-SEC-8`. `GRC-IAM` owns the identity of record and entitlement
   governance that `ITO-SEC` and `EUC-IAM` consume; it does not own workload identity (`CAP-ITO-SEC-1`, `CAP-ITO-SEC-2`,
   `CAP-ITO-SEC-3`) or the sign-in experience. `GRC-RISK` owns the register and risk acceptance, consuming findings
   from `CAP-ITO-SEC-4` and `CAP-ITO-SEC-7`. `GRC-CMP` attests evidence `ITO-GOV` produces. `GRC-POL` authors what `ITO-FND` and
   `ITO-SEC` enforce. `GRC-AWR` has no platform counterpart. `GRC-INS` reports enterprise posture, not platform health
   (`ITO-GOV`, `ITO-OBS`).
5. Further seams are boundaries between peers: endpoint evidence from `SD-END-USER`, the contact channel of
   `SD-SERVICE-DESK`, cross-provider coordination by `SD-SERVICE-MGMT` (amended by ADR 0047).

## Consequences

- No platform control is restated at the enterprise tier; each is found once, with its owner.
- The authority depends on estates for every signal, finding and item of evidence; what an estate withholds, the
  enterprise cannot see.
- The workload-identity clause lets ADR 0035 refuse a second identity register for delegated actors.

## Alternatives

- Restate the platform's controls under the enterprise domain — duplicates `ITO-SEC` and `ITO-GOV` and breaks single
  ownership; the authority governs, estates implement.
- Place identity governance in `ITO-SEC` — the identity of record and entitlement governance are enterprise
  authorities the platform consumes.

## Sources

- https://www.nist.gov/blogs/taking-measure/identify-protect-detect-respond-and-recover-nist-cybersecurity-framework · CSF 2.0 functions incl. Govern behind GRC-SOC/GRC-POL · accessed 2026-05-30
- https://www.paloaltonetworks.com/cyberpedia/what-is-identity-governance-and-administration-iga · identity governance, lifecycle and certification (GRC-IAM) · accessed 2026-05-30

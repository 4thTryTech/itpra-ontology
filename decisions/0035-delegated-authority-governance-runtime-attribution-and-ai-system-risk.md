# ADR 0035 — Delegated authority — governance, runtime attribution and AI-system risk

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

A delegated actor (ADR 0030) acts under authority delegated by an accountable persona it never holds. That needs an
actor identity, a governed delegation, a standing record, runtime attribution and a classification of AI
obligations. GRC does not own workload identity (ADR 0024).

## Decision

1. No new capability: every candidate resolves to an existing term.
2. A delegated actor's identity is workload identity, owned by the platform (`CAP-ITO-SEC-1`, `CAP-ITO-SEC-3`);
   `CAP-GRC-IAM-1` stays the register of people, to which every delegation binds an accountable person.
3. Delegated authority, a bounded, revocable subset of a person's authority passed to a non-person, is governed by
   `CAP-GRC-IAM-2` on the least-privilege basis of a direct grant through
   `FUNC-grc-delegated-authority-governance` (`supports` `CAP-GRC-IAM-2`, `CAP-GRC-IAM-5`), which keeps the standing
   record: `GC-OWNERSHIP` and `GC-RECORD` applied to a new subject (ADR 0015).
4. `FUNC-grc-delegated-authority-recertification` (`supports` `CAP-GRC-IAM-4`) is its own function: a
   non-human principal never leaves, so no leaver event catches it.
5. GRC governs whether a delegation may exist and keeps the standing record; the platform establishes and presents
   the chain at runtime and decides against it. `FUNC-ito-delegated-authority-chain` (`supports` `CAP-ITO-SEC-2`,
   `applies_to` `AUTON-ACTOR`) carries the chain from the accountable person, via any intermediating
   application, to the executing principal; `CAP-ITO-SEC-2` attributes an action to an accountable person, never only
   to the executing principal, and `CAP-GRC-IAM-5` governs the ceiling of a runtime-chosen action (ADR 0033).
6. The chain is a named pattern with no protocol in id, term or definition: the candidate mechanism, an individual
   draft with competing siblings, fails ADR 0011's maturity criterion.
7. `FUNC-grc-ai-system-risk-classification` (`supports` `CAP-GRC-RISK-1`, `CAP-GRC-CMP-1`) classifies an AI
   system by risk to determine its obligations, named once because two regimes converge on it as the entry point.
   AI obligations map onto the unified control framework (`CAP-GRC-CMP-1`); `CAP-GRC-CMP-5` re-verifies a cited
   date at use; no tier label, threshold, regime name or date enters any term.

## Consequences

- The actor's attributability claim is met, not asserted: identified by the platform, made accountable by
  governance, attributed at runtime.
- A chain is only as strong as its weakest hop; how hops are bound, propagation and depth are decided below the
  reference tier.
- No date or tier entered a term, so nothing decays when a timeline moves.

## Alternatives

- A non-human identity governance capability — collides with ADR 0024 and duplicates `CAP-ITO-SEC-1`, `CAP-ITO-SEC-3`.
- Register non-human principals in `CAP-GRC-IAM-1` — "who exists" would then mean two things.
- A dedicated AI compliance capability — the overlap with existing obligations is what `CAP-GRC-CMP-1` absorbs.

## Sources

- https://labs.cloudsecurityalliance.org/research/csa-whitepaper-nonhuman-identity-agentic-ai-governance-v1-cs/ · non-human principals lack lifecycle governance · accessed 2026-09-11
- https://datatracker.ietf.org/doc/html/draft-oauth-ai-agents-on-behalf-of-user-02 · the on-behalf-of chain pattern; an individual draft · accessed 2026-09-11
- https://artificialintelligenceact.eu/implementation-timeline/ · classification as the entry point; dates moved · accessed 2026-09-11
- https://www.nist.gov/itl/ai-risk-management-framework · a second regime converging on classification · accessed 2026-09-11

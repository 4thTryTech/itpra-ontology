# ADR 0030 — Delegated actor, agent harness and in-flight control

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The automation boundary (ADR 0028) promises attributable autonomous activity, yet nothing names the non-human
actor, where it runs, or what its owner can do meanwhile. A persona is a human accountable role archetype
(ADR 0012), so the actor cannot be one.

## Decision

1. `AUTON-ACTOR` "Delegated actor" is a Concept, never a Persona: a non-human actor acting under authority
   delegated by an accountable persona, which it never holds — a distinct, identified principal with bounded,
   revocable authority, its actions recorded against itself and the persona, governed by the boundary including
   actions it selects at runtime. Edges: `depends_on` `GC-OWNERSHIP`, `FUNC-ito-privileged-access-management`.
2. Named for the accountability relationship, not the technology; agentic actor, digital worker, AI agent,
   software agent and non-human actor are aliases.
3. `consumed_by` stays human: an actor's use counts as the accountable persona's.
4. `AUTON-HARNESS` "Agent harness" is a Concept: the governed runtime that hosts a delegated actor's loop,
   mediates every tool and system it may reach, enforces the boundary on each selected action, bounds the budget
   of active execution and records the action trace. The budget bounds work in progress, not elapsed time: a
   suspended run consumes none, its suspension governed by the validity of its permission (ADR 0039). Edges:
   `applies_to` `AUTON-ACTOR`; `depends_on` `AUTON-BOUNDARY`, `FUNC-ito-policy-evaluation`, `FUNC-ito-audit-logging`.
5. `AUTON-INFLIGHT-CONTROL` "In-flight action control" is a Concept, not a Function: observing a delegated
   actor's execution while it runs and intervening (pause, resume, redirect, terminate); an unresumable pause is
   a terminate (ADR 0039). The intervention point is the harness, reachable by the accountable persona. Edges:
   `applies_to` `AUTON-ACTOR`; `depends_on` `AUTON-HARNESS`, `GC-OWNERSHIP`.
6. The four autonomy concepts form a closed set; construction, loop shape and intervention mechanism are
   scenario decisions. Plan approval is within `GC-APPROVAL` (ADR 0015); realizing functions land with the
   execution capabilities (ADR 0033).

## Consequences

- Every autonomous action terminates at a human accountable party; the boundary's attributability clause has a
  principal.
- Trade-off: "harness" is young vocabulary, kept because it names the container, not the loop; a word shift
  changes the term, not the id.
- In-flight control asserts an obligation ahead of settled practice.

## Alternatives

- A fourth persona — makes the actor a peer stakeholder with accountability it never has.
- Widening `consumed_by` — one verb, two claims: accountability and use.
- Folding in-flight control into the boundary — a decision before is not a capability during.
- An agentic analysis-surface capability — the actor invoking tools over an existing capability's data.

## Sources

- https://labs.cloudsecurityalliance.org/research/csa-whitepaper-nonhuman-identity-agentic-ai-governance-v1-cs/ · non-human identities as bounded principals attributable to an owner · accessed 2026-09-11
- https://en.wikipedia.org/wiki/Agent_harness · "harness" as multi-vendor vocabulary for the runtime around the loop · accessed 2026-09-11
- https://galileo.ai/blog/human-in-the-loop-agent-oversight · oversight of a running agent as a stated, unsolved need · accessed 2026-09-11

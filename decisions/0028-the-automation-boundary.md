# ADR 0028 — The automation boundary

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

A platform that runs remediation, runbooks, autonomous response or a delegated actor must say which actions may
proceed unattended and which pass a decision point first. The enforcing behaviours exist as functions and the
approval moment as a governance construct (ADR 0015); nothing names the partition.

## Decision

1. `AUTON-BOUNDARY` "Automation boundary" is a Concept with no service domain: the governed partition of
   operational actions into those that may be executed autonomously — unattended, by automation or by a
   delegated actor — and those that must pass an approval / decision point first.
2. It covers actions enumerated in advance and actions selected at runtime by the executing actor; a proposed
   plan is governed through the actions it would take.
3. It is a versioned, reviewable artifact with an accountable owner, changed through a change point; actions
   under it are recorded, keeping autonomous activity attributable, countable and auditable.
4. The partition is over an action and the part of the estate it lands in: permission presumes the controls
   that make the action attributable, recorded and interruptible are provided there, so where their coverage is
   partitioned (`COVERAGE-AREA`, ADR 0029) the boundary is evaluated per area.
5. T1 asserts only that the partition exists, is owned and is enforced; granularity (risk tiers, blast-radius
   classes, identity ceilings) and the areas are scenario decisions.
6. One concept, neither a governance moment nor a function, defines the partition: its sides are named in the
   definition, not as terms or edges. ADR 0029 and ADR 0031 reuse this shape.
7. Edges: `depends_on` `GC-APPROVAL`, `FUNC-policy-authoring`, `FUNC-policy-evaluation`; `applies_to`
   `COVERAGE-AREA`; `governs` `AUTON-ACTOR` (ADR 0030), `FUNC-runbook-automation`,
   `FUNC-event-triggered-execution`, `FUNC-response-playbook-execution`, `FUNC-tool-invocation-mediation`,
   `FUNC-agent-execution-sandboxing` (ADR 0033). Aliases: autonomous-action authorization, autonomy boundary.

## Consequences

- Derived architectures root automation governance in one anchor instead of recomposing it.
- The term stays coarse (one fact, no tiers), so the vocabulary cannot say how much autonomy is allowed.
- Reachability-driven areas fail closed; responsibility- and regulatory-driven areas are reachable and fail open,
  hence evaluation per area.
- Per-area evaluation is an obligation derived architectures inherit, not a check the vocabulary performs; every
  `governs` edge widens it.

## Alternatives

- A governance construct — the constructs are coarse moments; the boundary is the standing artifact they act on.
- A boundary-management function — authoring, evaluating, routing and enforcing exist as functions; the gap was
  the noun.
- A conduit or area-crossing concept — the industrial conduit is a network construct; coverage areas are also
  contractual and regulatory.

## Sources

- https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-action-approve.html · an approval step inside an otherwise unattended runbook · accessed 2026-06-11
- https://sre.google/resources/practices-and-processes/ai-engineering-reliable-operations/ · autonomous remediation bounded by limits, interruptibility and review gates · accessed 2026-06-11
- https://www.mdpi.com/2624-800X/6/2/52 · zones and conduits, the precedent not copied · accessed 2026-06-21

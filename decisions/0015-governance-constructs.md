# ADR 0015 — Governance constructs

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Capabilities and journeys refer to the moments at which a platform is asked, decided, changed, restored,
recorded and improved, which every operating model formalises in its own vocabulary. The reference tier needs
one neutral, coarse, complete set to name them.

## Decision

1. A governance construct (`GC-<slug>`, type `Concept`) names a governance moment, not a process or practice;
   the set is the join key between the reference tier and any operating model.
2. Ten constructs in five moment groups, the group stated in each definition: Engage — request (`GC-REQUEST`),
   catalog/offer (`GC-CATALOG`); Decide & Control — approval/decision (`GC-APPROVAL`), change including release
   and deployment (`GC-CHANGE`); Operate & Restore — incident/restore (`GC-INCIDENT`), problem/root-cause
   (`GC-PROBLEM`), service-level/commitment (`GC-SERVICE-LEVEL`); Record & Improve — system-of-record update
   (`GC-RECORD`), feedback/improvement (`GC-FEEDBACK`); cross-cutting — ownership (`GC-OWNERSHIP`).
3. A construct exists if and only if it is a distinct governance moment that a capability or journey references
   and operating models formalise differently enough to need a neutral anchor; the set changes only by a record
   (ADR 0006).
4. A definition names no operating-model or tool vocabulary; a cross-walk to one model's practices exists
   downstream and is not vocabulary.
5. An event or alert is a signal triggering an incident or service-level response, not a governance moment.
6. `GC-APPROVAL` claims any control gate, human-judged or automated, and so reaches a proposed plan — an action
   set differing from one action only in granularity, a scenario decision; no plan-approval sibling exists.
7. `GC-APPROVAL` fixes the moment a gate is satisfied, not how long that holds; approval validity binds below
   the reference tier, carried where needed by a requirement, never by a clause on the construct.
8. A concept that needs an accountable owner `depends_on` `GC-OWNERSHIP` (ADR 0030).

## Consequences

- Coarseness is the point: a small scenario may merge problem into incident when it binds its model.
- Approval validity is a known mismatch carried outside the construct; the join key stays stable at the price
  of precision.
- Ownership is cross-cutting because every other construct has an owner; it makes accountability for autonomous
  action expressible.

## Alternatives

- The first seven as a closed set — leaves commitments, improvement loops and root-cause work without an anchor.
- The five most used (request, approval, change, incident, record) — discards the catalogue and the accountability model.
- A construct per practice of one model, such as the ITIL practice list — binds the reference tier to that model.

## Sources

- https://itsm.tools/34-itil-4-management-practices/ · the practice set of one operating model · accessed 2026-05-21
- https://sre.google/workbook/error-budget-policy/ · service level and error budget as a decision moment · accessed 2026-05-21
- https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html · an approval record carrying an expiry — the validity question left to requirements · accessed 2026-09-15

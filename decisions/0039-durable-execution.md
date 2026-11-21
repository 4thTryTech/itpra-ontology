# ADR 0039 — Durable execution

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Engines that record each completed step of a run outside its process, so a lost process resumes after the last
recorded step, are a converged market category; the terms describing their patterns are silent on the loss of the
coordinator and the cost of the run's record.

## Decision

1. No capability, attribute or verb for the category, a product shape with no single owner; `RECOVERABILITY` and
   `RESILIENCE` already measure what `DURABILITY` would (ADR 0016).
2. The market phrase is an alias at most (ADR 0007): a behaviour older than its name is defined by the behaviour and
   found by the name.
3. `CAP-AUT-9` Resumable Execution Service: a managed service recording each completed step of a consumer run
   outside its process, so the run resumes after the last; the consumer connects its own workers
   and the service never executes their code — unlike the platform's own automation (`CAP-AUT-5`, `CAP-AUT-6`) and
   runtime-chosen action sets (`CAP-AUT-8`, ADR 0033). Agent-run durability is the same on both sides: the model
   call is journaled, not re-invoked on replay.
4. `FUNC-execution-version-compatibility`: when a definition or its code changes, every open execution continues on a
   version able to complete it or is drained, migrated or terminated; none is retired silently. A standing duty,
   hence a function; supports `CAP-DEL-4`, `CAP-AUT-5`, `CAP-AUT-6`, `CAP-AUT-9`.
5. Terms that stop being silent: `FUNC-workflow-orchestration` (coordination state outlives its process),
   `FUNC-job-scheduling` and `FUNC-event-triggered-execution` (an in-run timer; an event resumes a waiting run),
   `FUNC-job-execution-tracking` (a step record sufficient to resume), `FUNC-erasure-propagation` (execution records
   are not re-derivable; qualifies ADR 0038), `CAP-DEL-4` (constrained by open runs).
6. `AUTON-INFLIGHT-CONTROL` names resume — a pause that cannot be resumed is a terminate — and the `AUTON-HARNESS`
   budget bounds active execution only, so a long wait is not a budget breach; a suspended run is governed by its
   permission's validity (wording in ADR 0030).
7. `GC-APPROVAL` is not amended for approval validity (ADR 0015): no engine re-validates a stale answer and a
   validity window is a mechanism; the obligation is a consumer requirement.

## Consequences

- Sharper, longer definitions plus one capability and one function absorb the category; an in-memory coordinator
  no longer satisfies `FUNC-workflow-orchestration`.
- Recovery and reversal are part of designing a multi-step sequence (`CAP-ADM-ENG-1`, ADR 0021): a resumable runtime
  does not discharge once-only obligations at an outbound boundary (`CAP-ADM-ENG-3`), and a runtime-chosen call site
  makes bounding duplicate effects guardrail work (`CAP-ADM-ENG-7`, ADR 0034).
- `GC-APPROVAL` still fixes a moment where the behaviour needs a window.

## Alternatives

- A compensation function — the cleanest test, but no engine provides it.
- A service type within `CAP-DATA-1` — that precedent places store types.

## Sources

- https://learn.microsoft.com/azure/durable-task/common/what-is-durable-task · a young, vendor-divergent phrase · accessed 2026-09-15
- https://docs.temporal.io/develop/go/workflows/versioning · old paths retire after open runs finish · accessed 2026-09-15
- https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html · an approval record carries an expiry · accessed 2026-09-15

# ADR 0040 — Agentic execution explainability

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

`EXPLAINABILITY` (ADR 0016) accounts for a particular decision or output to those accountable and affected;
`OBSERVABILITY` determines system state from telemetry. Engineering a behaviour, scoring its paths offline and tracing
a request for latency each stop one step short of the account of this execution. Which capability owns that
account?

## Decision

1. `CAP-ADM-VAL-5` Agentic Execution Explainability accounts for a particular execution of a model-grounded or
   autonomous application component — inputs, context and instructions in force, model binding, decision and
   tool-use steps with results, output — captured at run time and rendered intelligibly to the accountable and the
   affected.
2. It sits in `ADM-VAL` (ADR 0021), which observes the application for the owning team, where accountability sits;
   not `ADM-ENG`, since engineering a behaviour is not accounting for its runs; not platform observability, since
   `ITO-OBS` determines system state and `CAP-ITO-AUT-8` records actions for the platform's attributability (ADR 0033); the account
   consumes both.
3. Each function is separated from a neighbour: `FUNC-adm-execution-decision-trace-capture` captures the per-execution
   trace tree of steps and results, where `FUNC-adm-distributed-tracing` locates latency;
   `FUNC-adm-execution-account-rendering` renders an account a non-engineer can follow — rendering explains,
   `FUNC-adm-trajectory-scoring` grades (ADR 0034); `FUNC-adm-execution-record-retention` keeps records only as long
   as obligation requires and minimises them: a derived record inherits its sources' access and erasure
   obligations (`KNOWLEDGE-ROLE`, ADR 0031).
4. `CAP-ADM-VAL-5` `depends_on` `CAP-ADM-ENG-7` (ADR 0034): the bounds an execution was held to are part of its
   account. `JRN-adm-build-model-grounded-behaviour` `depends_on` `CAP-ADM-VAL-5`: every released execution is
   recorded, rendered on request and retained only as obligation requires.
5. No new persona, attribute, verb or construct: the readers are `PERSONA-adm-app-team`, `PERSONA-adm-ai-assurance`
   and `PERSONA-adm-app-support`; the account is a record, its release an approval, a questioned execution an
   incident (ADR 0015).

## Consequences

- The attribute has a home matching its definition: why an agentic component did what it did is
  answerable.
- Retention and redaction is a function of its own, so the account cannot become the estate's largest store of
  prompts and personal data.
- The value-insight domain is no longer purely aggregate; content capture is where the difficulty lives, and the
  reference tier names only the obligation.

## Alternatives

- Explainability on the engineering capabilities — the artefacts an explanation cites live there, not the account.
- Extending `CAP-ADM-VAL-1` — aggregate and performance-shaped; one execution's account would double its purpose.
- Placing it on the platform — it records for attributability; the application owner accounts for the
  output.

## Sources

- https://airc.nist.gov/airmf-resources/airmf/3-sec-characteristics/ · accounting for a specific outcome to the accountable, distinct from monitoring · accessed 2026-09-24
- https://artificialintelligenceact.eu/article/13/ · the duty to interpret and account sits with the deploying party · accessed 2026-09-24
- https://air-governance-framework.finos.org/mitigations/mi-21_agent-decision-audit-and-explainability.html · a decision audit rendered to the accountable, distinct from tracing · accessed 2026-09-24

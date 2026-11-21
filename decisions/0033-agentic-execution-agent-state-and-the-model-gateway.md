# ADR 0033 — Agentic execution, agent state and the model gateway

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

ADR 0030 names the delegated actor, its harness and in-flight control; nothing realised them. Three placements:
does `CAP-AUT-6` (pre-authored steps) cover runtime-chosen actions; is an actor's memory a second knowledge base
beside `CAP-GOV-9`; is a model-provider gateway a case of `CAP-SUB-6`?

## Decision

1. `CAP-AUT-8` Agent Execution & Tool Mediation (AUT, ADR 0017) runs delegated actors in the harness
   (`AUTON-HARNESS`), mediating every call the actor selects at runtime and enforcing `AUTON-BOUNDARY` per action over
   the reachable action space. `depends_on` `CAP-SEC-2`, `CAP-SUB-8`, `CAP-DATA-8`; `applies_to` `AUTON-ACTOR`.
2. `CAP-DATA-8` Agent State & Memory (DATA) is the principal-scoped state an actor accumulates by use, retained under
   policy and erasable per principal; not `CAP-GOV-9` (shared knowledge), `CAP-DATA-7` (working memory) or
   `CAP-DATA-1` (the store type). `depends_on` `CAP-DATA-1`, `CAP-DATA-4`; `applies_to` `AUTON-ACTOR`.
3. `CAP-SUB-8` Model Provider Gateway (SUB) is the managed egress edge to model providers (routing, failover, quotas,
   metering, caching): a provisioned resource (`depends_on` `CAP-SUB-2`), sibling of `CAP-SUB-6`,
   which exposes tenant APIs outward.
4. `FUNC-tool-invocation-mediation`, `FUNC-mcp-tool-interoperability`, `FUNC-agent-execution-sandboxing` (also
   `CAP-SUB-1`) and `FUNC-inflight-run-control` support `CAP-AUT-8`; `FUNC-agent-state-persistence`,
   `FUNC-context-assembly` (also `CAP-AUT-8`), `FUNC-erasure-propagation` (also `CAP-DATA-4`) and
   `FUNC-retrieval-provenance` (also `CAP-GOV-9`) support `CAP-DATA-8`; `FUNC-model-provider-routing`,
   `FUNC-token-usage-metering` (also `CAP-COST-1`) and `FUNC-inference-response-caching` support `CAP-SUB-8`.
5. `FUNC-mcp-tool-interoperability` names the Model Context Protocol under ADR 0011 beside the generic mechanism,
   reaching tools and the resources an actor can read (ADR 0038).
6. `FUNC-erasure-propagation` propagates a deletion or retention decision from a source record to every derived
   artifact (copies, indexes, embeddings, caches); re-derivation from the corrected source discharges it, except for
   an unreproducible account of what happened, such as an execution record, where retention expiry, purge or key
   destruction does (ADR 0038, ADR 0039); its read-time sibling is `FUNC-access-policy-propagation` (ADR 0038).
7. Existing terms widen: `AUTON-BOUNDARY` `governs` `FUNC-tool-invocation-mediation` and
   `FUNC-agent-execution-sandboxing`; `CAP-OBS-1` takes agent telemetry as new sources and vocabulary; `CAP-COST-1`
   takes token spend as the same attribution pattern; `CAP-DATA-1` takes vector stores as a store type; `CAP-GOV-9`
   `applies_to` `AUTON-ACTOR`; `FUNC-privileged-access-management` reaches runtime-chosen actions.

## Consequences

- The boundary is enforceable end to end: actor, harness, governed functions, attribution to the accountable persona
  (ADR 0035).
- Amendments carry more than the mints; `CAP-AUT-8` fits its domain by execution affinity.
- A standard's name in an id is a second exception; its status can change within weeks, which a definition edit absorbs.

## Alternatives

- Stretch `CAP-AUT-6` to runtime-selected actions — collapses the line the boundary depends on.
- Widen `CAP-SUB-6` to model egress — opposite direction; routing, metering, caching absent there.
- Retrieval-augmented generation as a term — a composition of existing functions.
- A telemetry-convention function or an autonomy-tier scale — lowest stability rung; no stable referent.

## Sources

- https://modelcontextprotocol.io/community/governance · the protocol's governance and change process · accessed 2026-09-11
- https://opentelemetry.io/docs/specs/semconv/general/semantic-convention-groups/ · generative-AI conventions in development · accessed 2026-09-11
- https://arxiv.org/html/2606.18497v1 · soft-deleted embeddings remain reconstructible · accessed 2026-09-11

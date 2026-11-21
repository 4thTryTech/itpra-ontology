# ADR 0038 — Obligations of derived knowledge

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

A derived retrieval representation — index, embedding set, graph or cache — inherits its sources' obligations
(`KNOWLEDGE-ROLE`, ADR 0031). Erasure reaches it (ADR 0033); nothing carries a read restriction into it, nothing says
the source wins on disagreement, and a knowledge graph has no store type. Which are terms, and which variation points?

## Decision

1. `FUNC-access-policy-propagation` enforces, at retrieval time, the access restriction of the source a derived
   representation was built from, against the principal a consumer or delegated actor currently acts for, including
   when entitlements changed after the build. Supports `CAP-DATA-4`, `CAP-DATA-8`; `applies_to` `AUTON-ACTOR`;
   `depends_on` `FUNC-authorization-decision`, `FUNC-delegated-authority-chain` (ADR 0035).
   `FUNC-bia-semantic-access-policy` stays the structured-data case.
2. A sibling of `FUNC-erasure-propagation`, not a generalisation: erasure is write-time and one-shot, access
   read-time and continuous; they fail different tests. Build-time inheritance, query-time check or both is a
   scenario decision.
3. Source over derivative: `FUNC-retrieval-provenance` traces to the authoritative record, not the index entry, and
   the source prevails on disagreement; `FUNC-erasure-propagation` may also be discharged by re-derivation, where
   available (ADR 0039 states where not); `CAP-GOV-4` is authoritative and governing for the estate, discovered
   topology (`CAP-OBS-10`) a peer reconciled under precedence rules, not a derivative.
4. `FUNC-mcp-tool-interoperability` reaches the resources an actor can discover and read as well as tools: a
   definition edit, not a re-mint (ADR 0011).
5. `JRN-run-delegated-actor` `depends_on` `CAP-GOV-9`: grounding is part of running an actor.

## Consequences

- The derived store honours its source's access restrictions and erasures, traces to the authoritative record and
  loses every disagreement with it.
- `CAP-DATA-1` gains graph stores as a store type beside ADR 0033's vector stores; the data model binds below the
  reference tier, and a store's role is a property of its deployment, not its type.
- `FUNC-knowledge-retrieval` names how material is found — lexical, similarity, graph traversal, model-grounded or
  combined — as a variation point; retrieval-augmented generation is a composition, not a function.
- The access function rests on a risk entry and vendor convergence, no named incident; "the source prevails" precedes
  any settled mechanism.
- Propagating a wrong source permission faithfully still overshares; source hygiene is `CAP-SEC-2`.

## Alternatives

- One propagation function for deletion and access — different tests; one target per function.
- A retrieval-security capability — one behaviour under existing capabilities.
- A knowledge-graph capability — conflates store type with role, as ADR 0033 refused for vector stores.

## Sources

- https://genai.owasp.org/llmrisk/llm08-excessive-agency/ · a risk entry on vector-store access control · accessed 2026-09-14
- https://docs.azure.cn/en-us/search/search-document-level-access-overview · copy permissions at ingestion, re-check entitlement at query time · accessed 2026-09-14
- https://truto.one/blog/how-to-maintain-document-level-rbac-in-enterprise-rag-pipelines/ · a second vendor on the same control · accessed 2026-09-14
- https://blog.modelcontextprotocol.io/posts/2026-07-28/ · the protocol distinguishes resources from tools · accessed 2026-09-14

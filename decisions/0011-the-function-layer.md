# ADR 0011 — The function layer

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

A capability states an outcome; consumers also need the discrete behaviours that realise it, fine enough to
select and bind tools to, without a third tier or a tool index, and neutral while naming the standards that
are themselves the behaviour.

## Decision

1. A function (`FUNCTION`, `type: Function`) is a discrete unit of behaviour finer than a capability, in one
   flat layer: no tier field, no `derived_from`, nothing below it.
2. A function `supports` one or more capabilities, many-to-many, and may `depends_on` a function or
   `applies_to` a concept. Shared behaviour is one function (ADR 0009); a child capability (ADR 0004) is for
   an outcome-level split only.
3. Every function carries the code of its home service domain (`FUNC-ito-event-correlation`,
   `FUNC-euc-device-enrollment`); it may support another domain's capability by a record (ADR 0009) and keeps
   its id (amended by ADR 0045).
4. A function names a standard, protocol or technique only where that is the function itself, on two
   independent criteria. Scope: the standard is the behaviour, not one encoding of it — a signed-manifest
   format is one encoding of content provenance. Maturity: a published specification under
   independent governance with multi-vendor adoption, its status stated in the definition
   (`FUNC-ito-opamp-remote-management` names a Beta specification); an individual draft among competing drafts
   fails.
5. A specification change is a definition edit, not a new id; the market name and interchangeable encodings
   of one behaviour are aliases on the one function.
6. A neutral technique (federation, reconciliation) is named freely; named or neutral makes no structural
   difference, and neutrality is enforced by review (ADR 0001).

## Consequences

- A consumer finds the protocol it looks for; the price is a definition that tracks the specification's
  status and may need an edit before stability.
- A mature standard can still be refused on scope and a fitting one on maturity; each refusal is recorded,
  which keeps the layer from becoming a tool index.
- A function's id names its home domain, not whether it is shared; in return, sharing a function never
  renames it.

## Alternatives

- A tier field with named functions derived from neutral parents — withdrawn: it doubled functions to record
  what a term's location already says.
- A third tier below functions — a tool index in all but name; tools bind to functions.

## Sources

- https://pubs.opengroup.org/togaf-standard/business-architecture/business-capabilities.html · decomposition depth chosen by purpose · accessed 2026-05-25
- https://opentelemetry.io/docs/specs/opamp/ · a specification whose status the definition states · accessed 2026-08-20
- https://www.cncf.io/blog/2026/07/13/operating-opentelemetry-at-scale-with-opamp/ · multi-vendor adoption, the maturity criterion · accessed 2026-08-20
- https://modelcontextprotocol.io/community/governance · independent governance with a change process · accessed 2026-09-11
- https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html · one encoding of content provenance: the scope criterion · accessed 2026-09-11

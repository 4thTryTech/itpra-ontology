# ADR 0036 — Generative-content provenance

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

When a model drafts a content item, does content governance need a sibling capability for generated content?
`CAP-DXC-CNT-4` promises accountable published content, and a generated draft has no accountable author. Generation,
evaluation and risk classification are decided elsewhere (ADR 0033, ADR 0034, ADR 0035); only what happens to the
item is in question.

## Decision

1. Generative-content governance is content governance: `CAP-DXC-CNT-4` governs the lifecycle, review, approval,
   versioning, scheduling, compliance and archival, whoever or whatever drafted the item. A capability does not
   partition by a property of its input; no capability is minted.
2. Accountability attaches at the approval gate (`GC-APPROVAL`, ADR 0015); a delegated actor (`AUTON-ACTOR`,
   ADR 0030) never holds it. That holds only if the gate can see how the item came to exist.
3. `FUNC-dxc-content-provenance` (`supports` `CAP-DXC-CNT-4`, `applies_to` `AUTON-ACTOR`) records how a content item
   came to exist, including whether it was machine-generated and from what, and presents that record at the publish
   decision point and on later review. It is a different object from rights tracking (`FUNC-dxc-asset-rights`),
   component and artifact provenance (`FUNC-ito-provenance-tracking`, `FUNC-ito-provenance-verification`) and runtime
   retrieval citation (`FUNC-ito-retrieval-provenance`, ADR 0033).
4. The record is evidence that informs an accountable person's gate, not proof that replaces it; the reference tier
   asks that it be recorded and presented, not verified.
5. No named-standard function for content credentials: the standard is one encoding of the record, not the behaviour,
   and fails the scope criterion of ADR 0011 although it is more mature than the mechanism ADR 0035 declined on
   maturity. Which checks the gate applies, what the record contains and whether cryptographic credentials carry it
   are decided below the reference tier.

## Consequences

- Each claim inside "generative-content governance" routes to the term that owns it; one function suffices because
  the generation side lives elsewhere.
- Provenance functions sit in several domains; the objects differ and each definition says so.
- The reference tier asks for a record, not its content or its verification: a record reading only "generated: yes"
  conforms, and deployed verification has been defeated, so the record informs a human gate and never replaces one.

## Alternatives

- A generative-content-governance capability — duplicates a whole lifecycle for one content class and partitions on
  how the input was produced.
- Resolve as fully covered and mint nothing — leaves the gate uninformed, so "accountable" reads stronger than it is.
- A named-standard function for content credentials — the encoding is not the behaviour (ADR 0011).

## Sources

- https://spec.c2pa.org/specifications/specifications/2.4/specs/C2PA_Specification.html · a signed-manifest encoding of origin, one encoding of the function · accessed 2026-09-11
- https://en.wikipedia.org/wiki/Content_Credentials · adoption split between generative producers and capture devices; a deployed verification flaw · accessed 2026-09-11
- https://www2.itif.org/2026-ibrahim-c2pa-content-credentials.pdf · provenance as evidence informing a human gate, not proof · accessed 2026-09-11

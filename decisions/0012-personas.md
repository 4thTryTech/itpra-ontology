# ADR 0012 — Personas

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Capabilities and journeys must say who uses them without naming job titles or one operating model's roles.
Industry sources agree on a provider side and a consumer side and treat leadership, cost, security and data
roles as specialisations; a build/run split is itself an operating-model choice.

## Decision

1. A persona (`PERSONA-<slug>`, type `Persona`, entity `PERSONA`; ADR 0008) is a coarse, neutral role archetype
   with goals and success measures — never a job title or a role of one operating model.
2. Personas are tier-graduated: the reference tier carries a few archetypes, each refining into granular roles
   below it. A build/run split, a product owner or a cost owner are refinements, not personas.
3. The first service domain carries a provider (`PERSONA-platform-team`), a consumer (`PERSONA-platform-consumer`)
   and an assurance owner (`PERSONA-security-compliance`); the consumer is not called a service team, which
   collides with the notion of an IT service.
4. Every other service domain mints its archetypes in its own file (ADR 0007, ADR 0009) on the same pattern and
   adds those its work needs (ADR 0017–0027); a persona belongs to one service domain and never crosses into
   another.
5. Ownership is neutral accountability: the provider provides the capabilities, including governance of its own
   offerings; the assurance owner owns posture and controls, including authority over change; the consumer owns
   its own workloads. Named roles are assigned below the reference tier.
6. Edges are stated from the capability and journey side (`consumed_by`); a persona record carries none of its
   own.
7. `consumed_by` means used by a human persona. A non-human actor under delegated authority is a `Concept`,
   never a persona (ADR 0030); a capability it uses is consumed by the persona accountable for it.

## Consequences

- Every capability's consumer resolves to an archetype readable in any organisation; operating-model roles are
  mapped once, below the reference tier.
- Coarseness hides nuance: one archetype does not say whether an engineer or an operator consumes a capability.
- Eleven files repeat the pattern under different names, at the price of near-duplicates such as several
  security-and-compliance archetypes.

## Alternatives

- A build/run split and a product owner as personas — fixes an operating-model choice in the neutral tier.
- Provider and consumer only — loses the assurance pattern, a stakeholder consuming evidence and controls rather than workloads.
- The delegated actor as a persona — states a peer stakeholder with standing accountability, which it never has.

## Sources

- https://teamtopologies.com/key-concepts-content/what-are-the-core-team-types-in-team-topologies · platform and stream-aligned teams as team types · accessed 2026-05-21
- https://tag-app-delivery.cncf.io/blog/paap-personas/ · platform-as-a-product personas: a platform side and a consumer side · accessed 2026-05-21
- https://labs.cloudsecurityalliance.org/research/csa-whitepaper-nonhuman-identity-agentic-ai-governance-v1-cs/ · a non-human identity is a principal attributable to an accountable owner · accessed 2026-09-11

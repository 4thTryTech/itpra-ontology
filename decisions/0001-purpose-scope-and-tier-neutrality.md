# ADR 0001 — Purpose, scope and tier neutrality

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Reference architectures for an enterprise IT platform need one vocabulary that every document, diagram and derived
architecture can be checked against. Industry vocabularies are either tool-shaped or bound to one operating model, so a
shared vocabulary has to sit above both.

## Decision

1. The ITPRA ontology is the controlled vocabulary of the IT Platform Reference Architecture: terms, types and
   relationships, machine-readable so documents can be checked against it.
2. Its scope is the reference tier of eleven service domains of enterprise IT: service domains, planes, capability
   domains, capabilities, functions, personas, journeys, workflows, dimensions, governance constructs, quality attributes
   and the concepts that bind them.
3. Architecture is described in three tiers: T1, the reference tier this vocabulary defines; T2, a scenario architecture
   that binds an operating model; T3, an implementable architecture that binds tools. T2 and T3 are authored elsewhere
   with this vocabulary; the ontology holds T1 terms only.
4. T1 terms are tool-agnostic and operating-model-neutral: no term names a product or vendor, and no term uses the process
   vocabulary of a named operating model. Organisational functions such as a service desk may be named.
5. A function may name a standard, protocol or technique only where that is the behaviour itself; the criteria are stated
   with the function layer.
6. Neutrality is enforced by review of each change, not by a field on the term. "Tier" names architecture tiers;
   "level" and L1/L2/L3 are reserved for operations-support tiers.

## Consequences

- Any organisation can read the vocabulary without translating a vendor's or framework's dialect; the operating-model
  mapping happens once, below T1.
- A neutral name is sometimes longer or less familiar than the market term; the familiar word is kept as an alias.
- The eleven domains are peers in one vocabulary: any term can relate to any other.
- Requirements, specifications and derived architectures stay outside; the ontology names, it does not oblige.
- The reviewer, not a tool, is the last line of neutrality — accepted because a word list would ban legitimate uses.

## Alternatives

- One vocabulary per service domain — cross-domain terms would be duplicated or multi-homed; the join is the point.
- An operating-model framework's glossary — binds every reader to that model and names processes where a neutral
  outcome is wanted.
- A term-level tier marker and a word list — tried and withdrawn; the marker repeated the term's location, and the
  list banned legitimate uses.

## Sources

- https://tag-app-delivery.cncf.io/whitepapers/platforms/ · a platform as capability domains framed by outcomes, not tools · accessed 2026-05-20
- https://platformengineering.org/blog/create-your-own-platform-engineering-reference-architectures · tool-neutral reference architectures · accessed 2026-05-22
- https://www.tbmcouncil.org/taxonomy/ · a tower taxonomy of enterprise IT services · accessed 2026-05-22
- https://itsm.tools/34-itil-4-management-practices/ · one operating model's practice set · accessed 2026-05-21
- https://axify.io/blog/devops-value-stream · a second operating model's vocabulary · accessed 2026-05-21

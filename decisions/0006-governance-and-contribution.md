# ADR 0006 — Governance and contribution

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

A vocabulary that others pin needs a predictable way to change: who decides, what a change must carry, and which parts
are load-bearing enough to need more than a pull request. The maintainers are few; the rules have to work without a
committee.

## Decision

1. The ontology is maintained by its owner; maintainers are listed in `CODEOWNERS` and review every change. Pull
   requests from anyone are welcome.
2. A change to a term — new, amended or retired — lands with the decision record that decides it (ADR 0005) and the
   version bump it requires (ADR 0003), in the same pull request.
3. The backbone needs a record and a maintainer's review even for one line: the schema, the entity types and relationship
   verbs, planes, quality attributes, journey groups, governance constructs, dimension values and the service-domain set.
4. Contributors sign off each commit under the Developer Certificate of Origin; no contributor licence agreement is
   required. A contribution is accepted under the licences of ADR 0002.
5. The checks run on every pull request and must pass before merge: the term linter, the record lint, the version-bump
   check, the link check and the publication guard that refuses private references.

## Consequences

- Every change is traceable to a record and a version, which is what makes the vocabulary safe to pin.
- A one-word fix to a definition still needs a version bump; batching small fixes into one release is the expected
  practice.
- Backbone changes are deliberately slow; a contributor who needs a new verb opens the discussion with a record, not a
  diff.
- Sign-off is enough for provenance; the absence of a contributor agreement lowers the bar for small contributions.
- Owner governance concentrates decisions in few hands — accepted for a vocabulary that must stay coherent.

## Alternatives

- A steering committee with voting — more process than a vocabulary of this size can carry today.
- A contributor licence agreement — adds a signature step without adding provenance beyond a sign-off.
- Direct edits to backbone files with review only — a verb's meaning changing without a record breaks consumers' checks.

## Sources

- https://developercertificate.org/ · the Developer Certificate of Origin 1.1 · accessed 2026-11-21
- https://obofoundry.org/principles/fp-001-open.html · open-ontology practice: contributions under the declared open licence · accessed 2026-11-08
- https://arxiv.org/pdf/2003.13084 · vocabulary practice: clear ownership and a documented change process · accessed 2026-05-21

# ADR 0046 — Records without content leave: workflows, placements and unused id forms

Status: Accepted  
Date: 2026-11-24  
Supersedes: —  
Superseded by: —  

## Context

A `Workflow` record catalogued a diagram the vocabulary does not hold, and two of eleven service domains had
any. A placement kept an industry term findable until its service domain had capability domains; all four
domains now have them. One reserved prefix and two requirement-id forms served no consumer. A release meant
for outside use holds only what a consumer can use.

## Decision

1. The vocabulary holds no `Workflow` record: the thirty are removed. `WORKFLOW`, the type `Workflow`, the form
   `WF-<code>-<slug>` and `realized_in` stay, for a consumer's own diagram of a journey (amends ADR 0001
   rule 2, ADR 0013 rule 6, ADR 0045 rule 5).
2. The four placements are removed, with the `SDP-` prefix and the pair `CONCEPT`→`SERVICE_DOMAIN` of
   `belongs_to_service_domain`, which only they used (amends ADR 0009 rule 7, ADR 0004 rule 2, ADR 0007
   rules 3 and 4, ADR 0008 rule 3). No placement is minted again: a recognised capability waits for a
   capability that describes it.
3. A removed placement's market words move, as aliases, to the record that describes the behaviour: unified
   endpoint management to `EUC-DEV`, product analytics to `BIA-PRD`, digital experience management to
   `SD-DIGITAL-EXPERIENCE`. Robotic process automation keeps no record: no capability describes it.
4. `SVC-` is no longer a reserved prefix. Requirement ids have two reserved forms, `FR-<CODE>-<n>` and
   `NFR-<CODE>_<QA>-<n>`; the forms without a service-domain code are withdrawn (amends ADR 0004 rule 5,
   ADR 0045 rule 8).
5. A term file opens with what it holds, its type, its id form and its deciding record. A comment groups
   records; it carries no history, ruling or reference to another document.
6. The removals are MAJOR and ship in 5.0.0 with the rename of ADR 0045. `migrations/5.0.0.yaml` lists the
   removed ids and files; a removed id has no successor and its IRI names no term.

## Consequences

- Every record defines something a consumer can use; one type, `Workflow`, has no instance in the vocabulary.
- A consumer that holds a workflow or placement id drops the reference: nothing replaces it.
- Robotic process automation is not findable in the vocabulary until a capability describes it.
- A registry whose requirement ids lack a service-domain code is outside the reserved forms.
- One MAJOR release carries the rename and the removals, so a consumer migrates once.

## Alternatives

- Retire the records (ADR 0048) — retirement keeps a term that defined something; these did not, and a MAJOR release is open.
- Author workflows for the nine other domains — a diagram is a document of the architecture that draws it, not a term.
- Keep the placements until each is modelled — their premise, a service domain without capability domains, is gone.

## Sources

- https://semver.org/ · an incompatible change is a MAJOR release · accessed 2026-11-08
- https://www.w3.org/TR/skos-reference/ · alternative labels beside one preferred label · accessed 2026-09-23

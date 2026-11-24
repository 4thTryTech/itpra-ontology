# ADR 0013 — Journeys, journey groups and workflows

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Journeys are the stories through which personas reach outcomes across capabilities; without an agreed grouping
they accrete inconsistently, and grouping by persona scatters one outcome across several buckets. The grouping
must be neutral, small and shared by eleven service domains.

## Decision

1. A journey (`JRN-<code>-<slug>`, type `Journey`, entity `JOURNEY`; ADR 0008) is an end-to-end story a persona
   follows to achieve an outcome across capabilities; it is `grouped_by` exactly one journey group, `consumed_by`
   its primary personas and `depends_on` the capabilities it exercises (amended by ADR 0045).
2. Six journey groups (`JG-<slug>`, type `JourneyGroup`) form a controlled vocabulary: Onboarding
   (`JG-ONBOARDING`), Build & Deliver (`JG-DELIVERY`), Operate (`JG-OPERATIONS`), Respond & Recover
   (`JG-RESPONSE`), Govern & Assure (`JG-GOVERNANCE`) and Evolve & Retire (`JG-EVOLUTION`).
3. Grouping is by lifecycle phase or cross-cutting concern: the design → deploy → operate spine, bracketed by
   Onboarding and Evolve & Retire, with Respond & Recover and Govern & Assure cutting across. A journey is never
   grouped by persona, technology or kind of actor; one that fits two groups goes with its primary outcome.
4. The six groups are shared by every service domain and never redefined; the group is not encoded in the
   journey id, and "Day 0/1/2" labels are not used.
5. A journey's steps reference capabilities and governance construct points (ADR 0015), never tools or named
   processes.
6. A workflow (`WF-<code>-<slug>`, type `Workflow`, entity `WORKFLOW`) is a consumer's own diagram `realized_in`
   exactly one journey; the vocabulary holds none (amended by ADR 0045, ADR 0046).
7. A group is merged or renamed only by a record, when authoring shows it never populated or routinely
   ambiguous; the most novel work since the set was fixed fitted existing groups, and the six stand.

## Consequences

- One grouping axis, the phase, with the persona orthogonal: a journey crosses personas and still has one home.
- Some journeys plausibly fit two groups, such as a migration; the primary-outcome rule decides.
- A diagram belongs to the architecture that draws it: a consumer's workflow names the journey it realises,
  and no diagram is versioned with the vocabulary.
- Refusing technology- or actor-shaped groups keeps the grouping stable as new kinds of work appear, at the cost
  of hiding that novelty from the grouping.

## Alternatives

- Five placeholder groups (onboarding, lifecycle, day-2, exception, governance) — "lifecycle" conflated delivery with evolution, "day-2" is ambiguous jargon, "exception" under-described recovery.
- Grouping by persona — journeys cross personas; one outcome such as incident response would be scattered.
- An agentic journey group — shaped by a technology and a kind of actor, not a lifecycle phase.

## Sources

- https://codilime.com/blog/day-0-day-1-day-2-the-software-lifecycle-in-the-cloud-age/ · design, deploy and operate lifecycle phases; the operate phase is open-ended · accessed 2026-05-21
- https://www.redhat.com/en/topics/platform-engineering/golden-paths · critical user journeys packaged as golden paths · accessed 2026-05-21

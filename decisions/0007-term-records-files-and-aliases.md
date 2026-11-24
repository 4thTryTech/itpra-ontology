# ADR 0007 — Term records, files and aliases

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

A term is read by people and checked by machines, so it needs one fixed shape. Eleven service domains author
into one vocabulary, so files must merge without conflict. Market words move faster than the behaviours they
name.

## Decision

1. A term is one YAML record: `id`, `term`, `type` and `definition` are required; `aliases`, `deprecated`,
   `relates_to`, `source`, `retired` and `replaced_by` optional. Ids: ADR 0004; `source` grammar: ADR 0005
   (amended by ADR 0048).
2. `type` is one of `EntityType`, `RelationshipType`, `QualityAttribute`, `Domain`, `Plane`, `Concept`,
   `Capability`, `Function`, `Persona`, `JourneyGroup`, `Journey`, `Workflow`, `ServiceDomain`. `relates_to`
   holds `{rel, target}` pairs: `rel` a verb of ADR 0008, `target` another record's id.
3. Files merge into one set with globally unique ids. `schema.yaml`, `entities.yaml` and `relationships.yaml`
   hold the shape, types and verbs; all other records sit under `terms/`, split by kind and service domain
   (`domains-<code>`, `capabilities-<code>-<grp>`, `functions-<code>-<grp>`, `personas-<code>`,
   `journeys-<code>`); a file named with a code is that domain's, one without is shared (amended by ADR 0045,
   ADR 0046).
4. Planes, journey groups, service domains, quality attributes, dimensions, governance constructs, coverage
   areas, autonomy concepts and knowledge roles are shared files (ADR 0006), never redefined by a domain
   (amended by ADR 0046).
5. `aliases` are alternative labels — synonyms, market words, industry categories — disjoint from the term's own
   label and naming no product or operating-model process (ADR 0001).
6. `deprecated` lists synonyms authors avoid; advisory, since the words occur legitimately elsewhere, and
   projected as hidden labels.
7. A term whose market name is younger than its behaviour is defined by its behaviour and found by its name: the
   phrase goes in `aliases`, never in `term` or `definition`. A young word naming the right object may be the
   `term`; when it moves, the label changes, not the id.
8. A change to `term`, `definition`, `aliases` or `deprecated` is PATCH; a change of id is a rename and MAJOR
   (ADR 0003).

## Consequences

- One parser reads every file; a term is found by its label or any market name.
- Parallel authoring touches disjoint files; only a shared file takes ADR 0006's slower path.
- Behaviour-defined labels outlive the words of the day but read less familiarly.
- An advisory `deprecated` list depends on review; nothing mechanical stops a banned word.

## Alternatives

- One file per kind — every domain edits the same file; parallel changes collide.
- Market words as ids — bind the vocabulary to vendor usage; a MAJOR release when the word moves.
- A machine-enforced banned-word list — the same words occur legitimately elsewhere.

## Sources

- https://www.w3.org/TR/skos-reference/ · preferred and alternative labels are disjoint · accessed 2026-09-19
- https://learn.microsoft.com/azure/durable-task/common/what-is-durable-task · a market phrase younger than the behaviour it names · accessed 2026-09-15
- https://en.wikipedia.org/wiki/Agent_harness · a young word kept as a term for the object it names · accessed 2026-09-11

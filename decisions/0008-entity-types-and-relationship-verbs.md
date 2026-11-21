# ADR 0008 — Entity types and relationship verbs

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Documents are checked against a closed set of kinds and verbs, each with a stated meaning, domain, range and
cardinality, or every check re-invents them. This record states the set as it stands and where each fact is
declared.

## Decision

1. The entity types (`EntityType` records): `ITPRA_TIER`, `PLANE`, `DOMAIN`, `CAPABILITY`, `FUNCTION`,
   `SERVICE`, `PERSONA`, `JOURNEY_GROUP`, `JOURNEY`, `WORKFLOW`, `OPERATING_MODEL`, `TENANT`, `ENVIRONMENT`,
   `SERVICE_DOMAIN`, `ADR`, `REQUIREMENT` (forms `FR` and `NFR`), `QUALITY_ATTRIBUTE` and `CONCEPT`. `PLANE`,
   `FUNCTION`, `JOURNEY_GROUP` and `SERVICE_DOMAIN` arrive with ADR 0010, ADR 0011, ADR 0013 and ADR 0009; the
   rest are seeded here.
2. Each verb's domain, range and cardinality are declared once, in the authoring schema, read off the data; the
   `EntityType` records restate them as permitted pairs, and a test holds both equal. A pair the data uses must
   be declared; a declared pair without instance stays.
3. The verbs (`RelationshipType` records) and their pairs: `grouped_by` `CAPABILITY`→`DOMAIN`, `DOMAIN`→`PLANE`,
   `JOURNEY`→`JOURNEY_GROUP`, `PLANE`|`JOURNEY_GROUP`→`ITPRA_TIER`; `consumed_by`
   `CAPABILITY`|`SERVICE`|`JOURNEY`|`TENANT`→`PERSONA`; `realized_in` `CAPABILITY`|`WORKFLOW`→`JOURNEY`;
   `depends_on` `CAPABILITY`→`CAPABILITY`, `FUNCTION`→`FUNCTION`, `JOURNEY`→`CAPABILITY`,
   `CONCEPT`→`CONCEPT`|`FUNCTION`; `decomposes_into` and `derived_from` `CAPABILITY`→`CAPABILITY`; `supports`
   `FUNCTION`→`CAPABILITY`; `met_by` `REQUIREMENT`|`FR`|`NFR`→`CAPABILITY`; `verified_by` the same→`JOURNEY`;
   `categorized_as` `NFR`→`QUALITY_ATTRIBUTE`; `supersedes` `ADR`→`ADR`; `owns` `PERSONA`→`CAPABILITY`;
   `governs` `OPERATING_MODEL`→`WORKFLOW`, `CONCEPT`→`FUNCTION`|`CONCEPT`; `applies_to`
   `CAPABILITY`|`FUNCTION`|`CONCEPT`→`CONCEPT`, `CONCEPT`→`CAPABILITY`, `OPERATING_MODEL`|`ADR`→`ITPRA_TIER`;
   `produces` `SERVICE`→`CAPABILITY`; `interfaces_with` (across a boundary, neither containing the other)
   `SERVICE_DOMAIN`→`PLANE`; `belongs_to_service_domain` `DOMAIN`|`CONCEPT`→`SERVICE_DOMAIN`. A concept's
   `applies_to` an entity type lives in the authoring schema alone.
4. `grouped_by`, `categorized_as` and `belongs_to_service_domain` are single-valued (a `Domain` carries exactly
   one, ADR 0009); a function `supports` at least one capability; other verbs are many-to-many. `met_by` runs
   from requirement to element, never the reverse.
5. `consumed_by` means used by a human persona; a delegated actor's use is expressed through the accountable
   persona it acts for (ADR 0030).
6. Conformance, derivation and authority are obligations on instances in an adopter's estate, carried by
   functions and definitions, not verbs; a term-level link uses `depends_on` or `applies_to` (ADR 0031). A new
   verb or type is a backbone change (ADR 0006).

## Consequences

- A check rejects an undeclared verb, pair or cardinality; a graph projection needs no rule of its own.
- A verb's facts live in two places by design; a test, not a reader, keeps them equal.
- Requirements are typed here but kept in consumers' registries (ADR 0001), so their verbs have no instance in
  the vocabulary.
- A verb whose meaning changes is MAJOR (ADR 0003), so verbs are added rarely and widened never.

## Alternatives

- Free-text relationships — unreadable by a check, unprojectable to a graph.
- A verb per nuance (informs, feeds, conforms_to) — claims no term needs and every check must learn.
- `consumed_by` widened to delegated actors — collapses accountability and use into one verb.

## Sources

- https://www.avolutionsoftware.com/abacus/ · capability-to-technology mapping as a many-to-many graph · accessed 2026-05-25
- https://datatracker.ietf.org/doc/html/draft-oauth-ai-agents-on-behalf-of-user-02 · an agent acts for a user under delegated, scoped authorization · accessed 2026-09-11

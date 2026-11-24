# ADR 0037 — The semantic progression

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

A semantic layer is reached in stages — glossary, taxonomy, ontology, knowledge graph, semantic layer — which practice
governs separately: a glossary change is a business-meaning judgement, an ontology change a modelling judgement
released in versions consumers pin. Each stage needs the right kind of term; the governing semantic model of ADR 0031
needs a home.

## Decision

1. `CAP-BIA-GOV-7` Ontology & Conceptual Model Management (`BIA-GOV`) maintains a formal, machine-readable, versioned
   model of the organisation's business concepts, built from the glossary and controlled vocabularies, so data,
   semantic definitions, automation and delegated actors share one governed meaning: the governing-semantic-model role
   of `KNOWLEDGE-ROLE` (ADR 0031). A capability, with its own owner, change control and journey; `depends_on`
   `CAP-BIA-GOV-1`, `CAP-BIA-GOV-5`.
2. Each stage is a kind of term: glossary, the function `FUNC-bia-glossary-management`, which owns the alias
   `business glossary` (`FUNC-bia-metadata-management` references it, not holds it); taxonomy,
   `FUNC-bia-reference-data-control`, widened from flat code lists to hierarchical vocabularies; ontology, the
   capability; knowledge graph, its instance layer, a store type under `CAP-ITO-DATA-1` (ADR 0038); semantic layer,
   `CAP-BIA-SEM-1`, reused. There is no thesaurus stage.
3. `FUNC-bia-ontology-modelling` (versioned releases with migration paths and deprecation windows) and
   `FUNC-bia-semantic-model-publication` (a release in standard machine-readable form) support `CAP-BIA-GOV-7`;
   publication also supports `CAP-BIA-GOV-5`.
4. No term, definition or alias names a standard or an edition (ADR 0011); modelling language and publication form
   are scenario decisions.
5. `PERSONA-bia-semantic-modeller` models vocabularies and ontology structure and approves structural change; the
   data steward assures, the analytics team consumes, business owners hold term meaning.
6. `CAP-BIA-SEM-1` `depends_on` `CAP-BIA-GOV-7` and serves its definitions to every consuming surface, delegated
   actors included; `CAP-BIA-GOV-5` reaches hierarchical vocabularies, and a mapping into another party's scheme needs
   that owner's governance.
7. `JRN-bia-formalise-business-term` (`JG-GOVERNANCE`) carries a term from agreed definition to the semantic layer;
   `JRN-bia-evolve-semantic-model` gains `depends_on` `CAP-BIA-GOV-7` and `CAP-BIA-GOV-3`.

## Consequences

- The progression is expressible stage by stage; a reader searching for "business glossary" finds the behaviour, not
  metadata management.
- A standards revision is a currency event below the reference tier, never a vocabulary change.
- Other domains' models can play the same governing role; ADR 0031 carries the role, this record one domain's
  management of it.
- Climbing is not the goal: stopping at glossary and taxonomy is healthy; how far to go is a scenario decision.

## Alternatives

- Ontology as a function under `CAP-BIA-GOV-2` — it has its own owner, release discipline and journey.
- Widening `PERSONA-bia-data-steward` — assurance and modelling differ in work and approval authority.
- Naming the standards in the functions — the standard is not the behaviour (ADR 0011).

## Sources

- https://stids.c4i.gmu.edu/STIDS2011/presentations/STIDS2011_Tutorial_LeoObrst.pdf · the ontology spectrum, glossary to ontology · accessed 2026-09-14
- https://www.getgalaxy.io/articles/ontology-management-semantic-modeling-operating-model-enterprise-context · ontology change owned separately from business meaning · accessed 2026-09-14

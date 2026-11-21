# ADR 0002 — Licence and attribution

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

## Context

A published vocabulary is useful only if others may copy, cite, extend and redistribute it, and the code that checks and
projects it has different needs from the vocabulary itself. The licence has to be settled before the first public release.

## Decision

1. The vocabulary — the term files, the generated projections and the decision records — is licensed under Creative
   Commons Attribution 4.0 International (CC BY 4.0).
2. Code — the linter, the projection pipeline, scripts and tests — is licensed under the Apache License 2.0.
3. Attribution names the ITPRA ontology, the version used and its URL; a derived vocabulary states what it changed.
4. Each release carries a `CITATION.cff`; once registered, every version receives a DOI and the ontology a concept DOI.
5. The licence is declared in the repository, in the header of every projection and in `CITATION.cff`; a licence change
   is a MAJOR version.

## Consequences

- Anyone may pin, vendor, translate or extend the vocabulary, commercially or not, as long as the attribution stays.
- Attribution rather than a public-domain dedication keeps a term's provenance visible across forks, at the cost of one
  obligation on every reuse.
- Two licences in one repository need a licence file for each and a header convention that says which applies where.
- Code contributions carry a patent grant; vocabulary contributions do not need one.
- No share-alike clause: a downstream vocabulary may be closed, which is the price of frictionless reuse.

## Alternatives

- CC0 for everything — drops attribution, the one thing the ontology asks in return; Creative Commons also advises against
  its licences for software, so code would still need another.
- Apache-2.0 for everything — a software licence; its patent and notice clauses fit code, not a vocabulary.
- CC BY-SA or CC BY-NC — share-alike and non-commercial clauses keep commercial platforms from adopting the vocabulary and
  are excluded by the open-ontology practice this record follows.

## Sources

- https://obofoundry.org/principles/fp-001-open.html · open-ontology practice: CC BY or CC0, licence declared in the ontology, NC and SA excluded · accessed 2026-11-08
- https://creativecommons.org/licenses/by/4.0/legalcode · the CC BY 4.0 licence text · accessed 2026-11-21
- https://www.apache.org/licenses/LICENSE-2.0 · the Apache License 2.0 text, including the patent grant · accessed 2026-11-21
- https://creativecommons.org/?p=27081 · Creative Commons on using its licences for software · accessed 2026-11-08
- https://citation-file-format.github.io/about · the Citation File Format · accessed 2026-11-08
- https://book.the-turing-way.org/communication/citable/citable-cff/ · a citation file with a DOI per release and a concept DOI · accessed 2026-11-08

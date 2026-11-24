# ADR 0005 — Decision records, citations and the writing standard

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Every term's `source:` names the decision that minted or changed it, so decisions must be findable, stable and short.
Consumers keep decision records of their own, so a citation must say whose record it names.

## Decision

1. Decisions about the vocabulary are recorded in `decisions/`, one decision per record, numbered from 0001 in reading
   order and never renumbered; the file is `NNNN-kebab-title.md`.
2. A record follows the template: a title that names the decision; a status block (Accepted, Superseded, Deprecated or
   Rejected, with date and lineage); Context, Decision, Consequences, Alternatives, Sources. It is proposed as a pull
   request with the change it decides and lands Accepted; a superseded record keeps its text and names its successor;
   an amended rule is restated in place, naming the amending record (amended by ADR 0049).
3. A record is short: at most 60 non-blank lines and 500 words (hard limit 80 and 700). Context in six lines; Decision
   as numbered rules in the present tense; Consequences in three to six bullets, at least one a trade-off; Alternatives
   one line each; Sources as URL, what it supports, access date.
4. A term's `source:` cites `ADR NNNN`, optionally with `(amended by ADR NNNN)` or `(extended by ADR NNNN)`; citations
   are separated by `; `. `ADR NNNN` always means the record of that number in this repository. Anything else — a
   standard, another project's record — is free text carrying its URL, external in its entirety.
5. A record never cites another project's record by number; it links only within `decisions/` or to the web. No
   research document is published: a record carries its own sources.
6. A record names no product, operating-model process or person; the lint rejects those words and any sign of
   another repository.

## Consequences

- A reader reaches the reason a term exists in one hop, and its evidence in one more.
- Short records leave out how a decision was reached; that history stays with those who took it.
- Consumers cite these records by URL, so a record's URL is part of the contract: numbers are never reused.
- Machine-checking keeps records uniform at the price of occasional awkward phrasing.
- Rejected decisions are kept, so a settled question is not reopened unknowingly.

## Alternatives

- Carry the originating project's records verbatim — long, written for another audience, bound to its numbers.
- Qualify citations with a project code — a token on every citation for what the repository boundary solves.
- Decisions in a wiki or issue tracker — not versioned with the vocabulary, not citable at a stable URL.

## Sources

- https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions · the decision-record form; records are superseded, not edited · accessed 2026-11-21
- https://adr.github.io/ · decision-record practice and templates · accessed 2026-11-21
- https://arxiv.org/pdf/2003.13084 · documented, versioned vocabulary decisions · accessed 2026-05-21

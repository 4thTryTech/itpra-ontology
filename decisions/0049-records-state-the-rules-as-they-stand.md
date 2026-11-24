# ADR 0049 — Records state the rules as they stand: amended in place, ids kept current

Status: Accepted  
Date: 2026-11-24  
Supersedes: —  
Superseded by: —  

## Context

A record whose text never changes ends up citing ids a rename has ended and stating rules a later record has
amended; its reader must hold every later record in mind. Consumers cite a record by its URL and read it
alone (ADR 0005), so each record has to be true by itself.

## Decision

1. A record states its rules as they stand. When a later record amends a rule, the rule is restated in place
   and names the amending record — `(amended by ADR NNNN)` — as a term's `source` does (ADR 0005 rule 4).
2. A rule that a later record withdraws is replaced by one line that names that record. Rule numbers never
   change.
3. An id cited in a record is a live id. When an id is renamed, the records that cite it follow; a removed id
   is cited only by the record that removes it and by the migration file.
4. The amending record lists every rule it amends, and lands in the same change as the restatements.
5. A record whose decision is replaced as a whole is superseded, not amended: its status says so, it names
   its successor and it keeps its text (ADR 0005 rule 2).
6. A record carries no change log. Earlier wording stays readable in the releases that carried it and in the
   repository's history.
7. This replaces ADR 0045 rule 7: no id in a record is read through a mapping.

## Consequences

- A record read alone is true today, and a term's `source` leads to a rule in force.
- A record's text is no longer fixed when it is accepted: what was decided when is read from releases and
  history, not from the record.
- A rename or an amendment costs an edit to every record that cites it, in the same change.
- A consumer that needs one wording of a record pins a release; the URL on `master` moves with the rules.

## Alternatives

- Fixed text, with old ids read through the migration map — records that cite ids no term carries, in a release meant for outside readers.
- Supersede every amended record whole — one rename would supersede a third of the records for a substitution.
- A change log inside each record — history in a document whose job is the rule.

## Sources

- https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions · the practice departed from: records are superseded, not edited · accessed 2026-11-21
- https://adr.github.io/ · a decision log of single decisions, each with its rationale · accessed 2026-11-24
- https://www.w3.org/TR/cooluris/ · a stable URL for a document whose content is maintained · accessed 2026-09-19

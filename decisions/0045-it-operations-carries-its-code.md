# ADR 0045 — IT Operations carries its code: one id and file form for all eleven service domains

Status: Accepted  
Date: 2026-11-23  
Supersedes: —  
Superseded by: —  

## Context

IT Operations was authored first and kept ids and file names without a service-domain code (ADR 0004, ADR 0007).
Its terms cannot be told from shared ones by name, and the domain reads as the vocabulary's home, not one of
eleven peers (ADR 0009).

## Decision

1. IT Operations has the code `ITO`, an alias of `SD-IT-OPERATIONS`; its terms carry it after the kind prefix as
   the other ten domains' do. ADR 0004 rule 3 keeps no exception.
2. Its capability domains are `ITO-FND`, `ITO-SUB`, `ITO-AUT`, `ITO-DEL`, `ITO-SEC`, `ITO-OBS`, `ITO-RES`,
   `ITO-COST`, `ITO-DATA`, `ITO-EXP` and `ITO-GOV`, its capabilities `CAP-ITO-<GRP>-<n>` (amends ADR 0010 rule 5,
   ADR 0017 rule 2).
3. Its functions are `FUNC-ito-<slug>`, personas `PERSONA-ito-<slug>`, journeys `JRN-ito-<slug>` and workflows
   `WF-ito-<slug>` (amends ADR 0011 rule 3 and the ids of ADR 0012 rule 3).
4. No function id is uncoded: the code names the function's home service domain. A function may still support
   another domain's capability by a record (ADR 0009), and keeps its id.
5. Its files are `domains-ito`, `capabilities-ito-<grp>`, `functions-ito-<grp>`, `personas-ito`, `journeys-ito`
   and `workflows-ito` (amends ADR 0007 rule 3). A term file named with a code is that domain's; one without is
   shared.
6. The change is a rename and MAJOR (ADR 0003): each new id is the old one with the code inserted, labels,
   definitions, planes and boundaries stay, and `migrations/5.0.0.yaml` lists every pair. A renamed record's
   `source` names this record.
7. An id written without the code in an earlier record reads as its coded successor; earlier records keep their
   text (ADR 0005).
8. Requirement ids stay with consumers (ADR 0001): `FR-<CODE>-<n>` and `NFR-<CODE>_<QA>-<n>` with a
   service-domain code are every domain's form; the uncoded forms of ADR 0004 rule 5 stay reserved for older
   registries.

## Consequences

- One rule reads every id and file name: the code after the kind prefix names the owning service domain.
- Every consumer reference to an IT Operations id breaks until rewritten; the map makes that a substitution,
  but each consumer must re-pin and apply it.
- The old ids' IRIs no longer name a term; the map is what a resolver needs to redirect them.
- A function's id no longer shows that it is shared; in return, sharing one never renames it.
- Earlier records show ids that no longer exist; rule 7 reconciles them, one indirection away.

## Alternatives

- Keep the exception — stable, but the first domain keeps reading as the home.
- Rename files and capability domains only — functions, personas and journeys stay unattributable by id.
- Keep each old id as a retired record — doubles the domain's records; the map carries the same information.

## Sources

- https://semver.org/ · an incompatible change is a MAJOR release · accessed 2026-11-08
- https://www.w3.org/TR/cooluris/ · slash IRIs that resolve individually · accessed 2026-09-19

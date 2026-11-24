# ADR 0009 — Service domains — eleven peers, attribution and placement

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Enterprise IT is wider than one platform. The vocabulary needs a partition coarser than a capability domain
and a rule for which partition owns a term — without privileging the platform over what surrounds it.

## Decision

1. A service domain (`SERVICE_DOMAIN`, `type: ServiceDomain`, id `SD-<slug>`) is a domain of IT services in
   the enterprise landscape; a capability domain is the finer grouping inside one (ADR 0010).
2. The eleven service domains are peers: none is the platform's home, none adjacent. `SD-IT-OPERATIONS`
   holds the infrastructure platform without structural privilege.
3. `interfaces_with` is symmetric and general: an exchange across a boundary where neither side contains the
   other. No service domain carries it to a plane (ADR 0010): the planes a domain works in follow from its
   capability domains' `grouped_by` edges (amended by ADR 0047).
4. Observing end-user experience is an operations capability; business analytics and customer-facing
   experience are domains of their own.
5. A term belongs to exactly one service domain: `belongs_to_service_domain` is single-valued, every
   capability domain carries it (IT Operations' included) and no tool defaults it. Placement is per term,
   never per topic.
6. Behaviour that recurs across service domains is one shared function `supports` each capability
   (ADR 0011); a capability is never multi-homed, and two domains' capabilities meet through `interfaces_with`
   or a dependency. A function may cross service domains, each crossing decided by a record; a persona never
   does.
7. Withdrawn by ADR 0046, which removes the placements.

## Consequences

- One partition covers all of enterprise IT: any term relates to any other, and one edge says who owns it.
- Single-valued attribution forces a choice where a capability recurs: a shared function and single-homed
  capabilities, two records where one would read more simply.
- A recognised capability that no capability describes has no record of its own: its market words are aliases
  on the record that describes the behaviour, or wait for one; acronyms stay aliases, never ids.

## Alternatives

- One home domain with adjacent domains — privileges one architecture over ten peers.
- Multi-homed capabilities — ownership becomes ambiguous; the function layer carries the shared part.

## Sources

- https://www.tbmcouncil.org/taxonomy/ · a tower taxonomy of enterprise IT services · accessed 2026-05-22
- https://www.gartner.com/reviews/market/digital-experience-monitoring · experience monitoring as an operations market · accessed 2026-05-26
- https://higherlogicdownload.s3.amazonaws.com/TBMCOUNCIL/c15d372f-9951-46c8-9c3f-213c696401b6/UploadedImages/TBM_Taxonomy_V4_0.pdf · one pattern, many executing towers · accessed 2026-05-26

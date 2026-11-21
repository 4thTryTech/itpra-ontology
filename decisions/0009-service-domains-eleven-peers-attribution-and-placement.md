# ADR 0009 — Service domains — eleven peers, attribution and placement

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Enterprise IT is wider than one platform. The vocabulary needs a partition coarser than a capability domain,
a rule for which partition owns a term, and a place for a recognised capability that no capability domain yet
describes — without privileging the platform over what surrounds it.

## Decision

1. A service domain (`SERVICE_DOMAIN`, `type: ServiceDomain`, id `SD-<slug>`) is a domain of IT services in
   the enterprise landscape; a capability domain is the finer grouping inside one (ADR 0010).
2. The eleven service domains are peers: none is the platform's home, none adjacent. `SD-IT-OPERATIONS`
   holds the infrastructure platform without structural privilege.
3. `interfaces_with` is symmetric and general: an exchange across a boundary where neither side contains the
   other. A service domain carries it to the planes (ADR 0010) it exchanges across — `SD-END-USER`
   Experience; `SD-SERVICE-DESK` Governance, Experience; `SD-FIELD-SUPPORT` Resource, Operations; `SD-APP-DEV`
   Delivery, Experience; `SD-DATACENTER` and `SD-NETWORK` Resource; `SD-SECURITY-GRC` Security, Governance;
   `SD-SERVICE-MGMT` Governance; `SD-BUSINESS-ANALYTICS` Resource, Experience; `SD-DIGITAL-EXPERIENCE`
   Experience, Delivery; `SD-IT-OPERATIONS` carries none.
4. Observing end-user experience is an operations capability; business analytics and customer-facing
   experience are domains of their own.
5. A term belongs to exactly one service domain: `belongs_to_service_domain` is single-valued, every
   capability domain carries it (the first domain's included) and no tool defaults it. Placement is per term,
   never per topic.
6. Behaviour that recurs across service domains is one shared function `supports` each capability
   (ADR 0011); a capability is never multi-homed, and two domains' capabilities meet through `interfaces_with`
   or a dependency. A function may cross service domains, each crossing decided by a record; a persona never
   does.
7. A recognised capability that no capability domain yet describes is a placement: `type: Concept`, id
   `SDP-<slug>`, one `belongs_to_service_domain` edge, aliases for its industry categories; not a capability,
   not a `supports` target. Four stand — `SDP-uem` (`SD-END-USER`), `SDP-rpa` (`SD-APP-DEV`),
   `SDP-product-analytics` (`SD-BUSINESS-ANALYTICS`), `SDP-dxm` (`SD-DIGITAL-EXPERIENCE`) — retired only by
   a record.

## Consequences

- One partition covers all of enterprise IT: any term relates to any other, and one edge says who owns it.
- Single-valued attribution forces a choice where a capability recurs: a shared function and single-homed
  capabilities, two records where one would read more simply.
- A placement keeps an industry term findable before it is modelled, at the price of records that are not
  capabilities; acronyms stay aliases, never ids.

## Alternatives

- One home domain with adjacent domains — privileges one architecture over ten peers.
- Multi-homed capabilities — ownership becomes ambiguous; the function layer carries the shared part.

## Sources

- https://www.tbmcouncil.org/taxonomy/ · a tower taxonomy of enterprise IT services · accessed 2026-05-22
- https://www.gartner.com/reviews/market/digital-experience-monitoring · experience monitoring as an operations market · accessed 2026-05-26
- https://higherlogicdownload.s3.amazonaws.com/TBMCOUNCIL/c15d372f-9951-46c8-9c3f-213c696401b6/UploadedImages/TBM_Taxonomy_V4_0.pdf · one pattern, many executing towers · accessed 2026-05-26

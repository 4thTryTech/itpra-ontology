# ADR 0047 — Service domains read as peers: definitions in their own right, no domain-to-plane edges

Status: Accepted  
Date: 2026-11-24  
Supersedes: —  
Superseded by: —  

## Context

ADR 0009 makes the eleven service domains peers. The shared records did not read that way: ten domains were
defined by their distance from the infrastructure platform, shared terms spoke of "the platform", and every
domain but one carried `interfaces_with` edges to planes. The planes group every domain's capability domains
(ADR 0010), so an edge from a domain to a plane cannot say whose part of the plane it means.

## Decision

1. A service domain's definition states what the domain is, does and owns in its own right. It places the
   domain neither outside, beside nor under another.
2. A boundary between two service domains is stated as a boundary between peers and names the other domain or
   its capability domain (amends the boundary rules of ADR 0017, ADR 0019, ADR 0020, ADR 0021, ADR 0022,
   ADR 0023, ADR 0024 and ADR 0027).
3. A shared record — plane, quality attribute, governance construct, journey group, dimension, entity type or
   verb — is worded to hold for all eleven domains. "The infrastructure platform" names what
   `SD-IT-OPERATIONS` owns and operates and is used only where a record is about it.
4. No service domain carries an `interfaces_with` edge to a plane: the sixteen edges are removed (amends
   ADR 0009 rule 3). The planes a domain works in follow from its capability domains' `grouped_by` edges.
5. `interfaces_with` keeps its meaning and its declared pair (ADR 0008). An edge between the terms of two
   service domains is added only by a record that decides it.
6. A reworded definition changes no id, label, type or relation, and its `source` names this record. The
   rewording is editorial (ADR 0007 rule 8); the edge removal ships in 5.0.0.

## Consequences

- A reader meets each domain on its own terms; none reads as the home of the others.
- The vocabulary no longer says which planes a domain exchanges across; what the edges told about the
  surroundings of the infrastructure platform is lost until edges between domains are decided.
- `interfaces_with` has no instance in the vocabulary; a consumer's query over it returns nothing.
- Wording that holds for eleven domains is less concrete than wording about one platform.

## Alternatives

- Keep the edges and redefine them as edges to another domain's plane — a plane belongs to no domain, so the edge cannot say whose.
- Edges from service domain to service domain — a new declared pair and a ruling on every pair of domains, not only ten.
- Keep the definitions and state the peer rule in the README — the term is what a consumer reads.

## Sources

- https://www.tbmcouncil.org/taxonomy/ · a tower taxonomy of enterprise IT services · accessed 2026-05-22
- https://www.w3.org/TR/skos-reference/ · a definition documents one concept · accessed 2026-09-23

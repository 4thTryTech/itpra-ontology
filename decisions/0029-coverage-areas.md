# ADR 0029 — Coverage areas

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

In an implementation one tool rarely covers one function across the whole estate: a hosted tool cannot reach
an air-gapped plant network, a regulated enclave needs a separately accredited stack. The same function then runs
on coexisting realizations, and industry has no neutral name for the parts of the estate they cover.

## Decision

1. `COVERAGE-AREA` "Coverage area" is a Concept with no service domain: a bounded partition of the estate within
   which a function's coverage is provided as a unit. A function may require simultaneous, distinct coverage in
   two or more areas because a single realization cannot span them.
2. Duplication is forced where a hard boundary withholds reach (the control plane cannot get there), trust,
   jurisdiction or accountability: four descriptive drivers — reachability, security, regulatory,
   responsibility — not a value set.
3. An area is genuine duplication, coexisting coverages of one function: the opposite of an environment
   dimension (`ENV-DIM-*`, ADR 0014), where one coverage's internals vary and the outcome stays one whole.
4. One baseline area covers the estate wherever no area overrides it: the declared term `AREA-baseline`
   "Enterprise-standard coverage area" (`applies_to` `COVERAGE-AREA`; id form ADR 0004), the default every function is
   served in unless an override area is declared, and the only area id the vocabulary holds.
5. T1 asserts only that coverage may be partitioned and that the baseline exists; the areas, their drivers and
   the functions needing per-area coverage are scenario decisions, the tool per area an implementation decision;
   tools never enter the vocabulary.
6. Only existing verbs, `applies_to` `ENVIRONMENT` and `FUNCTION`; one concept, in the shape of ADR 0028.
7. A function needing per-area coverage with none in a declared in-scope area is an error unless a baseline
   fallback or a recorded waiver is declared.

## Consequences

- Total coverage becomes a checkable fact rather than a silent gap.
- The partition falls at the function level: an execution function may ride the baseline while model serving is
  duplicated in an egress-free enclave.
- Trade-off: the drivers are prose, so a checker enforces fallback-or-waiver but cannot judge a driver.

## Alternatives

- A third environment-dimension axis — a dimension asserts one coverage, varying in realization, not coexisting
  duplication.
- A second concept for the enterprise standard — the default is not a new kind of thing.
- A fifth driver for agentic tooling — every force found resolves to one of the four; only the function-level
  granularity was confirmed.

## Sources

- https://csrc.nist.gov/glossary/term/enclave_boundary · a standards-body definition of a bounded part of the estate · accessed 2026-06-21
- https://www.fortinet.com/resources/cyberglossary/purdue-model · plant levels separated from enterprise IT: the reachability driver · accessed 2026-06-21
- https://pubs.opengroup.org/togaf-standard/ea-capability-and-governance/chap03.html · standards met by compliance or time-bounded dispensation: the baseline model · accessed 2026-06-21

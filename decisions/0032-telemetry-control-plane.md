# ADR 0032 — Telemetry control plane

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

The observability domain covers the telemetry data plane, collection (`CAP-OBS-1`) and pipeline (`CAP-OBS-8`), but not
the control plane over the components realising it: enrolling, inventorying, configuring and keeping current the
agents themselves. An open remote-management protocol exists at Beta with multi-vendor adoption; estates without it
assemble the behaviour from generic delivery machinery.

## Decision

1. `CAP-OBS-11` Telemetry Agent & Pipeline Configuration Management (OBS, ADR 0017): the configurations and versions
   of telemetry agents and pipeline components are authored, validated, versioned, distributed, progressively rolled
   out and kept current, with enrollment, inventory and health visible as a management concern; the control plane
   over the components realising `CAP-OBS-1` and `CAP-OBS-8`.
2. It is the telemetry estate's instantiation of generic configuration management plus the collector-specific
   behaviour no generic term covers: `depends_on` `CAP-FND-1`, `CAP-FND-2`, `CAP-AUT-4`, `CAP-OBS-5`; `consumed_by`
   `PERSONA-platform-team`; alias telemetry control plane.
3. `FUNC-collector-fleet-inventory`, the live register of deployed components and their reported state, and
   `FUNC-collector-enrollment`, the trust bootstrap between a component and its management plane (credential issuance
   stays `CAP-SEC-3`), support it alone.
4. `FUNC-configuration-templating` (composition from parameterised building blocks; also `CAP-FND-1`) and
   `FUNC-configuration-validation` (syntax, schema, load and dry-run checks before distribution) are generic
   functions also supporting `CAP-AUT-4`.
5. `FUNC-opamp-remote-management` is a named-standard function under ADR 0011: remote management of telemetry agents
   via the Open Agent Management Protocol, covering configuration exchange, package management, health reporting and
   connection settings. Its definition states the specification's status (Beta as of 2026-08), re-verified when
   binding; a specification change is a definition edit.
6. Other behaviour resolves to existing terms: health `FUNC-infrastructure-monitoring`, versions `CAP-OBS-5`,
   history `CAP-FND-1`, rollout `FUNC-progressive-rollout`, rollback `FUNC-configuration-rollback`, drift
   `CAP-AUT-3`, access and audit `CAP-SEC-2`, secrets `CAP-FND-2`, remote commands `CAP-AUT-6`.
7. Whether the control plane is a dedicated management plane, configuration-as-code over generic delivery machinery,
   or a split of both per coverage area (ADR 0029) is decided below the reference tier.

## Consequences

- The control plane is assessable as its own capability instead of disappearing inside generic configuration
  management.
- The named-standard function is a precise binding point; its definition may need an edit if the specification
  changes before it stabilises, the price of naming a Beta standard.
- `CAP-OBS-11` overlaps `CAP-AUT-4` in concept; the definition holds the line at the telemetry estate plus the
  collector-specific functions.

## Alternatives

- Reuse only, `CAP-AUT-4` and `CAP-FND-1` applied to telemetry components — inventory, enrollment, templating and
  validation had no generic home.
- One function per observed behaviour — most resolve to existing terms; duplicates breach ADR 0011.
- Defer the named-standard function until the specification is Stable — adoption is already multi-vendor; scenarios
  would describe the protocol by circumlocution.

## Sources

- https://opentelemetry.io/docs/specs/opamp/ · the protocol as an open specification at Beta: remote configuration, package management, health reporting · accessed 2026-08-20
- https://www.cncf.io/blog/2026/07/13/operating-opentelemetry-at-scale-with-opamp/ · multi-vendor and end-user adoption · accessed 2026-08-20

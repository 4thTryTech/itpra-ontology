# Governance

How this vocabulary is maintained, as decided in [ADR 0006](decisions/0006-governance-and-contribution.md).

- **Maintainers.** The ontology is maintained by its owner; the maintainers listed in [CODEOWNERS](CODEOWNERS) review
  every change and approve releases. Maintainers are added by the owner.
- **Decisions.** Every change to the vocabulary is decided in a record under `decisions/`, proposed as a pull request
  together with the change itself, and lands Accepted. A record is superseded by a later record, never rewritten; a
  declined proposal is kept as Rejected ([ADR 0005](decisions/0005-decision-records-citations-and-the-writing-standard.md)).
- **The backbone is slower by design.** The schema, entity types and relationship verbs, planes, quality attributes,
  journey groups, governance constructs, dimension values and the service-domain set change only with a record and a
  maintainer's review, because consumers' checks depend on them.
- **Releases.** A release is a tag `vX.Y.Z` on `master` with an immutable release; every content change bumps
  `ontology_version` ([ADR 0003](decisions/0003-versioning-releases-and-pinning.md)). Pre-releases are `vX.Y.Z-rc.N`.
  A maintainer cuts a release by running the `release` workflow on `master` with the version (it creates the tag) or
  by pushing the tag; the workflow checks the tag against `ontology_version` and the changelog, builds the source
  archive with its `sha256` from the tag, and publishes the release.
- **Contributions** are accepted under the repository's licences with a Developer Certificate of Origin sign-off; there
  is no contributor licence agreement ([ADR 0002](decisions/0002-licence-and-attribution.md)).
- **Disagreement** about a change is settled in the record's pull request; the maintainers decide and the record states
  the alternatives that were not taken.

# ADR 0044 — One release for the vocabulary and its tooling

Status: Accepted  
Date: 2026-11-23  
Supersedes: —  
Superseded by: —  

## Context

The repository now publishes the pipeline package beside the vocabulary (ADR 0043). ADR 0003 versions the content and
says every change bumps the version; it does not say what a change to tooling alone does, nor what a consumer of both
the vocabulary and the package pins. A consumer needs both to come from one state it can name.

## Decision

1. A release is one tag for everything in the repository: the vocabulary, the decision records and the pipeline
   package. The package has no tag or release of its own.
2. A change to the vocabulary bumps `ontology_version` in the same change (ADR 0003 rule 3). A change to tooling,
   records or documentation alone merges without a bump.
3. A release whose only changes since the previous one are tooling, records or documentation is a PATCH.
4. A consumer that uses the vocabulary and the package pins both at the same release tag on its release branch. On a
   working branch it may pin the package at a pushed commit or a pre-release until the release exists.
5. The changelog entry of a release says whether the vocabulary changed and whether a tooling change alters output or
   a consumer's configuration.
6. 4.0.1 is the first release that carries the package; it changes no term.

## Consequences

- The vocabulary and the tool that projects it always come from one commit; the fragments generated inside the package
  match the vocabulary they ship with.
- Tooling work lands on `master` without a release step, and several changes share one release.
- The version also moves when no term changed, so the number alone no longer says the content changed; the changelog does.
- A consumer waits for a release to take a tooling fix onto its release branch.
- The version does not tell whether a tooling change breaks a consumer's configuration; rule 5 puts that in the changelog.
- ADR 0003 rule 3 is narrowed to vocabulary changes; its rule 5 gains the same-tag requirement.

## Alternatives

- A separate version and tag for the package — two release trains and a pairing every consumer must get right.
- A bump with every tooling change — the number moves without a release and nothing a consumer pins changes.
- A commit pin on a consumer's release branch — a commit is not a release, and nothing keeps it reachable.

## Sources

- https://semver.org/ · a patch version for changes that add or remove nothing a consumer relies on · accessed 2026-11-08
- https://docs.astral.sh/uv/concepts/projects/dependencies/ · a package dependency pinned to a git tag or commit · accessed 2026-11-08
- https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/ · a release tag that cannot be moved · accessed 2026-11-08

# ADR 0003 — Versioning, releases and pinning

Status: Accepted  
Date: 2026-11-21  
Supersedes: —  
Superseded by: —  

Origin: Consolidates decisions taken between 2026-05 and 2026-11, before publication.

## Context

Consumers check documents against the vocabulary and generate artefacts from it, so a change can break them silently.
They need to know what kind of change a release carries and to hold a known version until they choose to move.

## Decision

1. The schema keeps two numbers: `schema_version`, an integer for the shape of a term record, and `ontology_version`, a
   Semantic Versioning 2.0.0 number for the content.
2. MAJOR: an id removed or renamed, a verb's meaning changed, a type or value dropped, a schema change that breaks a
   consumer's parser, a change of base IRI or licence. MINOR: additive terms, types, verbs or fields, and a retirement
   (the id and IRI stay, marked retired). PATCH: wording, comments, metadata.
3. Every change bumps `ontology_version` in the same change, with a release-history row; a change
   without a bump fails the checks.
4. A release is a tag `vX.Y.Z` on `master` with an immutable release carrying the source archive and its hash, later also
   the projections; tags cannot be updated or deleted. Pre-releases are tagged `vX.Y.Z-rc.N`.
5. Consumers pin a release: a vendored copy records version, tag, commit and archive hash; a package pins the tag;
   an artefact is pinned by digest; a linked-data consumer names the version IRI. A pre-release is
   pinned only on a working branch.
6. There is one vocabulary, edited in place here, never forked to be changed; consumers do not edit their copies.
7. The first public release is 4.0.0: no term changes, but a new location, a licence, minted IRIs and a pinning
   obligation make a new consumption contract.

## Consequences

- A consumer can tell from the version whether an upgrade can break its checks, and can prove which bytes it pinned.
- Every change is a release step; batching and release candidates keep the cost bearable.
- Retiring a term is MINOR because nothing a consumer holds disappears; renaming one is MAJOR because it does.
- A wrong release is corrected by a new one, never rewritten.
- A vendoring consumer must re-pin to receive a fix; that friction is intended.

## Alternatives

- A single version number — hides whether a parser or only the content needs attention.
- Branch or submodule tracking instead of pins — drifts silently; the hash of a release archive does not.
- Calendar versioning — says when, not what kind of change.

## Sources

- https://semver.org/ · Semantic Versioning 2.0.0 rules and pre-release precedence · accessed 2026-11-08
- https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/ · immutable releases · accessed 2026-11-08
- https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets · rulesets that restrict tag update and deletion · accessed 2026-11-21
- https://docs.astral.sh/uv/concepts/projects/dependencies/ · a package dependency pinned to a git tag · accessed 2026-11-08
- https://arxiv.org/pdf/2003.13084 · versioned vocabulary releases · accessed 2026-05-21
- https://www.w3.org/TR/owl2-syntax/#Ontology_IRI_and_Version_IRI · a version IRI identifies one version of an ontology · accessed 2026-11-21

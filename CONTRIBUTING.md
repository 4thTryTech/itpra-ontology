# Contributing

Thank you for helping keep this vocabulary precise. Everything below follows the decision records, chiefly
[ADR 0005](decisions/0005-decision-records-citations-and-the-writing-standard.md) and
[ADR 0006](decisions/0006-governance-and-contribution.md).

## What a change looks like

1. **One pull request carries the whole change**: the term records you add, amend or retire; the decision record that
   decides it (a new `decisions/NNNN-*.md` from [the template](decisions/0000-template.md); when it amends an earlier
   record's rule, that rule is restated in place and names the new record,
   [ADR 0049](decisions/0049-records-state-the-rules-as-they-stand.md)); and the `ontology_version` bump in
   `schema.yaml` with a changelog line.
2. **Cite the decision in the term**: `source: ADR NNNN`, or `ADR NNNN (amended by ADR MMMM)` when a later record changes
   an existing term. `ADR NNNN` always means a record in `decisions/`.
3. **Pick the right bump** ([ADR 0003](decisions/0003-versioning-releases-and-pinning.md)): PATCH for wording, MINOR for
   new terms, types, verbs or fields and for a retirement (the record stays, marked `retired`,
   [ADR 0048](decisions/0048-retirement.md)), MAJOR for anything that removes or renames an id, changes a
   verb's meaning or drops a value. A change to tooling, records or documentation alone needs no bump; it ships with
   the next release, a PATCH when nothing else changed
   ([ADR 0044](decisions/0044-one-release-for-the-vocabulary-and-its-tooling.md)).
4. **Backbone changes need a maintainer first**: a new verb, type, plane, quality attribute, journey group, governance
   construct, dimension value or service domain is discussed as a record before any diff.
5. **Sign off every commit** under the [Developer Certificate of Origin](https://developercertificate.org/) with
   `git commit -s`. No contributor licence agreement is required; contributions are accepted under the repository's
   licences ([ADR 0002](decisions/0002-licence-and-attribution.md)).

## What the vocabulary does not accept

- Product, vendor or tool names in any term; a function may name a standard, protocol or technique only where that is
  the behaviour itself ([ADR 0011](decisions/0011-the-function-layer.md)).
- Operating-model process vocabulary in a term; governance moments are expressed through the neutral constructs
  ([ADR 0015](decisions/0015-governance-constructs.md)).
- Requirements, specifications or scenario-specific terms: those belong to the consuming architecture
  ([ADR 0001](decisions/0001-purpose-scope-and-tier-neutrality.md)).
- Counts, history or narrative in a decision record: records state the rule, in the template's shape, under its
  length limits. `python tools/adr-lint.py --strict` tells you before CI does.

## Running the checks

```
python tools/ontology-lint.py              # the vocabulary, with the pipeline's core rules (tools/itpra-onto, itpra_onto.lint)
python tools/adr-lint.py --strict          # the decision records
python tools/check-version-bump.py --base origin/master   # a vocabulary change bumps ontology_version
python tools/check-links.py                # relative links resolve
python tools/publication-scan.py           # nothing refers to a private repository
python tools/publication-scan.py --root tools/itpra-onto   # nor does the pipeline's own tree
python -m unittest discover -s tests -v    # the tools' own tests
```

CI runs the same steps on every push and pull request (`.github/workflows/checks.yml`), and a second job runs the
pipeline under `tools/itpra-onto/` — generated fragments up to date, its tests, a reproducible build, SHACL clean:

```
uv sync --locked --project tools/itpra-onto
uv run --project tools/itpra-onto itpra-onto gen-enums --check
uv run --project tools/itpra-onto itpra-onto gen-prefixes --check
uv run --project tools/itpra-onto itpra-onto gen-verb-shapes --check
uv run --project tools/itpra-onto pytest -q tools/itpra-onto/tests
uv run --project tools/itpra-onto itpra-onto build --no-store && uv run --project tools/itpra-onto itpra-onto build --check
uv run --project tools/itpra-onto itpra-onto validate --json
uv run --project tools/itpra-onto itpra-onto parity && uv run --project tools/itpra-onto itpra-onto parity --fixtures
```

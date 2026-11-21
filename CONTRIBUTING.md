# Contributing

Thank you for helping keep this vocabulary precise. Everything below follows the decision records, chiefly
[ADR 0005](decisions/0005-decision-records-citations-and-the-writing-standard.md) and
[ADR 0006](decisions/0006-governance-and-contribution.md).

## What a change looks like

1. **One pull request carries the whole change**: the term records you add, amend or retire; the decision record that
   decides it (a new `decisions/NNNN-*.md` from [the template](decisions/0000-template.md), or an amendment recorded in
   a new record that names the one it amends); and the `ontology_version` bump in `schema.yaml` with a changelog line.
2. **Cite the decision in the term**: `source: ADR NNNN`, or `ADR NNNN (amended by ADR MMMM)` when a later record changes
   an existing term. `ADR NNNN` always means a record in `decisions/`.
3. **Pick the right bump** ([ADR 0003](decisions/0003-versioning-releases-and-pinning.md)): PATCH for wording, MINOR for
   new terms, types, verbs or fields and for a retirement, MAJOR for anything that removes or renames an id, changes a
   verb's meaning or drops a value.
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
python tools/ontology-lint.py              # schema, terms, verbs; every source: cites a record in decisions/
python tools/adr-lint.py --strict          # the decision records
python tools/check-version-bump.py --base origin/master   # a vocabulary change bumps ontology_version
python tools/check-links.py                # relative links resolve
python tools/publication-scan.py           # nothing refers to a private repository
python -m unittest discover -s tests -v    # the tools' own tests
```

CI runs the same six steps on every push and pull request (`.github/workflows/checks.yml`).

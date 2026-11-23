# `fixtures/requirements/` — fixtures for `shapes/requirements.ttl`

One fixture per shape-bearing rule id in `../../shapes/requirements.ttl`: `req-id-format`,
`req-qa-unresolved`, `req-statement-missing`, `req-target-unresolved`, `B-1` and `B-4` (see that file and
`../../shapes/REGISTER.md`'s `requirements` rows). These fixtures mutate a consumer's registry records, so
they need an `[overlay]`. One rule id in the same rows, `B-11`, deliberately has no shape and no fixture.

## B-4 — `met_by`/`verified_by` non-empty on every registry record: closed before emission *and* in the graph

Two mechanisms, deliberately:

1. `itpra_onto.authoring.AuthoringValidator.validate_registry_data` (behind `itpra-onto validate
   --authoring`) refuses an empty `met_by`: `Requirement.slot_usage.met_by.minimum_cardinality: 1` in
   `schema/itpra.linkml.yaml` becomes a JSON Schema `minItems: 1` on `/met_by`, and a synthetic FR with
   `met_by: []` reports `[] should be non-empty in /met_by`. The same holds for `verified_by`.
2. `emit.emit()` never calls `AuthoringValidator` (it uses `itpra_onto.authoring` only for the type→class
   dispatch), so a record that bypasses the authoring check — a hand-edited file, or a non-YAML authoring
   path — emits without error. `shapes/requirements.ttl` therefore carries
   `itpra-o:ReqMetByNonEmptyShape`/`itpra-o:ReqVerifiedByNonEmptyShape` (`sh:minCount 1` on
   `itpra-o:metBy`/`itpra-o:verifiedBy` per `itpra:REQUIREMENT`, `itpra-o:ruleId "B-4"`), and `B-4.yaml`
   proves it: a record with `met_by` emptied to `[]` raises exactly one Violation.

`B-4`'s mechanism in `REGISTER.md` is therefore `generated` + `core`.

## B-11 — `Meets` (markdown) ↔ `met_by` (registry) reciprocity: no shape, no fixture

The graph-side `itpra-o:meets` edges (`rules/40-requirement-meets.rq`) are `CONSTRUCT`ed directly from the
asserted `itpra-o:metBy` edges, subject and object swapped;
`tests/test_competency.py::test_meets_is_exactly_the_reverse_of_met_by` proves it. There is no independent
source for `meets` that could disagree with `metBy`, so a shape asserting the reciprocity could never fire
— it would be tautological, not a data check. The traceability check this rule id names — the `Meets:`
lines in a consumer's capability documents agreeing with its registry's `met_by:` — reads markdown, outside
anything a shape over the graph can see, and stays with the consumer (ADR 0042 D7). The same reasoning
leaves `B-14`–`B-17`, `B-20` and `B-21` (`REGISTER.md` Table B) without a fixture: they are pipeline-code
invariants proved once in `test_competency.py`, not authorable-content rules a fixture could break.

# Rule register — validation parity

Contract (ADR 0042 D1): **every** rule id of the consumer's linter maps to exactly one enforcement mechanism,
and every rule the RDF-projection shapes add *beyond* the linter is listed and marked **stricter than the
linter**. The shape files, their fixtures and `itpra-onto parity` build from this register; nothing here is
itself a shape, a fixture, or a schema change.

## Parity principle, and what the generated SHACL is (and is not)

- **The rule text wins** (ADR 0041 D1; ADR 0042 D6). Where a check (the consumer's linter, a hand-written
  shape) and a rule text (`schema.yaml`, a `schema/itpra.linkml.yaml` `itpra_verb` annotation, or a decision
  record) disagree, the rule text is authoritative and the check is wrong. This register cites, for every
  row, the rule text that authorises the mechanism — never the other way around.
- **`dist/schema/itpra.shacl.nt` (and `itpra.owl.nt`) are documentation of the *authoring* shape, not part
  of the projection's shapes** (ADR 0042 D2). They are generated straight from `schema/itpra.linkml.yaml` —
  the same schema `itpra-onto validate --authoring` checks the YAML against — and they describe the record
  shape the **YAML** must have, not the graph `itpra_onto.emit` actually publishes: no closed shapes, no
  knowledge of the `relates_to` pivot onto one predicate per verb, `xsd:string` where the emitted graph
  carries `@en`. Running pySHACL with them against `t1`/`req/*` produces tens of thousands of spurious
  violations. **Every shape this register routes to `core`/`sparql` is hand-written against the *emitted*
  graph**; the generated files play no part in `itpra-onto parity`. A mechanism of **`generated`** below
  means something different and narrower: the constraint is already fully closed **pre-emission** by the
  authoring schema, in a way that makes it structurally impossible for a violating record to ever become
  part of a graph in the first place (the emitter itself raises `EmitError` for the same defect) — so
  `itpra-onto parity` has nothing to compare for that id, and no shape file owes it a shape.
- **Shapes graph.** The projection's hand-written shapes live in a named graph `<graph_ns>shapes`
  (`itpra-onto.toml` `[iri] graph_path` + `shapes`).

## Table A — the 81 linter rule ids

**Count note.** The inventory is an AST-level extraction of every `err(...)`/`warn(...)` call's literal first
argument in the consumer's linter (`[overlay] linter_script`): 76 distinct ids at the first inventory (77
call sites, one id — `waiver-reason-missing` — used at two sites; exactly what the script's own docstring
rule-id table lists), plus two added since — `field-unknown` (a record field outside `schema.yaml`'s
`fields:`, or outside the registry record shape) and `req-link-malformed` (a `met_by`/`verified_by` that is
not a list) — making **78**; both are `python` rows in the A/C sub-table below. A `--json` run of the linter
over the live ontology does not change the count (it confirms the *live* ontology is clean; the id inventory
comes from reading the source, since some ids fire only on inputs outside the overlay).

Columns: **id** · **sev** (severity in the linter) · **check** (one line) · **family** (the 26-family
inventory of the linter's checks: `A1`–`A13` tier-A shared-ontology/registry, `B1`–`B13` tier-B manifest,
`C1`–`C2` content hygiene; "pre-A"/"pre-B" = a parse/shape guard prerequisite to a family, not itself one of
the 26) · **mechanism** (`generated` / `core` / `sparql` / `python`, reason — ADR 0042 D1) · **target
graph(s)** · **notes**.

### A/C — ontology term integrity, requirements registry, markdown scan (25 ids)

**`home`** says who implements the rule: `core` — `itpra_onto.lint`, the ontology's own lint, which a consumer's
linter imports and runs first; `consumer` — the consumer's linter alone (its registries and prose); `both` — each
for its own records (a term file and a registry file can each fail to parse, carry a non-mapping entry or an
unknown field). Without a consumer overlay, `itpra-onto parity` compares the ontology's own lint with the shapes
over the `core`/`both` rows that are comparable — `field-missing`, `id-pattern`, `target-unresolved`,
`function-derived-from` — and maps `type-unknown`, `verb-unknown` and `relates-to-malformed` to the emitter's
refusals; with an overlay the consumer's linter is compared over every comparable row.

| id | home | sev | check | family | mechanism | target | notes |
|---|---|---|---|---|---|---|---|
| `yaml-parse-error` | `both` | error | a term/schema YAML file failed to parse | pre-A | `python` — not a graph fact; `yaml.safe_load` fails inside the emitter first, so `itpra-onto build` cannot run and no graph exists to shape | n/a | guard, not one of the 26 named families |
| `termfile-not-list` | `core` | error | a term file's top level is not a list of records | pre-A | `python` — same: pre-graph file-shape guard | n/a | |
| `record-not-mapping` | `both` | error | a list entry in a term file is not a mapping | pre-A | `python` — same | n/a | |
| `field-missing` | `core` | error | required field (`id`/`term`/`type`/`definition`) absent or whitespace-only | A1 | `core` — `sh:minCount 1` on `skos:prefLabel` (`term`) and `skos:definition` (`definition`) per `Term` subject in `t1`/`req/*` | t1, req/* | `id`/`type` absence additionally crashes the emitter (`EmitError`) before a graph exists — doubly covered for those two sub-cases, but `term`/`definition` reach the graph fine if absent (the emitter omits the triple, no crash), so a real shape is still needed. **Presence only on both sides:** the linter treats a whitespace-only value as missing (the emitter already omitted it), and the shapes carry no `sh:maxCount` (two values on one subject is a duplicated record: B-12 on the graph, `id-duplicate` in the YAML) |
| `field-unknown` | `both` | error | a term record carries a field outside `schema.yaml` `fields:`, or a registry record one outside `{id, type, qa, statement, target, met_by, verified_by}` (the linter's `REGISTRY_FIELDS`) | pre-A | `python` — the emitter projects named fields only, so an unknown one never reaches a graph; also closed pre-emission by `validate --authoring` (closed mode) | n/a | added after the first inventory |
| `id-duplicate` | `core` | error | same id defined more than once | A3 | `python` (build-time), not a shape — SHACL has no native "no two distinct subjects share this literal" without a `SPARQL` aggregate, and once two colliding YAML records are emitted they skolemise onto the SAME IRI — the question is moot post-emission | n/a | |
| `id-pattern` | `core` | error | id does not match `schema.yaml`'s id pattern | A2 | `core` — `sh:pattern` on `dcterms:identifier` (the `id`) per `skos:Concept` in `t1`/`req/*` — the id survives emission unchanged as the IRI local name | t1, req/* | |
| `type-unknown` | `core` | error | `type` not in `schema.yaml`'s `types` | A4 | `generated` — the emitter raises `EmitError("...has type ..., which no Term subclass pins")` for an unrecognised/missing `type`; build fails before any graph exists. Construct: each subclass's `slot_usage: {type: {pattern: "^<Value>$"}}` + the generated `EntityTypeEnum` range on the `type` slot | n/a | no graph is reachable with this defect present |
| `relates-to-malformed` | `core` | error | a `relates_to` entry is not a mapping | pre-A (adjacent to A5/A6) | `core` — `RelatesTo` node shape (`rel`/`target` both required, `IRI`/literal kind) | t1, req/* | at the graph level this degenerates into the same shapes `target-unresolved` already needs, once `relates_to` is pivoted onto one predicate per verb; kept as its own row for parity, not a second independent shape |
| `verb-unknown` | `core` | error | `relates_to.rel` not a known verb | A5 | `generated` — the emitter raises `EmitError("relates_to verb ... is not a slot in the verbs subset")` for any `rel` outside the 17-verb `RelationshipVerbEnum` on a **term** record; build fails first. Construct: `RelatesTo.rel range: RelationshipVerbEnum` | n/a | **Correction:** "no graph is reachable" holds only for non-EntityType records. On an **EntityType** record the `relates_to` entries are meta-edges the emitter never projects, so an unknown verb there raises nothing and a graph IS built — that sub-case is `python`-only (the linter alone sees it). `itpra-onto parity` excludes such findings from the comparison and reports them (`parity.META_EDGE_RULE_IDS`). `fixtures/structural/verb-unknown.yaml` proves the emit-time guard on a Capability |
| `target-unresolved` | `core` | error | `relates_to.target` does not resolve | A6 | `core` — `sh:class skos:Concept` on the object of each term-carried verb's own predicate, once `relates_to` is pivoted; a dangling target carries no `rdf:type` triple, so `sh:class` fails. Plus one `sparql` shape under the same id for a target that names a **requirement** record: the linter resolves `relates_to` targets among term ids only | t1 | referential integrity is a property-shape range check. The verb's declared range (the `itpra_verb` `pairs`) is **B-22**, not this rule. **EntityType records:** a dangling meta-edge target is `python`-only — the emitter never projects meta-edges; `itpra-onto parity` excludes and reports those findings |
| `function-derived-from` | `core` | error | a `Function` record uses `derived_from` (ADR 0011) | A7 | `core` — `sh:targetClass Function` + `sh:maxCount 0` on `itpra-o:derivedFrom` | t1 | one predicate, one class, one cardinality bound — pure Core |
| `schema-types-missing` | `core` | warning | `schema.yaml` declares no `types` | pre-A | `python` — guards the linter's own input file, not a term/requirement record | n/a | |
| `req-file-missing` | `consumer` | warning | `functional.yaml`/`non-functional.yaml` not found | pre-A | `python` — filesystem fact, not a graph fact | n/a | |
| `req-file-malformed` | `consumer` | error | a registry file lacks a top-level `requirements` list | pre-A | `python` — pre-emission file-shape guard, same class as `yaml-parse-error` | n/a | a `requirements` value that is not a list is this id (the linter does not crash; the emitter raises `EmitError`), and a non-mapping entry is `record-not-mapping` |
| `req-id-format` | `consumer` | error | requirement id does not match the FR / NFR id pattern for its `type` | A8 | `core` — `sh:pattern` on `dcterms:identifier` per `FR`/`NFR` subclass in each `req/<X>` graph | req/* | the linter uses the same two patterns as the shapes (`FR` `^FR-[A-Z]+-[0-9]+$`, `NFR` `^NFR-[A-Z][A-Z_]*-[0-9]+$`, copied from `schema/itpra.linkml.yaml`, equality test-enforced), chosen by the record's `type` as the shapes choose by class |
| `req-link-malformed` | `consumer` | error | a `met_by`/`verified_by` value is not a list | pre-A | `python` — emit-time `EmitError` (`emit.check_requirement_record`), mapped in `itpra-onto parity` like `relates-to-malformed` (an `emit-error` finding on the same record); the linter does not iterate the characters of a scalar | n/a | added after the first inventory; `fixtures/structural/req-link-malformed.yaml` |
| `req-type-invalid` | `consumer` | error | requirement `type` is not `FR`/`NFR` | A9 (partial — see note) | `generated` — the emitter's `Requirement` dispatch raises `EmitError` for a `type` that pins to neither `FR` nor `NFR`; build fails first. Construct: `FR`/`NFR` `slot_usage: {requirement_type: {pattern: "^FR$"/"^NFR$"}}` | n/a | **A9's family text ("type is FR/NFR, consistent with the id prefix") is broader than any existing check**: neither the linter nor the schema cross-checks that an `FR-`-prefixed id actually carries `type: FR` (or the reverse). Not a rule id, only an unenforced reading of A9's prose — recorded as a gap, not created here |
| `req-qa-unresolved` | `consumer` | error | `NFR.qa` does not resolve to a `QualityAttribute` | A10 | `core` — `sh:class QualityAttribute` on the object of `itpra-o:categorizedAs` (the `qa` slot) | req/* | |
| `req-statement-missing` | `consumer` | error | requirement has no `statement` | A12 | `core` — `sh:minCount 1` on `itpra-o:statement` per `Requirement` subject | req/* | unlike `type-unknown`/`verb-unknown`, a missing `statement` does **not** crash emission (the triple is simply omitted), so this needs a real shape, not just `generated` |
| `req-target-unresolved` | `consumer` | warning | `met_by`/`verified_by` reference does not resolve | A13 | `sparql` — `sh:class` catches a genuine dangling reference, but the linter's **soft instance-prefix fallback** (`INSTANCE_PREFIXES`: `CAP`/`FUNC`/`SVC`/`PERSONA`/`JRN`/`WF`/`FR`/`NFR`/`ADR`/`OQ`) lets an unresolved-but-well-shaped id pass with only a warning — reproducing that fallback needs a `REGEX(STR(?target), ...)` test layered over the `sh:class` miss, which is `SHACL-SPARQL`, not Core | req/* | one shape (`requirements.ttl` `itpra-o:ReqTargetUnresolvedShape`) mirrors the linter exactly — untyped object AND local name not starting with an instance prefix (prefix list test-enforced equal to the linter's). No typed shape is filed under this id; typing is B-22 |
| `doc-idlike-unresolved` | `consumer` | warning | id-like token in markdown prose is not defined | C1 | `python` — scans prose outside fenced code blocks; not a graph fact | n/a | |
| `source-grammar` | `core` | error | a `source:` item names a record but is not `ADR NNNN` with an optional amended/extended tail (ADR 0005) | A14 | `python` — the emitter raises `SourceGrammarError` for the same item before any graph exists (the `B-13-emit-guard` fixture proves that side); the lint reports it on the record | n/a | an item carrying a URL is external and exempt |
| `source-adr-unresolved` | `core` | error | a cited `ADR NNNN` has no record under `decisions/` (ADR 0005) | A15 | `python` — decision records are files, not graph facts; B-13 checks only the citation node's shape | n/a | |
| `version-format` | `core` | error | `ontology_version` is not X.Y.Z, or `schema_version` is not an integer (ADR 0003) | pre-A | `python` — a fact of `schema.yaml`, read before emission | n/a | |

**C2 (banned-synonym scan) has no rule id and is not classified.** `schema.yaml` documents the `deprecated`
field as not machine-enforced: `level`/`feature` and their kin occur legitimately in dozens of definitions,
so the check was never implementable as written and no code path — linter or shape — exists or is owed
for it.

### B — derived-package manifest gates (56 ids; the consumer's linter keeps them as `python`, outside the graph — ADR 0042 D7)

**All 56 are `python`.** The projection covers the vocabulary and the consumer's requirement registries
(ADR 0041 D3); a consumer's derived-package manifests stay outside the graph (ADR 0042 D7). None of these 56
ids has a graph to check against — there is no `Manifest` LinkML class, no manifest graph, and no rule
targeting one; `validate_scenario()` in the consumer's linter remains the only mechanism. Target: n/a (no
graph). Grouped here by the B1–B13 families (two ids are a pre-B structural guard, the manifest-file
equivalent of `yaml-parse-error`):

| family | rule ids | sev (error unless noted) |
|---|---|---|
| pre-B (manifest file shape) | `package-manifest-missing`, `package-not-mapping` | error |
| B1 tier enum | `package-tier-invalid` | error |
| B2 participating service domains ≥1, resolve | `package-sds-missing`, `package-sd-unresolved` | error |
| B3 coverage-areas structural rules | `coverage-areas-malformed`, `coverage-area-entry-malformed`, `coverage-area-id-missing`, `coverage-area-duplicate`, `coverage-area-label-missing`, `coverage-area-baseline-id`, `coverage-area-driver-invalid`, `coverage-area-sds-missing`, `coverage-area-sd-unresolved`, `coverage-area-sd-out-of-scope`, `coverage-area-fallback-type`, `coverage-area-fallback-reachability` (warn), `coverage-areas-baseline-count` | error except noted |
| B4 exactly-one operating_model | `package-operating-model-invalid` | error |
| B5 capabilities ≥1, derived_from/required_functions resolve | `package-capabilities-missing`, `capability-derived-from-missing`, `capability-derived-from-unresolved`, `capability-functions-missing`, `capability-function-unresolved` | error |
| B6 per_area_functions ⊆ required_functions, needs coverage_areas | `capability-per-area-not-required`, `capability-per-area-unresolved`, `package-per-area-no-coverage-areas` | error |
| B7 requirement target/waiver, met_by present+resolves | `requirement-target-missing`, `requirement-waiver-format`, `requirement-met-by-missing`, `requirement-met-by-unresolved` | error |
| B8 tool bindings | `package-tools-missing`, `tool-functions-missing`, `tool-function-unresolved`, `tool-covers-malformed`, `tool-covers-function-mismatch`, `tool-covers-area-unresolved`, `tool-adr-missing` (warn) | error except noted |
| B9 in-isolation coverage | `t3-coverage-gap-function` | error |
| B10 strict per-area coverage | `t3-coverage-gap-per-area` | error |
| B11 per-area-by-construction (boundary-governed) | `t3-coverage-gap-boundary` | error |
| B12 derived↔parent gap comparison | `t3-parent-not-found` (warn), `t3-gap-capability`, `t3-gap-function`, `t3-gap-requirement`, `t3-capability-unmatched`, `t3-function-extra` (warn), `t3-requirement-local` (warn), `t3-coverage-area-local` (warn), `t3-gap-per-area` | error except noted |
| B13 waiver-record shape validation | `waivers-malformed`, `waiver-id-missing`, `waivers-entry-malformed`, `waiver-reason-missing` (warn), `waiver-coverage-malformed`, `waiver-coverage-reason-missing` (warn) | error except noted |

Family-id counts: pre-B 2, B1 1, B2 2, B3 13, B4 1, B5 5, B6 3, B7 4, B8 7, B9 1, B10 1, B11 1, B12 9, B13 6
— **total 56**, matching the linter docstring's manifest-rule block exactly. B7's family text names only
"requirement target non-null or a waiver"; the code's adequacy check for the *same* `requirements:` block
also requires `met_by` to be present and resolvable in one pass, so `requirement-met-by-missing`/
`requirement-met-by-unresolved` are folded into B7 here rather than left unfamilied.

## Table B — rules the shapes add that the linter lacks (all marked **stricter than the linter**, plus every competency invariant `test_competency.py` proves that is not yet a rule anywhere)

Sourced to the rule text that authorises each one — never invented here (the register adds no ontology term
or rule; a candidate needing a ruling is flagged, not bound). ADR 0042 D3: shapes may be stricter than the
linter; a declared-but-unstated minimum is a warning.

| # | Rule | Source | Mechanism | Status |
|---|---|---|---|---|
| B-1 | An NFR id embeds its `qa` (`NFR-<QA>-<n>` / `NFR-<X>_<QA>-<n>`) | `schema.yaml` `external_registries.requirements.rules` (checked by the RDF shapes, not by the linter); ADR 0004 | `sparql` — two-hop (`$this qa ?q . ?q id ?qid`) + a same-string-family containment test between two different nodes' literals | **new** — the linter has no id at all for this |
| B-2 | `grouped_by` ≥1 per `Capability`/`Domain`/`Journey` | `schema/itpra.linkml.yaml`'s `itpra_verb` `cardinality` for `grouped_by` (`{min:1,max:1}` on each); already enforced pre-emission by LinkML's `has_member` on the authoring schema | `core` — `sh:minCount 1` on `itpra-o:groupedBy` in `t1`, restating the same declared cardinality at the graph level (needed for `itpra-onto parity`, since the generated authoring SHACL doesn't validate the graph) | **stricter than the linter** — the linter has no "every Capability/Domain/Journey has a grouped_by" check at all |
| B-3 | `grouped_by` ≤1 per `Capability`/`Domain`/`Journey` | Same `itpra_verb` annotation, `cardinality` field; the LinkML schema's own comment at `Capability.relates_to.has_member` says "at most one: itpra_verb annotation, enforced by the shapes" | `core` — `sh:maxCount 1` on `itpra-o:groupedBy` | **stricter than the linter AND than the current authoring schema** — neither checks the upper bound today |
| B-4 | `met_by`/`verified_by` non-empty (≥1) on every registry record | the consumer's traceability rule — every requirement is met by ≥1 capability (ADR 0042 D7); `Requirement.met_by`/`verified_by` `slot_usage: {minimum_cardinality: 1}` in `schema/itpra.linkml.yaml` | `generated` + `core` — closed pre-emission (an empty list fails `validate --authoring`) **and** a graph shape: the emitter does not run the authoring validator, so an empty list would otherwise reach the graph unchecked. `requirements.ttl`'s `itpra-o:ReqMetByNonEmptyShape`/`itpra-o:ReqVerifiedByNonEmptyShape` (`sh:minCount 1` on `itpra-o:metBy`/`itpra-o:verifiedBy` per `itpra:REQUIREMENT`) close that gap; `fixtures/requirements/B-4.yaml` proves it | **stricter than the linter** — the linter iterates `for ref in r.get(link_field) or []`, so an **empty** `met_by`/`verified_by` list raises nothing at all; only per-reference resolution is checked (`req-target-unresolved`), never list non-emptiness. The graph shape closes the gap the pre-emission-only closure left (`fixtures/requirements/README.md`) |
| B-5 | `consumed_by` ≥1 per `Capability`/`Journey` | ADR 0042 D3: a minimum the data satisfies but nothing declares (`consumed_by` ≥1 on Capability and Journey) | `core` — `sh:minCount 1` on `itpra-o:consumedBy` (`structural.ttl`'s `itpra-o:ConsumedByMinCountShape`) | **built as `sh:Warning`** (ADR 0042 D3: advisory) — the `itpra_verb` annotation's own `cardinality: []` is deliberately empty, so this stays advisory rather than a linter-parity `sh:Violation`; `fixtures/structural/B-5.yaml` proves it fires |
| B-6 | `realized_in` exactly 1 per `Workflow` | Same ADR 0042 D3 case (a minimum nothing declares) | `core` — `sh:minCount 1`/`sh:maxCount 1` on `itpra-o:realizedIn` (`structural.ttl`'s `itpra-o:RealizedInExactlyOneShape`) | **built as `sh:Warning`** (ADR 0042 D3: advisory) — same reasoning as B-5; `cardinality: []` is empty; `fixtures/structural/B-6.yaml` proves it fires |
| B-7 | `depends_on` ≥1 per `Journey` | Same ADR 0042 D3 case | `core` — `sh:minCount 1` on `itpra-o:dependsOn` (`structural.ttl`'s `itpra-o:DependsOnMinCountShape`) | **built as `sh:Warning`** (ADR 0042 D3: advisory) — same reasoning; `fixtures/structural/B-7.yaml` proves it fires |
| B-8 | No `skos:altLabel` equals its own subject's `skos:prefLabel`, case-insensitively | ADR 0007 (an alias never equals the term's own label, case-insensitively) | `sparql` — `FILTER(LCASE(?alt) = LCASE(?pref))` between two properties of the **same** subject; SHACL Core's `sh:disjoint` compares property values by exact RDF-term equality only, not case-folded | **new** — the linter has zero SKOS label-collision checks |
| B-9 | A term's alias equals a **different** record's own `prefLabel` | (none — SKOS permits it) | — | **no rule, by design.** ADR 0007 forbids only a term's alias duplicating **its own** `prefLabel` (self-collision); a cross-term collision is ordinary controlled-vocabulary homonymy (a word legitimately reused as one term's alternate label and another's preferred one) and nothing in ADR 0007 or the linter forbids it. Not created here. If a future record wants a heuristic: `?a skos:altLabel ?l . ?b skos:prefLabel ?l . FILTER(?a != ?b)` at `warn` severity |
| B-10 | `source` grammar (`ADR NNNN`, optional amend/extend tail, or an external citation) | ADR 0005 (the `source:` grammar) | `python` (emit-time) — `emit.parse_source` raises `SourceGrammarError` naming the record id and the offending item; a violating record can never reach the graph, the same `EmitError`-class reasoning as `type-unknown`/`verb-unknown` | **enforced at emit time, not a shape** — recorded here so the mechanism is not left implicit |
| B-11 | `Meets` (markdown) ↔ `met_by` (registry) reciprocity | a consumer's traceability check (ADR 0042 D7) | `python` — the consumer's traceability check parses the `Meets:` lines of its **markdown** capability documents; not a graph fact | **stays with the consumer.** The graph-side `itpra-o:meets` reverse link (`rules/40-requirement-meets.rq`) is available, and `test_competency.py::test_meets_is_exactly_the_reverse_of_met_by` proves it — but that reciprocity is **true by construction** of the `CONSTRUCT` rule itself (the rule literally builds `meets` as the reverse of `metBy`); a shape re-asserting it would be tautological, not a data check. `test-only` |
| B-12 | Exactly one `itpra-o:authoringFile` per subject in `t1`/`req/<X>` | ADR 0043 D3 (provenance: every record names the file it was authored in); `test_competency.py::test_every_subject_has_exactly_one_existing_authoring_file` (CQ12) | `core` for the cardinality half — `sh:minCount 1` + `sh:maxCount 1` on `itpra-o:authoringFile` per subject; the **file-exists-on-disk** half stays `python`/`test-only` (SHACL cannot stat the filesystem) | **new** — an obligation the RDF projection carries that the linter has no analogue for at all (the linter validates YAML files it already has open, never "does this path exist as a separate check") |
| B-13 | Every `itpra-o:decidedIn` object is an `ADR-NNNN` node, four digits | `test_competency.py::test_every_decided_in_object_is_a_four_digit_adr_node` (CQ11); the shape follows directly from B-10's `source` grammar once `decidedIn` links exist in the graph | `sparql` — `FILTER(REGEX(STR(?adr), "ADR-[0-9]{4}$"))` on the local name of an IRI object; SHACL Core patterns match string **literals**, not IRI local names, so this needs SPARQL | **new** — `decidedIn` is a projection-only construct; the linter's `source` check is a free-text scan, not a typed-node check |
| B-14 | The `inferred` graph mints only schema-pre-declared derived vocabulary | `test_competency.py::test_inferred_graph_only_uses_schema_declared_derived_vocabulary` (CQ13) | `test-only` | Guards the **pipeline's own code discipline** (the rules engine must only mint vocabulary `emit.py` already declared with an `rdfs:comment` starting "derived by rule") — no authored YAML content can violate this; already proven in `test_competency.py` |
| B-15 | No blank nodes anywhere in the store | ADR 0041 D2 ("no blank nodes"); `test_competency.py::test_no_blank_nodes_anywhere` (CQ14) | `test-only`, optional `core` defence in depth (`sh:nodeKind sh:IRI` sweep) | Same reasoning as B-14 — a blank node can only be introduced by the emitter/rules code itself, not by content |
| B-16 | The default (unnamed) graph is empty | `test_competency.py::test_default_graph_is_empty` (CQ14) | `test-only` | Same reasoning |
| B-17 | Per-type instance counts in `t1` equal the YAML record counts | `test_competency.py::test_type_counts_match_the_yaml_records` (CQ1) | `test-only` | Positive control, not an authorable content rule |
| B-18 | Every `Function` has ≥1 `itpra-o:inDomain` (inferred) | `test_competency.py::test_function_in_domain_is_a_multiset_not_a_function` (CQ2) | `core`, defence in depth on `inferred` | Logically implied by `supports` ≥1 (A-tier, already required) + `grouped_by` on the supported Capability; a direct shape on the **derived** edge catches a rules-engine regression, not just a content defect |
| B-19 | Every `Capability` has exactly one `inPlane` and one `inServiceDomain` (inferred) | `test_competency.py::test_every_capability_has_exactly_one_plane_and_service_domain` (CQ3) | `core`, defence in depth on `inferred` | Same reasoning as B-18 |
| B-20 | The boundary-governed function set (rules-derived) equals the linter's own `_boundary_governed_functions()` helper | `test_competency.py::test_boundary_governed_function_set_equals_the_linter_helper` (CQ4) | `test-only` | Pipeline-code parity check (rules engine vs. linter helper), not a content rule; the underlying `governs` edges are already covered by `target-unresolved` (A6) |
| B-21 | Requirement counts per `req/<X>` graph equal that registry's record counts | `test_competency.py::test_requirement_counts_per_sub_project` (CQ6) | `test-only` | Positive control |

**Rows minted by the `structural`/`crossfield` shape files themselves:**

| # | Rule | Source | Mechanism | Status |
|---|---|---|---|---|
| B-8-pref-label-unique | A subject carries more than one `skos:prefLabel` per language tag | SKOS integrity condition S14 (a controlled-vocabulary norm, not a decision record); named after `crossfield.ttl`'s own docstring reference (CQ19, "duplicate pref labels") | `sparql` — same-subject cross-value comparison (`$this skos:prefLabel ?value . $this skos:prefLabel ?other . FILTER(?value != ?other && LANG(?value) = LANG(?other))`); SHACL Core has no native same-property-value-collision check | **new** — the linter has no SKOS label-uniqueness check. Built in `crossfield.ttl` (`itpra-o:PrefLabelUniqueShape`); defence in depth, proven by direct quad injection in `test_shapes_crossfield.py` (no authoring-YAML mutation can produce two `skos:prefLabel`s on one subject — `term` is a scalar field); `fixtures/crossfield/B-8-pref-label-unique.yaml` is a `count: 0` clean-case fixture documenting the nearest a mutation can get |
| B-3-belongs-to-service-domain | `belongs_to_service_domain` exactly 1 on `Domain`; at most 1 on every other term | `schema/itpra.linkml.yaml`'s `belongs_to_service_domain` `itpra_verb` `cardinality` list: `{subject: Domain, min:1, max:1}`, `{subject: Term, min:0, max:1}` — the same declared-cardinality mechanism that authorises the B-2/B-3 rows (`grouped_by`) | `core` — `sh:minCount 1`/`sh:maxCount 1` on `itpra-o:belongsToServiceDomain` for `itpra:DOMAIN` (`itpra-o:BelongsToServiceDomainDomainShape`); `sh:maxCount 1` for every other term class (`itpra-o:BelongsToServiceDomainTermMaxShape`) | **stricter than the linter** — no linter analogue restates this cardinality at the graph level. Built in `structural.ttl`, named in the family of B-3 (same declared-cardinality-at-the-graph-level pattern); `fixtures/structural/B-3-belongs-to-service-domain.yaml` proves the Domain arm |
| B-2-supports | `supports` ≥1 per `Function` | `schema/itpra.linkml.yaml`'s `supports` `itpra_verb` `cardinality`: `{subject: Function, min:1, max: null}` — the same declared-cardinality mechanism that authorises the B-2 row (`grouped_by`) | `core` — `sh:minCount 1` on `itpra-o:supports` for `itpra:FUNCTION` (`itpra-o:SupportsMinCountShape`) | **stricter than the linter** — no linter analogue. Built in `structural.ttl`, named in the family of B-2. **Causally coupled to B-18**: `itpra-o:inDomain` is entirely derived from `itpra-o:supports` (`rules/30-function-in-domain.rq`), so a Function with zero `supports` edges always has zero `inDomain` edges too, on the SAME focus — no isolated count-1 fixture is shippable (`assert_fixture`'s no-cascade check would reject it). `fixtures/structural/B-2-supports.yaml` is a `count: 0` clean-case fixture instead, proving the shape does not misfire on a partial (non-zeroing) mutation |

**Rows added by the mutation review of the shapes:**

| # | Rule | Source | Mechanism | Status |
|---|---|---|---|---|
| B-22 | A verb edge whose object is a resolved record must have a (subject class, object class) among the verb's **allowed pairs** | `schema/itpra.linkml.yaml` — every `verbs`-subset slot's `itpra_verb` annotation, `pairs` = "the ALLOWED (subject, object) combinations"; the annotations are governing rule text (ADR 0008: per-verb domain, range and cardinality live there; ADR 0041 D1) | `sparql`, **generated** from the annotations — `itpra-onto gen-verb-shapes` writes `shapes/generated/verb-pairs.ttl` (one `sh:NodeShape` per verb, `sh:targetSubjectsOf` the verb's predicate; `--check` fails when stale). Membership test over each node's record classes (a record is also `skos:Concept`); a dangling object is left to `target-unresolved`/`req-target-unresolved`; a pair naming no record class (`ADR`, `SERVICE`) matches nothing and is listed in the file header | **stricter than the linter** (the linter has no domain/range check). `sh:Violation`. Zero findings on the real tree at 3.16.0. Fixtures: `fixtures/structural/B-22-journey-grouped-by-persona.yaml`, `B-22-capability-belongs-to-service-domain.yaml`, `B-22-consumed-by-function.yaml`, `B-22-met-by-function.yaml`. Co-fires by construction with `function-derived-from` (derived_from's pairs allow only (Capability, Capability)) — that fixture declares `cofires: [B-22]` |
| B-23 | A term's `deprecated` (banned-label) list contains the term's own `term` | (none — `schema.yaml` `fields.deprecated` is not machine-enforced: the words occur legitimately elsewhere) | — | **no rule.** The case projects silently (the label becomes both `skos:prefLabel` and the `skos:hiddenLabel` sub-property `bannedLabel`). SKOS S13 (prefLabel/altLabel/hiddenLabel pairwise disjoint) would forbid it, but `bannedLabel` is only declared a sub-property of `skos:hiddenLabel`, and no rule text binds S13 here. Recorded, not built |
| B-24 | The `<X>` in an `NFR-<X>_<QA>-<n>` id names the owning registry | (none — `schema.yaml` `id.conventions.requirement_NFR` states the form, not that `<X>` must equal the owning registry) | — | **candidate, not built** (`NFR-ZZZ_<QA>-<n>` in any registry passes the linter and every shape, B-1 included). Needs a ruling that `<X>` is bound to the registry before a shape (`sparql`, comparing the id's segment with the `req/<X>` graph or `authoringFile`) can be written |

**Note on proof style.** `B-13` and `B-8-pref-label-unique` are defence in depth: the defect they catch can
only be produced by injecting quads directly into an emitted dataset, bypassing the emitter entirely — no
authoring-YAML mutation can reach it — so each is proven by direct quad injection in its shape file's test
module, and each additionally carries a `count: 0` clean-case fixture documenting the nearest an authoring
mutation can get without tripping the rule. `B-2-supports` carries a `count: 0` clean-case fixture for a
different reason (causal coupling with B-18 on the same focus, not defence in depth — see its own row
above): a genuine zeroing mutation CAN fire it, just never in isolation.

**Erratum: `relates-to-malformed`'s mechanism (Table A, pre-A) is corrected here, not in that row.** Table
A above still reads `core` — "`RelatesTo` node shape (`rel`/`target` both required, `IRI`/literal kind)" —
describing a shape that was never built. The rule is instead closed at **emit time**: `emit.py`'s
`_verb_edges` raises `EmitError` naming the record id and the offending `relates_to` entry when it is not a
mapping, or is missing `rel`/`target` (rather than an uncaught `TypeError`/`KeyError`). **Mechanism is
`python` (emit-time `EmitError`), not `core`** — the same class of guard as `type-unknown`/`verb-unknown`
(Table A's own `generated` rows), grouped here as `python` rather than `generated` since it is enforced by a
plain `raise`, not by a LinkML-generated pattern/range constraint. `fixtures/structural/relates-to-malformed.yaml`
proves it, with `rule: emit-error` (the same synthetic finding id every emit-time guard's fixture uses), not
`rule: relates-to-malformed` (the id was never a `sh:targetClass`/`itpra-o:ruleId` in any shape file, so
there is nothing for a fixture to name it against).

**Table B counts:** 27 rows. **13 stricter than the linter**, every one with a shape (12 hand-written +
B-22, generated); **3 `sh:Warning`** (B-5, B-6, B-7); **2 "no rule"** (B-9 by design, B-23 not
machine-enforced by rule text); **1 candidate, not built** (B-24); **1 enforced elsewhere** (B-10,
emit-time); **7 test-only** (B-11, B-14, B-15, B-16, B-17, B-20, B-21). 13 + 3 + 2 + 1 + 1 + 7 = 27.
B-18/B-19 count as stricter only in the narrow "no linter analogue on the derived graph" sense — see their
own rows.

## Table C — severity mapping

| Linter severity | Shape severity | Rule |
|---|---|---|
| `error` (`err(...)`, exit 1) | `sh:Violation` | default for every `core`/`sparql` row above |
| `warning` (`warn(...)`, exit 0) | `sh:Warning` | `req-target-unresolved` (A13); every `(warn)`-marked tier-B id (outside the graph) |
| `error` (emit-time `EmitError`) | `emit-error` finding, `sh:Violation` | `itpra-onto validate`/`parity` report an input the emitter refuses as a synthetic `emit-error` finding (on the record the error names; message `"<ErrorClass>: …"`) and exit 1 |

No row in Table A changes severity from what the linter already assigns. **New rows in Table B are assigned
severity here, since they have no linter row to inherit from:**

| Rule | Shape severity | Reason |
|---|---|---|
| B-1 NFR-id-embeds-qa | `sh:Violation` | `schema.yaml` states it as binding rule text, not a hint |
| B-2 `grouped_by` ≥1 | `sh:Violation` | sibling declared cardinalities (`supports`, `met_by`) are errors; a missing `grouped_by` breaks the plane/service-domain roll-up rules outright |
| B-3 `grouped_by` ≤1 | `sh:Violation` | same reasoning — a second `grouped_by` would silently corrupt the roll-up rules (`10-capability-in-plane.rq` etc.), which assume exactly one |
| B-8 alt-label self-collision | `sh:Violation` | ADR 0007 treats a self-duplicating alias as a defect to remove, not tolerated variance |
| B-12 authoringFile cardinality | `sh:Violation` | zero or two-or-more `authoringFile` triples on a subject indicates the **emitter itself** is broken, not an authoring choice |
| B-13 decidedIn node shape | `sh:Violation` | same — a malformed `decidedIn` object indicates emitter/parser corruption, not an authoring choice |
| B-2-supports `supports` ≥1 per Function | `sh:Violation` | a declared cardinality (`supports` `{Function, min 1}`), like B-2 |
| B-3-belongs-to-service-domain | `sh:Violation` | a declared cardinality (`belongs_to_service_domain` `{Domain, 1..1}`, `{Term, 0..1}`), like B-3 |
| B-4 `met_by`/`verified_by` ≥1 | `sh:Violation` | declared `minimum_cardinality: 1`; an empty list breaks the consumer's traceability (ADR 0042 D7) |
| B-8-pref-label-unique | `sh:Violation` | SKOS S14 is an integrity condition, not a preference |
| B-18 `inDomain` ≥1 (inferred) | `sh:Violation` | a missing derived edge means the rules engine regressed |
| B-19 `inPlane`/`inServiceDomain` exactly 1 (inferred) | `sh:Violation` | same |
| B-22 verb allowed pairs (generated) | `sh:Violation` | the `itpra_verb` `pairs` are governing rule text (ADR 0008), not a hint |
| B-5/B-6/B-7 candidate minimums | `sh:Warning` | ADR 0042 D3: advisory — no declared cardinality (`cardinality: []`) |
| B-9, B-10, B-11, B-14–B-17, B-20, B-21, B-23, B-24 | n/a | no shape (see their own rows) |

## Shape files and their fixtures

Exactly three hand-written shape files with disjoint ownership (ADR 0042 D2), each with its own fixture
directory and one deliberately broken record per rule (`fixtures/<file>/<rule-id>.yaml` — a wrong type, a
dangling target, a duplicate id, a second `grouped_by`, …; clean data must pass every shape file unmodified;
ADR 0042 D4). Shapes target `t1`, `req/*`, and (for B-18/B-19) `inferred`; the assembled shapes graph is
`<graph_ns>shapes` (see above). Only rows whose mechanism is `core` or `sparql` get a shape — `generated` and
`python` rows need no file.

### `structural` (SHACL **Core**) — `shapes/structural.ttl`, `fixtures/structural/`

Targets: `t1`, `inferred`. **14 distinct `itpra-o:ruleId` values** in `structural.ttl` **plus
`relates-to-malformed`**, which folds into the SAME shape as `target-unresolved` — it was never its own
separate shape node, so it contributes no distinct id of its own (its mechanism is `python`/emit-time
`EmitError`, not `core` — see the "Erratum" note above):

`field-missing` · `id-pattern` · `relates-to-malformed` (folds into `target-unresolved`, no distinct id) ·
`target-unresolved` · `function-derived-from` · B-2 (`grouped_by` ≥1) · B-3 (`grouped_by` ≤1) · B-12
(authoringFile cardinality — spans `t1` **and** `req/*`, kept here as a generic per-subject shape rather
than a registry-domain one) · B-18 (`inDomain` ≥1, `inferred`) · B-19 (`inPlane`/`inServiceDomain` exactly
1, `inferred`) — 9 linter-parity and Table B ids — plus **B-5, B-6, B-7** (`sh:Warning`) plus
**B-3-belongs-to-service-domain** (`belongs_to_service_domain` cardinality, named in the family of B-3) and
**B-2-supports** (`supports` ≥1 per Function, named in the family of B-2; causally coupled to B-18) —
9 + 3 + 2 = 14.

### `crossfield` (SHACL-**SPARQL**) — `shapes/crossfield.ttl`, `fixtures/crossfield/`

Targets: `t1`, `req/*`. General graph-wide checks that are not registry-domain-specific (label integrity,
node shape of a projection-only construct). 3 ids:

B-8 (alt-label self-collision) · B-8-pref-label-unique (at most one `skos:prefLabel` per language tag per
subject, SKOS S14) · B-13 (decidedIn node shape)

### `requirements` (registry and traceability shapes; mixed Core/SPARQL — the file is domain-scoped, not
mechanism-scoped, unlike the two above) — `shapes/requirements.ttl`, `fixtures/requirements/`

Targets: `req/*`. 6 shape-bearing rule ids, plus 1 documented-no-shape item the file's fixture README
explains rather than silently omits:

Shape-bearing: `req-id-format` (core) · `req-qa-unresolved` (core) · `req-statement-missing` (core) ·
`req-target-unresolved` (sparql — the soft-fallback case; ONE shape mirroring the linter, typing is B-22) ·
B-1 (NFR-id-embeds-qa, sparql) · B-4 (met_by/verified_by non-empty; `generated` **+** `core`)

Documented, no shape needed: B-11 (Meets↔met_by — the consumer's check; the graph-side reciprocal is
tautological)

### `shapes/generated/` — owned by the generator, not a hand-written file

`shapes/generated/verb-pairs.ttl` is written by `itpra-onto gen-verb-shapes` from the `itpra_verb`
annotations and checked by `gen-verb-shapes --check`; it is never edited by hand (regenerate instead).
`itpra_onto.shacl.load_shapes` loads `shapes/generated/*.ttl` after the hand-written files. 1 distinct rule
id: **B-22** (17 shapes, one per verb). Its fixtures live in `fixtures/structural/B-22-*.yaml`.

## Counts

Recomputed from the files:

- **Total linter rule ids: 81** — 25 A/C ids + 56 tier-B ids.
- **Table A 'A/C' sub-table rows:** 25 (`itpra-onto parity` fails if the table's row count differs). By `home`: `core` 14, `both` 3, `consumer` 8 — 17 ids are `itpra_onto.lint`'s (`CORE_RULE_IDS`).
- **Per mechanism (81 ids), with the `relates-to-malformed` erratum applied:** `core` **7** (`field-missing`,
  `id-pattern`, `target-unresolved`, `function-derived-from`, `req-id-format`, `req-qa-unresolved`,
  `req-statement-missing`) · `sparql` **1** (`req-target-unresolved`) · `generated` **3** (`type-unknown`,
  `verb-unknown`, `req-type-invalid`) · `python` **70** (14 A/C ids — `yaml-parse-error`, `termfile-not-list`,
  `record-not-mapping`, `field-unknown`, `id-duplicate`, `relates-to-malformed`, `schema-types-missing`,
  `req-file-missing`, `req-file-malformed`, `req-link-malformed`, `doc-idlike-unresolved`, `source-grammar`,
  `source-adr-unresolved`, `version-format` — + 56 tier-B).
  **7 + 1 + 3 + 70 = 81.** Comparable in `itpra-onto parity`: the 8 `core`/`sparql` ids. Emit-time mapped:
  the 3 `generated` ids + `relates-to-malformed` + `req-link-malformed` (5). Outside the comparison: the 12
  other `python` A/C ids.
- **Table B rows: 27** (see the Table B counts paragraph): 13 stricter, 3 warning, 2 no rule, 1 candidate,
  1 enforced elsewhere, 7 test-only.
- **Distinct `itpra-o:ruleId` values in the loaded shapes: 24** — `structural` 14 (the requirement-target
  shape carries the existing `target-unresolved` id) · `crossfield` 3 · `requirements` 6 · `generated` 1
  (B-22). `itpra-onto parity` checks at run time that every comparable id is among them and that every one
  of them is a Table A or Table B id.

# Rule register — validation parity

Contract (ADR 0042 D1): **every** rule id of the linter (`itpra_onto.lint`) maps to exactly one enforcement
mechanism, and every rule the RDF-projection shapes add *beyond* the linter is listed and marked **stricter
than the linter**. The shape files, their fixtures and `itpra-onto parity` build from this register; nothing
here is itself a shape, a fixture, or a schema change.

## Parity principle, and what the generated SHACL is (and is not)

- **The rule text wins** (ADR 0041 D1; ADR 0042 D6). Where a check (the linter, a hand-written shape) and a
  rule text (`schema.yaml`, a `schema/itpra.linkml.yaml` `itpra_verb` annotation, or a decision record)
  disagree, the rule text is authoritative and the check is wrong. This register cites, for every row, the
  rule text that authorises the mechanism — never the other way around.
- **`dist/schema/itpra.shacl.nt` (and `itpra.owl.nt`) are documentation of the *authoring* shape, not part
  of the projection's shapes** (ADR 0042 D2). They are generated straight from `schema/itpra.linkml.yaml` —
  the same schema `itpra-onto validate --authoring` checks the YAML against — and they describe the record
  shape the **YAML** must have, not the graph `itpra_onto.emit` actually publishes: no closed shapes, no
  knowledge of the `relates_to` pivot onto one predicate per verb, `xsd:string` where the emitted graph
  carries `@en`. Running pySHACL with them against `t1` produces tens of thousands of spurious violations.
  **Every shape this register routes to `core`/`sparql` is hand-written against the *emitted* graph**; the
  generated files play no part in `itpra-onto parity`.
- **Shapes graph.** The projection's shapes live in a named graph `<graph_ns>shapes` (`itpra-onto.toml`
  `[iri] graph_path` + `shapes`).

## Table A — the linter's rule ids

Columns: **id** · **sev** (severity in the linter) · **check** (one line) · **family** (`A1`–`A16`, the
linter's check families; "pre-A" = a parse or shape guard that precedes them) · **mechanism** · **target
graph** · **notes**.

Mechanisms (ADR 0042 D1): `core` — a SHACL Core shape; `sparql` — a SHACL-SPARQL shape; `generated` — closed
before emission by the authoring schema, so the emitter refuses the record and no graph exists to shape;
`emit` — the emitter refuses the record with a plain `EmitError`; `python` — not a graph fact, the linter
alone. `itpra-onto parity` compares the `core`/`sparql` rows by rule id, maps the `generated`/`emit` rows to
the emitter's `emit-error` finding, and reports the `python` rows as outside the comparison.

| id | sev | check | family | mechanism | target | notes |
|---|---|---|---|---|---|---|
| `yaml-parse-error` | error | a term/schema YAML file failed to parse | pre-A | `python` — not a graph fact; `yaml.safe_load` fails inside the emitter first, so `itpra-onto build` cannot run and no graph exists to shape | n/a | a guard, not a check family |
| `termfile-not-list` | error | a term file's top level is not a list of records | pre-A | `python` — same: pre-graph file-shape guard | n/a | |
| `record-not-mapping` | error | a list entry in a term file is not a mapping | pre-A | `python` — same | n/a | |
| `field-missing` | error | required field (`id`/`term`/`type`/`definition`) absent or whitespace-only | A1 | `core` — `sh:minCount 1` on `skos:prefLabel` (`term`) and `skos:definition` (`definition`) per `Term` subject in `t1` | t1 | `id`/`type` absence additionally crashes the emitter (`EmitError`) before a graph exists — doubly covered for those two sub-cases, but `term`/`definition` reach the graph fine if absent (the emitter omits the triple, no crash), so a real shape is still needed. **Presence only on both sides:** the linter treats a whitespace-only value as missing (the emitter already omitted it), and the shapes carry no `sh:maxCount` (two values on one subject is a duplicated record: B-12 on the graph, `id-duplicate` in the YAML) |
| `field-unknown` | error | a term record carries a field outside `schema.yaml` `fields:` | pre-A | `python` — the emitter projects named fields only, so an unknown one never reaches a graph; also closed pre-emission by `validate --authoring` (closed mode) | n/a | |
| `id-duplicate` | error | same id defined more than once | A3 | `python` (build-time), not a shape — SHACL has no native "no two distinct subjects share this literal" without a `SPARQL` aggregate, and once two colliding YAML records are emitted they skolemise onto the SAME IRI — the question is moot post-emission | n/a | |
| `id-pattern` | error | id does not match `schema.yaml`'s id pattern | A2 | `core` — `sh:pattern` on `dcterms:identifier` (the `id`) per `skos:Concept` — the id survives emission unchanged as the IRI local name | t1 | |
| `type-unknown` | error | `type` not in `schema.yaml`'s `types` | A4 | `generated` — the emitter raises `EmitError("...has type ..., which no Term subclass pins")` for an unrecognised/missing `type`; build fails before any graph exists. Construct: each subclass's `slot_usage: {type: {pattern: "^<Value>$"}}` + the generated `EntityTypeEnum` range on the `type` slot | n/a | no graph is reachable with this defect present |
| `relates-to-malformed` | error | a `relates_to` entry is not a mapping | pre-A (adjacent to A5/A6) | `emit` — `emit.py`'s `_verb_edges` raises `EmitError` naming the record id and the offending entry when it is not a mapping or lacks `rel`/`target`; no graph is reachable | n/a | `fixtures/structural/relates-to-malformed.yaml` proves it with `rule: emit-error` — the id is no `itpra-o:ruleId` in any shape file |
| `verb-unknown` | error | `relates_to.rel` not a known verb | A5 | `generated` — the emitter raises `EmitError("relates_to verb ... is not a slot in the verbs subset")` for any `rel` outside the 17-verb `RelationshipVerbEnum` on a **term** record; build fails first. Construct: `RelatesTo.rel range: RelationshipVerbEnum` | n/a | **Correction:** "no graph is reachable" holds only for non-EntityType records. On an **EntityType** record the `relates_to` entries are meta-edges the emitter never projects, so an unknown verb there raises nothing and a graph IS built — that sub-case is `python`-only (the linter alone sees it). `itpra-onto parity` excludes such findings from the comparison and reports them (`parity.META_EDGE_RULE_IDS`). `fixtures/structural/verb-unknown.yaml` proves the emit-time guard on a Capability |
| `target-unresolved` | error | `relates_to.target` does not resolve | A6 | `core` — `sh:class skos:Concept` on the object of each term-carried verb's own predicate, once `relates_to` is pivoted; a dangling target carries no `rdf:type` triple, so `sh:class` fails | t1 | referential integrity is a property-shape range check. The verb's declared range (the `itpra_verb` `pairs`) is **B-22**, not this rule. **EntityType records:** a dangling meta-edge target is `python`-only — the emitter never projects meta-edges; `itpra-onto parity` excludes and reports those findings |
| `function-derived-from` | error | a `Function` record uses `derived_from` (ADR 0011) | A7 | `core` — `sh:targetClass Function` + `sh:maxCount 0` on `itpra-o:derivedFrom` | t1 | one predicate, one class, one cardinality bound — pure Core |
| `schema-types-missing` | warning | `schema.yaml` declares no `types` | pre-A | `python` — guards the linter's own input file, not a term record | n/a | |
| `source-grammar` | error | a `source:` item names a record but is not `ADR NNNN` with an optional amended/extended tail (ADR 0005) | A14 | `python` — the emitter raises `SourceGrammarError` for the same item before any graph exists (the `B-13-emit-guard` fixture proves that side); the lint reports it on the record | n/a | an item carrying a URL is external and exempt |
| `source-adr-unresolved` | error | a cited `ADR NNNN` has no record under `decisions/` (ADR 0005) | A15 | `python` — decision records are files, not graph facts; B-13 checks only the citation node's shape | n/a | |
| `version-format` | error | `ontology_version` is not X.Y.Z, or `schema_version` is not an integer (ADR 0003) | pre-A | `python` — a fact of `schema.yaml`, read before emission | n/a | |
| `retired-format` | error | a `retired` value is not an X.Y.Z version (ADR 0048) | A16 | `core` — `sh:pattern` on `itpra-o:retiredIn` per subject of that predicate (`structural.ttl`'s `itpra-o:RetiredFormatShape`); the emitter projects the value verbatim | t1 | the `retired` slot of the authoring schema carries the same pattern |
| `replaced-by-unresolved` | error | `replaced_by` is not the id of a record, or names its own record (ADR 0048) | A16 | `sparql` — `dcterms:isReplacedBy` object that is no `skos:Concept` or is the subject itself (`crossfield.ttl`'s `itpra-o:ReplacedByUnresolvedShape`); `sh:class` alone cannot see the self-reference | t1 | `fixtures/crossfield/replaced-by-unresolved.yaml` proves the dangling arm; `test_shapes_crossfield.py` the self-reference arm |
| `replaced-by-without-retired` | error | `replaced_by` on a record that is not retired (ADR 0048) | A16 | `core` — `sh:hasValue true` on `owl:deprecated` per subject of `dcterms:isReplacedBy` (`structural.ttl`'s `itpra-o:ReplacedByWithoutRetiredShape`); the emitter marks a record `owl:deprecated` exactly when it carries `retired` | t1 | |

**The banned-synonym scan has no rule id.** `schema.yaml` documents the `deprecated` field as not
machine-enforced: the banned words occur legitimately in dozens of definitions, so no check — linter or
shape — exists or is owed for it. `deprecated` lists banned synonyms and never marks retirement; that is
`retired` (the three A16 rows above).

## Table B — rules the shapes add that the linter lacks

Sourced to the rule text that authorises each one — never invented here (the register adds no term or
rule; a candidate needing a ruling is flagged, not bound). ADR 0042 D3: shapes may be stricter than the
linter; a declared-but-unstated minimum is a warning. Ids are stable and never reused, so the numbering has
gaps.

| # | Rule | Source | Mechanism | Status |
|---|---|---|---|---|
| B-2 | `grouped_by` ≥1 per `Capability`/`Domain`/`Journey` | `schema/itpra.linkml.yaml`'s `itpra_verb` `cardinality` for `grouped_by` (`{min:1,max:1}` on each); already enforced pre-emission by LinkML's `has_member` on the authoring schema | `core` — `sh:minCount 1` on `itpra-o:groupedBy` in `t1`, restating the same declared cardinality at the graph level (needed for `itpra-onto parity`, since the generated authoring SHACL doesn't validate the graph) | **stricter than the linter** — the linter has no "every Capability/Domain/Journey has a grouped_by" check at all |
| B-3 | `grouped_by` ≤1 per `Capability`/`Domain`/`Journey` | Same `itpra_verb` annotation, `cardinality` field; the LinkML schema's own comment at `Capability.relates_to.has_member` says "at most one: itpra_verb annotation, enforced by the shapes" | `core` — `sh:maxCount 1` on `itpra-o:groupedBy` | **stricter than the linter AND than the current authoring schema** — neither checks the upper bound today |
| B-5 | `consumed_by` ≥1 per `Capability`/`Journey` | ADR 0042 D3: a minimum the data satisfies but nothing declares (`consumed_by` ≥1 on Capability and Journey) | `core` — `sh:minCount 1` on `itpra-o:consumedBy` (`structural.ttl`'s `itpra-o:ConsumedByMinCountShape`) | **built as `sh:Warning`** (ADR 0042 D3: advisory) — the `itpra_verb` annotation's own `cardinality: []` is deliberately empty, so this stays advisory rather than a linter-parity `sh:Violation`; `fixtures/structural/B-5.yaml` proves it fires |
| B-6 | `realized_in` exactly 1 per `Workflow` | Same ADR 0042 D3 case (a minimum nothing declares) | `core` — `sh:minCount 1`/`sh:maxCount 1` on `itpra-o:realizedIn` (`structural.ttl`'s `itpra-o:RealizedInExactlyOneShape`) | **built as `sh:Warning`** (ADR 0042 D3: advisory) — same reasoning as B-5; `cardinality: []` is empty. The vocabulary holds no Workflow record (ADR 0046): the shape applies to a consumer's own; `fixtures/structural/B-6.yaml` adds one to prove it fires |
| B-7 | `depends_on` ≥1 per `Journey` | Same ADR 0042 D3 case | `core` — `sh:minCount 1` on `itpra-o:dependsOn` (`structural.ttl`'s `itpra-o:DependsOnMinCountShape`) | **built as `sh:Warning`** (ADR 0042 D3: advisory) — same reasoning; `fixtures/structural/B-7.yaml` proves it fires |
| B-8 | No `skos:altLabel` equals its own subject's `skos:prefLabel`, case-insensitively | ADR 0007 (an alias never equals the term's own label, case-insensitively) | `sparql` — `FILTER(LCASE(?alt) = LCASE(?pref))` between two properties of the **same** subject; SHACL Core's `sh:disjoint` compares property values by exact RDF-term equality only, not case-folded | **new** — the linter has zero SKOS label-collision checks |
| B-9 | A term's alias equals a **different** record's own `prefLabel` | (none — SKOS permits it) | — | **no rule, by design.** ADR 0007 forbids only a term's alias duplicating **its own** `prefLabel` (self-collision); a cross-term collision is ordinary controlled-vocabulary homonymy (a word legitimately reused as one term's alternate label and another's preferred one) and nothing in ADR 0007 or the linter forbids it. Not created here. If a future record wants a heuristic: `?a skos:altLabel ?l . ?b skos:prefLabel ?l . FILTER(?a != ?b)` at `warn` severity |
| B-10 | `source` grammar (`ADR NNNN`, optional amend/extend tail, or an external citation) | ADR 0005 (the `source:` grammar) | `python` (emit-time) — `emit.parse_source` raises `SourceGrammarError` naming the record id and the offending item; a violating record can never reach the graph, the same `EmitError`-class reasoning as `type-unknown`/`verb-unknown` | **enforced at emit time, not a shape** — recorded here so the mechanism is not left implicit |
| B-12 | Exactly one `itpra-o:authoringFile` per record | ADR 0043 D3 (provenance: every record names the file it was authored in); `test_competency.py::test_every_subject_has_exactly_one_existing_authoring_file` (CQ8) | `core` for the cardinality half — `sh:minCount 1` + `sh:maxCount 1` on `itpra-o:authoringFile` per subject; the **file-exists-on-disk** half stays `python`/`test-only` (SHACL cannot stat the filesystem) | **new** — an obligation the RDF projection carries that the linter has no analogue for at all (the linter validates YAML files it already has open, never "does this path exist as a separate check") |
| B-13 | Every `itpra-o:decidedIn` object is an `ADR-NNNN` node, four digits | `test_competency.py::test_every_decided_in_object_is_a_four_digit_adr_node` (CQ7); the shape follows directly from B-10's `source` grammar once `decidedIn` links exist in the graph | `sparql` — `FILTER(REGEX(STR(?adr), "ADR-[0-9]{4}$"))` on the local name of an IRI object; SHACL Core patterns match string **literals**, not IRI local names, so this needs SPARQL | **new** — `decidedIn` is a projection-only construct; the linter's `source` check is a free-text scan, not a typed-node check |
| B-14 | The `inferred` graph mints only schema-pre-declared derived vocabulary | `test_competency.py::test_inferred_graph_only_uses_schema_declared_derived_vocabulary` (CQ9) | `test-only` | Guards the **pipeline's own code discipline** (the rules engine must only mint vocabulary `emit.py` already declared with an `rdfs:comment` starting "derived by rule") — no authored YAML content can violate this; already proven in `test_competency.py` |
| B-15 | No blank nodes anywhere in the store | ADR 0041 D2 ("no blank nodes"); `test_competency.py::test_no_blank_nodes_anywhere` (CQ10) | `test-only`, optional `core` defence in depth (`sh:nodeKind sh:IRI` sweep) | Same reasoning as B-14 — a blank node can only be introduced by the emitter/rules code itself, not by content |
| B-16 | The default (unnamed) graph is empty | `test_competency.py::test_default_graph_is_empty` (CQ10) | `test-only` | Same reasoning |
| B-17 | Per-type instance counts in `t1` equal the YAML record counts | `test_competency.py::test_type_counts_match_the_yaml_records` (CQ1) | `test-only` | Positive control, not an authorable content rule |
| B-18 | Every `Function` has ≥1 `itpra-o:inDomain` (inferred) | `test_competency.py::test_function_in_domain_is_a_multiset_not_a_function` (CQ2) | `core`, defence in depth on `inferred` | Logically implied by `supports` ≥1 (A-tier, already required) + `grouped_by` on the supported Capability; a direct shape on the **derived** edge catches a rules-engine regression, not just a content defect |
| B-19 | Every `Capability` has exactly one `inPlane` and one `inServiceDomain` (inferred) | `test_competency.py::test_every_capability_has_exactly_one_plane_and_service_domain` (CQ3) | `core`, defence in depth on `inferred` | Same reasoning as B-18 |

**Rows minted by the `structural`/`crossfield` shape files themselves:**

| # | Rule | Source | Mechanism | Status |
|---|---|---|---|---|
| B-8-pref-label-unique | A subject carries more than one `skos:prefLabel` per language tag | SKOS integrity condition S14 (a controlled-vocabulary norm, not a decision record); the competency query `cq-11-duplicate-pref-labels.rq` asks the same | `sparql` — same-subject cross-value comparison (`$this skos:prefLabel ?value . $this skos:prefLabel ?other . FILTER(?value != ?other && LANG(?value) = LANG(?other))`); SHACL Core has no native same-property-value-collision check | **new** — the linter has no SKOS label-uniqueness check. Built in `crossfield.ttl` (`itpra-o:PrefLabelUniqueShape`); defence in depth, proven by direct quad injection in `test_shapes_crossfield.py` (no authoring-YAML mutation can produce two `skos:prefLabel`s on one subject — `term` is a scalar field); `fixtures/crossfield/B-8-pref-label-unique.yaml` is a `count: 0` clean-case fixture documenting the nearest a mutation can get |
| B-3-belongs-to-service-domain | `belongs_to_service_domain` exactly 1 on `Domain`; at most 1 on every other term | `schema/itpra.linkml.yaml`'s `belongs_to_service_domain` `itpra_verb` `cardinality` list: `{subject: Domain, min:1, max:1}`, `{subject: Term, min:0, max:1}` — the same declared-cardinality mechanism that authorises the B-2/B-3 rows (`grouped_by`) | `core` — `sh:minCount 1`/`sh:maxCount 1` on `itpra-o:belongsToServiceDomain` for `itpra:DOMAIN` (`itpra-o:BelongsToServiceDomainDomainShape`); `sh:maxCount 1` for every other term class (`itpra-o:BelongsToServiceDomainTermMaxShape`) | **stricter than the linter** — no linter analogue restates this cardinality at the graph level. Built in `structural.ttl`, named in the family of B-3 (same declared-cardinality-at-the-graph-level pattern); `fixtures/structural/B-3-belongs-to-service-domain.yaml` proves the Domain arm |
| B-2-supports | `supports` ≥1 per `Function` | `schema/itpra.linkml.yaml`'s `supports` `itpra_verb` `cardinality`: `{subject: Function, min:1, max: null}` — the same declared-cardinality mechanism that authorises the B-2 row (`grouped_by`) | `core` — `sh:minCount 1` on `itpra-o:supports` for `itpra:FUNCTION` (`itpra-o:SupportsMinCountShape`) | **stricter than the linter** — no linter analogue. Built in `structural.ttl`, named in the family of B-2. **Causally coupled to B-18**: `itpra-o:inDomain` is entirely derived from `itpra-o:supports` (`rules/30-function-in-domain.rq`), so a Function with zero `supports` edges always has zero `inDomain` edges too, on the SAME focus — no isolated count-1 fixture is shippable (`assert_fixture`'s no-cascade check would reject it). `fixtures/structural/B-2-supports.yaml` is a `count: 0` clean-case fixture instead, proving the shape does not misfire on a partial (non-zeroing) mutation |

**Rows added by the mutation review of the shapes:**

| # | Rule | Source | Mechanism | Status |
|---|---|---|---|---|
| B-22 | A verb edge whose object is a resolved record must have a (subject class, object class) among the verb's **allowed pairs** | `schema/itpra.linkml.yaml` — every `verbs`-subset slot's `itpra_verb` annotation, `pairs` = "the ALLOWED (subject, object) combinations"; the annotations are governing rule text (ADR 0008: per-verb domain, range and cardinality live there; ADR 0041 D1) | `sparql`, **generated** from the annotations — `itpra-onto gen-verb-shapes` writes `shapes/generated/verb-pairs.ttl` (one `sh:NodeShape` per verb, `sh:targetSubjectsOf` the verb's predicate; `--check` fails when stale). Membership test over each node's record classes (a record is also `skos:Concept`); a dangling object is left to `target-unresolved`; a pair naming no record class (`ADR`, `SERVICE`, `FR`) matches nothing and is listed in the file header | **stricter than the linter** (the linter has no domain/range check). `sh:Violation`. Zero findings on the real tree. Fixtures: `fixtures/structural/B-22-journey-grouped-by-persona.yaml`, `B-22-capability-belongs-to-service-domain.yaml`, `B-22-consumed-by-function.yaml`. Co-fires by construction with `function-derived-from` (derived_from's pairs allow only (Capability, Capability)) — that fixture declares `cofires: [B-22]` |
| B-23 | A term's `deprecated` (banned-label) list contains the term's own `term` | (none — `schema.yaml` `fields.deprecated` is not machine-enforced: the words occur legitimately elsewhere) | — | **no rule.** The case projects silently (the label becomes both `skos:prefLabel` and the `skos:hiddenLabel` sub-property `bannedLabel`). SKOS S13 (prefLabel/altLabel/hiddenLabel pairwise disjoint) would forbid it, but `bannedLabel` is only declared a sub-property of `skos:hiddenLabel`, and no rule text binds S13 here. Recorded, not built |

**Note on proof style.** `B-13` and `B-8-pref-label-unique` are defence in depth: the defect they catch can
only be produced by injecting quads directly into an emitted dataset, bypassing the emitter entirely — no
authoring-YAML mutation can reach it — so each is proven by direct quad injection in its shape file's test
module, and each additionally carries a `count: 0` clean-case fixture documenting the nearest an authoring
mutation can get without tripping the rule. `B-2-supports` carries a `count: 0` clean-case fixture for a
different reason (causal coupling with B-18 on the same focus, not defence in depth — see its own row
above): a genuine zeroing mutation CAN fire it, just never in isolation.

**Table B counts:** 21 rows. **11 stricter than the linter**, every one with a shape (10 hand-written +
B-22, generated); **3 `sh:Warning`** (B-5, B-6, B-7); **2 "no rule"** (B-9 by design, B-23 not
machine-enforced by rule text); **1 enforced elsewhere** (B-10, emit-time); **4 test-only** (B-14, B-15,
B-16, B-17). 11 + 3 + 2 + 1 + 4 = 21. B-18/B-19 count as stricter only in the narrow "no linter analogue on
the derived graph" sense — see their own rows.

## Table C — severity mapping

| Linter severity | Shape severity | Rule |
|---|---|---|
| `error` (exit 1) | `sh:Violation` | default for every `core`/`sparql` row above |
| `warning` (exit 0) | `sh:Warning` | no Table A row with a shape is a warning today |
| `error` (emit-time `EmitError`) | `emit-error` finding, `sh:Violation` | `itpra-onto validate`/`parity` report an input the emitter refuses as a synthetic `emit-error` finding (on the record the error names; message `"<ErrorClass>: …"`) and exit 1 |

No row in Table A changes severity from what the linter already assigns. **New rows in Table B are assigned
severity here, since they have no linter row to inherit from:**

| Rule | Shape severity | Reason |
|---|---|---|
| B-2 `grouped_by` ≥1 | `sh:Violation` | a declared cardinality; a missing `grouped_by` breaks the plane/service-domain roll-up rules outright |
| B-3 `grouped_by` ≤1 | `sh:Violation` | same reasoning — a second `grouped_by` would silently corrupt the roll-up rules (`10-capability-in-plane.rq` etc.), which assume exactly one |
| B-8 alt-label self-collision | `sh:Violation` | ADR 0007 treats a self-duplicating alias as a defect to remove, not tolerated variance |
| B-12 authoringFile cardinality | `sh:Violation` | zero or two-or-more `authoringFile` triples on a subject indicates the **emitter itself** is broken, not an authoring choice |
| B-13 decidedIn node shape | `sh:Violation` | same — a malformed `decidedIn` object indicates emitter/parser corruption, not an authoring choice |
| B-2-supports `supports` ≥1 per Function | `sh:Violation` | a declared cardinality (`supports` `{Function, min 1}`), like B-2 |
| B-3-belongs-to-service-domain | `sh:Violation` | a declared cardinality (`belongs_to_service_domain` `{Domain, 1..1}`, `{Term, 0..1}`), like B-3 |
| B-8-pref-label-unique | `sh:Violation` | SKOS S14 is an integrity condition, not a preference |
| B-18 `inDomain` ≥1 (inferred) | `sh:Violation` | a missing derived edge means the rules engine regressed |
| B-19 `inPlane`/`inServiceDomain` exactly 1 (inferred) | `sh:Violation` | same |
| B-22 verb allowed pairs (generated) | `sh:Violation` | the `itpra_verb` `pairs` are governing rule text (ADR 0008), not a hint |
| B-5/B-6/B-7 candidate minimums | `sh:Warning` | ADR 0042 D3: advisory — no declared cardinality (`cardinality: []`) |
| B-9, B-10, B-14–B-17, B-23 | n/a | no shape (see their own rows) |

## Shape files and their fixtures

Two hand-written shape files with disjoint ownership (ADR 0042 D2), each with its own fixture directory and
one deliberately broken record per rule (`fixtures/<file>/<rule-id>.yaml` — a wrong type, a dangling target,
a second `grouped_by`, …; clean data must pass every shape file unmodified; ADR 0042 D4). Shapes target `t1`
and (for B-18/B-19) `inferred`; the assembled shapes graph is `<graph_ns>shapes` (see above). Only rows whose
mechanism is `core` or `sparql` get a shape.

### `structural` (SHACL **Core**) — `shapes/structural.ttl`, `fixtures/structural/`

Targets: `t1`, `inferred`. **16 distinct `itpra-o:ruleId` values:**

`field-missing` · `id-pattern` · `target-unresolved` · `function-derived-from` · `retired-format` ·
`replaced-by-without-retired` · B-2 (`grouped_by` ≥1) · B-3 (`grouped_by` ≤1) · B-12 (authoringFile
cardinality) · B-18 (`inDomain` ≥1, `inferred`) · B-19 (`inPlane`/`inServiceDomain` exactly 1, `inferred`) —
11 linter-parity and Table B ids — plus **B-5, B-6, B-7** (`sh:Warning`) plus **B-3-belongs-to-service-domain**
(`belongs_to_service_domain` cardinality, named in the family of B-3) and **B-2-supports** (`supports` ≥1 per
Function, named in the family of B-2; causally coupled to B-18) — 11 + 3 + 2 = 16. The emit-time ids (`type-unknown`, `verb-unknown`,
`relates-to-malformed`) have fixtures here with `rule: emit-error`.

### `crossfield` (SHACL-**SPARQL**) — `shapes/crossfield.ttl`, `fixtures/crossfield/`

Targets: `t1`. Graph-wide checks (label integrity, node shape of a projection-only construct, a successor
that is another record). 4 ids:

`replaced-by-unresolved` (a retired record's `dcterms:isReplacedBy` names another record) · B-8 (alt-label
self-collision) · B-8-pref-label-unique (at most one `skos:prefLabel` per language tag per subject, SKOS S14)
· B-13 (decidedIn node shape)

### `shapes/generated/` — owned by the generator, not a hand-written file

`shapes/generated/verb-pairs.ttl` is written by `itpra-onto gen-verb-shapes` from the `itpra_verb`
annotations and checked by `gen-verb-shapes --check`; it is never edited by hand (regenerate instead).
`itpra_onto.shacl.load_shapes` loads `shapes/generated/*.ttl` after the hand-written files. 1 distinct rule
id: **B-22** (17 shapes, one per verb). Its fixtures live in `fixtures/structural/B-22-*.yaml`.

## Counts

Recomputed from the files:

- **Table A rows:** 19 (`itpra-onto parity` fails if the table's row count differs) — the ids
  `itpra_onto.lint` implements (`CORE_RULE_IDS`).
- **Per mechanism:** `core` **6** (`field-missing`, `id-pattern`, `target-unresolved`,
  `function-derived-from`, `retired-format`, `replaced-by-without-retired`) · `sparql` **1**
  (`replaced-by-unresolved`) · `generated` **2** (`type-unknown`, `verb-unknown`) · `emit` **1**
  (`relates-to-malformed`) · `python` **9** (`yaml-parse-error`, `termfile-not-list`, `record-not-mapping`,
  `field-unknown`, `id-duplicate`, `schema-types-missing`, `source-grammar`, `source-adr-unresolved`,
  `version-format`). **6 + 1 + 2 + 1 + 9 = 19.** Comparable in `itpra-onto parity`: the 7 `core`/`sparql`
  ids. Emit-time mapped: the 3 `generated`/`emit` ids. Outside the comparison: the 9 `python` ids.
- **Table B rows: 21** (see the Table B counts paragraph): 11 stricter, 3 warning, 2 no rule, 1 enforced
  elsewhere, 4 test-only.
- **Distinct `itpra-o:ruleId` values in the loaded shapes: 21** — `structural` 16 · `crossfield` 4 ·
  `generated` 1 (B-22). `itpra-onto parity` checks at run time that every comparable id is among them and
  that every one of them is a Table A or Table B id.

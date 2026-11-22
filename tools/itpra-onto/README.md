# itpra-onto

The ITPRA ontology-as-code pipeline. It projects the authored vocabulary (YAML, validated against a LinkML
authoring schema) into RDF in named graphs — SKOS concepts under a thin OWL class layer, verbs as object
properties, no blank nodes — materialises a small set of derived facts with ordered SPARQL `CONSTRUCT`
rules, validates the result with hand-written SHACL, loads it into an embedded
[Oxigraph](https://github.com/oxigraph/oxigraph) store, and writes canonical, digest-addressed artefacts.
The YAML stays authoritative; every emitted graph is derived from it (ADR 0041 D1).

Decision records cited as `ADR NNNN` are the ontology's own, in `decisions/` at the repository root; the
pipeline is decided in [ADR 0041](https://github.com/4thtrytech/itpra-ontology/blob/master/decisions/0041-the-rdf-projection-roles-modelling-and-derivation.md)
(the RDF projection), [ADR 0042](https://github.com/4thtrytech/itpra-ontology/blob/master/decisions/0042-validation-parity-register-shapes-fixtures-and-the-parity-check.md)
(validation parity) and [ADR 0043](https://github.com/4thtrytech/itpra-ontology/blob/master/decisions/0043-builds-artefacts-and-the-consumer-overlay.md)
(builds, artefacts and the consumer overlay).

## Configuration

`itpra-onto.toml`, next to `pyproject.toml`, is read by `itpra_onto.config.load_config()`; paths are
relative to its directory. `ITPRA_ONTO_CONFIG` (an environment variable; tests and CI) points at another
file.

| Table | Keys | Meaning |
|---|---|---|
| `[iri]` | `base`, `id_path`, `onto_path`, `graph_path` | The base IRI and the three namespaces built from it: `itpra:` = `<base><id_path>` (one IRI per record), `itpra-o:` = `<base><onto_path>` (verbs, classes and annotation properties), `itpra-g:` = `<base><graph_path>` (named graphs). Every key is required; a missing one raises `ConfigError` — no default is baked into the code (ADR 0004). |
| `[paths]` | `ontology_dir`, `dist_dir`, `store_dir` | The vocabulary's directory (`schema.yaml`, `entities.yaml`, `relationships.yaml`, `terms/*.yaml`), the output root (`<dist_dir>/rdf/`, `<dist_dir>/schema/`) and the embedded store's directory. |
| `[python]` | `pinned` | The interpreter version the package is pinned to (`3.12`). |

The base IRI is written once, in `[iri] base`: the LinkML prefixes are generated from it (`gen-prefixes`),
the schema's own `id:` is substituted in memory at load time, and rule, shape and query files declare no
`PREFIX`/`@prefix` for `itpra:`/`itpra-o:`/`itpra-g:` — a block computed from the configuration is prepended
before they run or parse. `tests/test_iri_config.py` fails if the literal appears outside `itpra-onto.toml`
and the two generated fragments. A host ending in `.invalid` is a placeholder that `itpra-onto release` refuses.

## Core and overlay

The **core** is built from the vocabulary alone: the `schema` and `t1` graphs, the `inferred` graph from
the five vocabulary rules, the `structural`, `crossfield` and generated verb shapes, and the generated
LinkML artefacts. Everything a *consumer* layers on top is the **overlay**, an optional `[overlay]` table
(ADR 0043 D1):

| Key | What it enables |
|---|---|
| `requirements_glob` | The consumer's requirement registries. Each becomes a `req/<X>` graph and enables the `requirement-meets` rule (`overlay: true` in `rules/manifest.yaml`), `shapes/requirements.ttl` and the requirement fixtures. A registry is named by the first path component below the glob's fixed prefix (the components before its first wildcard), or by the file's stem when the file sits directly there. |
| `linter_script` | The consumer's own linter, which `parity` compares the shapes against (ADR 0042 D5). |
| `excluded_dirs` | Directory names the input-path guard refuses at any depth, case-insensitively, beyond the built-in `dist`, `public` and `__pycache__`. |

Without the table, `build` emits `schema` + `t1` + `inferred` only, `validate` loads no requirements
shapes, `validate --authoring` checks the term files only, and `parity` refuses to run (exit 1). A
configuration that still carries `requirements_glob` under `[paths]` is read as an overlay with that one
key.

## Commands

`itpra-onto <command>` (or `uv run itpra-onto <command>` from this directory):

| Command | Behaviour |
|---|---|
| `gen-enums [--check]` | Regenerates `schema/generated/itpra-enums.linkml.yaml` (`EntityTypeEnum`, `RelationshipVerbEnum`) from `schema.yaml`'s `types:` and `relationships:`. Sorted, LF. `--check` exits 1 if the committed file is stale or missing. |
| `gen-prefixes [--check]` | Regenerates `schema/generated/itpra-prefixes.linkml.yaml` from `[iri]`. Sorted, LF. `--check` as above. |
| `gen-verb-shapes [--check]` | Regenerates `shapes/generated/verb-pairs.ttl` (rule `B-22`: one SHACL-SPARQL shape per verb, allowing only the (subject class, object class) pairs its `itpra_verb` annotation declares) from `schema/itpra.linkml.yaml`. `shapes/generated/` is owned by this command; never edit it by hand. `--check` as above. |
| `gen-artifacts [--check]` | Regenerates `<dist_dir>/schema/` (`itpra.schema.json`, `itpra_models.py`, `itpra.owl.nt`, `itpra.shacl.nt`, `doc/`) from the LinkML schema. Two runs are byte-identical. `--check` regenerates into a temporary directory and exits 1 on any difference. |
| `validate --authoring [--quiet]` | LinkML-validates every term file (and, with an overlay, every registry) against `schema/itpra.linkml.yaml`, in-process, closed mode. One line per file and a total; exit 0 only if every file passes. `--quiet` prints failing files only. See [`schema/README.md`](schema/README.md). |
| `validate [--shapes DIR] [--json]` | Emits, applies the rules and SHACL-validates the result against `shapes/` (or `DIR`). One line per finding, sorted, then a summary. Exit 0 only when no `sh:Violation` fired; a `sh:Warning` is advisory. `--json` prints a JSON list of `rule`/`subject`/`severity`/`message` and nothing else on stdout. An input the emitter refuses is reported as an `emit-error` finding (exit 1), never a traceback. |
| `build [--out DIR] [--no-store] [--check]` | Emits, applies the rules, adds the `provenance` graph, canonicalises and writes `<dist_dir>/rdf/` (or `DIR`), then loads the embedded store unless `--no-store`. `--check` builds into a temporary directory, never touches the store, and exits 1 if `base/` would differ from what is on disk or is missing. |
| `parity [--json] [--fixtures] [--sub X ...]` | Overlay only. Compares the consumer's linter with the shapes over the comparable rule ids: the real tree by default (`--sub X`, repeatable, restricts the linter side to those registries), or fixture by fixture with `--fixtures` (`--sub` ignored). `--json` prints one object and nothing else. |
| `release` | Not implemented yet. Exits 1 while `[iri] base` has a `.invalid` host; otherwise prints that it is not implemented and exits 2. |

`python -m itpra_onto.profile` prints the per-verb profile read off the data (type pairs with counts,
per-record edge counts, meta-edges) that the schema's `itpra_verb` annotations were written from.

## The emitted graphs

`itpra_onto.emit` (`load_inputs()` then `emit()`) builds an in-memory `pyoxigraph.Dataset`. It reads every
`*.yaml` directly under `ontology_dir` except `schema.yaml` and `PIN.yaml`, then every `*.yaml` under
`terms/` (not recursive beyond that, so an ontology directory that is a repository root sweeps up no
tooling), `schema.yaml` for `ontology_version` only, and the overlay's registries if any. Every path first
passes the **input-path guard** (ADR 0043 D1): under the repository root; no component beginning with `.`;
not under `dist`, `public`, `__pycache__` or an `excluded_dirs` name at any depth; a file must be `.yaml`.
A violation raises `InputPathError` naming the path and the rule.

Only named graphs are written; the default graph stays empty, and no query reads the union (ADR 0041 D3):

| Graph | Holds |
|---|---|
| `schema` | The ontology header and version IRI, the concept scheme, each EntityType record as an `owl:Class` under `skos:Concept`, `FR`/`NFR` under `REQUIREMENT`, the 17 verbs as `owl:ObjectProperty` with `rdfs:seeAlso` to their RelationshipType record, the annotation properties, and the declarations of what the rules derive and the build records (each with an `rdfs:comment` naming the rule or build step that asserts it). No domain, range, inverse or functional axioms (ADR 0041 D2). |
| `t1` | Every term record. |
| `req/<X>` | One per registry: its FR/NFR records, typed `REQUIREMENT`, `FR` or `NFR` and, like every term, explicitly `skos:Concept`, so listing concepts needs no reasoning. |
| `inferred` | Written only by the rules (below). |
| `provenance` | Written only by `build` (below). |

Every predicate and class is the `slot_uri`/`class_uri` of `schema/itpra.linkml.yaml`; labels, definitions
and statements are tagged `@en`; no data graph contains a blank node. A `source` value is kept verbatim as
`dcterms:source`, and each `ADR NNNN` in it becomes `itpra-o:decidedIn <id>ADR-NNNN` (`itpra-o:amendedBy`/
`itpra-o:extendedBy` inside an `(amended by …)`/`(extended by …)` tail). The grammar is strict (ADR 0005):
each `;`-separated item mentioning `ADR` must match `ADR NNNN` exactly, optionally followed by one such tail,
or `SourceGrammarError` names the record and the item. An item carrying a URL is an external reference in
its entirety, never a `decidedIn` link; a bare `ADR NNNN` means the record of that number in the file's repository.

## Rules

`itpra_onto.rules.apply_rules()` runs the SPARQL `CONSTRUCT` files under `rules/` in the order
`rules/manifest.yaml` states and writes every constructed triple into `inferred`, never into an asserted
graph — no reasoner, no inverse minted (ADR 0041 D4). A rule's `WHERE` reads graphs by name
(`GRAPH itpra-g:t1 { … }`, or a `STRSTARTS` test over every `req/*` graph); its template has no `GRAPH`
clause, and the file declares no base IRI or `itpra*` prefix: `rules.prefix_block(config)` is prepended at
run time. A file with no `CONSTRUCT` is skipped and contributes zero triples.

| # | Rule id | Derives | Reads |
|---|---|---|---|
| 10 | `capability-in-plane` | `itpra-o:inPlane`: `groupedBy` Capability→Domain→Plane, flattened | `t1` |
| 20 | `capability-in-service-domain` | `itpra-o:inServiceDomain`: `groupedBy` then `belongsToServiceDomain` | `t1` |
| 30 | `function-in-domain` | `itpra-o:inDomain`: `supports` then `groupedBy`; one triple per distinct domain | `t1` |
| 40 | `requirement-meets` | `itpra-o:meets`, the inverse of the authored `metBy` — the one materialised reverse link, kept for a consumer's traceability check (ADR 0042 D7). Overlay only | every `req/*` graph |
| 50 | `boundary-governed-function` | `itpra-o:BoundaryGovernedFunction` typing for every function `AUTON-BOUNDARY` (the automation boundary, ADR 0028) `governs` directly | `t1` |
| 90 | `inverses` | Nothing: the deliberately empty slot. No named inverse is minted for any verb; SPARQL inverse paths (`^itpra-o:supports`) are used instead | — |

`rules.rules_digest(config)` is the sha256 of `manifest.yaml` and every listed rule file, in manifest
order, with no timestamp — the `rules_version` the build records.

## Build

`itpra-onto build` runs `load_inputs()` → `emit()` → `apply_rules()`, adds the `provenance` graph,
canonicalises the whole dataset (RDFC-1.0, then a line sort — `itpra_onto.canon`; ADR 0041 D5) and writes,
under `<dist_dir>/rdf/`:

- `full/itpra.nq` — sorted canonical N-Quads of every graph, `inferred` and `provenance` included.
- `base/<graph>.ttl` — one Turtle file per *asserted* graph (`schema.ttl`, `t1.ttl`, one `req/<X>.ttl` per
  registry), never `inferred` or `provenance`, so `base/` is exactly what re-running the rules regenerates;
  each declares the `itpra*` prefixes plus `rdf`, `rdfs`, `owl`, `skos`, `dcterms` and `prov`.
- `base/manifest.json` — every base file's sha256 and quad count, sorted keys.
- `build.json` — the provenance record: sorted keys, indent 2, LF.

**Provenance carries no timestamp and no commit SHA** (ADR 0043 D3): seven scalars — `input_hash` (every
input file's bytes, each contribution prefixed by its repository-relative path, so a rename alone changes
it), `pipeline_version` (this distribution's version), `uv_lock_hash`, `rules_version`,
`ontology_version` (from `schema.yaml`), `schema_hash` (the hand-authored LinkML schema plus its two
generated fragments) and `code_hash` (every `src/itpra_onto/**/*.py`). All are hashed over
line-ending-normalised bytes (CRLF collapsed to LF), so they depend on content, never on the checkout. The
same record is written as RDF: the dataset node `<base>dataset` carries the seven as literals plus one
`prov:wasDerivedFrom` per input file, each a `prov:Entity` with `dcterms:identifier` (its path) and
`itpra-o:sha256`. `prov:wasDerivedFrom` is reserved for this dataset-to-input sense; a term's link to its
decision record is `itpra-o:decidedIn`.

**The store is disposable** (ADR 0041 D5): `[paths] store_dir` is removed and rebuilt with
`Store.bulk_load` from `full/itpra.nq` on every build unless `--no-store` is given, and its quad count is
asserted to equal the file's line count. Its on-disk format is not stable across `pyoxigraph` releases, so
it is never committed, backed up or migrated; only the serialised files are artefacts, built once,
digest-addressed and attached to the release (ADR 0043 D4). Nothing under `dist/` is committed (ADR 0043 D5).

## Validation

`itpra_onto.shacl` loads the shape files, restricts the dataset to the graphs a shape should see, runs
pySHACL and normalises the result into `Finding`/`ValidationReport` objects; its module docstring is the
full reference. The load-bearing points:

- **Shape files:** every `shapes/*.ttl` (`requirements.ttl` only with an overlay), then every
  `shapes/generated/*.ttl`. A shape file declares no `@prefix`: the loader prepends the `itpra*` block plus
  `sh`, `rdf`, `rdfs`, `skos`, `owl`, `xsd`, `dcterms` and `prov`, and injects one `owl:Ontology` node,
  `itpra-o:shapesPrefixes`, carrying `sh:declare` for all of them. Blank nodes are renamed per file so two
  files' `[...]` nodes never collide. The shapes graph is an input, never written into `full/itpra.nq`.
- **One named shape node per rule**, carrying its target, path, constraint, `sh:severity` and
  `itpra-o:ruleId "<id>"` directly — never a `sh:property [...]` wrapper, because the rule id is read off the
  shape pySHACL's `sh:sourceShape` names. Every `sh:sparql` node sets `sh:prefixes itpra-o:shapesPrefixes`.
- **Graphs validated** (default): `t1`, `inferred` and every `req/*` the dataset carries, copied into a
  fresh store's default graph — never `schema` or `provenance`; pySHACL would otherwise validate the union
  of every named graph.
- **Severity:** `sh:Violation` for a rule the linter reports as an error, `sh:Warning` for a warning and
  for a declared-but-unstated minimum (ADR 0042 D3). Exit 0 only when no Violation fired.

[`shapes/REGISTER.md`](shapes/REGISTER.md) is the contract (ADR 0042 D1): Table A maps every linter rule
id to exactly one mechanism — `generated` (closed before emission by the authoring schema), `core` (SHACL
Core over the emitted graph), `sparql` (`sh:SPARQLConstraint`) or `python` (stays in code, with a reason);
Table B lists every rule the shapes add beyond the linter (`B-n`), each marked stricter than the linter;
Table C is the severity mapping. The shape files have disjoint ownership (ADR 0042 D2): `structural.ttl`
(Core; `t1`, `inferred`), `crossfield.ttl` (SPARQL; `t1`, `req/*`), `requirements.ttl` (`req/*`) and the
generated `verb-pairs.ttl` — see [`shapes/README.md`](shapes/README.md).

**Fixtures** (ADR 0042 D4): one YAML file per rule id, `fixtures/<group>/<rule-id>.yaml`, describes one
deliberately broken record — a `mutate` of a real record (`set`, `append_relates_to` or `delete`) or an
`add` of a new one — and `expect: {severity, focus, count}`. `itpra_onto.fixtures.assert_fixture()` applies
it in memory, runs emit → rules → validate, and asserts that the rule fires exactly `count` times on the
focus, that no other Violation newly fires there (`cofires` lists those that do by construction) and that
the rule is silent on the clean corpus; `count: 0` is a clean-case fixture. An `EmitError` the mutation
triggers becomes one synthetic `emit-error` finding; such a fixture names its guard with `expect.emit_error`
and sits beside the positive one as `<rule-id>-emit-guard.yaml`. A rule no mutation can reach is proven by
quad injection in its group's test module.

## Parity (overlay only)

`itpra-onto parity` (`itpra_onto.parity`) compares the consumer's linter (`[overlay] linter_script`,
`--json`) with the shapes over the same `(rule, subject, severity)` triples (ADR 0042 D5). On conflict the
rule text wins (ADR 0042 D6).

- **Comparable ids:** Table A rows whose mechanism is `core` or `sparql`, parsed from the register at run
  time (a parse failure is a `ParityError`). `python` rows are reported as `outside_scope`, never compared;
  Table B rules have no linter analogue and are proven by fixture only.
- **Emit-time mapping:** ids the emitter refuses before any graph exists (Table A's `generated` rows plus
  `relates-to-malformed` and `req-link-malformed`) reach SHACL only as `emit-error`; `--fixtures` matches
  the linter's finding for the id recovered from the fixture's filename against that marker, by subject.
- **Real tree:** the linter runs once per registry (`--sub X` restricts) and its findings are unioned and
  deduplicated (a shared-term defect would otherwise count once per registry); SHACL runs once over the
  whole dataset; linter findings on EntityType meta-edges are excluded and reported. Exit 0 iff
  `linter_only` and `shacl_only` are empty and there are no `emit_errors`. `--json` keys: `comparable_rules`,
  `linter`, `shacl`, `linter_only`, `shacl_only`, `stricter_findings`, `outside_scope`, `meta_edge_excluded`,
  `emit_errors`.
- **`--fixtures`:** every fixture with `expect.count >= 1` is materialised into a temporary tree (the
  vocabulary, the fixture's registry and a byte-identical copy of the linter script, which locates its
  repository from its own path) for the linter; the SHACL side stays the in-memory harness. Verdicts: `both`,
  `shacl-only` (expected for every stricter rule), `linter-only`, `neither`. Exit 0 unless a comparable or
  emit-time-mapped rule verdicts `neither` or `linter-only`; exit 2 is a usage error; a `ParityError` propagates.

## Generated artefacts, never committed

`<dist_dir>/rdf/` (the build), `<dist_dir>/schema/` (`gen-artifacts`) and `[paths] store_dir` are rebuilt
from the inputs on every run and are never the system of record. `gen-artifacts` canonicalises what LinkML
does not: the JSON Schema is re-serialised with sorted keys, the absolute path LinkML echoes into the
Pydantic module is stripped, and the OWL and SHACL output is made deterministic at the source before
RDFC-1.0 and a line sort; the OWL generator runs with `use_native_uris=False`, so it uses the schema's
`slot_uri`/`class_uri`. `itpra.owl.nt` and `itpra.shacl.nt` describe the **authoring** shape, not the
emitted projection: they carry range and cardinality axioms the `schema` graph omits, and the generated
SHACL does not validate what `emit()` produces (no closed shapes, no `relates_to` pivot, `xsd:string` where
the graph has `@en`). The hand-written shapes are the projection's validation (ADR 0042 D2).

The committed generated files are `schema/generated/*.linkml.yaml` and `shapes/generated/verb-pairs.ttl`;
each command's `--check` detects drift and belongs in CI.

## Tests

```sh
uv sync                                        # create or update .venv without running anything
uv run pytest -q                               # the whole suite
uv run pytest -q -s tests/test_competency.py   # with the printed tables and timings
```

Tests that need the overlay (registries, the consumer's linter) carry the `overlay` marker and are skipped
when the configuration in use has no `[overlay]`; the rest must pass on the vocabulary alone. Point
`ITPRA_ONTO_CONFIG` at a file without the table for a core-only run. Every expected count is computed from
`emit.load_inputs()`, never a literal. `tests/competency/cq-NN-*.rq` holds 36 single-purpose SPARQL queries
run against one store holding `schema` + `t1` + every `req/*` + `inferred`; every query asserting an empty
result has a sibling counting query that confirms the pattern's positive count first.

## Dependency pins

Every dependency is pinned to an exact version in `pyproject.toml` and `uv.lock`; a bump is a
re-verification, not a routine update.

| Package | Version | Notes |
|---|---|---|
| `pyyaml` | 6.0.3 | |
| `rdflib` | 7.6.0 | |
| `pyoxigraph` | 0.5.11 | Alpha upstream; the store format is not stable across releases, so the store is always rebuilt |
| `pyshacl[oxigraph]` | 0.40.1 | The extra pulls in `pyoxigraph>=0.5.6`, satisfied by the pin above |
| `linkml` | 1.11.1 | |
| `linkml-runtime` | 1.11.1 | |
| `pytest` (dev group) | 9.1.1 | |
| `hatchling` (build backend) | 1.32.4 | |

## Python

`3.12` (`.python-version`; `requires-python = ">=3.12,<3.14"` in `pyproject.toml`).

# `schema/` — the LinkML authoring schema

`itpra.linkml.yaml` describes the ontology **as it is authored**, and the pipeline validates the YAML
against it unchanged. It is not the published RDF shape: the emitter turns each authored `relates_to`
entry into one RDF predicate per verb (ADR 0041 D2).

| File | Edited by | Holds |
|---|---|---|
| `itpra.linkml.yaml` | hand | The shared `Term` record shape, one subclass per `type` value (per-type rules go in `slot_usage`), `RelatesTo`, predicate and class mappings (`slot_uri`, `class_uri`), and one slot per relationship verb carrying the `itpra_verb` annotation. Declares no `itpra:`/`itpra-o:`/`itpra-g:` prefix and no real `id:` itself — see "The base IRI is a configuration item" below |
| `generated/itpra-enums.linkml.yaml` | **generator only** | `EntityTypeEnum` and `RelationshipVerbEnum`, built from the vocabulary's `schema.yaml` |
| `generated/itpra-prefixes.linkml.yaml` | **generator only** | The `itpra:`/`itpra-o:`/`itpra-g:` prefix declarations, built from `itpra-onto.toml` `[iri]`. Imported by both files above |

## What is authored where

| Fact | Authored in | Reaches LinkML by |
|---|---|---|
| `type` value list | `schema.yaml` `types:` | `itpra-onto gen-enums` → `EntityTypeEnum` |
| Relationship verb list | `schema.yaml` `relationships:` | `itpra-onto gen-enums` → `RelationshipVerbEnum` |
| id pattern | `schema.yaml` `id.pattern` | copied into `itpra.linkml.yaml`. A test fails if the two differ |
| Record shape, per-type refinement | `itpra.linkml.yaml` only | — |
| Per-verb domain / range / cardinality / inverse | `itpra.linkml.yaml` only (`itpra_verb` annotations; ADR 0008) | — |
| Predicate and class IRIs | `itpra.linkml.yaml` only (`slot_uri`, `class_uri`) | — |

## The base IRI is a configuration item (ADR 0004)

The base IRI is **never hard-coded**. `itpra-onto.toml` `[iri]` (`base`, `id_path`, `onto_path`,
`graph_path`) is the single source; a base whose host ends in `.invalid` (the reserved TLD that never
resolves) is a placeholder that `itpra-onto release` refuses. The prefixes are `itpra:` = `<base>id/`,
`itpra-o:` = `<base>onto#` and `itpra-g:` = `<base>graph/` (named graphs).

Two mechanisms keep those IRIs out of the hand-authored `itpra.linkml.yaml`:

- **The three prefixes** are generated into `generated/itpra-prefixes.linkml.yaml` by
  `itpra-onto gen-prefixes` (`src/itpra_onto/gen_prefixes.py`), and `itpra.linkml.yaml` imports that
  fragment rather than declaring `itpra:`/`itpra-o:`/`itpra-g:` itself. LinkML merges an import's prefixes
  into the importing schema's namespace map without the importer redeclaring them (linkml-runtime 1.11.1).
- **The schema's own `id:`** cannot be inherited the same way — LinkML requires `id` to be present on the
  `SchemaDefinition` actually being loaded (constructing one without `id` raises `ValueError: id must be
  supplied`, even when an import supplies it). Rather than generating a second, physical copy of the whole
  schema file just to carry one field, `itpra.linkml.yaml`'s `id:` on disk holds a sentinel
  (`__GENERATED_SCHEMA_ID__`, never IRI-shaped) and `src/itpra_onto/schema_loading.py` substitutes the real
  value **in memory** at load time, before handing the schema to `SchemaView` or `Validator`. Every reader
  of the schema (`itpra-onto validate --authoring`, `gen-artifacts`, the test suite) goes through that
  module instead of pointing a `SchemaView`/`Validator` at the file path directly, so the substitution
  happens exactly once and `itpra.linkml.yaml` stays fully hand-authored and human-readable.

A schema loaded any other way than through `schema_loading` (for example the stock `linkml-validate` CLI
pointed straight at `itpra.linkml.yaml`) sees the sentinel, not a real IRI — one reason, beside the UTF-8
issue below, that this package validates in-process rather than shelling out.

Labels, definitions and statements are English. The emitter tags them `@en`, and the YAML stays free of
language tags.

## Regenerate / check

```sh
itpra-onto gen-enums              # rewrite generated/itpra-enums.linkml.yaml
itpra-onto gen-enums --check      # exit 1 if it is stale
itpra-onto gen-prefixes           # rewrite generated/itpra-prefixes.linkml.yaml
itpra-onto gen-prefixes --check   # exit 1 if it is stale
itpra-onto validate --authoring
python -m itpra_onto.profile      # per-verb profile read off the data
```

(Prefix each with `uv run` when the environment is not activated.)

Run `gen-enums` whenever `schema.yaml`'s `types:` or `relationships:` list changes, and `gen-prefixes`
whenever `itpra-onto.toml`'s `[iri]` table changes. Both outputs are sorted, use LF line endings and carry
no version stamp, so an ontology release that changes neither source leaves them untouched. Never merge a
generated file by hand. Regenerate it instead.

A new `type` value also needs a new subclass in `itpra.linkml.yaml`. A new verb also needs a new verb slot
with an `itpra_verb` annotation. The tests fail until both exist.

## How validation works

- **Term files** (`terms/*.yaml`, `entities.yaml` and `relationships.yaml` under `[paths] ontology_dir`)
  are bare top-level lists. No container is needed. Each record is checked against the subclass named by
  its `type`, and a `type` that names no subclass fails on the enum. A subclass pins its `type` with
  `slot_usage: {type: {pattern: "^<Value>$"}}`, not `equals_string`, because gen-shacl 1.11.1 rejects
  `equals_string` on an enum-typed slot.
- The JSON Schema plugin runs in **closed** mode, so an unknown key is an error. Files are read as UTF-8 by
  `itpra_onto.authoring`. The stock `linkml-validate` CLI's YAML loader opens files in the platform
  encoding (cp1252 on Windows).

JSON Schema can enforce these rules directly:

- id patterns
- required fields
- enums
- at least one `grouped_by` on Capability, Domain and Journey (`has_member`)
- at least one `supports` on Function
- no `derived_from` on Function (`all_members` / `none_of`; ADR 0011)

It cannot check these:

- at most one edge per verb
- the type of an edge's target
- whether an id resolves

Those rules live in the `itpra_verb` annotations, for the SHACL shapes (`../shapes/`).

## `itpra_verb` annotation grammar

The full grammar is in the header of `itpra.linkml.yaml`. In short, each of the 17 verb slots (subset
`verbs`, `slot_uri itpra-o:<camelCase>`) carries one annotation:

```yaml
annotations:
  itpra_verb:
    value:
      carried_by: relates_to
      evidence: data | meta-only | definition
      domain: [<Class>, …]          # = distinct subjects of pairs, sorted
      range: [<Class>, …]           # = distinct objects of pairs, sorted
      pairs: [{subject, object, count}]         # allowed combinations; count dated 3.14.0
      cardinality: [{subject, min, max|null}]   # declared rules only; subject Term = every record
      observed: [{subject, records, min, max}]  # read off the data, informational
      meta_edges: ["ENTITY -> ENTITY", …]       # entities.yaml relates_to, verbatim
      inverse_name: null                        # no named inverse is minted (ADR 0041 D4)
```

`<Class>` is a class in this schema. Where no `type` value exists, it is an UPPER_SNAKE EntityType id
instead (`SERVICE`, `ADR`, `REQUIREMENT`). The tests enforce four things:

- For every `evidence: data` verb, the declared `pairs` set equals the set read off the data.
- Every declared `cardinality` holds.
- `meta_edges` equals `entities.yaml`.
- `domain` and `range` are derived from `pairs`.

The `count` and `observed` numbers are dated to 3.14.0 and are **not** asserted. Refresh them from
`python -m itpra_onto.profile`.

## Class ↔ EntityType bridge

Each class carries `annotations: {entity_type_id: <ID> | none}`. The value is the `entities.yaml` record
the class is punned with:

| Class | EntityType |
|---|---|
| Capability | CAPABILITY |
| Function | FUNCTION |
| Persona | PERSONA |
| Journey | JOURNEY |
| Workflow | WORKFLOW |
| JourneyGroup | JOURNEY_GROUP |
| Domain | DOMAIN |
| Plane | PLANE |
| ServiceDomain | SERVICE_DOMAIN |
| QualityAttribute | QUALITY_ATTRIBUTE |
| Concept | CONCEPT |

Two classes have **none**: `EntityType` and `RelationshipType` are schema-namespace classes.

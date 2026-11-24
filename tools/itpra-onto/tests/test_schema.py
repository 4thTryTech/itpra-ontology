"""Tests for the LinkML authoring schema, the generated enums, and ``validate --authoring`` (ADR 0008).

Every test reads the real vocabulary files — nothing is ever written to them; mutation tests work on
in-memory copies.
"""

from __future__ import annotations

import copy
import subprocess
import sys
import warnings
from pathlib import Path

import pytest
import yaml
from linkml_runtime.utils.schemaview import SchemaView

from itpra_onto import gen_enums, schema_loading
from itpra_onto.authoring import AuthoringValidator, default_term_files
from itpra_onto.config import load_config
from itpra_onto.profile import compute_profile, load_records

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _expected_term_files() -> int:
    """The vocabulary's files counted off the directory (ADR 0007): top-level ``*.yaml`` but ``schema.yaml``
    and ``PIN.yaml``, plus ``terms/*.yaml`` — independent of :func:`default_term_files`."""
    root = gen_enums.ontology_dir()
    top = [p for p in root.glob("*.yaml") if p.name not in ("schema.yaml", "PIN.yaml")]
    return len(top) + len(list((root / "terms").glob("*.yaml")))


EXPECTED_TERM_FILES = _expected_term_files()


# ---------------------------------------------------------------------------------------------------
# fixtures


@pytest.fixture(scope="module")
def sv() -> SchemaView:
    return schema_loading.load_schema_view()


@pytest.fixture(scope="module")
def checker() -> AuthoringValidator:
    return AuthoringValidator()


@pytest.fixture(scope="module")
def ontology_schema_yaml() -> dict:
    with (gen_enums.ontology_dir() / "schema.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="module")
def verb_annotations(sv: SchemaView) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for name, slot in sv.all_slots().items():
        if "verbs" in (slot.in_subset or []):
            ann = slot.annotations["itpra_verb"].value
            out[name] = _plain(ann)
    return out


def _plain(value):
    """JsonObj / dict / list -> plain Python containers."""
    if hasattr(value, "_as_dict"):
        value = value._as_dict
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _load(path: Path):
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------------------------------
# schema loads


def test_schema_loads_with_generated_import(sv: SchemaView):
    assert sv.schema.name == "itpra"
    assert "EntityTypeEnum" in sv.all_enums()
    assert "RelationshipVerbEnum" in sv.all_enums()
    for cls in ("Term", "RelatesTo"):
        assert sv.get_class(cls) is not None, cls


def test_schema_iris_come_from_config(sv: SchemaView):
    """ADR 0004: the schema's id and its itpra:/itpra-o:/itpra-g: prefixes are never
    literals in this package — they are computed from itpra-onto.toml [iri] at load time
    (schema id) or generated from it (the prefixes, schema/generated/itpra-prefixes.linkml.yaml).
    This test reads the same config the schema was loaded against, never a hard-coded IRI."""
    config = load_config()
    assert sv.schema.id == config.iri.linkml_module_id(schema_loading.MAIN_MODULE_NAME)
    sv.imports_closure()
    namespaces = sv.namespaces()
    assert namespaces["itpra"] == config.iri.id_ns
    assert namespaces["itpra-o"] == config.iri.onto_ns
    assert namespaces["itpra-g"] == config.iri.graph_ns


def test_one_subclass_per_type_value(sv: SchemaView, checker: AuthoringValidator, ontology_schema_yaml: dict):
    assert sorted(checker.type_to_class) == sorted(ontology_schema_yaml["types"])
    # the data convention: a `type` value IS the LinkML class name
    assert all(value == cls for value, cls in checker.type_to_class.items())


def test_id_pattern_equals_ontology_schema_yaml(sv: SchemaView, ontology_schema_yaml: dict):
    assert sv.get_slot("id").pattern == ontology_schema_yaml["id"]["pattern"]


def test_real_slot_names_and_mappings(sv: SchemaView):
    """Slot-naming decision: the YAML keys `aliases` / `deprecated` are the slot names (no rename)."""
    term_slots = {s.name for s in sv.class_induced_slots("Term")}
    assert {"id", "term", "type", "definition", "aliases", "deprecated", "relates_to", "source", "retired", "replaced_by"} == term_slots
    aliases = sv.induced_slot("aliases", "Capability")
    deprecated = sv.induced_slot("deprecated", "Capability")
    assert aliases.multivalued and aliases.slot_uri == "skos:altLabel"
    assert deprecated.multivalued and deprecated.slot_uri == "itpra-o:bannedLabel"
    assert "skos:hiddenLabel" in deprecated.broad_mappings
    # the metamodel's element-level `deprecated`/`aliases` stay untouched on the class itself
    assert sv.get_class("Term").deprecated is None
    assert list(sv.get_class("Term").aliases) == []


def test_term_slots_are_schema_yaml_fields(sv: SchemaView, ontology_schema_yaml: dict):
    assert {s.name for s in sv.class_induced_slots("Term")} == set(ontology_schema_yaml["fields"])


def test_retirement_slots(sv: SchemaView):
    """ADR 0048: `retired` is an X.Y.Z version, projected as itpra-o:retiredIn; `replaced_by` a reference to
    another record, projected as dcterms:isReplacedBy."""
    retired = sv.induced_slot("retired", "Capability")
    replaced_by = sv.induced_slot("replaced_by", "Capability")
    assert retired.slot_uri == "itpra-o:retiredIn" and retired.pattern == "^[0-9]+\\.[0-9]+\\.[0-9]+$"
    assert replaced_by.slot_uri == "dcterms:isReplacedBy" and replaced_by.range == "Term"
    assert not retired.required and not replaced_by.required


def test_retired_record_validates_and_a_malformed_version_fails(checker, capability_file):
    ok = checker.validate_term_records(_mutate(capability_file, lambda r: r.update(retired="5.1.0", replaced_by="CAP-ITO-FND-2")))
    assert ok.ok, ok.errors
    bad = checker.validate_term_records(_mutate(capability_file, lambda r: r.update(retired="5.1")))
    assert not bad.ok and "does not match" in bad.errors[0]


def test_function_forbids_derived_from_in_schema(sv: SchemaView):
    rel = sv.induced_slot("relates_to", "Function").all_members.range_expression.slot_conditions["rel"]
    assert [x.equals_string for x in rel.none_of] == ["derived_from"]


def test_entity_type_bridge_annotations(sv: SchemaView):
    entities = {r["id"] for r in _load(gen_enums.ontology_dir() / "entities.yaml")}
    for cls_name in sv.class_descendants("Term", reflexive=False):
        ann = sv.get_class(cls_name).annotations["entity_type_id"].value
        assert ann == "none" or ann in entities, (cls_name, ann)


# ---------------------------------------------------------------------------------------------------
# generated enums


def test_generated_enums_equal_schema_yaml_lists(sv: SchemaView, ontology_schema_yaml: dict):
    assert set(sv.get_enum("EntityTypeEnum").permissible_values) == set(ontology_schema_yaml["types"])
    assert set(sv.get_enum("RelationshipVerbEnum").permissible_values) == set(
        ontology_schema_yaml["relationships"]
    )


def test_gen_enums_check_is_clean():
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "gen-enums", "--check"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_gen_enums_check_detects_stale(tmp_path: Path):
    stale = tmp_path / "itpra-enums.linkml.yaml"
    stale.write_text(gen_enums.generate().replace("  supports: {}\n", ""), encoding="utf-8", newline="\n")
    assert gen_enums.check(stale) is False
    assert gen_enums.check(tmp_path / "missing.yaml") is False


def test_gen_enums_is_deterministic(tmp_path: Path):
    first, second = gen_enums.generate(), gen_enums.generate()
    assert first == second
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    gen_enums.write(first, a)
    gen_enums.write(second, b)
    assert a.read_bytes() == b.read_bytes()
    assert b"\r\n" not in a.read_bytes()
    assert a.read_bytes() == gen_enums.GENERATED_ENUMS_PATH.read_bytes()


def test_gen_enums_follows_source_lists(tmp_path: Path):
    src = tmp_path / "schema.yaml"
    src.write_text("types: [B, A]\nrelationships: [z_verb, a_verb]\n", encoding="utf-8")
    text = gen_enums.generate(src)
    module = yaml.safe_load(text)
    assert list(module["enums"]["EntityTypeEnum"]["permissible_values"]) == ["A", "B"]
    assert list(module["enums"]["RelationshipVerbEnum"]["permissible_values"]) == ["a_verb", "z_verb"]


# ---------------------------------------------------------------------------------------------------
# the real files validate


def test_file_counts():
    assert len(default_term_files()) == EXPECTED_TERM_FILES


@pytest.mark.parametrize("path", default_term_files(), ids=lambda p: p.name)
def test_every_term_file_validates(checker: AuthoringValidator, path: Path):
    result = checker.validate_term_file(path)
    assert result.records > 0
    assert result.ok, "\n".join(result.errors)


def test_cli_validate_authoring_passes():
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "validate", "--authoring", "--quiet"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{EXPECTED_TERM_FILES}/{EXPECTED_TERM_FILES} files passed" in result.stdout


# ---------------------------------------------------------------------------------------------------
# mutated copies fail


@pytest.fixture(scope="module")
def function_file() -> list[dict]:
    path = next(p for p in default_term_files() if p.name == "functions-ito-fnd.yaml")
    return _load(path)


@pytest.fixture(scope="module")
def capability_file() -> list[dict]:
    path = next(p for p in default_term_files() if p.name == "capabilities-ito-fnd.yaml")
    return _load(path)


def _mutate(records: list[dict], fn) -> list[dict]:
    mutated = copy.deepcopy(records)
    fn(mutated[0])
    return mutated


def test_unmutated_copy_passes(checker, function_file, capability_file):
    assert checker.validate_term_records(copy.deepcopy(function_file)).ok
    assert checker.validate_term_records(copy.deepcopy(capability_file)).ok


def test_bad_id_fails(checker, function_file):
    result = checker.validate_term_records(_mutate(function_file, lambda r: r.update(id="1-BAD ID")))
    assert not result.ok and "does not match" in result.errors[0]


def test_unknown_type_fails(checker, function_file):
    result = checker.validate_term_records(_mutate(function_file, lambda r: r.update(type="Widget")))
    assert not result.ok and "'Widget' is not one of" in result.errors[0]


def test_unknown_verb_fails(checker, function_file):
    result = checker.validate_term_records(
        _mutate(function_file, lambda r: r["relates_to"].append({"rel": "likes", "target": "CAP-ITO-FND-1"}))
    )
    assert not result.ok and "'likes' is not one of" in result.errors[0]


def test_function_with_derived_from_fails(checker, function_file):
    result = checker.validate_term_records(
        _mutate(function_file, lambda r: r["relates_to"].append({"rel": "derived_from", "target": "CAP-ITO-FND-1"}))
    )
    assert not result.ok and "derived_from" in result.errors[0]


def test_derived_from_still_allowed_on_capability(checker, capability_file):
    result = checker.validate_term_records(
        _mutate(capability_file, lambda r: r["relates_to"].append({"rel": "derived_from", "target": "CAP-ITO-FND-2"}))
    )
    assert result.ok, result.errors


def test_capability_without_grouped_by_fails(checker, capability_file):
    def drop(r):
        r["relates_to"] = [e for e in r["relates_to"] if e["rel"] != "grouped_by"]

    result = checker.validate_term_records(_mutate(capability_file, drop))
    assert not result.ok and "does not contain items" in result.errors[0]


def test_unknown_key_fails(checker, function_file):
    result = checker.validate_term_records(_mutate(function_file, lambda r: r.update(colour="red")))
    assert not result.ok and "colour" in result.errors[0]


# ---------------------------------------------------------------------------------------------------
# verb annotations


def test_verb_annotations_cover_exactly_the_17_verbs(verb_annotations, ontology_schema_yaml):
    assert len(ontology_schema_yaml["relationships"]) == 17
    assert set(verb_annotations) == set(ontology_schema_yaml["relationships"])


def test_verb_annotation_grammar(sv: SchemaView, verb_annotations):
    entity_type_ids = {r["id"] for r in _load(gen_enums.ontology_dir() / "entities.yaml")}
    known = set(sv.all_classes()) | entity_type_ids
    keys = {"carried_by", "evidence", "domain", "range", "pairs", "cardinality", "observed", "meta_edges", "inverse_name"}
    for verb, ann in verb_annotations.items():
        assert set(ann) == keys, verb
        assert ann["inverse_name"] is None, verb  # no inverse is minted (ADR 0041 D4)
        assert ann["evidence"] in {"data", "meta-only", "definition"}, verb
        assert ann["carried_by"] == "relates_to", verb
        assert ann["domain"] == sorted({p["subject"] for p in ann["pairs"]}), verb
        assert ann["range"] == sorted({p["object"] for p in ann["pairs"]}), verb
        for token in ann["domain"] + ann["range"] + [c["subject"] for c in ann["cardinality"]]:
            assert token in known, (verb, token)
        slot = sv.get_slot(verb)
        camel = verb.split("_")[0] + "".join(w.title() for w in verb.split("_")[1:])
        assert slot.slot_uri == f"itpra-o:{camel}", verb  # verbs live in the onto# namespace (ADR 0004)


def test_verb_annotations_match_the_data(verb_annotations):
    """Domain/range are read off the data: declared pairs == data pairs for every `evidence: data` verb,
    and no data exists for the others.

    The numeric `pairs[].count` and `observed[]` fields are a labelled SNAPSHOT (the schema header names the
    ontology version they were read at), not a governing fact: this test checks the semantic facts — which
    (subject, object) pairs exist, the meta-edges, that nothing is unresolved — exactly, and reports count
    drift as a pytest warning rather than a failure, so a routine term mint does not break the pipeline job
    (counts are refreshed with `python -m itpra_onto.profile` when the schema is re-profiled).
    """
    profile = compute_profile()
    for verb, ann in verb_annotations.items():
        data_pairs = set(profile[verb].pairs) if verb in profile else set()
        declared = {(p["subject"], p["object"]) for p in ann["pairs"]}
        if ann["evidence"] == "data":
            assert data_pairs == declared, (verb, sorted(data_pairs ^ declared))
        else:
            assert data_pairs == set(), verb
        assert not (profile[verb].unresolved if verb in profile else {}), verb
        meta = sorted(profile[verb].meta_edges) if verb in profile else []
        assert meta == sorted(ann["meta_edges"]), verb

        if ann["evidence"] == "data":
            declared_counts = {(p["subject"], p["object"]): p["count"] for p in ann["pairs"]}
            data_counts = dict(profile[verb].pairs) if verb in profile else {}
            if declared_counts != data_counts:
                warnings.warn(f"{verb}: itpra_verb pairs[].count is a stale snapshot; refresh with `python -m itpra_onto.profile`", stacklevel=1)

            declared_observed = {o["subject"]: (o["records"], o["min"], o["max"]) for o in ann["observed"]}
            per_record = profile[verb].per_record if verb in profile else {}
            data_observed = {
                subj: (sum(counts.values()), min(counts), max(counts)) for subj, counts in per_record.items()
            }
            if declared_observed != data_observed:
                warnings.warn(f"{verb}: itpra_verb observed[] is a stale snapshot; refresh with `python -m itpra_onto.profile`", stacklevel=1)
        else:
            # meta-only / definition evidence: zero instances, so `pairs`/`observed` carry a placeholder
            # count: 0 (the candidate pair, not a measured one) rather than a live count to refresh.
            assert all(p["count"] == 0 for p in ann["pairs"]), (verb, "0-instance verb must declare count: 0")
            assert ann["observed"] == [], (verb, "0-instance verb must declare observed: []")


def test_declared_cardinalities_hold_in_the_data(verb_annotations):
    records = load_records()
    for verb, ann in verb_annotations.items():
        for rule in ann["cardinality"]:
            subjects = [r for r in records if rule["subject"] in ("Term", r["type"]) and r["type"] != "EntityType"]
            assert subjects or rule["max"] == 0, (verb, rule)
            for rec in subjects:
                n = sum(1 for e in rec.get("relates_to") or [] if e["rel"] == verb)
                assert n >= rule["min"], (verb, rule, rec["id"], n)
                assert rule["max"] is None or n <= rule["max"], (verb, rule, rec["id"], n)

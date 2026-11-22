"""Tests for ``itpra_onto.gen_verb_shapes`` (``itpra-onto gen-verb-shapes``) and rule B-22 (ADR 0042 D2).

The generated ``shapes/generated/verb-pairs.ttl`` is committed; these tests prove it is current (``--check``),
deterministic, detects staleness, resolves classes exactly as ``emit.Vocabulary`` does, covers every verb,
carries no base IRI, loads through ``shacl.load_shapes``, and raises zero findings on the real corpus. That
B-22 FIRES is proven by ``fixtures/structural/B-22-*.yaml`` (``test_shapes_structural.py``) plus the direct
checks below (a multi-typed subject, a dangling object, an unresolvable pair).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pyoxigraph as ox
import pytest

from itpra_onto import emit, gen_verb_shapes, rules, schema_loading, shacl
from itpra_onto.config import Config, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


@pytest.fixture(scope="module")
def vocab(config: Config) -> emit.Vocabulary:
    return emit.Vocabulary(config, schema_loading.load_schema_view(config=config))


@pytest.fixture(scope="module")
def clean_dataset(config: Config) -> ox.Dataset:
    return rules.apply_rules(emit.emit(config=config), config).dataset


@pytest.fixture(scope="module")
def generated_only(tmp_path_factory: pytest.TempPathFactory, config: Config) -> ox.Dataset:
    """Only the generated shapes (a shapes dir whose sole content is generated/verb-pairs.ttl)."""
    directory = tmp_path_factory.mktemp("generated-only")
    (directory / shacl.GENERATED_SUBDIR).mkdir()
    (directory / shacl.GENERATED_SUBDIR / "verb-pairs.ttl").write_bytes(gen_verb_shapes.VERB_PAIRS_PATH.read_bytes())
    return shacl.load_shapes(directory, config=config)


def test_committed_file_is_up_to_date():
    assert gen_verb_shapes.check(), "shapes/generated/verb-pairs.ttl is stale - run `itpra-onto gen-verb-shapes`"


def test_generation_is_deterministic():
    first = gen_verb_shapes.generate()
    second = gen_verb_shapes.generate()
    assert first == second
    assert "\r" not in first
    assert first.startswith("# GENERATED FILE - DO NOT EDIT BY HAND.")


def test_check_detects_a_stale_or_missing_file(tmp_path: Path):
    stale = tmp_path / "verb-pairs.ttl"
    assert not gen_verb_shapes.check(stale)  # missing
    stale.write_text(gen_verb_shapes.generate() + "# edited by hand\n", encoding="utf-8", newline="\n")
    assert not gen_verb_shapes.check(stale)
    stale.write_text(gen_verb_shapes.generate(), encoding="utf-8", newline="\n")
    assert gen_verb_shapes.check(stale)


def test_cli_gen_verb_shapes_check_exits_0():
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "gen-verb-shapes", "--check"],
        cwd=PROJECT_ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    assert "is up to date" in result.stdout


def test_record_classes_are_the_emitters_class_table(vocab: emit.Vocabulary):
    """Classes resolve through the schema's class table exactly as emit.Vocabulary pins records to them."""
    curies = gen_verb_shapes.record_classes(vocab.sv)
    expanded = {vocab.expand(curie) for curie in curies.values()}
    assert expanded == set(vocab.term_class.values()) | set(vocab.requirement_class.values())
    assert curies["EntityType"] == "itpra-o:EntityType"
    assert curies["FR"] == "itpra:FR" and curies["NFR"] == "itpra:NFR"


def test_every_verb_gets_one_shape_with_rule_id_b22(config: Config, vocab: emit.Vocabulary):
    entries = gen_verb_shapes.read_verb_pairs(vocab.sv, config)
    assert [e.verb for e in entries] == vocab.verb_slots  # all 17, every evidence class
    shapes = shacl.load_shapes(shacl.SHAPES_DIR, config=config)
    rule_ids = shacl._shape_rule_ids(shapes, config)
    for entry in entries:
        shape = config.iri.onto_ns + gen_verb_shapes._shape_name(entry.verb)
        assert rule_ids.get(shape) == "B-22", entry.verb


def test_pairs_match_the_annotations_and_unresolvable_pairs_are_reported(config: Config, vocab: emit.Vocabulary):
    by_verb = {e.verb: e for e in gen_verb_shapes.read_verb_pairs(vocab.sv, config)}
    assert by_verb["grouped_by"].pair_names == (("Capability", "Domain"), ("Domain", "Plane"), ("Journey", "JourneyGroup"))
    assert by_verb["met_by"].predicate == "itpra-o:metBy"
    assert by_verb["categorized_as"].predicate == "itpra-o:categorizedAs"
    # annotation grammar: an UPPER_SNAKE EntityType id where no class exists — no record can match it
    assert by_verb["supersedes"].pairs == () and by_verb["supersedes"].unresolved == (("ADR", "ADR"),)
    assert by_verb["produces"].unresolved == (("SERVICE", "Capability"),)


def test_generated_file_carries_no_base_iri_and_no_prefix_block(config: Config):
    text = gen_verb_shapes.VERB_PAIRS_PATH.read_text(encoding="utf-8")
    assert config.iri.base not in text
    assert not [line for line in text.splitlines() if line.lstrip().startswith("@prefix")]


def test_zero_b22_findings_on_the_real_corpus(config: Config, clean_dataset: ox.Dataset, generated_only: ox.Dataset):
    """If this fails it is a DATA finding (a real edge outside its verb's declared pairs), never a reason to
    weaken the generated shape."""
    report = shacl.validate(clean_dataset, generated_only, config=config)
    assert report.findings == (), "\n".join(f"{f.focus} {f.message}" for f in report.findings)


def _with_quads(dataset: ox.Dataset, config: Config, *triples: tuple[str, str, str]) -> ox.Dataset:
    copy = ox.Dataset(dataset)
    t1 = ox.NamedNode(config.iri.graph_ns + "t1")
    for s, p, o in triples:
        copy.add(ox.Quad(ox.NamedNode(s), ox.NamedNode(p), ox.NamedNode(o), t1))
    return copy


def test_b22_fires_on_a_wrong_pair_and_names_verb_and_classes(config: Config, clean_dataset: ox.Dataset, generated_only: ox.Dataset):
    idn, onto = config.iri.id_ns, config.iri.onto_ns
    mutated = _with_quads(clean_dataset, config, (idn + "CAP-FND-1", onto + "consumedBy", idn + "FUNC-version-control"))
    report = shacl.validate(mutated, generated_only, config=config)
    assert [(f.rule_id, shacl.focus_local_name(f.focus, config)) for f in report.findings] == [("B-22", "CAP-FND-1")]
    message = report.findings[0].message
    assert "consumed_by" in message and "CAPABILITY" in message and "FUNCTION" in message


def test_b22_ignores_a_dangling_object(config: Config, clean_dataset: ox.Dataset, generated_only: ox.Dataset):
    """A dangling object is target-unresolved's business, not B-22's."""
    idn, onto = config.iri.id_ns, config.iri.onto_ns
    mutated = _with_quads(clean_dataset, config, (idn + "CAP-FND-1", onto + "consumedBy", idn + "PERSONA-does-not-exist"))
    assert shacl.validate(mutated, generated_only, config=config).findings == ()


def test_b22_tests_membership_not_equality_for_a_multi_typed_subject(config: Config, clean_dataset: ox.Dataset, generated_only: ox.Dataset):
    """A subject carrying an allowed class AND another record class (e.g. two colliding records) is allowed
    when ANY of its classes forms an allowed pair — the skos:Concept type every record carries never counts."""
    idn = config.iri.id_ns
    # JRN-adm-onboard-developer grouped_by JG-ONBOARDING is allowed (Journey, JourneyGroup); also typing the
    # journey a Persona must not make the (Persona, JourneyGroup) combination fire.
    mutated = _with_quads(clean_dataset, config, (idn + "JRN-adm-onboard-developer", emit.RDF + "type", idn + "PERSONA"))
    report = shacl.validate(mutated, generated_only, config=config)
    assert report.findings == (), "\n".join(f"{f.focus} {f.message}" for f in report.findings)


def test_b22_fires_for_a_verb_whose_pairs_are_all_unresolvable(config: Config, clean_dataset: ox.Dataset, generated_only: ox.Dataset):
    """supersedes allows only (ADR, ADR) — no record class — so any edge between two records fires."""
    idn, onto = config.iri.id_ns, config.iri.onto_ns
    mutated = _with_quads(clean_dataset, config, (idn + "CAP-FND-1", onto + "supersedes", idn + "CAP-FND-2"))
    report = shacl.validate(mutated, generated_only, config=config)
    assert [(f.rule_id, shacl.focus_local_name(f.focus, config)) for f in report.findings] == [("B-22", "CAP-FND-1")]

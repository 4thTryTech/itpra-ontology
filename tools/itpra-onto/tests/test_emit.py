"""Tests for the RDF emitter (``itpra_onto.emit``; ADR 0041).

Every test reads the REAL input files (the vocabulary); nothing is ever written to them. Alternative
configs are written to ``tmp_path`` only. IRIs are always built from the loaded config, never typed here
(ADR 0004; ``test_iri_config.py`` scans this file too).
"""

from __future__ import annotations

import re
import time
from collections import Counter
from pathlib import Path

import pyoxigraph as ox
import pytest

from itpra_onto import emit, schema_loading
from itpra_onto.authoring import default_term_files
from itpra_onto.config import DEFAULT_CONFIG_PATH, Config, load_config
from itpra_onto.emit import InputPathError, parse_source
from itpra_onto.profile import compute_profile, load_records
EXPECTED_VERBS = 17
LANG_TAGGED_SLOTS = ("term", "definition", "aliases", "deprecated")
UNTAGGED_SLOTS = ("id", "source")


# ---------------------------------------------------------------------------------------------------
# fixtures and helpers


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


@pytest.fixture(scope="module")
def dataset(config: Config) -> ox.Dataset:
    started = time.perf_counter()
    result = emit.emit(config=config)
    print(f"\nemit(): {len(result)} quads in {time.perf_counter() - started:.2f}s (full corpus, incl. load)")
    return result


@pytest.fixture(scope="module")
def vocab(config: Config) -> emit.Vocabulary:
    return emit.Vocabulary(config, schema_loading.load_schema_view(config=config))


def _graph(config: Config, local: str) -> ox.NamedNode:
    return ox.NamedNode(config.iri.graph_ns + local)


def _match(dataset: ox.Dataset, s=None, p=None, o=None, g=None) -> list[ox.Quad]:
    """Quads matching a pattern (``pyoxigraph.Dataset`` 0.5.11 has per-position lookups only)."""
    return [
        q for q in dataset.quads_for_predicate(p)
        if (s is None or q.subject == s) and (o is None or q.object == o) and (g is None or q.graph_name == g)
    ]


def _instance_quads(dataset: ox.Dataset, config: Config) -> list[ox.Quad]:
    """Quads in ``t1``."""
    t1 = config.iri.graph_ns + "t1"
    return [q for q in dataset if isinstance(q.graph_name, ox.NamedNode) and q.graph_name.value == t1]


def _sorted_nquads(dataset: ox.Dataset) -> list[str]:
    """RDFC-1.0 canonicalise, serialise N-Quads, sort lines (the build's recipe, ADR 0041 D5)."""
    dataset.canonicalize(ox.CanonicalizationAlgorithm.RDFC_1_0)
    raw = ox.serialize(dataset, format=ox.RdfFormat.N_QUADS).decode("utf-8")
    return sorted(raw.splitlines(keepends=True))


def _write_config(tmp_path: Path, **paths: str) -> Path:
    """A temp copy of the shipped itpra-onto.toml with the named [paths] keys replaced."""
    text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
    paths.setdefault("repo_root", load_config().repo_root.as_posix())  # the copy lives under tmp_path; the root stays real
    for key, value in paths.items():
        text, count = re.subn(rf'^{key} = "[^"]*"', f'{key} = "{value}"', text, count=1, flags=re.M)
        assert count == 1, key
    path = tmp_path / "itpra-onto.toml"
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------------------------------
# inputs and the input-path guard (ADR 0043 D1)


def test_term_file_set_equals_the_authoring_set(config: Config):
    """The emitter's term-file rule (recursive, all but schema.yaml) equals the authoring validator's
    enumeration (terms/*.yaml + entities.yaml + relationships.yaml)."""
    assert set(emit.term_files(config)) == set(default_term_files())


def test_shipped_config_passes_the_guard(config: Config):
    inputs = emit.load_inputs(config)
    assert inputs.terms
    assert inputs.ontology_version
    for path in emit.term_files(config):
        assert emit.guard_input_path(path, repo_root=config.repo_root) == path


def test_guard_refuses_a_worktree_ontology_dir_given_relatively(tmp_path: Path):
    """``../../.cache/worktrees/x`` relative to a config outside the repository escapes the root (rule a)."""
    config = load_config(_write_config(tmp_path, ontology_dir="../../.cache/worktrees/x"))
    with pytest.raises(InputPathError, match=r"rule \(a\)"):
        emit.load_inputs(config)


def test_guard_refuses_a_worktree_ontology_dir_inside_the_repository(tmp_path: Path, config: Config):
    target = (config.repo_root / ".cache" / "worktrees" / "x").as_posix()
    config = load_config(_write_config(tmp_path, ontology_dir=target))
    with pytest.raises(InputPathError, match=r"rule \(b\).*\.cache"):
        emit.load_inputs(config)


@pytest.mark.parametrize(
    ("relative", "rule"),
    [
        (".git/config.yaml", "b"),
        ("tools/x/.venv/x.yaml", "b"),
        ("dist/t1.yaml", "c"),
        ("public/x.yaml", "c"),
        ("terms/README.md", "d"),
        # dist/, public/ and __pycache__/ are generated output at ANY depth, never an input: a nested
        # occurrence of any of these names is refused too, not only a first path component.
        ("terms/dist/leak.yaml", "c"),
        ("terms/public/leak.yaml", "c"),
        ("terms/__pycache__/leak.yaml", "c"),
        ("a/b/docs/dist/leak.yaml", "c"),
        # case-insensitive, like every other name comparison in this pipeline
        ("terms/DIST/leak.yaml", "c"),
    ],
)
def test_guard_rules(relative: str, rule: str, config: Config):
    with pytest.raises(InputPathError, match=rf"rule \({rule}\)"):
        emit.guard_input_path(config.repo_root / relative, repo_root=config.repo_root)


def test_guard_rule_a_is_the_configured_repository_root(tmp_path: Path, config: Config):
    """``repo_root`` comes from the configuration ([paths] repo_root), not from where the package is installed."""
    other = tmp_path / "elsewhere" / "terms" / "x.yaml"
    with pytest.raises(InputPathError, match=r"rule \(a\)"):
        emit.guard_input_path(other, repo_root=config.repo_root)
    assert emit.guard_input_path(other, repo_root=tmp_path) == other


def test_guard_refuses_excluded_names_at_any_depth_only_when_given(config: Config):
    """Names passed as ``excluded`` are refused at any depth, case-insensitively; the same path passes when
    nothing is excluded. No path here exists on disk; :func:`emit.guard_input_path` checks shape, never
    existence."""
    root = config.repo_root
    nested = root / "some" / "Drafts" / "x.yaml"
    with pytest.raises(InputPathError, match=r"rule \(c\).*Drafts"):
        emit.guard_input_path(nested, repo_root=root, excluded=("drafts",))
    assert emit.guard_input_path(nested, repo_root=root) == nested
    top = root / "private" / "acme" / "x.yaml"
    with pytest.raises(InputPathError, match=r"rule \(c\).*private"):
        emit.guard_input_path(top, repo_root=root, excluded=("private",))


# ---------------------------------------------------------------------------------------------------
# IRI discipline: the type -> class table comes from the schema


def test_type_to_class_table(config: Config, vocab: emit.Vocabulary):
    id_ns, onto_ns = config.iri.id_ns, config.iri.onto_ns
    table = {k: v.value for k, v in vocab.term_class.items()}
    assert table["Capability"] == id_ns + "CAPABILITY"
    assert table["ServiceDomain"] == id_ns + "SERVICE_DOMAIN"
    assert table["JourneyGroup"] == id_ns + "JOURNEY_GROUP"
    assert table["Concept"] == id_ns + "CONCEPT"
    assert table["EntityType"] == onto_ns + "EntityType"
    assert table["RelationshipType"] == onto_ns + "RelationshipType"


def test_stale_schema_prefixes_fail_loudly(tmp_path: Path):
    """The schema's itpra: prefixes are generated from the shipped config; a config with another base must
    regenerate them first rather than emit a mixed-base graph."""
    text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
    alt = tmp_path / "itpra-onto.toml"
    alt.write_text(re.sub(r'base = "[^"]*"', 'base = "https://example.test/ns/alt/"', text, count=1), encoding="utf-8")
    alt_config = load_config(alt)
    with pytest.raises(emit.EmitError, match="gen-prefixes"):
        emit.Vocabulary(alt_config, schema_loading.load_schema_view(config=alt_config))


# ---------------------------------------------------------------------------------------------------
# the `source` grammar (ADR 0005)


def test_parse_single_adr():
    assert parse_source("ADR 0001") == emit.ParsedSource(decided_in=("ADR-0001",))


def test_parse_two_adrs_semicolon_separated():
    parsed = parse_source("ADR 0017; ADR 0252")
    assert parsed.decided_in == ("ADR-0017", "ADR-0252")
    assert parsed.amended_by == parsed.extended_by == parsed.external == ()


def test_parse_amended_tail_with_two_adrs():
    parsed = parse_source("ADR 0071 (amended by ADR 0233, ADR 0252)")
    assert parsed.decided_in == ("ADR-0071", "ADR-0233", "ADR-0252")
    assert parsed.amended_by == ("ADR-0233", "ADR-0252")
    assert parsed.extended_by == ()


def test_parse_extended_tail():
    parsed = parse_source("ADR 0234 (extended by ADR 0252)")
    assert parsed.decided_in == ("ADR-0234", "ADR-0252")
    assert parsed.extended_by == ("ADR-0252",)
    assert parsed.amended_by == ()


def test_parse_external_citation_only():
    parsed = parse_source("ISO/IEC 25010; well-architected")
    assert parsed.decided_in == ()
    assert parsed.external == ("ISO/IEC 25010", "well-architected")


def test_parse_external_citation_with_adr():
    parsed = parse_source("ISO/IEC 25010 (functional suitability); NIST AI RMF (valid and reliable); ADR 0140")
    assert parsed.decided_in == ("ADR-0140",)
    assert parsed.external == ("ISO/IEC 25010 (functional suitability)", "NIST AI RMF (valid and reliable)")


def test_parse_normalises_whitespace_and_pads():
    assert parse_source("ADR 7\n  (amended by ADR 12)").amended_by == ("ADR-0012",)


# ---- the strict ADR grammar (ADR 0005) -------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # a semicolon INSIDE the parens is not a top-level item separator (_split_top_level_items) --
        # this is one item mixing an amended tail and an extended tail, which the grammar does not allow
        "ADR 0071 (amended by ADR 0233; extended by ADR 0252)",
        "(Amended by ADR 0233)",  # no leading "ADR NNNN"
        "ADR-0012",  # hyphen, not a space, after "ADR"
        "ADRs 0012 and 0034",  # plural "ADRs", and free text after the number
        "(superseded by ADR 0099)",  # no leading "ADR NNNN"
    ],
)
def test_parse_source_rejects_grammar_violations(text: str):
    with pytest.raises(emit.SourceGrammarError):
        parse_source(text)


def test_parse_source_error_names_the_record_id_and_the_item():
    with pytest.raises(emit.SourceGrammarError, match=re.escape("CAP-FND-1") + ".*" + re.escape("ADR-0012")):
        parse_source("ADR-0012", record_id="CAP-FND-1")


def test_parse_source_still_accepts_every_previously_valid_case():
    """The rejections above must not have narrowed what the existing, already-tested valid grammar accepts
    (test_parse_single_adr and its neighbours above, re-run here as a group)."""
    assert parse_source("ADR 0001") == emit.ParsedSource(decided_in=("ADR-0001",))
    assert parse_source("ADR 0017; ADR 0252").decided_in == ("ADR-0017", "ADR-0252")
    amended = parse_source("ADR 0071 (amended by ADR 0233, ADR 0252)")
    assert amended.decided_in == ("ADR-0071", "ADR-0233", "ADR-0252")
    assert amended.amended_by == ("ADR-0233", "ADR-0252")
    extended = parse_source("ADR 0234 (extended by ADR 0252)")
    assert extended.extended_by == ("ADR-0252",)
    external = parse_source("ISO/IEC 25010; well-architected")
    assert external.decided_in == ()
    assert external.external == ("ISO/IEC 25010", "well-architected")
    mixed = parse_source("ISO/IEC 25010 (functional suitability); NIST AI RMF (valid and reliable); ADR 0140")
    assert mixed.decided_in == ("ADR-0140",)
    assert parse_source("ADR 7\n  (amended by ADR 12)").amended_by == ("ADR-0012",)


def test_parse_source_treats_a_url_bearing_item_as_an_external_citation_even_when_it_mentions_adr():
    """Another project's decision record is cited as any citable reference would be -- free text carrying its
    URL -- and never becomes a ``decidedIn`` link; a bare ``ADR NNNN`` is a record of THIS repository's own
    decision sequence (ADR 0005)."""
    other = "ITPRA ontology ADR 0003 (https://github.com/4thtrytech/itpra-ontology/blob/main/decisions/0003-x.md)"
    parsed = parse_source(f"ADR 0017; {other}")
    assert parsed.decided_in == ("ADR-0017",)
    assert parsed.amended_by == () and parsed.extended_by == ()
    assert parsed.external == (other,)
    # a URL-bearing item is external in its entirety, even one whose text looks like a local tail
    tail_like = "see ADR 0017 (amended by ADR 0252) at https://example.test/decisions/0017"
    assert parse_source(tail_like) == emit.ParsedSource(external=(tail_like,))


def test_parse_source_still_rejects_an_adr_mention_without_a_url_that_is_not_the_local_grammar():
    """Without a URL the typo guard stands: an item that mentions a decision record must be this repository's
    own ``ADR NNNN`` form."""
    with pytest.raises(emit.SourceGrammarError):
        parse_source("ITPRA ontology ADR 0003")


def test_parse_source_full_corpus_never_trips_the_grammar(config: Config):
    """Every ``source`` value across the real, authored ontology must already conform to ADR 0005's
    grammar (0 of the corpus's records trip it) -- confirming the strict check is a no-op on today's data,
    not merely on the handful of unit-tested strings above."""
    inputs = emit.load_inputs(config)
    checked = 0
    for term in inputs.terms:
        source = term.record.get("source")
        if source is not None:
            parse_source(str(source), record_id=term.record["id"])  # raises SourceGrammarError on failure
            checked += 1
    assert checked > 0
    print(f"\nsource grammar: {checked} records with a source value, 0 grammar violations")


# ---------------------------------------------------------------------------------------------------
# acceptance: the CAP-FND-1 worked example, byte for byte after canonicalisation


def test_emit_is_deterministic(config: Config):
    inputs = emit.load_inputs(config)
    first = _sorted_nquads(emit.emit(inputs, config))
    second = _sorted_nquads(emit.emit(emit.load_inputs(config), config))
    assert "".join(first).encode("utf-8") == "".join(second).encode("utf-8")


def test_no_blank_nodes_and_no_default_graph(dataset: ox.Dataset):
    blank = [q for q in dataset if isinstance(q.subject, ox.BlankNode) or isinstance(q.object, ox.BlankNode)]
    assert blank == []
    assert list(dataset.quads_for_graph_name(ox.DefaultGraph())) == []


def test_per_graph_quad_counts_reported(dataset: ox.Dataset):
    counts = Counter(q.graph_name.value for q in dataset)
    for graph, n in sorted(counts.items()):
        print(f"  {graph}: {n}")
    assert sum(counts.values()) == len(dataset)


# ---------------------------------------------------------------------------------------------------
# coverage against the authored data


def test_per_verb_edge_counts_equal_the_profile(dataset: ox.Dataset, config: Config, vocab: emit.Vocabulary):
    profile = compute_profile()
    emitted = Counter(q.predicate.value for q in _instance_quads(dataset, config))
    for verb in vocab.verb_slots:
        expected = sum(profile[verb].pairs.values()) if verb in profile else 0
        assert emitted[vocab.verb[verb].value] == expected, verb


def test_record_counts_per_type(dataset: ox.Dataset, config: Config, vocab: emit.Vocabulary):
    terms = load_records()
    t1 = _graph(config, "t1")
    for type_value, expected in Counter(r["type"] for r in terms).items():
        cls = vocab.term_class[type_value]
        typed = {q.subject for q in _match(dataset, None, emit.RDF_TYPE, cls, t1)}
        assert len(typed) == expected, type_value


# ---------------------------------------------------------------------------------------------------
# the schema graph (thin OWL; ADR 0041 D2)


def test_every_entity_type_is_an_owl_class(dataset: ox.Dataset, config: Config):
    schema = _graph(config, "schema")
    entity_types = [t.record["id"] for t in emit.load_inputs(config).terms if t.record["type"] == "EntityType"]
    assert entity_types
    for eid in entity_types:
        node = ox.NamedNode(config.iri.id_ns + eid)
        assert ox.Quad(node, emit.RDF_TYPE, emit.OWL_CLASS, schema) in dataset, eid
        assert ox.Quad(node, emit.RDFS_SUBCLASS_OF, emit.SKOS_CONCEPT, schema) in dataset, eid


def test_seventeen_verb_properties_with_see_also(dataset: ox.Dataset, config: Config, vocab: emit.Vocabulary):
    schema = _graph(config, "schema")
    assert len(vocab.verb_slots) == EXPECTED_VERBS
    for name in vocab.verb_slots:
        prop = vocab.verb[name]
        assert ox.Quad(prop, emit.RDF_TYPE, emit.OWL_OBJECT_PROPERTY, schema) in dataset, name
        see_also = [q.object for q in _match(dataset, prop, emit.RDFS_SEE_ALSO, None, schema)]
        assert see_also == [ox.NamedNode(config.iri.id_ns + name)], name


def test_no_domain_range_or_inverse_axioms(dataset: ox.Dataset):
    forbidden = {emit.RDFS + "domain", emit.RDFS + "range", emit.OWL + "inverseOf", emit.OWL + "FunctionalProperty"}
    assert [q for q in dataset if q.predicate.value in forbidden or q.object.value in forbidden] == []


# ---------------------------------------------------------------------------------------------------
# SKOS integrity and language tags


def test_no_alt_label_equals_its_own_pref_label(dataset: ox.Dataset, vocab: emit.Vocabulary):
    """Compared case-insensitively (ADR 0007 is itself case-insensitive on this point), so an alias differing
    from the pref label only in case is caught too, not just an exact-string match."""
    pref = {q.subject: q.object.value for q in dataset.quads_for_predicate(vocab.slot_iri("term"))}
    offenders = sorted(
        q.subject.value for q in dataset.quads_for_predicate(vocab.slot_iri("aliases"))
        if q.object.value.lower() == (pref.get(q.subject) or "").lower()
    )
    assert offenders == []


def test_language_tags(dataset: ox.Dataset, vocab: emit.Vocabulary, config: Config):
    for slot_name in LANG_TAGGED_SLOTS:
        literals = [q.object for q in dataset.quads_for_predicate(vocab.slot_iri(slot_name))]
        assert literals, slot_name
        assert {lit.language for lit in literals} == {emit.LANG}, slot_name
    untagged = [vocab.slot_iri(s) for s in UNTAGGED_SLOTS] + [vocab.onto(emit.AUTHORING_FILE)]
    for predicate in untagged:
        literals = [q.object for q in dataset.quads_for_predicate(predicate) if isinstance(q.object, ox.Literal)]
        assert all(lit.language is None for lit in literals), predicate.value


def test_decided_in_links(dataset: ox.Dataset, config: Config):
    """Every record with a ``source`` naming an ADR gets ``decidedIn`` to an ``ADR-NNNN`` node."""
    decided = list(dataset.quads_for_predicate(ox.NamedNode(config.iri.onto_ns + emit.DECIDED_IN)))
    assert decided
    assert all(re.fullmatch(re.escape(config.iri.id_ns) + r"ADR-\d{4,}", q.object.value) for q in decided)


# ---------------------------------------------------------------------------------------------------
# dangling references


def test_dangling_object_iris_reported(dataset: ox.Dataset, config: Config):
    """The real corpus must have NO dangling object IRIs — this asserts the empty set, not
    merely that a set comes back (an ``isinstance`` check alone would pass even if the corpus regressed)."""
    dangling = emit.dangling_object_iris(dataset, config)
    print(f"\ndangling object IRIs: {len(dangling)}")
    for iri in sorted(dangling):
        print(f"  {iri}")
    assert dangling == set()


# ---------------------------------------------------------------------------------------------------
# every input-shape defect is an EmitError (never a KeyError/TypeError/ValueError), and names
# the offending record (`EmitError.record_id`) when there is one.


def _term(record: dict) -> emit.TermRecord:
    return emit.TermRecord(record=record, file="terms/fixture.yaml")


_GOOD_TERM = {"id": "CAP-FIXTURE-1", "term": "Fixture", "type": "Capability", "definition": "A fixture."}


def test_term_file_that_is_not_a_list_is_an_emit_error(tmp_path: Path):
    """A term file rewritten as a mapping used to be iterated key by key."""
    path = tmp_path / "mapping.yaml"
    path.write_text("CAP-X: {id: CAP-X}\n", encoding="utf-8")
    with pytest.raises(emit.EmitError, match="must be a top-level list"):
        emit._term_file_records(path)


def test_term_file_entry_that_is_not_a_mapping_is_an_emit_error(tmp_path: Path):
    path = tmp_path / "list.yaml"
    path.write_text("- just a string\n", encoding="utf-8")
    with pytest.raises(emit.EmitError, match=r"record \[0\] is not a mapping"):
        emit._term_file_records(path)


def test_empty_term_file_is_no_records(tmp_path: Path):
    path = tmp_path / "empty.yaml"
    path.write_text("", encoding="utf-8")
    assert emit._term_file_records(path) == []


@pytest.mark.parametrize("field", ["id", "type"])
@pytest.mark.parametrize("value", [None, 7, "", "   ", ["CAP-X"]])
def test_term_without_a_string_id_or_type_is_an_emit_error(vocab: emit.Vocabulary, field: str, value):
    record = dict(_GOOD_TERM)
    if value is None:
        del record[field]
    else:
        record[field] = value
    with pytest.raises(emit.EmitError, match=f"no string `{field}`"):
        list(emit.term_triples(_term(record), vocab))


def test_term_type_error_names_the_record(vocab: emit.Vocabulary):
    """The old handler re-read rec['type'] inside `except KeyError` and crashed on a record with no type."""
    record = dict(_GOOD_TERM)
    del record["type"]
    with pytest.raises(emit.EmitError) as info:
        list(emit.term_triples(_term(record), vocab))
    assert info.value.record_id == "CAP-FIXTURE-1"


def test_unpinned_term_type_names_the_record(vocab: emit.Vocabulary):
    with pytest.raises(emit.EmitError, match="which no Term subclass pins") as info:
        list(emit.term_triples(_term({**_GOOD_TERM, "type": "Nope"}), vocab))
    assert info.value.record_id == "CAP-FIXTURE-1"


@pytest.mark.parametrize("bad_id", ["CAP X", "CAP<X>", 'CAP"X', "CAP{X}", "CAP|X", "CAP\\X", "CAP^X", "CAP`X", "CAP\tX"])
def test_term_id_that_cannot_be_an_iri_is_an_emit_error(vocab: emit.Vocabulary, bad_id: str):
    with pytest.raises(emit.EmitError, match="cannot be an IRI local name"):
        list(emit.term_triples(_term({**_GOOD_TERM, "id": bad_id}), vocab))


def test_relates_to_target_that_cannot_be_an_iri_names_the_referring_record(vocab: emit.Vocabulary):
    """`target: 'PERSONA x'` used to escape as pyoxigraph's bare ValueError."""
    record = {**_GOOD_TERM, "relates_to": [{"rel": "consumed_by", "target": "PERSONA x"}]}
    with pytest.raises(emit.EmitError, match="cannot be an IRI local name") as info:
        list(emit.term_triples(_term(record), vocab))
    assert info.value.record_id == "CAP-FIXTURE-1"


def test_relates_to_target_that_is_not_a_string_is_an_emit_error(vocab: emit.Vocabulary):
    record = {**_GOOD_TERM, "relates_to": [{"rel": "consumed_by", "target": ["PERSONA-x"]}]}
    with pytest.raises(emit.EmitError, match="is not a non-empty string"):
        list(emit.term_triples(_term(record), vocab))


def test_relates_to_verb_that_is_not_a_string_is_an_emit_error(vocab: emit.Vocabulary):
    record = {**_GOOD_TERM, "relates_to": [{"rel": ["grouped_by"], "target": "FND"}]}
    with pytest.raises(emit.EmitError, match="is not a slot in the verbs subset"):
        list(emit.term_triples(_term(record), vocab))


def test_iri_safe_but_pattern_breaking_id_still_reaches_the_graph(vocab: emit.Vocabulary):
    """The guard is IRI-safety, not the schema id pattern: '1-bad' and 'X/Y' must reach the graph, where the
    `id-pattern` shape reports them as the linter does (fixtures/structural/id-pattern.yaml)."""
    for iri_safe in ("1-bad", "TEN-DIM-DATA/X"):
        triples = list(emit.term_triples(_term({**_GOOD_TERM, "id": iri_safe}), vocab))
        assert triples[0][0] == vocab.id(iri_safe)


def _with_first_term(inputs: emit.Inputs, record: dict) -> emit.Inputs:
    return emit.Inputs(
        terms=(emit.TermRecord(record, inputs.terms[0].file), *inputs.terms[1:]),
        ontology_version=inputs.ontology_version,
    )


def test_emit_refuses_a_term_with_no_type_before_building_the_schema_graph(config: Config):
    """The schema graph reads every term's `type`/`id` first; a term with no `type` used to crash there with
    a bare KeyError. emit() checks every record's shape before any graph is built."""
    inputs = emit.load_inputs(config)
    record = dict(inputs.terms[0].record)
    del record["type"]
    with pytest.raises(emit.EmitError, match="no string `type`") as info:
        emit.emit(_with_first_term(inputs, record), config)
    assert info.value.record_id == record["id"]


def test_emit_refuses_a_term_with_no_id(config: Config):
    """A term with no `id` used to crash with a bare KeyError."""
    inputs = emit.load_inputs(config)
    record = dict(inputs.terms[0].record)
    del record["id"]
    with pytest.raises(emit.EmitError, match="no string `id`"):
        emit.emit(_with_first_term(inputs, record), config)

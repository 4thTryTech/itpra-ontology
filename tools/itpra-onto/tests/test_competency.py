"""Tests: competency questions run as SPARQL against the built store.

Every question is a plain ``.rq`` file under ``tests/competency/`` (a ``SELECT`` or ``ASK``), run
in-process against one ``pyoxigraph.Store`` loaded with the schema + t1 + inferred graphs — the default
dataset a query reads (ADR 0041 D3). A query file never names the base IRI or declares
a ``PREFIX`` for ``itpra:``/``itpra-o:``/``itpra-g:`` (``tests/test_iri_config.py``'s placeholder scan
covers ``.rq`` files too, matching ``rules/*.rq``'s discipline); :func:`itpra_onto.rules.prefix_block`
supplies that block at run time. A standard W3C vocabulary (``skos:``, ``rdf:``, ``rdfs:``) may be
declared directly inside a query file, since it is not the configured base IRI.

Every expected value is COMPUTED from ``emit.load_inputs()`` here or reused from ``test_rules.py``'s own
YAML-computed helpers — never a literal — for the same reason ``test_rules.py`` gives: the live ontology
keeps growing. Fixtures are module-scoped and built once (``emit()`` then ``apply_rules()`` then one
``Store``), exactly like ``test_rules.py``'s fixture chain, so this module's cost is one corpus load plus
one rules pass plus two dozen small SPARQL queries.

Reused from ``test_rules.py`` (same package, same test run): the YAML-computed expectations for
the rule-derived edges (``_expected_in_plane``, ``_expected_in_service_domain``, ``_expected_in_domain``,
``_expected_boundary_governed_functions``) and the small record helpers (``_by_id``, ``_targets``,
``_terms_of_type``). Nothing here writes to the vocabulary.
"""

from __future__ import annotations

import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyoxigraph as ox
import pytest

from itpra_onto import emit, rules
from itpra_onto.config import Config, load_config
from itpra_onto.emit import Inputs

from test_rules import (  # test_rules.py's YAML-computed expectations and helpers, reused rather than duplicated
    _expected_boundary_governed_functions,
    _expected_in_domain,
    _targets,
    _terms_of_type,
)

REPO_ROOT = load_config().repo_root
COMPETENCY_DIR = Path(__file__).resolve().parent / "competency"
EXPECTED_TYPES = 13

_MODULE_STARTED = time.perf_counter()  # test_zz_competency_suite_timing, at the bottom, reports elapsed


# ---------------------------------------------------------------------------------------------------
# fixtures: one corpus load, one rules pass, one store — shared by every test below


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config()


@pytest.fixture(scope="module")
def inputs(config: Config) -> Inputs:
    return emit.load_inputs(config)


@pytest.fixture(scope="module")
def dataset(config: Config, inputs: Inputs) -> ox.Dataset:
    return emit.emit(inputs, config)


@pytest.fixture(scope="module")
def report(dataset: ox.Dataset, config: Config) -> rules.RuleReport:
    return rules.apply_rules(dataset, config)


@pytest.fixture(scope="module")
def store(report: rules.RuleReport) -> ox.Store:
    """One store holding schema + t1 + inferred — the default dataset (ADR 0041 D3)."""
    s = ox.Store()
    s.extend(report.dataset)
    return s


# ---------------------------------------------------------------------------------------------------
# helpers


def _query(store: ox.Store, config: Config, filename: str):
    text = (COMPETENCY_DIR / filename).read_text(encoding="utf-8")
    return store.query(rules.prefix_block(config) + text)


def _rows(result: Any) -> list[dict[str, Any]]:
    variables = [v.value for v in result.variables]
    return [{name: solution[name] for name in variables} for solution in result]


def _strip(namespace: str, value: str) -> str:
    return value[len(namespace):] if value.startswith(namespace) else value


def _count(store: ox.Store, config: Config, filename: str) -> int:
    """The single ``?n`` column of a ``SELECT (COUNT(*) AS ?n) …`` positive-control query file."""
    rows = _rows(_query(store, config, filename))
    return int(rows[0]["n"].value)


def _as_list(value: Any) -> list[Any]:
    """:func:`itpra_onto.emit._as_list`'s own null/scalar/list normalisation, reproduced here (rather than
    imported) so this module's YAML-computed expectations stay independent of the emitter's internals."""
    if value is None or value == "":
        return []
    return value if isinstance(value, list) else [value]


def _count_consumed_by(inputs: Inputs, type_value: str) -> int:
    """Total ``consumed_by`` ``relates_to`` edges from every term of ``type_value`` — the YAML-computed
    positive control for cq-14/cq-16."""
    return sum(len(_targets(t, "consumed_by")) for t in _terms_of_type(inputs, type_value))


# =====================================================================================================
# CQ1 — counts per type


def test_type_counts_match_the_yaml_records(store: ox.Store, config: Config, inputs: Inputs):
    """For each of the 13 authored `type` values, the number of subjects of that class in t1 equals the
    YAML record count of that type."""
    from itpra_onto import schema_loading

    vocab = emit.Vocabulary(config, schema_loading.load_schema_view(config=config))
    assert len(vocab.term_class) == EXPECTED_TYPES

    rows = _rows(_query(store, config, "cq-01-type-counts.rq"))
    counted = {row["class"].value: int(row["n"].value) for row in rows}
    expected = Counter(t.record["type"] for t in inputs.terms)
    assert set(expected) == set(vocab.term_class)
    for type_value, n in expected.items():
        cls_iri = vocab.term_class[type_value].value
        assert counted.get(cls_iri) == n, type_value


# =====================================================================================================
# CQ2 — every Function has >=1 inDomain; NOT exactly one (a function may span several domains)


def test_function_in_domain_is_a_multiset_not_a_function(store: ox.Store, config: Config, inputs: Inputs):
    """Every Function has at least one inDomain edge, and the (function, domain) multiset the rule
    derives equals the YAML-computed set — the true invariant is NOT "exactly one Domain per Function":
    a function may support capabilities that live in several domains."""
    rows = _rows(_query(store, config, "cq-02-function-in-domain.rq"))
    id_ns = config.iri.id_ns
    pairs = {(_strip(id_ns, r["func"].value), _strip(id_ns, r["domain"].value)) for r in rows}
    assert pairs == _expected_in_domain(inputs)

    functions = {f["id"] for f in _terms_of_type(inputs, "Function")}
    covered = {func for func, _ in pairs}
    assert functions <= covered

    by_function = Counter(func for func, _ in pairs)
    spanning = sorted(func for func, n in by_function.items() if n > 1)
    print(f"\nfunctions spanning more than one domain: {len(spanning)} of {len(functions)}")
    for func in spanning[:20]:
        print(f"  {func}")


# =====================================================================================================
# CQ3 — every Capability has exactly one inPlane and exactly one inServiceDomain; distribution tables


def test_every_capability_has_exactly_one_plane_and_service_domain(
    store: ox.Store, config: Config, inputs: Inputs
):
    """Every Capability has exactly one inPlane edge and exactly one inServiceDomain edge."""
    id_ns = config.iri.id_ns
    caps = {c["id"] for c in _terms_of_type(inputs, "Capability")}

    plane_rows = _rows(_query(store, config, "cq-03-capability-in-plane.rq"))
    by_cap_plane: dict[str, set[str]] = defaultdict(set)
    for r in plane_rows:
        by_cap_plane[_strip(id_ns, r["cap"].value)].add(_strip(id_ns, r["plane"].value))
    assert set(by_cap_plane) == caps
    assert all(len(v) == 1 for v in by_cap_plane.values())

    sd_rows = _rows(_query(store, config, "cq-04-capability-in-service-domain.rq"))
    by_cap_sd: dict[str, set[str]] = defaultdict(set)
    for r in sd_rows:
        by_cap_sd[_strip(id_ns, r["cap"].value)].add(_strip(id_ns, r["sd"].value))
    assert set(by_cap_sd) == caps
    assert all(len(v) == 1 for v in by_cap_sd.values())

    plane_dist = Counter(next(iter(v)) for v in by_cap_plane.values())
    sd_dist = Counter(next(iter(v)) for v in by_cap_sd.values())
    print("\ncapabilities per plane:")
    for plane, n in sorted(plane_dist.items()):
        print(f"  {plane}: {n}")
    print("capabilities per service domain:")
    for sd, n in sorted(sd_dist.items()):
        print(f"  {sd}: {n}")


# =====================================================================================================
# CQ4 — the boundary-governed function set


def test_boundary_governed_function_set_equals_the_yaml(store: ox.Store, config: Config, inputs: Inputs):
    """The boundary-governed function set the rules materialise in the graph equals the set computed from
    the YAML (not merely the same count)."""
    rows = _rows(_query(store, config, "cq-05-boundary-governed-functions.rq"))
    from_graph = {_strip(config.iri.id_ns, r["func"].value) for r in rows}
    assert from_graph == _expected_boundary_governed_functions(inputs)
    assert from_graph, "expected at least one boundary-governed function in the real ontology"


# =====================================================================================================
# CQ5 — consumption / grouping cardinalities


def test_every_capability_is_consumed_by_at_least_one_persona(store: ox.Store, config: Config, inputs: Inputs):
    """Every Capability is consumed by at least one Persona.

    Positive control first: confirm the `consumedBy`-from-Capability edge count against the YAML, so a
    misspelt/renamed predicate cannot leave the EMPTY assertion below vacuously true.
    """
    assert _count(store, config, "cq-20-capability-consumed-by-count.rq") == _count_consumed_by(
        inputs, "Capability"
    )
    rows = _rows(_query(store, config, "cq-06-capabilities-without-consumed-by.rq"))
    assert rows == []


def test_every_journey_is_grouped_in_exactly_one_journey_group(
    store: ox.Store, config: Config, inputs: Inputs
):
    """Every Journey is grouped in exactly one JourneyGroup."""
    id_ns = config.iri.id_ns
    rows = _rows(_query(store, config, "cq-07-journey-in-journey-group.rq"))
    by_journey: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        by_journey[_strip(id_ns, r["journey"].value)].add(_strip(id_ns, r["group"].value))

    journeys = {j["id"] for j in _terms_of_type(inputs, "Journey")}
    assert set(by_journey) == journeys
    assert all(len(v) == 1 for v in by_journey.values())

    groups = {t["id"] for t in _terms_of_type(inputs, "JourneyGroup")}
    targets = {g for v in by_journey.values() for g in v}
    assert targets <= groups


def test_every_journey_is_consumed_by_at_least_one_persona(store: ox.Store, config: Config, inputs: Inputs):
    """Every Journey is consumed by at least one Persona. Positive count first (see
    test_every_capability_is_consumed_by_at_least_one_persona)."""
    assert _count(store, config, "cq-21-journey-consumed-by-count.rq") == _count_consumed_by(inputs, "Journey")
    rows = _rows(_query(store, config, "cq-08-journeys-without-consumed-by.rq"))
    assert rows == []


def test_every_domain_is_grouped_in_exactly_one_plane(store: ox.Store, config: Config, inputs: Inputs):
    """Every Domain is grouped in exactly one Plane."""
    id_ns = config.iri.id_ns
    rows = _rows(_query(store, config, "cq-09-domain-in-plane.rq"))
    by_domain: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        by_domain[_strip(id_ns, r["domain"].value)].add(_strip(id_ns, r["plane"].value))

    domains = {d["id"] for d in _terms_of_type(inputs, "Domain")}
    assert set(by_domain) == domains
    assert all(len(v) == 1 for v in by_domain.values())

    planes = {t["id"] for t in _terms_of_type(inputs, "Plane")}
    targets = {p for v in by_domain.values() for p in v}
    assert targets <= planes


def test_every_domain_belongs_to_exactly_one_service_domain(
    store: ox.Store, config: Config, inputs: Inputs
):
    """Every Domain belongs to exactly one ServiceDomain."""
    id_ns = config.iri.id_ns
    rows = _rows(_query(store, config, "cq-10-domain-in-service-domain.rq"))
    by_domain: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        by_domain[_strip(id_ns, r["domain"].value)].add(_strip(id_ns, r["sd"].value))

    domains = {d["id"] for d in _terms_of_type(inputs, "Domain")}
    assert set(by_domain) == domains
    assert all(len(v) == 1 for v in by_domain.values())

    service_domains = {t["id"] for t in _terms_of_type(inputs, "ServiceDomain")}
    targets = {s for v in by_domain.values() for s in v}
    assert targets <= service_domains


# =====================================================================================================
# CQ6 — SKOS label integrity


def test_no_term_has_two_pref_labels(store: ox.Store, config: Config, inputs: Inputs):
    """No term has two (distinct) skos:prefLabels.

    Positive control first: confirm the total skos:prefLabel triple count against the YAML-computed term count —
    a mistyped predicate would otherwise leave the "no duplicates" GROUP BY/HAVING query vacuously EMPTY.
    """
    assert _count(store, config, "cq-22-pref-label-count.rq") == len(inputs.terms)
    rows = _rows(_query(store, config, "cq-11-duplicate-pref-labels.rq"))
    assert rows == []


def test_no_alt_label_equals_its_subjects_own_pref_label(store: ox.Store, config: Config, inputs: Inputs):
    """No skos:altLabel equals its subject's own skos:prefLabel (case-insensitively — ADR 0007). Positive
    control first: confirm the total skos:altLabel triple count against the YAML-computed alias count."""
    expected_aliases = sum(len(_as_list(t.record.get("aliases"))) for t in inputs.terms)
    assert _count(store, config, "cq-23-alt-label-count.rq") == expected_aliases
    rows = _rows(_query(store, config, "cq-12-alt-label-equals-pref-label.rq"))
    assert rows == []


# =====================================================================================================
# CQ7 — decidedIn ADR nodes


def test_every_decided_in_object_is_a_four_digit_adr_node(store: ox.Store, config: Config):
    """Every `decidedIn` object is an ADR-NNNN node with four digits, and the number of distinct ADR
    nodes referenced is reported."""
    id_ns = config.iri.id_ns
    rows = _rows(_query(store, config, "cq-13-decided-in-adr-objects.rq"))
    locals_ = [_strip(id_ns, r["adr"].value) for r in rows]
    assert locals_, "expected at least one ADR-NNNN node referenced via decidedIn"
    for local in locals_:
        assert re.fullmatch(r"ADR-\d{4}", local), local
    print(f"\ndistinct ADR nodes referenced via decidedIn: {len(locals_)}")


# =====================================================================================================
# CQ8 — one authoringFile per subject, and the file exists


def test_every_subject_has_exactly_one_existing_authoring_file(store: ox.Store, config: Config, inputs: Inputs):
    """Every subject in t1 has exactly one itpra-o:authoringFile, and that file exists relative to the
    repository root.

    The row count itself is a positive control — one row per DISTINCT subject carrying
    authoringFile, which must equal the total number of term records (every record gets exactly one),
    not merely a non-empty result.
    """
    rows = _rows(_query(store, config, "cq-14-authoring-file.rq"))
    assert len(rows) == len(inputs.terms)
    missing: list[str] = []
    for r in rows:
        assert int(r["n"].value) == 1, r["s"].value
        file_value = r["sample"].value
        if not (REPO_ROOT / file_value).exists():
            missing.append(file_value)
    assert missing == []


# =====================================================================================================
# CQ9 — the inferred graph mints only the schema-declared derived vocabulary


def test_inferred_graph_only_uses_schema_declared_derived_vocabulary(store: ox.Store, config: Config):
    """The inferred graph contains only predicates/classes the schema declares in advance with an
    rdfs:comment starting "derived by rule"."""
    declared_rows = _rows(_query(store, config, "cq-17-schema-derived-declarations.rq"))
    declared = {r["term"].value for r in declared_rows}
    assert declared  # sanity: the 4 roll-up/reverse-link properties + BoundaryGovernedFunction

    predicate_rows = _rows(_query(store, config, "cq-15-inferred-predicates.rq"))
    predicates = {r["p"].value for r in predicate_rows}
    assert predicates, "expected at least one non-rdf:type predicate in the inferred graph"
    assert predicates <= declared

    type_rows = _rows(_query(store, config, "cq-16-inferred-types.rq"))
    types = {r["type"].value for r in type_rows}
    assert types, "expected at least one rdf:type triple (BoundaryGovernedFunction) in the inferred graph"
    assert types <= declared


# =====================================================================================================
# CQ10 — the default graph is empty; no blank nodes anywhere


def test_default_graph_is_empty(store: ox.Store, config: Config):
    """The default (unnamed) graph is empty."""
    result = _query(store, config, "cq-18-default-graph-triples.rq")
    assert bool(result) is False


def test_no_blank_nodes_anywhere(store: ox.Store, config: Config, report: rules.RuleReport):
    """There are no blank nodes anywhere in the store (no named graph has a blank subject or object).

    Confirm the store is non-trivial FIRST — an empty store would make the ASK query below
    vacuously ``False`` for the wrong reason.
    """
    assert _count(store, config, "cq-24-total-quad-count.rq") == len(report.dataset)
    result = _query(store, config, "cq-19-blank-nodes-anywhere.rq")
    assert bool(result) is False


# =====================================================================================================
# every .rq file parses and runs, even if no test above happens to use it


ALL_QUERY_FILES = sorted(COMPETENCY_DIR.glob("*.rq"))


@pytest.mark.parametrize("path", ALL_QUERY_FILES, ids=lambda p: p.name)
def test_every_competency_query_file_parses_and_runs(store: ox.Store, config: Config, path: Path):
    """Every .rq file under tests/competency/ parses and runs against the store without error."""
    text = path.read_text(encoding="utf-8")
    result = store.query(rules.prefix_block(config) + text)
    if isinstance(result, ox.QueryBoolean):
        bool(result)
    else:
        list(result)


def test_at_least_one_query_file_per_numbered_competency_question():
    """Sanity: the competency directory holds at least as many query files as the 10 numbered competency
    questions above (several questions are split into a few small, single-purpose queries)."""
    assert len(ALL_QUERY_FILES) >= 10


# =====================================================================================================
# timing — printed with -s; run last (default pytest order = file definition order) so the elapsed time
# approximates the whole module's fixture-build-plus-every-query cost


def test_zz_competency_suite_timing():
    """Reports (informational) the wall-clock time from this module's import to this, its last test —
    fixture construction (emit + apply_rules + Store.extend) plus every competency query."""
    elapsed = time.perf_counter() - _MODULE_STARTED
    print(f"\ncompetency module total (fixtures + all queries): {elapsed:.3f}s")
    assert elapsed >= 0

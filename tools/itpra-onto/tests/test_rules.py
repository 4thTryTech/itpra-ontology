"""Tests for the SPARQL materialisation rules (``itpra_onto.rules``; ADR 0041 D4).

Every test reads the REAL input files (the vocabulary and, with an overlay, the requirements registries),
exactly like ``test_emit.py``: nothing is ever written to them. Expected counts are always COMPUTED from
``emit.load_inputs()`` in this file (never a literal), since the schema's ``itpra_verb`` annotation counts
are a snapshot taken at authoring time and the live ontology keeps growing. Alternative rule directories used
to test :func:`rules.rules_digest` are written to ``tmp_path`` only.
"""

from __future__ import annotations

import importlib.util
import shutil
import time
from pathlib import Path
from typing import Any

import pyoxigraph as ox
import pytest

from itpra_onto import emit, rules
from itpra_onto.config import Config, load_config
from itpra_onto.emit import Inputs

REPO_ROOT = emit.REPO_ROOT
EXPECTED_RULE_IDS = (
    "capability-in-plane",
    "capability-in-service-domain",
    "function-in-domain",
    "requirement-meets",
    "boundary-governed-function",
    "inverses",
)


# ---------------------------------------------------------------------------------------------------
# fixtures and helpers


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
    result = rules.apply_rules(dataset, config)
    print(f"\napply_rules(): {result.total} quads in {result.elapsed:.3f}s")
    for rule_id, count in result.counts.items():
        print(f"  {rule_id}: {count}")
    return result


def _by_id(inputs: Inputs) -> dict[str, dict[str, Any]]:
    return {t.record["id"]: t.record for t in inputs.terms}


def _targets(rec: dict[str, Any], verb: str) -> list[str]:
    return [edge["target"] for edge in (rec.get("relates_to") or []) if edge.get("rel") == verb]


def _terms_of_type(inputs: Inputs, type_value: str) -> list[dict[str, Any]]:
    return [t.record for t in inputs.terms if t.record["type"] == type_value]


def _sorted_nquads(dataset: ox.Dataset) -> list[str]:
    """RDFC-1.0 canonicalise, serialise N-Quads, sort lines (test_emit.py's recipe)."""
    dataset.canonicalize(ox.CanonicalizationAlgorithm.RDFC_1_0)
    raw = ox.serialize(dataset, format=ox.RdfFormat.N_QUADS).decode("utf-8")
    return sorted(raw.splitlines(keepends=True))


def _actual_pairs(report: rules.RuleReport, config: Config, predicate_local: str) -> set[tuple[str, str]]:
    """(subject local id, object local id) pairs the graph actually carries for a derived predicate — used
    to check the SET the rule materialises, not merely its count, against the YAML-computed
    set: a count-only check cannot catch a rule that derives the right number of edges between the wrong
    pairs."""
    predicate = ox.NamedNode(config.iri.onto_ns + predicate_local)
    id_ns = config.iri.id_ns
    return {
        (q.subject.value.removeprefix(id_ns), q.object.value.removeprefix(id_ns))
        for q in report.dataset.quads_for_predicate(predicate)
    }


def _subset(dataset: ox.Dataset, *, exclude_graph: str) -> ox.Dataset:
    subset = ox.Dataset()
    for quad in dataset:
        if quad.graph_name.value != exclude_graph:
            subset.add(quad)
    return subset


# ---- expected counts, computed from the YAML (never a literal) --------------------------------------


def _expected_in_plane(inputs: Inputs) -> set[tuple[str, str]]:
    by_id = _by_id(inputs)
    pairs: set[tuple[str, str]] = set()
    for cap in _terms_of_type(inputs, "Capability"):
        for domain_id in _targets(cap, "grouped_by"):
            domain = by_id.get(domain_id)
            if not domain or domain["type"] != "Domain":
                continue
            for plane_id in _targets(domain, "grouped_by"):
                plane = by_id.get(plane_id)
                if plane and plane["type"] == "Plane":
                    pairs.add((cap["id"], plane_id))
    return pairs


def _expected_in_service_domain(inputs: Inputs) -> set[tuple[str, str]]:
    by_id = _by_id(inputs)
    pairs: set[tuple[str, str]] = set()
    for cap in _terms_of_type(inputs, "Capability"):
        for domain_id in _targets(cap, "grouped_by"):
            domain = by_id.get(domain_id)
            if not domain or domain["type"] != "Domain":
                continue
            for sd_id in _targets(domain, "belongs_to_service_domain"):
                sd = by_id.get(sd_id)
                if sd and sd["type"] == "ServiceDomain":
                    pairs.add((cap["id"], sd_id))
    return pairs


def _expected_in_domain(inputs: Inputs) -> set[tuple[str, str]]:
    by_id = _by_id(inputs)
    pairs: set[tuple[str, str]] = set()
    for func in _terms_of_type(inputs, "Function"):
        for cap_id in _targets(func, "supports"):
            cap = by_id.get(cap_id)
            if not cap or cap["type"] != "Capability":
                continue
            for domain_id in _targets(cap, "grouped_by"):
                domain = by_id.get(domain_id)
                if domain and domain["type"] == "Domain":
                    pairs.add((func["id"], domain_id))
    return pairs


def _expected_meets(inputs: Inputs) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for req in inputs.requirements:
        met_by = req.record.get("met_by")
        targets = met_by if isinstance(met_by, list) else ([met_by] if met_by else [])
        for cap_id in targets:
            pairs.add((str(cap_id), req.record["id"]))
    return pairs


def _linter_boundary_governed_functions():
    """Import the consumer's linter's (``[overlay] linter_script``) helper by path.

    The script is a CLI (guarded by ``if __name__ == "__main__":``), so ``exec_module`` under a different
    module name never runs ``main()``; only top-level defs and three empty module-level lists execute.
    """
    from itpra_onto import parity

    spec = importlib.util.spec_from_file_location("itpra_onto_consumer_lint_under_test", parity.linter_script())
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._boundary_governed_functions


def _expected_boundary_governed_functions(inputs: Inputs) -> set[str]:
    by_id = _by_id(inputs)
    boundary = by_id.get("AUTON-BOUNDARY") or {}
    return {
        target
        for target in _targets(boundary, "governs")
        if (by_id.get(target) or {}).get("type") == "Function"
    }


# ---------------------------------------------------------------------------------------------------
# the manifest and rule-file discipline


def test_manifest_lists_rules_in_the_documented_order():
    manifest = rules.load_manifest(all_rules=True)  # the shipped set, overlay rules included
    assert tuple(rule.id for rule in manifest) == EXPECTED_RULE_IDS


def test_inverses_rule_has_no_construct_and_produces_none():
    manifest = {rule.id: rule for rule in rules.load_manifest()}
    inverses = manifest["inverses"]
    assert inverses.has_construct is False
    assert inverses.produces == "none"


def test_rule_files_carry_no_prefix_declaration_or_base_iri(config: Config):
    base = config.iri.base
    for rule in rules.load_manifest():
        text = rule.path.read_text(encoding="utf-8")
        assert "PREFIX itpra" not in text, rule.id
        assert base not in text, rule.id
    manifest_text = (rules.RULES_DIR / "manifest.yaml").read_text(encoding="utf-8")
    assert "PREFIX itpra" not in manifest_text
    assert base not in manifest_text


def test_prefix_block_contains_the_configured_namespaces(config: Config):
    block = rules.prefix_block(config)
    assert f"<{config.iri.id_ns}>" in block
    assert f"<{config.iri.onto_ns}>" in block
    assert f"<{config.iri.graph_ns}>" in block


# ---------------------------------------------------------------------------------------------------
# per-rule triple counts, computed from the YAML


def test_capability_in_plane_count(report: rules.RuleReport, inputs: Inputs):
    assert report.counts["capability-in-plane"] == len(_expected_in_plane(inputs))


def test_capability_in_plane_set(report: rules.RuleReport, config: Config, inputs: Inputs):
    """The actual (capability, plane) SET the rule materialises, not only its count."""
    assert _actual_pairs(report, config, "inPlane") == _expected_in_plane(inputs)


def test_capability_in_service_domain_count(report: rules.RuleReport, inputs: Inputs):
    assert report.counts["capability-in-service-domain"] == len(_expected_in_service_domain(inputs))


def test_capability_in_service_domain_set(report: rules.RuleReport, config: Config, inputs: Inputs):
    assert _actual_pairs(report, config, "inServiceDomain") == _expected_in_service_domain(inputs)


def test_function_in_domain_count(report: rules.RuleReport, inputs: Inputs):
    assert report.counts["function-in-domain"] == len(_expected_in_domain(inputs))


def test_function_in_domain_set(report: rules.RuleReport, config: Config, inputs: Inputs):
    assert _actual_pairs(report, config, "inDomain") == _expected_in_domain(inputs)


@pytest.mark.overlay  # needs the consumer's registries
def test_requirement_meets_count(report: rules.RuleReport, inputs: Inputs):
    assert report.counts["requirement-meets"] == len(_expected_meets(inputs))


def test_requirement_meets_set(report: rules.RuleReport, config: Config, inputs: Inputs):
    assert _actual_pairs(report, config, "meets") == _expected_meets(inputs)


def test_boundary_governed_function_count(report: rules.RuleReport, inputs: Inputs):
    expected = _expected_boundary_governed_functions(inputs)
    assert report.counts["boundary-governed-function"] == len(expected)


def test_inverses_rule_contributes_zero_triples(report: rules.RuleReport):
    assert report.counts["inverses"] == 0


def test_total_equals_sum_of_counts(report: rules.RuleReport):
    assert report.total == sum(report.counts.values())


# ---------------------------------------------------------------------------------------------------
# the boundary-governed set equals the consumer's linter helper's (same ids, not just the same count)


@pytest.mark.overlay  # imports the consumer's linter
def test_boundary_governed_set_equals_the_linter_helper(inputs: Inputs):
    terms = {t.record["id"]: t.record for t in inputs.terms}
    helper = _linter_boundary_governed_functions()
    from_linter = helper(terms)
    from_here = _expected_boundary_governed_functions(inputs)
    assert from_linter == from_here
    assert from_linter, "expected at least one boundary-governed function in the real ontology"
    print(f"\nboundary-governed functions ({len(from_linter)}): {sorted(from_linter)}")


def test_boundary_governed_set_matches_the_graph(report: rules.RuleReport, config: Config, inputs: Inputs):
    boundary_class = ox.NamedNode(config.iri.onto_ns + emit.BOUNDARY_GOVERNED_FUNCTION)
    typed = {
        q.subject.value.removeprefix(config.iri.id_ns)
        for q in report.dataset.quads_for_predicate(emit.RDF_TYPE)
        if q.object == boundary_class
    }
    assert typed == _expected_boundary_governed_functions(inputs)


# ---------------------------------------------------------------------------------------------------
# competency: cardinalities every capability/function must satisfy


def test_every_capability_has_exactly_one_in_plane(report: rules.RuleReport, config: Config, inputs: Inputs):
    in_plane = ox.NamedNode(config.iri.onto_ns + "inPlane")
    counts: dict[str, int] = {}
    for quad in report.dataset.quads_for_predicate(in_plane):
        counts[quad.subject.value] = counts.get(quad.subject.value, 0) + 1
    caps = {config.iri.id_ns + cap["id"] for cap in _terms_of_type(inputs, "Capability")}
    assert set(counts) == caps
    assert set(counts.values()) == {1}


def test_every_capability_has_exactly_one_in_service_domain(report: rules.RuleReport, config: Config, inputs: Inputs):
    in_sd = ox.NamedNode(config.iri.onto_ns + "inServiceDomain")
    counts: dict[str, int] = {}
    for quad in report.dataset.quads_for_predicate(in_sd):
        counts[quad.subject.value] = counts.get(quad.subject.value, 0) + 1
    caps = {config.iri.id_ns + cap["id"] for cap in _terms_of_type(inputs, "Capability")}
    assert set(counts) == caps
    assert set(counts.values()) == {1}


def test_every_function_has_at_least_one_in_domain(report: rules.RuleReport, config: Config, inputs: Inputs):
    in_domain = ox.NamedNode(config.iri.onto_ns + "inDomain")
    subjects = {quad.subject.value for quad in report.dataset.quads_for_predicate(in_domain)}
    funcs = {config.iri.id_ns + func["id"] for func in _terms_of_type(inputs, "Function")}
    assert funcs <= subjects


# ---------------------------------------------------------------------------------------------------
# inferred graph isolation


def test_emit_alone_never_writes_the_inferred_graph(dataset: ox.Dataset, config: Config):
    inferred = config.iri.graph_ns + "inferred"
    assert not any(q.graph_name.value == inferred for q in dataset)


def test_every_new_quad_lands_only_in_the_inferred_graph(dataset: ox.Dataset, report: rules.RuleReport, config: Config):
    original = set(dataset)
    new_quads = [q for q in report.dataset if q not in original]
    assert new_quads, "apply_rules produced no new triples"
    inferred = config.iri.graph_ns + "inferred"
    assert all(q.graph_name.value == inferred for q in new_quads)
    assert len(new_quads) == report.total


def test_asserted_graphs_are_byte_identical_before_and_after(dataset: ox.Dataset, config: Config):
    inferred = config.iri.graph_ns + "inferred"
    before = _sorted_nquads(_subset(dataset, exclude_graph=inferred))
    result = rules.apply_rules(dataset, config)
    after = _sorted_nquads(_subset(result.dataset, exclude_graph=inferred))
    assert before == after


# ---------------------------------------------------------------------------------------------------
# no rule re-asserts an already-used predicate; no owl:inverseOf anywhere


def test_no_derived_predicate_or_class_collides_with_an_asserted_one(dataset: ox.Dataset, report: rules.RuleReport, config: Config):
    inferred = config.iri.graph_ns + "inferred"
    asserted_predicates = {q.predicate.value for q in dataset if q.graph_name.value != inferred}
    derived_predicates = {config.iri.onto_ns + local for local in emit.DERIVED_PROPERTY_RULES}
    if config.overlay is None:
        derived_predicates.discard(config.iri.onto_ns + "meets")  # requirement-meets is an overlay rule; it did not run
    assert derived_predicates.isdisjoint(asserted_predicates)
    inferred_predicates = {q.predicate.value for q in report.dataset if q.graph_name.value == inferred}
    assert derived_predicates <= inferred_predicates

    boundary_class = config.iri.onto_ns + emit.BOUNDARY_GOVERNED_FUNCTION
    asserted_types = {q.object.value for q in dataset if q.predicate == emit.RDF_TYPE}
    assert boundary_class not in asserted_types


def test_no_owl_inverse_of_anywhere(report: rules.RuleReport):
    owl_inverse_of = ox.NamedNode(emit.OWL + "inverseOf")
    assert list(report.dataset.quads_for_predicate(owl_inverse_of)) == []


# ---------------------------------------------------------------------------------------------------
# rules_digest


def test_rules_digest_is_stable(config: Config):
    assert rules.rules_digest(config) == rules.rules_digest(config)


def test_rules_digest_changes_when_a_rule_file_changes(tmp_path: Path, config: Config):
    copy_dir = tmp_path / "rules"
    shutil.copytree(rules.RULES_DIR, copy_dir)
    unchanged = rules.rules_digest(config, rules_dir=copy_dir)
    assert unchanged == rules.rules_digest(config)

    target = copy_dir / "10-capability-in-plane.rq"
    target.write_text(target.read_text(encoding="utf-8") + "\n# test mutation\n", encoding="utf-8")
    changed = rules.rules_digest(config, rules_dir=copy_dir)
    assert changed != unchanged


def test_rules_digest_changes_when_the_manifest_changes(tmp_path: Path, config: Config):
    copy_dir = tmp_path / "rules"
    shutil.copytree(rules.RULES_DIR, copy_dir)
    before = rules.rules_digest(config, rules_dir=copy_dir)
    manifest_path = copy_dir / "manifest.yaml"
    manifest_path.write_text(manifest_path.read_text(encoding="utf-8") + "\n# mutated\n", encoding="utf-8")
    after = rules.rules_digest(config, rules_dir=copy_dir)
    assert after != before


# ---------------------------------------------------------------------------------------------------
# determinism


def test_two_independent_runs_are_byte_identical(config: Config):
    first = rules.apply_rules(emit.emit(config=config), config)
    second = rules.apply_rules(emit.emit(config=config), config)
    assert _sorted_nquads(first.dataset) == _sorted_nquads(second.dataset)


# ---------------------------------------------------------------------------------------------------
# timing


def test_apply_rules_time_reported(dataset: ox.Dataset, config: Config):
    started = time.perf_counter()
    result = rules.apply_rules(dataset, config)
    elapsed = time.perf_counter() - started
    print(f"\napply_rules() (fresh run): {result.total} quads in {elapsed:.3f}s")
    assert elapsed >= 0

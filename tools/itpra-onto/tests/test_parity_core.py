"""``itpra-onto parity`` without a consumer overlay (ADR 0042 D5, ADR 0043 D1): the ontology's own lint
(:mod:`itpra_onto.lint`) against the shapes over the core-home comparable rules, on the real vocabulary and
fixture by fixture. Runs in every configuration (a consumer's configuration is reduced to the core here).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from itpra_onto import lint, parity
from itpra_onto.config import DEFAULT_CONFIG_PATH, Config, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_COMPARABLE = {"field-missing", "id-pattern", "target-unresolved", "function-derived-from"}
CORE_EMIT_MAPPED = {"type-unknown", "verb-unknown", "relates-to-malformed"}


@pytest.fixture(scope="module")
def core_config() -> Config:
    return replace(load_config(), overlay=None)


@pytest.fixture(scope="module")
def real_tree(core_config: Config) -> parity.RealTreeComparison:
    return parity.run_real_tree(config=core_config)


@pytest.fixture(scope="module")
def verdicts(core_config: Config) -> list[parity.FixtureVerdict]:
    return parity.run_fixtures(config=core_config)


def test_core_mode_compares_the_core_home_comparable_rules(real_tree: parity.RealTreeComparison):
    assert real_tree.mode == "core"
    assert set(real_tree.comparable_rules) == CORE_COMPARABLE
    # the consumer-home comparable rules are reported, not silently dropped
    assert {"req-id-format", "req-qa-unresolved", "req-statement-missing", "req-target-unresolved"} <= set(real_tree.outside_scope)


def test_core_mode_real_tree_parity_is_empty(real_tree: parity.RealTreeComparison):
    assert real_tree.emit_errors == ()
    assert real_tree.linter_only == () and real_tree.shacl_only == (), (real_tree.linter_only, real_tree.shacl_only)
    assert real_tree.passed


def test_core_mode_skips_registry_fixtures_and_fails_none(verdicts: list[parity.FixtureVerdict]):
    assert verdicts, "no fixtures ran"
    assert not any(v.fixture.startswith("requirements/") for v in verdicts)
    assert "structural/req-link-malformed.yaml" not in {v.fixture for v in verdicts}
    assert parity.fixture_failures(verdicts) == []


def test_core_mode_fixtures_the_lint_can_prove_are_caught_on_both_sides(verdicts: list[parity.FixtureVerdict]):
    by_rule: dict[str, set[str]] = {}
    for v in verdicts:
        by_rule.setdefault(v.nominal_rule, set()).add(v.verdict)
    for rule in CORE_COMPARABLE | CORE_EMIT_MAPPED:
        assert by_rule.get(rule) == {"both"}, (rule, by_rule.get(rule))
    # the stricter-than-the-linter shapes stay shacl-only and are never comparable
    assert all(v.verdict == "shacl-only" and not v.comparable for v in verdicts if v.nominal_rule.startswith("B-"))


def test_core_lint_findings_run_over_a_scratch_copy_label_files_from_the_repository_root(tmp_path: Path, core_config: Config):
    """The scratch copy mirrors the real layout, so the labels equal the real run's and a focus id matches."""
    from itpra_onto import emit

    scratch = tmp_path / "scratch"
    parity._copy_ontology_dir(scratch, core_config)
    real = parity.core_lint_findings(core_config)
    scratch_findings = parity.core_lint_findings(core_config, ontology_dir=parity._scratch_path(scratch, emit.ontology_dir(core_config)))
    assert lint.errors(real) == [] and lint.errors(scratch_findings) == []


def test_cli_parity_core_mode(tmp_path: Path):
    """The command, over a configuration without an [overlay]: mode core, parity empty, exit 0."""
    text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
    text = re.sub(r"\n\[overlay\].*?(?=\n\[|\Z)", "\n", text, flags=re.S)
    shipped = load_config()
    text = re.sub(r'^ontology_dir = "[^"]*"', f'ontology_dir = "{(shipped.config_path.parent / shipped.paths.ontology_dir).resolve().as_posix()}"', text, count=1, flags=re.M)
    text = re.sub(r'^dist_dir = "[^"]*"', f'dist_dir = "{(tmp_path / "dist").as_posix()}"', text, count=1, flags=re.M)
    text = re.sub(r'^store_dir = "[^"]*"', f'store_dir = "{(tmp_path / "store").as_posix()}"', text, count=1, flags=re.M)
    config_path = tmp_path / "itpra-onto.toml"
    config_path.write_text(text, encoding="utf-8")
    assert load_config(config_path).overlay is None
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "parity", "--json"],
        cwd=PROJECT_ROOT, env={**os.environ, "ITPRA_ONTO_CONFIG": str(config_path)},
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["mode"] == "core"
    assert set(payload["comparable_rules"]) == CORE_COMPARABLE
    assert payload["linter_only"] == [] and payload["shacl_only"] == []

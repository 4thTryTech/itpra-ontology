"""Tests: the base IRI is a configuration item, never hard-coded (ADR 0004).

``itpra-onto.toml`` ``[iri] base`` is the single source; neither the LinkML schema's own ``id:`` nor its
``itpra:``/``itpra-o:`` prefix declarations may carry an IRI literal. This module tests that this holds:

(a) a project-wide scan: the configured base appears only in ``itpra-onto.toml`` itself and the two schema
    fragments generated from it.
(b) regenerating the prefixes fragment (and the in-memory main-schema id) from a config whose
    ``[iri] base`` has changed yields the new IRIs and is otherwise byte-identical / unchanged.
(c) ``gen-prefixes --check`` (and the underlying :func:`itpra_onto.gen_prefixes.check`) fails once the
    config has moved on from what the committed fragment reflects.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from itpra_onto import gen_prefixes, schema_loading
from itpra_onto.config import DEFAULT_CONFIG_PATH, ConfigError, load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------------------------------
# (a) the configured base appears ONLY in the config and what it generates (ADR 0004: no IRI literal outside
# the config file)

GENERATED_FROM_CONFIG = {
    PROJECT_ROOT / "src" / "itpra_onto" / "schema" / "generated" / "itpra-enums.linkml.yaml",
    PROJECT_ROOT / "src" / "itpra_onto" / "schema" / "generated" / "itpra-prefixes.linkml.yaml",
}
SCANNED_SUFFIXES = {".py", ".yaml", ".rq", ".nq", ".ttl", ".json", ".md", ".toml"}
# dist/ (and public/, listed in the repository root .gitignore alongside it) is DERIVED, gitignored and
# rebuilt from the current [iri] base on every `gen-artifacts`/`build` -- it legitimately carries the base
# literal in dozens of generated .json/.ttl/.md files whenever it exists on disk, so it is skipped here the
# same way it is already excluded from every authored-content check this pipeline runs.
SKIPPED_DIR_NAMES = {".venv", "__pycache__", ".pytest_cache", "dist", "public", ".store"}


def _scanned_files() -> list[Path]:
    files = []
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in SCANNED_SUFFIXES:
            continue
        if any(part in SKIPPED_DIR_NAMES for part in path.parts):
            continue
        files.append(path)
    return files


def test_shipped_config_carries_a_ruled_base():
    """The shipped config carries the published base IRI (ADR 0004), and the two generated fragments were
    regenerated from it (what `gen-prefixes --check` / `gen-enums --check` enforce in CI)."""
    config = load_config()
    assert config.iri.base.startswith("https://") and config.iri.base.endswith("/")
    for generated in GENERATED_FROM_CONFIG:
        assert config.iri.base in generated.read_text(encoding="utf-8"), generated


def test_config_toml_is_the_single_hand_authored_source():
    """itpra-onto.toml is the one place the base IRI is hand-authored (ADR 0004). It may appear
    elsewhere only in the fragments generated from the config; any other file carrying the literal is a
    hard-coded IRI that a later base change would silently miss."""
    config = load_config()
    assert config.iri.base in DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
    offenders: dict[Path, list[str]] = {}
    for path in _scanned_files():
        if path == DEFAULT_CONFIG_PATH or path in GENERATED_FROM_CONFIG:
            continue
        text = path.read_text(encoding="utf-8")
        if config.iri.base in text:
            offenders[path] = [line for line in text.splitlines() if config.iri.base in line]
    assert offenders == {}, offenders


# ---------------------------------------------------------------------------------------------------
# (b) regeneration reflects a changed base, and nothing else

ALT_BASE = "https://example.test/ns/itpra-alt/"


def _write_alt_config(tmp_path: Path, base: str = ALT_BASE) -> Path:
    """A temp copy of the real itpra-onto.toml with only [iri] base swapped."""
    text = DEFAULT_CONFIG_PATH.read_text(encoding="utf-8")
    new_text, count = re.subn(r'base = "[^"]*"', f'base = "{base}"', text, count=1)
    assert count == 1, "itpra-onto.toml's [iri] base line has moved or changed shape"
    alt_path = tmp_path / "itpra-onto.toml"
    alt_path.write_text(new_text, encoding="utf-8")
    return alt_path


def test_iri_namespaces_are_derived_from_base_and_paths():
    config = load_config()
    assert config.iri.base_iri == config.iri.base
    assert config.iri.id_ns == config.iri.base + config.iri.id_path
    assert config.iri.onto_ns == config.iri.base + config.iri.onto_path
    assert config.iri.graph_ns == config.iri.base + config.iri.graph_path
    assert config.iri.linkml_module_id("x") == config.iri.base + "linkml/x"


def test_regenerated_prefixes_fragment_reflects_changed_base_only(tmp_path: Path):
    real_config = load_config()
    original = gen_prefixes.render(real_config)
    alt_config = load_config(_write_alt_config(tmp_path))
    regenerated = gen_prefixes.render(alt_config)

    assert regenerated != original
    original_lines = original.splitlines()
    regenerated_lines = regenerated.splitlines()
    assert len(original_lines) == len(regenerated_lines), "regeneration changed the fragment's shape"
    changed = 0
    for before, after in zip(original_lines, regenerated_lines):
        if before == after:
            continue
        changed += 1
        assert real_config.iri.base in before
        assert ALT_BASE in after
    assert changed > 0


def test_regenerated_main_schema_id_reflects_changed_base(tmp_path: Path):
    alt_config = load_config(_write_alt_config(tmp_path))
    schema = schema_loading.load_schema_definition(config=alt_config)
    assert schema.id == alt_config.iri.linkml_module_id(schema_loading.MAIN_MODULE_NAME)
    assert schema.id.startswith(ALT_BASE)


def test_gen_prefixes_is_deterministic(tmp_path: Path):
    alt_config = load_config(_write_alt_config(tmp_path))
    first, second = gen_prefixes.render(alt_config), gen_prefixes.render(alt_config)
    assert first == second
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    gen_prefixes.write(first, a)
    gen_prefixes.write(second, b)
    assert a.read_bytes() == b.read_bytes()
    assert b"\r\n" not in a.read_bytes()


# ---------------------------------------------------------------------------------------------------
# (c) `--check` fails once the config has moved on from the committed fragment


def test_gen_prefixes_check_is_clean_against_the_committed_fragment():
    assert gen_prefixes.check() is True


def test_gen_prefixes_check_detects_drift_from_a_changed_config(tmp_path: Path):
    alt_config = load_config(_write_alt_config(tmp_path))
    assert gen_prefixes.check(config=alt_config) is False


def test_gen_prefixes_check_detects_missing_file(tmp_path: Path):
    assert gen_prefixes.check(tmp_path / "missing.yaml") is False


def test_gen_prefixes_check_cli_is_clean():
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "gen-prefixes", "--check"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------------------------------
# config loading: no default IRI literal in code; a missing key fails loudly


def test_env_var_overrides_default_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    alt_path = _write_alt_config(tmp_path)
    monkeypatch.setenv("ITPRA_ONTO_CONFIG", str(alt_path))
    config = load_config()
    assert config.iri.base == ALT_BASE
    assert config.config_path == alt_path


def test_missing_base_key_fails_loudly(tmp_path: Path):
    bad = tmp_path / "itpra-onto.toml"
    bad.write_text('[iri]\nid_path = "id/"\nonto_path = "onto#"\ngraph_path = "graph/"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match=r"\[iri\] base"):
        load_config(bad)


def test_missing_path_component_key_fails_loudly(tmp_path: Path):
    bad = tmp_path / "itpra-onto.toml"
    bad.write_text('[iri]\nbase = "https://example.test/ns/itpra/"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match=r"\[iri\] id_path"):
        load_config(bad)

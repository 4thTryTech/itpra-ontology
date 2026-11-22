"""Tests for ``itpra_onto.gen_artifacts``: the derived schema artefacts under ``dist/schema/``.

Acceptance criterion: two consecutive runs are byte-identical. ADR 0041 D5: LinkML's generators are not
deterministic on their own -- this module (and the tests below) exist to prove the pipeline's
neutralisation of that actually holds, for the real schema, not just a toy fixture.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from itpra_onto import gen_artifacts
from itpra_onto.config import load_config

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# The 13 Term subclasses (`schema.yaml` `types:`, schema/itpra.linkml.yaml) that must appear
# as JSON Schema $defs, independent of the RequirementRegistry / requirement classes.
TERM_SUBCLASSES = {
    "Capability",
    "Concept",
    "Domain",
    "EntityType",
    "Function",
    "Journey",
    "JourneyGroup",
    "Persona",
    "Plane",
    "QualityAttribute",
    "RelationshipType",
    "ServiceDomain",
    "Workflow",
}

_DATE_STAMP_RE = re.compile(r"20\d\d-\d\d-\d\d")
# A Windows drive-letter absolute path (D:\... or D:/...) or a POSIX-style absolute home path -- either
# would leak the generating machine's own filesystem layout into a supposedly portable artefact. The
# negative lookbehind keeps this from matching the "s:/" in "https://" (the single letter before the
# colon must not itself be preceded by another letter/digit, which rules out URL schemes).
_ABS_PATH_RE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/home/|/Users/")


def _iter_generated_files(schema_dir: Path) -> list[Path]:
    return sorted(p for p in schema_dir.rglob("*") if p.is_file())


# ---------------------------------------------------------------------------------------------------
# (a) two consecutive generate() runs are byte-identical (the acceptance criterion)


def test_generate_is_byte_identical_across_two_runs(tmp_path: Path):
    run1 = tmp_path / "run1"
    run2 = tmp_path / "run2"

    written1 = gen_artifacts.generate(out_dir=run1)
    written2 = gen_artifacts.generate(out_dir=run2)

    assert written1  # non-empty: something was actually generated
    rel1 = sorted(p.relative_to(run1) for p in written1)
    rel2 = sorted(p.relative_to(run2) for p in written2)
    assert rel1 == rel2

    for rel in rel1:
        assert (run1 / rel).read_bytes() == (run2 / rel).read_bytes(), f"{rel} differs between runs"


def test_generate_returns_every_written_file_sorted(tmp_path: Path):
    out_dir = tmp_path / "schema"
    written = gen_artifacts.generate(out_dir=out_dir)
    assert written == sorted(written)
    for path in written:
        assert path.is_file()
        assert path.is_relative_to(out_dir)
    names = {p.name for p in written}
    assert gen_artifacts.JSON_SCHEMA_FILENAME in names
    assert gen_artifacts.PYDANTIC_FILENAME in names
    assert gen_artifacts.OWL_FILENAME in names
    assert gen_artifacts.SHACL_FILENAME in names
    assert any(p.parent.name == gen_artifacts.DOC_DIRNAME for p in written)


@pytest.fixture(scope="module")
def generated_schema_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One shared generate() call for the read-only content assertions below (b)-(d), (f) -- they only
    inspect the output, so there is no need to regenerate per test."""
    out_dir = tmp_path_factory.mktemp("gen-artifacts-shared") / "schema"
    gen_artifacts.generate(out_dir=out_dir)
    return out_dir


# ---------------------------------------------------------------------------------------------------
# (b) JSON Schema contains the 13 Term subclasses and RequirementRegistry


def test_json_schema_contains_term_subclasses_and_requirement_registry(generated_schema_dir: Path):
    data = json.loads((generated_schema_dir / gen_artifacts.JSON_SCHEMA_FILENAME).read_text(encoding="utf-8"))
    defs = data["$defs"]
    missing = TERM_SUBCLASSES - defs.keys()
    assert not missing, f"missing Term subclasses in $defs: {missing}"
    assert "RequirementRegistry" in defs


def test_json_schema_is_sorted_keys_with_lf(generated_schema_dir: Path):
    raw = (generated_schema_dir / gen_artifacts.JSON_SCHEMA_FILENAME).read_bytes()
    assert raw.endswith(b"\n")
    assert b"\r\n" not in raw
    text = raw.decode("utf-8")
    reparsed = json.dumps(json.loads(text), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    assert text == reparsed  # already exactly the canonical sorted-keys rendering


# ---------------------------------------------------------------------------------------------------
# (c) OWL N-Triples contain the expanded class_uri of Capability (computed, never a literal)


def test_owl_ntriples_contain_capability_class_uri(generated_schema_dir: Path):
    capability_iri = load_config().iri.id_ns + "CAPABILITY"
    text = (generated_schema_dir / gen_artifacts.OWL_FILENAME).read_text(encoding="utf-8")
    assert f"<{capability_iri}>" in text


def test_owl_ntriples_use_the_schemas_declared_slot_and_class_uris(generated_schema_dir: Path):
    """``OwlSchemaGenerator`` is run with ``use_native_uris=False`` so it uses the schema's own
    declared ``slot_uri``/``class_uri`` (``itpra-o:groupedBy``, ``itpra:CAPABILITY``) rather than minting a
    second, OWL-only vocabulary from the Python slot/class names (``itpra-o:grouped_by``). Every IRI is
    computed from the loaded config, never a literal (ADR 0004; ``test_iri_config.py`` scans this file
    too)."""
    config = load_config()
    onto_ns, id_ns = config.iri.onto_ns, config.iri.id_ns
    text = (generated_schema_dir / gen_artifacts.OWL_FILENAME).read_text(encoding="utf-8")
    assert f"<{onto_ns}groupedBy>" in text
    assert f"<{id_ns}CAPABILITY>" in text
    assert f"<{onto_ns}grouped_by>" not in text


def test_owl_ntriples_have_no_double_fragment_iris(generated_schema_dir: Path):
    """Regression guard for the enum_iri_separator finding: no IRI under the (hash-shaped) onto
    namespace may contain a second '#' (computed from config, never a literal namespace)."""
    onto_ns = load_config().iri.onto_ns
    text = (generated_schema_dir / gen_artifacts.OWL_FILENAME).read_text(encoding="utf-8")
    double_fragment = re.compile(re.escape(onto_ns) + r"[^#\s>]*#")
    assert double_fragment.search(text) is None


# ---------------------------------------------------------------------------------------------------
# (d) SHACL N-Triples contain at least one sh:NodeShape


def test_shacl_ntriples_contain_a_node_shape(generated_schema_dir: Path):
    text = (generated_schema_dir / gen_artifacts.SHACL_FILENAME).read_text(encoding="utf-8")
    assert "<http://www.w3.org/ns/shacl#NodeShape>" in text


def test_shacl_ntriples_are_sorted_lf_terminated(generated_schema_dir: Path):
    raw = (generated_schema_dir / gen_artifacts.SHACL_FILENAME).read_bytes()
    assert raw.endswith(b"\n")
    lines = raw.decode("utf-8").splitlines()
    assert lines == sorted(lines)


# ---------------------------------------------------------------------------------------------------
# (e) main(check_only=True) returns 1 when dist/schema/ is missing


def _write_isolated_config(tmp_path: Path) -> Path:
    """A config file living in ``tmp_path`` whose ``[paths] dist_dir`` resolves to an empty, isolated
    location (``tmp_path`` itself is that location's parent, since dist_dir is relative to the config
    file's own directory) -- so ``dist_schema_dir()`` for this config has never been generated into."""
    config_path = tmp_path / "itpra-onto.toml"
    config_path.write_text(
        '[iri]\n'
        'base = "https://example.test/ns/itpra-gen-artifacts-check/"\n'
        'id_path = "id/"\n'
        'onto_path = "onto#"\n'
        'graph_path = "graph/"\n'
        "\n"
        "[paths]\n"
        'dist_dir = "dist"\n',
        encoding="utf-8",
    )
    return config_path


def test_main_check_returns_1_when_dist_schema_is_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = _write_isolated_config(tmp_path)
    monkeypatch.setenv("ITPRA_ONTO_CONFIG", str(config_path))

    assert not (tmp_path / "dist" / "schema").exists()
    assert gen_artifacts.main(check_only=True) == 1


def test_main_check_cli_returns_1_when_dist_schema_is_missing(tmp_path: Path):
    config_path = _write_isolated_config(tmp_path)
    result = subprocess.run(
        [sys.executable, "-m", "itpra_onto.cli", "gen-artifacts", "--check"],
        cwd=PROJECT_ROOT,
        env={**os.environ, "ITPRA_ONTO_CONFIG": str(config_path)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr


def test_main_generates_then_check_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config_path = _write_isolated_config(tmp_path)
    monkeypatch.setenv("ITPRA_ONTO_CONFIG", str(config_path))

    assert gen_artifacts.main(check_only=False) == 0
    assert (tmp_path / "dist" / "schema" / gen_artifacts.OWL_FILENAME).exists()
    assert gen_artifacts.main(check_only=True) == 0


# ---------------------------------------------------------------------------------------------------
# (f) no generated file contains an absolute filesystem path or a date stamp


def test_no_generated_file_contains_a_date_stamp_or_absolute_path(generated_schema_dir: Path):
    offenders: dict[str, list[str]] = {}
    for path in _iter_generated_files(generated_schema_dir):
        text = path.read_text(encoding="utf-8", errors="strict")
        hits = [line for line in text.splitlines() if _DATE_STAMP_RE.search(line) or _ABS_PATH_RE.search(line)]
        if hits:
            offenders[str(path.relative_to(generated_schema_dir))] = hits
    assert offenders == {}, offenders


def test_no_generated_file_contains_this_repos_own_path(generated_schema_dir: Path):
    """A sharper, this-machine-specific check alongside the generic pattern above: the literal absolute
    path of this checkout/worktree must not leak into any generated artefact (PydanticGenerator echoes its
    ``source_file`` unless told not to)."""
    repo_root_str = str(PROJECT_ROOT)
    for path in _iter_generated_files(generated_schema_dir):
        text = path.read_text(encoding="utf-8", errors="strict")
        assert repo_root_str not in text, f"{path} contains this worktree's own absolute path"


def test_pydantic_module_has_no_source_file_key(generated_schema_dir: Path):
    text = (generated_schema_dir / gen_artifacts.PYDANTIC_FILENAME).read_text(encoding="utf-8")
    assert "'source_file'" not in text
    assert '"source_file"' not in text

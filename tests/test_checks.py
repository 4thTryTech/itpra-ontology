"""Tests for tools/check-version-bump.py, check-links.py and publication-scan.py (pure functions)."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bump = load("check-version-bump")
links = load("check-links")
scan = load("publication-scan")


class VersionBump(unittest.TestCase):
    def test_vocabulary_change_requires_a_higher_version(self):
        ok, _ = bump.verdict("ontology_version: 3.16.3\n", "ontology_version: 3.16.3\n", ["terms/x.yaml"])
        self.assertFalse(ok)
        ok, _ = bump.verdict("ontology_version: 3.16.3\n", "ontology_version: 3.16.4\n", ["terms/x.yaml"])
        self.assertTrue(ok)
        ok, _ = bump.verdict("ontology_version: 3.16.3\n", "ontology_version: 3.16.2\n", ["schema.yaml"])
        self.assertFalse(ok)

    def test_non_vocabulary_change_needs_no_bump(self):
        ok, msg = bump.verdict("ontology_version: 3.16.3\n", "ontology_version: 3.16.3\n", ["README.md", "tools/x.py"])
        self.assertTrue(ok)
        ok, msg = bump.verdict("ontology_version: 3.16.3\n", "ontology_version: 4.0.0\n", ["CHANGELOG.md"])
        self.assertTrue(ok); self.assertIn("release bump", msg)

    def test_no_base_passes_when_well_formed(self):
        self.assertTrue(bump.verdict(None, "ontology_version: 4.0.0\n", [])[0])
        self.assertFalse(bump.verdict(None, "ontology_version: 4.0\n", [])[0])


class Links(unittest.TestCase):
    def test_relative_links_must_resolve(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "a.md").write_text("[ok](b.md) [anchor](b.md#x) [web](https://example.org) [bad](c.md)\n")
            (root / "b.md").write_text("# b\n")
            problems = links.broken_links(root)
            self.assertEqual(len(problems), 1); self.assertIn("c.md", problems[0])


class Scan(unittest.TestCase):
    def test_private_references_are_found_and_urls_exempt(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root / "terms").mkdir()
            (root / "terms" / "x.yaml").write_text("# see EUC/docs/10-capabilities/x.md\n- id: X\n  source: ADR 0001\n")
            (root / "ok.md").write_text("- https://example.org/docs/10-things · fine\n")
            hits = scan.scan(root)
            self.assertEqual(len(hits), 1); self.assertIn("terms/x.yaml:1", hits[0])


if __name__ == "__main__":
    unittest.main()


notes = load("release-notes")


class ReleaseNotes(unittest.TestCase):
    CHANGELOG = "# Changelog\n\nIntro.\n\n## 4.1.0 — 2026-12-01\n\nAdded a term.\n\n## 4.0.0 — 2026-11-21\n\nFirst release.\nTwo lines.\n\n## Before 4.0.0\n\nHistory.\n"

    def test_section_is_the_body_under_the_version_heading(self):
        self.assertEqual(notes.section(self.CHANGELOG, "4.0.0"), "First release.\nTwo lines.\n")
        self.assertEqual(notes.section(self.CHANGELOG, "4.1.0"), "Added a term.\n")

    def test_missing_version_is_none_and_prefixes_do_not_match(self):
        self.assertIsNone(notes.section(self.CHANGELOG, "4.0"))
        self.assertIsNone(notes.section(self.CHANGELOG, "3.16.3"))

    def test_main_fails_without_a_section(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "CHANGELOG.md"
            path.write_text(self.CHANGELOG, encoding="utf-8")
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(notes.main(["4.0.0", "--changelog", str(path)]), 0)
                self.assertEqual(notes.main(["9.9.9", "--changelog", str(path)]), 1)

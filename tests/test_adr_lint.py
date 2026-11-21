"""Tests for tools/adr-lint.py — run with: python -m unittest discover -s tests -v"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path

LINT = Path(__file__).resolve().parents[1] / "tools" / "adr-lint.py"
spec = importlib.util.spec_from_file_location("adr_lint", LINT)
adr_lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adr_lint)


def args(**over) -> argparse.Namespace:
    base = dict(strict=False, soft_lines=60, soft_words=500, max_lines=80, max_words=700)
    base.update(over)
    return argparse.Namespace(**base)


def record(number: str, title: str = "A short noun phrase", *, status="Accepted", date="2026-11-21",
           sup="—", supby="—", origin: str | None = None, context=None, decision=None,
           consequences=None, alternatives=None, sources=None) -> str:
    context = context or ["The question in one line and the constraint in another."]
    decision = decision or ["1. The rule, stated once in the present tense.", "2. The second rule."]
    consequences = consequences or ["- A consequence.", "- Another consequence.", "- A trade-off accepted."]
    alternatives = alternatives or ["- Doing nothing — the gap would stay open."]
    sources = sources or ["- https://example.org/spec · the standard behind rule 1 · accessed 2026-11-21"]
    head = [f"# ADR {number} — {title}", "",
            f"Status: {status}  ", f"Date: {date}  ", f"Supersedes: {sup}  ", f"Superseded by: {supby}  "]
    if origin:
        head += ["", f"Origin: {origin}"]
    body = ["", "## Context", "", *context, "", "## Decision", "", *decision, "", "## Consequences", "",
            *consequences, "", "## Alternatives", "", *alternatives, "", "## Sources", "", *sources, ""]
    return "\n".join(head + body)


def index(rows: list[tuple[str, str, str, str, str]]) -> str:
    head = ["# Decision records", "", "## Index", "", "| ADR | Title | Status | Date |", "|---|---|---|---|"]
    return "\n".join(head + [f"| {n} | [{t}]({f}) | {s} | {d} |" for n, t, f, s, d in rows]) + "\n"


class LintCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, files: dict[str, str], rows=None) -> None:
        for name, text in files.items():
            (self.dir / name).write_text(text, encoding="utf-8")
        if rows is not None:
            (self.dir / "README.md").write_text(index(rows), encoding="utf-8")

    def lint(self, **over):
        return adr_lint.lint_dir(self.dir, args(**over))

    def messages(self, rep):
        return [m for _, _, m in rep.errors]

    def valid_pair(self):
        self.write({
            "0001-first.md": record("0001", "First decision"),
            "0002-second.md": record("0002", "Second decision", decision=["1. Builds on ADR 0001."]),
        }, rows=[("0001", "First decision", "0001-first.md", "Accepted", "2026-11-21"),
                 ("0002", "Second decision", "0002-second.md", "Accepted", "2026-11-21")])

    def test_valid_set_passes_clean(self):
        self.valid_pair()
        rep = self.lint(strict=True)
        self.assertEqual(rep.errors, [])
        self.assertEqual(rep.warnings, [])

    def test_template_and_readme_are_skipped(self):
        self.valid_pair()
        (self.dir / "0000-template.md").write_text("# ADR NNNN — <title>\n", encoding="utf-8")
        self.assertEqual(self.lint().errors, [])

    def test_proposed_is_an_error(self):
        self.write({"0001-x.md": record("0001", status="Proposed")},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Proposed", "2026-11-21")])
        self.assertTrue(any("Proposed" in m for m in self.messages(self.lint())))

    def test_missing_section_and_stray_heading(self):
        text = record("0001").replace("## Alternatives", "## Options")
        self.write({"0001-x.md": text}, rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        msgs = self.messages(self.lint())
        self.assertTrue(any("missing section '## Alternatives'" in m for m in msgs))
        self.assertTrue(any("heading not in the template" in m for m in msgs))

    def test_banned_vocabulary(self):
        bad = ["1. In this session the sub-project moved the monorepo.", "2. See ITO ADR 0001 and FR-SEC-1 and Claude."]
        self.write({"0001-x.md": record("0001", decision=bad)},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        msgs = " ".join(self.messages(self.lint()))
        for label in ("session", "sub-project", "monorepo", "another repository", "requirement id", "Claude"):
            self.assertIn(label, msgs)

    def test_capability_label_with_red_teaming_is_allowed_but_narrative_is_not(self):
        ok = ["1. `CAP-X-1` AI Red-Teaming & Adversarial Testing is a capability."]
        self.write({"0001-x.md": record("0001", decision=ok)},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        self.assertEqual(self.lint().errors, [])
        self.write({"0001-x.md": record("0001", decision=["1. The red-team review found a gap."])})
        self.assertTrue(any("red team" in m for m in self.messages(self.lint())))

    def test_banned_token_inside_a_url_is_not_flagged(self):
        src = ["- https://labs.example.org/research/docs/paper.html · supports rule 1 · accessed 2026-11-21"]
        self.write({"0001-x.md": record("0001", sources=src)},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        self.assertEqual(self.lint().errors, [])

    def test_operating_model_vocabulary_only_in_alternatives(self):
        self.write({"0001-x.md": record("0001", decision=["1. The ITIL change process is the rule."])},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        self.assertTrue(any("operating-model vocabulary in Decision" in m for m in self.messages(self.lint())))
        self.write({"0001-x.md": record("0001", alternatives=["- Adopt the ITIL change process — binds an operating model."])})
        self.assertEqual(self.lint().errors, [])

    def test_links_must_stay_inside_the_folder(self):
        ctx = ["See [the first](0001-x.md), [the web](https://example.org) and [outside](../70-adrs/0013.md)."]
        self.write({"0001-x.md": record("0001", context=ctx)},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        msgs = self.messages(self.lint())
        self.assertEqual(len([m for m in msgs if "link leaves decisions/" in m]), 1)

    def test_unresolved_reference_is_a_warning_then_strict_error(self):
        self.write({"0001-x.md": record("0001", decision=["1. Follows ADR 0007."])},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        rep = self.lint()
        self.assertEqual(rep.errors, [])
        self.assertTrue(any("ADR 0007 is not a record" in m for _, _, m in rep.warnings))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(adr_lint.main(["--path", str(self.dir), "--strict"]), 1)
            self.assertEqual(adr_lint.main(["--path", str(self.dir)]), 0)

    def test_numbering_gap_is_a_warning(self):
        self.write({"0001-a.md": record("0001"), "0003-c.md": record("0003")},
                   rows=[("0001", "A short noun phrase", "0001-a.md", "Accepted", "2026-11-21"),
                         ("0003", "A short noun phrase", "0003-c.md", "Accepted", "2026-11-21")])
        rep = self.lint()
        self.assertEqual(rep.errors, [])
        self.assertTrue(any("not contiguous" in m and "0002" in m for _, _, m in rep.warnings))

    def test_length_limits(self):
        long_ctx = ["A line of context."] * 6
        many = [f"- Consequence {i}." for i in range(1, 7)]
        padding = [f"{i}. Rule number {i} stated at length to add words to the record body here." for i in range(1, 75)]
        self.write({"0001-x.md": record("0001", context=long_ctx, consequences=many, decision=padding)},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        msgs = self.messages(self.lint())
        self.assertTrue(any("hard limit 80" in m for m in msgs))
        self.assertTrue(any("hard limit 700" in m for m in msgs))

    def test_soft_limit_is_a_warning(self):
        decision = [f"{i}. A rule." for i in range(1, 50)]
        self.write({"0001-x.md": record("0001", decision=decision)},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        rep = self.lint()
        self.assertEqual(rep.errors, [])
        self.assertTrue(any("target 60" in m for _, _, m in rep.warnings))

    def test_context_consequences_and_sources_shape(self):
        self.write({"0001-x.md": record("0001", context=["x"] * 7, consequences=["- one", "- two"],
                                         sources=["- https://example.org · no access date"])},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        msgs = " ".join(self.messages(self.lint()))
        self.assertIn("Context has 7 lines", msgs)
        self.assertIn("Consequences has 2 bullets", msgs)
        self.assertIn("accessed YYYY-MM-DD", msgs)

    def test_index_must_match_records(self):
        self.write({"0001-x.md": record("0001", "Real title")},
                   rows=[("0001", "Real title", "0001-x.md", "Superseded", "2026-11-20"),
                         ("0002", "Ghost", "0002-ghost.md", "Accepted", "2026-11-21")])
        msgs = " ".join(self.messages(self.lint()))
        self.assertIn("status Superseded, record says Accepted", msgs)
        self.assertIn("date 2026-11-20", msgs)
        self.assertIn("row 0002 has no record file", msgs)
        self.write({"0003-y.md": record("0003")})
        self.assertIn("index has no row for ADR 0003", " ".join(self.messages(self.lint())))

    def test_supersession_is_checked_both_ways(self):
        self.write({
            "0001-old.md": record("0001", "Old", status="Superseded", supby="ADR 0002"),
            "0002-new.md": record("0002", "New"),
        }, rows=[("0001", "Old", "0001-old.md", "Superseded", "2026-11-21"),
                 ("0002", "New", "0002-new.md", "Accepted", "2026-11-21")])
        self.assertTrue(any("does not list ADR 0001 under Supersedes" in m for m in self.messages(self.lint())))
        self.write({"0002-new.md": record("0002", "New", sup="ADR 0001")})
        self.assertEqual(self.lint().errors, [])
        self.write({"0001-old.md": record("0001", "Old", supby="ADR 0002")})  # Accepted with a successor
        self.assertTrue(any("must have status Superseded" in m for m in self.messages(self.lint())))

    def test_status_block_must_be_four_lines(self):
        text = record("0001").replace("Date: 2026-11-21  \n", "")
        self.write({"0001-x.md": text}, rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        self.assertTrue(any("four-line status block" in m for m in self.messages(self.lint())))

    def test_origin_line_is_allowed(self):
        self.write({"0001-x.md": record("0001", origin="Consolidates decisions taken between 2026-05 and 2026-11, before publication.")},
                   rows=[("0001", "A short noun phrase", "0001-x.md", "Accepted", "2026-11-21")])
        self.assertEqual(self.lint(strict=True).errors, [])


if __name__ == "__main__":
    unittest.main()

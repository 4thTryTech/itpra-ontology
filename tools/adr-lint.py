#!/usr/bin/env python3
"""adr-lint — checks the decision records in decisions/ against the template and the writing standard.

Usage: python tools/adr-lint.py [--path decisions] [--strict] [--soft-lines 60] [--soft-words 500]
                                [--max-lines 80] [--max-words 700]

Exit status 1 on any error. --strict also fails on the structural warnings (numbering gaps, unresolved
cross-references), which is how CI runs it on main; while a set of records is being authored on a branch
those stay warnings. Standard library only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

SECTIONS = ["Context", "Decision", "Consequences", "Alternatives", "Sources"]
STATUSES = {"Accepted", "Superseded", "Deprecated", "Rejected"}

FILENAME_RE = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
H1_RE = re.compile(r"^# ADR (\d{4}) — (.+)$")
# The status block is four lines (each may end with two spaces, Markdown's hard line break), then a blank line.
STATUS_LINES = [
    ("status", re.compile(r"^Status: (?P<v>[A-Za-z]+) {0,2}$")),
    ("date", re.compile(r"^Date: (?P<v>\d{4}-\d{2}-\d{2}) {0,2}$")),
    ("sup", re.compile(r"^Supersedes: (?P<v>—|ADR \d{4}(?:, ADR \d{4})*) {0,2}$")),
    ("supby", re.compile(r"^Superseded by: (?P<v>—|ADR \d{4}) {0,2}$")),
]
ORIGIN_RE = re.compile(r"^Origin: \S.*$")
NUMBERED_RE = re.compile(r"^(\d+)\. \S")
BULLET_RE = re.compile(r"^- \S")
CONTINUATION_RE = re.compile(r"^ {2,}\S")
SOURCE_RE = re.compile(r"^- <?https?://\S+?>? · .+? · accessed (\d{4}-\d{2}-\d{2})$")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
LOCAL_LINK_RE = re.compile(r"^(?:\d{4}-[a-z0-9-]+\.md|README\.md|0000-template\.md)?(?:#[A-Za-z0-9_-]+)?$")
URL_RE = re.compile(r"<?https?://\S+>?")
ADR_REF_RE = re.compile(r"\bADR[ -](\d{4})\b")
INDEX_ROW_RE = re.compile(r"^\| (\d{4}) \| \[(.+?)\]\((\d{4}-[a-z0-9-]+\.md)\) \| ([A-Za-z]+) \| (\d{4}-\d{2}-\d{2}) \|$")

# Vocabulary that would show the record was written somewhere else, for someone else, or about something private.
BANNED = [
    (re.compile(r"\bmonorepo\b", re.I), "monorepo"),
    (re.compile(r"\bsub-?projects?\b", re.I), "sub-project"),
    (re.compile(r"\b9[012]-[a-z]", re.I), "a private directory name"),
    (re.compile(r"\b7[0-9]-adrs\b", re.I), "a decision home of another repository"),
    (re.compile(r"\bAGENT-STATE\b"), "AGENT-STATE"),
    (re.compile(r"\bwork[- ]packages?\b", re.I), "work package"),
    (re.compile(r"\bWP\b"), "WP"),
    (re.compile(r"\bPhase\s+[0-9A-Z]\b"), "Phase n"),
    (re.compile(r"\b(?:this|the|a|per|next|prior|previous|each|every|same|one) sessions?\b", re.I), "session (narrative)"),
    (re.compile(r"\borchestrators?\b", re.I), "orchestrator"),
    (re.compile(r"\bbuilders?\b", re.I), "builder"),
    (re.compile(r"\bowner checkpoint\b", re.I), "owner checkpoint"),
    (re.compile(r"\bred[- ]team(?:ed|ing|s)?\b(?!\s*&)", re.I), "red team"),  # a term label "… Red-Teaming & …" is allowed
    (re.compile(r"\bresearch/"), "a research path"),
    (re.compile(r"\bdocs/"), "a document path"),
    (re.compile(r"\b0\d-[a-z]+(?:-[a-z]+)*/", re.I), "a methodology or document folder"),
    (re.compile(r"\bClaude\b"), "Claude"),
    (re.compile(r"\bitpra-framework\b", re.I), "the name of another repository"),
    (re.compile(r"\b(?:ITO|EUC|SVD|FLD|ADM|DCF|NET|GRC|ITSM|BIA|DXC|root|framework|sub-project|scenario|local) ADRs?\b"), "a record of another repository"),
    (re.compile(r"\b(?:FR|NFR)-[A-Z][A-Z0-9_]*-\d+\b"), "a requirement id (requirements are not vocabulary)"),
    (re.compile(r"\bOQ-[A-Z0-9-]+\b"), "an open-question id"),
]
# Operating-model process vocabulary: never in Context, Decision or Consequences (an Alternative may name it once).
OPERATING_MODEL = [
    (re.compile(r"\bITIL\b"), "ITIL"),
    (re.compile(r"\bDevOps\b"), "DevOps"),
    (re.compile(r"\bCMDB\b"), "CMDB"),
    (re.compile(r"\b[SOX]LAs?\b"), "SLA/OLA/XLA"),
]


class Report:
    def __init__(self) -> None:
        self.errors: list[tuple[str, int, str]] = []
        self.warnings: list[tuple[str, int, str]] = []

    def error(self, file: str, line: int, msg: str) -> None:
        self.errors.append((file, line, msg))

    def warn(self, file: str, line: int, msg: str) -> None:
        self.warnings.append((file, line, msg))


def split_sections(lines: list[str]) -> tuple[dict[str, tuple[int, list[str]]], list[tuple[int, str]]]:
    """Return {section: (start_line_no, body_lines)} and the list of heading lines that are not the five H2."""
    sections: dict[str, tuple[int, list[str]]] = {}
    stray: list[tuple[int, str]] = []
    current: str | None = None
    for no, line in enumerate(lines, start=1):
        if no == 1:
            continue
        if line.startswith("#"):
            m = re.match(r"^## (\S.*)$", line)
            if m and m.group(1) in SECTIONS and m.group(1) not in sections:
                current = m.group(1)
                sections[current] = (no, [])
            else:
                stray.append((no, line))
                current = None
            continue
        if current:
            sections[current][1].append(line)
    return sections, stray


def items(body: list[str], pattern: re.Pattern[str]) -> tuple[list[str], list[str]]:
    """Split a section body into list items (pattern) and lines that are neither items, continuations nor blank."""
    found, bad = [], []
    for line in body:
        if not line.strip():
            continue
        if pattern.match(line):
            found.append(line)
        elif CONTINUATION_RE.match(line) and found:
            found[-1] += " " + line.strip()
        else:
            bad.append(line)
    return found, bad


def lint_record(path: Path, rep: Report, known: set[str], args: argparse.Namespace) -> dict | None:
    name = path.name
    f = str(path)
    m = FILENAME_RE.match(name)
    if not m:
        rep.error(f, 0, "file name must be NNNN-kebab-title.md")
        return None
    number = m.group(1)
    if number == "0000":
        rep.error(f, 0, "0000 is reserved for the template")
        return None
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if not text.endswith("\n"):
        rep.warn(f, len(lines), "file should end with a newline")

    # H1 and status block
    h1 = H1_RE.match(lines[0]) if lines else None
    title = ""
    if not h1:
        rep.error(f, 1, "first line must be '# ADR NNNN — <title>'")
    else:
        title = h1.group(2).strip()
        if h1.group(1) != number:
            rep.error(f, 1, f"heading number {h1.group(1)} differs from file number {number}")
        if len(title) > 90:
            rep.error(f, 1, "title longer than 90 characters; use a short noun phrase")
        if title.endswith("."):
            rep.error(f, 1, "title ends with a period")
    if len(lines) < 3 or lines[1].strip():
        rep.error(f, 2, "line 2 must be blank")
    status = {"status": "", "date": "", "sup": "—", "supby": "—"}
    ok = True
    for i, (key, rx) in enumerate(STATUS_LINES):
        line_no = 3 + i
        m2 = rx.match(lines[line_no - 1]) if len(lines) >= line_no else None
        if not m2:
            rep.error(f, line_no, f"line {line_no} must read '{key.replace('supby', 'Superseded by').replace('sup', 'Supersedes').capitalize() if key in ('sup', 'supby') else key.capitalize()}: …' "
                                  "(the four-line status block: Status, Date, Supersedes, Superseded by)")
            ok = False
        else:
            status[key] = m2.group("v")
    if ok:
        if status["status"] == "Proposed":
            rep.error(f, 3, "'Proposed' never lands: a record is proposed as a pull request and is Accepted when it merges")
        elif status["status"] not in STATUSES:
            rep.error(f, 3, f"unknown status '{status['status']}' (Accepted, Superseded, Deprecated, Rejected)")
        try:
            dt.date.fromisoformat(status["date"])
        except ValueError:
            rep.error(f, 3, f"invalid date {status['date']}")
        if status["supby"] != "—" and status["status"] != "Superseded":
            rep.error(f, 3, "a record with a successor must have status Superseded")
        if status["status"] == "Superseded" and status["supby"] == "—":
            rep.error(f, 3, "status Superseded needs 'Superseded by: ADR NNNN'")
    body_start = 7  # 0-based index of the line after the status block and its blank line
    if len(lines) > 6 and lines[6].strip():
        rep.error(f, 7, "a blank line must follow the status block")
    if len(lines) > 7 and lines[7].startswith("Origin:"):
        if not ORIGIN_RE.match(lines[7].rstrip()):
            rep.error(f, 8, "Origin line must be one non-empty line")
        body_start = 9
        if len(lines) > 8 and lines[8].strip():
            rep.error(f, 9, "a blank line must follow the Origin line")
    if len(lines) > body_start and lines[body_start].strip() and not lines[body_start].startswith("## Context"):
        rep.error(f, body_start + 1, "'## Context' must follow the status block (and the optional Origin line)")

    # Sections
    sections, stray = split_sections(lines)
    for no, line in stray:
        rep.error(f, no, f"heading not in the template: {line.strip()!r} (only the five H2 sections are allowed)")
    order = [s for s in sections]
    if order != [s for s in SECTIONS if s in sections]:
        rep.error(f, 0, f"sections out of order: {order}")
    for s in SECTIONS:
        if s not in sections:
            rep.error(f, 0, f"missing section '## {s}'")

    if "Context" in sections:
        no, body = sections["Context"]
        n = sum(1 for l in body if l.strip())
        if n == 0:
            rep.error(f, no, "Context is empty")
        if n > 6:
            rep.error(f, no, f"Context has {n} lines; at most 6")
    if "Decision" in sections:
        no, body = sections["Decision"]
        found, bad = items(body, NUMBERED_RE)
        if not found:
            rep.error(f, no, "Decision needs at least one numbered rule")
        for l in bad:
            rep.error(f, no, f"Decision holds a line that is not a numbered rule: {l.strip()[:60]!r}")
        nums = [int(NUMBERED_RE.match(l).group(1)) for l in found]
        if nums and nums != list(range(1, len(nums) + 1)):
            rep.error(f, no, f"Decision rules must be numbered 1..n, found {nums}")
    if "Consequences" in sections:
        no, body = sections["Consequences"]
        found, bad = items(body, BULLET_RE)
        for l in bad:
            rep.error(f, no, f"Consequences holds a line that is not a bullet: {l.strip()[:60]!r}")
        if not 3 <= len(found) <= 6:
            rep.error(f, no, f"Consequences has {len(found)} bullets; three to six")
    if "Alternatives" in sections:
        no, body = sections["Alternatives"]
        found, bad = items(body, BULLET_RE)
        for l in bad:
            rep.error(f, no, f"Alternatives holds a line that is not a bullet: {l.strip()[:60]!r}")
        if not found:
            rep.error(f, no, "Alternatives needs at least one line")
        for l in found:
            if " — " not in l:
                rep.error(f, no, f"an alternative reads '<name> — <why not>': {l.strip()[:60]!r}")
    if "Sources" in sections:
        no, body = sections["Sources"]
        found, bad = items(body, BULLET_RE)
        for l in bad:
            rep.error(f, no, f"Sources holds a line that is not a bullet: {l.strip()[:60]!r}")
        if not found:
            rep.error(f, no, "Sources needs at least one row")
        for l in found:
            sm2 = SOURCE_RE.match(l)
            if not sm2:
                rep.error(f, no, f"a source reads '- URL · what it supports · accessed YYYY-MM-DD': {l.strip()[:70]!r}")
            else:
                try:
                    dt.date.fromisoformat(sm2.group(1))
                except ValueError:
                    rep.error(f, no, f"invalid access date in source: {l.strip()[:70]!r}")

    # Length
    n_lines = sum(1 for l in lines if l.strip())
    n_words = len(text.split())
    if n_lines > args.max_lines:
        rep.error(f, 0, f"{n_lines} non-blank lines; hard limit {args.max_lines}")
    elif n_lines > args.soft_lines:
        rep.warn(f, 0, f"{n_lines} non-blank lines; target {args.soft_lines}")
    if n_words > args.max_words:
        rep.error(f, 0, f"{n_words} words; hard limit {args.max_words}")
    elif n_words > args.soft_words:
        rep.warn(f, 0, f"{n_words} words; target {args.soft_words}")

    # Vocabulary: banned tokens anywhere (URLs removed first); operating-model terms outside Alternatives/Sources
    for no, line in enumerate(lines, start=1):
        stripped = URL_RE.sub("", line)
        for rx, label in BANNED:
            if rx.search(stripped):
                rep.error(f, no, f"banned vocabulary: {label}")
    for s in ("Context", "Decision", "Consequences"):
        if s in sections:
            no, body = sections[s]
            for i, line in enumerate(body):
                for rx, label in OPERATING_MODEL:
                    if rx.search(URL_RE.sub("", line)):
                        rep.error(f, no + 1 + i, f"operating-model vocabulary in {s}: {label} (state the neutral outcome; an Alternative may name it once)")

    # Links and cross-references
    for no, line in enumerate(lines, start=1):
        for target in LINK_RE.findall(line):
            if target.startswith(("http://", "https://")):
                continue
            if not LOCAL_LINK_RE.match(target):
                rep.error(f, no, f"link leaves decisions/: {target}")
        if no == 1:
            continue
        for ref in ADR_REF_RE.findall(URL_RE.sub("", line)):
            if ref == number:
                continue
            if ref not in known:
                rep.warn(f, no, f"ADR {ref} is not a record in this folder (strict: error)")
    return {"file": name, "number": number, "title": title, **status}


def lint_dir(path: Path, args: argparse.Namespace) -> Report:
    rep = Report()
    files = sorted(p for p in path.glob("*.md") if p.name not in ("README.md", "0000-template.md"))
    known = {FILENAME_RE.match(p.name).group(1) for p in files if FILENAME_RE.match(p.name)}
    records = [r for r in (lint_record(p, rep, known, args) for p in files) if r]

    # Folder level: unique and contiguous numbers
    numbers = sorted(int(r["number"]) for r in records)
    dups = {n for n in numbers if numbers.count(n) > 1}
    for n in sorted(dups):
        rep.error(str(path), 0, f"number {n:04d} is used by more than one record")
    if numbers:
        expected = list(range(1, numbers[-1] + 1))
        gaps = sorted(set(expected) - set(numbers))
        if numbers[0] != 1 or gaps:
            rep.warn(str(path), 0, f"numbering is not contiguous from 0001; missing {[f'{g:04d}' for g in gaps] or ['0001']} (strict: error)")

    # Supersession consistency
    by_number = {r["number"]: r for r in records}
    for r in records:
        if r["supby"] != "—":
            succ = by_number.get(r["supby"][4:])
            if succ and r["number"] not in [s[4:] for s in succ["sup"].split(", ")] and succ["sup"] != "—":
                rep.error(str(path / r["file"]), 3, f"{r['supby']} does not list ADR {r['number']} under Supersedes")
            elif succ and succ["sup"] == "—":
                rep.error(str(path / r["file"]), 3, f"{r['supby']} does not list ADR {r['number']} under Supersedes")
        if r["sup"] != "—":
            for s in r["sup"].split(", "):
                pred = by_number.get(s[4:])
                if pred and (pred["status"] != "Superseded" or pred["supby"] != f"ADR {r['number']}"):
                    rep.error(str(path / r["file"]), 3, f"{s} must be Superseded by ADR {r['number']}")

    # Index
    readme = path / "README.md"
    if not readme.exists():
        rep.error(str(readme), 0, "decisions/README.md (the index) is missing")
    else:
        rows = {}
        for no, line in enumerate(readme.read_text(encoding="utf-8").split("\n"), start=1):
            m = INDEX_ROW_RE.match(line)
            if m:
                rows[m.group(1)] = (no, m.group(2), m.group(3), m.group(4), m.group(5))
        for r in records:
            row = rows.get(r["number"])
            if not row:
                rep.error(str(readme), 0, f"index has no row for ADR {r['number']}")
                continue
            no, title, link, status, date = row
            if link != r["file"]:
                rep.error(str(readme), no, f"row {r['number']} links {link}, file is {r['file']}")
            if title != r["title"]:
                rep.error(str(readme), no, f"row {r['number']} title differs from the record's heading")
            if status != r["status"]:
                rep.error(str(readme), no, f"row {r['number']} status {status}, record says {r['status']}")
            if date != r["date"]:
                rep.error(str(readme), no, f"row {r['number']} date {date}, record says {r['date']}")
        for n, (no, *_rest) in rows.items():
            if n not in by_number:
                rep.error(str(readme), no, f"index row {n} has no record file")
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lint the decision records.")
    ap.add_argument("--path", default="decisions")
    ap.add_argument("--strict", action="store_true", help="fail on numbering gaps and unresolved cross-references too")
    ap.add_argument("--soft-lines", type=int, default=60)
    ap.add_argument("--soft-words", type=int, default=500)
    ap.add_argument("--max-lines", type=int, default=80)
    ap.add_argument("--max-words", type=int, default=700)
    args = ap.parse_args(argv)
    path = Path(args.path)
    if not path.is_dir():
        print(f"adr-lint: {path} is not a directory", file=sys.stderr)
        return 2
    rep = lint_dir(path, args)
    n = len([p for p in path.glob("[0-9][0-9][0-9][0-9]-*.md") if p.name != "0000-template.md"])
    for file, line, msg in rep.errors:
        print(f"ERROR {file}:{line}: {msg}")
    for file, line, msg in rep.warnings:
        print(f"WARN  {file}:{line}: {msg}")
    failing = len(rep.errors) + (len([w for w in rep.warnings if "(strict: error)" in w[2]]) if args.strict else 0)
    print(f"adr-lint: {n} record(s), {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)"
          + (" [strict]" if args.strict else ""))
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())

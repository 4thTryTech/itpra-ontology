#!/usr/bin/env python3
"""ontology-lint.py — validate the ITPRA ontology's term files against schema.yaml and decisions/.

Merges schema.yaml, entities.yaml, relationships.yaml and every terms/*.yaml into one vocabulary and checks:
  yaml-parse-error        a file failed to parse
  termfile-not-list       a term file's top level is not a list of records
  record-not-mapping      a list entry is not a mapping
  field-missing           a required field (id, term, type, definition) is absent or whitespace-only
  field-unknown           a record carries a field schema.yaml's `fields:` does not define
  id-duplicate            the same id is defined more than once
  id-pattern              an id does not match schema.yaml's id pattern
  type-unknown            a record's `type` is not in schema.yaml's `types`
  relates-to-malformed    a `relates_to` entry is not a mapping
  verb-unknown            a `relates_to.rel` is not a declared relationship verb
  target-unresolved       a `relates_to.target` does not resolve to a defined id
  function-derived-from   a Function record uses `derived_from` (ADR 0011)
  source-grammar          a `source:` item mentions a record but is not `ADR NNNN`, `ADR NNNN (amended by …)`
                          or `ADR NNNN (extended by …)` (ADR 0005); an item carrying a URL is external and exempt
  source-adr-unresolved   a cited `ADR NNNN` has no record in decisions/ (ADR 0005)
  version-format          `ontology_version` is not X.Y.Z or `schema_version` is not an integer (ADR 0003)

Usage:  python tools/ontology-lint.py [--root DIR] [--json]
Exit 1 on any error; warnings never fail. Standard library plus PyYAML.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: PyYAML is required (pip install pyyaml)\n")
    sys.exit(2)

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ADR_ITEM_RE = re.compile(r"^ADR (\d{4})(?: \((amended|extended) by ADR \d{4}(?:, ADR \d{4})*\))?$")
ADR_NUM_RE = re.compile(r"\bADR (\d{4})\b")
URL_RE = re.compile(r"https?://")
DECISION_FILE_RE = re.compile(r"^(\d{4})-.+\.md$")


class Lint:
    def __init__(self) -> None:
        self.findings: list[dict] = []

    def err(self, rule: str, subject: str, msg: str, file: str = "") -> None:
        self.findings.append({"rule": rule, "subject": subject, "severity": "error", "message": msg, "file": file})

    def warn(self, rule: str, subject: str, msg: str, file: str = "") -> None:
        self.findings.append({"rule": rule, "subject": subject, "severity": "warning", "message": msg, "file": file})

    @property
    def errors(self) -> list[dict]:
        return [f for f in self.findings if f["severity"] == "error"]


def load_yaml(lint: Lint, path: Path, rel: str):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        lint.err("yaml-parse-error", rel, f"{rel}: {exc}", rel)
        return None


def decision_numbers(root: Path) -> set[str]:
    folder = root / "decisions"
    if not folder.is_dir():
        return set()
    return {m.group(1) for p in folder.glob("*.md") if (m := DECISION_FILE_RE.match(p.name)) and m.group(1) != "0000"}


def run(root: Path) -> tuple[Lint, dict]:
    lint = Lint()
    schema = load_yaml(lint, root / "schema.yaml", "schema.yaml") or {}
    types = set(schema.get("types", []))
    verbs = set(schema.get("relationships", []))
    id_pattern = re.compile(schema.get("id", {}).get("pattern", r"^[A-Za-z][A-Za-z0-9_.-]*$"))
    fields = set(schema["fields"]) if isinstance(schema.get("fields"), dict) else set()
    if not types:
        lint.warn("schema-types-missing", "schema.yaml", "schema.yaml declares no `types`; type checks limited", "schema.yaml")
    ov = str(schema.get("ontology_version", ""))
    if not SEMVER_RE.match(ov):
        lint.err("version-format", "schema.yaml", f"ontology_version {ov!r} is not X.Y.Z", "schema.yaml")
    if not isinstance(schema.get("schema_version"), int):
        lint.err("version-format", "schema.yaml", "schema_version must be an integer", "schema.yaml")

    term_files = [root / "entities.yaml", root / "relationships.yaml"] + sorted((root / "terms").glob("*.yaml"))
    terms: dict[str, dict] = {}
    for path in term_files:
        rel = path.relative_to(root).as_posix()
        data = load_yaml(lint, path, rel)
        if data is None:
            continue
        if not isinstance(data, list):
            lint.err("termfile-not-list", rel, f"{rel}: expected a top-level list of term records", rel)
            continue
        for rec in data:
            if not isinstance(rec, dict):
                lint.err("record-not-mapping", rel, f"{rel}: non-mapping record {rec!r}", rel)
                continue
            tid = rec.get("id")
            for field in ("id", "term", "type", "definition"):
                value = rec.get(field)
                if not value or not str(value).strip():
                    lint.err("field-missing", str(tid or rec), f"{rel}: record {tid or rec!r} missing required field {field!r}", rel)
            for field in sorted(set(rec) - fields, key=str) if fields else ():
                lint.err("field-unknown", str(tid), f"{rel}: record {tid!r} carries field {field!r}, not in schema.yaml `fields:`", rel)
            if not tid:
                continue
            if tid in terms:
                lint.err("id-duplicate", tid, f"{rel}: duplicate id {tid!r}", rel)
            if not id_pattern.match(str(tid)):
                lint.err("id-pattern", tid, f"{rel}: id {tid!r} does not match the id pattern", rel)
            if types and rec.get("type") not in types:
                lint.err("type-unknown", tid, f"{rel}: id {tid!r} has unknown type {rec.get('type')!r}", rel)
            rec["__file__"] = rel
            terms[tid] = rec

    known_decisions = decision_numbers(root)
    for tid, rec in terms.items():
        rel = rec["__file__"]
        for link in rec.get("relates_to") or []:
            if not isinstance(link, dict):
                lint.err("relates-to-malformed", tid, f"{rel}: {tid}: relates_to entry is not a mapping: {link!r}", rel)
                continue
            verb, target = link.get("rel"), link.get("target")
            if not isinstance(verb, str) or verb not in verbs:
                lint.err("verb-unknown", tid, f"{rel}: {tid}: unknown relationship verb {verb!r}", rel)
            if not isinstance(target, str) or target not in terms:
                lint.err("target-unresolved", tid, f"{rel}: {tid}: relates_to target {target!r} is not a defined id", rel)
            if verb == "derived_from" and rec.get("type") == "Function":
                lint.err("function-derived-from", tid, f"{rel}: {tid}: a Function may not use `derived_from` (ADR 0011)", rel)
        source = rec.get("source")
        if isinstance(source, str) and source.strip():
            for item in (s.strip() for s in source.split(";") if s.strip()):
                if URL_RE.search(item):
                    continue  # an external citation carrying a URL, whatever it mentions (ADR 0005)
                if "ADR" in item.upper() and not ADR_ITEM_RE.match(item):
                    lint.err("source-grammar", tid, f"{rel}: {tid}: source item {item!r} is not `ADR NNNN` with an optional amended/extended tail", rel)
                    continue
                for number in ADR_NUM_RE.findall(item):
                    if number not in known_decisions:
                        lint.err("source-adr-unresolved", tid, f"{rel}: {tid}: source cites ADR {number}, which has no record in decisions/", rel)

    summary = {"terms": len(terms), "decisions": len(known_decisions), "ontology_version": ov,
               "quality_attributes": sum(1 for r in terms.values() if r.get("type") == "QualityAttribute")}
    return lint, summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Lint the ITPRA ontology's term files.")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--json", action="store_true", help="emit findings as JSON and nothing else")
    args = ap.parse_args(argv)
    lint, summary = run(Path(args.root))
    if args.json:
        print(json.dumps(lint.findings, ensure_ascii=False))
        return 1 if lint.errors else 0
    print(f"ontology-lint: {summary['terms']} terms, {summary['quality_attributes']} quality attributes, "
          f"{summary['decisions']} decision records, ontology_version {summary['ontology_version']}")
    for f in lint.findings:
        print(f"  {'ERROR' if f['severity'] == 'error' else 'WARN '} {f['rule']}: {f['message']}")
    n_err = len(lint.errors); n_warn = len(lint.findings) - n_err
    print(f"{'FAILED' if n_err else 'OK'}: {n_err} error(s), {n_warn} warning(s)")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())

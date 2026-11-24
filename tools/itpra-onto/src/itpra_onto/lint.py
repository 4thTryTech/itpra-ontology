"""Lint the vocabulary: the ontology's own rules, implemented once (ADR 0042 D1, D5).

The rules here are the rows of the register's Table A (``shapes/REGISTER.md``): file shape, required and
unknown fields, unique ids and the id pattern, known types and verbs, resolving targets, ``derived_from``
kept off Functions (ADR 0011), the ``source:`` grammar and resolving decision citations (ADR 0005), the two
version numbers (ADR 0003). :func:`lint_vocabulary` returns the merged vocabulary beside its findings, so a
caller can check further rules against the same terms; ``itpra-onto parity`` compares these findings with the
shapes.

Standard library plus PyYAML only, so the module imports without the pipeline's RDF dependencies
(``import itpra_onto.lint`` with ``src/`` on ``sys.path`` is enough).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

Finding = dict[str, str]

REQUIRED_FIELDS = ("id", "term", "type", "definition")
DEFAULT_ID_PATTERN = r"^[A-Za-z][A-Za-z0-9_.-]*$"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
ADR_ITEM_RE = re.compile(r"^ADR (\d{4})(?: \((amended|extended) by ADR \d{4}(?:, ADR \d{4})*\))?$")
ADR_NUM_RE = re.compile(r"\bADR (\d{4})\b")
URL_RE = re.compile(r"https?://")
DECISION_FILE_RE = re.compile(r"^(\d{4})-.+\.md$")
NOT_VOCABULARY = ("schema.yaml", "PIN.yaml")  # the meta-schema, and the pin file of a vendored copy (ADR 0003)

# Every rule id this module emits — the register's `core`-home Table A rows (tests keep the two in step).
CORE_RULE_IDS = (
    "yaml-parse-error",
    "termfile-not-list",
    "record-not-mapping",
    "field-missing",
    "field-unknown",
    "id-duplicate",
    "id-pattern",
    "type-unknown",
    "relates-to-malformed",
    "verb-unknown",
    "target-unresolved",
    "function-derived-from",
    "schema-types-missing",
    "source-grammar",
    "source-adr-unresolved",
    "version-format",
)


@dataclass
class Vocabulary:
    """The merged vocabulary a lint run read: what further rules over the same terms need."""

    terms: dict[str, dict[str, Any]] = field(default_factory=dict)  # id -> record, in file order
    files: dict[str, str] = field(default_factory=dict)  # id -> the file label it was read from
    types: set[str] = field(default_factory=set)
    verbs: set[str] = field(default_factory=set)
    fields: set[str] = field(default_factory=set)
    quality_attributes: set[str] = field(default_factory=set)
    decisions: set[str] = field(default_factory=set)
    ontology_version: str = ""
    schema: dict[str, Any] = field(default_factory=dict)


class _Sink:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def err(self, rule: str, subject: str, msg: str, file: str) -> None:
        self.findings.append({"rule": rule, "subject": subject, "severity": "error", "message": msg, "file": file})

    def warn(self, rule: str, subject: str, msg: str, file: str) -> None:
        self.findings.append({"rule": rule, "subject": subject, "severity": "warning", "message": msg, "file": file})


def vocabulary_files(root: Path) -> list[Path]:
    """The vocabulary's files, the set the emitter reads too: every ``*.yaml`` directly under ``root`` except
    ``schema.yaml`` and ``PIN.yaml``, then every ``*.yaml`` under ``terms/`` (ADR 0007)."""
    top = sorted(p for p in root.glob("*.yaml") if p.name not in NOT_VOCABULARY)
    terms = sorted((root / "terms").glob("*.yaml")) if (root / "terms").is_dir() else []
    return top + terms


def decision_numbers(decisions_dir: Path) -> set[str]:
    """The ``NNNN`` of every ``decisions/NNNN-<slug>.md``; ``0000`` is the template."""
    if not decisions_dir.is_dir():
        return set()
    return {m.group(1) for p in decisions_dir.glob("*.md") if (m := DECISION_FILE_RE.match(p.name)) and m.group(1) != "0000"}


def _label(path: Path, rel_to: Path) -> str:
    try:
        return path.resolve().relative_to(rel_to.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_yaml(sink: _Sink, path: Path, label: str) -> Any:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        sink.err("yaml-parse-error", label, f"{label}: YAML parse error: {exc}", label)
        return None
    except OSError as exc:
        sink.err("yaml-parse-error", label, f"{label}: cannot read: {exc}", label)
        return None


def lint_vocabulary(
    root: Path, *, decisions_dir: Path | None = None, rel_to: Path | None = None
) -> tuple[list[Finding], Vocabulary]:
    """Lint the vocabulary under ``root`` (``schema.yaml`` beside its term files). ``decisions_dir`` defaults to
    ``root/decisions``; ``rel_to`` is the directory file labels are made relative to (default ``root``).
    Returns the findings in emission order and the merged :class:`Vocabulary`."""
    root = Path(root)
    rel_to = Path(rel_to) if rel_to is not None else root
    decisions_dir = Path(decisions_dir) if decisions_dir is not None else root / "decisions"
    sink = _Sink()
    vocab = Vocabulary()

    schema_label = _label(root / "schema.yaml", rel_to)
    schema = _load_yaml(sink, root / "schema.yaml", schema_label) or {}
    if not isinstance(schema, dict):
        sink.err("yaml-parse-error", schema_label, f"{schema_label}: expected a mapping at the top level", schema_label)
        schema = {}
    vocab.schema = schema
    vocab.types = set(schema.get("types") or [])
    vocab.verbs = set(schema.get("relationships") or [])
    id_spec = schema.get("id") if isinstance(schema.get("id"), dict) else {}
    id_pattern = re.compile(id_spec.get("pattern", DEFAULT_ID_PATTERN))
    vocab.fields = set(schema["fields"]) if isinstance(schema.get("fields"), dict) else set()
    if not vocab.types:
        sink.warn("schema-types-missing", schema_label, f"{schema_label}: declares no `types`; type checks limited", schema_label)
    vocab.ontology_version = str(schema.get("ontology_version", ""))
    if not SEMVER_RE.match(vocab.ontology_version):
        sink.err("version-format", schema_label, f"{schema_label}: ontology_version {vocab.ontology_version!r} is not X.Y.Z", schema_label)
    if not isinstance(schema.get("schema_version"), int) or isinstance(schema.get("schema_version"), bool):
        sink.err("version-format", schema_label, f"{schema_label}: schema_version must be an integer", schema_label)

    for path in vocabulary_files(root):
        label = _label(path, rel_to)
        data = _load_yaml(sink, path, label)
        if data is None:
            continue
        if not isinstance(data, list):
            sink.err("termfile-not-list", label, f"{label}: expected a top-level list of term records", label)
            continue
        for rec in data:
            if not isinstance(rec, dict):
                sink.err("record-not-mapping", label, f"{label}: non-mapping record {rec!r}", label)
                continue
            tid = rec.get("id")
            subject = str(tid) if tid else repr(rec)
            for name in REQUIRED_FIELDS:
                value = rec.get(name)
                if not value or not str(value).strip():
                    sink.err("field-missing", subject, f"{label}: record {subject} missing required field {name!r}", label)
            if vocab.fields:
                for name in sorted(set(rec) - vocab.fields, key=str):
                    sink.err("field-unknown", subject, f"{label}: record {subject} carries field {name!r}, which schema.yaml's `fields:` does not define", label)
            if not tid:
                continue
            tid = str(tid)
            if tid in vocab.terms:
                sink.err("id-duplicate", tid, f"{label}: duplicate id {tid!r} (also in {vocab.files[tid]})", label)
            if not id_pattern.match(tid):
                sink.err("id-pattern", tid, f"{label}: id {tid!r} does not match the id pattern", label)
            rtype = rec.get("type")
            if vocab.types and rtype not in vocab.types:
                sink.err("type-unknown", tid, f"{label}: id {tid!r} has unknown type {rtype!r}", label)
            if rtype == "QualityAttribute":
                vocab.quality_attributes.add(tid)
            vocab.terms[tid] = rec
            vocab.files[tid] = label

    vocab.decisions = decision_numbers(decisions_dir)
    for tid, rec in vocab.terms.items():
        label = vocab.files[tid]
        for link in rec.get("relates_to") or []:
            if not isinstance(link, dict):
                sink.err("relates-to-malformed", tid, f"{label}: {tid}: relates_to entry is not a mapping: {link!r}", label)
                continue
            verb, target = link.get("rel"), link.get("target")
            if not isinstance(verb, str) or verb not in vocab.verbs:
                sink.err("verb-unknown", tid, f"{label}: {tid}: unknown relationship verb {verb!r}", label)
            if not isinstance(target, str) or target not in vocab.terms:
                sink.err("target-unresolved", tid, f"{label}: {tid}: relates_to target {target!r} is not a defined id", label)
            if verb == "derived_from" and rec.get("type") == "Function":
                sink.err("function-derived-from", tid, f"{label}: {tid}: a Function may not use `derived_from` (ADR 0011)", label)
        source = rec.get("source")
        if isinstance(source, str) and source.strip():
            for item in (s.strip() for s in source.split(";") if s.strip()):
                if URL_RE.search(item):
                    continue  # an external citation carrying a URL, whatever it mentions (ADR 0005)
                if "ADR" in item.upper() and not ADR_ITEM_RE.match(item):
                    sink.err("source-grammar", tid, f"{label}: {tid}: source item {item!r} is not `ADR NNNN` with an optional amended/extended tail (ADR 0005)", label)
                    continue
                for number in ADR_NUM_RE.findall(item):
                    if number not in vocab.decisions:
                        sink.err("source-adr-unresolved", tid, f"{label}: {tid}: source cites ADR {number}, which has no record under {_label(decisions_dir, rel_to)}/", label)
    return sink.findings, vocab


def errors(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f["severity"] == "error"]


def summary_line(findings: list[Finding], vocab: Vocabulary) -> str:
    return (
        f"itpra-onto lint: {len(vocab.terms)} terms, {len(vocab.quality_attributes)} quality attributes, "
        f"{len(vocab.decisions)} decision records, ontology_version {vocab.ontology_version}"
    )


def main(argv: list[str] | None = None, *, default_root: Path | None = None) -> int:
    """``itpra-onto lint``. ``--root`` defaults to ``default_root``, else the configured
    ``[paths] ontology_dir``. Exit 1 on any error; warnings never fail."""
    ap = argparse.ArgumentParser(prog="itpra-onto lint", description="Lint the vocabulary with the ontology's own rules.")
    ap.add_argument("--root", help="the vocabulary's directory (schema.yaml beside its term files)")
    ap.add_argument("--decisions", help="the decision records' directory (default: <root>/decisions)")
    ap.add_argument("--json", action="store_true", help="emit the findings as JSON and nothing else on stdout")
    args = ap.parse_args(argv)
    if args.root:
        root = Path(args.root)
    elif default_root is not None:
        root = Path(default_root)
    else:
        from itpra_onto.config import load_config  # stdlib only; the shipped configuration names the directory

        config = load_config()
        root = (config.config_path.parent / config.paths.ontology_dir).resolve()
    findings, vocab = lint_vocabulary(root, decisions_dir=Path(args.decisions) if args.decisions else None)
    n_err = len(errors(findings))
    if args.json:
        print(json.dumps(findings, ensure_ascii=False))
        return 1 if n_err else 0
    print(summary_line(findings, vocab))
    for f in findings:
        print(f"  {'ERROR' if f['severity'] == 'error' else 'WARN '} {f['rule']}: {f['message']}")
    print(f"{'FAILED' if n_err else 'OK'}: {n_err} error(s), {len(findings) - n_err} warning(s)")
    return 1 if n_err else 0


if __name__ == "__main__":  # pragma: no cover - `python -m itpra_onto.lint`
    sys.exit(main())

#!/usr/bin/env python3
"""check-version-bump.py — a change to the vocabulary must bump `ontology_version` in the same change (ADR 0003).

Compares the working tree (HEAD) with a base commit: if any of schema.yaml, entities.yaml, relationships.yaml or
terms/** differs, `ontology_version` must differ too and must be a higher Semantic Version. A version change with no
vocabulary change is allowed (a release bump) and reported. With no usable base (first commit, or an all-zero sha
from a branch-creation push) the check passes after validating the version format.

A version that is on the base but not released yet is still open: while the tag `v<version>` does not exist, a
further vocabulary change joins that pending release and needs no second bump. The tags must be in the clone for
this (CI fetches them); a clone with no `v*` tag at all cannot tell, and the check then asks for the bump.

Usage:  python tools/check-version-bump.py [--base <git ref or sha>]   (default: BASE_SHA env, else HEAD~1)
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

VOCAB = ("schema.yaml", "entities.yaml", "relationships.yaml", "terms/")
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
VERSION_LINE_RE = re.compile(r"^ontology_version:\s*([0-9.]+)\s*$", re.M)


def parse_version(text: str) -> tuple[int, int, int] | None:
    m = VERSION_LINE_RE.search(text)
    if not m or not SEMVER_RE.match(m.group(1)):
        return None
    return tuple(int(p) for p in m.group(1).split("."))  # type: ignore[return-value]


def vocabulary_changed(paths: list[str]) -> bool:
    return any(p == v or (v.endswith("/") and p.startswith(v)) for p in paths for v in VOCAB)


def verdict(base_schema: str | None, head_schema: str, changed: list[str], base_released: bool = True) -> tuple[bool, str]:
    head = parse_version(head_schema)
    if head is None:
        return False, "schema.yaml: ontology_version missing or not X.Y.Z"
    if base_schema is None:
        return True, f"no base to compare with; ontology_version {'.'.join(map(str, head))} is well-formed"
    base = parse_version(base_schema)
    if not vocabulary_changed(changed):
        note = " (version changed without a vocabulary change: a release bump)" if base != head else ""
        return True, f"no vocabulary change; ontology_version {'.'.join(map(str, head))}{note}"
    if base is None:
        return True, f"vocabulary changed; base version unreadable; head {'.'.join(map(str, head))}"
    if head == base and not base_released:
        return True, f"vocabulary changed; ontology_version {'.'.join(map(str, head))} is not released yet (no tag), so the change joins it"
    if head == base:
        return False, f"vocabulary changed but ontology_version is still {'.'.join(map(str, head))} — bump it in this change (ADR 0003)"
    if head < base:
        return False, f"ontology_version went backwards: {'.'.join(map(str, base))} → {'.'.join(map(str, head))}"
    return True, f"vocabulary changed; ontology_version {'.'.join(map(str, base))} → {'.'.join(map(str, head))}"


def git(*args: str, root: Path) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def released(schema_text: str | None, root: Path) -> bool:
    """True when the tag v<ontology_version> of this schema text exists, or when the clone holds no v* tag at all
    (then nothing can be told, and the stricter answer is given)."""
    version = parse_version(schema_text or "")
    tags = git("tag", "--list", "v*", root=root)
    if version is None or not tags or not tags.strip():
        return True
    return f"v{'.'.join(map(str, version))}" in tags.split()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("BASE_SHA") or "HEAD~1")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args(argv)
    root = Path(args.root)
    head_schema = (root / "schema.yaml").read_text(encoding="utf-8")
    base = args.base
    base_schema = None
    changed: list[str] = []
    if base and not set(base) <= {"0"}:
        base_schema = git("show", f"{base}:schema.yaml", root=root)
        diff = git("diff", "--name-only", base, "HEAD", root=root)
        if diff is not None:
            changed = [line.strip() for line in diff.splitlines() if line.strip()]
            status = git("status", "--porcelain", root=root) or ""
            changed += [line[3:].strip() for line in status.splitlines() if line.strip()]
    ok, message = verdict(base_schema, head_schema, changed, base_released=released(base_schema, root))
    print(f"check-version-bump: {'OK' if ok else 'FAILED'} — {message}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

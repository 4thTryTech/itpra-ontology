#!/usr/bin/env python3
"""publication-scan.py — nothing in the published tree may refer to a private repository's structure.

Scans every .yaml and .md file (code and licences excluded) for references to another repository's folders,
documents, specifications, registries or working state, and for a `source:` item that cites the originating
repository by URL. URLs are exempt from the path patterns. Exit 1 on any hit.
Usage:  python tools/publication-scan.py [--root DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PRIVATE_RE = re.compile(
    r"docs/research/|92-cross-domain-research/|91-architecture-scenarios/|90-t1-architecture-framework/|AGENT-STATE"
    r"|\.claude/|[A-Za-z]:\\\\|\b[A-Za-z]+/docs/|\bdocs/\d\d-|05-methodology/|\b70-adrs\b|sub-project|Full specs"
    r"|monorepo|framework repositor"
)
SOURCE_LINE = re.compile(r"^\s*source:")
FRAMEWORK_URL_RE = re.compile(r"https?://\S*itpra-framework", re.IGNORECASE)
ANY_URL_RE = re.compile(r"https?://\S+")
SKIP_DIRS = {".git", "tools", "tests", ".github"}


def scan(root: Path) -> list[str]:
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in {".yaml", ".md"} or set(path.relative_to(root).parts[:-1]) & SKIP_DIRS:
            continue
        rel = path.relative_to(root).as_posix()
        for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            if PRIVATE_RE.search(ANY_URL_RE.sub("", line)):
                hits.append(f"{rel}:{n}: private reference")
            if path.suffix == ".yaml" and SOURCE_LINE.match(line) and FRAMEWORK_URL_RE.search(line):
                hits.append(f"{rel}:{n}: source cites the originating repository")
    return hits


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args(argv)
    hits = scan(Path(args.root))
    for h in hits:
        print(f"ERROR {h}")
    print(f"publication-scan: {'FAILED' if hits else 'OK'} — {len(hits)} hit(s)")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())

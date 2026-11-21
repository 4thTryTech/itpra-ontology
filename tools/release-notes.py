#!/usr/bin/env python3
"""Print the CHANGELOG.md section for one version — the body of the GitHub Release.

Usage: python tools/release-notes.py 4.0.0 [--changelog CHANGELOG.md]
Exits 1 when the version has no section, so a release cannot be cut without its changelog entry.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


def section(text: str, version: str) -> str | None:
    """The lines under `## <version> — <date>` up to the next `## ` heading, stripped; None when absent."""
    lines = text.splitlines()
    head = re.compile(rf"^## {re.escape(version)}(?:\s|$)")
    start = next((i for i, line in enumerate(lines) if head.match(line)), None)
    if start is None:
        return None
    body: list[str] = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        body.append(line)
    return "\n".join(body).strip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    ap.add_argument("--changelog", default=str(Path(__file__).resolve().parents[1] / "CHANGELOG.md"))
    args = ap.parse_args(argv)
    body = section(Path(args.changelog).read_text(encoding="utf-8"), args.version)
    if body is None:
        print(f"CHANGELOG.md has no section '## {args.version}' — add the entry before tagging (ADR 0003)", file=sys.stderr)
        return 1
    sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""check-links.py — every relative link in a Markdown file must resolve to a file in this repository.

Web links (http, https, mailto) are not fetched. Anchors are stripped. Exit 1 on any broken link.
Usage:  python tools/check-links.py [--root DIR]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SKIP = ("http://", "https://", "mailto:", "#")


def broken_links(root: Path) -> list[str]:
    problems: list[str] = []
    for md in sorted(root.rglob("*.md")):
        if ".git" in md.parts:
            continue
        for n, line in enumerate(md.read_text(encoding="utf-8").split("\n"), 1):
            for target in LINK_RE.findall(line):
                if target.startswith(SKIP):
                    continue
                path = target.split("#", 1)[0]
                if not path:
                    continue
                if not (md.parent / path).exists():
                    problems.append(f"{md.relative_to(root).as_posix()}:{n}: broken link {target}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    args = ap.parse_args(argv)
    problems = broken_links(Path(args.root))
    for p in problems:
        print(f"ERROR {p}")
    print(f"check-links: {'FAILED' if problems else 'OK'} — {len(problems)} broken link(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

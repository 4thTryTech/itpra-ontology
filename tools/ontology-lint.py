#!/usr/bin/env python3
"""ontology-lint.py — lint the vocabulary with the ontology's own rules.

The rules live once, in the pipeline package: `tools/itpra-onto/src/itpra_onto/lint.py` (ADR 0042 D1) — file
shape, required and unknown fields, unique ids and the id pattern, known types and verbs, resolving targets,
`derived_from` kept off Functions (ADR 0011), the `source:` grammar and resolving decision citations (ADR 0005),
the two version numbers (ADR 0003), the retirement fields (ADR 0048). This script imports that module (standard library plus PyYAML, no RDF
dependencies) and lints the repository root; `itpra-onto lint` is the same run from the package's environment.

Usage:  python tools/ontology-lint.py [--root DIR] [--decisions DIR] [--json]
Exit 1 on any error; warnings never fail.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "itpra-onto" / "src"))

from itpra_onto.lint import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(default_root=ROOT))

"""Read the per-verb profile off the authored data (the evidence behind the ``itpra_verb`` annotations).

For every relationship verb: the (subject type, object type) pairs with edge counts, the per-record
edge-count range per subject type, and the ``entities.yaml`` meta-edges. Instance edges come from
``relates_to`` on every non-EntityType record. ``relates_to`` on EntityType records are meta-edges (schema
statements), reported separately and never counted as instances.

The ``itpra_verb`` annotations in ``schema/itpra.linkml.yaml`` were written from this profile;
``tests/test_schema.py`` checks they stay consistent with it. Print it with
``uv run python -m itpra_onto.profile``.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from itpra_onto.authoring import default_term_files

META_SUBJECT_TYPE = "EntityType"


@dataclass
class VerbProfile:
    pairs: Counter = field(default_factory=Counter)  # (subject, object) -> edges
    per_record: dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))  # subject -> {n: records}
    meta_edges: set[str] = field(default_factory=set)
    unresolved: Counter = field(default_factory=Counter)


def _load(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_records() -> list[dict]:
    return [r for p in default_term_files() for r in (_load(p) or [])]


def compute_profile(terms: list[dict] | None = None) -> dict[str, VerbProfile]:
    if terms is None:
        terms = load_records()
    type_of = {r["id"]: r["type"] for r in terms}
    records_of_type = Counter(r["type"] for r in terms)
    profile: dict[str, VerbProfile] = defaultdict(VerbProfile)

    def record_edges(subject: dict, edges: list[tuple[str, str]]) -> None:
        per_verb = Counter()
        for verb, target in edges:
            obj = type_of.get(target)
            if obj is None:
                profile[verb].unresolved[target] += 1
                obj = "UNRESOLVED"
            profile[verb].pairs[(subject["type"], obj)] += 1
            per_verb[verb] += 1
        for verb, n in per_verb.items():
            profile[verb].per_record[subject["type"]][n] += 1

    for rec in terms:
        edges = [(e["rel"], e["target"]) for e in rec.get("relates_to") or []]
        if rec["type"] == META_SUBJECT_TYPE:
            for verb, target in edges:
                profile[verb].meta_edges.add(f"{rec['id']} -> {target}")
            continue
        record_edges(rec, edges)

    # Records of a subject type that carry zero edges of a verb count as n = 0.
    for prof in profile.values():
        for subject, counts in prof.per_record.items():
            counts[0] = records_of_type[subject] - sum(c for n, c in counts.items() if n)
            if not counts[0]:
                del counts[0]
    return dict(profile)


def as_jsonable(profile: dict[str, VerbProfile]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for verb in sorted(profile):
        prof = profile[verb]
        out[verb] = {
            "pairs": [{"subject": s, "object": o, "count": c} for (s, o), c in sorted(prof.pairs.items())],
            "observed": [
                {"subject": s, "records": sum(c.values()), "min": min(c), "max": max(c)}
                for s, c in sorted(prof.per_record.items())
            ],
            "meta_edges": sorted(prof.meta_edges),
            "unresolved": dict(prof.unresolved),
        }
    return out


if __name__ == "__main__":
    print(json.dumps(as_jsonable(compute_profile()), indent=2))

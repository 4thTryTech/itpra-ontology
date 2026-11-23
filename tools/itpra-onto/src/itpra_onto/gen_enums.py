"""Generate the LinkML enums from the vocabulary's ``schema.yaml``.

``schema.yaml`` stays the single hand-authored home of the two controlled value lists:

* ``types:``          -> ``EntityTypeEnum``        (the ``type`` field of every term record)
* ``relationships:``  -> ``RelationshipVerbEnum``  (the ``rel`` of every ``relates_to`` entry)

This module reads those two lists and writes ``schema/generated/itpra-enums.linkml.yaml``, a small
LinkML schema module that the hand-authored ``schema/itpra.linkml.yaml`` imports. Output is
deterministic: keys sorted, LF newlines, UTF-8, no timestamps, no version stamp (so a content-only
ontology release does not make the generated file stale — only a change to either list does). The
module's ``id:`` is computed from ``itpra-onto.toml`` (:func:`itpra_onto.config.load_config`; ADR 0004)
and it declares no ``itpra-*`` prefix of its own — the generated fragment imports
``itpra-prefixes.linkml`` (:mod:`itpra_onto.gen_prefixes`) instead of repeating it.

``--check`` regenerates in memory and exits non-zero when the committed file differs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from itpra_onto.config import Config, load_config

PACKAGE_DIR = Path(__file__).resolve().parent  # src/itpra_onto: the package's own code and data
SCHEMA_DIR = PACKAGE_DIR / "schema"
GENERATED_ENUMS_PATH = SCHEMA_DIR / "generated" / "itpra-enums.linkml.yaml"

ENTITY_TYPE_ENUM = "EntityTypeEnum"
RELATIONSHIP_VERB_ENUM = "RelationshipVerbEnum"

_HEADER = """\
# GENERATED FILE - DO NOT EDIT BY HAND.
# Source:     schema.yaml of the vocabulary (its `types:` and `relationships:` lists stay authored there;
#             these LinkML enums are derived from them — ADR 0041 D5) and itpra-onto.toml [iri] (this
#             module's `id:`; ADR 0004).
# Generator:  src/itpra_onto/gen_enums.py
# Regenerate: itpra-onto gen-enums
# Check:      itpra-onto gen-enums --check
"""


def ontology_dir() -> Path:
    config = load_config()
    return (config.config_path.parent / config.paths.ontology_dir).resolve()


def read_source_lists(schema_yaml: Path | None = None) -> tuple[list[str], list[str]]:
    """Return ``(types, relationships)`` exactly as listed in the vocabulary's ``schema.yaml``."""
    path = schema_yaml if schema_yaml is not None else ontology_dir() / "schema.yaml"
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    types = data.get("types")
    verbs = data.get("relationships")
    if not isinstance(types, list) or not all(isinstance(t, str) for t in types):
        raise ValueError(f"{path}: `types:` is not a list of strings")
    if not isinstance(verbs, list) or not all(isinstance(v, str) for v in verbs):
        raise ValueError(f"{path}: `relationships:` is not a list of strings")
    for name, values in (("types", types), ("relationships", verbs)):
        if len(set(values)) != len(values):
            raise ValueError(f"{path}: `{name}:` contains duplicates")
    return list(types), list(verbs)


def render(types: list[str], verbs: list[str], config: Config | None = None) -> str:
    """Render the generated LinkML module as text (deterministic).

    ``id`` and the ``itpra-o:`` prefix are configuration items (ADR 0004): this module
    carries no IRI literal of its own. The prefix itself is not redeclared here — it is inherited
    from importing ``itpra-prefixes.linkml`` (``gen_prefixes.py``), the single generated source of
    every ``<base>``-derived prefix.
    """
    config = config if config is not None else load_config()
    module = {
        "id": config.iri.linkml_module_id("itpra-enums"),
        "name": "itpra-enums",
        "description": (
            "Enums generated from the vocabulary's schema.yaml (types, relationships). "
            "Imported by itpra.linkml.yaml. Do not edit by hand."
        ),
        "default_prefix": "itpra-o",
        "prefixes": {
            "linkml": "https://w3id.org/linkml/",
        },
        "imports": ["linkml:types", "itpra-prefixes.linkml"],
        "enums": {
            ENTITY_TYPE_ENUM: {
                "description": "Allowed values of a term record's `type` field (schema.yaml `types:`).",
                "permissible_values": {t: {} for t in types},
            },
            RELATIONSHIP_VERB_ENUM: {
                "description": (
                    "Allowed values of `relates_to[].rel` (schema.yaml `relationships:`)."
                ),
                "permissible_values": {v: {} for v in verbs},
            },
        },
    }
    body = yaml.safe_dump(module, sort_keys=True, allow_unicode=True, default_flow_style=False, width=100)
    return _HEADER + body


def generate(schema_yaml: Path | None = None, config: Config | None = None) -> str:
    types, verbs = read_source_lists(schema_yaml)
    return render(types, verbs, config)


def write(text: str, path: Path = GENERATED_ENUMS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def check(path: Path = GENERATED_ENUMS_PATH, config: Config | None = None) -> bool:
    """True when the file at ``path`` equals a fresh generation byte for byte."""
    if not path.exists():
        return False
    return path.read_bytes() == generate(config=config).encode("utf-8")


def main(check_only: bool = False) -> int:
    if check_only:
        if check():
            print(f"gen-enums: {GENERATED_ENUMS_PATH.relative_to(PACKAGE_DIR).as_posix()} is up to date")
            return 0
        print(
            f"gen-enums: {GENERATED_ENUMS_PATH.relative_to(PACKAGE_DIR).as_posix()} is STALE or missing - "
            "run `itpra-onto gen-enums`",
            file=sys.stderr,
        )
        return 1
    write(generate())
    print(f"gen-enums: wrote {GENERATED_ENUMS_PATH.relative_to(PACKAGE_DIR).as_posix()}")
    return 0

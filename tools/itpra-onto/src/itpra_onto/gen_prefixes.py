"""Generate the ``itpra:`` / ``itpra-o:`` / ``itpra-g:`` prefix fragment from ``itpra-onto.toml``
(ADR 0004).

The base IRI is a configuration item and is never hard-coded (ADR 0004): ``itpra-onto.toml`` is the *only*
file that carries the literal. This module reads ``[iri] base`` (and ``id_path`` / ``onto_path`` /
``graph_path``) and writes ``schema/generated/itpra-prefixes.linkml.yaml``, a small LinkML schema fragment
carrying nothing but ``id``, ``prefixes`` (``itpra``, ``itpra-o``, ``itpra-g``) and ``default_prefix``.
``schema/itpra.linkml.yaml`` and ``schema/generated/itpra-enums.linkml.yaml`` both import it instead of
declaring those three prefixes themselves.

``schema/itpra.linkml.yaml`` has one further IRI LinkML requires directly on the importing file and
will not accept purely by inheritance from an import: the schema's own ``id:``. Rather than also
generating a second physical copy of the (large, hand-authored, otherwise unchanged) schema file, that
one field is injected in memory at load time by :mod:`itpra_onto.schema_loading`, which every user
(``itpra-onto validate --authoring``, the test suite) goes through instead of constructing a
``SchemaView``/``Validator`` directly from ``schema/itpra.linkml.yaml``'s path. See that module's
docstring and ``schema/README.md`` for why: empirically, LinkML merges
*prefixes* from an imported fragment into the importing schema's namespace map, but a schema's ``id``
must be present on the object being loaded, not merely importable — confirmed against linkml-runtime
1.11.1 by constructing a ``SchemaDefinition`` without ``id`` (``ValueError: id must be supplied``).
Injecting it in memory keeps ``schema/itpra.linkml.yaml`` fully hand-authored and human-readable, with
no generated sibling copy of the whole file to keep in sync.

Output is deterministic: keys sorted, LF newlines, UTF-8, no timestamps.

``--check`` regenerates in memory and exits non-zero when the committed file differs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from itpra_onto.config import Config, load_config

PACKAGE_DIR = Path(__file__).resolve().parent  # src/itpra_onto: the package's own code and data
SCHEMA_DIR = PACKAGE_DIR / "schema"
GENERATED_PREFIXES_PATH = SCHEMA_DIR / "generated" / "itpra-prefixes.linkml.yaml"

MODULE_NAME = "itpra-prefixes"

_HEADER = """\
# GENERATED FILE - DO NOT EDIT BY HAND.
# Source:     itpra-onto.toml [iri] (base, id_path, onto_path, graph_path) — the base IRI is a
#             configuration item, never hard-coded (ADR 0004).
# Generator:  src/itpra_onto/gen_prefixes.py
# Regenerate: itpra-onto gen-prefixes
# Check:      itpra-onto gen-prefixes --check
"""


def render(config: Config | None = None) -> str:
    """Render the generated LinkML prefix fragment as text (deterministic)."""
    config = config if config is not None else load_config()
    module = {
        "id": config.iri.linkml_module_id(MODULE_NAME),
        "name": MODULE_NAME,
        "description": (
            "itpra: / itpra-o: / itpra-g: prefix declarations generated from "
            "itpra-onto.toml [iri]. Imported by itpra.linkml.yaml (in memory, via "
            "itpra_onto.schema_loading) and by itpra-enums.linkml.yaml. Do not edit by hand."
        ),
        "default_prefix": "itpra-o",
        "prefixes": {
            "itpra": config.iri.id_ns,
            "itpra-o": config.iri.onto_ns,
            "itpra-g": config.iri.graph_ns,
        },
    }
    body = yaml.safe_dump(module, sort_keys=True, allow_unicode=True, default_flow_style=False, width=100)
    return _HEADER + body


def write(text: str, path: Path = GENERATED_PREFIXES_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def check(path: Path = GENERATED_PREFIXES_PATH, config: Config | None = None) -> bool:
    """True when the file at ``path`` equals a fresh generation byte for byte."""
    if not path.exists():
        return False
    return path.read_bytes() == render(config).encode("utf-8")


def main(check_only: bool = False) -> int:
    if check_only:
        if check():
            print(f"gen-prefixes: {GENERATED_PREFIXES_PATH.relative_to(PACKAGE_DIR).as_posix()} is up to date")
            return 0
        print(
            f"gen-prefixes: {GENERATED_PREFIXES_PATH.relative_to(PACKAGE_DIR).as_posix()} is STALE or missing - "
            "run `itpra-onto gen-prefixes`",
            file=sys.stderr,
        )
        return 1
    write(render())
    print(f"gen-prefixes: wrote {GENERATED_PREFIXES_PATH.relative_to(PACKAGE_DIR).as_posix()}")
    return 0

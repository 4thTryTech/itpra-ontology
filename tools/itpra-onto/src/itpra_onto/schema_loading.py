"""Load ``schema/itpra.linkml.yaml`` with its ``id:`` injected from ``itpra-onto.toml`` (ADR 0004).

``schema/itpra.linkml.yaml`` is hand-authored and stays that way: it declares no ``itpra:`` /
``itpra-o:`` / ``itpra-g:`` prefix of its own (those come from importing the generated
``generated/itpra-prefixes.linkml`` fragment — LinkML merges an import's prefixes into the importing
schema's namespace map without the importer redeclaring them), but LinkML's ``SchemaDefinition``
requires ``id`` to be present on the object actually being loaded; it is not filled in by merging an
import. On disk, the field holds :data:`SCHEMA_ID_SENTINEL` — never an IRI — so that
``schema/itpra.linkml.yaml`` carries no IRI literal outside the generated fragments either. Every
user of the schema (``itpra-onto validate --authoring``, the test suite) loads it through this
module rather than constructing a ``SchemaView`` / ``Validator`` straight from the file path, so the
substitution happens exactly once.

This is a runtime substitution, not a second generated file on disk: :func:`load_schema_definition`
parses the YAML, replaces the sentinel ``id`` with the value computed from config
(:meth:`itpra_onto.config.IriConfig.linkml_module_id`), and builds the ``SchemaDefinition`` in memory
with ``source_file`` set to the real path so relative ``imports:`` (``generated/itpra-enums.linkml``,
``generated/itpra-prefixes.linkml``) still resolve exactly as authored. Confirmed empirically against
linkml-runtime 1.11.1: a ``SchemaView``/``Validator`` built this way resolves imported prefixes and
validates instances identically to one loaded straight from a file that had the real ``id:`` baked in.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from linkml.validator import Validator
from linkml.validator.plugins.validation_plugin import ValidationPlugin
from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.utils.schemaview import SchemaView

from itpra_onto.config import Config, load_config

PACKAGE_DIR = Path(__file__).resolve().parent  # src/itpra_onto: the package's own code and data
SCHEMA_PATH = PACKAGE_DIR / "schema" / "itpra.linkml.yaml"

# Marks the `id:` field in schema/itpra.linkml.yaml. Never IRI-shaped, so a scan for the base IRI
# literal never matches it, and a schema loaded any other way than
# through this module fails loudly instead of silently carrying a bogus id.
SCHEMA_ID_SENTINEL = "__GENERATED_SCHEMA_ID__"

MAIN_MODULE_NAME = "itpra"


def _schema_dict(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if data.get("id") != SCHEMA_ID_SENTINEL:
        raise ValueError(
            f"{path}: expected id: {SCHEMA_ID_SENTINEL} (substituted by itpra_onto.schema_loading at "
            f"load time; see schema/README.md) — found {data.get('id')!r}"
        )
    return data


def load_schema_definition(path: Path = SCHEMA_PATH, config: Config | None = None) -> SchemaDefinition:
    """Parse ``path``, substitute the config-derived ``id``, and return a ``SchemaDefinition``.

    ``source_file`` is set to ``path`` so LinkML resolves this schema's relative ``imports:`` against
    ``path``'s own directory, exactly as if ``id:`` had been a literal in the file.
    """
    config = config if config is not None else load_config()
    data = dict(_schema_dict(path))
    data["id"] = config.iri.linkml_module_id(MAIN_MODULE_NAME)
    return SchemaDefinition(**data, source_file=str(path))


def load_schema_view(path: Path = SCHEMA_PATH, config: Config | None = None) -> SchemaView:
    return SchemaView(load_schema_definition(path, config))


def load_validator(
    path: Path = SCHEMA_PATH,
    validation_plugins: list[ValidationPlugin] | None = None,
    config: Config | None = None,
) -> Validator:
    return Validator(load_schema_definition(path, config), validation_plugins=validation_plugins)

"""Validate the authored YAML against the LinkML authoring schema (``itpra-onto validate --authoring``).

Runs in-process through ``linkml.validator.Validator`` with the JSON Schema plugin in closed mode
(unknown keys are errors):

* Term files (``terms/*.yaml``, ``entities.yaml``, ``relationships.yaml`` under ``[paths] ontology_dir``) are BARE
  top-level lists. Each record is validated against the subclass whose ``type`` slot_usage pins
  (``pattern: "^<type>$"``) to the record's ``type`` (read from the schema, not hard-coded); a record whose
  ``type`` matches no subclass is validated against ``Term`` and fails on the generated enum.

Files are read as UTF-8 by this module (linkml's own YamlLoader opens files in the platform default
encoding, which is not UTF-8 on Windows).

The schema itself is loaded through :mod:`itpra_onto.schema_loading` (ADR 0004), not by
pointing a ``SchemaView``/``Validator`` straight at ``schema/itpra.linkml.yaml``'s path: the base IRI
is a configuration item, and that module is where the schema's ``id:`` sentinel is substituted for the
value ``itpra-onto.toml`` [iri] computes.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml
from linkml.validator import Validator
from linkml.validator.plugins import JsonschemaValidationPlugin
from linkml_runtime.utils.schemaview import SchemaView

from itpra_onto import schema_loading
from itpra_onto.config import load_config

SCHEMA_PATH = schema_loading.SCHEMA_PATH

TERM_BASE_CLASS = "Term"

# A subclass pins its discriminator with slot_usage `pattern: "^<Value>$"`. (Not `equals_string`:
# gen-shacl 1.11.1 rejects equals_string on an enum-ranged slot.)
_PIN = re.compile(r"^\^([A-Za-z][A-Za-z0-9_]*)\$$")


@dataclass
class FileResult:
    path: Path
    kind: str  # "terms"
    records: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def discriminator_map(schema_view: SchemaView, base_class: str, slot_name: str) -> dict[str, str]:
    """Value of the YAML discriminator key -> subclass of ``base_class`` whose slot_usage pins it.

    Shared by the authoring validator (record dispatch) and the RDF emitter (the type -> class_uri
    table): both read the pins off the schema rather than transforming the value's spelling.
    """
    mapping: dict[str, str] = {}
    for cls_name in schema_view.class_descendants(base_class, reflexive=False):
        induced = schema_view.induced_slot(slot_name, cls_name)
        match = _PIN.match(induced.pattern or "")
        if match:
            value = match.group(1)
            if value in mapping:
                raise ValueError(f"two classes pin {slot_name} == {value!r}")
            mapping[value] = cls_name
    return mapping


def default_term_files() -> list[Path]:
    config = load_config()
    onto = (config.config_path.parent / config.paths.ontology_dir).resolve()
    return sorted((onto / "terms").glob("*.yaml")) + [onto / "entities.yaml", onto / "relationships.yaml"]


class AuthoringValidator:
    def __init__(self, schema_path: Path = SCHEMA_PATH) -> None:
        self.schema_path = schema_path
        schema_definition = schema_loading.load_schema_definition(schema_path)
        self.schema_view = SchemaView(schema_definition)
        self.validator = Validator(
            schema_definition,
            validation_plugins=[JsonschemaValidationPlugin(closed=True)],
        )

    def _discriminator_map(self, base_class: str, slot_name: str) -> dict[str, str]:
        """Value of the YAML ``type`` key -> subclass of ``base_class`` whose slot_usage pins it."""
        return discriminator_map(self.schema_view, base_class, slot_name)

    @cached_property
    def type_to_class(self) -> dict[str, str]:
        """Term ``type`` value -> subclass of Term (from each subclass's ``type`` slot_usage)."""
        return self._discriminator_map(TERM_BASE_CLASS, "type")

    def target_class_for(self, record: Any) -> str:
        if isinstance(record, dict):
            cls = self.type_to_class.get(record.get("type"))  # type: ignore[arg-type]
            if cls:
                return cls
        return TERM_BASE_CLASS

    def _messages(self, instance: Any, target_class: str, prefix: str) -> list[str]:
        report = self.validator.validate(instance, target_class)
        return [f"{prefix}{r.message}" for r in report.results]

    def validate_term_records(self, records: Any, label: str = "") -> FileResult:
        result = FileResult(path=Path(label), kind="terms")
        if not isinstance(records, list):
            result.errors.append(f"top level is {type(records).__name__}, expected a bare list of term records")
            return result
        result.records = len(records)
        for index, record in enumerate(records):
            rid = record.get("id", "?") if isinstance(record, dict) else "?"
            target = self.target_class_for(record)
            result.errors.extend(self._messages(record, target, f"[{index}] {rid} ({target}): "))
        return result

    def validate_term_file(self, path: Path) -> FileResult:
        result = self.validate_term_records(_load_yaml(path), str(path))
        result.path = path
        return result


def _display(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


def run(quiet: bool = False) -> int:
    """Validate every term file; print a per-file summary; 0 only if all pass."""
    started = time.perf_counter()
    repo_root = load_config().repo_root
    checker = AuthoringValidator()
    results: list[FileResult] = []
    for path in default_term_files():
        results.append(checker.validate_term_file(path))

    for res in results:
        status = "ok  " if res.ok else "FAIL"
        if not quiet or not res.ok:
            print(f"{status} {res.kind:8} {res.records:4} records  {_display(res.path, repo_root)}")
        for message in res.errors:
            print(f"       {message}")

    elapsed = time.perf_counter() - started
    failed = sum(1 for r in results if not r.ok)
    records = sum(r.records for r in results)
    print(
        f"validate --authoring: {len(results) - failed}/{len(results)} files passed ({records} records), "
        f"{failed} failed, {elapsed:.1f}s"
    )
    return 0 if failed == 0 and results else 1

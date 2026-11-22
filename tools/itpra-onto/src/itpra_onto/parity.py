"""``itpra-onto parity`` (ADR 0042 D5; ``shapes/REGISTER.md`` is the register the comparison is read from).

Compares the consumer's linter's ``--json`` findings (``[overlay] linter_script``) against pySHACL's
(:mod:`itpra_onto.shacl`) over the SAME inputs, as ``(rule, subject, severity)`` triples — the shape both
``--json`` outputs share (the linter's own contract; ``itpra_onto.cli._cmd_validate``'s ``--json`` payload).

**Guards.** The register parser fails loudly (exact header row, row count equal to the
Counts section's stated figure, and a cross-check that every comparable id is an ``itpra-o:ruleId`` in the
loaded shapes and every shape ``ruleId`` is a Table A or Table B id); linter findings of
``target-unresolved``/``verb-unknown`` on an EntityType record (meta-edges, never projected) are excluded
from the real-tree comparison and reported; an ``EmitError`` becomes an ``emit-error`` finding that fails the
comparison; ``req-link-malformed`` joins the emit-time mapping; and ``--fixtures`` fails on ``linter-only``
for a comparable/emit-mapped rule (:func:`fixture_failures`).

**Comparable set.** Only rows of ``shapes/REGISTER.md`` Table A (the "A/C" sub-table; the "B" sub-table's
ids are a consumer's own manifest rules and stay outside the graph — ADR 0042 D7) whose ``mechanism``
column reads ``core`` or ``sparql`` exist on *both* sides under the same rule id, and are therefore directly
comparable by rule-id equality. This module parses that table at run time (:func:`parse_table_a`) rather
than hard-coding the id list, so the register stays the single source; a parse failure raises
:class:`ParityError` rather than silently falling back to a stale hard-coded set. **The erratum applies**:
Table A's own row for ``relates-to-malformed`` still literally reads ``core``, but the register's own
"Erratum" paragraph (below Table B) corrects this to an emit-time ``python`` guard
(``emit.py``'s ``_verb_edges``) — :func:`comparable_rule_ids` excludes it, and it is folded into
:func:`emit_time_mapped_rule_ids` instead. :func:`parse_table_a` defensively greps for that erratum
paragraph's own header text and raises :class:`ParityError` if it is gone, so a future register edit that
removes or rewords the erratum cannot silently desync this module's hard-coded override.

**Emit-time mapping.** Four Table A ids never reach a graph to shape at all: the emitter raises
``EmitError`` for them before ``emit()`` returns (Table A's ``generated`` mechanism, plus the erratum-
corrected ``relates-to-malformed``): ``type-unknown``, ``verb-unknown``, ``req-type-invalid``,
``relates-to-malformed``. :mod:`itpra_onto.fixtures`'s ``run_fixture`` already turns an ``EmitError`` into a
single synthetic ``rule_id="emit-error"`` finding (its own module docstring) — SHACL/pySHACL never sees a
rule-specific id for these, only the generic marker. Comparing them therefore cannot be rule-id equality:
:func:`_nominal_rule_id` recovers the ORIGINAL id a given ``rule: emit-error`` fixture proves (the fixture's
own filename, stripped of a trailing ``-emit-guard`` suffix — ``shapes/README.md``'s "a positive fixture,
plus a `-emit-guard` sibling" convention), and the ``--fixtures`` comparison (below) matches the linter's
OWN finding for that recovered id against the SHACL/emit side's ``emit-error`` marker, on the SAME subject
— never by rule-id equality, since ``emit-error`` is not a real Table A id on either side.

**Real-tree comparison** (``itpra-onto parity``, no ``--fixtures``): runs the consumer's linter's ``--json``
once per registry (default: every registry the overlay's ``requirements_glob`` matches; ``--sub`` restricts)
as a subprocess of ``[overlay] linter_script`` (never a modified copy — the real tree needs no
materialisation, unlike ``--fixtures`` below), and :func:`itpra_onto.shacl.validate` ONCE over the whole
emitted+ruled dataset (every graph: ``t1``, ``inferred``, every ``req/<X>``, the same default
:func:`itpra_onto.shacl.default_validation_graphs` selection ``itpra-onto validate`` itself uses).
**Avoiding an N-times-duplicated term finding**: a linter that re-reads the ENTIRE shared vocabulary on every
per-registry invocation (each run independent of the others) reports a defect in a shared TERM (not a
per-registry requirement) once per registry, while pySHACL reports it exactly once (it validates the union
graph a single time). This module does not attempt to partition either side by registry (a term finding has
no single owning registry to partition by in the first place — it is shared vocabulary); instead it takes
the **union, deduplicated** of the per-registry linter runs' ``(rule, subject, severity)`` triples before
comparing. Since a requirement-registry finding's ``subject`` is unique to the one registry that produced
it, union+dedup reduces exactly to "count each requirement-registry finding once" for those, and to "the
term defect is one row in the set, not N" for shared-vocabulary findings — both sides end up counting each
real-world defect exactly once, with no per-registry partitioning machinery needed at all.

**``--fixtures`` comparison**: for every fixture under ``fixtures/**/*.yaml`` whose ``expect.count >= 1``
(a ``count: 0`` clean-case/defence-in-depth fixture proves the shape does NOT fire in isolation — there is
nothing for the linter side to independently confirm or deny, so it is out of scope for parity and skipped
here; ``shapes/REGISTER.md``'s "Note on proof style" documents why those fixtures exist), this module
**materialises the fixture's mutation onto disk**, in a fresh temporary directory that mirrors just enough
of the real tree for the REAL, UNMODIFIED linter script to run against the mutated data:

* the ontology directory (``[paths] ontology_dir``) — a full copy (mutated in place, or with one new file
  added, matching the fixture).
* the consumer's registry files — copied only for the ONE registry the fixture's mutated/added record
  belongs to (a term-only fixture copies none at all; the linter is expected to degrade gracefully to a
  missing-registry warning in that case).
* ``[overlay] linter_script`` — **a byte-identical copy of the real script**, not a modified one, at the SAME
  path relative to the repository root. This is load-bearing, not incidental: a linter that locates its
  repository root by walking up from **the script file's own on-disk location** (never from the process's
  cwd or from ``sys.argv``) would, if run uncopied, always resolve back to the ACTUAL repository root and
  read the ACTUAL, unmutated vocabulary — the mutation would silently never be seen. Copying the script
  into the scratch tree at the same relative depth makes that ancestor walk land on the scratch root
  instead.

**The SHACL/emit side of ``--fixtures`` never touches the scratch copy — it stays exactly the existing
in-memory ``itpra_onto.fixtures.run_fixture`` call.** ``emit.guard_input_path`` (ADR 0043 D1) refuses any
input path outside the repository root, and a scratch directory under the system temp directory is normally
NOT under the repository root — so even if this module wanted to point the emitter at the scratch tree, it
could not. The guard's rules (a)–(d) bind only :mod:`itpra_onto.emit`, not the consumer's linter, which is
exactly why the scratch directory is free to live anywhere writable.

Every fixture's verdict is one of ``both`` (linter and SHACL both independently catch the mutation under
the SAME nominal rule id), ``shacl-only`` (only the shape fires — the expected verdict for every Table B
"stricter than the linter" id, and for the one Table A id, ``req-target-unresolved``, whose own fixture
deliberately exercises a record where the SPARQL shape's ``sh:class`` type-check is stricter than the
linter's own soft instance-prefix fallback — see ``fixtures/requirements/req-target-unresolved.yaml``'s own
header), ``linter-only`` (a real gap in the SHACL projection — never expected), or ``neither`` (neither side
caught it at all — always a bug, and a failure in :mod:`tests.test_parity` whenever the fixture's nominal
rule is comparable or emit-time-mapped).
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from itpra_onto import emit, fixtures, rules, shacl
from itpra_onto.config import Config, load_config

PROJECT_DIR = Path(__file__).resolve().parents[2]  # the package root
REPO_ROOT = PROJECT_DIR.parents[1]
REGISTER_MD = PROJECT_DIR / "shapes" / "REGISTER.md"
FIXTURES_DIR = PROJECT_DIR / "fixtures"


def linter_script(config: Config | None = None) -> Path:
    """The consumer's linter, ``[overlay] linter_script`` (ADR 0042 D5)."""
    config = require_overlay(config)
    if not config.overlay.linter_script:  # type: ignore[union-attr]
        raise ParityError("parity needs [overlay] linter_script in itpra-onto.toml: the consumer's linter to compare")
    return (config.config_path.parent / config.overlay.linter_script).resolve()  # type: ignore[union-attr]


def require_overlay(config: Config | None = None) -> Config:
    """``parity`` compares the consumer's linter with the shapes over the consumer's registries: without an
    ``[overlay]`` there is nothing to compare (ADR 0042 D5, ADR 0043 D1)."""
    config = config if config is not None else load_config()
    if config.overlay is None:
        raise ParityError(
            "parity needs an [overlay] in itpra-onto.toml (requirements_glob, linter_script): "
            "the core build has no consumer linter or registries to compare"
        )
    return config


def _default_linter_arg(config: Config) -> str:
    """The registry name passed to the linter for a term-only fixture: any registry serves, since the linter
    reports only its absence from the scratch tree (module docstring)."""
    registries = default_registries(config)
    return registries[0] if registries else ""

# Table A mechanisms that ARE directly comparable by rule-id equality (module docstring).
_COMPARABLE_MECHANISMS = ("core", "sparql")

# The erratum: `relates-to-malformed`'s Table A row literally reads `core`, but shapes/REGISTER.md's own
# "Erratum" paragraph (below Table B) corrects this to an emit-time `python` guard. Applied by
# comparable_rule_ids()/emit_time_mapped_rule_ids(), never by mutating the parsed table itself.
_RELATES_TO_MALFORMED = "relates-to-malformed"
# Table A `python` rows enforced by a plain emit-time `raise EmitError` (not a LinkML-generated constraint):
# mapped to the `emit-error` synthetic finding exactly like the `generated` rows.
_EMIT_TIME_PYTHON_IDS = frozenset({_RELATES_TO_MALFORMED, "req-link-malformed"})
_ERRATUM_MARKER = "**Erratum: `relates-to-malformed`'s mechanism (Table A, pre-A) is corrected here"

_AC_SECTION_RE = re.compile(
    r"### A/C — ontology term integrity.*?\n(.*?)\n### B — derived-package", re.DOTALL
)
_TABLE_B_SECTION_RE = re.compile(r"\n## Table B .*?\n(.*?)\n## Table C ", re.DOTALL)
_TABLE_B_ID_RE = re.compile(r"^\|\s*(B-[0-9]+(?:-[a-z0-9-]+)?)\s*\|", re.MULTILINE)
_ID_CELL_RE = re.compile(r"`([^`]+)`")
# The exact header the A/C sub-table must carry (as written in the register), and the Counts line
# stating its row count — both checked, so a register edit that reshapes the table fails loudly.
TABLE_A_HEADER = "| id | sev | check | family | mechanism | target | notes |"
_TABLE_A_ROWS_COUNT_RE = re.compile(r"\*\*Table A 'A/C' sub-table rows:\*\* (\d+)")

# The consumer's linter checks `relates_to` on EntityType records too (their meta-edges), but the emitter
# never projects a meta-edge (a schema statement, ADR 0008), so no graph ever carries one. Findings of
# these ids on an EntityType subject are python-only by construction and are left out of the comparison
# (and reported).
META_EDGE_RULE_IDS = frozenset({"target-unresolved", "verb-unknown"})
EMIT_ERROR_RULE = "emit-error"


class ParityError(RuntimeError):
    """The register could not be parsed, or a comparison input was malformed."""


# =====================================================================================================
# Register parsing (shapes/REGISTER.md Table A, "A/C" sub-table)


def parse_table_b_ids(register_path: Path = REGISTER_MD) -> frozenset[str]:
    """Every rule id Table B lists in its first column (``B-<n>`` or ``B-<n>-<family-suffix>``)."""
    text = register_path.read_text(encoding="utf-8")
    match = _TABLE_B_SECTION_RE.search(text)
    if not match:
        raise ParityError(f"{register_path}: could not locate the '## Table B' section")
    ids = frozenset(_TABLE_B_ID_RE.findall(match.group(1)))
    if not ids:
        raise ParityError(f"{register_path}: parsed zero Table B rule ids")
    return ids


def shape_rule_ids(shapes_dir: Path = shacl.SHAPES_DIR, config: Config | None = None) -> frozenset[str]:
    """Every ``itpra-o:ruleId`` value in the loaded shapes (hand-written and generated)."""
    config = config if config is not None else load_config()
    shapes = shacl.load_shapes(shapes_dir, config=config)
    return frozenset(shacl._shape_rule_ids(shapes, config).values())


def parse_table_a(
    register_path: Path = REGISTER_MD,
    *,
    shapes_dir: Path | None = shacl.SHAPES_DIR,
    config: Config | None = None,
) -> dict[str, str]:
    """``id -> mechanism`` for every row of Table A's "A/C" sub-table (module docstring), parsed from the
    register at run time so it stays the single source. Raises :class:`ParityError` — never a silent
    fallback to a hard-coded id list — if:

    * the section or the erratum paragraph this module relies on cannot be found;
    * the header row is not exactly :data:`TABLE_A_HEADER`, or a row cannot be parsed;
    * the number of rows differs from the "Table A 'A/C' sub-table rows" figure the register's Counts
      section states;
    * (``shapes_dir`` given — the default) a comparable id is not an ``itpra-o:ruleId`` in the loaded shapes,
      or a ``ruleId`` in the shapes appears in neither Table A nor Table B. ``shapes_dir=None``
      skips this cross-check (the register alone is parsed).
    """
    path = register_path
    text = path.read_text(encoding="utf-8")
    if _ERRATUM_MARKER not in text:
        raise ParityError(
            f"{path}: expected the relates-to-malformed erratum paragraph (starting {_ERRATUM_MARKER!r}) "
            "was not found — the register changed; re-check this module's erratum handling before trusting "
            "its parity output"
        )
    match = _AC_SECTION_RE.search(text)
    if not match:
        raise ParityError(f"{path}: could not locate the '### A/C' Table A sub-table")
    lines = [ln.strip() for ln in match.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 3:
        raise ParityError(f"{path}: Table A 'A/C' sub-table has too few rows ({len(lines)})")
    if lines[0] != TABLE_A_HEADER:
        raise ParityError(f"{path}: Table A 'A/C' header row is {lines[0]!r}, expected exactly {TABLE_A_HEADER!r}")
    if not re.fullmatch(r"\|(?:-+\|)+", lines[1]):
        raise ParityError(f"{path}: Table A 'A/C' second row is not a '|---|' separator: {lines[1]!r}")
    mechanisms: dict[str, str] = {}
    for row in lines[2:]:  # skip the header row and the '|---|...' separator
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 5:
            raise ParityError(f"{path}: malformed Table A row (expected >=5 columns): {row!r}")
        id_match = _ID_CELL_RE.search(cells[0])
        mech_match = _ID_CELL_RE.search(cells[4])
        if not id_match or not mech_match:
            raise ParityError(f"{path}: could not extract id/mechanism from Table A row: {row!r}")
        if id_match.group(1) in mechanisms:
            raise ParityError(f"{path}: Table A 'A/C' lists {id_match.group(1)!r} twice")
        mechanisms[id_match.group(1)] = mech_match.group(1)
    if not mechanisms:
        raise ParityError(f"{path}: parsed zero Table A 'A/C' rows")

    count_match = _TABLE_A_ROWS_COUNT_RE.search(text)
    if not count_match:
        raise ParityError(f"{path}: the Counts section states no \"**Table A 'A/C' sub-table rows:** <n>\" figure")
    stated = int(count_match.group(1))
    if stated != len(mechanisms):
        raise ParityError(f"{path}: Table A 'A/C' has {len(mechanisms)} rows but the Counts section states {stated}")

    if shapes_dir is not None:
        in_shapes = shape_rule_ids(shapes_dir, config)
        missing = sorted(set(comparable_rule_ids(mechanisms)) - in_shapes)
        if missing:
            raise ParityError(
                f"{path}: comparable Table A id(s) {missing} are no itpra-o:ruleId in the shapes under {shapes_dir}"
            )
        unregistered = sorted(in_shapes - set(mechanisms) - parse_table_b_ids(path))
        if unregistered:
            raise ParityError(
                f"{path}: itpra-o:ruleId value(s) {unregistered} in the shapes under {shapes_dir} appear in "
                "neither Table A nor Table B"
            )
    return mechanisms


def comparable_rule_ids(mechanisms: dict[str, str]) -> tuple[str, ...]:
    """Ids whose Table A mechanism is ``core``/``sparql``, minus ``relates-to-malformed`` (the erratum)."""
    ids = {rid for rid, mech in mechanisms.items() if mech in _COMPARABLE_MECHANISMS}
    ids.discard(_RELATES_TO_MALFORMED)
    return tuple(sorted(ids))


def emit_time_mapped_rule_ids(mechanisms: dict[str, str]) -> tuple[str, ...]:
    """Ids an ``emit-error`` synthetic finding can stand in for: Table A's ``generated`` rows, plus the
    ``python`` rows enforced by a plain emit-time ``raise`` (:data:`_EMIT_TIME_PYTHON_IDS`:
    ``relates-to-malformed`` — the erratum, module docstring — and ``req-link-malformed``).
    Each of those must be a Table A row, or :class:`ParityError` (the register and this module drifted)."""
    ids = {rid for rid, mech in mechanisms.items() if mech == "generated"}
    missing = sorted(_EMIT_TIME_PYTHON_IDS - set(mechanisms))
    if missing:
        raise ParityError(f"emit-time-mapped id(s) {missing} are not Table A 'A/C' rows")
    ids |= _EMIT_TIME_PYTHON_IDS
    return tuple(sorted(ids))


def outside_scope_rule_ids(mechanisms: dict[str, str]) -> tuple[str, ...]:
    """Table A 'A/C' ids that are neither comparable nor emit-time-mapped (mechanism ``python``) — reported,
    never hidden, so a reader can see the full Table A inventory this module's comparison touches."""
    comparable = set(comparable_rule_ids(mechanisms))
    emit_mapped = set(emit_time_mapped_rule_ids(mechanisms))
    return tuple(sorted(set(mechanisms) - comparable - emit_mapped))


def _nominal_rule_id(fixture: fixtures.Fixture) -> str:
    """The Table A/B id a fixture proves. Equal to ``fixture.rule`` except for an emit-time-guard fixture
    (``rule: emit-error``), whose real id is the fixture's own filename with a trailing ``-emit-guard``
    suffix stripped (module docstring's "Emit-time mapping")."""
    if fixture.rule != "emit-error":
        return fixture.rule
    return fixture.path.stem.removesuffix("-emit-guard")


# =====================================================================================================
# Running the linter as a subprocess


def default_registries(config: Config | None = None) -> tuple[str, ...]:
    """Every registry the overlay's ``requirements_glob`` matches (:func:`itpra_onto.emit.registry_of`), sorted."""
    config = config if config is not None else load_config()
    return tuple(sorted({emit.registry_of(path, config) for path in emit.registry_files(config)}))


def _run_linter_json(script: Path, sub_arg: str, *, cwd: Path) -> list[dict[str, Any]]:
    proc = subprocess.run(
        [sys.executable, str(script), sub_arg, "--json"],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ParityError(
            f"linter --json ({script}, sub={sub_arg!r}, exit {proc.returncode}) did not print valid JSON: "
            f"stdout={proc.stdout[:2000]!r} stderr={proc.stderr[:2000]!r}"
        ) from exc
    if not isinstance(payload, list):
        raise ParityError(f"linter --json ({script}, sub={sub_arg!r}): expected a JSON list, got {type(payload).__name__}")
    return payload


def run_linter(sub: str, config: Config | None = None) -> list[dict[str, Any]]:
    """Run the REAL, committed consumer linter against the real repository tree for one registry."""
    return _run_linter_json(linter_script(config), sub, cwd=REPO_ROOT)


def _linter_findings_as_set(findings: list[dict[str, Any]], rule_ids: frozenset[str]) -> set[tuple[str, str, str]]:
    return {(f["rule"], f["subject"], f["severity"]) for f in findings if f.get("rule") in rule_ids}


# =====================================================================================================
# Real-tree comparison


@dataclass(frozen=True)
class RealTreeComparison:
    comparable_rules: tuple[str, ...]
    linter_count: int
    shacl_count: int
    linter_only: tuple[tuple[str, str, str], ...]
    shacl_only: tuple[tuple[str, str, str], ...]
    stricter_findings: tuple[tuple[str, str, str], ...]
    outside_scope: tuple[str, ...]
    # Linter findings of META_EDGE_RULE_IDS on an EntityType record — python-only by construction (the
    # emitter never projects a meta-edge), left out of the comparison and reported here.
    meta_edge_excluded: tuple[tuple[str, str, str], ...] = ()
    # The emitter refused the inputs (an EmitError); the SHACL side never ran. Each entry is the
    # synthetic `emit-error` finding {rule, subject, severity, message}. Non-empty -> the comparison fails.
    emit_errors: tuple[dict[str, str], ...] = ()

    @property
    def empty_symmetric_difference(self) -> bool:
        return not self.linter_only and not self.shacl_only

    @property
    def passed(self) -> bool:
        """Empty symmetric difference AND the SHACL side actually ran (no emit error)."""
        return self.empty_symmetric_difference and not self.emit_errors


def entity_type_record_ids(inputs: emit.Inputs) -> frozenset[str]:
    """Ids of every ``EntityType`` term record (their ``relates_to`` are meta-edges, never emitted)."""
    return frozenset(
        str(t.record.get("id")) for t in inputs.terms if t.record.get("type") == emit.META_SUBJECT_TYPE
    )


def emit_error_as_dict(exc: emit.EmitError, config: Config) -> dict[str, str]:
    """The synthetic ``emit-error`` finding, in the linter's ``--json`` row shape."""
    finding = shacl.emit_error_finding(exc, config)
    return {
        "rule": finding.rule_id or shacl.EMIT_ERROR_RULE_ID,
        "subject": shacl.focus_local_name(finding.focus, config),
        "severity": shacl.SEVERITY_TO_LINTER[finding.severity],
        "message": finding.message,
    }


def run_real_tree(
    subs: Sequence[str] | None = None,
    *,
    config: Config | None = None,
    register_path: Path = REGISTER_MD,
) -> RealTreeComparison:
    """The primary parity comparison: the union (deduplicated) of the consumer's linter's ``--json`` findings
    over ``subs`` (default: every registry — :func:`default_registries`), restricted to the comparable
    (``core``/``sparql``) rule ids, versus one whole-tree :func:`itpra_onto.shacl.validate` run restricted
    to the same ids (module docstring: "Avoiding an N-times-duplicated term finding").

    A linter finding of ``target-unresolved``/``verb-unknown`` on an EntityType record is excluded
    (meta-edges never reach a graph — ``meta_edge_excluded``); an :class:`itpra_onto.emit.EmitError` becomes
    the synthetic ``emit-error`` finding (``emit_errors``) instead of a traceback, and fails the comparison."""
    config = config if config is not None else load_config()
    mechanisms = parse_table_a(register_path, config=config)
    comparable = frozenset(comparable_rule_ids(mechanisms))
    outside = outside_scope_rule_ids(mechanisms)

    targets = tuple(subs) if subs else default_registries(config)
    if not targets:
        raise ParityError("run_real_tree: no registries to compare against (subs=() and none discovered)")
    linter_union: set[tuple[str, str, str]] = set()
    for sub in targets:
        linter_union |= _linter_findings_as_set(run_linter(sub), comparable)

    emit_errors: tuple[dict[str, str], ...] = ()
    all_shacl: set[tuple[str | None, str, str]] = set()
    inputs: emit.Inputs | None = None
    try:
        inputs = emit.load_inputs(config)
        asserted = emit.emit(inputs, config)
    except emit.EmitError as exc:
        emit_errors = (emit_error_as_dict(exc, config),)
    else:
        dataset = rules.apply_rules(asserted, config).dataset
        shapes = shacl.load_shapes(config=config)
        report = shacl.validate(dataset, shapes, config=config)
        all_shacl = shacl.findings_as_set(report, config)

    meta_types = entity_type_record_ids(inputs) if inputs is not None else frozenset()
    excluded = {f for f in linter_union if f[0] in META_EDGE_RULE_IDS and f[1] in meta_types}
    linter_union -= excluded

    shacl_comparable = {f for f in all_shacl if f[0] in comparable}
    stricter = {f for f in all_shacl if f[0] not in comparable}

    return RealTreeComparison(
        comparable_rules=tuple(sorted(comparable)),
        linter_count=len(linter_union),
        shacl_count=len(shacl_comparable),
        linter_only=tuple(sorted(linter_union - shacl_comparable)),
        shacl_only=tuple(sorted(shacl_comparable - linter_union)),
        stricter_findings=tuple(sorted(stricter)),
        outside_scope=outside,
        meta_edge_excluded=tuple(sorted(excluded)),
        emit_errors=emit_errors,
    )


def _finding_dict(finding: tuple[str, str, str]) -> dict[str, str]:
    rule, subject, severity = finding
    return {"rule": rule, "subject": subject, "severity": severity}


def comparison_as_dict(comparison: RealTreeComparison) -> dict[str, Any]:
    return {
        "comparable_rules": list(comparison.comparable_rules),
        "linter": comparison.linter_count,
        "shacl": comparison.shacl_count,
        "linter_only": [_finding_dict(f) for f in comparison.linter_only],
        "shacl_only": [_finding_dict(f) for f in comparison.shacl_only],
        "stricter_findings": [_finding_dict(f) for f in comparison.stricter_findings],
        "outside_scope": list(comparison.outside_scope),
        "meta_edge_excluded": [_finding_dict(f) for f in comparison.meta_edge_excluded],
        "emit_errors": list(comparison.emit_errors),
    }


def print_report(comparison: RealTreeComparison) -> None:
    print(f"parity: {len(comparison.comparable_rules)} comparable rule id(s): {', '.join(comparison.comparable_rules)}")
    for e in comparison.emit_errors:
        print(f"parity: EMIT ERROR — the SHACL side did not run: {e['severity']}  {e['rule']}  {e['subject']}  {e['message']}")
    print(f"parity: linter {comparison.linter_count} finding(s), shacl {comparison.shacl_count} finding(s) (comparable set)")
    if comparison.empty_symmetric_difference:
        print("parity: symmetric difference is EMPTY — linter and SHACL agree over the comparable set")
    else:
        for f in comparison.linter_only:
            print(f"  linter-only  {f[2]:8} {f[0]:25} {f[1]}")
        for f in comparison.shacl_only:
            print(f"  shacl-only   {f[2]:8} {f[0]:25} {f[1]}")
    if comparison.meta_edge_excluded:
        print(
            f"parity: {len(comparison.meta_edge_excluded)} linter finding(s) on EntityType meta-edges excluded "
            "(python-only: the emitter never projects a meta-edge):"
        )
        for f in comparison.meta_edge_excluded:
            print(f"  meta-edge    {f[2]:8} {f[0]:25} {f[1]}")
    if comparison.stricter_findings:
        print(f"parity: {len(comparison.stricter_findings)} stricter (Table B) SHACL finding(s) on the real tree (informational):")
        for f in comparison.stricter_findings:
            print(f"  stricter     {f[2]:8} {f[0]:25} {f[1]}")
    print(f"parity: {len(comparison.outside_scope)} linter rule id(s) outside the comparable set (mechanism python/generated): "
          f"{', '.join(comparison.outside_scope)}")


# =====================================================================================================
# Materialising a fixture's mutation onto disk (--fixtures only; module docstring)


def _load_yaml_file(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _dump_yaml_file(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, default_flow_style=False)


def _scratch_path(scratch_root: Path, real: Path) -> Path:
    """Where ``real`` lives in the scratch tree: the same path relative to the repository root, so the
    consumer's linter finds everything where its own layout puts it."""
    resolved = real.resolve()
    if not resolved.is_relative_to(REPO_ROOT):
        raise ParityError(f"{real}: outside the repository root {REPO_ROOT}; cannot mirror it into a scratch tree")
    return scratch_root / resolved.relative_to(REPO_ROOT)


def _copy_ontology_dir(scratch_root: Path, config: Config | None = None) -> None:
    config = config if config is not None else load_config()
    shutil.copytree(emit.ontology_dir(config), _scratch_path(scratch_root, emit.ontology_dir(config)), dirs_exist_ok=True)


def _copy_linter_script(scratch_root: Path, config: Config | None = None) -> None:
    dest = _scratch_path(scratch_root, linter_script(config))
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(linter_script(config), dest)


def _registry_files_of(registry: str, config: Config) -> list[Path]:
    return [p for p in emit.registry_files(config) if emit.registry_of(p, config) == registry]


def _copy_registry_dir(scratch_root: Path, registry: str, config: Config | None = None) -> None:
    config = config if config is not None else load_config()
    files = _registry_files_of(registry, config)
    if not files:
        raise ParityError(f"no registry file of {registry!r} matches the overlay's requirements_glob")
    for src in files:
        dest = _scratch_path(scratch_root, src)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _materialize_mutate_term(scratch_root: Path, record_file: str, record_id: str, mutate: fixtures.MutateAction) -> None:
    path = scratch_root / record_file
    data = _load_yaml_file(path)
    if not isinstance(data, list):
        raise ParityError(f"{path}: expected a term file top-level list")
    for index, rec in enumerate(data):
        if isinstance(rec, dict) and rec.get("id") == record_id:
            data[index] = fixtures._apply_mutation(rec, mutate)
            break
    else:
        raise ParityError(f"{path}: mutate.id {record_id!r} not found")
    _dump_yaml_file(path, data)


def _materialize_mutate_registry(scratch_root: Path, record_file: str, record_id: str, mutate: fixtures.MutateAction) -> None:
    path = scratch_root / record_file
    data = _load_yaml_file(path) or {}
    reqs = data.get("requirements")
    if not isinstance(reqs, list):
        raise ParityError(f"{path}: expected a top-level 'requirements' list")
    for index, rec in enumerate(reqs):
        if isinstance(rec, dict) and rec.get("id") == record_id:
            reqs[index] = fixtures._apply_mutation(rec, mutate)
            break
    else:
        raise ParityError(f"{path}: mutate.id {record_id!r} not found")
    _dump_yaml_file(path, data)


def _materialize_add_term(scratch_root: Path, record: dict[str, Any], config: Config) -> None:
    path = _scratch_path(scratch_root, emit.ontology_dir(config)) / "_fixture-scratch.yaml"
    existing = _load_yaml_file(path) if path.exists() else []
    existing = existing or []
    existing.append(copy.deepcopy(record))
    _dump_yaml_file(path, existing)


def _materialize_add_registry(scratch_root: Path, registry: str, kind: str, record: dict[str, Any], config: Config) -> None:
    """Append ``record`` to the registry file of ``registry`` whose stem is ``kind`` (``registry:<X>/<kind>``)."""
    matches = [p for p in _registry_files_of(registry, config) if p.stem == kind]
    if len(matches) != 1:
        raise ParityError(f"registry {registry!r} has {len(matches)} file(s) named {kind}.yaml; add.file needs exactly one")
    path = _scratch_path(scratch_root, matches[0])
    data = _load_yaml_file(path) or {}
    reqs = data.setdefault("requirements", [])
    reqs.append(copy.deepcopy(record))
    _dump_yaml_file(path, data)


def materialize_fixture(
    fixture: fixtures.Fixture, scratch_root: Path, real_inputs: emit.Inputs, config: Config | None = None
) -> str:
    """Apply ``fixture``'s mutation/addition onto the scratch copy of the tree rooted at ``scratch_root``
    (which must already hold a copy of the ontology dir and the linter script — module docstring). Returns
    the registry name to pass as the linter's positional argument."""
    config = config if config is not None else load_config()
    action = fixture.action
    if isinstance(action, fixtures.MutateAction):
        for term in real_inputs.terms:
            if term.record.get("id") == action.id:
                _materialize_mutate_term(scratch_root, term.file, action.id, action)
                return _default_linter_arg(config)
        for req in real_inputs.requirements:
            if req.record.get("id") == action.id:
                _copy_registry_dir(scratch_root, req.registry, config)
                _materialize_mutate_registry(scratch_root, req.file, action.id, action)
                return req.registry
        raise ParityError(f"materialize_fixture: mutate.id {action.id!r} matches no term or requirement record")

    if action.file == "terms":
        _materialize_add_term(scratch_root, action.record, config)
        return _default_linter_arg(config)
    registry, _, kind = action.file.removeprefix("registry:").partition("/")
    if not registry or not kind:
        raise ParityError(f"materialize_fixture: add.file {action.file!r} does not name a registry/kind")
    _copy_registry_dir(scratch_root, registry, config)
    _materialize_add_registry(scratch_root, registry, kind, action.record, config)
    return registry


# =====================================================================================================
# --fixtures comparison


@dataclass(frozen=True)
class FixtureVerdict:
    fixture: str  # e.g. "structural/field-missing.yaml" (repo-relative to fixtures/)
    nominal_rule: str  # the Table A/B id this fixture proves (module docstring's _nominal_rule_id)
    focus: str
    shacl_caught: bool
    shacl_rule_seen: str | None  # the actual SHACL-side rule_id (may be "emit-error")
    linter_caught: bool
    linter_rules_seen: tuple[str, ...]  # every rule id the linter reported on this focus (debugging aid)
    verdict: str  # "both" | "shacl-only" | "linter-only" | "neither"
    comparable: bool  # nominal_rule is in the comparable OR emit-time-mapped set


def verdict_as_dict(verdict: FixtureVerdict) -> dict[str, Any]:
    return {
        "fixture": verdict.fixture,
        "nominal_rule": verdict.nominal_rule,
        "focus": verdict.focus,
        "shacl_caught": verdict.shacl_caught,
        "shacl_rule_seen": verdict.shacl_rule_seen,
        "linter_caught": verdict.linter_caught,
        "linter_rules_seen": list(verdict.linter_rules_seen),
        "verdict": verdict.verdict,
        "comparable": verdict.comparable,
    }


def _run_one_fixture(
    fixture_path: Path,
    shapes_dir: Path,
    real_inputs: emit.Inputs,
    config: Config,
    comparable: frozenset[str],
    emit_mapped: frozenset[str],
) -> FixtureVerdict:
    fixture = fixtures.load_fixture(fixture_path)
    nominal = _nominal_rule_id(fixture)

    report, _expected = fixtures.run_fixture(fixture_path, shapes_dir, config=config)

    # An emit-time fixture naming expect.emit_error matches only that EmitError class, not any emit error
    # on the same subject (fixtures.finding_matches).
    shacl_matches = [f for f in report.findings if fixtures.finding_matches(f, fixture, config)]
    shacl_caught = fixture.count >= 1 and len(shacl_matches) == fixture.count
    shacl_rule_seen = shacl_matches[0].rule_id if shacl_matches else None

    with tempfile.TemporaryDirectory(prefix="itpra-parity-") as tmp:
        scratch_root = Path(tmp)
        _copy_ontology_dir(scratch_root, config)
        _copy_linter_script(scratch_root, config)
        sub_arg = materialize_fixture(fixture, scratch_root, real_inputs, config)
        script = _scratch_path(scratch_root, linter_script(config))
        linter_findings = _run_linter_json(script, sub_arg, cwd=scratch_root)

    focus_findings = [f for f in linter_findings if f.get("subject") == fixture.focus]
    linter_rules_seen = tuple(sorted({f["rule"] for f in focus_findings}))
    linter_caught = nominal in linter_rules_seen

    if shacl_caught and linter_caught:
        verdict = "both"
    elif shacl_caught:
        verdict = "shacl-only"
    elif linter_caught:
        verdict = "linter-only"
    else:
        verdict = "neither"

    return FixtureVerdict(
        fixture=fixture_path.relative_to(FIXTURES_DIR).as_posix(),
        nominal_rule=nominal,
        focus=fixture.focus,
        shacl_caught=shacl_caught,
        shacl_rule_seen=shacl_rule_seen,
        linter_caught=linter_caught,
        linter_rules_seen=linter_rules_seen,
        verdict=verdict,
        comparable=(nominal in comparable or nominal in emit_mapped),
    )


def run_fixtures(
    *,
    config: Config | None = None,
    shapes_dir: Path = shacl.SHAPES_DIR,
    register_path: Path = REGISTER_MD,
) -> list[FixtureVerdict]:
    """The ``--fixtures`` comparison: one :class:`FixtureVerdict` per fixture with ``expect.count >= 1``
    under ``fixtures/**/*.yaml`` (module docstring: a ``count: 0`` clean-case fixture has nothing for the
    linter side to independently confirm, so it is skipped here)."""
    config = config if config is not None else load_config()
    mechanisms = parse_table_a(register_path, shapes_dir=shapes_dir, config=config)
    comparable = frozenset(comparable_rule_ids(mechanisms))
    emit_mapped = frozenset(emit_time_mapped_rule_ids(mechanisms))
    real_inputs = emit.load_inputs(config)

    verdicts: list[FixtureVerdict] = []
    for fixture_path in sorted(FIXTURES_DIR.glob("*/*.yaml")):
        fixture = fixtures.load_fixture(fixture_path)
        if fixture.count < 1:
            continue
        verdicts.append(_run_one_fixture(fixture_path, shapes_dir, real_inputs, config, comparable, emit_mapped))
    return verdicts


FAILING_VERDICTS = ("neither", "linter-only")


def fixture_failures(verdicts: Sequence[FixtureVerdict]) -> list[FixtureVerdict]:
    """The verdicts that fail ``parity --fixtures``: ``neither`` on any fixture (nothing noticed
    the mutation at all — always a bug), and ``linter-only`` on a comparable or emit-time-mapped rule (the
    projection has a gap the linter does not). ``linter-only`` on a Table B id cannot occur (the linter has
    no such id)."""
    return [
        v for v in verdicts if v.verdict == "neither" or (v.verdict in FAILING_VERDICTS and v.comparable)
    ]


def print_fixture_report(verdicts: list[FixtureVerdict]) -> None:
    for v in verdicts:
        print(f"{v.verdict:12} {v.nominal_rule:32} {v.focus:34} shacl={v.shacl_caught!s:5} linter={v.linter_caught!s:5}  ({v.fixture})")
    failures = fixture_failures(verdicts)
    print(
        f"parity --fixtures: {len(verdicts)} fixture(s) checked, {len(failures)} failure(s) "
        "(verdict 'neither', or 'linter-only' on a comparable/emit-time-mapped rule)"
    )

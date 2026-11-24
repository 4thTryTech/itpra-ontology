"""``itpra-onto parity`` (ADR 0042 D5; ``shapes/REGISTER.md`` is the register the comparison is read from).

Compares the linter's findings (:mod:`itpra_onto.lint`) against pySHACL's (:mod:`itpra_onto.shacl`) over the
SAME inputs, as ``(rule, subject, severity)`` triples — the shape both sides' ``--json`` outputs share.

**Guards.** The register parser fails loudly (exact header row, row count equal to the Counts section's
stated figure, and a cross-check that every comparable id is an ``itpra-o:ruleId`` in the loaded shapes and
every shape ``ruleId`` is a Table A or Table B id); linter findings of ``target-unresolved``/``verb-unknown``
on an EntityType record (meta-edges, never projected) are excluded from the real-tree comparison and
reported; an ``EmitError`` becomes an ``emit-error`` finding that fails the comparison; and ``--fixtures``
fails on ``linter-only`` for a comparable or emit-mapped rule (:func:`fixture_failures`).

**Comparable set.** Rows of ``shapes/REGISTER.md`` Table A whose ``mechanism`` reads ``core`` or ``sparql``
exist on *both* sides under the same rule id, and are compared by rule-id equality. The table is parsed at
run time (:func:`parse_table_a`), so the register stays the single source; a parse failure raises
:class:`ParityError` rather than falling back to a hard-coded set.

**Emit-time mapping.** A ``generated`` or ``emit`` row never reaches a graph: the emitter raises
``EmitError`` first, and :mod:`itpra_onto.fixtures` turns that into one synthetic ``emit-error`` finding.
Comparing those rows cannot be rule-id equality: :func:`nominal_rule_id` recovers the id a ``rule:
emit-error`` fixture proves (its filename, stripped of a trailing ``-emit-guard``), and the ``--fixtures``
comparison matches the linter's own finding for that id against the ``emit-error`` marker on the same
subject.

**Real-tree comparison** (``itpra-onto parity``): the linter over the vocabulary, and one
:func:`itpra_onto.shacl.validate` over the emitted and ruled dataset, both restricted to the comparable ids.

**``--fixtures`` comparison**: for every fixture under ``fixtures/**/*.yaml`` whose ``expect.count >= 1`` (a
``count: 0`` clean-case fixture proves a shape does NOT fire — there is nothing for the linter to confirm,
so it is skipped), the mutation is written into a scratch copy of the vocabulary and the linter runs over
that copy, while the shape side stays the in-memory :func:`itpra_onto.fixtures.run_fixture` call. Each
fixture's verdict is ``both``, ``shacl-only`` (expected for every Table B id), ``linter-only`` (a gap in the
shapes — never expected) or ``neither`` (always a bug).
"""

from __future__ import annotations

import copy
import re
import shutil
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pyoxigraph as ox
import yaml

from itpra_onto import emit, fixtures, lint, rules, shacl
from itpra_onto.config import Config, load_config

PACKAGE_DIR = Path(__file__).resolve().parent  # src/itpra_onto: the package's own code and data
REGISTER_MD = PACKAGE_DIR / "shapes" / "REGISTER.md"
FIXTURES_DIR = fixtures.FIXTURES_DIR

COMPARABLE_MECHANISMS = ("core", "sparql")
EMIT_TIME_MECHANISMS = ("generated", "emit")
MECHANISMS = (*COMPARABLE_MECHANISMS, *EMIT_TIME_MECHANISMS, "python")

_TABLE_A_SECTION_RE = re.compile(r"\n## Table A .*?\n(.*?)\n## Table B ", re.DOTALL)
_TABLE_B_SECTION_RE = re.compile(r"\n## Table B .*?\n(.*?)\n## Table C ", re.DOTALL)
_TABLE_B_ID_RE = re.compile(r"^\|\s*(B-[0-9]+(?:-[a-z0-9-]+)?)\s*\|", re.MULTILINE)
_ID_CELL_RE = re.compile(r"`([^`]+)`")
# The exact header Table A must carry, and the Counts line stating its row count — both checked, so a
# register edit that reshapes the table fails loudly.
TABLE_A_HEADER = "| id | sev | check | family | mechanism | target | notes |"
_TABLE_A_ROWS_COUNT_RE = re.compile(r"\*\*Table A rows:\*\* (\d+)")

# The linter checks `relates_to` on EntityType records too (their meta-edges), but the emitter never
# projects a meta-edge (a schema statement, ADR 0008), so no graph ever carries one. Findings of these ids
# on an EntityType subject are python-only by construction and are left out of the comparison (and reported).
META_EDGE_RULE_IDS = frozenset({"target-unresolved", "verb-unknown"})
EMIT_ERROR_RULE = "emit-error"


class ParityError(RuntimeError):
    """The register could not be parsed, or a comparison input was malformed."""


# =====================================================================================================
# Register parsing (shapes/REGISTER.md)


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


def shape_rule_ids(
    shapes: ox.Dataset | None = None, *, shapes_dir: Path = shacl.SHAPES_DIR, config: Config | None = None
) -> frozenset[str]:
    """Every ``itpra-o:ruleId`` value in ``shapes`` (default: the shapes loaded from ``shapes_dir``)."""
    config = config if config is not None else load_config()
    if shapes is None:
        shapes = shacl.load_shapes(shapes_dir, config=config)
    return frozenset(shacl._shape_rule_ids(shapes, config).values())


def parse_table_a(
    register_path: Path = REGISTER_MD,
    *,
    shapes_dir: Path | None = shacl.SHAPES_DIR,
    config: Config | None = None,
) -> dict[str, str]:
    """``id -> mechanism`` for every row of Table A, parsed from the register at run time so it stays the
    single source. Raises :class:`ParityError` — never a silent fallback to a hard-coded id list — if:

    * the section cannot be found, the header row is not exactly :data:`TABLE_A_HEADER`, or a row cannot be
      parsed or names a mechanism outside :data:`MECHANISMS`;
    * the number of rows differs from the "Table A rows" figure the register's Counts section states;
    * (``shapes_dir`` given — the default) a comparable id is not an ``itpra-o:ruleId`` in the shapes loaded
      from it, or a ``ruleId`` there appears in neither Table A nor Table B. ``shapes_dir=None`` skips this
      cross-check (the register alone is parsed).
    """
    path = register_path
    text = path.read_text(encoding="utf-8")
    match = _TABLE_A_SECTION_RE.search(text)
    if not match:
        raise ParityError(f"{path}: could not locate the '## Table A' section")
    lines = [ln.strip() for ln in match.group(1).splitlines() if ln.strip().startswith("|")]
    if len(lines) < 3:
        raise ParityError(f"{path}: Table A has too few rows ({len(lines)})")
    if lines[0] != TABLE_A_HEADER:
        raise ParityError(f"{path}: Table A header row is {lines[0]!r}, expected exactly {TABLE_A_HEADER!r}")
    if not re.fullmatch(r"\|(?:-+\|)+", lines[1]):
        raise ParityError(f"{path}: Table A second row is not a '|---|' separator: {lines[1]!r}")
    mechanisms: dict[str, str] = {}
    for row in lines[2:]:  # skip the header row and the '|---|...' separator
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) < 5:
            raise ParityError(f"{path}: malformed Table A row (expected >=5 columns): {row!r}")
        id_match = _ID_CELL_RE.search(cells[0])
        mech_match = _ID_CELL_RE.search(cells[4])
        if not id_match or not mech_match:
            raise ParityError(f"{path}: could not extract id/mechanism from Table A row: {row!r}")
        if mech_match.group(1) not in MECHANISMS:
            raise ParityError(f"{path}: Table A row {id_match.group(1)!r} has mechanism {mech_match.group(1)!r}, expected one of {MECHANISMS}")
        if id_match.group(1) in mechanisms:
            raise ParityError(f"{path}: Table A lists {id_match.group(1)!r} twice")
        mechanisms[id_match.group(1)] = mech_match.group(1)
    if not mechanisms:
        raise ParityError(f"{path}: parsed zero Table A rows")

    count_match = _TABLE_A_ROWS_COUNT_RE.search(text)
    if not count_match:
        raise ParityError(f'{path}: the Counts section states no "**Table A rows:** <n>" figure')
    stated = int(count_match.group(1))
    if stated != len(mechanisms):
        raise ParityError(f"{path}: Table A has {len(mechanisms)} rows but the Counts section states {stated}")

    if shapes_dir is not None:
        in_shapes = shape_rule_ids(shapes_dir=shapes_dir, config=config)
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
    """Ids whose Table A mechanism is ``core`` or ``sparql``."""
    return tuple(sorted(rid for rid, mech in mechanisms.items() if mech in COMPARABLE_MECHANISMS))


def emit_time_mapped_rule_ids(mechanisms: dict[str, str]) -> tuple[str, ...]:
    """Ids an ``emit-error`` synthetic finding can stand in for: Table A's ``generated`` and ``emit`` rows."""
    return tuple(sorted(rid for rid, mech in mechanisms.items() if mech in EMIT_TIME_MECHANISMS))


def outside_scope_rule_ids(mechanisms: dict[str, str]) -> tuple[str, ...]:
    """Table A ids that are neither comparable nor emit-time-mapped (mechanism ``python``) — reported, never
    hidden, so a reader can see the full inventory the comparison touches."""
    return tuple(sorted(rid for rid, mech in mechanisms.items() if mech == "python"))


def nominal_rule_id(fixture: fixtures.Fixture) -> str:
    """The Table A/B id a fixture proves. Equal to ``fixture.rule`` except for an emit-time-guard fixture
    (``rule: emit-error``), whose real id is the fixture's own filename with a trailing ``-emit-guard``
    suffix stripped (module docstring's "Emit-time mapping")."""
    if fixture.rule != EMIT_ERROR_RULE:
        return fixture.rule
    return fixture.path.stem.removesuffix("-emit-guard")


# =====================================================================================================
# The linter side


def lint_findings(config: Config | None = None, *, ontology_dir: Path | None = None) -> list[dict[str, Any]]:
    """:mod:`itpra_onto.lint` over ``ontology_dir`` (default: the configured one)."""
    config = config if config is not None else load_config()
    root = ontology_dir if ontology_dir is not None else emit.ontology_dir(config)
    findings, _vocab = lint.lint_vocabulary(root, rel_to=config.repo_root)
    return findings


def findings_as_set(findings: Iterable[dict[str, Any]], rule_ids: frozenset[str]) -> set[tuple[str, str, str]]:
    """Linter ``--json`` rows as ``{(rule, subject, severity)}``, restricted to ``rule_ids``."""
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


def compare(
    linter: set[tuple[str, str, str]],
    shacl_findings: set[tuple[str | None, str, str]],
    *,
    comparable: frozenset[str],
    outside_scope: Sequence[str],
    entity_types: frozenset[str] = frozenset(),
    emit_errors: Sequence[dict[str, str]] = (),
) -> RealTreeComparison:
    """One :class:`RealTreeComparison` from both sides' ``(rule, subject, severity)`` sets. ``linter`` holds
    comparable ids only; a finding of :data:`META_EDGE_RULE_IDS` on one of ``entity_types`` is set aside."""
    excluded = {f for f in linter if f[0] in META_EDGE_RULE_IDS and f[1] in entity_types}
    linter = linter - excluded
    shacl_comparable = {f for f in shacl_findings if f[0] in comparable}
    stricter = {f for f in shacl_findings if f[0] not in comparable}
    return RealTreeComparison(
        comparable_rules=tuple(sorted(comparable)),
        linter_count=len(linter),
        shacl_count=len(shacl_comparable),
        linter_only=tuple(sorted(linter - shacl_comparable)),
        shacl_only=tuple(sorted(shacl_comparable - linter)),
        stricter_findings=tuple(sorted(stricter)),
        outside_scope=tuple(outside_scope),
        meta_edge_excluded=tuple(sorted(excluded)),
        emit_errors=tuple(emit_errors),
    )


def run_real_tree(*, config: Config | None = None, register_path: Path = REGISTER_MD) -> RealTreeComparison:
    """The primary parity comparison: the linter's findings over the vocabulary, restricted to the comparable
    (``core``/``sparql``) rule ids, versus one :func:`itpra_onto.shacl.validate` run restricted to the same
    ids. An :class:`itpra_onto.emit.EmitError` becomes the synthetic ``emit-error`` finding (``emit_errors``)
    instead of a traceback, and fails the comparison."""
    config = config if config is not None else load_config()
    mechanisms = parse_table_a(register_path, config=config)
    comparable = frozenset(comparable_rule_ids(mechanisms))
    linter = findings_as_set(lint_findings(config), comparable)

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
        report = shacl.validate(dataset, shacl.load_shapes(config=config), config=config)
        all_shacl = shacl.findings_as_set(report, config)

    return compare(
        linter,
        all_shacl,
        comparable=comparable,
        outside_scope=outside_scope_rule_ids(mechanisms),
        entity_types=entity_type_record_ids(inputs) if inputs is not None else frozenset(),
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
    print(f"parity: {len(comparison.outside_scope)} linter rule id(s) outside the comparable set (mechanism python): "
          f"{', '.join(comparison.outside_scope)}")


# =====================================================================================================
# Writing a fixture's mutation into a scratch copy of the vocabulary (--fixtures only; module docstring)


def load_yaml_file(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def dump_yaml_file(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True, default_flow_style=False)


def scratch_path(scratch_root: Path, real: Path, repo_root: Path) -> Path:
    """Where ``real`` lives in the scratch tree: the same path relative to the repository root."""
    resolved = real.resolve()
    root = repo_root.resolve()
    if not resolved.is_relative_to(root):
        raise ParityError(f"{real}: outside the repository root {root}; cannot mirror it into a scratch tree")
    return scratch_root / resolved.relative_to(root)


def copy_ontology_dir(scratch_root: Path, config: Config | None = None) -> Path:
    """Copy the vocabulary into the scratch tree; returns the copy's directory."""
    config = config if config is not None else load_config()
    dest = scratch_path(scratch_root, emit.ontology_dir(config), config.repo_root)
    shutil.copytree(emit.ontology_dir(config), dest, dirs_exist_ok=True)
    return dest


def materialize_fixture(
    fixture: fixtures.Fixture, scratch_root: Path, real_inputs: emit.Inputs, config: Config | None = None
) -> None:
    """Apply ``fixture``'s mutation or addition to the scratch copy of the vocabulary under ``scratch_root``
    (:func:`copy_ontology_dir`)."""
    config = config if config is not None else load_config()
    action = fixture.action
    if isinstance(action, fixtures.MutateAction):
        record_file = next((t.file for t in real_inputs.terms if t.record.get("id") == action.id), None)
        if record_file is None:
            raise ParityError(f"materialize_fixture: mutate.id {action.id!r} matches no term record")
        path = scratch_root / record_file
        data = load_yaml_file(path)
        if not isinstance(data, list):
            raise ParityError(f"{path}: expected a term file top-level list")
        for index, rec in enumerate(data):
            if isinstance(rec, dict) and rec.get("id") == action.id:
                data[index] = fixtures.mutated_record(rec, action)
                break
        else:
            raise ParityError(f"{path}: mutate.id {action.id!r} not found")
        dump_yaml_file(path, data)
        return

    if action.file != "terms":
        raise ParityError(f"materialize_fixture: add.file {action.file!r} is not 'terms'")
    path = scratch_path(scratch_root, emit.ontology_dir(config), config.repo_root) / "_fixture-scratch.yaml"
    existing = (load_yaml_file(path) if path.exists() else []) or []
    existing.append(copy.deepcopy(action.record))
    dump_yaml_file(path, existing)


# =====================================================================================================
# --fixtures comparison


@dataclass(frozen=True)
class FixtureVerdict:
    fixture: str  # e.g. "structural/field-missing.yaml" (relative to its fixtures directory)
    nominal_rule: str  # the Table A/B id this fixture proves (nominal_rule_id)
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


def verdict_for(
    fixture: fixtures.Fixture,
    label: str,
    report: shacl.ValidationReport,
    linter_findings: Iterable[dict[str, Any]],
    *,
    comparable: frozenset[str],
    emit_mapped: frozenset[str],
    config: Config,
) -> FixtureVerdict:
    """One fixture's verdict from both sides' findings: the shape side's ``report`` over the mutated data and
    the linter's rows over the same mutation."""
    nominal = nominal_rule_id(fixture)
    # An emit-time fixture naming expect.emit_error matches only that EmitError class, not any emit error
    # on the same subject (fixtures.finding_matches).
    shacl_matches = [f for f in report.findings if fixtures.finding_matches(f, fixture, config)]
    shacl_caught = fixture.count >= 1 and len(shacl_matches) == fixture.count
    linter_rules_seen = tuple(sorted({f["rule"] for f in linter_findings if f.get("subject") == fixture.focus}))
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
        fixture=label,
        nominal_rule=nominal,
        focus=fixture.focus,
        shacl_caught=shacl_caught,
        shacl_rule_seen=shacl_matches[0].rule_id if shacl_matches else None,
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
    under ``fixtures/**/*.yaml``."""
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
        report, _expected = fixtures.run_fixture(fixture_path, shapes_dir, config=config)
        with tempfile.TemporaryDirectory(prefix="itpra-parity-") as tmp:
            scratch_root = Path(tmp)
            scratch_ontology = copy_ontology_dir(scratch_root, config)
            materialize_fixture(fixture, scratch_root, real_inputs, config)
            linter_findings = lint_findings(config, ontology_dir=scratch_ontology)
        verdicts.append(
            verdict_for(
                fixture,
                fixture_path.relative_to(FIXTURES_DIR).as_posix(),
                report,
                linter_findings,
                comparable=comparable,
                emit_mapped=emit_mapped,
                config=config,
            )
        )
    return verdicts


FAILING_VERDICTS = ("neither", "linter-only")


def fixture_failures(verdicts: Sequence[FixtureVerdict]) -> list[FixtureVerdict]:
    """The verdicts that fail ``parity --fixtures``: ``neither`` on any fixture (nothing noticed the mutation
    at all — always a bug), and ``linter-only`` on a comparable or emit-time-mapped rule (the shapes have a
    gap the linter does not). ``linter-only`` on a Table B id cannot occur (the linter has no such id)."""
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

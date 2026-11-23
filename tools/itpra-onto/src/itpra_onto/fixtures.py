"""The fixture harness for SHACL validation parity (ADR 0042 D4), importable by the tests of the three
hand-written shape files (``shapes/REGISTER.md``: ``structural``, ``crossfield``, ``requirements``).

A fixture is one YAML file under ``fixtures/<group>/<rule-id>.yaml`` describing a single, deliberately
broken record — a mutation of one real, currently-clean record from the live ontology/requirements
registries, or a whole new record added alongside them — plus what that mutation is expected to make the
shapes report. It is the mechanism ADR 0042 D4 asks for: one deliberately broken record per rule, and clean
data must pass every shape file unmodified.

**Fixture file grammar** (every field below):

.. code-block:: yaml

    rule: field-missing          # the itpra-o:ruleId this fixture proves (Table A id or a Table-B "B-n" id)
    expect:
      severity: Violation        # Violation | Warning (sh:severity local name, Table C)
      focus: CAP-ITO-FND-1           # the id (local name) the finding must land on
      count: 1                   # optional, default 1: how many findings of `rule` the mutation must raise
                                  # (a non-negative integer). `count: 0` is a CLEAN-CASE / defence-in-depth
                                  # fixture: the mutation below must NOT make `rule` fire at all, and the
                                  # fixture's own header comment documents why no (or no isolatable) mutation
                                  # can trigger it — e.g. the defect can only be produced by injecting quads
                                  # directly (bypassing the emitter, proven elsewhere in that group's test
                                  # module), or the rule is causally coupled to another rule on the same
                                  # focus so no mutation can fire it in isolation. `assert_fixture()` still
                                  # asserts exactly `count` matching findings and that clean (real) data
                                  # raises none, but skips the no-cascade check for `count: 0` (see below).
      emit_error: SourceGrammarError   # optional, only with `rule: emit-error`: the EmitError
                                  # class the emitter must raise — the synthetic finding's message starts
                                  # with that class name, and assert_fixture() requires it, so an emit-time
                                  # fixture proves ITS guard fired, not merely that some emit error hit
                                  # the same subject.
      cofires: [B-22]            # optional: other Violation rule ids that the mutation fires on
                                  # the same focus BY CONSTRUCTION (one defect that two stated rules both
                                  # describe — e.g. a Function's derived_from edge is function-derived-from
                                  # AND an edge outside derived_from's allowed pairs, B-22). The no-cascade
                                  # check tolerates exactly these ids; the fixture header must say why.

    # then exactly ONE of the two blocks below:

    mutate:                      # start from an EXISTING record (by id) and break one thing about it
      id: CAP-ITO-FND-1
      set: {type: Persona}       # replace/add top-level fields (a dict merged into the record)
      # -- or --
      append_relates_to: {rel: grouped_by, target: DOM-FOUNDATION}   # append one relates_to edge
      # -- or --
      delete: [term]             # drop top-level fields entirely (e.g. to trigger field-missing)
      # exactly one of set / append_relates_to / delete is given

    add:                         # or: introduce a whole NEW record instead of mutating one
      file: terms                # "terms" (-> a term record of the vocabulary) or "registry:<X>/<functional|non-functional>"
      record: {id: CAP-FIXTURE-1, type: Capability, term: "...", definition: "...", relates_to: []}

Only one of ``mutate``/``add`` is given per fixture. :func:`apply_fixture` never touches disk — both paths
work on an in-memory, deep-copied :class:`itpra_onto.emit.Inputs`, exactly the object
:func:`itpra_onto.emit.load_inputs` returns from the real, clean corpus. A fixture's ``add.record`` is
tagged with a synthetic, human-readable ``file`` string (never a real path — :data:`SYNTHETIC_FILE`) so the
emitted ``itpra-o:authoringFile`` triple is still present without implying a file that does not exist.

The emitter may itself refuse a mutated record before any SHACL shape ever sees it (an unrecognised
``type``, a ``relates_to.rel`` outside the 17-verb list, a malformed ``source`` — every case
``shapes/REGISTER.md`` Table A marks mechanism ``generated``, plus B-10's ``source`` grammar, ADR 0005).
:func:`run_fixture` treats an :class:`itpra_onto.emit.EmitError` raised at that point as a single
synthetic :class:`itpra_onto.shacl.Finding` with ``rule_id="emit-error"`` (severity ``"Violation"``, focus
the mutated/added record's own id), so a fixture proving emit-time enforcement uses exactly the same
:func:`assert_fixture` call as one proving a SHACL shape (``shapes/REGISTER.md``'s own note: "the `source`
grammar is enforced at emit time" — B-10 is documented, not shape-bearing, precisely because of this).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from itpra_onto import emit, rules, shacl
from itpra_onto.config import Config, load_config
from itpra_onto.emit import Inputs, RegistryRecord, TermRecord

PACKAGE_DIR = Path(__file__).resolve().parent  # src/itpra_onto: the package's own code and data
FIXTURES_DIR = PACKAGE_DIR / "fixtures"  # the fixtures ship inside the package
SYNTHETIC_FILE = "fixtures/<synthetic, no real file>"


class FixtureError(RuntimeError):
    """A fixture YAML file is malformed, or names a record id ``mutate`` cannot find."""


# =====================================================================================================
# Fixture: parsed YAML


@dataclass(frozen=True)
class MutateAction:
    id: str
    set: dict[str, Any] | None = None
    append_relates_to: dict[str, str] | None = None
    delete: tuple[str, ...] = ()


@dataclass(frozen=True)
class AddAction:
    file: str  # "terms" | "registry:<X>/functional" | "registry:<X>/non-functional"
    record: dict[str, Any]


@dataclass(frozen=True)
class Fixture:
    """One parsed fixture file: what it proves (``rule``/``expect``) and how it breaks the data (``action``:
    a :class:`MutateAction` or an :class:`AddAction`, never both)."""

    rule: str
    severity: str
    focus: str
    count: int
    action: MutateAction | AddAction
    path: Path
    emit_error: str | None = None  # expect.emit_error
    cofires: tuple[str, ...] = ()  # expect.cofires


def _require_mapping(value: Any, *, path: Path, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise FixtureError(f"{path}: {where} must be a mapping, got {type(value).__name__}")
    return value


def load_fixture(path: Path) -> Fixture:
    """Parse one ``fixtures/<group>/<rule-id>.yaml`` file (the grammar in this module's docstring)."""
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    raw = _require_mapping(raw, path=path, where="the fixture")

    rule = raw.get("rule")
    if not isinstance(rule, str) or not rule:
        raise FixtureError(f"{path}: 'rule' must be a non-empty string")

    expect = _require_mapping(raw.get("expect"), path=path, where="'expect'")
    severity = expect.get("severity")
    if severity not in ("Violation", "Warning"):
        raise FixtureError(f"{path}: expect.severity must be 'Violation' or 'Warning', got {severity!r}")
    focus = expect.get("focus")
    if not isinstance(focus, str) or not focus:
        raise FixtureError(f"{path}: expect.focus must be a non-empty string")
    count = expect.get("count", 1)
    if not isinstance(count, int) or count < 0:
        raise FixtureError(f"{path}: expect.count must be a non-negative integer, got {count!r}")
    emit_error = expect.get("emit_error")
    if emit_error is not None:
        if rule != shacl.EMIT_ERROR_RULE_ID:
            raise FixtureError(f"{path}: expect.emit_error is only meaningful with rule: {shacl.EMIT_ERROR_RULE_ID}")
        if not isinstance(emit_error, str) or not hasattr(emit, emit_error) or not (
            isinstance(getattr(emit, emit_error), type) and issubclass(getattr(emit, emit_error), emit.EmitError)
        ):
            raise FixtureError(f"{path}: expect.emit_error must name an EmitError class in itpra_onto.emit, got {emit_error!r}")
    cofires = expect.get("cofires") or []
    if not isinstance(cofires, list) or not all(isinstance(c, str) and c for c in cofires):
        raise FixtureError(f"{path}: expect.cofires must be a list of rule ids, got {cofires!r}")

    has_mutate = "mutate" in raw
    has_add = "add" in raw
    if has_mutate == has_add:
        raise FixtureError(f"{path}: exactly one of 'mutate'/'add' must be given (got {has_mutate=}, {has_add=})")

    action: MutateAction | AddAction
    if has_mutate:
        mutate = _require_mapping(raw["mutate"], path=path, where="'mutate'")
        record_id = mutate.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise FixtureError(f"{path}: mutate.id must be a non-empty string")
        modes = [key for key in ("set", "append_relates_to", "delete") if key in mutate]
        if len(modes) != 1:
            raise FixtureError(f"{path}: mutate must give exactly one of set/append_relates_to/delete, got {modes}")
        action = MutateAction(
            id=record_id,
            set=mutate.get("set"),
            append_relates_to=mutate.get("append_relates_to"),
            delete=tuple(mutate.get("delete") or ()),
        )
    else:
        add = _require_mapping(raw["add"], path=path, where="'add'")
        file = add.get("file")
        if file != "terms" and not (isinstance(file, str) and file.startswith("registry:")):
            raise FixtureError(f"{path}: add.file must be 'terms' or 'registry:<X>/<functional|non-functional>', got {file!r}")
        record = _require_mapping(add.get("record"), path=path, where="'add.record'")
        action = AddAction(file=file, record=record)

    return Fixture(
        rule=rule,
        severity=severity,
        focus=focus,
        count=count,
        action=action,
        path=path,
        emit_error=emit_error,
        cofires=tuple(cofires),
    )


def finding_matches(finding: shacl.Finding, fixture: Fixture, config: Config) -> bool:
    """``finding`` is one ``fixture`` expects: its rule, severity and focus — and, for an emit-time fixture
    naming ``expect.emit_error``, raised by that EmitError class."""
    if finding.rule_id != fixture.rule or finding.severity != fixture.severity:
        return False
    if shacl.focus_local_name(finding.focus, config) != fixture.focus:
        return False
    if fixture.emit_error is not None and not finding.message.startswith(f"{fixture.emit_error}: "):
        return False
    return True


def fixture_files(fixtures_dir: Path) -> list[Path]:
    """Every ``*.yaml`` file directly under ``fixtures_dir``, sorted by name (mirrors :func:`itpra_onto.shacl.shape_files`)."""
    return sorted(fixtures_dir.glob("*.yaml"))


# =====================================================================================================
# apply_fixture(): an in-memory, disk-free mutation of emit.Inputs


def _apply_mutation(record: dict[str, Any], mutate: MutateAction) -> dict[str, Any]:
    rec = copy.deepcopy(record)
    if mutate.set is not None:
        rec.update(copy.deepcopy(mutate.set))
    elif mutate.append_relates_to is not None:
        edges = list(rec.get("relates_to") or [])
        edges.append(dict(mutate.append_relates_to))
        rec["relates_to"] = edges
    elif mutate.delete:
        for field in mutate.delete:
            rec.pop(field, None)
    return rec


def apply_fixture(inputs: Inputs, fixture: Fixture) -> Inputs:
    """Return a new :class:`itpra_onto.emit.Inputs` with ``fixture``'s mutation applied. Never touches disk;
    ``inputs`` itself is left unmodified (every touched record is deep-copied first)."""
    action = fixture.action
    if isinstance(action, MutateAction):
        terms = list(inputs.terms)
        for index, term in enumerate(terms):
            if term.record.get("id") == action.id:
                terms[index] = TermRecord(record=_apply_mutation(term.record, action), file=term.file)
                return replace(inputs, terms=tuple(terms))

        requirements = list(inputs.requirements)
        for index, req in enumerate(requirements):
            if req.record.get("id") == action.id:
                requirements[index] = RegistryRecord(
                    record=_apply_mutation(req.record, action), file=req.file, registry=req.registry
                )
                return replace(inputs, requirements=tuple(requirements))

        raise FixtureError(f"{fixture.path}: mutate.id {action.id!r} matches no term or requirement record")

    record = copy.deepcopy(action.record)
    if action.file == "terms":
        terms = (*inputs.terms, TermRecord(record=record, file=SYNTHETIC_FILE))
        return replace(inputs, terms=terms)

    registry, _, _kind = action.file.removeprefix("registry:").partition("/")
    if not registry:
        raise FixtureError(f"{fixture.path}: add.file {action.file!r} names no registry")
    requirements = (*inputs.requirements, RegistryRecord(record=record, file=SYNTHETIC_FILE, registry=registry))
    return replace(inputs, requirements=requirements)


def _mutated_focus_id(fixture: Fixture) -> str:
    if isinstance(fixture.action, MutateAction):
        return fixture.action.id
    return str(fixture.action.record.get("id", fixture.focus))


# =====================================================================================================
# run_fixture() / assert_fixture()


@dataclass(frozen=True)
class Expectation:
    """What a fixture claims about the mutated data — ``run_fixture``'s second return value."""

    rule: str
    severity: str
    focus: str
    count: int
    emit_error: str | None = None
    cofires: tuple[str, ...] = ()


def run_fixture(
    fixture_path: Path, shapes_dir: Path, *, config: Config | None = None
) -> tuple[shacl.ValidationReport, Expectation]:
    """Load -> apply -> emit -> rules -> validate one fixture file; return ``(report, expected)``.

    An :class:`itpra_onto.emit.EmitError` raised by ``emit()`` on the mutated data (module docstring) is
    caught and turned into a single synthetic ``rule_id="emit-error"`` finding rather than propagating, so a
    fixture proving emit-time enforcement is asserted the same way as one proving a SHACL shape.
    """
    config = config if config is not None else load_config()
    fixture = load_fixture(fixture_path)
    expected = Expectation(
        rule=fixture.rule,
        severity=fixture.severity,
        focus=fixture.focus,
        count=fixture.count,
        emit_error=fixture.emit_error,
        cofires=fixture.cofires,
    )

    inputs = emit.load_inputs(config)
    mutated = apply_fixture(inputs, fixture)

    try:
        dataset = emit.emit(mutated, config)
    except emit.EmitError as exc:
        # The message carries the exception class name ("SourceGrammarError: ..."), so assert_fixture can
        # require the specific emit-time guard a fixture names (expect.emit_error).
        finding = shacl.emit_error_finding(exc, config, focus_id=_mutated_focus_id(fixture))
        report = shacl.ValidationReport(conforms=False, findings=(finding,), results_text=finding.message, graphs=())
        return report, expected

    dataset = rules.apply_rules(dataset, config).dataset
    shapes = shacl.load_shapes(shapes_dir, config=config)
    report = shacl.validate(dataset, shapes, config=config)
    return report, expected


@lru_cache(maxsize=None)
def _clean_report(shapes_dir_str: str, config: Config) -> shacl.ValidationReport:
    """The shapes under ``shapes_dir_str`` run over the real, unmutated corpus — memoised (cheap for the many
    fixtures one shape file's test module runs, since it depends only on ``shapes_dir``/``config``, not on
    any one fixture)."""
    inputs = emit.load_inputs(config)
    dataset = emit.emit(inputs, config)
    dataset = rules.apply_rules(dataset, config).dataset
    shapes = shacl.load_shapes(Path(shapes_dir_str), config=config)
    return shacl.validate(dataset, shapes, config=config)


def _format_findings(findings: Any) -> str:
    return "\n".join(f"  {f.severity:9} {f.rule_id!r:30} {f.focus!r:40} {f.message}" for f in findings) or "  (none)"


def assert_fixture(fixture_path: Path, shapes_dir: Path, *, config: Config | None = None) -> None:
    """Assert that ``fixture_path`` proves exactly its own rule: the expected rule fires with the expected
    severity on the expected focus exactly ``count`` times; no OTHER ``Violation``-severity rule fires on
    that same focus that did not already fire on clean data (a fixture proves one rule, not a cascade); and
    clean (unmutated) data raises zero findings of the fixture's own rule (otherwise the fixture proves
    nothing). Prints the full finding set on any failure.

    ``count: 0`` (a clean-case / defence-in-depth fixture — this module's own grammar docstring) skips the
    no-cascade check: the whole point of such a fixture is that its own rule stays silent under the given
    mutation, so whatever else the mutation does (or does not) trigger on the same focus is out of scope —
    there is no "one rule this fixture proves" to protect from a cascade. The "clean data raises zero
    findings of this rule" check still applies (a rule that already fires on the real corpus would make even
    a ``count: 0`` claim meaningless).
    """
    config = config if config is not None else load_config()
    fixture = load_fixture(fixture_path)
    report, expected = run_fixture(fixture_path, shapes_dir, config=config)

    def local(focus: str) -> str:
        return shacl.focus_local_name(focus, config)

    matching = [f for f in report.findings if finding_matches(f, fixture, config)]
    what = f" raised as {expected.emit_error}" if expected.emit_error else ""
    assert len(matching) == expected.count, (
        f"{fixture_path}: expected {expected.count} finding(s) of rule {expected.rule!r}{what} severity "
        f"{expected.severity!r} on focus {expected.focus!r}, got {len(matching)}. All findings:\n"
        f"{_format_findings(report.findings)}"
    )

    clean = _clean_report(str(shapes_dir), config)
    clean_same_rule = [f for f in clean.findings if f.rule_id == expected.rule]
    assert not clean_same_rule, (
        f"{fixture_path}: rule {expected.rule!r} already fires on CLEAN (unmutated) data — this fixture proves "
        f"nothing:\n{_format_findings(clean_same_rule)}"
    )

    if expected.count == 0:
        return  # clean-case / defence-in-depth fixture: no cascade to check (module docstring above)

    clean_violations_on_focus = {
        (f.rule_id, local(f.focus)) for f in clean.findings if f.severity == "Violation" and local(f.focus) == expected.focus
    }
    cascading = [
        f
        for f in report.findings
        if local(f.focus) == expected.focus
        and f.severity == "Violation"
        and f.rule_id != expected.rule
        and f.rule_id not in expected.cofires
        and (f.rule_id, local(f.focus)) not in clean_violations_on_focus
    ]
    assert not cascading, (
        f"{fixture_path}: mutation for {expected.rule!r} also triggered other Violation(s) on the same focus "
        f"not present on clean data (a fixture must prove ONE rule, not a cascade):\n{_format_findings(cascading)}"
    )
    # a declared co-firing rule must really co-fire: expect.cofires documents a fact, never a blanket waiver
    fired_on_focus = {f.rule_id for f in report.findings if local(f.focus) == expected.focus}
    silent = [rule for rule in expected.cofires if rule not in fired_on_focus]
    assert not silent, f"{fixture_path}: expect.cofires names {silent}, which did not fire on {expected.focus!r}"

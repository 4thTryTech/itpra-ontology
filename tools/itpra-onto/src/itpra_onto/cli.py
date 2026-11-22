"""Command-line entry point for the ITPRA ontology-as-code pipeline (``itpra-onto``).

Commands:

* ``gen-enums [--check]`` — the LinkML enums from the vocabulary's ``schema.yaml``.
* ``gen-prefixes [--check]`` — the ``itpra:``/``itpra-o:``/``itpra-g:`` prefixes generated from
  ``itpra-onto.toml`` [iri] (ADR 0004).
* ``gen-verb-shapes [--check]`` — rule B-22: ``shapes/generated/verb-pairs.ttl`` from the schema's
  ``itpra_verb`` annotations (see ``itpra_onto.gen_verb_shapes``).
* ``gen-artifacts [--check]`` — the derived schema artefacts (JSON Schema, Pydantic, OWL, SHACL, doc/) under
  ``dist/schema/``, canonicalised by this pipeline rather than by LinkML (ADR 0041 D5).
* ``validate --authoring`` — LinkML validation of the authored YAML.
* ``validate [--shapes DIR] [--json]`` — emit, apply the rules, and SHACL-validate the result against
  ``shapes/*.ttl`` (see ``itpra_onto.shacl``); exit 0 only when no ``sh:Violation`` fires (a ``sh:Warning``
  is advisory, ADR 0042 D3).
* ``build [--out DIR] [--no-store] [--check]`` — the canonical RDF output and the disposable Oxigraph store
  load (see ``itpra_onto.build``).
* ``parity [--json] [--fixtures] [--sub SUB ...]`` — compares the consumer's linter's ``--json`` findings
  with pySHACL's over the comparable (``core``/``sparql``) rule ids, either over the real tree (default) or
  fixture by fixture (``--fixtures``); exit 0 only when the symmetric difference (real tree) or the failure
  list (``--fixtures``) is empty (see ``itpra_onto.parity``; needs an ``[overlay]``).
* ``release`` — not implemented yet: it refuses while ``itpra-onto.toml``'s ``[iri] base`` has a reserved
  ``.invalid`` host (exit 1) and otherwise exits 2.

``validate`` and ``parity`` report an input the emitter refuses as an ``emit-error`` finding (exit 1), never
a traceback.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from itpra_onto.config import is_placeholder_base_iri, load_config

NOT_IMPLEMENTED_EXIT = 2
REFUSAL_EXIT = 1
CHECK_FAILED_EXIT = 1
VALIDATE_FAILED_EXIT = 1


def _print_build_report(report) -> None:  # noqa: ANN001 - itpra_onto.build.BuildReport, imported lazily
    print(f"build: wrote {report.out_dir}")
    print(f"build: {report.total_quads} quads total")
    for graph, count in sorted(report.graph_counts.items()):
        print(f"  {graph}: {count}")
    print("build: inferred rule counts:")
    for rule_id, count in report.inferred_counts.items():
        print(f"  {rule_id}: {count}")
    if report.store_quad_count is not None:
        print(f"build: store quad count: {report.store_quad_count}")
    print("build: elapsed seconds:")
    for phase, seconds in report.elapsed.items():
        print(f"  {phase}: {seconds:.3f}")


def _cmd_build(args: argparse.Namespace) -> int:
    from itpra_onto import build as build_module

    out_dir = Path(args.out) if args.out else None
    if args.check:
        diffs = build_module.check(out_dir=out_dir)
        if diffs:
            print(
                "build --check: dist/rdf/base is STALE or missing - run `itpra-onto build`",
                file=sys.stderr,
            )
            for line in diffs:
                print(f"  {line}", file=sys.stderr)
            return CHECK_FAILED_EXIT
        print("build --check: dist/rdf/base is up to date")
        return 0

    report = build_module.build(out_dir=out_dir, load_store=not args.no_store)
    _print_build_report(report)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    if args.authoring:
        # Imported lazily: linkml is slow to import and the other subcommands do not need it.
        from itpra_onto import authoring

        return authoring.run(quiet=args.quiet)

    # Imported lazily: pyshacl/rdflib are slow to import and the other subcommands do not need them.
    from itpra_onto import emit, rules, shacl

    config = load_config()
    shapes_dir = Path(args.shapes) if args.shapes else shacl.SHAPES_DIR

    try:
        inputs = emit.load_inputs(config)
        asserted = emit.emit(inputs, config)
    except emit.EmitError as exc:
        # An input the emitter refuses is a finding (rule `emit-error`, on the record the error names),
        # reported like any other and failing the run — never a traceback.
        finding = shacl.emit_error_finding(exc, config)
        report = shacl.ValidationReport(conforms=False, findings=(finding,), results_text=finding.message, graphs=())
    else:
        dataset = rules.apply_rules(asserted, config).dataset
        shapes = shacl.load_shapes(shapes_dir, config=config)
        report = shacl.validate(dataset, shapes, config=config)

    violations = sum(1 for f in report.findings if f.severity == "Violation")

    if args.json:
        payload = [
            {
                "rule": f.rule_id,
                "subject": shacl.focus_local_name(f.focus, config),
                "severity": shacl.SEVERITY_TO_LINTER.get(f.severity, f.severity.lower()),
                "message": f.message,
            }
            for f in sorted(report.findings, key=lambda f: (f.rule_id or "", shacl.focus_local_name(f.focus, config), f.severity))
        ]
        print(json.dumps(payload, ensure_ascii=False))
        return 0 if violations == 0 else VALIDATE_FAILED_EXIT

    rows = sorted(
        (f.severity, f.rule_id or "(no ruleId)", shacl.focus_local_name(f.focus, config), f.message) for f in report.findings
    )
    for severity, rule_id, focus, message in rows:
        print(f"{severity}  {rule_id}  {focus}  {message}")
    warnings = len(report.findings) - violations
    over = f"graphs [{', '.join(report.graphs)}]" if report.graphs else "no graph (the emitter refused the input)"
    print(f"validate: {len(report.findings)} finding(s) over {over} ({violations} violation(s), {warnings} warning(s))")
    return 0 if violations == 0 else VALIDATE_FAILED_EXIT


def _cmd_gen_enums(args: argparse.Namespace) -> int:
    from itpra_onto import gen_enums

    return gen_enums.main(check_only=args.check)


def _cmd_gen_prefixes(args: argparse.Namespace) -> int:
    from itpra_onto import gen_prefixes

    return gen_prefixes.main(check_only=args.check)


def _cmd_gen_verb_shapes(args: argparse.Namespace) -> int:
    from itpra_onto import gen_verb_shapes

    return gen_verb_shapes.main(check_only=args.check)


def _cmd_gen_artifacts(args: argparse.Namespace) -> int:
    from itpra_onto import gen_artifacts

    return gen_artifacts.main(check_only=args.check)


def _cmd_lint(args: argparse.Namespace) -> int:
    from itpra_onto import lint

    argv = ["--json"] if args.json else []
    if args.root:
        argv += ["--root", args.root]
    return lint.main(argv)


def _cmd_parity(args: argparse.Namespace) -> int:
    from itpra_onto import parity

    if args.fixtures:
        verdicts = parity.run_fixtures()
        failures = parity.fixture_failures(verdicts)
        if args.json:
            payload = {
                "fixture_count": len(verdicts),
                "verdicts": [parity.verdict_as_dict(v) for v in verdicts],
                "failures": [parity.verdict_as_dict(v) for v in failures],
            }
            print(json.dumps(payload, ensure_ascii=False))
        else:
            parity.print_fixture_report(verdicts)
        return 0 if not failures else VALIDATE_FAILED_EXIT

    comparison = parity.run_real_tree(subs=args.sub)
    if args.json:
        print(json.dumps(parity.comparison_as_dict(comparison), ensure_ascii=False))
    else:
        parity.print_report(comparison)
    return 0 if comparison.passed else VALIDATE_FAILED_EXIT


def _cmd_release(args: argparse.Namespace) -> int:
    config = load_config()
    if is_placeholder_base_iri(config.iri.base):
        print(
            "release: refusing to run - itpra-onto.toml's [iri] base has a reserved .invalid host "
            f"({config.iri.base!r}), a placeholder that is never published. Set [iri] base in "
            f"{config.config_path} to the real base IRI (ADR 0004) before running release.",
            file=sys.stderr,
        )
        return REFUSAL_EXIT
    print("release: not implemented yet")
    return NOT_IMPLEMENTED_EXIT


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="itpra-onto",
        description="itpra-onto: the ITPRA ontology-as-code pipeline (YAML -> LinkML -> RDF -> SHACL -> Oxigraph).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser(
        "build",
        help="emit RDF from the vocabulary and any configured registries, write dist/rdf/, load the disposable store",
    )
    build.add_argument("--out", metavar="DIR", help="write into DIR instead of dist/rdf/")
    build.add_argument("--no-store", action="store_true", help="skip loading the Oxigraph store")
    build.add_argument(
        "--check",
        action="store_true",
        help="build into a temp dir and exit 1 if dist/rdf/base/ would differ (never touches the store)",
    )
    build.set_defaults(func=_cmd_build)
    validate = subparsers.add_parser(
        "validate",
        help="--authoring: LinkML-validate the authored YAML; otherwise: SHACL-validate the "
        "emitted graph against shapes/*.ttl",
    )
    validate.add_argument(
        "--authoring",
        action="store_true",
        help="validate every term file of the vocabulary and every requirements registry against "
        "schema/itpra.linkml.yaml",
    )
    validate.add_argument("--quiet", action="store_true", help="with --authoring: print failing files only")
    validate.add_argument(
        "--shapes", metavar="DIR", help="load shape files from DIR instead of shapes/ (ignored with --authoring)"
    )
    validate.add_argument(
        "--json",
        action="store_true",
        help="print the findings as a JSON list (rule/subject/severity/message) and nothing else on stdout "
        "(ignored with --authoring)",
    )
    validate.set_defaults(func=_cmd_validate)
    gen = subparsers.add_parser(
        "gen-enums",
        help="generate schema/generated/itpra-enums.linkml.yaml from the vocabulary's schema.yaml",
    )
    gen.add_argument("--check", action="store_true", help="exit 1 if the committed generated file is stale")
    gen.set_defaults(func=_cmd_gen_enums)
    gen_prefixes = subparsers.add_parser(
        "gen-prefixes",
        help="generate schema/generated/itpra-prefixes.linkml.yaml (itpra:/itpra-o:/itpra-g:) from "
        "itpra-onto.toml [iri]",
    )
    gen_prefixes.add_argument("--check", action="store_true", help="exit 1 if the committed generated file is stale")
    gen_prefixes.set_defaults(func=_cmd_gen_prefixes)
    gen_verb_shapes = subparsers.add_parser(
        "gen-verb-shapes",
        help="generate shapes/generated/verb-pairs.ttl (rule B-22: verb domain/range) from the schema's "
        "itpra_verb annotations",
    )
    gen_verb_shapes.add_argument("--check", action="store_true", help="exit 1 if the committed generated file is stale")
    gen_verb_shapes.set_defaults(func=_cmd_gen_verb_shapes)
    gen_artifacts = subparsers.add_parser(
        "gen-artifacts",
        help="generate dist/schema/ (JSON Schema, Pydantic, OWL, SHACL, doc/) from the LinkML schema",
    )
    gen_artifacts.add_argument(
        "--check", action="store_true", help="exit 1 if dist/schema/ is stale or missing"
    )
    gen_artifacts.set_defaults(func=_cmd_gen_artifacts)
    lint = subparsers.add_parser(
        "lint",
        help="lint the vocabulary with the ontology's own rules (itpra_onto.lint; the register's core-home rows); "
        "exit 1 on any error",
    )
    lint.add_argument("--root", help="the vocabulary's directory (default: [paths] ontology_dir)")
    lint.add_argument("--json", action="store_true", help="emit the findings as JSON and nothing else on stdout")
    lint.set_defaults(func=_cmd_lint)
    parity = subparsers.add_parser(
        "parity",
        help="compare a linter's findings with pySHACL's over the comparable (core/sparql) rule ids: without an "
        "[overlay] the ontology's own lint over the core rules; with one, the consumer's linter ([overlay] "
        "linter_script) over every comparable rule — over the real tree (default) or fixture by fixture (--fixtures)",
    )
    parity.add_argument(
        "--fixtures",
        action="store_true",
        help="compare fixture by fixture (fixtures/**/*.yaml, expect.count >= 1) instead of the real tree; "
        "--sub is ignored in this mode",
    )
    parity.add_argument(
        "--sub",
        action="append",
        metavar="SUB",
        help="restrict the real-tree comparison to this registry (repeatable); default: every registry the "
        "overlay's requirements_glob matches (ignored with --fixtures)",
    )
    parity.add_argument(
        "--json",
        action="store_true",
        help="print the comparison as one JSON object and nothing else on stdout",
    )
    parity.set_defaults(func=_cmd_parity)
    subparsers.add_parser(
        "release", help="Publish the canonical RDF artefacts (not implemented yet; refuses a reserved .invalid host)"
    ).set_defaults(func=_cmd_release)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

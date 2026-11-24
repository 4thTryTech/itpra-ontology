"""Layers: graphs, rules and shapes built on top of the vocabulary's own (ADR 0043 D2).

A build takes the vocabulary and, optionally, one or more layers. A layer can add quads to the dataset once
the vocabulary is emitted, name a rules directory that runs after the vocabulary's rules, name a shapes
directory validated beside the vocabulary's shapes, and declare the files and code it is built from so that
the provenance record covers them. With no layer every function here returns what the vocabulary alone
gives.

A layer follows the pipeline's own conventions: its rules directory holds a ``manifest.yaml`` and ``.rq``
files exactly like ``rules/`` (constructed triples land in ``inferred``), its shapes directory holds
``.ttl`` files exactly like ``shapes/`` (no ``@prefix`` block, one named node per rule carrying
``itpra-o:ruleId``), and an input it cannot project is an :class:`itpra_onto.emit.EmitError`.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import pyoxigraph as ox

from itpra_onto import emit, rules
from itpra_onto.config import Config, load_config


class LayerError(RuntimeError):
    """A layer that cannot be combined with the vocabulary's build (e.g. a rule id used twice)."""


@dataclass(frozen=True)
class Layer:
    """One layer. Every part is optional.

    ``emit(dataset, config)`` adds quads to the emitted dataset in place, before any rule runs.
    ``input_files(config)`` lists the files the layer reads; they join the build's input hash and its
    ``prov:wasDerivedFrom`` list. ``rules_dir`` and ``shapes_dir`` are directories in the pipeline's own
    layout. ``code_dir`` is the layer's own source directory; its ``.py`` files join the code hash under the
    label ``<name>/<relative path>``.
    """

    name: str
    emit: Callable[[ox.Dataset, Config], None] | None = None
    input_files: Callable[[Config], Sequence[Path]] | None = None
    rules_dir: Path | None = None
    shapes_dir: Path | None = None
    code_dir: Path | None = None


@dataclass(frozen=True)
class Assembled:
    """The dataset a build writes and a validation reads: the asserted graphs plus ``inferred``."""

    inputs: emit.Inputs
    dataset: ox.Dataset
    rule_counts: dict[str, int]
    emit_seconds: float
    rules_seconds: float


def assemble(config: Config | None = None, layers: Sequence[Layer] = ()) -> Assembled:
    """Emit the vocabulary, let each layer add its quads, then run the vocabulary's rules followed by each
    layer's rules in the order given. Rule ids are unique across the vocabulary and every layer."""
    config = config if config is not None else load_config()

    started = time.perf_counter()
    inputs = emit.load_inputs(config)
    dataset = emit.emit(inputs, config)
    for layer in layers:
        if layer.emit is not None:
            layer.emit(dataset, config)
    emit_seconds = time.perf_counter() - started

    started = time.perf_counter()
    report = rules.apply_rules(dataset, config)
    dataset, counts = report.dataset, dict(report.counts)
    for layer in layers:
        if layer.rules_dir is None:
            continue
        more = rules.apply_rules(dataset, config, rules_dir=layer.rules_dir)
        clash = sorted(counts.keys() & more.counts.keys())
        if clash:
            raise LayerError(f"layer {layer.name!r}: rule id(s) {clash} are already in use")
        dataset = more.dataset
        counts.update(more.counts)
    rules_seconds = time.perf_counter() - started

    return Assembled(inputs=inputs, dataset=dataset, rule_counts=counts, emit_seconds=emit_seconds, rules_seconds=rules_seconds)


def input_files(config: Config, layers: Sequence[Layer] = ()) -> list[Path]:
    """Every file the layers read, in the order the layers list them."""
    return [Path(path) for layer in layers if layer.input_files is not None for path in layer.input_files(config)]


def shapes_dirs(layers: Sequence[Layer] = ()) -> list[Path]:
    return [layer.shapes_dir for layer in layers if layer.shapes_dir is not None]


def rules_version(config: Config, layers: Sequence[Layer] = ()) -> str:
    """The vocabulary's rules digest alone when no layer has rules; otherwise one digest over it and each
    layer's own, in order."""
    digests = [rules.rules_digest(config)]
    digests += [rules.rules_digest(config, rules_dir=layer.rules_dir) for layer in layers if layer.rules_dir is not None]
    if len(digests) == 1:
        return digests[0]
    return hashlib.sha256("\n".join(digests).encode("utf-8")).hexdigest()


def code_files(layers: Sequence[Layer] = ()) -> list[tuple[str, Path]]:
    """``(label, path)`` for every ``.py`` file under each layer's ``code_dir``, sorted by label."""
    out: list[tuple[str, Path]] = []
    for layer in layers:
        if layer.code_dir is None:
            continue
        root = Path(layer.code_dir).resolve()
        out += [(f"{layer.name}/{path.relative_to(root).as_posix()}", path) for path in root.rglob("*.py")]
    return sorted(out)

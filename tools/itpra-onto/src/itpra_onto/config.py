"""Configuration loading for the ITPRA ontology-as-code pipeline.

Reads ``itpra-onto.toml`` at the package root (or an explicit path override)
into a small read-only structure. The base IRI is **one configuration item
and is never hard-coded** anywhere in this package (ADR 0004). This module is
the single place that reads ``[iri] base`` (and the ``id_path`` /
``onto_path`` / ``graph_path`` it combines with); every other module reaches
the base IRI, or the derived namespace IRIs, through the :class:`Config` this
module returns — never by writing a literal IRI of its own. A config file
missing any ``[iri]`` key fails loudly (:class:`ConfigError`) rather than
silently falling back to a value baked into this module.

``[paths]`` locates the vocabulary and the output directories; an optional
``[overlay]`` names what a consumer layers on the vocabulary
(:class:`OverlayConfig`, ADR 0043 D1). :func:`is_placeholder_base_iri` is the
check ``itpra-onto release`` runs first: the shipped ``[iri] base`` is the
real base IRI (ADR 0004), and ``release`` refuses a base whose host is a
reserved ``.invalid`` name.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

CONFIG_FILENAME = "itpra-onto.toml"

# The file shipped beside a checkout's pyproject.toml (src/itpra_onto/config.py -> src/itpra_onto -> src ->
# the project). An installed package has no such file: a consumer keeps its own itpra-onto.toml in its
# overlay project and runs from there, or names it (see find_config_path).
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / CONFIG_FILENAME

# Names the configuration file explicitly; `itpra-onto --config PATH` sets it for one invocation.
CONFIG_PATH_ENV_VAR = "ITPRA_ONTO_CONFIG"


class ConfigError(RuntimeError):
    """Raised when ``itpra-onto.toml`` is missing a required key.

    The base IRI (and the paths it is built from) is a configuration item
    (ADR 0004): there is no built-in default to fall back to, so a missing
    key is a hard, explicit failure rather than a silently substituted
    literal.
    """


def _require(raw: dict, key: str, *, section: str, path: Path) -> str:
    try:
        return raw[key]
    except KeyError as exc:
        raise ConfigError(
            f"{path}: missing required [{section}] {key} — the base IRI and its shape are "
            "configuration items (ADR 0004) with no code default; set it in this file."
        ) from exc


@dataclass(frozen=True)
class IriConfig:
    base: str
    id_path: str
    onto_path: str
    graph_path: str

    @property
    def base_iri(self) -> str:
        """Alias of :attr:`base` (the name callers outside this module should read)."""
        return self.base

    @property
    def id_ns(self) -> str:
        """``<base><id_path>`` — one IRI per term/requirement record (ADR 0004)."""
        return self.base + self.id_path

    @property
    def onto_ns(self) -> str:
        """``<base><onto_path>`` — the schema vocabulary namespace (verb properties, etc.)."""
        return self.base + self.onto_path

    @property
    def graph_ns(self) -> str:
        """``<base><graph_path>`` — named graphs (``itpra-g:``)."""
        return self.base + self.graph_path

    def linkml_module_id(self, name: str) -> str:
        """``<base>linkml/<name>`` — the ``id:`` of a generated or hand-authored LinkML module.

        Used for ``schema/itpra.linkml.yaml`` (``name="itpra"``) and every
        ``schema/generated/itpra-*.linkml.yaml`` fragment, so no module's ``id:`` is a literal
        baked outside this config.
        """
        return f"{self.base}linkml/{name}"


@dataclass(frozen=True)
class PathsConfig:
    ontology_dir: str
    dist_dir: str
    store_dir: str
    repo_root: str = "../.."  # the consumer's repository root: every input lies under it, labels are relative to it


@dataclass(frozen=True)
class OverlayConfig:
    """What a *consumer* layers on the vocabulary (ADR 0043 D1): the requirement registries that become
    ``req/<X>`` graphs (``X`` is the first path component below the glob's fixed prefix), the consumer's own
    linter that ``parity`` compares the shapes against, and directory names the input-path guard refuses
    beyond the built-in ones. The core builds ``schema`` + ``t1`` + ``inferred`` from the vocabulary alone;
    everything that needs an overlay runs only when one is configured."""

    requirements_glob: str | None = None
    linter_script: str | None = None
    excluded_dirs: tuple[str, ...] = ()


@dataclass(frozen=True)
class PythonConfig:
    pinned: str


@dataclass(frozen=True)
class Config:
    iri: IriConfig
    paths: PathsConfig
    python: PythonConfig
    config_path: Path
    overlay: OverlayConfig | None = None

    @property
    def has_overlay(self) -> bool:
        return self.overlay is not None

    @property
    def repo_root(self) -> Path:
        """The repository root (``[paths] repo_root``, default two levels above the configuration file):
        the root every input must lie under (ADR 0043 D1) and the one file labels are made relative to."""
        return (self.config_path.parent / self.paths.repo_root).resolve()


def find_config_path() -> Path:
    """The configuration file in effect: ``ITPRA_ONTO_CONFIG`` when set; else ``itpra-onto.toml`` in the
    working directory or one of its parents (a consumer's overlay project); else the file shipped beside a
    checkout's ``pyproject.toml``. :class:`ConfigError` when none exists."""
    override = os.environ.get(CONFIG_PATH_ENV_VAR)
    if override:
        return Path(override)
    cwd = Path.cwd().resolve()
    for folder in (cwd, *cwd.parents):
        candidate = folder / CONFIG_FILENAME
        if candidate.is_file():
            return candidate
    if DEFAULT_CONFIG_PATH.is_file():
        return DEFAULT_CONFIG_PATH
    raise ConfigError(
        f"no {CONFIG_FILENAME} found: set {CONFIG_PATH_ENV_VAR}, pass --config, or run from a directory that holds one"
    )


def load_config(path: Path | str | None = None) -> Config:
    """Load ``itpra-onto.toml``.

    Without ``path`` the file is found by :func:`find_config_path` (the environment variable, the working
    directory and its parents, then the checkout's shipped file).

    Every ``[iri]`` key is required — there is no code-level default for the
    base IRI or the paths it is built from (ADR 0004); a missing key raises
    :class:`ConfigError` with the file and key named. ``[paths]`` and
    ``[python]`` have code defaults; ``[overlay]`` is optional and ``None``
    when absent.
    """
    config_path = Path(path) if path is not None else find_config_path()
    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    iri_raw = raw.get("iri", {})
    paths_raw = raw.get("paths", {})
    python_raw = raw.get("python", {})
    overlay_raw = raw.get("overlay")
    if overlay_raw is None and paths_raw.get("requirements_glob"):
        # Pre-split layout: `requirements_glob` under [paths] is read as an overlay with that one key.
        overlay_raw = {"requirements_glob": paths_raw["requirements_glob"]}
    overlay = (
        OverlayConfig(
            requirements_glob=overlay_raw.get("requirements_glob"),
            linter_script=overlay_raw.get("linter_script"),
            excluded_dirs=tuple(str(name) for name in overlay_raw.get("excluded_dirs", ())),
        )
        if isinstance(overlay_raw, dict)
        else None
    )

    return Config(
        iri=IriConfig(
            base=_require(iri_raw, "base", section="iri", path=config_path),
            id_path=_require(iri_raw, "id_path", section="iri", path=config_path),
            onto_path=_require(iri_raw, "onto_path", section="iri", path=config_path),
            graph_path=_require(iri_raw, "graph_path", section="iri", path=config_path),
        ),
        paths=PathsConfig(
            ontology_dir=paths_raw.get("ontology_dir", "../.."),
            dist_dir=paths_raw.get("dist_dir", "../../dist"),
            store_dir=paths_raw.get("store_dir", ".store"),
            repo_root=paths_raw.get("repo_root", "../.."),
        ),
        overlay=overlay,
        python=PythonConfig(pinned=python_raw.get("pinned", "3.12")),
        config_path=config_path,
    )


def is_placeholder_base_iri(base_iri: str) -> bool:
    """True when ``base_iri``'s host ends with ``.invalid``.

    ``.invalid`` is the RFC 2606 reserved TLD guaranteed to never resolve. The
    shipped ``itpra-onto.toml`` carries the real base IRI (ADR 0004); a
    ``.invalid`` host is a placeholder that is never published, and the
    ``release`` CLI subcommand calls this to refuse running against one. The
    tests exercise the refusal through a temporary config with such a host.
    """
    host = urlsplit(base_iri).hostname or ""
    return host.endswith(".invalid")

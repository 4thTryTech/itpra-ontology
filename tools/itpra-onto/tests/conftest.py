"""Shared test configuration: the `overlay` marker.

A test marked ``overlay`` needs what a consumer layers on the vocabulary (ADR 0043) — requirement registries
and the consumer's linter. When the configuration in use (``ITPRA_ONTO_CONFIG`` or the shipped
``itpra-onto.toml``) has no ``[overlay]``, those tests are skipped and the rest must pass on the vocabulary
alone — the core-only run.
"""
from __future__ import annotations

import pytest

from itpra_onto.config import load_config


def pytest_configure(config):
    config.addinivalue_line("markers", "overlay: needs the consumer overlay (registries, linter); skipped in a core-only run")


def pytest_collection_modifyitems(config, items):
    if load_config().overlay is not None:
        return
    skip = pytest.mark.skip(reason="core-only run: no [overlay] configured")
    for item in items:
        if "overlay" in item.keywords:
            item.add_marker(skip)

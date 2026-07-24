"""The complete, categorized application catalog."""

from __future__ import annotations

from collections.abc import Iterator

from workstation_setup.registry.apps import APP_REGISTRY
from workstation_setup.registry.ides import IDE_REGISTRY
from workstation_setup.registry.models import AppSpec

REGISTRIES: dict[str, list[AppSpec]] = {"apps": APP_REGISTRY, "ides": IDE_REGISTRY}


def all_specs() -> Iterator[AppSpec]:
    """Yield every app exactly once, grouped in its declared category order."""
    for registry in REGISTRIES.values():
        yield from registry

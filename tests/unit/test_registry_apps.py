import pytest
from factories import make_context

from workstation_setup.registry.apps import APP_REGISTRY
from workstation_setup.registry.ides import IDE_REGISTRY
from workstation_setup.registry.models import AppSpec

ALL_REGISTRIES = [("apps", APP_REGISTRY), ("ides", IDE_REGISTRY)]


@pytest.mark.parametrize("name,registry", ALL_REGISTRIES)
def test_registry_ids_are_unique(name, registry):
    ids = [spec.id for spec in registry]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("name,registry", ALL_REGISTRIES)
def test_every_entry_has_a_macos_install_method(name, registry):
    for spec in registry:
        assert isinstance(spec, AppSpec)
        assert spec.macos is not None
        assert spec.macos.kind in ("brew_cask", "brew_formula")


@pytest.mark.parametrize("name,registry", ALL_REGISTRIES)
def test_every_entry_has_at_least_one_linux_method(name, registry):
    for spec in registry:
        assert len(spec.linux) > 0


@pytest.mark.parametrize("name,registry", ALL_REGISTRIES)
def test_every_entry_check_is_callable_and_safe(name, registry):
    ctx = make_context()
    for spec in registry:
        # Should not raise even when nothing is actually installed on this machine.
        assert spec.check(ctx) in (True, False)


@pytest.mark.parametrize("name,registry", ALL_REGISTRIES)
def test_windsows_field_unused_in_v1(name, registry):
    for spec in registry:
        assert spec.windows is None

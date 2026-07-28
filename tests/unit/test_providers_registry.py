import pytest
from factories import make_os_info

from workstation_setup.errors import UnsupportedPlatformError
from workstation_setup.providers.apt import AptProvider
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.providers.dnf import DnfProvider
from workstation_setup.providers.pacman import PacmanProvider
from workstation_setup.providers.registry import get_brew_provider, get_system_provider
from workstation_setup.providers.winget import WingetProvider


def test_get_brew_provider_returns_brew():
    assert isinstance(get_brew_provider(), BrewProvider)


@pytest.mark.parametrize(
    "distro_family,expected_type",
    [("debian", AptProvider), ("fedora", DnfProvider), ("arch", PacmanProvider)],
)
def test_get_system_provider_picks_by_distro_family(distro_family, expected_type):
    os_info = make_os_info(distro_family=distro_family)

    assert isinstance(get_system_provider(os_info), expected_type)


def test_get_system_provider_raises_for_unknown_distro():
    os_info = make_os_info(distro_family="other")

    with pytest.raises(UnsupportedPlatformError):
        get_system_provider(os_info)


def test_get_system_provider_returns_winget_on_windows():
    os_info = make_os_info(family="windows", distro_family=None)

    assert isinstance(get_system_provider(os_info), WingetProvider)


def test_get_system_provider_raises_on_macos():
    os_info = make_os_info(family="macos", distro_family=None)

    with pytest.raises(UnsupportedPlatformError):
        get_system_provider(os_info)

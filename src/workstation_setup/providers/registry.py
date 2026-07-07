from __future__ import annotations

from workstation_setup.errors import UnsupportedPlatformError
from workstation_setup.os_detect import OSInfo
from workstation_setup.providers.apt import AptProvider
from workstation_setup.providers.base import PackageProvider
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.providers.dnf import DnfProvider
from workstation_setup.providers.pacman import PacmanProvider

_LINUX_PROVIDERS: dict[str, type[PackageProvider]] = {
    "debian": AptProvider,
    "fedora": DnfProvider,
    "arch": PacmanProvider,
}


def get_brew_provider() -> BrewProvider:
    """Homebrew is cross-family (macOS + Linuxbrew), so it's looked up
    independently of distro_family.
    """
    return BrewProvider()


def get_system_provider(os_info: OSInfo) -> PackageProvider:
    """The distro-native package manager, used as the fallback path for
    Linux GUI apps that have no Homebrew cask equivalent.
    """
    if os_info.family != "linux":
        raise UnsupportedPlatformError(
            f"No native system provider for {os_info.family!r}; use Homebrew instead"
        )

    provider_cls = _LINUX_PROVIDERS.get(os_info.distro_family or "other")
    if provider_cls is None:
        raise UnsupportedPlatformError(
            f"Unsupported Linux distro family: {os_info.distro_family!r}"
        )
    return provider_cls()

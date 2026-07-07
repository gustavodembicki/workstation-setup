from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from workstation_setup.context import RunContext


class PackageProvider(Protocol):
    """Abstracts a system package manager (brew, apt, dnf, pacman).

    Homebrew is the primary provider on both macOS and Linux (Linuxbrew);
    apt/dnf/pacman exist mainly for the native-package fallback path used to
    install Linux GUI apps that don't ship as Homebrew casks (casks are
    macOS-only).
    """

    name: str

    def is_available(self, ctx: RunContext) -> bool:
        """Whether this provider's binary is present on the system."""
        ...

    def is_installed(self, ctx: RunContext, package: str) -> bool: ...

    def install(self, ctx: RunContext, package: str, *, cask: bool = False) -> None: ...

    def list_installed(self, ctx: RunContext) -> set[str]: ...

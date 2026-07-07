from __future__ import annotations

from typing import TYPE_CHECKING

from workstation_setup.errors import UnsupportedPlatformError
from workstation_setup.exec import command_exists

if TYPE_CHECKING:
    from workstation_setup.context import RunContext


class DnfProvider:
    """Fedora/RHEL package manager. Used as the native-package fallback for
    Linux GUI apps that don't ship as Homebrew casks (casks are macOS-only).
    """

    name = "dnf"

    def is_available(self, ctx: RunContext) -> bool:
        return command_exists("dnf")

    def is_installed(self, ctx: RunContext, package: str) -> bool:
        result = ctx.run_command(["rpm", "-q", package], check=False)
        return result.ok

    def install(self, ctx: RunContext, package: str, *, cask: bool = False) -> None:
        if cask:
            raise UnsupportedPlatformError("dnf has no concept of a Homebrew cask")
        ctx.run_command(["sudo", "dnf", "install", "-y", package])

    def list_installed(self, ctx: RunContext) -> set[str]:
        result = ctx.run_command(["rpm", "-qa", "--qf", "%{NAME}\n"], check=False)
        return {line.strip() for line in result.stdout.splitlines() if line.strip()}

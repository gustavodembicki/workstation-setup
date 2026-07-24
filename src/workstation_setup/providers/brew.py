from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from workstation_setup.errors import UnsupportedPlatformError
from workstation_setup.exec import command_exists
from workstation_setup.os_detect import OSInfo

if TYPE_CHECKING:
    from workstation_setup.context import RunContext


def resolve_brew_binary(os_info: OSInfo) -> str:
    """The path Homebrew installs to, used to invoke `brew` in the same
    process right after installing it, before the shell's PATH has been
    reloaded to pick it up.
    """
    if os_info.family == "macos":
        return "/opt/homebrew/bin/brew" if os_info.arch == "arm64" else "/usr/local/bin/brew"
    if os_info.family == "linux":
        return "/home/linuxbrew/.linuxbrew/bin/brew"
    raise UnsupportedPlatformError("Homebrew is not supported on this platform")


def ensure_brew_on_path(os_info: OSInfo) -> None:
    """Prepend Homebrew's bin directory to this process's PATH so later
    steps that shell out to brew-installed binaries by bare name (zsh,
    asdf, git, gh, ...) can find them — even within the same wizard run
    that just installed Homebrew, before any shell rc file gets a chance
    to pick up the change.
    """
    try:
        # PurePosixPath, not Path: this is always a Unix-style install path
        # (Linux/macOS are the only supported targets), independent of the
        # OS this code happens to be running/tested on.
        brew_bin_dir = str(PurePosixPath(resolve_brew_binary(os_info)).parent)
    except UnsupportedPlatformError:
        return

    current_path = os.environ.get("PATH", "")
    if brew_bin_dir not in current_path.split(os.pathsep):
        os.environ["PATH"] = os.pathsep.join(filter(None, [brew_bin_dir, current_path]))


class BrewProvider:
    name = "brew"

    def _brew(self, ctx: RunContext) -> str:
        if command_exists("brew"):
            return "brew"
        return resolve_brew_binary(ctx.os_info)

    def is_available(self, ctx: RunContext) -> bool:
        if command_exists("brew"):
            return True
        try:
            return Path(resolve_brew_binary(ctx.os_info)).exists()
        except UnsupportedPlatformError:
            return False

    def is_installed(self, ctx: RunContext, package: str) -> bool:
        result = ctx.run_command([self._brew(ctx), "list", "--versions", package], check=False)
        return result.ok

    def install(self, ctx: RunContext, package: str, *, cask: bool = False) -> None:
        if cask and ctx.os_info.family != "macos":
            raise UnsupportedPlatformError(
                f"Homebrew casks are only supported on macOS (requested: {package})"
            )
        args = [self._brew(ctx), "install"]
        if cask:
            args.append("--cask")
        args.append(package)
        ctx.run_command(args, capture=False)

    def reinstall(self, ctx: RunContext, package: str, *, cask: bool = False) -> None:
        """Force a real reinstall — used when the user explicitly asks to
        reinstall something `is_installed` already reports as present.
        `brew install` on an already-installed package is a no-op, which
        isn't what "reinstall" means to the user.
        """
        if cask and ctx.os_info.family != "macos":
            raise UnsupportedPlatformError(
                f"Homebrew casks are only supported on macOS (requested: {package})"
            )
        args = [self._brew(ctx), "reinstall"]
        if cask:
            args.append("--cask")
        args.append(package)
        ctx.run_command(args, capture=False)

    def list_installed(self, ctx: RunContext) -> set[str]:
        result = ctx.run_command([self._brew(ctx), "list", "--versions"], check=False)
        return {line.split()[0] for line in result.stdout.splitlines() if line.strip()}

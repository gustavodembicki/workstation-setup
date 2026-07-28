from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from workstation_setup.context import RunContext

InstallKind = Literal[
    "brew_formula",
    "brew_cask",
    "apt_repo",
    "deb_download",
    "appimage",
    "tarball",
    "script",
    "winget",
]


@dataclass
class InstallMethod:
    kind: InstallKind
    identifier: str
    # None means "generic fallback, tried when no distro-specific entry matches".
    distro_family: str | None = None
    # Only used by kind="apt_repo": adds the vendor's repo/gpg key before `apt-get install`.
    repo_setup: Callable[[RunContext], None] | None = None


@dataclass
class AppSpec:
    """One installable app/IDE, data-driven so adding a new one is a single
    registry entry rather than a code change. Shared by both the GUI-apps
    checkbox and the IDE checkbox — only the screen they appear on differs.
    """

    id: str
    display_name: str
    check: Callable[[RunContext], bool]
    macos: InstallMethod
    linux: list[InstallMethod] = field(default_factory=list)
    windows: InstallMethod | None = None

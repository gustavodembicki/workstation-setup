from __future__ import annotations

from workstation_setup.exec import command_exists
from workstation_setup.registry.models import AppSpec, InstallMethod
from workstation_setup.registry.trustlist import TRUSTLIST

IDE_REGISTRY: list[AppSpec] = [
    AppSpec(
        id="jetbrains_toolbox",
        display_name="JetBrains Toolbox (installs/updates all JetBrains IDEs)",
        check=lambda ctx: command_exists("jetbrains-toolbox"),
        macos=InstallMethod("brew_cask", "jetbrains-toolbox"),
        linux=[
            InstallMethod(
                "tarball",
                TRUSTLIST["jetbrains_toolbox"].download_url,
            ),
        ],
        windows=InstallMethod("winget", "JetBrains.Toolbox"),
    ),
    AppSpec(
        id="vscode",
        display_name="VS Code",
        check=lambda ctx: command_exists("code"),
        macos=InstallMethod("brew_cask", "visual-studio-code"),
        linux=[
            InstallMethod(
                "deb_download",
                TRUSTLIST["vscode"].download_url,
                distro_family="debian",
            ),
        ],
        windows=InstallMethod("winget", "Microsoft.VisualStudioCode"),
    ),
    AppSpec(
        id="cursor",
        display_name="Cursor",
        check=lambda ctx: command_exists("cursor"),
        macos=InstallMethod("brew_cask", "cursor"),
        linux=[
            InstallMethod("appimage", TRUSTLIST["cursor"].download_url),
        ],
        windows=InstallMethod("winget", "Anysphere.Cursor"),
    ),
]

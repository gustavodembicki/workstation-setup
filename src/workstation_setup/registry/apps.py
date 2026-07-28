from __future__ import annotations

from workstation_setup.exec import command_exists
from workstation_setup.registry.models import AppSpec, InstallMethod
from workstation_setup.registry.trustlist import TRUSTLIST, apt_repo_setup

APP_REGISTRY: list[AppSpec] = [
    AppSpec(
        id="chrome",
        display_name="Google Chrome",
        check=lambda ctx: command_exists("google-chrome") or command_exists("google-chrome-stable"),
        macos=InstallMethod("brew_cask", "google-chrome"),
        linux=[
            InstallMethod(
                "apt_repo",
                "google-chrome-stable",
                distro_family="debian",
                repo_setup=apt_repo_setup(
                    TRUSTLIST["chrome"].gpg_key_url,
                    TRUSTLIST["chrome"].apt_repo_line,
                    "google-chrome",
                ),
            ),
        ],
        windows=InstallMethod("winget", "Google.Chrome"),
    ),
    AppSpec(
        id="spotify",
        display_name="Spotify",
        check=lambda ctx: command_exists("spotify"),
        macos=InstallMethod("brew_cask", "spotify"),
        linux=[
            InstallMethod(
                "apt_repo",
                "spotify-client",
                distro_family="debian",
                repo_setup=apt_repo_setup(
                    TRUSTLIST["spotify"].gpg_key_url,
                    TRUSTLIST["spotify"].apt_repo_line,
                    "spotify",
                ),
            ),
        ],
        windows=InstallMethod("winget", "Spotify.Spotify"),
    ),
    AppSpec(
        id="slack",
        display_name="Slack",
        check=lambda ctx: command_exists("slack"),
        macos=InstallMethod("brew_cask", "slack"),
        linux=[
            InstallMethod(
                "deb_download",
                TRUSTLIST["slack"].download_url,
                distro_family="debian",
            ),
        ],
        windows=InstallMethod("winget", "SlackTechnologies.Slack"),
    ),
    AppSpec(
        id="devin_desktop",
        display_name="Devin Desktop",
        check=lambda ctx: command_exists("devin"),
        macos=InstallMethod("brew_cask", "devin"),
        linux=[
            InstallMethod(
                "appimage",
                TRUSTLIST["devin_desktop"].download_url,
            ),
        ],
    ),
    AppSpec(
        id="gcloud_sdk",
        display_name="Google Cloud SDK",
        check=lambda ctx: command_exists("gcloud"),
        macos=InstallMethod("brew_cask", "google-cloud-sdk"),
        linux=[
            # Google's official cross-distro installer — works on debian, fedora,
            # arch, and anything else, so it doubles as the generic fallback.
            InstallMethod("script", TRUSTLIST["gcloud_sdk"].download_url),
        ],
        windows=InstallMethod("winget", "Google.CloudSDK"),
    ),
]

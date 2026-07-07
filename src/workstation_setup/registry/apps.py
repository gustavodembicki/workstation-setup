from __future__ import annotations

from workstation_setup.exec import command_exists
from workstation_setup.registry.models import AppSpec, InstallMethod

_CHROME_APT_REPO_SETUP_SCRIPT = (
    "curl -fsSL https://dl.google.com/linux/linux_signing_key.pub "
    "| sudo gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && "
    "echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] "
    "http://dl.google.com/linux/chrome/deb/ stable main' "
    "| sudo tee /etc/apt/sources.list.d/google-chrome.list"
)

_SPOTIFY_APT_REPO_SETUP_SCRIPT = (
    "curl -fsSL https://download.spotify.com/debian/pubkey_6224F9941A8AA6D1.gpg "
    "| sudo gpg --dearmor -o /usr/share/keyrings/spotify.gpg && "
    "echo 'deb [signed-by=/usr/share/keyrings/spotify.gpg] "
    "http://repository.spotify.com stable non-free' "
    "| sudo tee /etc/apt/sources.list.d/spotify.list"
)


def _chrome_repo_setup(ctx) -> None:
    ctx.run_command(["bash", "-c", _CHROME_APT_REPO_SETUP_SCRIPT])


def _spotify_repo_setup(ctx) -> None:
    ctx.run_command(["bash", "-c", _SPOTIFY_APT_REPO_SETUP_SCRIPT])


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
                repo_setup=_chrome_repo_setup,
            ),
        ],
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
                repo_setup=_spotify_repo_setup,
            ),
        ],
    ),
    AppSpec(
        id="slack",
        display_name="Slack",
        check=lambda ctx: command_exists("slack"),
        macos=InstallMethod("brew_cask", "slack"),
        linux=[
            InstallMethod(
                "deb_download",
                "https://downloads.slack-edge.com/desktop-releases/linux/x64/latest/slack-desktop-amd64.deb",
                distro_family="debian",
            ),
        ],
    ),
    AppSpec(
        id="devin_desktop",
        display_name="Devin Desktop",
        check=lambda ctx: command_exists("devin"),
        macos=InstallMethod("brew_cask", "devin"),
        linux=[
            InstallMethod(
                "appimage",
                "https://app.devin.ai/downloads/devin-desktop-linux-x86_64.AppImage",
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
            InstallMethod("script", "https://sdk.cloud.google.com"),
        ],
    ),
]

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workstation_setup.context import RunContext


@dataclass(frozen=True)
class AppLinks:
    """External URLs a single app trusts, all in one place for easy audit.

    Only the fields a given app needs are set; the rest stay None. Local
    filesystem paths (e.g. the keyring destination) are install mechanics,
    not a trust fact, so they don't live here.
    """

    download_url: str | None = None  # deb_download / appimage / tarball / script identifier
    gpg_key_url: str | None = None  # apt_repo only: key fetched before `gpg --dearmor`
    # apt_repo only: full `deb [...] <url> <suite> <component>` line
    apt_repo_line: str | None = None


TRUSTLIST: dict[str, AppLinks] = {
    "chrome": AppLinks(
        gpg_key_url="https://dl.google.com/linux/linux_signing_key.pub",
        apt_repo_line=(
            "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] "
            "http://dl.google.com/linux/chrome/deb/ stable main"
        ),
    ),
    "spotify": AppLinks(
        gpg_key_url="https://download.spotify.com/debian/pubkey_6224F9941A8AA6D1.gpg",
        apt_repo_line=(
            "deb [signed-by=/usr/share/keyrings/spotify.gpg] "
            "http://repository.spotify.com stable non-free"
        ),
    ),
    "slack": AppLinks(
        download_url=(
            "https://downloads.slack-edge.com/desktop-releases/linux/x64/latest/slack-desktop-amd64.deb"
        ),
    ),
    "devin_desktop": AppLinks(
        download_url="https://app.devin.ai/downloads/devin-desktop-linux-x86_64.AppImage",
    ),
    "gcloud_sdk": AppLinks(download_url="https://sdk.cloud.google.com"),
    "jetbrains_toolbox": AppLinks(
        download_url="https://data.services.jetbrains.com/products/download?code=TBA&platform=linux",
    ),
    "vscode": AppLinks(
        download_url="https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64",
    ),
    "windsurf": AppLinks(
        download_url="https://windsurf-stable.codeiumdata.com/linux-x64/stable/latest/Windsurf.deb",
    ),
    "cursor": AppLinks(download_url="https://downloader.cursor.sh/linux/appImage/x64"),
}


def apt_repo_setup(
    gpg_key_url: str, apt_repo_line: str, keyring_name: str
) -> Callable[[RunContext], None]:
    """Build a repo_setup closure for InstallMethod(kind="apt_repo", ...): fetches
    gpg_key_url, dearmors it into /usr/share/keyrings/{keyring_name}.gpg, and
    writes apt_repo_line as /etc/apt/sources.list.d/{keyring_name}.list.
    """
    keyring_path = f"/usr/share/keyrings/{keyring_name}.gpg"
    list_path = f"/etc/apt/sources.list.d/{keyring_name}.list"
    script = (
        f"curl -fsSL {gpg_key_url} | sudo gpg --dearmor -o {keyring_path} && "
        f"echo '{apt_repo_line}' | sudo tee {list_path}"
    )

    def _setup(ctx: RunContext) -> None:
        ctx.run_command(["bash", "-c", script])

    return _setup

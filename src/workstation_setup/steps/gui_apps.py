from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from workstation_setup import log
from workstation_setup.errors import UnsupportedPlatformError
from workstation_setup.providers.apt import AptProvider
from workstation_setup.providers.registry import get_brew_provider
from workstation_setup.registry.models import AppSpec, InstallMethod
from workstation_setup.steps.base import StepResult, StepStatus

if TYPE_CHECKING:
    from workstation_setup.context import RunContext

DOWNLOAD_DEB_PATH = "/tmp/workstation-setup-download.deb"
DOWNLOAD_TARBALL_PATH = "/tmp/workstation-setup-download.tar.gz"


def _pick_linux_method(ctx: RunContext, spec: AppSpec) -> InstallMethod | None:
    distro_specific = [m for m in spec.linux if m.distro_family == ctx.os_info.distro_family]
    if distro_specific:
        return distro_specific[0]
    generic = [m for m in spec.linux if m.distro_family is None]
    return generic[0] if generic else None


def _download(ctx: RunContext, url: str, dest: str) -> None:
    """Download with curl's own live progress bar streamed straight to the
    terminal (capture=False) instead of being silently buffered — a plain
    `-fsSL` capture makes a multi-hundred-MB download look like a hang.
    """
    log.note(f"Downloading {url}")
    ctx.run_command(["curl", "-fSL", "--progress-bar", "-o", dest, url], capture=False)


def _execute_install_method(
    ctx: RunContext, method: InstallMethod, *, reinstall: bool = False
) -> None:
    if method.kind == "brew_cask":
        if reinstall:
            get_brew_provider().reinstall(ctx, method.identifier, cask=True)
        else:
            get_brew_provider().install(ctx, method.identifier, cask=True)
    elif method.kind == "brew_formula":
        if reinstall:
            get_brew_provider().reinstall(ctx, method.identifier)
        else:
            get_brew_provider().install(ctx, method.identifier)
    elif method.kind == "apt_repo":
        # `reinstall` needs no special branch here: re-running the repo setup
        # + apt-get install is safe and is itself the "reinstall" action.
        if method.repo_setup:
            method.repo_setup(ctx)
        ctx.run_command(["sudo", "apt-get", "update"])
        AptProvider().install(ctx, method.identifier)
    elif method.kind == "deb_download":
        _download(ctx, method.identifier, DOWNLOAD_DEB_PATH)
        log.note("Installing package (dpkg)")
        result = ctx.run_command(["sudo", "dpkg", "-i", DOWNLOAD_DEB_PATH], check=False)
        if not result.ok:
            ctx.run_command(["sudo", "apt-get", "install", "-f", "-y"])
    elif method.kind == "appimage":
        dest_dir = Path.home() / "Applications"
        ctx.run_command(["mkdir", "-p", str(dest_dir)])
        dest = str(dest_dir / Path(method.identifier).name)
        _download(ctx, method.identifier, dest)
        ctx.run_command(["chmod", "+x", dest])
    elif method.kind == "tarball":
        _download(ctx, method.identifier, DOWNLOAD_TARBALL_PATH)
        log.note("Extracting archive to /opt")
        ctx.run_command(["sudo", "tar", "-xzf", DOWNLOAD_TARBALL_PATH, "-C", "/opt"])
    elif method.kind == "script":
        ctx.run_command(["bash", "-c", f"curl -fsSL {method.identifier} | bash"])
    else:
        raise UnsupportedPlatformError(f"Unknown install method kind: {method.kind}")


def install_app(ctx: RunContext, spec: AppSpec, *, reinstall: bool = False) -> StepResult:
    """Dispatch a single AppSpec's install per the current OS/distro. Shared
    by every `AppSpecStep` (IDEs and everyday apps alike) — they only differ
    in which registry they come from.
    """
    if ctx.os_info.family == "macos":
        _execute_install_method(ctx, spec.macos, reinstall=reinstall)
        return StepResult(StepStatus.INSTALLED)

    if ctx.os_info.family == "linux":
        method = _pick_linux_method(ctx, spec)
        if method is None:
            return StepResult(
                StepStatus.UNSUPPORTED,
                detail=f"no install method for {spec.display_name} on this distro",
            )
        _execute_install_method(ctx, method, reinstall=reinstall)
        return StepResult(StepStatus.INSTALLED)

    return StepResult(
        StepStatus.UNSUPPORTED, detail=f"{spec.display_name} not supported on {ctx.os_info.family}"
    )

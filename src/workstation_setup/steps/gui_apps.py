from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import questionary

from workstation_setup.errors import StepError, UnsupportedPlatformError
from workstation_setup.providers.apt import AptProvider
from workstation_setup.providers.registry import get_brew_provider
from workstation_setup.registry.apps import APP_REGISTRY
from workstation_setup.registry.models import AppSpec, InstallMethod
from workstation_setup.steps.base import Step, StepResult, StepStatus
from workstation_setup.ui import prompts

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
    ctx.console.print(f"  [cyan]Downloading[/cyan] {url}")
    ctx.run_command(["curl", "-fSL", "--progress-bar", "-o", dest, url], capture=False)


def _execute_install_method(ctx: RunContext, method: InstallMethod) -> None:
    if method.kind == "brew_cask":
        get_brew_provider().install(ctx, method.identifier, cask=True)
    elif method.kind == "brew_formula":
        get_brew_provider().install(ctx, method.identifier)
    elif method.kind == "apt_repo":
        if method.repo_setup:
            method.repo_setup(ctx)
        ctx.run_command(["sudo", "apt-get", "update"])
        AptProvider().install(ctx, method.identifier)
    elif method.kind == "deb_download":
        _download(ctx, method.identifier, DOWNLOAD_DEB_PATH)
        ctx.console.print("  [cyan]Installing[/cyan] package (dpkg)")
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
        ctx.console.print("  [cyan]Extracting[/cyan] archive to /opt")
        ctx.run_command(["sudo", "tar", "-xzf", DOWNLOAD_TARBALL_PATH, "-C", "/opt"])
    elif method.kind == "script":
        ctx.run_command(["bash", "-c", f"curl -fsSL {method.identifier} | bash"])
    else:
        raise UnsupportedPlatformError(f"Unknown install method kind: {method.kind}")


def install_app(ctx: RunContext, spec: AppSpec) -> StepResult:
    """Dispatch a single AppSpec's install per the current OS/distro. Shared
    by both the GUI-apps step and the IDE step — they only differ in which
    checkbox screen the entries show up on.
    """
    if ctx.os_info.family == "macos":
        _execute_install_method(ctx, spec.macos)
        return StepResult(StepStatus.INSTALLED)

    if ctx.os_info.family == "linux":
        method = _pick_linux_method(ctx, spec)
        if method is None:
            return StepResult(
                StepStatus.UNSUPPORTED,
                detail=f"no install method for {spec.display_name} on this distro",
            )
        _execute_install_method(ctx, method)
        return StepResult(StepStatus.INSTALLED)

    return StepResult(
        StepStatus.UNSUPPORTED, detail=f"{spec.display_name} not supported on {ctx.os_info.family}"
    )


def run_selection_step(ctx: RunContext, title: str, registry: list[AppSpec]) -> StepResult:
    choices = [
        questionary.Choice(
            title=f"{spec.display_name}{' (already installed)' if spec.check(ctx) else ''}",
            value=spec.id,
            checked=spec.check(ctx),
        )
        for spec in registry
    ]
    selected_ids = set(prompts.checkbox_select(f"Select {title.lower()} to install:", choices))

    installed, failed, unsupported = [], [], []
    for spec in registry:
        if spec.id not in selected_ids:
            continue
        ctx.console.print(f"\n[bold]-> {spec.display_name}[/bold]")
        try:
            result = install_app(ctx, spec)
        except StepError as error:
            reason = str(error) + (f": {error.stderr}" if error.stderr else "")
            ctx.console.print(f"[red]x {spec.display_name} failed - {reason}[/red]")
            failed.append(f"{spec.display_name} ({reason})")
            continue
        except Exception as error:  # unexpected failure (fs/permissions/etc.), not just StepError
            ctx.console.print(f"[red]x {spec.display_name} failed unexpectedly - {error}[/red]")
            failed.append(f"{spec.display_name} ({error})")
            continue

        if result.status == StepStatus.UNSUPPORTED:
            ctx.console.print(f"[yellow]! {spec.display_name} unsupported here[/yellow]")
            unsupported.append(spec.display_name)
        else:
            ctx.console.print(f"[green]OK {spec.display_name} installed[/green]")
            installed.append(spec.display_name)

    if not selected_ids:
        return StepResult(StepStatus.SKIPPED_BY_USER, detail="nothing selected")

    detail_parts = [f"installed: {', '.join(installed) or 'none'}"]
    if failed:
        detail_parts.append(f"failed: {', '.join(failed)}")
    if unsupported:
        detail_parts.append(f"unsupported: {', '.join(unsupported)}")

    status = StepStatus.INSTALLED if installed and not failed else StepStatus.PARTIAL
    return StepResult(status, detail="; ".join(detail_parts))


class GuiAppsSelectionStep(Step):
    id = "gui-apps"
    title = "Everyday apps"
    description = (
        "Pick everyday apps to install: Chrome, Slack, Spotify, GCloud SDK, Devin Desktop."
    )

    def check_installed(self, ctx: RunContext) -> StepStatus:
        # Always offered — re-running lets the user add apps they skipped before.
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext) -> StepResult:
        return run_selection_step(ctx, self.title, APP_REGISTRY)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return [f"Prompt to select from: {', '.join(s.display_name for s in APP_REGISTRY)}"]

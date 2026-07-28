from __future__ import annotations

from typing import TYPE_CHECKING

from workstation_setup.providers.winget import WingetProvider
from workstation_setup.registry.models import AppSpec, InstallMethod
from workstation_setup.steps.base import Step, StepResult, StepStatus
from workstation_setup.steps.gui_apps import _pick_linux_method, install_app

if TYPE_CHECKING:
    from workstation_setup.context import RunContext

_PREVIEW_BY_KIND = {
    "brew_cask": lambda m: f"brew install --cask {m.identifier}",
    "brew_formula": lambda m: f"brew install {m.identifier}",
    "apt_repo": lambda m: f"add vendor apt repo, then apt-get install {m.identifier}",
    "deb_download": lambda m: f"download {m.identifier} and dpkg -i it",
    "appimage": lambda m: f"download {m.identifier} to ~/Applications",
    "tarball": lambda m: f"download {m.identifier} and extract it to /opt",
    "script": lambda m: f"curl -fsSL {m.identifier} | bash",
    "winget": lambda m: f"winget install --id {m.identifier} --exact --source winget",
}


def _describe_method(method: InstallMethod) -> str:
    describe = _PREVIEW_BY_KIND.get(method.kind)
    return describe(method) if describe else f"unknown install method kind: {method.kind}"


class AppSpecStep(Step):
    """Adapts a data-driven `AppSpec` (registry/apps.py, registry/ides.py) to
    the `Step` interface so it can sit in the same flat menu as Homebrew,
    zsh, asdf, etc. — one entry per app/IDE, not one step per checkbox
    screen.
    """

    def __init__(self, spec: AppSpec) -> None:
        self.spec = spec
        self.id = spec.id
        self.title = spec.display_name
        self.description = f"Install {spec.display_name}."

    def is_applicable(self, ctx: RunContext) -> bool:
        if ctx.os_info.family == "windows":
            return self.spec.windows is not None
        return True

    def check_installed(self, ctx: RunContext) -> StepStatus:
        if ctx.os_info.family == "windows" and self.spec.windows is not None:
            installed = WingetProvider().is_installed(ctx, self.spec.windows.identifier)
            return StepStatus.ALREADY_INSTALLED if installed else StepStatus.NOT_INSTALLED
        if self.spec.check(ctx):
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        return install_app(ctx, self.spec, reinstall=reinstall)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        if ctx.os_info.family == "macos":
            return [_describe_method(self.spec.macos)]
        if ctx.os_info.family == "linux":
            method = _pick_linux_method(ctx, self.spec)
            if method is None:
                return [f"No install method for {self.spec.display_name} on this distro"]
            return [_describe_method(method)]
        if ctx.os_info.family == "windows" and self.spec.windows is not None:
            return [_describe_method(self.spec.windows)]
        return [f"{self.spec.display_name} not supported on {ctx.os_info.family}"]

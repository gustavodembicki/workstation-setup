from __future__ import annotations

from typing import TYPE_CHECKING

from workstation_setup.exec import command_exists
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.providers.winget import WingetProvider
from workstation_setup.steps.base import Step, StepResult, StepStatus

if TYPE_CHECKING:
    from workstation_setup.context import RunContext


class InstallGitStep(Step):
    id = "git"
    title = "git"
    description = "Install a modern Git version through the platform package manager."

    def check_installed(self, ctx: RunContext) -> StepStatus:
        if ctx.os_info.family == "windows":
            installed = WingetProvider().is_installed(ctx, "Git.Git")
            return StepStatus.ALREADY_INSTALLED if installed else StepStatus.NOT_INSTALLED
        if command_exists("git"):
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        if ctx.os_info.family == "windows":
            provider = WingetProvider()
            if reinstall:
                provider.reinstall(ctx, "Git.Git")
            else:
                provider.install(ctx, "Git.Git")
            return StepResult(StepStatus.INSTALLED)
        if reinstall:
            BrewProvider().reinstall(ctx, "git")
        else:
            BrewProvider().install(ctx, "git")
        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        if ctx.os_info.family == "windows":
            return ["winget install --id Git.Git --exact --source winget"]
        return ["brew install git"]


class InstallGhStep(Step):
    id = "gh"
    title = "GitHub CLI (gh)"
    description = "Install the GitHub CLI through the platform package manager."

    def check_installed(self, ctx: RunContext) -> StepStatus:
        if ctx.os_info.family == "windows":
            installed = WingetProvider().is_installed(ctx, "GitHub.cli")
            return StepStatus.ALREADY_INSTALLED if installed else StepStatus.NOT_INSTALLED
        if command_exists("gh"):
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        if ctx.os_info.family == "windows":
            provider = WingetProvider()
            if reinstall:
                provider.reinstall(ctx, "GitHub.cli")
            else:
                provider.install(ctx, "GitHub.cli")
            return StepResult(StepStatus.INSTALLED)
        if reinstall:
            BrewProvider().reinstall(ctx, "gh")
        else:
            BrewProvider().install(ctx, "gh")
        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        if ctx.os_info.family == "windows":
            return ["winget install --id GitHub.cli --exact --source winget"]
        return ["brew install gh"]


class GhAuthLoginStep(Step):
    id = "gh-auth-login"
    title = "GitHub CLI authentication"
    description = "Authenticate the GitHub CLI (opens a browser or shows a device code)."

    def is_applicable(self, ctx: RunContext) -> bool:
        return command_exists("gh")

    def check_installed(self, ctx: RunContext) -> StepStatus:
        result = ctx.run_command(["gh", "auth", "status"], check=False)
        ctx.selections["gh_authenticated"] = result.ok
        if result.ok:
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        # Genuinely interactive (opens a browser / shows a device code), so
        # stdout/stderr must attach to the real terminal, not be captured.
        # Re-running is itself the "modify" action (re-authenticate), so
        # `reinstall` needs no separate branch.
        ctx.run_command(["gh", "auth", "login"], capture=False)
        ctx.selections["gh_authenticated"] = True
        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return ["gh auth login (interactive)"]

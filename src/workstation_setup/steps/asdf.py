from __future__ import annotations

from typing import TYPE_CHECKING

import questionary

from workstation_setup.errors import StepError
from workstation_setup.exec import command_exists
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.steps.base import Step, StepResult, StepStatus
from workstation_setup.ui import prompts

if TYPE_CHECKING:
    from workstation_setup.context import RunContext

CURATED_PLUGINS = ["nodejs", "python", "erlang", "elixir", "ruby", "golang"]
OTHER_CHOICE = "__other__"
ALREADY_ADDED_MARKER = "already added"


def _is_unix(ctx: RunContext) -> bool:
    return ctx.os_info.family in ("linux", "macos")


class InstallAsdfStep(Step):
    id = "asdf"
    title = "asdf"
    description = "Install the asdf version manager via Homebrew."

    def is_applicable(self, ctx: RunContext) -> bool:
        return _is_unix(ctx)

    def check_installed(self, ctx: RunContext) -> StepStatus:
        if command_exists("asdf"):
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        if reinstall:
            BrewProvider().reinstall(ctx, "asdf")
        else:
            BrewProvider().install(ctx, "asdf")
        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return ["brew install asdf"]


class AsdfPluginsStep(Step):
    id = "asdf-plugins"
    title = "asdf plugins"
    description = "Add asdf plugins for the language runtimes you use."

    def is_applicable(self, ctx: RunContext) -> bool:
        return _is_unix(ctx) and command_exists("asdf")

    def check_installed(self, ctx: RunContext) -> StepStatus:
        # Always offered — picking no plugins is a valid, repeatable no-op.
        return StepStatus.NOT_INSTALLED

    def _select_plugins(self) -> list[str]:
        choices = [questionary.Choice(title=name, value=name) for name in CURATED_PLUGINS]
        choices.append(questionary.Choice(title="Other (type plugin name(s))", value=OTHER_CHOICE))
        selected = prompts.checkbox_select("Which asdf plugins do you want to add?", choices)

        plugins = [name for name in selected if name != OTHER_CHOICE]
        if OTHER_CHOICE in selected:
            typed = prompts.text_input("Enter additional plugin name(s), comma-separated:")
            plugins += [name.strip() for name in typed.split(",") if name.strip()]
        return plugins

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        # Always "modify" — re-running re-opens the plugin picker so the
        # user can add more, so `reinstall` needs no separate branch.
        plugins = self._select_plugins()
        if not plugins:
            return StepResult(StepStatus.SKIPPED_BY_USER, detail="no plugins selected")

        added, failed = [], []
        for plugin in plugins:
            result = ctx.run_command(["asdf", "plugin", "add", plugin], check=False)
            if result.ok or ALREADY_ADDED_MARKER in result.stderr.lower():
                added.append(plugin)
            else:
                failed.append(plugin)

        if not added:
            raise StepError(f"Failed to add plugins: {', '.join(failed)}")
        if failed:
            detail = f"added: {', '.join(added)}; failed: {', '.join(failed)}"
            return StepResult(StepStatus.PARTIAL, detail=detail)
        return StepResult(StepStatus.INSTALLED, detail=", ".join(added))

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return ["Prompt for asdf plugins to add, then `asdf plugin add <name>` for each"]

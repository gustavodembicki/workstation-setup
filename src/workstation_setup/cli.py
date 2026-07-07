import sys

import click
from rich.console import Console

from workstation_setup import __version__, wizard
from workstation_setup.context import RunContext
from workstation_setup.errors import AbortError
from workstation_setup.exec import SubprocessRunner
from workstation_setup.os_detect import detect_os
from workstation_setup.providers.brew import ensure_brew_on_path
from workstation_setup.state import load_state, save_state
from workstation_setup.steps.asdf import AsdfPluginsStep, InstallAsdfStep
from workstation_setup.steps.base import Step
from workstation_setup.steps.git_gh import GhAuthLoginStep, InstallGhStep, InstallGitStep
from workstation_setup.steps.gui_apps import GuiAppsSelectionStep
from workstation_setup.steps.homebrew import InstallHomebrewStep
from workstation_setup.steps.ides import IdeSelectionStep
from workstation_setup.steps.shell import (
    ConfigureZshThemeStep,
    InstallOhMyZshStep,
    InstallZshStep,
    SetDefaultShellStep,
)
from workstation_setup.steps.ssh import GenerateSshKeyStep

STEP_PIPELINE: list[Step] = [
    InstallHomebrewStep(),
    InstallZshStep(),
    InstallOhMyZshStep(),
    ConfigureZshThemeStep(),
    SetDefaultShellStep(),
    InstallAsdfStep(),
    AsdfPluginsStep(),
    InstallGitStep(),
    InstallGhStep(),
    GhAuthLoginStep(),
    GenerateSshKeyStep(),
    IdeSelectionStep(),
    GuiAppsSelectionStep(),
]


@click.command()
@click.option("--dry-run", is_flag=True, help="Preview what would happen, install nothing.")
@click.option("--yes", "-y", "assume_yes", is_flag=True, help="Assume yes for every prompt.")
@click.option("--only", multiple=True, help="Only run the given step id(s).")
@click.option("--skip", multiple=True, help="Skip the given step id(s).")
@click.version_option(version=__version__, prog_name="workstation-setup")
def main(dry_run: bool, assume_yes: bool, only: tuple[str, ...], skip: tuple[str, ...]) -> None:
    """Bootstrap a fresh developer workstation."""
    console = Console()
    os_info = detect_os()

    if os_info.family not in ("linux", "macos"):
        console.print(
            f"[red]workstation-setup does not support {os_info.family} yet "
            "- only Linux and macOS are supported.[/red]"
        )
        sys.exit(1)

    # Covers the case where Homebrew was already installed in a previous run —
    # its bin dir may still be missing from this process's PATH.
    ensure_brew_on_path(os_info)

    state = load_state()

    steps = STEP_PIPELINE
    if only:
        steps = [s for s in steps if s.id in only]
    if skip:
        steps = [s for s in steps if s.id not in skip]

    ctx = RunContext(
        os_info=os_info,
        console=console,
        runner=SubprocessRunner(),
        state=state,
        dry_run=dry_run,
        assume_yes=assume_yes,
    )

    try:
        wizard.run(ctx, steps)
    except AbortError as error:
        console.print(f"[red]{error}[/red]")
        save_state(ctx.state)
        sys.exit(1)

    save_state(ctx.state)


if __name__ == "__main__":
    main()

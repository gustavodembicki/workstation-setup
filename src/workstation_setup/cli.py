import sys

import click
from rich.console import Console

from workstation_setup import __version__, wizard
from workstation_setup.context import RunContext
from workstation_setup.errors import AbortError
from workstation_setup.exec import SubprocessRunner
from workstation_setup.os_detect import detect_os
from workstation_setup.providers.brew import ensure_brew_on_path
from workstation_setup.registry.apps import APP_REGISTRY
from workstation_setup.registry.ides import IDE_REGISTRY
from workstation_setup.state import load_state, save_state
from workstation_setup.steps.app_spec_step import AppSpecStep
from workstation_setup.steps.asdf import AsdfPluginsStep, InstallAsdfStep
from workstation_setup.steps.base import Step
from workstation_setup.steps.git_gh import GhAuthLoginStep, InstallGhStep, InstallGitStep
from workstation_setup.steps.homebrew import InstallHomebrewStep
from workstation_setup.steps.shell import (
    ConfigureZshThemeStep,
    InstallOhMyZshStep,
    InstallZshStep,
    SetDefaultShellStep,
)
from workstation_setup.steps.ssh import GenerateSshKeyStep
from workstation_setup.ui import prompts
from workstation_setup.ui.console import print_welcome

# The recommended initial bootstrap, in the order it's made sense to run in
# since v1: Homebrew before anything that installs via it, gh before the SSH
# key step that offers to register it. Nothing here is mandatory anymore —
# it's just a convenience fast path, offered up front, into the same items
# that also live in MASTER_REGISTRY below.
RECOMMENDED_PIPELINE: list[Step] = [
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
]

# Every single installable thing, flattened into one list — no separate
# "selection steps" for IDEs/apps. Nothing here is required; it's a menu of
# possibilities, not a pipeline.
MASTER_REGISTRY: list[Step] = [
    *RECOMMENDED_PIPELINE,
    *(AppSpecStep(spec) for spec in IDE_REGISTRY),
    *(AppSpecStep(spec) for spec in APP_REGISTRY),
]


def _filter_steps(steps: list[Step], *, only: tuple[str, ...], skip: tuple[str, ...]) -> list[Step]:
    result = steps
    if only:
        result = [s for s in result if s.id in only]
    if skip:
        result = [s for s in result if s.id not in skip]
    return result


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

    recommended_steps = _filter_steps(RECOMMENDED_PIPELINE, only=only, skip=skip)
    menu_steps = _filter_steps(MASTER_REGISTRY, only=only, skip=skip)

    ctx = RunContext(
        os_info=os_info,
        console=console,
        runner=SubprocessRunner(),
        state=state,
        dry_run=dry_run,
        assume_yes=assume_yes,
    )

    print_welcome(console, f"{ctx.os_info.family} ({ctx.os_info.distro_name or ''})")

    try:
        if assume_yes:
            if only:
                # Targeted, unattended automation: run just the requested
                # id(s) directly. run_recommended never blocks on a prompt
                # when ctx.assume_yes is set (an already-installed match is
                # left as is, same as historical --yes behavior).
                wizard.run_recommended(ctx, menu_steps)
            else:
                console.print(
                    "[yellow]--yes with no --only given: nothing to run — the big "
                    "menu of possibilities has no interactive session to pick from. "
                    "Pass --only <id> to run something specific unattended.[/yellow]"
                )
        else:
            run_bootstrap = bool(recommended_steps) and prompts.confirm_step(
                "Run the recommended initial bootstrap first? "
                "(Homebrew, zsh + Oh My Zsh + theme, default shell, asdf + plugins, "
                "git, GitHub CLI + auth, SSH key)",
                default=True,
            )
            if run_bootstrap:
                wizard.run_recommended(ctx, recommended_steps)

            wizard.run_menu(ctx, menu_steps)
    except AbortError as error:
        console.print(f"[red]{error}[/red]")
        save_state(ctx.state)
        sys.exit(1)

    save_state(ctx.state)


if __name__ == "__main__":
    main()

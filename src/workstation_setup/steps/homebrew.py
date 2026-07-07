from __future__ import annotations

import os
from typing import TYPE_CHECKING

from workstation_setup.providers.brew import BrewProvider, ensure_brew_on_path
from workstation_setup.steps.base import Step, StepResult, StepStatus

if TYPE_CHECKING:
    from workstation_setup.context import RunContext

INSTALL_SCRIPT_URL = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"


class InstallHomebrewStep(Step):
    id = "homebrew"
    title = "Homebrew"
    description = (
        "Install Homebrew, the primary package manager used by this tool "
        "on both macOS and Linux (Linuxbrew)."
    )

    def check_installed(self, ctx: RunContext) -> StepStatus:
        if BrewProvider().is_available(ctx):
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext) -> StepResult:
        # `bash -c "$(curl ...)"` only works when an outer shell performs the
        # substitution before bash starts; invoked directly via subprocess
        # (no outer shell), bash instead word-splits the fetched script into
        # a single bogus command. Piping avoids that gotcha entirely.
        ctx.run_command(
            ["/bin/bash", "-c", f"curl -fsSL {INSTALL_SCRIPT_URL} | bash"],
            env={**os.environ, "NONINTERACTIVE": "1"},
        )
        ensure_brew_on_path(ctx.os_info)
        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return [
            f"Run the official Homebrew install script ({INSTALL_SCRIPT_URL}) "
            "with NONINTERACTIVE=1"
        ]

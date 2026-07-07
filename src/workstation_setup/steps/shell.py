from __future__ import annotations

import os
import shutil
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from workstation_setup.exec import command_exists
from workstation_setup.providers.brew import BrewProvider, resolve_brew_binary
from workstation_setup.steps.base import Step, StepResult, StepStatus

if TYPE_CHECKING:
    from workstation_setup.context import RunContext

OH_MY_ZSH_INSTALL_URL = "https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh"
P10K_SOURCE_LINE = "source $(brew --prefix)/share/powerlevel10k/powerlevel10k.zsh-theme"
SHELLS_FILE = Path("/etc/shells")


class InstallZshStep(Step):
    id = "zsh"
    title = "zsh"
    description = "Install zsh via Homebrew."

    def check_installed(self, ctx: RunContext) -> StepStatus:
        if command_exists("zsh"):
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext) -> StepResult:
        BrewProvider().install(ctx, "zsh")
        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return ["brew install zsh"]


class InstallOhMyZshStep(Step):
    id = "oh-my-zsh"
    title = "Oh My Zsh"
    description = "Install the Oh My Zsh framework for zsh configuration."

    def check_installed(self, ctx: RunContext) -> StepStatus:
        if (Path.home() / ".oh-my-zsh").exists():
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext) -> StepResult:
        # See InstallHomebrewStep.run for why this pipes rather than using
        # `bash -c "$(curl ...)"` (word-splitting gotcha with no outer shell).
        ctx.run_command(
            ["/bin/bash", "-c", f"curl -fsSL {OH_MY_ZSH_INSTALL_URL} | bash"],
            env={**os.environ, "RUNZSH": "no", "CHSH": "no", "KEEP_ZSHRC": "yes"},
        )
        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return [f"Run the Oh My Zsh install script ({OH_MY_ZSH_INSTALL_URL}) non-interactively"]


class InstallPowerlevel10kStep(Step):
    id = "powerlevel10k"
    title = "Powerlevel10k theme"
    description = "Install the Powerlevel10k zsh theme via Homebrew and wire it into ~/.zshrc."

    def _zshrc(self) -> Path:
        return Path.home() / ".zshrc"

    def check_installed(self, ctx: RunContext) -> StepStatus:
        zshrc = self._zshrc()
        theme_wired = zshrc.exists() and P10K_SOURCE_LINE in zshrc.read_text()
        if BrewProvider().is_installed(ctx, "powerlevel10k") and theme_wired:
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext) -> StepResult:
        BrewProvider().install(ctx, "powerlevel10k")
        zshrc = self._zshrc()
        contents = zshrc.read_text() if zshrc.exists() else ""
        if P10K_SOURCE_LINE not in contents:
            with zshrc.open("a") as f:
                if contents and not contents.endswith("\n"):
                    f.write("\n")
                f.write(P10K_SOURCE_LINE + "\n")
        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return [
            "brew install powerlevel10k",
            f"Append '{P10K_SOURCE_LINE}' to ~/.zshrc if missing",
        ]


class SetDefaultShellStep(Step):
    id = "set-default-shell"
    title = "Set zsh as default shell"
    description = (
        "Change your login shell to zsh via chsh. This affects how you log in "
        "from now on — make sure that's what you want before confirming."
    )

    def _target_zsh_path(self, ctx: RunContext) -> str:
        found = shutil.which("zsh")
        if found:
            return found
        brew = resolve_brew_binary(ctx.os_info)
        return str(PurePosixPath(brew).parent / "zsh")

    def check_installed(self, ctx: RunContext) -> StepStatus:
        target = self._target_zsh_path(ctx)
        if os.environ.get("SHELL", "") == target:
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext) -> StepResult:
        target = self._target_zsh_path(ctx)
        if SHELLS_FILE.exists() and target not in SHELLS_FILE.read_text():
            ctx.run_command(["sudo", "sh", "-c", f"echo {target} >> {SHELLS_FILE}"])
        ctx.run_command(["chsh", "-s", target])
        return StepResult(StepStatus.INSTALLED, detail=target)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        target = self._target_zsh_path(ctx)
        return [f"chsh -s {target} (adding it to /etc/shells first if needed)"]

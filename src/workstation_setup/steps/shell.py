from __future__ import annotations

import os
import re
import shutil
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

from workstation_setup.exec import command_exists
from workstation_setup.providers.brew import BrewProvider, resolve_brew_binary
from workstation_setup.steps.base import Step, StepResult, StepStatus
from workstation_setup.ui import prompts

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

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        if reinstall:
            BrewProvider().reinstall(ctx, "zsh")
        else:
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

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        # See InstallHomebrewStep.run for why this pipes rather than using
        # `bash -c "$(curl ...)"` (word-splitting gotcha with no outer shell).
        # Re-running the installer with KEEP_ZSHRC=yes is a safe no-op-ish
        # "reinstall"/"repair" action, so `reinstall` needs no special branch.
        ctx.run_command(
            ["/bin/bash", "-c", f"curl -fsSL {OH_MY_ZSH_INSTALL_URL} | bash"],
            env={**os.environ, "RUNZSH": "no", "CHSH": "no", "KEEP_ZSHRC": "yes"},
        )
        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return [f"Run the Oh My Zsh install script ({OH_MY_ZSH_INSTALL_URL}) non-interactively"]


class ConfigureZshThemeStep(Step):
    id = "zsh-theme"
    title = "ZSH theme"
    description = "Choose and configure an oh-my-zsh theme in ~/.zshrc."

    def _zshrc(self) -> Path:
        return Path.home() / ".zshrc"

    def check_installed(self, ctx: RunContext) -> StepStatus:
        zshrc = self._zshrc()
        if not zshrc.exists():
            return StepStatus.NOT_INSTALLED
        contents = zshrc.read_text()
        if P10K_SOURCE_LINE in contents or "ZSH_THEME=" in contents:
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        # This step is inherently "modify" on every call — it always
        # re-prompts for a theme and reconciles ~/.zshrc, so `reinstall`
        # doesn't need a separate branch.
        theme = prompts.text_input(
            "Which oh-my-zsh theme would you like?", default="powerlevel10k"
        )
        ctx.selections["zsh_theme"] = theme

        zshrc = self._zshrc()
        contents = zshrc.read_text() if zshrc.exists() else ""

        if theme == "powerlevel10k":
            BrewProvider().install(ctx, "powerlevel10k")
            if P10K_SOURCE_LINE not in contents:
                with zshrc.open("a") as f:
                    if contents and not contents.endswith("\n"):
                        f.write("\n")
                    f.write(P10K_SOURCE_LINE + "\n")
        else:
            theme_line = f'ZSH_THEME="{theme}"'
            if re.search(r'^ZSH_THEME=', contents, re.MULTILINE):
                new_contents = re.sub(r'^ZSH_THEME=.*$', theme_line, contents, flags=re.MULTILINE)
                zshrc.write_text(new_contents)
            else:
                with zshrc.open("a") as f:
                    if contents and not contents.endswith("\n"):
                        f.write("\n")
                    f.write(theme_line + "\n")

        return StepResult(StepStatus.INSTALLED)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return ["Would prompt for ZSH theme (default: powerlevel10k) and configure ~/.zshrc"]


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

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        target = self._target_zsh_path(ctx)
        if SHELLS_FILE.exists() and target not in SHELLS_FILE.read_text():
            ctx.run_command(["sudo", "sh", "-c", f"echo {target} >> {SHELLS_FILE}"])
        ctx.run_command(["chsh", "-s", target])
        return StepResult(StepStatus.INSTALLED, detail=target)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        target = self._target_zsh_path(ctx)
        return [f"chsh -s {target} (adding it to /etc/shells first if needed)"]

from __future__ import annotations

import getpass
import socket
from pathlib import Path
from typing import TYPE_CHECKING

from workstation_setup import log
from workstation_setup.exec import command_exists
from workstation_setup.steps.base import Step, StepResult, StepStatus
from workstation_setup.ui import prompts

if TYPE_CHECKING:
    from workstation_setup.context import RunContext

GITHUB_SSH_SETTINGS_URL = "https://github.com/settings/ssh/new"


def _key_paths() -> tuple[Path, Path, Path]:
    ssh_dir = Path.home() / ".ssh"
    return ssh_dir, ssh_dir / "id_ed25519", ssh_dir / "id_ed25519.pub"


class GenerateSshKeyStep(Step):
    id = "ssh-key"
    title = "SSH key"
    description = (
        "Generate an ed25519 SSH key and, if the GitHub CLI is authenticated, "
        "register it with GitHub automatically."
    )

    def is_applicable(self, ctx: RunContext) -> bool:
        # Only offered once gh is around — GitHub is the whole point of this step.
        if ctx.os_info.family == "windows":
            return command_exists("gh") and command_exists("ssh-keygen")
        return command_exists("gh")

    def check_installed(self, ctx: RunContext) -> StepStatus:
        _, priv, _ = _key_paths()
        if priv.exists():
            return StepStatus.ALREADY_INSTALLED
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        # Already "modify" on every call — the overwrite confirmation below
        # is the real gate, so `reinstall` needs no separate branch.
        ssh_dir, priv, pub = _key_paths()

        if priv.exists():
            overwrite = prompts.confirm_step(
                f"An SSH key already exists at {priv}. Overwrite it? This is irreversible.",
                default=False,
            )
            if not overwrite:
                return StepResult(StepStatus.SKIPPED_BY_USER, detail="kept existing key")

        ssh_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

        comment = prompts.text_input(
            "Comment/email for the SSH key:", default=getpass.getuser()
        )
        passphrase_less = prompts.confirm_step(
            "Generate a passphrase-less key? (Recommended for a frictionless bootstrap — "
            "you can add a passphrase manually later)",
            default=True,
        )
        passphrase = "" if passphrase_less else prompts.text_input("Enter a passphrase:")

        ctx.run_command(
            ["ssh-keygen", "-t", "ed25519", "-C", comment, "-f", str(priv), "-N", passphrase]
        )
        ctx.run_command(["ssh-add", str(priv)], check=False)

        if ctx.selections.get("gh_authenticated"):
            return self._offer_github_upload(ctx, pub)

        log.panel(
            pub.read_text(),
            title=f"Public key — add it manually at {GITHUB_SSH_SETTINGS_URL}",
        )
        return StepResult(StepStatus.INSTALLED, detail="key generated")

    def _offer_github_upload(self, ctx: RunContext, pub: Path) -> StepResult:
        upload = prompts.confirm_step(
            "Upload this public key to your GitHub account now via `gh ssh-key add`?",
            default=True,
        )
        if not upload:
            return StepResult(StepStatus.INSTALLED, detail="key generated, not uploaded")

        result = ctx.run_command(
            [
                "gh",
                "ssh-key",
                "add",
                str(pub),
                "--title",
                f"{socket.gethostname()} (workstation-setup)",
            ],
            check=False,
        )
        if result.ok:
            return StepResult(StepStatus.INSTALLED, detail="key generated and uploaded to GitHub")
        return StepResult(
            StepStatus.PARTIAL, detail=f"key generated but upload failed: {result.stderr.strip()}"
        )

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return [
            "ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 (after confirming overwrite if one exists)",
            "ssh-add ~/.ssh/id_ed25519",
            "gh ssh-key add ~/.ssh/id_ed25519.pub (only if gh is authenticated)",
        ]

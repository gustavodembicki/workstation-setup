from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from workstation_setup.errors import StepError, UnsupportedPlatformError
from workstation_setup.exec import command_exists

if TYPE_CHECKING:
    from workstation_setup.context import RunContext

# HRESULT returned by WinGet when an exact query has no installed match.
_NO_APPLICATIONS_FOUND = 0x8A150014


def _normalized_exit_code(returncode: int) -> int:
    return returncode & 0xFFFFFFFF


def refresh_windows_path() -> None:
    """Refresh this process from Windows' persisted user/machine PATH.

    Installers broadcast environment changes to future processes, but the
    currently-running wizard does not receive those updates. Refreshing here
    lets later steps find git/gh immediately after WinGet installs them.
    """
    if os.name != "nt":
        return

    import winreg

    paths: list[str] = []
    locations = (
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
        ),
        (winreg.HKEY_CURRENT_USER, r"Environment"),
    )
    for hive, key_name in locations:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                value, _ = winreg.QueryValueEx(key, "Path")
        except OSError:
            continue
        paths.extend(part for part in os.path.expandvars(value).split(os.pathsep) if part)

    # Git for Windows keeps ssh-keygen/ssh-add in usr/bin, which is not always
    # included in its persisted PATH even though the main git command is.
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        paths.extend(
            [
                str(Path(program_files) / "Git" / "cmd"),
                str(Path(program_files) / "Git" / "usr" / "bin"),
                str(Path(program_files) / "GitHub CLI"),
            ]
        )

    paths.extend(part for part in os.environ.get("PATH", "").split(os.pathsep) if part)
    os.environ["PATH"] = os.pathsep.join(dict.fromkeys(paths))


class WingetProvider:
    name = "winget"

    def is_available(self, ctx: RunContext) -> bool:
        return command_exists("winget")

    def is_installed(self, ctx: RunContext, package: str) -> bool:
        result = ctx.run_command(
            ["winget", "list", "--id", package, "--exact", "--disable-interactivity"],
            check=False,
            read_only=True,
        )
        if result.ok:
            return True
        if _normalized_exit_code(result.returncode) == _NO_APPLICATIONS_FOUND:
            return False
        raise StepError(
            f"Could not inspect WinGet package: {package}",
            command=result.command,
            stderr=result.stderr or result.stdout,
        )

    def _install_args(self, ctx: RunContext, package: str, *, force: bool = False) -> list[str]:
        args = [
            "winget",
            "install",
            "--id",
            package,
            "--exact",
            "--source",
            "winget",
        ]
        if force:
            args.append("--force")
        if ctx.assume_yes:
            args.extend(
                [
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                    "--disable-interactivity",
                ]
            )
        return args

    def install(self, ctx: RunContext, package: str, *, cask: bool = False) -> None:
        if cask:
            raise UnsupportedPlatformError("WinGet has no concept of a Homebrew cask")
        ctx.run_command(self._install_args(ctx, package), capture=False)
        refresh_windows_path()

    def reinstall(self, ctx: RunContext, package: str, *, cask: bool = False) -> None:
        if cask:
            raise UnsupportedPlatformError("WinGet has no concept of a Homebrew cask")
        ctx.run_command(self._install_args(ctx, package, force=True), capture=False)
        refresh_windows_path()

    def list_installed(self, ctx: RunContext) -> set[str]:
        result = ctx.run_command(
            ["winget", "list", "--disable-interactivity"],
            check=False,
            read_only=True,
        )
        if not result.ok:
            raise StepError(
                "Could not list installed WinGet packages",
                command=result.command,
                stderr=result.stderr or result.stdout,
            )

        lines = result.stdout.splitlines()
        separator_index = next(
            (
                index
                for index, line in enumerate(lines)
                if "--" in line and not line.replace("-", "").strip()
            ),
            None,
        )
        if separator_index is None:
            return set()

        if separator_index == 0:
            return set()

        header = lines[separator_index - 1]
        columns = list(re.finditer(r"\S(?:.*?\S)?(?=\s{2,}|$)", header))
        if len(columns) < 3:
            return set()
        id_start = columns[1].start()
        id_end = columns[2].start()
        return {
            line[id_start:id_end].strip()
            for line in lines[separator_index + 1 :]
            if line[id_start:id_end].strip()
        }

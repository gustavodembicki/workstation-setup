from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Protocol

from workstation_setup.errors import StepError


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    command: list[str]

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class Runner(Protocol):
    def run(
        self,
        args: list[str],
        *,
        input: str | None = None,
        env: dict[str, str] | None = None,
        capture: bool = True,
    ) -> CommandResult: ...


class SubprocessRunner:
    """The real Runner, used outside of tests."""

    def run(
        self,
        args: list[str],
        *,
        input: str | None = None,
        env: dict[str, str] | None = None,
        capture: bool = True,
    ) -> CommandResult:
        completed = subprocess.run(
            args,
            input=input,
            env=env,
            capture_output=capture,
            text=True,
        )
        return CommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout or "" if capture else "",
            stderr=completed.stderr or "" if capture else "",
            command=args,
        )


@dataclass
class FakeRunner:
    """Test double for Runner. Pre-program responses by command name (args[0]),
    or fall back to `default_result`. Every call is recorded in `calls`.
    """

    responses: dict[str, CommandResult] = field(default_factory=dict)
    default_result: CommandResult | None = None
    calls: list[list[str]] = field(default_factory=list)
    captures: list[bool] = field(default_factory=list)

    def run(
        self,
        args: list[str],
        *,
        input: str | None = None,
        env: dict[str, str] | None = None,
        capture: bool = True,
    ) -> CommandResult:
        self.calls.append(args)
        self.captures.append(capture)
        key = args[0] if args else ""
        if key in self.responses:
            return self.responses[key]
        if self.default_result is not None:
            return self.default_result
        return CommandResult(returncode=0, stdout="", stderr="", command=args)


def run_command(
    runner: Runner,
    args: list[str],
    *,
    check: bool = True,
    input: str | None = None,
    env: dict[str, str] | None = None,
    capture: bool = True,
    dry_run: bool = False,
) -> CommandResult:
    """The single chokepoint for executing external commands.

    When dry_run is True, nothing is executed and a synthetic success result
    is returned so callers can preview what would happen. When check is True
    (default) a non-zero exit raises StepError with stderr attached instead
    of being silently swallowed.
    """
    if dry_run:
        return CommandResult(returncode=0, stdout="", stderr="", command=args)

    result = runner.run(args, input=input, env=env, capture=capture)

    if check and result.returncode != 0:
        raise StepError(
            f"Command failed ({result.returncode}): {' '.join(args)}",
            command=args,
            stderr=result.stderr,
        )

    return result


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None

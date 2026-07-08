from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, field
from typing import Any

from workstation_setup import log
from workstation_setup.exec import Runner, run_command
from workstation_setup.os_detect import OSInfo
from workstation_setup.state import State


@dataclass
class RunContext:
    """Everything a Step needs, bundled so it can be mocked/faked in one place
    for tests instead of relying on module-level globals.
    """

    os_info: OSInfo
    runner: Runner
    state: State
    dry_run: bool = False
    assume_yes: bool = False
    selections: dict[str, Any] = field(default_factory=dict)

    def run_command(
        self,
        args: list[str],
        *,
        check: bool = True,
        input: str | None = None,
        env: dict[str, str] | None = None,
        capture: bool = True,
    ):
        # capture=False means the subprocess is interactive or streams its own
        # progress straight to the terminal (gh auth login, curl --progress-bar)
        # — suspend any active spinner so it doesn't repaint over that output.
        suspend = log.suspend_task() if not capture else nullcontext()
        with suspend:
            return run_command(
                self.runner,
                args,
                check=check,
                input=input,
                env=env,
                capture=capture,
                dry_run=self.dry_run,
            )

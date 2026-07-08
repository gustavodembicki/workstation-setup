from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workstation_setup.context import RunContext


class StepStatus(StrEnum):
    ALREADY_INSTALLED = "already_installed"
    NOT_INSTALLED = "not_installed"
    PARTIAL = "partial"
    INSTALLED = "installed"
    SKIPPED_BY_USER = "skipped_by_user"
    UNSUPPORTED = "unsupported"
    FAILED = "failed"


class ExistingAction(StrEnum):
    """What the user wants to do about a Step that is already installed.

    Surfaced whenever check_installed() returns ALREADY_INSTALLED — that
    status must never cause a silent skip on its own (see wizard.py).
    """

    REINSTALL = "reinstall"
    LEAVE = "leave"
    CANCEL = "cancel"


@dataclass
class StepResult:
    status: StepStatus
    detail: str | None = None
    error: Exception | None = None


class Step(ABC):
    """One installable unit (Homebrew, zsh, an IDE, a GUI app, ...).

    Kept small and self-contained so the wizard can orchestrate a plain list
    of these rather than one monolithic script, and so each one is testable
    in isolation with a FakeRunner.
    """

    id: str
    title: str
    description: str

    def is_applicable(self, ctx: RunContext) -> bool:
        """Whether this step should even be offered. E.g. the SSH step is
        only applicable if the GitHub CLI step ran/is installed.
        """
        return True

    @abstractmethod
    def check_installed(self, ctx: RunContext) -> StepStatus:
        """Live detection of current system state — the source of truth for
        idempotency. Never trust state.json alone for this decision.
        """

    @abstractmethod
    def run(self, ctx: RunContext, *, reinstall: bool = False) -> StepResult:
        """Perform the actual install action. Must not swallow errors —
        let StepError propagate so the wizard can report it.

        `reinstall=True` is passed when the user explicitly asked to
        reinstall/modify something check_installed() already reported as
        ALREADY_INSTALLED. Package-style steps (brew formulas/casks) should
        force a real reinstall rather than a no-op install. Steps that are
        already interactive/reconfigurable on every call (shell theme, SSH
        key, gh auth, asdf plugins) can ignore the flag — re-running them is
        already the "modify" action.
        """

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        """Human-readable lines describing what `run` would do, without
        doing it. Default implementation is a generic placeholder; steps
        with real side effects should override this.
        """
        return [f"Would run: {self.title}"]

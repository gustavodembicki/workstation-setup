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
    def run(self, ctx: RunContext) -> StepResult:
        """Perform the actual install action. Must not swallow errors —
        let StepError propagate so the wizard can report it.
        """

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        """Human-readable lines describing what `run` would do, without
        doing it. Default implementation is a generic placeholder; steps
        with real side effects should override this.
        """
        return [f"Would run: {self.title}"]

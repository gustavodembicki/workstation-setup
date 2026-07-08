from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.table import Table

if TYPE_CHECKING:
    from workstation_setup.steps.base import Step, StepResult

DEFAULT_LOG_DIR = Path.home() / ".workstation-setup"
DEFAULT_LOG_PATH = DEFAULT_LOG_DIR / "run.log"

_STATUS_STYLE = {
    "already_installed": ("cyan", "already installed"),
    "installed": ("green", "installed"),
    "partial": ("yellow", "partially installed"),
    "skipped_by_user": ("yellow", "skipped"),
    "unsupported": ("yellow", "unsupported on this platform"),
    "failed": ("red", "failed"),
    "not_installed": ("white", "not installed"),
}


@dataclass
class _LogState:
    console: Console = field(default_factory=Console)
    log_path: Path | None = None
    log_file: TextIO | None = None
    dry_run: bool = False
    failed: bool = False
    finalized: bool = False
    task_stack: list[Status] = field(default_factory=list)
    suspend_depth: int = 0


_state = _LogState()


def configure(*, dry_run: bool = False, log_dir: Path = DEFAULT_LOG_DIR) -> None:
    """Called once, early in cli.py::main(). Opens the run's log file (unless
    dry_run, which never touches disk) and resets in-memory state so a fresh
    process always starts clean.
    """
    global _state
    _state = _LogState(console=Console(), dry_run=dry_run)

    if dry_run:
        return

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "run.log"
    _state.log_path = log_path
    _state.log_file = log_path.open("w", encoding="utf-8")


def reset() -> None:
    """Test-only: fresh recording console, no file I/O. Call from an autouse
    pytest fixture so tests never see another test's state or touch disk.
    """
    global _state
    if _state.log_file is not None:
        _state.log_file.close()
    _state = _LogState(console=Console(record=True), dry_run=True)


def _write_file(line: str) -> None:
    if _state.log_file is None:
        return
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    _state.log_file.write(f"[{timestamp}] {line}\n")
    _state.log_file.flush()


def _print(renderable, *, plain: str | None = None) -> None:
    _state.console.print(renderable)
    if plain is not None:
        _write_file(plain)


def welcome(os_summary: str) -> None:
    _print(
        Panel(f"workstation-setup\nDetected: {os_summary}", title="Welcome"),
        plain=f"Welcome — detected: {os_summary}",
    )


def step_header(step: Step) -> None:
    _print(f"\n[bold]{step.title}[/bold]")
    _print(step.description, plain=f"=== {step.title} — {step.description}")


def result(step: Step, step_result: StepResult) -> None:
    color, label = _STATUS_STYLE.get(step_result.status.value, ("white", step_result.status.value))
    line = f"[{color}]{step.title} — {label}[/{color}]"
    plain = f"{step.title} — {label}"
    if step_result.detail:
        line += f" ({step_result.detail})"
        plain += f" ({step_result.detail})"
    _print(line, plain=plain)


def failure(step: Step, error: Exception) -> None:
    stderr = getattr(error, "stderr", "")
    command = getattr(error, "command", None)
    body = str(error) + (f"\n{stderr}" if stderr else "")
    _print(Panel(body, title=f"[red]Failed: {step.title}[/red]"))
    plain = f"FAILED: {step.title} — {error}"
    if command:
        plain += f"\n  command: {' '.join(command)}"
    if stderr:
        plain += f"\n  stderr: {stderr}"
    _write_file(plain)


def summary_table(results: list[tuple[Step, StepResult]]) -> None:
    table = Table(title="Summary")
    table.add_column("Step")
    table.add_column("Status")
    table.add_column("Notes")

    lines = ["Summary:"]
    for step, step_result in results:
        _, label = _STATUS_STYLE.get(step_result.status.value, ("white", step_result.status.value))
        table.add_row(step.title, label, step_result.detail or "")
        lines.append(f"  {step.title}: {label} ({step_result.detail or ''})")

    _state.console.print(table)
    _write_file("\n".join(lines))


def info(message: str) -> None:
    _print(message, plain=message)


def warning(message: str) -> None:
    _print(f"[yellow]{message}[/yellow]", plain=f"WARNING: {message}")


def error(message: str) -> None:
    _print(f"[red]{message}[/red]", plain=f"ERROR: {message}")


def note(message: str) -> None:
    _print(f"  [cyan]{message}[/cyan]", plain=message)


def panel(body: str, title: str) -> None:
    _print(Panel(body, title=title), plain=f"{title}\n{body}")


def dry_run_line(text: str, *, indent: int = 2) -> None:
    prefix = " " * indent
    _print(f"{prefix}{text}", plain=f"{prefix}{text}")


@contextmanager
def task(label: str) -> Iterator[None]:
    """Indeterminate spinner around a blocking call. Stacks: a nested task
    replaces the visible label and the outer one resumes on exit.
    """
    if _state.dry_run:
        yield
        return

    status = _state.console.status(label, spinner="dots")
    status.start()
    _state.task_stack.append(status)
    try:
        yield
    finally:
        _state.task_stack.pop()
        status.stop()


@contextmanager
def suspend_task() -> Iterator[None]:
    """Pause the active spinner (if any) so an interactive/uncaptured
    subprocess can safely own the terminal. No-op if no task is active.
    Safe to nest.
    """
    active = _state.task_stack[-1] if _state.task_stack else None
    if active is not None:
        active.stop()
    try:
        yield
    finally:
        if active is not None:
            active.start()


def mark_failed() -> None:
    _state.failed = True


def finalize(*, success: bool) -> None:
    """Idempotent — closes the log file; deletes it on a clean success run,
    retains it (and reports its path) otherwise.
    """
    if _state.finalized:
        return
    _state.finalized = True

    if _state.log_file is not None:
        _state.log_file.close()
        _state.log_file = None

    log_path = _state.log_path
    if log_path is None:
        return

    if success and not _state.failed:
        log_path.unlink(missing_ok=True)
    else:
        info(f"Run log kept for debugging: {log_path}")


def console_export() -> str:
    """Test helper: returns everything printed since the last reset()."""
    if _state.console.record:
        return _state.console.export_text()
    return ""

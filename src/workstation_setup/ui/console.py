from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from workstation_setup.steps.base import Step, StepResult, StepStatus

_STATUS_STYLE = {
    StepStatus.ALREADY_INSTALLED: ("cyan", "already installed"),
    StepStatus.INSTALLED: ("green", "installed"),
    StepStatus.PARTIAL: ("yellow", "partially installed"),
    StepStatus.SKIPPED_BY_USER: ("yellow", "skipped"),
    StepStatus.UNSUPPORTED: ("yellow", "unsupported on this platform"),
    StepStatus.FAILED: ("red", "failed"),
    StepStatus.NOT_INSTALLED: ("white", "not installed"),
}


def print_welcome(console: Console, os_summary: str) -> None:
    console.print(Panel(f"workstation-setup\nDetected: {os_summary}", title="Welcome"))


def print_step_header(console: Console, step: Step) -> None:
    console.print(f"\n[bold]{step.title}[/bold]")
    console.print(step.description)


def print_result(console: Console, step: Step, result: StepResult) -> None:
    color, label = _STATUS_STYLE.get(result.status, ("white", result.status.value))
    line = f"[{color}]{step.title} — {label}[/{color}]"
    if result.detail:
        line += f" ({result.detail})"
    console.print(line)


def print_failure(console: Console, step: Step, error: Exception) -> None:
    stderr = getattr(error, "stderr", "")
    body = str(error) + (f"\n{stderr}" if stderr else "")
    console.print(Panel(body, title=f"[red]Failed: {step.title}[/red]"))


def print_summary_table(console: Console, results: list[tuple[Step, StepResult]]) -> None:
    table = Table(title="Summary")
    table.add_column("Step")
    table.add_column("Status")
    table.add_column("Notes")

    for step, result in results:
        _, label = _STATUS_STYLE.get(result.status, ("white", result.status.value))
        table.add_row(step.title, label, result.detail or "")

    console.print(table)

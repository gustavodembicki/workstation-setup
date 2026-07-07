from __future__ import annotations

from collections.abc import Callable

from workstation_setup.context import RunContext
from workstation_setup.errors import AbortError, StepError
from workstation_setup.steps.base import Step, StepResult, StepStatus
from workstation_setup.ui import prompts
from workstation_setup.ui.console import (
    print_failure,
    print_result,
    print_step_header,
    print_summary_table,
    print_welcome,
)

ConfirmFn = Callable[[str], bool]


def run(
    ctx: RunContext,
    steps: list[Step],
    *,
    confirm_fn: ConfirmFn = prompts.confirm_step,
) -> list[tuple[Step, StepResult]]:
    """Walk the ordered list of Steps, driving prompts and recording results.

    `confirm_fn` is injectable so tests can drive the wizard without a real
    terminal prompt.
    """
    console = ctx.console
    results: list[tuple[Step, StepResult]] = []

    print_welcome(console, f"{ctx.os_info.family} ({ctx.os_info.distro_name or ''})")

    for step in steps:
        if not step.is_applicable(ctx):
            continue

        status = step.check_installed(ctx)

        if status == StepStatus.ALREADY_INSTALLED:
            result = StepResult(status)
            print_result(console, step, result)
            ctx.state.record(step.id, status.value)
            results.append((step, result))
            continue

        print_step_header(console, step)

        if ctx.dry_run:
            for line in step.dry_run_preview(ctx):
                console.print(f"  {line}")
            results.append((step, StepResult(status, detail="dry-run preview")))
            continue

        proceed = ctx.assume_yes or confirm_fn(f"Proceed with: {step.title}?")
        if not proceed:
            result = StepResult(StepStatus.SKIPPED_BY_USER)
            print_result(console, step, result)
            ctx.state.record(step.id, result.status.value)
            results.append((step, result))
            continue

        try:
            result = step.run(ctx)
            print_result(console, step, result)
            ctx.state.record(step.id, result.status.value, detail=result.detail)
        except StepError as error:
            print_failure(console, step, error)
            result = StepResult(StepStatus.FAILED, detail=str(error), error=error)
            ctx.state.record(step.id, result.status.value, detail=str(error))
            results.append((step, result))

            keep_going = ctx.assume_yes or confirm_fn("Continue with remaining steps?")
            if not keep_going:
                print_summary_table(console, results)
                raise AbortError(f"Aborted after failure in step '{step.id}'") from error
            continue

        results.append((step, result))

    print_summary_table(console, results)
    return results

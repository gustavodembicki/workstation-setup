from __future__ import annotations

from collections.abc import Callable

import questionary

from workstation_setup.context import RunContext
from workstation_setup.errors import AbortError, StepError
from workstation_setup.steps.base import ExistingAction, Step, StepResult, StepStatus
from workstation_setup.ui import prompts
from workstation_setup.ui.console import (
    print_failure,
    print_result,
    print_step_header,
    print_summary_table,
)

ConfirmFn = Callable[[str], bool]
ActionFn = Callable[[str], ExistingAction]

Results = list[tuple[Step, StepResult]]


def _execute_step(ctx: RunContext, step: Step, *, reinstall: bool = False) -> StepResult:
    """Run a Step for real, reporting/recording the outcome either way.
    Shared by run_recommended and run_menu so both stay in sync on how a
    result is printed and persisted to state.json.
    """
    console = ctx.console
    try:
        result = step.run(ctx, reinstall=reinstall)
        print_result(console, step, result)
        ctx.state.record(step.id, result.status.value, detail=result.detail)
        return result
    except StepError as error:
        print_failure(console, step, error)
        result = StepResult(StepStatus.FAILED, detail=str(error), error=error)
        ctx.state.record(step.id, result.status.value, detail=str(error))
        return result


def _resolve_already_installed(
    ctx: RunContext, step: Step, *, action_fn: ActionFn
) -> StepResult:
    """A Step reported ALREADY_INSTALLED — never treat that as "nothing to
    do" on its own. Ask the user for a real decision instead of silently
    skipping (that silent skip was the whole bug being fixed here).
    """
    console = ctx.console

    if ctx.assume_yes:
        # No terminal to prompt in non-interactive/automation runs — the
        # safe default is to leave existing installs alone, same as the
        # pre-existing idempotent behavior.
        result = StepResult(StepStatus.ALREADY_INSTALLED, detail="left as is (--yes)")
        print_result(console, step, result)
        ctx.state.record(step.id, result.status.value, detail=result.detail)
        return result

    action = action_fn(step.title)
    if action == ExistingAction.REINSTALL:
        return _execute_step(ctx, step, reinstall=True)

    detail = "left as is by user" if action == ExistingAction.LEAVE else "cancelled by user"
    result = StepResult(StepStatus.SKIPPED_BY_USER, detail=detail)
    print_result(console, step, result)
    ctx.state.record(step.id, result.status.value, detail=detail)
    return result


def run_recommended(
    ctx: RunContext,
    steps: list[Step],
    *,
    confirm_fn: ConfirmFn = prompts.confirm_step,
    action_fn: ActionFn = prompts.select_existing_action,
) -> Results:
    """Walk the recommended bootstrap pipeline in its designed order
    (Homebrew -> zsh -> ... -> SSH key). Unlike the old wizard loop, an
    ALREADY_INSTALLED status is never a silent skip — see
    _resolve_already_installed.
    """
    console = ctx.console
    results: Results = []

    for step in steps:
        if not step.is_applicable(ctx):
            continue

        status = step.check_installed(ctx)
        print_step_header(console, step)

        if ctx.dry_run:
            for line in step.dry_run_preview(ctx):
                console.print(f"  {line}")
            results.append((step, StepResult(status, detail="dry-run preview")))
            continue

        if status == StepStatus.ALREADY_INSTALLED:
            result = _resolve_already_installed(ctx, step, action_fn=action_fn)
        else:
            proceed = ctx.assume_yes or confirm_fn(f"Proceed with: {step.title}?")
            if not proceed:
                result = StepResult(StepStatus.SKIPPED_BY_USER)
                print_result(console, step, result)
                ctx.state.record(step.id, result.status.value)
            else:
                result = _execute_step(ctx, step)

        results.append((step, result))

        if result.status == StepStatus.FAILED:
            keep_going = ctx.assume_yes or confirm_fn("Continue with remaining steps?")
            if not keep_going:
                print_summary_table(console, results)
                raise AbortError(f"Aborted after failure in step '{step.id}'") from result.error

    print_summary_table(console, results)
    return results


def run_menu(
    ctx: RunContext,
    steps: list[Step],
    *,
    confirm_fn: ConfirmFn = prompts.confirm_step,
    action_fn: ActionFn = prompts.select_existing_action,
    checkbox_fn: Callable[[str, list[questionary.Choice]], list[str]] = prompts.checkbox_select,
) -> Results:
    """The master menu: every installable thing (core tooling, IDEs,
    everyday apps) in one flat, non-mandatory checklist. Nothing is
    pre-checked -- the user opts into whatever they want this run, whether
    or not it's already installed.
    """
    console = ctx.console
    applicable = [s for s in steps if s.is_applicable(ctx)]
    statuses = {step.id: step.check_installed(ctx) for step in applicable}

    if ctx.dry_run:
        console.print("\n[bold]Everything available to install/reinstall/modify:[/bold]")
        results: Results = []
        for step in applicable:
            already = statuses[step.id] == StepStatus.ALREADY_INSTALLED
            note = " (already installed)" if already else ""
            console.print(f"  - {step.title}{note}")
            for line in step.dry_run_preview(ctx):
                console.print(f"      {line}")
            results.append((step, StepResult(statuses[step.id], detail="dry-run preview")))
        return results

    def _label(step: Step) -> str:
        if statuses[step.id] == StepStatus.ALREADY_INSTALLED:
            return f"{step.title} (already installed)"
        return step.title

    choices = [
        questionary.Choice(title=_label(step), value=step.id, checked=False) for step in applicable
    ]
    selected_ids = set(checkbox_fn("Select anything to install, reinstall, or modify:", choices))

    results = []
    for step in applicable:
        if step.id not in selected_ids:
            continue

        print_step_header(console, step)
        status = statuses[step.id]
        if status == StepStatus.ALREADY_INSTALLED:
            result = _resolve_already_installed(ctx, step, action_fn=action_fn)
        else:
            result = _execute_step(ctx, step)
        results.append((step, result))

    print_summary_table(console, results)
    return results

import pytest
from factories import make_context

from workstation_setup import wizard
from workstation_setup.errors import AbortError, StepError
from workstation_setup.steps.base import ExistingAction, Step, StepResult, StepStatus


class FakeStep(Step):
    def __init__(
        self,
        id_: str,
        *,
        applicable: bool = True,
        installed_status: StepStatus = StepStatus.NOT_INSTALLED,
        run_result: StepResult | None = None,
        raises: Exception | None = None,
    ):
        self.id = id_
        self.title = id_
        self.description = f"Install {id_}"
        self._applicable = applicable
        self._installed_status = installed_status
        self._run_result = run_result or StepResult(StepStatus.INSTALLED)
        self._raises = raises
        self.run_called = False
        self.run_calls: list[bool] = []  # records the `reinstall` flag of each call

    def is_applicable(self, ctx):
        return self._applicable

    def check_installed(self, ctx):
        return self._installed_status

    def run(self, ctx, *, reinstall: bool = False):
        self.run_called = True
        self.run_calls.append(reinstall)
        if self._raises:
            raise self._raises
        return self._run_result

    def dry_run_preview(self, ctx):
        return [f"Would install {self.id}"]


# ---- run_recommended ----------------------------------------------------


def test_recommended_already_installed_prompts_for_an_action_never_skips_silently():
    ctx = make_context()
    step = FakeStep("zsh", installed_status=StepStatus.ALREADY_INSTALLED)

    def action_fn(title):
        pytest.fail("action_fn was not supposed to be reached in this test")

    called = {"n": 0}

    def tracking_action_fn(title):
        called["n"] += 1
        return ExistingAction.LEAVE

    results = wizard.run_recommended(ctx, [step], action_fn=tracking_action_fn)

    assert called["n"] == 1
    assert step.run_called is False
    assert results == [(step, StepResult(StepStatus.SKIPPED_BY_USER, detail="left as is by user"))]


def test_recommended_already_installed_reinstall_action_runs_the_step():
    ctx = make_context()
    step = FakeStep("zsh", installed_status=StepStatus.ALREADY_INSTALLED)

    results = wizard.run_recommended(ctx, [step], action_fn=lambda title: ExistingAction.REINSTALL)

    assert step.run_called is True
    assert step.run_calls == [True]  # reinstall=True
    assert results == [(step, StepResult(StepStatus.INSTALLED))]


def test_recommended_already_installed_cancel_action_leaves_it_alone():
    ctx = make_context()
    step = FakeStep("zsh", installed_status=StepStatus.ALREADY_INSTALLED)

    results = wizard.run_recommended(ctx, [step], action_fn=lambda title: ExistingAction.CANCEL)

    assert step.run_called is False
    assert results == [(step, StepResult(StepStatus.SKIPPED_BY_USER, detail="cancelled by user"))]


def test_recommended_already_installed_with_assume_yes_leaves_alone_without_prompting():
    ctx = make_context(assume_yes=True)
    step = FakeStep("zsh", installed_status=StepStatus.ALREADY_INSTALLED)

    def action_fn(title):
        pytest.fail("should not prompt when assume_yes is set")

    results = wizard.run_recommended(ctx, [step], action_fn=action_fn)

    assert step.run_called is False
    expected = StepResult(StepStatus.ALREADY_INSTALLED, detail="left as is (--yes)")
    assert results == [(step, expected)]


def test_recommended_not_applicable_step_is_excluded_entirely():
    ctx = make_context()
    step = FakeStep("ssh", applicable=False)

    results = wizard.run_recommended(
        ctx, [step], confirm_fn=lambda msg: pytest.fail("should not prompt")
    )

    assert results == []
    assert "ssh" not in ctx.state.steps


def test_recommended_user_declining_confirm_skips_step_without_running():
    ctx = make_context()
    step = FakeStep("asdf")

    results = wizard.run_recommended(ctx, [step], confirm_fn=lambda msg: False)

    assert step.run_called is False
    assert results == [(step, StepResult(StepStatus.SKIPPED_BY_USER))]


def test_recommended_user_confirming_runs_step_and_records_success():
    ctx = make_context()
    step = FakeStep("git", run_result=StepResult(StepStatus.INSTALLED, detail="git 2.45"))

    results = wizard.run_recommended(ctx, [step], confirm_fn=lambda msg: True)

    assert step.run_called is True
    assert results == [(step, StepResult(StepStatus.INSTALLED, detail="git 2.45"))]
    assert ctx.state.steps["git"].detail == "git 2.45"


def test_recommended_dry_run_previews_without_calling_run_or_prompting():
    ctx = make_context(dry_run=True)
    step = FakeStep("homebrew", installed_status=StepStatus.ALREADY_INSTALLED)

    wizard.run_recommended(
        ctx,
        [step],
        confirm_fn=lambda msg: pytest.fail("should not prompt in dry-run"),
        action_fn=lambda title: pytest.fail("should not prompt in dry-run"),
    )

    assert step.run_called is False


def test_recommended_failed_step_aborts_when_user_declines_to_continue():
    ctx = make_context()
    failing = FakeStep("homebrew", raises=StepError("boom", stderr="permission denied"))
    never_reached = FakeStep("zsh")

    confirms = iter([True, False])  # proceed with homebrew, then decline to continue

    with pytest.raises(AbortError):
        wizard.run_recommended(ctx, [failing, never_reached], confirm_fn=lambda msg: next(confirms))

    assert never_reached.run_called is False
    assert ctx.state.steps["homebrew"].status == "failed"


def test_recommended_failed_step_continues_when_user_agrees_to_continue():
    ctx = make_context()
    failing = FakeStep("homebrew", raises=StepError("boom", stderr="permission denied"))
    next_step = FakeStep("zsh")

    confirms = iter([True, True, True])  # proceed, continue after failure, proceed with zsh

    results = wizard.run_recommended(
        ctx, [failing, next_step], confirm_fn=lambda msg: next(confirms)
    )

    assert next_step.run_called is True
    assert [status.status for _, status in results] == [StepStatus.FAILED, StepStatus.INSTALLED]


# ---- run_menu -------------------------------------------------------------


def test_menu_nothing_pre_checked_only_selected_items_are_processed():
    ctx = make_context()
    a = FakeStep("a")
    b = FakeStep("b")
    captured_choices = {}

    def checkbox_fn(message, choices):
        captured_choices["choices"] = choices
        return ["a"]  # only "a" selected, "b" left unchecked

    results = wizard.run_menu(ctx, [a, b], checkbox_fn=checkbox_fn)

    assert all(choice.checked is False for choice in captured_choices["choices"])
    assert a.run_called is True
    assert b.run_called is False
    assert [step.id for step, _ in results] == ["a"]


def test_menu_not_applicable_step_is_excluded_from_the_checkbox():
    ctx = make_context()
    step = FakeStep("ssh", applicable=False)
    captured_choices = {}

    def checkbox_fn(message, choices):
        captured_choices["choices"] = choices
        return []

    wizard.run_menu(ctx, [step], checkbox_fn=checkbox_fn)

    assert captured_choices["choices"] == []


def test_menu_selecting_an_already_installed_item_prompts_for_an_action():
    ctx = make_context()
    step = FakeStep("zsh", installed_status=StepStatus.ALREADY_INSTALLED)

    results = wizard.run_menu(
        ctx,
        [step],
        checkbox_fn=lambda message, choices: ["zsh"],
        action_fn=lambda title: ExistingAction.REINSTALL,
    )

    assert step.run_called is True
    assert step.run_calls == [True]
    assert results == [(step, StepResult(StepStatus.INSTALLED))]


def test_menu_selecting_a_not_installed_item_just_runs_it_no_extra_confirm():
    ctx = make_context()
    step = FakeStep("chrome")

    results = wizard.run_menu(
        ctx,
        [step],
        checkbox_fn=lambda message, choices: ["chrome"],
        confirm_fn=lambda msg: pytest.fail("selection itself is the confirmation"),
    )

    assert step.run_called is True
    assert results == [(step, StepResult(StepStatus.INSTALLED))]


def test_menu_failure_does_not_abort_remaining_selected_items():
    ctx = make_context()
    failing = FakeStep("chrome", raises=StepError("boom", stderr="network"))
    next_step = FakeStep("slack")

    results = wizard.run_menu(
        ctx,
        [failing, next_step],
        checkbox_fn=lambda message, choices: ["chrome", "slack"],
        confirm_fn=lambda msg: pytest.fail("run_menu never asks to keep going"),
    )

    assert next_step.run_called is True
    assert [status.status for _, status in results] == [StepStatus.FAILED, StepStatus.INSTALLED]


def test_menu_dry_run_lists_everything_without_prompting_or_running():
    ctx = make_context(dry_run=True)
    a = FakeStep("a", installed_status=StepStatus.ALREADY_INSTALLED)
    b = FakeStep("b")

    def checkbox_fn(message, choices):
        pytest.fail("dry-run must never prompt for a selection")

    results = wizard.run_menu(ctx, [a, b], checkbox_fn=checkbox_fn)

    assert a.run_called is False
    assert b.run_called is False
    assert {step.id for step, _ in results} == {"a", "b"}

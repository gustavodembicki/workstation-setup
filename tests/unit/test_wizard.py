import pytest
from factories import make_context

from workstation_setup import wizard
from workstation_setup.errors import AbortError, StepError
from workstation_setup.steps.base import Step, StepResult, StepStatus


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

    def is_applicable(self, ctx):
        return self._applicable

    def check_installed(self, ctx):
        return self._installed_status

    def run(self, ctx):
        self.run_called = True
        if self._raises:
            raise self._raises
        return self._run_result

    def dry_run_preview(self, ctx):
        return [f"Would install {self.id}"]


def test_already_installed_step_is_skipped_without_prompting():
    ctx = make_context()
    step = FakeStep("zsh", installed_status=StepStatus.ALREADY_INSTALLED)

    results = wizard.run(ctx, [step], confirm_fn=lambda msg: pytest.fail("should not prompt"))

    assert results == [(step, StepResult(StepStatus.ALREADY_INSTALLED))]
    assert ctx.state.steps["zsh"].status == "already_installed"


def test_not_applicable_step_is_excluded_entirely():
    ctx = make_context()
    step = FakeStep("ssh", applicable=False)

    results = wizard.run(ctx, [step], confirm_fn=lambda msg: pytest.fail("should not prompt"))

    assert results == []
    assert "ssh" not in ctx.state.steps


def test_user_declining_confirm_skips_step_without_running():
    ctx = make_context()
    step = FakeStep("asdf")

    results = wizard.run(ctx, [step], confirm_fn=lambda msg: False)

    assert step.run_called is False
    assert results == [(step, StepResult(StepStatus.SKIPPED_BY_USER))]


def test_user_confirming_runs_step_and_records_success():
    ctx = make_context()
    step = FakeStep("git", run_result=StepResult(StepStatus.INSTALLED, detail="git 2.45"))

    results = wizard.run(ctx, [step], confirm_fn=lambda msg: True)

    assert step.run_called is True
    assert results == [(step, StepResult(StepStatus.INSTALLED, detail="git 2.45"))]
    assert ctx.state.steps["git"].detail == "git 2.45"


def test_dry_run_previews_without_calling_run():
    ctx = make_context(dry_run=True)
    step = FakeStep("homebrew")

    wizard.run(ctx, [step], confirm_fn=lambda msg: pytest.fail("should not prompt in dry-run"))

    assert step.run_called is False


def test_failed_step_aborts_when_user_declines_to_continue():
    ctx = make_context()
    failing = FakeStep("homebrew", raises=StepError("boom", stderr="permission denied"))
    never_reached = FakeStep("zsh")

    confirms = iter([True, False])  # proceed with homebrew, then decline to continue

    with pytest.raises(AbortError):
        wizard.run(ctx, [failing, never_reached], confirm_fn=lambda msg: next(confirms))

    assert never_reached.run_called is False
    assert ctx.state.steps["homebrew"].status == "failed"


def test_failed_step_continues_when_user_agrees_to_continue():
    ctx = make_context()
    failing = FakeStep("homebrew", raises=StepError("boom", stderr="permission denied"))
    next_step = FakeStep("zsh")

    confirms = iter([True, True, True])  # proceed, continue after failure, proceed with zsh

    results = wizard.run(ctx, [failing, next_step], confirm_fn=lambda msg: next(confirms))

    assert next_step.run_called is True
    assert [status.status for _, status in results] == [StepStatus.FAILED, StepStatus.INSTALLED]

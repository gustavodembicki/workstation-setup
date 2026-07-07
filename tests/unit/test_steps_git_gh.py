from factories import make_context

from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.steps import git_gh as git_gh_module
from workstation_setup.steps.base import StepStatus
from workstation_setup.steps.git_gh import GhAuthLoginStep, InstallGhStep, InstallGitStep


def test_git_check_installed_true_when_present(monkeypatch):
    monkeypatch.setattr(git_gh_module, "command_exists", lambda name: True)

    assert InstallGitStep().check_installed(make_context()) == StepStatus.ALREADY_INSTALLED


def test_git_run_installs_via_brew(monkeypatch):
    installed = []
    monkeypatch.setattr(
        BrewProvider, "install", lambda self, ctx, pkg, cask=False: installed.append(pkg)
    )

    result = InstallGitStep().run(make_context())

    assert installed == ["git"]
    assert result.status == StepStatus.INSTALLED


def test_gh_run_installs_via_brew(monkeypatch):
    installed = []
    monkeypatch.setattr(
        BrewProvider, "install", lambda self, ctx, pkg, cask=False: installed.append(pkg)
    )

    result = InstallGhStep().run(make_context())

    assert installed == ["gh"]
    assert result.status == StepStatus.INSTALLED


def test_gh_auth_login_is_applicable_only_when_gh_installed(monkeypatch):
    monkeypatch.setattr(git_gh_module, "command_exists", lambda name: False)

    assert GhAuthLoginStep().is_applicable(make_context()) is False


def test_gh_auth_login_check_installed_records_selection(monkeypatch):
    monkeypatch.setattr(git_gh_module, "command_exists", lambda name: True)
    runner = FakeRunner(default_result=CommandResult(0, "logged in", "", []))
    ctx = make_context(runner=runner)

    status = GhAuthLoginStep().check_installed(ctx)

    assert status == StepStatus.ALREADY_INSTALLED
    assert ctx.selections["gh_authenticated"] is True


def test_gh_auth_login_check_installed_false_when_not_authenticated():
    runner = FakeRunner(default_result=CommandResult(1, "", "not logged in", []))
    ctx = make_context(runner=runner)

    status = GhAuthLoginStep().check_installed(ctx)

    assert status == StepStatus.NOT_INSTALLED
    assert ctx.selections["gh_authenticated"] is False


def test_gh_auth_login_run_uses_uncaptured_output_and_marks_authenticated():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    result = GhAuthLoginStep().run(ctx)

    assert result.status == StepStatus.INSTALLED
    assert ctx.selections["gh_authenticated"] is True

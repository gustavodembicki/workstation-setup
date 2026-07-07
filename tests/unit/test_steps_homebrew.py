from factories import make_context

from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.steps import homebrew as homebrew_module
from workstation_setup.steps.base import StepStatus
from workstation_setup.steps.homebrew import InstallHomebrewStep


def test_check_installed_already_installed_when_brew_available(monkeypatch):
    monkeypatch.setattr(BrewProvider, "is_available", lambda self, ctx: True)
    ctx = make_context()

    assert InstallHomebrewStep().check_installed(ctx) == StepStatus.ALREADY_INSTALLED


def test_check_installed_not_installed_when_brew_unavailable(monkeypatch):
    monkeypatch.setattr(BrewProvider, "is_available", lambda self, ctx: False)
    ctx = make_context()

    assert InstallHomebrewStep().check_installed(ctx) == StepStatus.NOT_INSTALLED


def test_run_invokes_official_install_script_with_noninteractive_env(monkeypatch):
    ensure_path_calls = []
    monkeypatch.setattr(homebrew_module, "ensure_brew_on_path", ensure_path_calls.append)
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    result = InstallHomebrewStep().run(ctx)

    assert result.status == StepStatus.INSTALLED
    [call_args] = runner.calls
    assert call_args[0] == "/bin/bash"
    assert "curl" in call_args[2] and "| bash" in call_args[2]
    assert ensure_path_calls == [ctx.os_info]


def test_dry_run_preview_mentions_install_script():
    ctx = make_context()

    preview = InstallHomebrewStep().dry_run_preview(ctx)

    assert any("NONINTERACTIVE" in line for line in preview)

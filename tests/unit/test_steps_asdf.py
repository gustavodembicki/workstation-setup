import pytest
from factories import make_context

from workstation_setup.errors import StepError
from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.steps import asdf as asdf_module
from workstation_setup.steps.asdf import AsdfPluginsStep, InstallAsdfStep
from workstation_setup.steps.base import StepStatus


def test_asdf_check_installed_true_when_command_exists(monkeypatch):
    monkeypatch.setattr(asdf_module, "command_exists", lambda name: True)

    assert InstallAsdfStep().check_installed(make_context()) == StepStatus.ALREADY_INSTALLED


def test_asdf_run_installs_via_brew(monkeypatch):
    installed = []
    monkeypatch.setattr(
        BrewProvider, "install", lambda self, ctx, pkg, cask=False: installed.append(pkg)
    )

    result = InstallAsdfStep().run(make_context())

    assert installed == ["asdf"]
    assert result.status == StepStatus.INSTALLED


def test_plugins_step_only_applicable_when_asdf_installed(monkeypatch):
    monkeypatch.setattr(asdf_module, "command_exists", lambda name: False)

    assert AsdfPluginsStep().is_applicable(make_context()) is False


def test_plugins_step_adds_selected_curated_plugins(monkeypatch):
    monkeypatch.setattr(
        asdf_module.prompts, "checkbox_select", lambda msg, choices: ["nodejs", "ruby"]
    )
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    result = AsdfPluginsStep().run(ctx)

    assert runner.calls == [
        ["asdf", "plugin", "add", "nodejs"],
        ["asdf", "plugin", "add", "ruby"],
    ]
    assert result.status == StepStatus.INSTALLED
    assert result.detail == "nodejs, ruby"


def test_plugins_step_supports_free_text_other_plugins(monkeypatch):
    monkeypatch.setattr(
        asdf_module.prompts, "checkbox_select", lambda msg, choices: [asdf_module.OTHER_CHOICE]
    )
    monkeypatch.setattr(asdf_module.prompts, "text_input", lambda msg: "rust, deno")
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    result = AsdfPluginsStep().run(ctx)

    assert runner.calls == [
        ["asdf", "plugin", "add", "rust"],
        ["asdf", "plugin", "add", "deno"],
    ]
    assert result.detail == "rust, deno"


def test_plugins_step_treats_already_added_as_success(monkeypatch):
    monkeypatch.setattr(asdf_module.prompts, "checkbox_select", lambda msg, choices: ["nodejs"])
    runner = FakeRunner(default_result=CommandResult(2, "", "plugin nodejs already added", []))
    ctx = make_context(runner=runner)

    result = AsdfPluginsStep().run(ctx)

    assert result.status == StepStatus.INSTALLED
    assert result.detail == "nodejs"


def test_plugins_step_no_selection_is_skipped(monkeypatch):
    monkeypatch.setattr(asdf_module.prompts, "checkbox_select", lambda msg, choices: [])

    result = AsdfPluginsStep().run(make_context())

    assert result.status == StepStatus.SKIPPED_BY_USER


def test_plugins_step_all_fail_raises_step_error(monkeypatch):
    monkeypatch.setattr(
        asdf_module.prompts, "checkbox_select", lambda msg, choices: [asdf_module.OTHER_CHOICE]
    )
    monkeypatch.setattr(asdf_module.prompts, "text_input", lambda msg: "notreal")
    runner = FakeRunner(default_result=CommandResult(1, "", "some error", []))
    ctx = make_context(runner=runner)

    with pytest.raises(StepError, match="notreal"):
        AsdfPluginsStep().run(ctx)


def test_plugins_step_partial_success(monkeypatch):
    monkeypatch.setattr(
        asdf_module.prompts, "checkbox_select", lambda msg, choices: ["nodejs", "ruby"]
    )
    ok = CommandResult(0, "", "", [])
    fail = CommandResult(1, "", "some error", [])
    runner = FakeRunner(responses={"asdf": fail})
    runner.responses = {}
    calls = iter([ok, fail])
    runner.run = lambda args, **kw: (runner.calls.append(args), next(calls))[1]
    ctx = make_context(runner=runner)

    result = AsdfPluginsStep().run(ctx)

    assert result.status == StepStatus.PARTIAL
    assert "nodejs" in result.detail
    assert "ruby" in result.detail

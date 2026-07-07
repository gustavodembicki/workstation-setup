import pytest

from workstation_setup import exec as exec_module
from workstation_setup.errors import StepError
from workstation_setup.exec import CommandResult, FakeRunner, command_exists, run_command


def test_dry_run_does_not_call_runner_and_returns_synthetic_success():
    runner = FakeRunner()

    result = run_command(runner, ["brew", "install", "zsh"], dry_run=True)

    assert result.ok
    assert runner.calls == []


def test_run_command_returns_result_on_success():
    runner = FakeRunner(default_result=CommandResult(0, "done", "", []))

    result = run_command(runner, ["echo", "hi"])

    assert result.ok
    assert result.stdout == "done"
    assert runner.calls == [["echo", "hi"]]


def test_run_command_raises_step_error_with_stderr_on_failure():
    runner = FakeRunner(default_result=CommandResult(1, "", "boom", []))

    with pytest.raises(StepError) as exc_info:
        run_command(runner, ["false"])

    assert exc_info.value.stderr == "boom"
    assert exc_info.value.command == ["false"]


def test_run_command_does_not_raise_when_check_false():
    runner = FakeRunner(default_result=CommandResult(1, "", "boom", []))

    result = run_command(runner, ["false"], check=False)

    assert not result.ok
    assert result.stderr == "boom"


def test_fake_runner_returns_per_command_response():
    runner = FakeRunner(
        responses={"brew": CommandResult(0, "1.2.3", "", [])},
        default_result=CommandResult(1, "", "not found", []),
    )

    brew_result = run_command(runner, ["brew", "--version"])
    other_result = run_command(runner, ["missing-tool"], check=False)

    assert brew_result.stdout == "1.2.3"
    assert other_result.returncode == 1


def test_command_exists_uses_shutil_which(monkeypatch):
    def fake_which(name):
        return "/usr/bin/git" if name == "git" else None

    monkeypatch.setattr(exec_module.shutil, "which", fake_which)

    assert command_exists("git") is True
    assert command_exists("nonexistent-tool") is False

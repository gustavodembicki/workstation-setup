from pathlib import Path

from factories import make_context

from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.steps import shell as shell_module
from workstation_setup.steps.base import StepStatus
from workstation_setup.steps.shell import (
    InstallOhMyZshStep,
    InstallPowerlevel10kStep,
    InstallZshStep,
    SetDefaultShellStep,
)


def test_zsh_check_installed_true_when_command_exists(monkeypatch):
    monkeypatch.setattr(shell_module, "command_exists", lambda name: True)

    assert InstallZshStep().check_installed(make_context()) == StepStatus.ALREADY_INSTALLED


def test_zsh_check_installed_false_when_missing(monkeypatch):
    monkeypatch.setattr(shell_module, "command_exists", lambda name: False)

    assert InstallZshStep().check_installed(make_context()) == StepStatus.NOT_INSTALLED


def test_zsh_run_installs_via_brew(monkeypatch):
    installed = []
    monkeypatch.setattr(
        BrewProvider, "install", lambda self, ctx, pkg, cask=False: installed.append(pkg)
    )

    result = InstallZshStep().run(make_context())

    assert installed == ["zsh"]
    assert result.status == StepStatus.INSTALLED


def test_oh_my_zsh_check_installed_true_when_dir_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / ".oh-my-zsh").mkdir()

    assert InstallOhMyZshStep().check_installed(make_context()) == StepStatus.ALREADY_INSTALLED


def test_oh_my_zsh_check_installed_false_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert InstallOhMyZshStep().check_installed(make_context()) == StepStatus.NOT_INSTALLED


def test_oh_my_zsh_run_uses_bash_installer():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    result = InstallOhMyZshStep().run(ctx)

    [call] = runner.calls
    assert call[0] == "/bin/bash"
    assert result.status == StepStatus.INSTALLED


def test_p10k_appends_source_line_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(BrewProvider, "install", lambda self, ctx, pkg, cask=False: None)

    InstallPowerlevel10kStep().run(make_context())

    assert (tmp_path / ".zshrc").read_text().strip() == shell_module.P10K_SOURCE_LINE


def test_p10k_run_is_idempotent_does_not_duplicate_line(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(BrewProvider, "install", lambda self, ctx, pkg, cask=False: None)
    zshrc = tmp_path / ".zshrc"
    zshrc.write_text(shell_module.P10K_SOURCE_LINE + "\n")

    InstallPowerlevel10kStep().run(make_context())

    assert zshrc.read_text().count(shell_module.P10K_SOURCE_LINE) == 1


def test_p10k_check_installed_already_when_brew_installed_and_wired(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(BrewProvider, "is_installed", lambda self, ctx, pkg: True)
    (tmp_path / ".zshrc").write_text(shell_module.P10K_SOURCE_LINE + "\n")

    status = InstallPowerlevel10kStep().check_installed(make_context())

    assert status == StepStatus.ALREADY_INSTALLED


def test_set_default_shell_already_installed_when_shell_matches(monkeypatch):
    monkeypatch.setattr(shell_module.shutil, "which", lambda name: "/opt/homebrew/bin/zsh")
    monkeypatch.setenv("SHELL", "/opt/homebrew/bin/zsh")

    status = SetDefaultShellStep().check_installed(make_context())

    assert status == StepStatus.ALREADY_INSTALLED


def test_set_default_shell_not_installed_when_shell_differs(monkeypatch):
    monkeypatch.setattr(shell_module.shutil, "which", lambda name: "/opt/homebrew/bin/zsh")
    monkeypatch.setenv("SHELL", "/bin/bash")

    status = SetDefaultShellStep().check_installed(make_context())

    assert status == StepStatus.NOT_INSTALLED


def test_set_default_shell_run_calls_chsh_without_touching_real_shells_file(tmp_path, monkeypatch):
    monkeypatch.setattr(shell_module.shutil, "which", lambda name: "/opt/homebrew/bin/zsh")
    # Point at a tmp file so this test never touches the real /etc/shells.
    monkeypatch.setattr(shell_module, "SHELLS_FILE", tmp_path / "shells")
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    result = SetDefaultShellStep().run(ctx)

    assert runner.calls == [["chsh", "-s", "/opt/homebrew/bin/zsh"]]
    assert result.detail == "/opt/homebrew/bin/zsh"


def test_set_default_shell_adds_to_shells_file_when_entry_missing(tmp_path, monkeypatch):
    shells_file = tmp_path / "shells"
    shells_file.write_text("/bin/bash\n")
    monkeypatch.setattr(shell_module.shutil, "which", lambda name: "/opt/homebrew/bin/zsh")
    monkeypatch.setattr(shell_module, "SHELLS_FILE", shells_file)
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    SetDefaultShellStep().run(ctx)

    assert runner.calls[0][0] == "sudo"
    assert runner.calls[1] == ["chsh", "-s", "/opt/homebrew/bin/zsh"]

from pathlib import Path

import pytest
from factories import make_context

from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.steps import shell as shell_module
from workstation_setup.steps.base import StepStatus
from workstation_setup.steps.shell import (
    ConfigureZshThemeStep,
    InstallOhMyZshStep,
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


def test_zsh_run_reinstall_uses_brew_reinstall(monkeypatch):
    reinstalled = []

    def fail_install(self, ctx, pkg, cask=False):
        pytest.fail("should not install")

    monkeypatch.setattr(BrewProvider, "install", fail_install)
    monkeypatch.setattr(
        BrewProvider, "reinstall", lambda self, ctx, pkg, cask=False: reinstalled.append(pkg)
    )

    result = InstallZshStep().run(make_context(), reinstall=True)

    assert reinstalled == ["zsh"]
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


def test_zsh_theme_check_installed_when_p10k_source_line_present(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / ".zshrc").write_text(shell_module.P10K_SOURCE_LINE + "\n")

    assert ConfigureZshThemeStep().check_installed(make_context()) == StepStatus.ALREADY_INSTALLED


def test_zsh_theme_check_installed_when_zsh_theme_line_present(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / ".zshrc").write_text('ZSH_THEME="robbyrussell"\n')

    assert ConfigureZshThemeStep().check_installed(make_context()) == StepStatus.ALREADY_INSTALLED


def test_zsh_theme_check_not_installed_when_no_theme_configured(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert ConfigureZshThemeStep().check_installed(make_context()) == StepStatus.NOT_INSTALLED


def test_zsh_theme_p10k_appends_source_line(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(BrewProvider, "install", lambda self, ctx, pkg, cask=False: None)
    monkeypatch.setattr(shell_module.prompts, "text_input", lambda msg, **kw: "powerlevel10k")

    ConfigureZshThemeStep().run(make_context())

    assert (tmp_path / ".zshrc").read_text().strip() == shell_module.P10K_SOURCE_LINE


def test_zsh_theme_p10k_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(BrewProvider, "install", lambda self, ctx, pkg, cask=False: None)
    monkeypatch.setattr(shell_module.prompts, "text_input", lambda msg, **kw: "powerlevel10k")
    zshrc = tmp_path / ".zshrc"
    zshrc.write_text(shell_module.P10K_SOURCE_LINE + "\n")

    ConfigureZshThemeStep().run(make_context())

    assert zshrc.read_text().count(shell_module.P10K_SOURCE_LINE) == 1


def test_zsh_theme_bundled_writes_zsh_theme_line(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(shell_module.prompts, "text_input", lambda msg, **kw: "robbyrussell")

    ConfigureZshThemeStep().run(make_context())

    assert (tmp_path / ".zshrc").read_text().strip() == 'ZSH_THEME="robbyrussell"'


def test_zsh_theme_bundled_replaces_existing_zsh_theme_line(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(shell_module.prompts, "text_input", lambda msg, **kw: "agnoster")
    zshrc = tmp_path / ".zshrc"
    zshrc.write_text('ZSH_THEME="robbyrussell"\n')

    ConfigureZshThemeStep().run(make_context())

    assert zshrc.read_text().strip() == 'ZSH_THEME="agnoster"'


def test_zsh_theme_bundled_does_not_brew_install(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(shell_module.prompts, "text_input", lambda msg, **kw: "robbyrussell")
    installed = []
    monkeypatch.setattr(
        BrewProvider, "install", lambda self, ctx, pkg, cask=False: installed.append(pkg)
    )

    ConfigureZshThemeStep().run(make_context())

    assert installed == []


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

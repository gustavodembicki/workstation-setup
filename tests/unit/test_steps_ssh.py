from pathlib import Path

from factories import make_context

from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.steps import ssh as ssh_module
from workstation_setup.steps.base import StepStatus
from workstation_setup.steps.ssh import GenerateSshKeyStep


def _home(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def test_is_applicable_only_when_gh_installed(monkeypatch):
    monkeypatch.setattr(ssh_module, "command_exists", lambda name: False)

    assert GenerateSshKeyStep().is_applicable(make_context()) is False


def test_check_installed_true_when_key_exists(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519").write_text("fake-private-key")

    status = GenerateSshKeyStep().check_installed(make_context())

    assert status == StepStatus.ALREADY_INSTALLED


def test_check_installed_false_when_no_key(tmp_path, monkeypatch):
    _home(tmp_path, monkeypatch)

    assert GenerateSshKeyStep().check_installed(make_context()) == StepStatus.NOT_INSTALLED


def test_run_declines_overwrite_when_key_exists(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519").write_text("existing-key")
    monkeypatch.setattr(ssh_module.prompts, "confirm_step", lambda msg, default=True: False)
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    result = GenerateSshKeyStep().run(ctx)

    assert result.status == StepStatus.SKIPPED_BY_USER
    assert runner.calls == []


def test_run_generates_key_and_prints_manual_instructions_when_not_authenticated(
    tmp_path, monkeypatch
):
    home = _home(tmp_path, monkeypatch)
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519.pub").write_text("ssh-ed25519 AAAAfake user@host")
    monkeypatch.setattr(ssh_module.prompts, "confirm_step", lambda msg, default=True: True)
    monkeypatch.setattr(ssh_module.prompts, "text_input", lambda msg, default="": default)
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    result = GenerateSshKeyStep().run(ctx)

    assert result.status == StepStatus.INSTALLED
    assert runner.calls[0][0] == "ssh-keygen"
    assert runner.calls[1] == ["ssh-add", str(ssh_dir / "id_ed25519")]
    assert not any(call[0] == "gh" for call in runner.calls)


def test_run_uploads_to_github_when_authenticated_and_confirmed(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519.pub").write_text("ssh-ed25519 AAAAfake user@host")
    monkeypatch.setattr(ssh_module.prompts, "confirm_step", lambda msg, default=True: True)
    monkeypatch.setattr(ssh_module.prompts, "text_input", lambda msg, default="": default)
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)
    ctx.selections["gh_authenticated"] = True

    result = GenerateSshKeyStep().run(ctx)

    assert result.status == StepStatus.INSTALLED
    assert "uploaded to GitHub" in result.detail
    assert any(call[:3] == ["gh", "ssh-key", "add"] for call in runner.calls)


def test_run_reports_partial_when_github_upload_fails(tmp_path, monkeypatch):
    home = _home(tmp_path, monkeypatch)
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir()
    (ssh_dir / "id_ed25519.pub").write_text("ssh-ed25519 AAAAfake user@host")
    monkeypatch.setattr(ssh_module.prompts, "confirm_step", lambda msg, default=True: True)
    monkeypatch.setattr(ssh_module.prompts, "text_input", lambda msg, default="": default)

    def fake_run(args, *, input=None, env=None, capture=True):
        if args[0] == "gh":
            return CommandResult(1, "", "key already in use", args)
        return CommandResult(0, "", "", args)

    runner = FakeRunner()
    runner.run = fake_run
    ctx = make_context(runner=runner)
    ctx.selections["gh_authenticated"] = True

    result = GenerateSshKeyStep().run(ctx)

    assert result.status == StepStatus.PARTIAL
    assert "upload failed" in result.detail


def test_dry_run_preview_mentions_keygen_and_conditional_upload():
    preview = GenerateSshKeyStep().dry_run_preview(make_context())

    assert any("ssh-keygen" in line for line in preview)
    assert any("gh ssh-key add" in line for line in preview)

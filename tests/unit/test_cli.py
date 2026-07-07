from click.testing import CliRunner
from factories import make_os_info

from workstation_setup import cli
from workstation_setup.state import State


def test_version_flag_prints_version(monkeypatch):
    result = CliRunner().invoke(cli.main, ["--version"])

    assert result.exit_code == 0
    assert "workstation-setup" in result.output


def test_main_runs_empty_pipeline_without_touching_real_state(monkeypatch):
    saved: list[State] = []
    monkeypatch.setattr(cli, "detect_os", lambda: make_os_info(family="linux"))
    monkeypatch.setattr(cli, "load_state", lambda: State())
    monkeypatch.setattr(cli, "save_state", lambda state: saved.append(state))
    monkeypatch.setattr(cli, "STEP_PIPELINE", [])

    result = CliRunner().invoke(cli.main, ["--dry-run"])

    assert result.exit_code == 0
    assert len(saved) == 1


def test_main_exits_early_with_friendly_message_on_unsupported_platform(monkeypatch):
    windows_os_info = make_os_info(family="windows", distro_family=None)
    monkeypatch.setattr(cli, "detect_os", lambda: windows_os_info)

    result = CliRunner().invoke(cli.main)

    assert result.exit_code == 1
    assert "does not support windows" in result.output

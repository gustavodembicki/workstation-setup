from click.testing import CliRunner
from factories import make_os_info

from workstation_setup import cli, log
from workstation_setup.state import State
from workstation_setup.steps.base import Step, StepResult, StepStatus


def _fake_configure(*, dry_run: bool = False) -> None:
    # cli.main() always calls log.configure() first, which by default opens
    # ~/.workstation-setup/run.log for real. Route it through log.reset()
    # instead so CLI tests never touch the real filesystem (same rationale as
    # mocking load_state/save_state below), while keeping a real,
    # stdout-bound Console so CliRunner still captures printed output.
    log.reset()


class FakeStep(Step):
    def __init__(self, id_: str):
        self.id = id_
        self.title = id_
        self.description = f"Install {id_}"
        self.run_called = False

    def check_installed(self, ctx):
        return StepStatus.NOT_INSTALLED

    def run(self, ctx, *, reinstall: bool = False):
        self.run_called = True
        return StepResult(StepStatus.INSTALLED)


def _common_monkeypatches(monkeypatch, *, saved: list[State]):
    monkeypatch.setattr(cli.log, "configure", _fake_configure)
    monkeypatch.setattr(cli, "detect_os", lambda: make_os_info(family="linux"))
    monkeypatch.setattr(cli, "load_state", lambda: State())
    monkeypatch.setattr(cli, "save_state", lambda state: saved.append(state))
    monkeypatch.setattr(cli, "ensure_brew_on_path", lambda os_info: None)


def test_version_flag_prints_version():
    result = CliRunner().invoke(cli.main, ["--version"])

    assert result.exit_code == 0
    assert "workstation-setup" in result.output


def test_main_runs_on_windows_when_winget_is_available(monkeypatch):
    saved: list[State] = []
    monkeypatch.setattr(cli.log, "configure", _fake_configure)
    monkeypatch.setattr(
        cli,
        "detect_os",
        lambda: make_os_info(
            family="windows",
            distro_family=None,
            distro_name="Windows",
            arch="AMD64",
        ),
    )
    monkeypatch.setattr(cli, "load_state", lambda: State())
    monkeypatch.setattr(cli, "save_state", lambda state: saved.append(state))
    monkeypatch.setattr(cli, "refresh_windows_path", lambda: None)
    monkeypatch.setattr(cli.WingetProvider, "is_available", lambda self, ctx: True)
    monkeypatch.setattr(cli, "RECOMMENDED_PIPELINE", [])
    monkeypatch.setattr(cli, "MASTER_REGISTRY", [])
    monkeypatch.setattr(cli.wizard, "run_menu", lambda ctx, steps: [])

    result = CliRunner().invoke(cli.main)

    assert result.exit_code == 0
    assert "windows" in result.output.lower()
    assert len(saved) == 1


def test_main_exits_with_guidance_when_winget_is_missing(monkeypatch):
    monkeypatch.setattr(cli.log, "configure", _fake_configure)
    monkeypatch.setattr(
        cli,
        "detect_os",
        lambda: make_os_info(
            family="windows",
            distro_family=None,
            distro_name="Windows",
            arch="AMD64",
        ),
    )
    monkeypatch.setattr(cli, "load_state", lambda: State())
    monkeypatch.setattr(cli, "refresh_windows_path", lambda: None)
    monkeypatch.setattr(cli.WingetProvider, "is_available", lambda self, ctx: False)

    result = CliRunner().invoke(cli.main)

    assert result.exit_code == 1
    assert "winget is required" in result.output.lower()
    assert "app installer" in result.output.lower()


def test_main_rejects_windows_arm64(monkeypatch):
    monkeypatch.setattr(cli.log, "configure", _fake_configure)
    monkeypatch.setattr(
        cli,
        "detect_os",
        lambda: make_os_info(family="windows", distro_family=None, arch="ARM64"),
    )

    result = CliRunner().invoke(cli.main)

    assert result.exit_code == 1
    assert "windows x64 only" in result.output.lower()


def test_main_with_yes_and_no_only_does_nothing_but_still_saves_state(monkeypatch):
    saved: list[State] = []
    _common_monkeypatches(monkeypatch, saved=saved)
    monkeypatch.setattr(cli, "RECOMMENDED_PIPELINE", [])
    monkeypatch.setattr(cli, "MASTER_REGISTRY", [])

    result = CliRunner().invoke(cli.main, ["--yes"])

    assert result.exit_code == 0
    assert "nothing to run" in result.output.lower()
    assert len(saved) == 1


def test_main_with_yes_and_only_runs_the_requested_step_directly(monkeypatch):
    saved: list[State] = []
    _common_monkeypatches(monkeypatch, saved=saved)
    target = FakeStep("chrome")
    other = FakeStep("slack")
    monkeypatch.setattr(cli, "RECOMMENDED_PIPELINE", [])
    monkeypatch.setattr(cli, "MASTER_REGISTRY", [target, other])

    result = CliRunner().invoke(cli.main, ["--yes", "--only", "chrome"])

    assert result.exit_code == 0
    assert target.run_called is True
    assert other.run_called is False


def test_main_runs_recommended_pipeline_when_user_accepts_the_prompt(monkeypatch):
    saved: list[State] = []
    _common_monkeypatches(monkeypatch, saved=saved)
    recommended = [FakeStep("homebrew")]
    menu_only = [FakeStep("chrome")]
    monkeypatch.setattr(cli, "RECOMMENDED_PIPELINE", recommended)
    monkeypatch.setattr(cli, "MASTER_REGISTRY", recommended + menu_only)
    monkeypatch.setattr(cli.prompts, "confirm_step", lambda message, default=True: True)

    calls = []
    monkeypatch.setattr(
        cli.wizard, "run_recommended", lambda ctx, steps: calls.append(("recommended", steps))
    )
    monkeypatch.setattr(cli.wizard, "run_menu", lambda ctx, steps: calls.append(("menu", steps)))

    result = CliRunner().invoke(cli.main)

    assert result.exit_code == 0
    assert calls == [("recommended", recommended), ("menu", recommended + menu_only)]


def test_main_skips_recommended_pipeline_when_user_declines_the_prompt(monkeypatch):
    saved: list[State] = []
    _common_monkeypatches(monkeypatch, saved=saved)
    recommended = [FakeStep("homebrew")]
    monkeypatch.setattr(cli, "RECOMMENDED_PIPELINE", recommended)
    monkeypatch.setattr(cli, "MASTER_REGISTRY", recommended)
    monkeypatch.setattr(cli.prompts, "confirm_step", lambda message, default=True: False)

    calls = []
    monkeypatch.setattr(
        cli.wizard, "run_recommended", lambda ctx, steps: calls.append(("recommended", steps))
    )
    monkeypatch.setattr(cli.wizard, "run_menu", lambda ctx, steps: calls.append(("menu", steps)))

    result = CliRunner().invoke(cli.main)

    assert result.exit_code == 0
    assert calls == [("menu", recommended)]


def test_main_does_not_ask_about_recommended_bootstrap_when_nothing_to_recommend(monkeypatch):
    saved: list[State] = []
    _common_monkeypatches(monkeypatch, saved=saved)
    menu_only = [FakeStep("chrome")]
    monkeypatch.setattr(cli, "RECOMMENDED_PIPELINE", [])
    monkeypatch.setattr(cli, "MASTER_REGISTRY", menu_only)

    def confirm_step(message, default=True):
        raise AssertionError("should not ask when there's nothing recommended to run")

    monkeypatch.setattr(cli.prompts, "confirm_step", confirm_step)
    monkeypatch.setattr(cli.wizard, "run_recommended", lambda ctx, steps: None)
    monkeypatch.setattr(cli.wizard, "run_menu", lambda ctx, steps: [])

    result = CliRunner().invoke(cli.main)

    assert result.exit_code == 0


def test_only_and_skip_filter_the_master_registry(monkeypatch):
    saved: list[State] = []
    _common_monkeypatches(monkeypatch, saved=saved)
    a, b, c = FakeStep("a"), FakeStep("b"), FakeStep("c")
    monkeypatch.setattr(cli, "RECOMMENDED_PIPELINE", [a, b, c])
    monkeypatch.setattr(cli, "MASTER_REGISTRY", [a, b, c])
    monkeypatch.setattr(cli.prompts, "confirm_step", lambda message, default=True: True)

    calls = []
    monkeypatch.setattr(
        cli.wizard, "run_recommended", lambda ctx, steps: calls.append(("recommended", steps))
    )
    monkeypatch.setattr(cli.wizard, "run_menu", lambda ctx, steps: calls.append(("menu", steps)))

    CliRunner().invoke(cli.main, ["--skip", "b"])

    (_, recommended_steps), (_, menu_steps) = calls
    assert [s.id for s in recommended_steps] == ["a", "c"]
    assert [s.id for s in menu_steps] == ["a", "c"]

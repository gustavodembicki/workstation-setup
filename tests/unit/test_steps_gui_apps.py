from pathlib import Path

from factories import make_context, make_os_info

from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.registry.models import AppSpec, InstallMethod
from workstation_setup.steps import gui_apps as gui_apps_module
from workstation_setup.steps.base import StepStatus
from workstation_setup.steps.gui_apps import (
    _execute_install_method,
    _pick_linux_method,
    install_app,
    run_selection_step,
)


def make_spec(**overrides) -> AppSpec:
    defaults = dict(
        id="thing",
        display_name="Thing",
        check=lambda ctx: False,
        macos=InstallMethod("brew_cask", "thing"),
        linux=[InstallMethod("apt_repo", "thing", distro_family="debian")],
    )
    defaults.update(overrides)
    return AppSpec(**defaults)


def test_pick_linux_method_prefers_distro_specific():
    spec = make_spec(
        linux=[
            InstallMethod("apt_repo", "thing", distro_family="debian"),
            InstallMethod("script", "https://example.com/install.sh", distro_family=None),
        ]
    )
    ctx = make_context(os_info=make_os_info(distro_family="debian"))

    method = _pick_linux_method(ctx, spec)

    assert method.kind == "apt_repo"


def test_pick_linux_method_falls_back_to_generic():
    spec = make_spec(
        linux=[
            InstallMethod("apt_repo", "thing", distro_family="debian"),
            InstallMethod("script", "https://example.com/install.sh", distro_family=None),
        ]
    )
    ctx = make_context(os_info=make_os_info(distro_family="fedora"))

    method = _pick_linux_method(ctx, spec)

    assert method.kind == "script"


def test_pick_linux_method_returns_none_when_no_match():
    spec = make_spec(linux=[InstallMethod("apt_repo", "thing", distro_family="debian")])
    ctx = make_context(os_info=make_os_info(distro_family="arch"))

    assert _pick_linux_method(ctx, spec) is None


def test_execute_brew_cask(monkeypatch):
    calls = []
    monkeypatch.setattr(
        BrewProvider, "install", lambda self, ctx, pkg, cask=False: calls.append((pkg, cask))
    )
    ctx = make_context(os_info=make_os_info(family="macos", distro_family=None))

    _execute_install_method(ctx, InstallMethod("brew_cask", "google-chrome"))

    assert calls == [("google-chrome", True)]


def test_execute_apt_repo_runs_repo_setup_then_installs():
    setup_calls = []
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    _execute_install_method(
        ctx,
        InstallMethod(
            "apt_repo",
            "google-chrome-stable",
            distro_family="debian",
            repo_setup=setup_calls.append,
        ),
    )

    assert setup_calls == [ctx]
    assert ["sudo", "apt-get", "update"] in runner.calls
    assert ["sudo", "apt-get", "install", "-y", "google-chrome-stable"] in runner.calls


def test_execute_deb_download_downloads_then_installs():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    _execute_install_method(ctx, InstallMethod("deb_download", "https://example.com/app.deb"))

    assert runner.calls[0][:2] == ["curl", "-fSL"]
    assert "--progress-bar" in runner.calls[0]
    assert runner.calls[1][:3] == ["sudo", "dpkg", "-i"]


def test_execute_deb_download_falls_back_to_apt_fix_broken_on_dpkg_failure():
    runner = FakeRunner()
    runner.responses["curl"] = CommandResult(0, "", "", [])

    def fake_run(args, *, input=None, env=None, capture=True):
        runner.calls.append(args)
        if args[:2] == ["sudo", "dpkg"]:
            return CommandResult(1, "", "dependency problems", args)
        return CommandResult(0, "", "", args)

    runner.run = fake_run
    ctx = make_context(runner=runner)

    _execute_install_method(ctx, InstallMethod("deb_download", "https://example.com/app.deb"))

    assert ["sudo", "apt-get", "install", "-f", "-y"] in runner.calls


def test_execute_appimage_downloads_to_applications_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    _execute_install_method(ctx, InstallMethod("appimage", "https://example.com/App.AppImage"))

    dest = str(tmp_path / "Applications" / "App.AppImage")
    assert [
        "curl",
        "-fSL",
        "--progress-bar",
        "-o",
        dest,
        "https://example.com/App.AppImage",
    ] in runner.calls
    assert ["chmod", "+x", dest] in runner.calls


def test_execute_script_pipes_curl_to_bash():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    _execute_install_method(ctx, InstallMethod("script", "https://sdk.cloud.google.com"))

    [call] = runner.calls
    assert call[0] == "bash"
    assert "curl -fsSL https://sdk.cloud.google.com | bash" in call[2]


def test_install_app_unsupported_on_linux_when_no_method_matches():
    spec = make_spec(linux=[InstallMethod("apt_repo", "thing", distro_family="debian")])
    ctx = make_context(os_info=make_os_info(family="linux", distro_family="arch"))

    result = install_app(ctx, spec)

    assert result.status == StepStatus.UNSUPPORTED


def test_run_selection_step_no_selection_is_skipped(monkeypatch):
    monkeypatch.setattr(gui_apps_module.prompts, "checkbox_select", lambda msg, choices: [])
    ctx = make_context()

    result = run_selection_step(ctx, "Everyday apps", [make_spec()])

    assert result.status == StepStatus.SKIPPED_BY_USER


def test_run_selection_step_installs_selected_and_reports_success(monkeypatch):
    spec = make_spec(id="thing", display_name="Thing")
    monkeypatch.setattr(gui_apps_module.prompts, "checkbox_select", lambda msg, choices: ["thing"])
    monkeypatch.setattr(
        gui_apps_module,
        "install_app",
        lambda ctx, s: gui_apps_module.StepResult(StepStatus.INSTALLED),
    )
    ctx = make_context()

    result = run_selection_step(ctx, "Everyday apps", [spec])

    assert result.status == StepStatus.INSTALLED
    assert "Thing" in result.detail


def test_run_selection_step_reports_partial_on_individual_failure(monkeypatch):
    from workstation_setup.errors import StepError

    spec = make_spec(id="thing", display_name="Thing")
    monkeypatch.setattr(gui_apps_module.prompts, "checkbox_select", lambda msg, choices: ["thing"])

    def fake_install(ctx, s):
        raise StepError("network error", stderr="timeout")

    monkeypatch.setattr(gui_apps_module, "install_app", fake_install)
    ctx = make_context()

    result = run_selection_step(ctx, "Everyday apps", [spec])

    assert result.status == StepStatus.PARTIAL
    assert "Thing" in result.detail

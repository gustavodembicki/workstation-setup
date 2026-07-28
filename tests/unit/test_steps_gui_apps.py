from pathlib import Path

from factories import make_context, make_os_info

from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers.brew import BrewProvider
from workstation_setup.providers.winget import WingetProvider
from workstation_setup.registry.models import AppSpec, InstallMethod
from workstation_setup.steps import gui_apps
from workstation_setup.steps.base import StepStatus
from workstation_setup.steps.gui_apps import (
    _execute_install_method,
    _pick_linux_method,
    install_app,
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


def test_execute_brew_cask_reinstall_uses_brew_reinstall(monkeypatch):
    calls = []
    monkeypatch.setattr(
        BrewProvider, "reinstall", lambda self, ctx, pkg, cask=False: calls.append((pkg, cask))
    )
    monkeypatch.setattr(
        BrewProvider, "install", lambda self, ctx, pkg, cask=False: (_ for _ in ()).throw(
            AssertionError("should not install")
        ),
    )
    ctx = make_context(os_info=make_os_info(family="macos", distro_family=None))

    _execute_install_method(ctx, InstallMethod("brew_cask", "google-chrome"), reinstall=True)

    assert calls == [("google-chrome", True)]


def test_execute_brew_formula_reinstall_uses_brew_reinstall(monkeypatch):
    calls = []
    monkeypatch.setattr(
        BrewProvider, "reinstall", lambda self, ctx, pkg, cask=False: calls.append(pkg)
    )
    ctx = make_context(os_info=make_os_info(family="macos", distro_family=None))

    _execute_install_method(ctx, InstallMethod("brew_formula", "gcloud-sdk"), reinstall=True)

    assert calls == ["gcloud-sdk"]


def test_execute_apt_repo_runs_repo_setup_then_installs(monkeypatch):
    setup_calls = []
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)
    monkeypatch.setattr(gui_apps, "command_exists", lambda name: True)

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
    assert runner.captures == [False, False]


def test_execute_apt_repo_installs_gnupg_when_missing(monkeypatch):
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)
    monkeypatch.setattr(gui_apps, "command_exists", lambda name: name != "gpg")

    _execute_install_method(ctx, InstallMethod("apt_repo", "thing", repo_setup=lambda ctx: None))

    assert runner.calls[0] == ["sudo", "apt-get", "install", "-y", "gnupg"]


def test_execute_deb_download_downloads_then_installs():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    _execute_install_method(ctx, InstallMethod("deb_download", "https://example.com/app.deb"))

    assert runner.calls[0][:2] == ["curl", "-fSL"]
    assert "--progress-bar" in runner.calls[0]
    assert runner.calls[1][:3] == ["sudo", "dpkg", "-i"]
    assert runner.captures == [False, False]


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
    assert runner.captures == [False]


def test_install_app_unsupported_on_linux_when_no_method_matches():
    spec = make_spec(linux=[InstallMethod("apt_repo", "thing", distro_family="debian")])
    ctx = make_context(os_info=make_os_info(family="linux", distro_family="arch"))

    result = install_app(ctx, spec)

    assert result.status == StepStatus.UNSUPPORTED


def test_install_app_passes_reinstall_through_to_brew(monkeypatch):
    calls = []
    monkeypatch.setattr(
        BrewProvider, "reinstall", lambda self, ctx, pkg, cask=False: calls.append((pkg, cask))
    )
    spec = make_spec(macos=InstallMethod("brew_cask", "thing"))
    ctx = make_context(os_info=make_os_info(family="macos", distro_family=None))

    install_app(ctx, spec, reinstall=True)

    assert calls == [("thing", True)]


def test_execute_winget_reinstall_uses_winget_provider(monkeypatch):
    calls = []
    monkeypatch.setattr(
        WingetProvider, "reinstall", lambda self, ctx, package: calls.append(package)
    )
    ctx = make_context(os_info=make_os_info(family="windows", distro_family=None))

    _execute_install_method(ctx, InstallMethod("winget", "Vendor.Thing"), reinstall=True)

    assert calls == ["Vendor.Thing"]


def test_install_app_uses_windows_method(monkeypatch):
    calls = []
    monkeypatch.setattr(
        WingetProvider, "install", lambda self, ctx, package: calls.append(package)
    )
    spec = make_spec(windows=InstallMethod("winget", "Vendor.Thing"))
    ctx = make_context(os_info=make_os_info(family="windows", distro_family=None))

    result = install_app(ctx, spec)

    assert result.status == StepStatus.INSTALLED
    assert calls == ["Vendor.Thing"]

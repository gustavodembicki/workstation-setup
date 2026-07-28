import pytest
from factories import make_context, make_os_info

from workstation_setup.errors import StepError, UnsupportedPlatformError
from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers import winget as winget_module
from workstation_setup.providers.winget import WingetProvider

WINDOWS = make_os_info(
    family="windows",
    distro_family=None,
    distro_name="Windows",
    version="10.0.26100",
    arch="AMD64",
)


def test_is_available_uses_live_command_detection(monkeypatch):
    monkeypatch.setattr(winget_module, "command_exists", lambda name: name == "winget")

    assert WingetProvider().is_available(make_context(os_info=WINDOWS)) is True


def test_is_installed_queries_exact_package_id():
    runner = FakeRunner(
        default_result=CommandResult(0, "Google Chrome  Google.Chrome  1.0", "", [])
    )
    ctx = make_context(os_info=WINDOWS, runner=runner, dry_run=True)

    assert WingetProvider().is_installed(ctx, "Google.Chrome") is True
    assert runner.calls == [
        ["winget", "list", "--id", "Google.Chrome", "--exact", "--disable-interactivity"]
    ]


def test_is_installed_returns_false_for_no_applications_hresult():
    runner = FakeRunner(default_result=CommandResult(0x8A150014, "", "No package found", []))
    ctx = make_context(os_info=WINDOWS, runner=runner)

    assert WingetProvider().is_installed(ctx, "Google.Chrome") is False


def test_is_installed_propagates_unexpected_failure():
    runner = FakeRunner(default_result=CommandResult(7, "", "source unavailable", []))
    ctx = make_context(os_info=WINDOWS, runner=runner)

    with pytest.raises(StepError, match="Could not inspect"):
        WingetProvider().is_installed(ctx, "Google.Chrome")


def test_install_uses_exact_winget_id_and_streams_output(monkeypatch):
    monkeypatch.setattr(winget_module, "refresh_windows_path", lambda: None)
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(os_info=WINDOWS, runner=runner)

    WingetProvider().install(ctx, "Google.Chrome")

    assert runner.calls == [
        [
            "winget",
            "install",
            "--id",
            "Google.Chrome",
            "--exact",
            "--source",
            "winget",
        ]
    ]
    assert runner.captures == [False]


def test_install_accepts_agreements_only_in_assume_yes_mode(monkeypatch):
    monkeypatch.setattr(winget_module, "refresh_windows_path", lambda: None)
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(os_info=WINDOWS, runner=runner, assume_yes=True)

    WingetProvider().install(ctx, "Google.Chrome")

    call = runner.calls[0]
    assert "--accept-package-agreements" in call
    assert "--accept-source-agreements" in call
    assert "--disable-interactivity" in call


def test_reinstall_forces_winget(monkeypatch):
    monkeypatch.setattr(winget_module, "refresh_windows_path", lambda: None)
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(os_info=WINDOWS, runner=runner)

    WingetProvider().reinstall(ctx, "Google.Chrome")

    assert "--force" in runner.calls[0]


def test_install_rejects_cask():
    with pytest.raises(UnsupportedPlatformError):
        WingetProvider().install(make_context(os_info=WINDOWS), "thing", cask=True)


def test_list_installed_parses_id_column():
    rows = [
        f"{'Name':<22}{'Id':<30}Version",
        "-" * 60,
        f"{'Google Chrome':<22}{'Google.Chrome':<30}1.0",
        f"{'Visual Studio Code':<22}{'Microsoft.VisualStudioCode':<30}2.0",
    ]
    output = "\n".join(rows)
    runner = FakeRunner(default_result=CommandResult(0, output, "", []))
    ctx = make_context(os_info=WINDOWS, runner=runner)

    assert WingetProvider().list_installed(ctx) == {
        "Google.Chrome",
        "Microsoft.VisualStudioCode",
    }

from factories import make_context, make_os_info

from workstation_setup.providers.brew import BrewProvider
from workstation_setup.providers.winget import WingetProvider
from workstation_setup.registry.models import AppSpec, InstallMethod
from workstation_setup.steps.app_spec_step import AppSpecStep
from workstation_setup.steps.base import StepStatus


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


def test_step_identity_mirrors_the_spec():
    spec = make_spec(id="vscode", display_name="VS Code")

    step = AppSpecStep(spec)

    assert step.id == "vscode"
    assert step.title == "VS Code"


def test_check_installed_already_installed_when_spec_check_true():
    spec = make_spec(check=lambda ctx: True)

    assert AppSpecStep(spec).check_installed(make_context()) == StepStatus.ALREADY_INSTALLED


def test_check_installed_not_installed_when_spec_check_false():
    spec = make_spec(check=lambda ctx: False)

    assert AppSpecStep(spec).check_installed(make_context()) == StepStatus.NOT_INSTALLED


def test_run_delegates_to_install_app_with_reinstall_flag(monkeypatch):
    calls = []
    monkeypatch.setattr(
        BrewProvider, "reinstall", lambda self, ctx, pkg, cask=False: calls.append((pkg, cask))
    )
    spec = make_spec(macos=InstallMethod("brew_cask", "thing"))
    ctx = make_context(os_info=make_os_info(family="macos", distro_family=None))

    result = AppSpecStep(spec).run(ctx, reinstall=True)

    assert calls == [("thing", True)]
    assert result.status == StepStatus.INSTALLED


def test_dry_run_preview_describes_macos_method():
    spec = make_spec(macos=InstallMethod("brew_cask", "thing"))
    ctx = make_context(os_info=make_os_info(family="macos", distro_family=None))

    preview = AppSpecStep(spec).dry_run_preview(ctx)

    assert preview == ["brew install --cask thing"]


def test_dry_run_preview_reports_when_linux_has_no_matching_method():
    spec = make_spec(linux=[InstallMethod("apt_repo", "thing", distro_family="debian")])
    ctx = make_context(os_info=make_os_info(family="linux", distro_family="arch"))

    preview = AppSpecStep(spec).dry_run_preview(ctx)

    assert "No install method" in preview[0]


def test_windows_step_is_hidden_without_install_method():
    spec = make_spec(windows=None)
    ctx = make_context(os_info=make_os_info(family="windows", distro_family=None))

    assert AppSpecStep(spec).is_applicable(ctx) is False


def test_windows_check_uses_winget_package_id(monkeypatch):
    checked = []
    monkeypatch.setattr(
        WingetProvider,
        "is_installed",
        lambda self, ctx, package: checked.append(package) or True,
    )
    spec = make_spec(windows=InstallMethod("winget", "Vendor.Thing"))
    ctx = make_context(os_info=make_os_info(family="windows", distro_family=None))

    status = AppSpecStep(spec).check_installed(ctx)

    assert status == StepStatus.ALREADY_INSTALLED
    assert checked == ["Vendor.Thing"]


def test_windows_dry_run_preview_describes_winget():
    spec = make_spec(windows=InstallMethod("winget", "Vendor.Thing"))
    ctx = make_context(os_info=make_os_info(family="windows", distro_family=None))

    assert AppSpecStep(spec).dry_run_preview(ctx) == [
        "winget install --id Vendor.Thing --exact --source winget"
    ]

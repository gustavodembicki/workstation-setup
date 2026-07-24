import pytest
from factories import make_context, make_os_info

from workstation_setup.errors import UnsupportedPlatformError
from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers import brew as brew_module
from workstation_setup.providers.brew import BrewProvider, ensure_brew_on_path, resolve_brew_binary


@pytest.fixture(autouse=True)
def brew_on_path(monkeypatch):
    """Most tests assume `brew` is already resolvable on PATH so calls use
    the literal "brew" command name instead of a resolved absolute path.
    """
    monkeypatch.setattr(brew_module, "command_exists", lambda name: name == "brew")


def test_resolve_brew_binary_macos_arm64():
    path = resolve_brew_binary(make_os_info(family="macos", arch="arm64"))
    assert path == "/opt/homebrew/bin/brew"


def test_resolve_brew_binary_macos_intel():
    assert resolve_brew_binary(make_os_info(family="macos", arch="x86_64")) == "/usr/local/bin/brew"


def test_resolve_brew_binary_linux():
    path = resolve_brew_binary(make_os_info(family="linux"))
    assert path == "/home/linuxbrew/.linuxbrew/bin/brew"


def test_resolve_brew_binary_windows_unsupported():
    with pytest.raises(UnsupportedPlatformError):
        resolve_brew_binary(make_os_info(family="windows", distro_family=None))


def test_is_available_falls_back_to_resolved_path_when_not_on_path(monkeypatch, tmp_path):
    monkeypatch.setattr(brew_module, "command_exists", lambda name: False)
    fake_brew = tmp_path / "brew"
    fake_brew.touch()
    monkeypatch.setattr(brew_module, "resolve_brew_binary", lambda os_info: str(fake_brew))

    ctx = make_context()

    assert BrewProvider().is_available(ctx) is True


def test_is_installed_true_when_brew_list_succeeds():
    ctx = make_context(runner=FakeRunner(default_result=CommandResult(0, "zsh 5.9", "", [])))

    assert BrewProvider().is_installed(ctx, "zsh") is True


def test_is_installed_false_when_brew_list_fails():
    ctx = make_context(runner=FakeRunner(default_result=CommandResult(1, "", "not installed", [])))

    assert BrewProvider().is_installed(ctx, "zsh") is False


def test_install_formula_calls_brew_install():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    BrewProvider().install(ctx, "zsh")

    assert runner.calls == [["brew", "install", "zsh"]]
    assert runner.captures == [False]


def test_install_cask_adds_cask_flag_on_macos():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(
        os_info=make_os_info(family="macos", distro_family=None, arch="arm64"), runner=runner
    )

    BrewProvider().install(ctx, "google-chrome", cask=True)

    assert runner.calls == [["brew", "install", "--cask", "google-chrome"]]
    assert runner.captures == [False]


def test_install_cask_on_linux_raises():
    ctx = make_context()  # linux by default

    with pytest.raises(UnsupportedPlatformError):
        BrewProvider().install(ctx, "google-chrome", cask=True)


def test_reinstall_formula_calls_brew_reinstall():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    BrewProvider().reinstall(ctx, "zsh")

    assert runner.calls == [["brew", "reinstall", "zsh"]]
    assert runner.captures == [False]


def test_reinstall_cask_adds_cask_flag_on_macos():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(
        os_info=make_os_info(family="macos", distro_family=None, arch="arm64"), runner=runner
    )

    BrewProvider().reinstall(ctx, "google-chrome", cask=True)

    assert runner.calls == [["brew", "reinstall", "--cask", "google-chrome"]]
    assert runner.captures == [False]


def test_reinstall_cask_on_linux_raises():
    ctx = make_context()  # linux by default

    with pytest.raises(UnsupportedPlatformError):
        BrewProvider().reinstall(ctx, "google-chrome", cask=True)


def test_list_installed_parses_brew_list_output():
    runner = FakeRunner(default_result=CommandResult(0, "zsh 5.9\nasdf 0.14.0\n", "", []))
    ctx = make_context(runner=runner)

    assert BrewProvider().list_installed(ctx) == {"zsh", "asdf"}


def test_ensure_brew_on_path_prepends_bin_dir(monkeypatch):
    sep = brew_module.os.pathsep
    monkeypatch.setattr(brew_module.os, "environ", {"PATH": "/usr/bin"})

    ensure_brew_on_path(make_os_info(family="linux"))

    assert brew_module.os.environ["PATH"] == f"/home/linuxbrew/.linuxbrew/bin{sep}/usr/bin"


def test_ensure_brew_on_path_is_idempotent(monkeypatch):
    sep = brew_module.os.pathsep
    existing = f"/home/linuxbrew/.linuxbrew/bin{sep}/usr/bin"
    monkeypatch.setattr(brew_module.os, "environ", {"PATH": existing})

    ensure_brew_on_path(make_os_info(family="linux"))

    assert brew_module.os.environ["PATH"] == existing


def test_ensure_brew_on_path_no_op_on_unsupported_platform(monkeypatch):
    monkeypatch.setattr(brew_module.os, "environ", {"PATH": "/usr/bin"})

    ensure_brew_on_path(make_os_info(family="windows", distro_family=None))

    assert brew_module.os.environ["PATH"] == "/usr/bin"

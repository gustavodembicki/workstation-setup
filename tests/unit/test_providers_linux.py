import pytest
from factories import make_context

from workstation_setup.errors import UnsupportedPlatformError
from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.providers.apt import AptProvider
from workstation_setup.providers.dnf import DnfProvider
from workstation_setup.providers.pacman import PacmanProvider

PROVIDERS = [
    (AptProvider(), "dpkg-query"),
    (DnfProvider(), "rpm"),
    (PacmanProvider(), "pacman"),
]


@pytest.mark.parametrize("provider,_", PROVIDERS)
def test_is_installed_true_when_query_succeeds(provider, _):
    ctx = make_context(runner=FakeRunner(default_result=CommandResult(0, "installed", "", [])))

    assert provider.is_installed(ctx, "git") is True


@pytest.mark.parametrize("provider,_", PROVIDERS)
def test_is_installed_false_when_query_fails(provider, _):
    ctx = make_context(runner=FakeRunner(default_result=CommandResult(1, "", "not found", [])))

    assert provider.is_installed(ctx, "git") is False


@pytest.mark.parametrize("provider,_", PROVIDERS)
def test_install_cask_always_unsupported(provider, _):
    ctx = make_context()

    with pytest.raises(UnsupportedPlatformError):
        provider.install(ctx, "git", cask=True)


def test_apt_install_uses_apt_get():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    AptProvider().install(ctx, "git")

    assert runner.calls == [["sudo", "apt-get", "install", "-y", "git"]]
    assert runner.captures == [False]


def test_dnf_install_uses_dnf():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    DnfProvider().install(ctx, "git")

    assert runner.calls == [["sudo", "dnf", "install", "-y", "git"]]
    assert runner.captures == [False]


def test_pacman_install_uses_pacman():
    runner = FakeRunner(default_result=CommandResult(0, "", "", []))
    ctx = make_context(runner=runner)

    PacmanProvider().install(ctx, "git")

    assert runner.calls == [["sudo", "pacman", "-S", "--noconfirm", "git"]]
    assert runner.captures == [False]


def test_apt_list_installed_parses_dpkg_query_output():
    runner = FakeRunner(default_result=CommandResult(0, "git\ncurl\n", "", []))
    ctx = make_context(runner=runner)

    assert AptProvider().list_installed(ctx) == {"git", "curl"}


def test_dnf_list_installed_parses_rpm_qa_output():
    runner = FakeRunner(default_result=CommandResult(0, "git\ncurl\n", "", []))
    ctx = make_context(runner=runner)

    assert DnfProvider().list_installed(ctx) == {"git", "curl"}


def test_pacman_list_installed_parses_pacman_qq_output():
    runner = FakeRunner(default_result=CommandResult(0, "git\ncurl\n", "", []))
    ctx = make_context(runner=runner)

    assert PacmanProvider().list_installed(ctx) == {"git", "curl"}

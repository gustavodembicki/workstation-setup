import pytest
from factories import make_context, make_os_info

from workstation_setup.steps.asdf import AsdfPluginsStep, InstallAsdfStep
from workstation_setup.steps.homebrew import InstallHomebrewStep
from workstation_setup.steps.shell import (
    ConfigureZshThemeStep,
    InstallOhMyZshStep,
    InstallZshStep,
    SetDefaultShellStep,
)


@pytest.mark.parametrize(
    "step",
    [
        InstallHomebrewStep(),
        InstallZshStep(),
        InstallOhMyZshStep(),
        ConfigureZshThemeStep(),
        SetDefaultShellStep(),
        InstallAsdfStep(),
        AsdfPluginsStep(),
    ],
)
def test_unix_bootstrap_steps_are_hidden_on_windows(step):
    ctx = make_context(
        os_info=make_os_info(family="windows", distro_family=None, arch="AMD64")
    )

    assert step.is_applicable(ctx) is False

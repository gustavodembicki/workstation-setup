from workstation_setup.context import RunContext
from workstation_setup.exec import CommandResult, FakeRunner
from workstation_setup.os_detect import OSInfo
from workstation_setup.state import State


def make_os_info(**overrides) -> OSInfo:
    defaults = dict(
        family="linux",
        distro_family="debian",
        distro_name="Ubuntu",
        version="24.04",
        arch="x86_64",
    )
    defaults.update(overrides)
    return OSInfo(**defaults)


def make_context(**overrides) -> RunContext:
    defaults = dict(
        os_info=make_os_info(),
        runner=FakeRunner(default_result=CommandResult(0, "ok", "", [])),
        state=State(),
    )
    defaults.update(overrides)
    return RunContext(**defaults)

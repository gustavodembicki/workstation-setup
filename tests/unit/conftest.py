import pytest

from workstation_setup import log


@pytest.fixture(autouse=True)
def _reset_log():
    log.reset()
    yield
    log.reset()

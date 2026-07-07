from factories import make_context

from workstation_setup.steps import ides as ides_module
from workstation_setup.steps.base import StepResult, StepStatus
from workstation_setup.steps.ides import IdeSelectionStep


def test_run_delegates_to_shared_selection_helper_with_ide_registry(monkeypatch):
    captured = {}

    def fake_run_selection_step(ctx, title, registry):
        captured["title"] = title
        captured["registry"] = registry
        return StepResult(StepStatus.INSTALLED, detail="ok")

    monkeypatch.setattr(ides_module, "run_selection_step", fake_run_selection_step)
    ctx = make_context()

    result = IdeSelectionStep().run(ctx)

    assert result.status == StepStatus.INSTALLED
    assert captured["title"] == "IDEs"
    assert captured["registry"] is ides_module.IDE_REGISTRY


def test_check_installed_always_offers_the_step():
    assert IdeSelectionStep().check_installed(make_context()) == StepStatus.NOT_INSTALLED

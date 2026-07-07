from __future__ import annotations

from typing import TYPE_CHECKING

from workstation_setup.registry.ides import IDE_REGISTRY
from workstation_setup.steps.base import Step, StepResult, StepStatus
from workstation_setup.steps.gui_apps import run_selection_step

if TYPE_CHECKING:
    from workstation_setup.context import RunContext


class IdeSelectionStep(Step):
    id = "ides"
    title = "IDEs"
    description = "Pick which IDEs to install: JetBrains Toolbox, VS Code, Windsurf, Cursor."

    def check_installed(self, ctx: RunContext) -> StepStatus:
        # Always offered — re-running lets the user add IDEs they skipped before.
        return StepStatus.NOT_INSTALLED

    def run(self, ctx: RunContext) -> StepResult:
        return run_selection_step(ctx, self.title, IDE_REGISTRY)

    def dry_run_preview(self, ctx: RunContext) -> list[str]:
        return [f"Prompt to select from: {', '.join(s.display_name for s in IDE_REGISTRY)}"]

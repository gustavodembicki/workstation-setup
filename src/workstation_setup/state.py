from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

STATE_VERSION = 1
DEFAULT_STATE_PATH = Path.home() / ".workstation-setup" / "state.json"


@dataclass
class StepRecord:
    status: str
    last_run: str
    detail: str | None = None


@dataclass
class State:
    version: int = STATE_VERSION
    steps: dict[str, StepRecord] = field(default_factory=dict)

    def record(self, step_id: str, status: str, detail: str | None = None) -> None:
        self.steps[step_id] = StepRecord(
            status=status,
            last_run=datetime.now(UTC).isoformat(),
            detail=detail,
        )


def load_state(path: Path = DEFAULT_STATE_PATH) -> State:
    if not path.exists():
        return State()

    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return State()

    steps = {
        step_id: StepRecord(**record) for step_id, record in raw.get("steps", {}).items()
    }
    return State(version=raw.get("version", STATE_VERSION), steps=steps)


def save_state(state: State, path: Path = DEFAULT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": state.version,
        "steps": {step_id: asdict(record) for step_id, record in state.steps.items()},
    }
    path.write_text(json.dumps(payload, indent=2))

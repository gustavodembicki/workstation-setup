from workstation_setup.state import State, load_state, save_state


def test_load_state_returns_empty_state_when_file_missing(tmp_path):
    state = load_state(tmp_path / "nonexistent" / "state.json")

    assert state.version == 1
    assert state.steps == {}


def test_save_and_load_state_round_trip(tmp_path):
    path = tmp_path / "state.json"
    state = State()
    state.record("homebrew", "already_installed", detail="brew 4.3.0")

    save_state(state, path)
    loaded = load_state(path)

    assert loaded.steps["homebrew"].status == "already_installed"
    assert loaded.steps["homebrew"].detail == "brew 4.3.0"
    assert loaded.steps["homebrew"].last_run


def test_load_state_recovers_from_corrupt_json(tmp_path):
    path = tmp_path / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not valid json {")

    state = load_state(path)

    assert state.steps == {}

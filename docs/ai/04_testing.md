# 04 — Testing

## Two tiers, on purpose

- **`tests/unit/`** — runs under plain `pytest`, in CI, on every push. No real subprocess calls, no real filesystem mutation outside `tmp_path`. This is where correctness of the *decision logic* (idempotency checks, dispatch logic, wizard orchestration, registry shape) is verified.
- **`tests/integration/`** — **not** collected by `pytest` (`pyproject.toml`'s `testpaths` is `["tests/unit"]`). Real installers are inherently slow, environment-mutating, and sometimes interactive (`gh auth login`, `chsh`). Verified manually, in a disposable Docker container (or a scratch VM for macOS) before cutting a release. See `tests/integration/README.md`.

Do not try to make real `brew install` / `chsh` / `ssh-keygen` calls pass under `pytest` — mock the `Runner`, as below.

## The core test pattern: `FakeRunner` + `make_context`

`tests/unit/factories.py` provides `make_context(**overrides)` and `make_os_info(**overrides)` — always use these instead of constructing `RunContext`/`OSInfo` by hand, so every test starts from the same sane defaults (Linux/debian, a `FakeRunner` that returns success for everything by default).

```python
from factories import make_context
from workstation_setup.exec import CommandResult, FakeRunner

def test_something():
    runner = FakeRunner(default_result=CommandResult(0, "some stdout", "", []))
    ctx = make_context(runner=runner)

    result = SomeStep().run(ctx)

    assert runner.calls == [["expected", "argv"]]   # FakeRunner records every call verbatim
    assert result.status == StepStatus.INSTALLED
```

For a command whose behavior needs to differ based on its arguments (e.g. "gh succeeds but the follow-up upload fails"), swap in a custom `runner.run` function:

```python
def fake_run(args, *, input=None, env=None, capture=True):
    if args[0] == "gh":
        return CommandResult(1, "", "some error", args)
    return CommandResult(0, "", "", args)

runner = FakeRunner()
runner.run = fake_run
```

## Logging in tests: `log.reset()`, not dependency injection

`workstation_setup.log` is a module-level singleton (see [01_architecture.md](01_architecture.md)), not a `RunContext` field, so it isn't faked by passing something into `make_context()`. Isolation instead comes from an autouse fixture in `tests/unit/conftest.py` that calls `log.reset()` before and after every test — this swaps in a fresh `Console(record=True)` and clears any file/failure state, so tests never see another test's output and never touch `~/.workstation-setup/run.log`. You don't need to do anything extra in most tests; it's automatic.

The one place this bites: **`cli.main()` itself calls `log.configure()`**, which by default opens the real `~/.workstation-setup/run.log`. `tests/unit/test_cli.py` monkeypatches `cli.log.configure` to call `log.reset()` instead (see `_fake_configure`) so `CliRunner().invoke(cli.main, ...)` never writes to the real filesystem — apply the same pattern if you add new tests that invoke `cli.main` directly.

If a test needs to assert on printed content, use `log.console_export()` (requires `record=True`, which is what `reset()` sets up).

## Monkeypatching rules that matter

- **Patch the module attribute, not the imported name.** If `steps/asdf.py` does `from workstation_setup.exec import command_exists`, you must patch `workstation_setup.steps.asdf.command_exists` (imported into asdf.py's own namespace) — patching `workstation_setup.exec.command_exists` has no effect, because `asdf.py` already holds its own reference. Same applies to `prompts.confirm_step` etc. — steps call `prompts.checkbox_select(...)` (attribute access on the imported module), so patching `some_step_module.prompts.checkbox_select` works correctly.
- **`Path.home()`** — monkeypatch with `monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))` for any step that touches `~/.ssh`, `~/.zshrc`, `~/.oh-my-zsh`, etc. Never let a unit test touch the real home directory.
- **Never let a test touch a real system file path unconditionally present on the test runner** — e.g. `SetDefaultShellStep` reads `/etc/shells` (a file that genuinely exists on real Linux/macOS CI runners!). It's exposed as the module-level `shell.SHELLS_FILE` constant specifically so tests can monkeypatch it to a `tmp_path` file — never assume "it won't exist in the test sandbox," because on real CI runners it does.
- **`os.environ` mutations** (`ensure_brew_on_path`) — monkeypatch `brew_module.os.environ` to a fresh dict per test, don't mutate the real process environment from a unit test.
- **Cross-platform path construction** — code that builds a known Unix-style path (Homebrew's install locations) uses `PurePosixPath`, not `Path`, specifically so tests behave the same on a Windows dev machine as they will in production on Linux/macOS. If you add a new hardcoded POSIX path and need to manipulate it (`.parent`, `/`), use `PurePosixPath`, not `Path`.

## Manual/Docker verification (`tests/integration/`)

```bash
docker build -f tests/integration/docker/Dockerfile.ubuntu -t workstation-setup-smoketest .
docker run -it --rm workstation-setup-smoketest
# inside the container:
source .venv/bin/activate
python -m workstation_setup --dry-run      # full preview
python -m workstation_setup --yes --only homebrew --only zsh   # real install, throwaway container
```

This is genuinely valuable, not a formality — it's how the two real bugs mentioned in [02_steps_and_providers.md](02_steps_and_providers.md) (the `$(curl...)` word-splitting issue and the Homebrew-PATH issue) were actually found. Run it after any change to `steps/homebrew.py`, `steps/shell.py`, `steps/asdf.py`, `steps/git_gh.py`, or the install-method dispatch in `steps/gui_apps.py` before considering the change done.

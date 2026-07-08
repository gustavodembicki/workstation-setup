# workstation-setup — Agent Guide

This is a **Python CLI**, packaged with PyInstaller into a single native executable, that bootstraps a fresh Linux or macOS developer workstation. There is no web layer, no database — it's a terminal wizard that shells out to real system tools (Homebrew, apt/dnf/pacman, git, gh, ssh-keygen, ...).

## What this project is

A "format the laptop, run one binary, get a working dev environment" tool. Nothing is mandatory: Homebrew, zsh + Oh My Zsh + Powerlevel10k, asdf (+ plugins), git + GitHub CLI (+ SSH key generation and upload), IDEs (JetBrains Toolbox, VS Code, Windsurf, Cursor), and everyday apps (Chrome, Slack, Spotify, Google Cloud SDK, Devin Desktop) are all just entries in one flat menu of possibilities the user opts into — with a "run the recommended bootstrap first?" fast path offered up front for convenience, not as a gate.

**Tech stack:** Python 3.11+, `click` (CLI), `questionary` (interactive prompts), `rich` (console output), `pytest` (tests), `ruff` (lint/format), `pyinstaller` (packaging).

**Scope:** Linux and macOS only. Windows is explicitly out of scope for v1 — see [`docs/ai/01_architecture.md`](docs/ai/01_architecture.md) for the seam left for a future Windows provider.

**Detailed AI context:** See [`docs/ai/`](docs/ai/README.md) for layered documentation covering architecture, the Step/Provider/Registry model, testing patterns, and packaging/CI.

## Architecture overview

```
cli.py            — click entry point, builds RunContext, owns RECOMMENDED_PIPELINE + MASTER_REGISTRY
wizard.py          — run_recommended() / run_menu(): check_installed → (confirm | ask reinstall/modify/leave/cancel) → run → record state
context.py          — RunContext: os_info, console, runner, dry_run, assume_yes, state, selections

os_detect.py         — detect_os() -> OSInfo(family, distro_family, arch, ...)
exec.py               — the ONLY place subprocess is called from (Runner/FakeRunner, dry-run, StepError)
state.py               — ~/.workstation-setup/state.json — an audit log only, NEVER the source of truth

providers/               — PackageProvider abstraction: brew (primary, both OSes; install + reinstall), apt/dnf/pacman (Linux fallback)
steps/                    — one Step per installable unit (homebrew, shell, asdf, git_gh, ssh, gui_apps dispatcher, app_spec_step adapter)
registry/                  — data-driven AppSpec list for GUI apps + IDEs (the extensibility seam)
ui/                         — thin, mockable wrappers around questionary (prompts.py, incl. select_existing_action) and rich (console.py)
```

**Rule:** Steps never call `subprocess` directly — always through `ctx.run_command(...)`, which itself always goes through `exec.run_command`. This is what makes every Step unit-testable with a `FakeRunner` and makes `--dry-run` work for free.

## Mandatory rules

**Nothing is mandatory, and `ALREADY_INSTALLED` is never a silent skip.** Every Step's `check_installed` must use live detection, never trust `state.json` alone (`state.json` is only an audit log — see [`docs/ai/02_steps_and_providers.md`](docs/ai/02_steps_and_providers.md)). When a Step is already installed, the user is always asked to Reinstall/Modify, Leave as is, or Cancel — never skipped without a prompt. `Step.run(ctx, *, reinstall: bool = False)` — package-style steps (Homebrew formulas/casks) must honor `reinstall=True` by calling `BrewProvider.reinstall` instead of `install`; steps that already reconfigure on every call (shell theme, SSH key, gh auth, asdf plugins) can ignore the flag.

- Every new `Step` needs a test in `tests/unit/test_steps_<name>.py` using the `make_context`/`FakeRunner` pattern from `tests/unit/factories.py` — never a real subprocess call in a unit test.
- Never build a shell command as `["/bin/bash", "-c", "$(curl ... )"]` — without an outer shell, bash word-splits the fetched script into a bogus single command instead of running it. Always pipe: `curl -fsSL <url> | bash`. (This was a real bug found via the Docker smoke test — see git history on `steps/homebrew.py`.)
- After anything that installs Homebrew (or any brew package) within the same process, don't assume the binary is on `PATH` — call `ensure_brew_on_path(os_info)` (in `providers/brew.py`) or resolve the absolute path via `resolve_brew_binary`. Homebrew's own bin directory isn't on `PATH` until a shell rc file is reloaded, which never happens mid-process.
- Never silently swallow a failed command. `exec.run_command` raises `StepError` (with stderr attached) by default; only pass `check=False` when a non-zero exit is a genuinely expected, meaningful outcome (e.g. `gh auth status` when not yet authenticated) — and then branch on it explicitly.
- Confirm before anything destructive/hard-to-reverse: overwriting an existing SSH key, changing the login shell via `chsh`. See `steps/ssh.py` and `steps/shell.py` for the pattern.
- Adding a 6th GUI app or a 5th IDE is a single new `AppSpec` entry in `registry/apps.py` / `registry/ides.py` — never a new branch in `steps/gui_apps.py`'s dispatcher or `steps/app_spec_step.py`'s adapter. See [`docs/ai/03_registry_apps_ides.md`](docs/ai/03_registry_apps_ides.md).

## Project-specific test patterns

```python
# tests/unit/factories.py provides make_context() / make_os_info() — use them, don't hand-roll RunContext
from factories import make_context
from workstation_setup.exec import CommandResult, FakeRunner

def test_some_step_installs_via_brew(monkeypatch):
    installed = []
    monkeypatch.setattr(BrewProvider, "install", lambda self, ctx, pkg, cask=False: installed.append(pkg))
    result = SomeStep().run(make_context())
    assert installed == ["expected-package"]
    assert result.status == StepStatus.INSTALLED

# Steps that call the ui/prompts wrappers — monkeypatch the module attribute, not the imported name:
monkeypatch.setattr(some_step_module.prompts, "confirm_step", lambda msg, default=True: True)

# Steps that touch the real filesystem (~/.zshrc, ~/.ssh/...) — monkeypatch Path.home:
monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
```

## Security invariants — never violate

- SSH private keys are never generated with a forced passphrase — the user is asked, defaulting to passphrase-less for a frictionless bootstrap, but it must remain a real, visible choice.
- An existing SSH key at `~/.ssh/id_ed25519` is never overwritten without an explicit, separate confirmation (distinct from the step's normal "proceed?" prompt) — this is irreversible.
- `gh auth login` and any other genuinely interactive subprocess must run with `capture=False` so it attaches to the real terminal — never silently capture and hide an interactive auth flow.
- Homebrew casks are macOS-only. `BrewProvider.install(..., cask=True)` raises `UnsupportedPlatformError` on Linux rather than silently no-op'ing or crashing with a confusing brew error.

## Running the project

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/unit          # unit suite (fast, no real subprocess calls)
ruff check .                # lint

python -m workstation_setup --dry-run    # full wizard preview, no side effects
python -m workstation_setup --yes --only homebrew   # run a single step for real

pyinstaller packaging/pyinstaller.spec   # build the standalone binary (current OS only — no cross-compile)
```

Manual, real-install verification (not part of `pytest`) lives in `tests/integration/` — see [`docs/ai/04_testing.md`](docs/ai/04_testing.md).

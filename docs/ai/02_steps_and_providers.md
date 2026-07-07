# 02 — Steps and Providers

## The Step contract (`steps/base.py`)

```python
class Step(ABC):
    id: str
    title: str
    description: str

    def is_applicable(self, ctx) -> bool: ...       # default True; override to gate on prior state
    def check_installed(self, ctx) -> StepStatus: ...  # ALWAYS live detection
    def run(self, ctx) -> StepResult: ...              # the real install action
    def dry_run_preview(self, ctx) -> list[str]: ...    # human-readable lines, no side effects
```

`StepStatus`: `ALREADY_INSTALLED`, `NOT_INSTALLED`, `PARTIAL`, `INSTALLED`, `SKIPPED_BY_USER`, `UNSUPPORTED`, `FAILED`.

## Idempotency model — read this before touching `check_installed`

**Live detection is the only source of truth.** `check_installed` must ask the real system ("is `zsh` on PATH?", "does `brew list --versions X` succeed?", "does `~/.ssh/id_ed25519` exist?") — never infer from `state.json`.

`state.json` (`~/.workstation-setup/state.json`, managed by `state.py`) exists only as:
- a **cache** of user choices that can't be re-derived from the filesystem (e.g. "user declined Windsurf last time"), so re-running doesn't re-prompt for everything every time — this is discretionary UX polish, not implemented as a hard skip;
- an **audit log** of what ran and when, for debugging a bad run.

If `state.json` and the live system ever disagree, the live system wins. Concretely: `wizard.run` calls `step.check_installed(ctx)` on every run, unconditionally, regardless of what `state.json` says.

## Why `is_applicable` exists separately from `check_installed`

`is_applicable` answers "should this step even be shown," `check_installed` answers "is it already done." They're different questions:

- `GhAuthLoginStep.is_applicable` → `command_exists("gh")` (no point offering auth if gh isn't installed)
- `GenerateSshKeyStep.is_applicable` → same gate — SSH key generation is only offered once `gh` exists, per the product decision that GitHub is the whole point of the key
- `AsdfPluginsStep.is_applicable` → `command_exists("asdf")`

If `is_applicable` returns `False`, the step is skipped **silently** — no state recorded, no line printed. If `check_installed` returns `ALREADY_INSTALLED`, the step **is** shown, just without a prompt.

## PackageProvider abstraction (`providers/`)

```python
class PackageProvider(Protocol):
    name: str
    def is_available(self, ctx) -> bool: ...
    def is_installed(self, ctx, package: str) -> bool: ...
    def install(self, ctx, package: str, *, cask: bool = False) -> None: ...
    def list_installed(self, ctx) -> set[str]: ...
```

- **`BrewProvider`** (`providers/brew.py`) is the primary provider on **both** macOS and Linux (Linuxbrew). `install(..., cask=True)` raises `UnsupportedPlatformError` on Linux — Homebrew casks are macOS-only, full stop.
- **`AptProvider` / `DnfProvider` / `PacmanProvider`** exist only as the Linux fallback path for GUI apps that have no Homebrew cask equivalent (see [03_registry_apps_ides.md](03_registry_apps_ides.md)). They are not used for the core toolchain (zsh, asdf, git, gh) — those always go through Homebrew for consistency across distros.
- `providers/registry.py`: `get_brew_provider()` (always available, cross-family) vs. `get_system_provider(os_info)` (picks apt/dnf/pacman by `os_info.distro_family`, raises `UnsupportedPlatformError` for unknown distros or non-Linux).

## The PATH gotcha — read this before adding a step that installs a brew package

Homebrew's bin directory (`/opt/homebrew/bin`, `/usr/local/bin`, or `/home/linuxbrew/.linuxbrew/bin`) is **not** on `PATH` until a shell rc file is sourced — which never happens mid-process. Two consequences already handled, keep handling them the same way:

1. **`BrewProvider` invokes `brew` itself via an absolute, resolved path** when it's not yet on `PATH` (`_brew()` / `resolve_brew_binary()`), so `brew install X` always works regardless of `PATH` state.
2. **Anything that shells out to a *brew-installed package's binary* by bare name** (the Oh My Zsh installer invoking `zsh`, `asdf plugin add`, `gh auth login`, ...) needs `PATH` itself updated. That's what `ensure_brew_on_path(os_info)` does — it's called once in `cli.py` at startup (covers "Homebrew was already installed before this run") and again at the end of `InstallHomebrewStep.run()` (covers "Homebrew was just installed in this run"). If you add a new step whose `run()` shells out to a brew-installed binary by name, you don't need to call this yourself — it's already guaranteed to have run before any step in the pipeline gets a chance to execute, as long as `InstallHomebrewStep` stays first in `STEP_PIPELINE`.

This was a real bug caught by the Docker integration smoke test (see [04_testing.md](04_testing.md)): the Oh My Zsh install step failed with "Zsh is not installed" immediately after the zsh step had, in fact, just succeeded — because the new `zsh` binary wasn't resolvable from the current process's `PATH`.

## Another real bug worth knowing about: `$(curl ...)` vs. `curl | bash`

`/bin/bash -c "$(curl -fsSL <url>)"` is the idiom the Homebrew/Oh My Zsh docs show for a terminal — but it only behaves as "run the whole downloaded script" when an **outer shell** performs the `$(...)` substitution before `bash -c` ever starts, handing bash the already-substituted multi-line text as its script argument. Constructed directly as a Python list (`["/bin/bash", "-c", "$(curl ...)"]`, no outer shell involved), bash instead evaluates `$(...)` itself, word-splits the captured output on whitespace/newlines, and tries to exec the *first word* of the script (typically `#!/bin/bash`) as a literal command — which fails.

**Always use the pipe form instead:** `["/bin/bash", "-c", f"curl -fsSL {url} | bash"]`. See `steps/homebrew.py`, `steps/shell.py` (Oh My Zsh), and the `"script"` install-method kind in `steps/gui_apps.py` for the correct pattern.

# 01 — Architecture

## Module map

```
┌──────────────────────────────────────────────────────────┐
│  cli.py                                                   │
│  click entry point · STEP_PIPELINE · builds RunContext    │
└───────────────────────────┬────────────────────────────---┘
                            │ wizard.run(ctx, steps)
┌───────────────────────────▼────────────────────────────---┐
│  wizard.py                                                 │
│  orchestrates Steps: check → confirm → run → record state  │
└──┬──────────────┬──────────────┬──────────────┬───────────┘
   │              │              │              │
┌──▼───┐    ┌─────▼─────┐  ┌─────▼──────┐  ┌────▼─────┐
│steps/│    │providers/  │  │registry/   │  │ui/       │
│one   │───▶│PackageProv-│  │AppSpec /   │  │prompts.py│
│Step  │    │ider: brew, │  │InstallMeth-│  │console.py│
│class │    │apt/dnf/    │  │od (data-   │  │(thin,    │
│per   │    │pacman      │  │driven app/ │  │mockable  │
│unit  │    │            │  │IDE list)   │  │wrappers) │
└──┬───┘    └─────┬──────┘  └────────────┘  └──────────┘
   │              │
   └──────┬───────┘
          │ ctx.run_command(...)
   ┌──────▼───────┐
   │ exec.py       │  the ONLY place subprocess is invoked from
   │ Runner/       │  (SubprocessRunner in prod, FakeRunner in tests)
   │ FakeRunner    │
   └───────────────┘
```

**Rule:** `wizard.py` never knows about brew/apt/curl/etc. — it only knows the `Step` interface. `steps/*.py` never call `subprocess` directly — only `ctx.run_command`. This is what keeps every layer independently testable.

## File tree (key paths only)

```
src/workstation_setup/
├── cli.py                    # entry point, STEP_PIPELINE, --dry-run/--yes/--only/--skip
├── wizard.py                  # orchestration loop
├── context.py                  # RunContext dataclass
├── os_detect.py                 # detect_os() -> OSInfo
├── exec.py                       # run_command/command_exists, Runner/FakeRunner, StepError
├── state.py                       # ~/.workstation-setup/state.json (cache/log, not source of truth)
├── errors.py                       # StepError, AbortError, UnsupportedPlatformError
│
├── providers/
│   ├── base.py                # PackageProvider Protocol
│   ├── brew.py                 # BrewProvider + resolve_brew_binary + ensure_brew_on_path
│   ├── apt.py / dnf.py / pacman.py  # Linux fallback providers
│   └── registry.py              # get_brew_provider() / get_system_provider(os_info)
│
├── steps/
│   ├── base.py                # Step ABC, StepStatus, StepResult
│   ├── homebrew.py              # InstallHomebrewStep
│   ├── shell.py                  # zsh, Oh My Zsh, Powerlevel10k, SetDefaultShellStep
│   ├── asdf.py                    # InstallAsdfStep, AsdfPluginsStep
│   ├── git_gh.py                   # git, gh, gh auth login
│   ├── ssh.py                       # GenerateSshKeyStep
│   ├── ides.py                       # IdeSelectionStep (thin — delegates to gui_apps)
│   └── gui_apps.py                    # install_app() dispatcher + GuiAppsSelectionStep
│
├── registry/
│   ├── models.py               # AppSpec, InstallMethod dataclasses
│   ├── apps.py                  # Chrome, Slack, Spotify, Devin Desktop, GCloud SDK
│   └── ides.py                   # JetBrains Toolbox, VS Code, Windsurf, Cursor
│
└── ui/
    ├── prompts.py              # confirm_step / checkbox_select / text_input (questionary wrappers)
    └── console.py               # print_welcome / print_result / print_summary_table (rich wrappers)

tests/
├── unit/                   # pytest — FakeRunner, no real subprocess calls, mirrors src structure
└── integration/            # NOT run by pytest — manual/Docker verification, see 04_testing.md
```

## Wizard step lifecycle (detailed)

```
1. is_applicable(ctx)?
   False → skip entirely, no state recorded (e.g. SSH step when gh isn't installed)

2. check_installed(ctx) — ALWAYS live detection (command_exists, brew list, file existence...)
   ALREADY_INSTALLED → print + record state, move to next step, no prompt

3. dry_run?
   True → print dry_run_preview(ctx) lines, move to next step, no side effects

4. confirm (unless --yes) → declined → SKIPPED_BY_USER, move to next step

5. run(ctx) — the real install action
   success → print + record state
   StepError → print failure panel, ask "continue with remaining steps?"
     declined → raise AbortError (wizard stops, state saved)
     accepted → record "failed", move to next step anyway

6. after all steps: print summary table, save_state(ctx.state)
```

## Future Windows seam

Not implemented in v1, but the following exist specifically so adding it later doesn't require a rewrite:

- `os_detect.OSInfo.family` is typed as `Literal["linux", "macos", "windows"]` — `detect_os()` already returns `"windows"` correctly, it's just that `cli.py` bails out early when it sees it.
- `registry.models.AppSpec.windows: InstallMethod | None = None` — every registry entry already has the field, just unset.
- `providers.base.PackageProvider` is a `Protocol` — a future `providers/winget.py` implementing it would slot in next to `brew.py`/`apt.py` without touching the interface.

When picking this up: the main work is a `WindowsProvider`, `AppSpec.windows` entries for the existing registry, and a `windows` branch in each `Step.run` that currently only branches on `macos`/`linux` (mainly `steps/homebrew.py`, `steps/shell.py`, `steps/gui_apps.py`).

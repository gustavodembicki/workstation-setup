# 01 — Architecture

## Module map

```
┌──────────────────────────────────────────────────────────┐
│  cli.py                                                   │
│  click entry point · RECOMMENDED_PIPELINE / MASTER_REGISTRY│
│  · builds RunContext                                       │
└───────────────────────────┬────────────────────────────---┘
                 │ wizard.run_recommended(ctx, steps)
                 │ wizard.run_menu(ctx, steps)
┌───────────────────────────▼────────────────────────────---┐
│  wizard.py                                                 │
│  orchestrates Steps: check → (confirm | ask reinstall/     │
│  modify/leave/cancel) → run → record state                 │
└──┬──────────────┬──────────────┬──────────────┬───────────┘
   │              │              │              │
┌──▼───┐    ┌─────▼─────┐  ┌─────▼──────┐  ┌────▼─────┐
│steps/│    │providers/  │  │registry/   │  │ui/       │
│one   │───▶│PackageProv-│  │AppSpec /   │  │prompts.py│
│Step  │    │ider: brew, │  │InstallMeth-│  │(thin,    │
│class │    │apt/dnf/    │  │od (data-   │  │mockable  │
│per   │    │pacman/     │  │driven app/ │  │wrapper   │
│unit  │    │winget      │  │IDE list)   │  │around    │
│      │    │            │  │            │  │questionary)│
└──┬───┘    └─────┬──────┘  └────────────┘  └──────────┘
   │              │
   └──────┬───────┘
          │ ctx.run_command(...)
   ┌──────▼───────┐
   │ exec.py       │  the ONLY place subprocess is invoked from
   │ Runner/       │  (SubprocessRunner in prod, FakeRunner in tests)
   │ FakeRunner    │
   └───────────────┘

   Every layer above also reaches log.py directly — a module-level
   singleton, imported wherever needed, not passed through RunContext:
   log.info/warning/error/note/panel/result/... for all output, log.task(...)
   as an indeterminate spinner around a blocking call. ctx.run_command
   auto-suspends the active spinner whenever capture=False.
```

**Rule:** `wizard.py` never knows about brew/apt/curl/etc. — it only knows the `Step` interface. `steps/*.py` never call `subprocess` directly — only `ctx.run_command`. This is what keeps every layer independently testable.

**Rule:** Nothing prints/logs directly — always through `log.py` (`workstation_setup.log`). Unlike `ctx.runner` (still injected via `RunContext` for `FakeRunner` swapping in tests), logging is a plain module import, not a `RunContext` field — a brand-new Step/Provider gets logging (and the spinner) for free with zero constructor wiring. Tests get isolation via `log.reset()` (an autouse fixture in `tests/unit/conftest.py`), not dependency injection.

## File tree (key paths only)

```
src/workstation_setup/
├── cli.py                    # entry point, RECOMMENDED_PIPELINE, MASTER_REGISTRY,
│                              # --dry-run/--yes/--only/--skip
├── wizard.py                  # run_recommended() / run_menu() orchestration
├── context.py                  # RunContext dataclass
├── os_detect.py                 # detect_os() -> OSInfo
├── exec.py                       # run_command/command_exists, Runner/FakeRunner, StepError
├── state.py                       # ~/.workstation-setup/state.json (audit trail, not source of truth)
├── log.py                          # the ONLY place output/logging happens — module-level singleton,
│                                    # import from anywhere (log.info/task/etc.), no RunContext wiring.
│                                    # Also owns ~/.workstation-setup/run.log: written during the run,
│                                    # deleted on clean success, kept on failure/abort.
├── errors.py                       # StepError, AbortError, UnsupportedPlatformError
│
├── providers/
│   ├── base.py                # PackageProvider Protocol
│   ├── brew.py                 # BrewProvider (install + reinstall) + resolve_brew_binary + ensure_brew_on_path
│   ├── apt.py / dnf.py / pacman.py  # Linux fallback providers
│   ├── winget.py              # Windows provider + current-process PATH refresh
│   └── registry.py              # get_brew_provider() / get_system_provider(os_info)
│
├── steps/
│   ├── base.py                # Step ABC (run() takes `reinstall: bool`), StepStatus, StepResult, ExistingAction
│   ├── homebrew.py              # InstallHomebrewStep
│   ├── shell.py                  # zsh, Oh My Zsh, Powerlevel10k, SetDefaultShellStep
│   ├── asdf.py                    # InstallAsdfStep, AsdfPluginsStep
│   ├── git_gh.py                   # git, gh, gh auth login
│   ├── ssh.py                       # GenerateSshKeyStep
│   ├── gui_apps.py                    # install_app() / _execute_install_method() dispatcher only
│   └── app_spec_step.py                # AppSpecStep — adapts one AppSpec into a flat Step
│
├── registry/
│   ├── models.py               # AppSpec, InstallMethod dataclasses
│   ├── apps.py                  # Chrome, Slack, Spotify, Devin Desktop, GCloud SDK
│   └── ides.py                   # JetBrains Toolbox, VS Code, Cursor
│
└── ui/
    └── prompts.py              # confirm_step / checkbox_select / text_input / select_existing_action

tests/
├── unit/                   # pytest — FakeRunner, no real subprocess calls, mirrors src structure
└── integration/            # NOT run by pytest — manual/Docker verification, see 04_testing.md
```

IDEs and everyday apps used to be two monolithic `Step`s that each opened
their own checkbox screen (`steps/ides.py`, `GuiAppsSelectionStep`). They're
now flattened: `AppSpecStep` wraps a single `AppSpec` as an ordinary `Step`,
so `cli.py` can list `IDE_REGISTRY`/`APP_REGISTRY` entries side by side with
Homebrew/zsh/etc. in one `MASTER_REGISTRY` — see
[03_registry_apps_ides.md](03_registry_apps_ides.md).

## Wizard step lifecycle (detailed)

Shared by both `run_recommended` (walks `RECOMMENDED_PIPELINE` in order) and
`run_menu` (the flat checkbox over `MASTER_REGISTRY`, nothing pre-checked):

```
1. is_applicable(ctx)?
   False → excluded entirely, no state recorded (e.g. SSH step when gh isn't installed)

2. check_installed(ctx) — ALWAYS live detection (command_exists, brew list, file existence...)

3. dry_run?
   True → print dry_run_preview(ctx) lines, move to next step, no side effects, no prompts

4. run_menu only: the checkbox selection itself IS the confirmation for a
   NOT_INSTALLED item — no extra "proceed?" prompt.
   run_recommended only: confirm (unless --yes) → declined → SKIPPED_BY_USER

5. status == ALREADY_INSTALLED? → NEVER a silent skip. Ask
   prompts.select_existing_action(step.title):
     Reinstall/Modify → run(ctx, reinstall=True)
     Leave as is       → record SKIPPED_BY_USER, no side effects
     Cancel            → same as "leave as is"
   (--yes: no terminal to ask, so this defaults to "leave as is" — the same
   safe, idempotent behavior automation always had.)

6. run(ctx, reinstall=...) — the real install/reinstall action
   success → print + record state
   StepError → print failure panel
     run_recommended: ask "continue with remaining steps?" — declined raises
       AbortError (stops, state saved); accepted records "failed" and moves on
     run_menu: no abort prompt — selections are independent, so it just
       records "failed" and continues with the rest of the selection

7. after all steps: print summary table, save_state(ctx.state)
```

## Windows implementation

`WingetProvider` implements the package-provider contract and uses exact
package IDs for live detection/install/reinstall. `AppSpec.windows` is
optional; `AppSpecStep.is_applicable` hides entries without a Windows route.
Unix-only steps use explicit applicability gates. After WinGet installs a
package, `refresh_windows_path()` reloads persisted environment paths and adds
the Git/GitHub CLI tool directories needed by later steps in the same run.

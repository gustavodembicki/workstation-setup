# 00 — Overview

## Why this exists

Setting up a new developer machine after a fresh OS install is slow and manual: Homebrew, shell + theme, a version manager, git/gh, SSH keys, an IDE, and a handful of everyday apps. `workstation-setup` is a single, dependency-free executable that walks a new engineer through all of that interactively, once.

## Scope

- **Supported:** Linux and macOS. These are treated as close cousins throughout the codebase — Homebrew (Linuxbrew on Linux) is the primary installer on both.
- **Not supported (v1):** Windows. `cli.py` detects this and exits with a clear message rather than attempting anything. The architecture leaves a seam (`OSInfo.family` already includes `"windows"`, `AppSpec.windows` field exists but is unused) for a future Windows provider — see [01_architecture.md](01_architecture.md#future-windows-seam).

## Tech stack

- **Runtime:** Python 3.11+
- **CLI/prompts/output:** `click`, `questionary`, `rich`
- **Packaging:** `pyinstaller` — one spec file (`packaging/pyinstaller.spec`), built separately per OS in CI (no cross-compilation)
- **Tests:** `pytest` + `pytest-mock`, `ruff` for lint/format

## High-level flow

```
1. cli.py: detect_os() → bail early with a friendly message if not linux/macos
2. ensure_brew_on_path() — in case Homebrew is already installed from a prior run
3. Build RunContext (real SubprocessRunner, real Console, loaded state.json)
4. wizard.run(ctx, STEP_PIPELINE):
     for each Step:
       - is_applicable(ctx)?          skip entirely if not (e.g. SSH step needs gh)
       - check_installed(ctx)          live detection — ALREADY_INSTALLED short-circuits
       - [dry-run: print preview, continue]
       - confirm with the user (unless --yes)
       - run(ctx) — the real install action; StepError is caught, reported,
         and the user is asked whether to keep going
     print a summary table
5. save_state(ctx.state)
```

The pipeline itself (`STEP_PIPELINE` in `cli.py`) is currently:

Homebrew → zsh → Oh My Zsh → Powerlevel10k → set default shell → asdf → asdf plugins → git → gh → gh auth login → SSH key → IDE selection → GUI app selection.

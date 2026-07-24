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

Nothing is mandatory. Every installable thing — Homebrew, zsh, the theme,
asdf, git/gh, the SSH key, every IDE, every everyday app — is one entry in a
single flat `MASTER_REGISTRY` (`cli.py`), and an `ALREADY_INSTALLED` result
is never treated as "nothing to do": the user is always asked whether to
reinstall/modify it, leave it alone, or cancel. See
[02_steps_and_providers.md](02_steps_and_providers.md) for why that matters.

```
1. cli.py: detect_os() → bail early with a friendly message if not linux/macos
2. ensure_brew_on_path() — in case Homebrew is already installed from a prior run
3. Build RunContext (real SubprocessRunner, real Console, loaded state.json)
4. Ask once: "Run the recommended initial bootstrap first?" (Homebrew → zsh →
   Oh My Zsh → theme → set default shell → asdf → asdf plugins → git → gh →
   gh auth login → SSH key, in that order — RECOMMENDED_PIPELINE). This is a
   convenience fast path, not a gate:
     - yes → wizard.run_recommended(ctx, RECOMMENDED_PIPELINE) walks that
       list in order. NOT_INSTALLED items get the usual confirm-then-run.
       ALREADY_INSTALLED items get a Reinstall/Modify, Leave as is, or
       Cancel prompt — never a silent skip.
     - no  → straight to step 5.
5. wizard.run_menu(ctx, MASTER_REGISTRY) — the big list of possibilities:
   one checkbox menu with every entry (nothing pre-checked, whether or not
   it's already installed), annotated "(already installed)" where that
   applies. Whatever the user checks gets acted on: NOT_INSTALLED items run
   directly (the checkbox is the confirmation), ALREADY_INSTALLED items get
   the same Reinstall/Modify/Leave/Cancel prompt as step 4. This runs
   regardless of what happened in step 4 — recommended items show up here
   too, so nothing is ever only-offered-once.
6. save_state(ctx.state)
```

`--yes` skips both prompts (no terminal session to answer them from). Paired
with `--only <id>`, it runs just that item unattended; bare `--yes` with no
`--only` does nothing but tells you so, rather than guessing a default
selection for a menu no human looked at.

## Documentation boundaries

The top-level [README](../../README.md) and [usage guide](../usage.md) explain
how an end user runs the wizard. Keep implementation details, extension rules,
and architectural invariants in this `docs/ai/` layer instead. Security facts
that affect a user's decision—curated registries, privileged commands, and the
absence of project-managed artifact verification—belong in
[security.md](../security.md) as well as the relevant implementation document.

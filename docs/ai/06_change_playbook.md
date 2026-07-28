# 06 — Change Playbook and Invariants

Use this document after the orientation layers when making a common extension.
It deliberately focuses on decisions that are easy to get wrong; read the
linked layer for the full contract.

## Add an app or IDE

1. Add an `AppSpec` to `registry/apps.py` or `registry/ides.py`; do not add a
   special branch in the dispatcher.
2. Put every external URL and apt repository fact in `registry/trustlist.py`.
   Treat this as a security review: identify the vendor, artifact type, target
   platforms, privilege requirement, and whether the route executes a script.
3. Choose an existing `InstallMethod` only when it accurately represents the
   vendor route. A Linux method may be distro-specific or a generic fallback;
   unsupported is preferable to a fabricated install path.
4. Add or update registry/dispatch unit tests using `make_context` and
   `FakeRunner`. Confirm macOS, Linux, and Windows preview/selection behavior where
   applicable.
5. Update user-facing availability or security docs if the new item changes a
   listed capability or trust boundary.

See [03_registry_apps_ides.md](03_registry_apps_ides.md) for the data model.

## Add a new Step

1. Implement the `Step` contract with live detection in `check_installed`.
   `state.json` is an audit record, never a detection input.
2. Run every command through `ctx.run_command`; never import or call
   `subprocess` in a step. Send output through `workstation_setup.log`, never
   `print`, Rich, or a new logger instance.
3. Decide whether it belongs in `RECOMMENDED_PIPELINE`, `MASTER_REGISTRY`, or
   both. All entries remain optional; a recommended entry is only a fast path.
4. Honor `reinstall=True` when a package install would otherwise become a
   no-op. Configuration steps can re-prompt instead when that is the real
   modify behavior.
5. Add `tests/unit/test_steps_<name>.py` using `make_context`/`FakeRunner`.
   Add a dry-run preview that describes the actual side effects.

See [02_steps_and_providers.md](02_steps_and_providers.md) and
[04_testing.md](04_testing.md).

## Change providers, commands, or prompts

- Preserve the `PackageProvider` abstraction. Resolve Homebrew's binary or
  call `ensure_brew_on_path` after Homebrew/package installation when later
  commands need its binaries on `PATH`.
- For genuinely interactive commands such as `gh auth login`, use
  `capture=False` so the real terminal owns the session. Do not wrap an
  individual uncaptured command in `log.task`; `RunContext` already suspends
  the spinner.
- Use `check=False` only for an expected non-zero result and branch explicitly
  on the returned status. Do not swallow command failures.
- Keep confirmation separate for destructive actions, especially replacing an
  SSH private key or changing the login shell.
- Patch the importing module's attribute in tests, not the original export.

## Security invariants

- No arbitrary user-supplied package names or external installer URLs.
- All app/IDE external URLs are centralized in `registry/trustlist.py`.
- Never generate an SSH key with a forced passphrase; present the user choice.
- Never capture interactive authentication output.
- Never use the broken direct `bash -c "$(curl ...)"` pattern. Pipe the
  downloaded script to `bash` through an actual shell instead.
- Do not claim checksum, signature, or provenance verification in code or
  docs unless the implementation performs it.

## Windows work

Windows routes use exact curated WinGet IDs. Add `AppSpec.windows` only when a
real package exists; otherwise leave it `None` so the entry is hidden. Keep
Unix-only steps explicitly inapplicable, refresh the current process PATH
after WinGet installs, and update Windows unit/manual verification whenever a
new package or core step is introduced.

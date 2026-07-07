# 05 — Packaging and CI

## PyInstaller does not cross-compile

A binary built on `ubuntu-latest` only runs on Linux. A binary built on `macos-latest` only runs on macOS. There is no way to produce the macOS artifact from a Linux (or Windows) build machine, or vice versa. This is why release builds need one CI job per target OS, each running `pyinstaller` on its own runner — never try to "build once, package for all OSes."

## `packaging/pyinstaller.spec`

One spec file, used identically by both CI runners — it doesn't branch on OS itself; PyInstaller reads the *actual* platform it's running on at build time and emits the matching binary format (ELF vs. Mach-O).

- `SPECPATH` (a PyInstaller-provided variable, not a Python builtin) is used to locate `src/` relative to the spec file's own location, so `pyinstaller packaging/pyinstaller.spec` works regardless of the caller's current directory.
- `hiddenimports=["questionary", "prompt_toolkit", "rich"]` — these are listed explicitly because `questionary`/`prompt_toolkit` lazily import some renderer/style modules that PyInstaller's static analysis can miss. If a future dependency exhibits the same "works with `python -m workstation_setup` but the built binary crashes with an ImportError" symptom, add it here rather than restructuring the import.

Build locally: `pyinstaller packaging/pyinstaller.spec` → binary lands in `dist/workstation-setup` (or `.exe` on Windows, though Windows isn't a supported target — see [00_overview.md](00_overview.md)).

## CI workflows

- **`.github/workflows/ci.yml`** — runs on every push/PR, matrix `[ubuntu-latest, macos-latest]`: `ruff check .` then `pytest tests/unit`. This is the gate that must stay green; it never invokes PyInstaller.
- **`.github/workflows/release.yml`** — triggered on `v*` tags. Matrix builds the two real artifacts (`workstation-setup-linux-x86_64`, `workstation-setup-macos-arm64`) and attaches them to a GitHub Release. If Intel Mac support is ever needed, add a `macos-13` (Intel runner) leg alongside `macos-latest` (Apple Silicon) — don't assume one macOS artifact covers both architectures.

## Before tagging a release

1. `pytest tests/unit` and `ruff check .` green on both OSes (CI).
2. A local `pyinstaller` build smoke test (`--version`, `--dry-run`) on at least one real OS.
3. The Docker integration smoke test (`tests/integration/`) — full dry-run plus a real install of at least the Homebrew/zsh/asdf/git/gh steps, and an idempotency check (run the same steps twice, confirm the second run reports everything as "already installed").
4. A manual macOS pass on a spare machine/VM — there's no automated equivalent, Docker doesn't provide a real macOS kernel.

None of this is automated end-to-end on purpose (see [04_testing.md](04_testing.md) for why) — treat it as a checklist, not something CI enforces for you.

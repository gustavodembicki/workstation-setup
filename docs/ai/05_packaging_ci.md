# 05 — Packaging and CI

## PyInstaller does not cross-compile

A binary built on `ubuntu-latest`, `macos-latest`, or `windows-latest` only
runs on that platform. Release builds therefore use one PyInstaller job per
target OS; there is no cross-compilation.

## `packaging/pyinstaller.spec`

One spec file is used identically by all three CI runners. PyInstaller emits
ELF, Mach-O, or PE/`.exe` from the actual build platform.

- `SPECPATH` (a PyInstaller-provided variable, not a Python builtin) is used to locate `src/` relative to the spec file's own location, so `pyinstaller packaging/pyinstaller.spec` works regardless of the caller's current directory.
- `hiddenimports=["questionary", "prompt_toolkit", "rich"]` — these are listed explicitly because `questionary`/`prompt_toolkit` lazily import some renderer/style modules that PyInstaller's static analysis can miss. If a future dependency exhibits the same "works with `python -m workstation_setup` but the built binary crashes with an ImportError" symptom, add it here rather than restructuring the import.

Build locally: `pyinstaller packaging/pyinstaller.spec` → binary lands in
`dist/workstation-setup` or `dist/workstation-setup.exe`.

## CI workflows

- **`.github/workflows/ci.yml`** — runs lint/tests on Ubuntu, macOS, and Windows.
- **`.github/workflows/release.yml`** — builds Linux x86_64, macOS ARM64, and Windows x86_64 artifacts, smoke-tests `--version`, then publishes them.

## Before tagging a release

1. `pytest tests/unit` and `ruff check .` green on all three OSes (CI).
2. A local `pyinstaller` build smoke test (`--version`, `--dry-run`) on at least one real OS.
3. The Docker integration smoke test (`tests/integration/`) — full dry-run plus a real install of at least the Homebrew/zsh/asdf/git/gh steps, and an idempotency check (run the same steps twice, confirm the second run reports everything as "already installed").
4. A manual macOS pass on a spare machine/VM — there's no automated equivalent, Docker doesn't provide a real macOS kernel.
5. `make test-windows` under a Windows container daemon, then a manual Windows
   x64 VM pass with WinGet, including Git/gh/SSH and one GUI app.

None of this is automated end-to-end on purpose (see [04_testing.md](04_testing.md) for why) — treat it as a checklist, not something CI enforces for you.

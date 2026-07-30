# 05 — Packaging and CI

## PyInstaller does not cross-compile

A binary built on `ubuntu-latest`, `macos-latest`, or `windows-latest` only
runs on that platform. Release builds therefore use one PyInstaller job per
target OS; there is no cross-compilation.

## `packaging/pyinstaller.spec`

One spec file is used identically by all three CI runners. PyInstaller emits
ELF, Mach-O, or PE/`.exe` from the actual build platform.

- `SPECPATH` (a PyInstaller-provided variable, not a Python builtin) is used to locate `src/` relative to the spec file's own location, so `pyinstaller packaging/pyinstaller.spec` works regardless of the caller's current directory.
- `hiddenimports` explicitly includes `questionary`, `prompt_toolkit`, `rich`,
  and the release-only `workstation_setup._build_version` module. The first
  group covers lazy imports that static analysis can miss; the generated
  version module ensures release binaries retain their unique pre-release
  version.

Build locally: `pyinstaller packaging/pyinstaller.spec` → binary lands in
`dist/workstation-setup` or `dist/workstation-setup.exe`.

## CI workflows

- **`.github/workflows/ci.yml`** — runs lint/tests for pull requests.
- **`.github/workflows/release.yml`** — every push to `master` validates and builds Linux x86_64, Windows x86_64, macOS Intel x86_64 (`macos-15-intel`), and macOS Apple Silicon ARM64 (`macos-14`) artifacts. Before each clean PyInstaller build, it generates and compiles the release-version module; it then smoke-tests the frozen binary's exact version, publishes a unique GitHub pre-release, and attaches `SHA256SUMS`.

## Before merging to `master`

1. `pytest tests/unit` and `ruff check .` green on all three OSes (CI).
2. A local `pyinstaller` build smoke test (`--version`, `--dry-run`) on at least one real OS.
3. The Docker integration smoke test (`tests/integration/`) — full dry-run plus a real install of at least the Homebrew/zsh/asdf/git/gh steps, and an idempotency check (run the same steps twice, confirm the second run reports everything as "already installed").
4. A manual macOS pass on a spare machine/VM — there's no automated equivalent, Docker doesn't provide a real macOS kernel.
5. `make test-windows` under a Windows container daemon, then a manual Windows
   x64 VM pass with WinGet, including Git/gh/SSH and one GUI app.

None of this is automated end-to-end on purpose (see [04_testing.md](04_testing.md) for why) — treat it as a checklist, not something CI enforces for you.

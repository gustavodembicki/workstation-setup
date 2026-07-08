# workstation-setup

An interactive wizard that bootstraps a fresh Linux or macOS developer workstation. Format the laptop, download one file, run it, and get a working dev environment — no manual copy-pasting of install commands, no forgetting a step.

Ships as a **single self-contained executable per OS** (built with PyInstaller) — no Python installation required on the target machine.

## What it sets up

Each step is optional and skippable — the wizard asks before doing anything, and re-running it is always safe (already-installed things are detected and skipped automatically):

- **Homebrew** — the primary package manager on both macOS and Linux (Linuxbrew)
- **zsh** + **Oh My Zsh** + **Powerlevel10k** theme, with an explicit confirmation before changing your login shell
- **asdf** version manager, with a curated plugin picker (Node, Python, Erlang, Elixir, Ruby, Go) plus free-text entry for anything else in asdf's plugin registry
- **git** + **GitHub CLI (`gh`)**, with an interactive `gh auth login`
- **SSH key generation** (ed25519) — offered only once `gh` is around, never overwrites an existing key without an explicit confirmation, and offers to upload the public key to GitHub automatically via `gh ssh-key add` when authenticated
- **IDEs** (pick any combination): JetBrains Toolbox, VS Code, Windsurf, Cursor
- **Everyday apps** (pick any combination): Google Chrome, Slack, Spotify, Google Cloud SDK, Devin Desktop

**Scope:** Linux and macOS only. Windows isn't supported in v1 — the CLI detects this and exits with a clear message rather than doing anything unsafe.

## Quick start

Download the appropriate binary from the [latest release](../../releases/latest) and run it:

```bash
chmod +x workstation-setup-linux-x86_64   # or workstation-setup-macos-arm64
./workstation-setup-linux-x86_64
```

Useful flags:

```bash
./workstation-setup --dry-run              # preview every step, install nothing
./workstation-setup --yes                  # accept every prompt (non-interactive)
./workstation-setup --only homebrew --only zsh   # run just specific steps (repeatable flag)
./workstation-setup --skip gui-apps        # run everything except specific steps
./workstation-setup --version
```

## How it works

Under the hood, a `Step` interface (check → confirm → run) drives an ordered pipeline — Homebrew, shell, asdf, git/gh, SSH, then IDE/app selection — each backed by a `PackageProvider` abstraction (Homebrew primarily, apt/dnf/pacman as the Linux fallback for GUI apps without a Homebrew cask). Apps and IDEs are data-driven entries in a registry, not hardcoded branches, so adding a new one is a single new entry.

See [AGENTS.md](AGENTS.md) and [docs/ai/](docs/ai/README.md) for the full architecture writeup, including two real bugs the design had to work around (a `bash -c "$(curl ...)"` word-splitting gotcha, and Homebrew's bin directory not being on `PATH` mid-process).

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/unit    # unit suite — fast, no real subprocess calls
ruff check .          # lint
```

Run the wizard from source (no build needed):

```bash
python -m workstation_setup --dry-run
```

Manual, real-install verification (Docker for Linux, since real installers are too slow/mutating for the automated suite — covers Ubuntu/Fedora/Arch to exercise the apt/dnf/pacman fallback paths):

```bash
docker compose -f tests/integration/docker/docker-compose.yml build
docker compose -f tests/integration/docker/docker-compose.yml run --rm ubuntu   # or fedora / arch
```

See [tests/integration/README.md](tests/integration/README.md) for the full manual verification checklist, including macOS (Docker can't provide a real macOS kernel — needs a spare Mac or a local VM like UTM/Tart).

## Building the standalone binary

```bash
pyinstaller packaging/pyinstaller.spec
```

PyInstaller does not cross-compile: build on Linux for the Linux binary, on macOS for the macOS binary. CI does this via a build matrix — see [`.github/workflows/release.yml`](.github/workflows/release.yml).

## Project structure

```
src/workstation_setup/
├── cli.py, wizard.py, context.py   # entry point + orchestration
├── os_detect.py, exec.py, state.py, errors.py   # foundation
├── providers/    # brew / apt / dnf / pacman
├── steps/        # one Step per installable unit
├── registry/     # data-driven app/IDE list
└── ui/           # thin questionary/rich wrappers

tests/
├── unit/         # pytest, FakeRunner — no real subprocess calls
└── integration/  # manual/Docker verification (not run by pytest)
```

## Contributing

Every new `Step` needs a unit test using the `FakeRunner`/`make_context` pattern in `tests/unit/factories.py` — see [docs/ai/04_testing.md](docs/ai/04_testing.md). Adding a new GUI app or IDE is a single registry entry, not new dispatch code — see [docs/ai/03_registry_apps_ides.md](docs/ai/03_registry_apps_ides.md).

## Windows

Out of scope for v1. The architecture (`OSInfo.family`, `AppSpec.windows`) leaves room for a future Windows provider without a rewrite — see [docs/ai/01_architecture.md](docs/ai/01_architecture.md#future-windows-seam).

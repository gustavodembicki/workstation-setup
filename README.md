# workstation-setup

`workstation-setup` is an interactive terminal wizard for bootstrapping a new
developer machine on Linux or macOS. It packages the setup workflow into one
native executable: choose the tools you want, review each action, and let the
wizard run the supported installation path.

Windows is deliberately unsupported in v1. The program detects it and exits
without changing the machine.

## What it can configure

Nothing is mandatory. The menu contains individual, opt-in entries for:

- Homebrew (including Linuxbrew), zsh, Oh My Zsh, Powerlevel10k, and the login shell
- asdf and selected language plugins
- Git, GitHub CLI, GitHub authentication, and an ed25519 SSH key
- IDEs: JetBrains Toolbox, VS Code, Windsurf, and Cursor
- Apps: Google Chrome, Slack, Spotify, Google Cloud SDK, and Devin Desktop

Install support depends on the operating system and Linux distribution. The
wizard clearly reports an unsupported selection instead of pretending it was
installed.

## Quick start

Download the binary for your operating system from the
[latest release](../../releases/latest), make it executable, and start it in a
real terminal:

```bash
chmod +x workstation-setup-linux-x86_64 # or workstation-setup-macos-arm64
./workstation-setup-linux-x86_64
```

The wizard first offers the recommended bootstrap (Homebrew through SSH), then
always shows the complete flat menu. You may skip either path and choose only
the tools you need.

Useful commands:

```bash
./workstation-setup --dry-run
./workstation-setup --dry-run --only homebrew
./workstation-setup --yes --only homebrew --only git
./workstation-setup --skip gcloud_sdk
./workstation-setup --version
```

`--yes` is intended for targeted automation and should be paired with one or
more `--only` values. With no `--only`, it safely runs nothing because no
interactive user was able to choose menu entries.

For the complete walkthrough, prerequisites, recovery information, and the
behavior of re-runs, see [the usage guide](docs/usage.md). See
[the CLI reference](docs/cli-reference.md) for every option and valid step ID.

## Safety model

The project only offers applications and installation routes that are defined
in its source registry. External app/IDE download URLs and apt repository
metadata are centralized in a reviewable trustlist rather than accepted from
terminal input.
It also asks before changing the login shell or overwriting an existing SSH
key, and attaches interactive GitHub authentication to your terminal.

This is a curated installer, not a complete supply-chain verification system:
the project does not currently verify downloaded artifacts with project-managed
checksums or signatures. Review the full boundary, permissions, and limitations
before running it in a sensitive environment: [security documentation](docs/security.md).

## Develop from source

Python 3.11+ is required for development, not for running a release binary.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/unit
ruff check .
python -m workstation_setup --dry-run
```

Build a native binary on the target operating system:

```bash
pyinstaller packaging/pyinstaller.spec
```

PyInstaller does not cross-compile. Linux and macOS artifacts must be built on
their respective platforms.

## Documentation

- [Usage guide](docs/usage.md) — run the wizard safely and recover from failures
- [CLI reference](docs/cli-reference.md) — options, examples, and step IDs
- [Security model](docs/security.md) — curated registry, trust boundaries, and limitations
- [Integration verification](tests/integration/README.md) — disposable Linux and macOS checks
- [AI Knowledge](docs/ai/README.md) — architecture and safe extension guidance

## Contributing

The core design is `Step` + provider + registry: a new application or IDE is
normally one registry entry, while a new category is a new `Step`. Every new
step needs a `FakeRunner`-based unit test; never call subprocesses directly
from a step. Read [the AI Knowledge index](docs/ai/README.md) before changing
installation behavior, providers, trust boundaries, packaging, or CI.

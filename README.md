# workstation-setup

`workstation-setup` is an interactive terminal wizard for bootstrapping a new
developer machine on Linux, macOS, or Windows. It packages the setup workflow
into one native executable: choose the tools you want, review each action, and
let the wizard run the supported installation path.

Windows support is native and terminal-based: the wizard uses WinGet rather
than requiring WSL, Chocolatey, or a graphical frontend.

## What it can configure

Nothing is mandatory. The menu contains individual, opt-in entries for:

- Homebrew (including Linuxbrew), zsh, Oh My Zsh, Powerlevel10k, and the login shell
  on Linux/macOS
- asdf and selected language plugins on Linux/macOS
- Git, GitHub CLI, GitHub authentication, and an ed25519 SSH key
- IDEs: JetBrains Toolbox, VS Code, and Cursor
- Apps: Google Chrome, Slack, Spotify, Google Cloud SDK, and Devin Desktop

Devin Desktop currently has no Windows install route and is hidden there.
Other install support depends on the operating system and Linux distribution.
The wizard clearly reports an unsupported selection instead of pretending it
was installed.

## Quick start

Download the binary for your operating system from the
[latest release](../../releases/latest) and start it in a real terminal.
Linux/macOS:

```bash
chmod +x workstation-setup-linux-x86_64 # or workstation-setup-macos-arm64
./workstation-setup-linux-x86_64
```

Windows 10 1809+ or Windows 11 x64, from PowerShell:

```powershell
.\workstation-setup-windows-x86_64.exe
```

Windows requires WinGet, normally supplied by Microsoft App Installer. The
wizard exits with repair guidance if WinGet is unavailable.

The wizard first offers the platform-appropriate recommended bootstrap, then
shows the complete flat menu. After each selected batch, it refreshes live
installation status and returns to the menu so you can choose more tools or
select **Exit** to finish.

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

PyInstaller does not cross-compile. Linux, macOS, and Windows artifacts must be
built on their respective platforms.

## Docker verification

The integration environments are intentionally separated:

- `tests/integration/docker/linux/` contains Ubuntu, Fedora, and Arch images.
  They can exercise the real Linux wizard and package-manager routes.
- `tests/integration/docker/windows/` uses the official
  `python:3.12-windowsservercore-ltsc2022` image to validate native Windows
  tests and PyInstaller packaging.

Docker must be using the matching container daemon. Linux targets require
Linux containers; Windows targets require Docker Desktop/Engine switched to
Windows containers. Every build/run/test target checks this first and prints
how to switch when the active daemon is incompatible.

### Make targets

| Action | Linux | Windows |
|---|---|---|
| Build | `make build-linux` | `make build-windows` |
| Open shell | `make run-linux` | `make run-windows` |
| Tests | `make test-linux` | `make test-windows` |
| Clean rebuild | `make rebuild-linux` | `make rebuild-windows` |
| Stop/remove Compose resources | `make down-linux` | `make down-windows` |

Ubuntu is the default Linux distribution. Select another provider path with,
for example, `make test-linux DISTRO=fedora` or
`make rebuild-linux DISTRO=arch`.

The requested positional forms are also supported:

```bash
make build linux
make run linux DISTRO=fedora
make build windows
make test windows
```

Other useful commands:

```bash
make help       # show all Docker targets
make validate   # parse/validate both Compose files without building
```

`make test-linux` runs pytest and Ruff inside the selected Linux image.
`make test-windows` runs pytest, Ruff, PyInstaller, and
`dist\workstation-setup.exe --version` inside Windows Server Core.

### Windows container limitation

Windows containers do not provide the Desktop/App Installer user environment
required by the project's WinGet GUI application routes. The WinGet CLI is
also not supported in the LocalSystem-style context commonly used by
containers. Therefore the Windows image validates code, tests, and `.exe`
packaging, but real Git/WinGet/application installation must still be verified
in a disposable Windows 10/11 x64 VM with Microsoft App Installer.

See the [integration-test guide](tests/integration/README.md) for the complete
Linux, Windows, and macOS release checklist.

## Documentation

- [Usage guide](docs/usage.md) — run the wizard safely and recover from failures
- [CLI reference](docs/cli-reference.md) — options, examples, and step IDs
- [Security model](docs/security.md) — curated registry, trust boundaries, and limitations
- [Integration verification](tests/integration/README.md) — Linux containers and macOS/Windows manual checks
- [AI Knowledge](docs/ai/README.md) — architecture and safe extension guidance

## Contributing

The core design is `Step` + provider + registry: a new application or IDE is
normally one registry entry, while a new category is a new `Step`. Every new
step needs a `FakeRunner`-based unit test; never call subprocesses directly
from a step. Read [the AI Knowledge index](docs/ai/README.md) before changing
installation behavior, providers, trust boundaries, packaging, or CI.

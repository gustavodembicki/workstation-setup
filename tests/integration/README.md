# Manual integration testing

Actually invoking real installers (Homebrew, chsh, ssh-keygen, gh auth login,
GUI app downloads) is inherently environment-mutating, slow, and sometimes
interactive — it is intentionally **not** part of the automated `pytest`
suite (`tests/unit/`). Verify it manually instead, in a disposable
environment, before cutting a release.

## Linux (Docker)

Three Dockerfiles under `docker/linux/` cover the package-manager fallback
paths for GUI apps (apt/dnf/pacman). Each builds a disposable, non-root,
sudo-capable user with the project installed in a venv.

### Build the images

```bash
make build-linux                 # Ubuntu (default)
make build-linux DISTRO=fedora   # Fedora
make build-linux DISTRO=arch     # Arch

# Positional form is also accepted:
make build linux DISTRO=fedora
```

(or build a single distro with plain `docker`: `docker build -f
tests/integration/docker/linux/Dockerfile.ubuntu -t workstation-setup-smoketest .`)

### Enter a container

```bash
make run-linux                   # Ubuntu (default)
make run-linux DISTRO=fedora     # or DISTRO=arch
make run linux DISTRO=arch       # positional equivalent
```

This drops you into `/bin/bash` as the non-root `dev` user, inside a copy of
the repo with a venv already set up. Activate it first:

```bash
source .venv/bin/activate
```

### Run the automated test suite inside the container

Same commands as local development — useful for catching platform-specific
surprises the host OS wouldn't hit:

```bash
pytest tests/unit    # unit suite — fast, no real subprocess calls
ruff check .          # lint
mypy src              # type check (src only — the test suite itself has pre-existing,
                       # unrelated mypy findings and isn't part of the CI gate)
```

### Manually exercise the real installers

This is the actual point of these containers — running the real,
side-effecting install steps somewhere throwaway:

```bash
python -m workstation_setup --dry-run              # full preview, no side effects
python -m workstation_setup --dry-run --only homebrew   # preview a single step
python -m workstation_setup --only homebrew         # really install just Homebrew
python -m workstation_setup                         # real run, full interactive menu — safe, container is thrown away after
```

For a useful release smoke test, do the following in one fresh container:

1. Run the full `--dry-run`, accept the initial recommended-bootstrap prompt,
   and confirm that it previews every available step without changing the
   container or asking menu questions.
2. Run `--only homebrew` for the real Homebrew bootstrap.  Then run the full
   wizard and choose one app or IDE appropriate to the distro.  Watch that
   download URLs are sensible and that `curl` shows its progress bar in the
   terminal rather than returning only after a hidden download.
3. Where a step prompts for authentication (for example GitHub CLI), confirm
   that the prompt is attached to the terminal.  Do not automate credentials
   into this disposable test.
4. After deliberately cancelling a step or observing a command failure,
   inspect the reported `~/.workstation-setup/run.log`; it must remain present.
   Start a new successful run and verify that the file is removed at the end.

Ubuntu is the best first pass for APT repositories and `.deb` downloads.
Repeat the menu flow in Fedora and Arch for compatible `dnf` and `pacman`
fallbacks.  Script, tarball, and AppImage methods can be exercised on any of
the images.

Exit the container (`exit` or Ctrl-D) and `docker compose run` tears it down
automatically (`--rm`); nothing persists between runs.

### Iterating on code changes

`COPY` happens at build time, so editing source on the host doesn't show up
in a running container. `make rebuild-linux` clears Compose state then creates a
no-cache image for a fully fresh test environment:

```bash
make rebuild-linux
make run-linux
```

(Bind-mounting the repo instead of rebuilding is tempting for faster
iteration, but it shadows the container's `.venv` with whatever `.venv` — or
lack of one — exists on the host, which silently breaks the container. Not
worth the fragility here; just rebuild.)

### All three distros

```bash
make run-linux DISTRO=ubuntu
make run-linux DISTRO=fedora
make run-linux DISTRO=arch
```

## macOS

Docker doesn't provide a real macOS kernel — Apple's license only allows
macOS to run on Apple hardware, and there is no Linux-container equivalent of
`launchctl`/`chsh`/Homebrew's macOS cask machinery to fake it. Before a
release, run the same manual walkthrough on a spare Mac or a disposable local
VM (e.g. UTM/Tart) / scratch user account — this is a pre-release gate, not
something to automate.

## Windows container

`docker/windows/` is deliberately separate from the Linux Compose project.
It uses `python:3.12-windowsservercore-ltsc2022` and requires Docker
Desktop/Engine switched to Windows containers:

```powershell
make build-windows
make test-windows
make run-windows

# Positional form:
make build windows
```

`make test-windows` runs the unit suite, Ruff, PyInstaller, and the resulting
`.exe --version` smoke test. `make validate` parses both Linux and Windows
Compose files without requiring either daemon mode. Build/run/test targets
check the active daemon OS first and explain how to switch on mismatch.

Windows Server Core containers do not have the Desktop/App Installer user
environment required for this project's WinGet application routes. Microsoft
also does not support the WinGet CLI in the container-style LocalSystem
context. Therefore the container validates native Windows code and packaging,
not real GUI application installation.

## Windows real-install verification

Use a disposable Windows 10/11 x64 VM with Microsoft App Installer/WinGet.
Run the release `.exe` from PowerShell and verify `--version`, a full
`--dry-run`, `--yes --only git --only gh`, interactive GitHub authentication,
SSH-key generation, and one WinGet-backed GUI app. Run the same package twice
and confirm the second selection offers Reinstall/Modify, Leave as is, or
Cancel. Also launch the `.exe` from Explorer, install one item, confirm the
menu reappears with refreshed status, and select Exit to close. Verify that a
VM without WinGet exits with App Installer repair guidance and makes no
installation attempt.

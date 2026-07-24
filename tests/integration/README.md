# Manual integration testing

Actually invoking real installers (Homebrew, chsh, ssh-keygen, gh auth login,
GUI app downloads) is inherently environment-mutating, slow, and sometimes
interactive — it is intentionally **not** part of the automated `pytest`
suite (`tests/unit/`). Verify it manually instead, in a disposable
environment, before cutting a release.

## Linux (Docker)

Three Dockerfiles cover the three package-manager fallback paths for GUI
apps (apt/dnf/pacman): `Dockerfile.ubuntu`, `Dockerfile.fedora`,
`Dockerfile.arch`. Each builds a disposable, non-root, sudo-capable user with
the project installed in a venv — same setup, different base image.

### Build the images

```bash
make build                 # Ubuntu (default)
make build DISTRO=fedora   # Fedora
make build DISTRO=arch     # Arch
```

(or build a single distro with plain `docker`: `docker build -f
tests/integration/docker/Dockerfile.ubuntu -t workstation-setup-smoketest .`)

### Enter a container

```bash
make run                   # Ubuntu (default)
make run DISTRO=fedora     # or DISTRO=arch
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
in a running container. `make rebuild` clears Compose state then creates a
no-cache image for a fully fresh test environment:

```bash
make rebuild
make run
```

(Bind-mounting the repo instead of rebuilding is tempting for faster
iteration, but it shadows the container's `.venv` with whatever `.venv` — or
lack of one — exists on the host, which silently breaks the container. Not
worth the fragility here; just rebuild.)

### All three distros

```bash
make run DISTRO=ubuntu
make run DISTRO=fedora
make run DISTRO=arch
```

## macOS

Docker doesn't provide a real macOS kernel — Apple's license only allows
macOS to run on Apple hardware, and there is no Linux-container equivalent of
`launchctl`/`chsh`/Homebrew's macOS cask machinery to fake it. Before a
release, run the same manual walkthrough on a spare Mac or a disposable local
VM (e.g. UTM/Tart) / scratch user account — this is a pre-release gate, not
something to automate.

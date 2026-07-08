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
docker compose -f tests/integration/docker/docker-compose.yml build
```

(or build a single distro with plain `docker`: `docker build -f
tests/integration/docker/Dockerfile.ubuntu -t workstation-setup-smoketest .`)

### Enter a container

```bash
docker compose -f tests/integration/docker/docker-compose.yml run --rm ubuntu   # or fedora / arch
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

Exit the container (`exit` or Ctrl-D) and `docker compose run` tears it down
automatically (`--rm`); nothing persists between runs.

### Iterating on code changes

`COPY` happens at build time, so editing source on the host doesn't show up
in a running container — rebuild after each change (Docker layer caching
keeps this fast; only the `COPY` + `pip install -e` layers re-run):

```bash
docker compose -f tests/integration/docker/docker-compose.yml build ubuntu
docker compose -f tests/integration/docker/docker-compose.yml run --rm ubuntu
```

(Bind-mounting the repo instead of rebuilding is tempting for faster
iteration, but it shadows the container's `.venv` with whatever `.venv` — or
lack of one — exists on the host, which silently breaks the container. Not
worth the fragility here; just rebuild.)

### All three distros

```bash
docker compose -f tests/integration/docker/docker-compose.yml run --rm ubuntu
docker compose -f tests/integration/docker/docker-compose.yml run --rm fedora
docker compose -f tests/integration/docker/docker-compose.yml run --rm arch
```

## macOS

Docker doesn't provide a real macOS kernel — Apple's license only allows
macOS to run on Apple hardware, and there is no Linux-container equivalent of
`launchctl`/`chsh`/Homebrew's macOS cask machinery to fake it. Before a
release, run the same manual walkthrough on a spare Mac or a disposable local
VM (e.g. UTM/Tart) / scratch user account — this is a pre-release gate, not
something to automate.

# Manual integration testing

Actually invoking real installers (Homebrew, chsh, ssh-keygen, gh auth login,
GUI app downloads) is inherently environment-mutating, slow, and sometimes
interactive — it is intentionally **not** part of the automated `pytest`
suite (`tests/unit/`). Verify it manually instead, in a disposable
environment, before cutting a release.

## Linux (Docker)

```bash
docker build -f tests/integration/docker/Dockerfile.ubuntu -t workstation-setup-smoketest .
docker run -it --rm workstation-setup-smoketest

# inside the container:
source .venv/bin/activate
python -m workstation_setup --dry-run   # full preview, no side effects
python -m workstation_setup             # real run — safe, the container is thrown away after
```

Repeat with a Fedora/Arch base image (swap the Dockerfile's `FROM` line and
package manager bootstrap commands) to exercise the apt/dnf/pacman fallback
paths for GUI apps.

## macOS

Docker doesn't provide a real macOS kernel, so there's no container
equivalent. Before a release, run the same manual walkthrough on a spare
machine or a disposable local VM (e.g. UTM/Tart) / scratch user account —
this is a pre-release gate, not something to automate.

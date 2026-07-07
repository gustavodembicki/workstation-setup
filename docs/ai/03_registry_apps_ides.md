# 03 — Registry: GUI apps and IDEs

## The data model (`registry/models.py`)

```python
@dataclass
class InstallMethod:
    kind: Literal["brew_formula", "brew_cask", "apt_repo", "deb_download", "appimage", "tarball", "script"]
    identifier: str                          # formula/cask/package name, or a URL — depends on kind
    distro_family: str | None = None          # None = generic fallback, tried when no distro-specific entry matches
    repo_setup: Callable[[RunContext], None] | None = None   # apt_repo only: adds the vendor's repo/gpg key first

@dataclass
class AppSpec:
    id: str
    display_name: str
    check: Callable[[RunContext], bool]       # already installed?
    macos: InstallMethod                       # always exactly one — macOS story is simple (brew cask)
    linux: list[InstallMethod] = field(default_factory=list)   # ordered; first matching wins
    windows: InstallMethod | None = None       # unused seam, see 01_architecture.md
```

`registry/apps.py` holds the 5 initial GUI apps (Chrome, Slack, Spotify, Devin Desktop, Google Cloud SDK). `registry/ides.py` holds the 4 IDEs (JetBrains Toolbox, VS Code, Windsurf, Cursor). Same `AppSpec` shape — they're only split into two files because they show up on two separate checkbox screens (`steps/gui_apps.py` and `steps/ides.py`), not because the underlying model differs.

## How to add a new app or IDE

Add one `AppSpec` entry to the relevant registry list. That's it — `steps/gui_apps.py`'s `run_selection_step()` and `install_app()` dispatcher are already generic over the registry. Do **not** add a new `if spec.id == "..."` branch anywhere; if you find yourself doing that, the app's specifics belong in its `InstallMethod`/`repo_setup` instead.

```python
AppSpec(
    id="my_new_app",
    display_name="My New App",
    check=lambda ctx: command_exists("my-new-app"),
    macos=InstallMethod("brew_cask", "my-new-app"),
    linux=[
        InstallMethod("apt_repo", "my-new-app", distro_family="debian", repo_setup=_my_repo_setup),
        # optionally a distro_family=None generic fallback (script/appimage/tarball)
    ],
)
```

## Linux dispatch logic (`_pick_linux_method` in `steps/gui_apps.py`)

1. Look for an `InstallMethod` whose `distro_family` matches the detected distro exactly (e.g. `"debian"` for Ubuntu) → use it if found.
2. Otherwise, fall back to the first entry with `distro_family=None` (a generic, cross-distro method) if one exists.
3. Otherwise, the app is `UNSUPPORTED` on this distro — reported clearly, not silently skipped, not a hard failure for the rest of the selection.

Why some apps only have a `distro_family="debian"` entry and no generic fallback (Spotify, Slack): they genuinely have no official cross-distro distribution mechanism this tool implements yet. That's an honest gap, not an oversight — extend it by adding a real fallback `InstallMethod` when one exists, not by faking success.

## `install_app()` dispatch per `InstallMethod.kind`

| kind | what happens |
|------|--------------|
| `brew_cask` / `brew_formula` | `get_brew_provider().install(ctx, identifier, cask=...)` |
| `apt_repo` | run `repo_setup(ctx)` if present (adds gpg key + apt source), `apt-get update`, then `AptProvider().install(ctx, identifier)` |
| `deb_download` | `curl -fsSL -o /tmp/...deb <identifier>`, then `sudo dpkg -i`, falling back to `sudo apt-get install -f -y` if dpkg reports broken deps |
| `appimage` | download into `~/Applications/`, `chmod +x` |
| `tarball` | download, `sudo tar -xzf ... -C /opt` |
| `script` | `curl -fsSL <identifier> \| bash` (see the word-splitting gotcha in [02_steps_and_providers.md](02_steps_and_providers.md)) |

## Selection step behavior (`run_selection_step`, shared by both `steps/ides.py` and `steps/gui_apps.py`)

- Always offered (`check_installed` returns `NOT_INSTALLED` unconditionally) — re-running the wizard lets the user add things they skipped before. The checkbox pre-checks entries whose `check(ctx)` already returns `True`, so re-selecting an already-installed app is a harmless no-op, not a hard block.
- One selected app failing to install does **not** abort the rest of the batch — failures are collected per-app and reported in the step's final `detail` string as `PARTIAL`, so picking 5 apps where 1 has a network hiccup still installs the other 4.

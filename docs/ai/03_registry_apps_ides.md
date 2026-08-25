# 03 — Registry: GUI apps and IDEs

## The data model (`registry/models.py`)

```python
@dataclass
class InstallMethod:
    kind: Literal["brew_formula", "brew_cask", "apt_repo", "deb_download", "appimage", "tarball", "script", "winget"]
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
    windows: InstallMethod | None = None       # exact WinGet package ID when supported
```

`registry/apps.py` holds the 5 initial GUI apps (Chrome, Slack, Spotify, Devin Desktop, Google Cloud SDK). `registry/ides.py` holds the 3 IDEs (JetBrains Toolbox, VS Code, Cursor). Same `AppSpec` shape — they're only split into two files by convention (apps vs. IDEs), not because the underlying model differs. Both lists get wrapped into `AppSpecStep`s and flattened into `MASTER_REGISTRY` in `cli.py`, so an IDE and an everyday app show up side by side with Homebrew/zsh/etc. in the same menu — there's no separate "IDE screen" or "apps screen" anymore.

## The trustlist (`registry/trustlist.py`)

Every external URL an `AppSpec` downloads or executes (GPG keys, apt repo lines, `.deb`/AppImage/tarball/script links) is centralized in `registry/trustlist.py` as `TRUSTLIST: dict[str, AppLinks]`, keyed by `AppSpec.id` — a single, auditable place to see exactly which external links this tool trusts, instead of hunting through `apps.py`/`ides.py` literals. `apps.py`/`ides.py` reference `TRUSTLIST["<id>"].download_url` (etc.) instead of inlining URLs. `trustlist.py` also exposes `apt_repo_setup(gpg_key_url, apt_repo_line, keyring_name)`, the shared builder for `InstallMethod(kind="apt_repo", repo_setup=...)` closures — used in place of the old per-app `_chrome_repo_setup`/`_spotify_repo_setup` functions. Adding a 3rd `apt_repo` app is a `TRUSTLIST` entry + one `apt_repo_setup(...)` call, not a new function.

## How to add a new app or IDE

Add one `AppSpec` entry to the relevant registry list, plus its URL(s) in `TRUSTLIST` (`registry/trustlist.py`). That's it — `steps/app_spec_step.py`'s `AppSpecStep` and `steps/gui_apps.py`'s `install_app()` dispatcher are already generic over any `AppSpec`. Do **not** add a new `if spec.id == "..."` branch anywhere; if you find yourself doing that, the app's specifics belong in its `InstallMethod`/`repo_setup` instead.

```python
# in trustlist.py:
# "my_new_app": AppLinks(gpg_key_url=..., apt_repo_line=...),

AppSpec(
    id="my_new_app",
    display_name="My New App",
    check=lambda ctx: command_exists("my-new-app"),
    macos=InstallMethod("brew_cask", "my-new-app"),
    linux=[
        InstallMethod(
            "apt_repo",
            "my-new-app",
            distro_family="debian",
            repo_setup=apt_repo_setup(
                TRUSTLIST["my_new_app"].gpg_key_url,
                TRUSTLIST["my_new_app"].apt_repo_line,
                "my-new-app",
            ),
        ),
        # optionally a distro_family=None generic fallback (script/appimage/tarball)
    ],
    windows=InstallMethod("winget", "Vendor.MyNewApp"),
)
```

## Linux dispatch logic (`_pick_linux_method` in `steps/gui_apps.py`)

## Catalog and source-health flow

The new registry/catalog.py module is the canonical enumerator across application categories. Use it for cross-cutting validation rather than concatenating individual category lists; a future category only needs to be added to REGISTRIES.

All trusted endpoints must use HTTPS. The Validate application sources GitHub workflow runs on registry-related pull requests, merges to main, manual dispatch, and every Monday. It invokes python -m workstation_setup.registry.url_validation, which probes every download URL, GPG-key URL, and repository URL embedded in an apt source line without downloading installers. Any bad response fails with the exact app_id.field that needs attention.

When adding an application: add its AppSpec, add its TRUSTLIST routes, run pytest tests/unit, then run python -m workstation_setup.registry.url_validation. Require the source-health check alongside normal CI before merging.

1. Look for an `InstallMethod` whose `distro_family` matches the detected distro exactly (e.g. `"debian"` for Ubuntu) → use it if found.
2. Otherwise, fall back to the first entry with `distro_family=None` (a generic, cross-distro method) if one exists.
3. Otherwise, the app is `UNSUPPORTED` on this distro — reported clearly, not silently skipped, not a hard failure for the rest of the selection.

Why some apps only have a `distro_family="debian"` entry and no generic fallback (Spotify, Slack): they genuinely have no official cross-distro distribution mechanism this tool implements yet. That's an honest gap, not an oversight — extend it by adding a real fallback `InstallMethod` when one exists, not by faking success.

## `install_app()` dispatch per `InstallMethod.kind`

`install_app(ctx, spec, *, reinstall=False)` and its inner `_execute_install_method` both take a `reinstall` flag — see [02_steps_and_providers.md](02_steps_and_providers.md) for when it's set.

| kind | what happens | with `reinstall=True` |
|------|--------------|------------------------|
| `brew_cask` / `brew_formula` | `get_brew_provider().install(ctx, identifier, cask=...)` | `get_brew_provider().reinstall(...)` (`brew reinstall`) |
| `apt_repo` | run `repo_setup(ctx)` if present (adds gpg key + apt source), `apt-get update`, then `AptProvider().install(ctx, identifier)` | same steps again — re-running the repo setup + install is itself the reinstall |
| `deb_download` | `curl -fsSL -o /tmp/...deb <identifier>`, then `sudo dpkg -i`, falling back to `sudo apt-get install -f -y` if dpkg reports broken deps | re-downloads and re-installs the same way |
| `appimage` | download into `~/Applications/`, `chmod +x` | re-downloads over the existing file |
| `tarball` | download, `sudo tar -xzf ... -C /opt` | re-downloads and re-extracts |
| `script` | `curl -fsSL <identifier> \| bash` (see the word-splitting gotcha in [02_steps_and_providers.md](02_steps_and_providers.md)) | re-runs the same installer script |
| `winget` | install the exact WinGet ID from the `winget` source | repeats with `--force` |

Homebrew and WinGet methods have distinct reinstall paths; other methods rerun
their normal install route.

## `AppSpecStep` (`steps/app_spec_step.py`)

Adapts one `AppSpec` into an ordinary `Step` so it can sit in `MASTER_REGISTRY` next to Homebrew/zsh/etc.:

- `check_installed` → `spec.check(ctx)` on Unix; exact WinGet package detection on Windows
- `is_applicable` → hides the app on Windows when `spec.windows is None`
- `run(ctx, *, reinstall=False)` → `install_app(ctx, spec, reinstall=reinstall)`
- `dry_run_preview` → one line describing whichever `InstallMethod` would be used on the current OS/distro

There's no more "always offered, re-running lets you add things you skipped before" special case — that used to live on `GuiAppsSelectionStep`/`IdeSelectionStep` because they were the only steps offered on every run regardless of status. Now *every* entry in `MASTER_REGISTRY` behaves that way (see [02_steps_and_providers.md](02_steps_and_providers.md)'s idempotency model), so `AppSpecStep` doesn't need to special-case it.

`run_menu` (in `wizard.py`) is what used to be `run_selection_step` — a recurring checkbox over every applicable `Step` (not just `AppSpec`s), nothing pre-checked. It refreshes applicability and live status after each batch, so installing a prerequisite can expose another entry without restarting the executable. A failure in one selected item doesn't abort the rest: failures are recorded per-item and the batch continues, so picking 5 things where 1 has a network hiccup still installs the other 4.

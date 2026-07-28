# CLI reference

```text
workstation-setup [OPTIONS]
```

| Option | Behavior |
|---|---|
| `--dry-run` | Preview applicable actions without running installers or writing the run log/state. The initial bootstrap choice is still interactive unless `--yes` is also supplied. |
| `--yes`, `-y` | Suppress prompts for targeted automation. Existing installs are left unchanged. With no `--only`, no menu entry is selected and nothing runs. |
| `--only ID` | Restrict execution to a step ID. Repeat to select several IDs. |
| `--skip ID` | Remove a step ID from the recommended path and menu. Repeat to skip several IDs. |
| `--version` | Print the application version and exit. |
| `--help` | Print Click-generated help and exit. |

`--only` is applied before `--skip`; if the same ID appears in both, it is not
run. Unknown IDs simply match no entry, so verify IDs before automating.

## Step IDs

Core bootstrap IDs:

```text
homebrew  zsh  oh-my-zsh  zsh-theme  set-default-shell
asdf      asdf-plugins  git  gh         gh-auth-login  ssh-key
```

Homebrew, shell, and asdf IDs apply only to Linux/macOS. On Windows, the
recommended core set is `git`, `gh`, `gh-auth-login`, and `ssh-key`.

IDE IDs:

```text
jetbrains_toolbox  vscode  cursor
```

Application IDs:

```text
chrome  spotify  slack  devin_desktop  gcloud_sdk
```

`devin_desktop` is currently hidden on Windows.

## Examples

```bash
# Inspect every available action without changing the machine.
./workstation-setup --dry-run

# Interactively choose only from the menu, omitting one application.
./workstation-setup --skip devin_desktop

# Run explicit, non-interactive bootstrap targets.
./workstation-setup --yes --only homebrew --only git --only gh
```

```powershell
# Windows equivalent (PowerShell).
.\workstation-setup-windows-x86_64.exe --yes --only git --only gh
```

```bash
# Preview a single app's platform-specific install method.
./workstation-setup --dry-run --only vscode
```

The step IDs are stable implementation identifiers, not package names. An item
can be unsupported or hidden on a particular platform even when its ID is
valid. Consult [the usage guide](usage.md) for interactive and recovery flows.

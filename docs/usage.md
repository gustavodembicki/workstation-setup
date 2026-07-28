# Using workstation-setup

## Before you start

Use a Linux, macOS, or Windows machine with an internet connection and an interactive
terminal. Several supported install routes invoke `sudo`; authenticate only
when you understand the displayed system prompt. Keep the terminal open while
an install runs, especially during downloads and `gh auth login`.

Windows support targets Windows 10 1809+ and Windows 11 on x64. WinGet must be
available; it is normally installed with Microsoft App Installer. The wizard
reports how to install or re-register App Installer and exits without changing
the machine when WinGet is missing.

Release binaries do not need Python. If you run from source, install the
development dependencies described in the [README](../README.md).

## First run

1. Start the binary in a terminal.
2. Confirm the detected operating system is correct.
3. Choose whether to run the recommended bootstrap. Linux/macOS offer Homebrew,
   shell setup, asdf, Git/GitHub CLI, and SSH; Windows offers Git/GitHub CLI
   and SSH. It is a convenience path—not a requirement.
4. For each recommended item, confirm the action. Some actions open an
   additional prompt: changing the login shell and overwriting an SSH key are
   separately confirmed.
5. Use the master menu that follows to select any individual tool, IDE, or app.
   Nothing is selected by default.
6. Review the summary printed after each phase.

The master menu is shown even after accepting the recommended bootstrap, so
you can add applications in the same run.

## Re-running the wizard

Installation status is detected from the live machine, not from a prior run.
When a selected item is already installed, choose one of the following:

- **Reinstall / Modify** runs the item again. Homebrew-backed packages use
  `brew reinstall`, WinGet packages use a forced install, and
  configuration-oriented steps prompt again as appropriate.
- **Leave as is** records no change.
- **Cancel** leaves that item unchanged.

This prevents an existing installation from being silently overwritten. In
unattended `--yes` mode, already-installed items are left unchanged because
there is no terminal available to choose a reinstall.

## Preview and automation

Use a dry run to inspect the available items and the actions each would take:

```bash
./workstation-setup --dry-run
./workstation-setup --dry-run --only homebrew --only vscode
```

For scripted or CI-like use, explicitly target the desired IDs:

```bash
./workstation-setup --yes --only homebrew --only git --only gh
```

Do not use bare `--yes` as a shortcut for a default setup. It intentionally
does nothing without `--only`. See [CLI reference](cli-reference.md) for all
IDs and option behavior.

## Failures, cancellation, and records

If a command fails during a normal run, the wizard reports the failed step.
The recommended bootstrap lets you decide whether to continue; independent
items selected in the menu continue after a failure. An aborted or failed run
keeps a diagnostic log at `~/.workstation-setup/run.log` and reports its path.
A clean successful run deletes that temporary log.

`~/.workstation-setup/state.json` records outcomes and timestamps for audit
purposes. It is not the source of truth for installation detection; deleting
or editing it does not make the wizard treat software as installed or missing.

If an app is marked unsupported, its current registry has no install route for
your OS or Linux distribution. No workaround is attempted automatically.

### Linux app availability

On Debian/Ubuntu, Chrome and Spotify use their official APT repositories, and
Slack and VS Code use their official `.deb` packages. Those four routes are not
currently available on Fedora or Arch and are shown as **unsupported** there.
JetBrains Toolbox, Cursor, Devin Desktop, and Google Cloud SDK use portable
Linux installers and are available on all three supported Linux families.

The APT-repository route installs `gnupg` when needed to validate its signing
key. The Google Cloud SDK route installs `which` through the detected native
package manager when the vendor installer requires it.

### Windows app availability

Windows installs Git, GitHub CLI, Chrome, Spotify, Slack, Google Cloud SDK,
JetBrains Toolbox, VS Code, and Cursor by exact WinGet package ID. Homebrew,
zsh, Oh My Zsh, asdf, and Devin Desktop are hidden because they have no native
Windows route in this release. The wizard refreshes its process `PATH` after
WinGet runs so GitHub authentication and SSH setup can continue in the same
session.

## Sensitive actions

The wizard may download third-party installers, add apt repositories, invoke
`sudo`, change your login shell, create an SSH key, or run interactive GitHub
authentication. Review [Security model](security.md) before using it on a
machine with stricter controls.

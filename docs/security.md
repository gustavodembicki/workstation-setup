# Security model

## What is curated

`workstation-setup` does not accept an arbitrary package name or download URL
from the user. The menu is assembled from a fixed registry of core steps, IDEs,
and apps. Each app/IDE has an `AppSpec` with a macOS route and one or more
Linux routes. App/IDE URLs used for downloads, scripts, GPG keys, and apt
repository lines are centralized in `src/workstation_setup/registry/trustlist.py`;
core installer URLs are explicit constants in their corresponding steps.

That makes the set of external endpoints reviewable in one place. It does not
make those endpoints risk-free: adding or changing a trustlist entry is a
security-sensitive code change and must be reviewed as such.

## Privileges and interactive boundaries

Depending on your selections, the wizard can:

- invoke `sudo` for system packages, apt repository configuration, or archive extraction;
- download and execute vendor-provided installer scripts;
- change the login shell with `chsh`, after a separate confirmation;
- generate an ed25519 SSH key, with a separate confirmation before replacing an existing key;
- start `gh auth login` attached to the real terminal, so credentials are never hidden in captured output;
- upload a public SSH key to GitHub only through the chosen GitHub CLI flow.

Review terminal prompts and vendor content before granting elevated privileges
or authenticating. The state file is designed to record step outcomes; treat
your home directory and logs according to your local security policy.

## Current limitations

The curated trustlist is an allowlist of installation sources, not artifact
verification. This project currently does **not** maintain or verify checksums,
signatures, provenance attestations, or pinned versions for all downloaded
artifacts. Some routes use the vendor's apt GPG-key mechanism; others download
`.deb`, AppImage, tarball, or script content directly from a trusted URL.

As a result, use the tool only when you accept the relevant vendor trust and
your network controls. For high-assurance environments, inspect the trustlist
and generated commands first with `--dry-run`, apply organizational controls,
or install software through your approved distribution mechanism instead.

## Reporting or changing a trust boundary

Do not add a URL inline in an app registry or conceal a new external call in a
step. Place the URL in the trustlist, document its installation method, and
add tests for the resulting route. The contributor workflow and invariants are
documented in [AI Knowledge](ai/README.md).

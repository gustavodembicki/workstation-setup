# docs/ai — AI Context Layers

Layered documentation for AI agents. Load only the file(s) relevant to your task — each is self-contained.

| File | What it covers |
|------|----------------|
| [00_overview.md](00_overview.md) | Why this exists, scope (Linux/macOS only), tech stack, high-level flow |
| [01_architecture.md](01_architecture.md) | Module map, the Step/Provider/Registry abstractions, wizard orchestration |
| [02_steps_and_providers.md](02_steps_and_providers.md) | Step contract, idempotency model, PackageProvider, PATH gotcha |
| [03_registry_apps_ides.md](03_registry_apps_ides.md) | AppSpec/InstallMethod model, how to add a new app or IDE |
| [04_testing.md](04_testing.md) | FakeRunner pattern, ctx factories, unit vs. manual/Docker verification |
| [05_packaging_ci.md](05_packaging_ci.md) | PyInstaller spec, no-cross-compile constraint, CI/release workflow |
| [06_change_playbook.md](06_change_playbook.md) | Safe recipes and security invariants for common future changes |

## Quick orientation

- **Adding a new installable app or IDE?** → [03_registry_apps_ides.md](03_registry_apps_ides.md)
- **Adding a brand-new Step (a new category, not a registry entry)?** → [02_steps_and_providers.md](02_steps_and_providers.md) + [01_architecture.md](01_architecture.md)
- **Writing or fixing a test?** → [04_testing.md](04_testing.md)
- **Touching the PyInstaller spec or CI workflows?** → [05_packaging_ci.md](05_packaging_ci.md)
- **Adding an app, Step, provider, URL, or prompt?** → [06_change_playbook.md](06_change_playbook.md)
- **Understanding the full picture?** → [00_overview.md](00_overview.md) then [01_architecture.md](01_architecture.md)

The public, user-facing documentation lives one level up: [usage guide](../usage.md),
[CLI reference](../cli-reference.md), and [security model](../security.md).

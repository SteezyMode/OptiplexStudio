# Studio — current implementation and verification

Updated: **2026-10-29**. This describes the published **v0.4.12** on `main` (commit `3b4bf917ab2ecf71d9b345ab192421440f97af4c`), not historical remote-service experiments or unmerged ideas.

## Available in current .deb

- Local-first GTK3 desktop and unified Studio projects; new projects include documents, categorized assets, Git initialization and a Godot starter scene.
- **Non-destructive discovery** of historical v1 Blank, Godot, Music/Audio, Animation and 3D manifests, plus Godot projects without a Studio manifest. Existing projects are not silently migrated or overwritten.
- Local asset imports with conflict checks, project documents, reviewed project snapshots, local Git status and project-scoped conversation discovery/resume.
- Native tool discovery/launch for Godot, Blender, Blockbench, LMMS, and optional Krita/VSCodium; optional consented rootless tool setup.
- Codex integration uses the local executable and project ownership/sandbox rules. Binary availability is **not** authenticated, ready-to-work Codex status.

Studio's ordinary project operations require no SSH, Tailscale, Wolf, NOW, Docker or hosted browser backend. Wolf can independently display a workstation session but is not a required Studio service.

## Verification evidence

- [v0.4.12 release](https://github.com/SteezyMode/OptiplexStudio/releases/tag/v0.4.12) is published with a versioned Debian installer, SHA-256 sidecar and stable-named Current installer.
- [PR #36](https://github.com/SteezyMode/OptiplexStudio/pull/36) added legacy-project/no-migration regression tests and repaired an installed-package CI cleanup failure.
- The exact [main commit CI](https://github.com/SteezyMode/OptiplexStudio/actions/runs/40859485766) and [release CI](https://github.com/SteezyMode/OptiplexStudio/actions/runs/40859485691) **passed** on October 29. These include unit, GTK fixture, Debian payload and installed-package smoke checks on GitHub runners.
- Earlier October 26 scheduled CI failure followed a successful installed-app GUI smoke check: temporary GVfs cleanup returned an error. PR #36 addressed this; subsequent main CI passed.
- These are CI and isolated GTK evidence, **not** independently observed normal-user device installation or live integration acceptance.

## Still open

1. [#31 — Codex sign-in and verified readiness](https://github.com/SteezyMode/OptiplexStudio/issues/31): verify official CLI login, guide sign-in/retry/cancel, then—with consent—exercise an authenticated project-scoped embedded interaction. A version command or discovered path cannot pass this gate.
2. [#30 — Unified project UI and capabilities](https://github.com/SteezyMode/OptiplexStudio/issues/30): historical project discovery is fixed; tool-specific project actions, navigation and verified readiness still need end-to-end work.
3. [#27 — Core-four creative workflow](https://github.com/SteezyMode/OptiplexStudio/issues/27): fresh compatible machine, Godot+Blender+LMMS+Codex native workflow, editable source-to-export roundtrip and actual playback. Recovery and off-host restore also remain unaccepted.

**Next engineering action:** tackle #31 in a focused PR without modifying user credentials, project contents or unrelated server services. Distinguish code/fixture CI from a logged-in workstation result.

For current instructions use [AGENTS.md](../AGENTS.md), [CONTRIBUTING.md](../CONTRIBUTING.md) and [RELEASING.md](RELEASING.md). Historical v0.3.0 remote/container guides do not define Studio's supported local-first workflow.

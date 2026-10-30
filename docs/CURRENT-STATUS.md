# Studio — current implementation and verification

Updated: **2026-10-29**. This describes the latest Studio source (package version **0.4.21**); verify the **actually published Current .deb** using the repository's latest GitHub Release rather than assuming a source version is a published artifact. Historical remote-service experiments are not part of the supported product.

Alpha 1 acceptance gates are tracked in [the Alpha 1 roadmap](ALPHA-1-ROADMAP.md), a subset of the frozen [v1 six-milestone plan](https://github.com/SteezyMode/OptiplexStudio/issues/3); **none are signed off solely by CI**.

## Integration pass in v0.4.20

- **Studio workbench is the default first tab:** Edit/Play Godot, launch Blender/LMMS, open/import project files and prompt/resume Codex from one surface. The other Project tab contains documents, context, secondary editors and collapsed tool diagnostics; the third Creative Tools tab is removed. Add Godot appears only when the selected project lacks a scaffold.
- **Direct Play** starts the selected Godot main scene with the same validated project path and executable as the editor action, but without `--editor`; it neither mutates the Godot project nor claims playback was observed. No more navigating to an external launcher tab for edit–play–revise.
- **Codex project affinity:** changing the selection closes the previous project's idle embedded conversation, leaving its history resumable; selecting another project during an active turn is rejected. New/resumed conversations switch to the Studio workbench, not an unrelated tab.
- New CI tests verify scoped Play argv, missing-scaffold/traversal refusal, project switch handling, and the default two-tab GTK layout. This is source/CI acceptance, **not** live Godot playback or an authenticated AI tool roundtrip.

## AI workflow preflight (v0.4.21)

- Code inspection uncovered a real prompt-launch failure in the v0.4.20 embedded Codex workflow: the Run/prepared-task path called `Gtk.TextView.set_text()`, which is not a valid GTK3 method. The initial prompt is now supplied to `EmbeddedView` before the async Codex connection begins, and `connected()` uses the widget's text buffer to submit it once.
- Native GTK GUI regression tests now open a **real** embedded conversation composer with a representative dead-tree creation prompt, simulate the successful connection without credentials, and verify its text is populated and submitted exactly once. This is **not** a real model request, Blender MCP call, `.blend` or Godot playtest.
- The CI runner has no real Blender, Godot or Codex model account; no host desktop, Tailscale or remote service was modified. A real workstation test (Alpha A1–A4) remains required. Do not claim AI asset generation works from CI alone.

## Available in current .deb

- Local-first GTK3 desktop and unified Studio projects; new projects include documents, categorized assets, Git initialization and a Godot starter scene.
- **Non-destructive discovery** of historical v1 Blank, Godot, Music/Audio, Animation and 3D manifests, plus Godot projects without a Studio manifest. Existing projects are not silently migrated or overwritten.
- Local asset imports with conflict checks, project documents, reviewed project snapshots, local Git status and project-scoped conversation discovery/resume.
- Native tool discovery/launch for Godot, Blender, Blockbench, LMMS, and optional Krita/VSCodium; optional consented rootless tool setup.
- Creative Tools now shows passive core-four status for Godot, Blender, LMMS and Codex, with explicit Settings directions and automatic refresh. Discovery is labeled **Detected / launch unverified**, never green Ready merely for an executable file. Missing alpha core tools are an actionable setup warning; missing optional tools are not treated as an application failure.
- Godot-only actions depend on the selected project's actual `project.godot`; legacy projects without it offer a confirmed, non-destructive Add Godot action. Blender, Blockbench, LMMS and Krita launch in existing project-owned models/music/art directories, never by guessing source documents.
- Codex integration uses the local executable and project ownership/sandbox rules. CLI sign-in reports **Signed in**, not verified AI readiness, and cannot infer live model access from a binary or saved credentials. Settings offers normal CLI sign-in and official device-code sign-in.

Studio's ordinary project operations require no SSH, Tailscale, Wolf, NOW, Docker or hosted browser backend. Wolf can independently display a workstation session but is not a required Studio service.

- **One AI creation flow (v0.4.19):** all new project-scoped embedded Codex conversations now receive universal task-based guidance: Blender MCP for props, flora, weapons, architecture, humans and materials; MPFB for human-specific anatomy; Godot for scenes/gameplay; LMMS for audio; dormant Rigger only on request. The previous Character Study preset is removed. **Settings → Install AI creative tools** is the shared integration entry, not a separate Character Lab product. Existing project documents, sandbox and on-request approvals remain unchanged. Download/install and live MCP readiness are distinct: the real Blender socket, MPFB asset pack and completed Codex tool calls are still physically unverified. See the [AI creative integration guide](CHARACTER-LAB.md). The five Alpha 1 gates remain unchanged.

## Verification evidence

- v0.4.19 adds regression checks for generic developer instructions even in a new project without AI_MEMORY, preserved user memory, no character-specific UI entry, and unchanged Codex sandbox/approval policy. This does not demonstrate artistic output or functioning agent MCP calls on a Linux desktop.

- v0.4.18 adds unit/GTK tests for installer consent, installed package presence, bundled modules, Blender extension activation, dormant Rigger, pinned visual MCP, localhost/no-clobber Codex registration and the offline socket doctor. This is CI evidence only; physical Blender 5.2 and Codex MCP proof remain open.

- The v0.4.16 source adds testable passive readiness classifications, in-app core-four status, Settings installation feedback and stale-worker protection; regression tests mock discovery without executing binaries or touching tool credentials. **No new runtime smoke test or physical Alpha gate is accepted by this change**.

- The 0.4.15 project-capability change includes tests for legacy Blank/Music/Godot projects, idempotent Godot initialization, no file or manifest overwrite, symlink refusal, creative-tool working directories and GTK button state. These are source/CI checks; **real creative editor launch and Godot scene playtest remain unverified**.

- The 0.4.13 source introduced bounded read-only Codex `login status` interpretation, explicit `--device-auth`, and failure/secret-handling tests. The 0.4.14 source adds an explicit, confirmed **Test Codex in selected Project** action in Settings. It opens the existing in-app project-bound conversation with a benign no-tools prompt, after the Settings dialog closes; it does not bypass the sandbox, silently mark AI ready, or consume model usage without explicit user confirmation. Login polling now skips busy periods rather than stopping entirely. **Authenticated model replies and physical sign-in are still unverified**; #31 remains open.

- [v0.4.14 release](https://github.com/SteezyMode/OptiplexStudio/releases/tag/v0.4.14) is published with a versioned Debian installer, SHA-256 sidecar and stable-named Current installer.
- [PR #36](https://github.com/SteezyMode/OptiplexStudio/pull/36) added legacy-project/no-migration regression tests and repaired an installed-package CI cleanup failure.
- The exact [main commit CI](https://github.com/SteezyMode/OptiplexStudio/actions/runs/40859485766) and [release CI](https://github.com/SteezyMode/OptiplexStudio/actions/runs/40859485691) **passed** on October 29. These include unit, GTK fixture, Debian payload and installed-package smoke checks on GitHub runners.
- Earlier October 26 scheduled CI failure followed a successful installed-app GUI smoke check: temporary GVfs cleanup returned an error. PR #36 addressed this; subsequent main CI passed.
- These are CI and isolated GTK evidence, **not** independently observed normal-user device installation or live integration acceptance.

## Still open

1. [#31 — Codex sign-in and verified readiness](https://github.com/SteezyMode/OptiplexStudio/issues/31): verify official CLI login, guide sign-in/retry/cancel, then—with consent—exercise an authenticated project-scoped embedded interaction. A version command or discovered path cannot pass this gate.
2. [#30 — Unified project UI and capabilities](https://github.com/SteezyMode/OptiplexStudio/issues/30): discovery and Godot capability controls are implemented; complete per-tool health/readiness and real editor roundtrip still need end-to-end acceptance.
3. [#27 — Core-four creative workflow](https://github.com/SteezyMode/OptiplexStudio/issues/27): fresh compatible machine, Godot+Blender+LMMS+Codex native workflow, editable source-to-export roundtrip and actual playback. Recovery and off-host restore also remain unaccepted.

**Next engineering action:** use the Current v0.4.21 .deb to physically exercise the [Alpha A1–A3 clean-install and core-four flow](ALPHA-1-ROADMAP.md). Fix only reproducible failures found on-device, then complete A4 real Godot media playback and A5 off-host recovery. Keep #27, #30, #31 open until accepted.

For current instructions use [AGENTS.md](../AGENTS.md), [CONTRIBUTING.md](../CONTRIBUTING.md) and [RELEASING.md](RELEASING.md). Historical v0.3.0 remote/container guides do not define Studio's supported local-first workflow.

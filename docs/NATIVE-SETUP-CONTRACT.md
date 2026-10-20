# Native Studio setup contract — design and current evidence

**Status: proposal / partial implementation, not a finished installer.** Tracks [release-priority issue #27](https://github.com/SteezyMode/OptiplexStudio/issues/27) and the unchanged [frozen v1 contract #3](https://github.com/SteezyMode/OptiplexStudio/issues/3).

## User-level contract

1. **Install Studio** using one documented package path on supported amd64 Linux. Do not require a terminal full of manual project-specific setup steps.
2. **Open Studio** and either create or open a project. Native-first operation must not require Wolf, Moonlight, Tailscale, Docker, a public server, or a second account.
3. **Use Codex** on the selected project with explicit user authorization, visible errors, and recoverable project/conversation context.
4. **Make an asset or soundtrack** with Blender and LMMS; preserve editable source and transfer standard GLB/OGG or WAV into the same Godot project.
5. **Reopen/recover** after closing Studio, replacing a supported app version, or restoring data from backup.

All five steps need real acceptance tests. None should be described as working solely because an executable exists.

## Engineering model

- **Separate responsibilities:** (a) read-only environment detection, (b) explicit user-approved tool installation/configuration, (c) per-project launch/adapters, (d) integration smoke tests, (e) persistence/backup and restore. Never bury installation or migration in a diagnostic.
- **One preferred default per capability:** Godot, Blender, Codex, LMMS for the initial in-house beta. Optional creative tools are tracked separately, not prerequisites.
- **Native first:** honor existing executable installations (including user-managed standalone archives/AppImages), prefer documented official/pinned packages when installing, and avoid silent Flatpak, container, system-service or system-wide configuration changes.
- **Portable identity:** project, home and binary paths are discovered/configured, not tied to `/home/optiplex` or Wolf-specific `/projects`. Local project paths are canonical; remote paths require an explicit mapping.
- **Reversible state:** approved installs must be idempotent, existing projects are not overwritten, errors remain actionable, rollback is documented, and no installer adjusts Jellyfin/Wolf/NOW/Tailscale or active services.
- **Security:** Codex remains project-scoped, uses its normal sandbox/approval policy, doesn't automatically install MCP bridges or start unrestricted ports; installation is explicit and reviewable.
- **Testability:** disposable Ubuntu/Pop!_OS representative installation + packaging CI + actual GUI/user playtest. A simulated CLI test is evidence of detection logic only.

## First small implementation: read-only native preflight

`tools/native_preflight.py` discovers executable candidates for the core four in conventional install paths and legacy user-managed `~/StudioProjects/.tools` staging. It prints a concise report, offers `--json` for future setup UI use, returns nonzero when a tool is missing, and **does not install, connect, launch or modify anything**.

Example (diagnostic only; not a requested permanent user setup step):

```sh
python3 tools/native_preflight.py
```

The preflight intentionally reports *executable presence*, not actual health, installed version, export support, MCP connection or project readiness. Native Studio **cannot yet operate completely without its remote Tailscale/Wolf-oriented routes**; making local launch and Codex/asset handoff reliable is follow-up work, not magically solved by the preflight.

## Next engineering slices — do in order

1. Verify preflight against isolated fixture tests/CI; document actual observed machine state without assuming it is a clean installation.
2. Add a **local core-four launch adapter** with scoped project paths and explicit readiness/error handling. Choose supported Godot/Blender/LMMS CLI invocations after inspecting their exact installed help/version output in a disposable environment. Reuse project-aware Codex behavior; don't create parallel agents.
3. Add a controlled, non-destructive installation plan (pinned upstream sources + checksums, prerequisites, platform checks, clear opt-in, rollback), then test on a fresh disposable Linux system.
4. Prove a freshly created project accepts an editable Blender asset and LMMS audio and plays in Godot. Visually review real output.
5. Prove off-host backup and isolated restore, clean-restart/reconnection and Codex resume. Only then mark the frozen milestone complete.

**Not part of this task:** Cyclops, Material Maker, Zed, Pixelorama, GdUnit4, new editor/GUI redesign, speculative new MCP frameworks, or a polished wizard before the backend is demonstrably stable.

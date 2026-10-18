# OptiPlex Studio — current status and handoff
Updated: **2026-10-19 JST**. Source of truth for *current observed development*, read with the frozen [six-milestone v1.0 release contract](https://github.com/SteezyMode/OptiplexStudio/issues/3). Do not retroactively redefine that contract.

## Versions: release vs. development vs. machine
- **Latest published GitHub release: [OptiPlex Studio v0.3.0](https://github.com/SteezyMode/OptiplexStudio/releases/tag/v0.3.0)** (published 2026-10-16). Includes an amd64 Debian package and checksum.
- **Current `main`: post-v0.3.0 development code, documentation and host-side helpers**. It is **not** a published v0.4 or v1.0 release. A successful `git pull` on the host updates a checkout, **not** an installed desktop application, package, running Wolf container, or other service.
- The existing on-host Art Director workflows and Wolf desktop were exercised separately from the v0.3.0 package. The exact installed native/remote GTK application build has **not been reverified here**; don't infer it from GitHub tags.
- Companion [OptiPlex NOW](https://github.com/SteezyMode/OptiplexNow) is a separate application. Its latest release is **v1.13.0**, not Studio v0.3.0.

## Frozen v1.0 contract — six milestones, status as of this review
Official acceptance criteria are on [issue #3](https://github.com/SteezyMode/OptiplexStudio/issues/3), not redefined here. `Verified` means user-observed in a relevant live workflow; a past agent or headless claim alone is not enough.

| Frozen milestone | Status | Evidence and remaining acceptance |
| --- | --- | --- |
| **1. Stabilize existing integrations** | **Substantially demonstrated; final baseline cross-check pending** | Playable Godot tests, Blockbench glTF export, LMMS audio export, Codex Godot/Blockbench/LMMS tools exercised; a same-host backup exists. Need a deliberate known-good replay of **the original** listed integrations and baseline, not infer release acceptance from newer demos. |
| **2. Blender MCP** | **Partial / operationally demonstrated** | Blender MCP connected and was used for real objects/character work; Blender Python and GLB exports demonstrated. Startup, reconnection and reliable project-scoped availability after Wolf recreation or reboot remain unverified. Scripted Blender Python is an accepted fallback under the frozen contract. |
| **3. Rigging and animation convention + one mechanical test** | **Demonstrated broadly; original mechanical-test acceptance not formally checked off** | An animated crawler/security camera and later humanoid retarget/animation audition/playable animation tests occurred. The exact frozen mechanical-creature/prop in-running-Godot acceptance should be replayed and signed off separately, rather than substituted with zombie work. |
| **4. Codex project awareness** | **Accepted / completed** | User confirmed a fresh project-scoped Codex task modified the existing player's fall reset without breaking the test. |
| **5. Persistent and recoverable** | **Incomplete — high priority** | One local Studio backup `~/StudioBackups/studio-baseline-20261018.tar.gz` (467 MB, integrity checked), host project bind mount, timed Godot registration and demo controls now exist. **No off-host restore test;** local-first/native+Wolf common runtime not implemented; stable Blender MCP reattachment, reboot/container rebuild and clean install acceptance outstanding. See [#5](https://github.com/SteezyMode/OptiplexStudio/issues/5), [#6](https://github.com/SteezyMode/OptiplexStudio/issues/6), [#7](https://github.com/SteezyMode/OptiplexStudio/issues/7) and [ADR-001](ADR-001-LOCAL-FIRST-SHARED-STUDIO-RUNTIME.md). |
| **6. New-project two-room horror acceptance test** | **Not accepted / still outstanding** | The separate Threshold prototype has a playable corridor/room, player interactions, audio and title/death/victory states. These and the V3 hallway demo **do not prove** the frozen fresh-project, two-room, interactive door, animated object, music and transition test. Do not check it off by renaming existing work. |

Only milestone **4** is explicitly marked complete in the frozen issue. Keep the other boxes open pending their **exact** criteria; do not widen v1.0 with later features.

## What is actually working in the 2026-10-18/19 development session
- Studio project files on host: `/home/optiplex/StudioProjects`; Wolf remounts them under `/projects`. Separate Wolf/XFCE desktop and physical desktop remain isolated GUI sessions on the same host hardware.
- Godot 4.7.2 and Blender 5.2 observed inside Wolf; Art Director Codex runs on host in project-scoped tmux. The host can continue a CLI task after Moonlight disconnect, but tmux does not survive host reboot.
- A **one-shot 3-minute systemd timer** registers approved Studio Godot project directories in Wolf's Flatpak Godot Project Manager. Operator installation and successful runtime output were confirmed: the first run added three projects; an additional run checked eight.
- **Universal experiment demo exit controls** were installed on host using that *same* timer: nine Python tests passed; actual Godot disposable-project preflight passed; five experiments modified successfully; the user directly confirmed **Esc pause menu and F10 quit** through Wolf/Moonlight. Regular production games, including Threshold, were not automatically modified.
- **Windowing was tested**: native Godot Wayland inside Wolf/XFCE gave undecorated windows. Switching demo launch to `DISPLAY=:0`, `--display-driver x11 --windowed --resolution 960x540` (with Flatpak `--socket=x11`) produced a **normal draggable/minimizable title bar**, user-confirmed. [Shared X11 launch script](../tools/run_wolf_studio_demo.sh) is in the repo, but still requires deployment/integration; it does **not** make all arbitrary launch paths automatically X11.
- Patient V3 animation viewer imported **28 clips** for native-source audition; user rated a few promising, a few cheesy, others mixed. The placeholder Quaternius zombie encounter now runs a `DORMANT → TURNING → APPROACH → ATTACK` controller, after fixing a syntax error by hand. Runtime behavior exists; **the zombie is not yet scary or a completed game.**
- The imported zombie was **measured in Godot** at 8.147 m source bounds; scale 0.18 made it ~1.466 m. Calculated target scale for 1.75 m is **0.21481**, but a final visually confirmed live scale acceptance is **not recorded**. Verify before marking the calibration finished.
- Godot/Flatpak had intermittent editor and launch issues; a headless validation earlier missed a parse error. Do not equate agent 'passed validation' with observed graphical success.
- A feature prototype for host-side persistent Codex/tmux sessions exists on [draft PR #8](https://github.com/SteezyMode/OptiplexStudio/pull/8); **not merged and not integrated with the app**.

## Two work tracks, deliberately separate
1. **Frozen Studio v1.0:** finish/replay the six original acceptance gates, especially #5 persistence/off-host backups and #6 the exact new-project two-room acceptance. No seventh v1 milestone is implied.
2. **Game-production pilot and post-v1 product direction:** user wants a **short, complete 5–10-minute zombie encounter game**, not endless modeling/asset sourcing. The playable V3 hallway prototype is an *early vertical slice*, not that finished game. See [#12](https://github.com/SteezyMode/OptiplexStudio/issues/12). Build a coherent beginning, exploration, one or two scary encounters, interaction, atmosphere/audio, and an ending; keep small human visual review gates.

### Later, only when the above is moving
- [#13](https://github.com/SteezyMode/OptiplexStudio/issues/13): improve demo discovery and one-click Play/Stop UX without creating a desktop full of one-off shortcuts. Esc/F10 and windowed X11 are solved for tested demos; **no universal GUI Play/Stop yet**.
- [#9](https://github.com/SteezyMode/OptiplexStudio/issues/9): Godot Project Manager **registration solved** in active Wolf; unified native/Wolf project/test browser still open.
- [#11](https://github.com/SteezyMode/OptiplexStudio/issues/11): general-purpose, **genre-neutral** production knowledge library (art, Blender, Godot logic, materials/fabrics, animals, vehicles, audio, UI, etc.). **Not** a zombie-only library or neural weight training. Start with a small approved metadata/recipes catalog. See [library v1 plan](STUDIO-GENERAL-PRODUCTION-LIBRARY-V1.md).
- Character visuals: Patient V2.1 had materially improved hands/shoulders/walk but weak zombie art; V2.2 was rejected by user as mostly a facial recolor; no body part must be reused. Avoid unbounded procedural re-modeling. Future V3 design should be coherent, ordinary-human zombie visuals with deliberately frightening animation rather than exaggerated muscles or retro polygon nostalgia.
- Source animation policy for now: **free only**, already-local first; any additional free Rokoko/Mixamo downloads must follow actual quality/rights review and account approval. See [free mocap shortlist](STUDIO-FREE-MOCAP-SOURCES-2026-10-18.md).

## Next-session handoff
1. Do not restart Wolf/Docker or interfere with the physical desktop simply for Studio experiments.
2. Confirm active scene launches with **X11 inside Wolf** and Esc/F10 exit, and measure final actor height before changing unrelated features.
3. Keep a short playable zombie mini-game as a clear creative deliverable; use Luna Medium for bounded routine Codex work and escalate only on a specific blocker. A passing headless run is not visual acceptance.
4. Schedule separate controlled tests for frozen v1 gates #1–3, #5 and #6; focus recovery/backup as the release risk.
5. Do **not** claim a new Studio release, newly installed GTK package, completed common runtime, clean reinstall or off-host backup until those operations are verified.

## Product safety
Preserve Jellyfin, NOW, Tailscale, Caddy, Wolf and existing project assets. Do not publish authentication tokens or backups, auto-download unapproved asset packs, bypass Codex sandbox, or silently replace finished models. Native local Studio must not depend on NOW or Wolf long term; [ADR-001](ADR-001-LOCAL-FIRST-SHARED-STUDIO-RUNTIME.md) captures that accepted design, not a shipped implementation.

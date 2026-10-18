# ADR-001 — Local-first Studio, shared machine runtime, interchangeable graphical sessions

Status: **ACCEPTED AS PRODUCT DIRECTION, NOT YET IMPLEMENTED**  
Decision: 2026-10-18  
Products: OptiPlex Studio; OptiPlex NOW (working title)  
Owner: product direction confirmed with user

## Decision

OptiPlex Studio is **primarily a locally installed game-development suite**. Its creative workflows and task state belong to a **single authoritative Studio runtime and workspace on the workstation**, not to a particular desktop session, window, streaming client or container.

The same workstation may expose multiple independent Studio frontends:

1. **Native/local:** Studio opened from the physical desktop's usual desktop environment (COSMIC/KDE/XFCE/etc.).
2. **Separate graphical session:** the *same* Studio installed on that workstation, opened inside an optional Wolf-provided independent desktop and streamed through OptiPlex NOW to a modest laptop/other client.
3. **Headless:** Studio tasks continue on the workstation without either frontend connected.

Switching between 1 and 2 should preserve projects, creative direction, source library, AI conversation history, task state, progress/output, settings that logically belong to the project, and access to **the same active Codex/agent process**. No file syncing, separate project clone, manual export, or duplicate agent launch should be required.

**Graphical process state is intentionally per session:** the Blender/Godot window and unsaved GUI edits in Wolf do not transfer to the physical desktop. Saving project files and relaunching a local Blender/Godot window does. Access to the same file does not make simultaneous edits safe.

OptiPlex NOW is a **standalone remote access/streaming application**, not Studio's task engine. NOW should offer both physical-desktop streaming where supported and independent-workspace streaming; both are deployment modes, neither is mandatory for Studio. The present Wolf/XFCE session is useful, proven, and should stay working while Studio evolves, but is not a required Studio dependency.

## Why

An independent Wolf desktop allows another household user to use the physical workstation while a laptop client accesses its GPU and CPU remotely. The value is **simultaneous use of powerful shared hardware**, not primarily isolation. Native local Studio must work just as well without any remote software. Both desktop sessions share finite machine resources (notably GPU VRAM), and their independent UI/desktop windows are not interchangeable.

## Current implementation baseline and gaps

- Host: Pop!_OS/COSMIC, shared project root `/home/optiplex/StudioProjects`.
- Wolf Studio container: independent XFCE desktop through Wolf/Moonlight; project bind mount `/home/optiplex/StudioProjects` → `/projects`.
- V2 Threshold Godot test runs inside Wolf. Host CLI Codex + Art Director workspace use `/home/optiplex/StudioProjects/.studio/art-director` and tmux. Wolf user `retro` has separate Linux home, Flatpak installs/settings and graphical apps.
- The bind mount already points both graphical sessions at the same **project bytes**, but does NOT itself share all Codex sessions/config, saved GUI layout, background task ownership, AI history or runtime identity. No fully shared Studio session manager has been implemented. A project file opened through separate paths must be normalized to one canonical project ID.
- Do not move user credentials or mount an unrestricted host Docker socket into Wolf as a shortcut. Retain project-scoped Codex launch rights and isolated credentials.
- Wolf/XFCE is an optional session runner. Keep existing games, Jellyfin, Wolf and host desktop unaffected during transition.

## Runtime boundary and minimum shared data model

The **Studio core/runtime** on the workstation owns:
- Stable project IDs and path aliases (`/home/optiplex/StudioProjects/Godot/threshold` ⇆ `/projects/Godot/threshold`), plus portable project metadata.
- Art Director knowledge, approved visual references, provenance/source inventory, production history, and asset/library manifests.
- Agent/task records: task ID, role, project, owner, started/last activity, process/session identity, state, append-only output log/history, sandbox/approval settings and explicit cancellation.
- Codex conversation lookup and resume mapping; existing running Codex processes must reconnect rather than spawn duplicates.
- Shared project-level settings, recent-project history and working state, with clear distinction from per-desktop display, layout, keybinding or personal preferences.
- Per-project concurrent-edit safeguards: show active edit/ownership, soft lease/lock for shared write actions, warn on divergent disk versions, atomic writes where feasible. A second frontend must not silently overwrite changes made by the other.
- Background job persistence independent of a GUI window. Linux interactive PTYs may use `tmux`; other workers/backends must fit the same abstract task interface. Tmux survives client disconnects, not workstation reboot, process crash or necessarily Codex API disconnection. Persist task records/logs and recover/resume where possible.

Studio frontends are thin **views and controllers**, locally or within Wolf. They do not own long-running tasks or writable authoritative catalogs. Noninteractive workers may run without any graphical session, but headless tasks that genuinely need a GPU/render display must use a supported execution context.

## Implementation boundaries

1. **Canonicalize file/data identity first.** Use shared project IDs independent of `/projects` path mapping; centralize source assets, Art Director inventory and reports on the workstation. Do not duplicate big binaries per GUI.
2. **Session manager MVP:** local host-side manager owns Codex/tmux sessions and durable logs. Frontends connect through a limited, authenticated interface (local IPC or an existing secured transport); no exposed general-purpose shell, privileged Docker access, extra public port, or unscoped file reads. A Wolf process should not require host credentials copied into the container.
3. **Two frontend test:** launch Studio natively on the OptiPlex and in Wolf, open Threshold and confirm same canonical project, task status, history and references. Start Codex from one view, reconnect from the other with **zero new Codex process**.
4. **Safe simultaneous work:** distinct independent window state; last-save detection and visible conflicts before overwriting project files. Avoid two GUI sessions driving one Blender process.
5. **Background/close behavior:** local GUI close and remote NOW disconnect both detach; explicit Stop Task terminates it after confirmation. When tmux/session missing, Codex saved conversation resume should work without falsely claiming a running process. Host reboot recovery should report interrupted tasks honestly.
6. **Packaging:** ordinary standalone Studio install works without Wolf, NOW or a container. Optional Wolf workstation profile brings the same Studio frontend and shares only approved paths and runtime interface.
7. **Cross-machine/remote distinction:** streaming a *host-resident* Studio frontend through NOW naturally uses the host runtime; installing the Studio UI on a physically different client and connecting to a remote backend is a later optional feature requiring deliberate authenticated client/server protocol design.

## Non-goals

- Making every Studio installation create its own XFCE desktop.
- Requiring NOW to use Studio locally.
- Duplicating Studio Codex/tmux management inside NOW.
- Assuming tmux saves graphical windows, survives host reboots, or makes arbitrary jobs immortal.
- Giving external clients unrestricted SSH/Docker/root access.
- Running simultaneously editing processes with no conflict detection.

## Acceptance criteria

- Local native Studio and Wolf Studio view **one canonical Threshold project** and **the same Art Director batch**.
- Start one project-scoped task from Wolf, abruptly close the MacBook/NOW client, access native Studio, and reattach to **the same task, transcript and process** without manually finding tmux names.
- Repeat in reverse; verify no duplicated agent/work and per-session graphical windows behave independently.
- Save a file locally; Wolf shows same version; concurrent saves report conflict rather than overwrite silently.
- Uninstall/disable NOW: native Studio and background task persistence still work.
- When only a weak laptop connects through NOW, GPU-heavy Blender/Godot stays on host. Physical desktop remains separately usable subject to shared hardware load.
- Distinguish actual implementation from this ADR: current system has path sharing and manual tmux, not the complete shared runtime/session GUI.

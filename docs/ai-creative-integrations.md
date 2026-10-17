# Optional AI-assisted creative integrations

Status: evaluated candidates, **not installed or enabled**. Each integration is optional and must be verified in the existing XFCE/Wolf session before becoming a launcher action.

## Integration policy

1. Use the project directory and its `AGENTS.md`, `GAME.md`, `PROGRESS.md`, and `DECISIONS.md` as the persistent handoff. Never put credentials in these files.
2. Prefer Codex-accessible editor tooling over an independent chat agent per application. Start with read-only inspection, then small approved writes and observable verification.
3. Run MCP processes only when the relevant editor/workflow is in use. Bind any unauthenticated editor socket to localhost inside the remote desktop. Never expose it on the public interface or Tailscale without a separately designed authentication layer.
4. Treat execution-capable plugins as privileged code. Install reviewed pinned revisions, use project-only permissions where feasible, take recoverable backups before mutations, and require user approval for deletes, exports, uploads, purchases or network access.
5. Distinguish *connectivity tested*, *read-only operation tested*, *write tested on disposable project*, and *production verified*. Do not claim an integration is supported before these checks.
6. Editors stay independently functional if their AI plugin is absent, disabled, or crashes.

## Priority pilots

| Workflow | Candidate | What would help | Required validation |
| --- | --- | --- | --- |
| Godot scenes and troubleshooting | [hybridindie/godot-mcp](https://github.com/hybridindie/godot-mcp) | Codex inspection of scene trees, resources, runtime errors; later small reviewed edits | Match installed Godot version; local-only bridge; read-only first; dry-run and undo for edits; compare Godot project after test |
| Blender modeling | [Blender's MCP server](https://www.blender.org/lab/mcp-server/) | Inspect scene and use Blender Python for geometry, materials and export | Check Blender version and plugin dependencies; **high risk** because generated Python has unrestricted effect inside Blender; use only isolated test files and restricted runtime, never give it unrestricted home/server access |
| Blender alternative | [RFingAdam/mcp-blender](https://github.com/RFingAdam/mcp-blender) | Broader scene/mesh/animation controls; Codex-compatible stdio server | Audit socket interface, file and code-execution tools; compare to official option, install only one |
| Krita paintover and texture work | [Acly/krita-ai-diffusion](https://github.com/Acly/krita-ai-diffusion) | Inpaint, outpaint, guided textures and image editing | Verify Krita/Flatpak compatibility, model backend and GPU/RAM usage; remote/cloud processing must be an explicit opt-in |
| Music composition | [LMMS](https://lmms.io/) with optional [lmms-mcp](https://github.com/ZipseLu/lmms-mcp) | Codex-assisted beats, melodic tracks, synth presets, automation, mixer effects and editable native LMMS sessions | Audit this third-party MCP before installation; pin version; restrict project output directory; verify MMP/MMPZ opening and rendering in LMMS on a disposable composition |\n| Sound editing and effects | Existing openDAW/AudioMass | Edit and assemble recorded effects; import reviewed AI-generated MIDI and WAV assets | Test end-to-end WAV import/export, effect processing, naming and game-engine playback |
| ChatGPT creative generation | Optional Runway connection | Create or revise sound effects, reference images or video, then import chosen files into project | External account, costs/credits, asset licensing, privacy and human review; never automatic uploads |

## First practical end-to-end pilot

1. Select a **disposable Godot project**, inspect it from Codex and inspect the running Godot scene through a local-only Godot MCP bridge.
2. Ask Codex to identify a specific scene problem without changing the scene. Capture the exact evidence in `PROGRESS.md`.
3. Authorize one small scene edit. Preserve a backup/diff, run the project validator and manually confirm the result inside Godot.
4. In a separate disposable music project, use an LMMS MCP candidate to create a pattern and render a WAV; inspect both the editable source and the exported sound. Export/import one Blender or Krita asset through existing Studio project files. Verify the asset in Godot and note its source.
5. Resume another Codex session and verify that the project documents, not chat history, are sufficient to recover the objective and status.

## Not in scope yet

No automatic multi-tool agent with broad server privileges; no persistent GPU-intensive local inference requirement; no public MCP socket; no automatic asset replacement; no assumption that a web chat can silently read private project files. These are integration boundaries, not limitations on future design.

## Project-aware tray design

Keep a small launcher and use an **opt-in** tray submenu named Creative Tools (Godot, Blender, Krita, ChatGPT, browser editors) that reuses existing launch callbacks. Only enable project-specific actions when a valid project is selected. Keep project import, setup and connection recovery in the client. Direct Godot launch must focus an existing process where available, not spawn duplicates. Verify submenu behavior with and without an active Wolf session before removing dashboard controls.

## Additional creative editor candidates (verified documentation, not deployments)

| Workflow | Integration candidate | Integration reality | Pilot gate |
| --- | --- | --- | --- |
| Blockbench low-poly modeling | [sosadly/blockbench-mcp](https://github.com/sosadly/blockbench-mcp) | 70-tool MCP bridge requires **Blockbench desktop**, not the browser editor; local HTTP listener and stdio adapter | Install a pinned, reviewed desktop build in disposable XFCE test environment; keep loopback-only, inspect before edit, verify native project export and undo |
| CozyClay previsualization | [NomaDamas/CozyClay](https://github.com/NomaDamas/CozyClay) | Has native MCP, CLI and embedded AI agent for shots/characters/camera; browser UI can stay | Prefer one control surface (MCP via Codex), test read-only scene then a reversible camera change, preserve .cclayproject; do not configure motion GPU worker initially |
| Piskel pixel art | [Ne9roni/piskel-cli](https://github.com/Ne9roni/piskel-cli) | Scripts native .piskel data and exports; no additional MCP daemon required | Audit CLI package and pinned dependencies; create disposable sprite, reopen in existing browser Piskel, export frames and verify pixels/animation |
| Onionskyn vector animation | [papptimus/Onionskyn](https://github.com/papptimus/Onionskyn) | Browser-first; no confirmed maintained MCP integration | Keep launcher/export only; revisit if a safe documented API appears |

**No automatic install:** These are third-party candidates, not verified production Studio extensions. In particular, do not change network listeners, start unrestricted JavaScript evaluation endpoints, or download code through unreviewed one-liner scripts. Use the existing project's approved import/export path and document provenance, revisions, and licenses.

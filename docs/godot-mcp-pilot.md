# Godot MCP pilot — deliberately opt-in

This is **not an installation performed on the XFCE server**. It documents the separately approved steps to connect the Codex CLI running inside a Godot project to the live Godot editor. Tested GitHub configuration code is not proof of a working editor connection.

## Prerequisites

- Godot 4.4 or newer on the Studio XFCE desktop.
- An isolated, backed-up disposable Godot project with its own `project.godot`.
- Codex installed and working within that project. Codex must trust project-local configuration before loading `.codex/config.toml`.
- Reviewed release of [hybridindie/godot-mcp](https://github.com/hybridindie/godot-mcp/releases) pinned to the **same** release for the Python MCP server and Godot addon. Pilot reference: `2026.10.12` (verify downloaded assets/checksums before installation).

## XFCE-host installation (explicit user action)

1. Inspect and approve upstream code and a pinned release. Install its Python MCP server in an isolated user-owned tool environment (such as `uv tool install godot-editor-mcp==2026.10.12`). Do **not** install via Docker; do not expose ports.
2. Unpack the matching release's `godot_mcp_addon.zip` into the disposable Godot project so `addons/godot_mcp` exists. Enable the Godot addon under Project Settings → Plugins.
3. In the **same host and project** where Codex runs, review what the project-local configuration generator proposes:
   ```sh
   python3 studio/godot_mcp.py /path/to/disposable/project
   ```
   Use the Studio repository's actual path to `studio/godot_mcp.py` when invoking from another directory.
4. If the proposed path and command are correct, explicitly create the project-local `.codex/config.toml` with `--enable`. The helper refuses to overwrite an existing configuration. Manually merge it if the project already has one.
5. Start Codex **inside the trusted project**. Use `/mcp` to confirm the `godot` server appears. Start the Godot editor with the addon enabled; confirm the addon reports connection to the loopback bridge.

## Read-only acceptance test

- Confirm the editor reports connected.
- Run `godot_get_server_info`, `godot_list_toolsets`, `godot_inspection_get_scene_tree`, and `godot_inspection_get_selected_node` (names and exposed toolsets depend on the pinned version).
- Confirm no scene, `.tscn`, script, or shared server file changed. Capture before/after repository status.
- Record actual commands, output, tool versions, failure modes, and results in `PROGRESS.md`.

## Write validation only after inspection passes

On disposable project only: review the exact scene edit, enable the minimum needed toolset, make one reversible node change, validate with Godot, manually playtest, and inspect the diff. Do not turn on broad toolsets by default.

## Architecture constraints

The Python MCP server uses **stdio** with Codex and maintains a loopback WebSocket bridge with Godot (default ws://127.0.0.1:9080; it is still a network listener, but bound to loopback only). Multiple concurrent stdio MCP servers competing for the same bridge port may fail; use one active Codex session for the pilot. Keep the editor independently useful if the MCP process exits. Never expose the bridge on a public address or grant Docker/server management access.

# Experimental Character Lab — MPFB, Blender visual MCP, and Rigger

**Optional, not an Alpha 1 acceptance gate.** Studio currently cannot prove these
integrations work inside its embedded Codex app-server; this is a cautious *local
workstation setup experiment* for a disposable Patient V4 project. Do not modify
the original Patient scene or an active production project.

**Status distinction:** source **prepared**, Blender extension **installed**,
Blender extension **enabled**, MCP server **registered**, server **connected**, and
model **tested** are different stages. No checkbox is accepted without actually
seeing the expected tool/response.

## The three integrations

| Tool | Role | Initial policy |
| --- | --- | --- |
| [MPFB 2](https://extensions.blender.org/add-ons/mpfb/) and [MPFB MCP](https://github.com/makehumancommunity/mpfb-mcp) | Parametric human base, facial anatomy, rigs, constrained MPFB commands | Install and test on a disposable Blender scene |
| [MCP for Blender](https://www.mcp-for-blender.com/docs/installation) | Blender inspection, screenshot and modeling feedback for Codex | Enable deliberately, loopback only, safe mode enabled |
| [Rigger](https://github.com/asu37/Rigger) | Later motion capture, retargeting and Godot export | Prepare and install extension, **leave disabled** |

MPFB MCP needs **both** the MPFB main extension and its separately packaged
**MPFB Bridge** add-on. It also requires a MakeHuman system asset pack. The visual
MCP is a different add-on on a different local port.

## One-click preparation in Studio

In **Settings → Experimental Character Lab**, select
**Prepare MPFB MCP and Rigger…** and confirm. This opens a terminal with an
additional explicit **YES** confirmation and then uses **pinned GitHub commits**
to download MPFB MCP and Rigger to
`~/.local/share/optiplex-studio/character-lab/`, creates an isolated
`mpfb-mcp/.venv` and builds Rigger's extension zip.

The helper never runs on Studio startup, a normal .deb install, or opening a
project. It does not use sudo, overwrite source checkouts, copy credentials,
modify Codex MCP config, change Blender preferences, enable add-ons or touch
project files. Python package installation and Rigger's upstream build script
**do execute third-party code** after user confirmation. If source revisions,
dependencies or the remote service are unavailable, setup stops and reports
the error. A retry leaves previous source trees intact.

For source checkout use `python3 -B studio/character_lab_setup.py status`
(read-only) or `python3 -B studio/character_lab_setup.py prepare` (explicit
confirmation). The helper requires Git, Python 3.10+ and Python venv/pip.
No addons are automatically installed or activated by this preparation.

## Complete the installation inside Blender 5.2

1. **MPFB:** In Blender open **Edit → Preferences → Get Extensions**, find
   **MPFB**, install and enable it. This uses the official Blender repository,
   not a random downloaded installer. From
   [MakeHuman Asset Packs](https://download.makehumancommunity.org/assets/downloadassets/index.html)
   download the **MakeHuman system assets** zip, then in MPFB's
   **Apply assets → Library settings → Load pack from zip file** import it.
   Restart Blender. Do not confuse the asset-pack zip with the MPFB add-on.
2. **MPFB Bridge:** Package the source from the prepared checkout using the
   same Blender executable you actually use in Studio. For a `blender` on PATH:
   
   ```sh
   mkdir -p "$HOME/.local/share/optiplex-studio/character-lab/mpfb-mcp/dist"
   blender --command extension build \
     --source-dir "$HOME/.local/share/optiplex-studio/character-lab/mpfb-mcp/bridge/mpfb_bridge" \
     --output-dir "$HOME/.local/share/optiplex-studio/character-lab/mpfb-mcp/dist"
   ```
   
   In Blender **Edit → Preferences → Get Extensions → Install from Disk**,
   choose the resulting `mpfb_bridge-*.zip`. Enable **MPFB Bridge**.
   The MPFB Bridge is **off** until you explicitly click
   **Start MPFB Bridge server** in its Blender preferences. It uses
   **127.0.0.1:9877**, separate from the visual MCP.
3. **Rigger:** In Blender choose **Install from Disk** and select
   `~/.local/share/optiplex-studio/character-lab/rigger/dist/rigger-*.zip`.
   **Leave it disabled** in Preferences. Do not download its optional
   motion-capture/pose models, run video analysis, or change the current rig.
   When we start the animation experiment, we can enable it and create a copy.
4. **Visual MCP:** With uv/uvx installed, use the publisher's installer:
   
   ```sh
   uvx mcp-for-blender install-addon
   ```
   
   Enable **Interface: MCP for Blender** in Blender preferences. Its
   local service uses `127.0.0.1:9876`. Check the Blender sidebar for its
   port. Do not expose either bridge on a LAN, Docker port forward or Tailscale.
   The visual MCP's socket has no authentication and can execute Blender code.

## Deliberately connect Codex only after verifying both local bridges

These commands **change your user Codex MCP configuration**. They should be
run only after reviewing what is already installed with `codex mcp list`.
Use the same Codex executable configured in Studio. Do **not** apply the commands
to a different Codex home/profile by accident.

```sh
codex mcp add blender --env BLENDER_HOST=127.0.0.1 --env BLENDER_PORT=9876 \
  --env BLENDER_MCP_SAFE_MODE=1 -- uvx mcp-for-blender

codex mcp add mpfb -- \
  "$HOME/.local/share/optiplex-studio/character-lab/mpfb-mcp/.venv/bin/mpfb-mcp"
```

If the `blender` or `mpfb` MCP name already exists, **stop and review it**
rather than overwrite or silently duplicate it. Restart the Codex process
after registering MCP tools. In Blender start the **MPFB Bridge** manually.
The visual MCP add-on may start automatically when enabled; check the sidebar.

The rich Codex viewport **plugin** is optional on top of the plain MCP server.
Its interactive viewport is documented for supported Codex clients, **not yet
verified inside Studio's GTK embedded transcript**. The base look/screenshot
tools may need the external Codex client first. Do not count rich-image rendering
as working in Studio without a real session test.

## Acceptance check for Patient V4 (not an alpha release gate)

1. With an empty disposable Blender scene, `mpfb_get_status` answers **ok**.
2. Create a neutral MPFB human, save its editable .blend in `models/`, add an
   appropriate rig and inspect front/side/three-quarter images using visual MCP.
3. Make a *controlled* deform/skin improvement and compare fixed-lighting,
   fixed-camera before/after renders. No changes to Patient V3.
4. Export a new .glb into the same disposable Godot project and actually view it.
5. Only later, enable Rigger on a copy and try one short mocap or retargeted
   action, verifying planted turns and hand contacts.

**Security/limits:** MCP for Blender's safe mode is a code-content filter, not
an operating-system sandbox. The loopback socket permits Blender Python
execution and can reach Blender's filesystem permissions; use a disposable
project and no exposed listening port. Studio's isolated Codex app-server may
block access to host-local MCP services; treat that as an integration bug to
test, not a reason to disable project isolation or expose the socket.

**Upstream references:** [MPFB install](https://github.com/makehumancommunity/mpfb-mcp/blob/master/INSTALL.md),
[MCP for Blender safe mode](https://www.mcp-for-blender.com/docs/reference/configuration),
[Rigger source/build](https://github.com/asu37/Rigger).

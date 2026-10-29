# AI Creative Tools — a shared game-asset workflow

**One Studio project and one AI conversation for all creative work.**
Blender and visual MCP are general-purpose tools for models, props, weapons,
flora, environments, materials, and animation. MPFB is a specialized extension
for anatomically coherent humans, not a character-specific Studio mode;
Rigger stays installed but disabled until an explicit retargeting/mocap task.
Godot creates/tests scenes and gameplay; LMMS handles music/audio. Codex
selects relevant available tools based on the user's request, not a lab type.
This experimental integration is not a new Alpha 1 gate.

## One on-device toolchain install (v0.4.19)

1. Install the [Current Studio .deb](https://github.com/SteezyMode/OptiplexStudio/releases/latest)
   on a supported Linux workstation. In Studio Settings, install or choose
   **Blender 5.2+** and **Codex**.
2. Choose **Settings → Install AI creative tools…**, review its disclosure and
   approve. Studio runs the actual installation in a local terminal. It may
   download several hundred megabytes and execute upstream packaging scripts.
3. The installer:
   - Fetches pinned MPFB MCP and Rigger sources; installs MPFB MCP in an
     isolated Python environment under
     `~/.local/share/optiplex-studio/character-lab/`.
   - Installs **MPFB** from Blender's official extension repository and
     builds/installs/enables its separate **MPFB Bridge** add-on.
   - Installs **Rigger** from its built extension ZIP, **without enabling it**.
   - Installs **MCP for Blender** (visual MCP, pinned PyPI release) in an
     isolated Python environment and calls its real `install-addon` command.
   - Registers two named MCP servers in the **existing user Codex profile**:
     `studio-mpfb` on loopback port 9877 and `studio-blender` on loopback
     port 9876, with visual MCP safe mode and telemetry disabled.
   - Never overwrites an existing MCP entry of those names. It does **not**
     change Studio projects, NOW, Wolf or Docker.
4. **Restart Blender and Codex.** Visual MCP and MPFB Bridge must be enabled
   and connected in the actual Blender instance. MPFB Bridge's listener is
   started manually from Blender's add-on preferences; it does not autostart.
5. MPFB also requires a **MakeHuman system assets pack**, containing eyes,
   skins and other base assets. Download it from
   [MakeHuman's official asset page](https://www.makehumancommunity.org/assets/downloadassets/index.html)
   and import once inside Blender **MPFB → Apply assets → Library settings →
   Load pack from zip file**. Restart Blender.
6. Open Studio, create a **disposable** unified project, and open
   **AI Workspace**. In the normal prompt, ask Codex to model a human, dead tree,
   weapon or prop, inspect the Blender result and export it into the Godot project.
   This starts real Codex model usage. No asset-category button is required.

This is not yet automatic end-to-end provisioning: the MakeHuman asset pack and
actual Blender bridge session still require a short first-run step. In
particular **Codex MCP registration is not a live AI tool-call test**.

## General creative workflow acceptance (one project)

- For a *general prop* or flora study, use Blender visual MCP to create an
  editable .blend, inspect the silhouette from multiple angles, refine it and
  export .glb to the active project. MPFB is not needed for these assets.
- For a human model, first ask for MPFB status and Blender scene; missing tools or assets
  must be reported rather than worked around with a fake generated model.
- Start from an anatomically coherent MPFB body; improve posture, face,
  asymmetry and surface treatment with measurable changes.
- Use Blender visual MCP `look` in front, side, and three-quarter views;
  inspect the model *before and after* one round of modifications.
- Keep the editable scene in the selected project `models/`; export a
  separately named glTF/GLB to `assets/3d/`. Never overwrite Patient V3.
- Load the exported asset in Godot and check its actual silhouette, skeleton,
  scale and performance. The agent cannot mark artistic quality accepted;
  the user judges the renders and gameplay.
- Rigger remains installed but disabled; its future experiment will be a
  short, isolated retargeted performance on a copy of the rig.

## Local diagnosis and reruns

In a terminal, the same helper supports these explicit commands:

```sh
python3 -B studio/character_lab_setup.py status
python3 -B studio/character_lab_setup.py doctor
```

These commands do not install software. `doctor` only checks whether loopback
ports 9876 and 9877 accept a TCP connection; that is **not** proof that either
MCP protocol or the AI is working. The real proof is a completed Codex tool
call, a visible Blender change, an editable saved `.blend`, and an exported
`.glb` that opens in Godot.

The on-device installer can be rerun but is **not transactional**. If one
upstream step fails, previous completed steps remain and the terminal names
the failing operation. It refuses missing or old Blender and never silently
replaces existing `studio-blender` or `studio-mpfb` registrations.
Review existing entries with `codex mcp list` before retrying a conflicting
installation. All source checkouts are pinned; mismatched pre-existing
checkouts require explicit review instead of forced updates.

**Security:** The visual MCP opens a localhost TCP server which can execute
Blender Python with Blender's user privileges. Its safe mode is a content
filter, not an OS-level sandbox. Studio disables visual MCP telemetry in
its own Codex registration. Do not expose either port to LAN, Wolf, Docker or
Tailscale and do not use sensitive/production projects for experimental runs.
Existing Codex on-request approvals and Studio project isolation remain in
force. If the embedded app-server blocks localhost MCP tools, this is a
real integration blocker to fix, not a justification to bypass isolation.

## Upstream references

- [Official MPFB extension](https://extensions.blender.org/add-ons/mpfb/)
  and [MPFB MCP install/protocol](https://github.com/makehumancommunity/mpfb-mcp/blob/master/INSTALL.md)
- [MCP for Blender install and safe-mode details](https://www.mcp-for-blender.com/docs/installation)
- [Blender 5.2 extension CLI](https://docs.blender.org/manual/en/5.2/advanced/command_line/extension_arguments.html)
- [Rigger rigging, retargeting, and Godot export](https://github.com/asu37/Rigger)

**Compatibility:** The installer still uses legacy internal paths named
`character-lab` so existing user-level payloads are not moved or downloaded
again. This is an internal directory label, not a separate user-facing
Studio feature. The .deb ships installer logic, not vendored large assets;
the initial setup needs connectivity. Online installation, detected sockets,
MCP registration, live agent operations and quality acceptance are distinct
checks.

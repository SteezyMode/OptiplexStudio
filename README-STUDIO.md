# OptiPlex Studio — local creative workspace

Studio keeps its GTK3 interface, project templates, categorized assets, documents,
reviewed context exports and project-aware Codex workflows. Normal operation runs
on this computer. Wolf, Docker, SSH, Tailscale, Flatpak and a remote server are not
required. Native creative applications and Codex are optional tools installed by
the user; a missing tool does not prevent browsing or managing projects.

Run `python3 -B studio/app.py` with Python 3, PyGObject and GTK3 installed.
An optional supported terminal is required for interactive Codex sessions:
xterm, GNOME Terminal, Konsole or XFCE Terminal.

## Workspace and existing data

The default workspace is `~/StudioProjects`. Change **Settings → Local workspace**
to an absolute directory (a leading `~` is expanded). Creating the first project
creates a missing workspace. Merely opening Studio does not create projects.
Workspace and project directories must not be symlinks.

Settings remain in `$XDG_CONFIG_HOME/optiplex-studio/config.json`, defaulting to
`~/.config/optiplex-studio/config.json`. The `projects_dir` setting selects the
workspace. Existing settings and remembered project selection are retained;
legacy connection fields no longer control normal operation.

Studio never moves, converts or deletes existing projects. To use an older local
layout such as `~/StudioProjects/Godot`, select that directory as the workspace.
Remote data stays where it is; copying it locally is a separate user action.
Recognized projects are immediate subdirectories containing `project.godot` or
valid `studio-project.json` metadata. Invalid names and symlinks are excluded.

## Projects, assets and documents

New projects support Blank, Godot, Music/Audio, Animation and 3D templates.
Each includes categorized asset folders and GAME.md, PROGRESS.md, DECISIONS.md
AGENTS.md and AI_MEMORY.md. Godot includes a minimal scene and native project file. Git is
initialized without a commit when available; if Git is missing, Studio reports a
warning and the project remains usable. Existing project files are never replaced
by template creation or missing-document initialization.

Project Files and Browse Assets open local folders through the file manager or
the GTK fallback browser. Import Assets retains conflict review, size limits,
content hashes and checks against files changing during import. Document writes
still check the reviewed hash. Context exports remain explicitly selected ZIP
snapshots with credential, symlink, traversal and size protections. Attach these
snapshots to ChatGPT manually; nothing is uploaded automatically.

## Native creative tools

Godot opens the selected Godot project with `--editor --path PROJECT_DIRECTORY`.
Blender, Blockbench, LMMS and Krita launch with the selected project as their
working directory. Studio does not guess which source asset to open or overwrite
an existing application session. Native launches may open another application
window; window focusing is left to the desktop environment.

Tools & Setup opens on first use and can be reopened from its tab or Settings.
Review detected tools, use Choose Executable, or use Auto to clear an override.
Install missing tools with per-download consent; Recheck updates status. Repair is
available for incomplete Studio-managed optional packages and supported Codex components.
Continue to Studio keeps existing tools and settings and permits incomplete setup.
Ready means an executable file is available, not that runtime compatibility was tested.
Invalid configured paths show Needs attention; a completed managed repair may resolve
the original managed override without changing the saved setting.

Discovery prefers configured paths, PATH, ~/.local/bin, then bounded searches in
persistent tool directories. Defaults include ~/.local/share/optiplex-studio/tools,
~/.tools and /projects/.tools; Settings accepts additional absolute directories.
Each root may contain TOOL-native or TOOL with version subdirectories. No version
is pinned; use Choose to select a specific version. Executable paths are single
files, never shell commands. Extracted AppImage squashfs-root/AppRun is supported
without FUSE. No Flatpak, Docker, Wolf, SSH, Tailscale or root is required.

Godot, Codex, Blender, Krita, Blockbench, LMMS and VSCodium offer
verified rootless installation into the managed
persistent tool directory. Background downloads use official publisher releases;
missing trusted checksums stop installation. No remote scripts, sudo or system
packages are used. Codex sign-in is a separate native terminal step with guidance
in the wizard. All creative tools remain optional. AppImages are verified and stored
without executing or extracting them; FUSE and desktop libraries may require manual
setup. Missing publisher integrity data, unsupported architecture or changed layouts
stop automation and offer official guidance and manual executable selection.
Cancel installation or close the wizard to cancel. Existing versions are preserved.
Embedded Codex shells receive session-only aliases for detected tools, including
`godot` and `godot4`. Login shell profiles are disabled for these embedded sessions
to retain the tool PATH. Headless Godot user data and caches stay under the selected
project’s `.studio/headless/`; project imports still use `.godot/`. Tool directories,
other projects and HOME receive no additional write access. Reconnect after changing
tool setup. Shell profiles and saved Codex settings are unchanged.

See [installation behavior, publisher trust, first-run steps and deferred work](docs/NATIVE-TOOL-INSTALLATION.md).

VSCodium is an optional editor. Open Current Project passes the validated selected
Project directory to the native editor. Future Codex change-review integration
should show project-scoped diffs and explicit review decisions in the editor while
retaining Studio conversation ownership and native Codex approval/sandbox settings;
no extension, review bridge or automated edits are implemented here.

Compatibility observations: Krita scripting availability depends on the native
build and its Python/plugin environment; launching Krita does not verify scripting.
LMMS scaling may vary with its Qt build and desktop display configuration. Neither
Krita scripting nor LMMS scaling is changed in this pass.

## Codex

The active Project is shown above the workspace. **New Conversation** starts local
Codex in that Project; **Resume Conversation** lists its conversations with readable
titles and dates. **All Projects** provides global discovery: selecting a known
conversation switches to its owning Project before resuming. Unassigned conversations
remain visible globally but cannot resume through Studio. Search and sort apply to
loaded pages; use Load More for additional history.

Resume checks current metadata and Project ownership again before opening a terminal.
An unavailable metadata service blocks resume. The unrestricted Codex picker is not
exposed by Studio. Codex runs with `--no-daemon -C PROJECT_DIRECTORY`, preserving the
native launcher workaround and existing approval, sandbox and authentication settings.
Metadata listing uses Codex app-server and never rewrites original histories.

Verified associations are stored in `.studio-conversations.json`, bound to the UUID
in `.studio-project-id`. These additive files support directory renames after discovery;
keep them with the Project. Conflicting mappings, copied duplicate identities, unknown
working directories and unrecognized projects remain unassigned. No inferred mapping
between host/container paths is made. Discovery can add these small Studio metadata
files to recognized writable Projects; existing project content is preserved.

**AI Memory** opens the Project's editable AI_MEMORY.md using conflict-checked saves.
New Codex tasks explicitly receive its current text as initial project context, followed
by the task when provided. This is user-maintained context, not automatic memory or
transcript synchronization. Memory is limited to 24 KB when launching; existing
conversations are resumed without injecting new memory into their history.

See [the project-first architecture and prioritized native setup roadmap](docs/ADR-002-PROJECT-FIRST-CONVERSATIONS.md).
The first-run Tools & Setup flow inventories persistent native installs and offers consented native tool installation. Downloads require explicit confirmation.

## Build and verification

On Debian/Ubuntu, install build-essential, python3, python3-gi,
gir1.2-gtk-3.0, desktop-file-utils and binutils. GTK display tests additionally
need a working Broadway server and dbus-run-session.

```sh
python3 -B -m unittest discover -s tests -v
make -f Makefile.studio package
python3 -B studio/validate_package.py
python3 -B tests/run_gtk.py
```

The local-first package version is 0.4.0. Packaging refuses to overwrite an
existing 0.4.0 staging directory or artifact. Approved PNG artwork is copied
unchanged. Runtime package dependencies contain no SSH, remote filesystem,
container or streaming client. Optional native applications are not installed
automatically. Legacy remote helpers and regression fixtures remain for historical
compatibility but are not exposed by the normal interface.

Tests distinguish local engine/command checks from real GUI and application
execution. A successful mocked launch does not establish that Godot, Blender or
Codex ran on the host. No Studio packaging or workflow changes OptiPlex NOW,
Wolf services or infrastructure.

### Embedded Codex conversations

AI Workspace now opens native Codex conversations inside its output panel. Select
an existing Project, choose New Conversation or Resume Conversation, and send a
message. Run and task presets create a thread and send the selected prompt.
New threads receive that Project's AI_MEMORY.md; existing threads retain their
history. Interrupt stops the current turn; Reconnect re-verifies ownership and
reloads the thread without replaying messages. Review history before retrying a
message after connection failure.

Action requests offer Deny or Approve once, with Deny as the default. The client
uses a read-only sandbox and Codex's untrusted policy. Unsupported interactive
requests are rejected. External Codex Terminal remains available in More actions
and in the conversation panel. Unassigned historical conversations require a
separate future recovery flow. No new runtime dependencies were added.

This source milestone is fixture-tested; authenticated native streaming and the
1024x768 GTK layout still require workstation validation. See ADR-002 in `docs/`
for exact environment failures and remaining acceptance checks.

## Release integrity

Official GitHub packages are built from version tags using the validated CI release workflow. The native installer and SHA-256 sidecar are provided through the repository’s latest Release page. See `docs/RELEASING.md`.

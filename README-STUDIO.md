# OptiPlex Studio 0.3.0

Independent native GTK3 project workspace, with a compiled C launcher and
PyGObject interface. The NOW reference source, build files, installed application,
and original artwork are unchanged. The approved Studio application and tray
PNGs are supplied separately; no SVG substitutions or artwork conversions are made. Nothing in this release installs or modifies server services.

## Build and package

    make -f Makefile.studio package
    ./build/optiplex-studio

Output: `dist/optiplex-studio_0.3.0_amd64.deb` on amd64. The package is independently
installable alongside NOW; building it does not install it. Build requires GCC,
make, Python 3 and dpkg-deb. Runtime dependencies are declared in the package.

Before packaging, place the approved square PNGs at exactly:

- `/home/optiplex/StudioProjects/optiplex-studio/assets/optiplex-studio.png`
- `/home/optiplex/StudioProjects/optiplex-studio/assets/optiplex-studio-tray.png`

The builder validates their PNG headers and dimensions, copies them unchanged
into the matching hicolor size directories and the standard pixmaps fallback
(for approved sizes absent from the hicolor index), and stops before staging
if either is missing or cannot be decoded. No artwork is resized or regenerated.
Both approved PNGs are included in the release source. No old SVGs are used.
Validate a built artifact with `/usr/bin/python3 studio/validate_package.py`.
Run isolated native GUI checks with `/usr/bin/python3 tests/run_gtk.py`.
The release workflow builds and validates the package before publishing its
Debian artifact and SHA-256 checksum to the v0.3.0 GitHub release.

App ID: `com.monumentrisk.OptiPlexStudio`. Settings remain in
`$XDG_CONFIG_HOME/optiplex-studio/config.json`, defaulting to
`~/.config/optiplex-studio/config.json`. Existing fields are retained when saving
settings. Last project selection is kept separately in `project-state.json`.
Existing NOW configuration is neither read nor changed.

## Project-first workspace

Projects live on the OptiPlex under `~/StudioProjects/Godot/PROJECT`. The desktop
container must already mount the same directory as `/projects/Godot/PROJECT`.
The directory name is retained for compatibility; it no longer defines the
project type. The selector and + New Project button remain above Project,
AI Workspace and Creative Tools tabs. Last selection is remembered, and the
active project/type is visible while switching sections.

Templates: Blank, Godot, Music/Audio, Animation and 3D. Each creates a Git
repository, `studio-project.json` type marker, `GAME.md` (goals and creative
direction), `PROGRESS.md`, `DECISIONS.md`, `AGENTS.md`, `docs/` and shared asset
folders. Only the Godot template creates `project.godot` and a starting scene.
Existing projects containing `project.godot` are recognized as Godot without
requiring or writing a manifest. Other directories must have a valid Studio
manifest to be listed. No existing project is moved or migrated. Discovery merges
the existing HTTPS Projects API with narrow SSH-based project discovery because
the existing API lists Godot projects only. An API/SSH discovery failure is
visible and clears the active project/actions.

Asset categories:

| Category | Project-relative destination |
| --- | --- |
| Sprites | assets/sprites |
| Textures | assets/textures |
| 3D Models | assets/3d |
| Music | assets/audio/music |
| Sound Effects | assets/audio/sfx |
| Other Assets | assets/other |

The new GUI creation workflow initializes Git without creating a commit. It does
not alter the existing `studio` scripts. Existing projects are not automatically
rewritten or migrated. Project Documents can create only missing documentation,
or view/edit one document with a server-side hash conflict check. Existing
content is preserved unless the user explicitly saves an edit.

Codex New and Resume launch the existing Codex binary with the selected project
as its working directory, workspace-write sandbox, on-request approval, and a
configuration override asking it to read the four project documents, maintain
concise progress/decisions, avoid automatic commits, and use available Godot
validation for Godot projects. Missing tools/permissions must be reported, never bypassed through
unrestricted Docker access. Before a session starts, missing project documents
are created without overwriting existing documents. No Codex configuration file is edited. Terminal sessions are monitored independently,
so a running Codex conversation does not block project file workflows.

## Codex sessions and contextual actions

New Codex Session starts in the active project. Resume Session opens a GUI
browser defaulting to that project, with All Projects, title/path/ID search,
recent/oldest/name sorting and explicit Load More pagination. Search and sort
apply to loaded pages (the dialog states this). Active, unarchived CLI, VS Code, app-server, exec and unknown-source sessions
are queried. Titles, timestamps, IDs and cwd come from Codex; Studio does not invent or rewrite conversation metadata.
Only an exact project directory or a reliably recognized child directory can
associate a returned session with a Studio project. The project-scoped server
query uses Codex's exact cwd filter; sessions started from child directories are
visible via All Projects. Sessions outside recognized Studio projects are shown
there but use Codex's All Projects picker for resumption.

Metadata uses the documented `initialize` / `thread/list` stdio app-server
protocol over the existing Tailscale SSH connection, including cursor pagination,
updated-at ordering and `useStateDbOnly: true` to avoid rollout scan/repair.
Studio never parses or edits Codex JSONL files or SQLite databases. A bounded
short-lived process is terminated after each page; no service is installed or
public endpoint opened. No thread/start, turn/start or thread/resume RPC is sent.
Resume Selected Session runs the existing CLI `codex --cd PROJECT ... resume UUID`.
The existing interactive conversation picker remains available independently and
as a browser fallback, including `resume --all` for All Projects. History is kept.

The remote Codex version must support `app-server --listen stdio://` and the
listed protocol fields. Unsupported versions produce an actionable error; use
the picker or separately update Codex through your existing administration flow.
Studio does not install or update Codex. Protocol reference:
https://developers.openai.com/codex/app-server (thread/list).

Review Changes and Explain Project start a new interactive session with a fixed,
visible-purpose prompt and project instructions. Fix Godot Errors and Validate
Project do likewise for Godot projects only. Validation runs within Codex's
existing approval/sandbox workflow; Studio does not claim a successful validation
just because a terminal opened. Missing tools/permissions must be reported.
No unrelated AI API, custom chat panel or automatic ChatGPT upload is added.

## Assets and creative tools

Import Assets uses a native multi-file picker and category selection. Transfers
use the configured Tailscale SSH connection, show progress, and verify the
resulting SHA-256. Limits are 100 files, 32 MiB/file and 256 MiB/batch. ASCII
filenames may contain letters, digits, spaces, parentheses, dots, underscores
and hyphens; executable/private filenames are rejected. Common image, audio,
model, font and source asset formats are allowlisted, including `.kra`, `.blend`
and `.bbmodel`. Filenames cannot specify directories.

Existing filenames are checked before transfer. The GUI asks before replacing
any conflicts, and the helper verifies that the confirmed server version has
not changed. Writes use temporary files and atomic replacement; new files use
an atomic no-clobber create. A failure reports how many files completed; the
batch is not transactional. No silent overwrite or automatic Git commit occurs.

Project Files and Browse Assets check and mount the selected remote directory
through GVfs before opening it. The verified local GVfs/FUSE path is passed to
the directory file manager, avoiding unsupported SFTP URI handlers. When that
is unavailable, a native GTK browser opens the remote folder directly and can
save selected files locally. `gvfs-backends` and `gvfs-fuse` are required package
dependencies. Connection, authentication and launch failures produce a dialog. It uses the configured numeric Tailscale address and
existing SSH trust/keys. File-manager authentication or trust prompts may still
appear; no typed SSH commands are required.

Launcher buttons display actual application names:

| Button | Existing service or desktop action |
| --- | --- |
| UltraBox | synth.monumentrisk.com |
| AudioMass | recorder.monumentrisk.com |
| openDAW | daw.monumentrisk.com |
| Piskel | pixel.monumentrisk.com |
| Onionskyn | SSH-forwarded existing loopback service 18771 |
| CozyClay | SSH-forwarded existing loopback service 18769/app/ |
| Blockbench | SSH-forwarded existing loopback service 18770 |
| Blender | org.blender.Blender in the running Wolf Studio Desktop |
| Krita | org.kde.krita in the running Wolf Studio Desktop |

The old Models / 3D Workshop entry is consolidated under Blockbench. The
models/previs/animate HTTPS virtual hosts currently fail TLS and have no route
in the active Caddy configuration. Studio does not disable certificate checks
or edit Caddy. Instead it creates fixed, temporary SSH loopback forwards on
127.0.0.1:28770, :28769 and :28771, respectively, to the existing static services.
Traffic to the OptiPlex is encrypted by SSH over Tailscale; HTTP exists only on
the loopback ends. SSH forwarding permission and those existing services must be
available. If a local forward cannot bind or the service is unreachable, the
GUI reports an error rather than opening an unrelated port. Forwards close with
Studio and are reused while it runs. Switching servers replaces its own forward.

Working HTTPS tools still open in a separate Chromium/Chrome/Brave profile with
Tailscale host resolver rules. HTTPS hostname verification remains enabled.
Browser documents are origin/profile-specific; old browser work is not migrated
by this release. Export existing work before switching origins. Other external
assets or optional remote tool backends may require their own connectivity.
CozyClay's optional motion/AI backends remain absent; this release does not add
them. Browser editor export/import round trips still require live verification.

Selecting a creative tool shows the active project and clear asset destinations.
Export/download from the browser, then Import Assets. Browser applications do
**not** directly save into the remote project directory. For Krita/Blender inside
the existing desktop, use the mapped `/projects/Godot/PROJECT/assets/...` path
in their own Save dialogs; native save/export round trips are not yet live-tested.

## Share Project Context

Select project → Share Project Context → review files and optional images → Export
ZIP locally → attach the ZIP to ChatGPT manually. Copy ChatGPT Brief supplies the
project name, branch, commit, dirty state and snapshot review instructions. Open
ChatGPT uses the user's existing browser. There is no automatic upload, account
link, chat panel, conversation synchronization or AI API dependency.

The allowlist includes Godot configuration, GDScript, text scenes/resources,
shaders, project documentation, project data files and optional PNG/JPEG/WebP
previews. Native asset binaries and large media are inventoried rather than
attached. Limits: 512 KiB/text file, 2 MiB/image, 24 MiB selected content,
1,500 eligible files, 10,000 visited entries and 12 directory levels. Images
retain their original metadata; review before sharing.

The review dialog supports per-file selection and native text/image previews.
It does not upload anything. ZIP contains `OVERVIEW.md`, `CHATGPT-BRIEF.md`,
`CHANGES.diff` and the selected files under the project name. Sources are current
working-tree contents, including staged, unstaged and untracked work. Relevant
reviewed text-file deletions are represented in the diff, not resurrected as
files. Diffs compare only reviewed selected text paths against HEAD. Sensitive
or oversized old versions/diffs are omitted with an explanation. New repositories
without commits still include their current files and metadata.

.git internals, .godot cache, hidden files, compiled/export directories,
credentials/private filenames, symlinks, hard links and nonallowlisted contents
are excluded. Root-level unrelated text files are not exportable. Conservative
secret scanning is performed on text, Git metadata and diff contents. It is
not a guarantee against every secret: review the selected files and final ZIP
before sharing. Files that change after review require another review. Project
access is anchored to directory descriptors with O_NOFOLLOW. Git metadata is
read only for ordinary project-local .git directories; linked/external gitdirs
are intentionally unsupported. Size-limited sources can still omit larger game
assets; the overview lists inventory-only entries and exclusions.

## Godot, Krita, Blender and Moonlight

The bundled `desktop_helper.py` supports only Godot, Krita and Blender. It uses
existing server-user permissions and exactly one already-running
`WolfStudioDesktop_*` container. It never starts/stops/restarts containers,
creates profiles, installs software, grants Docker permissions or accepts an
arbitrary executable. The existing server-side `~/.local/bin/studio edit PROJECT` is not modified.
The client uses its fixed Godot Flatpak/editor arguments after checking for an
existing editor for that exact project. It discovers the running desktop
Wayland socket rather than hardcoding wayland-2 (the inspected desktop uses
wayland-1). Godot, Blender and Krita share this environment resolution and up
to 30 seconds of startup process confirmation; a connected desktop alone is
not reported as successful application startup. A fixed Python/X11 focus request matches the editor by its exact
project path and in-container PID, then raises its window inside the connected stream.
It needs no wmctrl/xdotool installation inside Wolf. If activation is unavailable,
Studio reports that the editor is already open instead of launching a replacement.
Per-project locks and pending-launch markers prevent repeated helper
launches; ambiguous launches require waiting two minutes before a retry. An
external launcher not using this helper can still bypass its duplicate lock.
Krita/Blender use fixed Flatpak IDs and process confirmation. They connect and
wait for the desktop first, can launch with no project selected, and use the
selected project directory when available; they do not require project.godot.
Their existing Flatpaks must be installed in the Wolf desktop. Studio does not
install them or modify Wolf.

Moonlight detection follows NOW's AppImage → native → Flatpak order and launches
`stream CONFIGURED_TAILSCALE_IP CONFIGURED_APP_TITLE` with no pairing, decoder,
bitrate, resolution or profile overrides. A matching existing stream is reused
and brought forward using wmctrl when supported. On Wayland/no window activation,
Studio reports the existing stream rather than launching a duplicate. Missing
clients, failed processes and later nonzero stream exits are visible in the GUI.

The verified default application is **OptiPlex Studio Desktop**. Open Godot
connects directly to that application on the configured Tailscale IP, waits for
exactly one Wolf Studio Desktop container, a ready X11 window manager and the
selected Godot project mount, then opens/focuses the editor. The readiness wait
has a 90-second deadline with checks about every two seconds (individual SSH
requests have a 25-second timeout), shows
progress/reasons, and never launches Godot after a detected stream failure or
readiness timeout. Blank settings and the obsolete `Studio Desktop`
placeholder use this verified title; explicit custom titles remain supported for
other servers. Steam is not substituted for the desktop.

**Open Studio Desktop** is a separate main-window and tray action. It streams
without requiring project selection, querying the Projects API, running the
project helper, or launching Godot. If no desktop session/container is running,
Open Godot now connects and waits automatically. The separate Moonlight button
still opens the existing client's general UI.

AppImage launches, including the general Moonlight UI, receive the process-local
`APPIMAGE_EXTRACT_AND_RUN=1` environment variable, matching the user-verified
Moonlight 6.2.0 command. Detection paths, pairing and playback preferences are
unchanged. Native and Flatpak installations continue to use their existing
launch commands. No global environment, Moonlight preferences or Wolf settings
are written by this change.

## Connection and server prerequisites

Set the numeric OptiPlex Tailscale IPv4 address in Settings (100.64.0.0/10), SSH
user and optionally a Moonlight AppImage path or custom Wolf desktop title.
Leaving the title blank uses OptiPlex Studio Desktop.
Existing Tailscale connectivity, SSH keys and trusted known_hosts entries are
required. Unknown SSH host keys are never accepted automatically. Conventional
/home/USER or /root paths are used for CLI and SFTP access; nonstandard home
layouts are not supported by this client version.

The Projects API connects directly to the configured IP on 443, retaining
studio.monumentrisk.com for Host, TLS SNI and certificate validation. No public
DNS, proxy, insecure certificate override or redirect fallback is used. API
failures clear selection and disable project-dependent main/tray actions.

`project_helper.py` and `desktop_helper.py` are separate, narrow components
bundled in the client package. At runtime the fixed source is passed to the
server's `/usr/bin/python3 -c` over SSH; JSON stdin selects only supported
operations. No helper is installed on the server and no service deployment is
needed. Remote prerequisites: Python 3; Git for history/diffs; existing project
root; SFTP subsystem for graphical browsing; authorized SSH forwarding for the
three static tools; existing Studio CLI and running desktop with the expected
project mount and Flatpaks for desktop actions. The focus helper uses existing
Python 3 and libX11 inside the desktop; if unavailable it falls back to reusing
the editor without automatic focus. Permission failures are reported;
Studio does not alter policy or add Docker group/sudo privileges.

No API filesystem exposure, execution endpoint, unrestricted Docker API or
server configuration changes are introduced. This work does not modify NOW,
existing games, Wolf, Caddy, Tailscale or the installed Studio application.

## Validation and remaining live checks

The current 106 automated tests cover file transfer framing/progress, conflict confirmation,
atomic writes, traversal/symlink/hard-link rejection, documentation preservation,
current/staged/untracked/deleted snapshots, secret/diff exclusions, size limits,
ZIP selection/integrity, GUI actions, project persistence, Codex command options,
Moonlight arguments/failures, desktop reuse and fixed creative SSH routing.
Tests use temporary local projects and mocked remote desktop/SSH operations.

The native GTK workflow driver uses a private Broadway display and disposable
projects to exercise remembered selection, real snapshot review/save dialogs,
ZIP creation, documentation editing, project isolation and window restoration.
Broadway emits the previously observed tray scale-factor warnings; it does not
validate a real SNI/XEmbed panel. Rendered UI/review screenshots are saved in `build/qa/project-workspace.png`
and `build/qa/snapshot-review.png`. The launcher compiled with GCC and the
unit/syntax checks passed. The private GTK workflow and lifecycle smoke tests
passed; the smoke test uses its own fresh Broadway server.

Read-only checks confirmed the working HTTPS apps over Tailscale and the existing
Blockbench, CozyClay and Onionskyn pages through real temporary Tailscale SSH
forwards. Those test forwards were closed afterward. A read-only live Tailscale SFTP mount and native GTK folder display passed
against this Studio source repository. Real remote imports,
actual browser rendering/export round trips, real Codex conversations,
Krita/Blender launches, duplicate-editor behavior in the actual Wolf session,
Moonlight streaming/focus and real tray panels require live testing after
operator installation. Direct Wolf desktop streaming has been verified separately
by the user; this build does not reconfigure it.
No package is installed, published or committed by the build.

Version 0.3.0 adds project template/discovery checks, multiple projects/sessions,
real subprocess stdio metadata framing, source injection, UUID/prompt quoting,
GUI session search/filter/resume routing and native template selection. It also
includes the cold-desktop Godot startup/source-order fixes and explicit
GLib/GDK/AppIndicator/XEmbed/desktop-file identity. Real tray panels, remote
Codex metadata compatibility, terminal resumption, native save/export and cold
Wolf/Moonlight Godot startup still need live verification after installation.
The supplied approved PNGs are included unchanged. No server deployment
is required: session/project/desktop helpers are bundled and sent over SSH.

## Corrections within v0.3.0

The existing release and tag are retained. Corrections are committed directly
to main; after package and packaged-GUI validation the workflow uses
`gh release upload v0.3.0 ... --clobber` to replace the Debian installer and
checksum. Release notes identify the asset source commit; the original tag is
not moved. No other branch/repository/release version is created.

The MacBook installation was not accessible for comparison or GUI testing.
The previously published package was compared with repository sources, and
native GUI checks now import modules extracted from the rebuilt Debian package.
These verify real widget visibility/clicks, folder browsing and local copying,
plus project-scoped AI action and session selection routing with fixture backends.
No real Codex session was started or modified. Read-only desktop probes confirmed
Godot/Blender/Krita installations, versions, project mounts and display readiness;
their live interactive windows and Moonlight focus still need MacBook testing.

Quit Studio from its tray before reinstalling this corrected same-version
package, then relaunch it; single-instance activation otherwise raises the old
running process. Use your package manager's reinstall option if it reports
0.3.0 already installed. Existing settings/projects/conversations are retained.

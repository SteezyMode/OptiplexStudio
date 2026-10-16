# OptiPlex Studio 0.3.0

Project-first native GTK3 creative workspace with Blank, Godot, Music/Audio,
Animation and 3D templates. Existing Godot directories and Codex history remain
in place. Project files, categorized imports, persistent documents and reviewed
ChatGPT snapshot ZIPs share the selected project directory.

## Changes

- Active project selector and New Project button above Project, AI Workspace
  and Creative Tools tabs; remembered selection and prerequisite-aware controls.
- Codex session browser with project association, All Projects, loaded-page
  search/sort, pagination, UUID resumption and the existing conversation picker.
- Project-scoped Review Changes and Explain Project; Godot-specific Fix Errors
  and Validate actions retain existing approval and sandbox behavior.
- Godot connects Moonlight to `OptiPlex Studio Desktop`, waits for the existing
  Wolf desktop to become ready, then launches or focuses the selected project.
  Existing editor detection, locks and pending markers prevent duplicate launches.
- Blender and Krita connect the desktop first and can launch without a selected
  project. Browser tools show actual software names and explicit import/export paths.
- Corrected helper source injection and GTK/AppIndicator/desktop-file identity.
- Approved PNGs are decoded before packaging and copied without conversion.
  Pixmaps fallback supports nonstandard approved icon sizes.

## Validation performed for this release

- C launcher compiled using GCC with warnings treated as errors.
- All 106 automated tests passed, covering networking/TLS, launcher construction,
  cold-session sequencing and failure handling, transfers/conflicts/path safety,
  snapshots/exclusions, templates, session association and UUID/prompt quoting.
- Native GTK tests passed on isolated Broadway displays with temporary project
  fixtures: multiple project types, all-project session search/selection/UUID
  routing, template selection, snapshot review/export, document editing,
  remembered selection, action sensitivity, no-tray close and window restoration.
- Application PNG decoded as 901x901 RGBA, SHA256:
  `b7edaa92d4f376cc199875d89f773ddad20cda2e86841d58604b11d87f92bb48`.

These are fixture-based desktop/session tests, not live Godot, Blender, Krita,
Codex or Moonlight launch tests. Real panel behavior, remote Codex metadata
compatibility, real conversation resumption, editor focus/duplicate behavior,
streaming and browser/native import/export round trips require live verification.
No running Wolf services, installed application, server configuration or game
projects were changed during this release pass.

## Requirements and limits

Use the existing Tailscale IP, SSH keys/trusted host keys, Studio CLI and Wolf
profile named `OptiPlex Studio Desktop`. The remote Codex CLI must support the
stdio app-server metadata interface; its existing picker remains a fallback.
Krita/Blender require their existing desktop Flatpaks; graphical SFTP needs
GVfs support. No server service deployment is required.

Session search/sorting applies to loaded pages. Sessions outside recognized
Studio projects use Codex's All Projects picker. Browser editors do not directly
save into remote projects. ChatGPT snapshots require manual attachment.

## Debian package

Artifact: `optiplex-studio_0.3.0_amd64.deb` (amd64), accompanied by a SHA-256 file.
The package validator checks metadata, dependencies, ownership and permissions,
exact file contents, desktop-file validity, ELF architecture, bundled sources
and unchanged approved PNGs. The package contains no server service units or
maintainer scripts. Building/publishing does not install the application.

Approved tray PNG: 549x549 RGBA, SHA256:
`7f3c4f5dd7f5a75a145450fe4dd504a2dbaad399854049c5085b9246bc66645a`.

Repository: https://github.com/SteezyMode/OptiplexStudio
Release: https://github.com/SteezyMode/OptiplexStudio/releases/tag/v0.3.0

## Same-version corrections

- Project Files/Browse Assets now verify and mount SFTP, use a mounted local
  path with file managers, or fall back to a native GTK remote browser with
  local-copy support. GVfs backends and FUSE are required dependencies.
- Godot/Blender/Krita discover the running desktop's Wayland socket rather than
  passing the obsolete wayland-2 value. The existing server CLI is unchanged;
  fixed client-side Flatpak launch arguments use the discovered environment.
  Launch confirmation waits up to 30 seconds, with no automatic duplicate launch.
- Application launch failures are shown in dialogs, not just the status footer.
- Native tests now exercise modules extracted from the built Debian package,
  click both file buttons, display their folders, download a fixture file,
  and verify mapped AI controls and selected-project action/session routing.
- A live read-only SFTP mount and GTK folder display passed over Tailscale for
  this source directory. Read-only desktop probes found all three applications,
  successful version commands and a ready display using wayland-1.

The MacBook installation was not accessed or changed. Its installed-source
comparison and final interactive testing remain for the user. Quit the existing
Studio process, reinstall the corrected 0.3.0 package, and reopen it to avoid
single-instance activation of an older process. No projects, Codex history,
configuration, NOW, Wolf or other server services were changed.

Only the existing v0.3.0 installer/checksum assets and release notes are updated;
the original release tag is retained. The release workflow requires successful
checks before `gh release upload v0.3.0 ... --clobber`.

## Final Studio Desktop integration (October 2026)

- Fix Godot/Krita/Blender Docker process detection by requesting a PID column and parsing it.
- Add a ChatGPT-in-Wolf launcher and project-specific conversation picker access.
- Add `docker/studio-desktop-v3.Dockerfile`, the graphical Wolf AI Workspace, and a project-restricted SSH Codex gate. The v3 image and forced-command SSH key must be configured on the host separately; the client `.deb` does not install Wolf or manage its running configuration.
- Confirmed on the reference OptiPlex: v3 desktop launched and project-scoped Codex session retrieval succeeded. The host's Codex sessions remain persistent and separate from ChatGPT's web history.

Release build: final integrated Studio client and Wolf AI Workspace [release 0.3.0]

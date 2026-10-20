# OptiPlex Studio — current status

Updated: 2026-10-20. This status describes the v0.4.11 local-first source on the
merged `main` branch. This source has not yet been published as a new release.

## Implemented in source

- GTK3 project browser and local project creation with project templates and Git
  initialization.
- Categorized local asset importing with conflict review and integrity checks.
- Project documents with conflict-checked saves, project inventory and reviewed
  ZIP snapshots.
- Local Git metadata and project-aware Codex conversation discovery, association,
  new conversations and resume flows.
- Native launch adapters for Godot, Blender, Blockbench, LMMS and optional Krita
  and VSCodium.
- Optional rootless setup for native tools and Codex.
- Project-scoped Codex sandbox and approval boundaries.

Normal Studio operation uses the configured local workspace. It does not require
SSH, Tailscale, Moonlight, Wolf, Docker, remote project APIs or hosted browser
services. Wolf can provide graphical access to the workstation independently.

## Verification state

For this local-first source, 163 unit tests pass. `make -f Makefile.studio package` builds the
0.4.11 amd64 Debian package, and `studio/validate_package.py` verifies its exact
payload, desktop entry and dependencies. All four native GTK scenarios pass against
source and the unpacked package payload, including project workflows, folder browsing,
conversation layout and application launch. The installed package was not changed.
No public release or version tag is created by this cleanup.

## Historical material

The 0.3.0 release notes, remote-development guide, Wolf/container experiments and
older architecture records describe historical development. They are retained for
context only and do not define current product behavior. See [the documentation
map](README.md) for current guides.

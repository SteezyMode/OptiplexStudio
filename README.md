# OptiPlex Studio

> **Current status (2026-10-19):** The latest **published** Studio package is v0.3.0. Later repository changes and Wolf host-side utilities are not automatically included in that .deb or installed GUI. See [Current status: frozen v1 milestones, verified Wolf improvements, and next work](docs/CURRENT-STATUS.md). Studio v1.0 remains unreleased.


**Remote development:** [Persistent SSH/Codex sessions with tmux](docs/remote-development-tmux.md) — survive client disconnects (not host reboots).

Native GTK3 creative workspace for projects, assets, documentation, and Codex-assisted game development. It is independently installable; Wolf can optionally provide a streamed graphical session.

- [Download OptiPlex Studio 0.3.0](https://github.com/SteezyMode/OptiplexStudio/releases/tag/v0.3.0)
- [New contributor guide and code map](CONTRIBUTING.md)
- [Build, configuration and workflow documentation](README-STUDIO.md)
- [0.3.0 release notes and testing limits](RELEASE-0.3.0.md)

Build on an amd64 Debian/Ubuntu system with GTK3/PyGObject development requirements installed:

```sh
make -f Makefile.studio package
/usr/bin/python3 tests/run_gtk.py
/usr/bin/python3 studio/validate_package.py
```

The application is independently installable alongside OptiPlex NOW. Building or publishing it does not install it or change Wolf/server services. Browser tools use explicit export/import workflows; ChatGPT snapshots require manual attachment.

Release packages include the approved PNG icons unchanged and a SHA-256 sidecar. The release checks cover 96 automated regressions, isolated native GTK workflows and Debian payload validation. Live Wolf/Godot, Codex resumption and real tray-panel checks are documented separately in the release notes.

## Long-term product architecture

- [ADR-002 — Upstream-first integrated creative toolchain](docs/ADR-002-UPSTREAM-FIRST-INTEGRATED-TOOLCHAIN.md): Godot, Blender, Blockbench and LMMS, adapter-first integration, compatibility matrix and strict fork criteria. **Proposed strategy, not an implemented feature.**
- [ADR-001 — Shared local-first Studio runtime](docs/ADR-001-LOCAL-FIRST-SHARED-STUDIO-RUNTIME.md): native/remote frontends share the same project and agent state.

## Active development handoff

- [Art Director experimental handoff (not a seventh frozen v1 milestone)](docs/MILESTONE-8-ART-DIRECTOR-HANDOFF-2026-10-18.md)

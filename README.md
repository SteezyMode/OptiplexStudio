# OptiPlex Studio

[![Build, package and GUI verification](https://github.com/SteezyMode/OptiplexStudio/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SteezyMode/OptiplexStudio/actions/workflows/ci.yml)
**Automated health checks:** Pull requests, changes to main and a weekly Monday 03:47 UTC run compile, package, and exercise the installed native GTK app on disposable Ubuntu runners. These checks never publish a release or modify the reference server; live Wolf/streaming functionality still needs separate acceptance.


> **Current status (2026-10-19):** The latest **published** Studio package is v0.3.0. Later repository changes and Wolf host-side utilities are not automatically included in that .deb or installed GUI. See [Current status: frozen v1 milestones, verified Wolf improvements, and next work](docs/CURRENT-STATUS.md). Studio v1.0 remains unreleased.


**Remote development:** [Persistent SSH/Codex sessions with tmux](docs/remote-development-tmux.md) — survive client disconnects (not host reboots).

Native GTK3 creative workspace for projects, assets, documentation, and Codex-assisted game development. It is independently installable; Wolf can optionally provide a streamed graphical session.

- [Download OptiPlex Studio 0.3.0](https://github.com/SteezyMode/OptiplexStudio/releases/tag/v0.3.0)
- [New contributor guide and code map](CONTRIBUTING.md)
- [Documentation index: current status, architecture and experimental notes](docs/README.md)
- [Build, configuration and workflow documentation](README-STUDIO.md)
- [0.3.0 release notes and testing limits](RELEASE-0.3.0.md)

Build on an amd64 Debian/Ubuntu system with GTK3/PyGObject development requirements installed:

```sh
make -f Makefile.studio package
/usr/bin/python3 tests/run_gtk.py
/usr/bin/python3 studio/validate_package.py
```

The application is independently installable alongside OptiPlex NOW. Building or publishing it does not install it or change Wolf/server services. Browser tools use explicit export/import workflows; ChatGPT snapshots require manual attachment.

Release packages include the approved PNG icons unchanged and a SHA-256 sidecar. Release checks run automated regressions, isolated native GTK workflows and Debian payload validation; the exact test count changes as coverage grows. Live Wolf/Godot, Codex resumption and real tray-panel checks are documented separately in the release notes.

## Long-term product architecture

- [ADR-002 — Upstream-first integrated creative toolchain](docs/ADR-002-UPSTREAM-FIRST-INTEGRATED-TOOLCHAIN.md): Godot, Blender, Blockbench and LMMS, adapter-first integration, compatibility matrix and strict fork criteria. **Proposed strategy, not an implemented feature.**
- [ADR-001 — Shared local-first Studio runtime](docs/ADR-001-LOCAL-FIRST-SHARED-STUDIO-RUNTIME.md): native/remote frontends share the same project and agent state.

## Development references

The [documentation index](docs/README.md) distinguishes the frozen six-milestone acceptance contract from Art Director and other experimental research. See [current status](docs/CURRENT-STATUS.md) for actual verified progress rather than treating experiment titles as release milestones.

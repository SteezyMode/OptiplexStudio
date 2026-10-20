# Contributing to OptiPlex Studio

## What this application is

Studio is a native GTK3 creative workspace for projects, assets, documentation, and Codex-assisted game development. Wolf is an optional remote graphical environment, not the Studio application. NOW is a separate launcher. [Current status](docs/CURRENT-STATUS.md) describes the difference between published packages, current source, and independently tested host-side experiments.

The published desktop package is v0.3.0. A successful host-side Godot or Blender experiment is not necessarily part of that release.

## Source map

| Path | Purpose |
| --- | --- |
| `studio/app.py`, `studio/project_ui.py`, `studio/session_ui.py` | GTK application and screens |
| `studio/core.py` | Tailscale, SSH, HTTPS service URLs and browser integration |
| `studio/project_client.py`, `studio/project_helper.py` | Project operations and scoped remote helpers |
| `studio/desktop_helper.py`, `studio/file_browser.py` | Desktop actions and asset browser |
| `studio/session_helper.py`, `studio/codex_gate.py` | Codex session behavior |
| `studio/launcher.c`, `studio/package.py`, `studio/validate_package.py` | Binary launcher, Debian package and verification |
| `tests/` | Tests including isolated Broadway GTK workflows |
| `tools/`, `docker/`, `studio/demo_controls/` | Optional host/Wolf tools, not automatically shipped in the GTK package |
| `docs/`, `catalogs/`, `templates/` | ADRs, experimental references and templates |

## First build

Use an amd64 Debian/Ubuntu-compatible development system with dependencies listed in [.github/workflows/ci.yml](.github/workflows/ci.yml). The repository already contains its approved application artwork.

```sh
make -f Makefile.studio check
make -f Makefile.studio package
/usr/bin/python3 -B tests/run_gtk.py --package dist/optiplex-studio_0.3.0_amd64.deb
/usr/bin/python3 -B studio/validate_package.py
```

Package versions are defined in **studio/version.py**; do not patch multiple scripts or CI filenames to bump a release. A green build validates packaging and fixtures, not live Wolf, Blender, Godot, Codex, networking or persistence. Building does not install or update the running desktop.

## Change rules

1. Begin with [the six frozen Studio v1 gates](https://github.com/SteezyMode/OptiplexStudio/issues/3); changes outside them are post-v1 unless explicitly approved.
2. Identify one reproducible problem and its acceptance test; separate shipped, observed and proposed behavior.
3. Work in a feature branch. Keep projects, configuration, session history and existing services intact.
4. Add tests and describe the required live manual checks; avoid equating a headless validation with working GUI behavior.
5. In PRs explain purpose, risk, tests, compatibility and rollback. Do not make unrelated host changes to fix the app.

[ADR-001 local-first](docs/ADR-001-LOCAL-FIRST-SHARED-STUDIO-RUNTIME.md) and [ADR-002 upstream-first](docs/ADR-002-UPSTREAM-FIRST-INTEGRATED-TOOLCHAIN.md) describe accepted design directions, not fully shipped features. See [release process](docs/RELEASING.md) for version-tagged builds.

No application-code LICENSE is present at the root. An explicit licensing and contribution policy is needed before outside contributors rely on reuse or redistribution rights. A public product name and tested migration path must also be chosen before commercial launch.

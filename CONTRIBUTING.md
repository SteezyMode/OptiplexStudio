# Contributing to OptiPlex Studio

Studio is a local-first GTK3 desktop workspace for creative projects, assets, native tools and project-aware Codex. It does **not** require a separate host, SSH, Wolf, Docker or NOW. Wolf/NOW may independently provide graphical remote access to the workstation; neither is part of Studio's local data backend.

Read [AGENTS.md](AGENTS.md), [current status](docs/CURRENT-STATUS.md) and [the application guide](README-STUDIO.md) before a change. The current **downloadable .deb** is linked from the [repository README](README.md); don't infer the published version from historical guides.

## Source map

| Path | Role |
| --- | --- |
| `studio/app.py`, `project_ui.py`, `tools_ui.py`, `session_ui.py`, `embedded_ui.py` | GTK app, project/navigation and native Codex UI |
| `studio/project_helper.py`, `project_client.py`, `conversation_store.py` | Local project filesystem and conversation ownership |
| `studio/native_tools.py`, `portable_install.py`, `codex_install.py` | Native launcher, discovery and consented rootless installation |
| `studio/codex_rpc.py`, `embedded_codex.py`, `session_helper.py` | Codex protocol, project-scope and session behavior |
| `studio/launcher.c`, `package.py`, `validate_package.py`, `version.py` | Desktop launcher and single-version Debian packaging |
| `tests/` and `.github/workflows/` | Unit/GTK fixtures, package smoke, PR CI and release publication |
| `docs/`, `catalogs/`, `tools/`, `docker/` | Current reference docs plus optional or historical experiments |

## Development and verification

Use a Debian/Ubuntu-family amd64 environment with prerequisites from [Studio CI](.github/workflows/ci.yml). Do not install over an active workstation merely to run the test suite.

```sh
make -f Makefile.studio check
make -f Makefile.studio package
/usr/bin/python3 -B tests/run_gtk.py --package "dist/optiplex-studio_$(/usr/bin/python3 -c 'import runpy; print(runpy.run_path("studio/version.py")["PACKAGE_VERSION"])')_amd64.deb"
/usr/bin/python3 -B studio/validate_package.py
```

CI additionally installs the built .deb on an isolated GitHub runner and checks the actual GTK window. Only run `tests/smoke_installed_package.sh` on a disposable runner: it uses `sudo apt-get install`.

A green CI result validates source, fixtures and package wiring. It **does not** prove native Codex sign-in, a working graphics/audio session, real Blender-to-Godot or LMMS-to-Godot output, or compatibility with every workstation.

## Change and release policy

1. Work on one user-visible issue at a time. Include the failure/need, observable success criteria, and a minimal scope. The current priorities are unified-project compatibility/navigation ([#30](https://github.com/SteezyMode/OptiplexStudio/issues/30)) and guided Codex authentication/readiness ([#31](https://github.com/SteezyMode/OptiplexStudio/issues/31)).
2. Create a feature branch and PR. Add focused regression tests; preserve existing projects, user files, Codex history, approval/sandbox boundaries and unrelated services.
3. Record test evidence and unperformed physical checks in the PR. Merge only when relevant checks pass. Keep [current status](docs/CURRENT-STATUS.md) factual.
4. Normal `main` updates validate but do not release. Only a deliberate `studio/version.py` bump (or matching version tag) publishes a new GitHub Release. See [releasing](docs/RELEASING.md). Verify the actual downloadable artifact afterward. Do not overwrite published assets.

The root currently has **no application-code LICENSE**, so do not assume a permissive redistribution or contributor policy. That must be resolved before inviting external contributions or commercialization.

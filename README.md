# OptiPlex Studio

> **Current release:** OptiPlex Studio 0.4.9 is the proposed merged functional local-first beta. The GitHub Release is not published until CI and installed-package checks pass.

**Download:** [Latest tested OptiPlex Studio release](https://github.com/SteezyMode/OptiplexStudio/releases/latest) (choose the `.deb` asset).


Native GTK3 creative workspace for local projects, assets, documents and
project-aware Codex sessions. Projects default to configurable `~/StudioProjects`.
Godot, Blender, Blockbench, LMMS and Krita use native executable adapters.
Normal operation needs no Wolf, Docker, SSH, Tailscale, Flatpak or remote server.

See [setup, workflows, packaging and testing](README-STUDIO.md).

```sh
python3 -B studio/app.py
python3 -B -m unittest discover -s tests -v
make -f Makefile.studio package
python3 -B studio/validate_package.py
```

Existing project data and settings stay in place. Choose an older workspace in
Settings to use it; Studio performs no automatic migration. OptiPlex NOW and server
infrastructure are independent of this application.

[Previous 0.3.0 release notes](RELEASE-0.3.0.md) describe the historical remote release.

## Release and contribution references

- [Publishing releases](docs/RELEASING.md)
- [Current status and limitations](docs/CURRENT-STATUS.md)
- [Contributor guide](CONTRIBUTING.md)

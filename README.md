# OptiPlex Studio

> **Release candidate:** OptiPlex Studio 0.4.10 is the integrated local-first beta. The v0.4.9 GitHub Actions release failed because GTK tests lacked a display; the workflow has been corrected. Version 0.4.10 is not a published download until its release workflow succeeds.

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

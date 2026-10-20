# OptiPlex Studio

OptiPlex Studio is a local-first Linux creative workspace for Godot, Blender,
Blockbench, LMMS, project management and project-aware Codex development. Krita
and VSCodium can be configured as optional native tools. Wolf may be used as an optional graphical access method; it is not a Studio backend.

The GTK3 application manages local projects, categorized asset imports, project
documents, reviewed snapshots and Git history. Godot and other configured native tools launch locally. Codex conversations are associated with projects and retain Codex's native authentication, approval and sandbox settings. Studio's normal operation does not require remote access or hosted browser services.

See [setup, workflows, packaging and testing](README-STUDIO.md).

```sh
python3 -B studio/app.py
python3 -B -m unittest discover -s tests -v
make -f Makefile.studio package
python3 -B studio/validate_package.py
```

Existing project data and settings stay in place. Choose an older workspace in
Settings to use it; Studio performs no automatic migration.

The 0.3.0 release notes and documents labeled historical describe earlier remote
experiments. Those experiments are not current Studio integrations.

## Release and contribution references

- [Publishing releases](docs/RELEASING.md)
- [Current status and limitations](docs/CURRENT-STATUS.md)
- [Contributor guide](CONTRIBUTING.md)

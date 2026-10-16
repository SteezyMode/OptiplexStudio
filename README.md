# OptiPlex Studio

Native GTK3 creative workspace for OptiPlex projects, assets, documentation, Codex sessions and Wolf desktop streaming over Tailscale.

- [Download OptiPlex Studio 0.3.0](https://github.com/SteezyMode/OptiplexStudio/releases/tag/v0.3.0)
- [Build, configuration and workflow documentation](README-STUDIO.md)
- [0.3.0 release notes and testing limits](RELEASE-0.3.0.md)

Build on an amd64 Debian/Ubuntu system with GTK3/PyGObject development requirements installed:

```sh
make -f Makefile.studio package
/usr/bin/python3 tests/run_gtk.py
/usr/bin/python3 studio/validate_package.py
```

The application is independently installable alongside OptiPlex NOW. Building or publishing it does not install it or change Wolf/server services. Browser tools use explicit export/import workflows; ChatGPT snapshots require manual attachment.

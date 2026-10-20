# Publishing a Studio release

After the release-workflow cleanup PR is merged, routine commits to `main` run validation only. They never republish v0.3.0 or install anything on the reference host.

## Release checklist

1. Finish the frozen v1 acceptance gates before calling a release v1.0. Experimental Wolf-host improvements are **not automatically present** in the packaged GTK app.
2. Prepare a release PR that updates **`studio/version.py` (PACKAGE_VERSION)** and release/status documentation. The package builder and payload validator read this single version; normal CI discovers the built artifact rather than hardcoding its filename. Review the complete release diff.
3. Verify unit tests, isolated GTK tests, package payload validation and a manual clean native GUI smoke test on the intended distro.
4. Review the exact source commit, then push a **new** annotated `vX.Y.Z` tag for it. Do not force-update old release tags.
5. The tag-only workflow builds against that commit, requires the .deb's metadata version to equal the tag, runs the GUI/package checks, emits a SHA-256 checksum and publishes a new release. It refuses to overwrite an existing release.
6. Test the downloaded artifact on a representative machine; explicitly report the tests that still require live Godot, Blender, Codex or Wolf services.

## Safety boundaries

Neither release workflow nor CI should change Wolf, Tailscale, Jellyfin, installed desktop packages, or existing user project data. Packaging and isolated fixture tests are not equivalent to running the real reference environment.

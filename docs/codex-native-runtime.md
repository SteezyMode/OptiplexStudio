# Native Codex runtime installation and repair

Studio installs the official canonical `codex-package-<target>.tar.gz`, rather
than the single-binary `codex-<target>.tar.gz`. Supported hosts are Linux musl and
macOS, on x86_64 and ARM64. Windows and older releases without canonical packages
remain guidance-only; there is no unchecked or single-binary fallback.

Publisher sources inspected for `rust-v0.163.0`:

- https://github.com/openai/codex/releases/tag/rust-v0.163.0
- https://api.github.com/repos/openai/codex/releases/tags/rust-v0.163.0
- https://github.com/openai/codex/blob/rust-v0.163.0/scripts/codex_package/layout.py
- https://github.com/openai/codex/blob/rust-v0.163.0/scripts/codex_package/archive.py
- https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/install-context/src/lib.rs

The package layout is `bin/codex`, `bin/codex-code-mode-host`, `codex-path/rg`,
`codex-resources/` (including `bwrap` on Linux), and `codex-package.json`.
Studio checks the exact asset URL and SHA-256 digest supplied by GitHub's
HTTPS API for `openai/codex`, rechecks metadata at installation time, checks the
archive digest, and validates package version, architecture, layout, and all
required regular files. It does not perform Sigstore signature verification.
The managed receipt records hashes for passive checks; it is not a signature.

Fresh installs publish the complete package atomically under
`~/.local/share/optiplex-studio/tools/codex/<release>/`.
Repair fetches the exact installed tag, never latest. Canonical repairs add only
missing files after checking every existing file for conflicts. A conflicting,
non-executable, symlinked, or changed existing component is preserved and the
repair fails with guidance. No existing binary is overwritten.

For legacy `<release>/codex` installs, repair retains that executable and its
installation metadata and adds the complete canonical package at
`<release>/runtime/`. Studio resolves the old managed path to the repaired
`runtime/bin/codex` only while the original binary hash and complete receipt
still match. This also covers an explicitly configured legacy path without
changing settings. Direct invocation of the retained legacy executable outside
Studio still uses its original layout; use the repaired path shown by Setup.
If standalone and package binaries differ, the retained executable must match
the separately SHA-256-verified standalone artifact from the same release.
External PATH, npm, Homebrew, and custom installations are never repaired.

Setup distinguishes executable detection, verified components, and successful
local runtime startup checks. Detection and installation never execute code.
The user-requested Check Codex runtime action checks Codex's version and starts
the host with `--help`, ripgrep with `--version`, and Linux bubblewrap with
`--version`, using temporary HOME/CODEX_HOME and no inherited credentials.
These checks do not prove authentication, app-server compatibility, model tool
execution, or working sandbox policy. No status claims those have passed.

## Live validation still required

On the affected MacBook, open Tools & Setup, select Repair, review the pinned
version and publisher source, then run Check Codex runtime. Confirm the path is
`runtime/bin/codex`, sign-in remains available, existing settings are intact,
and a new embedded AI turn can execute a harmless tool in a disposable project.
Exercise approval/denial, stop/resume, and a tool error. Verify both fresh setup
and repair on macOS ARM64 (and Intel where supported); check Gatekeeper/signing
and architecture errors. On Linux, confirm real sandboxed command execution
and bundled ripgrep/bubblewrap operation. Download interruption and concurrent
Studio instances should also be exercised with real artifacts.

Automated tests use offline archives and mock startup checks. They do not
substitute for these live checks. Installation never reads or changes Codex
credentials, user settings, or projects.

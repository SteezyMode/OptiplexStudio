# Studio releases: one Current .deb

**Current published release:** v0.4.12 (October 29, 2026). The authoritative install link is the [Current Studio .deb](https://github.com/SteezyMode/OptiplexStudio/releases/latest/download/optiplex-studio_amd64.deb) on the repository front page. All previous versioned releases remain available for rollback.

## What publishes a release

`studio/version.py` defines `PACKAGE_VERSION` for the package builder, verifier and publisher. A **deliberate version bump merged into `main`** triggers the [release workflow](../.github/workflows/release.yml). A matching `vX.Y.Z` tag pushed separately also triggers it; tags must match the version in that commit. No manual tag is needed when the main-branch version bump creates the release.

PRs, ordinary main commits and scheduled validation are not releases. The workflow refuses to replace a release with an existing tag. Do not retag, clobber assets or advertise a PR package as Current.

The publisher checks source/tests, builds the versioned .deb, validates package metadata, runs GTK/installed-package smoke checks, creates a SHA-256 sidecar, and publishes:
- `optiplex-studio_X.Y.Z_amd64.deb` — immutable versioned installer.
- `optiplex-studio_X.Y.Z_amd64.deb.sha256` — checksum.
- `optiplex-studio_amd64.deb` — **identical release-local asset** used by the permanent `latest/download` link.

The latest link resolves to the asset on the most recently published latest release; no version-agnostic file is overwritten in the repository.

## Minimal release procedure

1. Finish a focused PR with regression checks and document the user-visible behavior, existing-file safety, rollback and any real-hardware checks still not performed.
2. Only if publishing is intended, increment `PACKAGE_VERSION` and update `docs/CURRENT-STATUS.md` with the source/acceptance distinction. Do not bump for routine docs or test improvements.
3. Require the PR's `Validate OptiPlex Studio` checks to pass (unit tests, package, GTK, installed-package smoke), then merge to `main` with the version bump included.
4. Confirm the main commit's Validate and Publish jobs pass. Confirm GitHub's latest Release, tag and all three assets correspond to the **merged main SHA**, and check the checksum. If publication failed, diagnose first; do not pretend the previous release was replaced.
5. Test the actual downloaded installer on a supported workstation when possible; document real Codex authentication, native tool launch, project persistence, restart and recovery separately. CI is not physical beta acceptance.

## Safety

Build/release CI runs on GitHub's isolated runners. It does not install packages on your laptop, manipulate live project folders, or touch NOW, Wolf, Tailscale, Jellyfin or server services. Preserve historical releases for rollback.

GitHub branch-protection and required-check settings are repository administration settings: the source workflows alone do **not** prove these protections are enabled. Verify them in repository Settings → Rules → Rulesets or branch protection separately.

Do not promote Studio as generally ready for consumers until clean-machine installation, authenticated Codex workflow, real native tools and persistence have been exercised end to end.

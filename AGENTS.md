# Studio development instructions

OptiPlex Studio is a **local-first Linux creative workspace** under an internal development name. It is not affiliated with Dell. These instructions apply to code, tests, documentation, pull requests and releases.

## Read before editing

1. `docs/CURRENT-STATUS.md`: shipped source, CI evidence and unverified real-device behavior.
   `docs/ALPHA-1-ROADMAP.md`: Alpha 1 exit gates (subset of frozen issue #3).
2. `README-STUDIO.md`: current local project, tools and Codex workflows.
3. The issue defining the work; currently [#30](https://github.com/SteezyMode/OptiplexStudio/issues/30) for unified project/navigation and [#31](https://github.com/SteezyMode/OptiplexStudio/issues/31) for Codex authentication/readiness.
4. Relevant source, tests and `docs/RELEASING.md` if packaging changes.

Historic Wolf, remote-mode, Docker and container instructions are **research, not the current supported product**. The Studio app runs locally. Wolf is an optional external graphical session, and NOW is a separate application.

## Development priorities

- Finish one end-to-end user workflow before expanding the tool catalog: create or reopen a unified Studio project, open native tools, use project-scoped Codex, validate assets in Godot, and recover the same project.
- Preserve old Blank/Godot/Music/Animation/3D manifests and Godot-only directories. New projects have one unified Studio format. No silent migrations, file moves, template replacement or data loss.
- Projects, assets, notes and Codex history belong to the user. Do not overwrite them because a fixture passes.
- Do not invent custom engines, AI agents, background daemons, transport protocols or integrations without a demonstrated blocking need. Use supported upstream interfaces.
- No feature creep into NOW, Wolf, Tailscale, Jellyfin, Docker or the server stack to fix a Studio issue.

## Safety and evidence

- Keep project operations local and scoped. Preserve safe path handling, conflict-checked writes, project isolation and Codex sandbox/approval rules. Never broaden permissions to hide a failing test.
- Never commit credentials, Codex tokens, private project files or machine-specific secrets. Authentication must be performed by the official tool, without reading or logging tokens.
- Test failure, cancellation, missing dependencies, old project formats and recovery; do not report an executable's presence as verified usability.
- Distinguish **implemented**, **fixture/unit tested**, **packaged/CI tested**, **physically exercised**, and **accepted**. A green CI build does not establish an actual Godot render, editable Blender/LMMS roundtrip, authenticated Codex request or clean-machine usability.
- Work on an isolated branch. Prefer a focused PR over patch/tarball handoffs. Verify the exact PR head, run relevant tests and the full GitHub CI before merging.

## One canonical installation and release

- The authoritative user download is the **Current Studio .deb** on the repository front page, served from GitHub Releases. Do not advertise PR artifacts, local builds or historic packages as Current.
- Normal PRs and non-versioned main changes do not publish. A deliberate `studio/version.py` version bump merged to `main` runs the release workflow; matching version tags are supported. Never overwrite or retag a published release.
- CI must check Python regressions, native GTK scenarios, package validation and an **installed** Debian smoke test. Keep the PR and main results distinguishable from physical device acceptance.
- Confirm published release tag, source SHA, installer asset and checksum before claiming a new build is available. Leave prior versions accessible for rollback.
- No release is called v1.0 or broadly consumer-ready until the relevant acceptance gates have actual observed evidence.

## PR checklist and handoff

For behavior changes, state: user problem and acceptance criteria; scope/files modified; compatibility/security boundaries; tests and their results; untested physical checks; rollback; and **one next action**. Update `docs/CURRENT-STATUS.md` only when evidence changes. Avoid multiple overlapping plans, issues or unneeded documents. Keep `CONTRIBUTING.md` and `docs/RELEASING.md` consistent with the implemented workflow.

**Operating rule:** make Studio usable and reliably installable, not merely more elaborate.
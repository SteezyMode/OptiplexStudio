# Studio Alpha 1 — acceptance path

**Status: pre-alpha, not yet accepted.** This is a concrete *subset and verification
checkpoint* of the frozen six-milestone v1.0 contract in [issue #3](https://github.com/SteezyMode/OptiplexStudio/issues/3),
**not a seventh v1 milestone or a rewrite of the frozen scope**. The local-first
implementation is authoritative; NOW, Wolf, SSH, Tailscale and Docker are not required
components of Studio.

**Goal:** On one compatible clean Linux workstation, install Studio from the single
Current .deb, open one unified project, use **Godot, Blender, LMMS and Codex**, then
reopen/recover the same editable work. Blockbench, Krita and VSCodium remain optional.
Prefer supported native applications and formats over new integration infrastructure.

## Alpha 1 exit gates — in order

- [ ] **A1 — Fresh installation and tool setup.** Download the Current .deb on a
  supported Ubuntu/Mint/Pop!_OS amd64 client, install it with the desktop package
  installer, open the GTK application, set up/detect the four tools in Settings,
  and reopen after logout/reboot. Record distro, installer version, observed UI,
  missing-tool recovery and actual launch results. GitHub Actions installed-package
  smoke and artifact checks are necessary but **do not** satisfy this physical gate.
  References: [#27](https://github.com/SteezyMode/OptiplexStudio/issues/27), [#29](https://github.com/SteezyMode/OptiplexStudio/issues/29).

- [ ] **A2 — One project, four tools.** Create one Studio project, reopen it, edit
  its Godot scene, save a Blender `.blend` plus a Godot-readable `.glb`, create an
  LMMS `.mmp` plus a playable `.ogg` or `.wav`, and import those exports into
  the *same* project. Verify original editable files and project history persist.
  For an old project without Godot, test the confirmed Add Godot operation without
  overwriting legacy files. References: [#30](https://github.com/SteezyMode/OptiplexStudio/issues/30), [#27](https://github.com/SteezyMode/OptiplexStudio/issues/27).

- [ ] **A3 — Codex real request, scoped changes, reconnect.** Sign in with the
  official Codex flow on that client; verify saved credentials without exposing them.
  With explicit consent, run the in-app project test and observe a *completed real
  model response*. Ask Codex to make a small reviewed project-local change; inspect
  the diff and ensure approval/sandbox enforcement. Close/reopen Studio and resume
  that same project conversation. Test cancel/offline/expired-login recovery.
  Reference: [#31](https://github.com/SteezyMode/OptiplexStudio/issues/31).

- [ ] **A4 — Playable roundtrip.** Run the Godot scene locally and verify the Blender
  exported object and LMMS exported audio are present and functioning. Preserve
  the source assets. Headless project import or a successful tool launch alone
  does *not* satisfy the gate. Reference: [#27](https://github.com/SteezyMode/OptiplexStudio/issues/27).

- [ ] **A5 — Persistence and recovery.** Reboot/restart Studio, restore selection
  and saved work, check project and Codex history, export a reviewed backup,
  **restore a copy onto a different clean workspace/machine**, then open editable
  Blender/LMMS/Godot sources. Off-device backup/restore must be tested; a backup
  archive stored on its source machine is insufficient.
  References: [#6](https://github.com/SteezyMode/OptiplexStudio/issues/6), [#27](https://github.com/SteezyMode/OptiplexStudio/issues/27).

## Shared AI creative integrations (not an extra alpha gate)

[AI Creative Tools](CHARACTER-LAB.md) installs general Blender automation,
specialized MPFB human anatomy controls and dormant Rigger as one toolchain.
Codex uses these according to the user's creative request inside the same
project; separate character, prop or plant labs are not part of Studio.
This does not change A1–A5 or frozen issue #3. Acceptance still requires
actual editable sources, Godot playback, completed agent tool calls and
recovery on supported hardware.

## Completion standard

Each gate requires a dated evidence note (OS, package version, Git commit, machine,
test steps, actual results and any failure/recovery). Distinguish source unit tests,
isolated GTK/package tests, installed-package CI, and **real application operation**.
Do not check a gate on fixture evidence, assume authentication from `codex --version`,
or call alpha complete until all five gates pass. Keep the published .deb available
for rollback and **do not touch NOW or the live host services**.

## Work order from the present v0.4.15 baseline

1. **Now:** Make core-four availability and diagnosis clear without presenting
   executable discovery as proof of working applications; keep the single Settings
   installer. Improve automated regression evidence as needed.
2. **Next device pass:** Exercise A1, A2 and A3 on the existing Linux test client;
   fix *observed blockers only* in small PRs, shipping via one Current .deb.
3. **Then:** Prove A4 and A5 with editable sources, actual Godot playback and tested
   off-host restore. Record observed failures and fix them before declaring Alpha 1.
4. **After Alpha 1:** Continue the remaining frozen v1.0 milestones; optional tool
   integrations and appearance polish remain backlog rather than new alpha gates.

See [Current Status](CURRENT-STATUS.md) for implementation-vs-acceptance evidence
and [Releasing](RELEASING.md) for immutable installer publication.

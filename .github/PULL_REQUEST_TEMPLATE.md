## User problem / acceptance
Describe the observed problem or user outcome, link the relevant issue, and say what someone must actually observe to call it fixed.

## Scope and boundaries
Identify the changed components and important non-goals. Describe how old projects, documents, Codex sessions, local configuration, and unrelated NOW/Wolf/server services are preserved.

## Verification and evidence
- [ ] Focused regressions (commands/results):
- [ ] Full `Validate OptiPlex Studio` PR CI (link/run):
- [ ] GTK + Debian package and installed-package smoke checks:
- [ ] Real workstation acceptance (evidence, or **NOT TESTED**):

Do not equate mocked API responses, headless engine tests, or a binary version check with successful native tool use or authenticated Codex.

## Release and rollback
- [ ] No version bump unless deliberately publishing a new Current .deb.
- [ ] If published: main SHA, release tag, current link, package checksum verified.
- [ ] Existing data/settings preserved; rollback and remaining limitations documented.

**Next action:** One concrete follow-up, not a second roadmap.

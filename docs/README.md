# Studio documentation map

**Studio is a native GTK3 AI-assisted creative workspace.** It may be used inside a Wolf-streamed XFCE desktop, but the streaming container is not the Studio application. NOW is an independent remote-access launcher.

Read these in order when joining the project:

| Need | Canonical document |
| --- | --- |
| Product, current released package, local build | [Root README](../README.md) |
| How to change code safely, run tests and submit PRs | [CONTRIBUTING](../CONTRIBUTING.md) |
| What has been **actually verified** in source vs published .deb vs Wolf reference environment | [CURRENT STATUS](CURRENT-STATUS.md) |
| Exactly what counts as Studio v1.0 completion | [Frozen six-milestone issue #3](https://github.com/SteezyMode/OptiplexStudio/issues/3) |
| Native GTK client configuration and feature behavior | [Detailed app guide](../README-STUDIO.md) |
| Repeatable packaging and immutable release flow | [RELEASING](RELEASING.md) |
| Project/runtime state ownership and local-first direction | [ADR-001](ADR-001-LOCAL-FIRST-SHARED-STUDIO-RUNTIME.md) |
| Godot/Blender/Blockbench/LMMS upstream integration rules | [ADR-002](ADR-002-UPSTREAM-FIRST-INTEGRATED-TOOLCHAIN.md) |

## Reference material — not independent v1 release gates

These notes describe past research, examples, prototype assets and experimental directions. They are **not** proof that a packaged app reproduces the results, and their titles do not expand the frozen six-milestone contract:

- [Art Director prototype handoff](MILESTONE-8-ART-DIRECTOR-HANDOFF-2026-10-18.md): the experimental label "Milestone 8" is **not** a seventh/eighth frozen Studio v1 criterion.
- [Creative direction and asset sourcing](CREATIVE-DIRECTION-AND-ASSET-SOURCING-V1.md)
- [Reference production curriculum](ART-DIRECTOR-REFERENCE-PRODUCTION-CURRICULUM-2026-10-18.md)
- [Production reference library](STUDIO-GENERAL-PRODUCTION-LIBRARY-V1.md) and [future knowledge roadmap](STUDIO-PRODUCTION-KNOWLEDGE-ROADMAP-2026-10-18.md)
- [Reference batch](THRESHOLD-REFERENCE-BATCH-01.md), [Codex ingest task](REFERENCE-BATCH-01-CODEX-INGEST-TASK.md) and [Threshold art direction](THRESHOLD-PATIENT-V2-2-HORROR-DIRECTION-BRIEF.md)
- [Mocap sources](STUDIO-FREE-MOCAP-SOURCES-2026-10-18.md) and [animation trial](TRIAL-01-PATIENT-V2-ANIMATION-SOURCING.md)
- [Remote tmux session guide](remote-development-tmux.md): disconnect persistence is not reboot recovery.

## Rules for keeping this useful

1. Update **CURRENT STATUS** only for verified changes. Label the observed environment and commit/release; avoid claiming GUI package deployment from a host experiment.
2. Create an issue for a new idea before writing a lengthy design handoff. Do not copy active checklists into multiple documents.
3. The authoritative Studio v1 completion contract is issue #3. Any new creative research remains separate/post-v1 unless needed by that exact acceptance test.
4. Keep credentials, private projects, unlicensed visual references and session tokens out of Git.
5. Code/document changes should be scoped to their owning repo. NOW does not own Studio's creative pipeline, and Suite is only a navigational/architectural hub.

The public product name and application-code license remain unresolved decisions. Follow the [contributor guide](../CONTRIBUTING.md) for current code boundaries. Before renaming, protect package/executable names, GTK application IDs, configuration paths, project manifests and Wolf shortcuts with tested compatibility and rollback. Do not invent a license or rename persisted technical IDs without those tests. Private Suite coordination notes are not required to build this public repository.

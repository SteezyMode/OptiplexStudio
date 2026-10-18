# Studio Art Director — reference-driven production curriculum (pilot)
Status: ACTIVE DESIGN / PARTIALLY EXECUTED; source acquisition and tests require host operations. 2026-10-18.

## Why
Threshold Patient V2 achieved a major visual jump versus V1, but the hands remain anatomically weak, diagnostic animations are stiff, and the prior V1 AI behavior is substantially unchanged. Address those as separate measurable workstreams rather than one massive autonomous 'make realistic zombie' Codex prompt.

This is **not model fine-tuning**: accumulate verified references, indexed asset data, test scripts, approved design rules, test results and Codex task briefs. Require license provenance, a human artistic review and in-engine playtest before promotion into shared best practices. Document failures, too.

## Common loop
1. Identify specific deficiency with screenshot/gameplay evidence and human acceptance criterion.
2. Find/reference prior art and existing reusable open assets, with exact version/license and no assumptions.
3. Inventory formats/armature/animation clips/materials in scripts without using AI calls for predictable parsing.
4. Approve ONE small adaptation/import.
5. Launch tightly scoped Codex with workspace-write path, explicit no-touch paths, time/iteration cap.
6. Validate automatically (topology, transforms, animation track mappings, Godot import, frame captures); visually inspect through Wolf.
7. Record before/after, failures, source metadata, elapsed time, Codex sessions/revisions and reuse notes. Commit only original code/docs or properly distributable assets.

## Track A — Animation (first)
- Start with creator-published CC0 Quaternius Universal Animation Library 2 Standard, using a free version and checking exact clip inventory.
- First stage source: older Jan 2026 Quaternius OpenGameArt mirror https://opengameart.org/content/universal-animation-library-2 with direct ZIP https://opengameart.org/sites/default/files/universal_animation_library_2standard.zip (creator upload, 10.3 MB). It predates June root-motion update. Prefer current 17 MB itch Standard https://quaternius.itch.io/universal-animation-library-2 once we know suitable motion is included.
- Mapping: target V2 44 bones; source glTF/FBX may differ in names/rest poses. Compare before retarget. Use Godot 4 SkeletonProfileHumanoid/BoneMap or Blender mapping with recorded settings; do not alter V2 source rig blindly.
- First deliverable: one reversible comparison of imported locomotion vs TEMP_walk with walking-in-place or root motion deliberately chosen; check thumbs/wrists, shoulder/clavicle, pelvis, foot sliding, gown intersection.
- Gate: review before blending, foot IK, attacks, or additional motion packs.

## Track B — Anatomy (after Track A review)
- Targeted repair of hands/thumbs/wrist/knuckles first; maintain one current mesh/gown/rig; photograph/reference hand poses and establish correct handedness, knuckle bends and palm/dorsal views.
- Inspect joints, heel/foot shape, face and garment clearance next. Use Blender Human Base Meshes as *reference* where license safe; avoid redistributing ambiguous Rain Rig contents.
- Measure topology/weight changes with fixed before/after screenshots and joint animation poses.

## Track C — Behavior (separate from animation)
- Define what 'physically compromised patient' means mechanically: hesitant walking, pauses, imperfect recovery, delayed response, low-energy reaching, deliberate pursuit; user approves actual game design rules.
- Maintain a reversible separate AI behavior experiment, with deterministic states/transitions and tests for perception/pathing/stalls/obstructions/attack tell and collision.
- Avoid coupling skeleton retarget failures to behavior logic.

## Track D — Wider Studio
- Expand exactly the same loop to environment assets, textures/materials, props, VFX, audio, quest/item/saving systems, and game logic. Two reference sets: shared technical patterns and game-specific creative bible.
- Use curated and licensed libraries before autonomous custom creation. No bulk downloads, off-scope project mutations, scraped creative training sets, or uncontrolled automatic editing.
- Only extend the GUI after proving usefulness in a few hands-on pilots; combine with planned broken Wolf AI Workspace repair.

## Guardrails
- Preserve original Patient V1, V2 r06 source, normal game startup, Wolf services and existing Codex work.
- Avoid unbounded tasks while Codex allowance is limited. Small bounded runs with human inspection between stages.
- Stage acquired ZIP outside the Godot project; record SHA256, internal license, file and animation inventory before use. Do not automatically commit ZIP/binaries.
- Publishing rights must be checked at exact asset version, not inferred from a creator's general home-page license.

## User-approved direction
- 2026-10-18: User explicitly approved downloading the free Quaternius animation pack to test one walk and pursuing a broader staged improvement process for anatomy, animation and logic.
- Artistic direction: a restrained, physically compromised patient, not a generic aggressive zombie.
- Actual downloaded archive, clip inventory and successful retarget remain **unverified** until the server test.

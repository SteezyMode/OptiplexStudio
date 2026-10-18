# ADR-002 — Upstream-first integrated creative toolchain

**Status:** Proposed long-term product direction (not an implementation authorization).  
**Date:** 2026-10-19  
**Scope:** OptiPlex Studio (distinct from OptiPlex NOW).  
**Related:** [ADR-001: shared local-first runtime](ADR-001-LOCAL-FIRST-SHARED-STUDIO-RUNTIME.md), [frozen Studio v1.0 requirements](https://github.com/SteezyMode/OptiplexStudio/issues/3), [current status](CURRENT-STATUS.md), [NOW integration strategy](https://github.com/SteezyMode/OptiplexNow/blob/main/docs/UPSTREAM-FIRST-WOLF-INTEGRATION.md).

## Product hypothesis

The opportunity is **not** to resell Godot, Blender, LMMS, Blockbench or Codex with a new logo. It is to make it reliably simpler to create a complete game by managing project context, assets, task lifecycle, formats, compatible versions and playable tests across them. A polished launcher alone has weak differentiation; tested interoperability and recovery are what users might pay for. This is a hypothesis, not proven market demand.

**Decision:** Studio owns the production workflow and integration contracts, while specialist editors remain upstream when possible. White-label the **Studio-owned user experience**, not every external editor. No mass forks or source-code dismantling merely to make all windows look alike.

## Small initial product stack

| Role | Default | Integration tier |
| --- | --- | --- |
| Game engine / runtime / preview / export | **Godot** | Deep editor plugin, CLI import/validation, stable scene templates |
| Complex 3D / rigging / animation / materials | **Blender** | Deep Python addon and scripted export/retarget recipes |
| Simple low-poly modeling | Blockbench | Project-aware save/export plugin or glTF converter if needed |
| Music / scores | LMMS | Managed project/source and predictable exported audio first; deep automation only where feasible |
| AI assistance | Existing Codex/other provider | Project-scoped worker, approval, logs, bounded tasks, context retrieval |
| Coordination | Studio-owned core | Canonical manifest, source/derived assets, test results, provenance, human review |

**Confirmed prioritization (2026-10-19):** Godot gameplay and project completion first; Blender is the active 3D modeling/animation companion; Codex orchestrates bounded tasks. LMMS remains important for finishing games but deeper integration is deferred. Blockbench and browser editors are optional, without new integration work unless an observed need emerges. See the confirmed-focus section below. Other software adapters must not become prerequisites for shipping a playable game.

## Specific interoperability contract

An asset record has project ID, stable asset ID, source file, derived exports, original author/license/provenance, units/axes, mesh bounds, skeleton mapping, animations, material requirements and reproducible conversion recipe. Studio provides:

1. **Export:** versioned Blender Python or Blockbench adapter exports GLB/glTF and validates source/bake assumptions; LMMS delivers OGG/WAV for Godot.
2. **Import:** Godot-side import presets and scene templates, measured model-height/unit normalization, rig/animation mapping, naming and dependency checks. Do not use guessed character scales.
3. **Validate:** reproducible local checks *and* rendered playtests; parse success alone never proves attractive or functional visuals. Catch GDScript parse errors, missing clips, animation deformation, nonhuman scale and frame/window issues before review.
4. **Review:** developer can compare previews, open source editor on an asset, approve/reject work, retain prior versions and keep the same project history.
5. **Recover:** stable, repeatable updates for known-good tool combinations; preserve originals, rebuild derived outputs, migrate deliberately and allow rollback.

The zombie trials supplied concrete negative cases: 8.147 m imported model, retarget-induced shoulder/foot damage, valid headless tests but bad graphics, duplicate launcher processes, and missing Wolf titlebars when Godot was forced to Wayland under XFCE. These are **pipeline-quality failures**, not reasons to fork Blender or Godot. The Studio-owned demo exit safety autoload and Wolf X11 launcher are early adapter examples, **not a finished integrated UI**.

## Updates and vendor changes

Keep a **compatibility manifest**: tool name/version, supported addon/plugin versions, interchange versions, validated fixture set and platform constraints. Run representative import/export/rig/audio/gameplay smoke tests before making an upgrade default. A known-good project toolchain may stay on pinned compatible versions, with deliberate security update and migration pathways. Do not freeze the host OS or silently update running game/server services.

## Fork decision gate

Prefer: **supported CLI/file formats → plugin/add-on → small upstream change → maintained patch set → full fork only when warranted**.

Fork only after writing down: the exact blocked workflow, why documented APIs/plugins fail, legal and trademark constraints, patch size, maintenance cost across at least two upstream releases, CI matrix, end-user benefit, rollback plan and security response policy.

Initial license map (**informational; not legal clearance**):
- [Godot](https://github.com/godotengine/godot) MIT.
- [Blender](https://www.blender.org/about/license/) principally GPL, with other third-party and component terms; distributing a modified executable has obligations.
- [Blockbench](https://github.com/JannisX11/blockbench) GPL-3.0 for application source. Its [upstream README](https://github.com/JannisX11/blockbench#plugins) explicitly states that external API plugins/themes may be proprietary or paid; redistribution of modified Blockbench itself remains a separate license question.
- [LMMS](https://github.com/LMMS/lmms) GPL-2.0; individual dependencies/plug-ins may differ.
- Game models, motions, sounds, fonts, Codex accounts and provider APIs need separate rights review. A game-use license does not automatically allow redistribution of an asset pack within Studio. Do not claim that separate execution automatically guarantees that a proprietary bundle has no copyleft obligations.

## Sequence / criteria

**No change to the [frozen six-milestone Studio v1.0 contract](https://github.com/SteezyMode/OptiplexStudio/issues/3).** This is architecture and likely post-v1 productization:

1. Finish v1 recovery/reinstall and the specific two-room game acceptance (potentially aligned with the requested short zombie game).
2. Demonstrate one **Godot ↔ Blender** animation/model roundtrip with consistent scale, skeleton mapping, repeatable export/import, and a visual/human pass — *without manual SSH fixes*.
3. Repeat on at least one unrelated asset/game style to prove the pipeline is genre-neutral.
4. Preserve LMMS audio source/export as part of finished-game production; defer deep LMMS automation, Blockbench plugins, and browser-tool integration until a demonstrated workflow bottleneck warrants them.
5. Test with an outside developer on supported Linux; record setup time, manual repairs, onboarding questions and willingness to pay.
6. Evaluate selective forks only if repeated real-world blockers justify them.

**Kill criterion:** If users still routinely have to manually troubleshoot imported scale, animation, installed tool versions or experiment launch, calling this a unified Studio product is premature.

**Commercial boundary:** OptiPlex is placeholder branding. Rebrand before selling, perform trademark and full distribution license review, and do not promise automated game creation or bundle ongoing expensive AI inference without pricing it.


## Confirmed near-term focus — 2026-10-19

The owner explicitly selected **Godot + Blender + Codex as the active development stack**, focused on completing a short playable zombie game and the frozen Studio v1 acceptance conditions. Do **not** initiate a Blockbench-first comparison or expand browser-tool integrations as a prerequisite.

- **Godot is the center of game completion:** gameplay scripting, doors/objectives, scenes, triggers, audio playback, playtesting, endings, editor/runtime stability. Headless validation complements but never substitutes for rendered playtests.
- **Blender is the active 3D companion:** editable source, needed props, rigging, animation, predictable glTF/GLB export into Godot. Prioritize actual game requirements and limited, measurable fixes; do not embark on an unbounded character/model pipeline.
- **Codex provides project-scoped automation**, with its existing human approval/review workflow.
- **LMMS is important to a finished game**, especially score, music and atmosphere. Retain it as a meaningful production capability and satisfy audio/music requirements using currently working export/import. **Defer deeper LMMS integration**, not audio production itself.
- **Blockbench remains optional/deferred.** It may be useful for quick low-poly modeling or as a gentler manual editor, but its incremental value over already-scriptable Blender is not currently established. Revisit only if a concrete Blender workflow proves unnecessarily costly.
- Existing browser tools remain available but **not active integration priorities**; shortcuts alone aren't proof of a unified production pipeline. No rush to remove functioning tools.

**Minimal next test:** make progress on the existing zombie experience with Godot gameplay and only the Blender assets necessary to support it; preserve current Wolf streaming, demo exit controls and original project data. Revisit tooling only in response to observed bottlenecks. This is a **priority clarification**, not new v1 scope, and supersedes earlier Blockbench-first recommendations.

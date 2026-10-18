# Single bounded Codex job — Threshold Reference Batch 01
Run in **Art Director** workspace after local catalog inventory. This is a sourcing/intake job, NOT a character regeneration job. Default budget: <=20 minutes of active investigation and scripted operations, no more than 2 network download attempts per source. If network is unreliable, finish offline inventory and report remaining downloads clearly. Do not repeatedly retry or consume the remaining five-hour allowance waiting on large assets.

## Context
User visually approved Patient V2 r06 as a huge model improvement over V1, but hands/face remain amateur and motion is stiff. AI logic is V1 reused, so it is not improved. Test scene is operational through Wolf. User now explicitly wants batch staging of anatomy, zombies, animation, materials/textures and relevant props, with the long-term goal of reusable Studio knowledge rather than a narrow character-only tool.

## First read
- `catalogs/threshold-reference-batch-01.json` and `docs/THRESHOLD-REFERENCE-BATCH-01.md` in OptiplexStudio repository.
- `/home/optiplex/StudioProjects/.studio/art-director/reference-batches/threshold-patient-reference-batch-01/INVENTORY.md` and `source-inventory.json` (if generated).
- Prior Patient V2 report and game test documents only as needed.
- Official license / exact version pages linked from the catalog, not a guessed search-result label.

## Deliverables, in order
1. **Verified archive inventory:** Determine all actual humanoid idle/walk/zombie/reach animations in existing `incoming/quaternius-ual2-standard.zip`; if FBX, inspect non-destructively via installed Blender 5.2 environment and read source animation names, rig bone names, frame ranges and FPS. Do not import into Godot yet.
2. **Curated zombie models:** Confirm direct authorized download options for the official Quaternius Animated Zombie Pack and Zombie Apocalypse Kit; stage smaller public CC0 archives when available without login, document exact URL/license/checksum/file tree and rig/motion counts. Do not download from third-party rehosts or infer a ZIP URL.
3. **Real anatomy foundation:** Verify MPFB 2.0.18 + bundled MakeHuman core CC0 material and current Blender 5.2 compatibility. Produce a **safe installation plan** for persistent Wolf Flatpak user `retro` or a parallel isolated install; do not install add-ons, overwrite Blender configuration, or rebuild Wolf in this pass. Compare V2 anatomy shortcomings to MPFB capabilities.
4. **PBR material starter kit:** Use official Poly Haven API (or official pages) to shortlist 1–2 suitable 1K or 2K maps each for realistic gown weave/roughness, skin surface detail (procedural core preferred rather than mislabeling unrelated textures as skin), ward wall/floor tile, aged/stained environment, and one relevant hospital prop. After verifying specific file/map licenses, download a **small** sample set into the Art Director intake area if accessible; save provenance and hashes. Do not apply automatically to Patient V2.
5. **Review dashboard:** Write a single `REFERENCE-INTAKE-REPORT.md` and `source-inventory.json` under the batch's `reference-batches` folder. Include a simple table with source, version, license, bytes, local path, skeleton/animations or PBR map kinds, intended use, fit concerns, status, and action needed. Include explicit blockers and actual elapsed time.
6. **One next production brief:** Prepare `NEXT-ANIMATION-BRIEF.md` describing how to compare ONE compromised-patient walking clip against V2's TEMP_walk in a separate scene, including target 44-bone mapping, rotation/root-motion, gown/fingers, foot sliding, visual check and rollback. Do not execute the retarget/import inside this job.

## Non-goals / safety
- No changes to `~/StudioProjects/Godot/threshold`, V1, V2 .blend, test scene or main startup.
- No unbounded model remodeling, training of AI weights, bulk image scraping, paid downloads, hidden remote access, privileged Docker operations, or arbitrary Git commits.
- This task does not require installing new applications or modifying the existing Wolf session.
- Keep archives outside public Git, without exfiltrating personal files or contacting other external services.
- Avoid holding huge ZIP members fully in memory. Validate hash and inspect files, do not extract unsafe paths.
- Stop and report clear partial status if a pack's license/version/download URL is uncertain or network unreachable.
- Finish with 1-page status and specific next action, **then wait for human approval** of the first retarget/MPFB installation.

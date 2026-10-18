# OptiPlex Studio — General Production Knowledge Library v1
Date: 2026-10-18
Status: **accepted product direction; proposed first implementation batch, requires item-by-item source/usage approval**
Scope: **genre-neutral**, reusable across Studio projects. Threshold is a proving ground, NOT the library's organizing principle.

## Product objective
Studio should help one creator take an original game from concept to a playable, shippable result. Make a *retrievable, testable production knowledge system* across design, art, engineering, audio and delivery — not an inert hoard of sample ZIPs.

The AI's base model is NOT fine-tuned merely by downloading references. Its practical output improves when it can find relevant **approved source examples, validated recipes, realistic project constraints, expert documentation, evaluation rubrics, and prior human-reviewed outcomes** and use them in a bounded task.

## Hard boundary: shared expertise vs. projects
- **Shared Studio Library:** genre-neutral techniques, tooling recipes, reference packs, proven code patterns, comparative tests, licensing and provenance, templates, design concepts and evaluation methods.
- **Project Design Library:** intended identity and approved references for one game (e.g., Threshold's undead patient, hospital, enemy behavior and horror-specific art direction). It can **use** global techniques without turning the global library into horror-specific defaults.
- **Job/Artifact History:** concrete per-project tasks, inputs, changes, human feedback and test results. Reusable lessons can be promoted into shared library after review; raw history remains project-scoped.

## Curriculum / top-level categories

| Domain | Reusable examples and technical knowledge | Evaluate with |
| --- | --- | --- |
| Game design & philosophy | core loops, level flow, readability, feedback, tension, challenge, accessibility, progression, pacing, player agency, economy, risk/reward, camera/controller feel | clear player goals; playable iteration; human playtest rubric |
| Gameplay systems & Godot | GDScript architecture, finite-state machines, behavior trees, navigation, combat interactions, inventory, save/load, UI/input, event/quest logic, physics, signals, debugging | runnable small test scene, reproducible checks, performance |
| Characters, creatures & rigging | human and animal anatomy, topology, skin weights, UVs, gestures, facial rigs, animation retarget, stylized vs. realistic design | neutral multi-view renders, posing and skin deformation tests |
| Props & industrial objects | mundane clutter, furniture, tools, machinery, usable interactive props, collision shapes, LODs | importability, scale, visual style, collider fit |
| Materials, textures & fabrics | physically based workflows, skin, textiles, metal, glass, wood, plastics, dirt/wear, UVs, baked/procedural textures | calibrated neutral lighting and in-scene response |
| Architecture & worlds | modular rooms, outdoors, lighting, doors, pathways, terrain, signage, decals, level composition | snap/scale, navigation, clipping, performance |
| Flora, fauna & ecosystems | plant models, foliage shaders, wind, animals, quadruped rigs, habitats and spawning systems | animation, silhouette, draw calls, ecological consistency |
| Vehicles & mechanics | cars, bicycles, wheels/suspension, machinery, paths, camera integration, controls, physics | small controllable scene with believable motion |
| Weapons, tools & interactions | game-side held-item presentation, attachments, gameplay interactions, hit boxes, projectile systems, balancing | in-engine responsiveness, clipping, readability, fairness |
| Audio, music & atmosphere | DAW workflow, foley, spatial audio, procedural effects, music states/transitions, mix and accessibility | in-engine cues, transitions and balance |
| UI, UX & accessibility | responsive layouts, inventory HUDs, menus, controller navigation, subtitling, legibility, visual affordances | keyboard/gamepad workflow and low-resolution viewing |
| Optimization, QA & shipping | asset budgets, profiling, build pipelines, version control, backups, tests, licensing/attribution, export targets | repeatable test, memory/GPU budget, clean rollback |

No genre is the default. Do not add a dedicated horror folder to this *global* taxonomy; keep genres in project-specific overlays or cross-domain tags.

## Record model for each curated item
Each source entry should have:
1. Stable ID, category/tags, short plain-language **what this teaches / when it is useful**.
2. Direct origin URL and creator; access date; version, price and license evidence, uncertainty plainly flagged; approved/rejected/pending status. Do not assume a distributor's blanket license applies to every asset.
3. Files/formats and known compatibility (Blender, Blockbench, Godot, etc.), approximate size, restrictions on distribution/source control, attribution obligations if any.
4. Art direction notes, intended transformation and anti-references (what *not* to blindly imitate).
5. A runnable *recipe* or small demonstration when practical: import/render, retarget, shader, template scene, test fixture, etc.
6. An evidence record: screenshots/render and human evaluation; technical failures, fixes and reusable lesson.
7. Provenance chain between original source and game-specific derived outputs; source assets never silently moved into public repositories.

A link-only candidate is cataloged as a candidate, **not labeled a verified recipe or completed skill**.

## Discovery and production modes
- **Discover:** Find a relevant approved source or trusted documentation.
- **Transform:** Modify and adapt geometry, materials, animation, art, code and systems where license allows, preserving originality and provenance.
- **Create:** Build a new solution from scratch using tested methods and source-informed art direction when the desired outcome is specific or no suitable asset exists.
- Do not artificially bias toward downloads/premade assets, and do not demand all work be made from scratch. Choose based on project goal, quality, modification cost, rights and performance.

## First cross-disciplinary acquisition wave — breadth before volume

Start with a **small representative matrix, not a full mirror of asset websites**. Each entry begins as source metadata/notes; binaries downloaded only after approval. We deliberately sample multiple domains rather than make the first library a zombie catalog.

1. **Game design framework** — one original Studio design-brief template and player-loop/playtest rubric; grounded in respected public developer talks or docs, with clear claims and source links.
2. **Reusable Godot AI** — one inspectable, well-scoped NPC state-machine/nav demonstration with idle, patrol, notice, investigate, return; no Threshold-specific enemy behavior baked into the global recipe.
3. **Human and creature rig references** — one legally clear general human topology/rig example and one nonhuman or quadruped reference candidate, noting skeletal compatibility/retarget limits.
4. **PBR samples** — one fabric, one hard-surface (metal/wood/paint) and one organic surface candidate with full channel/roughness notes; test a *material conversion recipe*, not just catalog labels.
5. **Modular world + ordinary props** — one architecture module candidate and 2–3 everyday objects; demonstrate Godot import, scaling, collision and basic interaction.
6. **Natural world** — vegetation and terrain material candidate with one wind/LOD note; separate animal/creature reference from vegetation.
7. **Vehicle/mechanism** — a simple rigid-body or wheel/suspension/reference candidate and a small Godot functional prototype **proposal**, not a production vehicle.
8. **Audio** — a small sound library/DAW process and Godot spatial/trigger test recipe; no bulk sounds.
9. **UI/interaction** — one controller-friendly Godot menu/inventory interaction pattern and a low-resolution usability rubric.
10. **Production pipeline** — an end-to-end original asset test: provenance → Blender or Blockbench → Godot → render/playtest → versioned lesson.

These are cross-domain **candidate tasks**. Validate one or two first and adjust based on actual usefulness. Prefer authoritative official documentation and established, clearly licensed/open-asset repositories over generic search snippets. Candidate source families: Godot/Blender official documentation, Poly Haven, Kenney, Quaternius and source-visible permissively licensed code examples; verify exact individual terms and compatibility. If external sources need accounts, payments or uncertain rights, stop for user choice.

## Architecture and operating constraints
- Initial version should be text/manifest-first under `~/StudioProjects/.studio/`, preferably a small JSON catalog plus Markdown recipes. Use link metadata until approval to acquire files.
- Existing Art Director batch catalogs and human decisions form the first seed; do not overwrite or reorganize active Threshold jobs.
- Build a simple searchable index with category/tag/project applicability; retrieve **only task-relevant items** into Codex context, rather than feeding thousands of pages into every session.
- Keep large examples/videos/models outside version control with hashes and backups where feasible; no blind crawling, indiscriminate scraping, automatic redistribution or training on unapproved copyrighted content.
- **Resource budget:** no always-running LLM, vector database, GPU render/indexer, image embeddings or extra container required for v1. Background scheduling is unnecessary until measured retrieval or catalog size justifies it. Cap each bounded acquisition/test job by wall time and file size; don't compete with ongoing animation production on a single 6-GB VRAM GPU.
- Add independent Studio native/Wolf frontends as *views* of this same host library, per [ADR-001](ADR-001-LOCAL-FIRST-SHARED-STUDIO-RUNTIME.md). No duplicate catalog in each container.
- Track provenance, rejected candidates, incomplete tests and user taste rather than extrapolating project-specific preferences into generic rules.

## Next operator-facing action
Finish the currently running V2.2 design report separately. Then request a **short, no-download inventory and sourcing plan** for wave 1 (prefer about 10 cross-domain candidate records; no new meshes, no render-intensive evaluation yet). User reviews domains and priority source choices before obtaining binaries or spending substantial Codex allowance. Later pilot 2–3 recipes end to end and score actual output improvement.

## Definition of v1 success
A fresh game project can ask Studio for, e.g., "a deer AI prototype", "a driveable car", "a medieval cloth material", "an interactive vending machine", "an atmospheric horror hallway", or "a rhythm-game UI" and receive a focused set of relevant vetted methods/assets/examples **without routing everything through Threshold or zombie references**. Each suggested implementation has licensing context, quality checks and known integration steps rather than only a list of links.

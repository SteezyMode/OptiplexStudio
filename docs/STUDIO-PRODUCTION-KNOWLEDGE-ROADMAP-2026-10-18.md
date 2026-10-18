# OptiPlex Studio — Art Director and future production knowledge roadmap
Date: 2026-10-18
Status: User-approved direction; implementation pending

## Central purpose
Create a persistent, portable, selectively curated AI-assisted game-development knowledge and production system that improves Codex's practical output across projects, sessions, and installations. It must develop reusable workflows, inspections, benchmarks, documentation, and human-reviewed artistic lessons—not treat asset collection as model training or indiscriminately download references.

## Milestone 8 immediate work
- Complete Worker vs. Threshold patient visual and technical comparison, with neutral front/side/three-quarter renders, wireframes, rig/weight checks, animation inventory and user-reviewed findings.
- Current verified Worker Blender source: 4 meshes, 2,357 vertices, 2,323 polygons, one 49-bone rig, 12 materials. Worker glTF has 24 animations, four meshes, one skin, embedded buffer and no image dependencies. Separate Animations.fbx retained.
- Current verified Threshold patient: 44 meshes, 6,820 vertices, 6,778 polygons, two 18-bone rigs, 39 materials; two NLA idle tracks 1–73 and walk tracks 1–49 with matching timing; most small components single-group skinned and a main PatientSkin mesh attached to the duplicate rig.
- The first Codex attempt created no renders/scripts/reports because the Threshold-scoped workspace cannot write to shared `.studio/art-director/workflows/` or `.studio/art-director/comparisons/worker-vs-patient/`. Respect that boundary. Solve via a deliberately scoped Studio Art Director workspace/launcher or specific approved write mounts, NOT blanket filesystem or Docker access. Reuse the existing Blender Flatpak within Wolf Studio desktop and existing MCP; do not disturb live services or game assets.

## User-approved expansion direction
Develop both an engineering evaluator (correctness, performance, importability) and art-direction evaluator (readability, anatomy, silhouette, composition, materials, movement) with human approval of subjective results.

Curate licensed *technical* reference files in small representative sets:
- Characters: humanoids, anatomy, face/hands, clothing, rigs, locomotion, animation; later animals, quadrupeds and creatures.
- Everyday props and environmental dressing: furniture, household objects, tools, machines, debris, litter, signage and fixtures.
- PBR materials: complete channel sets and node graphs, real-world surface wear and lighting responses.
- Architecture: modular buildings and rooms, roads, doors, stairs, windows, interiors and exteriors.
- Natural world: vegetation, trees, plants, ground cover, rocks, terrain, water and wind.
- Vehicles and mechanical systems: cars, bicycles, moving parts, mechanical animations.
- Weapons and other gameplay-facing objects: weapons, attachments, equipment, inventories, item presentation; add when relevant to a project.

Over time extend this production-knowledge system beyond art into *gameplay and systems engineering*: interaction systems, combat logic, hit detection, damage/health, enemy AI, state machines, equipment, weapons, projectiles, inventory, RPG attributes, progression, quests, dialogue, saving/loading, animation-state integration, balancing, testing, and performance. Scope and priorities should follow real project needs rather than attempting to implement everything now.

Sources for study: verified Blender and Godot official docs, credible PBR guidance, inspectable CC0 assets from Poly Haven, Quaternius and Kenney where appropriate. Check individual asset licenses and source provenance. Keep the ten approved horror influences separately as curated artistic references; do not add unapproved horror imagery. Do not narrowly define global library by horror/Threshold.

## Workflow goal
Gradually deliver reusable, project-independent capabilities along the lines of `studio-art register`, `inspect`, `compare`, `review`, `validate`. These are aspirational interfaces, not implemented commands. Each acquisition produces a source/license record, manifest, hashes, dependency audit, technical inspection, renderable comparison and actionable learnings awaiting human review. Prefer searchable/indexed targeted retrieval over loading the whole library into every Codex session. Keep small code/docs/approved previews in version control; large binaries in backed-up asset storage. Preserve Codex sandboxing.

## Immediate order
1. Fix narrow Art Director workspace write access, verify allowed paths.
2. Produce Worker-vs-patient renders/report, have user inspect and approve conclusions.
3. Select together one well-constructed ordinary prop and one complete PBR material for study.
4. Add modular architecture, vegetation, secondary character/rig and further cases as justified.
5. Build repeatable documentation, asset inspection, project-specific instruction routing and later gameplay/system reference modules.

## Deferred priority: fix Wolf desktop AI Workspace (open, 2026-10-18)
Return after Patient V2 review. Goal: a persistent **normal window within Wolf**, primary interface for project-scoped and Art Director Codex sessions; new/resume, status, conversation history and working GUI. Future direction: optional side-by-side ChatGPT companion and explicit context handoff, without assuming ChatGPT web conversations are directly API-accessible. Preserve existing services and CLI.

Diagnostics: image `optiplex-studio-desktop:v5`; Wolf shortcut `/home/retro/Desktop/optiplex-ai-workspace.desktop` points at `/usr/bin/python3 /opt/optiplex-studio/wolf_ai_workspace.py`, but that file and directory do not exist in the active container. Searched StudioProjects and relevant local Git history with no recovered copy. Separate GTK3 app source exists in `~/StudioProjects/optiplex-studio/studio/` and corrected v0.3.0 .deb; its AI Workspace is a launcher and session browser rather than native chat. Host `~/.local/bin/studio` CLI is separate. Copied GTK source to persistent Wolf `/home/retro/.local/optiplex-studio` and started GUI successfully, but it appeared full-screen/desktop-obscuring, not the desired interface. Do not call this fixed or overwrite the shortcut blindly. Inspect installation architecture, fix missing entry point or intentionally consolidate apps, implement windowed Codex conversation interface, verify launcher behavior and persistence.

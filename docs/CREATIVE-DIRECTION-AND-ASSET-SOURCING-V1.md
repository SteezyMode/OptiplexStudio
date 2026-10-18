# Creative Direction & Asset Sourcing — v1 milestone
Status: DESIGN / REFERENCE WORKFLOW; not implemented in Wolf UI. Owner approves artistic decisions and source imports. Added 2026-10-18.

## Purpose
Provide a lightweight shared contract between ChatGPT-led creative exploration, human approval, and bounded Codex tasks across character art, environments, props, audio, narrative, game logic, and gameplay. Keep project vision separate from reusable Studio technical knowledge. Do not block Patient V2 testing or the Wolf AI Workspace repair.

## Five-step workflow
1. EXPLORE: Discuss an idea freely and gather examples. Nothing is approved by implication.
2. DEFINE: Create a small board (references + notes) with desired outcomes, anti-references, tradeoffs, and game-specific constraints.
3. SOURCE: Find existing assets/templates/code/animations first, before proposing scratch construction. Show 3-5 candidates with stable URLs and provenance.
4. APPROVE: User chooses use / modify / build / defer. Record license, alternatives considered, design intent, and approval state.
5. PRODUCE & REVIEW: Generate a bounded Codex brief with inputs, paths, deliverables, time/iteration budget, acceptance checks, rollback, and in-engine preview. Save review outcomes and reusable patterns.

## Asset sourcing pipeline
For each need, search the internal catalog first, then verified external catalogs. Initial discovery sources (verify each item and current license): Poly Haven (CC0 models/materials/HDRIs, public API), Kenney (modular game assets), Quaternius (various packs: current QAL with standalone redistribution restriction; old or specific packages may have distinct terms), Blendkit/BlenderKit (CC0 and royalty-free variants); expand after testing. More restricted marketplaces only when the user opts in. Official licenses: https://polyhaven.com/license ; https://kenney.nl/assets ; https://quaternius.com/license.html ; https://www.blendkit.com/docs/licenses/ . Do not assume a source's homepage policy overrides the license bundled with a specific downloaded version.

Candidate card includes: name, exact source URL, creator, exact pack/version, price/access, license evidence and checked date, preview/reference link, formats (GLB/glTF/FBX/Blend), textures/materials, poly/texture budgets if verified, rig/bone and animation data where relevant, commercial-use and attribution constraints, redistribution and repository constraints, artistic fit, estimated conversion effort, provenance confidence, and status (unreviewed/shortlisted/approved/rejected). Unknowns are UNKNOWN, not guessed.

Default ranking: (1) visual & gameplay fit, (2) license clarity, (3) Godot/Blender compatibility, (4) modification cost, (5) performance/asset budget, (6) price. Favor safe, reusable, correctly licensed existing assets rather than repeated low-quality scratch builds. Do not confuse *using a model in a finished game* with *committing distributable source files to a public repository*. Never silently commit third-party proprietary assets, use scraped previews as reusable texture training material, or bulk-download without consent.

## Scope / storage
Per-project files: `<godot-project>/.studio/vision.md`, `references/`, `decisions.md`, `briefs/`, `reviews/` (created only on opt-in; avoid modifying active game unprompted).
Shared Studio knowledge: `~/StudioProjects/.studio/` (existing Art Director material) plus reviewed reusable sourcing/workflow records. Keep source asset and license provenance adjacent to imported material. Text/links first; binaries and images only after explicit selection.

## Cross-disciplinary example
User: 'I want a hospital hallway that quietly changes on the third visit.'
Explore mood -> select architectural references + reject generic rusty corridors -> source reusable doors, lighting, tile/paint materials -> approve board -> write Godot interaction/event design brief (trigger logic, state machine, lighting/audio/props changes) -> Codex builds a reversible test scene -> inspect and record design lessons.

## v1 acceptance test
Run three diverse trials: (1) Patient V2 movement, (2) hospital environment + sourced props/materials, (3) interactive gameplay mechanic. In each: one approved board, >=2 checked source candidates when assets apply, clear brief, reversible test, human review, and retained lesson. Compare cost: Codex turns, elapsed work, number of avoidable reruns, and quality. No new running service or complicated database. UI and automatic import only after this contract proves useful.

## Future GUI
Merge with Wolf AI Workspace repair rather than build a disconnected application. Normal non-fullscreen window; project selector; reference board; sourcing candidate cards; explicit approvals; Codex sessions; live job status; review queue. ChatGPT conversations are not automatically available to Codex or API apps: shared files are the source of truth; API-based chat requires separate evaluation and billing decisions.

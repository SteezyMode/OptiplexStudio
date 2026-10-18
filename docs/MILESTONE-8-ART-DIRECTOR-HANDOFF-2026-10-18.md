# Milestone 8 handoff — Studio Art Director (2026-10-18)

## Purpose and non-negotiable direction

OptiPlex Studio is an AI-assisted, end-to-end game-development workspace using Codex, Godot, Blender, and other specialized tools. **Milestone 8 is a permanent, portable, curated art-direction and asset-production knowledge base**, not a one-off improvement to one zombie. Its purpose is to improve artistic quality across projects, Codex sessions, clean installations, and machines. This is persistent documentation, reusable assets, benchmarks, and human-approved critiques—not neural-network fine-tuning.

The user and assistant **jointly curate** the reference set; Codex builds the infrastructure, performs asset inspections and production, and follows the approved standards. Do **not** autonomously fill the library with generic horror references. Avoid mascot-horror/FNAF-type imagery, generic indie horror, visual clichés, gratuitous mutation, or indiscriminate PS1/VHS filters. Avoid narrowly defining the global library around hospital/body horror. Focus on *soul*, deliberate form, visual hierarchy, convincing anatomy, characterful motion, materials, and grounded environments. Keep the global library style-agnostic enough to support future games.

**Threshold character target:** closer to an original *Resident Evil 2 (1998)* shambling zombie: clearly formerly human, recognizable anatomy, intentional distortion/decay and clothing wear, evocative face, irregular weighty gait. Low polygon counts are acceptable; crude assembled primitives are not. References teach design principles, never permission to copy protected character designs.

## Current proven technical state

- Milestone 6 **Threshold** playable first-person horror prototype: room/corridor, door/key/objective, flashlight, enemy AI, audio, title/death/victory states. It has been manually launched and played, with primitive graphics.
- Milestone 7 upgraded the patient through Blender MCP: Codex reported a Blender source, GLB, 18-bone rig and idle/walk animations, working integration, `studio-validate threshold` pass and 17 automated checks. User confirmed game runs and new patient is better but still **very primitive** and artistically weak. Sound was impressive out of the gate.
- Existing patient locations:
  - `~/StudioProjects/Godot/threshold/assets/characters/patient/source/patient.blend`
  - `~/StudioProjects/Godot/threshold/assets/characters/patient/patient.glb`
- Host-side Godot and Blender are **Flatpak applications inside the Wolf Studio desktop container**, not host binaries. Godot: `flatpak run org.godotengine.Godot`; Blender: `flatpak run org.blender.Blender`. Blender background Python executed successfully, and headless Godot validation succeeded outside Codex.
- Blender MCP server listens on container port 9876 **when Blender GUI is open**. A Python TCP check showed CONNECTED; Codex successfully called `blender.get_scene_info`, reporting default Cube, Light, Camera, once launcher approval changed to `--ask-for-approval on-request`.
- Codex project launcher: `~/.local/bin/studio-codex-project threshold`, sandbox `workspace-write`, approval `on-request` (changed during the conversation). It cannot access Docker from that sandbox directly. Preserve isolation from unrelated services; do not broadly grant Docker privileges.
- Godot editor can be opened using `studio-open-project threshold` (previously created host wrapper); Godot project manager's import dialog silently closed, so launch by Flatpak `--editor --path /projects/Godot/threshold`.
- Preference: **ONE terminal command at a time**, short response, paste output. User typically uses MacBook SSH to host; do not ask them to paste shell commands in Codex by accident.

## Milestone 8 on-disk structure already created

Base: `~/StudioProjects/.studio/art-director/`

- `standards/`, `workflows/`, `evaluations/`
- `references/characters/{anatomy,faces,clothing,horror}/`
- `references/environments/{architecture,interiors,lighting}/`, `references/props/`
- `asset-library/{characters,animations,materials,props,architecture}/`
- `manifests/`, `comparisons/`, `incoming/`

This is **not yet a populated/committed library**. In particular, an earlier long command to create `catalog.json` was **NOT run**; user deliberately paused it pending a better asset-aware schema. Do not claim that catalog exists without checking.

## Human-approved visual influence list (10)

1. Resident Evil 2 (1998), ordinary zombies — human readability, heavy walk, face, damaged clothing. Primary Threshold character baseline.
2. Silent Hill 2 (2001), Lying Figure — strange form and restricted movement.
3. The Suffering (2004), Slayer — purposeful readable silhouette.
4. Dead Space (2008), Slasher — coherent transformed anatomy.
5. Lucio Fulci, Zombie (1979) — layered decay and textured deterioration.
6. Tom Savini, Day of the Dead (1985) — practical makeup and individuated facial damage.
7. Resident Evil (1996), Spencer Mansion — deliberate rooms, architectural detail and composition.
8. Jacob's Ladder (1990), hospital — oppressive institutional space and light.
9. The Thing (1982), practical effects — material continuity and transformation.
10. Alien (1979), H. R. Giger — formal unity, surface rhythm, selective biomechanical shapes.

Five additional **candidates, not yet explicitly approved**: Event Horizon (1997; user called it “deep horizon,” assistant inferred Event Horizon), The Evil Dead (1981), Evil Dead II (1987), The Texas Chain Saw Massacre (1974), Puppet Combo—especially Murder House. No need to force all references onto each game.

## Real asset reference: first acquisition (Quaternius)

Goal: curate a small licensed *technical* asset-reference library (not necessarily style references): **one humanoid + walk animation, one prop, one full PBR material**, then expand selectively. Analyze actual topology, silhouette, weights, textures, rig, animation, and construction, comparing them with Threshold patient's shortcomings. Do not substitute Quaternius character wholesale for the horror patient.

Source: Quaternius “Ultimate Modular Men — Feb 2022” archive, downloaded via creator's Google Drive, uploaded to host:
`~/StudioProjects/.studio/art-director/incoming/Ultimate Modular Men- Feb 2022-20261018T053129Z-1-001.zip`
User confirmed `scp` transfer succeeded (52 MB).
Archive was listed and license examined **inside** it: `License.txt` declares CC0 1.0 Universal with attribution to @Quaternius, public domain dedication URL `https://creativecommons.org/publicdomain/zero/1.0/`. Official creator page: `https://quaternius.com/packs/ultimatemodularcharacters.html`.

The archive contains editable Worker files, including:
- `Humanoid Rig/Individual Characters/Blend/Worker.blend`
- `Individual Characters/glTF/Worker.gltf`
- `Separate Skeletal Meshes and Animations/Animations.fbx`
- `Separate Skeletal Meshes and Animations/Worker/Worker_{Head,Body,Legs,Feet}.fbx`
- `License.txt`, `How To Use.txt`
- Other characters and rigged variants retained in the original ZIP.

**Exact latest action:** User just ran a Python `zipfile` command extracting a curated subset into:
`~/StudioProjects/.studio/art-director/asset-library/characters/quaternius-worker/`
using basename outputs for those selected files. **The extraction command's terminal output has NOT been seen**, so verify files actually exist and check for collisions/dependencies before assuming success. In particular `Worker.gltf` may require an external `.bin` file or textures absent from this subset; inspect its buffer/image URIs and original archive before considering it importable. The whole original ZIP remains in `incoming/`. A safer downstream approach may preserve original paths or retain associated binary/image dependencies.

## Suggested next steps, ONE command per turn

1. **Verify actual extraction:** list files/sizes in `asset-library/characters/quaternius-worker`, compare against expected curated subset and inspect `.gltf` dependencies. No re-download unless needed.
2. Record source, creator, URL, exact license, checksums, formats, dependencies, asset role, approved/candidate status, and a technical analysis plan in a **versioned manifest**. Visual influences and asset files are different types of entries. Preserve originals and rights metadata. Avoid making a huge JSON catalog manually before schema is decided.
3. Test Quaternius Worker.blend in Blender and compare to Threshold patient: mesh topology, shape, materials, rig and weight painting, motion and knee/shoulder deformations. Generate controlled multi-angle renders and/or inspection reports; user reviews actual visuals rather than Codex self-approving quality.
4. Curate one high-quality prop + one complete PBR material from Poly Haven (CC0; `https://polyhaven.com/`), verifying files and licenses, then repeat evaluation.
5. Create standards/docs and per-project `docs/ART_DIRECTION.md`; a shared `AGENTS.md`/Codex startup integration should make relevant art standards/lessons available across *all* Studio projects. Note Codex workspace-write may block shared `.studio` writes; design a narrowly scoped workflow rather than disabling host security.
6. Store manifests, metadata, standards, evals and small approved previews in Git; maintain larger binary source assets locally with checksums + separate backups. A public repo should not automatically include large files, copyrighted film stills, or private machine credentials. Configure portable bootstrap/recovery and validate reinstall procedure eventually.

## Tracking deferred

- VueTorrent on the existing qBittorrent container: user wants persistent login from multiple computers and browser restarts. Defer until after Studio work. The WebUI `SID` cookie is session-only; port 8085 accessible over Tailscale. Prior Docker port bindings returned `{}`; no final auth solution implemented. Don't suggest disabling auth globally.
- Wolf briefly had connectivity symptoms during upload; subsequently working on alternate network, no restart needed.

## Guidance for the next ChatGPT conversation

Continue **Milestone 8 / Quaternius Worker verification**, not a new game or more generic prompts. User wants focused, curated references with actual model/material files and gradual measurable learning, and is sensitive to scope drift. The **very next command** should inspect the contents extracted to `.../quaternius-worker/`, then evaluate glTF dependencies. Use one shell command at a time. Preserve Threshold and all existing services. Do not treat an assistant-produced description as proof of file creation or a completed review.

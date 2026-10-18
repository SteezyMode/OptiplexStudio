# Reference Batch 01 — fast staging and technical intake
**Status:** source shortlist + deterministic inventory runner in repo, not installed on the OptiPlex by committing. The gameplay-test V2 is not automatically changed.

This batch spans 4 character/tooling/animation sources, the already-staged Blender Human Base Mesh, and 5 Poly Haven candidate assets. See `catalogs/threshold-reference-batch-01.json` for verified source pages, license evidence and intended use.

## Current proven downloads
`incoming/quaternius-ual2-standard.zip` is locally present as of 2026-10-18, passed ZIP integrity, SHA256 `ec0e40d6d78fe9aaad59e322f40865a8675c22f0745e291622e54520391a9217`. Don't redownload it unless integrity changed. `incoming/human-base-meshes-v1.4.1.zip` exists with license questions around embedded Rain Rig; never blanket-publish.

## Stage 1: one local source inventory, no Codex tokens
After updating the existing OptiplexStudio repo clone (review local changes; no force reset), run:

```bash
python3 tools/inspect_reference_batch.py --workspace ~/StudioProjects/.studio/art-director --online
```

Outputs to `~/StudioProjects/.studio/art-director/reference-batches/threshold-patient-reference-batch-01/`: `source-inventory.json` and `INVENTORY.md`. Only downloads optional Poly Haven **API metadata**; no asset binaries, and no changes to Threshold. With poor network, omit `--online`. Archive reads are bounded and do not extract third-party ZIPs.

## Stage 2: one bounded Codex reference-preparation job
Operate in scoped `~/.local/bin/studio-codex-art` / tmux. Read the inventory and report 1) exactly which UAL2 clips exist, 2) which zombie packs are downloadable without sign-in, 3) whether MPFB 2.0.18 can safely be installed in persistent Wolf environment later, and 4) exact 1K PBR maps and scene references to stage. Can stage freely licensed source assets in `incoming/` after checking pack-specific licenses and hashes. **Do not** install add-ons in the active Wolf image, change active Godot projects, add to public Git, or start a new full character build. Stop if authentication/payment/version mismatch is encountered, and record URLs.

## Stage 3: production proofs
- Motion: one retargeted walking clip, compare to V2 TEMP_walk with identical camera and lighting, and review in game.
- Anatomy: MPFB-based independent hand/face prototype, **not a replacement**; compare thumbnails and skinning under motion. Only promote after approval.
- Materials: create an optional lower-cost 1K/2K PBR swatch sheet of skin procedural masks, cloth roughness/normal, and aged/discolored hospital materials; do not label patterned or terry texture as a hospital gown by fiat. Do not substitute color maps from external art in an incompatible aesthetic.
- Behavior: separate finite-state-machine spec/test for compromised patient; no enemy-controller rewrite until movement and character designs are approved.

## Default review questions
Did it improve appearance, motion, technical correctness or workflow speed? What did we reuse? What failed? What would be reusable for environments, props and other genres? Record before/after screenshots and timings.

Official source evidence:
- https://extensions.blender.org/add-ons/mpfb/ (MPFB 2.0.18)
- https://static.makehumancommunity.org/about/license.html (core CC0 assets)
- https://quaternius.com/packs/animatedzombie.html ; https://quaternius.com/packs/zombieapocalypsekit.html (CC0 packs)
- https://quaternius.itch.io/universal-animation-library-2 (current CC0 Standard)
- https://polyhaven.com/our-api (free API) ; https://polyhaven.com/license (CC0)

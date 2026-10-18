# OptiPlex Studio — free motion sourcing and auditions (2026-10-18)

**Purpose:** genre-neutral, reusable source discovery and Blender-to-Godot animation production; *Threshold* is a pilot. No acquisitions, logins, account creation or uploads are authorized by this document. Do not treat link listings as checked clip quality or verified downloadable binaries.

## Trial observation
The local Patient V3 audition viewer successfully imported 28 named source clips; human review: a few convincing, some generic/cringey, some merely okay. Imported rigged characters are sample source rigs, NOT approved character designs. Desired Threshold tone is grounded and genuinely unnerving, less over-acted "PG zombie." Need more visual variety, but not uncontrolled pack accumulation.

## Ranked sources (free; verify exact downloaded terms/file structure before import)

| Priority | Source | What is verified | Caveat |
| --- | --- | --- | --- |
| **P1** | [Rokoko — 12 free zombie/halloween animations](https://www.rokoko.com/resources/rokoko-mocap-12-free-zombie-animations) | Publisher confirms 12 full-body clips including fingers; FBX on Mixamo skeleton, 30fps; permitted personal/commercial game projects. | Form asks name/email; actual FBXs and performance strength not yet viewed. Do **not** claim it contains specific turns/grabs. |
| **P1** | [Rokoko — 10 free everyday idle animations](https://www.rokoko.com/resources/rokoko-mocap-10-free-everyday-idle-animations) | Publisher confirms full-body FBX, Mixamo skeleton, 30fps, commercial use. | Human baseline clips; tone must be directed later. Form required. |
| P2 gap-fill | [Adobe Mixamo](https://www.mixamo.com/) / [Adobe official FAQ](https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html) | Free Adobe ID; game commercial use royalty-free; large humanoid-motion library. | Exact useful zombie/turn/reach clips and availability require account preview. Raw animation/character redistribution in asset packages prohibited per [Adobe licensing FAQ](https://community.adobe.com/questions-696/mixamo-faq-licensing-royalties-ownership-eula-and-tos-589400). Keep only locally, not public repo or bundled OptiPlex Studio distribution. |
| P2 broad | [Rokoko — 263 free motion assets](https://www.rokoko.com/resources/download-263-rokoko-motion-capture-assets) | Publisher confirms free commercial-use FBX pack with Mixamo/UE/HumanIK skeleton variants. | Do not download all 263 solely because they're free; inventory and select by gaps. Form required. |
| P3 research | [CMU Mocap Database](https://mocap.cs.cmu.edu/) / [CMU README](https://github.com/una-dinosauria/cmu-mocap/blob/master/READMEFIRST.txt) | University motion database explicitly says free for all uses; commercial allowed. | More format conversion work (ASF/AMC/BVH etc); not a turnkey zombie pack. |
| Already local | Quaternius UAL2; Animated Zombie/Apocalypse Kit | Existing local source assets and inventory; reuse already validated importer and source rig viewing. | Several candidates stylistically too generic; source names don't establish good acting. |

## Community findings (anecdotal, not technical guarantees)
- [r/godot March 2025 Quaternius animation release](https://www.reddit.com/r/godot/comments/1jg4wtx/quaternius_just_dropped_a_high_quality_free_3d/) welcomed quality/value, repeatedly referenced Mixamo as alternative.
- [r/gamedev September 2026 animation workflow](https://www.reddit.com/r/gamedev/comments/1wmktse/how_do_you_guys_handle_3d_animations/) users note stock Mixamo works for ordinary movements but not automatically for expressive multi-actor/action sequences; mocap cleanup can be costly.
- [r/godot Feb 2025 Mixamo deformation thread](https://www.reddit.com/r/godot/comments/1j00i38) provides example of bad limb twisting due to rig mismatch; reinforces that imported success != retarget success.
- [r/godot May 2026 reusable viewer thread](https://www.reddit.com/r/godot/comments/1t2pua2/i_created_an_animation_viewer_and_a_godot_plugin/) describes reusable animation browsers and reimport workflows; relevance to our own viewer.

## Next approved-source procedure (no Codex work until user provides download)
1. Human submits publisher form and downloads P1 Rokoko 12 zombie clips (optional 10 idles). No silent account access, no new cost.
2. Save original unmodified ZIP and publisher/source metadata in a **local-only** art-director source directory, not public Git.
3. Before invoking Codex, use a deterministic local inspector: list files, counts, clip names, durations, skeleton bone mappings, root translation and archive safety; exact package license, format and hashes. This should become a reusable Studio script.
4. Add selected clips to existing V3 audition **as a separately labeled source group**, not replace or break local 28 and not load the full source catalog into every project.
5. Human rates each as **KEEP / EDIT / REJECT**, with observations about believable movement, zombie tone, foot contact, turns/grab suitability, relative visual quality. Avoid "R-rated" as a technical property of a pack.
6. Only then choose 3–6 high-value clips and build **one** cohesive scary approach/reach performance. Use skeleton-native audition before retarget, and original artwork/characters only after motion quality passes.

## Time/resource/licensing discipline
Start with P1 rather than 263 assets. Avoid simultaneous heavy Blender/Godot builds, autonomous downloads, GPU renders, and redundant Codex research. Favor GPT-6 Luna Medium for ingest, simple viewer extension and scripting; escalate to Sol for bounded rig issues only. For future general-purpose **commercial Studio product**, bundled third-party raw animations may need independent redistribution rights; do not confuse commercial game-use permission with asset-library redistribution permission.

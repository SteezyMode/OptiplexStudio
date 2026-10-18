# Threshold Patient V2.2 — Horror art direction before further production
Date: 2026-10-18
Status: **PROPOSED creative brief — references and new designs require user review. No production changes approved by this document.**

## Human playtest verdict from V2.1
The user reviewed the isolated `repair-v2.1` Godot comparison:
- Raised shoulders: **fixed**, a meaningful improvement.
- Feet: **better** but remain imperfect.
- Hands: **good**, major V2-over-V1 win; preserve mesh, weights, pose and visual treatment.
- Overall walk: substantially improved from the original.
- Face: **not yet good**.
- Horror effect: **not scary**; character looks more like a sad old man shambling forward. The user sees this as a useful, moderately successful human baseline, not a failed production attempt.
- Do not promote into Threshold or change V1, original V2 r06, Trial 01 or V2.1 comparison without a separate approval.

## The new bottleneck
The bottleneck is now **art direction and character expressiveness**, not basic Godot playback or importing more animation libraries. Extra generic instructions like 'make it scarier' or unbounded procedural remeshing are unlikely to help. Use **specific, curated references and reviewed production techniques**—not actual model weight training.

Preserve the familiar, human hospital-patient baseline. The direction is **restrained, uncanny, physically compromised former human**, inspired by the *emotional effect* of classic late-1990s survival-horror zombies, not copied character designs. Avoid generic spiky/huge-mouth monsters, cartoon aggression, loud visual gore, exaggerated comic-book anatomy, and default 'shuffling grandpa' performance.

## Distinct artistic workstreams

### 1. Character face and expression (first production focus)
- Collect a *small*, human-approved reference board for real facial anatomy and the desired uncanny expression. Store labels, observations, provenance and permissions; do **not** bulk-scrape or auto-import unlicensed images.
- Inspect existing face topology, eyes/eyelids, brow and mouth; distinguish ineffective materials from genuine mesh/rig faults.
- Candidate cues to propose (not automatically implement): lost or misfocused gaze; nonmatching eyelids; slack but subtly asymmetric mouth/jaw; skin tone variation; a mild, unsettling facial tension that clashes with otherwise passive body language.
- Keep face readable in neutral lighting and several camera angles, not only a close frontal shot.

### 2. Material and patient identity
- Preserve recognizable human identity and original hospital-patient styling; make gown/skin feel intentional through PBR surface response, fabric weight, wrinkles, dampness/soil and period/context cues where appropriate.
- Use verified licensed reference sources (e.g. approved Poly Haven materials) as technical baselines; do not assume that a CC0 fabric is automatically a good design choice.
- Prefer a few high-impact, human-reviewable details over broad procedural texture noise.

### 3. Performance and fear
- Keep improved V2.1 retarget and shoulders; don't undo the hand anatomy.
- Explore subtle head/eye offsets, irregular pauses, delayed orientation, uneven step timing, and unexpected stillness as **proposals**, not another general retarget job.
- Fix gross foot geometry/weights before the final animation review, but don't spend endless passes chasing subpixel foot contact while character direction is unresolved.
- Separate animation mechanics (planted feet) from emotional acting (uneasy or wrong presence).

### 4. Presentation versus intrinsic design
- A/B in a **consistent neutral stage** to judge whether the face/silhouette/model itself became more unsettling.
- Separately render a **controlled horror-context stage** with plausible hospital lighting, camera distance, partial occlusion and environmental cues. Lighting/sound should enhance, not obscure, design.
- Report each condition separately, so presentation effects don't masquerade as improved character modeling.

## Proposed bounded next task: reference + treatment board, NO mesh changes
Have Art Director use currently approved influences and its existing source catalog first, inspect existing V2.1 front/side/three-quarter captures, and author:
1. Brief **Current vs intended** diagnosis: exactly why the patient reads as elderly/sad instead of unnerving. Distinguish observations in rendered captures from speculative design theories.
2. Three specific, *original* treatment directions grounded in existing model: (A) wrong gaze and subtle facial asymmetry; (B) illness/material and hospital realism; (C) behavioral eeriness/idle acting. They may combine after review. State scope, implementation costs/risks and which improvements can remain untouched.
3. A 3–6 item curated source shortlist (human anatomy, period hospital clothing/material, and motion/performance examples), with URLs/license/provenance and **no new download or auto-use without approval**. Copyrighted entertainment stills may be discussed as mood inspiration, not duplicated or committed as game art.
4. A minimal **V2.2 first-pass plan**: one face/material treatment only in an isolated copy of V2.1, preserved hands and shoulder rig; consistent neutral renders + separate atmospheric review; optionally include a small suggested movement-expression adjustment only after signoff.
5. Acceptance rubric: face reads as wrong/unsettling while visibly human, not merely decrepit; improved look from front, side, 3/4 and mid-distance; no sacrifice of hands/shoulder improvements; no generic monster silhouette; foot defects tracked separately; output genuinely readable at low display/streaming resolution.

Wait for user approval after the board **before generating models, installing new tools, changing game files, or launching an unbounded overnight job**.

## Reusable Studio lesson
A successful 'production knowledge' module is not a bag of downloaded assets or fake fine-tuning claims. It is a compact, reviewable packet of **visual intentions + anti-references + verified reusable sources + known-good procedural methods + screenshots of before/after + human scoring**. Reuse the method across future games; keep Threshold-specific horror choices in its project context.

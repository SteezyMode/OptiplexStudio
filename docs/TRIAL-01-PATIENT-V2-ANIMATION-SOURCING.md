# Trial 01 — Threshold Patient V2 animation sourcing
Status: READY FOR USER APPROVAL / NOT IMPORTED (2026-10-18)
Existing work: Codex is separately integrating V2 into a reversible Threshold test. Do not interfere, assume completion, overwrite scenes, or start a competing Codex task.

## Goal
Determine whether existing professionally animated humanoid motion can drive Patient V2 r06 (44-bone rig) more convincingly and efficiently than wholly procedural animation. The intended movement is an impaired hospital patient, not a generic aggressive zombie: uneasy balance, labored gait, slow head/body timing, grounded feet, deliberate reaching. This is a hypothesis, not yet an approved artistic decision.

## Sourcing shortlist (verified public descriptions; license must be reconfirmed on actual downloaded files)
1. PRIORITY: Quaternius Universal Animation Library 2. https://quaternius.itch.io/universal-animation-library-2 — 130+ humanoid animations, expressly includes zombie locomotion; Godot-compatible formats, standard no-cost ZIP 17 MB. Its asset page expressly states CC0, commercial use; root-motion and no-root-motion variants; current standard may contain only some animations. Preview at https://quaternius.com/animviewer.html . Source .blend edition is paid; not necessary for initial test. Check exact archive contents before asserting a specific zombie clip is included.
2. FALLBACK: Quaternius Universal Animation Library (first pack). https://quaternius.itch.io/universal-animation-library — 120+ humanoid animations including locomotion, walking and death, Godot-compatible, standard no-cost version. Pack page states CC0. Does not expressly promise zombie locomotion in the free edition.
3. COMPARISON ONLY: Adobe Mixamo. https://www.mixamo.com/ ; official rights https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html — free with Adobe ID and permitted in games; not CC0, may have redistribution limitations; account/interactive export required. Source check before download. No credential automation.

## Approval gates
A. User confirms the motion direction and authorizes downloading a named pack. No silent downloads, payment, login, or attribution/license assumptions.
B. Verify exact package version and bundled license; record URL, date, SHA256, internal file/clip inventory, formats, root-motion variant and size. Store third-party sources outside production Godot scenes until tested; exclude from public git unless permitted.
C. Inspect V2 armature hierarchy/rest pose/axis and animation skeleton; map using Godot SkeletonProfileHumanoid/BoneMap or Blender retargeting where appropriate. Do not assume 44-bone direct compatibility.
D. Build isolated locomotion test with ONE walk (prefer zombie/impaired), one idle if available, and one reaching animation if available. Distinguish authored, retargeted and diagnostic clips. Check thumbs/wrists/palms, knees, feet, gown clearance, scale, axes, foot sliding, root drift, and animation transition behavior.
E. Present simple Wolf/Godot instructions, screenshots or captures, technical findings and reusability notes. No replacement of existing patient or main scene.
F. Stop after one candidate library and one test pass, request approval before polishing.

## Evaluation
Rate visual fit, rig compatibility, import complexity, runtime performance, foot contact, skin/gown deformations, and whether this reduced Codex iterations versus procedural authoring. If no suitable clip in free package, document the gap and request a different source instead of improvising an uncertain substitute.

## Next action
When the existing V2 Godot integration Codex task finishes, inspect its test scene and report. Obtain explicit approval for free Quaternius UAL2 Standard pack and selected motion style. Then issue a scoped Codex task, not a free-form redo.

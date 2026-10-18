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

## First in-engine human review — 2026-10-18
User launched `res://scenes/tests/patient_v2_test.tscn` in Threshold via the existing Wolf desktop and directly observed V1 beside V2. Findings: **V2 looks dramatically better than V1 visually**; hands are still not convincing; animation is stiff; character/enemy logic and movement behavior did not materially improve. These are qualitative human observations, not new automated test results.

Interpretation: V2 was deliberately deployed with the unchanged V1 AI/controller and TEMP_idle / TEMP_walk / TEMP_reach diagnostic cycles. The lack of improved behavior/animation is expected, not evidence that the rig or model pipeline failed. Keep the V2 review source and V1 unchanged; V2 is a **visual baseline**, not a production-approved model.

Next step and acceptance gates:
1. Test ONE externally sourced humanoid motion set (prefer Quaternius UAL2 Standard, after verifying exact package contents and license). First obtain user approval for actual download/import if not already granted.
2. Preview and retarget ONE suitable compromised/zombie walk to the V2 44-bone skeleton in a reversible test copy. Check hand/wrist orientation, foot sliding, hips/root travel, skin and gown contact.
3. Compare human-review video/screen captures against the TEMP_walk baseline before spending credits on further tweaks. Cap this first pass at one sourcing/import/retarget test; stop and report failures instead of recursive autonomous remodeling.
4. Make a separate AI-behavior brief **after** locomotion quality is evaluated; do not blend the two experiments.
5. Track elapsed Codex work and revision count so the Studio creative-direction pilot has cost/quality evidence.

## Trial 01 completed — second in-engine human review (2026-10-18)
**Current real status supersedes the stale opening "READY" status:** Codex completed the scoped `Zombie_Walk_Fwd_Loop` retarget experiment in an isolated Godot project. Test scene: `res://scenes/walk_comparison.tscn`; source and report: `~/StudioProjects/.studio/art-director/comparisons/patient-v2/animation-trial-01/REPORT.md`; capture gallery alongside report. User launched the comparison through Wolf and reviewed it in motion.

**Human findings:** the retargeted movement is **better** than the procedural original, but shoulders sit **unrealistically high** and feet remain **badly distorted**; overall appearance still amateur. Visual assessment is not approval to promote the animation into Threshold or replace V2.

**Diagnostic hypothesis, not confirmed:** inspect mismatched bind/rest poses and clavicle/upper-arm rotation offsets for shoulder shrug; inspect target foot/ankle/toe transforms AND underlying foot mesh proportions, topology and weight painting for foot deformation. Compare original vs retarget and static rest pose before choosing a fix.

**Bounded production Trial 02 (Patient V2.1 anatomical rig correction):**
1. Read `animation-trial-01/REPORT.md` and latest capture gallery, then inspect both animation rigs and Patient V2's 44-bone skeleton. Check whether shoulder lift and foot breakage appear in rest pose, original procedural walk, retargeted walk, or multiple conditions; distinguish animation mapping error from geometry/weight failure.
2. Make a reversible **test-only** working copy of the retarget setup and V2 mesh/rig, retaining V1, V2 r06, separate trial 01 and normal Threshold startup unchanged. Do not silently promote edits to the real game.
3. Correct clavicle/upper-arm rest offsets and bone rotations if those cause the shrug; target grounded shoulders with natural shoulder elevation during gait, not locked joints. Correct foot mesh/proportions/ankle-toe placement and weight-painting only where deformation actually requires it; avoid masking errors with scale or a pose that only looks good in one frame.
4. Compare identical front/side/back views at bind/rest pose and multiple walk keyframes, including planted and lifted foot. Keep gait timing and improvements from Trial 01. Show separate before/after screenshots and short test video. Flag remaining structural issues rather than overpolishing.
5. Run Blender/Godot validation; supply exact Wolf launch path and a concise report, including what is *rig*, *mesh*, *weights*, or *animation*. Human approves next steps. Keep Codex effort bounded to a first evidence-driven pass; no new zombie pack or large generation task.

**After Trial 02:** review corrected shoulders/feet and then pursue hands/face and PBR skin/gown materials, with separate AI-behavior work after locomotion is fit for purpose.

**Reboot note:** workstation froze and rebooted later the same evening; prior tmux process cannot survive reboot. Review saved Codex conversations and files; do not assume a task is still running because an old terminal title exists.

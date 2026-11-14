# Control room, Gagoo rig and learning prototype

Design decisions confirmed by the owner on **15 November 2026**:

- Alien X is an original project character. Use the supplied green chibi references: oversized head, two round antenna tips, very large dark almond eyes and a tiny body. Render it as broad low-poly forms with strong outlines.
- Gagoo's secondary motion should bounce visibly and feel soft and humorous while keeping the character readable. Limbs, neck, ears and eyes stay attached and have limited motion.
- The learning interaction after choosing **test** is **multiple choice with answers**, not flashcards.
- On mobile, the upper half of the viewport is the game screen and the lower half contains controls, following the already approved handheld-console layout.

## Current scope

`web/control-room.html` is a separate, runnable design prototype. The public Learn route remains blank. The prototype uses the same Gagoo model as the home page, an original low-poly control room, an oblique top-down camera, a tablet interaction, Alien X dialogue and a transparent quiz overlay.

The tablet interaction visibly moves the tablet into Gagoo's hand before opening its blank screen. Alien X's dialogue advances to a test request; choosing the option opens the quiz without replacing the room background. Wrong and correct answers receive text feedback. Leaving an overlay returns control to the room.

The prototype does not save quiz results to an account, send analytics, or claim a validated educational assessment. It does not operate SPHEREx or display live spacecraft telemetry.

## Visual direction and references

- Camera and readable room composition: [Stardew Valley's official media](https://www.stardewvalley.net/media/). The prototype is a 3D room, with its own geometry and palette.
- Dialogue rhythm and bold graphic panels: [Persona 5 Royal's official site](https://persona.atlus.com/p5r/). Angular panels, name tags and high contrast guide the new interface; game artwork is not bundled.
- Character identity: the user's Alien X references supplied in this conversation and the existing Gagoo design in [GAGOO_BRIEF.md](design/GAGOO_BRIEF.md).
- Rig implementation reference: [Three.js Bone](https://threejs.org/docs/pages/Bone.html) and [SkinnedMesh](https://threejs.org/docs/pages/SkinnedMesh.html). The runtime's pinned local Three.js version is authoritative for implementation.
- Quiz science: [JPL mission overview](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/) and the sources linked with the answers. Pre-launch schedules in that press kit are not used as actual historical dates.

## Acceptance criteria

1. Dragging Gagoo drives independently delayed joint motion; release and window impact settle without detached parts, unstable transforms or helmet penetration.
2. The entrance begins from the visible Earth, satellite and Gagoo composition. The camera withdraws through a window; Gagoo fills most of the opening on contact, then recoils backward. Cancel restores the home scene; skip and reduced motion remain supported.
3. Gagoo can reach both room interactions with keyboard, touch controls or accessible station controls. Walls and consoles prevent walking through solid geometry.
4. Tablet pickup is visible, its display is blank, and closing it returns control without stuck input.
5. Alien X dialogue reaches the test option; the quiz shows correct/incorrect feedback, explanation, retry and progression.
6. Mobile controls stay in their own half of the viewport in portrait and landscape. Touch release/cancellation stops movement, and overlays stop background movement.
7. Both Vietnamese and English remain usable. Keyboard focus, readable feedback, reduced motion, WebGL failure and resizing are checked.

## Run and review

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m http.server 8000 --directory web
```

Open `http://localhost:8000/control-room.html?lang=vi` or `?lang=en`. A local HTTP server is required for JavaScript modules; double-clicking the file with a `file:` URL is not the supported launch method.

```powershell
.\.venv\Scripts\python.exe -m scripts.browser_control_room
.\.venv\Scripts\python.exe -m scripts.browser_gagoo
.\.venv\Scripts\python.exe -m scripts.check_gagoo_entrance
```

Review receipts and screenshots are written under ignored `data/raw/`. Final rig exports and exact validation results should be read with the delivery receipt; the acceptance list above describes requirements, not a claim that every check has already passed.

## Verification recorded on 15 November 2026

- The rig contains 19 bones and 46 meshes, totaling 2,004 triangles. Blender and GLB retain normalized rigid weights, named joints and one four-second rebound clip. The round-trip check compares every bone over all 121 sampled animation frames, not only the rest pose.
- The cinema suite covers 16 cases, including actual desktop/mobile home continuity, backward recoil, contact sizing, cancellation, reentry, delayed imports, context loss and reduced motion. The underlying home DOM is retained beneath a transparent 3D cabin/actor layer; this is a staged camera illusion rather than one shared orbital physics world.
- Control-room checks cover desktop, mobile widths of 390 and 320 pixels, a landscape touch viewport and unavailable WebGL. They exercise actual movement, touchscreen hold/cancel, tablet pickup, both dialogue stages, wrong-answer retry, both correct answers, language changes and return to the room. No API writes occur in these checks.
- Local Python tests: 659 run, eight environment-dependent MongoDB integration tests skipped; CI must exercise those against its disposable MongoDB replica set before merge. All 16 JavaScript suites pass locally.

The final Blender handoff is under `data/raw/gagoo-rig-assets/`; use `glb-roundtrip.json` and `blender-handoff.json` there to check geometry, source hashes and export consistency. Prototype gameplay, learning effectiveness and real-device GPU performance are not validated by automated browser tests. The tablet intentionally has no content; the quiz has two demonstration questions and no persistent learner record.

## Next design milestone

Use this room to test one complete short learning activity with a beginner: approach Alien X, read a concept, answer a question, inspect the explanation and return to exploration. Check that learners can find the interaction and explain the answer without assistance before expanding the room or adding rewards.

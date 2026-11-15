# Control room, Gagoo rig and learning prototype

Design decisions confirmed by the owner on **15 November 2026**:

- Alien X is an original project character. Use the supplied green chibi references: oversized head, two round antenna tips, very large dark almond eyes and a tiny body. Render it as broad low-poly forms with strong outlines.
- Gagoo's secondary motion should bounce visibly and feel soft and humorous while keeping the character readable. Limbs, neck, ears and eyes stay attached and have limited motion.
- The current entrance sticks Gagoo to the glass for 650 milliseconds, then slides it right until it is fully out of view before the one-second blinds transition. This replaces the earlier backward recoil.
- The room uses bold ink/cel shading, runtime shadows and six floating props that respond to collisions. The contextual E prompt appears only within reach of an interaction.
- The learning interaction after choosing **test** is **multiple choice with answers**, not flashcards.
- On mobile, the upper half of the viewport is the game screen and the lower half contains controls, following the already approved handheld-console layout.

## Current scope

`web/control-room.html` is a separate, runnable design prototype. The public Learn route remains blank. The prototype uses the same Gagoo model as the home page, an original low-poly bus-shaped spaceship with six connected rooms, an oblique top-down camera, a tablet interaction, Alien X dialogue and a transparent quiz overlay.

The playable single-deck layout runs from cockpit through sleeping room and kitchen to the living quarter. The living quarter branches directly to the fuel/generator room and the spacewalk airlock. Shared door openings and collision walls derive from `web/ship-layout.js`. There is one external spacewalk hatch; the rest of the outer hull is mirrored. The exterior and spacecraft systems are fictional game geometry, not an engineering or pressure-safety model.

Gameplay shows only the current room. Crossing a threshold hides it and shows a short connecting chamber while the destination's furniture module loads and its meshes are built. The destination becomes visible and its door opens once that work succeeds. Entering it hides the chamber; retreat restores the previous room. Failed loads keep the destination closed and offer retry or retreat. Loaded rooms are cached for the scene lifetime. This is actual module/mesh loading, not an artificial progress timer; it does not stream a large external 3D asset library.

The camera frames the active room on desktop and mobile, centering on the connecting chamber during travel. Walls that would hide the character lower visually while retaining collision. The separate “View outside” control shows the whole ship; “Other side” reverses the exterior view. Movement is paused during this inspection. The original room furnishings are generated in `web/ship-room-assets.js`: flight consoles and seats, bunks and personal storage, food and water preparation, a communal reading/tablet area, suit and pressurization equipment, and tanks/generator controls. The user's room and prop images guide proportions, visual layering and function; their artwork is not copied or bundled.

The tablet interaction visibly moves the tablet into Gagoo's hand before opening its blank screen. Alien X's dialogue advances to a test request; choosing the option opens the quiz without replacing the room background. Wrong and correct answers receive text feedback. Leaving an overlay returns control to the room.

The ship contains a floating coffee mug, two books, two pens and a notepad. Gagoo can bump them into motion and spin; props also contact each other, consoles and room boundaries. The simulation uses conservative sphere proxies for props and a vertical capsule for Gagoo, with bounded timesteps and light damping. It does not model individual hand contact, liquid in the mug, precise prop shapes or engineering-grade microgravity. Opening an interaction overlay pauses prop simulation. The motion preference suppresses decorative drift while preserving the visible consequence of deliberate contact.

The current style uses heavy silhouette strokes, selected surface lines, discrete light bands and cast/received shadows on the characters, objects and room. It is inspired by ink/grease-pencil drawing; it is implemented with WebGL materials and geometry rather than hand-drawn animation frames or Blender Grease Pencil assets.

The prototype does not save quiz results to an account, send analytics, or claim a validated educational assessment. It does not operate SPHEREx or display live spacecraft telemetry.

## Visual direction and references

- Camera and readable room composition: [Stardew Valley's official media](https://www.stardewvalley.net/media/). The prototype is a 3D room, with its own geometry and palette.
- Dialogue rhythm and bold graphic panels: [Persona 5 Royal's official site](https://persona.atlus.com/p5r/). Angular panels, name tags and high contrast guide the new interface; game artwork is not bundled.
- Character identity: the user's Alien X references supplied in this conversation and the existing Gagoo design in [GAGOO_BRIEF.md](design/GAGOO_BRIEF.md).
- Rig implementation reference: [Three.js Bone](https://threejs.org/docs/pages/Bone.html) and [SkinnedMesh](https://threejs.org/docs/pages/SkinnedMesh.html). The runtime's pinned local Three.js version is authoritative for implementation.
- Quiz science: [JPL mission overview](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/) and the sources linked with the answers. Pre-launch schedules in that press kit are not used as actual historical dates.

## Acceptance criteria

1. Dragging Gagoo drives independently delayed joint motion; release and window impact settle without detached parts, unstable transforms or helmet penetration.
2. The entrance begins from the visible Earth, satellite and Gagoo composition. The camera withdraws through a window; Gagoo fills most of the opening on contact, sticks for 650 milliseconds, then slides right on the glass plane. Its complete silhouette disappears before blinds begin. Cancel restores the home scene; skip and reduced motion remain supported.
3. Gagoo can reach both room interactions with keyboard, touch controls or accessible station controls. Walls and consoles prevent walking through solid geometry. The contextual E prompt appears only when the player is close enough to interact, and clears when they leave.
4. Tablet pickup is visible, its display is blank, and closing it returns control without stuck input.
5. Alien X dialogue reaches the test option; the quiz shows correct/incorrect feedback, explanation, retry and progression.
6. Mobile controls stay in their own half of the viewport in portrait and landscape. Touch release/cancellation stops movement, and overlays stop background movement.
7. Both Vietnamese and English remain usable. Keyboard focus, readable feedback, reduced motion, WebGL failure and resizing are checked.
8. All six floating props drift and rotate without falling; player contact changes their velocity/spin. Props remain within room bounds and avoid persistent overlaps with obstacles and each other. Pausing an overlay must stop the simulation without a jump on return.
9. Ink outlines and shadows remain readable on desktop and mobile, do not obscure the face or tablet/quiz, and clean up with the scene.
10. Each doorway supports room → chamber-only loading → open door/destination → destination-only, in both directions. A delayed, failed or cancelled load must not reveal an unrelated room or allow walking through a closed door.
11. The six-room graph remains traversable. Exterior inspection preserves mirrored geometry except the single external hatch; returning to gameplay restores the current room and position.

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

## Historical verification: first control-room release, 15 November 2026

The following counts describe the earlier backward-recoil release (`a4e82dd`), before the glass slide, looser joints, floating props and stronger ink treatment. They are retained as history, not current-release acceptance evidence.

- The rig contains 19 bones and 46 meshes, totaling 2,004 triangles. Blender and GLB retain normalized rigid weights, named joints and one four-second rebound clip. The round-trip check compares every bone over all 121 sampled animation frames, not only the rest pose.
- The cinema suite covers 16 cases, including actual desktop/mobile home continuity, backward recoil, contact sizing, cancellation, reentry, delayed imports, context loss and reduced motion. The underlying home DOM is retained beneath a transparent 3D cabin/actor layer; this is a staged camera illusion rather than one shared orbital physics world.
- Control-room checks cover desktop, mobile widths of 390 and 320 pixels, a landscape touch viewport and unavailable WebGL. They exercise actual movement, touchscreen hold/cancel, tablet pickup, both dialogue stages, wrong-answer retry, both correct answers, language changes and return to the room. No API writes occur in these checks.
- Local Python tests: 659 run, eight environment-dependent MongoDB integration tests skipped; CI must exercise those against its disposable MongoDB replica set before merge. All 16 JavaScript suites pass locally.

That earlier Blender handoff remains under `data/raw/gagoo-rig-assets/`.

## Previous rig handoff and release verification

The current handoff is under `data/raw/gagoo-loose-rig-assets/`. It retains 19 bones, 46 meshes and 2,004 triangles, with the four-second `Gagoo_Loose_Joint_Response` clip. `glb-roundtrip.json` records a comparison of all 121 sampled frames against the runtime, and `blender-handoff.json` records source and artifact hashes. The clip demonstrates the loose joint response; it does not include the home scene, glass slide or blinds.

The current focused rig tests verify bounded follow-through, different hand/arm settling rates, stable timestep integration, exact pose handoff and helmet clearance. Visual pose samples are under `data/raw/gagoo-loose-rig-qa/`.

The following checks describe the earlier glass-slide and floating-room release, before the bus layout:

- All 18 JavaScript suites pass.
- All 659 local Python tests complete successfully; eight MongoDB integration tests require the disposable CI database and are skipped locally.
- Five enhanced control-room browser cases pass, including desktop/mobile and unavailable WebGL.
- Five home/Gagoo browser cases pass.
- Nineteen cinematic cases pass for the glass hold and right-slide revision, including ultrawide clearance, a zero-height canvas and a bounded return home when projection cannot verify clearance.

The earlier core suite covered guided comparison, timeline fixtures, retry and script recovery. These historical counts are not evidence for the current ship layout; use the current delivery receipt and browser checks.

Prototype gameplay, learning effectiveness and real-device GPU performance are not validated by automated browser tests. The tablet intentionally has no content; the quiz has two demonstration questions and no persistent learner record.

## Next design milestone

Use this room to test one complete short learning activity with a beginner: approach Alien X, read a concept, answer a question, inspect the explanation and return to exploration. Check that learners can find the interaction and explain the answer without assistance before expanding the room or adding rewards.

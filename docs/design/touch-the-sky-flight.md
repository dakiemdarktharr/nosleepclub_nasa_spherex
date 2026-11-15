# Touch The Sky: ship interaction milestone

Preview: `python scripts/serve_app.py`, then open
<http://127.0.0.1:8767/?lang=vi#learn>.

## Playable loop

1. On the first visit on this device, a green spiral gate opens, Alien X steps
   through, and the camera cuts to Gagoo's startled face. Skip/Escape returns
   control immediately. Finishing or skipping marks the introduction as seen.
2. The tablet teaches lesson 1. Alien X retains its prerequisite, conversation,
   six-question quiz, explanations, review and replay after the introduction.
3. Five correct first responses earn regular fuel; six earn rainbow fuel.
   Receiving a reward commits inventory before its animation. Reopening the
   results cannot claim it twice. A fresh complete quiz can earn another can.
4. Walk, click a station, or use the engine/cockpit shortcuts. At the thruster,
   use E/the touch interaction button or click the thruster. Regular fuel fills
   the gauge. Rainbow fuel breaks its face with a shard burst and gives the
   thruster a vibrating rainbow aura. Loading consumes exactly one can.
5. A loaded engine enables Launch ship in the cockpit, both on the HUD and
   flight controls. Regular flight lasts 3 active seconds and reaches 1/3.
   Rainbow flight enters/exits a wormhole over 4 active seconds and reaches 2/3.
   The resulting tablet places a ship marker at the progress bar's endpoint.
6. Return to the room and continue using Tablet and Alien X. Replaying lesson 1
   retains the furthest milestone rather than accumulating repeated flights.

## Reliability and accessibility

- Inventory, loaded fuel, furthest progress, introduction completion, first
  answers and claim state share the existing browser-local lesson save.
- Reloading an unfinished flight restarts that same paid flight. It does not
  consume another can. Hidden tabs and the host's QR/library pause active time.
- Closing a quiz preserves the current explanation, including after reload.
- Dialog focus is contained; the scene controls become inert while a dialog is
  open. Escape/close restores focus. The introduction has an explicit skip.
- Reduced motion removes decorative shaking, spinning and the gauge burst.
- A failed WebGL scene preserves the existing accessible lesson/quiz fallback.
  Hardware navigation needs the 3D scene; retry is available.

## Design and verification

The exterior uses a faceted pressure hull, armored spine, tapered cockpit,
exposed pipes, radiator fins, service ladder and twin aft thrusters. Dialogue
combines angular black/red comic frames with space-radio details. Public
branding and page titles use Touch The Sky; scientific SPHEREx names stay intact.

Automated checks:

```powershell
node tests/ship-journey.test.cjs
python -m scripts.browser_control_room
python -m scripts.browser_ship_flight
python -m scripts.browser_gagoo
```

The flight test earns fuel through the real quiz, reloads, loads the thruster,
flies both routes and reopens both original interactions on desktop/mobile.
The control-room suite covers four viewport sizes, VI/EN, all six rooms,
keyboard/joystick cancellation, loading failure/retry, corridor retreat and
WebGL fallback. Screenshots and test output go to ignored `data/raw/`.

## Limits and next milestone

This is a fictional learning game. Fuel, alien characters, wormholes and journey
fractions are story mechanics, not SPHEREx telemetry or astronomical evidence.
Progress is local to this browser, not an authenticated account or cloud save.
Denied local storage allows play in memory but cannot retain progress on reload.

Next milestone: make the destination after 2/3 a playable NightSky observation
task. Acceptance: arrive from the report tablet, find a real documented field,
answer questions about its image, and retain the source and measurement limits.

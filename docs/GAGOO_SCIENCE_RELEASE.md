# Gagoo and the SPHEREx science showcase

Delivery scope: the orbital home now opens a separate learning route through Gagoo, while the existing research workspace and full-resolution SPHEREx timeline remain available. Learn intentionally contains no lessons yet.

## Product changes

- Gagoo is a real polygonal character: 1,860 triangles, 38 named meshes, broad gray face planes, dusty pink ears, simplified amber eyes, clear helmet and a compact off-white suit. Its eye width relative to the head is 15.19% smaller than the preceding model. The 1,794 checked head vertices fit inside the helmet.
- The mascot rotates in place, supports pointer dragging and a simulated tether, and separates drag from activation. Touch uses a first-tap label and second-tap entrance. Keyboard activation, pause, reduced motion, off-screen suspension and a rendered poster fallback are supported.
- The entrance pulls back behind a spacecraft window, brings Gagoo into contact with the glass, slides the character away, then uses a one-second blinds cover/reveal. Skip, cancel, browser navigation, context loss and delayed imports clean up the temporary scene.
- History precedes the expanded bilingual science showcase: goals, orbit and Sun orientation, optical/thermal/electrical systems, six detectors and the LVF principle, published results, and the path from photons to scientific data.
- Public display names are **sphere x night**, **sphere x search** and **sphere x learn**. Existing URL hashes and research links remain compatible.

## Review and reproduction

Run the static frontend from the repository root:

```powershell
.\.venv\Scripts\python.exe -m http.server 8000 --directory web
```

Open `http://localhost:8000/?lang=vi#orbit`, `#about`, `#night-sky` or `#learn`. Production adds the existing MongoDB-backed API.

The character source and export instructions are in [GAGOO_BRIEF.md](design/GAGOO_BRIEF.md). `data/raw/gagoo-assets/` contains the editable Blender scene, GLB, actual-model studio renders and geometry receipts. The concept PNG is explicitly separate from those renders.

Checks for this milestone:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
Get-ChildItem tests -Filter '*.test.cjs' | ForEach-Object { node $_.FullName }
.\.venv\Scripts\python.exe -m scripts.browser_smoke
.\.venv\Scripts\python.exe -m scripts.browser_gagoo
.\.venv\Scripts\python.exe -m scripts.check_gagoo_entrance
node scripts/check_gagoo_glb.mjs
```

GitHub CI runs Python 3.12 with a disposable MongoDB replica set, all JavaScript suites, the core desktop/mobile checks, mascot integration and entrance lifecycle checks. Production promotion must also pass the existing MongoDB asset/hash gate and checks against the exact deployment commit.

## Scientific and product limits

The science diagrams are explanatory schematics, not live spacecraft telemetry, engineering drawings or calibrated observations. The tether and glass collision are stylized interaction effects. The Blender handoff preserves editable parts but does not add an animation armature. See [SPHEREX_SCIENCE_SHOWCASE.md](SPHEREX_SCIENCE_SHOWCASE.md) for dated primary sources, the shield/optical-axis distinction and DR1 limitations.

No learning effectiveness or astronomical discovery is claimed from passing software tests. The next content milestone is the approved three-lesson SPHEREx journey: history, spacecraft/mission, then guided practice. Its acceptance criterion should be that a new learner can explain a masked pixel and distinguish a time comparison from a wavelength comparison using real images. Learn remains blank until that content milestone is implemented.

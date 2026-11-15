# Gagoo — character direction

Approved direction supplied by the project owner on 14 November 2026. The mascot is a bushbaby astronaut and opens **sphere x learn** from the orbital home screen.

## Identity and surfaces

- Cool gray face, large rounded ears with one dusty pink inset each, amber eyes, clear helmet, warm off-white suit and dark teal chest panel.
- Oversized head and compact body, with separate short legs and flat-soled boots.
- A few broad polygonal volumes. Broad forehead, two clean cheek planes, lightly chamfered jaw. Angular breaks belong mainly at the silhouette, temples and jaw.
- Eye width reduced approximately 15–20% from the preceding Gagoo model. One amber shape, one dark pupil and one highlight per eye. No stacked rings or dark goggle-like sockets.
- One compact pale muzzle, charcoal nose, subtle mouth; a small tuft and no separate cheek spikes.
- Each ear is a chunky beveled polygon. Both ears and the face must fit inside the helmet, including at side and rear views.
- One transparent polygonal dome, one short soft reflection, one chunky collar.
- Tapered sleeves and mitten gloves. Shoulder plates, elbow bands, kneepads and boot rings merge into the main suit forms. Flat colors suggest cuffs and seams; one small mustard patch.
- One flush teal chest panel, pale cyan display and two status dots.

## References and concept

The owner supplied the earlier Gagoo front view for identity, two low-poly chibi character references for proportion and broad surfaces, and a painted low-poly character reference for detail treatment. Their species, costume and props are not copied.

[gagoo-concept-v3.png](gagoo-concept-v3.png) is the **Imagegen concept**, created with the built-in image tool from those references and the owner's detailed prompt. It is an art-direction image, not a render or photograph of the shipped geometry.

The runtime model is authored as named polygonal parts in `web/gagoo-scene.js`. The export scripts convert that same geometry into an editable Blender scene and GLB. The studio PNG is rendered from the actual geometry in Blender. Keep these outputs distinct from the concept when showing progress.

## Presentation and interaction

- Studio review: straight-on front view, full body and both boots visible, plain light-gray background, diffuse lighting, gentle contact shadow, no UI counter.
- Website: transparent background, shared home-scene lighting, slow idle rotation, draggable position and a simulated zero-gravity tether. Runtime toon bands, bold ink silhouettes and shadow maps give the character a grease-pencil-inspired appearance. These are WebGL effects, not Blender Grease Pencil strokes embedded in the editable model.
- Touch: first tap reveals the label, second tap opens Learn. A drag must not activate navigation. Enter/Space provide keyboard activation; motion can be paused or reduced.
- Opening Learn: the visible home scene remains in place while the camera pulls back behind a spacecraft window. Gagoo approaches, fills most of the opening, contacts the glass and sticks for 650 milliseconds. It then slides right along the glass until the entire character is hidden beyond the window edge. Only after it has disappeared do the blinds cover and reveal the destination in one second. The loose limbs follow the impact and slide; Gagoo no longer rebounds backward. Skip and cancel remain available.
- Learn is intentionally blank for this milestone. Its header, language/theme controls and home link remain usable.

## Reproduce the Blender handoff

From the repository root:

```powershell
node scripts/export_gagoo_geometry.mjs data/raw/gagoo-loose-rig-assets/gagoo-geometry.json
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --factory-startup --python scripts/export_gagoo_blender.py -- --input data/raw/gagoo-loose-rig-assets/gagoo-geometry.json --output data/raw/gagoo-loose-rig-assets
node scripts/check_gagoo_glb.mjs data/raw/gagoo-loose-rig-assets
```

The current `.blend`, `.glb` and geometry receipts live under ignored `data/raw/gagoo-loose-rig-assets/`. This conversion runs in a separate Blender process and does not modify a user's open scene. The character has 19 named bones; each broad polygonal part is rigidly attached to its bone in the runtime. The Blender/GLB handoff uses normalized rigid vertex weights and includes `Gagoo_Loose_Joint_Response`, a four-second demonstration of the joint solver. This clip is not the staged glass-slide cinematic. Runtime ink outlines and scene shadow maps are applied separately, so the exported mesh remains editable without duplicate outline shells. Add `--render --resolution 1200` when fresh studio renders are required.

## Articulated motion

The neck, ears, eyes, shoulders, elbows, hands, hips, knees and feet respond to drag acceleration and impact. The current revision lowers spring stiffness and damping, with more front/back limb travel and a slower return. Hands and heavier arms settle at different rates. Shoulder and hip side limits allow broader outward movement than inward folding, which limits passage through the torso. The helmet and collar follow the neck together; ear and eye limits stay small enough to preserve the face and visor clearance. Suit-colored joint cores close gaps when elbows and knees bend.

This is a stylized articulated ragdoll, not a general rigid-body collision simulation. Window contact is a staged impulse with a glass-plane constraint during the hold and slide; the character does not simulate arbitrary self-collisions or real astronaut biomechanics. The tether remains a separate zero-gravity approximation.

## Verification

Use `tests/gagoo-physics.test.cjs`, `tests/gagoo-ragdoll.test.cjs`, the geometry checks, `scripts/browser_gagoo.py`, `scripts/check_gagoo_entrance.py`, the GLB round-trip check, and the existing desktop/mobile smoke suite. Inspect front, side, back and three-quarter poses. Verify ear/helmet clearance at joint limits, loose follow-through and settling, simple eye layers, reduced eye width, mobile drag-to-tap behavior, the glass hold, complete right-side disappearance before blinds, and cancellation before release. Test requirements here do not imply that the current full browser release suite has already completed; consult its delivery receipt.

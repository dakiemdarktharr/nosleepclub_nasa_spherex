# Workflow-Oriented Interface

The interface processes one dataset at a time through four screens. [Open the app](https://nosleepclub-nasa-spherex.vercel.app/#home). This is a change to interface/context management; it does not rerun scientific measurements.

| Step | WISE 0855 sample | IRSA image search |
|---|---|---|
| 1. Data | Select an image set; preview its real SPHEREx images at reduced size, before/after | Enter coordinates, release, detector, and field of view; search metadata and download cutouts |
| 2. Compare | Wipe, side-by-side, difference, or blink; select WISE/residual | Keep image A and select image B; blink downloaded images with the same display scale |
| 3. Check | WISE vector/SNR appears only when WISE is selected; residual has its own coordinates and score | View both image IDs, mask, sources, display convention, and limits; no motion fitting yet |
| 4. Record | Private note tied to the correct analysis hash, scene, and region; MongoDB API lifecycle remains unchanged | Export JSON with the exact query, A/B pair, and note; do not POST IRSA notes to the WISE API |

The step bar and primary button use the same order. Each screen has a back button; changing screens does not change data. Returning to data selection is an explicit action. Switching to the audit archive preserves the current position so the user can return to the workflow.

## Reduce copy while preserving decision-relevant information

- Remove the large illustrative landing page, promotional sections, and repeated instructions under headings. The data-selection image is a thumbnail of the selected SPHEREx scene; Canva assets stay in the guide and remain labeled as illustrations.
- Put long technical details, provenance, hashes, and limits in expandable sections. Units, real-image/synthetic-source labels, uncalibrated-error warnings, and image-quality failures that affect decisions remain visible beside the relevant step.
- Keep the audit archive separate from the four screens. Display one report at a time, with links back to the list and current work. Historical reports must not be presented as analysis of the currently selected IRSA coordinates. Large journals remain on-demand downloads.
- Use the local Be Vietnam Pro font, solid backgrounds, clear field labels, and focus indicators; do not place data-processing text over decorative images.

## Context constraints

The next-step button waits for data to be ready. IRSA requires retaining image A and downloading a different image B before moving to check/record. The check screen is remembered against a signature of the image set and field; changing scene, region, query, or image pair requires a new check. This is an interaction sequence, **not a scientific validation gate**.

When a new scene loads, old data is not treated as the new scene being ready. A late error from an old request must not overwrite the new scene. Blinking stops when leaving the compare screen and retains the selected pair, even if image A was visible when the user continued.

IRSA notes stay in memory under the query and two source URLs; changing pairs does not attach an old note to a different pair, and returning to the same pair restores its draft. These drafts are not persisted across reload or closing the page; **Export review JSON** is the output that must be saved. WISE reviews retain their separate ReviewStore/API lifecycle and do not move into the IRSA workspace.

## Navigation and keyboard

`#home` is the data screen; `#compare-step`, `#check-step`, and `#review-step` retain the selected source. The old `#workspace` link opens WISE, `#explore` opens IRSA search, and report links such as `#signal-controls`/`#profile-landscape` still resolve. Back/Forward changes screens without reinitializing the dataset.

The skip link moves focus only to the current content. After each screen change, focus moves to its heading; opening a report with Enter does not leave focus in the hidden list. Help returns to the current source and does not silently switch IRSA to WISE.

Keyboard and reflow checks verify only the tested interactions; they do not replace screen-reader testing or a full WCAG audit.

## Scientific limits remain unchanged

IRSA images are cutouts placed on the display WCS; they have not been star-aligned, spectrally joined at source, or fit for motion. WISE measurements use the previously published conditional product. Residuals have no celestial-source identity; a successful fit does not confirm a detection. Do not change thresholds, PSF, covariance, or locked science products; the 252 assessment cells and 30 reserved fields remain unopened.

## Next step

Test with three new users: each should complete both WISE and IRSA flows, preserve the correct dataset/region when returning, and export/save the right record without route prompts. Record where they stop or misunderstand, especially the distinction among residual, WISE vector, and synthetic-source report. After this round, continue the separate science milestone on pixel-area bias, template, and overlapping sources described in `SIGNAL_CONTROL_RESULTS.md`.

Local preview:

```powershell
.venv/Scripts/python.exe -m scripts.serve_app --port 8770
```

Open `http://127.0.0.1:8770/#home`. The web runtime remains separate from the scientific-computing environment; do not add a Node runtime or framework build to the application.

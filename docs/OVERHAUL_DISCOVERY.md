# Reshaping Sky Lab

## Challenge and current product gap

**Planet X and SPHEREx** asks for a public web application where users enter RA/Dec and play SPHEREx images of the same sky region over time to identify changes. The five test targets are Barnard's Star, Epsilon Indi B, WISE 0855, RW Aurigae, and R Draconis. The challenge suggests image addition/subtraction, field-of-view controls, spectra, Gaia/WISE layers, contamination flags, and coordinates in the URL. [Challenge notes](CHALLENGE.md) · [Official Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details) · [HackAthlone repost](https://hackathlone.com/challenges/planet-x-and-spherex).

On 14 November 2026, the official Details and Resources pages did not open in the lookup tool. The HackAthlone repost matched the repository's saved goal and listed eight resources, including IRSA, the SPHEREx notebook, WiseView, Gaia DR3, CADC, and NEOSSat. A prepared cutout set for all five targets remains unconfirmed. [Official Resources](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) · [HackAthlone resources](https://hackathlone.com/challenges/planet-x-and-spherex#resources) · [Discussion with Space Apps Navigator](https://github.com/nasa/spaceapps/discussions/1847).

| Requirement | Current version | Work for the next version |
|---|---|---|
| Find a region by RA/Dec | Accepts two coordinate formats, has five sample targets, and queries IRSA by data release, detector, field of view, and date range. Page title and default sample focus on WISE 0855. | Put sample targets and coordinate entry in the same entry point. Move live queries to DR1/QR3 and verify them. |
| View change over time | Has observation list, previous/next steps, and blinking between two loaded A/B images. Historical evidence has two QR2 cutouts per target. | Play multiple frames in observation-time order with a timeline, pause, and frame-by-frame controls. Use A/B when only two suitable images exist. |
| Understand what changed | IRSA images share a display WCS grid and have pixel flags and a common contrast scale. They have not been star-registered or checked for wavelength at the source. | Show time, detector, data release, known band, and image-edge flags. Report when same-band comparison data are unavailable. |
| Inspect and save evidence | Has an audit archive, JSON, and FITS links. WISE notes use separate guest sessions. IRSA queries export notes for each pair. | Let experts open metadata while keeping the current region/frame. Choose a sharing format based on actual needs. |

[Current workflow](WORKFLOW_UI.md) · [Explorer and five-target checks](SKY_EXPLORER.md) · [A/B playback code](../web/explorer.js#L171) · [Readiness status](PRODUCTION_READINESS.md).

IRSA documentation dated 12 November 2026 confirms **DR1 and QR3 have replaced QR2**. DR1 reprocesses Survey 1–2 images. QR3 covers Survey 3–4 and is designed to be used with DR1 images. IRSA says QR2 has left the search service and remains available for direct download until February 2027. The current interface/API accepts only `qr2` or `qr3`, with `qr2` as the default. Query newer DR1/QR3 separately and retain QR2 labels on historical products. The DR1 all-sky cube has 102 nominal channels. The player needs **Spectral Images** per observation. [IRSA Data Releases](https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-releases/) · [IRSA DR1 Overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html) · [Current API](OBSERVATION_API_CONTRACT.md).

## Six decisions that set direction

You can reply with a question number and a few words. The last column is the proposed option for you to correct or replace.

| # | Question | Proposed option |
|---|---|---|
| **1. Purpose and deadline** | Is the first release for **the hackathon submission**, **long-term users**, or **both**? What is the hard deadline, who will review it, and do you need a URL, video, or internal prototype? | For a hackathon deadline, prioritize one complete public workflow for judges and prepare real images cached for a stable demo. |
| **2. First user and task** | Who must succeed first: a curious newcomer unfamiliar with RA/Dec, students/educators, amateur candidate hunters, or astronomers? What must they accomplish on their first visit for you to call it a success? | A newcomer opens a sample and plays its images. An experienced user enters RA/Dec directly, changes filters, and downloads evidence. |
| **3. Science story** | Should the lead be **motion** of Barnard/WISE 0855, **variability** of RW Aur/R Dra, **candidate triage** for human review, or another story? Which target appears first? | Choose a motion example after verifying a suitable sequence. Use other targets for exploration and state the data status for each region. |
| **4. Entry and map** | Should the first screen show **sample targets**, a **coordinate field**, or the **3D map**? Should both groups use one screen with advanced controls or separate modes? Which current interaction must remain? | Use one observation screen with sample targets and direct coordinate entry. Open advanced controls in place and put the 3D map under Explore. |
| **5. Data and measurements** | Should the first version use **SPHEREx image sequences**, **Gaia/WISE comparison**, or **multiple surveys**? Which two expert functions matter most: metadata/masks, star registration, image subtraction, position measurement, light curves, spectra, or batch download? | Play DR1/QR3 images over time, show WCS/mask/metadata, and provide FITS download. Add overlays or measurements in the order you choose. |
| **6. Output and devices** | What should a viewer be able to submit after observing? Options include a **link reopening region/frames**, **image/video**, **JSON/CSV/FITS**, or a **shared review record**. Which devices, languages, weak-network, or offline constraints are mandatory? | Provide a link reopening the query and selected frames, with JSON/FITS when needed for reproduction. Support keyboard and mobile use; set the default language based on the recipient. |

## Detailed scope questions

### Finding and viewing images

7. Beyond RA/Dec in degrees and hour/minute/second format, do you need object-name search, sky-sphere selection, shared links, or pasted coordinate lists? For name search, how should the identifier source and epoch be shown?
8. Does the player need speed controls, frame stepping, looping, locked contrast, synchronized zoom/pan, or A/B blinking? Should users select frames for a sequence, or should the site suggest them first? If a region lacks enough valid frames, should the interface show the real count, change the date range, or suggest another target?
9. Should users select data by human-readable band, detector D1–D6, wavelength at the current point, or all three at different expertise levels? Do you need a maximum field of view, default date range, or a way to mark a subregion for checking?
10. Should the 3D map guide users through **survey selection → footprint → position selection → image**, or mainly support learning/presentations? Do you need a background image, equator/Milky Way, time cross-section, or per-image footprints? [Prototype sky map](sky-atlas.html) · [Source catalog](DATASET_CATALOG.md).

### Scientific evidence

11. When stacking images, should the first version simply place them on a common WCS grid, or register to reference stars and check residuals before comparison? Should the system choose a small set of spectrally compatible images, or allow a broader selection with explicit compatibility labels?
12. If an external survey layer is added, what should come first? Gaia can provide positions/motion cross-checks, WISE/NEOWISE infrared history, ZTF optical variability, or JWST spectral comparison for one source. Should these be shown side by side, overlaid, or measured jointly? Who sets the conditions for comparing measurements across surveys?
13. Should the tool stop at inspection and notes, or rank candidates for expert review? If ranking is added, how should it distinguish motion, variability, moving objects, image artifacts, and insufficient-evidence cases? Who reviews candidates, and what evidence is sufficient to share one?
14. Do experts need to reproduce only the query, the common-grid image placement, or the measurement too? Which items must be retained: frame list, time, original data, mask, wavelength, parameters, processing version, and errors? Is batch export across targets needed, or a format matching a current notebook?

### Release and operations

15. Do you need to upload sessions to a server, use them across devices, share privately, or collaborate with experts? If so, who can view/edit/delete and for how long? Would a link containing only query configuration meet your needs?
16. Should the running Sky Lab URL be retained, or should a separate preview be used? Do you have a presentation reference, name/brand to keep, English-before-submission requirement, or storage/bandwidth cost and user-count limits?
17. Who can try it before the scope is finalized? Do you want to measure time from landing page to playback, whether users can find images without help, reopening the right query from a link, or their ability to read each frame's source and limits?

## Proposed next milestone

**From coordinates to a SPHEREx player.** After decisions 1–6 are settled, choose a lead example and build one workflow with a separate preview. Verify the DR1/QR3 API first to avoid designing the interface around a source that has changed.

1. Enter RA/Dec or open a sample target, then play **at least three compatible real observations from one region**, ordered by observation time. Verify each frame's footprint, display quality, common grid and display scale, and sufficient spectral metadata for the chosen comparison. Record timestamp, release, detector, original URL, hash, and mask in the evidence. Count each observation once even if it has multiple processed versions.
2. Check new queries for all five targets. Two suitable frames permit A/B blinking. If only one or no suitable frames exist, report the count and any known reason. If IRSA fails, the cached demo must show release and observation time clearly.
3. Ask three newcomers to open a sample and play images without route guidance, then ask which dates they saw and what might explain one visible change. Ask one experienced user to reproduce the view from coordinates and inspect each frame's data source. Test keyboard and mobile flows, including back and pause. User-test counts are proposals for you to adjust.
4. Separate observed images, extrapolated coordinates, synthetic sources, and model outputs. Show comparison conditions for each frame. Scientific confirmation requires appropriate measurements, errors, and controls. [Recorded science and operating limits](PRODUCTION_READINESS.md).

**Quick reply**

```text
1. Purpose / deadline:
2. First user / required task:
3. Story / lead target:
4. Entry / advanced use:
5. Data sources / two expert features:
6. Output / devices / languages:
Other requirements:
```

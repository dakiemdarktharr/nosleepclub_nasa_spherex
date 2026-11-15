# SPHEREx Science Showcase

Reviewed on **14 November 2026**. The page content remains bilingual VI/EN, following the SPHEREx history. This section explains the mission, design, and how to read the data; its SVGs are project-created diagrams, not science products or physical simulations.

## Integration

- CSS: `web/spherex-science.css`.
- JS: `web/spherex-science.js`, no dependencies, network calls, or user-data storage.
- Mount point: `window.SpherexScience.mount(container)`. The module also finds `#spherex-science` when the DOM is ready. Calling it again with the same element does not create duplicate content or listeners.
- `mount` replaces fallback content, changes the container class from `about-mission` to `spherex-science`, and sets the heading and container `aria-labelledby`.
- Initial language comes from `document.documentElement.lang`; the module listens for the document `spherex:language` event with `{detail: {language: "vi" | "en"}}`. Changing languages preserves selections, slider position, open details, and control focus.
- The returned object has `destroy()` to remove listeners. The project currently uses one fixed container; it does not need to be called on route changes.
- The table of contents uses `#about-story-title` and `#ss-1-*` anchors for the standard instance. The router should keep users on About when they select one of these anchors.
- Use theme variables `--public-text`, `--public-muted`, `--public-panel`, `--public-border`, and `--public-accent`. Do not depend on a network-loaded font. Diagrams use fixed dark backgrounds and separate text colors to preserve contrast in both themes.

## Content and interactions

1. **Three big questions:** choose early universe / galaxy history / interstellar ice. The diagram, method, and limits of inference change with the selection.
2. **Orbit and Sun:** three orbital states: polar orbit / safe orientation / seasonal coverage. Distinguish the opening of the photon shield from the optical axis and solar array.
3. **Design:** select optics / photon shield / radiator / power and data. A cutaway diagram highlights the corresponding system; deeper details open with `details`.
4. **Six detectors and 102 channels:** choose one of six detector bands and move a source position across the LVF. Five positions illustrate the principle; they do not simulate an exposure or return a calibrated wavelength. Do not draw a fabricated spectrum.
5. **Published results:** distinguish survey milestones, observations, papers, and data releases. Selected examples are not presented as an exhaustive list of all mission discoveries.
6. **From photons to evidence:** measurement → calibration → product → validation. Expand explanations of FITS, wavelength calibration, DR1 cube limits, and reproducibility metadata.

All important content is available outside SVG. Screen readers receive diagram descriptions; buttons have `aria-pressed`; ranges have labels/output/`aria-valuetext`. Changing content uses a polite live region. Do not switch scenes automatically or run continuous animation. Respect `prefers-reduced-motion`.

## Sources and claim scope

| Topic | Primary source checked | Interpretation rule |
|---|---|---|
| Mission design, 102 channels, 0.75–5 µm range | [Bock et al., *The SPHEREx Satellite Mission*](https://arxiv.org/abs/2511.02985), [published Caltech version](https://authors.library.caltech.edu/records/1hhqm-ehm09) | An all-sky spectral survey; do not describe it as 102 cameras or imply every pixel in an image has the same wavelength. |
| Early universe | [Caltech: Origin of the Universe](https://spherex.caltech.edu/page/the-origin-of-the-universe) | Galaxy distribution and redshift help test inflation models; the mission does not directly image the Big Bang or claim to have identified the inflation mechanism. |
| Galaxies and EBL | [Caltech: Origin and History of Galaxies](https://spherex.caltech.edu/page/the-origin-and-history-of-galaxies) | Extragalactic background light and spatial variation; the ecliptic poles are not geographic poles. |
| Interstellar ice | [Caltech: Origin of Water](https://spherex.caltech.edu/page/the-origin-of-water-in-planetary-systems) | Absorption spectra identify molecules in ice; do not infer life. |
| Orbit | [JPL: Mission overview](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/) | About 650 km, 98 minutes, one pass about every six months, four planned passes in the prime mission; this is not a live ephemeris. The press kit predates launch; do not use its planned launch date as the actual date. |
| Orientation relative to the Sun | [JPL: Spacecraft, Cooling Orbit and Orientation](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/) | **91° refers to the photon-shield opening, not the telescope axis.** The telescope inside tilts slightly sunward for all-sky coverage. Solar arrays point almost continuously toward the Sun; the telescope observes away from Earth. |
| Optics, LVF | [Caltech: Instrument](https://spherex.caltech.edu/page/instrument), [Korngut et al., calibration/testing/performance](https://arxiv.org/abs/2603.29835) | 20 cm aperture, three mirrors, two dichroic branches, six detectors with fixed LVFs. Do not depict the actual ray path as a zigzag. The Instrument page has historical design values; do not assign an older resolving power to DR1. |
| Structure, thermal, power, communications | [JPL: Spacecraft](https://www.jpl.nasa.gov/press-kits/spherex/mission-overview/spacecraft/), [Bock et al.](https://arxiv.org/abs/2511.02985) | Distinguish three photon shields from V-groove radiators. Passive cooling in normal operation does not mean the spacecraft needs no power. Solar arrays are about 750 W by design. The system has a heater for initial decontamination; do not claim it “never uses a heater.” |
| First map | [JPL, 18 December 2025](https://www.jpl.nasa.gov/news/nasas-spherex-observatory-completes-first-cosmic-map-like-no-other/) | A survey milestone and visualization, not confirmation of every science objective. |
| 3I/ATLAS | [NASA, 4 February 2026](https://science.nasa.gov/blogs/3iatlas/2026/02/04/nasas-spherex-mission-tracks-brightening-of-interstellar-comet/), [Lisse et al.](https://arxiv.org/abs/2601.06759) | December 2025 observations, post-perihelion activity, and coma dust/gas. Label as an “observation result”; do not turn it into a life-search claim. |
| Ice/PAHs | [Hora et al., ApJ 1001, 165](https://authors.library.caltech.edu/records/ba2ay-z4658), [preprint](https://arxiv.org/abs/2603.12390) | Cygnus X and North America Nebula maps; published 15 April 2026. Distinguish false color assigned to molecules from colors visible to the human eye. |
| Brown dwarfs | [NASA, 8 October 2026](https://www.nasa.gov/missions/spherex/nasas-spherex-telescope-sees-menagerie-of-brown-dwarfs/), [Rustamkulov et al.](https://arxiv.org/abs/2607.00543) | Sample of 37 brown dwarfs and comparison with atmospheric models. 8 October is NASA's feature date, not the paper's publication date. |
| Pipeline | [Akeson et al.](https://arxiv.org/abs/2511.15823), [Cukierman et al.](https://arxiv.org/abs/2603.25790) | Calibration, map making, foregrounds, and systematic errors are part of the research; blinking images only supports visual inspection. |
| Current DR1 | [IRSA DR1 overview](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/overview_dr1.html), [IRSA data products](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-products/), [Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp.pdf) | DR1, November 2026, uses reprocessed images with QR3. WCS-WAVE is for visualization; CWAVE/CBAND are for science. Cube channels 51/52 are empty and have stripes; ZODI has been subtracted. Spectral IMAGE has not had ZODI subtracted. HiPS PNGs do not replace analytical FITS. |

Do not describe a future catalog as released. Do not include uncalibrated first-light images in a list of science-ready data. Research results link to papers or author repositories, not only press coverage.

## Checks

Run Python Playwright from `.venv/Scripts/python.exe`, Chromium, with a separate local harness under `data/raw/science-showcase-review/` (ignored).

- Desktop 1366 px, mobile 390 px and 320 px.
- Click all 3 science goals, 3 orbit states, 4 systems, and 6 detectors; verify only one button per group has `aria-pressed=true`.
- Use Home/ArrowRight on the slider; output and `aria-valuetext` match.
- VI → EN → VI preserves detector, range, and open details.
- Dark/light theme, no horizontal overflow or JavaScript errors; a second mount does not duplicate content.
- Check SVG text bounding boxes and desktop/mobile screenshots for visual comparison.
- Evidence: `data/raw/science-showcase-review/results.json`, `orbit-1366-light.png`, `orbit-390-dark.png`, full-page screenshots, and additional checks in the same directory.

Module tests do not replace a router/About-page smoke test after integration. The repo owner is responsible for testing with the full site, anchors, and other changes before release.

## Boundaries and next steps

- The explanatory diagrams do not claim exact size, detailed angles, component positions, or instantaneous power for the real spacecraft.
- Working controls do not establish learning outcomes; observe whether learners understand the differences among shield/telescope, time/wavelength, and a visually attractive image/a measurement.
- Next, try a read–interact–explain activity with each age group and check whether learners can explain why two different images do not necessarily mean the object changed. Add a real-data exercise to the learning platform after the content has been reviewed.

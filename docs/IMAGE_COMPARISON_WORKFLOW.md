# SPHEREx Image Comparison Workflow

## Viewing workflow

1. Choose a sky field. Its card offers **Observation timeline** and **Compare A/B**. Both use the same IRSA query and preserve the selected view, center coordinates, field of view, detector, and release.
2. **Observation timeline** displays a large image next to the observation list. For a new field, the tool checks up to six observations spread across the available dates. Select **Play** when at least three compatible frames are ready. Pause on a frame or choose another exposure from the list. The caption shows the frame number, UTC time, and center wavelength. If IRSA fails for Epsilon Indi B, a link opens the saved three-frame DR1 sequence. [Epsilon Indi B observation receipt](data/spherex-dr1-timeline-smoke.json)
3. **Compare A/B** lets you choose an observation and detector for each image. Drag either image or the blue overview box, or use the keyboard to pan both views together. Select a point in the overview to zoom. The camera position is retained when switching between the timeline and A/B views.
4. After selecting two distinct observations, choose **Inspect results**. Review the dates, center wavelength, detector, display range, masks, and source FITS files. You can save a private note and export it as JSON.

## Reference tools

| Tool | How it works and what to adapt |
| --- | --- |
| Backyard Worlds: Planet 9 | Volunteers inspect short sequences of WISE difference images for candidate motion. Use short sequences in a fixed field of view and worked examples of a stationary source, apparent motion, and image artifacts. [Project research](https://www.zooniverse.org/projects/marckuchner/backyard-worlds-planet-9/about/research), [Kuchner et al. discovery paper](https://ntrs.nasa.gov/citations/20170007835) |
| WiseView | The creators describe coordinate, field-size, W1/W2, zoom, and playback-speed controls, plus a Pan-STARRS reference cutout. Their original cumulative stacks can elongate fast-moving sources. Use an explicit field size, synchronized zoom, and links that retain coordinates. Keep other surveys in a clearly attributed reference view. [Creator walkthrough](https://blog.backyardworlds.org/2017/09/13/wiseview/), [WiseView repository](https://github.com/backyardworlds/wiseview) |
| IRSA Time Series Tool and SPHEREx Data Explorer | IRSA links timestamps to individual exposures and reports the wavelength and bandwidth at individual SPHEREx image pixels. Use linked epoch selection and label values sampled only at the field center. [IRSA Time Series Tool](https://irsa.ipac.caltech.edu/onlinehelp/irsaviewer/irsaviewer/overviewTSV.html), [SPHEREx Data Explorer](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/overview.html) |
| SAOImageDS9 | DS9 matches frames by world coordinates and supports tiling, blinking, and blending. Use sky-coordinate alignment and a shared display scale for visual inspection. [DS9 frame matching](https://ds9.si.edu/doc/ref/command.html), [DS9 display modes](https://ds9.si.edu/doc/ref/) |

The live WiseView URL timed out during review. This assessment uses the creators’ documentation and published screenshots.

## Comparison modes

| Mode | Best use | Requirements |
| --- | --- | --- |
| Side-by-side A/B | Compare image shapes and masked regions while keeping metadata visible. | Both images need a shared field and WCS grid. Check spectral differences when the detector changes. |
| Blink or timeline | Spot apparent motion or brightness changes at a fixed sky position. | Use a shared display stretch, chronological times, similar wavelengths, and the ability to pause on any frame. |
| Swipe or color overlay | Inspect structures and edges in the same part of the field. | Useful for the project’s preprocessed WISE sample. PSF, wavelength, and background differences can change colors in arbitrary IRSA frames. |
| Difference image | Analyze changes after constructing a validated reference image. | Requires stellar registration, photometric scaling, PSF treatment, variance, and masks. Validate on static stars and injected sources before assigning scientific meaning. [Zackay, Ofek & Gal-Yam](https://doi.org/10.3847/0004-637X/830/1/27) |

## Science constraints

- The API projects FITS cutouts onto a common 6.15″/pixel TAN grid, north up and east left, subtracts ZODI, and applies a shared display range in MJy/sr. CSS zoom preserves the existing pixel samples. Account for both missing-data pixels (purple) and excluded pixels (orange) when reading images. Headers record the source URL, SHA-256, processing version, and mask policy.
- The optional timeline uses loaded frames with the same detector, display stretch, and declared mask policy. It requires a UTC timestamp, valid center WCS-WAVE, at least three distinct times and observation IDs, and common spectral overlap of at least 75% of the widest band in the group. This is a frame-selection rule for playback. SPHEREx’s linear variable filter means wavelengths vary across an image. [IRSA SPHEREx visualization](https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/visualization.html)
- Viewing a sequence can suggest hypotheses; measuring motion requires stellar image registration and quantified uncertainty. SPHEREx epochs may be much closer together than unWISE epochs, so playback speed is only an interface setting. [unTimely epoch catalog](https://arxiv.org/abs/2209.14327)

## Next milestone

Test the Epsilon Indi B card with first-time and experienced users. Each should open the intended mode, zoom to the same source in both panes, pause on the intended frame, and explain a difference that could be caused by wavelength or a mask. Record time to first interaction, failed actions, and the reasoning users write in their notes.

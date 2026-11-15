# Challenge Requirements Checklist — Planet X and SPHEREx

> Acceptance checklist for NASA Space Apps Challenge 2026 challenge **Planet X and SPHEREx**. An unchecked box marks an item for the team to verify and support with evidence; it does not necessarily mean the feature is absent.

**Official sources**

- [Challenge Details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details)
- [Challenge Resources](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources)

The official challenge page was reviewed on 14 November 2026. The challenge is rated **Advanced**.

## 1. Required objectives

- [ ] **R1 — Public tool:** Build a web tool for the public.
- [ ] **R2 — Correct data:** Display sky images from NASA’s SPHEREx mission.
- [ ] **R3 — Sky coordinates:** Allow users to enter right ascension (RA) and declination (Dec) for a region of the sky.
- [ ] **R4 — Time sequence:** Display a sequence of images of the same region as a short video.
- [ ] **R5 — Make changes easier to see:** Help users quickly inspect changes over time and identify moving objects.
- [ ] **R6 — Barnard’s Star test:** Test the tool with Barnard’s Star.
- [ ] **R7 — Epsilon Indi B test:** Test the tool with Epsilon Indi B, a brown-dwarf pair orbiting a star.
- [ ] **R8 — WISE 0855 test:** Test the tool with WISE 0855 at RA 08h55m10.831s, Dec −7°14′42.53″; it is a fast-moving brown dwarf.
- [ ] **R9 — RW Aurigae test:** Test the tool with the variable star RW Aurigae.
- [ ] **R10 — R Draconis test:** Test the tool with the variable star R Draconis.

## 2. Scientific context in the challenge

The following points explain why the challenge focuses on image sequences. They do not add required features beyond the objectives in Section 1.

- SPHEREx maps the entire sky every six months.
- The mission collects images in 102 near-infrared bands.
- The dataset includes more than one billion objects; the challenge mentions brown dwarfs, comets, asteroids, stars, supernovae, and galaxies.
- Apparent motion between observations can help locate new objects and measure distance.

## 3. Optional extensions

The challenge explicitly marks the following considerations as **optional**. Check an item only if the team chooses to implement it and has evidence that it works.

- [ ] **O1 — Data updates:** Design the tool so new SPHEREx releases can be added easily.
- [ ] **O2 — 102 infrared bands:** Consider ways to present all 102 bands to support exploration.
- [ ] **O3 — Combine detector arrays:** Consider combining data from the six detector arrays independently to improve signal-to-noise.
- [ ] **O4 — Spectra:** Optionally generate spectra on demand.
- [ ] **O5 — Image arithmetic:** Allow users to add or subtract images from different observation times.
- [ ] **O6 — Field of view:** Let users choose the field of view and explain the trade-off between wider coverage and longer data transfer times.
- [ ] **O7 — Catalog overlays:** Optionally overlay data from other missions, such as Gaia or WISE.
- [ ] **O8 — Share coordinates:** Allow coordinates to be embedded in a URL so a query can be shared.
- [ ] **O9 — Metadata:** Display useful metadata, such as contamination flags.
- [ ] **O10 — Astronomy tools:** Evaluate public tools such as Astropy for data processing and Aladin for astronomical visualization.

## 4. Official reference resources

These links are references; the product is not required to integrate every resource.

- [ ] Review SPHEREx resources from the NASA/IPAC Infrared Science Archive (IRSA).
- [ ] Review SPHEREx tutorial notebooks and Python data-access examples.
- [ ] Review WiseView as a related product for inspiration.
- [ ] Use Gaia Data Release 3 if the product needs Gaia data.
- [ ] Review Canadian Space Agency NEOSSat/CADC resources if relevant.

## 5. Acceptance conventions

- Check an item only when there is specific evidence in the application, data, a check, or documentation.
- For each test target, record the coordinates or query, number of observations, dates of the first and last images, and status if the source data is unavailable.
- Do not describe an image difference as a confirmed astronomical detection without independent scientific validation.

# Planet X and SPHEREx — Challenge Notes

Difficulty: **Advanced**. Reviewed on 14 November 2026. [Official details](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=details) · [Requirements and resource review](CHALLENGE_LIVE_REVIEW.md)

## Main requirement

Build a public web tool that accepts **right ascension (RA)** and **declination (Dec)** coordinates, then plays a time sequence of SPHEREx images of the same region like a short video to help viewers notice motion.

## Test targets specified by the challenge

| Target | Notes |
| --- | --- |
| Barnard’s Star | Star |
| Epsilon Indi B | Brown-dwarf pair |
| WISE 0855 | RA `08h55m10.831s`, Dec `-7d14m42.53s` |
| RW Aurigae | Variable star |
| R Draconis | Variable star |

## Optional suggestions from the challenge

- Make it easy to add new data; explore the 102 infrared bands.
- Add or subtract images, choose a field of view, and generate spectra.
- Overlay Gaia or WISE, include coordinates in the URL, and show metadata and contamination flags.
- Consider Astropy and Aladin/CDS.

## Resources

On 14 November 2026, the Resources tab listed eight items. NASA’s group included IRSA, SPHEREx notebooks, WiseView, and Gaia DR3. The Canadian Space Agency partner group included the NEOSSat overview, CADC, a NEOSSat tutorial, and the NEOSSat dataset. [Official resources](https://www.spaceappschallenge.org/2026/challenges/planet-x-and-spherex/?tab=resources) · [Links and notes](CHALLENGE_LIVE_REVIEW.md#optional-suggestions-and-challenge-sources)

## Proposed prototype evaluation criteria

The following criteria are proposed by the team; they are not claims that these features have been built:

- A first-time visitor can open an example target and understand how to compare images without knowing FITS.
- Images of the same sky region are aligned across observation times; apparent motion on screen can be distinguished from alignment error.
- Each frame shows its observation time, units, spectral band, and data source.
- The interface explains when images are missing, coverage is unavailable, or a query is invalid.
- Motion and variability are presented as candidates for follow-up, not as confirmed discoveries.

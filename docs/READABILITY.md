# Vietnamese Typography and Readability — Interface 0.5.4

## Font and layout

Be Vietnam Pro is served in five weights (400/500/600/700/800) with Vietnamese and Latin character sets. The ten WOFF2 files total 170,316 bytes. The original Google Fonts files are retained with the SIL OFL and [provenance.json](../web/assets/fonts/provenance.json). CSS uses the font for content, controls, SVG, and canvas labels, with Arial as a fallback. Assets load only from the same origin, work with the current CSP, and are available in the offline demo.

Heading and body line height was increased to prevent Vietnamese diacritics from being clipped. The hero now uses two rows in the document flow instead of absolutely positioned fact cards, so wrapped text does not overlap. Secondary text is brighter, badges use solid backgrounds, and table headers and alternating rows are clearer. Key data/control labels are at least 12 px on mobile.

The canvas **Before/After** labels use a solid `#070d16` background, colored border, and text size based on the display size, instead of always drawing 17 pixels into a 1024-pixel image and then shrinking it. Labels stay within the frame edges; residual labels appear only for the selected region to reduce clutter. The canvas redraws when the font loads or the viewport changes size. The map keeps full names in the dropdown and emphasizes only the selected, hovered, or focused star label.

The review panel scrolls with the page on short screens and becomes sticky only on desktops tall enough to contain it. Measurements, data, and scientific analysis rules were unchanged.

## Checked color pairs

Relative sRGB luminance was calculated using [W3C Contrast Minimum](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). The values below cover solid background pairs; the hero was also inspected visually because its image background varies.

| Element | Text / background | Contrast |
|---|---|---:|
| Body copy | `#f6f7f8` / `#101419` | 17.23:1 |
| Secondary text | `#c3ccd7` / `#101419` | 11.39:1 |
| Status | `#ffd3a4` / `#2b2117` | 11.34:1 |
| Measurement labels on images | `#d6fff6` / `#070d16` | 18.08:1 |
| Chart text | `#d1dce8` / `#101419` | 13.30:1 |
| Placeholder | `#b8c4d2` / `#12171e` | 10.17:1 |

## Interface checks

- Confirmed that weights 400/800 load for strings containing ă/â/đ/ê/ô/ơ/ư and Vietnamese tone marks.
- Checked the hero, tables, image labels, menu, and data selector at 1,265 px desktop and 390 px mobile widths; Vietnamese text loaded in weights 400/800.
- Checked that the page does not overflow horizontally, the hero does not cover the fact cards, and wide tables scroll within their frame.
- Offline suite: 46/46 tests passed. Production smoke checks also verified same-origin hashes for all ten font files and MongoDB operations through review QA.

Evidence: [desktop](wise0855-mission.jpg), [mobile](wise0855-vietnamese-mobile.jpg), [labels on a real image](wise0855-readable-overlay.jpg). These color measurements do not certify WCAG compliance for the full application.

The updated interface images and labels were added to the README. Next milestone: test the metric-reading flow with new users, especially their understanding of uncertainty and unconfirmed status, before increasing information density.

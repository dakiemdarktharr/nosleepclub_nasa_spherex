# First-Time Exploration Flow

NASA.gov and SpaceX.com were reviewed directly on 30 October 2026. The reference pattern uses a large hero image, high-contrast white text, short navigation, and clear actions. Do not copy their logos, images, articles, or source code.

Tokens: space black `#000000`, tool background `#101419`, surface `#191f27`, white `#f6f7f8`, readable gray `#c3ccd7`, marker orange `#ffb36a`. Since interface 0.5.4, Be Vietnam Pro is self-hosted in Vietnamese/Latin character sets and five weights, with Arial fallback. Use tabular figures for measurements; do not use monospace as decoration. Image labels have their own backgrounds; hero content stays in the document flow so wrapped text does not overlap the fact cards.

```text
Navigation: Mission | Observe | Validate | Record
Illustrative Canva hero + Start observing / Guide
1 Compare images → 2 Review evidence → 3 Save a note
Observe: large real image | target + notes
  Change dataset, mode, zoom, or selected point using real controls
  Open coordinates, terminology, and advanced settings as needed
Validate: QR3 data available? → 30 new fields → acceptance result
Next step: target and acceptance criteria
```

Compared with a technical dashboard, the default view prioritizes images, timely instructions, and the meaning of results. It does not put covariance tables, source IDs, and version lists in the introductory flow. Experienced users can still access Gaia, FITS, CSV/JSON, sources, hashes, and limitations. **Unconfirmed** status remains visible.

The Canva hero and two-epoch illustration were made to separate briefs. Both are labeled as illustrations and are not presented as observation images. FITS and overlays retain their scientific products. All figures in the hero and reports come from real data, not Canva images.

UX criteria: one action from the first page to an image; one action from the observed field to a note; the mobile menu opens/closes by keyboard; the guide explains targets, grainy images, the uncertainty ellipse, and why results may be unconfirmed; no overflow at 390 px; respect reduced-motion settings; dialogs have accessible labels and close controls without losing data selection; MongoDB review save/delete remains functional.

Canva assets: [Hero](https://www.canva.com/M/MAHZbvmhEbQ), [two-epoch guide](https://www.canva.com/M/MAHZbsQBgXg). WebP copies are stored in `web/assets/`; metadata and hashes are in `provenance.json`. Do not hotlink expiring thumbnail URLs. The main frontend code is in `mission.css`/`mission.js`; the canvas and measurements remain in `app.js`. Menu, dataset selector, four modes, zoom, modal, spectral/ePSF filters, and map inspection were checked to confirm each performs a real action.

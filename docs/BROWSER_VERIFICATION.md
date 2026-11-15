# Web Verification 0.10

Direct browser checks on 30 October 2026 in the in-app browser at `http://127.0.0.1:8767/`. The local environment used the live IRSA API, while reviews were stored in the browser. This is not evidence of a Vercel deployment or production MongoDB.

## Flows exercised

- RA = 350°, Dec = +35°, FOV = 0.06°, D6, QR2: the query returned 77 observations and loaded a real PNG. The first image at MJD 60853.93441 had cutout SHA-256 `514ac17f7c8d2b7de1f723e4464dfc85a1caacf666f868e70fd844c9d80de8a6`; the last image at MJD 61221.83881 had SHA-256 `2965965e13366ed397f1896f80025aa0facd42b0297141a6165a9407d5ffbb6c`. The final image loaded at 37 × 37 pixels; both used a grayscale range of −0.0399 to 0.3072 MJy/sr. These hashes are for source cutouts, not PNGs.
- Pinned the first image, selected the last image with the `End` key, played, and stopped blinking. The MJD label, image index, hash, and slider followed the displayed image. The FITS link used the correct cutout query. This checks display behavior only; there was no stellar registration or spectral comparison at the target.
- RA 360° was rejected with a range message and no query was sent. Manually entered coordinates are labeled `Custom coordinates` to avoid assigning an example-target name incorrectly.
- Saved a local QA note; history increased from 0 to 1. Deleted it; history returned to 0 and showed a deletion confirmation. No real notes were used.
- WISE defaults to the closer spectral configuration; measured and predicted positions are initially off. The `#covariance-validation` deep link automatically opens the older experiment archive and keeps it visible.
- The mobile menu opened and navigated to Explore. At 390 × 844, no input/select/button in Explore overflowed horizontally; document width measured 375 px. Vietnamese fonts and contrast were viewed directly. This is not a full screen-reader or WCAG audit.
- The browser reported no JavaScript errors in these flows.

## Related automated checks

142 Python tests passed locally. `tests/explorer.test.cjs` and `tests/review-store.test.cjs` execute real JavaScript with DOM/HTTP test doubles; lifecycle, session loss, concurrent GET/POST/DELETE, rapid image selection, stale responses, field changes, no-data, and mismatched display scale all passed in V8. These checks do not replace browser testing or tests against a real database. GitHub CI still needs to be checked against the exact deployment commit.

Screenshots: [desktop](evidence/0.10/explorer-desktop.jpg) and [mobile](evidence/0.10/explorer-mobile.jpg). IRSA data may change; observation counts and cutouts above are results from this run, not fixed assertions about the future archive.

## Not yet accepted

Vercel bundle/timeouts and deployment-context detection, real MongoDB quota/TTL/owner isolation, review behavior across multiple tabs after cookie loss, screen reader, full-page keyboard navigation, recovery, concurrent load, and independent scientific measurements. The site is not production-ready based only on the steps above.

## Additions after deployment and later research

- Production `c88fe57`, deployment `dpl_CWVm5qSJb2d7npBPv1ngV7vw3HGG`: all [24 response checks](evidence/0.10/production-c88fe57.json) passed, including API commit, real cutout, review transaction/isolation/expiry, and QA cleanup. This adds the API evidence missing above; it is not a concurrent-load test or a test that waited for the 180-day TTL to elapse.
- The production browser confirmed the tighter spectral default, uncalibrated label, disabled measurement/prediction overlays, and MongoDB storage. Tab from the last dialog control moved to the close button; Shift+Tab returned to the last control; Escape closed the dialog and returned focus to `workspace-help`. [Production focus screenshot](evidence/0.10/dialog-keyboard-production.png). Escape closed the mobile menu, set `aria-expanded=false`, and returned focus to the menu button. At the required 390 × 844 viewport, the document did not overflow horizontally (content area measured 375 px).
- The newer sandwich table was tried **locally**; this screenshot does not verify deployment. Enter opens it, with 68%/all accepted selected by default. Changing to 50/95% and accepted updates the numerator/denominator correctly. Example: w090p10 SNR2 at 95% accepted gives 95/124, 108/124, and 101/124 for GN/H/sandwich. No JavaScript errors occurred during these actions. [Desktop](evidence/0.10/sandwich-desktop.png), [mobile](evidence/0.10/sandwich-mobile.png); the table retains its own horizontal scroll area and controls do not overflow the page.
- Opening the page loads only about 177 KB of sandwich overview data; the 8.2 MB audit is an explicit download link. Both include hashes for comparison. The charts/table add no new WISE measurement.

A real screen reader, full-page keyboard navigation, 200–400% reflow, real mobile/touch, multi-tab behavior after cookie loss, load/restore, and independent science remain incompletely verified.

The sandwich table was later checked on **production `c65d79b`**: the deep link opened automatically, and all six default rows matched JSON. Selecting 95%/accepted retained 95/124, 108/124, and 101/124 for w090p10 SNR2, with no JavaScript error during the interaction. [Production screenshot](evidence/0.10/sandwich-production.png). [Receipt of 30 response checks](evidence/0.10/production-c65d79b.json) verifies new artifact hashes; an earlier 502 attempt remains separately recorded in evidence. This verification does not replace scientific measurement or the remaining audits.

Local check after API mask fix 1.1 (31 October 2026, Vietnam time): the 350°/+35° query returned 77 observations. The first real image showed 1,335 usable pixels, 34 excluded, and 0 missing on the 37×37 grid, with grayscale range −0.0399–0.3072 MJy/sr. No JavaScript errors occurred in this flow. Executed JS tests added a check rejecting a comparison across different mask policies, then reloaded the field to reset policy; the full explorer suite passed in V8. This local run does not verify that the new policy was deployed.

After merging PR #5, [public receipt `fc17f96`](evidence/0.10/production-fc17f96.json) verified asset bytes, API 1.1, the mask policy, and 1,335/34/0 pixels over HTTP. The browser-control session became unavailable while rechecking the public interface; there is no new screenshot or production interaction verification for this build. The `c65d79b` production screenshot above certifies only the version named in that receipt. Automatic review blocked the protected-preview fetch because it would create/reuse an authenticated share link that lasts 23 hours. Do not use that link or change access protection to bypass the block.

PR #6 reached production as `906af66`. [37 HTTP responses](evidence/0.10/production-906af66.json) verified new HTML and spectral JSON against commit hashes. Local responses returned the expected bytes for five static assets. The `#spectral-reference` details link uses existing details navigation and adds no JavaScript. The updated hero label says only that the project’s SPHEREx measurements are exploratory. The browser-control session remained unavailable, so no new screenshot/reflow/keyboard review was completed for this panel; HTTP and CI do not replace that evidence.

## Local linked-flux milestone — 30 October 2026 UTC

CUA inspected live content at `http://127.0.0.1:8767/#linked-flux`, with tab 8 selected in IAB. [Local receipt](evidence/0.10/linked-local-checks.json) includes asset hashes and screenshots: [desktop](evidence/0.10/linked-local-desktop.jpg), [mobile](evidence/0.10/linked-local-mobile.jpg). This is not a production receipt.

- Switching strict ↔ broad updated all seven rows, chart, SVG link, status, and spread value from 2.281″ ↔ 0.556″. The seven blocked strict branches remained visible. Enter opened diagnostics with both exposure rows and signed Δχ² values.
- Checked 1280×720, 768×1024, and 390×844. No document-wide horizontal overflow; on mobile, the chart has its own scroll area (298/650 px), as does the table. Tab moved focus to the chart area with an outline; the mobile menu opened/closed. Viewport override was reset after testing. Screen reader and full WCAG were not checked.
- Workspace loaded with strict default; measured/prior overlays were both disabled. An advisory links to the newer comparison; it does not change historical measurements or analysis hashes.
- Opening r8 at 19:19 UTC logged `ReviewStore is not defined`; reload recovered before code was changed, and the cause was not established. r9 added an error state and retry button if the review module is missing. A JavaScript fixture executing the actual app confirms it does not remain indefinitely in `aria-busy`. No r9 console error was observed in this run; the network cause is not claimed as known.
- Three JavaScript suites ran on Node v24.18.0. All 326 local Python tests completed (six Mongo fixture skips); CI replica-set and production need separate receipts.

## Public linked-flux release — `8032493`

[Public browser receipt](evidence/0.10/linked-production-browser.json) and [public screenshot](evidence/0.10/linked-production-desktop.jpg) verify strict/broad switching for the seven-row table, KPI, and SVG; diagnostics open with Enter and can return to the real image. Workspace defaults to strict, with both measured and prior overlays disabled. No console error/warning was observed in this run. Public checks were at 1280×720; tablet/mobile checks used the same hashed asset locally.

[45 response checks](evidence/0.10/production-8032493.json) compared 31 static artifacts with Git blobs and checked all three APIs against the same commit; QA guest data was deleted with no upstream retry required. `worktree_dirty:true` in the receipt is because CI evidence had not yet been committed when the verifier ran. The certified assets are the **Git blob at `8032493`**, not replacement bytes from the working tree. This remains a scoped check, not an SLO or astronomical acceptance.

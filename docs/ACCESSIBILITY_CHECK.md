# Accessibility Check 0.10

Manual browser review on 30 October 2026, following the `accessibility-compliance:wcag-audit-patterns` method. This is a scoped check, not WCAG 2.2 AA certification or a screen-reader user study.

## Checks performed

- The input fields use self-hosted Be Vietnam Pro, and Vietnamese copy was inspected directly. For visible elements on solid backgrounds, relative luminance checks of text and inherited background colors found no cases below 4.5:1 for normal text or 3:1 for large text. Disabled controls and image backgrounds were excluded; the check did not cover every opacity, interactive state, or pixel in illustrative images.
- The **Skip to observed images** link works with Enter. The next Tab reaches `workspace-help` in the image-comparison area, bypassing the navigation; focus remains below the fixed header.
- Enter opens the guide; Escape closes it and returns focus to the opener. The browser’s native Tab sequence sometimes moved to BODY, so focus cycling was added to both dialogs. In the corrected local build, Tab from the last control returns to `guide-close`, and Shift+Tab from the first control goes to `guide-start`; focus stays in the dialog. Ctrl/Alt/Meta+Tab combinations are not intercepted.
- The ePSF report opens with Enter and shows all six rows with their denominators and values. The older experiment archive opens through its deep link. The time control accepts End to move to the last image.
- The mobile menu opens and closes when a link is selected. At 390 × 844, no input/select/button in Explore overflows horizontally. Escape was added to close the menu; production verification after deployment was still pending.

Production hardening in `c88fe57`: Tab/Shift+Tab cycling inside the dialog and Escape returning focus to the opener were tested on the public URL. Escape also closes the mobile menu and restores focus. The newer sandwich table was checked locally: both selects have explicit accessible names; Enter opens the details; the 50/68/95% choices and accepted sample render correctly. The mobile document width does not grow with the table; the table has its own horizontal scroll area. This does not replace screen-reader or reflow auditing.

Focus-cycle evidence: [dialog-keyboard-local.jpg](evidence/0.10/dialog-keyboard-local.jpg). See [BROWSER_VERIFICATION.md](BROWSER_VERIFICATION.md) for checks on the web app/data and environment limitations.

## Still to check

Test a real screen reader (at least NVDA and one other combination), the full keyboard journey and a long evidence dialog, 200–400% zoom/reflow, high-contrast mode, reduced motion, nonvisual descriptions of science images and markers, real mobile/touch devices, and contrast for focus/hover states and image backgrounds. Keep these limits in the verification ledger; do not change scientific results based on interface checks.

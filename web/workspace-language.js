/* Localize static workspace copy without replacing interactive elements or app state. */
(() => {
  "use strict";

  const copy = [
    [".skip-link.legacy-surface", "Skip to content"],
    ["#main-nav a[href='#home'], [data-step-link='data']", "Data"],
    ["#main-nav a[href='#compare-step'], [data-step-link='compare']", "Compare"],
    ["#main-nav a[href='#check-step'], [data-step-link='check']", "Inspect"],
    ["#main-nav a[href='#review-step'], [data-step-link='review']", "Record"],
    ["#main-nav a[href='#research']", "Research"],
    [".workflow-library-link", "Research archive ↗"],
    ["#guide-open", "Guide"],
    ["#privacy-open", "Review storage"],
    ["#storage-status", "Stored only in this browser"],
    ["#step-data-title", "Choose data"],
    ["#home > header .workflow-step-label", "01 / Data"],
    ["#workflow-source-wise", "WISE 0855 sample"],
    ["#workflow-source-irsa", "Search IRSA"],
    ["#workflow-data-wise .workflow-chip", "Observed data · QR2"],
    ["label[for='scene-select']", "Image set"],
    ["#scene-select option[value='coadd-gaia-broad']", "More images · 10 per epoch"],
    ["#scene-select option[value='coadd-gaia-strict']", "Closer spectral match · 2 per epoch"],
    ["#workflow-data-wise dl div:first-child dt", "Time between observations"],
    ["#workflow-data-wise dl div:nth-child(2) dt", "Processing"],
    ["#load-retry", "Reload page"],
    ["label[for='explorer-preset']", "Example target"],
    ["#explorer-preset option[value='custom']", "Enter coordinates"],
    ["label[for='explorer-ra']", "RA · degrees or hours:minutes:seconds"],
    ["label[for='explorer-dec']", "Dec · degrees or degrees:minutes:seconds"],
    ["label[for='explorer-fov']", "Field of view"],
    ["#explorer-fov option[value='0.06']", "3.6 arcmin"],
    ["#explorer-fov option[value='0.12']", "7.2 arcmin"],
    ["#explorer-fov option[value='0.02']", "1.2 arcmin"],
    ["label[for='explorer-release']", "Data release"],
    ["label[for='explorer-detector']", "Detector band"],
    ["#explorer-detector option[value='6']", "D6 · 4.42–5.00 µm"],
    ["#explorer-detector option[value='5']", "D5 · 3.83–4.41 µm"],
    ["#explorer-detector option[value='4']", "D4 · 2.42–3.82 µm"],
    ["#explorer-detector option[value='3']", "D3 · 1.63–2.41 µm"],
    ["#explorer-detector option[value='2']", "D2 · 1.10–1.62 µm"],
    ["#explorer-detector option[value='1']", "D1 · 0.75–1.09 µm"],
    ["label[for='explorer-from']", "From date · optional"],
    ["label[for='explorer-to']", "To date · optional"],
    ["#explorer-search", "Find and open images"],
    ["#workflow-other-scenes > summary", "Single exposures and other configurations"],
    ["#workflow-other-scenes .dataset-history > summary", "Single exposures and comparison setups"],
    ["#workflow-data-next", "Compare images"],
    ["#step-compare-title", "Compare images"],
    ["#compare-step > header .workflow-step-label", "02 / Compare"],
    ["#workspace-help", "How to read the images"],
    ["#pixel-readout", "Move over the image to inspect pixel values"],
    ["#compare-step > .workflow-compact-context a", "Change data"],
    ["#evidence-open", "Source data"],
    ["#workspace .observation-head h3", "Observed images"],
    ["#download-manifest", "Download evidence"],
    ["#workspace .metrics div:first-child span", "Time between observations"],
    ["#wavelength-label", "Wavelength at target position"],
    ["#alignment-label", "Reference-star alignment RMS"],
    ["#workspace [data-mode='wipe']", "Before / after"],
    ["#workspace [data-mode='side']", "Side by side"],
    ["#workspace [data-mode='difference']", "Difference"],
    ["#workspace [data-mode='blink']", "Blink"],
    ["#reset-view span", "Reset"],
    ["#wipe-control label", "Before"],
    ["#wipe-control > span", "After"],
    ["#motion-overlay-label", "WISE 0855 · exploratory position and uncalibrated ellipse"],
    ["#prior-overlay-label", "Predicted position"],
    [".overlay-options label:has(#show-residuals)", "Residuals for review"],
    ["#workspace .workflow-details > summary", "Reading the images and their limits"],
    ["#workspace .inspector-header h3", "Selected region"],
    ["#focus-selection", "Zoom to selection"],
    ["#workspace .candidate-details > summary", "Candidate regions"],
    ["#explorer-upstream", "IRSA query ↗"],
    ["#explorer-previous", "← Previous"],
    ["label[for='explorer-current']", "Observation"],
    ["#explorer-next", "Next →"],
    ["#explorer-retry", "Retry image"],
    ["#compare-step > .workflow-step-actions a", "← Data"],
    ["#workflow-compare-next", "Inspect results →"],
    ["#step-check-title", "Inspect results"],
    ["#check-step > header .workflow-step-label", "03 / Inspect"],
    ["#check-step > .workflow-compact-context a", "Change the region"],
    ["#workflow-motion-summary > summary", "Motion estimate and signal strength"],
    ["#motion-heading", "Displacement · model uncertainty"],
    ["#motion-panel .motion-chart p", "Exploratory estimate · uncalibrated ellipse", 0],
    ["#motion-panel .motion-chart p", "External prediction", 1],
    ["#motion-panel .snr-summary h3", "S/N · signal to noise"],
    ["#motion-panel .snr-summary th:nth-child(2)", "Best single exposure"],
    ["#motion-panel .snr-summary th:nth-child(3)", "Coadd"],
    ["#workflow-measurement-context > summary", "Method and quality"],
    ["#workflow-measurement-context .motion-qualification:nth-child(2)", "Conditional 1σ model uncertainty. Some systematic errors are outside this estimate."],
    ["#workflow-measurement-context .motion-qualification:nth-child(3)", "Aperture S/N at the fitted position, with interpolation covariance propagated. This is conditional on the fit, not blind-detection confidence."],
    ["#workflow-selection-check > summary", "Selected region coordinates and uncertainty"],
    ["#workflow-check-irsa .workflow-check-grid div:nth-child(1) dt", "Image A"],
    ["#workflow-check-irsa .workflow-check-grid div:nth-child(2) dt", "Image B"],
    ["#workflow-check-irsa .workflow-check-grid div:nth-child(3) dt", "Display scale"],
    ["#workflow-check-irsa .workflow-check-grid div:nth-child(3) dd", "Shared across loaded images"],
    ["#workflow-check-irsa .workflow-check-grid div:nth-child(4) dt", "Star registration / motion fit"],
    ["#workflow-check-irsa .workflow-check-grid div:nth-child(4) dd", "Pending"],
    ["#workflow-check-irsa .workflow-details > summary", "Sources, masks and limitations"],
    ["#explorer-download-fits", "FITS cutout at IRSA ↗"],
    ["#workflow-check-irsa .explorer-limit", "Images share a WCS grid. Stellar registration and source-level spectral matching remain pending. A change in brightness or shape can come from wavelength, the point-spread function or noise. The WISE and Barnard presets use predicted 2026 positions. The Epsilon Indi B preset uses a wider field around a historical ESO coordinate. These are search coordinates. Measured source positions depend on the observation epoch."],
    ["#check-step .workflow-evidence-link", "Open research archive ↗"],
    ["#check-step > .workflow-step-actions a", "← Compare"],
    ["#workflow-check-next", "Record notes →"],
    ["#step-review-title", "Record notes"],
    ["#review-step > header .workflow-step-label", "04 / Record"],
    ["#review-step > .workflow-compact-context a", "Review images"],
    ["#review h3", "Review note"],
    ["label[for='review-status']", "Initial assessment"],
    ["#review-status option[value='uncertain']", "Unsure"],
    ["#review-status option[value='interesting']", "Worth a closer look"],
    ["#review-status option[value='artifact']", "Possible artifact"],
    ["label[for='review-note']", "Your observations"],
    ["#save-review", "Save review"],
    ["#export-reviews", "Export JSON"],
    ["#clear-review", "Delete review for this region"],
    ["#review .review-history > summary", "Saved reviews ·"],
    ["#review .review-history > p:first-of-type", "Includes earlier analysis versions. Reviews are private to this browser session and are retained for up to 180 days."],
    ["#workflow-review-irsa > h2", "Notes on IRSA images"],
    ["label[for='explorer-note']", "Your observations"],
    ["#explorer-export", "Export notes as JSON"],
    ["#workflow-review-irsa .workflow-output-kind", "Notes stay in your browser and in the exported JSON file."],
    ["#review-step .workflow-decision-warning", "Viewer notes record observations for further review."],
    ["#review-step > .workflow-step-actions a:first-child", "← Inspect"],
    ["#review-step > .workflow-step-actions a:last-child", "Choose other data"],
    ["#step-research-title, #research > header .workflow-step-label", "Research archive"],
    ["#workflow-return", "Return to workspace →"],
    ["#research > .workflow-library-scope", "Previously published reports in Vietnamese. Return to the workspace to inspect your selected images."],
    ["#workflow-report-nav a", "← All reports"],
    ["#guide-title", "Observing workflow"],
    ["#guide-dialog figcaption", "SPHEREx DR1 observations, detector D6 · NASA/IPAC IRSA"],
    ["#guide-dialog li:nth-child(1) strong", "Choose data."],
    ["#guide-dialog li:nth-child(1)", "Use the WISE 0855 sample or search IRSA by coordinate."],
    ["#guide-dialog li:nth-child(2) strong", "Compare images."],
    ["#guide-dialog li:nth-child(2)", "Choose two observations in A/B, or open the Timeline and play when compatible frames are available. Drag an image or the blue box in the overview to move around."],
    ["#guide-dialog li:nth-child(3) strong", "Inspect."],
    ["#guide-dialog li:nth-child(3)", "Check the source, mask and limits. Motion requires further evidence."],
    ["#guide-dialog li:nth-child(4) strong", "Record notes."],
    ["#guide-dialog li:nth-child(4)", "WISE reviews follow the region and analysis version. IRSA notes export to JSON with the image pair."],
    ["#guide-dialog .guide-layout p", "Zoom enlarges the displayed pixels. The markers and ellipse come from an exploratory analysis with uncalibrated uncertainty."],
    ["#guide-start", "Return to comparison"],
    ["#evidence-title", "Sample data and limitations"],
    ["#evidence-dialog > p", "Observed SPHEREx QR2 cutouts. The highlighted regions come from conventional image processing."],
    ["#download-fits", "Download aligned FITS"],
    ["#evidence-dialog > h3", "Original documentation"],
    ["#evidence-dialog li:nth-child(1) a", "IRSA: cutouts and spectral WCS"],
    ["#evidence-dialog li:nth-child(2) a", "IRSA: PSFs by position and data release"],
    ["#evidence-dialog li:nth-child(3) a", "Luhman 2014: WISE 0855 astrometry and proper motion"],
  ];

  const attributes = [
    ["#main-nav", "aria-label", "Main navigation"],
    [".workflow-steps", "aria-label", "Observation workflow"],
    [".workflow-source-switch", "aria-label", "Data source"],
    ["#workflow-dataset-before", "alt", "Earlier SPHEREx coadd"],
    ["#workflow-dataset-after", "alt", "Later SPHEREx coadd"],
    ["#scene-select", "aria-label", "Image set"],
    ["#scene-list", "aria-label", "Image pairs"],
    ["#workspace .observation", "aria-label", "Astronomical image comparison"],
    ["#workspace .view-switch", "aria-label", "View mode"],
    ["#reset-view", "aria-label", "Reset view"],
    ["#reset-view", "title", "Reset view"],
    ["#workspace canvas#sky", "aria-label", "Aligned SPHEREx images before and after. Use the residual list to select a region and the controls below to compare images."],
    ["#wipe", "aria-label", "Comparison slider position"],
    ["#workspace .inspector", "aria-label", "Inspect and review"],
    ["#explorer-frames", "aria-label", "Observations"],
    ["#motion-chart", "aria-label", "Exploratory vector and external prediction with an uncalibrated nominal 68 percent ellipse"],
    ["#workflow-review-image", "alt", "Image from the dataset under review"],
    ["#review-note", "placeholder", "Record what you see in the two images…"],
    ["#explorer-note", "placeholder", "Note a region to revisit or something you’re unsure about."],
    ["#workflow-report-nav", "aria-label", "Open research report"],
    ["#workflow-research-index, #workflow-reports", "lang", "vi"],
    ["#guide-close", "aria-label", "Close guide"],
    ["#guide-dialog img", "alt", "Side-by-side comparison of the Epsilon Indi B field"],
    ["#evidence-close", "aria-label", "Close evidence dialog"],
    ["#evidence-content", "lang", "vi"],
  ];

  const workspaceContent = "#workflow-main, .workflow-header, .workflow-sidebar, .skip-link.legacy-surface, #guide-dialog, #evidence-dialog";
  let bindings;

  function scopedElements(selector) {
    return [...document.querySelectorAll(selector)].filter((element) => element.closest(workspaceContent));
  }

  function capture() {
    const translated = [];
    for (const [selector, english, textIndex=0] of copy) {
      for (const element of scopedElements(selector)) {
        const text = [...element.childNodes].filter((node) => node.nodeType === 3 && node.nodeValue.trim())[textIndex];
        if (!text) continue;
        const original = text.nodeValue;
        const spacing = {before: original.match(/^\s*/)[0], after: original.match(/\s*$/)[0]};
        translated.push({
          original,
          english: spacing.before + english + spacing.after,
          read: () => text.nodeValue,
          write: (value) => { text.nodeValue = value; },
        });
      }
    }
    for (const [selector, attribute, english] of attributes) {
      for (const element of scopedElements(selector)) {
        translated.push({
          original: element.getAttribute(attribute),
          english,
          read: () => element.getAttribute(attribute),
          write: (value) => value === null ? element.removeAttribute(attribute) : element.setAttribute(attribute, value),
        });
      }
    }
    return translated;
  }

  window.SpherexWorkspaceLanguage = {
    apply(language) {
      if (!bindings) bindings = capture();
      const english = String(language || document.documentElement.lang).toLowerCase().startsWith("en");
      for (const binding of bindings) {
        const value = binding.read();
        if (value === binding.original || value === binding.english) {
          const next = english ? binding.english : binding.original;
          if (value !== next) binding.write(next);
        }
      }
    },
  };
})();

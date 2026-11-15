(() => {
  "use strict";
  const el = (id) => document.getElementById(id);
  const t = (key) => window.SpherexSite.text(key);
  const pageSet = new Set(["orbit", "about", "night-sky", "learn"]);
  const workbenchPages = new Set(["home", "explore", "compare-step", "check-step", "review-step", "research"]);
  const pages = [...document.querySelectorAll("[data-public-page]")];
  const site = el("public-site");
  const orbit = el("orbit");
  const media = matchMedia("(prefers-reduced-motion: reduce)");
  const compactSky = matchMedia("(max-width: 620px)");
  const field = el("sky-field");
  const preview = el("sky-field-image");
  const expanded = el("sky-image-expanded");
  const search = el("sky-target-search");
  const dialog = el("sky-image-dialog");
  const learnQr = el("learn-qr-dialog");
  const workspaceScripts = [
    "review-store.js?v=0.10.0-r11", "draft-store.js?v=0.11.1-r18", "app.js?v=0.11.1-r20",
    "mission.js?v=0.11.0-r17", "benchmark.js?v=0.10.0-r11", "quality.js?v=0.11.0-r17",
    "covariance.js?v=0.10.0-r11", "ablation.js?v=0.10.0-r11", "linked-comparison.js?v=2", "explorer.js?v=0.14.0",
    "goal-dashboard.js?v=0.10.0-r11", "linked-evidence.js?v=0.10.0-r11",
    "neighbor-evidence.js?v=0.10.0-r11", "reference-evidence.js?v=0.10.0-r11",
    "calibration-evidence.js?v=0.10.0-r12", "profile-evidence.js?v=0.10.0-r13",
    "signal-evidence.js?v=0.10.0-r14", "data-links.js?v=0.11.1-r19", "navigation.js?v=0.12.0-r4"
  ];
  let motionPaused = false;
  let orbitLoading;
  let aboutLoading;
  let scienceLoading;
  let learnLoading;
  let gagooLoading;
  let gagoo;
  let gagooEntering = false;
  let titleAnimation = 0;
  let titleShown = false;
  const arrivalKey = "spherex.curtain";
  const wipeCovered = "polygon(0 0, 130% 0, 100% 100%, -30% 100%)";
  const wipeStart = "polygon(0 0, 0 0, -30% 100%, -30% 100%)";
  const wipeEnd = "polygon(130% 0, 130% 0, 100% 100%, 100% 100%)";
  let transitioning = false;
  let arrival;
  let historyTraversal = 0;
  let posterFrame = 0;
  let archivedPlayer;
  let guidedComparison;
  let orbitRefresh;
  let skyLoading;
  let dome;
  let currentPage;
  let workspaceLoading;
  let fields = [];
  let selected;
  let previewState = "loading";

  function newButton(text, className) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = text;
    return button;
  }

  function publicPage() {
    const hash = location.hash.slice(1);
    if (hash === "field-guide") return "orbit";
    if (hash === "about-story-title" || /^ss-\d+-[a-z-]+$/.test(hash)) return "about";
    const owner = el(hash)?.closest("section[data-public-page]");
    if (owner) return owner.id;
    const query = new URL(location.href).searchParams;
    return pageSet.has(hash) ? hash : !hash && !query.has("sky_ra") && !query.has("flow_source") ? "orbit" : null;
  }

  function updateMotion() {
    const paused = motionPaused || media.matches;
    orbit.dataset.motion = paused ? "paused" : "running";
    el("orbit-motion").hidden = media.matches;
    el("orbit-motion").setAttribute("aria-pressed", String(paused));
    el("orbit-motion").textContent = t(paused ? "resumeMotion" : "pauseMotion");
    orbitRefresh?.();
    gagoo?.refresh();
    if (paused) showTitle();
  }

  function showTitle() {
    if (titleAnimation) cancelAnimationFrame(titleAnimation);
    titleAnimation = 0;
    el("orbit-title-full").classList.remove("title-measure");
    el("orbit-title-typed").hidden = true;
    el("orbit-title-typed").textContent = "";
  }

  function typeTitle() {
    const full = el("orbit-title-full");
    const typed = el("orbit-title-typed");
    if (titleShown || media.matches || motionPaused) return;
    titleShown = true;
    const clusters = typeof Intl.Segmenter === "function"
      ? [...new Intl.Segmenter(window.SpherexSite.language(), {granularity: "grapheme"}).segment(t("brand"))].map((part) => part.segment)
      : Array.from(t("brand"));
    full.classList.add("title-measure");
    typed.hidden = false;
    const start = performance.now() - 110;
    function tick(time) {
      const length = Math.max(1, Math.floor((time - start) / 42));
      typed.textContent = clusters.slice(0, length).join("");
      if (length < clusters.length && currentPage === "orbit") titleAnimation = requestAnimationFrame(tick);
      else showTitle();
    }
    titleAnimation = requestAnimationFrame(tick);
  }

  function updatePoster() {
    posterFrame = 0;
    if (currentPage !== "orbit" || media.matches) return;
    const poster = site.querySelector(".poster-window");
    const bounds = poster.getBoundingClientRect();
    if (bounds.top > innerHeight + 100) return;
    const uncovered = Math.max(0, Math.min(1, (innerHeight - bounds.top) / bounds.height));
    poster.style.setProperty("--poster-offset", `${-64 * (1 - uncovered)}px`);
    poster.style.setProperty("--poster-opacity", (0.55 + 0.45 * uncovered).toFixed(3));
  }

  function schedulePoster() {
    if (!posterFrame && currentPage === "orbit") posterFrame = requestAnimationFrame(updatePoster);
  }

  function animateCurtain(from, to, duration) {
    const curtain = el("public-iris");
    curtain.hidden = false;
    curtain.style.clipPath = to;
    const animation = curtain.animate([{clipPath: from}, {clipPath: to}], {
      duration, easing: "cubic-bezier(.45,.05,.27,1)", fill: "both"
    });
    return animation.finished.finally(() => animation.cancel());
  }

  function closeCurtain() {
    const curtain = el("public-iris");
    curtain.hidden = true;
    curtain.style.removeProperty("clip-path");
    transitioning = false;
  }

  async function transitionTo(url, irisOrigin) {
    if (arrival) await arrival;
    if (transitioning) return;
    const traversal = historyTraversal;
    const reload = Boolean(publicPage()) !== (pageSet.has(url.hash.slice(1)) || url.hash === "#field-guide")
      && !irisOrigin && url.search !== location.search;
    const go = () => {
      if (reload) { location.assign(url); return; }
      if (irisOrigin) titleShown = false;
      const oldURL = location.href;
      if (url.href !== oldURL) {
        history.pushState(null, "", url);
        window.dispatchEvent(new HashChangeEvent("hashchange", {oldURL, newURL: url.href}));
      } else if (irisOrigin) step(true);
    };
    if (media.matches || typeof el("public-iris").animate !== "function") { go(); return; }
    let start = wipeStart, covered = wipeCovered, end = wipeEnd;
    if (irisOrigin) {
      const {x, y} = irisOrigin;
      const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)) + 8;
      start = end = `circle(0px at ${x}px ${y}px)`;
      covered = `circle(${r}px at ${x}px ${y}px)`;
    }
    transitioning = true;
    let leaving = false;
    try {
      await animateCurtain(start, covered, 420);
      if (historyTraversal !== traversal) return;
      if (reload) {
        try { sessionStorage.setItem(arrivalKey, url.href); } catch { /* Arrival can render directly. */ }
        leaving = true;
      }
      go();
      if (!leaving) await animateCurtain(covered, end, 580);
    } finally {
      if (!leaving) closeCurtain();
    }
  }

  window.SpherexTransition = (id) => {
    const url = new URL(location.href);
    url.hash = id;
    return transitionTo(url, null);
  };

  function revealArrival() {
    try {
      if (sessionStorage.getItem(arrivalKey) !== location.href) return;
      sessionStorage.removeItem(arrivalKey);
    } catch { return; }
    if (media.matches || typeof el("public-iris").animate !== "function") return;
    arrival = animateCurtain(wipeCovered, wipeEnd, 580).finally(() => {
      arrival = undefined;
      closeCurtain();
    });
  }

  function startOrbit() {
    if (!orbitLoading) {
      orbitLoading = import("./orbit-scene.js?v=2").then(({mountOrbit}) => mountOrbit({
        canvas: el("spacecraft-canvas"),
        target: orbit.querySelector(".spacecraft-target"),
        orbit,
        reduced: media,
        isActive: () => currentPage === "orbit",
        isPaused: () => motionPaused
      })).then((refresh) => { orbitRefresh = refresh; }).catch(() => { orbit.dataset.model = "poster"; });
    }
    orbitRefresh?.();
    startGagoo();
  }

  function openLearn() {
    const url = new URL(location.href);
    url.hash = "learn";
    const oldURL = location.href;
    history.pushState(null, "", url);
    window.dispatchEvent(new HashChangeEvent("hashchange", {oldURL, newURL: url.href}));
  }

  async function enterLearn() {
    if (gagooEntering || transitioning || currentPage !== "orbit") return;
    const homeSnapshot = gagoo?.snapshot?.();
    gagooEntering = true;
    gagoo?.refresh();
    try {
      const {playGagooEntrance} = await import("./gagoo-entrance.js?v=3");
      if (currentPage !== "orbit") return;
      await playGagooEntrance({
        reduced: media,
        language: window.SpherexSite.language(),
        home: {element: orbit, actorTarget: el("gagoo-target"), snapshot: homeSnapshot},
        onCovered: () => { if (currentPage === "orbit") openLearn(); }
      });
    } catch {
      // An optional visual effect must never block the learning entrance.
      if (currentPage === "orbit") openLearn();
    } finally {
      gagooEntering = false;
      gagoo?.refresh();
      if (currentPage === "learn") el("learn-title").focus({preventScroll: true});
    }
  }

  function startGagoo() {
    if (!gagooLoading) {
      gagooLoading = import("./gagoo-scene.js?v=3").then(({mountGagoo}) => mountGagoo({
        canvas: el("gagoo-canvas"), target: el("gagoo-target"), stage: orbit,
        reduced: media,
        isActive: () => currentPage === "orbit" && !gagooEntering,
        isPaused: () => motionPaused,
        onActivate: enterLearn
      })).then((controller) => { gagoo = controller; gagoo.refresh(); }).catch(() => {
        const target = el("gagoo-target");
        target.dataset.model = "fallback";
        target.addEventListener("click", (event) => {
          event.preventDefault();
          const touch = event.pointerType === "touch" || event.sourceCapabilities?.firesTouchEvents;
          if (touch && !target.hasAttribute("data-tap-preview")) {
            orbit.querySelector("[data-tap-preview]")?.removeAttribute("data-tap-preview");
            target.setAttribute("data-tap-preview", "true");
          } else enterLearn();
        });
      });
    }
    gagoo?.refresh();
  }

  function startWorkspace() {
    if (workspaceLoading) return workspaceLoading;
    const progress = el("workspace-progress");
    progress.hidden = false;
    progress.dataset.copy = "workspaceLoading";
    progress.textContent = t("workspaceLoading");
    workspaceLoading = Promise.all(workspaceScripts.map((source) => new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.async = false;
      script.src = source;
      script.onload = resolve;
      script.onerror = reject;
      document.head.append(script);
    }))).then(() => {
      progress.hidden = true;
      document.dispatchEvent(new Event("spherex:workspace-ready"));
    }).catch(() => {
      progress.dataset.copy = "workspaceError";
      progress.textContent = t("workspaceError");
      const reload = document.createElement("button");
      reload.type = "button";
      reload.className = "outline-button";
      reload.dataset.copy = "reloadPage";
      reload.textContent = t("reloadPage");
      reload.addEventListener("click", () => location.reload());
      progress.after(reload);
    });
    return workspaceLoading;
  }

  async function localJson(path) {
    const response = await fetch(path, {signal: AbortSignal.timeout(15000)});
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function searchLink(target, mode) {
    const url = new URL(location.href);
    url.search = "";
    url.hash = "explore";
    url.searchParams.set("lang", window.SpherexSite.language());
    if (target) {
      const {ra, dec, fov} = target;
      url.searchParams.set("sky_ra", ra);
      url.searchParams.set("sky_dec", dec);
      url.searchParams.set("sky_fov", fov);
      url.searchParams.set("sky_det", "6");
      url.searchParams.set("sky_release", "dr1");
      url.searchParams.set("sky_autoload", "1");
      if (mode) url.searchParams.set("sky_view", mode);
      if (target.id) url.searchParams.set("from_field", target.id);
      else url.searchParams.set("from_sky", "1");
      if (target.id === "epsilon") {
        url.searchParams.set("sky_sequence", "epsilon-dr1");
        url.searchParams.set("sky_from", "2025-04-29");
        url.searchParams.set("sky_to", "2025-05-07");
      }
    }
    return url;
  }

  function getFieldDisplay(target) {
    const full = target.observation;
    return {image: full.image, release: full.release, detector: full.detector, mjd: full.mjd, obsId: full.obs_id,
      original: full.original_url, date: full.timesys === "UTC" ? full.date_obs : null,
      x: full.target_x, y: full.target_y};
  }

  function updateFieldText() {
    if (!selected) return;
    const display = getFieldDisplay(selected);
    const isEnglish = window.SpherexSite.language() === "en";
    const time = Number.isFinite(display.mjd) ? `MJD ${display.mjd.toFixed(5)}` : "";
    const date = display.date ? `${display.date.slice(0, 19).replace("T", " ")} UTC` : time;
    el("sky-field-title").textContent = selected.name;
    el("sky-field-when").textContent = [display.release.toUpperCase(), `D${display.detector}`, date, display.obsId].filter(Boolean).join(" · ");
    el("sky-field-coordinates").textContent = `ICRS · RA ${selected.ra.toFixed(5)}° · Dec ${selected.dec.toFixed(5)}°`;
    const alt = isEnglish ? `SPHEREx image of the ${selected.name} field` : `Ảnh SPHEREx của vùng ${selected.name}`;
    preview.alt = expanded.alt = alt;
    el("sky-image-caption").textContent = el("sky-field-when").textContent;
    el("sky-image-title").textContent = selected.name;
    el("sky-field-status").textContent = previewState === "loading" ? t("loadingPreview") : previewState === "error" ? t("previewUnavailable") : "";
    el("sky-field-note").textContent = t("fullFieldLimit");
    el("sky-field-original").href = display.original;
    el("sky-field-compare").href = searchLink(selected, "compare");
    el("sky-field-timeline").href = searchLink(selected, "timeline");
    el("sky-field-example").hidden = selected.id !== "epsilon";
    const inFrame = Number.isFinite(display.x) && Number.isFinite(display.y) && display.x >= 0 && display.x <= 1 && display.y >= 0 && display.y <= 1;
    for (const id of ["sky-field-marker", "sky-image-marker"]) {
      const marker = el(id);
      marker.hidden = !inFrame;
      if (inFrame) {
        marker.style.left = `${display.x * 100}%`;
        marker.style.top = `${display.y * 100}%`;
      }
    }
  }

  function showField(id, scroll = true) {
    const target = fields.find((item) => item.id === id);
    if (!target) return;
    const url = new URL(location.href);
    url.searchParams.set("field", target.id);
    history.replaceState(history.state, "", url);
    selected = target;
    const display = getFieldDisplay(target);
    dome?.lookAt(target);
    for (const item of fields) {
      item.marker.setAttribute("aria-pressed", String(item === target));
      item.choice.setAttribute("aria-pressed", String(item === target));
    }
    field.hidden = false;
    setSkySidebar(true);
    previewState = "loading";
    el("sky-image-enlarge").hidden = true;
    updateFieldText();
    preview.src = display.image;
    if (preview.complete && preview.naturalWidth) previewReady();
    if (scroll) {
      el("sky-field-title").focus({preventScroll: true});
      field.scrollIntoView({block: "nearest", behavior: "instant"});
    }
  }

  function setSkySidebar(open) {
    el("night-sky").dataset.sidebar = open ? "open" : "closed";
    el("sky-sidebar-toggle").setAttribute("aria-expanded", String(open));
  }

  function restoreSkyField() {
    const query = new URL(location.href).searchParams;
    const fieldId = query.get("field");
    if (fieldId && fields.length && currentPage === "night-sky") {
      showField(fieldId, false);
      if (fieldId === "epsilon" && query.get("view") === "saved") openSavedSequence();
    }
  }

  function previewReady() {
    previewState = "ready";
    el("sky-image-enlarge").hidden = false;
    updateFieldText();
  }

  function populate(entries) {
    fields = Object.entries(entries).map(([id, observation]) => {
      const {target: name, center_ra_deg: ra, center_dec_deg: dec, compare_fov_deg: fov} = observation;
      const marker = newButton("", "sky-marker");
      const star = document.createElement("b");
      star.setAttribute("aria-hidden", "true");
      star.textContent = "✦";
      const label = document.createElement("span");
      label.textContent = name;
      marker.append(star, label);
      marker.setAttribute("aria-pressed", "false");
      marker.hidden = true;
      el("sky-markers").append(marker);
      const choice = newButton("", "sky-target-choice");
      const icon = document.createElement("span");
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = "✦";
      choice.append(icon, document.createTextNode(name));
      choice.setAttribute("aria-pressed", "false");
      choice.addEventListener("click", () => showField(id));
      el("sky-targets").append(choice);
      return {id, name, ra, dec, fov, marker, choice, observation};
    });
    if (!fields.length) throw new Error("Empty target catalog");
  }

  async function loadSky() {
    const status = el("sky-target-status");
    el("sky-retry")?.remove();
    status.hidden = false;
    status.dataset.copy = "loadingFields";
    status.textContent = t("loadingFields");
    try {
      const data = await localJson("assets/mission/full-fields/provenance.json");
      populate(data.fields);
    } catch {
      status.dataset.copy = "fieldsUnavailable";
      status.textContent = t("fieldsUnavailable");
      skyLoading = null;
      const retry = document.createElement("button");
      retry.id = "sky-retry";
      retry.type = "button";
      retry.className = "outline-button";
      retry.dataset.copy = "retryFields";
      retry.textContent = t("retryFields");
      retry.addEventListener("click", () => { if (!skyLoading) skyLoading = loadSky(); });
      status.after(retry);
      return;
    }
    status.hidden = true;
    try {
      const {mountSkyDome} = await import("./sky-dome.js");
      dome = mountSkyDome({
        canvas: el("sky-dome"),
        markers: fields.map((target) => ({...target, button: target.marker})),
        readout: el("sky-readout"),
        buttons: {out: el("sky-out"), in: el("sky-in"), reset: el("sky-reset")},
        onPick: showField,
        onMove: ({ra, dec}) => {
          const link = el("sky-center-search");
          link.hidden = false;
          link.href = searchLink({ra, dec, fov: .06});
        },
        start: {ra: 109, dec: 4}
      });
    } catch {
      el("sky-guide").dataset.copy = "skyFallback";
      el("sky-guide").textContent = t("skyFallback");
      for (const id of ["sky-in", "sky-out", "sky-reset"]) el(id).disabled = true;
    }
    restoreSkyField();
  }

  function startLearn() {
    if (learnLoading) return;
    const status = el("learn-load-status");
    const retry = el("learn-load-retry");
    const showStatus = (key) => {
      status.dataset.copy = key;
      status.textContent = t(key);
    };
    showStatus("learnLoading");
    retry.hidden = true;
    learnLoading = import("./learn.js?v=1")
      .then(({mountLearn}) => {
        mountLearn(el("learn"), window.SpherexSite.language);
        status.hidden = true;
      })
      .catch(() => {
        learnLoading = null;
        showStatus("learnError");
        retry.hidden = false;
      });
  }

  function step(focus = false) {
    const next = publicPage();
    const sectionHash = location.hash.slice(1);
    const aboutSection = next === "about" && sectionHash !== "about";
    currentPage = next;
    gagoo?.refresh();
    const isPublic = Boolean(next);
    document.body.classList.toggle("public-mode", isPublic);
    document.body.dataset.publicPage = next || "";
    site.hidden = !isPublic;
    el("orbit-extras").hidden = next !== "orbit";
    if (next !== "orbit") showTitle();
    for (const page of pages) page.hidden = page.id !== next;
    if (!isPublic) {
      startWorkspace();
      return;
    }
    window.SkyApp?.pause();
    window.SkyExplorer?.pause();
    refreshText();
    if (next === "orbit") { startOrbit(); typeTitle(); schedulePoster(); }
    if (next === "learn") startLearn();
    if (next === "about") {
      if (!aboutLoading) aboutLoading = import("./about-story.js?v=3")
        .then(({mountAboutStory}) => mountAboutStory(el("about")))
        .catch(() => { aboutLoading = null; });
      if (!scienceLoading) scienceLoading = import("./spherex-science.js?v=1")
        .then(() => window.SpherexScience?.mount(el("spherex-science")))
        .catch(() => { scienceLoading = null; });
      if (aboutSection) Promise.all([aboutLoading, scienceLoading]).then(() => {
        if (currentPage !== "about" || location.hash.slice(1) !== sectionHash) return;
        const section = el(sectionHash);
        if (!section) return;
        section.scrollIntoView({block: "start", behavior: "instant"});
        if (focus) { section.setAttribute("tabindex", "-1"); section.focus({preventScroll: true}); }
      });
    }
    if (next === "night-sky") {
      if (!skyLoading) skyLoading = loadSky();
      else restoreSkyField();
      dome?.refresh();
    }
    if (location.hash === "#field-guide") {
      el("field-guide").scrollIntoView({block: "start"});
      if (focus) el("field-guide").focus({preventScroll: true});
    } else if (focus && !aboutSection) {
      el(next).querySelector("h1").focus({preventScroll: true});
      window.scrollTo({top: 0, behavior: "instant"});
    }
  }

  function refreshText() {
    updateMotion();
    el("sky-coordinates").href = searchLink();
    const center = dome?.coordinates();
    if (center) el("sky-center-search").href = searchLink({...center, fov: .06});
    updateFieldText();
    if (!currentPage) return;
    const titleKey = currentPage === "about" ? "aboutTitle" : currentPage === "learn" ? "learnTitle" : "skyTitle";
    const title = currentPage === "orbit" ? t("brand") : `${t(titleKey)} · ${t("brand")}`;
    const headerBrand = site.querySelector(".public-brand [data-copy]");
    headerBrand.dataset.copy = currentPage === "learn" ? "learnTitle" : "brand";
    headerBrand.textContent = t(headerBrand.dataset.copy);
    document.title = title;
  }

  el("learn-load-retry").addEventListener("click", () => location.reload());
  el("orbit-motion").addEventListener("click", () => { motionPaused = !motionPaused; updateMotion(); });
  el("sky-sidebar-toggle").addEventListener("click", () => {
    const expanded = el("sky-sidebar-toggle").getAttribute("aria-expanded") === "true";
    setSkySidebar(!expanded);
    if (!expanded && compactSky.matches) el("sky-sidebar").focus();
  });
  el("sky-sidebar-close").addEventListener("click", () => {
    setSkySidebar(false);
    el("sky-sidebar-toggle").focus();
  });
  el("sky-sidebar").addEventListener("keydown", (event) => {
    if (event.key === "Escape" && compactSky.matches && !event.defaultPrevented) {
      setSkySidebar(false);
      el("sky-sidebar-toggle").focus();
    }
  });
  document.addEventListener("click", (event) => {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    const anchor = event.target.closest?.("a[href]");
    const object = anchor?.matches(".spacecraft-target, .earth-target") ? anchor : null;
    const touch = event.pointerType === "touch" || event.sourceCapabilities?.firesTouchEvents;
    if (touch && object && !object.hasAttribute("data-tap-preview")) {
      event.preventDefault();
      orbit.querySelector("[data-tap-preview]")?.removeAttribute("data-tap-preview");
      object.setAttribute("data-tap-preview", "");
      return;
    }
    orbit.querySelector("[data-tap-preview]")?.removeAttribute("data-tap-preview");
    if (!anchor || anchor.target || anchor.hasAttribute("download")) return;
    const url = new URL(anchor.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname) return;
    const iris = anchor.hasAttribute("data-iris-home");
    const destination = url.hash.slice(1);
    if (!iris && !pageSet.has(destination) && !workbenchPages.has(destination)) return;
    if (!iris && url.hash === location.hash && url.search === location.search) return;
    if (!currentPage && url.hash === "#night-sky" && !url.searchParams.has("view")) {
      const fieldId = url.searchParams.get("from_field");
      url.search = "";
      url.searchParams.set("lang", window.SpherexSite.language());
      if (fieldId) url.searchParams.set("field", fieldId);
    }
    if (iris) {
      url.search = "";
      url.searchParams.set("lang", window.SpherexSite.language());
    }
    const bounds = anchor.getBoundingClientRect();
    const origin = iris ? {
      x: event.detail ? event.clientX : bounds.left + bounds.width / 2,
      y: event.detail ? event.clientY : bounds.top + bounds.height / 2
    } : null;
    event.preventDefault();
    transitionTo(url, origin);
  });
  media.addEventListener("change", updateMotion);
  window.addEventListener("popstate", () => { historyTraversal++; });
  window.addEventListener("scroll", schedulePoster, {passive: true});
  window.addEventListener("resize", schedulePoster);
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      closeCurtain();
      const urlLanguage = new URL(location.href).searchParams.get("lang");
      if (urlLanguage) window.SpherexSite.apply(urlLanguage);
      step();
    }
  });
  search.addEventListener("input", () => {
    const normalize = (value) => value.normalize("NFKD").toLowerCase().replace(/[\u0300-\u036f’']/g, "");
    const term = normalize(search.value.trim()).replaceAll("ε", "epsilon");
    let total = 0;
    for (const target of fields) {
      const match = normalize(target.name).includes(term);
      target.choice.hidden = !match;
      if (match) total++;
    }
    el("sky-target-empty").hidden = !fields.length || total > 0;
  });
  preview.addEventListener("load", previewReady);
  preview.addEventListener("error", () => {
    previewState = "error";
    el("sky-image-enlarge").hidden = true;
    updateFieldText();
  });
  el("sky-image-enlarge").addEventListener("click", () => {
    expanded.src = preview.src;
    dialog.showModal();
  });
  el("sky-image-close").addEventListener("click", () => dialog.close());
  el("guided-open").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    const output = el("guided-open-status");
    button.disabled = true;
    output.textContent = "";
    try {
      if (!guidedComparison) {
        const {mountGuidedComparison} = await import("./guided-comparison.js");
        guidedComparison = mountGuidedComparison(t, window.SpherexSite.language);
      }
      if (currentPage === "orbit") guidedComparison();
    } catch {
      output.textContent = t("guidedError");
    } finally { button.disabled = false; }
  });
  async function openSavedSequence() {
    const button = el("sky-field-example");
    if (button.disabled) return;
    button.disabled = true;
    try {
      if (!archivedPlayer) {
        const {mountArchivedSequence} = await import("./archived-sequence.js");
        archivedPlayer = mountArchivedSequence({dialog: el("archived-sequence"), translate: t});
      }
      if (currentPage === "night-sky") archivedPlayer();
    } catch {
      el("sky-field-status").textContent = t("archivedError");
    } finally {
      button.disabled = false;
    }
  }
  el("sky-field-example").addEventListener("click", openSavedSequence);
  el("learn-qr-open").addEventListener("click", () => learnQr.showModal());
  site.querySelector(".skip-link").addEventListener("click", (event) => {
    event.preventDefault();
    el("public-main").focus();
  });
  document.addEventListener("spherex:language", () => { refreshText(); if (titleAnimation) showTitle(); });
  window.addEventListener("hashchange", () => {
    if (dialog.open) dialog.close();
    if (learnQr.open) learnQr.close();
    if (el("archived-sequence").open) el("archived-sequence").close();
    if (el("guided-activity").open) el("guided-activity").close();
    step(true);
  });
  step();
  revealArrival();
})();

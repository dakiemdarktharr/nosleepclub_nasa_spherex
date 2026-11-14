(() => {
  "use strict";
  const el = (id) => document.getElementById(id);
  const t = (key) => window.SpherexSite.text(key);
  const pageSet = new Set(["orbit", "about", "night-sky"]);
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
  const workspaceScripts = [
    "review-store.js?v=0.10.0-r11", "draft-store.js?v=0.11.1-r18", "app.js?v=0.11.1-r19",
    "mission.js?v=0.11.0-r17", "benchmark.js?v=0.10.0-r11", "quality.js?v=0.11.0-r17",
    "covariance.js?v=0.10.0-r11", "ablation.js?v=0.10.0-r11", "linked-comparison.js?v=1", "explorer.js?v=0.13.0",
    "goal-dashboard.js?v=0.10.0-r11", "linked-evidence.js?v=0.10.0-r11",
    "neighbor-evidence.js?v=0.10.0-r11", "reference-evidence.js?v=0.10.0-r11",
    "calibration-evidence.js?v=0.10.0-r12", "profile-evidence.js?v=0.10.0-r13",
    "signal-evidence.js?v=0.10.0-r14", "data-links.js?v=0.11.1-r19", "navigation.js?v=0.12.0-r2"
  ];
  let motionPaused = false;
  let orbitLoading;
  let aboutLoading;
  let titleAnimation = 0;
  let titleShown = false;
  let irising = false;
  let posterFrame = 0;
  let archivedPlayer;
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

  async function irisHome(event) {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
    event.preventDefault();
    if (irising) return;
    if (media.matches || typeof el("public-iris").animate !== "function") {
      if (location.hash === "#orbit") step(true);
      else location.hash = "orbit";
      return;
    }
    irising = true;
    const curtain = el("public-iris");
    const bounds = event.currentTarget.getBoundingClientRect();
    const x = event.detail ? event.clientX : bounds.left + bounds.width / 2;
    const y = event.detail ? event.clientY : bounds.top + bounds.height / 2;
    const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y)) + 8;
    const closed = `circle(0px at ${x}px ${y}px)`;
    const open = `circle(${r}px at ${x}px ${y}px)`;
    curtain.hidden = false;
    try {
      await curtain.animate([{clipPath: closed}, {clipPath: open}], {duration: 280, easing: "ease-in", fill: "forwards"}).finished;
      titleShown = false;
      if (location.hash !== "#orbit") {
        const url = new URL(location.href);
        url.hash = "orbit";
        history.pushState(null, "", url);
      }
      step(true);
      await curtain.animate([{clipPath: open}, {clipPath: closed}], {duration: 490, easing: "cubic-bezier(.25,.7,.3,1)", fill: "forwards"}).finished;
    } finally {
      for (const animation of curtain.getAnimations()) animation.cancel();
      curtain.hidden = true;
      irising = false;
    }
  }

  function startOrbit() {
    if (!orbitLoading) {
      orbitLoading = import("./orbit-scene.js").then(({mountOrbit}) => mountOrbit({
        canvas: el("spacecraft-canvas"),
        target: orbit.querySelector(".spacecraft-target"),
        orbit,
        reduced: media,
        isActive: () => currentPage === "orbit",
        isPaused: () => motionPaused
      })).then((refresh) => { orbitRefresh = refresh; }).catch(() => { orbit.dataset.model = "poster"; });
    }
    orbitRefresh?.();
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
    });
    return workspaceLoading;
  }

  async function localJson(path) {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function searchLink(target) {
    const url = new URL(location.pathname, location.href);
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
    el("sky-field-compare").href = searchLink(selected);
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
    status.dataset.copy = "loadingFields";
    status.textContent = t("loadingFields");
    try {
      const data = await localJson("assets/mission/full-fields/provenance.json");
      populate(data.fields);
    } catch {
      status.dataset.copy = "fieldsUnavailable";
      status.textContent = t("fieldsUnavailable");
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
      const fieldId = new URL(location.href).searchParams.get("field");
      if (fieldId && currentPage === "night-sky") showField(fieldId, false);
    } catch {
      el("sky-guide").dataset.copy = "skyFallback";
      el("sky-guide").textContent = t("skyFallback");
      for (const id of ["sky-in", "sky-out", "sky-reset"]) el(id).disabled = true;
    }
  }

  function step(focus = false) {
    const next = publicPage();
    currentPage = next;
    const isPublic = Boolean(next);
    document.body.classList.toggle("public-mode", isPublic);
    document.body.dataset.publicPage = next || "";
    site.hidden = !isPublic;
    el("orbit-extras").hidden = next !== "orbit";
    if (next !== "orbit") showTitle();
    for (const page of pages) page.hidden = page.id !== next;
    for (const anchor of site.querySelectorAll("[data-nav]")) {
      if (anchor.dataset.nav === next) anchor.setAttribute("aria-current", "page");
      else anchor.removeAttribute("aria-current");
    }
    if (!isPublic) {
      startWorkspace();
      return;
    }
    window.SkyApp?.pause();
    window.SkyExplorer?.pause();
    refreshText();
    if (next === "orbit") { startOrbit(); typeTitle(); schedulePoster(); }
    if (next === "about") {
      const aboutImage = el("about").querySelector("img[data-src]");
      aboutImage.alt = t("orbitImage");
      if (!aboutImage.getAttribute("src")) aboutImage.src = aboutImage.dataset.src;
      if (!aboutLoading) aboutLoading = import("./about-story.js")
        .then(({mountAboutStory}) => mountAboutStory(el("about")))
        .catch(() => { aboutLoading = null; });
    }
    if (next === "night-sky") {
      if (!skyLoading) skyLoading = loadSky();
      dome?.refresh();
    }
    if (location.hash === "#field-guide") {
      el("field-guide").scrollIntoView({block: "start"});
      if (focus) el("field-guide").focus({preventScroll: true});
    } else if (focus) {
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
    el("about").querySelector("img").alt = t("orbitImage");
    if (!currentPage) return;
    const title = currentPage === "orbit" ? t("brand") : `${t(currentPage === "about" ? "aboutTitle" : "skyTitle")} · ${t("brand")}`;
    document.title = title;
  }

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
  for (const anchor of document.querySelectorAll("[data-iris-home]")) anchor.addEventListener("click", irisHome);
  media.addEventListener("change", updateMotion);
  window.addEventListener("scroll", schedulePoster, {passive: true});
  window.addEventListener("resize", schedulePoster);
  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
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
  el("sky-field-example").addEventListener("click", async () => {
    const button = el("sky-field-example");
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
  });
  for (const anchor of document.querySelectorAll(".legacy-surface a[href='#night-sky']")) {
    anchor.addEventListener("click", (event) => {
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      const url = new URL(location.pathname, location.href);
      url.hash = "night-sky";
      url.searchParams.set("lang", window.SpherexSite.language());
      const fieldId = new URL(location.href).searchParams.get("from_field");
      if (fieldId) url.searchParams.set("field", fieldId);
      location.assign(url);
    });
  }
  site.querySelector(".skip-link").addEventListener("click", (event) => {
    event.preventDefault();
    el("public-main").focus();
  });
  document.addEventListener("spherex:language", () => { refreshText(); if (titleAnimation) showTitle(); });
  window.addEventListener("hashchange", () => {
    if (dialog.open) dialog.close();
    if (el("archived-sequence").open) el("archived-sequence").close();
    step(true);
  });
  step();
})();

const directory = new URL("./assets/mission/epsilon-sequence/", import.meta.url);
const notePrefix = "spherex.guided-note.v1.";

async function readJson(url) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export function mountGuidedComparison(translate, language) {
  const el = (id) => document.getElementById(id);
  const dialog = el("guided-activity");
  const opener = el("guided-open");
  const note = el("guided-note");
  const form = el("guided-form");
  const body = el("guided-body");
  let loading;
  let archive;
  let archiveUrl;
  let activity;
  let index = 0;
  let answer = "";
  let evaluated = false;
  let status;
  let noteStatus;
  const drafts = new Map();
  const archives = new Map();
  const local = (copy) => copy[language()];
  const current = () => activity.cases[index];
  const lookup = (id) => archive.observations.find((observation) => observation.obs_id === id);
  const noteKey = () => notePrefix + current().observations.join(".");

  function setStatus(next) {
    status = next;
    el("guided-status").textContent = next ? translate(next) : "";
  }

  function setNoteStatus(next) {
    noteStatus = next;
    el("guided-note-status").textContent = next ? translate(next) : "";
  }

  function restoreNote() {
    const key = noteKey();
    if (drafts.has(key)) return drafts.get(key);
    try { return JSON.parse(localStorage.getItem(key))?.note || ""; } catch { return ""; }
  }

  function evidence() {
    return {
      schema_version: 1,
      activity: current().id,
      recorded_at_utc: new Date().toISOString(),
      answer,
      note: note.value.trim(),
      target: archive.target,
      scope: archive.scope,
      ra_deg: archive.ra_deg,
      dec_deg: archive.dec_deg,
      coordinate_frame: archive.coordinate_frame,
      release: archive.release,
      detector: archive.detector,
      preview_verified_at_utc: archive.verified_at_utc,
      spectral_metadata: archive.spectral_metadata,
      processing: archive.settings,
      observations: current().observations.map(lookup)
    };
  }

  function renderEvidence() {
    const grid = el("guided-panes");
    grid.replaceChildren();
    const item = current();
    for (const [position, id] of item.observations.entries()) {
      const observation = lookup(id);
      const side = position === 0 ? "A" : "B";
      const frame = document.createElement("figure");
      const picture = document.createElement("div");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      const date = observation.date_obs.replace("T", " ").slice(0, 19);
      image.alt = `SPHEREx ${side} · ${date} UTC`;
      image.src = new URL(observation.image, archiveUrl).href;
      image.width = image.height = archive.settings.grid_size_px;
      caption.textContent = `${side} · ${date} UTC · ${observation.center_wavelength_um.toFixed(4)} µm`;
      picture.className = "guided-picture";
      picture.append(image);
      if (item.highlight) {
        const marker = document.createElement("span");
        marker.className = "guided-pixel";
        marker.setAttribute("aria-hidden", "true");
        marker.style.left = `${(item.highlight.x + .5) / archive.settings.grid_size_px * 100}%`;
        marker.style.top = `${(item.highlight.y + .5) / archive.settings.grid_size_px * 100}%`;
        picture.append(marker);
      }
      frame.append(picture, caption);
      grid.append(frame);
    }
  }

  function renderCopy() {
    if (body.hidden) { setStatus(status); return; }
    const item = current();
    el("guided-context").textContent = `${archive.target.replace(/ field$/, "")} · ${archive.release.toUpperCase()} D${archive.detector} · ${local(item.title)}`;
    el("guided-question").textContent = local(item.prompt);
    el("guided-limit").textContent = local(item.science_caveat ?? activity.science_caveat);
    for (const [position, option] of item.options.entries()) {
      el("guided-options").children[position].lastElementChild.textContent = local(option.label);
    }
    if (evaluated) {
      el("guided-result").textContent = translate(answer === item.answer ? "guidedCorrect" : "guidedExplain");
      el("guided-explanation").textContent = local(item.explanation);
    }
    setNoteStatus(noteStatus);
  }

  function showCase() {
    answer = "";
    evaluated = false;
    note.value = restoreNote();
    setNoteStatus("");
    el("guided-feedback").hidden = true;
    form.hidden = false;
    const options = el("guided-options");
    options.replaceChildren();
    for (const option of current().options) {
      const label = document.createElement("label");
      const input = document.createElement("input");
      Object.assign(input, {type: "radio", name: "guided-answer", value: option.id, required: true});
      label.append(input, document.createElement("span"));
      options.append(label);
    }
    renderEvidence();
    body.querySelector(".public-back").href = archiveUrl.href;
    renderCopy();
  }

  async function loadCase() {
    activity ??= await readJson(new URL("activities.json", directory));
    const item = current();
    archiveUrl = new URL(item.archive ?? "provenance.json", directory);
    archive = archives.get(archiveUrl.href) ?? await readJson(archiveUrl);
    const observations = item.observations.map(lookup);
    if (observations.length !== 2 || observations.some((observation) => !observation)) {
      throw new Error("Missing observation in activity");
    }
    await Promise.all(observations.map(({image}) => {
      const frame = new Image();
      frame.src = new URL(image, archiveUrl).href;
      return frame.decode();
    }));
    archives.set(archiveUrl.href, archive);
    setStatus("");
    body.hidden = false;
    showCase();
  }

  function start() {
    if (!dialog.open) dialog.showModal();
    el("guided-title").focus({preventScroll: true});
    if (!body.hidden) return;
    if (loading) return loading;
    el("guided-retry").hidden = true;
    setStatus("guidedLoading");
    loading = loadCase().catch(() => {
      body.hidden = true;
      setStatus("guidedError");
      el("guided-retry").hidden = false;
    }).finally(() => { loading = undefined; });
    return loading;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    answer = new FormData(form).get("guided-answer");
    if (!answer) return;
    evaluated = true;
    form.hidden = true;
    el("guided-feedback").hidden = false;
    renderCopy();
    el("guided-feedback").focus();
  });
  el("guided-save").addEventListener("click", () => {
    const record = evidence();
    drafts.set(noteKey(), record.note);
    try {
      localStorage.setItem(noteKey(), JSON.stringify(record));
      setNoteStatus("guidedSaved");
    } catch { setNoteStatus("guidedSaveError"); }
  });
  el("guided-export").addEventListener("click", () => {
    const href = URL.createObjectURL(new Blob([JSON.stringify(evidence(), null, 2)], {type: "application/json"}));
    const link = document.createElement("a");
    link.href = href;
    link.download = `spherex-${current().id}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
  });
  el("guided-next").addEventListener("click", () => {
    drafts.set(noteKey(), note.value);
    index = (index + 1) % activity.cases.length;
    body.hidden = true;
    start();
    dialog.scrollTop = 0;
  });
  el("guided-close").addEventListener("click", () => dialog.close());
  el("guided-retry").addEventListener("click", start);
  dialog.addEventListener("close", () => { if (!body.hidden) drafts.set(noteKey(), note.value); opener.focus(); });
  document.addEventListener("spherex:language", renderCopy);
  return start;
}

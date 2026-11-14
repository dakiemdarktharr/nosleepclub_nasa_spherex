export function mountArchivedSequence({dialog, translate}) {
  const el = (id) => document.getElementById(id);
  const play = el("archived-play");
  const previous = el("archived-prev");
  const next = el("archived-next");
  const frame = el("archived-frame");
  const timestamp = el("archived-time");
  const fits = el("archived-fits");
  const directory = new URL("./assets/mission/epsilon-sequence/", import.meta.url);
  let load;
  let observations = [];
  let index = 0;
  let timer;
  let failed = false;

  function render() {
    play.textContent = translate(timer ? "archivedPause" : "archivedPlay");
    if (!observations.length) {
      timestamp.textContent = translate(failed ? "archivedError" : "archivedLoading");
      return;
    }
    const observation = observations[index];
    frame.src = new URL(observation.image, directory).href;
    frame.hidden = false;
    const utc = observation.date_obs.replace("T", " ").slice(0, 19);
    const label = `${index + 1}/${observations.length} · ${utc} UTC · ${observation.obs_id}`;
    if (timestamp.textContent !== label) timestamp.textContent = label;
    frame.alt = `Epsilon Indi B · SPHEREx DR1 D6 · ${utc} UTC`;
    fits.href = observation.cutout_url;
    fits.hidden = false;
    play.disabled = previous.disabled = next.disabled = false;
  }

  function stop() {
    clearInterval(timer);
    timer = undefined;
  }

  function move(direction) {
    index = (index + direction + observations.length) % observations.length;
    render();
  }

  function preload(item) {
    const image = new Image();
    image.src = new URL(item.image, directory).href;
    return image.decode();
  }

  function open() {
    if (dialog.open) return;
    index = 0;
    dialog.showModal();
    render();
    if (!load) {
      failed = false;
      load = fetch(new URL("provenance.json", directory))
        .then((response) => {
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          return response.json();
        })
        .then(async (data) => {
          await Promise.all(data.observations.map(preload));
          observations = data.observations;
          render();
        })
        .catch(() => { load = undefined; failed = true; render(); });
    }
  }

  play.addEventListener("click", () => {
    if (timer) stop();
    else timer = setInterval(() => move(1), 1050);
    render();
  });
  previous.addEventListener("click", () => { stop(); move(-1); });
  next.addEventListener("click", () => { stop(); move(1); });
  el("archived-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("close", stop);
  document.addEventListener("visibilitychange", () => { if (document.hidden) { stop(); render(); } });
  document.addEventListener("spherex:language", () => { if (dialog.open) render(); });
  return open;
}

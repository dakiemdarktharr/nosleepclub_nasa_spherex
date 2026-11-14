/* Draw an inside-looking celestial panorama with RA increasing to the left. */
export function mountSkyDome({canvas, markers, readout, buttons, onPick, onMove, start}) {
  const deg = Math.PI / 180;
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const wrap = (n) => (n % 360 + 360) % 360;
  const vector = (ra, dec) => [Math.cos(dec) * Math.cos(ra), Math.cos(dec) * Math.sin(ra), Math.sin(dec)];
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const ctx = canvas.getContext("2d");
  const catalog = markers.map(({ra, dec, button}) => ({button, direction: vector(ra * deg, dec * deg)}));
  const texture = new Image();
  let pixels;
  let image;
  let frame = 0;
  let drag;
  let ra = start.ra;
  let dec = start.dec;
  let zoom = 1;
  let width = 0;
  let height = 0;
  let drawWidth = 0;
  let drawHeight = 0;
  const coordinates = () => ({ra, dec});
  const offscreen = document.createElement("canvas");
  const buffer = offscreen.getContext("2d");

  function basis() {
    const lon = ra * deg;
    const lat = dec * deg;
    return {
      front: vector(lon, lat),
      right: [Math.sin(lon), -Math.cos(lon), 0],
      up: [-Math.sin(lat) * Math.cos(lon), -Math.sin(lat) * Math.sin(lon), Math.cos(lat)],
      focal: Math.min(width, height) * .72 * zoom
    };
  }

  function drawPanorama(view) {
    ctx.fillStyle = "#050a15";
    ctx.fillRect(0, 0, width, height);
    if (!pixels || !image) return;
    const [fx, fy, fz] = view.front;
    const [rx, ry] = view.right;
    const [ux, uy, uz] = view.up;
    const {width: tw, height: th, data: source} = pixels;
    const output = image.data;
    for (let y = 0; y < drawHeight; y++) {
      const vertical = (.5 - (y + .5) / drawHeight) * height / view.focal;
      const ax = fx + ux * vertical;
      const ay = fy + uy * vertical;
      const az = fz + uz * vertical;
      for (let x = 0; x < drawWidth; x++) {
        const horizontal = ((x + .5) / drawWidth - .5) * width / view.focal;
        const gx = ax + rx * horizontal;
        const gy = ay + ry * horizontal;
        const lon = Math.atan2(gy, gx);
        const lat = Math.atan2(az, Math.hypot(gx, gy));
        // NASA SVS celestial plate carrée is centered on RA 0, north up.
        const a = Math.min(tw - 1, Math.floor((.5 - lon / (2 * Math.PI)) * tw));
        const b = clamp(Math.floor((.5 - lat / Math.PI) * th), 0, th - 1);
        const sample = (b * tw + a) * 4;
        const out = (y * drawWidth + x) * 4;
        output[out] = source[sample] + 3;
        output[out + 1] = source[sample + 1] + 5;
        output[out + 2] = source[sample + 2] + 11;
        output[out + 3] = 255;
      }
    }
    buffer.putImageData(image, 0, 0);
    ctx.drawImage(offscreen, 0, 0, width, height);
  }

  function draw() {
    frame = 0;
    const box = canvas.getBoundingClientRect();
    if (!box.width || !box.height) return;
    if (box.width !== width || box.height !== height) {
      width = box.width;
      height = box.height;
      const scale = Math.min(1, 550 / width, 310 / height);
      drawWidth = Math.max(1, Math.round(width * scale));
      drawHeight = Math.max(1, Math.round(height * scale));
      if (ctx && buffer) {
        canvas.width = Math.round(width);
        canvas.height = Math.round(height);
        offscreen.width = drawWidth;
        offscreen.height = drawHeight;
        image = buffer.createImageData(drawWidth, drawHeight);
      }
    }
    const view = basis();
    if (ctx && buffer) drawPanorama(view);
    for (const {button, direction} of catalog) {
      const z = dot(direction, view.front);
      const x = width / 2 + view.focal * dot(direction, view.right) / z;
      const y = height / 2 - view.focal * dot(direction, view.up) / z;
      button.hidden = z <= 0 || x < 14 || x > width - 14 || y < 14 || y > height - 14;
      if (!button.hidden) {
        button.style.left = `${x}px`;
        button.style.top = `${y}px`;
      }
    }
    readout.textContent = `RA ${ra.toFixed(2)}°  ·  Dec ${dec.toFixed(2)}°`;
    onMove(coordinates());
  }

  function refresh() {
    if (!frame) frame = requestAnimationFrame(draw);
  }

  function lookAt(target) {
    ra = wrap(target.ra);
    dec = target.dec;
    refresh();
  }

  function changeZoom(divisor) {
    zoom = clamp(zoom * divisor, .6, 3.6);
    refresh();
  }

  canvas.addEventListener("pointerdown", (event) => {
    if (!event.isPrimary || event.button !== 0) return;
    drag = {x: event.clientX, y: event.clientY, ra, dec};
    canvas.setPointerCapture(event.pointerId);
    canvas.classList.add("dragging");
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!event.isPrimary || !drag) return;
    const scale = 71 / (Math.max(120, Math.min(width, height)) * zoom);
    ra = wrap(drag.ra + (event.clientX - drag.x) * scale / Math.max(.28, Math.cos(dec * deg)));
    dec = clamp(drag.dec + (event.clientY - drag.y) * scale, -89.9, 89.9);
    refresh();
  });
  canvas.addEventListener("lostpointercapture", () => { drag = undefined; canvas.classList.remove("dragging"); });
  canvas.addEventListener("keydown", (event) => {
    const delta = 10 / zoom;
    switch (event.key) {
      case "ArrowLeft": ra = wrap(ra + delta); break;
      case "ArrowRight": ra = wrap(ra - delta); break;
      case "ArrowUp": dec = clamp(dec + delta, -89.9, 89.9); break;
      case "ArrowDown": dec = clamp(dec - delta, -89.9, 89.9); break;
      case "+": case "=": changeZoom(1.25); break;
      case "-": changeZoom(.8); break;
      case "Home": zoom = 1; lookAt(start); break;
      default: return;
    }
    event.preventDefault();
    refresh();
  });
  buttons.out.addEventListener("click", () => changeZoom(.8));
  buttons.in.addEventListener("click", () => changeZoom(1.25));
  buttons.reset.addEventListener("click", () => { zoom = 1; lookAt(start); });
  markers.forEach((target) => target.button.addEventListener("click", () => onPick(target.id)));
  new ResizeObserver(refresh).observe(canvas);
  texture.addEventListener("load", () => {
    const scratch = document.createElement("canvas");
    scratch.width = texture.naturalWidth;
    scratch.height = texture.naturalHeight;
    const source = scratch.getContext("2d", {willReadFrequently: true});
    if (!source) return;
    source.drawImage(texture, 0, 0);
    pixels = source.getImageData(0, 0, scratch.width, scratch.height);
    refresh();
  });
  texture.src = new URL("./assets/mission/celestial-sky.webp", import.meta.url).href;
  refresh();
  return {coordinates, lookAt, refresh};
}

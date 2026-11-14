// A local implementation of the cover/swap/reveal blinds pattern described at
// https://motion.dev/docs/curtains#blinds. No Motion+ code or service is required.
let activeEntrance;
const CINEMA_MS = 3100;
const clamp = (value) => Math.max(0, Math.min(1, value));
const smooth = (value) => value * value * (3 - 2 * value);
const mix = (a, b, progress) => a + (b - a) * progress;

export function sampleGagooEntrance(milliseconds, contactZ = 2.36) {
  const pullback = smooth(clamp(milliseconds / 850));
  const flight = clamp((milliseconds - 650) / 1150);
  const contact = clamp((milliseconds - 1800) / 220);
  const slide = clamp((milliseconds - 2020) / 1080);
  const impact = milliseconds >= 1800 && milliseconds < 2020 ? Math.sin(contact * Math.PI) : 0;
  return {
    cameraZ: mix(1.6, 7.7, pullback),
    x: Math.sin(flight * Math.PI) * .42 + slide * slide * .35,
    y: .12 - slide * slide * 5.4,
    z: mix(-7.5, contactZ, flight * flight),
    rotationZ: -.08 * Math.sin(flight * Math.PI) - slide * .34,
    rotationX: .12 * (1 - flight) + slide * .12,
    scaleX: 1 + impact * .07,
    scaleY: 1 - impact * .07,
    scaleZ: 1 - impact * .28,
    contact: milliseconds >= 1800,
    markOpacity: milliseconds < 1800 ? 0 : .12 * (1 - slide),
    phase: milliseconds < 850 ? "pullback" : milliseconds < 1800 ? "flight" : milliseconds < 2020 ? "contact" : "slide"
  };
}

function abortError() { return new DOMException("Entrance cancelled", "AbortError"); }
function reducedValue(value) {
  return typeof value === "boolean" ? value : Boolean(value?.matches);
}

function roundedPath(Three, width, height, radius) {
  const path = new Three.Shape();
  const x = -width / 2, y = -height / 2;
  path.moveTo(x + radius, y);
  path.lineTo(x + width - radius, y);
  path.quadraticCurveTo(x + width, y, x + width, y + radius);
  path.lineTo(x + width, y + height - radius);
  path.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  path.lineTo(x + radius, y + height);
  path.quadraticCurveTo(x, y + height, x, y + height - radius);
  path.lineTo(x, y + radius);
  path.quadraticCurveTo(x, y, x + radius, y);
  return path;
}

async function createCinema(canvas, signal) {
  const [Three, {createGagooModel}] = await Promise.all([
    import("./assets/three-0.187.0/three.module.js"), import("./gagoo-scene.js")
  ]);
  if (signal.aborted) throw abortError();
  const renderer = new Three.WebGLRenderer({canvas, alpha: false, antialias: true, powerPreference: "low-power"});
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
  renderer.setClearColor(0x08162e);
  renderer.toneMapping = Three.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  const scene = new Three.Scene();
  const camera = new Three.PerspectiveCamera(46, 1, .05, 80);
  const model = createGagooModel(Three);
  model.updateMatrixWorld(true);
  const modelBounds = new Three.Box3().setFromObject(model);
  const modelSize = modelBounds.getSize(new Three.Vector3());
  const helmetCenter = new Three.Box3().setFromObject(model.getObjectByName("clear polygonal helmet") || model.userData.head || model).getCenter(new Three.Vector3());
  const modelBaseScale = model.scale.clone();
  let modelFit = .77;
  let frontDepth = Math.max(.01, modelBounds.max.z * modelFit);
  let halfHeight = modelSize.y * modelFit / 2;
  const actor = new Three.Group();
  actor.add(model);
  model.scale.copy(modelBaseScale).multiplyScalar(modelFit);
  scene.add(actor);
  scene.add(new Three.HemisphereLight(0xdffaff, 0x14325c, 2.8));
  const key = new Three.DirectionalLight(0xffffff, 4);
  key.position.set(-4, 5, 7);
  scene.add(key);
  const rim = new Three.DirectionalLight(0x42e7ff, 2.7);
  rim.position.set(3, 1, -1);
  scene.add(rim);
  const cabin = new Three.Group();
  scene.add(cabin);
  const materials = [];
  const geometries = [];
  const material = (options) => { const item = new Three.MeshStandardMaterial(options); materials.push(item); return item; };
  const white = material({color: 0xe9f5f7, metalness: .38, roughness: .33});
  const navy = material({color: 0x14287b, metalness: .35, roughness: .4});
  const cyan = material({color: 0x22d6ed, emissive: 0x159bb4, emissiveIntensity: .45, metalness: .2, roughness: .4});
  const glassMaterial = new Three.MeshBasicMaterial({color: 0x8bedff, transparent: true, opacity: .035, depthWrite: false, side: Three.DoubleSide});
  const markMaterial = new Three.MeshBasicMaterial({color: 0xc3f8ff, transparent: true, opacity: 0, depthWrite: false});
  materials.push(glassMaterial, markMaterial);
  const mesh = (geometry, surface, parent = cabin) => {
    geometries.push(geometry);
    const item = new Three.Mesh(geometry, surface);
    parent.add(item);
    return item;
  };
  const mark = mesh(new Three.RingGeometry(.16, .17, 24), markMaterial, scene);
  mark.position.set(0, .12 + helmetCenter.y * modelFit, 2.95);
  mark.scale.set(1, .62, 1);
  const starPoints = [];
  let seed = 57;
  const random = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
  for (let i = 0; i < 110; i++) starPoints.push((random() - .5) * 44, (random() - .5) * 27, -15 - random() * 20);
  const starsGeometry = new Three.BufferGeometry();
  starsGeometry.setAttribute("position", new Three.Float32BufferAttribute(starPoints, 3));
  const starsMaterial = new Three.PointsMaterial({color: 0xd5f5ff, size: .045, sizeAttenuation: true});
  geometries.push(starsGeometry); materials.push(starsMaterial);
  scene.add(new Three.Points(starsGeometry, starsMaterial));
  let width = 0, height = 0;
  function resize() {
    const nextWidth = canvas.clientWidth, nextHeight = canvas.clientHeight;
    if (!nextWidth || !nextHeight || (nextWidth === width && nextHeight === height)) return;
    width = nextWidth; height = nextHeight;
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    for (const item of [...cabin.children]) {
      item.geometry.dispose();
      const position = geometries.indexOf(item.geometry);
      if (position !== -1) geometries.splice(position, 1);
      cabin.remove(item);
    }
    const openingWidth = Math.min(7.8, 3.5 * camera.aspect);
    const openingHeight = 3.25;
    // Fit the actual shared model, including its helmet/ears, on narrow screens.
    // Contact is measured from its front bound rather than a stale model size.
    modelFit = Math.min(.77, openingWidth * .82 / modelSize.x, openingHeight * .8 / modelSize.y);
    model.scale.copy(modelBaseScale).multiplyScalar(modelFit);
    frontDepth = Math.max(.01, modelBounds.max.z * modelFit);
    halfHeight = modelSize.y * modelFit / 2;
    mark.position.set(helmetCenter.x * modelFit, .12 + helmetCenter.y * modelFit, 2.95);
    const outer = roundedPath(Three, openingWidth + 8, 10, .7);
    const hole = roundedPath(Three, openingWidth, openingHeight, Math.min(.42, openingWidth / 5));
    outer.holes.push(new Three.Path(hole.getPoints(24).reverse()));
    const frame = mesh(new Three.ExtrudeGeometry(outer, {depth: .16, bevelEnabled: true, bevelSegments: 2, steps: 1, bevelSize: .045, bevelThickness: .035}), white);
    frame.position.z = 3;
    const inset = roundedPath(Three, openingWidth + .16, openingHeight + .16, .46);
    inset.holes.push(new Three.Path(roundedPath(Three, openingWidth + .05, openingHeight + .05, .43).getPoints(24).reverse()));
    mesh(new Three.ShapeGeometry(inset), cyan).position.z = 3.2;
    const glass = mesh(new Three.PlaneGeometry(openingWidth, openingHeight), glassMaterial);
    glass.position.z = 2.92;
    for (const side of [-1, 1]) {
      const panel = mesh(new Three.BoxGeometry(.12, .7, .05), navy);
      panel.position.set(side * (openingWidth / 2 + .3), .15, 3.22);
      for (const vertical of [-1, 1]) {
        const bolt = mesh(new Three.CylinderGeometry(.035, .035, .02, 12), navy);
        bolt.rotation.x = Math.PI / 2;
        bolt.position.set(side * (openingWidth / 2 + .22), vertical * (openingHeight / 2 + .2), 3.22);
      }
    }
  }
  let lost = false;
  const onLost = (event) => { event.preventDefault(); lost = true; };
  canvas.addEventListener("webglcontextlost", onLost);
  return {
    draw(milliseconds) {
      if (lost) return false;
      resize();
      const pose = sampleGagooEntrance(milliseconds, 2.92 - frontDepth);
      camera.position.set(0, 0, pose.cameraZ);
      camera.lookAt(0, 0, -4);
      const keepContact = pose.contact ? (1 - pose.scaleZ) * frontDepth - Math.sin(pose.rotationX) * halfHeight : 0;
      actor.position.set(pose.x, pose.y, pose.z + keepContact);
      actor.rotation.set(pose.rotationX, 0, pose.rotationZ);
      actor.scale.set(pose.scaleX, pose.scaleY, pose.scaleZ);
      const reaching = clamp((milliseconds - 1100) / 700);
      const slipping = clamp((milliseconds - 2020) / 1080);
      for (const [name, side] of [["leftArm", -1], ["rightArm", 1]]) {
        if (!model.userData[name]) continue;
        model.userData[name].rotation.x = -.6 * reaching * (1 - slipping * .6);
        model.userData[name].rotation.z = side * (.25 * reaching + slipping * .42);
      }
      markMaterial.opacity = pose.markOpacity;
      canvas.dataset.phase = pose.phase;
      renderer.render(scene, camera);
      return true;
    },
    dispose() {
      canvas.removeEventListener("webglcontextlost", onLost);
      model.userData.dispose?.();
      for (const item of geometries) item.dispose();
      for (const item of materials) item.dispose();
      renderer.dispose();
    }
  };
}

/** Cancel an entrance on application teardown. Escape has the same behavior. */
export function cancelGagooEntrance() { activeEntrance?.abort(); }

/**
 * Plays the 3D flight, then a 1s blinds cover/swap/reveal.
 * onCovered changes the route directly, without adding another transition.
 * Resolves after cleanup; cancellation never invokes onCovered.
 */
export async function playGagooEntrance({reduced, onCovered, signal, language = "vi"} = {}) {
  if (typeof onCovered !== "function") throw new TypeError("onCovered must be a function");
  cancelGagooEntrance();
  const controller = new AbortController();
  activeEntrance = controller;
  const previousFocus = document.activeElement;
  const languageCode = typeof language === "function" ? language() : language;
  const vi = languageCode !== "en";
  const dialog = document.createElement("dialog");
  dialog.className = "gagoo-entrance";
  dialog.setAttribute("aria-label", vi ? "Gagoo dẫn tới SPHEREx Learn" : "Gagoo opens SPHEREx Learn");
  const canvas = document.createElement("canvas");
  canvas.className = "gagoo-entrance-canvas";
  canvas.setAttribute("aria-hidden", "true");
  const controls = document.createElement("div");
  controls.className = "gagoo-entrance-controls";
  const skip = document.createElement("button");
  skip.type = "button";
  skip.textContent = vi ? "Bỏ qua hoạt cảnh" : "Skip animation";
  const cancel = document.createElement("button");
  cancel.type = "button";
  cancel.textContent = "×";
  cancel.setAttribute("aria-label", vi ? "Hủy và quay lại" : "Cancel and go back");
  const curtain = document.createElement("div");
  curtain.className = "gagoo-entrance-blinds";
  curtain.setAttribute("aria-hidden", "true");
  const slats = Array.from({length: 14}, () => {
    const slat = document.createElement("span");
    curtain.append(slat);
    return slat;
  });
  controls.append(skip, cancel);
  dialog.append(canvas, controls, curtain);
  let cinema;
  let raf = 0;
  let loadingTimeout = 0;
  let cinemaDone;
  let swapping = false;
  let covered = false;
  let skipRequested = false;
  let completed = false;
  const animations = new Set();
  const abort = () => controller.abort();
  const routeChanged = () => { if (!swapping) abort(); };
  const assertActive = () => { if (controller.signal.aborted) throw abortError(); };
  const finishCinema = () => { skipRequested = true; cinemaDone?.(); };
  const keyCancel = (event) => { event.preventDefault(); abort(); };
  const updateMotion = () => {
    if (!reducedValue(reduced)) return;
    finishCinema();
    for (const animation of animations) {
      try { animation.finish(); } catch { /* A concurrent cancel already settles it. */ }
    }
  };
  const visibility = () => { if (document.hidden) finishCinema(); };
  const onAbort = () => {
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    cinemaDone?.();
    for (const animation of animations) animation.cancel();
  };
  controller.signal.addEventListener("abort", onAbort, {once: true});
  signal?.addEventListener("abort", abort, {once: true});
  if (signal?.aborted) abort();
  skip.addEventListener("click", finishCinema);
  cancel.addEventListener("click", abort);
  dialog.addEventListener("cancel", keyCancel);
  window.addEventListener("hashchange", routeChanged);
  window.addEventListener("popstate", routeChanged);
  window.addEventListener("pagehide", abort);
  document.addEventListener("visibilitychange", visibility);
  reduced?.addEventListener?.("change", updateMotion);

  async function animateSlats(closing, duration) {
    const transform = closing ? ["scaleY(0)", "scaleY(1)"] : ["scaleY(1)", "scaleY(0)"];
    if (!duration || typeof slats[0].animate !== "function") {
      for (const slat of slats) slat.style.transform = transform[1];
      return;
    }
    await Promise.all(slats.map(async (slat, index) => {
      const delay = Math.min(110, duration * .22) * index / (slats.length - 1);
      slat.style.transformOrigin = closing ? "center top" : "center bottom";
      const animation = slat.animate([{transform: transform[0]}, {transform: transform[1]}], {
        duration: duration - Math.min(110, duration * .22), delay,
        easing: "cubic-bezier(.45,.05,.2,1)", fill: "both"
      });
      animations.add(animation);
      try {
        await animation.finished;
        slat.style.transform = transform[1];
      } finally {
        animations.delete(animation);
        animation.cancel();
      }
    }));
  }

  try {
    assertActive();
    document.body.append(dialog);
    dialog.showModal();
    skip.focus({preventScroll: true});
    if (!reducedValue(reduced)) {
      try {
        const pending = createCinema(canvas, controller.signal);
        const interrupted = new Promise((resolve) => {
          cinemaDone = () => resolve(undefined);
          loadingTimeout = setTimeout(finishCinema, 5000);
        });
        cinema = await Promise.race([pending, interrupted]);
        clearTimeout(loadingTimeout); loadingTimeout = 0;
        cinemaDone = undefined;
        // Dynamic imports cannot be aborted. A late renderer must never survive
        // a cancelled or skipped entrance, or appear over the destination page.
        if (!cinema) pending.then((late) => late?.dispose(), () => {});
      }
      catch (error) { if (error.name === "AbortError") throw error; skipRequested = true; }
      assertActive();
      if (!skipRequested && cinema) {
        await new Promise((resolve) => {
          const start = performance.now();
          cinemaDone = resolve;
          const frame = (now) => {
            raf = 0;
            if (controller.signal.aborted || skipRequested || now - start >= CINEMA_MS) { resolve(); return; }
            try { if (!cinema.draw(now - start)) { resolve(); return; } }
            catch { resolve(); return; }
            raf = requestAnimationFrame(frame);
          };
          raf = requestAnimationFrame(frame);
        });
        cinemaDone = undefined;
      }
    }
    assertActive();
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    const duration = reducedValue(reduced) ? 0 : skipRequested ? 60 : 500;
    controls.hidden = true;
    dialog.dataset.stage = "blinds";
    await animateSlats(true, duration);
    assertActive();
    swapping = true;
    try { await onCovered(); covered = true; }
    finally { swapping = false; }
    assertActive();
    cinema?.dispose(); cinema = undefined;
    canvas.hidden = true;
    dialog.dataset.stage = "reveal";
    await animateSlats(false, reducedValue(reduced) ? 0 : duration);
    completed = true;
    return {completed: true, cancelled: false};
  } catch (error) {
    if (error.name !== "AbortError" && !controller.signal.aborted) throw error;
    return {completed: false, cancelled: true};
  } finally {
    if (loadingTimeout) clearTimeout(loadingTimeout);
    if (raf) cancelAnimationFrame(raf);
    for (const animation of animations) animation.cancel();
    cinema?.dispose();
    controller.signal.removeEventListener("abort", onAbort);
    signal?.removeEventListener("abort", abort);
    window.removeEventListener("hashchange", routeChanged);
    window.removeEventListener("popstate", routeChanged);
    window.removeEventListener("pagehide", abort);
    document.removeEventListener("visibilitychange", visibility);
    reduced?.removeEventListener?.("change", updateMotion);
    dialog.close();
    dialog.remove();
    if (activeEntrance === controller) activeEntrance = undefined;
    if (!completed && !covered && previousFocus?.isConnected) previousFocus.focus({preventScroll: true});
  }
}

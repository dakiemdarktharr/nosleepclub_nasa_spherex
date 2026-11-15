// A local implementation of the cover/swap/reveal blinds pattern described at
// https://motion.dev/docs/curtains#blinds. No Motion+ code or service is required.
let activeEntrance;
const CINEMA_MS = 4800;
const CINEMA_CEILING_MS = CINEMA_MS + 2000;
const FLIGHT_START = 550;
const CONTACT_START = 2050;
const SLIDE_START = 2700;
const SLIDE_END = 4600;
const clamp = (value) => Math.max(0, Math.min(1, value));
const smooth = (value) => value * value * (3 - 2 * value);
const mix = (a, b, progress) => a + (b - a) * progress;

/** Timing is shared by the camera, continuity layer and deterministic QA. */
export function sampleGagooEntrance(milliseconds, contactZ = 2.36) {
  const pullback = smooth(clamp(milliseconds / 1200));
  const flight = smooth(clamp((milliseconds - FLIGHT_START) / (CONTACT_START - FLIGHT_START)));
  const contact = clamp((milliseconds - CONTACT_START) / (SLIDE_START - CONTACT_START));
  const slide = smooth(clamp((milliseconds - SLIDE_START) / (SLIDE_END - SLIDE_START)));
  const impact = milliseconds >= CONTACT_START ? Math.sin(Math.min(1, contact * 2.5) * Math.PI) : 0;
  return {
    cameraZ: mix(1.5, 7.8, pullback), pullback, flight, slide,
    z: mix(-3, contactZ, flight),
    rotationZ: -slide * .17,
    rotationX: 0,
    scaleX: 1 + impact * .06,
    scaleY: 1 - impact * .04,
    scaleZ: 1 - (milliseconds >= CONTACT_START ? .09 + impact * .10 : 0),
    contact: milliseconds >= CONTACT_START,
    markOpacity: milliseconds < CONTACT_START ? 0 : .14 * (1 - slide),
    phase: milliseconds < FLIGHT_START ? "pullback" : milliseconds < CONTACT_START ? "flight" : milliseconds < SLIDE_START ? "contact" : milliseconds < SLIDE_END ? "slide" : "clear"
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

/** Retain the real home, including its WebGL canvases, below the modal.
 * Only presentation styles change; the original nodes/listeners are never cloned.
 */
function createHomeContinuity(home) {
  const element = home?.element;
  const target = home?.actorTarget;
  const original = new Map();
  let restored = false;
  const remember = (node, property, value) => {
    if (!node) return;
    if (!original.has(node)) original.set(node, new Map());
    const values = original.get(node);
    if (!values.has(property)) values.set(property, [node.style.getPropertyValue(property), node.style.getPropertyPriority(property)]);
    node.style.setProperty(property, value);
  };
  const animations = element?.getAnimations({subtree: true}).filter(animation => animation.playState === "running") || [];
  animations.forEach(animation => animation.pause());
  const rect = element?.getBoundingClientRect();
  const tetherPaths = element ? [...element.querySelectorAll(".gagoo-tether path")] : [];
  const tetherOriginal = tetherPaths.map(path => path.getAttribute("d"));
  const tetherPath = tetherPaths.at(-1);
  const tetherLength = tetherPath?.getTotalLength() || 0;
  const tetherPoints = tetherLength ? Array.from({length: 21}, (_, index) => tetherPath.getPointAtLength(tetherLength * index / 20)) : [];
  const ui = element ? [...element.querySelectorAll(".orbit-copy,.orbit-caption,.orbit-scroll,.scene-label"), ...document.querySelectorAll(".public-header")] : [];
  if (element) {
    remember(element, "will-change", "transform");
    remember(element, "transform-origin", `${innerWidth / 2 - rect.left}px ${innerHeight / 2 - rect.top}px`);
  }
  return {
    available: Boolean(element && home?.snapshot?.rect),
    update(progress, transferred) {
      if (restored || !element) return;
      remember(element, "transform", `scale(${mix(1, .86, progress)})`);
      for (const node of ui) remember(node, "opacity", String(1 - smooth(clamp(progress * 2.3))));
      if (target) remember(target, "visibility", transferred ? "hidden" : "visible");
    },
    sourceRect(width, height, progress) {
      const source = home?.snapshot?.rect || {x: width * .22, y: height * .35, width: width * .18, height: height * .34};
      const scale = mix(1, .86, progress);
      return {x: width / 2 + (source.x - width / 2) * scale,
        y: height / 2 + (source.y - height / 2) * scale,
        width: source.width * scale, height: source.height * scale};
    },
    moveTether(screenX, screenY, progress) {
      if (restored || !tetherPoints.length || !rect) return;
      const scale = mix(1, .86, progress), endpoint = tetherPoints.at(-1);
      const x = (screenX - innerWidth / 2) / scale + innerWidth / 2 - rect.left;
      const y = (screenY - innerHeight / 2) / scale + innerHeight / 2 - rect.top;
      // Preserve the anchored curve at handover and continuously pull its free end.
      const d = tetherPoints.map((point, index) => {
        const weight = (index / 20) ** 2;
        return `${index ? "L" : "M"}${(point.x + (x - endpoint.x) * weight).toFixed(2)},${(point.y + (y - endpoint.y) * weight).toFixed(2)}`;
      }).join(" ");
      tetherPaths.forEach(path => path.setAttribute("d", d));
    },
    restore() {
      if (restored) return;
      restored = true;
      for (const [node, values] of original) for (const [property, [value, priority]] of values) {
        if (value) node.style.setProperty(property, value, priority); else node.style.removeProperty(property);
      }
      tetherPaths.forEach((path, index) => {
        if (tetherOriginal[index] !== null) path.setAttribute("d", tetherOriginal[index]);
        else path.removeAttribute("d");
      });
      animations.forEach(animation => { if (animation.playState === "paused") animation.play(); });
    }
  };
}

async function createCinema(canvas, signal, home) {
  const [Three, {createGagooModel}, {createRagdollController}, {applyGagooInk}] = await Promise.all([
    import("./assets/three-0.187.0/three.module.js"), import("./gagoo-scene.js?v=3"), import("./gagoo-ragdoll.js?v=2"), import("./gagoo-ink.js?v=1")
  ]);
  if (signal.aborted) throw abortError();
  const renderer = new Three.WebGLRenderer({canvas, alpha: true, antialias: true, powerPreference: "low-power"});
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.5));
  renderer.setClearColor(0x08162e, 0);
  renderer.toneMapping = Three.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.13;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = Three.PCFShadowMap;
  const scene = new Three.Scene();
  const camera = new Three.PerspectiveCamera(46, 1, .05, 80);
  const model = createGagooModel(Three);
  const disposeInk = applyGagooInk(model, Three);
  const ragdoll = createRagdollController(model);
  if (home?.snapshot?.pose) ragdoll.restore(home.snapshot.pose);
  model.updateMatrixWorld(true);
  const modelBounds = new Three.Box3().setFromObject(model);
  const modelSize = modelBounds.getSize(new Three.Vector3());
  const helmetCenter = new Three.Box3().setFromObject(model.getObjectByName("clear polygonal helmet") || model.userData.head || model).getCenter(new Three.Vector3());
  const modelBaseScale = model.scale.clone();
  const sourceRotation = home?.snapshot?.rotation || [0, -.28, 0];
  const sourcePose = home?.snapshot?.pose?.pose || {};
  const actor = new Three.Group(); actor.add(model); scene.add(actor);
  // Match home lighting at the handover; no abrupt new material treatment.
  scene.add(new Three.HemisphereLight(0xdcf2ff, 0x5d6580, 1.1));
  for (const [color, intensity, position] of [[0xffecc8, 2.3, [-3, 4, 5]], [0x74d9ff, .85, [3, 1, -3]], [0xffffff, .3, [2, 0, 5]]]) {
    const light = new Three.DirectionalLight(color, intensity); light.position.set(...position); scene.add(light);
    if (position[0] === -3) {
      light.castShadow = true; light.shadow.mapSize.set(512, 512);
      Object.assign(light.shadow.camera, {left: -2.6, right: 2.6, top: 2.6, bottom: -2.6, near: .5, far: 14});
      light.shadow.normalBias = .025; light.shadow.bias = -.0002;
    }
  }
  const continuity = createHomeContinuity(home);
  const cabin = new Three.Group(); scene.add(cabin);
  const materials = [], geometries = [];
  const material = (options) => { const item = new Three.MeshStandardMaterial(options); materials.push(item); return item; };
  const white = material({color: 0xe9f5f7, metalness: .24, roughness: .48});
  const navy = material({color: 0x14287b, metalness: .2, roughness: .5});
  const cyan = material({color: 0x22d6ed, emissive: 0x159bb4, emissiveIntensity: .4, metalness: .2, roughness: .4});
  const glassMaterial = new Three.MeshBasicMaterial({color: 0x8bedff, transparent: true, opacity: .035, depthWrite: false, side: Three.DoubleSide});
  const markMaterial = new Three.MeshBasicMaterial({color: 0xc3f8ff, transparent: true, opacity: 0, depthWrite: false});
  materials.push(glassMaterial, markMaterial);
  const mesh = (geometry, surface, parent = cabin) => {
    geometries.push(geometry); const item = new Three.Mesh(geometry, surface); parent.add(item); return item;
  };
  const mark = mesh(new Three.RingGeometry(.16, .17, 24), markMaterial, scene);
  mark.scale.set(1, .62, 1);
  let width = 0, height = 0, openingWidth = 0, openingHeight = 0, contactFit = 1, frontDepth = 0;
  function resize() {
    const nextWidth = canvas.clientWidth, nextHeight = canvas.clientHeight;
    if (!Number.isFinite(nextWidth) || !Number.isFinite(nextHeight) || nextWidth <= 0 || nextHeight <= 0) return false;
    if (nextWidth === width && nextHeight === height) return true;
    width = nextWidth; height = nextHeight;
    renderer.setSize(width, height, false); camera.aspect = width / height; camera.updateProjectionMatrix();
    for (const item of [...cabin.children]) {
      item.geometry.dispose(); const index = geometries.indexOf(item.geometry);
      if (index !== -1) geometries.splice(index, 1); cabin.remove(item);
    }
    const visibleHeight = 2 * Math.tan(Three.MathUtils.degToRad(23)) * (7.8 - 3);
    openingWidth = Math.min(2.85, visibleHeight * camera.aspect * .88);
    openingHeight = openingWidth / .85;
    contactFit = Math.min(openingWidth * .89 / modelSize.x, openingHeight * .91 / modelSize.y);
    frontDepth = Math.max(.01, modelBounds.max.z * contactFit);
    mark.position.set(helmetCenter.x * contactFit, helmetCenter.y * contactFit, 2.95);
    const radius = Math.min(.34, openingWidth * .16);
    const outer = roundedPath(Three, 24, 22, .7);
    outer.holes.push(new Three.Path(roundedPath(Three, openingWidth, openingHeight, radius).getPoints(24).reverse()));
    const frame = mesh(new Three.ExtrudeGeometry(outer, {depth: .16, bevelEnabled: true, bevelSegments: 2, steps: 1, bevelSize: .045, bevelThickness: .035}), white);
    frame.position.z = 3;
    const inset = roundedPath(Three, openingWidth + .16, openingHeight + .16, radius + .08);
    inset.holes.push(new Three.Path(roundedPath(Three, openingWidth + .05, openingHeight + .05, radius + .025).getPoints(24).reverse()));
    mesh(new Three.ShapeGeometry(inset), cyan).position.z = 3.2;
    mesh(new Three.PlaneGeometry(openingWidth, openingHeight), glassMaterial).position.z = 2.92;
    for (const side of [-1, 1]) {
      const panel = mesh(new Three.BoxGeometry(.12, .7, .05), navy);
      panel.position.set(side * (openingWidth / 2 + .3), .15, 3.22);
      for (const vertical of [-1, 1]) {
        const bolt = mesh(new Three.CylinderGeometry(.035, .035, .02, 12), navy); bolt.rotation.x = Math.PI / 2;
        bolt.position.set(side * (openingWidth / 2 + .22), vertical * (openingHeight / 2 + .2), 3.22);
      }
    }
    return true;
  }
  const actorBounds = new Three.Box3(), projected = new Three.Vector3();
  let lost = false, lastTime = 0, struck = false, disposed = false, clearedAt = null;
  let actorClear = false;
  const onLost = (event) => { event.preventDefault(); lost = true; };
  canvas.addEventListener("webglcontextlost", onLost);
  return {
    draw(milliseconds) {
      if (lost || disposed) return false;
      if (!resize()) return false;
      const pose = sampleGagooEntrance(milliseconds, 2.92 - frontDepth);
      camera.position.set(0, 0, pose.cameraZ); camera.lookAt(0, 0, -4);
      const dt = Math.max(0, Math.min(.04, (milliseconds - lastTime) / 1000)); lastTime = milliseconds;
      const transferred = milliseconds >= FLIGHT_START;
      continuity.update(pose.pullback, transferred);
      actor.visible = transferred || !continuity.available;
      const source = continuity.sourceRect(width, height, pose.pullback);
      const sourceDistance = pose.cameraZ + 3;
      const viewHeight = 2 * Math.tan(Three.MathUtils.degToRad(23)) * sourceDistance;
      const startFit = source.height / height * viewHeight / 3.6;
      const startX = ((source.x + source.width / 2) / width - .5) * viewHeight * camera.aspect;
      const startY = (.5 - (source.y + source.height / 2) / height) * viewHeight;
      const fit = mix(startFit, contactFit, pose.flight);
      model.scale.copy(modelBaseScale).multiplyScalar(fit);
      // The body stays against the glass; the whole character slides horizontally
      // behind the right jamb rather than falling or recoiling into open space.
      const slideDistance = openingWidth / 2 + modelSize.x * contactFit * .9 + .45;
      actor.position.set(mix(startX, .04, pose.flight) + slideDistance * pose.slide,
        mix(startY, 0, pose.flight), pose.z);
      actor.rotation.set(mix(sourceRotation[0], 0, pose.flight) + pose.rotationX,
        mix(sourceRotation[1], 0, pose.flight),
        mix(sourceRotation[2], 0, pose.flight) + pose.rotationZ);
      actor.scale.set(pose.scaleX, pose.scaleY, pose.scaleZ);
      if (milliseconds >= CONTACT_START && !struck) { struck = true; ragdoll.impulse({x: .22, y: -.08, z: -1.9}, 1); }
      if (transferred) {
        const blendedPose = Object.fromEntries(Object.entries(sourcePose).map(([joint, angles]) => [joint, angles.map(angle => angle * (1 - pose.flight))]));
        const stick = smooth(clamp((milliseconds - CONTACT_START) / 240));
        for (const [joint, angles] of Object.entries({leftArm: [-.33, .12, -.31], rightArm: [-.33, -.12, .31],
          leftForearm: [-.20, 0, 0], rightForearm: [-.20, 0, 0], leftHand: [.08, 0, -.12], rightHand: [.08, 0, .12],
          leftLeg: [.08, 0, -.10], rightLeg: [-.06, 0, .10]})) {
          blendedPose[joint] = angles.map((angle, axis) => (blendedPose[joint]?.[axis] || 0) + angle * stick);
        }
        const sliding = clamp((milliseconds - SLIDE_START) / (SLIDE_END - SLIDE_START));
        const slideAcceleration = milliseconds >= SLIDE_START && milliseconds < SLIDE_END ? (1 - 2 * sliding) * .9 : 0;
        ragdoll.step(dt, {acceleration: {x: slideAcceleration, y: 0, z: milliseconds < CONTACT_START ? .2 : 0}, strength: 1, pose: blendedPose});
        if (pose.contact) {
          // Keep the current posed helmet at the glass even with a loose neck.
          // Bounds are conservative and include the visor, gloves and ears.
          actor.updateMatrixWorld(true); actorBounds.setFromObject(actor);
          actor.position.z += 2.92 - actorBounds.max.z;
        }
        actor.updateMatrixWorld(true); camera.updateMatrixWorld(true);
        const anchor = model.userData.backpackAnchor?.getWorldPosition(new Three.Vector3()).project(camera);
        if (anchor) continuity.moveTether((anchor.x + 1) * width / 2, (1 - anchor.y) * height / 2, pose.pullback);
      }
      markMaterial.opacity = pose.markOpacity;
      canvas.dataset.phase = pose.phase;
      canvas.dataset.continuity = continuity.available ? "home" : "fallback";
      canvas.dataset.actorDepth = String(actor.position.z);
      canvas.dataset.actorX = String(actor.position.x);
      canvas.dataset.actorY = String(actor.position.y);
      actorBounds.setFromObject(actor);
      let leftEdge = Infinity;
      for (const x of [actorBounds.min.x, actorBounds.max.x]) for (const y of [actorBounds.min.y, actorBounds.max.y]) for (const z of [actorBounds.min.z, actorBounds.max.z]) {
        projected.set(x, y, z).project(camera); leftEdge = Math.min(leftEdge, projected.x);
      }
      const rightJamb = projected.set(openingWidth / 2, 0, 3).project(camera).x;
      // Project a world-space margin so very wide viewports do not demand an
      // unreachable fixed NDC gap after the character is already behind the jamb.
      const clearanceEdge = projected.set(openingWidth / 2 + .05, 0, 3).project(camera).x;
      actorClear = pose.contact && Number.isFinite(leftEdge) && Number.isFinite(clearanceEdge) && leftEdge > clearanceEdge;
      clearedAt = actorClear ? clearedAt ?? milliseconds : null;
      canvas.dataset.frontSurfaceZ = String(actorBounds.max.z);
      canvas.dataset.actorLeftEdge = String(leftEdge);
      canvas.dataset.windowRightEdge = String(rightJamb);
      canvas.dataset.clearanceEdge = String(clearanceEdge);
      canvas.dataset.actorClear = String(actorClear);
      if (actorClear) canvas.dataset.phase = "clear";
      canvas.dataset.windowOccupancy = JSON.stringify({width: modelSize.x * contactFit / openingWidth, height: modelSize.y * contactFit / openingHeight});
      renderer.render(scene, camera);
      return true;
    },
    readyToTransition(milliseconds) { return actorClear && clearedAt !== null && milliseconds - clearedAt >= 120; },
    dispose() {
      if (disposed) return;
      disposed = true;
      continuity.restore();
      canvas.removeEventListener("webglcontextlost", onLost);
      ragdoll.dispose?.(); disposeInk?.(); model.userData.dispose?.();
      scene.traverse(node => node.shadow?.dispose());
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
export async function playGagooEntrance({reduced, onCovered, signal, language = "vi", home} = {}) {
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
        const pending = createCinema(canvas, controller.signal, home);
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
            if (controller.signal.aborted || skipRequested) { resolve(); return; }
            const elapsed = now - start;
            // A bad projection/context must restore home, never cover a still
            // visible actor or keep an uncancellable render loop alive forever.
            if (elapsed >= CINEMA_CEILING_MS) { abort(); resolve(); return; }
            try {
              if (!cinema.draw(Math.min(elapsed, CINEMA_MS))) { abort(); resolve(); return; }
              if (cinema.readyToTransition(elapsed)) { resolve(); return; }
            }
            catch { abort(); resolve(); return; }
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

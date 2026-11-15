import * as Three from "./assets/three-0.187.0/three.module.js";
import {bodyBounds, clampBody, stepBody, createRope, stepRope, ropePath} from "./gagoo-physics.js";
import {attachGagooRig} from "./gagoo-rig.js";
import {createRagdollController} from "./gagoo-ragdoll.js";
import {applyGagooInk} from "./gagoo-ink.js";

/** Broad planar forms; +Z faces the viewer. The articulated mascot is 3.2 units tall. */
export function createGagooModel(T = Three) {
  const root = new T.Group(); root.name = 'Gagoo — bushbaby astronaut';
  const body = new T.Group(); root.add(body);
  const geometries = new Set(), materials = new Set();
  const mat = (color, options = {}) => { const m = new T.MeshStandardMaterial({color, roughness: .88, flatShading: true, ...options}); materials.add(m); return m; };
  const fur = mat(0x8d989f), pink = mat(0xb99497), pale = mat(0xcbd0ca), white = mat(0xe9e7dc);
  const shadow = mat(0x74868d), dark = mat(0x303940), amber = mat(0xc99139), teal = mat(0x37656c), cyan = mat(0xbfe5de), mustard = mat(0xb9a25a);
  const glint = new T.MeshBasicMaterial({color: 0xfffaf0}); materials.add(glint);
  const mesh = (geometry, material, name, position = [0, 0, 0], parent = body) => {
    geometries.add(geometry); const m = new T.Mesh(geometry, material); m.name = name; m.position.set(...position); parent.add(m); return m;
  };
  const polygon = (points, depth, bevel = .035) => {
    const shape = new T.Shape(); shape.moveTo(...points[0]); for (const p of points.slice(1)) shape.lineTo(...p); shape.closePath();
    const g = new T.ExtrudeGeometry(shape, {depth, bevelEnabled: bevel > 0, bevelSegments: 1, steps: 1, bevelSize: bevel, bevelThickness: bevel, curveSegments: 1});
    g.translate(0, 0, -depth / 2); return g;
  };
  const octagon = (rx, ry, cut = .26) => [[-rx * (1 - cut), -ry], [rx * (1 - cut), -ry], [rx, -ry * (1 - cut)], [rx, ry * (1 - cut)], [rx * (1 - cut), ry], [-rx * (1 - cut), ry], [-rx, ry * (1 - cut)], [-rx, -ry * (1 - cut)]];
  const slab = (rx, ry, depth, material, name, position, parent = body, bevel = .03) => mesh(polygon(octagon(rx, ry), depth, bevel), material, name, position, parent);
  const disc = (rx, ry, material, name, position, parent = body, segments = 12) => {
    const m = mesh(new T.CircleGeometry(1, segments), material, name, position, parent); m.scale.set(rx, ry, 1); return m;
  };
  const link = (from, to, r1, r2, material, name, parent = body) => {
    const a = new T.Vector3(...from), b = new T.Vector3(...to), direction = b.clone().sub(a);
    const openJoint = ['upper sleeve', 'forearm sleeve', 'upper leg', 'lower leg'].includes(name);
    const m = mesh(new T.CylinderGeometry(r2, r1, direction.length(), 6, 1, openJoint), material, name, a.clone().add(b).multiplyScalar(.5).toArray(), parent);
    m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), direction.normalize()); return m;
  };
  const tube = (points, radius, material, name, parent = body) => mesh(new T.TubeGeometry(new T.CatmullRomCurve3(points.map(p => new T.Vector3(...p))), 5, radius, 4, false), material, name, [0, 0, 0], parent);

  // One head volume: each pair of triangles lies on a broad planar quad.
  const head = new T.Group(); head.position.y = -.28; body.add(head); root.userData.head = head;
  const ringData = [[1.04, .56], [1.18, .76], [1.48, .97], [2.13, .97], [2.48, .78], [2.64, .43]].map(([y, width]) => [y, width, width * .60, width * -.69]);
  const positions = [], indices = [];
  for (const [y, w, front, back] of ringData) {
    for (const [x, z] of [[-.68 * w, front], [.68 * w, front], [w, .67 * front], [w, .66 * back], [.67 * w, back], [-.67 * w, back], [-w, .66 * back], [-w, .67 * front]]) positions.push(x, y, z);
  }
  for (let row = 0; row < ringData.length - 1; row++) for (let j = 0; j < 8; j++) {
    const a = row * 8 + j, b = row * 8 + (j + 1) % 8, c = a + 8, d = b + 8;
    indices.push(a, b, c, b, d, c);
  }
  const topRing = (ringData.length - 1) * 8;
  for (let j = 1; j < 7; j++) { indices.push(0, j + 1, j); indices.push(topRing, topRing + j, topRing + j + 1); }
  const headGeometry = new T.BufferGeometry(); headGeometry.setAttribute('position', new T.Float32BufferAttribute(positions, 3)); headGeometry.setIndex(indices); headGeometry.computeVertexNormals();
  mesh(headGeometry, fur, 'broad forehead and clean cheek planes', [0, 0, 0], head);
  link([0, .64, 0], [0, 1.13, 0], .26, .29, fur, 'neck', head);
  const earOutline = [[-.28, -.56], [.12, -.62], [.37, -.28], [.36, .29], [.12, .62], [-.17, .65], [-.34, .29], [-.36, -.19]];
  for (const side of [-1, 1]) {
    const ear = new T.Group(); ear.position.set(side * 1.06, 2.39, -.05); ear.rotation.z = side * -.24; head.add(ear);
    mesh(polygon(earOutline, .18, .055), fur, 'chunky beveled ear', [0, 0, 0], ear);
    mesh(polygon(earOutline.map(([x, y]) => [x * .73, y * .78]), .012, .008), pink, 'flat dusty-pink ear inset', [0, .014, .148], ear);
    // Include the bevel in the visible width, rather than measuring its inner face.
    const irisPoints = Array.from({length: 12}, (_, i) => { const t = i * Math.PI / 6; return [Math.cos(t) * .318, Math.sin(t) * .355]; });
    const iris = mesh(polygon(irisPoints, .035, .014), amber, 'single amber eye', [side * .43, 1.94, .64], head);
    iris.geometry.computeBoundingBox();
    const irisWidth = iris.geometry.boundingBox.max.x - iris.geometry.boundingBox.min.x;
    root.userData.eyeDesign = {previousIrisWidth: .8, previousHeadWidth: 1.98, headWidth: 1.94, irisWidth, widthReduction: 1 - irisWidth / .8, relativeHeadReduction: 1 - (irisWidth / 1.94) / (.8 / 1.98), layeredSockets: false};
    disc(.205, .244, dark, 'dark pupil', [side * .43, 1.946, .675], head);
    disc(.061, .061, glint, 'single eye highlight', [side * .43 - .075, 2.054, .679], head, 8);
  }
  // A single pale muzzle replaces segmented cheek patches and separate cheek spikes.
  mesh(polygon(octagon(.35, .22, .46), .13, .045), pale, 'single pale muzzle', [0, 1.35, .625], head);
  mesh(polygon(octagon(.112, .078, .45), .045, .014), dark, 'charcoal nose', [0, 1.43, .748], head);
  tube([[-.10, 1.27, .752], [0, 1.245, .758], [.10, 1.27, .752]], .014, dark, 'short mouth', head);
  mesh(polygon([[-.13, 0], [.15, 0], [.06, .15], [-.02, .09]], .15, 0), fur, 'small crown tuft', [0, 2.62, -.05], head);

  // Compact suit: no layered shoulders, elbow rings, knee pads or ankle rings.
  mesh(polygon([[-.39, -.48], [.39, -.48], [.53, -.29], [.54, .28], [.36, .43], [-.36, .43], [-.54, .28], [-.53, -.29]], .60, .065), white, 'single pressure-suit torso', [0, .08, 0]);
  slab(.25, .14, .018, teal, 'flush teal chest panel', [0, .18, .371], body, .005);
  slab(.13, .035, .009, cyan, 'pale cyan display', [-.045, .21, .389], body, 0);
  for (const x of [-.05, .06]) disc(.022, .022, pale, 'panel status dot', [x, .113, .391], body, 6);
  for (const side of [-1, 1]) {
    const arm = new T.Group(); arm.position.set(side * .48, .30, 0); arm.name = side < 0 ? 'left arm' : 'right arm'; body.add(arm);
    link([side * .05, 0, 0], [side * .17, -.24, .03], .20, .1775, white, 'upper sleeve', arm);
    link([side * .17, -.24, .03], [side * .29, -.48, .06], .1775, .155, white, 'forearm sleeve', arm);
    mesh(new T.SphereGeometry(.1775, 6, 4), white, 'elbow joint', [side * .17, -.24, .03], arm);
    link([side * .28, -.43, .057], [side * .31, -.53, .07], .163, .161, shadow, 'simple cuff', arm);
    const glove = mesh(polygon(octagon(.18, .18, .5), .23, .04), white, 'mitten hand', [side * .32, -.64, .09], arm); glove.rotation.z = side * -.12;
    root.userData[side < 0 ? 'leftArm' : 'rightArm'] = arm;
    link([side * .27, -.36, 0], [side * .305, -.64, .02], .21, .195, white, 'upper leg');
    link([side * .305, -.64, .02], [side * .34, -.92, .04], .195, .18, white, 'lower leg');
    mesh(new T.SphereGeometry(.195, 6, 4), white, 'knee joint', [side * .305, -.64, .02]);
    const boot = slab(.23, .16, .46, white, 'flat-soled boot', [side * .35, -1.06, .14], body, .035);
    boot.geometry.translate(0, .025, 0);
  }
  slab(.072, .065, .012, mustard, 'single mustard sleeve patch', [-.61, .19, .19], body, .005);
  slab(.39, .39, .27, white, 'beveled life-support backpack', [0, .11, -.49], body, .06);
  slab(.23, .22, .012, shadow, 'backpack inset', [0, .13, -.686], body, .012).rotation.y = Math.PI;
  const backpackAnchor = new T.Object3D(); backpackAnchor.position.set(-.25, -.13, -.72); body.add(backpackAnchor); root.userData.backpackAnchor = backpackAnchor;
  link([-.25, -.13, -.65], [-.25, -.13, -.74], .055, .055, shadow, 'umbilical socket');

  // Single thick collar; broad 12-sided helmet planes follow the ear silhouette.
  const collar = mesh(new T.TorusGeometry(.78, .115, 4, 12), white, 'single chunky helmet collar', [0, .65, .01]); collar.rotation.x = Math.PI / 2; collar.scale.y = .73;
  const profile = [[.65, .80, .59], [.98, 1.12, .85], [1.44, 1.48, 1.02], [2.08, 1.62, 1.02], [2.69, 1.50, .88], [3.03, 1.05, .63], [3.18, .48, .32], [3.24, .003, .003]];
  const shellPositions = [], shellIndices = [], segments = 16;
  for (const [y, rx, rz] of profile) for (let i = 0; i < segments; i++) { const a = i / segments * Math.PI * 2; shellPositions.push(Math.cos(a) * rx, y, Math.sin(a) * rz); }
  for (let row = 0; row < profile.length - 1; row++) for (let i = 0; i < segments; i++) { const a = row * segments + i, b = row * segments + (i + 1) % segments, c = a + segments, d = b + segments; shellIndices.push(a, c, b, b, c, d); }
  const shell = new T.BufferGeometry(); shell.setAttribute('position', new T.Float32BufferAttribute(shellPositions, 3)); shell.setIndex(shellIndices);
  body.updateMatrixWorld(true);
  const headVertices = [], vertex = new T.Vector3();
  head.traverse(node => { if (!node.isMesh || node.name === 'neck') return; const p = node.geometry.attributes.position; for (let i = 0; i < p.count; i++) headVertices.push(vertex.fromBufferAttribute(p, i).applyMatrix4(node.matrixWorld).clone()); });
  function shellClearance() {
    const p = shell.attributes.position, ix = shell.index, a = new T.Vector3(), b = new T.Vector3(), c = new T.Vector3(), normal = new T.Vector3(); let clearance = Infinity;
    for (let i = 0; i < ix.count; i += 3) {
      a.fromBufferAttribute(p, ix.getX(i)); b.fromBufferAttribute(p, ix.getX(i + 1)); c.fromBufferAttribute(p, ix.getX(i + 2)); normal.crossVectors(b.clone().sub(a), c.clone().sub(a)).normalize();
      if (normal.dot(a.clone().sub(new T.Vector3(0, 2, 0))) < 0) normal.negate();
      for (const point of headVertices) clearance = Math.min(clearance, normal.x * (a.x - point.x) + normal.y * (a.y - point.y) + normal.z * (a.z - point.z));
    }
    return clearance;
  }
  let clearance = shellClearance(), fitIterations = 0;
  while (clearance < .045 && fitIterations < 12) { const p = shell.attributes.position; for (let i = 0; i < p.count; i++) p.setXYZ(i, p.getX(i) * 1.018, 2 + (p.getY(i) - 2) * 1.018, p.getZ(i) * 1.018); fitIterations++; clearance = shellClearance(); }
  shell.computeVertexNormals();
  const glass = new T.MeshPhysicalMaterial({color: 0xe0f2ee, roughness: .23, transparent: true, opacity: .045, depthWrite: false, side: T.FrontSide, flatShading: true}); materials.add(glass);
  mesh(shell, glass, 'clear polygonal helmet').renderOrder = 5;
  const sheen = new T.MeshBasicMaterial({color: 0xe8f1e8, transparent: true, opacity: .32, depthWrite: false}); materials.add(sheen);
  tube([[.35, 3.08, .38], [.56, 3.01, .45], [.72, 2.92, .51]], .018, sheen, 'single soft upper reflection');
  attachGagooRig(T, root, body, head);
  const unscaled = new T.Box3().setFromObject(body), size = unscaled.getSize(new T.Vector3()); body.position.y = -(unscaled.min.y + unscaled.max.y) / 2;
  const scale = 3.2 / size.y; root.scale.setScalar(scale); root.updateMatrixWorld(true); const bounds = new T.Box3().setFromObject(root);
  let triangles = 0, meshes = 0; root.traverse(node => { if (node.isMesh) { meshes++; triangles += (node.geometry.index?.count ?? node.geometry.attributes.position.count) / 3; } });
  root.userData.normalizedBounds = {min: bounds.min.toArray(), max: bounds.max.toArray()}; root.userData.frontDepth = bounds.max.z;
  root.userData.helmetFit = {testedHeadVertices: headVertices.length, minClearance: clearance * scale, fitIterations, excludesNeckThroughCollar: true, passed: clearance >= .045};
  root.userData.geometryStats = {triangles, meshes};
  root.userData.dispose = () => { geometries.forEach(g => g.dispose()); materials.forEach(m => m.dispose()); };
  return root;
}


export function mountGagoo({canvas, target, stage, reduced, isActive = () => true, isPaused = () => false, onActivate = () => {}, tetherPath}) {
  const renderer = new Three.WebGLRenderer({canvas, alpha: true, antialias: true, powerPreference: "low-power"});
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.6));
  renderer.toneMapping = Three.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.13;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = Three.PCFShadowMap;
  const scene = new Three.Scene();
  const camera = new Three.OrthographicCamera(-1.5, 1.5, 1.9, -1.9, .1, 30);
  camera.position.set(0, .08, 8); camera.lookAt(0, 0, 0);
  scene.add(new Three.HemisphereLight(0xdcf2ff, 0x5d6580, 1.1));
  for (const [color, intensity, position] of [[0xffecc8, 2.3, [-3, 4, 5]], [0x74d9ff, .85, [3, 1, -3]], [0xffffff, .3, [2, 0, 5]]]) {
    const light = new Three.DirectionalLight(color, intensity); light.position.set(...position); scene.add(light);
    if (intensity === 2.3) {
      light.castShadow = true; light.shadow.mapSize.set(512, 512);
      Object.assign(light.shadow.camera, {left: -2.6, right: 2.6, top: 2.6, bottom: -2.6, near: .5, far: 14});
      light.shadow.normalBias = .025; light.shadow.bias = -.0002;
    }
  }
  const model = createGagooModel(); scene.add(model);
  const disposeInk = applyGagooInk(model, Three);
  const ragdoll = createRagdollController(model);
  const svgNS = "http://www.w3.org/2000/svg";
  let svg, ownRope = false;
  if (!tetherPath) {
    ownRope = true; svg = document.createElementNS(svgNS, "svg");
    svg.classList.add("gagoo-tether"); svg.setAttribute("aria-hidden", "true");
    svg.style.cssText = "position:absolute;inset:0;width:100%;height:100%;overflow:hidden;pointer-events:none;z-index:3";
    const shadow = document.createElementNS(svgNS, "path"); shadow.setAttribute("fill", "none"); shadow.setAttribute("stroke", "#173844"); shadow.setAttribute("stroke-width", "6");
    tetherPath = document.createElementNS(svgNS, "path");
    for (const [key, value] of Object.entries({fill: "none", stroke: "#c7d1c9", "stroke-width": "3", "stroke-linecap": "round"})) tetherPath.setAttribute(key, value);
    svg.append(shadow, tetherPath); stage.append(svg);
  } else svg = tetherPath.ownerSVGElement;
  let dimensions = {width: 0, height: 0}, bounds, rope, ropeLength = 200, anchor = {x: 0, y: 0};
  const body = {x: 0, y: 0, vx: 0, vy: 0, width: 0, height: 0};
  let frame = 0, last = 0, elapsed = 0, disposed = false, lost = false, inView = true, drag = null;
  let suppressClick = false, suppressTimer = 0, entrance = false;
  let previousVelocity = {x: 0, y: 0};
  const listeners = [];
  const listen = (node, event, callback, options) => { node.addEventListener(event, callback, options); listeners.push(() => node.removeEventListener(event, callback, options)); };
  const available = () => !disposed && !lost && isActive() && inView && !document.hidden;
  const moving = () => !reduced.matches && !isPaused();

  function measure() {
    const width = stage.clientWidth, height = stage.clientHeight;
    const w = target.offsetWidth, h = target.offsetHeight;
    if (!width || !height || !w || !h) return false;
    if (width === dimensions.width && height === dimensions.height && w === body.width && h === body.height) return true;
    const old = dimensions;
    body.x = old.width ? (body.x + body.width / 2) / old.width * width - w / 2 : width * .24 - w / 2;
    body.y = old.height ? (body.y + body.height / 2) / old.height * height - h / 2 : height * .55 - h / 2;
    dimensions = {width, height}; body.width = w; body.height = h;
    bounds = bodyBounds(width, height, w, h); clampBody(body, bounds);
    anchor = {x: 0, y: height * .46};
    ropeLength = Math.hypot(body.x + w / 2, body.y + h / 2 - anchor.y) * 1.18;
    renderer.setSize(w, h, false);
    camera.left = -1.8 * w / h; camera.right = 1.8 * w / h;
    camera.top = 1.8; camera.bottom = -1.8; camera.updateProjectionMatrix();
    if (svg) svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    rope = null; return true;
  }
  function render(now) {
    frame = 0;
    if (!available() || !measure()) { last = 0; return; }
    const dt = last ? Math.min(.035, (now - last) / 1000) : 1 / 60; last = now;
    const animate = moving();
    if (animate) elapsed += dt;
    if (animate && !drag && !entrance) stepBody(body, dt, bounds, anchor, ropeLength);
    if (!entrance) {
      model.rotation.y = -.28 + elapsed * Math.PI * 2 / 45;
      model.rotation.x = .03 + Math.sin(elapsed * .33) * .055;
      model.rotation.z = Math.sin(elapsed * .65) * .045 - Math.max(-.2, Math.min(.2, body.vx * .001));
      if (animate) {
        const pixelsToWorld = 3.6 / Math.max(1, body.height);
        const inertia = new Three.Vector3(
          -(body.vx - previousVelocity.x) / Math.max(dt, .008) * pixelsToWorld,
          (body.vy - previousVelocity.y) / Math.max(dt, .008) * pixelsToWorld,
          0
        ).applyQuaternion(model.quaternion.clone().invert());
        ragdoll.step(dt, {acceleration: inertia, pose: {
          leftArm: [0, 0, -.045 + Math.sin(elapsed * .7) * .035],
          rightArm: [0, 0, .06 + Math.sin(elapsed * .5) * .04]
        }});
      }
    }
    previousVelocity = {x: body.vx, y: body.vy};
    target.style.transform = `translate3d(${body.x.toFixed(2)}px,${body.y.toFixed(2)}px,0)`;
    scene.updateMatrixWorld(true); camera.updateMatrixWorld(true);
    const end = model.userData.backpackAnchor.getWorldPosition(new Three.Vector3()).project(camera);
    const point = {x: body.x + (end.x + 1) * body.width / 2, y: body.y + (1 - end.y) * body.height / 2};
    rope ??= createRope(anchor, point, 20, ropeLength);
    stepRope(rope, anchor, point, ropeLength, animate ? dt : 0);
    const d = ropePath(rope); tetherPath.setAttribute("d", d);
    if (ownRope) svg.firstElementChild.setAttribute("d", d);
    renderer.render(scene, camera); canvas.hidden = false; target.dataset.model = "3d";
    target.dataset.ragdoll = ragdoll.energy > .02 ? "active" : "settled";
    if (animate || drag) frame = requestAnimationFrame(render); else last = 0;
  }
  function refresh() {
    if (!available()) { if (frame) cancelAnimationFrame(frame); frame = 0; last = 0; return; }
    if (!frame) frame = requestAnimationFrame(render);
  }
  function endDrag(event, cancelled = false) {
    if (!drag || (event.pointerId !== undefined && event.pointerId !== drag.id)) return;
    const finished = drag, wasMoved = finished.moved;
    drag = null;
    if (target.hasPointerCapture(finished.id)) target.releasePointerCapture(finished.id);
    if (cancelled || !moving()) body.vx = body.vy = 0;
    target.removeAttribute("data-dragging");
    if (wasMoved || (!cancelled && finished.type === "touch")) {
      suppressClick = true; clearTimeout(suppressTimer); suppressTimer = setTimeout(() => { suppressClick = false; }, 400);
    }
    // Some mobile engines omit the compatibility click after a captured drag.
    // A touch tap is therefore completed on pointerup; any generated click is
    // consumed once, so first-tap preview and second-tap activation stay exact.
    if (!wasMoved && !cancelled && finished.type === "touch") activate(event, true);
    refresh();
  }
  listen(target, "pointerdown", event => {
    if (event.button !== 0 || event.isPrimary === false || drag || !measure()) return;
    suppressClick = false; clearTimeout(suppressTimer);
    drag = {id: event.pointerId, startX: event.clientX, startY: event.clientY, x: body.x, y: body.y, lastX: event.clientX, lastY: event.clientY, lastTime: performance.now(), moved: false, type: event.pointerType};
    body.vx = body.vy = 0; target.setPointerCapture(event.pointerId);
  });
  listen(target, "pointermove", event => {
    if (!drag || drag.id !== event.pointerId) return;
    const dx = event.clientX - drag.startX, dy = event.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < 7) return;
    drag.moved = true; target.dataset.dragging = "true"; target.removeAttribute("data-tap-preview"); event.preventDefault();
    const now = performance.now(), dt = Math.max(.008, (now - drag.lastTime) / 1000);
    body.x = drag.x + dx; body.y = drag.y + dy; clampBody(body, bounds);
    body.vx = Math.max(-260, Math.min(260, (event.clientX - drag.lastX) / dt * .28));
    body.vy = Math.max(-260, Math.min(260, (event.clientY - drag.lastY) / dt * .28));
    drag.lastX = event.clientX; drag.lastY = event.clientY; drag.lastTime = now;
    refresh();
  });
  listen(target, "pointerup", event => endDrag(event));
  listen(target, "pointercancel", event => endDrag(event, true));
  listen(target, "lostpointercapture", event => { if (drag) endDrag(event, true); });
  function activate(event, touch) {
    event.preventDefault(); event.stopPropagation();
    if (touch && !target.hasAttribute("data-tap-preview")) {
      stage.querySelectorAll("[data-tap-preview]").forEach(node => node.removeAttribute("data-tap-preview"));
      target.setAttribute("data-tap-preview", "true"); refresh(); return;
    }
    target.removeAttribute("data-tap-preview"); onActivate(event);
  }
  listen(target, "click", event => {
    event.preventDefault(); event.stopPropagation();
    if (suppressClick && event.detail !== 0) { suppressClick = false; clearTimeout(suppressTimer); return; }
    const touch = event.pointerType === "touch" || (event.detail > 0 && matchMedia("(hover: none)").matches);
    activate(event, touch);
  });
  listen(target, "keydown", event => {
    if (!event.altKey || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) return;
    event.preventDefault(); if (!measure()) return;
    body.x += event.key === "ArrowRight" ? 16 : event.key === "ArrowLeft" ? -16 : 0;
    body.y += event.key === "ArrowDown" ? 16 : event.key === "ArrowUp" ? -16 : 0;
    body.vx = body.vy = 0; clampBody(body, bounds); refresh();
  });
  listen(canvas, "webglcontextlost", event => { event.preventDefault(); lost = true; canvas.hidden = true; target.dataset.model = "fallback"; refresh(); });
  listen(canvas, "webglcontextrestored", () => { lost = false; refresh(); });
  listen(document, "visibilitychange", () => { if (document.hidden && drag) endDrag({pointerId: drag.id}, true); refresh(); });
  listen(reduced, "change", refresh);
  for (const name of ["pointerenter", "pointerleave", "focus", "blur"]) listen(target, name, refresh);
  const resize = new ResizeObserver(refresh); resize.observe(stage); resize.observe(target);
  const intersection = new IntersectionObserver(entries => { inView = entries[0].isIntersecting; refresh(); }, {threshold: 0}); intersection.observe(stage);
  refresh();
  return {
    refresh,
    snapshot() {
      // Capture synchronously while this renderer still owns its drawing buffer.
      // The cinematic receives the same pose and screen registration, not a reset.
      scene.updateMatrixWorld(true);
      renderer.render(scene, camera);
      const rect = target.getBoundingClientRect();
      let dataUrl;
      try { dataUrl = canvas.toDataURL('image/png'); } catch { /* Live canvas remains available. */ }
      return {canvas, dataUrl, rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height},
        rotation: model.rotation.toArray().slice(0, 3), pose: ragdoll.snapshot(), modelHeight: 3.2};
    },
    playEntrance: () => { entrance = true; body.vx = body.vy = 0; refresh(); return () => { entrance = false; refresh(); }; },
    dispose() {
      disposed = true; if (frame) cancelAnimationFrame(frame); clearTimeout(suppressTimer);
      resize.disconnect(); intersection.disconnect(); listeners.forEach(remove => remove());
      disposeInk(); model.userData.dispose();
      scene.traverse(node => node.shadow?.dispose());
      renderer.dispose(); if (ownRope) svg.remove();
      canvas.hidden = true; target.dataset.model = "fallback";
    }
  };
}

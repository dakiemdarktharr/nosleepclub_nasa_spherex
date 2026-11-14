import * as Three from "./assets/three-0.187.0/three.module.js";
import { GLTFLoader } from "./assets/three-0.187.0/loaders/GLTFLoader.js";

export async function mountOrbit({canvas, target, orbit, reduced, isActive, isPaused}) {
  const renderer = new Three.WebGLRenderer({canvas, alpha: true, antialias: true, powerPreference: "low-power"});
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.65));
  renderer.toneMapping = Three.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.07;
  const scene = new Three.Scene();
  const camera = new Three.PerspectiveCamera(35, 1, .1, 100);
  camera.position.set(-3.35, 2.4, -6.3);
  camera.lookAt(0, -.04, 0);

  scene.add(new Three.HemisphereLight(0xcde6ff, 0x587092, 2.6));
  const lamp = (color, intensity, x, y, z) => {
    const light = new Three.DirectionalLight(color, intensity);
    light.position.set(x, y, z);
    scene.add(light);
  };
  // The solar panel faces the warm key light in the home pose.
  lamp(0xffedcf, 3.05, 4.7, 2.8, -1.5);
  lamp(0x77baff, 1.15, 3, 2, 3);
  lamp(0xc0dbff, 1.15, -5, -1, 1);

  let loaded;
  try {
    loaded = await new GLTFLoader().loadAsync(new URL("./assets/mission/spherex.glb", import.meta.url).href);
  } catch (error) {
    renderer.dispose();
    throw error;
  }
  const model = loaded.scene;
  const bounds = new Three.Box3().setFromObject(model);
  model.position.sub(bounds.getCenter(new Three.Vector3()));
  const pivot = new Three.Group();
  pivot.add(model);
  scene.add(pivot);
  const hullMaterial = new Three.MeshBasicMaterial({color: 0x15eeff, side: Three.BackSide});
  const outline = model.clone(true);
  outline.traverse((obj) => {
    if (obj.isMesh) {
      obj.material = hullMaterial;
      obj.renderOrder = -1;
    }
  });
  // Shell expands around the centered model, tracing the full silhouette.
  const outlinePivot = new Three.Group();
  outlinePivot.scale.setScalar(1.026);
  outlinePivot.add(outline);
  outlinePivot.visible = false;
  pivot.add(outlinePivot);
  let last = 0;
  let frame = 0;
  let lost = false;

  function render(now = 0) {
    frame = 0;
    if (!isActive() || document.hidden || lost) { last = 0; return; }
    const size = target.getBoundingClientRect();
    if (!size.width || !size.height) return;
    const pixelRatio = renderer.getPixelRatio();
    if (Math.abs(canvas.width - size.width * pixelRatio) > 1 || Math.abs(canvas.height - size.height * pixelRatio) > 1) {
      renderer.setSize(size.width, size.height, false);
      camera.aspect = size.width / size.height;
      camera.updateProjectionMatrix();
    }
    const animate = !isPaused() && !reduced.matches;
    const hovered = target.matches(":hover, :focus-visible, [data-tap-preview]");
    outlinePivot.visible = hovered;
    const spin = animate && hovered;
    if (spin && last) pivot.rotation.y += Math.min(40, now - last) * .00075;
    renderer.render(scene, camera);
    canvas.hidden = false;
    orbit.dataset.model = "3d";
    last = spin ? now : 0;
    if (spin) frame = requestAnimationFrame(render);
  }

  function refresh() {
    if (!frame && isActive() && !document.hidden && !lost) frame = requestAnimationFrame(render);
  }

  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    lost = true;
    last = 0;
    canvas.hidden = true;
    orbit.dataset.model = "poster";
  });
  canvas.addEventListener("webglcontextrestored", () => { lost = false; refresh(); });
  for (const name of ["pointerenter", "pointerleave", "focus", "blur"]) target.addEventListener(name, refresh);
  new MutationObserver(refresh).observe(target, {attributeFilter: ["data-tap-preview"]});
  reduced.addEventListener("change", refresh);
  document.addEventListener("visibilitychange", refresh);
  new ResizeObserver(refresh).observe(target);
  refresh();
  return refresh;
}

/** Export the actual procedural browser model for an editable Blender handoff. */
import {writeFile, mkdir, readFile} from "node:fs/promises";
import {createHash} from "node:crypto";
import {resolve, dirname} from "node:path";
import * as Three from "../web/assets/three-0.187.0/three.module.js";
import {createGagooModel} from "../web/gagoo-scene.js";

const output = resolve(process.argv[2] || "data/raw/gagoo-assets/gagoo-geometry.json");
const model = createGagooModel(Three);
model.updateMatrixWorld(true);
const nodes = [];
const nodeIds = new Map();
model.traverse(object => nodeIds.set(object, `part_${String(nodeIds.size).padStart(3, "0")}`));
const materialIds = new Map();
const materials = [];
function serializeMaterial(material) {
  if (materialIds.has(material)) return materialIds.get(material);
  const id = materials.length;
  materialIds.set(material, id);
  materials.push({
    id, name: material.name || `material_${id}`,
    color_linear: material.color?.toArray() || [1, 1, 1],
    opacity: material.opacity, transparent: material.transparent,
    metalness: material.metalness || 0, roughness: material.roughness ?? .6,
    emissive_linear: material.emissive?.toArray() || [0, 0, 0],
    emissive_intensity: material.emissiveIntensity || 0,
    unlit: Boolean(material.isMeshBasicMaterial),
    flat_shading: Boolean(material.flatShading),
    double_sided: material.side === Three.DoubleSide,
    clearcoat: material.clearcoat || 0
  });
  return id;
}
model.traverse((object) => {
  const node = {id: nodeIds.get(object), parent: object === model ? null : nodeIds.get(object.parent), name: object.name || object.type, matrix: object.matrix.toArray(), type: object.type};
  if (object.isMesh) {
    if (Array.isArray(object.material)) throw new Error("Material groups require an explicit importer; refusing to flatten them silently.");
    const position = object.geometry.getAttribute("position");
    node.positions = Array.from(position.array);
    node.indices = object.geometry.index ? Array.from(object.geometry.index.array) : Array.from({length: position.count}, (_, index) => index);
    node.material_id = serializeMaterial(object.material);
    node.uv = object.geometry.getAttribute("uv") ? Array.from(object.geometry.getAttribute("uv").array) : null;
  }
  nodes.push(node);
});
const sourceHashes = {};
for (const path of ["web/gagoo-scene.js", "web/gagoo-physics.js", "web/assets/three-0.187.0/three.module.js"]) {
  sourceHashes[path] = createHash("sha256").update(await readFile(path)).digest("hex");
}
const bounds = new Three.Box3().setFromObject(model);
const payload = {
  schema_version: 1, source_kind: "runtime procedural geometry export; not hand-sculpted",
  source_axes: "Y up, face +Z", source_hashes: sourceHashes,
  bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()},
  materials, nodes,
  limits: ["Static mesh handoff, no armature or baked animation.", "Browser and Blender lighting/alpha sorting can differ; geometry and part transforms are preserved."]
};
await mkdir(dirname(output), {recursive: true});
const bytes = JSON.stringify(payload);
await writeFile(output, bytes);
model.userData.dispose?.();
console.log(JSON.stringify({output, meshes: nodes.filter(node => node.positions).length, triangles: nodes.reduce((sum, node) => sum + (node.indices?.length || 0) / 3, 0), sha256: createHash("sha256").update(bytes).digest("hex")}));

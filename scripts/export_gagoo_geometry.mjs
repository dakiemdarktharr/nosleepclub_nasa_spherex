/** Export the actual procedural browser model for an editable Blender handoff. */
import {writeFile, mkdir, readFile} from "node:fs/promises";
import {createHash} from "node:crypto";
import {resolve, dirname} from "node:path";
import * as Three from "../web/assets/three-0.187.0/three.module.js";
import {createGagooModel} from "../web/gagoo-scene.js";
import {createRagdollController, GAGOO_JOINTS} from "../web/gagoo-ragdoll.js";

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
  if (object.isBone) {
    let parentBone = object.parent;
    while (parentBone && !parentBone.isBone) parentBone = parentBone.parent;
    node.bone_parent = parentBone ? nodeIds.get(parentBone) : null;
    node.rest_matrix_world = object.matrixWorld.toArray();
    node.joint = object.userData.joint;
    node.limits = GAGOO_JOINTS[node.joint].limits;
  }
  if (object.isMesh) {
    if (Array.isArray(object.material)) throw new Error("Material groups require an explicit importer; refusing to flatten them silently.");
    const position = object.geometry.getAttribute("position");
    node.positions = Array.from(position.array);
    node.indices = object.geometry.index ? Array.from(object.geometry.index.array) : Array.from({length: position.count}, (_, index) => index);
    node.material_id = serializeMaterial(object.material);
    node.rigid_bone = object.userData.rigidBone;
    if (!node.rigid_bone) throw new Error(`Unbound rig mesh: ${object.name}`);
    node.uv = object.geometry.getAttribute("uv") ? Array.from(object.geometry.getAttribute("uv").array) : null;
  }
  nodes.push(node);
});
const sourceHashes = {};
for (const path of ["web/gagoo-scene.js", "web/gagoo-physics.js", "web/gagoo-rig.js", "web/gagoo-ragdoll.js", "web/assets/three-0.187.0/three.module.js"]) {
  sourceHashes[path] = createHash("sha256").update(await readFile(path)).digest("hex");
}
const bounds = new Three.Box3().setFromObject(model);
const motion = createRagdollController(model);
const samples = [];
for (let frame = 0; frame <= 120; frame++) {
  if (frame === 1) motion.impulse({x: 8, y: -3, z: 7}, .85);
  if (frame > 0) motion.step(1 / 30);
  samples.push({time: frame / 30, rotations: Object.fromEntries(Object.entries(model.userData.rig.joints).map(([name, bone]) => [bone.name, bone.quaternion.toArray()]))});
}
motion.reset();
const payload = {
  schema_version: 2, source_kind: "runtime articulated geometry and bone rig export; not hand-sculpted",
  source_axes: "Y up, face +Z", source_hashes: sourceHashes,
  bounds: {min: bounds.min.toArray(), max: bounds.max.toArray()},
  materials, nodes,
  rig: {type: 'rigid-part armature', bone_count: Object.keys(model.userData.rig.joints).length, influences_per_vertex: 1, clip: {name: 'Gagoo_Loose_Joint_Response', fps: 30, samples}},
  limits: ["Rigid-part FK armature: each vertex has one bone influence; no soft-skin deformation or IK controls.", "One free joint-response demonstration is baked from the runtime spring solver; it is not the staged glass-slide cinematic. Browser dragging is simulated live, not replayed.", "Browser and Blender lighting/alpha sorting can differ; geometry and part transforms are preserved."]
};
await mkdir(dirname(output), {recursive: true});
const bytes = JSON.stringify(payload);
await writeFile(output, bytes);
model.userData.dispose?.();
console.log(JSON.stringify({output, meshes: nodes.filter(node => node.positions).length, triangles: nodes.reduce((sum, node) => sum + (node.indices?.length || 0) / 3, 0), sha256: createHash("sha256").update(bytes).digest("hex")}));

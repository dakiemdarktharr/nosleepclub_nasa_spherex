/** Check the Blender GLB against its source geometry, with no browser required. */
import {readFile, writeFile} from "node:fs/promises";
import {createHash} from "node:crypto";
import {resolve} from "node:path";
import * as Three from "../web/assets/three-0.187.0/three.module.js";
import {GLTFLoader} from "../web/assets/three-0.187.0/loaders/GLTFLoader.js";

const directory = resolve(process.argv[2] || "data/raw/gagoo-assets");
const source = JSON.parse(await readFile(resolve(directory, "gagoo-geometry.json"), "utf8"));
for (const [path, expected] of Object.entries(source.source_hashes)) {
  const actual = createHash("sha256").update(await readFile(path)).digest("hex");
  if (actual !== expected) throw new Error(`Source changed since export: ${path}`);
}
const raw = await readFile(resolve(directory, "gagoo-lowpoly.glb"));
const loaded = await new GLTFLoader().parseAsync(raw.buffer.slice(raw.byteOffset, raw.byteOffset + raw.byteLength), "");
const box = new Three.Box3().setFromObject(loaded.scene);
const actual = {min: box.min.toArray(), max: box.max.toArray()};
const errors = ["min", "max"].flatMap(key => actual[key].map((value, index) => Math.abs(value - source.bounds[key][index])));
const maxError = Math.max(...errors);
if (!Number.isFinite(maxError) || maxError > .00001) throw new Error(`GLB bounds mismatch: ${JSON.stringify({actual, expected: source.bounds})}`);
let meshes = 0, triangles = 0, skinnedMeshes = 0;
let maxPoseError = 0;
const bones = new Set();
loaded.scene.traverse(node => {
  if (!node.isMesh) return;
  meshes++;
  triangles += (node.geometry.index?.count || node.geometry.attributes.position.count) / 3;
  if (node.isSkinnedMesh) {
    skinnedMeshes++;
    for (const bone of node.skeleton.bones) bones.add(bone.name);
    const weights = node.geometry.attributes.skinWeight;
    for (let i = 0; i < weights.count; i++) {
      if (Math.abs(weights.getX(i) - 1) > 1e-6 || weights.getY(i) !== 0 || weights.getZ(i) !== 0 || weights.getW(i) !== 0) throw new Error('Rigid-part vertex weights must have one normalized influence');
    }
  }
});
const sourceMeshes = source.nodes.filter(node => node.positions);
const sourceTriangles = sourceMeshes.reduce((sum, node) => sum + node.indices.length / 3, 0);
if (meshes !== sourceMeshes.length || triangles !== sourceTriangles) throw new Error("GLB mesh/triangle count differs from the source geometry");
if (source.rig) {
  if (skinnedMeshes !== meshes || bones.size !== source.rig.bone_count) throw new Error(`Exported armature is incomplete: ${skinnedMeshes} skinned meshes, ${bones.size} bones`);
  if (loaded.animations.length !== 1) throw new Error('Expected the runtime-sampled rebound clip');
  const restRotations = new Map();
  loaded.scene.traverse(node => { if (node.isBone) restRotations.set(node.name, node.quaternion.clone().normalize()); });
  const mixer = new Three.AnimationMixer(loaded.scene);
  const action = mixer.clipAction(loaded.animations[0]);
  action.play(); mixer.setTime(.3); loaded.scene.updateMatrixWorld(true);
  const arm = loaded.scene.getObjectByName('gagoo_leftArm');
  if (!arm || arm.quaternion.angleTo(new Three.Quaternion()) < .05) throw new Error('Exported animation does not move the armature');
  for (const sample of source.rig.clip.samples) {
    // Stay just below the last key so the default clip loop cannot wrap.
    mixer.setTime(Math.min(sample.time, loaded.animations[0].duration - 1e-7));
    for (const [name, quaternion] of Object.entries(sample.rotations)) {
      const bone = loaded.scene.getObjectByName(name);
      const expected = new Three.Quaternion().fromArray(quaternion).normalize();
      // The top exported bone includes Blender's Y-up conversion in its rest
      // transform. Compare local motion relative to bind pose for every bone.
      const delta = bone && restRotations.get(name).clone().invert().multiply(bone.quaternion).normalize();
      const error = delta ? delta.angleTo(expected) : Infinity;
      maxPoseError = Math.max(maxPoseError, error);
      if (error > .0005) throw new Error(`Baked armature pose differs from runtime at ${sample.time}s: ${name}`);
    }
  }
  mixer.stopAllAction();
}
const report = {passed: true, meshes, triangles, skinned_meshes: skinnedMeshes, bones: bones.size, animation_clips: loaded.animations.map(clip => ({name: clip.name, duration: clip.duration})), animation_samples_verified: source.rig?.clip.samples.length || 0, max_pose_error_radians: maxPoseError, max_bound_error: maxError, actual_bounds: actual, source_hashes_match_current_files: true};
await writeFile(resolve(directory, "glb-roundtrip.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));

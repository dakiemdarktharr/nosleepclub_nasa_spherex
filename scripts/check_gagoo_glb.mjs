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
let meshes = 0, triangles = 0;
loaded.scene.traverse(node => {
  if (!node.isMesh) return;
  meshes++;
  triangles += (node.geometry.index?.count || node.geometry.attributes.position.count) / 3;
});
const sourceMeshes = source.nodes.filter(node => node.positions);
const sourceTriangles = sourceMeshes.reduce((sum, node) => sum + node.indices.length / 3, 0);
if (meshes !== sourceMeshes.length || triangles !== sourceTriangles) throw new Error("GLB mesh/triangle count differs from the source geometry");
const report = {passed: true, meshes, triangles, max_bound_error: maxError, actual_bounds: actual, source_hashes_match_current_files: true};
await writeFile(resolve(directory, "glb-roundtrip.json"), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));

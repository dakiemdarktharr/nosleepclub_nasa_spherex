const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');

(async () => {
  const load = file => import(pathToFileURL(path.join(__dirname, '../web', file)));
  const T = await load('assets/three-0.187.0/three.module.js');
  const {createGagooModel} = await load('gagoo-scene.js');
  const {applyGagooInk} = await load('gagoo-ink.js');
  const model = createGagooModel();
  const parts = [];
  model.traverse(node => { if (node.isMesh) parts.push([node, node.material]); });
  let geometryDisposals = 0, materialDisposals = 0;
  const geometries = new Set(parts.map(([part]) => part.geometry));
  const materials = new Set(parts.map(([,material]) => material));
  for (const geometry of geometries) geometry.addEventListener('dispose', () => geometryDisposals++);
  for (const material of materials) material.addEventListener('dispose', () => materialDisposals++);
  const clean = applyGagooInk(model, T);
  for (const [part, original] of parts) {
    if (original.transparent) assert.equal(part.material, original, 'visor keeps transparency');
    else if (!original.isMeshBasicMaterial) assert.ok(part.material.isMeshToonMaterial);
    if (/eye|pupil/.test(part.name)) assert.equal(part.children.filter(child => child.userData.inkOutline).length, 0, 'avoid layered eye rings');
  }
  let shells = 0;
  model.traverse(node => { if (node.userData.inkOutline) shells++; });
  assert.ok(shells > 10, 'major silhouette surfaces receive ink');
  clean(); clean();
  for (const [part, original] of parts) assert.equal(part.material, original, 'return borrowed material to its original owner');
  assert.equal(geometryDisposals, 0, 'ink teardown must not dispose geometry still owned by the character');
  assert.equal(materialDisposals, 0, 'ink teardown must not dispose original materials');
  model.traverse(node => assert.ok(!node.userData.inkOutline, 'remove all runtime outline shells'));
  model.userData.dispose();
  assert.equal(geometryDisposals, geometries.size);
  assert.equal(materialDisposals, materials.size);
  console.log('Gagoo ink: transparent visor, clean eyes and resource ownership/teardown passed');
})().catch(error => { console.error(error); process.exitCode = 1; });

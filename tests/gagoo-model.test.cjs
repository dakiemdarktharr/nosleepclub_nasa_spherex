const assert = require('node:assert/strict');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

(async () => {
  const {createGagooModel} = await import(pathToFileURL(path.join(__dirname, '../web/gagoo-scene.js')));
  const T = await import(pathToFileURL(path.join(__dirname, '../web/assets/three-0.187.0/three.module.js')));
  const model = createGagooModel();
  model.updateMatrixWorld(true);
  const bounds = new T.Box3().setFromObject(model);
  assert.ok(Math.abs(bounds.max.y - bounds.min.y - 3.2) < 1e-6, 'shared cinematic model remains normalized');
  assert.ok(model.userData.geometryStats.triangles < 4000, 'keep broad low-poly geometry');
  assert.ok(model.userData.geometryStats.meshes < 50, 'keep simple parts, including four joint cores that close elbow/knee gaps');
  const eyes = [];
  model.traverse(node => { if (node.name === 'single amber eye') eyes.push(node); });
  assert.equal(eyes.length, 2);
  const head = model.getObjectByName('broad forehead and clean cheek planes');
  head.geometry.computeBoundingBox();
  const headWidth = head.geometry.boundingBox.max.x - head.geometry.boundingBox.min.x;
  eyes[0].geometry.computeBoundingBox();
  const eyeWidth = eyes[0].geometry.boundingBox.max.x - eyes[0].geometry.boundingBox.min.x;
  const relativeReduction = 1 - (eyeWidth / headWidth) / (.8 / 1.98);
  assert.ok(relativeReduction >= .15 && relativeReduction <= .20, 'visible iris, including bevel, is 15–20% smaller relative to head');

  // Check each head side quad geometrically: diagonal triangulation must not add
  // a second cheek plane. End caps are excluded from this side-strip check.
  const hp = head.geometry.attributes.position, hi = head.geometry.index;
  const va = new T.Vector3(), vb = new T.Vector3(), vc = new T.Vector3(), vd = new T.Vector3();
  for (let i = 0; i < 5 * 8 * 6; i += 6) {
    va.fromBufferAttribute(hp, hi.getX(i)); vb.fromBufferAttribute(hp, hi.getX(i + 1)); vc.fromBufferAttribute(hp, hi.getX(i + 2)); vd.fromBufferAttribute(hp, hi.getX(i + 4));
    const plane = new T.Plane().setFromCoplanarPoints(va, vb, vc);
    assert.ok(Math.abs(plane.distanceToPoint(vd)) < 1e-6, 'head quad is planar');
  }

  // Independently test every head vertex against actual helmet triangle planes
  // in world space. The neck intentionally passes through the open collar.
  const helmet = model.getObjectByName('clear polygonal helmet');
  const position = helmet.geometry.attributes.position, index = helmet.geometry.index;
  const center = new T.Box3().setFromObject(helmet).getCenter(new T.Vector3());
  const vertices = [];
  model.userData.head.traverse(node => {
    if (!node.isMesh || node.name === 'neck') return;
    const p = node.geometry.attributes.position;
    for (let i = 0; i < p.count; i++) vertices.push(new T.Vector3().fromBufferAttribute(p, i).applyMatrix4(node.matrixWorld));
  });
  let minimumClearance = Infinity;
  for (let i = 0; i < index.count; i += 3) {
    va.fromBufferAttribute(position, index.getX(i)).applyMatrix4(helmet.matrixWorld);
    vb.fromBufferAttribute(position, index.getX(i + 1)).applyMatrix4(helmet.matrixWorld);
    vc.fromBufferAttribute(position, index.getX(i + 2)).applyMatrix4(helmet.matrixWorld);
    const normal = vb.clone().sub(va).cross(vc.clone().sub(va)).normalize();
    if (normal.dot(va.clone().sub(center)) < 0) normal.negate();
    for (const vertex of vertices) minimumClearance = Math.min(minimumClearance, normal.dot(va.clone().sub(vertex)));
  }
  assert.ok(vertices.length > 1000);
  assert.ok(minimumClearance > .02, `head/ears must remain inside helmet: ${minimumClearance}`);
  model.userData.dispose();
  console.log(`Gagoo model: normalized, ${model.userData.geometryStats.triangles} triangles, planar cheeks, ${(relativeReduction * 100).toFixed(2)}% smaller eyes, helmet clearance ${minimumClearance.toFixed(5)} passed`);
})().catch(error => { console.error(error); process.exitCode = 1; });

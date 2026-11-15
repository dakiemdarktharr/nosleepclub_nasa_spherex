const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');

(async () => {
  const load = name => import(pathToFileURL(path.join(__dirname, '../web/', name)));
  const {createGagooModel} = await load('gagoo-scene.js');
  const {GAGOO_JOINTS, createRagdollState, impulseRagdoll, stepRagdoll, createRagdollController} = await load('gagoo-ragdoll.js');
  const T = await load('assets/three-0.187.0/three.module.js');
  const state = createRagdollState();
  impulseRagdoll(state, {x: 14, y: -8, z: 20}, 1);
  let maxArm = 0;
  for (let frame = 0; frame < 1200; frame++) {
    stepRagdoll(state, frame === 30 ? 2 : 1 / 60);
    maxArm = Math.max(maxArm, Math.abs(state.leftArm.angle[0]), Math.abs(state.leftArm.angle[2]));
    for (const [name, joint] of Object.entries(state)) for (let axis = 0; axis < 3; axis++) {
      const [low, high] = GAGOO_JOINTS[name].limits[axis];
      assert.ok(Number.isFinite(joint.angle[axis]) && Number.isFinite(joint.velocity[axis]));
      assert.ok(joint.angle[axis] >= low && joint.angle[axis] <= high, `${name} joint limit`);
    }
  }
  assert.ok(maxArm > .35, 'ragdoll should be visibly responsive, not static');
  assert.ok(Object.values(state).every(j => j.angle.every(v => Math.abs(v) < .0001)), 'motion settles without drift');
  // A gentle impulse should produce a loose follow-through, not a quick
  // mechanical snap. Distal joints must turn back before the heavier arm.
  const gentle = createRagdollState();
  impulseRagdoll(gentle, {x: 0, y: 0, z: 1.8});
  let gentlePeak = 0, firstReturn = 0, armAtOneSecond = 0, handAtOneSecond = 0;
  for (let frame = 1; frame <= 360; frame++) {
    stepRagdoll(gentle, 1 / 120);
    gentlePeak = Math.max(gentlePeak, Math.abs(gentle.leftArm.angle[0]));
    if (!firstReturn && gentle.leftArm.angle[0] > 0) firstReturn = frame / 120;
    if (frame === 120) { armAtOneSecond = gentle.leftArm.angle[0]; handAtOneSecond = gentle.leftHand.angle[0]; }
  }
  assert.ok(gentlePeak > .35 && gentlePeak < .7, 'a gentle drag has visible, controlled arm follow-through');
  assert.ok(firstReturn > 1 && firstReturn < 1.7, 'the loose arm should reverse slowly after its first swing');
  assert.ok(armAtOneSecond < -.1 && handAtOneSecond > 0, 'hand and arm should settle at different rates');
  const coarse = createRagdollState(), fine = createRagdollState();
  impulseRagdoll(coarse, [4, -3, 5]); impulseRagdoll(fine, [4, -3, 5]);
  for (let i = 0; i < 30; i++) stepRagdoll(coarse, 1 / 30);
  for (let i = 0; i < 120; i++) stepRagdoll(fine, 1 / 120);
  for (const name of Object.keys(coarse)) for (let a = 0; a < 3; a++) assert.ok(Math.abs(coarse[name].angle[a] - fine[name].angle[a]) < 1e-8);
  stepRagdoll(fine, NaN, {x: Infinity});
  const model = createGagooModel(), ragdoll = createRagdollController(model);
  const rig = model.userData.rig;
  assert.equal(Object.keys(rig.joints).length, 19);
  assert.ok(Object.values(rig.joints).every(bone => bone.isBone));
  assert.equal(model.userData.rightHand, rig.joints.rightHand);
  // Joint transforms rotate only; no part can translate away from its parent.
  const bindPositions = Object.fromEntries(Object.entries(rig.joints).map(([name, bone]) => [name, bone.position.toArray()]));
  ragdoll.impulse({x: 7, y: 3, z: 12});
  for (let i = 0; i < 30; i++) ragdoll.step(1 / 60);
  const saved = ragdoll.snapshot(), pose = rig.snapshot();
  ragdoll.reset(); ragdoll.restore(saved);
  assert.deepEqual(rig.snapshot(), pose, 'cinematic handoff preserves the exact live pose');
  for (const [name, bone] of Object.entries(rig.joints)) assert.deepEqual(bone.position.toArray(), bindPositions[name]);

  function helmetClearance() {
    model.updateMatrixWorld(true);
    const helmet = model.getObjectByName('clear polygonal helmet');
    const p = helmet.geometry.attributes.position, index = helmet.geometry.index;
    const center = new T.Box3().setFromObject(helmet).getCenter(new T.Vector3());
    const vertices = [];
    model.userData.head.traverse(node => {
      if (!node.isMesh || node.name === 'neck') return;
      for (let i = 0; i < node.geometry.attributes.position.count; i++) vertices.push(new T.Vector3().fromBufferAttribute(node.geometry.attributes.position, i).applyMatrix4(node.matrixWorld));
    });
    let clearance = Infinity;
    for (let i = 0; i < index.count; i += 3) {
      const a = new T.Vector3().fromBufferAttribute(p, index.getX(i)).applyMatrix4(helmet.matrixWorld);
      const b = new T.Vector3().fromBufferAttribute(p, index.getX(i + 1)).applyMatrix4(helmet.matrixWorld);
      const c = new T.Vector3().fromBufferAttribute(p, index.getX(i + 2)).applyMatrix4(helmet.matrixWorld);
      const normal = b.sub(a).cross(c.sub(a)).normalize();
      if (normal.dot(a.clone().sub(center)) < 0) normal.negate();
      for (const v of vertices) clearance = Math.min(clearance, normal.dot(a.clone().sub(v)));
    }
    return clearance;
  }
  let minimum = Infinity;
  // Test all eight extreme combinations, including opposite ear folding and
  // maximum eye offsets while the entire head/helmet assembly is tilted.
  for (let sample = 0; sample < 8; sample++) {
    const extreme = createRagdollState();
    for (const name of ['neck', 'leftEar', 'rightEar', 'leftEye', 'rightEye']) {
      extreme[name].angle = GAGOO_JOINTS[name].limits.map((limit, axis) => limit[(sample >> axis) & 1]);
    }
    ragdoll.restore({joints: extreme});
    const clearance = helmetClearance();
    minimum = Math.min(minimum, clearance);
    assert.ok(clearance > .005, `head and ear must remain inside helmet at pose ${sample}: ${clearance}`);
  }
  model.userData.dispose();
  console.log(`Gagoo rig: 19 bone joints, loose follow-through ${(gentlePeak * 180 / Math.PI).toFixed(1)} degrees, delayed reversal ${firstReturn.toFixed(2)}s, stable timestep, exact pose handoff, helmet clearance ${minimum.toFixed(5)} passed`);
})().catch(error => { console.error(error); process.exitCode = 1; });

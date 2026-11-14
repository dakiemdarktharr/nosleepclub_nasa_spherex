/** Bounded angular spring rig, in radians and seconds. No world gravity in EVA.
 * Rigid links stay attached; eye/ear motion is deliberately smaller than limbs.
 * This is a stylized articulated ragdoll, not a general collision solver.
 */
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
const finite = n => Number.isFinite(n) ? n : 0;
const axes = ['x', 'y', 'z'];
const vector = value => axes.map((axis, i) => finite(Array.isArray(value) ? value[i] : value?.[axis]));
const symmetric = values => values.map(v => [-v, v]);

export const GAGOO_JOINTS = {
  root: {limits: symmetric([.02, .02, .02]), spring: 28, damping: 7, gain: 0},
  spine: {limits: symmetric([.09, .06, .10]), spring: 32, damping: 5.5, gain: .12},
  neck: {limits: symmetric([.20, .16, .19]), spring: 23, damping: 4.0, gain: .28},
  leftEar: {limits: [[-.07, .07], [-.05, .05], [-.18, .018]], spring: 49, damping: 3.0, gain: .22},
  rightEar: {limits: [[-.07, .07], [-.05, .05], [-.018, .18]], spring: 47, damping: 3.1, gain: .22},
  leftEye: {limits: symmetric([.045, .055, .028]), spring: 65, damping: 4.0, gain: .06},
  rightEye: {limits: symmetric([.045, .055, .028]), spring: 62, damping: 4.2, gain: .06},
  leftArm: {limits: symmetric([.85, .35, .70]), spring: 14, damping: 2.9, gain: .85},
  rightArm: {limits: symmetric([.85, .35, .70]), spring: 15, damping: 3.0, gain: .82},
  leftForearm: {limits: [[-.95, .35], [-.14, .14], [-.38, .38]], spring: 18, damping: 3.1, gain: .72},
  rightForearm: {limits: [[-.95, .35], [-.14, .14], [-.38, .38]], spring: 17, damping: 3.0, gain: .74},
  leftHand: {limits: symmetric([.32, .22, .28]), spring: 23, damping: 3.1, gain: .4},
  rightHand: {limits: symmetric([.32, .22, .28]), spring: 24, damping: 3.2, gain: .4},
  leftLeg: {limits: symmetric([.60, .22, .38]), spring: 15, damping: 3.1, gain: .68},
  rightLeg: {limits: symmetric([.60, .22, .38]), spring: 16, damping: 3.0, gain: .70},
  leftShin: {limits: [[-.20, .70], [-.12, .12], [-.15, .15]], spring: 20, damping: 3.6, gain: .57},
  rightShin: {limits: [[-.20, .70], [-.12, .12], [-.15, .15]], spring: 21, damping: 3.5, gain: .55},
  leftFoot: {limits: symmetric([.28, .12, .18]), spring: 24, damping: 3.6, gain: .36},
  rightFoot: {limits: symmetric([.28, .12, .18]), spring: 25, damping: 3.7, gain: .36}
};

export function createRagdollState() {
  return Object.fromEntries(Object.keys(GAGOO_JOINTS).map(name => [name, {angle: [0, 0, 0], velocity: [0, 0, 0]}]));
}

function torque(name, acceleration) {
  const side = name.startsWith('left') ? -1 : name.startsWith('right') ? 1 : 0;
  const ear = name.endsWith('Ear'), eye = name.endsWith('Eye');
  const [x, y, z] = acceleration;
  if (eye) return [-y * .6, -x * .7, -x * .15];
  if (ear) return [-z * .45 + y * .12, x * .12, -x * .75 + side * Math.abs(y) * .3];
  return [-z - y * .22, x * .14 + z * side * .08, x + y * side * .20];
}

export function impulseRagdoll(state, impulse, strength = 1) {
  const values = vector(impulse).map(v => clamp(v, -30, 30));
  strength = clamp(finite(strength), 0, 4);
  for (const [name, joint] of Object.entries(state)) {
    const config = GAGOO_JOINTS[name];
    if (!config) continue;
    const force = torque(name, values);
    for (let axis = 0; axis < 3; axis++) joint.velocity[axis] = clamp(joint.velocity[axis] + force[axis] * config.gain * strength, -9, 9);
  }
}

export function stepRagdoll(state, dt, acceleration = {}, strength = 1) {
  dt = clamp(finite(dt), 0, .1);
  if (!dt) return state;
  const input = vector(acceleration).map(v => clamp(v, -45, 45));
  strength = clamp(finite(strength), 0, 4);
  // Small substeps make touch bursts and frame stalls behave like steady 60fps.
  const count = Math.max(1, Math.ceil(dt * 120)), h = dt / count;
  for (let substep = 0; substep < count; substep++) {
    for (const [name, joint] of Object.entries(state)) {
      const config = GAGOO_JOINTS[name];
      if (!config) continue;
      const force = torque(name, input);
      for (let axis = 0; axis < 3; axis++) {
        const [lower, upper] = config.limits[axis];
        joint.velocity[axis] += (force[axis] * config.gain * strength - config.spring * joint.angle[axis] - config.damping * joint.velocity[axis]) * h;
        joint.angle[axis] += joint.velocity[axis] * h;
        if (joint.angle[axis] < lower || joint.angle[axis] > upper) {
          joint.angle[axis] = clamp(joint.angle[axis], lower, upper);
          joint.velocity[axis] *= -.18;
        }
        if (Math.abs(joint.angle[axis]) < 1e-6 && Math.abs(joint.velocity[axis]) < 1e-5) joint.angle[axis] = joint.velocity[axis] = 0;
      }
    }
  }
  return state;
}

export function createRagdollController(model) {
  const rig = model?.userData?.rig;
  if (!rig?.joints) throw new TypeError('Gagoo rig is required');
  let state = createRagdollState();
  let pose = {};
  function apply() {
    for (const [name, joint] of Object.entries(rig.joints)) {
      const rest = rig.rest[name].rotation;
      const base = vector(pose[name]);
      const offset = state[name]?.angle || [0, 0, 0];
      const limits = GAGOO_JOINTS[name].limits;
      joint.rotation.set(...rest.map((angle, axis) => angle + clamp(base[axis] + offset[axis], ...limits[axis])));
    }
    model.updateMatrixWorld(true);
  }
  const api = {
    step(dt, options = {}) {
      pose = options.pose || {};
      stepRagdoll(state, dt, options.acceleration, options.strength ?? 1);
      apply();
      return api;
    },
    impulse(impulse, strength = 1) { impulseRagdoll(state, impulse, strength); return api; },
    reset() { state = createRagdollState(); pose = {}; apply(); },
    snapshot() { return {version: 1, joints: structuredClone(state), pose: structuredClone(pose)}; },
    restore(saved) {
      if (!saved?.joints) return;
      state = createRagdollState();
      for (const [name, values] of Object.entries(saved.joints)) {
        if (!state[name]) continue;
        state[name].angle = vector(values.angle).map((v, i) => clamp(v, ...GAGOO_JOINTS[name].limits[i]));
        state[name].velocity = vector(values.velocity).map(v => clamp(v, -9, 9));
      }
      pose = saved.pose || {};
      apply();
    },
    get energy() { return Object.values(state).reduce((sum, j) => sum + j.angle.reduce((s, v) => s + v * v, 0) + j.velocity.reduce((s, v) => s + v * v, 0), 0); }
  };
  return api;
}

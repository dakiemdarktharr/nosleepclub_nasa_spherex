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
  spine: {limits: symmetric([.13, .09, .14]), spring: 19, damping: 3.0, gain: .16},
  neck: {limits: symmetric([.24, .19, .23]), spring: 13, damping: 2.2, gain: .35},
  leftEar: {limits: [[-.07, .07], [-.05, .05], [-.18, .018]], spring: 32, damping: 2.0, gain: .27},
  rightEar: {limits: [[-.07, .07], [-.05, .05], [-.018, .18]], spring: 30, damping: 2.1, gain: .27},
  leftEye: {limits: symmetric([.045, .055, .028]), spring: 44, damping: 3.0, gain: .07},
  rightEye: {limits: symmetric([.045, .055, .028]), spring: 42, damping: 3.1, gain: .07},
  // More front/back travel, but inward side-folding stops before a limb swings
  // through the torso. Outward travel is deliberately broader and floppy.
  leftArm: {limits: [[-1.10, 1.10], [-.42, .42], [-1.00, .18]], spring: 6.5, damping: 1.45, gain: 1.0},
  rightArm: {limits: [[-1.10, 1.10], [-.42, .42], [-.18, 1.00]], spring: 7.0, damping: 1.5, gain: .97},
  leftForearm: {limits: [[-1.20, .40], [-.18, .18], [-.42, .42]], spring: 8.5, damping: 1.8, gain: .87},
  rightForearm: {limits: [[-1.20, .40], [-.18, .18], [-.42, .42]], spring: 8.0, damping: 1.75, gain: .89},
  leftHand: {limits: symmetric([.40, .27, .34]), spring: 12, damping: 2.0, gain: .48},
  rightHand: {limits: symmetric([.40, .27, .34]), spring: 12.5, damping: 2.1, gain: .48},
  leftLeg: {limits: [[-.80, .80], [-.27, .27], [-.48, .16]], spring: 8.0, damping: 1.7, gain: .79},
  rightLeg: {limits: [[-.80, .80], [-.27, .27], [-.16, .48]], spring: 8.5, damping: 1.75, gain: .82},
  leftShin: {limits: [[-.20, .95], [-.14, .14], [-.18, .18]], spring: 10, damping: 1.9, gain: .68},
  rightShin: {limits: [[-.20, .95], [-.14, .14], [-.18, .18]], spring: 10.5, damping: 2.0, gain: .66},
  leftFoot: {limits: symmetric([.36, .15, .23]), spring: 12, damping: 2.1, gain: .44},
  rightFoot: {limits: symmetric([.36, .15, .23]), spring: 12.5, damping: 2.2, gain: .44}
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

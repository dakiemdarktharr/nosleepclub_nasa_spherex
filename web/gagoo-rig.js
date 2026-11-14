/** Rigid-part bone rig. Bind transforms preserve the approved low-poly model. */
export function attachGagooRig(T, model, body, head) {
  body.updateMatrixWorld(true);
  const joints = {}, rest = {};
  const bone = (name, parent, point, coordinates = body) => {
    coordinates.updateWorldMatrix(true, false);
    parent.updateWorldMatrix(true, false);
    const joint = new T.Bone();
    joint.name = `gagoo_${name}`;
    joint.userData.joint = name;
    joint.position.copy(parent.worldToLocal(coordinates.localToWorld(new T.Vector3(...point))));
    parent.add(joint);
    joint.updateWorldMatrix(true, false);
    joints[name] = joint;
    return joint;
  };
  const bind = (joint, object) => {
    joint.attach(object);
    object.traverse(node => { if (node.isMesh) node.userData.rigidBone = joint.name; });
  };
  const root = bone('root', body, [0, 0, 0]);
  const spine = bone('spine', root, [0, .05, 0]);
  const neck = bone('neck', spine, [0, .65, 0]);
  bind(neck, head);
  const headChildren = [...head.children];
  for (const side of [-1, 1]) {
    const name = side < 0 ? 'left' : 'right';
    const ear = headChildren.find(node => node.children.some(child => child.name === 'chunky beveled ear') && Math.sign(node.position.x) === side);
    // The ear root is near its inner base. Most motion folds toward the face,
    // with a small outward stop enforced by the physics controller.
    const earJoint = bone(`${name}Ear`, head, [side * .83, 2.00, -.05], head);
    bind(earJoint, ear);
    const eyeJoint = bone(`${name}Eye`, head, [side * .43, 1.94, .64], head);
    for (const part of headChildren.filter(node => ['single amber eye', 'dark pupil', 'single eye highlight'].includes(node.name) && Math.sign(node.position.x) === side)) bind(eyeJoint, part);
    const arm = body.children.find(node => node.name === `${name} arm`);
    const shoulder = bone(`${name}Arm`, spine, [side * .48, .30, 0]);
    bind(shoulder, arm);
    const forearm = bone(`${name}Forearm`, shoulder, [side * .65, .06, .03]);
    const hand = bone(`${name}Hand`, forearm, [side * .80, -.34, .09]);
    for (const part of [...arm.children]) {
      if (['forearm sleeve', 'simple cuff', 'elbow joint'].includes(part.name)) bind(forearm, part);
      else if (part.name === 'mitten hand') bind(hand, part);
    }
    const leg = bone(`${name}Leg`, root, [side * .27, -.36, 0]);
    const shin = bone(`${name}Shin`, leg, [side * .305, -.64, .02]);
    const foot = bone(`${name}Foot`, shin, [side * .35, -.99, .14]);
    const parts = [...body.children].filter(node => node.isMesh && Math.sign(node.position.x) === side);
    for (const part of parts) {
      if (part.name === 'upper leg') bind(leg, part);
      else if (['lower leg', 'knee joint'].includes(part.name)) bind(shin, part);
      else if (part.name === 'flat-soled boot') bind(foot, part);
      else if (part.name === 'single mustard sleeve patch') bind(shoulder, part);
    }
    model.userData[`${name}Arm`] = shoulder;
    model.userData[`${name}Hand`] = hand;
    model.userData[`${name}Leg`] = leg;
    model.userData[`${name}Foot`] = foot;
  }
  for (const part of [...body.children]) {
    if (part.isMesh) {
      const isHelmet = ['clear polygonal helmet', 'single soft upper reflection', 'single chunky helmet collar'].includes(part.name);
      bind(isHelmet ? neck : spine, part);
    } else if (part === model.userData.backpackAnchor) spine.attach(part);
  }
  for (const [name, joint] of Object.entries(joints)) {
    rest[name] = {position: joint.position.toArray(), quaternion: joint.quaternion.toArray(), rotation: joint.rotation.toArray().slice(0, 3)};
    joint.userData.bindRotation = rest[name].rotation;
  }
  model.userData.rig = {
    version: 1, type: 'rigid-part bone rig', joints, rest,
    reset() { for (const [name, joint] of Object.entries(joints)) joint.quaternion.fromArray(rest[name].quaternion); },
    snapshot() { return Object.fromEntries(Object.entries(joints).map(([name, joint]) => [name, joint.rotation.toArray().slice(0, 3).map((v, i) => v - rest[name].rotation[i])])); }
  };
  model.updateMatrixWorld(true);
  return model.userData.rig;
}

/** Small zero-gravity prop solver. Units are room metres and seconds.
 * Props use conservative sphere proxies; the astronaut uses a vertical capsule.
 * Contact impulses and spin are stylized, not a spacecraft engineering model.
 */
const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
const length = a => Math.hypot(...a);
const dot = (a, b) => a.reduce((sum, v, i) => sum + v * b[i], 0);
const minus = (a, b) => a.map((v, i) => v - b[i]);
const finite = (n, fallback = 0) => Number.isFinite(n) ? n : fallback;

export const ROOM_PROP_LAYOUT = [
  {id:'floating-mug', kind:'mug', position:[-.62,1.12,1.05], radius:.33, mass:.55, velocity:[.028,.015,-.018], rotation:[.18,-.2,-.24], spin:[.08,.12,-.04]},
  {id:'field-book', kind:'book', position:[.95,1.58,.75], radius:.36, mass:.8, velocity:[-.021,.01,.018], rotation:[.2,.5,-.23], spin:[-.045,.075,.06]},
  {id:'orbit-book', kind:'book', position:[-1.18,1.8,-1.25], radius:.34, mass:.7, velocity:[.012,-.013,.021], rotation:[-.3,-.4,.5], spin:[.07,-.06,.04]},
  {id:'orange-pen', kind:'pen', position:[-.15,1.02,-.3], radius:.25, mass:.09, velocity:[.014,.009,.016], rotation:[.5,.8,-.7], spin:[-.08,.1,.08]},
  {id:'teal-pen', kind:'pen', position:[2,1.55,2.55], radius:.25, mass:.09, velocity:[-.018,-.012,-.014], rotation:[-.3,-.2,.8], spin:[.09,-.08,.05]},
  {id:'floating-notepad', kind:'notepad', position:[-3.65,1.65,2.55], radius:.33, mass:.35, velocity:[.02,.012,-.014], rotation:[.12,-.15,.26], spin:[.04,.06,-.04]}
];

export function createFloatingPropState(layout = ROOM_PROP_LAYOUT) {
  return layout.map(item => ({...item, position:[...item.position], previous:[...item.position],
    velocity:[...(item.velocity || [0,0,0])], rotation:[...(item.rotation || [0,0,0])],
    spin:[...(item.spin || [0,0,0])], contacts:0, playerContacts:0, engaged:false}));
}

function spinFromImpact(body, normal, relative, impulse) {
  const tangent = [normal[1]*relative[2]-normal[2]*relative[1],
    normal[2]*relative[0]-normal[0]*relative[2], normal[0]*relative[1]-normal[1]*relative[0]];
  // A little off-centre response makes broad boxes/handles readable despite
  // their spherical collision proxy. It is deterministic, never random jitter.
  body.spin = body.spin.map((v,i) => clamp(v + tangent[i]*.22 + normal[(i+1)%3]*impulse*.18, -3, 3));
}

function surfaceImpulse(body, normal, surfaceVelocity = [0,0,0], restitution = .64) {
  const relative = minus(body.velocity, surfaceVelocity), closing = dot(relative, normal);
  if (closing >= -.002) return false;
  const impulse = -(1+restitution)*closing;
  for(let i=0;i<3;i++) body.velocity[i] += normal[i]*impulse;
  spinFromImpact(body, normal, relative, impulse);
  body.engaged = true; body.contacts++;
  return true;
}

function boxContact(body, box) {
  const p=body.position, closest=p.map((value,i)=>clamp(value,box.min[i],box.max[i]));
  const delta=minus(p,closest), distance=length(delta);
  if(distance >= body.radius) return;
  let normal, depth;
  if(distance > 1e-9){normal=delta.map(v=>v/distance);depth=body.radius-distance;}
  else {
    const candidates=[];
    for(let axis=0;axis<3;axis++) {
      candidates.push({axis,sign:-1,distance:p[axis]-box.min[axis]});
      candidates.push({axis,sign:1,distance:box.max[axis]-p[axis]});
    }
    candidates.sort((a,b)=>a.distance-b.distance);
    const nearest=candidates[0];normal=[0,0,0];normal[nearest.axis]=nearest.sign;depth=body.radius+nearest.distance;
  }
  for(let i=0;i<3;i++)p[i]+=normal[i]*(depth+1e-5);
  surfaceImpulse(body,normal);
}

function capsuleContact(body, player, center, velocity) {
  const nearest=[center[0],clamp(body.position[1],center[1]+.38,center[1]+1.48),center[2]];
  const delta=minus(body.position,nearest), distance=length(delta), radius=body.radius+(player.radius||.43);
  if(distance >= radius) return;
  const normal=distance>1e-8?delta.map(v=>v/distance):[1,0,0];
  for(let i=0;i<3;i++)body.position[i]+=normal[i]*(radius-distance+1e-5);
  if(surfaceImpulse(body,normal,velocity,.48))body.playerContacts++;
}

function pairContact(a,b) {
  const delta=minus(b.position,a.position), distance=length(delta), radius=a.radius+b.radius;
  if(distance>=radius)return;
  const normal=distance>1e-8?delta.map(v=>v/distance):[1,0,0];
  const inverseA=1/a.mass,inverseB=1/b.mass,total=inverseA+inverseB,depth=radius-distance+1e-5;
  for(let i=0;i<3;i++){a.position[i]-=normal[i]*depth*inverseA/total;b.position[i]+=normal[i]*depth*inverseB/total;}
  const relative=minus(b.velocity,a.velocity), closing=dot(relative,normal);
  if(closing>=-.002)return;
  const impulse=-1.62*closing/total;
  for(let i=0;i<3;i++){a.velocity[i]-=normal[i]*impulse*inverseA;b.velocity[i]+=normal[i]*impulse*inverseB;}
  spinFromImpact(a,normal,relative,impulse*inverseA);spinFromImpact(b,normal,relative,-impulse*inverseB);
  a.engaged=b.engaged=true;a.contacts++;b.contacts++;
}

function boundsContact(body,bounds){
  for(let i=0;i<3;i++) {
    const low=bounds.min[i]+body.radius,high=bounds.max[i]-body.radius;
    if(body.position[i]<low){body.position[i]=low;const n=[0,0,0];n[i]=1;surfaceImpulse(body,n);}
    if(body.position[i]>high){body.position[i]=high;const n=[0,0,0];n[i]=-1;surfaceImpulse(body,n);}
  }
}

export function stepFloatingProps(bodies, elapsed, {player, obstacles=[], idleMotion=true, paused=false,
  bounds={min:[-4.72,.15,-3.78],max:[4.72,2.95,3.78]}}={}) {
  if(paused)return bodies;
  const dt=clamp(finite(elapsed),0,.1);if(!dt)return bodies;
  const steps=Math.max(1,Math.ceil(dt*120)),h=dt/steps;
  const old=player?.previous||player?.position;
  const current=player?.position;
  const playerVelocity=player?minus(current,old).map(v=>clamp(v/dt,-4,4)):[0,0,0];
  for(const body of bodies)body.previous=[...body.position];
  for(let step=0;step<steps;step++) {
    const fraction=(step+1)/steps;
    const center=player?old.map((v,i)=>v+(current[i]-v)*fraction):null;
    for(const body of bodies){
      const moving=idleMotion||body.engaged;
      if(moving)for(let i=0;i<3;i++){
        body.velocity[i]=clamp(finite(body.velocity[i]),-3.6,3.6)*Math.exp(-.045*h);
        body.position[i]+=body.velocity[i]*h;
        body.spin[i]=clamp(finite(body.spin[i]),-3,3)*Math.exp(-.075*h);
        body.rotation[i]=(body.rotation[i]+body.spin[i]*h)%(Math.PI*2);
      }
      if(player)capsuleContact(body,player,center,playerVelocity);
      for(const obstacle of obstacles)boxContact(body,obstacle);
      boundsContact(body,bounds);
    }
    for(let a=0;a<bodies.length;a++)for(let b=a+1;b<bodies.length;b++)pairContact(bodies[a],bodies[b]);
    // Pair separation must not eject a neighbour through the room boundary.
    for(const body of bodies){for(const obstacle of obstacles)boxContact(body,obstacle);boundsContact(body,bounds);}
  }
  return bodies;
}

export function floatingPropSnapshot(bodies) {
  const round=n=>Math.round(n*10000)/10000;
  return bodies.map(({id,kind,position,velocity,rotation,contacts,playerContacts})=>({id,kind,
    position:position.map(round),velocity:velocity.map(round),rotation:rotation.map(round),contacts,playerContacts}));
}

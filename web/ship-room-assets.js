/** Original, low-poly room dressing for the bus-ship learning prototype.
 * Coordinates are in the ship's world frame; the group stays at the origin.
 * All geometry/materials come from the host's tracked helpers. Door openings
 * and player traversal lanes are kept clear; these props are decorative.
 */
export function createRoomAssets({roomId, box, cylinder, sphere, mesh, T, c, material, parent}) {
  const group = new T.Group();
  group.name = `Room dressing: ${roomId}`;
  parent.add(group);
  const B = (w,h,d,color,x,y,z,outlined=true) => box(w,h,d,color,[x,y,z],group,outlined);
  const C = (top,bottom,h,color,x,y,z,segments=6) => cylinder(top,bottom,h,color,[x,y,z],group,segments);
  const S = (radius,color,x,y,z) => sphere(radius,color,[x,y,z],group,7,4);
  const glass = material(0x89c9c0);
  const soft = material(0xf1e5c8);
  const amber = material(0xd5a653);
  const leaves = material(0x76a37a);
  const brown = material(0x765c4f);
  const dark = material(0x172b3b);
  const light = material(0xb9e4d9,true);
  const indicator = (x,y,z,color=c.yellow) => B(.08,.08,.025,color,x,y,z,false);
  const panel = (x,y,z,w,h) => {
    B(w,h,.08,c.navy,x,y,z);B(w-.12,h-.12,.025,c.screen,x,y,z+.055,false);
  };
  const vent = (x,y,z,width=.65) => {
    B(width,.38,.13,c.cream,x,y,z);
    B(width-.1,.27,.025,dark,x,y,z+.08,false);
    for(let i=0;i<4;i++) B(width-.14,.025,.03,c.teal,x,y-.09+i*.06,z+.1,false);
  };
  const wallShelf = (x,y,z,width) => {
    B(width,.10,.32,c.cream,x,y,z);
    for(const side of [-1,1]) B(.06,.22,.20,c.navy,x+side*(width/2-.08),y-.12,z-.04);
  };
  const plant = (x,y,z,scale=1) => {
    // A translucent carton is represented with light teal flat faces;
    // no fragile transparency ordering is needed in the gameplay camera.
    B(.28*scale,.28*scale,.28*scale,glass,x,y+.14*scale,z);
    B(.21*scale,.04*scale,.21*scale,brown,x,y+.3*scale,z,false);
    for(const [dx,dz,h] of [[-.07,0,.26],[.07,.03,.34],[0,-.07,.2]]) {
      const leaf=mesh(new T.ConeGeometry(.095*scale,h*scale,4),leaves,
        [x+dx*scale,y+.29*scale+h*scale/2,z+dz*scale],group);
      leaf.rotation.z=dx*1.4;
    }
  };
  if(roomId==='cockpit') {
    // Full-width navigator console within the cockpit furniture footprint.
    B(2.35,.62,1.0,c.navy,7.3,.4,-2.35);
    B(2.42,.14,1.06,soft,7.3,.78,-2.35);
    for(const x of [6.55,7.3,8.05]) {
      B(.64,.43,.08,dark,x,1.10,-2.68);
      B(.52,.31,.025,c.screen,x,1.10,-2.62,false);
      for(let i=0;i<3;i++) B(.1,.025,.08,[c.teal,c.yellow,c.coral][i],x-.2+i*.2,.87,-2.13,false);
    }
    B(.22,.27,.22,c.navy,7.3,.96,-2.0);S(.10,c.coral,7.3,1.13,-2.0);
    // Paired, anchored flight seats; deliberately outside the doorway lane.
    for(const x of [6.75,7.85]) {
      C(.10,.13,.38,c.navy,x,.24,-1.86);
      B(.64,.16,.52,c.coral,x,.46,-1.86);
      B(.64,.65,.12,c.coral,x,.79,-2.13);
      B(.25,.08,.06,soft,x,1.1,-2.04,false);
    }
    // Shared power conduit, wall readouts and front observation glazing.
    B(2.9,.09,.09,amber,7.0,2.25,-2.92);
    vent(5.65,1.75,-2.92,.62);
    panel(7.45,1.8,-2.91,1.65,.47);
    for(let i=0;i<5;i++) B(.18,.025,.025,light,6.9+i*.25,1.77+(i%2)*.12,-2.84,false);
    B(.06,.90,3.2,dark,8.69,1.9,.15);
    B(.025,.72,3.0,glass,8.65,1.9,.15,false);
    B(.04,.75,.045,c.cream,8.62,1.9,.15,false);
  } else if(roomId==='sleep') {
    // Two restrained bunks, with straps, wall lamps and a personal locker.
    for(const y of [.36,1.24]) {
      B(1.65,.16,.9,c.navy,3.9,y,-2.35);
      B(1.5,.12,.78,soft,3.9,y+.13,-2.35);
      B(.44,.09,.65,c.coral,4.42,y+.23,-2.35);
      B(.06,.04,.8,c.teal,3.48,y+.22,-2.35,false);
    }
    for(const x of [3.12,4.68]) B(.10,1.78,.1,amber,x,.9,-1.87);
    B(.40,1.5,.44,c.cream,3.25,.82,-2.68);
    B(.30,.58,.025,c.teal,3.25,1.08,-2.44,false);indicator(3.34,1.08,-2.41);
    for(const x of [3.45,4.45]) B(.23,.09,.06,light,x,2.1,-2.89,false);
    // Ladder rungs, folded bedding, wall radio and a small framed sky chart.
    for(let i=0;i<5;i++) B(.42,.055,.08,c.cream,4.4,.35+i*.27,-1.86);
    B(.43,.10,.34,c.teal,3.62,1.55,-2.42);
    B(.43,.08,.34,soft,3.62,1.64,-2.42);
    vent(2.5,2.10,-2.92,.56);
    panel(2.48,1.50,-2.92,.48,.55);
    S(.045,light,2.39,1.60,-2.85);S(.025,light,2.57,1.39,-2.85);
  } else if(roomId==='kitchen') {
    // Counter, inset sink, water dispenser, secured cups and closed food stores.
    B(2.28,.74,.83,c.cream,.45,.43,-2.45);
    B(2.32,.10,.86,soft,.45,.85,-2.45);
    B(.58,.035,.44,c.teal,.03,.92,-2.45,false);
    B(.08,.23,.08,c.navy,.03,1.07,-2.76);
    B(.12,.07,.18,c.navy,.03,1.20,-2.69);
    for(const x of [-.36,.35,1.05]) {
      B(.58,.30,.025,c.navy,x,.55,-2.015,false);
      B(.22,.04,.02,amber,x,.62,-1.99,false);
    }
    B(.5,.58,.38,c.teal,1.14,1.19,-2.55);
    B(.34,.21,.025,c.screen,1.14,1.3,-2.34,false);
    for(const x of [.5,.72]) C(.08,.07,.18,soft,x,1.02,-2.30);
    B(.38,.46,.30,c.coral,-.33,1.17,-2.57);
    B(.24,.03,.025,soft,-.33,1.25,-2.405,false);
    // Vented food chiller below the counter, lidded meal containers above it.
    B(.60,.58,.025,c.teal,1.13,.48,-2.005,false);
    B(.035,.19,.035,soft,1.34,.57,-1.98,false);
    for(let i=0;i<3;i++) B(.42,.023,.025,dark,1.12,.26+i*.05,-1.98,false);
    wallShelf(.35,1.77,-2.75,1.9);
    for(const x of [-.25,.20,.65]) {
      B(.33,.18,.22,[c.coral,c.teal,amber][Math.round((x+.25)/.45)],x,1.91,-2.75);
      B(.35,.035,.24,soft,x,2.02,-2.75);
    }
    vent(1.5,2.10,-2.92,.6);
  } else if(roomId==='living') {
    // Lounge uses the existing tablet and Alien X; avoid duplicates.
    B(1.12,.45,.68,c.coral,-4.1,.35,2.42);
    B(1.12,.50,.12,c.coral,-4.1,.77,2.70);
    B(.35,.20,.25,amber,-4.42,.68,2.52);
    B(.9,.13,.65,c.cream,-2.4,.62,1.55);
    C(.16,.24,.49,c.navy,-2.4,.32,1.55);
    panel(-3.25,1.78,-2.91,1.58,.72);
    B(.55,.06,.02,light,-3.45,1.88,-2.85,false);
    B(.88,.04,.02,c.teal,-3.25,1.69,-2.85,false);
    wallShelf(-2.0,2.13,-2.79,.95);
    for(const [x,color] of [[-2.3,c.coral],[-2.1,c.teal],[-1.9,amber],[-1.7,c.navy]])
      B(.13,.25,.16,color,x,2.30,-2.79);
    wallShelf(-4.30,1.91,-2.79,.6);plant(-4.38,1.96,-2.79,.75);
    vent(-3.2,2.40,-2.92,1.0);
    // Open first-aid case: simple original cross, two instrument handles.
    wallShelf(-2.0,1.20,-2.79,.95);
    B(.65,.24,.28,c.coral,-2,1.37,-2.77);
    B(.65,.35,.07,c.coral,-2,1.60,-2.91);
    B(.20,.055,.025,soft,-2,1.63,-2.86,false);
    B(.055,.20,.025,soft,-2,1.63,-2.86,false);
    for(const x of [-2.18,-1.82]) C(.045,.045,.18,soft,x,1.56,-2.72);
  } else if(roomId==='fuel') {
    // Equipment sits within the protected rear-wall footprint; no volatile
    // tanks or props block the doorway from the living quarter.
    for(const x of [-8.18,-7.48]) {
      C(.29,.32,1.14,c.teal,x,.70,-2.43,7);
      C(.20,.23,.09,amber,x,1.30,-2.43,7);
      B(.62,.08,.06,amber,x,.76,-2.09,false);
    }
    B(1.8,.10,.10,amber,-7.35,1.66,-2.84);
    for(const x of [-7.95,-6.75]) B(.10,.38,.10,amber,x,1.48,-2.84);
    vent(-6.45,2.1,-2.92,.86);
    panel(-7.7,2.05,-2.92,.78,.42);
    for(let i=0;i<3;i++) B(.12,.17,.025,[c.teal,c.yellow,c.coral][i],-7.95+i*.24,2.06,-2.85,false);
    for(const x of [-8.18,-7.48]) {
      const dial=C(.10,.10,.05,soft,x,1.05,-2.08,8);dial.rotation.x=Math.PI/2;
      B(.025,.10,.035,c.navy,x,1.07,-2.04,false);
    }
  } else if(roomId==='airlock') {
    // Suit lockers and pressure controls occupy the existing west wall footprint.
    B(.38,1.64,2.15,c.navy,-8.43,.87,1.45);
    for(const z of [.85,1.9]) {
      B(.08,1.38,.78,c.cream,-8.17,.9,z);
      S(.19,soft,-8.06,1.38,z);
      B(.045,.16,.24,c.screen,-7.88,1.39,z,false);
      B(.28,.58,.30,soft,-8.04,.88,z);
      B(.04,.12,.15,c.teal,-7.88,.98,z,false);
      for(const dz of [-.12,.12]) B(.12,.25,.10,c.cream,-8.04,.49,z+dz);
    }
    B(.12,.53,.56,c.cream,-8.00,1.75,2.48);
    B(.025,.32,.38,c.screen,-7.92,1.8,2.48,false);
    for(const z of [2.35,2.48,2.61]) B(.025,.05,.06,c.yellow,-7.90,1.62,z,false);
    // The single exterior hatch and nearby pressure indicator belong to this room.
    B(1.45,1.85,.12,c.navy,-7.9,1.0,3.01);
    B(1.15,1.55,.04,c.teal,-7.9,1.0,2.93,false);
    B(.10,1.55,.03,c.cream,-7.9,1.0,2.90,false);
    B(.34,.09,.04,amber,-7.9,1.45,2.88,false);
    for(const x of [-8.55,-7.25]) B(.10,.08,.04,c.yellow,x,1.94,2.93,false);
  }
  return group;
}

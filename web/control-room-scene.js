import * as T from './assets/three-0.187.0/three.module.js';
import {createGagooModel} from './gagoo-scene.js';
import {createRagdollController} from './gagoo-ragdoll.js';
import {createFloatingPropState,stepFloatingProps,floatingPropSnapshot} from './room-prop-physics.js';

/** Original low-poly room and Alien X. No image/texture downloads are required. */
export function createControlRoom({canvas, reduced, onNear, onArrive, onPickup, onError}) {
  const renderer = new T.WebGLRenderer({canvas, antialias:true, alpha:true, powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.65));
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.NoToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFShadowMap;
  const scene = new T.Scene();
  const camera = new T.OrthographicCamera(-8,8,6,-6,.1,80);
  camera.position.set(8.3,12.4,15.5); camera.lookAt(0,.45,-.15);
  const geometries = new Set(), materials = new Set();
  const gradient = new T.DataTexture(new Uint8Array([35,110,230]),3,1,T.RedFormat);
  gradient.minFilter = gradient.magFilter = T.NearestFilter; gradient.needsUpdate = true;
  const ink = new T.MeshBasicMaterial({color:0x101727,side:T.BackSide}); materials.add(ink);
  ink.onBeforeCompile = shader => {
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\ntransformed += normal * 0.04;');
  };
  ink.customProgramCacheKey = () => 'room-outline-040';
  const pencil = new T.LineBasicMaterial({color:0x1c2c3b,transparent:true,opacity:.58});materials.add(pencil);
  const palette = {};
  const material = (color, basic=false) => {
    const key = `${color}-${basic}`;
    if (!palette[key]) { palette[key] = basic ? new T.MeshBasicMaterial({color}) : new T.MeshToonMaterial({color,gradientMap:gradient}); materials.add(palette[key]); }
    return palette[key];
  };
  const c = {floor:material(0xb1c5bf), cream:material(0xe4e3cd), navy:material(0x31445f), blue:material(0x354c96), teal:material(0x72b7b2), coral:material(0xdc795f), yellow:material(0xe5be69), lime:material(0xbde54a), dark:material(0x101727), screen:material(0x143b4a,true), glow:material(0xa3e2d3,true), green:material(0x88d94d), pink:material(0xe2a0c3), purple:material(0x5960c6)};
  const room = new T.Group(); room.name='Original orbital classroom'; scene.add(room);
  scene.add(new T.HemisphereLight(0xf5f1da,0x3b536e,.95));
  const key = new T.DirectionalLight(0xffefd4,2.25); key.position.set(-5,10,8);scene.add(key);
  key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-7;key.shadow.camera.right=7;key.shadow.camera.top=6;key.shadow.camera.bottom=-6;key.shadow.camera.near=.5;key.shadow.camera.far=28;key.shadow.bias=-.0005;key.shadow.normalBias=.035;
  const fill = new T.DirectionalLight(0x98d8df,.25);fill.position.set(5,3,-6);scene.add(fill);

  function outline(mesh) {
    if (mesh.material.transparent || mesh.userData.noOutline) return;
    const shell = new T.Mesh(mesh.geometry,ink);shell.name='ink outline';shell.userData.noOutline=true;shell.castShadow=false;shell.receiveShadow=false;mesh.add(shell);
  }
  function mesh(geometry,surface,position=[0,0,0],parent=room,outlined=true) {
    geometries.add(geometry);const object = new T.Mesh(geometry,surface);object.position.set(...position);object.receiveShadow=!surface.isMeshBasicMaterial;object.castShadow=outlined&&!surface.transparent&&!surface.isMeshBasicMaterial;parent.add(object);if(outlined)outline(object);return object;
  }
  const box = (w,h,d,surface,position,parent=room,outlined=true) => {
    const result=mesh(new T.BoxGeometry(w,h,d),surface,position,parent,outlined);
    if(outlined&&Math.max(w,h,d)>1.1){const edges=new T.EdgesGeometry(result.geometry,35);geometries.add(edges);const lines=new T.LineSegments(edges,pencil);result.add(lines);}
    return result;
  };
  const cylinder = (rTop,rBottom,height,surface,position,parent=room,segments=8) => mesh(new T.CylinderGeometry(rTop,rBottom,height,segments),surface,position,parent);
  const sphere = (r,surface,position,parent=room,w=10,h=6) => mesh(new T.SphereGeometry(r,w,h),surface,position,parent);
  const rod = (a,b,r,surface,parent=room) => {
    const start=new T.Vector3(...a),end=new T.Vector3(...b),direction=end.clone().sub(start);
    const m=cylinder(r,r,direction.length(),surface,start.clone().add(end).multiplyScalar(.5).toArray(),parent,6);
    m.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),direction.normalize());return m;
  };

  // Open-front dollhouse construction keeps every interaction visible.
  box(10.6,.30,8.6,c.navy,[0,-.19,0]);
  box(10.0,.13,8.0,c.floor,[0,-.01,0]);
  const gridPositions=[];
  for(let x=-5;x<=5;x+=1)gridPositions.push(x,.063,-4,x,.063,4);
  for(let z=-4;z<=4;z+=1)gridPositions.push(-5,.063,z,5,.063,z);
  const gridGeo = new T.BufferGeometry();gridGeo.setAttribute('position',new T.Float32BufferAttribute(gridPositions,3));geometries.add(gridGeo);
  const gridMat = new T.LineBasicMaterial({color:0x71918f,transparent:true,opacity:.42});materials.add(gridMat);room.add(new T.LineSegments(gridGeo,gridMat));
  box(9.6,.025,.12,c.cream,[0,.08,2.9],room,false);
  for(const x of [-4.8,4.8])box(.12,.025,7.5,c.cream,[x,.08,0],room,false);
  box(10.35,1.2,.22,c.navy,[0,.6,-4.05]);
  box(.22,2.6,8.1,c.blue,[-5.04,1.3,-.05]);
  box(.25,.45,8.1,c.navy,[5.04,.22,-.05]);
  box(10.35,.22,.4,c.cream,[0,3.12,-4.05]);
  box(2.2,1.8,.25,c.blue,[-4,2.14,-4.05]);
  box(2.2,1.8,.25,c.blue,[4,2.14,-4.05]);
  const windowPanel=box(5.7,1.85,.18,c.screen,[0,2.13,-4.14]);windowPanel.name='observation window';
  const planet=sphere(.76,material(0x7fa9b8),[.45,2.07,-4.0],room,16,10);planet.scale.z=.08;
  const planetCloud = new T.TorusGeometry(.58,.035,4,20,Math.PI*1.35);const cloud=mesh(planetCloud,c.glow,[.45,2.1,-3.93],room,false);cloud.scale.y=.45;cloud.rotation.z=.2;
  for(const [x,y] of [[-2.35,2.7],[-1.7,1.6],[1.9,2.75],[2.35,1.6],[-.9,2.82],[1.8,1.5]])sphere(.028,c.glow,[x,y,-3.99],room,4,3);
  box(.10,1.8,.12,c.cream,[-2.83,2.1,-3.96]);box(.10,1.8,.12,c.cream,[2.83,2.1,-3.96]);
  box(5.8,.11,.15,c.cream,[0,1.24,-3.92]);box(.10,1.85,.12,c.navy,[0,2.1,-3.88]);

  // Console banks: large colored surfaces, stepped shading, thick silhouettes.
  for(const [i,x] of [-3.35,0,3.35].entries()) {
    const station=new T.Group();station.position.set(x,0,-2.8);room.add(station);
    box(2.6,.84,1.05,c.navy,[0,.49,0],station);
    const desktop=box(2.78,.18,1.2,i===1?c.teal:c.cream,[0,.96,.08],station);desktop.rotation.x=.06;
    const screen=new T.Group();screen.position.set(0,1.51,-.27);screen.rotation.x=-.25;station.add(screen);
    box(1.88,1.02,.15,c.dark,[0,0,0],screen);
    box(1.65,.78,.025,c.screen,[0,0,.09],screen,false);
    if(i===1) {
      const orbit=mesh(new T.TorusGeometry(.27,.016,4,28),c.glow,[0,0,.115],screen,false);orbit.scale.x=1.7;orbit.rotation.z=.45;
      sphere(.06,c.yellow,[0,0,.14],screen,8,4);
      for(let k=0;k<3;k++)box(.08,.16+k*.07,.01,c.teal,[.57+k*.11,-.2,.12],screen,false);
    } else {
      for(let k=0;k<4;k++){box(.6+k*.12,.035,.01,c.glow,[-.23,-.23+k*.14,.113],screen,false);box(.15,.06,.01,k===2?c.yellow:c.teal,[.59,-.23+k*.14,.113],screen,false);}
    }
    for(let k=0;k<5;k++)box(.19,.025,.12,k===0?c.coral:k===1?c.yellow:c.teal,[-.75+k*.35,1.083,.35],station,false);
    box(1.15,.02,.22,c.dark,[-.1,1.07,.12],station,false);
  }
  // A cozier reading nook and a tablet dock in the foreground.
  const desk = new T.Group();desk.position.set(-3,0,.2);room.add(desk);
  for(const x of [-.82,.82])for(const z of [-.43,.43])box(.13,.85,.13,c.navy,[x,.45,z],desk);
  box(2.05,.18,1.24,c.cream,[0,.95,0],desk);
  box(.66,.10,.78,c.navy,[0,1.1,-.07],desk);
  for(let i=0;i<3;i++)box(.32,.08,.4,[c.coral,c.yellow,c.teal][i],[.68,1.09+i*.08,-.1],desk);
  cylinder(.13,.11,.25,c.teal,[-.7,1.17,-.16],desk);
  const tablet=new T.Group();tablet.name='interactive tablet';room.add(tablet);
  box(.60,.045,.82,c.dark,[0,0,0],tablet);
  box(.50,.009,.67,c.screen,[0,.027,-.01],tablet,false);
  box(.15,.009,.025,c.cream,[0,.029,.357],tablet,false);
  const tabletOrigin=new T.Vector3(-3,1.19,.12);tablet.position.copy(tabletOrigin);tablet.rotation.z=-.12;
  const tabletMarker=mesh(new T.TorusGeometry(.47,.035,4,20),c.lime,[-3,.11,.2],room,false);tabletMarker.rotation.x=-Math.PI/2;

  const chair=new T.Group();chair.position.set(3.9,0,-.6);chair.rotation.y=-.45;room.add(chair);
  box(.92,.2,.8,c.coral,[0,.65,0],chair);box(.95,.95,.16,c.coral,[0,1.05,-.38],chair);
  cylinder(.08,.10,.65,c.navy,[0,.32,0],chair);
  for(const angle of [0,Math.PI/2]){const leg=box(1,.08,.12,c.navy,[0,.09,0],chair);leg.rotation.y=angle;}
  const plant=new T.Group();plant.position.set(-4.3,0,-2.2);room.add(plant);
  cylinder(.3,.23,.5,c.coral,[0,.27,0],plant);
  for(const [angle,h] of [[-.8,.9],[.2,1.13],[1.3,.86],[2.6,.96]]){const leaf=mesh(new T.ConeGeometry(.22,h,5),material(0x79ac78),[Math.sin(angle)*.19,.7,Math.cos(angle)*.19],plant);leaf.rotation.z=Math.sin(angle)*.4;}
  box(.17,1.5,1.2,c.cream,[-4.86,1.75,1.0]);
  for(let i=0;i<4;i++)box(.03,.12,.52,i===2?c.yellow:c.teal,[-4.75,1.32+i*.29,1],room,false);

  // Sparse deliberate pencil strokes, rather than noisy full-screen outlines.
  const strokes=[];
  for(let i=0;i<12;i++){
    const z=-3.1+i*.47;strokes.push(-4.895,.38,z,-4.895,.77,z+.16);
    const x=-4.4+i*.72;strokes.push(x,.085,3.42,x+.18,.085,3.60);
  }
  const strokeGeometry=new T.BufferGeometry();strokeGeometry.setAttribute('position',new T.Float32BufferAttribute(strokes,3));geometries.add(strokeGeometry);room.add(new T.LineSegments(strokeGeometry,pencil));

  // Floating objects have physical poses; they do not reset to a sine-wave path
  // after a bump. These conservative proxies trade precision for mobile speed.
  const floatingBodies=createFloatingPropState(), floatingVisuals=[];
  for(const [index,body] of floatingBodies.entries()){
    const prop=new T.Group();prop.name=body.id;scene.add(prop);
    const accent=index===2?c.teal:index===4?c.teal:c.coral;
    if(body.kind==='mug'){
      cylinder(.16,.13,.26,c.teal,[0,0,0],prop,8);
      const rim=mesh(new T.TorusGeometry(.143,.022,4,8),c.cream,[0,.137,0],prop);rim.rotation.x=Math.PI/2;
      const inside=mesh(new T.CircleGeometry(.12,8),c.dark,[0,.137,0],prop,false);inside.rotation.x=-Math.PI/2;
      mesh(new T.TorusGeometry(.095,.031,4,8),c.teal,[.186,.01,0],prop);
      box(.10,.07,.009,c.cream,[0,.015,.146],prop,false);
    }else if(body.kind==='book'){
      box(.40,.10,.50,c.cream,[0,0,0],prop);
      for(const side of [-1,1])box(.44,.035,.54,accent,[0,side*.067,0],prop);
      box(.045,.16,.54,accent,[-.21,0,0],prop);
      box(.20,.009,.035,c.cream,[.035,.09,-.1],prop,false);
      box(.13,.009,.026,c.cream,[.035,.09,-.035],prop,false);
      for(let i=0;i<2;i++)box(.006,.008,.40,c.navy,[.202,-.025+i*.05,.02],prop,false);
    }else if(body.kind==='pen'){
      cylinder(.033,.033,.34,accent,[0,0,0],prop,6);
      cylinder(.042,.042,.065,c.cream,[0,.20,0],prop,6);
      cylinder(.031,0,.075,c.yellow,[0,-.208,0],prop,6);
      box(.016,.13,.018,c.dark,[.035,.135,0],prop,false);
    }else{
      box(.43,.06,.47,c.navy,[0,0,0],prop);
      box(.38,.018,.42,c.cream,[0,.04,.015],prop);
      for(let line=0;line<4;line++)box(.23,.008,.012,line===0?c.coral:c.teal,[.015,.055,-.1+line*.065],prop,false);
      for(const x of [-.13,0,.13]){const ring=mesh(new T.TorusGeometry(.045,.011,3,6),c.dark,[x,.02,-.20],prop);ring.rotation.y=Math.PI/2;}
    }
    floatingVisuals.push(prop);
  }

  function makeAlien() {
    const alien=new T.Group();alien.name='Alien X — original classroom companion';
    const body=sphere(.34,c.green,[0,.55,0],alien,8,5);body.scale.set(.9,1.1,.76);
    const head=sphere(.65,c.green,[0,1.25,0],alien,10,6);head.scale.set(1.16,.86,.79);
    for(const side of [-1,1]) {
      const leg=cylinder(.12,.14,.31,c.green,[side*.19,.19,.025],alien,6);leg.rotation.z=side*-.05;
      const arm=sphere(.16,c.green,[side*.37,.55,.01],alien,6,4);arm.scale.set(.7,1.35,.7);arm.rotation.z=side*.65;
      rod([side*.42,1.70,-.015],[side*.57,1.98,-.03],.063,c.green,alien);
      sphere(.14,c.green,[side*.59,2.02,-.025],alien,6,4);
      sphere(.069,side<0?c.pink:c.purple,[side*.59,2.045,.079],alien,6,4);
      const shape=new T.Shape();shape.moveTo(-.16,-.25);shape.bezierCurveTo(-.33,-.08,-.21,.30,.08,.27);shape.bezierCurveTo(.23,.15,.17,-.12,-.16,-.25);
      const eye=mesh(new T.ShapeGeometry(shape,4),c.dark,[side*.29,1.26,.48],alien,false);eye.rotation.z=side*-.3;eye.rotation.y=side*.16;if(side<0)eye.scale.x=-1;
      sphere(.066,material(0xf3f6e8,true),[side*.31-.05,1.36,.505],alien,8,4);
      sphere(.023,material(0xf3f6e8,true),[side*.31-.08,1.23,.515],alien,6,3);
    }
    box(.095,.026,.023,c.dark,[0,.97,.47],alien,false);
    return alien;
  }
  const alien=makeAlien();alien.position.set(2.65,.08,.05);alien.rotation.y=.36;room.add(alien);
  const alienMarker=mesh(new T.TorusGeometry(.52,.028,4,20),c.lime,[2.65,.10,.05],room,false);alienMarker.rotation.x=-Math.PI/2;
  const actor=new T.Group();scene.add(actor);
  const model=createGagooModel(T);model.scale.multiplyScalar(.57);model.position.y=.92;actor.add(model);
  const toonCache = new Map();
  const characterMeshes=[];model.traverse(node=>{if(node.isMesh)characterMeshes.push(node);});
  for(const node of characterMeshes) {
    if(node.material.transparent)continue;
    const original=node.material;
    if(!toonCache.has(original)){const next=new T.MeshToonMaterial({color:original.color,gradientMap:gradient});toonCache.set(original,next);materials.add(next);}
    node.material=toonCache.get(original);node.castShadow=true;node.receiveShadow=true;
    if(!/eye|pupil|highlight|display|status/i.test(node.name))outline(node);
  }
  const ragdoll=createRagdollController(model);
  const contactShadow=new T.MeshBasicMaterial({color:0x101727,transparent:true,opacity:.18,depthWrite:false});materials.add(contactShadow);
  const actorShadow=mesh(new T.CircleGeometry(.42,20),contactShadow,[0,.077,0],scene,false);actorShadow.rotation.x=-Math.PI/2;actorShadow.scale.y=.68;
  actor.position.set(0,0,2.1);actor.rotation.y=.4;
  const solid=[{x0:-4.77,x1:4.77,z0:-3.8,z1:-2.03},{x0:-4.15,x1:-1.85,z0:-.58,z1:.98},{x0:3.35,x1:4.6,z0:-1.3,z1:.08},{x0:2.05,x1:3.25,z0:-.45,z1:.55}];
  const propObstacles=solid.map((o,i)=>({min:[o.x0,.08,o.z0],max:[o.x1,[1.2,1.16,1.56,2.2][i],o.z1]}));
  for(const x of [-3.35,0,3.35])propObstacles.push({min:[x-.98,1.05,-3.22],max:[x+.98,2.15,-2.75]});
  const radius=.25;
  const free=(x,z)=>x>=-4.58&&x<=4.58&&z>=-3.6&&z<=3.56&&!solid.some(o=>x>o.x0-radius&&x<o.x1+radius&&z>o.z0-radius&&z<o.z1+radius);
  let autoTarget=null, path=[], near='', pickup=0, pickupMode='', held=false, lastPickupState=false, time=0, lastDirection=new T.Vector2(), disposed=false, motionPaused=false, lost=false;
  const interactionPositions={tablet:new T.Vector3(-3,0,1.54),alien:new T.Vector3(2.65,0,1.25)};

  // Small deterministic grid search lets keyboard shortcuts navigate around desks.
  function pathTo(target) {
    const step=.35,minimum=-4.55,minimumZ=-3.5,nx=27,nz=21;
    const cell=(x,z)=>[Math.max(0,Math.min(nx-1,Math.round((x-minimum)/step))),Math.max(0,Math.min(nz-1,Math.round((z-minimumZ)/step)))];
    const point=([x,z])=>new T.Vector3(minimum+x*step,0,minimumZ+z*step);
    const start=cell(actor.position.x,actor.position.z),end=cell(target.x,target.z),id=([x,z])=>z*nx+x;
    const queue=[start],seen=new Map([[id(start),null]]);let found=null;
    for(let cursor=0;cursor<queue.length;cursor++){
      const node=queue[cursor];if(id(node)===id(end)){found=node;break;}
      for(const [dx,dz] of [[0,-1],[-1,0],[1,0],[0,1]]){const next=[node[0]+dx,node[1]+dz];if(next[0]<0||next[0]>=nx||next[1]<0||next[1]>=nz||seen.has(id(next)))continue;const p=point(next);if(!free(p.x,p.z))continue;seen.set(id(next),node);queue.push(next);}
    }
    if(!found)return [];
    const route=[];let node=found;while(node&&id(node)!==id(start)){route.unshift(point(node));node=seen.get(id(node));}route.push(target.clone());return route;
  }
  function goTo(which) { if(!interactionPositions[which])return;autoTarget=which;path=pathTo(interactionPositions[which]);if(!path.length){autoTarget=null;return false;}return true; }
  function cancelGoal(){autoTarget=null;path=[];}
  function updateNear(){const next=actor.position.distanceTo(interactionPositions.tablet)<.9?'tablet':actor.position.distanceTo(interactionPositions.alien)<.9?'alien':'';if(next!==near){near=next;onNear?.(near);}canvas.dataset.near=near||'none';}
  function beginPickup(){cancelGoal();pickupMode='take';pickup=0;held=false;actor.rotation.y=Math.PI;return true;}
  function putDown(){pickupMode='return';pickup=0;held=false;lastPickupState=false;}
  const handPoint=new T.Vector3(), startPoint=new T.Vector3();
  const pose={};
  function update(dt,input={x:0,y:0},active=true){
    if(disposed||lost)return;
    const previousActor=actor.position.toArray();
    dt=Math.min(.04,Math.max(0,dt));if(!motionPaused&&!reduced.matches)time+=dt;
    let dx=0,dz=0,moving=false;
    if(active&&!pickupMode){
      if(input.x||input.y){cancelGoal();const v=new T.Vector2(input.x,input.y);if(v.length()>1)v.normalize();
        // Controls follow screen directions, with the fixed oblique camera.
        dx=v.x*.882+v.y*.472;dz=-v.x*.472+v.y*.882;
      }else if(path.length){const delta=path[0].clone().sub(actor.position);if(delta.length()<.09){path.shift();if(!path.length){const arrived=autoTarget;autoTarget=null;onArrive?.(arrived);}}else{delta.normalize();dx=delta.x;dz=delta.z;}}
      const speed=2.4,oldX=actor.position.x,oldZ=actor.position.z;
      if(free(oldX+dx*speed*dt,oldZ))actor.position.x+=dx*speed*dt;
      if(free(actor.position.x,oldZ+dz*speed*dt))actor.position.z+=dz*speed*dt;
      moving=Math.hypot(actor.position.x-oldX,actor.position.z-oldZ)>.0001;
      if(moving){const wanted=Math.atan2(dx,dz),difference=Math.atan2(Math.sin(wanted-actor.rotation.y),Math.cos(wanted-actor.rotation.y));actor.rotation.y+=difference*Math.min(1,dt*14);}
    }
    updateNear();
    const stride=moving?Math.sin(time*11)*(reduced.matches ? .12 : .38):0;
    pose.leftLeg=[stride,0,0];pose.rightLeg=[-stride,0,0];pose.leftShin=[Math.max(0,-stride)*.5,0,0];pose.rightShin=[Math.max(0,stride)*.5,0,0];
    pose.leftArm=[-stride*.65,0,-.05];pose.rightArm=[stride*.65,0,.05];pose.rightForearm=[0,0,0];
    if(pickupMode||held){pose.rightArm=[-1.35,0,-.12];pose.rightForearm=[-.35,0,0];}
    ragdoll.step(dt,{pose,acceleration:{x:(dx-lastDirection.x)*.12,y:0,z:(dz-lastDirection.y)*.12},strength:reduced.matches?0:.45});lastDirection.set(dx,dz);
    actor.position.y=moving&&!reduced.matches?Math.abs(Math.sin(time*11))*.025:0;
    alien.position.y=.08+(!reduced.matches&&!motionPaused?Math.sin(time*1.9)*.025:0);
    model.updateMatrixWorld(true);
    const hand=model.userData.rightHand||model.userData.rig?.joints.rightHand;
    if(hand)hand.getWorldPosition(handPoint);else handPoint.copy(actor.position).add(new T.Vector3(-.38,.77,-.15));
    handPoint.y+=.03;
    if(pickupMode){
      pickup=Math.min(1,pickup+dt/(reduced.matches ? .12 : .85));const eased=pickup*pickup*(3-2*pickup);
      if(pickupMode==='take'){tablet.position.lerpVectors(tabletOrigin,handPoint,eased);tablet.position.y+=Math.sin(pickup*Math.PI)*.24;tablet.rotation.set(eased*.6,actor.rotation.y*eased,-.12*(1-eased));}
      else{if(!lastPickupState)startPoint.copy(tablet.position);tablet.position.lerpVectors(startPoint,tabletOrigin,eased);tablet.position.y+=Math.sin(pickup*Math.PI)*.15;tablet.rotation.set((1-eased)*.6,actor.rotation.y*(1-eased),-.12*eased);}
      lastPickupState=true;
      if(pickup>=1){const took=pickupMode==='take';pickupMode='';held=took;lastPickupState=false;if(took)onPickup?.();}
    }else if(held){tablet.position.copy(handPoint);tablet.rotation.set(.6,actor.rotation.y,0);}
    actorShadow.position.x=actor.position.x;actorShadow.position.z=actor.position.z;
    stepFloatingProps(floatingBodies,dt,{player:{position:actor.position.toArray(),previous:previousActor,radius:.43},obstacles:propObstacles,idleMotion:!motionPaused&&!reduced.matches,paused:!active});
    floatingBodies.forEach((body,i)=>{floatingVisuals[i].position.set(...body.position);floatingVisuals[i].rotation.set(...body.rotation);});
    canvas.dataset.floatingProps=JSON.stringify(floatingPropSnapshot(floatingBodies));
    canvas.dataset.propCollisions=String(floatingBodies.reduce((sum,body)=>sum+body.contacts,0));
    canvas.dataset.propPlayerCollisions=String(floatingBodies.reduce((sum,body)=>sum+body.playerContacts,0));
    canvas.dataset.shadowMap='enabled';
    tabletMarker.material=near==='tablet'?c.lime:c.teal;alienMarker.material=near==='alien'?c.lime:c.teal;
    canvas.dataset.playerX=actor.position.x.toFixed(3);canvas.dataset.playerZ=actor.position.z.toFixed(3);
    canvas.dataset.heldTablet=String(held||pickupMode==='take');
  }
  let width=0,height=0;
  function resize(){const w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h||(w===width&&h===height))return;width=w;height=h;renderer.setSize(w,h,false);const aspect=w/h;const vertical=Math.max(9.2,13.1/aspect);camera.left=-vertical*aspect/2;camera.right=vertical*aspect/2;camera.top=vertical/2;camera.bottom=-vertical/2;camera.zoom=1;camera.updateProjectionMatrix();}
  function render(){if(disposed||lost)return;resize();renderer.render(scene,camera);}
  const contextLost=e=>{e.preventDefault();lost=true;onError?.();};canvas.addEventListener('webglcontextlost',contextLost);
  const raycaster=new T.Raycaster(),pointer=new T.Vector2();
  function pick(clientX,clientY){const rect=canvas.getBoundingClientRect();pointer.set((clientX-rect.left)/rect.width*2-1,-(clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects([tablet,alien],true).find(item=>item.object.name!=='ink outline');if(!hit)return '';let n=hit.object;while(n){if(n===tablet)return 'tablet';if(n===alien)return 'alien';n=n.parent;}return '';}
  update(0);render();
  return {update,render,resize,goTo,cancelGoal,beginPickup,putDown,pick,getNear:()=>near,setPaused(value){motionPaused=value;},dispose(){disposed=true;canvas.removeEventListener('webglcontextlost',contextLost);ragdoll.dispose?.();model.userData.dispose?.();for(const g of geometries)g.dispose();for(const m of materials)m.dispose();gradient.dispose();key.shadow.map?.dispose();renderer.dispose();}};
}

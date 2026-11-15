import * as T from './assets/three-0.187.0/three.module.js';
import {createGagooModel} from './gagoo-scene.js';
import {createRagdollController} from './gagoo-ragdoll.js';
import {createFloatingPropState,stepFloatingProps,floatingPropSnapshot} from './room-prop-physics.js';
import {SHIP_HULL,SHIP_WALLS,SHIP_FURNITURE,SHIP_ROOMS,SHIP_DOORS,shipFree,shipRoom,shipPath} from './ship-layout.js';

/** A cutaway bus-shaped spaceship with connected rooms. */
export function createControlRoom({canvas, reduced, onNear, onArrive, onPickup, onError, onRoomState}) {
  const renderer = new T.WebGLRenderer({canvas, antialias:true, alpha:true, powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.65));
  renderer.outputColorSpace = T.SRGBColorSpace;
  renderer.toneMapping = T.NoToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFShadowMap;
  const scene = new T.Scene();
  const camera = new T.OrthographicCamera(-8,8,6,-6,.1,80);
  camera.position.set(10,17,25); camera.lookAt(0,.45,0);
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
  key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-12;key.shadow.camera.right=12;key.shadow.camera.top=10;key.shadow.camera.bottom=-10;key.shadow.camera.near=.5;key.shadow.camera.far=28;key.shadow.bias=-.0005;key.shadow.normalBias=.035;
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

  // One symmetric hull; the near-side upper shell is removed as a visual cutaway.
  // The only structural asymmetry is the external airlock hatch.
  const hullBlue=material(0x2354af), hullDark=material(0x142b54), roomFloor=material(0xbcb8ab), wall=material(0xe5d9bc);
  box(18.4,.36,6.6,hullBlue,[0,-.2,0]);
  box(18,.12,6.2,roomFloor,[0,.04,0]);
  for(const side of [-1,1]){
    if(side<0) box(18.4,.8,.2,hullBlue,[0,.4,side*3.2]);
    else { // near side is cut low for the camera; only one hatch interrupts the hull.
      box(.35,.8,.2,hullBlue,[-9.025,.4,3.2]);box(16.35,.8,.2,hullBlue,[1.025,.4,3.2]);
    }
    for(const x of [-5.7,5.7]){
      const wheel=cylinder(.61,.61,.32,c.navy,[x,.05,side*3.29],room,8);wheel.rotation.x=Math.PI/2;
      const cap=cylinder(.35,.35,.34,c.cream,[x,.05,side*3.3],room,8);cap.rotation.x=Math.PI/2;
    }
  }
  box(18.4,1.35,.2,hullDark,[0,1.45,-3.2]);
  box(18.4,.23,.22,hullDark,[0,2.2,-3.2]);
  box(18.4,.28,.26,hullBlue,[0,2.4,-3.2]);
  box(.22,1.1,6.6,hullBlue,[9.1,.55,0]);
  box(.22,1.1,6.6,hullBlue,[-9.1,.55,0]);
  const windscreen=box(.14,1.2,5.9,material(0x78c9ca),[9,1.25,0]);windscreen.rotation.z=-.18;
  for(const side of [-1,1]){
    const engine=cylinder(.58,.66,1.45,c.navy,[-9.75,.75,side*1.9],room,8);engine.rotation.z=Math.PI/2;
    const nozzle=cylinder(.36,.56,.28,c.yellow,[-10.54,.75,side*1.9],room,8);nozzle.rotation.z=Math.PI/2;
  }
  // An inspection-only symmetric outer shell; the near upper side and roof are
  // absent in cutaway mode, with the sole physical exception of the hatch.
  const exterior=new T.Group();exterior.name='Symmetric exterior inspection';scene.add(exterior);exterior.visible=false;
  box(18.4,.22,6.6,hullBlue,[0,2.54,0],exterior);
  const leftEdge=-9.2,rightEdge=9.2,hatchLeft=SHIP_HULL.spacewalk.x0,hatchRight=SHIP_HULL.spacewalk.x1;
  for(const [start,end] of [[leftEdge,hatchLeft],[hatchRight,rightEdge]]){
    box(end-start,1.35,.2,hullDark,[(start+end)/2,1.45,3.2],exterior);
    box(end-start,.23,.22,hullDark,[(start+end)/2,2.2,3.2],exterior);
    box(end-start,.28,.26,hullBlue,[(start+end)/2,2.4,3.2],exterior);
  }
  // Material above the hatch matches its mirrored counterpart.
  box(hatchRight-hatchLeft,.35,.2,hullDark,[(hatchLeft+hatchRight)/2,2.0,3.2],exterior);
  box(hatchRight-hatchLeft,.23,.22,hullDark,[(hatchLeft+hatchRight)/2,2.2,3.2],exterior);
  box(hatchRight-hatchLeft,.28,.26,hullBlue,[(hatchLeft+hatchRight)/2,2.4,3.2],exterior);
  let exteriorView=false, exteriorSide=1;

  // Room walls and collision rectangles share the exact same source geometry.
  let sternDivider;
  const bulkheads=[];
  for(const segment of SHIP_WALLS) {
    const wallMesh=box(segment.x1-segment.x0,1.65,segment.z1-segment.z0,wall,[(segment.x0+segment.x1)/2,.825,(segment.z0+segment.z1)/2]);
    bulkheads.push(wallMesh);
    if(segment.z0===-.1 && segment.z1===.1)sternDivider=wallMesh;
  }
  const portalPieces=[];
  for(const [x,z] of [[5,0],[2,0],[-1,0],[-5,-1.75],[-5,1.75]]){
    for(const side of [-1,1]) portalPieces.push(box(.21,1.85,.12,c.yellow,[x,.925,z+side*.96]));
    portalPieces.push(box(.21,.13,2.04,c.yellow,[x,1.82,z]));
  }
  // Compact, low-poly furnishings stay against the outer wall leaving doors clear.
  const cockpit=box(2.45,.75,1.15,c.navy,[7.35,.48,-2.25]);
  for(const z of [-2.5,-2.15,-1.8])box(.68,.06,.38,c.glow,[7.35,.88,z],room,false);
  for(const x of [6.7,7.8]){box(.63,.2,.6,c.coral,[x,.55,-.75]);box(.63,.65,.15,c.coral,[x,.9,-.45]);}
  // Bunk and mattress.
  for(const y of [.4,1.35]){box(1.7,.18,.95,c.navy,[3.9,y,-2.25]);box(1.52,.15,.82,c.cream,[3.9,y+.16,-2.25]);box(.45,.11,.65,c.coral,[4.4,y+.28,-2.25]);}
  for(const x of [3.1,4.7])box(.1,1.75,.1,c.yellow,[x,.9,-1.8]);
  // Galley.
  box(2.35,.8,.82,c.cream,[.45,.46,-2.45]);box(.7,.04,.5,c.teal,[.15,.9,-2.45],room,false);
  box(.65,.66,.6,c.coral,[.2,.36,1.65]);box(.75,.12,.75,c.cream,[.2,.77,1.65]);
  // Living room / tablet and alien stay close to the room's branching doors.
  box(1.15,.55,.7,c.coral,[-4.1,.38,2.4]);box(1.15,.55,.15,c.coral,[-4.1,.83,2.72]);
  box(.9,.13,.65,c.cream,[-2.4,.62,1.55]);
  const tablet=new T.Group();tablet.name='interactive tablet';room.add(tablet);
  box(.60,.045,.42,c.dark,[0,0,0],tablet);box(.50,.009,.34,c.screen,[0,.027,0],tablet,false);
  const tabletOrigin=new T.Vector3(-2.4,.72,1.55);tablet.position.copy(tabletOrigin);
  const tabletMarker=mesh(new T.TorusGeometry(.38,.035,4,16),c.lime,[-2.4,.12,.75],room,false);tabletMarker.rotation.x=-Math.PI/2;
  // Separate and directly reachable fuel/generator compartment.
  for(const x of [-8.25,-7.55])cylinder(.32,.32,1.2,c.teal,[x,.73,-2.4],room,7);
  box(1,.9,.75,c.navy,[-6.55,.55,-2.35]);box(.5,.09,.1,c.yellow,[-6.55,.73,-1.96],room,false);
  // Suit and pressurization room; this is the ship's sole external hatch.
  box(.4,1.6,2.2,c.navy,[-8.45,.85,1.45]);
  for(const z of [.85,1.9]){sphere(.22,c.cream,[-8.12,1.35,z],room,6,4);box(.35,.7,.32,c.cream,[-8.12,.85,z]);}
  const hatch=box(1.5,1.8,.14,c.navy,[-7.9,.95,3.25]);hatch.name='spacewalk exterior hatch';
  box(1.15,1.35,.08,c.teal,[-7.9,.95,3.34]);
  // Floating objects have physical poses; they do not reset to a sine-wave path
  // after a bump. These conservative proxies trade precision for mobile speed.
  const propStarts=[[-3.25,1.1,-1.35],[-2,1.5,-1.6],[0,1.6,.5],[3.5,1.1,.7],[7,1.5,.3],[-6.5,1.3,1.4]];
  const floatingBodies=createFloatingPropState().map((body,i)=>({...body,position:[...propStarts[i]],previous:[...propStarts[i]]})), floatingVisuals=[];
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
  const alien=makeAlien();alien.position.set(-3.9,.08,-1.7);alien.rotation.y=.36;room.add(alien);
  const alienMarker=mesh(new T.TorusGeometry(.52,.028,4,20),c.lime,[-3.9,.10,-1.7],room,false);alienMarker.rotation.x=-Math.PI/2;
  for(const node of [tablet,tabletMarker,alien,alienMarker])scene.attach(node);
  room.visible=false;
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
  actor.position.set(-2.8,0,-.4);actor.rotation.y=.4;
  const propObstacles=[...SHIP_WALLS,...SHIP_FURNITURE].map(o=>({min:[o.x0,.08,o.z0],max:[o.x1,1.65,o.z1]}));
  const free=shipFree;
  let autoTarget=null, path=[], near='', pickup=0, pickupMode='', held=false, lastPickupState=false, time=0, lastDirection=new T.Vector2(), disposed=false, motionPaused=false, lost=false, suspended=false, tabletHint=false;
  const interactionPositions={tablet:new T.Vector3(-2.4,0,.65),alien:new T.Vector3(-3.9,0,-.7)};
  let loot=null;
  canvas.dataset.lootTier='none';canvas.dataset.lootPhase='idle';canvas.dataset.lootVisible='false';

  function clearFuelLoot(collected=false){
    if(!loot)return;
    const finished=loot;loot=null;
    finished.group.removeFromParent();
    const ownedGeometry=new Set();finished.group.traverse(node=>{if(node.geometry)ownedGeometry.add(node.geometry);});
    for(const geometry of ownedGeometry){geometry.dispose();geometries.delete(geometry);}
    for(const surface of finished.surfaces){surface.dispose();materials.delete(surface);}
    canvas.dataset.lootVisible='false';canvas.dataset.lootPhase=collected?'collected':'cancelled';
    canvas.dataset.lootProgress=collected?'1':'0';
    finished.resolve(collected);
  }

  function playFuelLoot(tier='normal'){
    if(disposed||lost)return Promise.resolve(false);
    if(loot)return loot.promise;
    const kind=tier==='super'?'super':'normal',group=new T.Group(),surfaces=new Set();
    group.name=kind==='super'?'Rainbow super-fuel pickup':'Fuel pickup';scene.add(group);
    // Private materials permit a reduced-motion fade without changing the
    // shared room palette. Every pickup's geometry is released on completion.
    const surface=(base,basic=false)=>{
      const result=typeof base==='number'?(basic?new T.MeshBasicMaterial({color:base}):new T.MeshToonMaterial({color:base,gradientMap:gradient})):base.clone();
      materials.add(result);surfaces.add(result);return result;
    };
    const bodyColor=surface(kind==='super'?c.cream:c.yellow),trim=surface(c.navy),label=surface(c.teal),light=surface(c.cream);
    const shape=new T.Shape();shape.moveTo(-.25,-.30);shape.lineTo(.25,-.30);shape.lineTo(.25,.18);shape.lineTo(.14,.29);shape.lineTo(-.18,.29);shape.lineTo(-.25,.19);shape.closePath();
    const bodyGeometry=new T.ExtrudeGeometry(shape,{depth:.19,bevelEnabled:true,bevelSegments:1,bevelSize:.025,bevelThickness:.025,steps:1,curveSegments:1});
    bodyGeometry.translate(0,0,-.095);
    mesh(bodyGeometry,bodyColor,[0,0,0],group);
    // A hollow, chunky handle and capped spout make this legible as a small can.
    box(.27,.065,.12,trim,[-.045,.40,0],group);
    for(const x of [-.155,.065])box(.055,.15,.12,trim,[x,.34,0],group);
    cylinder(.07,.07,.085,light,[.19,.29,0],group,6);
    box(.085,.027,.11,trim,[.19,.35,0],group,false);
    if(kind==='super'){
      const colors=[0xf07475,0xffb367,0xf4e676,0x8add9b,0x76d7e9,0x8d9ae9,0xd797e2];
      for(let i=0;i<colors.length;i++){
        const color=surface(colors[i]);
        box(.46,.062,.025,color,[0,-.235+i*.064,.13],group,false);
      }
      for(const [inner,outer,opacity] of [[.42,.56,.18],[.56,.64,.07]]){
        const aura=new T.MeshBasicMaterial({color:0xa3e2e6,transparent:true,opacity,depthWrite:false,side:T.DoubleSide,blending:T.AdditiveBlending});
        materials.add(aura);surfaces.add(aura);
        mesh(new T.RingGeometry(inner,outer,24),aura,[0,.05,-.16],group,false);
      }
      for(let i=0;i<6;i++){
        const angle=i*Math.PI/3;
        mesh(new T.OctahedronGeometry(.035),surface(colors[i],true),[Math.cos(angle)*.58,.05+Math.sin(angle)*.58,0],group,false);
      }
    }else{
      box(.31,.26,.025,label,[0,-.015,.13],group,false);
      // One simple pale fuel-drop icon, built from broad polygonal surfaces.
      const drop=mesh(new T.ConeGeometry(.055,.14,5),light,[0,.005,.16],group,false);drop.rotation.z=Math.PI;
    }
    const start=actor.position.clone().add(new T.Vector3(-.80,1.18,.22));
    group.position.copy(start);group.rotation.y=.38;
    const promise=new Promise(resolve=>{loot={group,surfaces,start,elapsed:0,tier:kind,resolve,promise:null};});
    loot.promise=promise;
    for(const value of surfaces)value.userData.baseOpacity=value.opacity;
    cancelGoal();canvas.dataset.lootTier=kind;canvas.dataset.lootPhase='appearing';canvas.dataset.lootVisible='true';canvas.dataset.lootProgress='0';
    updateFuelLoot(0);return promise;
  }

  function updateFuelLoot(dt){
    if(!loot)return;
    loot.elapsed+=dt;
    const duration=reduced.matches ? .25 : 1.85,p=Math.min(1,loot.elapsed/duration);
    const target=actor.position.clone().add(new T.Vector3(0,.9,.09));
    if(reduced.matches){
      loot.group.position.copy(target);loot.group.scale.setScalar(.9);
      for(const value of loot.surfaces){value.transparent=true;value.opacity=value.userData.baseOpacity*(1-p);value.depthWrite=false;}
      loot.group.traverse(node=>{if(node.name==='ink outline')node.visible=false;});
    }else{
      const travel=Math.max(0,Math.min(1,(p-.28)/.72)),eased=travel*travel*(3-2*travel);
      loot.group.position.lerpVectors(loot.start,target,eased);
      loot.group.position.y+=Math.sin(travel*Math.PI)*.32;
      loot.group.scale.setScalar(Math.max(.001,Math.min(1,p/.12)*(1-eased)));
      loot.group.rotation.y=.38+Math.sin(p*Math.PI)*.28;
    }
    canvas.dataset.lootPhase=p<.28?'appearing':'collecting';
    canvas.dataset.lootProgress=p.toFixed(3);canvas.dataset.lootPosition=JSON.stringify(loot.group.position.toArray());
    if(p>=1)clearFuelLoot(true);
  }

  function getScreenAnchors(){
    camera.updateMatrixWorld(true);
    const displayed=!disposed&&!lost&&!suspended&&!exteriorView&&currentRoom==='living'&&roomPhase==='room'&&canvas.clientWidth>0&&canvas.clientHeight>0;
    const project=(object,offset)=>{
      object.updateWorldMatrix(true,false);
      const point=new T.Vector3(...offset).applyMatrix4(object.matrixWorld).project(camera);
      const x=(point.x+1)/2,y=(1-point.y)/2;
      return {x:Math.max(0,Math.min(1,x)),y:Math.max(0,Math.min(1,y)),visible:displayed&&object.visible&&point.z>=-1&&point.z<=1&&x>=0&&x<=1&&y>=0&&y<=1};
    };
    return {tablet:project(tablet,[0,.12,0]),alien:project(alien,[0,2.22,0])};
  }
  // Real lazy-loading boundary: a room's furniture module and meshes do not
  // exist until visited. A cancelled corridor never reveals a late result.
  const roomGroups=new Map(), roomPromises=new Map(), roomAttempts=new Map();
  const corridor=new T.Group();corridor.name='Doorway corridor';scene.add(corridor);corridor.visible=false;
  let corridorPanel=null, roomPhase='loading', currentRoom='living', travel=null, travelEpoch=0;
  const roomSpecs=Object.fromEntries(SHIP_ROOMS.map(spec=>[spec.id,spec]));
  function emitRoom(status,extra={}){roomPhase=status;canvas.dataset.roomPhase=status;onRoomState?.({status,room:currentRoom,from:travel?.from,to:travel?.to,...extra});}
  function buildRoom(id,assets){
    const before=new Set(geometries);
    const spec=roomSpecs[id],group=new T.Group();group.name='Room '+id;scene.add(group);group.visible=false;
    const w=spec.x1-spec.x0,d=spec.z1-spec.z0,cx=(spec.x0+spec.x1)/2,cz=(spec.z0+spec.z1)/2;
    box(w,.12,d,roomFloor,[cx,.04,cz],group);
    // Low side walls keep the selected room legible from the fixed game camera.
    if(spec.z0===-3)box(w,2.5,.16,hullBlue,[cx,1.25,-3.08],group);
    if(spec.z1===3)box(w,.7,.16,hullBlue,[cx,.35,3.08],group);
    if(spec.x0===-8.8)box(.16,.8,d,hullBlue,[-8.88,.4,cz],group);
    if(spec.x1===8.8)box(.16,.8,d,hullBlue,[8.88,.4,cz],group);
    const walls=[];
    for(const segment of SHIP_WALLS){
      const x0=Math.max(segment.x0,spec.x0-.11),x1=Math.min(segment.x1,spec.x1+.11);
      const z0=Math.max(segment.z0,spec.z0-.11),z1=Math.min(segment.z1,spec.z1+.11);
      if(x1-x0<=.01||z1-z0<=.01)continue;
      const part=box(x1-x0,1.65,z1-z0,wall,[(x0+x1)/2,.825,(z0+z1)/2],group);walls.push(part);
    }
    group.userData.walls=walls;
    for(const door of SHIP_DOORS.filter(port=>port.from===id||port.to===id)){
      for(const z of [door.start,door.end])box(.24,2.1,.12,c.navy,[door.at,1.05,z],group);
      box(.24,.13,door.end-door.start+.12,c.navy,[door.at,2.12,(door.start+door.end)/2],group);
      box(.26,.035,door.end-door.start-.18,c.glow,[door.at,2.10,(door.start+door.end)/2],group,false);
    }
    try { assets.createRoomAssets({roomId:id,box,cylinder,sphere,mesh,rod,T,c,material,parent:group}); }
    catch(error){group.removeFromParent();for(const geometry of geometries)if(!before.has(geometry)){geometry.dispose();geometries.delete(geometry);}throw error;}
    group.userData.hatch=[];if(id==='airlock')group.traverse(node=>{if(node.isMesh&&Math.abs(node.position.x+7.9)<.01&&node.position.z>2.85)group.userData.hatch.push(node);});
    roomGroups.set(id,group);return group;
  }
  function loadRoom(id){
    if(roomGroups.has(id))return Promise.resolve(roomGroups.get(id));
    if(roomPromises.has(id))return roomPromises.get(id);
    const attempt=(roomAttempts.get(id)||0)+1;roomAttempts.set(id,attempt);
    const promise=import(`./ship-room-assets.js?room=${encodeURIComponent(id)}&attempt=${attempt}`).then(assets=>{if(disposed)throw new Error('Scene disposed');return buildRoom(id,assets);}).finally(()=>roomPromises.delete(id));
    roomPromises.set(id,promise);return promise;
  }
  function syncRooms(){
    for(const [id,group] of roomGroups)group.visible=!exteriorView&&(roomPhase==='room'?id===currentRoom:roomPhase==='ready'&&id===travel?.to);
    corridor.visible=!exteriorView&&Boolean(travel);
    canvas.dataset.visibleRooms=[...roomGroups].filter(([,group])=>group.visible).map(([id])=>id).join(',');
    canvas.dataset.corridorVisible=String(corridor.visible);canvas.dataset.destination=travel?.to||'';
    canvas.dataset.doorOpen=String(roomPhase==='ready');
    const livingVisible=!exteriorView&&(roomPhase==='room'?currentRoom==='living':roomPhase==='ready'&&travel?.to==='living');
    for(const node of [tablet,tabletMarker,alien,alienMarker])node.visible=livingVisible;
    floatingVisuals.forEach((node,i)=>{const id=shipRoom(floatingBodies[i].position[0],floatingBodies[i].position[2]);node.visible=!exteriorView&&(roomPhase==='room'?id===currentRoom:roomPhase==='ready'&&id===travel?.to);});
  }
  function clearCorridor(){const used=new Set();corridor.traverse(node=>{if(node.geometry)used.add(node.geometry);});for(const node of [...corridor.children])node.removeFromParent();for(const geometry of used){geometry.dispose();geometries.delete(geometry);}corridorPanel=null;}
  function startTravel(door,from,to,sign){
    travel={door,from,to,sign};const epoch=++travelEpoch;clearCorridor();
    const mid=(door.start+door.end)/2, span=door.end-door.start;
    box(1.5,.12,span,roomFloor,[door.at,.045,mid],corridor);
    for(const [z,height] of [[door.start,1.25],[door.end,.35]])box(1.5,height,.12,wall,[door.at,height/2,z],corridor);
    for(const z of [door.start+.14,door.end-.14])box(1.38,.025,.045,c.glow,[door.at,.12,z],corridor,false);
    for(const z of [door.start,door.end])box(.17,2.05,.13,c.navy,[door.at+sign*.62,1.025,z],corridor);
    box(.17,.12,span+.12,c.navy,[door.at+sign*.62,2.08,mid],corridor);
    corridorPanel=box(.12,1.6,span-.15,c.navy,[door.at+sign*.62,.8,mid],corridor);
    emitRoom('loading');syncRooms();
    loadRoom(to).then(()=>{if(disposed||epoch!==travelEpoch||!travel)return;emitRoom('opening');syncRooms();},()=>{if(disposed||epoch!==travelEpoch||!travel)return;emitRoom('error');syncRooms();});
  }
  function retryRoom(){if(roomPhase!=='error'||!travel)return;const {door,from,to,sign}=travel;startTravel(door,from,to,sign);}
  function finishTravel(next){currentRoom=next;travel=null;travelEpoch++;clearCorridor();if(autoTarget)path=pathTo(interactionPositions[autoTarget]);emitRoom('room');syncRooms();}
  function corridorProgress(dx){
    if(exteriorView)return;
    if(travel){
      const progress=travel.sign*(actor.position.x-travel.door.at);
      if(progress<-.7)finishTravel(travel.from);
      else if(roomPhase==='ready'&&progress>.7)finishTravel(travel.to);
      return;
    }
    if(roomPhase!=='room'||Math.abs(dx)<.001)return;
    for(const door of SHIP_DOORS){
      if(currentRoom!==door.from&&currentRoom!==door.to)continue;
      const to=currentRoom===door.from?door.to:door.from;
      const center=spec=>(spec.x0+spec.x1)/2;
      const sign=Math.sign(center(roomSpecs[to])-center(roomSpecs[currentRoom]));
      if(sign*dx<=0||Math.abs(actor.position.x-door.at)>.7||actor.position.z<door.start+.25||actor.position.z>door.end-.25)continue;
      startTravel(door,currentRoom,to,sign);break;
    }
  }
  function movementFree(x,z){
    if(!shipFree(x,z))return false;
    if(travel){const progress=travel.sign*(x-travel.door.at);if(roomPhase!=='ready'&&progress>.15)return false;
      if(z<travel.door.start+.25||z>travel.door.end-.25)return false;}
    return true;
  }
  const ready=loadRoom(currentRoom).then(()=>{if(disposed)return false;emitRoom('room');syncRooms();return true;},error=>{if(!disposed)emitRoom('error',{initial:true});throw error;});
  function pathTo(target) { return shipPath(actor.position,target).map(p=>new T.Vector3(p.x,0,p.z)); }
  function goTo(which) { if(!interactionPositions[which])return;autoTarget=which;path=pathTo(interactionPositions[which]);if(!path.length){autoTarget=null;return false;}return true; }
  function cancelGoal(){autoTarget=null;path=[];}
  function updateNear(){const next=roomPhase!=='room'?'':actor.position.distanceTo(interactionPositions.tablet)<.9?'tablet':actor.position.distanceTo(interactionPositions.alien)<.9?'alien':'';if(next!==near){near=next;onNear?.(near);}canvas.dataset.near=near||'none';}
  function beginPickup(){cancelGoal();pickupMode='take';pickup=0;held=false;actor.rotation.y=Math.PI;return true;}
  function putDown(){pickupMode='return';pickup=0;held=false;lastPickupState=false;}
  const handPoint=new T.Vector3(), startPoint=new T.Vector3();
  const pose={};
  const mobileView=()=>matchMedia('(pointer: coarse)').matches||innerWidth<700;
  let cameraX=actor.position.x,cameraZ=actor.position.z;
  const visibilityRay=new T.Raycaster(), sightTarget=new T.Vector3(), sightDirection=new T.Vector3();
  function revealPlayer(){
    const activeGroups=[...roomGroups.values()].filter(group=>group.visible);
    for(const group of activeGroups)for(const hatch of group.userData.hatch||[])hatch.visible=currentRoom!=='airlock';
    const walls=activeGroups.flatMap(group=>group.userData.walls||[]);
    for(const wallMesh of walls){wallMesh.scale.y=1;wallMesh.position.y=.825;wallMesh.updateMatrixWorld(true);}
    for(const trim of portalPieces){trim.visible=true;trim.updateMatrixWorld(true);}
    // Cut obstructing walls down visually while retaining their full collision rectangles.
    // Check head and body rays: this also works when crossing a doorway diagonally.
    for(const height of [1.0,1.55]){
      sightTarget.set(actor.position.x,height,actor.position.z);
      sightDirection.copy(sightTarget).sub(camera.position);
      visibilityRay.set(camera.position,sightDirection.clone().normalize());visibilityRay.far=sightDirection.length();
      for(const hit of visibilityRay.intersectObjects(portalPieces,false))hit.object.visible=false;
      for(const hit of visibilityRay.intersectObjects(walls,false)){
        hit.object.scale.y=.18;hit.object.position.y=.825*.18;hit.object.updateMatrixWorld(true);
      }
    }
    if(currentRoom==='fuel')for(const wallMesh of walls)if(Math.abs(wallMesh.position.z)<.15){wallMesh.scale.y=.18;wallMesh.position.y=.825*.18;}
  }
  function update(dt,input={x:0,y:0},active=true){
    if(disposed||lost||suspended)return;
    const previousActor=actor.position.toArray();
    dt=Math.min(.04,Math.max(0,dt));if(!motionPaused&&!reduced.matches)time+=dt;
    let dx=0,dz=0,moving=false;
    if(active&&!pickupMode){
      if(input.x||input.y){cancelGoal();const v=new T.Vector2(input.x,input.y);if(v.length()>1)v.normalize();
        // Controls follow screen directions, with the fixed oblique camera.
        dx=v.x*.9285+v.y*.3714;dz=-v.x*.3714+v.y*.9285;
      }else if(path.length){
        // Complete the short chamber before turning toward the next waypoint.
        // The static room path can turn beside a bulkhead sooner than the
        // chamber's exit, so replan on arrival instead of wedging at its side.
        if(travel){dx=travel.sign;dz=0;}
        else {const delta=path[0].clone().sub(actor.position);if(delta.length()<.09){path.shift();if(!path.length){const arrived=autoTarget;autoTarget=null;onArrive?.(arrived);}}else{delta.normalize();dx=delta.x;dz=delta.z;}}
      }
      const speed=2.4,oldX=actor.position.x,oldZ=actor.position.z;
      if(movementFree(oldX+dx*speed*dt,oldZ))actor.position.x+=dx*speed*dt;
      if(movementFree(actor.position.x,oldZ+dz*speed*dt))actor.position.z+=dz*speed*dt;
      moving=Math.hypot(actor.position.x-oldX,actor.position.z-oldZ)>.0001;
      if(moving){const wanted=Math.atan2(dx,dz),difference=Math.atan2(Math.sin(wanted-actor.rotation.y),Math.cos(wanted-actor.rotation.y));actor.rotation.y+=difference*Math.min(1,dt*14);}
    }
    corridorProgress(dx);
    if(corridorPanel&&travel){const wanted=roomPhase==='opening'||roomPhase==='ready'?2.8:.8;corridorPanel.position.y=reduced.matches?wanted:corridorPanel.position.y+(wanted-corridorPanel.position.y)*Math.min(1,dt*8);if(roomPhase==='opening'&&corridorPanel.position.y>2.6)emitRoom('ready');}
    syncRooms();
    updateNear();
    const viewed=roomSpecs[roomPhase==='ready'&&travel?travel.to:currentRoom];
    const targetX=exteriorView?0:travel?travel.door.at:(viewed.x0+viewed.x1)/2;
    const targetZ=exteriorView?0:travel?(travel.door.start+travel.door.end)/2:(viewed.z0+viewed.z1)/2;
    const follow=reduced.matches?1:1-Math.exp(-Math.max(dt,.001)*6);
    cameraX+=(targetX-cameraX)*follow;cameraZ+=(targetZ-cameraZ)*follow;
    camera.position.set(10+cameraX,17,(exteriorView?25*exteriorSide:25)+cameraZ);camera.lookAt(cameraX,.85,cameraZ);
    if(!exteriorView)revealPlayer();
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
    stepFloatingProps(floatingBodies,dt,{player:{position:actor.position.toArray(),previous:previousActor,radius:.43},obstacles:propObstacles,bounds:{min:[-8.95,.15,-3.1],max:[8.95,2.95,3.1]},idleMotion:!motionPaused&&!reduced.matches,paused:!active});
    floatingBodies.forEach((body,i)=>{floatingVisuals[i].position.set(...body.position);floatingVisuals[i].rotation.set(...body.rotation);});
    canvas.dataset.floatingProps=JSON.stringify(floatingPropSnapshot(floatingBodies));
    canvas.dataset.propCollisions=String(floatingBodies.reduce((sum,body)=>sum+body.contacts,0));
    canvas.dataset.propPlayerCollisions=String(floatingBodies.reduce((sum,body)=>sum+body.playerContacts,0));
    canvas.dataset.shadowMap='enabled';
    tabletMarker.material=near==='tablet'||tabletHint?c.lime:c.teal;alienMarker.material=near==='alien'?c.lime:c.teal;
    tabletMarker.scale.setScalar(tabletHint&&!held&&!pickupMode&&!reduced.matches&&!motionPaused?1+Math.sin(time*2.2)*.045:1);
    canvas.dataset.room=currentRoom;canvas.dataset.playerX=actor.position.x.toFixed(3);canvas.dataset.playerZ=actor.position.z.toFixed(3);
    canvas.dataset.heldTablet=String(held||pickupMode==='take');
    // Input can be locked during dialogue and rewards without freezing loot.
    updateFuelLoot(dt);
  }
  let width=0,height=0;
  function resize(){const w=canvas.clientWidth,h=canvas.clientHeight;if(!w||!h||(w===width&&h===height))return;width=w;height=h;renderer.setSize(w,h,false);const aspect=w/h;const vertical=!exteriorView?Math.max(8.4,8/aspect):Math.max(9.2,23/aspect);camera.left=-vertical*aspect/2;camera.right=vertical*aspect/2;camera.top=vertical/2;camera.bottom=-vertical/2;camera.zoom=1;camera.updateProjectionMatrix();}
  function render(){if(disposed||lost||suspended)return;resize();renderer.render(scene,camera);}
  const contextLost=e=>{e.preventDefault();lost=true;clearFuelLoot(false);onError?.();};canvas.addEventListener('webglcontextlost',contextLost);
  const raycaster=new T.Raycaster(),pointer=new T.Vector2();
  function pick(clientX,clientY){if(disposed||lost||suspended||exteriorView||currentRoom!=='living'||roomPhase!=='room')return '';const rect=canvas.getBoundingClientRect();if(!rect.width||!rect.height)return '';pointer.set((clientX-rect.left)/rect.width*2-1,-(clientY-rect.top)/rect.height*2+1);raycaster.setFromCamera(pointer,camera);const hit=raycaster.intersectObjects([tablet,alien],true).find(item=>item.object.name!=='ink outline');if(!hit)return '';let n=hit.object;while(n){if(n===tablet)return 'tablet';if(n===alien)return 'alien';n=n.parent;}return '';}
  update(0);render();
  return {ready,retryRoom,update,render,resize,goTo,cancelGoal,beginPickup,putDown,pick,getNear:()=>near,
    getScreenAnchors,playFuelLoot,
    setTabletHint(value){tabletHint=Boolean(value);canvas.dataset.tabletHint=String(tabletHint);},
    setSuspended(value){suspended=Boolean(value);canvas.dataset.suspended=String(suspended);},
    setExterior(value,side=1){exteriorView=Boolean(value);exteriorSide=side<0?-1:1;exterior.visible=exteriorView;room.visible=exteriorView;syncRooms();canvas.dataset.view=exteriorView?'exterior':'cutaway';canvas.dataset.exteriorSide=String(exteriorSide);width=0;cameraX=exteriorView?0:actor.position.x;cameraZ=exteriorView?0:actor.position.z;camera.position.set(10+cameraX,17,(exteriorView?25*exteriorSide:25)+cameraZ);camera.lookAt(cameraX,.45,cameraZ);resize();render();},
    setPaused(value){motionPaused=value;},
    dispose(){disposed=true;travelEpoch++;clearFuelLoot(false);clearCorridor();canvas.removeEventListener('webglcontextlost',contextLost);ragdoll.dispose?.();model.userData.dispose?.();for(const g of geometries)g.dispose();for(const m of materials)m.dispose();gradient.dispose();key.shadow.map?.dispose();renderer.dispose();}
  };
}

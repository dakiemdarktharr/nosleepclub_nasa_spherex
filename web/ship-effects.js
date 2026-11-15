/** Original procedural flight hardware and cinematics. No external art/runtime. */
export function createShipEffects({T, scene, camera, actor, model, alien, box, mesh, cylinder, sphere, rod, material, c, reduced}) {
  const hull = new T.Group(); hull.name = 'Touch The Sky / industrial survey vessel'; scene.add(hull);
  const steel = material(0x8b9ca7), armor = material(0x344658), dark = material(0x14202d);
  const ivory = material(0xdedcc9), amber = material(0xf1ae43), cyan = material(0x8ae8ed, true);
  const flare = material(0x70dfff, true), rainbow = [0xff647f,0xffbc55,0xf3ee79,0x78f6aa,0x69dcff,0xb59aff].map(n=>material(n,true));
  // Faceted pressure hull, tapering nose, armored spine and exposed aft frame.
  const body = cylinder(3.05,3.05,15.8,armor,[-.6,.9,0],hull,8); body.rotation.z=Math.PI/2;
  const nose = cylinder(1.18,3.05,4.3,steel,[9.45,.9,0],hull,8); nose.rotation.z=-Math.PI/2;
  box(13.2,.48,3.1,ivory,[-.7,3.62,0],hull);
  box(11.8,.12,.28,amber,[-1,3.91,-.85],hull,false);
  for(const side of [-1,1]) {
    const glass=box(2.8,.08,1.22,cyan,[8.6,2.92,side*1.16],hull);glass.rotation.z=-.38;glass.rotation.x=side*.25;
    for(let x=-7;x<=6;x+=2.2) {
      box(1.85,.12,1.3,steel,[x,3.15,side*1.94],hull).rotation.x=side*.65;
      box(.14,1.2,.16,dark,[x,1.25,side*3.06],hull);
      for(const offset of [-.65,.65])sphere(.065,amber,[x+offset,3.29,side*1.94],hull,5,3);
    }
    box(7,.18,.16,amber,[-2,.8,side*3.04],hull);
    rod([-7,1.7,side*3.2],[2.9,1.7,side*3.2],.09,steel,hull);
    rod([-6,-.25,side*2.6],[-2,-.25,side*4.7],.20,dark,hull);
    // Swept outriggers and radiators give the craft a ship silhouette.
    const fin=box(5,.16,2.3,armor,[-3.8,.1,side*3.8],hull);fin.rotation.y=side*-.27;
    for(let i=0;i<6;i++)box(.11,.20,1.75,steel,[-5.7+i*.65,.21,side*3.8],hull,false);
    const nacelle=cylinder(.85,.94,4.5,dark,[-7.7,.65,side*3.8],hull,10);nacelle.rotation.z=Math.PI/2;
    for(const x of [-9.7,-8.9,-6]) {
      const collar=cylinder(.97,.97,.24,steel,[x,.65,side*3.8],hull,10);collar.rotation.z=Math.PI/2;
    }
    const nozzle=cylinder(.64,.88,.7,amber,[-10.4,.65,side*3.8],hull,10);nozzle.rotation.z=Math.PI/2;
    const core=cylinder(.59,.59,.05,cyan,[-10.78,.65,side*3.8],hull,12);core.rotation.z=Math.PI/2;
  }
  for(let i=0;i<8;i++)box(.16,.12,1.65,dark,[-7.4+i*.43,3.93,0],hull,false);
  box(1.1,.15,1.8,steel,[2,4.02,0],hull);rod([2,4.05,0],[2.4,5,0],.05,steel,hull);
  sphere(.14,cyan,[2.4,5,0],hull,6,4);
  // One airlock on the near side, with a protected service ladder.
  box(1.1,1.7,.16,ivory,[-6,1.1,3.01],hull);box(.68,1.15,.19,dark,[-6,1.1,3.08],hull);
  for(const x of [-6.5,-5.5])rod([x,-.5,3.19],[x,1.7,3.19],.045,amber,hull);
  for(let y=-.4;y<1.8;y+=.35)rod([-6.5,y,3.19],[-5.5,y,3.19],.04,steel,hull);
  const flames=[];
  for(const side of [-1,1]) {
    const flame=mesh(new T.ConeGeometry(.64,4,12),flare,[-12.7,.65,side*3.8],hull,false);flame.rotation.z=Math.PI/2;flames.push(flame);
  }
  hull.visible=false;

  const engine=new T.Group();engine.name='Interactive thruster';engine.position.set(-6.6,0,-2.3);scene.add(engine);
  box(1.25,.25,1.03,dark,[0,.22,0],engine);
  const reactor=cylinder(.47,.52,1.1,steel,[0,.9,0],engine,12);reactor.rotation.x=Math.PI/2;
  for(const z of [-.5,.1,.5]){const ring=cylinder(.54,.54,.09,amber,[0,.9,z],engine,12);ring.rotation.x=Math.PI/2;}
  const engineLight=mesh(new T.CircleGeometry(.37,20),cyan,[0,.9,.56],engine,false);
  const aura=new T.Group();engine.add(aura);
  for(let i=0;i<6;i++) {const ring=mesh(new T.TorusGeometry(.67+i*.055,.02,4,40),rainbow[i],[0,.9,.1],aura,false);ring.rotation.y=i*.48;}
  const marker=mesh(new T.TorusGeometry(.40,.035,4,24),cyan,[-6.55,.13,-1.15],scene,false);marker.rotation.x=-Math.PI/2;
  const launchTarget=box(.7,.12,.52,cyan,[7.2,.96,-1.75],scene);
  const gate=new T.Group();gate.position.set(-3.9,1.22,-2.15);scene.add(gate);
  const green=material(0xaaff39,true), jade=material(0x348a36,true);
  mesh(new T.CircleGeometry(1.03,64),jade,[0,0,0],gate,false);
  for(let i=0;i<6;i++) {
    const ring=mesh(new T.TorusGeometry(.25+i*.15,.033,4,52,Math.PI*1.72),i%2?green:material(0x76ce32,true),[0,0,.02+i*.012],gate,false);
    ring.rotation.z=i*.9;
  }
  for(let i=0;i<28;i++){const a=i*Math.PI/14;const blob=sphere(.065+(i%3)*.015,green,[Math.cos(a)*1.06,Math.sin(a)*1.06,.03],gate,5,3);blob.scale.y=1.6;}
  gate.visible=false;
  const wormholes=[];
  for(const x of [9,-9]){
    const hole=new T.Group();scene.add(hole);hole.position.set(x,1,0);hole.rotation.y=Math.PI/2;
    mesh(new T.CircleGeometry(4.7,64),material(0x070b21,true),[0,0,0],hole,false);
    for(let i=0;i<9;i++){const ring=mesh(new T.TorusGeometry(4.0+i*.14,.07,5,64),rainbow[i%6],[0,0,i*.05],hole,false);ring.rotation.x=.07*i;}
    hole.visible=false;wormholes.push(hole);
  }
  const stars=new T.Group();scene.add(stars);
  for(let i=0;i<52;i++)box(.025+(i%3)*.018,.025, .025,material(0xaac4d8,true),[((i*17)%53)-26,((i*13)%31)-14, -8-((i*7)%17)],stars,false);
  const alienLegs=alien.children.filter(n=>n.isMesh&&n.geometry?.type==='CylinderGeometry'&&Math.abs(n.position.y-.19)<.01);
  const scared=[];model.traverse(node=>{if(['dark pupil','single amber eye','short mouth'].includes(node.name))scared.push({node,scale:node.scale.clone()});});
  const mouth=mesh(new T.CircleGeometry(.10,16),c.dark,[0,1.25,.79],model.userData.head,false);mouth.visible=false;mouth.scale.y=1.45;
  let cinematic=null, engineTier='none', effectTime=0;
  function setCinematic(value){cinematic=value;}
  function update(dt,{exterior,currentRoom,roomPhase,paused}){
    if(!paused&&!reduced.matches)effectTime+=dt;
    const flight=cinematic?.kind==='flight', encounter=cinematic?.kind==='encounter';
    hull.visible=exterior||flight;stars.visible=exterior||flight;
    engine.visible=!exterior&&!flight&&roomPhase==='room'&&currentRoom==='fuel';marker.visible=engine.visible;
    launchTarget.visible=!exterior&&!flight&&roomPhase==='room'&&currentRoom==='cockpit';
    engine.position.x=-6.6+(engineTier==='super'&&!paused&&!reduced.matches?Math.sin(effectTime*25)*.035:0);
    aura.visible=engineTier==='super';aura.rotation.z=effectTime*.8;engineLight.material=engineTier==='none'?c.screen:engineTier==='super'?rainbow[Math.floor(effectTime*2)%6]:cyan;
    hull.position.set(0,0,0);hull.scale.setScalar(1);hull.rotation.set(0,0,0);
    flames.forEach((node,i)=>{node.visible=flight;node.material=cinematic?.tier==='super'?rainbow[(Math.floor(effectTime*3)+i)%6]:flare;node.scale.y=reduced.matches?1:1+Math.sin(effectTime*23+i)*.12;});
    wormholes.forEach(h=>h.visible=false);gate.visible=encounter;
    actor.visible=!exterior&&!flight;
    camera.zoom=1;camera.updateProjectionMatrix();
    for(const item of scared)item.node.scale.copy(item.scale);
    mouth.visible=false;
    if(encounter){
      const t=cinematic.elapsed;
      const appear=Math.min(1,t/1.1);gate.scale.setScalar(Math.max(.001,appear));gate.rotation.z=reduced.matches?0:effectTime*.28;
      alien.visible=t>=1;alien.scale.setScalar(Math.min(1,Math.max(.001,(t-1)/1.25)));
      alien.position.z=-2.6+Math.min(1,Math.max(0,(t-1)/1.6))*.9;
      alienLegs.forEach((leg,i)=>{leg.rotation.x=t>1&&t<2.6&&!reduced.matches?Math.sin(t*14+i*Math.PI)*.45:0;});
      if(t>=2.7){
        gate.scale.setScalar(Math.max(.001,1-(t-2.7)/1.1));
        actor.rotation.y=.08;
        for(const {node,scale} of scared){if(node.name==='dark pupil')node.scale.set(scale.x*.55,scale.y*.7,scale.z);else if(node.name==='single amber eye')node.scale.y=scale.y*1.2;else node.scale.setScalar(.001);}
        mouth.visible=true;model.updateMatrixWorld(true);
        const face=new T.Vector3();mouth.getWorldPosition(face);
        camera.position.set(face.x+.15,face.y+.4,face.z+10);camera.lookAt(face.x,face.y+.12,face.z);
        camera.zoom=2.9;camera.updateProjectionMatrix();
      }else{camera.position.set(-2.8,4.4,8);camera.lookAt(-3.5,1,-1.3);camera.zoom=1.3;camera.updateProjectionMatrix();}
    }else{alien.scale.setScalar(1);alien.position.z=-1.7;alienLegs.forEach(leg=>leg.rotation.x=0);}
    if(flight){
      const t=cinematic.elapsed,superFuel=cinematic.tier==='super';
      if(superFuel){
        wormholes[0].visible=t<2;wormholes[1].visible=t>=2;
        wormholes.forEach(h=>h.rotation.z=reduced.matches?0:effectTime*.4);
        // Enter at the right gate, emerge from the left. Scale keeps the whole
        // hull inside the aperture instead of intersecting its rim.
        hull.scale.setScalar(.65);
        hull.position.x=t<2?-6+t*10:-19+(t-2)*8;
        if(t>1.55&&t<2.05)hull.visible=false;
      }else{hull.position.x=-3+t*2.2;hull.position.y=reduced.matches?0:Math.sin(t*2)*.18;}
      camera.position.set(5,14,29);camera.lookAt(0,1,0);
    }
  }
  return {hull,engine,launchTarget,setCinematic,update,setFuel(tier){engineTier=tier;}};
}

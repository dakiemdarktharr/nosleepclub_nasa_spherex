const assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const path=require('node:path');

(async()=>{
  const {createFloatingPropState,stepFloatingProps,floatingPropSnapshot}=await import(pathToFileURL(path.join(__dirname,'../web/room-prop-physics.js')));
  const specimen=(position=[0,1,0],velocity=[0,0,0])=>createFloatingPropState([{id:'mug',kind:'mug',position,velocity,radius:.25,mass:.5}]);
  const idle=specimen([0,1,0],[.1,.03,0]);
  const initial=floatingPropSnapshot(idle);
  stepFloatingProps(idle,.1,{idleMotion:false});
  assert.deepEqual(floatingPropSnapshot(idle),initial,'reduced decorative motion holds untouched objects still');
  // A moving astronaut must transfer momentum even with decorative motion off.
  for(let i=0;i<30;i++){
    const previous=[-1+i*.04,0,0],position=[-1+(i+1)*.04,0,0];
    stepFloatingProps(idle,1/60,{idleMotion:false,player:{previous,position}});
  }
  assert.ok(idle[0].playerContacts>0,'real capsule contact was recorded');
  assert.ok(idle[0].velocity[0]>.2,'astronaut transfers velocity to prop');
  const afterHit=[...idle[0].position];
  for(let i=0;i<30;i++)stepFloatingProps(idle,1/60,{idleMotion:false});
  assert.ok(idle[0].position[0]>afterHit[0]+.1,'prop drifts after astronaut stops touching it');
  assert.ok(idle[0].rotation.some(v=>Math.abs(v)>.01),'off-centre impact spins prop');
  const frozen=floatingPropSnapshot(idle);
  stepFloatingProps(idle,.1,{paused:true});
  assert.deepEqual(floatingPropSnapshot(idle),frozen,'overlay pause stops all prop integration');

  const wall=specimen([4.3,1,0],[2,0,0]);
  for(let i=0;i<30;i++)stepFloatingProps(wall,1/60);
  assert.ok(wall[0].velocity[0]<0,'room wall reflects velocity');
  assert.ok(wall[0].position[0]<=4.47,'wall contact remains inside room');
  const desk=specimen([-1,1,0],[2,0,0]);
  for(let i=0;i<50;i++)stepFloatingProps(desk,1/60,{obstacles:[{min:[0,0,-1],max:[1,1.4,1]}]});
  assert.ok(desk[0].position[0]<-.25&&desk[0].velocity[0]<0,'prop rebounds off furniture rather than passing through');

  const pair=createFloatingPropState([
    {id:'book',kind:'book',position:[-.4,1,0],velocity:[1,0,0],radius:.25,mass:.5},
    {id:'pen',kind:'pen',position:[.4,1,0],velocity:[0,0,0],radius:.25,mass:.1}
  ]);
  for(let i=0;i<40;i++)stepFloatingProps(pair,1/120);
  assert.ok(pair[1].velocity[0]>.5,'lighter prop receives momentum in a prop/prop collision');
  assert.ok(pair[0].contacts>0&&pair[1].contacts>0);
  assert.ok(Math.abs(pair[0].position[0]-pair[1].position[0])>=.4999,'pair remains separated');
  const corner=createFloatingPropState([
    {id:'a',position:[4.44,1,0],velocity:[0,0,0],radius:.25,mass:.5},
    {id:'b',position:[4.20,1,0],velocity:[2,0,0],radius:.25,mass:.5}
  ]);
  stepFloatingProps(corner,1/120);
  assert.ok(corner.every(b=>b.position[0]<=4.47),'pair separation does not eject a prop through a wall');

  const coarse=specimen([0,1,0],[1,.3,-.5]),fine=specimen([0,1,0],[1,.3,-.5]);
  for(let i=0;i<30;i++)stepFloatingProps(coarse,1/30);
  for(let i=0;i<120;i++)stepFloatingProps(fine,1/120);
  for(let i=0;i<3;i++)assert.ok(Math.abs(coarse[0].position[i]-fine[0].position[i])<1e-8,'fixed substeps preserve frame-rate independence');
  const layout=createFloatingPropState();
  for(let frame=0;frame<18000;frame++){
    stepFloatingProps(layout,frame===60?5:1/60,{obstacles:[{min:[-4.7,0,-3.7],max:[4.7,1.2,-2]}]});
    for(const body of layout){
      assert.ok([...body.position,...body.velocity,...body.rotation,...body.spin].every(Number.isFinite),'long-run values remain finite');
      assert.ok(body.position[0]>=-4.72+body.radius-1e-3&&body.position[0]<=4.72-body.radius+1e-3,'bounded horizontal position');
      assert.ok(body.position[1]>=.15+body.radius-1e-3&&body.position[1]<=2.95-body.radius+1e-3,'bounded altitude');
      assert.ok(body.position[2]>=-3.78+body.radius-1e-3&&body.position[2]<=3.78-body.radius+1e-3,'bounded room depth');
    }
  }
  console.log('Floating room props: player and prop impulses, furniture/wall contacts, reduced motion, pause, timestep stability and five-minute bounds passed');
})().catch(error=>{console.error(error);process.exitCode=1;});

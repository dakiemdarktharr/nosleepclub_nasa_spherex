"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const nodes=new Map(),events=[];
const node=id=>{if(!nodes.has(id))nodes.set(id,{id,value:"",hidden:false,checked:false,textContent:"",handlers:{},classList:{toggle(){}},getContext(){return{};},addEventListener(k,f){this.handlers[k]=f;},setAttribute(){},removeAttribute(){},replaceChildren(){},append(){}});return nodes.get(id);};
const document={getElementById:node,querySelectorAll:()=>[],createElement:()=>node("created"+nodes.size),addEventListener(){},dispatchEvent(e){events.push(e.type);},fonts:{addEventListener(){}}};
const localStorage={getItem:()=>null,setItem(){},removeItem(){}};
const window={addEventListener(){}};
const context={window,document,localStorage,location:{protocol:"http:"},fetch:()=>new Promise(()=>{}),setTimeout,clearTimeout,setInterval,clearInterval,CustomEvent:class{constructor(type){this.type=type;}},console};
vm.createContext(context);vm.runInContext(fs.readFileSync("web/review-store.js","utf8"),context);context.ReviewStore=window.ReviewStore;
vm.runInContext(fs.readFileSync("web/app.js","utf8"),context);
const manifest=JSON.parse(fs.readFileSync("web/data/manifest.json","utf8"));const scene=manifest.scenes.find(s=>s.motion?.spectral_configuration==="strict");
assert(scene&&scene.candidates.length,"real shipped scene must retain a selectable residual");
context.fixture=scene;
vm.runInContext('state.scene=fixture;state.manifest={analysis_sha256:"a".repeat(64)};state.ready=true;render=()=>{};loadReview=()=>{};select("target");',context);
assert.equal(node("motion-panel").hidden,false);node("show-motion").checked=true;
vm.runInContext('select(fixture.candidates[0].id);',context);
assert.equal(node("motion-panel").hidden,true,"WISE motion must not appear under a residual context");assert.equal(node("show-motion").checked,false);assert.equal(node("show-motion").disabled,true);assert.equal(node("motion-overlay-label").hidden,true);assert.equal(node("prior-overlay-label").hidden,true);assert.equal(window.SkyApp.context().selection,scene.candidates[0].id);
vm.runInContext('select("target");',context);assert.equal(node("motion-panel").hidden,false);assert.equal(node("show-motion").disabled,false);assert.equal(node("motion-overlay-label").hidden,false);

// The older failed request cannot replace the newer successful scene's status.
context.pending=[];
vm.runInContext('loadImage=src=>new Promise((resolve,reject)=>pending.push({src,resolve,reject}));getJson=()=>Promise.resolve({});motionPanel=()=>{};candidateList=()=>{};sceneList=()=>{};evidenceContent=()=>{};select=()=>{};setMode=()=>{};state.gaia=null;window.loadFixture=scene=>loadScene(scene);',context);
async function run(){
  const old=window.loadFixture({...scene,id:"old-scene"});const fresh=window.loadFixture({...scene,id:"new-scene"});
  assert.equal(context.pending.length,6);for(const call of context.pending.slice(3))call.resolve({});await fresh;
  assert.equal(window.SkyApp.context().scene_id,"new-scene");assert.equal(window.SkyApp.context().ready,true);assert.equal(node("load-state").hidden,true);
  context.pending[0].reject(Error("late old request"));await old;
  assert.equal(window.SkyApp.context().scene_id,"new-scene");assert.equal(node("load-state").hidden,true);assert.equal(events.filter(x=>x==="scene:failed").length,0);
  console.log("App workflow: target/residual scientific context, motion visibility and stale scene failure isolation passed");
}
run().catch(e=>{console.error(e);process.exitCode=1;});

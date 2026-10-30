"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const source=fs.readFileSync("web/reference-evidence.js","utf8"),clone=x=>JSON.parse(JSON.stringify(x));
const text=n=>n.textContent+n.children.map(text).join(" ");
const tick=async()=>{for(let i=0;i<20;i++)await Promise.resolve();};
function metric(n){return {n,rms_arcsec:n?1.5:null,median_radial_arcsec:n?1:null,p90_radial_arcsec:n?2:null,mean_east_north_arcsec:n?[.1,-.2]:null};}
function summary(planned,completed,supported){return {planned_pairs:planned,common_completed:completed,common_numerical:supported,median_model_shift_arcsec:completed?.1:null,maximum_model_shift_arcsec:completed?.2:null,
  arms:["nearest","bilinear"].map(variant=>({variant,planned,completed,failed:planned-completed,numerically_supported:supported,negative_target_flux:0,all_completed:metric(completed),common_completed:metric(completed),common_numerical:metric(supported)}))};}
function fixture(){
  const download={bytes:123456,sha256:"a".repeat(64)};
  const stars={schema:"reference-star-overview-1",promotion:false,protocol_commit:"a".repeat(40),design_sha256:"b".repeat(64),journal_digest:"c".repeat(64),download,
    counts:{expected:840,recorded:840,missing:0,statuses:{fit_completed:720,fit_failed:0,preparation_failed:120}},summary:summary(420,360,350),
    sources:Array.from({length:21},(_,i)=>({source_id:String(1000+i),...summary(20,i<18?20:0,i===0?10:i<18?20:0)})),
    frames:Array.from({length:20},(_,i)=>({obs_id:"frame"+i,...summary(21,18,i<10?17:18)}))};
  const names=["plane_null","quadratic_null","plane_300uJy","plane_600uJy","quadratic_300uJy","quadratic_600uJy"];
  const presence={schema:"source-presence-overview-1",promotion:false,protocol_commit:"d".repeat(40),threshold_commit:"e".repeat(40),geometry_sha256:"f".repeat(64),download,
    threshold:{value:17.7,protocol_commit:"d".repeat(40),threshold_commit:"e".repeat(40)},calibration:{planned:1998,completed:1998,failed:0,missing:0,recorded:1998},validation:{planned:5994,completed:5994,failed:0,missing:0,recorded:5994},conditional_gates_passed:true,
    cases:names.map(scenario=>{const nullCase=scenario.endsWith("null"),flux=nullCase?0:scenario.includes("300")?300:600,accepted=nullCase?0:flux===300?400:900;
      return {scenario,role:nullCase?"null":"positive",flux_ujy:flux,background:scenario.startsWith("plane")?"plane":"quadratic",planned:999,completed:999,failed:0,accepted,conservative_events:accepted,one_sided_confidence:.975,false_accept_upper:nullCase?.0037:null,power_lower:nullCase?null:flux===300?.36:.87,gate_pass:nullCase||flux===600?true:null};})};
  return [stars,presence];
}
function harness(){
  const nodes=new Map(),requests=[];let serial=0;
  function node(id){if(!nodes.has(id))nodes.set(id,{id,value:id==="rstar-selection"?"common_completed":"",textContent:"",children:[],attrs:{},handlers:{},hidden:false,open:false,tabIndex:0,
    append(x){this.children.push(x);},replaceChildren(...x){this.children=x;},addEventListener(k,fn){this.handlers[k]=fn;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},focus(){this.focused=true;}});return nodes.get(id);}
  vm.runInNewContext(source,{document:{getElementById:node,createElement:tag=>node(tag+serial++)},fetch:url=>new Promise(resolve=>requests.push({url,resolve})),console});
  return {node,requests,open(){node("reference-presence").open=true;node("reference-presence").handlers.toggle();},reply(pair,offset=0){pair.forEach((value,i)=>requests[offset+i].resolve({ok:true,json:async()=>value}));}};
}
async function run(){
  const h=harness();assert.equal(h.requests.length,0);h.open();h.open();assert.equal(h.requests.length,2);
  assert.deepEqual(h.requests.map(x=>x.url),["data/reference-stars/overview.json","data/source-presence/overview.json"]);
  h.reply(fixture());await tick();
  assert.equal(h.node("reference-retry").hidden,true);assert.equal(h.node("rstar-summary-rows").children.length,2);assert.equal(h.node("rstar-source-rows").children.length,21);assert.equal(h.node("presence-case-rows").children.length,6);
  assert.equal(h.node("rstar-attempts").textContent,"720/840");assert.equal(h.node("rstar-failures").textContent,"120/840");assert.match(text(h.node("rstar-source-rows")),/0\/20 · 0\/20 — \/ —/);
  h.node("rstar-selection").value="common_numerical";h.node("rstar-selection").handlers.change();assert.match(text(h.node("rstar-summary-rows")),/350\/420/);
  assert.match(h.node("reference-status").textContent,/vẫn chưa được hiệu chuẩn/);assert.match(h.node("presence-verdict").textContent,/Chưa xác nhận/);
  h.node("reference-tab-presence").handlers.click();assert.equal(h.node("reference-tab-presence").attrs["aria-selected"],"true");assert.equal(h.node("reference-stars-panel").hidden,true);
  let prevented=false;h.node("reference-tab-presence").handlers.keydown({key:"ArrowLeft",preventDefault(){prevented=true;}});assert.equal(prevented,true);assert.equal(h.node("reference-tab-stars").focused,true);assert.equal(h.node("reference-stars-panel").hidden,false);
  h.node("reference-tab-stars").handlers.keydown({key:"End",preventDefault(){}});assert.equal(h.node("reference-tab-presence").tabIndex,0);
  h.open();assert.equal(h.requests.length,2); // Reports and geometry are explicit downloads only.
  for(const mutate of [p=>p[0].sources.pop(),p=>p[0].sources[0].source_id=p[0].sources[1].source_id,p=>p[0].counts.statuses.fit_completed=0,p=>p[0].summary.arms[0].common_numerical.n=100,p=>p[0].frames[0].arms[0].completed=0,
    p=>p[1].calibration.completed=1997,p=>p[1].cases[0].planned=998,p=>p[1].cases[0].false_accept_upper=-1,p=>p[1].cases[2].power_lower=.9,p=>p[1].cases[0].gate_pass=false,p=>p[1].threshold_commit="b".repeat(40),p=>p[1].promotion=true,p=>p[1].download.sha256="bad"]){
    const bad=harness(),data=clone(fixture());mutate(data);bad.open();bad.reply(data);await tick();assert.equal(bad.node("reference-retry").hidden,false);assert.equal(bad.node("rstar-summary-rows").children.length,0);assert.equal(bad.node("presence-case-rows").children.length,0);assert.equal(bad.node("rstar-attempts").textContent,"—");
  }
  const retry=harness();retry.open();retry.requests[0].resolve({ok:false,status:503});retry.requests[1].resolve({ok:true,json:async()=>fixture()[1]});await tick();assert.match(retry.node("reference-status").textContent,/HTTP 503/);
  retry.node("reference-retry").handlers.click();retry.reply(fixture(),2);await tick();assert.equal(retry.node("reference-retry").hidden,true);assert.equal(retry.node("rstar-source-rows").children.length,21);
  const files=["web/data/reference-stars/overview.json","web/data/source-presence/overview.json"];
  if(files.every(p=>fs.existsSync(p))){const live=harness(),data=files.map(p=>JSON.parse(fs.readFileSync(p,"utf8")));live.open();live.reply(data);await tick();assert.equal(live.node("reference-retry").hidden,true,live.node("reference-status").textContent);assert.equal(live.node("rstar-attempts").textContent,`${data[0].counts.statuses.fit_completed}/840`);assert.equal(live.node("presence-case-rows").children.length,6);}
  console.log("Reference/presence UI: lazy loading, fixed denominators, failed cases, tab keyboard, corruption refusals and retry passed");
}
run().catch(e=>{console.error(e);process.exitCode=1;});

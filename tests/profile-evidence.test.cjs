"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const source=fs.readFileSync("web/profile-evidence.js","utf8"),clone=x=>JSON.parse(JSON.stringify(x));
const tick=async()=>{for(let i=0;i<20;i++)await Promise.resolve();};
function harness(){
  const nodes=new Map(),requests=[];let i=0;
  const node=id=>{if(!nodes.has(id))nodes.set(id,{children:[],attrs:{},handlers:{},hidden:false,open:false,textContent:"",value:"",append(x){this.children.push(x);},replaceChildren(...x){this.children=x;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];delete this[k];},addEventListener(k,f){this.handlers[k]=f;}});return nodes.get(id);};
  vm.runInNewContext(source,{document:{getElementById:node,createElement:t=>node(t+i++)},fetch:url=>new Promise(resolve=>requests.push({url,resolve})),console});
  return {node,requests,open(){node("profile-landscape").open=true;node("profile-landscape").handlers.toggle();},reply(value,index=0){requests[index].resolve({ok:true,json:async()=>value});}};
}
async function run(){
  const report=JSON.parse(fs.readFileSync("web/data/profile-landscape/overview.json","utf8"));
  const h=harness();assert.equal(h.requests.length,0);h.open();h.open();assert.equal(h.requests.length,1);h.reply(report);await tick();
  assert.equal(h.node("profile-retry").hidden,true,h.node("profile-status").textContent);assert.equal(h.node("profile-count").textContent,"96/112");assert.equal(h.node("profile-unavailable").textContent,"16");assert.equal(h.node("profile-source").children.length,2);assert.equal(h.node("profile-numeric-rows").children.length,4);assert.match(h.node("profile-plot").src,/0214_3\.png$/);assert.match(h.node("profile-status").textContent,/gate hiệu chỉnh vẫn dừng/);
  const old=h.node("profile-plot").src;h.node("profile-source").value=h.node("profile-source").children[1].value;h.node("profile-source").handlers.change();assert.notEqual(h.node("profile-plot").src,old);h.node("profile-frame").value="2025W46_2A_0214_2";h.node("profile-frame").handlers.change();assert.match(h.node("profile-plot").src,/0214_2\.png$/);assert.equal(h.requests.length,1);h.open();assert.equal(h.requests.length,1);
  for(const mutate of [d=>d.promotion=true,d=>d.assessment_opened=true,d=>d.original_calibration_gate_passed=true,d=>d.counts.profile_completed=95,d=>d.sources.pop(),d=>d.sources[0].counts.profile_completed=7,d=>d.audit.counts.verified=95,d=>d.focus.pop(),d=>d.focus[0].arms.pop(),d=>d.focus[0].figure="https://untrusted.invalid/image.png",d=>d.focus[0].arms[0].record_checksum="bad",d=>d.focus[0].arms[0].valid_nodes=2,d=>d.focus[0].arms[0].saved_candidates.corrected[0].diagnostic.steps[0].gradient_infinity=-1]){
    const bad=harness(),data=clone(report);mutate(data);bad.open();bad.reply(data);await tick();assert.equal(bad.node("profile-retry").hidden,false);assert.equal(bad.node("profile-result").hidden,true);assert.equal(bad.node("profile-count").textContent,"—");assert.equal(bad.node("profile-numeric-rows").children.length,0);
  }
  const retry=harness();retry.open();retry.requests[0].resolve({ok:false,status:503});await tick();assert.match(retry.node("profile-status").textContent,/503/);retry.node("profile-retry").handlers.click();retry.reply(report,1);await tick();assert.equal(retry.node("profile-retry").hidden,true);retry.node("profile-plot").handlers.error();assert.equal(retry.node("profile-retry").hidden,false);assert.equal(retry.node("profile-plot").hidden,true);
  assert(h.requests.every(r=>r.url.endsWith("overview.json")),"large archive must not auto-load");
  console.log("Profile UI: lazy load, all denominators, source/frame switching, corruption refusal, no large auto-load and retry passed");
}
run().catch(e=>{console.error(e);process.exitCode=1;});

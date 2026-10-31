"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const source=fs.readFileSync("web/signal-evidence.js","utf8"),clone=x=>JSON.parse(JSON.stringify(x));
const tick=async()=>{for(let i=0;i<20;i++)await Promise.resolve();};
function harness(){
  const nodes=new Map(),requests=[];let i=0;
  const node=id=>{if(!nodes.has(id))nodes.set(id,{children:[],attrs:{},handlers:{},hidden:false,open:false,textContent:"",value:id==="signal-truth"?"gaussian":id==="signal-scene"?"modeled":"",append(x){this.children.push(x);},replaceChildren(...x){this.children=x;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];delete this[k];},addEventListener(k,f){this.handlers[k]=f;}});return nodes.get(id);};
  vm.runInNewContext(source,{document:{getElementById:node,createElement:t=>node(t+i++)},fetch:url=>new Promise(resolve=>requests.push({url,resolve})),console});
  return {node,requests,open(){node("signal-controls").open=true;node("signal-controls").handlers.toggle();},reply(value,index=0){requests[index].resolve({ok:true,json:async()=>value});}};
}
async function run(){
  const report=JSON.parse(fs.readFileSync("web/data/signal-controls/overview.json","utf8")),h=harness();
  assert.equal(h.requests.length,0);h.open();h.open();assert.equal(h.requests.length,1);h.reply(report);await tick();
  assert.equal(h.node("signal-retry").hidden,true,h.node("signal-status").textContent);assert.equal(h.node("signal-count").textContent,`${report.status_counts.fit_completed||0}/640`);
  assert.equal(h.node("signal-clean-count").textContent,`${report.noiseless_clean_gate.passed_count}/128`);assert.equal(h.node("signal-noisy-count").textContent,`${report.noisy_clean_gates.filter(x=>x.observed_sample_gate_passed).length}/16`);assert.equal(h.node("signal-preservation").textContent,`${report.noiseless_preservation_guard.passed_count}/64`);
  assert.equal(h.node("signal-noiseless-rows").children.length,32);assert.equal(h.node("signal-noisy-rows").children.length,8);assert.equal(h.node("signal-component-rows").children.length,8);assert.equal(h.node("signal-null-rows").children.length,8);
  assert.equal(h.node("signal-noisy-rows").children[0].children.length,9);assert.equal(h.node("signal-noisy-rows").children[0].children[8].textContent,"15 / 0 / 1 / 0");
  assert.match(h.node("signal-verdict").textContent,/252 ô dành riêng và 30 vùng mới vẫn chưa mở/);assert.equal(h.node("signal-plot").src,"data/signal-controls/scene-example.png");
  const old=h.node("signal-noiseless-rows").children.map(r=>r.children.map(c=>c.textContent).join("|")).join("\n");
  h.node("signal-truth").value="matched";h.node("signal-truth").handlers.change();assert.match(h.node("signal-truth-note").textContent,/kiểm tra phần mềm/);
  assert.notEqual(h.node("signal-noiseless-rows").children.map(r=>r.children.map(c=>c.textContent).join("|")).join("\n"),old);
  h.node("signal-scene").value="omitted";h.node("signal-scene").handlers.change();assert.equal(h.node("signal-noiseless-rows").children.length,32);assert.equal(h.node("signal-noisy-rows").children.length,8);assert(h.node("signal-noisy-rows").children.every(r=>r.children[7].textContent==="Stress · không có gate"));assert.match(h.node("signal-scene-note").textContent,/Cố tình bỏ sót/);assert.equal(h.requests.length,1);h.open();assert.equal(h.requests.length,1);
  for(const mutate of [
    d=>d.promotion=true,d=>d.assessment_opened=true,d=>d.old_assessment_blocked=false,d=>d.is_synthetic=false,d=>d.original_image_added=true,d=>d.protocol_commit="a".repeat(40),d=>d.prospective_fields_opened=1,
    d=>d.planned=639,d=>d.section_counts.noisy=383,d=>d.status_counts.fit_completed--,d=>d.source_ids.reverse(),d=>d.strata.pop(),d=>d.strata[1]=clone(d.strata[0]),d=>d.strata[0].planned=2,d=>d.strata[0].all_completed.n=42,d=>d.strata[0].all_completed.mean_flux_ratio_bias=null,
    d=>d.noiseless_clean_gate.passed_count=129,d=>d.noiseless_clean_gate.passed=!d.noiseless_clean_gate.passed,d=>d.noiseless_preservation_guard.planned_pairs=63,d=>d.noisy_clean_gates.pop(),d=>d.noisy_clean_gates[0].success=17,d=>d.noisy_clean_gates[0].exact_interval_95=[-1,1],
    d=>d.null_strata.pop(),d=>d.null_strata[0].truth="gaussian",d=>d.null_strata[0].signed_flux_jy.completed=9,d=>d.null_strata[0].signed_flux_jy.median=null,d=>d.fidelity_components[0].joint_passed=17,d=>d.paired.both_completed=321,d=>d.audit.counts.verified--,d=>d.audit.counts.audit_mismatch=1,d=>{d.audit.counts.verified--;d.audit.counts.input_checked_unavailable=1;},d=>d.figure.path="https://invalid.example/asset.png",d=>d.figure.record_checksums[0]="bad",d=>d.download.bytes=0
  ]){
    const bad=harness(),data=clone(report);mutate(data);bad.open();bad.reply(data);await tick();assert.equal(bad.node("signal-retry").hidden,false);assert.equal(bad.node("signal-result").hidden,true);assert.equal(bad.node("signal-count").textContent,"—");assert.equal(bad.node("signal-noiseless-rows").children.length,0);
  }
  const retry=harness();retry.open();retry.requests[0].resolve({ok:false,status:503});await tick();assert.match(retry.node("signal-status").textContent,/503/);retry.node("signal-retry").handlers.click();retry.reply(report,1);await tick();assert.equal(retry.node("signal-retry").hidden,true);retry.node("signal-plot").handlers.error();assert.equal(retry.node("signal-plot").hidden,true);assert.equal(retry.node("signal-retry").hidden,false);
  assert(h.requests.every(r=>r.url.endsWith("overview.json")),"no raw checkpoint archive auto-download");
  console.log("Signal UI: lazy load, all640 denominators, separate bias/support, selectors, null/stress semantics, corruption refusal and retry passed");
}
run().catch(e=>{console.error(e);process.exitCode=1;});

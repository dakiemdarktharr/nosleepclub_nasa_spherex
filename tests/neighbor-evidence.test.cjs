"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const source=fs.readFileSync("web/neighbor-evidence.js","utf8");
const variants=["plane_nearest_free","plane_nearest_nonnegative","plane_bilinear_free","plane_bilinear_nonnegative","quadratic_nearest_free","quadratic_nearest_nonnegative","quadratic_bilinear_free","quadratic_bilinear_nonnegative"];
const names=["plane_300uJy","plane_600uJy","quadratic_300uJy","quadratic_600uJy"];
const clone=x=>JSON.parse(JSON.stringify(x));
const content=node=>node.textContent+node.children.map(content).join(" ");
const tick=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
function metric(n,rms){return {n,rms_arcsec:n?rms:null,p90_arcsec:n?rms*1.4:null};}
function fixture(){
  return {schema:"neighbor-intervention-overview-1",schema_version:1,counts:{planned:288,recorded:288,fit_completed:280,failed:8},
    real:{configurations:["broad","strict"].map(config=>({configuration:config,frames_per_epoch:{before:config==="broad"?10:2,after:config==="broad"?10:2},numerical_supported_pairs:config==="broad"?7:0,max_pairwise_spread_arcsec:config==="broad"?.71:2.34,
      pairs:variants.map((variant,i)=>{const failed=config==="strict"&&i===7,unsupported=config==="strict"||i===7;return {variant,before_status:failed?"preparation_failed":"fit_completed",after_status:"fit_completed",before_reasons:failed?["synthetic unavailable"]:[],after_reasons:unsupported?["multiple_near_best_modes","irls_not_converged"]:[],east_north_arcsec:failed?null:[-3+i*.1,.2+i*.1],numerical_support_both:!unsupported,change_from_primary_control_arcsec:failed?null:i*.14};})}))},
    controls:{cases:names.map((name,index)=>({case:name,planned_draws:16,arms:variants.slice(0,2).map((variant,i)=>({variant,selections:{all_completed:metric(index===0&&i===0?15:16,1+index+i*.4),common_completed:metric(index===0?15:16,1+index+i*.4),common_numerically_supported:metric(index===0?3:4,.8+index+i*.5)}}))}))}};
}
function harness(){
  const nodes=new Map();let created=0;const requests=[];
  function node(id){
    if(!nodes.has(id))nodes.set(id,{id,value:id==="neighbor-configuration"?"strict":id==="neighbor-control-selection"?"common_completed":"",textContent:"",hidden:true,open:false,children:[],handlers:{},attrs:{},
      append(child){this.children.push(child);},replaceChildren(...x){this.children=x;},addEventListener(event,fn){this.handlers[event]=fn;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];}});
    return nodes.get(id);
  }
  vm.runInNewContext(source,{document:{getElementById:node,createElement:tag=>node(`${tag}-${created++}`)},console,fetch:url=>new Promise(resolve=>requests.push({url,resolve}))});
  return {node,requests,open(){node("neighbor-intervention").open=true;node("neighbor-intervention").handlers.toggle();},reply(value){requests.at(-1).resolve({ok:true,json:async()=>value});}};
}
async function cases(){
  const h=harness();assert.equal(h.requests.length,0);h.open();h.open();assert.equal(h.requests.length,1);
  assert.equal(h.requests[0].url,"data/neighbor-intervention/overview.json");
  h.requests[0].resolve({ok:false,status:503});await tick();
  assert.match(h.node("neighbor-status").textContent,/HTTP 503/);assert.equal(h.node("neighbor-retry").hidden,false);
  h.node("neighbor-retry").handlers.click();h.reply(fixture());await tick();
  assert.equal(h.node("neighbor-attempts").textContent,"280/288");assert.equal(h.node("neighbor-support").textContent,"0/8");
  assert.equal(h.node("neighbor-real-rows").children.length,8);assert.equal(h.node("neighbor-control-rows").children.length,4);
  assert.match(content(h.node("neighbor-real-rows")),/lỗi chuẩn bị/);
  assert.match(content(h.node("neighbor-real-rows")),/nhiều nghiệm cạnh tranh, trọng số chưa hội tụ/);
  assert.match(content(h.node("neighbor-control-rows")),/1,000 \/ 1,400/); // A worse constraint result must remain visible.
  assert.match(h.node("neighbor-status").textContent,/Chưa chọn mô hình/);
  assert.equal(h.node("neighbor-real-chart").src,"data/neighbor-intervention/real-sensitivity-strict.svg");
  h.node("neighbor-configuration").value="broad";h.node("neighbor-configuration").handlers.change();
  assert.equal(h.node("neighbor-support").textContent,"7/8");assert.equal(h.node("neighbor-real-rows").children.length,8);
  assert.equal(h.node("neighbor-chart-download").href,"data/neighbor-intervention/real-sensitivity-broad.svg");
  h.node("neighbor-control-selection").value="all_completed";h.node("neighbor-control-selection").handlers.change();
  assert.match(content(h.node("neighbor-control-rows").children[0]),/15\/16 16\/16/);
  h.node("neighbor-control-selection").value="common_numerically_supported";h.node("neighbor-control-selection").handlers.change();
  assert.match(content(h.node("neighbor-control-rows").children[0]),/3\/16 3\/16/);
  assert.equal(h.requests.length,2); // Full reports/controls remain explicit downloads.
  const empty=harness(),none=fixture();
  none.controls.cases[0].arms.forEach(a=>Object.keys(a.selections).forEach(k=>a.selections[k]=metric(0,0)));
  empty.open();empty.reply(none);await tick();assert.match(content(empty.node("neighbor-control-rows").children[0]),/0\/16 0\/16 — \/ —/);
  for(const tamper of [d=>d.real.configurations[0].pairs.pop(),d=>d.counts.failed=0,
    d=>d.real.configurations[0].pairs[0].before_status="fit_failed",d=>d.real.configurations[0].pairs[0].after_reasons.push("boundary"),
    d=>d.controls.cases.pop(),d=>d.controls.cases[0].arms[0].selections.common_completed.n=2,
    d=>d.controls.cases[0].arms[0].selections.common_completed.rms_arcsec=NaN]){
    const t=harness(),data=fixture();tamper(data);t.open();t.reply(data);await tick();
    assert.equal(t.node("neighbor-real-rows").children.length,0);assert.equal(t.node("neighbor-control-rows").children.length,0);
    assert.equal(t.node("neighbor-retry").hidden,false);assert.equal(t.node("neighbor-attempts").textContent,"—");
  }
  const publicPath="web/data/neighbor-intervention/overview.json";
  if(fs.existsSync(publicPath)){
    const published=JSON.parse(fs.readFileSync(publicPath,"utf8")),actual=harness();
    actual.open();actual.reply(published);await tick();
    assert.equal(actual.node("neighbor-retry").hidden,true);
    assert.equal(actual.node("neighbor-attempts").textContent,`${published.counts.fit_completed}/288`);
    assert.equal(actual.node("neighbor-real-rows").children.length,8);
    for(const selection of ["all_completed","common_completed","common_numerically_supported"]){
      actual.node("neighbor-control-selection").value=selection;actual.node("neighbor-control-selection").handlers.change();
      assert.equal(actual.node("neighbor-control-rows").children.length,4);
      published.controls.cases.forEach((row,index)=>{
        const first=row.arms.find(a=>a.variant===variants[0]).selections[selection];
        const second=row.arms.find(a=>a.variant===variants[1]).selections[selection];
        const rendered=content(actual.node("neighbor-control-rows").children[index]);
        assert.ok(rendered.includes(`${first.n}/16 ${second.n}/16`));
        assert.ok(!rendered.includes("NaN"));
      });
    }
  }
  console.log("Neighbor evidence: lazy loading, all refusals, paired denominators, worse outcomes and retries passed");
}
const done=cases();if(typeof process!=="undefined")done.catch(e=>{console.error(e);process.exitCode=1;});

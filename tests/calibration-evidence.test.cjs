"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
const source=fs.readFileSync("web/calibration-evidence.js","utf8"),clone=x=>JSON.parse(JSON.stringify(x));
const text=n=>n.textContent+n.children.map(text).join(" "),tick=async()=>{for(let i=0;i<30;i++)await Promise.resolve();};
function fixture(){
  const base={promotion:false,protocol_commit:"a".repeat(40),design_sha256:"b".repeat(64),download:{bytes:1000000,sha256:"c".repeat(64)}};
  const learn={...clone(base),schema:"shape-calibration-overview-1",planned:168,counts:{information_available:145,baseline_unavailable:22,baseline_numerical_refusal:1},status:"conditional_candidate",audit:{saved_cells:145},maximum_source_fraction:.129,
    sources:Array.from({length:14},(_,i)=>({source_id:String(i),planned:12,information_available:i<12?12:i===12?1:0})),coefficients:[-.008,.0007,.0008],conditional_standard_errors:[.005,.0008,.0008],units:["pix2","pix3","pix3"],shape_checks:{planned:145,passed:145}};
  const point={...clone(base),schema:"shape-point-overview-1",planned:420,recorded:420,deferred:0,counts:{fit_completed:359,preparation_failed:61},baseline_paired_rms_arcsec:.45,
    calibration_gate:{planned:168,counts:{fit_completed:146,preparation_failed:22},assessment_allowed:true,reasons:[],comparison_count:145,failure_count:0,failure_cases:[],linearization_error_p90_common_px:.004,linearization_error_max_common_px:.01},
    primary:{planned:56,common_completed_pairs:48,supported_source_count:6,new_numerical_refusals:0,promotion:false,
      source_rows:Array.from({length:7},(_,i)=>({source_id:String(1000+i),planned:8,pair_count:i<6?8:0,pair_count_by_season:{before:i<6?4:0,after:i<6?4:0},support_gate_met:i<6,baseline_mean_radial_arcsec:i<6?.4:null,point_mean_radial_arcsec:i<6?.35:null})),
      point_status_counts:{fit_completed:48,preparation_failed:8,missing:0},baseline_status_counts:{fit_completed:48,preparation_failed:8,missing:0},equal_source_baseline_mean_radial_arcsec:.4,equal_source_point_mean_radial_arcsec:.35,equal_source_mean_radial_improvement_arcsec:.05,pooled_baseline_p90_radial_arcsec:.6,pooled_point_p90_radial_arcsec:.55,pooled_p90_increase_arcsec:-.05,paired_point_rms_radial_arcsec:.4,
      gates:{all_planned_records_available:true,source_season_support:true,no_new_numerical_refusals:true,equal_source_improvement:true,pooled_p90_increase:true,paired_new_rms:true,paired_new_p90:true},developmental_gates_passed:true}};
  const cov={...clone(base),schema:"reference-covariance-overview-1",planned:420,counts:{influence_available:357,baseline_unavailable:61,baseline_numerical_refusal:2},status:"descriptive_complete",heldout_joint:{chi2:407.43,dof:238},heldout_sources:Array.from({length:7},(_,i)=>({source_id:String(1000+i),available:i<5?20:i===5?19:0,dof:i<5?40:i===5?38:0,chi2:i<6?50:null}))};
  return [learn,point,cov];
}
function harness(){
  const nodes=new Map(),requests=[];let serial=0;
  const node=id=>{if(!nodes.has(id))nodes.set(id,{textContent:"",children:[],attrs:{},handlers:{},open:false,hidden:false,append(x){this.children.push(x);},replaceChildren(...x){this.children=x;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},addEventListener(k,f){this.handlers[k]=f;}});return nodes.get(id);};
  vm.runInNewContext(source,{document:{getElementById:node,createElement:t=>node(t+serial++)},fetch:url=>new Promise(resolve=>requests.push({url,resolve})),console});
  return {node,requests,open(){node("shape-validation").open=true;node("shape-validation").handlers.toggle();},reply(data,offset=0){data.forEach((v,i)=>requests[offset+i].resolve({ok:true,json:async()=>v}));}};
}
async function run(){
  const h=harness();assert.equal(h.requests.length,0);h.open();h.open();assert.equal(h.requests.length,3);h.reply(fixture());await tick();
  assert.equal(h.node("shape-retry").hidden,true,h.node("shape-load-status").textContent);assert.equal(h.node("shape-source-rows").children.length,7);assert.equal(h.node("shared-source-rows").children.length,7);
  assert.match(text(h.node("shape-source-rows")),/0\/8/);assert.match(text(h.node("shared-source-rows")),/0\/20/);assert.equal(h.node("shape-learn-count").textContent,"145/168");
  assert.match(h.node("shape-verdict").textContent,/tập đã mở/);assert.match(h.node("shared-reference-note").textContent,/kiểm định độ phủ riêng/);h.open();assert.equal(h.requests.length,3);assert(h.requests.every(x=>x.url.endsWith("overview.json")));
  for(const mutate of [d=>d[0].promotion=true,d=>d[0].counts.information_available=144,d=>d[0].maximum_source_fraction=.4,d=>d[0].sources.pop(),d=>d[0].conditional_standard_errors[0]=-1,
    d=>d[1].recorded=419,d=>d[1].primary.source_rows[0].pair_count=7,d=>d[1].primary.gates.equal_source_improvement=false,d=>d[1].primary.equal_source_mean_radial_improvement_arcsec=.001,d=>d[1].calibration_gate.linearization_error_max_common_px=.1,
    d=>d[2].heldout_sources.pop(),d=>d[2].heldout_sources[6].chi2=0,d=>d[2].heldout_joint.dof=240,d=>d[2].download.sha256="bad"]){
    const bad=harness(),data=clone(fixture());mutate(data);bad.open();bad.reply(data);await tick();assert.equal(bad.node("shape-retry").hidden,false);assert.equal(bad.node("shape-source-rows").children.length,0);assert.equal(bad.node("shape-learn-count").textContent,"—");
  }
  const blocked=fixture(),p=blocked[1].primary;blocked[1].recorded=168;blocked[1].deferred=252;blocked[1].counts={fit_completed:146,preparation_failed:22};Object.assign(blocked[1].calibration_gate,{assessment_allowed:false,comparison_count:144,failure_count:1,failure_cases:[{key:["1000","frame"],baseline_near_best_count:1,corrected_near_best_count:2,corrected_mode_maximum_separation_arcsec:1.} ]});
  Object.assign(p,{common_completed_pairs:0,supported_source_count:0,new_numerical_refusals:48,point_status_counts:{missing:56},developmental_gates_passed:false});
  for(const k of ["equal_source_baseline_mean_radial_arcsec","equal_source_point_mean_radial_arcsec","equal_source_mean_radial_improvement_arcsec","pooled_baseline_p90_radial_arcsec","pooled_point_p90_radial_arcsec","pooled_p90_increase_arcsec","paired_point_rms_radial_arcsec"])p[k]=null;
  for(const s of p.source_rows)Object.assign(s,{pair_count:0,pair_count_by_season:{before:0,after:0},support_gate_met:false,baseline_mean_radial_arcsec:null,point_mean_radial_arcsec:null});for(const k of Object.keys(p.gates))p.gates[k]=false;
  const b=harness();b.open();b.reply(blocked);await tick();assert.equal(b.node("shape-retry").hidden,true,b.node("shape-load-status").textContent);assert.match(b.node("shape-verdict").textContent,/dừng ở calibration/);assert.match(b.node("shape-primary-note").textContent,/chưa được đo lại/);
  const retry=harness();retry.open();retry.requests[0].resolve({ok:false,status:503});retry.requests[1].resolve({ok:true,json:async()=>fixture()[1]});retry.requests[2].resolve({ok:true,json:async()=>fixture()[2]});await tick();assert.match(retry.node("shape-load-status").textContent,/HTTP 503/);retry.node("shape-retry").handlers.click();retry.reply(fixture(),3);await tick();assert.equal(retry.node("shape-retry").hidden,true);
  const paths=["web/data/shape-correction/overview.json","web/data/shape-point-check/overview.json","web/data/reference-covariance/overview.json"];
  if(paths.every(p=>fs.existsSync(p))){const live=harness();live.open();live.reply(paths.map(p=>JSON.parse(fs.readFileSync(p,"utf8"))));await tick();assert.equal(live.node("shape-retry").hidden,true,live.node("shape-load-status").textContent);}
  console.log("Calibration UI: lazy reports, complete denominators, declared gates, deferred outcomes, corruption refusal and retry passed");
}
run().catch(e=>{console.error(e);process.exitCode=1;});

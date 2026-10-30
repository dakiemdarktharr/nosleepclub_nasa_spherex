"use strict";
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const source=fs.readFileSync("web/linked-evidence.js","utf8");
const real=JSON.parse(fs.readFileSync("web/data/linked-flux/overview.json","utf8"));
const clone=value=>JSON.parse(JSON.stringify(value));
const text=node=>node.textContent+node.children.map(text).join(" ");
const settle=async()=>{for(let i=0;i<12;i++)await Promise.resolve();};
function harness(){
  const nodes=new Map();
  function node(id){
    if(!nodes.has(id))nodes.set(id,{id,value:id==="linked-configuration"?"strict":"",textContent:"",hidden:true,children:[],handlers:{},attributes:{},
      append(child){this.children.push(child);},replaceChildren(...children){this.children=children;},
      setAttribute(key,value){this.attributes[key]=value;},removeAttribute(key){delete this.attributes[key];},
      addEventListener(event,fn){this.handlers[event]=fn;}});
    return nodes.get(id);
  }
  let count=0;const requests=[];
  const document={getElementById:node,createElement:tag=>node(`created-${++count}-${tag}`)};
  vm.runInNewContext(source,{document,console,fetch:url=>new Promise(resolve=>requests.push({url,resolve}))});
  return {node,requests,reply(value,index=requests.length-1){requests[index].resolve({ok:true,json:async()=>value});}};
}
async function cases(){
  const h=harness();
  assert.equal(h.requests.length,1);
  assert.equal(h.requests[0].url,"data/linked-flux/overview.json");
  assert.equal(h.node("linked-flux").attributes["aria-busy"],"true");
  h.node("linked-retry").handlers.click();assert.equal(h.requests.length,1);
  h.requests[0].resolve({ok:false,status:503});await settle();
  assert.equal(h.node("linked-retry").hidden,false);
  assert.match(h.node("linked-verdict").textContent,/HTTP 503/);
  assert.equal(h.node("linked-flux").attributes["aria-busy"],undefined);
  h.node("linked-retry").handlers.click();h.reply(clone(real));await settle();
  assert.equal(h.node("linked-rows").children.length,7);
  assert.match(h.node("linked-verdict").textContent,/0\/7/);
  assert.match(h.node("linked-verdict").textContent,/7\/7 nhánh có nghiệm cạnh tranh/);
  assert.equal(h.node("linked-attempts").textContent,"28/28");
  assert.equal(h.node("linked-change").textContent,"2,280″");
  assert.equal(h.node("linked-spread").textContent,"2,281″");
  assert.equal(h.node("linked-download-chart").href,"data/linked-flux/sensitivity-strict.svg");
  assert.ok(h.node("linked-rows").children.every(row=>text(row).includes("sau: 2 nghiệm")));
  assert.equal(h.node("linked-mode-rows").children.length,2);
  assert.match(text(h.node("linked-mode-rows")),/-0,516770/);
  assert.equal(h.requests.length,2); // The 4.8MB report and 214KB diagnostic are explicit downloads.
  for(const config of ["broad","strict","broad"]){
    h.node("linked-configuration").value=config;h.node("linked-configuration").handlers.change();
  }
  assert.equal(h.node("linked-rows").children.length,7);
  assert.equal(h.node("linked-change").textContent,"0,116″");
  assert.equal(h.node("linked-spread").textContent,"0,556″");
  assert.match(h.node("linked-verdict").textContent,/7\/7/);
  assert.match(h.node("linked-verdict").textContent,/chưa có bằng chứng giảm bias/);
  assert.equal(h.node("linked-chart").src,"data/linked-flux/sensitivity-broad.svg");
  assert.ok(h.node("linked-rows").children.every(row=>text(row).includes("2/2 · số học")));
  const combined=harness(),several=clone(real);
  const ambiguous=several.pairs.find(x=>x.configuration==="strict"&&x.variant==="independent");
  ambiguous.epoch_status_and_screening.after.reasons.push("irls_not_converged","boundary");
  combined.reply(several);await settle();
  assert.match(text(combined.node("linked-rows")),/2 nghiệm, IRLS chưa hội tụ, chạm biên/);
  const f=harness(),failed=clone(real);
  failed.counts.fit_completed=27;failed.counts.failures=1;
  const row=failed.pairs.find(x=>x.configuration==="strict"&&x.variant==="shared_r7_68_a0");
  row.successful_epoch_fits=1;row.east_north_arcsec=null;delete row.change_from_independent_arcsec;
  Object.assign(row.epoch_status_and_screening.after,{status:"preparation_failed",solver_screening_passed:false,reasons:[],near_best_mode_count:null,failure:"synthetic preparation failure"});
  f.reply(failed);await settle();
  assert.equal(f.node("linked-rows").children.length,7);
  assert.equal(f.node("linked-attempts").textContent,"27/28");
  assert.match(text(f.node("linked-rows")),/synthetic preparation failure/);
  for(const tamper of [d=>d.pairs.pop(),d=>d.pairs[0].variant="unknown",d=>d.pairs[0].east_north_arcsec[0]=Infinity,d=>d.pairs[0].solver_screening_both=false,
    d=>{d.pairs[0].epoch_status_and_screening.after.status="fit_failed";d.pairs[0].successful_epoch_fits=1;d.pairs[0].east_north_arcsec=null;},
    d=>d.pairs[0].epoch_status_and_screening.after.reasons.push("boundary")]){
    const x=harness(),value=clone(real);tamper(value);x.reply(value);await settle();
    assert.equal(x.node("linked-rows").children.length,0);
    assert.equal(x.node("linked-retry").hidden,false);
    assert.match(x.node("linked-verdict").textContent,/chưa tương thích/);
  }
  console.log("Linked evidence: all denominators, refusals, model switches, failures and retries passed");
}
const done=cases();
if(typeof process!=="undefined")done.catch(error=>{console.error(error);process.exitCode=1;});

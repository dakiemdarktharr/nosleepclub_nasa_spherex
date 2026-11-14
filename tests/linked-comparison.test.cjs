"use strict";
const assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm");
class Element {
  constructor(tag="div") {this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.attributes={};this.handlers={};this.hidden=false;this.value="";this.textContent="";this.style={setProperty(k,v){this[k]=v;}};const classes=new Set();this.classList={add(...v){v.forEach(x=>classes.add(x));},remove(v){classes.delete(v);},toggle(v,on){if(on)classes.add(v);else classes.delete(v);}};}
  setAttribute(k,v){this.attributes[k]=v;}
  getAttribute(k){return this.attributes[k]??null;}
  removeAttribute(k){delete this.attributes[k];}
  append(...nodes){this.children.push(...nodes);}
  add(node){this.append(node);}
  replaceChildren(...nodes){this.children=[...nodes];}
  insertBefore(node,before){this.children.splice(this.children.indexOf(before),0,node);}
  addEventListener(type,fn){(this.handlers[type]??=[]).push(fn);}
  fire(type,event={}){for(const fn of this.handlers[type]||[])fn({target:this,currentTarget:this,preventDefault(){},...event});}
  descendants(){return this.children.flatMap(c=>[c,...(c.descendants?.()||[])]);}
  querySelectorAll(selector){return this.descendants().filter(n=>selector==="[data-linked-copy]"?n.dataset?.linkedCopy:selector.startsWith("#")?n.id===selector.slice(1):selector.startsWith(".")?n.className?.split(" ").includes(selector.slice(1)):n.tagName?.toLowerCase()===selector);}
  querySelector(selector){return this.querySelectorAll(selector)[0];}
}
const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve();};
const row=(id,det=6)=>({obs_id:id,detector:det,t_min_mjd:60000,access_url:`https://irsa.ipac.caltech.edu/${det}/${id}.fits`});
const info=r=>({row:r,src:`blob:${r.detector}/${r.obs_id}`,headers:{"x-frame-release":"dr1","x-frame-time-system":"UTC","x-frame-mjd-obs":"60000","x-frame-center-wavelength-um":"4.73","x-frame-center-bandwidth-um":"0.03","x-frame-center-spectral-source":"WCS-WAVE"}});
function harness(viewState=null){
  const root=new Element(),timeline=new Element(),viewport=new Element(),img=new Element("img"),player=new Element("button"),retry=new Element("button");
  timeline.id="explorer-display";viewport.className="explorer-image-wrap";viewport.append(img);timeline.append(viewport);player.id="explorer-timeline";retry.id="explorer-retry";root.append(timeline,player,retry);
  const document={documentElement:{lang:"en"},createElement:tag=>new Element(tag),addEventListener(){}};
  const window={addEventListener(){}};
  const calls=[],searches=[],states=[],pairs=[];
  const context={document,window,AbortController,URL:{revokeObjectURL(){}},Intl,Option:class extends Element {constructor(label,value){super("option");this.textContent=label;this.value=value;}},location:{hash:"#compare-step"}};
  vm.runInNewContext(fs.readFileSync("web/linked-comparison.js","utf8"),context);
  let api,snapshot;
  api=window.SkyLinkedComparison.mount({root,bands:[[.75,1.09],[1.1,1.62],[1.63,2.41],[2.42,3.82],[3.83,4.41],[4.42,5]],timeLabel:(v,system)=>system||`MJD ${v}`,stopTimeline(){},
    loadFrame:(row,signal)=>new Promise((resolve,reject)=>calls.push({row,signal,resolve,reject})),
    loadObservations:(det,signal)=>new Promise((resolve,reject)=>searches.push({det,signal,resolve,reject})),
    onPairChange:(pair,frames)=>{pairs.push({pair,frames});if(snapshot)api.update(snapshot);},onViewStateChange:s=>states.push(s)});
  const rows=[row("A"),row("B"),row("C")];
  snapshot={query:{det:6,view:"compare",viewState},rows,images:new Map(),dirty:false,busy:false,loading:false};
  api.update(snapshot);
  return {root,calls,searches,states,pairs,api,snapshot,select:id=>root.querySelector("#"+id),panes:()=>root.descendants().filter(e=>e.className==="linked-pane")};
}
async function main(){
  const h=harness();
  assert.equal(h.calls.length,2,"A/B boots without requiring a timeline or first successful image");
  assert.deepEqual(h.calls.map(c=>c.row.obs_id),["A","C"]);
  h.calls[0].reject(new Error("Source unavailable"));h.calls[1].resolve(info(h.calls[1].row));await flush();
  const [a,b]=h.panes();
  assert.equal(b.querySelector("img").hidden,false,"the successful side remains visible");
  assert.equal(a.querySelector("img").hidden,true);
  const retry=a.descendants().find(n=>n.dataset?.linkedCopy==="retry");
  assert.equal(retry.hidden,false);retry.fire("click");
  assert.equal(h.calls.length,3,"retry fetches only the failed pane");
  h.calls[2].resolve(info(h.calls[2].row));await flush();
  assert.equal(h.pairs.at(-1).pair.length,2);
  const pairState=h.states.at(-1);
  assert.equal(pairState.a.obs,"A");assert.equal(pairState.b.obs,"C");
  const plus=h.root.descendants().find(n=>n.dataset?.linkedCopy==="zoomIn");plus.fire("click");
  assert.equal(h.states.at(-1).camera.zoom,1.35);
  const restored=harness({a:{obs:"keepA",det:4},b:{obs:"keepB",det:5},camera:{zoom:2,x:.25,y:-.2}});
  assert.equal(restored.calls.length,0,"restore does not load unrelated default frames");
  assert.deepEqual(restored.searches.map(r=>r.det),[4,5]);
  assert.equal(restored.states.at(-1).a.obs,"keepA","retain the requested pair while discovery is in flight");
  assert.equal(restored.states.at(-1).b.obs,"keepB");
  restored.searches[0].resolve({rows:[row("other",4),row("keepA",4)],provenance:{}});
  restored.searches[1].resolve({rows:[row("keepB",5),row("other",5)],provenance:{}});await flush();
  assert.deepEqual(restored.calls.map(r=>[r.row.obs_id,r.row.detector]),[["keepA",4],["keepB",5]]);
  for(const call of restored.calls)call.resolve(info(call.row));await flush();
  assert.equal(restored.states.at(-1).camera.zoom,2);assert.equal(restored.states.at(-1).camera.x,.25);
  assert.equal(restored.pairs.at(-1).pair[0].row.detector,4);assert.equal(restored.pairs.at(-1).pair[1].row.detector,5);
  const absent=harness({a:{obs:"gone",det:4}});
  absent.searches[0].resolve({rows:[row("other",4)]});await flush();
  assert.equal(absent.calls.some(c=>c.row.obs_id==="other"),false,"missing restored observation is never silently substituted");
  assert.match(absent.panes()[0].descendants().map(n=>n.textContent).join(" "),/linked observation is not in/);
  assert.equal(absent.states.at(-1).a.obs,"gone","missing linked observation remains explicit on refresh");
  console.log("Linked comparison: independent A/B boot, partial failure/retry, exact cross-band restoration, camera and missing observation handling passed");
}
main().catch(error=>{console.error(error);process.exitCode=1;});

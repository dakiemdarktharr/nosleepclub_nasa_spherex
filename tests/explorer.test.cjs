"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

// Browser-like primitives stay local to this test; no real network or browser is used.
class Params {
  constructor(input="") {
    this.items = [];
    if(typeof input === "string") {
      for(const part of input.replace(/^\?/, "").split("&")) if(part) {
        const [key,...rest]=part.split("=");
        this.items.push([decodeURIComponent(key.replace(/\+/g," ")),decodeURIComponent(rest.join("=").replace(/\+/g," "))]);
      }
    } else for(const [key,value] of Object.entries(input))this.items.push([key,String(value)]);
  }
  get(key) {return this.items.find(item=>item[0]===key)?.[1]??null;}
  has(key) {return this.items.some(item=>item[0]===key);}
  set(key,value) {this.delete(key);this.items.push([key,String(value)]);}
  delete(key) {this.items=this.items.filter(item=>item[0]!==key);}
  keys() {return this.items.map(item=>item[0])[Symbol.iterator]();}
  toString() {return this.items.map(([k,v])=>`${encodeURIComponent(k)}=${encodeURIComponent(v)}`).join("&");}
}
class URLFake {
  constructor(value) {
    const [withoutHash,hash=""]=value.split("#"), [base,query=""]=withoutHash.split("?");
    this.base=base;this.hash=hash?`#${hash}`:"";this.searchParams=new Params(query);
  }
  get href(){const query=this.searchParams.toString();return this.base+(query?`?${query}`:"")+this.hash;}
  static createObjectURL(blob){return `blob:${blob.id}`;}
  static revokeObjectURL(){}
}
class AbortFake {
  constructor(){this.signal={aborted:false};}
  abort(){this.signal.aborted=true;}
}
class DOMError extends Error {constructor(message,name){super(message);this.name=name;}}

function harness(options={}) {
  const elements=new Map(),calls=[],timers=new Map(),blobs=[],events=[]; let nextTimer=0;
  const element=id=>{
    if(!elements.has(id))elements.set(id,{
      id,value:"",textContent:"",hidden:false,disabled:false,href:"",src:"",children:[],handlers:{},
      classList:{toggle(){}}, setAttribute(){}, removeAttribute(name){if(name==="href")this.href="";}, replaceChildren(){this.children=[];},
      append(...nodes){this.children.push(...nodes);},
      addEventListener(type,fn){this.handlers[type]=fn;},
      fire(type){return this.handlers[type]?.({preventDefault(){}});}
    });
    return elements.get(id);
  };
  const document={getElementById:element,createElement:()=>({children:[],handlers:{},setAttribute(){},
    append(...items){this.children.push(...items);},addEventListener(type,fn){this.handlers[type]=fn;},click(){}}),
    addEventListener(){},dispatchEvent(event){events.push(event);},hidden:false};
  const fetch=(url,options)=>new Promise((resolve,reject)=>{
    calls.push({url,options,params:new Params(url.split("?")[1]||""),resolve,reject});
  });
  const context={window:{SkyDrafts:options.drafts},document,fetch,URL:URLFake,URLSearchParams:Params,AbortController:AbortFake,DOMException:DOMError,
    location:{href:"https://demo.example/"+(options.search||"")+"#explore",search:options.search||""},history:{replaceState(a,b,url){context.shared=String(url.href||url);}},
    setInterval:fn=>{const id=++nextTimer;timers.set(id,fn);return id;},clearInterval:id=>timers.delete(id),
    setTimeout:fn=>{fn();return 1;},Blob:class {constructor(parts){this.id="export";blobs.push(parts);}},
    CustomEvent:class {constructor(type,options={}){this.type=type;this.detail=options.detail;}}};
  for(const [id,value] of Object.entries({"explorer-ra":"350","explorer-dec":"35","explorer-fov":"0.06",
    "explorer-detector":"6","explorer-release":"qr2","explorer-from":"","explorer-to":""}))element(id).value=value;
  vm.runInNewContext(fs.readFileSync("web/explorer.js","utf8"),context);
  return {element,calls,timers,blobs,events,context,api:context.window.SkyExplorer};
}
const flush=async()=>{for(let i=0;i<16;i++)await Promise.resolve();};
const find=(h,kind)=>h.calls.filter(call=>call.url.startsWith(`/api/${kind}?`));
function observations(call, ids) {
  const rows=ids.map((id,i)=>({access_url:`https://irsa.ipac.caltech.edu/${id}.fits`,
    t_min_mjd:60000+i,detector:6,obs_id:id}));
  call.resolve({ok:true,json:async()=>({observations:rows,provenance:{query_url:"https://irsa.ipac.caltech.edu/SIA"},truncated:false})});
}
function frame(call, id, options={}) {
  const values={"content-type":"image/png","x-frame-contrast-low":String(options.low??0.5),
    "x-frame-contrast-high":String(options.high??2.5),"x-frame-valid-pixels":"20",
    "x-frame-masked-pixels":"3","x-frame-missing-pixels":"2",
    "x-frame-mask-policy":options.policy??"source-only-allowlist-v2",
    "x-frame-cutout-url":options.cutout??`https://irsa.ipac.caltech.edu/${id}.fits?center=350,35&size=0.1`,
    "x-frame-cutout-sha256":"a".repeat(64)};
  const headers={get:key=>values[key.toLowerCase()]??null,*[Symbol.iterator](){yield* Object.entries(values);}};
  call.resolve({ok:true,headers,blob:async()=>({id})});
}
async function begin(h, ids) {
  const submit=h.element("explorer-form").fire("submit"); await flush();
  observations(find(h,"observations").at(-1),ids);await flush();return {submit};
}

async function coordinateCases() {
  const h=harness();
  assert.equal(h.element("explorer-preset").value,"custom");
  h.element("explorer-preset").value="barnard";h.element("explorer-preset").fire("change");
  assert.equal(h.element("explorer-ra").value,"269.44626688537255");
  h.element("explorer-ra").value="350";h.element("explorer-ra").fire("input");
  assert.equal(h.element("explorer-preset").value,"custom");
  h.element("explorer-ra").value="360";
  await h.element("explorer-form").fire("submit");
  assert.equal(h.calls.length,0);
  assert.equal(h.element("explorer-status").textContent.includes("RA"),true);
  h.element("explorer-ra").value="12:30:00";
  h.element("explorer-dec").value="-10:30:00";
  const submit=h.element("explorer-form").fire("submit");await flush();
  const request=find(h,"observations")[0];
  assert.equal(request.params.get("ra"),"187.5");
  assert.equal(request.params.get("dec"),"-10.5");
  observations(request,[]);await submit;
  h.element("explorer-ra").value="-00:01:00";
  await h.element("explorer-form").fire("submit");
  assert.equal(h.calls.length,1);
  for(const [ra,dec] of [["24:00:00","0"],["0","-90:00:01"],["9".repeat(400)+":00:00","0"],["Infinity","0"]]) {
    h.element("explorer-ra").value=ra;h.element("explorer-dec").value=dec;
    await h.element("explorer-form").fire("submit");
    assert.equal(h.calls.length,1);
  }
  h.element("explorer-ra").value="359d30m00s";
  h.element("explorer-dec").value="-00:30:00";
  const degrees=h.element("explorer-form").fire("submit");await flush();
  const second=find(h,"observations")[1];
  assert.equal(second.params.get("ra"),"359.5");assert.equal(second.params.get("dec"),"-0.5");
  observations(second,[]);await degrees;
}

async function serializedContrastAndBlink() {
  const h=harness();const {submit}=await begin(h,["A","B"]);
  assert.equal(find(h,"frame").length,1);
  h.element("explorer-current").value="1";
  const showingB=h.element("explorer-current").fire("change");await flush();
  assert.equal(find(h,"frame").length,1);
  frame(find(h,"frame")[0],"A",{low:0.5,high:2.5});await flush();
  const frameB=find(h,"frame")[1];
  assert.equal(frameB.params.get("low"),"0.5");assert.equal(frameB.params.get("high"),"2.5");
  const cutout="https://irsa.ipac.caltech.edu/B.fits?center=350%2C35&size=0.123";
  frame(frameB,"B",{cutout});await showingB;await submit;
  assert.equal(h.element("explorer-image").src,"blob:B");
  assert.equal(h.element("explorer-download-fits").href,cutout);
  h.element("explorer-pin").fire("click");
  h.element("explorer-current").value="0";await h.element("explorer-current").fire("change");
  assert.equal(h.element("explorer-image").src,"blob:A");
  h.element("explorer-play").fire("click");
  assert.equal(h.element("explorer-image").src,"blob:B");
  assert.equal(h.timers.size,1);
  h.element("explorer-play").fire("click");
  assert.equal(h.timers.size,0);
  h.element("explorer-pin").fire("click");
  assert.equal(h.element("explorer-reference").textContent.includes("Ảnh A: 1"),true);
}

async function workflowPairSurvivesBlinkAndInvalidatesOnEdit(){
  const h=harness(),{submit}=await begin(h,["A","B"]);frame(find(h,"frame")[0],"A");await submit;
  assert.equal(h.api.context().ready,true);assert.equal(h.api.context().paired,false);
  h.element("explorer-pin").fire("click");h.element("explorer-current").value="1";
  const b=h.element("explorer-current").fire("change");await flush();
  assert.equal(h.api.context().ready,false);assert.equal(h.element("explorer-pin").disabled,true);assert.equal(h.element("explorer-export").disabled,true);
  frame(find(h,"frame")[1],"B");await b;assert.equal(h.api.context().paired,true);
  h.element("explorer-play").fire("click");assert.equal(h.element("explorer-image").src,"blob:A");
  assert.equal(h.api.context().paired,true);assert.equal(h.api.context().current.obs_id,"B");
  h.api.pause();assert.equal(h.timers.size,0);assert.equal(h.element("explorer-image").src,"blob:B");assert.equal(h.api.context().paired,true);
  h.element("explorer-note").value="Chỉ là quan sát ảnh.";h.element("explorer-export").fire("click");
  const bundle=JSON.parse(h.blobs.at(-1)[0]);assert.equal(bundle.selected_pair.reference.obs_id,"A");assert.equal(bundle.selected_pair.current.obs_id,"B");assert.equal(bundle.review_note,"Chỉ là quan sát ảnh.");
  const count=h.blobs.length;h.element("explorer-form").fire("input");assert.equal(h.api.context().dirty,true);assert.equal(h.api.context().ready,false);
  h.element("explorer-export").fire("click");assert.equal(h.blobs.length,count);
  assert(h.events.some(e=>e.type==="explorer:state"&&e.detail.kind==="frame"));assert(h.calls.every(c=>!c.url.startsWith("/api/reviews")));
}

async function notesStayWithTheirQueryAndPair(){
  const h=harness();
  async function query(ra){
    h.element("explorer-ra").value=String(ra);const task=h.element("explorer-form").fire("submit");await flush();
    observations(find(h,"observations").at(-1),["A","B","C"]);await flush();frame(find(h,"frame").at(-1),"A");await task;
    h.element("explorer-pin").fire("click");
  }
  async function choose(index,id){const before=find(h,"frame").length;h.element("explorer-current").value=String(index);const task=h.element("explorer-current").fire("change");await flush();if(find(h,"frame").length>before)frame(find(h,"frame").at(-1),id);await task;}
  await query(350);await choose(1,"B");h.element("explorer-note").value="note for 350/A-B";h.element("explorer-note").fire("input");
  await choose(2,"C");assert.equal(h.element("explorer-note").value,"");await choose(1,"B");assert.equal(h.element("explorer-note").value,"note for 350/A-B");
  await query(120);await choose(1,"B");assert.equal(h.element("explorer-note").value,"");h.element("explorer-note").value="note for 120/A-B";h.element("explorer-note").fire("input");
  await query(350);await choose(1,"B");assert.equal(h.element("explorer-note").value,"note for 350/A-B");
  h.element("explorer-export").fire("click");const bundle=JSON.parse(h.blobs.at(-1)[0]);assert.equal(bundle.query.ra,350);assert.equal(bundle.review_note,"note for 350/A-B");
}

async function staleFailureCannotHideCachedFrame() {
  const h=harness();const {submit}=await begin(h,["X","B","A"]);
  frame(find(h,"frame")[0],"X");await submit;
  h.element("explorer-current").value="1";const b=h.element("explorer-current").fire("change");await flush();
  frame(find(h,"frame")[1],"B");await b;
  h.element("explorer-current").value="2";const a=h.element("explorer-current").fire("change");await flush();
  assert.equal(find(h,"frame").length,3);
  h.element("explorer-current").value="1";await h.element("explorer-current").fire("change");
  const status=h.element("explorer-status").textContent;
  find(h,"frame")[2].reject(new Error("offline old request"));await a;await flush();
  assert.equal(h.element("explorer-image").src,"blob:B");
  assert.equal(h.element("explorer-image").hidden,false);
  assert.equal(h.element("explorer-status").textContent,status);
}

async function refusesInconsistentContrast() {
  const h=harness();const {submit}=await begin(h,["A","B"]);
  frame(find(h,"frame")[0],"A",{low:0.5,high:2.5});await submit;
  h.element("explorer-current").value="1";
  const b=h.element("explorer-current").fire("change");await flush();
  frame(find(h,"frame")[1],"B",{low:0.5,high:2.6});await b;
  assert.equal(h.element("explorer-image").hidden,true);
  assert.equal(h.element("explorer-status").textContent.includes("không cùng thang tương phản"),true);
}

async function changedSearchRejectsOldResult() {
  const h=harness();const {submit:old}=await begin(h,["OLD"]);
  const oldFrame=find(h,"frame")[0];
  h.element("explorer-ra").value="120";h.element("explorer-dec").value="-20";
  const fresh=h.element("explorer-form").fire("submit");await flush();
  observations(find(h,"observations")[1],["NEW"]);await flush();
  const newFrame=find(h,"frame")[1];frame(newFrame,"NEW");await fresh;
  assert.equal(h.element("explorer-image").src,"blob:NEW");
  frame(oldFrame,"OLD");await old;await flush();
  assert.equal(oldFrame.options.signal.aborted,true);
  assert.equal(h.element("explorer-image").src,"blob:NEW");
  assert.equal(h.element("explorer-frame-label").textContent.includes("NEW"),true);
}

async function incompatibleMaskPoliciesCannotBeCompared() {
  const h=harness();const {submit}=await begin(h,["A","B"]);
  frame(find(h,"frame")[0],"A",{policy:"legacy-mask"});await submit;
  assert.equal(h.element("explorer-frame-meta").textContent.includes("20 pixel khả dụng; 3 bị loại; 2 thiếu"),true);
  h.element("explorer-pin").fire("click");h.element("explorer-current").value="1";
  const b=h.element("explorer-current").fire("change");await flush();
  frame(find(h,"frame")[1],"B");await b;
  assert.equal(h.element("explorer-image").hidden,true);
  assert.equal(h.element("explorer-status").textContent.includes("quy tắc loại pixel khác nhau"),true);
  assert.equal(h.element("explorer-play").disabled,true);
  const {submit:fresh}=await begin(h,["NEW"]);
  frame(find(h,"frame")[2],"NEW");await fresh;
  assert.equal(h.element("explorer-image").src,"blob:NEW");
  assert.equal(h.element("explorer-image").hidden,false);
}

async function emptySearchClearsPreviousProvenance() {
  const h=harness();const {submit}=await begin(h,["OLD"]);
  frame(find(h,"frame")[0],"OLD");await submit;
  assert.equal(h.element("explorer-export").disabled,false);
  h.element("explorer-ra").value="120";
  const fresh=h.element("explorer-form").fire("submit");await flush();
  observations(find(h,"observations")[1],[]);await fresh;
  assert.equal(h.element("explorer-image").hidden,true);
  assert.equal(h.element("explorer-frame-label").textContent,"");
  assert.equal(h.element("explorer-frame-hash").textContent,"");
  assert.equal(h.element("explorer-download-fits").href,"");
  assert.equal(h.element("explorer-export").disabled,true);
  assert.equal(h.element("explorer-pin").disabled,true);
}

async function boundedUpstreamRetry() {
  for(const status of [502,504]){
    const h=harness(),submit=h.element("explorer-form").fire("submit");await flush();
    find(h,"observations")[0].resolve({ok:false,status,json:async()=>({error:"upstream_timeout"})});await flush();
    assert.equal(find(h,"observations").length,2);
    assert.equal(h.element("explorer-status").textContent.includes("2/2"),true);
    find(h,"observations")[1].resolve({ok:false,status,json:async()=>({error:"upstream_timeout"})});await submit;
    assert.equal(find(h,"observations").length,2);
    assert.equal(h.element("explorer-status").textContent.includes("chưa thành công"),true);
    assert.equal(h.element("explorer-status").textContent.includes("Không có quan sát"),false);
  }
  const h=harness(),submit=h.element("explorer-form").fire("submit");await flush();
  find(h,"observations")[0].resolve({ok:false,status:429,json:async()=>({error:"rate_limited"})});await submit;
  assert.equal(find(h,"observations").length,1);
}

async function main() {
  await noviceFailureRecoveryAndReload();
  await coordinateCases();
  await serializedContrastAndBlink();
  await staleFailureCannotHideCachedFrame();
  await refusesInconsistentContrast();
  await changedSearchRejectsOldResult();
  await emptySearchClearsPreviousProvenance();
  await incompatibleMaskPoliciesCannotBeCompared();
  await boundedUpstreamRetry();
  await workflowPairSurvivesBlinkAndInvalidatesOnEdit();
  await notesStayWithTheirQueryAndPair();
  console.log("Explorer DOM and HTTP race cases passed");
}
async function noviceFailureRecoveryAndReload(){
  const memory=new Map(),drafts=require("../web/draft-store.js")(()=>({getItem:k=>memory.get(k)||null,setItem:(k,v)=>memory.set(k,v)}));
  const search="?sky_ra=350&sky_dec=35&sky_fov=0.06&sky_det=6&sky_release=qr2&sky_from=2025-06-01&sky_to=2025-06-30";
  let h=harness({drafts,search});
  assert.equal(h.element("explorer-from").value,"2025-06-01");
  const {submit}=await begin(h,["A","B"]);
  assert.equal(h.api.context().listed,true,"the frame list is available before the first image arrives");
  assert.equal(h.events.some(e=>e.detail.kind==="results"),true);
  find(h,"frame")[0].resolve({ok:false,status:502,json:async()=>({error:"upstream_unavailable"})});await submit;
  assert.equal(h.element("explorer-retry").hidden,false);
  assert.equal(h.api.context().listed,true);assert.equal(h.api.context().ready,false);
  const retry=h.element("explorer-retry").fire("click");await flush();frame(find(h,"frame")[1],"A");await retry;
  h.element("explorer-pin").fire("click");h.element("explorer-current").value="1";
  const b=h.element("explorer-current").fire("change");await flush();frame(find(h,"frame")[2],"B");await b;
  assert.equal(h.element("explorer-reference").textContent.includes("ảnh B: 2"),true);
  assert.equal(h.context.shared.includes("sky_from=2025-06-01"),true);
  h.element("explorer-note").value="Đúng cặp A/B sau reload";h.element("explorer-note").fire("input");
  h=harness({drafts,search});const restored=await begin(h,["A","B"]);frame(find(h,"frame")[0],"A");await restored.submit;
  h.element("explorer-pin").fire("click");h.element("explorer-current").value="1";
  const second=h.element("explorer-current").fire("change");await flush();frame(find(h,"frame")[1],"B");await second;
  assert.equal(h.element("explorer-note").value,"Đúng cặp A/B sau reload");
  const missing=harness(),pending=missing.element("explorer-form").fire("submit");await flush();
  find(missing,"observations")[0].resolve({ok:true,json:async()=>({observations:[{obs_id:"missing",t_min_mjd:60000,access_url:null},{obs_id:"B",t_min_mjd:60001,access_url:"https://irsa.ipac.caltech.edu/B.fits"}],provenance:{query_url:"https://irsa.ipac.caltech.edu/SIA"}})});
  await flush();assert.equal(find(missing,"frame")[0].params.get("url"),"https://irsa.ipac.caltech.edu/B.fits");
  frame(find(missing,"frame")[0],"B");await pending;
}
let timeout;
const done=Promise.race([main(),new Promise((_,reject)=>{
  timeout=setTimeout(()=>reject(new Error("Explorer test timed out")),5000);
})]).finally(()=>clearTimeout(timeout));
if(typeof process!=="undefined")done.catch(error=>{console.error(error);process.exitCode=1;});

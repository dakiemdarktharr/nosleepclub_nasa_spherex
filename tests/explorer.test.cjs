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
      after(...nodes){this.siblings=nodes;},
      addEventListener(type,fn){this.handlers[type]=fn;},
      fire(type){return this.handlers[type]?.({preventDefault(){}});}
    });
    return elements.get(id);
  };
  const document={documentElement:{lang:options.lang||"vi"},getElementById:element,createElement:()=>({children:[],handlers:{},dataset:{},setAttribute(){},removeAttribute(){},
    append(...items){this.children.push(...items);},addEventListener(type,fn){this.handlers[type]=fn;},click(){}}),
    addEventListener(){},dispatchEvent(event){events.push(event);},hidden:false};
  const fetch=(url,options)=>new Promise((resolve,reject)=>{
    calls.push({url,options,params:new Params(url.split("?")[1]||""),resolve,reject});
  });
  const context={window:{SkyDrafts:options.drafts,SkyWorkflow:{}},document,fetch,URL:URLFake,URLSearchParams:Params,AbortController:AbortFake,DOMException:DOMError,
    location:{href:"https://demo.example/"+(options.search||"")+"#explore",search:options.search||"", hash:"#explore"},history:{replaceState(a,b,url){context.shared=String(url.href||url);}},
    requestAnimationFrame(fn){fn();},
    setInterval:fn=>{const id=++nextTimer;timers.set(id,fn);return id;},clearInterval:id=>timers.delete(id),
    setTimeout:fn=>{fn();return 1;},Blob:class {constructor(parts){this.id="export";blobs.push(parts);}},
    CustomEvent:class {constructor(type,options={}){this.type=type;this.detail=options.detail;}}};
  for(const [id,value] of Object.entries({"explorer-ra":"350","explorer-dec":"35","explorer-fov":"0.06",
    "explorer-detector":"6","explorer-release":"dr1","explorer-from":"","explorer-to":""}))element(id).value=value;
  element("explorer-form").requestSubmit=()=>element("explorer-form").fire("submit");
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
  if(options.spectral)Object.assign(values,{
    "x-frame-center-spectral-source":"WCS-WAVE","x-frame-time-system":"UTC",
    "x-frame-mjd-obs":String(options.spectral.mjd),"x-frame-center-wavelength-um":String(options.spectral.center),
    "x-frame-center-bandwidth-um":String(options.spectral.width)
  });
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
  await autoplayUsesDistinctCompatibleLoadedFrames();
  await timelineEntryChecksSpacedCompatibleFrames();
  await explicitAutoloadIsValidatedAndPreservesLanguage();
  await curatedSequenceLoadsExactFramesOnly();
  await curatedSequenceResumesMissingFrames();
  await abandonedSearchDoesNotChangePublicRoute();
  await transientFrameIsRetriedOnce();
  console.log("Explorer DOM and HTTP race cases passed");
}
async function timelineEntryChecksSpacedCompatibleFrames(){
  const search="?lang=en&sky_view=timeline";
  const h=harness({search,lang:"en"}), ids=Array.from({length:10},(_,index)=>"VIS"+index);
  const spectral=(mjd,center)=>({spectral:{mjd,center,width:.034}});
  const {submit}=await begin(h,ids);
  const at=index=>find(h,"frame")[index];
  const nextIs=(index,id)=>assert.match(at(index).params.get("url"),new RegExp(id+"[.]fits$"));
  nextIs(0,"VIS0");frame(at(0),"VIS0",spectral(60000,4.73));await submit;await flush();
  assert.equal(h.element("explorer-image").src,"blob:VIS0","the first image is visible while the rest load");
  assert.match(h.element("explorer-timeline-hint").textContent,/2\/6|1\/6/);
  nextIs(1,"VIS9");frame(at(1),"VIS9",spectral(60009,4.95));await flush();
  nextIs(2,"VIS2");frame(at(2),"VIS2",spectral(60002,4.731));await flush();
  assert.equal(h.element("explorer-timeline").disabled,true,"the structurally valid out-of-band image cannot be played");
  nextIs(3,"VIS4");frame(at(3),"VIS4",spectral(60004,4.734));await flush();
  assert.equal(find(h,"frame").length,4,"prefetch stops at three compatible observations");
  assert.equal(h.element("explorer-timeline").disabled,false);
  h.element("explorer-timeline").fire("click");
  assert.equal(h.element("explorer-image").src,"blob:VIS0");
  const tick=[...h.timers.values()][0];tick();assert.equal(h.element("explorer-image").src,"blob:VIS2");
  tick();assert.equal(h.element("explorer-image").src,"blob:VIS4");
  const limited=harness({search,lang:"en"});
  const pending=await begin(limited,ids);
  const fetched=()=>find(limited,"frame");
  frame(fetched()[0],"VIS0",spectral(60000,4.73));await pending.submit;await flush();
  for(let index=1;index<6;index++){
    frame(fetched()[index],"unmatched",spectral(60000+index,4.91+index*.01));await flush();
  }
  assert.equal(fetched().length,6,"the number of candidate cutouts is bounded");
  assert.equal(limited.element("explorer-timeline").disabled,true);
  assert.match(limited.element("explorer-status").textContent,/Fewer than three compatible images/);
}
async function noviceFailureRecoveryAndReload(){
  const memory=new Map(),drafts=require("../web/draft-store.js")(()=>({getItem:k=>memory.get(k)||null,setItem:(k,v)=>memory.set(k,v)}));
  const search="?sky_ra=350&sky_dec=35&sky_fov=0.06&sky_det=6&sky_release=qr2&sky_from=2025-06-01&sky_to=2025-06-30";
  let h=harness({drafts,search});
  assert.equal(h.element("explorer-release").value,"dr1");
  assert.match(h.element("explorer-status").textContent,/QR2/);
  assert.equal(h.element("explorer-from").value,"2025-06-01");
  assert.equal(h.element("explorer-date-summary").textContent,"Khoảng ngày · 01/06/2025–30/06/2025");
  const {submit}=await begin(h,["A","B"]);
  assert.equal(h.api.context().listed,true,"the frame list is available before the first image arrives");
  assert.equal(h.events.some(e=>e.detail.kind==="results"),true);
  find(h,"frame")[0].resolve({ok:false,status:502,json:async()=>({error:"invalid_fits"})});await submit;
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
async function autoplayUsesDistinctCompatibleLoadedFrames() {
  const h=harness({lang:"en"}), spectral=(mjd,center)=>({spectral:{mjd,center,width:.034}});
  const {submit}=await begin(h,["A","B","C","different"]);
  frame(find(h,"frame")[0],"A",spectral(60100,4.73));await submit;
  async function open(index,id,meta){
    h.element("explorer-current").value=String(index);
    const task=h.element("explorer-current").fire("change");await flush();
    frame(find(h,"frame").at(-1),id,meta);await task;
  }
  await open(1,"B",spectral(60101,4.731));
  assert.equal(h.element("explorer-timeline").disabled,true);
  await open(2,"C",spectral(60102,4.734));
  assert.equal(h.element("explorer-timeline").disabled,false);
  await open(3,"different",spectral(60103,4.95));
  assert.equal(h.element("explorer-timeline").disabled,true);
  h.element("explorer-current").value="2";await h.element("explorer-current").fire("change");
  h.element("explorer-timeline").fire("click");
  assert.equal(h.element("explorer-image").src,"blob:A");
  assert.match(h.element("explorer-frame-label").textContent,/^1\/3.+λ 4\.730 µm/);
  const tick=[...h.timers.values()][0];tick();assert.equal(h.element("explorer-image").src,"blob:B");
  h.element("explorer-timeline").fire("click");await flush();
  assert.equal(h.element("explorer-image").src,"blob:B","pause keeps the displayed frame");
  h.element("explorer-timeline").fire("click");
  const replay=[...h.timers.values()][0];replay();assert.equal(h.element("explorer-image").src,"blob:B");
  replay();assert.equal(h.element("explorer-image").src,"blob:C");
  h.api.pause();assert.equal(h.timers.size,0);
}
async function explicitAutoloadIsValidatedAndPreservesLanguage(){
  const search="?lang=en&sky_autoload=1&sky_ra=350&sky_dec=35&sky_release=dr1&sky_view=timeline";
  const h=harness({search,lang:"en"});
  assert.equal(find(h,"observations").length,1);
  observations(find(h,"observations")[0],["A"]);await flush();
  frame(find(h,"frame")[0],"A");await flush();
  assert.match(h.context.shared,/lang=en/);
  assert.doesNotMatch(h.context.shared,/sky_autoload/);
  assert.match(h.context.shared,/sky_view=timeline/);
  assert.match(h.element("explorer-status").textContent,/Image loaded/);
  const invalid=harness({search:search.replace("350","360"),lang:"en"});
  assert.equal(find(invalid,"observations").length,0);
  assert.match(invalid.element("explorer-status").textContent,/below 360/);
  const unknownView=harness({search:search.replace("timeline","unknown"),lang:"en"});
  observations(find(unknownView,"observations")[0],["A"]);await flush();
  frame(find(unknownView,"frame")[0],"A");await flush();
  assert.match(unknownView.context.shared,/sky_view=compare/);
}
async function curatedSequenceLoadsExactFramesOnly(){
  const url="?lang=en&sky_autoload=1&sky_sequence=epsilon-dr1&sky_ra=331.04583333&sky_dec=-56.78333333&sky_fov=0.12&sky_det=6&sky_release=dr1";
  const h=harness({search:url,lang:"en"});
  const ids=["2025W18_1B_0081_3","2025W18_2B_0011_3","2025W19_1B_0344_3"];
  observations(find(h,"observations")[0],["others",ids[2],ids[0],ids[1]]);await flush();
  for(const [index,id] of ids.entries()){
    const calls=find(h,"frame");
    assert.equal(calls.length,index+1,"curated frames use serial requests");
    assert.match(calls[index].params.get("url"),new RegExp(id));
    assert.equal(h.element("explorer-timeline").disabled,true);
    frame(calls[index],id,{spectral:{mjd:60100+index,center:4.73+index*.001,width:.036}});await flush();
  }
  assert.equal(h.element("explorer-timeline").disabled,false);
  assert.match(h.element("explorer-status").textContent,/Three Epsilon/);
  assert.match(h.context.shared,/sky_sequence=epsilon-dr1/);
  const other=harness({search:url.replace("331.04583333","350"),lang:"en"});
  observations(find(other,"observations")[0],["generic",...ids]);await flush();
  assert.match(find(other,"frame")[0].params.get("url"),/generic/);
  assert.doesNotMatch(other.context.shared,/sky_sequence/);
  frame(find(other,"frame")[0],"generic");await flush();
}
async function abandonedSearchDoesNotChangePublicRoute(){
  const h=harness(),pending=h.element("explorer-form").fire("submit");await flush();
  h.context.location.hash="#night-sky";
  observations(find(h,"observations")[0],["somewhere"]);await pending;
  assert.equal(h.context.shared,undefined);
  assert.equal(find(h,"frame").length,0);
  assert.equal(h.context.location.hash,"#night-sky");
}
async function curatedSequenceResumesMissingFrames(){
  const search="?lang=en&sky_autoload=1&sky_sequence=epsilon-dr1&sky_ra=331.04583333&sky_dec=-56.78333333&sky_fov=0.12&sky_det=6&sky_release=dr1";
  const h=harness({search,lang:"en"}),ids=["2025W18_1B_0081_3","2025W18_2B_0011_3","2025W19_1B_0344_3"];
  observations(find(h,"observations")[0],ids);await flush();
  const spectral=mjd=>({spectral:{mjd,center:4.73,width:.036}});
  frame(find(h,"frame")[0],"A",spectral(60100));await flush();
  find(h,"frame")[1].resolve({ok:false,status:502,json:async()=>({error:"invalid_fits"})});await flush();
  assert.equal(h.element("explorer-retry").hidden,false);
  assert.equal(h.element("explorer-image").src,"blob:A");
  const saved=h.element("workflow-frame-status").siblings[0];
  assert.equal(saved.hidden,false);
  assert.match(saved.href,/lang=en&field=epsilon&view=saved#night-sky$/);
  const retried=h.element("explorer-retry").fire("click");await flush();
  assert.equal(find(h,"frame").length,3,"reuse the first downloaded frame");
  frame(find(h,"frame")[2],"B",spectral(60101));await flush();
  frame(find(h,"frame")[3],"C",spectral(60102));await retried;
  assert.equal(h.element("explorer-timeline").disabled,false);
  assert.match(h.element("explorer-status").textContent,/Three Epsilon/);
  assert.equal(saved.hidden,true);
}
async function transientFrameIsRetriedOnce(){
  const h=harness(), {submit}=await begin(h,["A"]);
  const failed={ok:false,status:502,json:async()=>({error:"upstream_http_error"})};
  find(h,"frame")[0].resolve(failed);await flush();
  assert.equal(find(h,"frame").length,2);
  assert.equal(find(h,"frame")[0].url,find(h,"frame")[1].url);
  find(h,"frame")[1].resolve(failed);await submit;
  assert.equal(find(h,"frame").length,2);
  assert.equal(h.element("explorer-retry").hidden,false);
}
let timeout;
const done=Promise.race([main(),new Promise((_,reject)=>{
  timeout=setTimeout(()=>reject(new Error("Explorer test timed out")),5000);
})]).finally(()=>clearTimeout(timeout));
if(typeof process!=="undefined")done.catch(error=>{console.error(error);process.exitCode=1;});

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
  constructor(){
    const listeners=new Set();
    this.signal={aborted:false,
      addEventListener(type,fn){if(type==="abort")listeners.add(fn);},
      removeEventListener(type,fn){if(type==="abort")listeners.delete(fn);}};
    this.listeners=listeners;
  }
  abort(){if(this.signal.aborted)return;this.signal.aborted=true;for(const listener of this.listeners)listener();this.listeners.clear();}
}
class DOMError extends Error {constructor(message,name){super(message);this.name=name;}}

function harness(options={}) {
  const elements=new Map(),calls=[],timers=new Map(),timeouts=new Map(),blobs=[],events=[]; let nextTimer=0;
  const makeClassList=()=>{const names=new Set();return {toggle(name,force){if(force===undefined? !names.has(name):force)names.add(name);else names.delete(name);return names.has(name);},add(...items){items.forEach(item=>names.add(item));},remove(...items){items.forEach(item=>names.delete(item));},contains(name){return names.has(name);}};};
  const element=id=>{
    if(!elements.has(id))elements.set(id,{
      id,value:"",textContent:"",hidden:false,disabled:false,href:"",src:"",children:[],handlers:{},style:{values:{},setProperty(key,value){this.values[key]=value;}},
      classList:makeClassList(), setAttribute(){}, removeAttribute(name){if(name==="href")this.href="";}, replaceChildren(){this.children=[];},
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
  const localManifest=options.localManifest;
  const fetch=(url,requestOptions)=>{
    const call={url,options:requestOptions,params:new Params(url.split("?")[1]||""),body:requestOptions?.body};calls.push(call);
    if(url==="/assets/mission/full-sequence/manifest.json")return Promise.resolve(localManifest
      ?{ok:true,json:async()=>localManifest}
      :{ok:false,status:404,json:async()=>({})});
    if(url.startsWith("/assets/mission/full-sequence/")&&url.endsWith(".webp")){
      const id=url.split("/").at(-1).replace(/\.webp$/,"");
      return Promise.resolve({ok:true,headers:{get:key=>key.toLowerCase()==="content-type"?"image/webp":null},blob:async()=>({id})});
    }
    return new Promise((resolve,reject)=>{
      call.resolve=resolve;call.reject=reject;
      requestOptions?.signal?.addEventListener?.("abort",()=>reject(new DOMError("aborted","AbortError")),{once:true});
    });
  };
  const context={window:{SkyDrafts:options.drafts,SkyWorkflow:{}},document,fetch,URL:URLFake,URLSearchParams:Params,AbortController:AbortFake,DOMException:DOMError,
    Image:class {constructor(){this.naturalWidth=2040;this.naturalHeight=2040;}decode(){return Promise.resolve();}},
    location:{href:"https://demo.example/"+(options.search===undefined?"?sky_view=compare":options.search)+"#explore",search:options.search===undefined?"?sky_view=compare":options.search, hash:"#explore"},history:{replaceState(a,b,url){context.shared=String(url.href||url);}},
    requestAnimationFrame(fn){fn();},
    setInterval:fn=>{const id=++nextTimer;timers.set(id,fn);return id;},clearInterval:id=>timers.delete(id),
    setTimeout:(fn,delay)=>{const id=++nextTimer;if(options.deferTimeouts)timeouts.set(id,{fn,delay});else fn();return id;},clearTimeout:id=>timeouts.delete(id),
    Blob:class {constructor(parts,meta={}){this.id=meta.type==="image/png"&&parts[0]?.length?String.fromCharCode(...parts[0]):"export";blobs.push(parts);}},
    atob:value=>Buffer.from(value,"base64").toString("binary"),
    CustomEvent:class {constructor(type,options={}){this.type=type;this.detail=options.detail;}}};
  for(const [id,value] of Object.entries({"explorer-ra":"350","explorer-dec":"35","explorer-fov":"0.06",
    "explorer-detector":"6","explorer-release":"dr1","explorer-from":"","explorer-to":""}))element(id).value=value;
  element("explorer-sequence-count").value="5";
  element("explorer-form").requestSubmit=()=>element("explorer-form").fire("submit");
  if(options.linked)context.window.SkyLinkedComparison={mount(args){context.linked=args;return {update(){}};}};
  vm.runInNewContext(fs.readFileSync("web/explorer.js","utf8"),context);
  return {element,calls,timers,timeouts,blobs,events,context,api:context.window.SkyExplorer};
}
const flush=async()=>{for(let i=0;i<16;i++)await Promise.resolve();};
const find=(h,kind)=>h.calls.filter(call=>call.url.split("?")[0]===`/api/${kind}`);
function observations(call, ids) {
  const rows=ids.map((id,i)=>({access_url:`https://irsa.ipac.caltech.edu/${id}.fits`,
    t_min_mjd:60000+i,detector:6,obs_id:id}));
  call.resolve({ok:true,json:async()=>({observations:rows,provenance:{query_url:"https://irsa.ipac.caltech.edu/SIA"},truncated:false})});
  return rows;
}
function frameHeaders(id, options={}) {
  const values={"content-type":"image/png","x-frame-grid-ra-deg":String(options.grid?.ra??350),
    "x-frame-grid-dec-deg":String(options.grid?.dec??35),"x-frame-grid-scale-arcsec":String(options.grid?.scale??6.15),
    "x-frame-grid-size-px":String(options.grid?.size??37),"x-frame-grid-fov-deg":String(options.grid?.fov??37*6.15/3600),
    "x-frame-source-url":options.source??`https://irsa.ipac.caltech.edu/${id}.fits`,
    "x-frame-contrast-low":String(options.low??0.5),"x-frame-contrast-high":String(options.high??2.5),"x-frame-valid-pixels":"20",
    "x-frame-masked-pixels":"3","x-frame-missing-pixels":"2",
    "x-frame-mask-policy":options.policy??"source-only-allowlist-v2",
    "x-frame-center-pixel-status":options.centerStatus??options.centerPixel??"valid","x-frame-release":options.release??"dr1",
    "x-frame-detector":String(options.detector??6),"x-frame-obs-id":options.obsId??id,
    "x-frame-cutout-url":options.cutout??`https://irsa.ipac.caltech.edu/${id}.fits?center=350,35&size=0.1`,
    "x-frame-cutout-sha256":"a".repeat(64)};
  if(options.spectral||Number.isFinite(options.mjd))Object.assign(values,{"x-frame-time-system":"UTC","x-frame-mjd-obs":String(options.spectral?.mjd??options.mjd)});
  if(options.spectral)Object.assign(values,{"x-frame-center-spectral-source":"WCS-WAVE",
    "x-frame-center-wavelength-um":String(options.spectral.center),"x-frame-center-bandwidth-um":String(options.spectral.width)});
  return values;
}
function localFullManifest(ids=["FULL0","FULL1","FULL2","FULL3","FULL4"]) {
  return {targets:{barnard:{frames:ids.map((id,index)=>{
    const accessUrl=`https://irsa.ipac.caltech.edu/${id}.fits`;
    return {row:{access_url:accessUrl,detector:6,release:"dr1",obs_id:id,t_min_mjd:61000+index},
      asset_url:`/assets/mission/full-sequence/barnard/${id}.webp`,headers:{
        "x-frame-full-detector":"true","x-frame-source-url":accessUrl,"x-frame-source-sha256":"f".repeat(64),
        "x-frame-release":"dr1","x-frame-obs-id":id,"x-frame-detector":"6",
        "x-frame-grid-scale-arcsec":index===1?"6.237057":"6.160000","x-frame-grid-size-px":"2040",
        "x-frame-grid-fov-deg":"3.49065","x-frame-target-x-px":"1020","x-frame-target-y-px":"1020",
        "x-frame-unit":"MJy/sr","x-frame-zodi":"subtract","x-frame-contrast-mode":"shared-target-stretch",
        "x-frame-contrast-low":"0.5","x-frame-contrast-high":"2.5","x-frame-valid-pixels":"4000000",
        "x-frame-mask-policy":"source-only-allowlist-v2","x-frame-masked-pixels":"0","x-frame-missing-pixels":"0",
        "x-frame-center-pixel-status":"valid","x-frame-mjd-obs":String(61000+index),"x-frame-time-system":"UTC"}};
  })}}};
}
function frame(call, id, options={}) {
  const values=frameHeaders(id,options);
  const headers={get:key=>values[key.toLowerCase()]??null,*[Symbol.iterator](){yield* Object.entries(values);}};
  call.resolve({ok:true,headers,blob:async()=>({id})});
}
function sequence(call, frames, errors=[]) {
  call.resolve({ok:true,status:200,json:async()=>({frames:frames.map(({index,id,options={}})=>({index,png:Buffer.from(id).toString("base64"),headers:frameHeaders(id,options)})),errors})});
}
function rateLimited(retryAfter="1") {
  return {ok:false,status:429,headers:{get:key=>key.toLowerCase()==="retry-after"?retryAfter:null},json:async()=>({error:"rate_limited"})};
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
  assert.equal(h.element("explorer-frame-meta").textContent.includes("37 × 37 pixel"),true,h.element("explorer-frame-meta").textContent);
  assert.equal(h.element("explorer-source-fits").href,"https://irsa.ipac.caltech.edu/A.fits");
  assert.equal(h.element("explorer-image-wrap").style.values["--linked-grid-width"],"296px");
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
async function localFullSequencePreloadsBeforePlayback(){
  const h=harness({lang:"en",localManifest:localFullManifest()});
  h.element("explorer-ra").value="269.44626688537255";
  h.element("explorer-dec").value="4.768222216475269";
  const submit=h.element("explorer-form").fire("submit");await flush();await submit;await flush();
  assert.equal(find(h,"observations").length,0,"a bundled target does not query the observations API");
  assert.equal(find(h,"frame").length,0,"a bundled full image does not call the cutout API");
  assert.equal(find(h,"sequence").length,0);
  assert.equal(h.calls.filter(call=>call.url.endsWith(".webp")).length,1,"the selected full detector image is shown first");
  assert.match(h.element("explorer-frame-meta").textContent,/2040 × 2040/);
  assert.equal(h.element("explorer-image-wrap").classList.contains("full-detector-view"),true);
  h.element("explorer-timeline").fire("click");await flush();
  assert.equal(h.calls.filter(call=>call.url.endsWith(".webp")).length,5,"one click downloads and decodes every frame before playback");
  assert.equal(find(h,"observations").length+find(h,"frame").length+find(h,"sequence").length,0,"the local sequence uses no image API");
  assert.equal(h.timers.size,1,"playback begins only after all five full images are decoded");
  assert.match(h.element("explorer-frame-label").textContent,/^1\/5/);
  h.api.pause();
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
  await userSequencesPlayExactlyTwoAndTenFrames();
  await userSequenceDeduplicatesAndReportsTruncation();
  await userSequenceRetriesPartialFrames();
  await detectorOnlySequenceAllowsMaskedCenterAndWarnsAboutWavelengths();
  await changingQueryCancelsUserSequenceLoad();
  await switchingToComparisonStopsSelectedSequence();
  await timelineEntryChecksSpacedCompatibleFrames();
  await localFullSequencePreloadsBeforePlayback();
  await explicitAutoloadIsValidatedAndPreservesLanguage();
  await curatedSequenceLoadsExactFramesOnly();
  await curatedSequenceResumesMissingFrames();
  await abandonedSearchDoesNotChangePublicRoute();
  await transientFrameIsRetriedOnce();
  console.log("Explorer DOM and HTTP race cases passed");
}
async function switchingToComparisonStopsSelectedSequence(){
  const h=harness({lang:"en",search:"?sky_view=timeline",linked:true}),ids=["A","B","C","D","E"];
  const {submit}=await begin(h,ids);
  frame(find(h,"frame")[0],"A",{spectral:{mjd:60000,center:4.73,width:.036}});await submit;
  h.element("explorer-timeline").fire("click");await flush();
  const pending=find(h,"sequence")[0],body=JSON.parse(pending.body);
  assert.equal(body.frames.length,4);
  h.context.linked.onModeChange("compare");
  sequence(pending,body.frames.map(({index})=>({index,id:ids[index],options:{spectral:{mjd:60000+index,center:4.73,width:.036}}})));
  await flush();
  assert.equal(h.timers.size,0,"switching to A/B prevents a pending timeline from starting playback");
  assert.match(h.context.shared,/sky_view=compare/);
}
async function userSequencesPlayExactlyTwoAndTenFrames(){
  const h=harness({lang:"en"}),ids=Array.from({length:12},(_,i)=>"OBS"+String(i).padStart(2,"0"));
  const {submit}=await begin(h,ids);
  frame(find(h,"frame")[0],ids[0],{spectral:{mjd:70000,center:4.73,width:.036}});await submit;
  h.element("explorer-timeline").fire("click");await flush();
  let call=find(h,"sequence")[0],body=JSON.parse(call.body);
  assert.deepEqual(body.frames.map(frame=>frame.index),[3,6,8,11],"one click batches the four images missing from the five-frame selection");
  assert.equal(find(h,"frame").length,1,"sequence loading does not issue serial per-image API calls");
  sequence(call,body.frames.map(({index})=>({index,id:ids[index],options:{spectral:{mjd:70000+index,center:4.73,width:.036}}})));
  await flush();
  assert.equal(h.timers.size,1,"playback starts after every selected image is ready");
  assert.equal(h.element("explorer-image").src,"blob:"+ids[0]);
  let tick=[...h.timers.values()][0];tick();assert.equal(h.element("explorer-image").src,"blob:"+ids[3]);
  h.element("explorer-timeline").fire("click");assert.equal(h.timers.size,0);
  h.element("explorer-sequence-count").value="10";h.element("explorer-sequence-count").fire("change");
  h.element("explorer-timeline").fire("click");await flush();
  call=find(h,"sequence")[1];body=JSON.parse(call.body);
  assert.deepEqual(body.frames.map(frame=>frame.index),[1,2,4,5,7,9,10],"the ten-frame option only fetches frames not already held in memory");
  sequence(call,body.frames.map(({index})=>({index,id:ids[index],options:{spectral:{mjd:70000+index,center:4.73,width:.036}}})));
  await flush();
  assert.equal(h.timers.size,1);
  assert.equal(h.element("explorer-timeline").textContent,"Pause sequence");
  h.api.pause();
}
async function userSequenceDeduplicatesAndReportsTruncation(){
  const h=harness({lang:"en"}),pending=h.element("explorer-form").fire("submit");await flush();
  const rows=[
    {obs_id:"FIRST",t_min_mjd:60000,detector:6,access_url:"https://irsa.ipac.caltech.edu/FIRST.fits"},
    {obs_id:"FIRST",t_min_mjd:60000.2,detector:6,access_url:"https://irsa.ipac.caltech.edu/FIRST-reprocessed.fits"},
    {obs_id:"NO_TIME",t_min_mjd:null,detector:6,access_url:"https://irsa.ipac.caltech.edu/NO_TIME.fits"},
    {obs_id:"NO_URL",t_min_mjd:60001,detector:6,access_url:null},
    {obs_id:"SAME_EPOCH_A",t_min_mjd:60002,detector:6,access_url:"https://irsa.ipac.caltech.edu/SAME_EPOCH_A.fits"},
    {obs_id:"SAME_EPOCH_B",t_min_mjd:60002,detector:6,access_url:"https://irsa.ipac.caltech.edu/SAME_EPOCH_B.fits"},
    {obs_id:"LAST",t_min_mjd:60003,detector:6,access_url:"https://irsa.ipac.caltech.edu/LAST.fits"},
    {obs_id:"OTHER_DETECTOR",t_min_mjd:60004,detector:5,access_url:"https://irsa.ipac.caltech.edu/OTHER_DETECTOR.fits"}
  ];
  find(h,"observations")[0].resolve({ok:true,json:async()=>({observations:rows,truncated:true,provenance:{query_url:"https://irsa.ipac.caltech.edu/SIA"}})});await flush();
  frame(find(h,"frame")[0],"FIRST",{spectral:{mjd:60000,center:4.73,width:.036}});await pending;
  assert.match(h.element("explorer-sequence-summary").textContent,/3 distinct times/);
  assert.equal(h.element("explorer-timeline").disabled,true,"the app does not pretend three unique observations can make a five-frame sequence");
  assert.equal(find(h,"sequence").length,0);
}
async function userSequenceRetriesPartialFrames(){
  const h=harness({lang:"en"}),ids=["A","B","C","D","E"],{submit}=await begin(h,ids);
  frame(find(h,"frame")[0],"A",{spectral:{mjd:61000,center:4.73,width:.036}});await submit;
  h.element("explorer-timeline").fire("click");await flush();
  let call=find(h,"sequence")[0],body=JSON.parse(call.body);
  assert.deepEqual(body.frames.map(frame=>frame.index),[1,2,3,4]);
  sequence(call,[1,2].map(index=>({index,id:ids[index],options:{spectral:{mjd:61000+index,center:4.73,width:.036}}})),
    [{index:3,error:"upstream_unavailable",status:502},{index:4,error:"upstream_unavailable",status:502}]);
  await flush();
  assert.equal(h.timers.size,0,"incomplete sequences never start");
  assert.equal(h.element("explorer-retry").hidden,false);
  assert.match(h.element("explorer-status").textContent,/Loaded 3\/5 frames/);
  const retry=h.element("explorer-retry").fire("click");await flush();
  call=find(h,"sequence")[1];body=JSON.parse(call.body);
  assert.deepEqual(body.frames.map(frame=>frame.index),[3,4],"retry fetches only missing frames");
  sequence(call,body.frames.map(({index})=>({index,id:ids[index],options:{spectral:{mjd:61000+index,center:4.73,width:.036}}})));
  await flush();await retry;
  assert.equal(h.timers.size,1,"playback starts automatically after retry completes the full sequence");
}
async function detectorOnlySequenceAllowsMaskedCenterAndWarnsAboutWavelengths(){
  const h=harness({lang:"en"}),ids=["A","B","C","D","E"],{submit}=await begin(h,ids);
  frame(find(h,"frame")[0],"A",{mjd:61000});await submit;
  h.element("explorer-timeline").fire("click");await flush();
  const call=find(h,"sequence")[0],body=JSON.parse(call.body);
  sequence(call,body.frames.map(({index})=>({index,id:ids[index],options:{mjd:61000+index,centerStatus:index===1?"masked":"valid"}})));
  await flush();
  assert.equal(h.timers.size,1,"missing WCS-WAVE metadata is disclosed but does not block visual playback");
  assert.match(h.element("explorer-status").textContent,/WCS-WAVE is missing from some frames/);
  const tick=[...h.timers.values()][0];tick();
  assert.match(h.element("explorer-center-status").textContent,/center pixel was excluded/);
  h.api.pause();
}
async function changingQueryCancelsUserSequenceLoad(){
  const h=harness(),ids=Array.from({length:12},(_,i)=>"OLD"+i),{submit:oldQuery}=await begin(h,ids);
  frame(find(h,"frame")[0],ids[0],{spectral:{mjd:62000,center:4.73,width:.036}});await oldQuery;
  h.element("explorer-sequence-count").value="10";h.element("explorer-sequence-count").fire("change");
  h.element("explorer-timeline").fire("click");await flush();
  const stale=find(h,"sequence")[0];assert.ok(stale);
  h.element("explorer-ra").value="120";const fresh=h.element("explorer-form").fire("submit");await flush();
  observations(find(h,"observations")[1],["NEW"]);await flush();
  frame(find(h,"frame")[1],"NEW",{spectral:{mjd:62050,center:4.73,width:.036}});await fresh;
  assert.equal(stale.options.signal.aborted,true);
  sequence(stale,JSON.parse(stale.body).frames.map(({index})=>({index,id:"OLD"+index,options:{spectral:{mjd:62000+index,center:4.73,width:.036}}})));
  await flush();
  assert.equal(h.element("explorer-image").src,"blob:NEW");
  assert.match(h.element("explorer-frame-label").textContent,/NEW/);
}
async function timelineEntryChecksSpacedCompatibleFrames(){
  const search="?lang=en&sky_view=timeline",h=harness({search,lang:"en"}),ids=Array.from({length:10},(_,index)=>"VIS"+index);
  const spectral=index=>({spectral:{mjd:60000+index,center:4.73,width:.034}});
  const {submit}=await begin(h,ids);
  frame(find(h,"frame")[0],"VIS0",spectral(0));await submit;await flush();
  assert.equal(find(h,"frame").length,1,"searching only downloads the first displayed frame");
  h.element("explorer-timeline").fire("click");await flush();
  const call=find(h,"sequence")[0],body=JSON.parse(call.body);
  assert.deepEqual(body.frames.map(frame=>frame.index),[2,5,7,9],"the timeline samples five distinct times across the full observation span");
  sequence(call,body.frames.map(({index})=>({index,id:ids[index],options:spectral(index)})));
  await flush();
  assert.equal(h.timers.size,1);
  assert.match(h.element("explorer-frame-label").textContent,/^1\/5/);
  h.api.pause();
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
  const h=harness({lang:"en"}),ids=["A","B","C","D","E"],{submit}=await begin(h,ids);
  frame(find(h,"frame")[0],"A",{spectral:{mjd:60100,center:4.73,width:.034}});await submit;
  h.element("explorer-timeline").fire("click");await flush();
  const call=find(h,"sequence")[0],body=JSON.parse(call.body);
  sequence(call,body.frames.map(({index})=>({index,id:ids[index],options:{spectral:{mjd:60100+index,
    center:index===2?4.95:4.73,width:.034}}})));
  await flush();
  assert.equal(h.timers.size,0,"one frame with a disjoint wavelength interval prevents playback of the entire selection");
  assert.equal(h.element("explorer-timeline").disabled,true,"the player never silently skips an incompatible observation");
  assert.match(h.element("explorer-status").textContent,/did not pass validation/);
}
async function explicitAutoloadIsValidatedAndPreservesLanguage(){
  const search="?lang=en&sky_autoload=1&sky_ra=350&sky_dec=35&sky_release=dr1&sky_view=timeline";
  const h=harness({search,lang:"en"});
  assert.equal(find(h,"observations").length,1);
  observations(find(h,"observations")[0],["A"]);await flush();
  frame(find(h,"frame")[0],"A");await flush();
  assert.match(h.context.shared,/lang=en/);
  assert.match(h.context.shared,/sky_autoload=1/);
  assert.match(h.context.shared,/sky_view=timeline/);
  assert.match(h.element("explorer-status").textContent,/Image loaded/);
  const invalid=harness({search:search.replace("350","360"),lang:"en"});
  assert.equal(find(invalid,"observations").length,0);
  assert.match(invalid.element("explorer-status").textContent,/below 360/);
  const unknownView=harness({search:search.replace("timeline","unknown"),lang:"en"});
  observations(find(unknownView,"observations")[0],["A"]);await flush();
  frame(find(unknownView,"frame")[0],"A");await flush();
  assert.match(unknownView.context.shared,/sky_view=timeline/);
}
async function curatedSequenceLoadsExactFramesOnly(){
  const url="?lang=en&sky_autoload=1&sky_sequence=epsilon-dr1&sky_view=timeline&sky_ra=331.04583333&sky_dec=-56.78333333&sky_fov=0.12&sky_det=6&sky_release=dr1";
  const h=harness({search:url,lang:"en"});
  const ids=["2025W18_1B_0081_3","2025W18_2B_0011_3","2025W19_1B_0344_3"];
  await flush();
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
  const search="?lang=en&sky_autoload=1&sky_sequence=epsilon-dr1&sky_view=timeline&sky_ra=331.04583333&sky_dec=-56.78333333&sky_fov=0.12&sky_det=6&sky_release=dr1";
  const h=harness({search,lang:"en"}),ids=["2025W18_1B_0081_3","2025W18_2B_0011_3","2025W19_1B_0344_3"];
  await flush();
  observations(find(h,"observations")[0],ids);await flush();
  const spectral=mjd=>({spectral:{mjd,center:4.73,width:.036}});
  frame(find(h,"frame")[0],ids[0],spectral(60100));await flush();
  find(h,"frame")[1].resolve({ok:false,status:502,json:async()=>({error:"invalid_fits"})});await flush();
  assert.equal(h.element("explorer-retry").hidden,false);
  assert.equal(h.element("explorer-image").src,`blob:${ids[0]}`);
  const saved=h.element("workflow-frame-status").siblings[0];
  assert.equal(saved.hidden,false);
  assert.match(saved.href,/lang=en&field=epsilon&view=saved#night-sky$/);
  const retried=h.element("explorer-retry").fire("click");await flush();
  assert.equal(find(h,"frame").length,3,"reuse the first downloaded frame");
  frame(find(h,"frame")[2],ids[1],spectral(60101));await flush();
  frame(find(h,"frame")[3],ids[2],spectral(60102));await retried;
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

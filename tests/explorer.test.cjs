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

function harness() {
  const elements=new Map(),calls=[],timers=new Map(); let nextTimer=0;
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
    append(...items){this.children.push(...items);},addEventListener(type,fn){this.handlers[type]=fn;}}),
    addEventListener(){},hidden:false};
  const fetch=(url,options)=>new Promise((resolve,reject)=>{
    calls.push({url,options,params:new Params(url.split("?")[1]||""),resolve,reject});
  });
  const context={document,fetch,URL:URLFake,URLSearchParams:Params,AbortController:AbortFake,DOMException:DOMError,
    location:{href:"https://demo.example/#explore",search:""},history:{replaceState(){}},
    setInterval:fn=>{const id=++nextTimer;timers.set(id,fn);return id;},clearInterval:id=>timers.delete(id),
    setTimeout:fn=>{fn();return 1;},Blob:class {constructor(){this.id="export";}}};
  for(const [id,value] of Object.entries({"explorer-ra":"350","explorer-dec":"35","explorer-fov":"0.06",
    "explorer-detector":"6","explorer-release":"qr2","explorer-from":"","explorer-to":""}))element(id).value=value;
  vm.runInNewContext(fs.readFileSync("web/explorer.js","utf8"),context);
  return {element,calls,timers};
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
  assert.equal(h.element("explorer-reference").textContent.includes("Ảnh đối chiếu: 2"),true);
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

async function main() {
  await coordinateCases();
  await serializedContrastAndBlink();
  await staleFailureCannotHideCachedFrame();
  await refusesInconsistentContrast();
  await changedSearchRejectsOldResult();
  await emptySearchClearsPreviousProvenance();
  console.log("Explorer DOM and HTTP race cases passed");
}
let timeout;
const done=Promise.race([main(),new Promise((_,reject)=>{
  timeout=setTimeout(()=>reject(new Error("Explorer test timed out")),5000);
})]).finally(()=>clearTimeout(timeout));
if(typeof process!=="undefined")done.catch(error=>{console.error(error);process.exitCode=1;});

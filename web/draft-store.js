"use strict";
/* Session-only drafts: never sent automatically; bounded, expiring, tab-local. */
((root,factory)=>{if(typeof module==="object"&&module.exports)module.exports=factory;else root.SkyDrafts=factory(()=>root.sessionStorage);})(typeof window!=="undefined"?window:globalThis,(storage,now=()=>Date.now())=>{
  const key="spherex-tab-drafts-v1",ttl=86400000,limit=50;
  function read(){try{const rows=JSON.parse(storage().getItem(key)||"[]");return Array.isArray(rows)?rows.filter(r=>r&&["wise","irsa"].includes(r.kind)&&typeof r.key==="string"&&r.key.length<5000&&Number.isFinite(r.time)&&now()-r.time<ttl&&r.time<=now()&&typeof r.value?.note==="string"&&r.value.note.length<=2000):[];}catch{return [];}}
  function write(rows){try{storage().setItem(key,JSON.stringify(rows.slice(-limit)));return true;}catch{return false;}}
  return {get:(kind,id)=>read().find(r=>r.kind===kind&&r.key===id)?.value||null,
    set(kind,id,value){if(!["wise","irsa"].includes(kind)||typeof id!=="string"||id.length>=5000||typeof value?.note!=="string"||value.note.length>2000)return false;return write([...read().filter(r=>r.kind!==kind||r.key!==id),{kind,key:id,value,time:now()}]);},
    remove:(kind,id)=>write(read().filter(r=>r.kind!==kind||r.key!==id))};
});

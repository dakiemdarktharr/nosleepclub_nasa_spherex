"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const memory = new Map();
const storage = {getItem: key => memory.get(key) || null, setItem: (key, value) => memory.set(key, value)};
const context = {window: {}, localStorage: storage};
vm.runInNewContext(fs.readFileSync("web/review-store.js", "utf8"), context);
const store = context.window.ReviewStore;
const now = Date.now(), stamp = ms => new Date(ms).toISOString();
const row = {analysis_sha256:"a".repeat(64), scene_id:"scene", selection:"target", status:"uncertain",
  note:"old cloud note", saved_at:stamp(now - 86400000), expires_at:stamp(now + 20*86400000),
  review_id:"1".repeat(64), cloud_scope:"scope-a", sync_state:"cloud"};
const id = store.key(row);

// A failed cloud edit keeps the prior remote ID/scope and remote expiry.
const edit = {...row, note:"new local draft", saved_at:stamp(now), expires_at:stamp(now + 180*86400000)};
const draft = store.localDraft(edit, row);
assert.equal(draft.sync_state, "local");
assert.equal(draft.review_id, row.review_id);
assert.equal(draft.cloud_scope, "scope-a");
assert.equal(draft.cloud_expires_at, row.expires_at);
assert.equal(draft.cloud_pending, true);
assert.equal(store.deletePlan(draft, "scope-a", []), "remote");
assert.equal(store.deletePlan(draft, "scope-b", []), "detached");
const again = store.localDraft({...edit,note:"edited again"}, draft);
assert.equal(again.cloud_expires_at, row.expires_at);
assert.equal(store.deletePlan({...edit,sync_state:"local",review_id:undefined,cloud_scope:undefined}, "scope-a", []), "local");

// Different sessions can both have the same scene/selection key.
const other = {...row, note:"new session cloud", review_id:"2".repeat(64), cloud_scope:undefined};
const merged = store.merge({[id]:row}, [other], "scope-b");
assert.equal(merged[id].note, "new session cloud");
assert.equal(merged[id].cloud_scope, "scope-b");
const archives = Object.values(merged).filter(item => item.archive_id);
assert.equal(archives.length, 1);
assert.equal(archives[0].note, "old cloud note");
assert.equal(archives[0].sync_state, "detached");
assert.equal(store.merge({[id]:row}, [other], null)[id].note, "old cloud note");
assert.equal(store.deletePlan(archives[0], "scope-b", [other]), "detached");
store.write(merged);
const reloaded = store.read();
assert.equal(Object.keys(reloaded).length, 2);
assert.equal(Object.values(reloaded).filter(item => item.archive_id)[0].note, "old cloud note");
const mergedDraft = store.merge({[id]:draft}, [other], "scope-b");
assert.equal(mergedDraft[id].note, "new session cloud");
assert.equal(Object.values(mergedDraft).filter(item => item.archive_id)[0].note, "new local draft");

// A detached v1 item without an archive ID must also survive a matching remote key.
const legacyDetached = {...row, sync_state:"detached"};
const legacyMerged = store.merge({[id]:legacyDetached}, [other], "scope-b");
assert.equal(Object.keys(legacyMerged).length, 2);
assert.equal(Object.values(legacyMerged).filter(item => item.archive_id)[0].note, row.note);
const legacyUnknown = {...row, cloud_scope:undefined};
assert.equal(store.deletePlan(legacyUnknown, "scope-a", [{review_id:row.review_id}]), "remote");
assert.equal(store.deletePlan(legacyUnknown, "scope-b", [other]), "detached");
assert.equal(Object.keys(store.merge({[id]:legacyUnknown}, [other], "scope-b")).length, 2);

// Explicit invalid or expired dates are rejected; never silently renewed.
assert.equal(Object.keys(store.clean({x:{...row,expires_at:"bad"}}, now)).length, 0);
assert.equal(Object.keys(store.clean({x:{...row,expires_at:stamp(now-1)}}, now)).length, 0);
assert.equal(Object.keys(store.clean({x:{...row,saved_at:stamp(now+300001)}}, now)).length, 0);
assert.equal(store.clean({x:{...row,expires_at:stamp(now+500*86400000)}}, now)[id].expires_at,
             stamp(Date.parse(row.saved_at)+180*86400000));
assert.equal(Object.keys(store.clean({x:{...row,note:"x".repeat(2001)}}, now)).length, 0);

// A GET that started before a mutation, or while it is pending, cannot apply.
assert.equal(store.snapshotAllowed(2, 2, 0), true);
assert.equal(store.snapshotAllowed(2, 3, 0), false);
assert.equal(store.snapshotAllowed(3, 3, 1), false);
assert.equal(store.snapshotAllowed(3, 4, 0), false);
console.log("ReviewStore lifecycle cases passed");

// A missing dependency must leave a visible retry, never an endless loading state.
{
  const nodes=new Map();let reloads=0;
  const node=id=>{
    if(!nodes.has(id))nodes.set(id,{hidden:true,textContent:"",attributes:{"aria-busy":"true"},handlers:{},
      getContext(){return {};},removeAttribute(key){delete this.attributes[key];},addEventListener(event,fn){this.handlers[event]=fn;}});
    return nodes.get(id);
  };
  assert.throws(()=>vm.runInNewContext(fs.readFileSync("web/app.js","utf8"),{
    window:{},document:{getElementById:node},location:{reload(){reloads++;}}
  }),/review_store_unavailable/);
  assert.equal(node("load-retry").hidden,false);
  assert.equal(node("workspace").attributes["aria-busy"],undefined);
  assert.match(node("load-state").textContent,/Chưa tải được/);
  node("load-retry").handlers.click();assert.equal(reloads,1);
}

// Run the actual app event handlers with an isolated DOM and controlled HTTP timing.
async function appCases() {
  const elements = new Map();
  function element(id) {
    if (!elements.has(id)) elements.set(id, {
      id, value:"", textContent:"", hidden:false, disabled:false, handlers:{},
      classList:{toggle(){}}, getContext(){return {};},
      addEventListener(type, fn){this.handlers[type]=fn;}, setAttribute(){}, replaceChildren(){}, append(){}
    });
    return elements.get(id);
  }
  const doc = {getElementById:element, querySelectorAll:()=>[], createElement:()=>element(`created-${elements.size}`),
               addEventListener(){}, fonts:{addEventListener(){}}};
  const win = {ReviewStore:store, addEventListener(){}};
  let http = () => new Promise(()=>{});
  const appContext = {window:win, document:doc, ReviewStore:store, location:{protocol:"https:"},
    fetch:(url,options)=>url === "data/manifest.json" ? new Promise(()=>{}) : http(url,options || {}),
    setTimeout, clearTimeout, setInterval, clearInterval, console};
  const appSource = fs.readFileSync("web/app.js", "utf8") + `\nwindow.__test={
    ready(){state.manifest={analysis_sha256:"${"a".repeat(64)}"};state.scene={id:"scene",before:{sha256:"x"},after:{sha256:"y"},target_detection:"unconfirmed"};state.selected="target";},
    get:()=>reviews, set:value=>{reviews=value;}, sync:syncReviews, remove:removeReview,
    online(){remoteStorage=true;reviewScope="scope-a";}
  };`;
  vm.runInNewContext(appSource, appContext);
  const app = win.__test; app.ready();
  const ok = data => ({ok:true,json:async()=>data});
  const snapshot = (rows, scope="scope-a") => ({reviews:rows,session_scope:scope});
  const tick = () => Promise.resolve();

  // A slow GET cannot erase what the user is typing.
  let resolveOld;
  http = () => new Promise(resolve=>{resolveOld=resolve;});
  const typingSync = app.sync();
  element("review-status").value="uncertain";
  element("review-note").value="typing without saving";
  element("review-note").handlers.input();
  resolveOld(ok(snapshot([])));
  await typingSync;
  assert.equal(element("review-note").value, "typing without saving");

  // A GET started before POST must not erase the later saved record.
  app.set({});
  let n = 0;
  http = (url,options) => {
    if(options.method === "POST")return Promise.resolve(ok({review:{...row,note:"newly saved"},session_scope:"scope-a"}));
    if(++n === 1)return new Promise(resolve=>{resolveOld=resolve;});
    return Promise.resolve(ok(snapshot([])));
  };
  const beforePost = app.sync();
  element("review-note").value="newly saved";
  element("review-note").handlers.input();
  await element("save-review").handlers.click();
  resolveOld(ok(snapshot([])));
  await beforePost;
  assert.equal(app.get()[id].note, "newly saved");

  // A GET started before DELETE cannot resurrect the removed cloud note.
  app.set({[id]:row}); n=0;
  http = (url,options) => {
    if(options.method === "DELETE")return Promise.resolve(ok({deleted:true}));
    if(++n === 1)return new Promise(resolve=>{resolveOld=resolve;});
    return Promise.resolve(ok(snapshot([row])));
  };
  const beforeDelete = app.sync();
  await app.remove(id,element("review-feedback"));
  resolveOld(ok(snapshot([row])));
  await beforeDelete;
  assert.equal(app.get()[id], undefined);

  // When POST fails, DELETE still targets the previous cloud ID for this scope.
  app.set({[id]:row}); let deletedId;
  http = (url,options) => {
    if(options.method === "POST")return Promise.reject(new Error("offline"));
    if(options.method === "DELETE"){deletedId=JSON.parse(options.body).review_id;return Promise.resolve(ok({deleted:true}));}
    return Promise.resolve(ok(snapshot([row])));
  };
  element("review-note").value="unsynced edit";
  element("review-note").handlers.input();
  await element("save-review").handlers.click();
  assert.equal(app.get()[id].review_id,row.review_id);
  assert.equal(app.get()[id].cloud_expires_at,row.expires_at);
  await app.remove(id,element("review-feedback"));
  assert.equal(deletedId,row.review_id);
  assert.equal(app.get()[id],undefined);

  // An edit in a changed session stays detached and does not POST into it.
  app.set({[id]:row}); let posts=0;
  http = (url,options) => {
    if(options.method === "POST"){posts++;return Promise.resolve(ok({}));}
    return Promise.resolve(ok(snapshot([other], "scope-b")));
  };
  element("review-note").value="draft from previous session";
  element("review-note").handlers.input();
  await element("save-review").handlers.click();
  assert.equal(posts,0);
  const detached = Object.values(app.get()).find(value=>value.archive_id);
  assert.equal(detached.note,"draft from previous session");
  assert.equal(detached.cloud_scope,"scope-a");
  assert.equal(detached.cloud_expires_at,row.expires_at);

  // GET launched during POST must also be discarded once that POST completes.
  app.set({}); app.online(); let resolvePost, resolveDuring;
  http = (url,options) => {
    if(options.method === "POST")return new Promise(resolve=>{resolvePost=resolve;});
    if(resolvePost)return new Promise(resolve=>{resolveDuring=resolve;});
    return Promise.resolve(ok(snapshot([])));
  };
  element("review-note").value="saved during request";
  element("review-note").handlers.input();
  const pendingSave=element("save-review").handlers.click();
  await tick(); await tick();
  const duringPost=app.sync();
  resolvePost(ok({review:{...row,note:"saved during request"},session_scope:"scope-a"}));
  await pendingSave;
  resolveDuring(ok(snapshot([])));
  await duringPost;
  assert.equal(app.get()[id].note,"saved during request");
}
const done = appCases().then(()=>console.log("Review UI race cases passed"));
if (typeof process !== "undefined") done.catch(error=>{console.error(error);process.exitCode=1;});

"use strict";
// Local notes expire after at most 180 days; reading never uploads drafts.
window.ReviewStore = (() => {
  const KEY = "nosleepclub.reviews.v1", LIFETIME = 180 * 86400000;
  const statuses = new Set(["uncertain", "interesting", "artifact"]);
  const safeId = value => typeof value === "string" && /^[A-Za-z0-9_.-]{1,200}$/.test(value);
  function key(item) { return `${item.analysis_sha256}:${item.scene_id}:${item.selection}`; }
  function storageKey(item) { return item.archive_id ? `${key(item)}:archive:${item.archive_id}` : key(item); }
  function clean(input, now = Date.now()) {
    const output = Object.create(null);
    if (!input || typeof input !== "object" || Array.isArray(input)) return output;
    for (const value of Object.values(input)) {
      if (!value || typeof value !== "object" || !statuses.has(value.status) ||
          !/^[a-f0-9]{64}$/.test(value.analysis_sha256 || "") ||
          !/^[A-Za-z0-9_.-]{1,128}$/.test(value.scene_id || "") ||
          !/^[A-Za-z0-9_.-]{1,128}$/.test(value.selection || "") ||
          typeof value.note !== "string" || value.note.length > 2000 ||
          (value.archive_id !== undefined && !safeId(value.archive_id))) continue;
      const saved = Date.parse(value.saved_at), expiry = value.expires_at === undefined ? saved + LIFETIME : Date.parse(value.expires_at);
      if (!Number.isFinite(saved) || saved > now + 300000 || !Number.isFinite(expiry)) continue;
      const expires = Math.min(saved + LIFETIME, expiry);
      if (expires <= now) continue;
      const item = {...value, expires_at: new Date(expires).toISOString()};
      if(item.sync_state === "detached" && !item.archive_id) {
        const scope = safeId(item.cloud_scope) ? item.cloud_scope : "unknown";
        item.archive_id = `${scope.slice(0,128)}-${saved}`;
      }
      let id = storageKey(item);
      // Preserve archive collisions instead of collapsing distinct notes.
      if (item.archive_id && output[id]) {
        const base = item.archive_id; let n = 1;
        do { item.archive_id = `${base.slice(0,180)}-${n++}`; id = storageKey(item); } while (output[id]);
      }
      output[id] = item;
    }
    return output;
  }
  function read() {
    try { return clean(JSON.parse(localStorage.getItem(KEY) || "{}")); }
    catch { return Object.create(null); }
  }
  function write(items) { localStorage.setItem(KEY, JSON.stringify(clean(items))); }
  function detach(items, id) {
    const item = items[id]; if (!item || item.archive_id) return items;
    const next = {...items}; delete next[id];
    const scope = safeId(item.cloud_scope) ? item.cloud_scope : "unknown";
    const base = `${scope.slice(0,128)}-${Date.parse(item.saved_at)}`;
    let archiveId = base, n = 1;
    while (next[`${key(item)}:archive:${archiveId}`]) archiveId = `${base}-${n++}`;
    const archived = {...item, sync_state:"detached", archive_id:archiveId};
    next[storageKey(archived)] = archived;
    return next;
  }
  function merge(items, cloud, scope) {
    let next = clean(items);
    if(typeof scope !== "string" || !scope || !Array.isArray(cloud))return next;
    const remote = clean(Object.fromEntries(cloud.map(item => [key(item), item])));
    for (const [id, item] of Object.entries(next)) {
      if (item.archive_id) continue;
      if (item.sync_state === "detached") {
        next = detach(next, id);
        continue;
      }
      if (item.cloud_scope && scope && item.cloud_scope !== scope) {
        next = detach(next, id);
      } else if (!item.cloud_scope && (item.sync_state === "cloud" || item.review_id || item.cloud_pending) &&
                 (!item.review_id || remote[id]?.review_id !== item.review_id)) {
        next = detach(next, id);
      } else if (item.sync_state === "cloud" && !remote[id]) {
        if (scope && item.cloud_scope === scope) delete next[id];
        else next = detach(next, id);
      }
    }
    for (const [id, item] of Object.entries(remote)) {
      if (next[id]?.sync_state !== "local") next[id] = {...item, sync_state:"cloud", cloud_scope:scope};
    }
    return clean(next);
  }
  function localDraft(item, previous) {
    const draft = {...item, sync_state:"local"};
    if (previous && !previous.archive_id && previous.sync_state !== "detached" &&
        (previous.sync_state === "cloud" || previous.review_id || previous.cloud_pending)) {
      draft.cloud_pending = true;
      for (const field of ["review_id", "cloud_scope"]) if (previous[field]) draft[field] = previous[field];
      const oldExpiry = previous.cloud_expires_at || previous.expires_at;
      if (oldExpiry && Number.isFinite(Date.parse(oldExpiry))) draft.cloud_expires_at = oldExpiry;
      draft.cloud_saved_at = previous.cloud_saved_at || previous.saved_at;
    }
    return draft;
  }
  function deletePlan(item, scope, cloud) {
    if (item.archive_id || item.sync_state === "detached") return "detached";
    if (item.sync_state === "local" && !item.review_id && !item.cloud_scope && !item.cloud_pending) return "local";
    if (item.cloud_scope) return scope && item.cloud_scope === scope ? "remote" : "detached";
    // Legacy records without scope can be verified only through their owner-scoped ID.
    return item.review_id && Array.isArray(cloud) && cloud.some(row => row.review_id === item.review_id) ? "remote" : "detached";
  }
  function snapshotAllowed(startVersion, currentVersion, pending) {
    return startVersion === currentVersion && pending === 0;
  }
  return Object.freeze({key, storageKey, clean, read, write, detach, merge, localDraft, deletePlan, snapshotAllowed});
})();

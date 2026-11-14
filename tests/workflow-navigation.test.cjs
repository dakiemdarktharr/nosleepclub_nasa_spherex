"use strict";
const assert=require("node:assert/strict");
const {decide,signature,sourceFromSearch,frameLabel}=require("../web/navigation.js");
assert.equal(sourceFromSearch("?sky_ra=350"),"irsa");assert.equal(sourceFromSearch("?sky_ra=350&flow_source=wise"),"wise");assert.equal(sourceFromSearch("?flow_source=irsa"),"irsa");assert.equal(sourceFromSearch("?flow_source=invalid"),"wise");
const wise={ready:true,analysis_sha256:"a".repeat(64),scene_id:"strict",selection:"target"};
const irsa={ready:true,paired:true,query:{ra:133.76,dec:-7.24,release:"qr2",det:6,fov:.06},reference:{obs_id:"A"},current:{obs_id:"B"},reference_index:0,current_index:1};
for(const source of["wise","irsa"]){
  for(const request of["compare","check","review"])assert.equal(decide(request,source,{ready:false},null).step,"data");
  assert.equal(decide("research",source,null,null).step,"research");assert.equal(decide("data",source,null,null).step,"data");
}
assert.equal(decide("compare","irsa",{...irsa,paired:false},null).step,"compare");
assert.equal(decide("compare","irsa",{ready:false,listed:true},null).step,"compare","metadata list remains reachable when first frame fails");
assert.equal(decide("check","irsa",{ready:false,listed:true},null).step,"data","metadata alone does not permit analysis/review");
assert.equal(decide("check","irsa",{...irsa,paired:false},null).step,"compare");
assert.equal(decide("review","irsa",{...irsa,paired:false},null).step,"compare");
for(const[source,context]of[["wise",wise],["irsa",irsa]]){
  assert.equal(decide("review",source,context,null).step,"check");
  const key=signature(source,context);assert.equal(decide("review",source,context,key).step,"review");
  assert.equal(signature(source,{...context,ready:false}),null);
}
const old=signature("wise",wise);
for(const change of[{analysis_sha256:"b".repeat(64)},{scene_id:"broad"},{selection:"R1"}])assert.equal(decide("review","wise",{...wise,...change},old).step,"check");
for(const change of[{query:{...irsa.query,ra:140}},{query:{...irsa.query,release:"qr3"}},{current:{obs_id:"C"}},{reference:{obs_id:"C"}},{current_index:2}])assert.equal(decide("review","irsa",{...irsa,...change},signature("irsa",irsa)).step,"check");
assert.notEqual(signature("wise",wise),signature("irsa",irsa));
assert.notEqual(signature("irsa",irsa),signature("irsa",{...irsa,current:{...irsa.current,detector:5}}));
assert.match(frameLabel({obs_id:"A",detector:4,t_min_mjd:60000},{"x-frame-time-system":"UTC","x-frame-mjd-obs":"60000","x-frame-center-spectral-source":"WCS-WAVE","x-frame-center-wavelength-um":"3.15"},"dr1"),/^DR1 · D4 · 2023-02-25 00:00:00 UTC · λ 3\.1500 µm · WCS-WAVE · A$/);
assert.match(frameLabel({obs_id:"B",detector:6,t_min_mjd:60000},{"x-frame-time-system":"TAI","x-frame-mjd-obs":"60000"},"qr3"),/^QR3 · D6 · MJD 60000\.00000 · B$/,"never relabel an unverified time system as UTC");
console.log("Workflow policy: data readiness, distinct source contexts, pair prerequisite, check before review and invalidation on data/selection changes passed");

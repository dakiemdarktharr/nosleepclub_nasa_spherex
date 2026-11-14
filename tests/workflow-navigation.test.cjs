"use strict";
const assert=require("node:assert/strict");
const {canonicalStep,decide,sourceFromSearch,frameLabel}=require("../web/navigation.js");
assert.equal(sourceFromSearch("?sky_ra=350"),"irsa");
assert.equal(sourceFromSearch("?sky_ra=350&flow_source=wise"),"wise");
assert.equal(sourceFromSearch("?flow_source=irsa"),"irsa");
assert.equal(sourceFromSearch("?flow_source=invalid"),"wise");
assert.equal(canonicalStep("check"),"compare");
assert.equal(canonicalStep("review"),"compare");
assert.equal(canonicalStep("research"),"research");
for(const source of ["wise","irsa"]){
  assert.deepEqual(decide("data",source,null),{step:"data",reason:""});
  assert.deepEqual(decide("research",source,null),{step:"research",reason:""});
  assert.equal(decide("compare",source,{ready:false}).step,"data");
  assert.equal(decide("check",source,{ready:false}).step,"data");
  assert.equal(decide("review",source,{ready:false}).step,"data");
}
assert.equal(decide("compare","irsa",{ready:false,listed:true}).step,"compare");
assert.equal(decide("check","irsa",{ready:false,listed:true}).step,"compare");
assert.equal(decide("review","wise",{ready:true}).step,"compare");
assert.match(frameLabel({obs_id:"A",detector:4,t_min_mjd:60000},{"x-frame-time-system":"UTC","x-frame-mjd-obs":"60000","x-frame-center-spectral-source":"WCS-WAVE","x-frame-center-wavelength-um":"3.15"},"dr1"),/^DR1 · D4 · 2023-02-25 00:00:00 UTC · λ 3\.1500 µm · WCS-WAVE · A$/);
assert.match(frameLabel({obs_id:"B",detector:6,t_min_mjd:60000},{"x-frame-time-system":"TAI","x-frame-mjd-obs":"60000"},"qr3"),/^QR3 · D6 · MJD 60000\.00000 · B$/);
console.log("Workflow policy: two viewing steps, legacy route aliases, and research navigation passed");

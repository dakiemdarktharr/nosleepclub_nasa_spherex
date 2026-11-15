const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');
const path = require('node:path');

(async () => {
  const {SHIP_BOUNDS, SHIP_HULL, SHIP_ROOMS, SHIP_DOORS, SHIP_WALLS, shipRoom, shipFree, shipPath} =
    await import(pathToFileURL(path.resolve('web/ship-layout.js')));
  const positions = {cockpit:{x:6,z:0}, sleep:{x:3.5,z:0}, kitchen:{x:.5,z:0},
    living:{x:-3,z:0}, fuel:{x:-6,z:-1.25}, airlock:{x:-6,z:1.25}};
  assert.deepEqual(new Set(SHIP_ROOMS.map(room => room.id)), new Set(Object.keys(positions)));
  const pairs = SHIP_DOORS.map(d => [d.from,d.to].sort().join(':')).sort();
  assert.deepEqual(pairs, ['airlock:living','cockpit:sleep','fuel:living','kitchen:living','kitchen:sleep'].sort());
  assert.equal(SHIP_HULL.spacewalk.side, 'near');
  assert.ok(SHIP_HULL.spacewalk.x0 < SHIP_HULL.spacewalk.x1);
  assert.equal(SHIP_BOUNDS.minZ, -SHIP_BOUNDS.maxZ, 'base hull is symmetric across its centerline');

  for (const [name, point] of Object.entries(positions)) {
    assert.equal(shipRoom(point.x,point.z),name);
    assert.ok(shipFree(point.x,point.z), `${name} center is walkable`);
  }
  // Validate grid paths AND sampled points on each line segment, so paths
  // cannot leave the vessel or jump through a bulkhead between grid nodes.
  for (const [from, start] of Object.entries(positions)) for (const [to, end] of Object.entries(positions)) {
    const route = shipPath(start,end);
    assert.ok(route.length, `${from} -> ${to} must be reachable`);
    let previous = start;
    for (const point of route) {
      for (let fraction=0; fraction<=1; fraction+=.1) {
        const x=previous.x+(point.x-previous.x)*fraction, z=previous.z+(point.z-previous.z)*fraction;
        assert.ok(shipFree(x,z), `${from} -> ${to} crosses an obstacle at ${x},${z}`);
      }
      previous=point;
    }
  }
  // Solid parts of room partitions reject the player, but marked doorway
  // centers remain traversable, with clearance for the player's radius.
  for (const d of SHIP_DOORS) {
    const center=(d.start+d.end)/2;
    assert.ok(shipFree(d.at,center), `door ${d.from}/${d.to} must open`);
    assert.ok(d.end-d.start > .5, `door ${d.from}/${d.to} fits player`);
  }
  for (const wall of SHIP_WALLS) {
    const x=(wall.x0+wall.x1)/2,z=(wall.z0+wall.z1)/2;
    assert.equal(shipFree(x,z),false,'bulkheads block walking through walls');
  }
  assert.equal(shipFree(-6.5,0),false,'fuel and airlock are separated');
  assert.equal(shipFree(SHIP_BOUNDS.maxX+1,0),false,'outside hull is inaccessible');
  console.log('Ship layout: six connected rooms, all-pairs routes, shared bulkhead doors and symmetric hull passed');
})().catch(error => { console.error(error); process.exitCode=1; });

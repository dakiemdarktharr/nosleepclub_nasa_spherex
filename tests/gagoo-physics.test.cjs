const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const source = fs.readFileSync(path.join(__dirname, '../web/gagoo-physics.js'), 'utf8');
  const {bodyBounds, clampBody, stepBody, createRope, stepRope, ropePath} = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
  for (const [width, height, w, h] of [[1440, 800, 260, 342], [390, 700, 155, 210], [320, 400, 155, 210]]) {
    const bounds = bodyBounds(width, height, w, h);
    const body = {x: width * .2, y: height * .5, vx: 260, vy: -260, width: w, height: h};
    clampBody(body, bounds);
    for (let i = 0; i < 500; i++) stepBody(body, 1 / 60, bounds, {x: 0, y: height * .46}, width * .37);
    assert.ok(body.x >= bounds.minX && body.x <= bounds.maxX);
    assert.ok(body.y >= bounds.minY && body.y <= bounds.maxY);
    assert.ok(Number.isFinite(body.vx) && Number.isFinite(body.vy));
  }
  const a = {x: 0, y: 300}, b = {x: 200, y: 400};
  const rope = createRope(a, b);
  for (let i = 0; i < 300; i++) stepRope(rope, a, {x: b.x + i, y: b.y - i / 2}, 280, 1 / 60);
  assert.deepEqual({x: rope[0].x, y: rope[0].y}, a);
  assert.equal(rope.at(-1).x, 499);
  assert.ok(rope.every(p => Number.isFinite(p.x) && Number.isFinite(p.y)));
  assert.ok(!/NaN|Infinity/.test(ropePath(rope)));
  const stationary = {x: 100, y: 150, vx: 0, vy: 0, width: 100, height: 150};
  stepBody(stationary, 1 / 60, bodyBounds(800, 600, 100, 150), {x: 0, y: 100}, 500);
  assert.equal(stationary.x, 100); assert.equal(stationary.y, 150);
  console.log('Gagoo physics: bounds, zero-gravity slack, inertial tension and rope anchors passed');
})().catch(error => { console.error(error); process.exitCode = 1; });

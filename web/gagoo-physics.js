// Pixel-space, zero-gravity motion. Time is seconds; speed is pixels/second.
export function bodyBounds(width, height, bodyWidth, bodyHeight) {
  const inset = Math.min(14, width * .03);
  const minX = inset, minY = Math.min(110, height * .18);
  return {minX, minY, maxX: Math.max(minX, width - bodyWidth - inset), maxY: Math.max(minY, height - bodyHeight - 46)};
}

export function clampBody(body, bounds) {
  body.x = Math.max(bounds.minX, Math.min(bounds.maxX, body.x));
  body.y = Math.max(bounds.minY, Math.min(bounds.maxY, body.y));
  return body;
}

export function stepBody(body, dt, bounds, anchor, reach) {
  dt = Math.max(0, Math.min(.035, Number.isFinite(dt) ? dt : 0));
  const dx = body.x + body.width * .5 - anchor.x;
  const dy = body.y + body.height * .5 - anchor.y;
  const length = Math.hypot(dx, dy);
  // A slack umbilical applies no attraction. Only tension can pull it back.
  if (length > reach && length > 0) {
    const tension = (length - reach) * 3.4;
    body.vx -= dx / length * tension * dt;
    body.vy -= dy / length * tension * dt;
  }
  const damping = Math.exp(-.48 * dt);
  body.vx *= damping;
  body.vy *= damping;
  body.x += body.vx * dt;
  body.y += body.vy * dt;
  if (body.x < bounds.minX || body.x > bounds.maxX) body.vx *= -.32;
  if (body.y < bounds.minY || body.y > bounds.maxY) body.vy *= -.32;
  return clampBody(body, bounds);
}

export function createRope(a, b, count = 20, length = Math.hypot(b.x - a.x, b.y - a.y) * 1.1) {
  const distance = Math.hypot(b.x - a.x, b.y - a.y) || 1;
  const amplitude = Math.sqrt(Math.max(0, length * length - distance * distance)) * .47;
  const normal = {x: -(b.y - a.y) / distance, y: (b.x - a.x) / distance};
  return Array.from({length: count}, (_, i) => {
    const t = i / (count - 1);
    const x = a.x + (b.x - a.x) * t + normal.x * Math.sin(t * Math.PI) * amplitude;
    const y = a.y + (b.y - a.y) * t + normal.y * Math.sin(t * Math.PI) * amplitude;
    return {x, y, px: x, py: y};
  });
}

export function stepRope(points, a, b, length, dt) {
  const ratio = Math.max(0, Math.min(2.1, dt * 60));
  const segment = Math.max(length, Math.hypot(b.x - a.x, b.y - a.y) * 1.005) / (points.length - 1);
  for (let i = 1; i < points.length - 1; i++) {
    const p = points[i], x = p.x, y = p.y;
    p.x += (p.x - p.px) * .96 * ratio;
    p.y += (p.y - p.py) * .96 * ratio;
    p.px = x; p.py = y;
  }
  for (let pass = 0; pass < 9; pass++) {
    Object.assign(points[0], {x: a.x, y: a.y, px: a.x, py: a.y});
    Object.assign(points.at(-1), {x: b.x, y: b.y, px: b.x, py: b.y});
    for (let i = 0; i < points.length - 1; i++) {
      const p = points[i], q = points[i + 1];
      const dx = q.x - p.x, dy = q.y - p.y, distance = Math.hypot(dx, dy) || .001;
      const correction = (distance - segment) / distance;
      const pFree = i > 0, qFree = i + 1 < points.length - 1;
      const share = pFree && qFree ? .5 : 1;
      if (pFree) { p.x += dx * correction * share; p.y += dy * correction * share; }
      if (qFree) { q.x -= dx * correction * share; q.y -= dy * correction * share; }
    }
  }
  // Fixed endpoints remain exact even after the last constraint pass.
  Object.assign(points[0], a); Object.assign(points.at(-1), b);
  return points;
}

export function ropePath(points) {
  const f = n => n.toFixed(1);
  let path = `M${f(points[0].x)},${f(points[0].y)}`;
  for (let i = 1; i < points.length - 1; i++) {
    const p = points[i], q = points[i + 1];
    path += ` Q${f(p.x)},${f(p.y)} ${f((p.x + q.x) / 2)},${f((p.y + q.y) / 2)}`;
  }
  const end = points.at(-1);
  return path + ` L${f(end.x)},${f(end.y)}`;
}

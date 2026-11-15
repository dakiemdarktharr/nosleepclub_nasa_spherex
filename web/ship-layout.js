/** Walkable single-deck ship. X grows toward the cockpit, Z across the hull. */
export const SHIP_BOUNDS={minX:-8.8,maxX:8.8,minZ:-3,maxZ:3};
// The visible upper near-side hull is cut away for viewing, not an asymmetric hull.
export const SHIP_HULL={length:18.4,width:6.6,sideHeight:.8,thickness:.2,spacewalk:{side:'near',x0:-8.65,x1:-7.15}};
export const SHIP_ROOMS=[
  {id:'cockpit',x0:5,x1:8.8,z0:-3,z1:3}, {id:'sleep',x0:2,x1:5,z0:-3,z1:3},
  {id:'kitchen',x0:-1,x1:2,z0:-3,z1:3}, {id:'living',x0:-5,x1:-1,z0:-3,z1:3},
  {id:'fuel',x0:-8.8,x1:-5,z0:-3,z1:0}, {id:'airlock',x0:-8.8,x1:-5,z0:0,z1:3}
];
export const SHIP_DOORS=[
  {from:'cockpit',to:'sleep',axis:'x',at:5,start:-.95,end:.95},
  {from:'sleep',to:'kitchen',axis:'x',at:2,start:-.95,end:.95},
  {from:'kitchen',to:'living',axis:'x',at:-1,start:-.95,end:.95},
  {from:'living',to:'fuel',axis:'x',at:-5,start:-2.6,end:-.9},
  {from:'living',to:'airlock',axis:'x',at:-5,start:.9,end:2.6}
];
// Rectangles generated from the same door gaps used by the rendered bulkheads.
export const SHIP_WALLS=[];
for(const x of [-1,2,5]) { SHIP_WALLS.push({x0:x-.1,x1:x+.1,z0:-3.2,z1:-.95}, {x0:x-.1,x1:x+.1,z0:.95,z1:3.2}); }
for(const [a,b] of [[-3.2,-2.6],[-.9,.9],[2.6,3.2]]) SHIP_WALLS.push({x0:-5.1,x1:-4.9,z0:a,z1:b});
SHIP_WALLS.push({x0:-9.1,x1:-5,z0:-.1,z1:.1});
export const SHIP_FURNITURE=[
 {x0:6.1,x1:8.6,z0:-2.9,z1:-1.6}, {x0:3,x1:4.8,z0:-2.9,z1:-1.7},
 {x0:-.7,x1:1.7,z0:-2.9,z1:-1.9}, {x0:-4.7,x1:-3.5,z0:1.9,z1:2.9},
 {x0:-2.85,x1:-1.95,z0:1.225,z1:1.875},
 {x0:-8.65,x1:-6.1,z0:-2.9,z1:-1.8}, {x0:-8.7,x1:-8,z0:.3,z1:2.6}
];
export const SHIP_SOLIDS=[...SHIP_WALLS,...SHIP_FURNITURE];
export function shipRoom(x,z) { return SHIP_ROOMS.find(r=>x>=r.x0&&x<=r.x1&&z>=r.z0&&z<=r.z1)?.id||''; }
export function shipFree(x,z,radius=.25){
 if(x<SHIP_BOUNDS.minX+radius||x>SHIP_BOUNDS.maxX-radius||z<SHIP_BOUNDS.minZ+radius||z>SHIP_BOUNDS.maxZ-radius)return false;
 return !SHIP_SOLIDS.some(o=>x>o.x0-radius&&x<o.x1+radius&&z>o.z0-radius&&z<o.z1+radius);
}
export function shipPath(start,target,step=.25){
 const minX=-8.75,minZ=-3,nx=71,nz=25;
 const cell=(x,z)=>[Math.max(0,Math.min(nx-1,Math.round((x-minX)/step))),Math.max(0,Math.min(nz-1,Math.round((z-minZ)/step)))];
 const point=([x,z])=>({x:minX+x*step,z:minZ+z*step});
 const from=cell(start.x,start.z),to=cell(target.x,target.z),id=([x,z])=>z*nx+x;
 const queue=[from],seen=new Map([[id(from),null]]);let found=null;
 for(let i=0;i<queue.length;i++){const n=queue[i];if(id(n)===id(to)){found=n;break;}
  for(const [dx,dz] of [[0,-1],[-1,0],[1,0],[0,1]]){const v=[n[0]+dx,n[1]+dz];if(v[0]<0||v[0]>=nx||v[1]<0||v[1]>=nz||seen.has(id(v)))continue;const p=point(v);if(!shipFree(p.x,p.z))continue;seen.set(id(v),n);queue.push(v);}}
 if(!found||!shipFree(target.x,target.z))return [];
 const route=[];let node=found;while(node&&id(node)!==id(from)){route.unshift(point(node));node=seen.get(id(node));}route.push({x:target.x,z:target.z});return route;
}

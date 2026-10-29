"use strict";

const $ = (id) => document.getElementById(id);
const canvas = $("sky");
const ctx = canvas.getContext("2d");
const state = { manifest: null, scene: null, images: {}, pixels: null, mode: "wipe", wipe: .5,
  zoom: 1, center: [32,32], selected: "target", blinkAfter: false, timer: null, loading: 0 };
const number = (value, digits=2) => Number(value).toLocaleString("vi-VN", {maximumFractionDigits:digits, minimumFractionDigits:digits});
let reviews = {};
try { reviews = JSON.parse(localStorage.getItem("nosleepclub.reviews.v1") || "{}"); } catch { reviews = {}; }

async function getJson(url) {
  const response = await fetch(url, {cache:"no-cache"});
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return response.json();
}
async function loadImage(src) {
  const image = new Image(); image.src = src; await image.decode(); return image;
}
function download(name, value) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value,null,2)], {type:"application/json"}));
  const a = document.createElement("a"); a.href=url; a.download=name; a.click();
  setTimeout(() => URL.revokeObjectURL(url),1000);
}
function crop() {
  const width=64/state.zoom;
  return {x:Math.max(0,Math.min(64-width,state.center[0]-width/2)),
    y:Math.max(0,Math.min(64-width,state.center[1]-width/2)), width};
}
function xy(x,y,width,height,offset=0) {
  const c=crop(); return [offset+(x+.5-c.x)/c.width*width, (63-y+.5-c.y)/c.width*height];
}
function drawImage(image,x,width,height) {
  const c=crop(); ctx.drawImage(image,c.x,c.y,c.width,c.width,x,0,width,height);
}
function overlays(width,height,offset=0) {
  const scene=state.scene;
  ctx.save();ctx.beginPath();ctx.rect(offset,0,width,height);ctx.clip();
  if ($("show-prior").checked) {
    const a=scene.target_prior[0], b=scene.target_prior[1];
    const [ax,ay]=xy(a.x,a.y,width,height,offset),[bx,by]=xy(b.x,b.y,width,height,offset);
    const radius=3.4/crop().width*width;
    ctx.strokeStyle="#c8afff";ctx.lineWidth=2;ctx.setLineDash([6,5]);
    ctx.beginPath();ctx.arc((ax+bx)/2,(ay+by)/2,radius,0,Math.PI*2);ctx.stroke();
    ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(bx,by);ctx.stroke();ctx.setLineDash([]);
    for (const [x,y] of [[ax,ay],[bx,by]]) {ctx.beginPath();ctx.moveTo(x-5,y);ctx.lineTo(x+5,y);ctx.moveTo(x,y-5);ctx.lineTo(x,y+5);ctx.stroke();}
    if (state.selected==="target") {ctx.fillStyle="#d9caff";ctx.font="500 18px Segoe UI";ctx.fillText("WISE 0855 · dự kiến",Math.max(offset+8,ax-radius),Math.max(22,ay-radius-13));}
  }
  if ($("show-residuals").checked) for (const candidate of scene.candidates) {
    const [x,y]=xy(candidate.x,candidate.y,width,height,offset);
    const selected=state.selected===candidate.id;
    ctx.lineWidth=selected?3:1.8;ctx.strokeStyle=candidate.score>0?"#f7be66":"#82d7f1";
    ctx.beginPath();ctx.arc(x,y,Math.max(12,2/crop().width*width),0,Math.PI*2);ctx.stroke();
    ctx.fillStyle=ctx.strokeStyle;ctx.font=`${selected?"600":"400"} 17px Segoe UI`;
    ctx.fillText(`${candidate.id} ${candidate.score>0?"+":"−"}`,x+14,y-14);
  }
  ctx.restore();
}
function render() {
  if (!state.scene || !state.images.before) return;
  canvas.classList.toggle("side",state.mode==="side");
  canvas.width=1024;canvas.height=state.mode==="side"?512:1024;
  ctx.imageSmoothingEnabled=false;ctx.fillStyle="#0e1a2c";ctx.fillRect(0,0,canvas.width,canvas.height);
  if (state.mode==="side") {
    drawImage(state.images.before,0,512,512);drawImage(state.images.after,512,512,512);
    overlays(512,512);overlays(512,512,512);
    ctx.fillStyle="#b8cad8";ctx.fillRect(511,0,2,512);
  } else if (state.mode==="wipe") {
    drawImage(state.images.before,0,1024,1024);
    const split=state.wipe*1024;
    ctx.save();ctx.beginPath();ctx.rect(split,0,1024-split,1024);ctx.clip();drawImage(state.images.after,0,1024,1024);ctx.restore();
    overlays(1024,1024);
    ctx.strokeStyle="#e4eff8";ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(split,0);ctx.lineTo(split,1024);ctx.stroke();
    ctx.fillStyle="#edf5fc";ctx.beginPath();ctx.arc(split,512,20,0,Math.PI*2);ctx.fill();
    ctx.fillStyle="#17314a";ctx.font="24px Segoe UI";ctx.textAlign="center";ctx.fillText("↔",split,520);ctx.textAlign="left";
  } else {
    drawImage(state.images[state.mode==="difference"?"difference":state.blinkAfter?"after":"before"],0,1024,1024);
    overlays(1024,1024);
  }
  $("mode-badge").textContent={wipe:"Kéo vạch để so sánh",side:"Cùng lưới tọa độ và mức kéo sáng",difference:"Vàng: dương / xanh: âm",blink:state.blinkAfter?"Đang xem ảnh sau":"Đang xem ảnh trước"}[state.mode];
}
function setMode(mode) {
  if (state.timer) clearInterval(state.timer);state.timer=null;
  state.mode=mode;state.blinkAfter=false;
  document.querySelectorAll("[data-mode]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.mode===mode)));
  $("wipe-control").hidden=mode!=="wipe";
  $("view-note").textContent=mode==="difference"
    ?"Ảnh sau trừ ảnh trước đã đồng nhất PSF và hiệu chỉnh flux/nền. Vùng xanh xám thiếu dữ liệu hoặc không qua kiểm tra phổ; điểm residual không phải sigma đã hiệu chuẩn."
    :"Hai ảnh dùng cùng mức kéo sáng. Vòng nét đứt là dự báo từ astrometry cũ, không phải phát hiện của model.";
  if (mode==="blink") state.timer=setInterval(()=>{state.blinkAfter=!state.blinkAfter;render();},850);
  render();
}
function keyForSelection() {
  return `${state.manifest.analysis_sha256}:${state.scene.id}:${state.selected}`;
}
function loadReview() {
  const saved=reviews[keyForSelection()];
  $("review-status").value=saved?.status||"uncertain";$("review-note").value=saved?.note||"";
  $("review-feedback").textContent=saved?"Đã có nhận xét được lưu trên trình duyệt này.":"";
  $("clear-review").hidden=!saved;
}
function select(id) {
  state.selected=id;
  $("select-target").setAttribute("aria-pressed",String(id==="target"));
  document.querySelectorAll(".candidate-button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.id===id)));
  const scene=state.scene,detail=$("selection-detail");
  if(id==="target") {
    const a=scene.before.target_fit,b=scene.after.target_fit;
    detail.innerHTML=`<div class="selection-title">Fit PSF tại vị trí dự kiến</div><div class="fit-score"><div><span>S/N ảnh trước</span><strong>${number(a.fixed_prior_snr,1)}</strong></div><div><span>S/N ảnh sau</span><strong>${number(b.fixed_prior_snr,1)}</strong></div></div><p>Fit biên độ tại vị trí ngoại suy; chưa fit vị trí độc lập. Hai giá trị này chưa xác nhận chuyển động.</p><dl><dt>Độ lệch bước sóng</dt><dd>≈ ${number(scene.target_wavelength_delta_nm,2)} nm</dd><dt>Bề rộng phổ trung bình</dt><dd>${number((scene.before.bandwidth_um+scene.after.bandwidth_um)*500,1)} nm</dd><dt>Vị trí dự kiến, ảnh sau</dt><dd>${number(scene.target_prior[1].ra_deg,5)}°</dd></dl>`;
  } else {
    const c=scene.candidates.find(c=>c.id===id);
    detail.innerHTML=`<div class="selection-title">${c.id} · Residual ${c.score>0?"dương":"âm"}</div><dl><dt>Điểm thực nghiệm</dt><dd>${number(c.score,2)}</dd><dt>RA</dt><dd>${number(c.ra_deg,6)}°</dd><dt>Dec</dt><dd>${number(c.dec_deg,6)}°</dd><dt>Pixel trên lưới chung</dt><dd>${c.x}, ${c.y}</dd></dl><p>Vùng ảnh sai khác đáng kiểm tra. Có thể do thiên thể, PSF, màu phổ hoặc noise. Chưa gán danh tính thiên thể.</p>`;
  }
  loadReview();render();
}
function candidateList() {
  const list=$("candidate-list");list.replaceChildren();
  $("candidate-count").textContent=String(state.scene.candidates.length);
  if(!state.scene.candidates.length){list.textContent="Không có residual vượt ngưỡng trong vùng hợp lệ.";return;}
  for(const c of state.scene.candidates) {
    const button=document.createElement("button");button.className="candidate-button";button.dataset.id=c.id;
    button.setAttribute("aria-pressed","false");
    button.innerHTML=`<span class="candidate-sign ${c.score<0?"negative":""}">${c.score>0?"+":"−"}</span><span><strong>${c.id}</strong><small>Residual ${c.score>0?"dương":"âm"}</small></span><span class="candidate-score">${number(c.score,2)}</span>`;
    button.addEventListener("click",()=>select(c.id));list.append(button);
  }
}
function sceneList() {
  const list=$("scene-list");list.replaceChildren();
  for(const scene of state.manifest.scenes) {
    const button=document.createElement("button");button.className="scene-button";button.dataset.scene=scene.id;
    button.setAttribute("aria-pressed",String(scene.id===state.scene?.id));
    const image=document.createElement("img");image.src=scene.before.image;image.alt="";
    const text=document.createElement("span");text.innerHTML=`<strong>${number((scene.before.wavelength_um+scene.after.wavelength_um)/2,3)} µm</strong><small>${Math.round(scene.baseline_days)} ngày · Δλ ${number(scene.target_wavelength_delta_nm,2)} nm</small>`;
    button.append(image,text);button.addEventListener("click",()=>loadScene(scene));list.append(button);
  }
}
function evidenceContent() {
  const s=state.scene;
  $("evidence-content").innerHTML=`<table><thead><tr><th>Thông tin</th><th>Trước</th><th>Sau</th></tr></thead><tbody><tr><td>Ngày quan sát</td><td>${s.before.date}</td><td>${s.after.date}</td></tr><tr><td>λ tại vị trí dự kiến</td><td>${number(s.before.wavelength_um,5)} µm</td><td>${number(s.after.wavelength_um,5)} µm</td></tr><tr><td>Pipeline IRSA</td><td>${s.before.pipeline_version}</td><td>${s.after.pipeline_version}</td></tr></tbody></table><p>RMS từ ${s.alignment.matched_stars} sao nền: ${number(s.alignment.rms_before_px,3)} → ${number(s.alignment.rms_after_px,3)} pixel. Đây là residual của các sao dùng để fit, chưa phải kiểm tra astrometry độc lập.</p><p>WCS-WAVE có độ chính xác dùng cho trực quan hóa, cỡ 1 nm theo IRSA. Các Δλ nhỏ hơn mức này là giá trị tính từ bảng tra, không phải độ chính xác hiệu chuẩn được cam kết.</p><p>Noise sau nội suy và convolution có tương quan. Highlight chỉ nằm trong vùng có dữ liệu và qua gate bước sóng cục bộ ≤ ½ bề rộng phổ. Vị trí dự kiến dùng ngoại suy tuyến tính từ Luhman 2014, chưa hiệu chỉnh parallax.</p><h3>Cutout gốc</h3><p><a href="${s.before.cutout_url}" target="_blank" rel="noopener noreferrer">Tải cutout trước từ IRSA</a> · <a href="${s.after.cutout_url}" target="_blank" rel="noopener noreferrer">Tải cutout sau từ IRSA</a></p>`;
  $("download-fits").href=s.fits;
}
async function loadScene(scene) {
  const generation=++state.loading;
  $("load-state").hidden=false;$("load-state").textContent="Đang tải cặp ảnh và bằng chứng…";
  try {
    const [before,after,difference,pixels]=await Promise.all([loadImage(scene.before.image),loadImage(scene.after.image),loadImage(scene.difference_image),getJson(scene.array_json)]);
    if(generation!==state.loading)return;
    state.scene=scene;state.images={before,after,difference};state.pixels=pixels;state.center=[32,32];state.zoom=1;
    $("zoom").value="1";$("zoom-value").textContent="1×";
    $("baseline").textContent=`${number(scene.baseline_days,1)} ngày`;
    $("wavelength").textContent=`${number((scene.before.wavelength_um+scene.after.wavelength_um)/2,3)} µm`;
    $("alignment").textContent=scene.alignment.rms_after_px===null?"Chỉ dùng WCS":`${number(scene.alignment.rms_after_px,3)} px`;
    $("date-before").textContent=`Trước · ${scene.before.date}`;$("date-after").textContent=`Sau · ${scene.after.date}`;
    $("load-state").hidden=true;candidateList();sceneList();evidenceContent();select("target");setMode(state.mode);
    ["download-manifest","save-review","export-reviews"].forEach(id=>$(id).disabled=false);
  } catch(error) {
    $("load-state").hidden=false;$("load-state").textContent=`Không tải được dữ liệu: ${error.message}. Chạy web bằng scripts/serve_demo.py rồi tải lại trang.`;
  }
}

document.querySelectorAll("[data-mode]").forEach(button=>button.addEventListener("click",()=>setMode(button.dataset.mode)));
$("wipe").addEventListener("input",e=>{state.wipe=Number(e.target.value)/100;render();});
$("zoom").addEventListener("input",e=>{state.zoom=Number(e.target.value);$("zoom-value").textContent=`${number(state.zoom,state.zoom%1?2:0)}×`;render();});
["show-prior","show-residuals"].forEach(id=>$(id).addEventListener("change",render));
$("reset-view").addEventListener("click",()=>{state.center=[32,32];state.zoom=1;state.wipe=.5;$("wipe").value="50";$("zoom").value="1";$("zoom-value").textContent="1×";setMode("wipe");});
$("select-target").addEventListener("click",()=>{if(state.scene)select("target");});
$("focus-selection").addEventListener("click",()=>{
  if(!state.scene)return;
  const p=state.selected==="target"?state.scene.target_prior[1]:state.scene.candidates.find(c=>c.id===state.selected);
  state.center=[p.x+.5,63-p.y+.5];state.zoom=3;$("zoom").value="3";$("zoom-value").textContent="3×";render();
});
$("evidence-open").addEventListener("click",()=>{if(state.scene)$("evidence-dialog").showModal();});
$("evidence-close").addEventListener("click",()=>$("evidence-dialog").close());
$("download-manifest").addEventListener("click",()=>download("wise0855-evidence.json",state.manifest));
$("save-review").addEventListener("click",()=>{
  const s=state.scene;
  reviews[keyForSelection()]={scene_id:s.id,selection:state.selected,status:$("review-status").value,note:$("review-note").value,
    saved_at:new Date().toISOString(),analysis_sha256:state.manifest.analysis_sha256,
    input_sha256:[s.before.sha256,s.after.sha256],target_detection:"unconfirmed"};
  try{localStorage.setItem("nosleepclub.reviews.v1",JSON.stringify(reviews));$("review-feedback").textContent="Đã lưu nhận xét trên trình duyệt này.";$("clear-review").hidden=false;}
  catch{$("review-feedback").textContent="Trình duyệt không cho lưu. Chọn Xuất JSON để giữ nhận xét.";}
});
$("export-reviews").addEventListener("click",()=>download("wise0855-reviews.json",{schema_version:1,reviews:Object.values(reviews)}));
$("clear-review").addEventListener("click",()=>{
  const key=keyForSelection(),next={...reviews};delete next[key];
  try{localStorage.setItem("nosleepclub.reviews.v1",JSON.stringify(next));reviews=next;loadReview();$("review-feedback").textContent="Đã xóa nhận xét của vùng này.";}
  catch{$("review-feedback").textContent="Trình duyệt không cho cập nhật lưu trữ. Nhận xét vẫn được giữ lại.";}
});
let dragging=false;
function pointerPixel(event) {
  const rect=canvas.getBoundingClientRect(), c=crop();
  let fraction=(event.clientX-rect.left)/rect.width;
  if(state.mode==="side")fraction=(fraction*2)%1;
  return {x:Math.max(0,Math.min(63,Math.floor(c.x+fraction*c.width))),
    y:Math.max(0,Math.min(63,63-Math.floor(c.y+(event.clientY-rect.top)/rect.height*c.width)))};
}
canvas.addEventListener("pointerdown",event=>{
  if(!state.scene)return;
  if(state.mode==="wipe"){dragging=true;canvas.setPointerCapture(event.pointerId);}
  else {const p=pointerPixel(event),near=state.scene.candidates.find(c=>Math.hypot(c.x-p.x,c.y-p.y)<3);if(near)select(near.id);}
});
canvas.addEventListener("pointermove",event=>{
  if(!state.scene)return;
  if(dragging){const rect=canvas.getBoundingClientRect();state.wipe=Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width));$("wipe").value=String(Math.round(state.wipe*100));render();}
  const {x,y}=pointerPixel(event),a=state.pixels.before[y][x],b=state.pixels.after[y][x];
  $("pixel-readout").textContent=`Pixel ${x},${y} · ${a===null?"thiếu":number(a,3)} / ${b===null?"thiếu":number(b,3)} MJy/sr`;
});
["pointerup","pointercancel","lostpointercapture"].forEach(name=>canvas.addEventListener(name,()=>dragging=false));
canvas.addEventListener("keydown",event=>{
  if(state.mode!=="wipe"||!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
  event.preventDefault();state.wipe=event.key==="Home"?0:event.key==="End"?1:Math.max(0,Math.min(1,state.wipe+(event.key==="ArrowLeft"?-.05:.05)));
  $("wipe").value=String(state.wipe*100);render();
});
document.addEventListener("visibilitychange",()=>{if(document.hidden&&state.mode==="blink")setMode("wipe");});
getJson("data/manifest.json").then(async manifest=>{state.manifest=manifest;await loadScene(manifest.scenes[0]);})
  .catch(error=>{$("load-state").textContent=`Không tải được manifest: ${error.message}. Chạy scripts/serve_demo.py để mở bản demo.`;});

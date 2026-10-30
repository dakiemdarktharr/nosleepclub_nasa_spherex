"use strict";

const $ = (id) => document.getElementById(id);
const canvas = $("sky");
const ctx = canvas.getContext("2d");
const state = { manifest: null, scene: null, images: {}, pixels: null, mode: "wipe", wipe: .5,
  zoom: 1, center: [32,32], selected: "target", blinkAfter: false, timer: null, loading: 0 };
const number = (value, digits=2) => Number(value).toLocaleString("vi-VN", {maximumFractionDigits:digits, minimumFractionDigits:digits});
let reviews = {};
let remoteStorage = false;
try { reviews = JSON.parse(localStorage.getItem("nosleepclub.reviews.v1") || "{}"); } catch { reviews = {}; }

async function reviewApi(method="GET", body) {
  const response = await fetch("/api/reviews", {method, credentials:"same-origin", cache:"no-store",
    headers:body?{"Content-Type":"application/json"}:{}, body:body?JSON.stringify(body):undefined});
  if(!response.ok)throw new Error(`HTTP ${response.status}`);
  return response.json();
}
async function syncReviews() {
  if(location.protocol!=="https:")return;
  try {
    const result=await reviewApi();
    remoteStorage=true;
    for(const item of result.reviews) {
      const key=`${item.analysis_sha256}:${item.scene_id}:${item.selection}`;
      if(!reviews[key]||reviews[key].saved_at<item.saved_at)reviews[key]=item;
    }
    if(state.scene)loadReview();
  } catch { remoteStorage=false; }
  $("storage-status").textContent=remoteStorage?"MongoDB":"Trình duyệt";
}

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
function ellipse(covariance, factor=2.30) {
  const a=covariance[0][0],b=covariance[0][1],d=covariance[1][1];
  const root=Math.hypot(a-d,2*b), major=Math.max(0,(a+d+root)/2),minor=Math.max(0,(a+d-root)/2);
  return {rx:Math.sqrt(factor*major),ry:Math.sqrt(factor*minor),angle:.5*Math.atan2(2*b,a-d)};
}
function canvasLabel(text,x,y,width,height,offset,color) {
  const scale=canvas.width/Math.max(canvas.getBoundingClientRect().width,1);
  const fontSize=13*scale,padding=6*scale,margin=5*scale;
  ctx.save();ctx.font=`600 ${fontSize}px "Be Vietnam Pro", Arial, sans-serif`;
  ctx.textAlign="left";ctx.textBaseline="middle";ctx.setLineDash([]);
  const boxWidth=Math.min(ctx.measureText(text).width+2*padding,width-2*margin),boxHeight=fontSize*1.65+padding;
  const left=Math.max(offset+margin,Math.min(offset+width-boxWidth-margin,x));
  const top=Math.max(margin,Math.min(height-boxHeight-margin,y-boxHeight/2));
  ctx.fillStyle="#070d16";ctx.fillRect(left,top,boxWidth,boxHeight);
  ctx.lineWidth=scale;ctx.strokeStyle=color;ctx.strokeRect(left,top,boxWidth,boxHeight);
  ctx.fillStyle=color;ctx.fillText(text,left+padding,top+boxHeight/2,boxWidth-2*padding);
  ctx.restore();
}
function overlays(width,height,offset=0) {
  const scene=state.scene;
  ctx.save();ctx.beginPath();ctx.rect(offset,0,width,height);ctx.clip();
  if (scene.measured_positions && $("show-motion").checked) {
    const points=scene.measured_positions.map(p=>xy(p.x,p.y,width,height,offset));
    ctx.strokeStyle="#a4e4d9";ctx.lineWidth=2;ctx.setLineDash([]);
    ctx.beginPath();ctx.moveTo(...points[0]);ctx.lineTo(...points[1]);ctx.stroke();
    scene.measured_positions.forEach((p,i)=>{
      const [x,y]=points[i],c=p.covariance_px2;
      const e=ellipse([[c[0][0],-c[0][1]],[-c[1][0],c[1][1]]]);
      const scale=width/crop().width;
      ctx.strokeStyle=i?"#f7be66":"#a4e4d9";ctx.fillStyle=ctx.strokeStyle;
      ctx.beginPath();ctx.ellipse(x,y,e.rx*scale,e.ry*scale,e.angle,0,2*Math.PI);ctx.stroke();
      ctx.beginPath();ctx.arc(x,y,3,0,2*Math.PI);ctx.fill();
      if(state.selected==="target") {
        const scale=canvas.width/Math.max(canvas.getBoundingClientRect().width,1);
        canvasLabel(i?"Sau · đo":"Trước · đo",x+14*scale,y+(i?25:-25)*scale,width,height,offset,i?"#ffd99b":"#d6fff6");
      }
    });
  }
  if ($("show-prior").checked) {
    const a=scene.target_prior[0], b=scene.target_prior[1];
    const [ax,ay]=xy(a.x,a.y,width,height,offset),[bx,by]=xy(b.x,b.y,width,height,offset);
    const radius=3.4/crop().width*width;
    ctx.strokeStyle="#c8afff";ctx.lineWidth=2;ctx.setLineDash([6,5]);
    ctx.beginPath();ctx.arc((ax+bx)/2,(ay+by)/2,radius,0,Math.PI*2);ctx.stroke();
    ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(ax,ay);ctx.lineTo(bx,by);ctx.stroke();ctx.setLineDash([]);
    for (const [x,y] of [[ax,ay],[bx,by]]) {ctx.beginPath();ctx.moveTo(x-5,y);ctx.lineTo(x+5,y);ctx.moveTo(x,y-5);ctx.lineTo(x,y+5);ctx.stroke();}
    if (state.selected==="target") canvasLabel("WISE 0855 · dự kiến",ax-radius,ay-radius-32,width,height,offset,"#e0d2ff");
  }
  if ($("show-residuals").checked) for (const candidate of scene.candidates) {
    const [x,y]=xy(candidate.x,candidate.y,width,height,offset);
    const selected=state.selected===candidate.id;
    ctx.lineWidth=selected?3:1.8;ctx.strokeStyle=candidate.score>0?"#f7be66":"#82d7f1";
    ctx.beginPath();ctx.arc(x,y,Math.max(12,2/crop().width*width),0,Math.PI*2);ctx.stroke();
    if(selected)canvasLabel(`${candidate.id} ${candidate.score>0?"+":"−"}`,x+14,y-28,width,height,offset,candidate.score>0?"#ffd99b":"#bdefff");
  }
  ctx.restore();
}
function render() {
  if (!state.scene || !state.images.before) return;
  canvas.classList.toggle("side",state.mode==="side");
  canvas.width=1024;canvas.height=state.mode==="side"?512:1024;
  $("fov-readout").textContent=`6,15″ / pixel gốc · khung ${number(64/state.zoom*6.15/60,2)}′`;
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
    ctx.fillStyle="#17314a";ctx.font='24px "Be Vietnam Pro", Arial, sans-serif';ctx.textAlign="center";ctx.fillText("↔",split,520);ctx.textAlign="left";
  } else {
    drawImage(state.images[state.mode==="difference"?"difference":state.blinkAfter?"after":"before"],0,1024,1024);
    overlays(1024,1024);
  }
  $("mode-badge").textContent={wipe:"Kéo vạch để so sánh",side:"Cùng lưới tọa độ và mức kéo sáng",difference:"Vàng: dương / xanh: âm",blink:state.blinkAfter?"Đang xem ảnh sau":"Đang xem ảnh trước"}[state.mode];
}
function setMode(mode) {
  if (state.timer) clearInterval(state.timer);state.timer=null;
  state.mode=mode;state.blinkAfter=false;
  $("mode-instruction").textContent={wipe:"Kéo vạch qua chấm được đánh dấu để so vị trí trước và sau.",side:"Hai ảnh đặt cạnh nhau: nhìn vị trí chấm so với các sao xung quanh.",difference:"Vùng sáng/tối cho biết ảnh sau khác ảnh trước; nhiễu cũng có thể tạo dấu như vậy.",blink:"Ảnh trước và sau đổi phiên. Tìm chấm nhảy chỗ trong khi các sao xung quanh đứng yên."}[mode];
  document.querySelectorAll("[data-mode]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.mode===mode)));
  $("wipe-control").hidden=mode!=="wipe";
  $("view-note").textContent=mode==="difference"
    ?"Ảnh sau trừ ảnh trước đã cross-convolution PSF và hiệu chỉnh flux/nền để hiển thị. Vùng xanh xám thiếu dữ liệu hoặc không qua gate phổ. Residual không phải sigma đã hiệu chuẩn."
    :state.scene?.kind==="coadd"?"Hai ảnh cùng mức kéo sáng. Chấm và ellipse 68% là vị trí fit trên pixel gốc, độc lập từng epoch. Xanh xám là pixel thiếu dữ liệu. Ảnh cộng đã làm mượt chỉ dùng để xem; vị trí dự kiến nét đứt là ngoại suy cũ, chưa có parallax."
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
  $("review-feedback").textContent="";
  $("clear-review").hidden=!saved;
}
function select(id) {
  state.selected=id;
  $("select-target").setAttribute("aria-pressed",String(id==="target"));
  document.querySelectorAll(".candidate-button").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.id===id)));
  const scene=state.scene,detail=$("selection-detail");
  if(id==="target" && scene.kind==="coadd") {
    const m=scene.motion;
    detail.innerHTML=`<div class="selection-title">Centroid ePSF · pixel gốc</div><p>Fit vị trí riêng cho từng epoch; biên độ riêng từng ảnh. Không buộc theo vector chuyển động dự báo.</p>${["before","after"].map((key,i)=>{
      const p=m["target_"+key],c=scene.measured_positions[i].covariance_px2;
      return `<div class="centroid-epoch"><strong>${i?"Sau":"Trước"} · MJD ${number(p.effective_mjd,3)}</strong><dl><dt>RA / Dec (độ)</dt><dd>${number(p.ra_deg,6)}<br>${number(p.dec_deg,6)}</dd><dt>σ đông / bắc</dt><dd>${number(Math.sqrt(c[0][0])*6.15,2)}″ / ${number(Math.sqrt(c[1][1])*6.15,2)}″</dd></dl></div>`;
    }).join("")}<p>Sai số trục có hạng căn chỉnh và sao giữ lại. ${m.gaia_reference?"Tọa độ neo Gaia đã lan truyền đến epoch; sai số chung giữa hai epoch được xử lý riêng trong covariance chuyển động.":"Tọa độ tương đối theo WCS SPHEREx, chưa neo vào Gaia."}</p><dl><dt>RMS sao giữ lại</dt><dd>${number(m.holdout_rms_arcsec,2)}″</dd><dt>Số sao căn chỉnh / giữ lại</dt><dd>${m.training_reference_positions.length} / ${m.heldout_controls.length}</dd><dt>Bootstrap / epoch</dt><dd>${m.bootstrap_before.draws}</dd></dl>`;
  } else if(id==="target") {
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
  if(!state.scene.candidates.length){list.textContent="0 ứng viên";return;}
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
    const text=document.createElement("span");text.innerHTML=scene.kind==="coadd"
      ?`<strong>${scene.label}</strong><small>${(scene.motion.spectral_configuration||scene.motion.id)==="strict"?"Phổ chặt · cấu hình chính":"Phổ rộng · kiểm tra độ nhạy"}</small>`
      :`<strong>Ảnh đơn · ${number((scene.before.wavelength_um+scene.after.wavelength_um)/2,3)} µm</strong><small>${Math.round(scene.baseline_days)} ngày · Δλ ${number(scene.target_wavelength_delta_nm,2)} nm</small>`;
    button.append(image,text);button.addEventListener("click",()=>loadScene(scene));list.append(button);
  }
}
function evidenceContent() {
  const s=state.scene;
  if(s.motion?.gaia_reference) {gaiaEvidence(s);$("download-fits").href=s.fits;return;}
  if(s.kind==="coadd") {
    const m=s.motion, controls=m.real_background_injection_controls;
    $("evidence-content").innerHTML=`<h3>${s.label} · ${m.id==="strict"?"cấu hình phổ chặt, chính":"cấu hình phổ rộng, kiểm tra độ nhạy"}</h3><p>Các cặp được chọn trước khi fit mục tiêu, trong 4,55–4,94 µm; |Δλ| / bề rộng phổ trung bình ≤ ${number(m.tolerance_bandwidth,2)}. Hai epoch dùng cùng trọng số cho từng cặp phổ. Đây là ảnh tổng hợp nhiều kênh, không phải nhiều lần chụp một bước sóng giống hệt.</p><table><thead><tr><th>Thông tin</th><th>Trước</th><th>Sau</th></tr></thead><tbody><tr><td>Cửa sổ ngày UTC</td><td>${s.before.date_start} → ${s.before.date_end}</td><td>${s.after.date_start} → ${s.after.date_end}</td></tr><tr><td>Số ảnh</td><td>${s.before.inputs.length}</td><td>${s.after.inputs.length}</td></tr><tr><td>λ trung bình có trọng số</td><td>${number(s.before.wavelength_um,5)} µm</td><td>${number(s.after.wavelength_um,5)} µm</td></tr><tr><td>Pipeline IRSA</td><td>${s.before.pipeline_version}</td><td>${s.after.pipeline_version}</td></tr></tbody></table><h3>Phương pháp và sai số</h3><p>CWAVE/CBAND khoa học đầy đủ và ePSF chính thức của IRSA. Fit trên pixel gốc: centroid chung trong mỗi epoch, biên độ và mặt phẳng nền riêng từng ảnh. Không dùng vị trí dự báo để ràng buộc vector dịch chuyển. ${m.bootstrap_before.draws} mô phỏng noise/epoch kiểm tra covariance; thêm hạng sai số căn chỉnh và RMS của ${m.heldout_controls.length} sao không tham gia fit căn chỉnh. RMS giữ lại: ${number(m.holdout_rms_arcsec,3)}″.</p><p>Khẩu độ bán kính 2,5 pixel, vành nền 4–6 pixel; truyền trọng số ngược về pixel gốc để giữ covariance nội suy. Vẫn giả định noise pixel gốc và các exposure độc lập. Phủ khẩu độ trước/sau: ${number(m.coadd_snr_before.coverage*100,1)}% / ${number(m.coadd_snr_after.coverage*100,1)}%. So ảnh đơn dùng cùng mặt nạ hợp lệ của ảnh cộng; đây là S/N có điều kiện tại vị trí fit.</p><p>Mahalanobis 2 chiều = ${number(m.mahalanobis_distance,2)}; không diễn giải thành Gaussian sigma hay xác suất phát hiện. Dự báo ngoài dùng Luhman 2014 và parallax 0,454″ với quỹ đạo Trái Đất; hai epoch chưa đủ để fit riêng proper motion và parallax.</p><h3>Kiểm tra và giới hạn còn mở</h3><p>Nguồn giả trên nền thật, khác vùng mục tiêu: ${controls.map(c=>`${c.kind==="stationary"?"đứng yên":"dịch chuyển"}: sai lệch hồi phục ${number(Math.hypot(...c.recovered_delta_px.map((v,i)=>v-c.injected_delta_px[i]))*6.15,2)}″, D<sub>M</sub> ${number(c.error_mahalanobis,2)}`).join("; ")}. Giữ nguyên noise map, chưa thêm shot noise nguồn. Một vị trí không đại diện completeness hoặc false-positive rate.</p><p>Đổi chéo tập sao tham chiếu chưa thực hiện được: không đủ 2 sao đạt S/N trong một exposure (${m.reference_swap_unavailable_reason.split(": ").pop()}). Chưa neo Gaia; mới so tâm/bề rộng phổ, chưa so toàn bộ đáp ứng phổ. Sai số ePSF, blending và noise thiết bị tương quan chưa được mô phỏng đầy đủ. Không suy ra biến thiên thông lượng từ ảnh tổng hợp này.</p><h3>Ảnh thành phần & trọng số phổ</h3><div class="evidence-table"><table><thead><tr><th>Cutout trước (IRSA)</th><th>Cutout sau (IRSA)</th><th>λ trước / sau (µm)</th><th>Trọng số</th></tr></thead><tbody>${m.spectral_pairs.map(p=>`<tr><td><a href="${p.before.cutout_url}" target="_blank" rel="noopener noreferrer">${p.before.obs_id}</a></td><td><a href="${p.after.cutout_url}" target="_blank" rel="noopener noreferrer">${p.after.obs_id}</a></td><td>${number(p.before_um,4)} / ${number(p.after_um,4)}</td><td>${number(p.weight,4)}</td></tr>`).join("")}</tbody></table></div><p><a href="data/${s.id}/evidence.json" download>JSON kết quả, SHA-256 đầu vào & hiệu chuẩn</a> · <a href="data/motion/results.json" download>Toàn bộ phép đo và covariance</a></p>`;
    $("download-fits").href=s.fits;return;
  }
  $("evidence-content").innerHTML=`<table><thead><tr><th>Thông tin</th><th>Trước</th><th>Sau</th></tr></thead><tbody><tr><td>Ngày quan sát</td><td>${s.before.date}</td><td>${s.after.date}</td></tr><tr><td>λ tại vị trí dự kiến</td><td>${number(s.before.wavelength_um,5)} µm</td><td>${number(s.after.wavelength_um,5)} µm</td></tr><tr><td>Pipeline IRSA</td><td>${s.before.pipeline_version}</td><td>${s.after.pipeline_version}</td></tr></tbody></table><p>RMS từ ${s.alignment.matched_stars} sao nền: ${number(s.alignment.rms_before_px,3)} → ${number(s.alignment.rms_after_px,3)} pixel. Đây là residual của các sao dùng để fit, chưa phải kiểm tra astrometry độc lập.</p><p>WCS-WAVE có độ chính xác dùng cho trực quan hóa, cỡ 1 nm theo IRSA. Các Δλ nhỏ hơn mức này là giá trị tính từ bảng tra, không phải độ chính xác hiệu chuẩn được cam kết.</p><p>Noise sau nội suy và convolution có tương quan. Highlight chỉ nằm trong vùng có dữ liệu và qua gate bước sóng cục bộ ≤ ½ bề rộng phổ. Vị trí dự kiến dùng ngoại suy tuyến tính từ Luhman 2014, chưa hiệu chỉnh parallax.</p><h3>Cutout gốc</h3><p><a href="${s.before.cutout_url}" target="_blank" rel="noopener noreferrer">Tải cutout trước từ IRSA</a> · <a href="${s.after.cutout_url}" target="_blank" rel="noopener noreferrer">Tải cutout sau từ IRSA</a></p>`;
  $("download-fits").href=s.fits;
}
function motionPanel(scene) {
  const active=scene.kind==="coadd";$("motion-panel").hidden=!active;$("motion-overlay-label").hidden=!active;
  $("science-status").textContent=active?"Dấu hiệu chuyển động · cần xác minh thêm":"Ảnh đơn · chưa đo chuyển động độc lập";
  $("target-subtitle").textContent=active?"Centroid fit độc lập từng epoch":"Vùng vị trí dự kiến";
  if(!active)return;
  const m=scene.motion;
  const spectral=m.spectral_configuration||m.id;
  $("configuration-label").textContent=`${scene.label} · ${spectral==="strict"?"Phổ chặt, cấu hình chính":"Phổ rộng, kiểm tra độ nhạy"}`;
  $("motion-value").textContent=`${number(m.displacement_arcsec,2)}″ ± ${number(m.radial_error_arcsec,2)}″`;
  $("motion-components").textContent=`Đông ${number(m.east_arcsec,2)}″ · Bắc ${number(m.north_arcsec,2)}″ · ${number(scene.baseline_days,1)} ngày`;
  $("snr-rows").innerHTML=["before","after"].map((key,i)=>`<tr><td>${i?"Tháng 4/2026":"Tháng 11/2025"}</td><td>${number(m["best_single_snr_"+key],1)}</td><td><strong>${number(m["coadd_snr_"+key].snr,1)}</strong></td></tr>`).join("");
  $("snr-note").textContent=spectral==="broad"?`S/N tăng ${number(m.coadd_snr_before.snr/m.best_single_snr_before,1)}× / ${number(m.coadd_snr_after.snr/m.best_single_snr_after,1)}×. Cùng trọng số phổ; cấu hình rộng là kiểm tra độ nhạy.`:"Phổ chặt cho dịch chuyển cùng hướng, nhưng S/N không tăng rõ so với ảnh đơn. Giữ lại để đối chiếu.";
  if(m.gaia_reference) {
    const stationary=m.injection_diagnostics.groups.find(g=>g.kind==="stationary"&&g.flux_scale===1);
    $("motion-limit").textContent=`Gaia: ${m.training_source_ids.length} sao căn chỉnh + ${m.heldout_controls.length} sao giữ lại. Đổi tập sao làm vector đổi ${number(m.reference_swap.change_arcsec,2)}″. Chưa xác nhận: nguồn giả đứng yên cùng độ sáng vẫn có RMS lệch ${number(stationary.rms_error_arcsec,2)}″ trên 8 nền ảnh khác.`;
  } else {
    const stationary=m.real_background_injection_controls[0];
    $("motion-limit").textContent=`Bản trước Gaia: chỉ ${m.heldout_controls.length} sao giữ lại; kiểm tra đổi tập sao chưa đủ dữ liệu. Nguồn giả đứng yên ở nền khác lệch ${number(Math.hypot(...stationary.recovered_delta_px)*6.15,2)}″. Xem cấu hình Gaia để kiểm tra lại.`;
  }
  const sx=27,ox=207,oy=90,point=(e,n)=>[ox+e*sx,oy-n*sx];
  const [mx,my]=point(m.east_arcsec,m.north_arcsec),[px,py]=point(m.predicted_motion.east_arcsec,m.predicted_motion.north_arcsec);
  const c=m.covariance_arcsec2,e=ellipse([[c[0][0],-c[0][1]],[-c[1][0],c[1][1]]]);
  $("motion-chart").innerHTML=`<path d="M18 ${oy}H261 M${ox} 14V151" stroke="#d2dee6" fill="none"/><g fill="#d1dce8" font-size="14"><text x="17" y="${oy+15}">−7″</text><text x="${ox+4}" y="${oy+15}">0</text><text x="233" y="${oy+15}">+2″</text><text x="${ox+4}" y="22">+2″ Bắc</text><text x="209" y="151">Đông →</text></g><path d="M${ox} ${oy}L${px} ${py}" stroke="#c3acff" stroke-dasharray="4 3"/><path d="M${ox} ${oy}L${mx} ${my}" stroke="#96dfd0" stroke-width="2"/><ellipse cx="${mx}" cy="${my}" rx="${e.rx*sx}" ry="${e.ry*sx}" transform="rotate(${e.angle*180/Math.PI} ${mx} ${my})" fill="#b7e6dc" fill-opacity=".15" stroke="#96dfd0"/><circle cx="${mx}" cy="${my}" r="4" fill="#96dfd0"/><path d="M${px} ${py-5}l5 5 -5 5 -5 -5Z" fill="white" stroke="#c3acff" stroke-width="1.5"/>`;
}
function gaiaEvidence(s) {
  const m=s.motion,g=state.gaia,loo=m.leave_one_out.filter(v=>v.success);
  $("evidence-content").innerHTML=`<h3>${s.label}</h3><p>Giữ cùng exposure và trọng số phổ của bản trước; cutout rộng 0,32° thay cho 0,12°. Gaia DR3: ${g.catalog_count} nguồn G&lt;18,5 trong bán kính 0,25°, ${g.candidate_count} ghép cô lập ban đầu, ${g.selected_count} sao đạt quality/S/N.</p><p>Lan truyền vị trí từ epoch Gaia 2016.0 bằng proper motion và parallax với vị trí barycentric Trái Đất. Truyền đủ covariance 5 tham số/correlation của mỗi sao. Cắt RUWE ≤1,4, ≥9 visibility periods, giới hạn nhiễu nhiều nguồn và chuyển động lớn. Quy tắc chọn và source ID có trong JSON.</p><p>${m.training_source_ids.length} sao fit translation cục bộ, ${m.heldout_controls.length} sao giữ ngoài fit. Đổi tập sao: ${m.reference_swap.success?`chạy được, vector đổi ${number(m.reference_swap.change_arcsec,3)}″`:`chưa chạy được: ${m.reference_swap.reason}`}. Bỏ từng sao: ${loo.length}/${m.leave_one_out.length} lượt chạy được, đổi lớn nhất ${number(Math.max(...loo.map(v=>v.change_arcsec)),3)}″. Affine: ${m.affine_sensitivity.success?`vector đổi ${number(m.affine_sensitivity.change_arcsec,3)}″`:`chưa chạy được: ${m.affine_sensitivity.reason}`}.</p><p>Covariance gồm noise centroid trên pixel gốc (${m.bootstrap_before.draws} mô phỏng/epoch), calibration (${m.calibration_bootstrap.accepted}/${m.calibration_bootstrap.draws} bootstrap ghép cặp sao tham chiếu) và second moment của residual sao giữ lại. Mỗi draw Gaia được dùng chung qua các exposure/epoch để giữ tương quan. Sai số này có điều kiện với ePSF và mô hình nền, chưa phải ngân sách hệ thống đầy đủ.</p><p>Injection: 8 vị trí × hai độ sáng × hai loại chuyển động. Giữ nguyên noise map, không thêm shot noise, dùng ePSF giống nhau để tiêm và fit. Không dùng nguồn giả để hiệu chỉnh vector mục tiêu hoặc đổi sai số cho đẹp. RMS lệch còn phụ thuộc nền; xem bảng Gaia bên dưới vùng so sánh.</p><p>Gaia cũng được dùng trong hiệu chuẩn WCS SPHEREx: các sao giữ lại độc lập với fit cục bộ này, không phải một catalog xác minh hoàn toàn độc lập. Hai epoch chưa tách được proper motion và parallax. Cấu hình phổ rộng/chặt dùng chung ảnh; tâm/bề rộng tương thích chưa thay thế kiểm tra đầy đủ đáp ứng phổ.</p><h3>Ảnh thành phần</h3><div class="evidence-table"><table><thead><tr><th>IRSA trước</th><th>IRSA sau</th><th>λ trước / sau (µm)</th><th>Trọng số</th></tr></thead><tbody>${m.spectral_pairs.map(p=>`<tr><td><a href="${p.before.cutout_url}" target="_blank" rel="noopener noreferrer">${p.before.obs_id}</a></td><td><a href="${p.after.cutout_url}" target="_blank" rel="noopener noreferrer">${p.after.obs_id}</a></td><td>${number(p.before_um,4)} / ${number(p.after_um,4)}</td><td>${number(p.weight,4)}</td></tr>`).join("")}</tbody></table></div><p><a href="${s.gaia_evidence}" download>Tải kết quả Gaia, covariance, CV và hash đầy đủ</a> · <a href="https://gaia.aip.de/metadata/gaiadr3/gaia_source/" target="_blank" rel="noopener noreferrer">Mô tả trường Gaia DR3</a></p>`;
}
function setupGaiaPanel() {
  $("gaia-validation").hidden=false;
  const gaiaNav=$("gaia-nav");if(gaiaNav)gaiaNav.hidden=false;
  const g=state.gaia,map=state.gaiaMap;
  const training=g.references.filter(r=>r.split==="training").length;
  $("gaia-counts").textContent=`${g.catalog_count} nguồn · ${g.selected_count} sao đạt chuẩn · ${training} căn chỉnh / ${g.selected_count-training} giữ lại`;
  $("reference-field").src=map.image;
  const select=$("reference-select");select.replaceChildren();
  for(const [i,r] of map.references.entries()) {
    const option=document.createElement("option");option.value=r.source_id;option.textContent=`${i+1}. Gaia ${r.source_id} · ${r.split==="training"?"căn chỉnh":"giữ lại"}`;select.append(option);
  }
  $("reference-overlay").innerHTML=map.references.map((r,i)=>`<g data-source="${r.source_id}" class="reference-marker ${r.split}" role="button" tabindex="0" aria-label="Sao ${i+1}, Gaia ${r.source_id}, ${r.split==="training"?"căn chỉnh":"giữ lại"}"><circle cx="${r.x+.5}" cy="${192-r.y-.5}" r="5" class="reference-hit"/><circle cx="${r.x+.5}" cy="${192-r.y-.5}" r="1.8"/><text x="${r.x+3}" y="${192-r.y-2}">${i+1}</text></g>`).join("")+`<path class="map-target" d="M91 96H101 M96 91V101"/><text class="map-target-label" x="99" y="103">WISE</text>`;
  $("reference-overlay").querySelectorAll("[data-source]").forEach(marker=>{
    const choose=()=>{select.value=marker.dataset.source;showReference();};
    marker.addEventListener("click",choose);marker.addEventListener("keydown",event=>{if(["Enter"," "].includes(event.key)){event.preventDefault();choose();}});
  });
  select.addEventListener("change",showReference);
  $("stability-rows").innerHTML=[...g.configurations].reverse().map(c=>{
    const loo=c.leave_one_out.filter(v=>v.success);
    return `<tr><td>${c.spectral_configuration==="broad"?"Rộng · 10 ảnh":"Chặt · 2 ảnh"}</td><td>${number(c.holdout_rms_arcsec,2)}″</td><td>${c.reference_swap.success?`${number(c.reference_swap.change_arcsec,2)}″`:"Chưa đạt"}</td><td>${number(Math.max(...loo.map(v=>v.change_arcsec)),2)}″ (${loo.length}/${c.leave_one_out.length})</td><td>${c.affine_sensitivity.success?`${number(c.affine_sensitivity.change_arcsec,2)}″`:"Chưa đạt"}</td></tr>`;
  }).join("");
  gaiaConfiguration("broad");
}
function gaiaConfiguration(spectral) {
  state.gaiaConfig=spectral;
  const m=state.gaia.configurations.find(c=>c.spectral_configuration===spectral);
  const vector=[m.east_arcsec,m.north_arcsec],norm2=vector[0]**2+vector[1]**2;
  const radial=c=>{
    const x=-vector[0]*6.15,y=vector[1]*6.15;
    return Math.sqrt(Math.max(0,(x*x*c[0][0]+2*x*y*c[0][1]+y*y*c[1][1])/norm2));
  };
  $("budget-config").textContent=spectral==="broad"?"· phổ rộng":"· phổ chặt";
  $("uncertainty-budget").innerHTML=[["Noise centroid",m.statistical_covariance_px2],["Căn chỉnh Gaia",m.registration_covariance_px2],["Sao giữ lại",m.holdout_covariance_px2]].map(([label,c])=>`<div><span>${label}</span><strong>${number(radial(c),2)}″</strong></div>`).join("")+`<div class="budget-total"><span>Tổng có điều kiện</span><strong>${number(m.radial_error_arcsec,2)}″</strong></div>`;
  $("injection-rows").innerHTML=m.injection_diagnostics.groups.map(g=>`<tr><td>${number(g.flux_scale,1)}×</td><td>${g.kind==="stationary"?"Đứng yên":"Dịch chuyển"}</td><td>${g.within_68_percent_ellipse}/${g.attempted}${g.failed_or_boundary?` · ${g.failed_or_boundary} lỗi/biên`:""}</td><td>${number(g.rms_error_arcsec,2)}″</td></tr>`).join("");
  $("gaia-conclusion").textContent=`Vector ${number(m.displacement_arcsec,2)}″ ± ${number(m.radial_error_arcsec,2)}″ đổi ${number(m.change_from_previous_arcsec,2)}″ so với bản trước Gaia; chênh vector dự báo ngoài ${number(m.difference_from_external_prediction_arcsec,2)}″. Frame ít thay đổi khi đổi sao, nhưng injection trên nền khác còn lệch lớn: chưa xác nhận sai số hệ thống hoặc chuyển động thiên thể.`;
  showReference();
}
function showReference() {
  const selected=$("reference-select").value,r=state.gaiaMap.references.find(v=>v.source_id===selected);
  if(!r)return;
  $("reference-overlay").querySelectorAll("[data-source]").forEach(marker=>marker.classList.toggle("selected",marker.dataset.source===selected));
  const residual=r[state.gaiaConfig+"_residual_arcsec"];
  $("reference-detail").innerHTML=`<strong>Gaia DR3 ${r.source_id}</strong><dl><dt>Vai trò</dt><dd>${r.split==="training"?"Dùng căn chỉnh":"Giữ ngoài fit"}</dd><dt>RUWE / G</dt><dd>${number(r.ruwe,2)} / ${number(r.g_mag,2)}</dd><dt>Exposure hợp lệ</dt><dd>${r.valid_frames}/20</dd><dt>Khoảng cách ghép ban đầu</dt><dd>${number(r.match_arcsec,2)}″</dd>${residual?`<dt>Residual Đông / Bắc</dt><dd>${number(residual[0],2)}″ / ${number(residual[1],2)}″</dd>`:""}</dl><p>Residual đã trừ chuyển động/parallax Gaia và hiệu chỉnh frame; chỉ sao giữ lại được dùng để đánh giá ngoài fit.</p>`;
}
async function setupAccuracy() {
  try {
    state.joint=await Promise.all([getJson("data/joint/broad.json"),getJson("data/joint/strict.json")]);
    $("accuracy-rows").innerHTML=state.joint.map(p=>p.protocol.control_flux_scales.map(flux=>{
      const g=p.result.groups,a=g.find(x=>x.model==="single"&&x.flux_scale===flux),b=g.find(x=>x.model==="joint"&&x.flux_scale===flux);
      return `<tr><td>${p.result.spectral_configuration==="broad"?"Rộng":"Chặt"}</td><td>${number(flux,1)}×</td><td>${number(a.rms_arcsec,2)}″</td><td>${number(b.rms_arcsec,2)}″</td><td>${a.valid}/${a.attempted} · ${b.valid}/${b.attempted}</td><td>${a.within_68_ellipse}/${a.attempted} · ${b.within_68_ellipse}/${b.attempted}</td></tr>`;
    }).join("")).join("");
    $("accuracy-validation").hidden=false;
  } catch {$("accuracy-validation").hidden=true;}
}
$("accuracy-evidence").addEventListener("click",()=>{
  $("evidence-content").innerHTML=`<h3>Phép thử A/B 0.4.0</h3><p>Fit trên cùng pixel gốc, cùng mặt nạ, ePSF và biên độ tiêm. Cả hai phương pháp dùng cùng solver đa điểm khởi tạo. Mô hình nhiều nguồn thêm ePSF tại vị trí Gaia đã lan truyền; fit biên độ nguồn lân cận và mặt phẳng nền riêng từng exposure bằng phép chiếu SVD. Không buộc centroid WISE theo dự báo ngoài.</p><p>12 vị trí mới được khóa trước khi chạy, tách khỏi tám vị trí cũ. Mỗi vị trí có hai độ sáng và hai vector thật: đứng yên và [0,6; 0,05] pixel. 48 injection/phương pháp/cấu hình. Các injection trên một nền và hai cấu hình phổ có tương quan. Sau khi xem kết quả, các vùng này trở thành dữ liệu phát triển cho lần sau.</p><p>RMS chỉ tính các fit thành công và không chạm biên; cột hợp lệ luôn giữ mẫu số tất cả lượt thử. Ellipse gồm noise mô hình có điều kiện, không bao gồm sai số frame, ePSF, vị trí nguồn lân cận hoặc blending chưa có trong catalog. Chưa thêm shot noise nguồn; tiêm và fit dùng chung họ ePSF. Không xem đây là completeness hoặc hiệu chuẩn xác suất phát hiện.</p><p>Phổ rộng: nguồn 0,5× giảm RMS 1,70″ → 1,57″, số hợp lệ 22/24 → 24/24; nguồn 1× tăng RMS 1,02″ → 1,34″. Chưa đạt tiêu chí cải thiện ở cả hai mức sáng. Giữ số đo Gaia 0.3.0 làm mặc định.</p><div class="evidence-table"><table><thead><tr><th>Phổ</th><th>Mô hình</th><th>Đông / Bắc</th><th>Độ dài</th><th>σ noise theo vector</th></tr></thead><tbody>${state.joint.map(p=>Object.entries(p.result.models).map(([label,m])=>`<tr><td>${p.result.spectral_configuration}</td><td>${label}</td><td>${number(m.east_arcsec,2)}″ / ${number(m.north_arcsec,2)}″</td><td>${number(m.displacement_arcsec,2)}″</td><td>${number(m.conditional_noise_radial_arcsec,2)}″</td></tr>`).join("")).join("")}</tbody></table></div><p>Sai số ở bảng này chỉ là noise có điều kiện, không so trực tiếp với sai số tổng của bản Gaia. Tệp JSON có bootstrap 128 lượt/epoch, danh sách hàng xóm, toàn bộ lượt injection và hash mã nguồn.</p><p>Bước kế: catalog hồng ngoại sâu để kiểm soát nguồn Gaia mờ trong IR, nội suy ePSF có kiểm chứng và kiểm tra đáp ứng phổ. Khóa mô hình trước khi đánh giá trên vùng mới; yêu cầu RMS giảm ở cả hai độ sáng và không tăng lỗi/biên.</p><h3>Lưu nhận xét</h3><p>Bản production lưu vào MongoDB theo phiên trình duyệt bằng cookie HttpOnly. Chưa có tài khoản hoặc đồng bộ giữa thiết bị. Dữ liệu tự hết hạn sau 180 ngày; có thể xuất JSON và xóa nhận xét. Nếu API lỗi, thao tác lưu vẫn giữ bản cục bộ và báo chưa đồng bộ.</p><p><a href="https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html" target="_blank" rel="noopener noreferrer">IRSA: mô hình nhiều nguồn</a> · <a href="https://arxiv.org/abs/2510.01410" target="_blank" rel="noopener noreferrer">Huai et al.: confusion và blending</a></p>`;
  $("evidence-content").insertAdjacentHTML("beforeend",`<p>So trên 22 lượt cùng hợp lệ ở phổ rộng 0,5×: RMS 1,70″ → 1,63″, giảm 4,06%. Bootstrap hậu kiểm theo vùng (2.000 lượt) cho khoảng 95% [0,89%; 7,64%], với chỉ 11 vùng có cặp hợp lệ; chưa phải phép kiểm định xác nhận. <a href="data/joint/summary.json" download>Tải so sánh ghép cặp</a> · <a href="https://github.com/dakiemdarktharr/nosleepclub_nasa_spherex/blob/main/docs/ACCURACY_RESEARCH.md" target="_blank" rel="noopener noreferrer">Nghiên cứu và tiêu chí bước kế</a>.</p>`);
  $("download-fits").href=state.scene.fits;$("evidence-dialog").showModal();
});
async function loadScene(scene) {
  const generation=++state.loading;
  $("workspace").setAttribute("aria-busy","true");
  $("load-state").hidden=false;$("load-state").textContent="Đang tải cặp ảnh và bằng chứng…";
  try {
    const [before,after,difference,pixels]=await Promise.all([loadImage(scene.before.image),loadImage(scene.after.image),loadImage(scene.difference_image),getJson(scene.array_json)]);
    if(generation!==state.loading)return;
    state.scene=scene;state.images={before,after,difference};state.pixels=pixels;state.center=[32,32];state.zoom=scene.kind==="coadd"?2:1;
    $("zoom").value=String(state.zoom);$("zoom-value").textContent=`${state.zoom}×`;
    $("baseline").textContent=`${number(scene.baseline_days,1)} ngày`;
    const isCoadd=scene.kind==="coadd";
    $("wavelength-label").textContent="Bước sóng hồng ngoại";
    $("alignment-label").textContent=isCoadd?"Độ lệch sao nền kiểm tra":"Độ lệch sao nền sau căn chỉnh";
    $("alignment-label").title="Độ ổn định căn chỉnh đo trên sao nền; không phải sai số vị trí của WISE 0855.";
    $("wavelength").textContent=isCoadd?"4,55–4,94 µm":`${number((scene.before.wavelength_um+scene.after.wavelength_um)/2,3)} µm`;
    $("alignment").textContent=isCoadd?`${number(scene.motion.holdout_rms_arcsec,2)}″ (${scene.motion.heldout_controls.length} sao)`:scene.alignment.rms_after_px===null?"Chỉ dùng WCS":`${number(scene.alignment.rms_after_px,3)} px`;
    $("date-before").textContent=`Trước · ${isCoadd?scene.before.date_start:scene.before.date}`;$("date-after").textContent=`Sau · ${isCoadd?scene.after.date_end:scene.after.date}`;
    $("load-state").hidden=true;motionPanel(scene);candidateList();sceneList();evidenceContent();select("target");setMode(state.mode);
    if(state.gaia)gaiaConfiguration(scene.motion?.spectral_configuration||"broad");
    ["download-manifest","save-review","export-reviews"].forEach(id=>$(id).disabled=false);
    document.dispatchEvent(new CustomEvent("scene:loaded"));
  } catch(error) {
    $("load-state").hidden=false;$("load-state").textContent=`Không tải được dữ liệu: ${error.message}. Chạy web bằng scripts/serve_demo.py rồi tải lại trang.`;
  }
  finally {if(generation===state.loading)$("workspace").removeAttribute("aria-busy");}
}

document.querySelectorAll("[data-mode]").forEach(button=>button.addEventListener("click",()=>setMode(button.dataset.mode)));
$("wipe").addEventListener("input",e=>{state.wipe=Number(e.target.value)/100;render();});
$("zoom").addEventListener("input",e=>{state.zoom=Number(e.target.value);$("zoom-value").textContent=`${number(state.zoom,state.zoom%1?2:0)}×`;render();});
["show-prior","show-residuals","show-motion"].forEach(id=>$(id).addEventListener("change",render));
$("reset-view").addEventListener("click",()=>{state.center=[32,32];state.zoom=1;state.wipe=.5;$("wipe").value="50";$("zoom").value="1";$("zoom-value").textContent="1×";setMode("wipe");});
$("select-target").addEventListener("click",()=>{if(state.scene)select("target");});
$("focus-selection").addEventListener("click",()=>{
  if(!state.scene)return;
  const p=state.selected==="target"?(state.scene.measured_positions?.[1]||state.scene.target_prior[1]):state.scene.candidates.find(c=>c.id===state.selected);
  state.center=[p.x+.5,63-p.y+.5];state.zoom=3;$("zoom").value="3";$("zoom-value").textContent="3×";render();
});
$("evidence-open").addEventListener("click",()=>{if(state.scene)$("evidence-dialog").showModal();});
$("evidence-close").addEventListener("click",()=>$("evidence-dialog").close());
$("download-manifest").addEventListener("click",()=>download("wise0855-evidence.json",state.manifest));
$("save-review").addEventListener("click",async()=>{
  const s=state.scene;
  const key=keyForSelection(),item={scene_id:s.id,selection:state.selected,status:$("review-status").value,note:$("review-note").value,
    saved_at:new Date().toISOString(),analysis_sha256:state.manifest.analysis_sha256,
    input_sha256:[s.before.sha256,s.after.sha256],target_detection:s.target_detection};
  $("save-review").disabled=true;
  let cloud=false,local=false;
  if(location.protocol==="https:")try {
    if(!remoteStorage)await reviewApi();
    const result=await reviewApi("POST",item);Object.assign(item,result.review);cloud=true;remoteStorage=true;
  } catch { remoteStorage=false; }
  reviews[key]=item;
  try{localStorage.setItem("nosleepclub.reviews.v1",JSON.stringify(reviews));local=true;}catch{}
  $("storage-status").textContent=cloud?"MongoDB":"Trình duyệt";
  if(key===keyForSelection()) {
    $("review-feedback").textContent=cloud?"Đã lưu MongoDB.":local?"Đã lưu trên trình duyệt. Chưa đồng bộ.":"Chưa lưu được. Hãy xuất JSON.";
    $("clear-review").hidden=false;
  }
  $("save-review").disabled=false;
});
$("export-reviews").addEventListener("click",()=>download("wise0855-reviews.json",{schema_version:1,reviews:Object.values(reviews)}));
$("clear-review").addEventListener("click",async()=>{
  const key=keyForSelection(),next={...reviews};delete next[key];
  if(location.protocol==="https:")try {
    await reviewApi("DELETE",reviews[key]);
  } catch {$("review-feedback").textContent="Chưa xóa được trên máy chủ. Hãy thử lại.";return;}
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
getJson("data/manifest.json").then(async manifest=>{
  state.manifest=manifest;
  if(manifest.gaia_results) {
    [state.gaia,state.gaiaMap]=await Promise.all([getJson(manifest.gaia_results),getJson(manifest.gaia_map)]);
    setupGaiaPanel();
  }
  await loadScene(manifest.scenes[0]);
  await setupAccuracy();
  await syncReviews();
})
  .catch(error=>{$("load-state").textContent=`Không tải được manifest: ${error.message}. Chạy scripts/serve_demo.py để mở bản demo.`;$("workspace").removeAttribute("aria-busy");});

window.addEventListener("resize",render);
document.fonts.addEventListener("loadingdone",render);

"use strict";
(() => {
  const el=id=>document.getElementById(id), n=(v,d=2)=>Number(v).toLocaleString("vi-VN",{maximumFractionDigits:d,minimumFractionDigits:d});
  Promise.all([fetch("data/diagnostics/bias-overview.json").then(r=>{if(!r.ok)throw Error(r.status);return r.json();}),fetch("data/explorer-check/coverage.json").then(r=>{if(!r.ok)throw Error(r.status);return r.json();})]).then(([bias,coverage])=>{
    const rows=el("bias-diagnostic-rows");rows.replaceChildren();
    for(const item of bias.cases){
      const tr=document.createElement("tr"),g=item.gaussian_controls;
      const label=item.snr_per_frame===2?"Nguồn mờ · đứng yên":"Nguồn sáng hơn · dịch 3,70″";
      for(const text of [item.field_id,label,n(item.original.error_arcsec)+"″",n(g.rms_numeric_arcsec)+"″",`${g.raw68_numeric}/${g.numeric} (${n(g.raw68_numeric/g.numeric*100,1)}%)`,n(item.exposure_influence.maximum_vector_change_arcsec)+"″"]){const td=document.createElement("td");td.textContent=text;tr.append(td);}rows.append(tr);
    }
    el("bias-diagnostic-note").textContent="Các ca Gaussian dùng cùng ePSF với fitter, 64 noise realizations mỗi ca trên bố cục detector đã mở. Đây là kiểm tra thống kê có điều kiện; các ca dùng stream noise ghép cặp, không phải 384 vùng trời độc lập. Bỏ một exposure giữ căn chỉnh cố định.";
    const grid=el("challenge-preview-grid");grid.replaceChildren();
    for(const field of coverage.targets){
      const card=document.createElement("article"),title=document.createElement("h3"),description=document.createElement("p"),images=document.createElement("div"),link=document.createElement("a");
      title.textContent=field.target.name;description.textContent=`${field.observations.length} quan sát D6 · ${field.images.filter(x=>x.image).length}/2 cutout đã tải thật`;
      images.className="challenge-pair";
      for(const image of field.images){if(!image.image)continue;const figure=document.createElement("figure"),img=document.createElement("img"),caption=document.createElement("figcaption");img.src=image.image;img.loading="lazy";img.alt=`Ảnh SPHEREx thật ${field.target.name}, ${image.side==="first"?"đầu":"cuối"} chuỗi, MJD ${image.observation.t_min_mjd}`;caption.textContent=`${image.side==="first"?"Đầu":"Cuối"} · MJD ${n(image.observation.t_min_mjd,2)}`;figure.append(img,caption);images.append(figure);}
      const p=new URLSearchParams({sky_ra:field.target.ra_deg,sky_dec:field.target.dec_deg,sky_fov:field.target.fov_deg,sky_det:6,sky_release:"qr2"});
      link.href=`?${p}#explore`;link.textContent="Mở vùng trời này →";card.append(title,description,images,link);grid.append(card);
    }
    el("challenge-preview-note").textContent=`Ảnh thật được kiểm tra ${new Date(coverage.created_at).toLocaleString("vi-VN")}. Hai ảnh mỗi mục tiêu dùng cùng mức xám và lưới WCS; chưa căn chỉnh sao, ghép phổ tại nguồn hay xác nhận chuyển động/biến quang. Tải JSON để xem URL, hash và mask.`;
  }).catch(error=>{el("bias-diagnostic-note").textContent=`Chưa tải được báo cáo: ${error.message}. Xem tài liệu và JSON nguồn bên dưới.`;}).finally(()=>el("validation").removeAttribute("aria-busy"));
  fetch("data/continuous-epsf/development-summary.json").then(r=>{if(!r.ok)throw Error(r.status);return r.json();}).then(data=>{
    const rows=el("continuous-epsf-rows");rows.replaceChildren();let before=0,after=0,total=0;
    for(const item of data.cases){
      const s=item.gaussian_summary.common_numeric,tr=document.createElement("tr"),p=s.candidate_profile,g=s.baseline_gn;
      for(const text of [item.field,n(item.snr_per_frame,0),`${n(s.baseline_error.rms_arcsec,4)}″ → ${n(s.candidate_error.rms_arcsec,4)}″`,`${g.within68}/${g.available}`,`${p.within68}/${p.available}`,`${item.gaussian_summary.common_accepted.count}/${item.gaussian_summary.attempts}`]){const td=document.createElement("td");td.textContent=text;tr.append(td);}rows.append(tr);
      for(const draw of item.paired_draws){for(const p of draw.baseline_epoch_profile){total++;if(p[2]>.05)before++;}for(const p of draw.candidate.epoch_profile)if(p[2]>.05)after++;}
    }
    el("continuous-epsf-note").textContent=`Hessian nhạy với bước sai phân giảm từ ${before}/${total} xuống ${after}/${total} epoch-fit. RMS sai số chưa giảm ở cả sáu ca; uncertainty nguồn mờ vẫn thiếu coverage. Chưa thay phép đo WISE hoặc hiệu chuẩn khoa học.`;
  }).catch(error=>{el("continuous-epsf-note").textContent=`Chưa tải được đối chứng ePSF: ${error.message}. Mở JSON hoặc báo cáo nguồn.`;});
  const sandwichDetails=el("sandwich-details");
  let sandwichData=null, sandwichPending=false;
  function renderSandwich(){
    if(!sandwichData)return;
    const level=el("sandwich-level").value,selection=el("sandwich-selection").value,rows=el("sandwich-rows");rows.replaceChildren();
    const methods=["gauss_newton","profile_hessian","exposure_sandwich"];
    for(const item of sandwichData.cases){
      const s=item.summary.selections[selection],tr=document.createElement("tr");
      const counts=methods.map(method=>{const c=s.methods[method].centroid_only.coverage[level];return `${c.inside}/${c.denominator} (${n(c.fraction*100,1)}%)`;});
      const areas=methods.map(method=>n(s.methods[method].centroid_only.median_ellipse68_area_arcsec2,2)).join(" / ");
      for(const text of [item.field,n(item.snr_per_frame,0),...counts,areas,n(s.rms_arcsec,3)]){const td=document.createElement("td");td.textContent=text;tr.append(td);}rows.append(tr);
    }
    el("sandwich-note").textContent=`Mức ${level}% · ${selection==="accepted"?"chỉ các lượt qua quality gate":"toàn bộ lượt thử"}. Mẫu số trong mỗi ô là số covariance tính được; cả ba cách đều hỗ trợ 128/128 lượt mỗi ca trước lọc. Diện tích luôn ở mức 68%; RMS dùng cùng vị trí fit cho cả ba cách.`;
  }
  async function loadSandwich(){
    if(sandwichData||sandwichPending)return;
    sandwichPending=true;el("sandwich-retry").hidden=true;el("sandwich-note").textContent="Đang tải kết quả…";
    try{
      const response=await fetch("data/sandwich/overview.json");if(!response.ok)throw Error(response.status);
      const data=await response.json();if(data.version!=="0.10.0-sandwich-overview.1"||data.cases.length!==6)throw Error("định dạng chưa tương thích");
      sandwichData=data;renderSandwich();
    }catch(error){el("sandwich-note").textContent=`Chưa tải được kết quả: ${error.message}. Bạn có thể thử lại hoặc tải JSON nguồn.`;el("sandwich-retry").hidden=false;}
    finally{sandwichPending=false;}
  }
  sandwichDetails.addEventListener("toggle",()=>{if(sandwichDetails.open)loadSandwich();});
  el("sandwich-level").addEventListener("change",renderSandwich);el("sandwich-selection").addEventListener("change",renderSandwich);
  el("sandwich-retry").addEventListener("click",loadSandwich);
  if(sandwichDetails.open)loadSandwich();
})();

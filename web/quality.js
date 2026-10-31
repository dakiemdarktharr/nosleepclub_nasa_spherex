"use strict";

(async function qualityValidation(){
  const el=id=>document.getElementById(id),fmt=n=>Number.isFinite(n)?n.toLocaleString("vi-VN",{minimumFractionDigits:2,maximumFractionDigits:2}):"—";
  const reasons={solver_failed:"solver không hội tụ",centroid_at_boundary:"vị trí chạm biên",nonpositive_flux:"biên độ không dương",low_epoch_snr:"tín hiệu yếu",poor_global_fit:"mô hình khớp ảnh kém",insufficient_core_pixels:"thiếu pixel lõi hợp lệ",structured_core_residual:"residual lõi lớn",core_outliers:"outlier trong lõi",unresolved_blend:"chưa tách được nguồn chồng",model_disagreement:"hai mô hình bất đồng vị trí",registration_unavailable:"không đủ sao căn chỉnh",fit_exception:"không fit được",input_exception:"không đủ dữ liệu đầu vào"};
  function basicGate(){
    const node=el("measurement-quality"),m=state.scene?.motion;
    if(state.selected!=="target"||!m?.target_before||!m?.target_after){node.hidden=true;return;}
    const warnings=[];
    for(const fit of [m.target_before,m.target_after]){
      if(!fit.success||fit.at_boundary)warnings.push("nghiệm fit chưa hợp lệ");
      if(fit.reduced_chi2>3)warnings.push("mô hình khớp ảnh kém");
      const snr=Math.sqrt((fit.per_frame||[]).reduce((sum,p)=>sum+Math.max(p.snr||0,0)**2,0));
      if(snr<5)warnings.push("tín hiệu yếu");
    }
    node.hidden=warnings.length===0;node.dataset.blocked=String(warnings.length>0);
    node.textContent=warnings.length?`Cần kiểm tra chất lượng: ${[...new Set(warnings)].join("; ")}.`:"Các kiểm tra cơ bản đạt; gate đầy đủ chưa chạy cho bộ ảnh WISE 0855 này.";
  }
  document.addEventListener("scene:loaded",basicGate);document.addEventListener("selection:changed",basicGate);basicGate();
  try {
    const response=await fetch("data/quality/overview.json");if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const data=await response.json();
    el("quality-verdict").textContent=data.passed?"Qua kiểm tra phổ rộng · cần kiểm chứng tiếp":"Chưa đạt tiêu chí thay mặc định";
    el("quality-protocol").textContent=`Protocol ${data.protocol_sha256.slice(0,12)} · khóa trước khi đo trên trường mới`;
    el("quality-fields").innerHTML=data.fields.map(f=>`<figure><img src="data/quality/${f.field.id}.png" alt="Ảnh SPHEREx thật tại ${f.field.name}" width="192" height="192" loading="lazy"><figcaption><strong>${f.field.name}</strong><a href="data/quality/evaluation-${f.field.id}.json" download>Kết quả JSON ↓</a></figcaption></figure>`).join("");
    function show(){
      const key=el("quality-sample").value==="real"?"real_summary":"injection_summary";
      el("quality-rows").innerHTML=data.fields.map(f=>{
        const s=f[key];if(!s?.models||key==="injection_summary"&&s.models.baseline.numeric_valid.attempted===0)return `<tr><th scope="row">${f.field.name}</th><td colspan="5">Chưa chạy ${f.planned_injections||32} lượt nguồn giả: không đủ cặp ảnh hoặc sao căn chỉnh cho baseline.</td></tr>`;
        const a=s.models.baseline,b=s.models.ir_robust,p=s.paired_numeric,g=s.paired_accepted;
        return `<tr><th scope="row">${f.field.name}</th><td>${a.numeric_valid.valid} / ${b.numeric_valid.valid}<span class="benchmark-pairs">trên ${a.numeric_valid.attempted} lượt</span></td><td>${fmt(p.baseline_rms)}″ → <strong>${fmt(p.candidate_rms)}″</strong><span class="benchmark-pairs">${p.common} cặp chung</span></td><td>${a.accepted.valid} / ${b.accepted.valid}<span class="benchmark-pairs">trên ${a.accepted.attempted} lượt</span></td><td>${fmt(g.baseline_rms)}″ → ${fmt(g.candidate_rms)}″<span class="benchmark-pairs">${g.common} cặp chung</span></td><td>${f.passed?"Qua tiêu chí chẩn đoán":"Cần cải thiện"}</td></tr>`;
      }).join("");
      el("quality-rejections").innerHTML=data.fields.map(f=>{
        const summary=f[key]?.models?.ir_robust?.accepted;
        if(!summary||summary.attempted===0)return `<li><strong>${f.field.name}</strong>: chưa chạy do không đủ dữ liệu căn chỉnh cho baseline.</li>`;
        const entries=Object.entries(summary.reasons).filter(([,count])=>count>0);
        return `<li><strong>${f.field.name}</strong>: ${entries.length?entries.map(([reason,count])=>`${reasons[reason]||reason} (${count})`).join("; "):"không có lượt bị gate loại"}. Một lượt có thể có nhiều lý do.</li>`;
      }).join("");
    }
    el("quality-sample").addEventListener("change",show);show();
    el("quality-cases").innerHTML=data.development_cases.map(c=>{
      const a=c.models.baseline,b=c.models.ir_robust;
      return `<article><h3>${c.label}</h3><p>Sai lệch ${fmt(a.error_arcsec)}″ → ${fmt(b.error_arcsec)}″.</p><strong>${b.accepted?"Qua gate chẩn đoán":"Không qua gate · cần người kiểm tra"}</strong><p>${b.quality_reasons.map(r=>reasons[r]||r).join("; ")||"Xem JSON để kiểm tra từng exposure."}</p></article>`;
    }).join("");
    el("quality-validation").removeAttribute("aria-busy");
  } catch {
    el("quality-verdict").textContent="Chưa tải được kết quả";
    el("quality-protocol").textContent="Chưa tải được kết quả quality gate. Tải lại trang để xem.";
    el("quality-validation").removeAttribute("aria-busy");
  }
})();

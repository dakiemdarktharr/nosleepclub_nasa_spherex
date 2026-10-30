"use strict";
(async function ablationValidation(){
  const el=id=>document.getElementById(id),fmt=(n,d=2)=>Number.isFinite(n)?n.toLocaleString("vi-VN",{minimumFractionDigits:d,maximumFractionDigits:d}):"—";
  const names={plane_fixed:"Nền phẳng · ePSF cố định",quadratic_fixed:"Nền bậc hai · ePSF cố định",plane_flexible:"Nền phẳng · ePSF linh hoạt",quadratic_flexible:"Nền bậc hai · ePSF linh hoạt"};
  const cells={snr_low_bg_smooth:"S/N thấp · biến động nền thấp",snr_low_bg_structured:"S/N thấp · biến động nền cao",snr_high_bg_smooth:"S/N cao · biến động nền thấp",snr_high_bg_structured:"S/N cao · biến động nền cao"};
  const fraction=v=>v?.supported?`${v.covered68} / ${v.supported} (${fmt(100*v.fraction68,1)}%)`:"Chưa có mẫu hỗ trợ";
  try {
    const response=await fetch("data/ablation/overview.json");if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const data=await response.json(),selection=data.selection,cal=data.calibrator;
    el("ablation-verdict").textContent=data.passed?"Đạt tiêu chí lượt thử":"Chưa đủ điều kiện áp dụng lên WISE 0855";
    el("ablation-selected").textContent=names[data.selected_model];
    el("ablation-choice-note").textContent=selection.retained_baseline?"Giữ mô hình đơn giản: chưa tổ hợp phức tạp nào đạt đủ tiêu chí theo nhóm.":"Mô hình thay thế đạt toàn bộ tiêu chí chọn trên tập phát triển.";
    el("ablation-lock").textContent=`Khóa ${data.lock_commit.slice(0,7)} · protocol ${data.validation_protocol_sha256.slice(0,12)}`;
    el("ablation-split-note").textContent=`Năm trường phát triển đã mở · ba trường calibration riêng · ba trường kiểm định mới. ${selection.leave_one_field_out.filter(f=>f.selected_model===data.selected_model).length}/5 lần bỏ một trường vẫn chọn cùng mô hình.`;
    el("ablation-field").innerHTML='<option value="all">Tất cả 5 trường đã mở</option>'+data.ablation.fields.map(f=>`<option value="${f.field.id}">${f.field.name}</option>`).join("");
    function showAblation(){
      const field=el("ablation-field").value,sample=el("ablation-sample").value;
      const stats=field==="all"?data.ablation.all[sample]:data.ablation.fields.find(f=>f.field.id===field).samples[sample];
      el("ablation-rows").innerHTML=Object.entries(names).map(([kind,label])=>{
        const v=stats[kind],p=v.paired,a=v.accepted,groups=selection.candidates[kind].groups.filter(g=>(field==="all"||g.field_id===field)&&(sample==="real"?g.real:!g.real));
        return `<tr><th scope="row">${label}${kind===data.selected_model?'<span class="benchmark-pairs">Được chọn</span>':""}</th><td>${v.summary.valid} / ${v.summary.attempted}</td><td>${fmt(p.baseline_rms_arcsec)}″ → ${fmt(p.candidate_rms_arcsec)}″<span class="benchmark-pairs">${p.common} cặp chung</span></td><td>${fmt(p.baseline_p90_arcsec)}″ → ${fmt(p.candidate_p90_arcsec)}″</td><td>${a.valid} / ${a.attempted}</td><td>${a.bias_east_north_arcsec?a.bias_east_north_arcsec.map(x=>fmt(x)+"″").join(" / "):"—"}</td><td>${groups.filter(g=>g.passed).length} / ${groups.length}</td></tr>`;
      }).join("");
    }
    el("ablation-field").addEventListener("change",showAblation);el("ablation-sample").addEventListener("change",showAblation);showAblation();
    const cuts=cal.thresholds;
    el("ablation-feature-note").textContent=`S/N thấp < ${fmt(cuts.snr_cut,0)}. Biến động nền thấp < ${fmt(cuts.background_cut,3)} theo MAD/noise trong vành đã che nguồn. Đây là chia tương đối theo tập phát triển, trước calibration; chỉ số gần 1 có thể chủ yếu phản ánh noise.`;
    el("ablation-pooling").innerHTML=Object.entries(cells).map(([cell,label])=>{
      const n=cal.nodes[cell];return `<li><strong>${label}</strong>: ${n.local_fitted?"hệ số nhóm riêng":"gộp về "+(cells[n.parameter_source]||({global:"toàn tập",snr_low:"S/N thấp",snr_high:"S/N cao"}[n.parameter_source]))}; vùng nền sẵn có cho floor / scale: ${n.floor_support.blocks} / ${n.quantile_support.blocks}.</li>`;
    }).join("");
    el("ablation-fields").innerHTML=data.validation.fields.map(f=>`<figure><img src="data/ablation/${f.field.id}.png" alt="Ảnh SPHEREx thật tại ${f.field.name}" width="192" height="192" loading="lazy"><figcaption><strong>${f.field.name}</strong><a href="data/ablation/validation-${f.field.id}.json" download>Phép đo & miền hỗ trợ ↓</a></figcaption></figure>`).join("");
    function showValidation(){
      const sample=el("ablation-validation-sample").value,all=data.validation[sample],common=all.common_supported;
      el("ablation-global-coverage").textContent=fraction(common.global);
      el("ablation-conditional-coverage").textContent=fraction(common.conditional);
      el("ablation-supported").textContent=`${all.conditional.supported} / ${all.conditional.accepted}`;
      el("ablation-cell-rows").innerHTML=Object.entries(cells).map(([cell,label])=>{
        const c=all.cells[cell],p=c.conditional,g=c.common_supported.global,n=c.common_supported.conditional;
        return `<tr><th scope="row">${label}</th><td>${p.supported} / ${p.accepted}<span class="benchmark-pairs">${p.unsupported} ngoài miền; ${p.blocks} vùng</span></td><td>${fraction(g)}</td><td>${fraction(n)}</td><td>×${fmt(g.median_area_inflation)} → ×${fmt(n.median_area_inflation)}</td><td>${p.pooled_count} / ${p.supported}</td></tr>`;
      }).join("");
      el("ablation-validation-rows").innerHTML=data.validation.fields.map(f=>{
        const v=f[sample],c=v.common_supported,p=v.conditional;
        return `<tr><th scope="row">${f.field.name}</th><td>${v.raw.valid} / ${v.raw.attempted}</td><td>${fmt(v.raw.rms_arcsec)}″ / ${fmt(v.raw.p90_arcsec)}″</td><td>${p.supported} / ${p.accepted}</td><td>${fraction(c.global)}<br>→ ${fraction(c.conditional)}</td><td>×${fmt(c.global.median_area_inflation)}<br>→ ×${fmt(c.conditional.median_area_inflation)}</td></tr>`;
      }).join("");
      el("ablation-validation-note").textContent=`${all.conditional.accepted}/${all.conditional.attempted} lượt qua quality gate. Độ phủ và diện tích so trên cùng các mẫu được cả hai cách hiệu chuẩn hỗ trợ. Cột trong miền / qua gate giữ lại số ca bị từ chối; một ellipse lớn hơn không làm vị trí chính xác hơn.`+(sample==="real"?" Sao Gaia sáng có thể nằm ngoài S/N đã hiệu chuẩn; không ngoại suy hệ số cho chúng.":"");
    }
    el("ablation-validation-sample").addEventListener("change",showValidation);showValidation();
    const patch=data.diagnostic_patch;
    if(patch){
      el("ablation-diagnostic").innerHTML=`<div class="reference-map"><img src="data/ablation/${patch.field.id}.png" alt="Nền ảnh SPHEREx gốc, trước khi tiêm nguồn giả" width="192" height="192"><svg viewBox="0 0 192 192" role="img" aria-label="Vòng cam đánh dấu vùng nền kiểm thử, không phải thiên thể phát hiện"><circle cx="${patch.map_center_px[0]}" cy="${patch.map_center_px[1]}" r="7" fill="none" stroke="#ffb36a" stroke-width="1.8"/></svg></div><div><h3>${patch.field.name} · vùng nền ${patch.patch_index+1}</h3><p>${patch.covered68}/${patch.attempted_accepted_supported} nguồn giả qua gate và trong miền nằm trong ellipse 68%. Sai lệch ${patch.error_range_arcsec.map(x=>fmt(x)+"″").join("–")}.</p><p>Các lượt dùng chung một vùng nền, không độc lập. Vòng cam là vùng dùng tiêm nguồn giả; ảnh đang xem là nền gốc, chưa có nguồn tiêm. Đây là chẩn đoán sau kiểm định, không phải phát hiện thiên thể.</p></div>`;
    }
    const gate=data.coverage_gate;
    el("ablation-gate-note").textContent=`Đối chiếu vị trí: ${selection.retained_baseline?"giữ baseline, không phải cải thiện centroid":data.point_passed?"đạt":"chưa đạt"}. Hiệu chuẩn theo nhóm: ${gate.passed?"đạt":"chưa đạt"}. Khung phủ 68% được nhận: 55–85%; cần đủ mẫu ở cả bốn nhóm và ít nhất 80% mẫu qua gate nằm trong miền hiệu chuẩn.`;
    el("model-selection").removeAttribute("aria-busy");
  } catch {
    el("ablation-verdict").textContent="Chưa tải được kiểm chứng";el("ablation-lock").textContent="Tải lại trang để xem bảng tách thử nền/ePSF.";el("model-selection").removeAttribute("aria-busy");
  }
})();

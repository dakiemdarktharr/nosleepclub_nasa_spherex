"use strict";
(async function covarianceValidation(){
  const el=id=>document.getElementById(id),fmt=(n,d=2)=>Number.isFinite(n)?n.toLocaleString("vi-VN",{minimumFractionDigits:d,maximumFractionDigits:d}):"—";
  const fraction=(n,total)=>total?`${n} / ${total} (${fmt(100*n/total,1)}%)`:"Chưa có mẫu qua gate";
  try {
    const response=await fetch("data/covariance/overview.json");if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const data=await response.json(),gate=data.coverage_gate;
    el("covariance-verdict").textContent=data.passed?"Đạt tiêu chí của lượt thử":"Chưa đạt tiêu chí thay mặc định";
    el("covariance-lock").textContent=`Khóa ${data.lock_commit.slice(0,7)} · protocol ${data.validation_protocol_sha256.slice(0,12)}`;
    const pooled=data.injection_summary.models.candidate.accepted;
    el("covariance-coverage").textContent=fraction(pooled.calibrated68_count||0,pooled.valid);
    el("covariance-area").textContent=`×${fmt(gate.median_area_inflation)}`;
    el("covariance-point").textContent=data.point_passed?"Đạt cả 3 trường":"Chưa đồng đều";
    el("covariance-gates").textContent=`Hiệu chuẩn ellipse: ${gate.passed?"đạt":"chưa đạt"} (khung nhận 55–85%). Độ lệch vị trí: ${data.point_passed?"đạt":"chưa đạt"}. Khoảng bootstrap tỷ lệ phủ: ${gate.hierarchical_block_bootstrap95?gate.hierarchical_block_bootstrap95.map(x=>fmt(x*100,1)+"%").join("–"):"chưa đủ dữ liệu"}; mức danh nghĩa là 68%.`;
    el("covariance-fields").innerHTML=data.fields.map(f=>`<figure><img src="data/covariance/${f.field.id}.png" alt="Ảnh SPHEREx tại RA ${f.field.ra} độ, Dec ${f.field.dec} độ" width="192" height="192" loading="lazy"><figcaption><strong>${f.field.name}</strong><a href="data/covariance/validation-${f.field.id}.json" download>Phép đo & pixel gate ↓</a></figcaption></figure>`).join("");
    function show(){
      const key=el("covariance-sample").value==="real"?"real_summary":"injection_summary";
      el("covariance-rows").innerHTML=data.fields.map(f=>{
        const s=f[key],p=s.paired_numeric,a=s.models.previous,b=s.models.candidate,c=b.accepted;
        return `<tr><th scope="row">${f.field.name}</th><td>${a.numeric_valid.valid} / ${b.numeric_valid.valid}<span class="benchmark-pairs">trên ${b.numeric_valid.attempted} lượt</span></td><td>${fmt(p.previous_rms_arcsec)}″ → <strong>${fmt(p.candidate_rms_arcsec)}″</strong><span class="benchmark-pairs">${p.common} cặp chung</span></td><td>${a.accepted.valid} / ${c.valid}<span class="benchmark-pairs">trên ${c.attempted} lượt</span></td><td>${c.bias_east_north_arcsec?c.bias_east_north_arcsec.map(x=>fmt(x)+"″").join(" / "):"—"}</td><td>${fraction(c.raw68_count,c.valid)}<br>→ <strong>${fraction(c.calibrated68_count||0,c.valid)}</strong></td><td>×${fmt(c.median_area_inflation)}</td><td>${f.point_gate.passed?"Đạt":"Cần cải thiện"}</td></tr>`;
      }).join("");
      el("covariance-explanation").textContent="Cũ / mới: IR + Huber 0.7 / nền bậc hai + ePSF linh hoạt 0.8. RMS so các fit hội tụ chung. Bias, tỷ lệ phủ và diện tích chỉ tính mẫu mới qua gate. Gate cả trường yêu cầu nguồn giả lẫn sao Gaia đạt."+(key==="real_summary"?" Sao Gaia sáng nằm ngoài hai mức S/N nguồn giả dùng hiệu chuẩn: đây là kiểm tra ngoại suy.":"");
    }
    el("covariance-sample").addEventListener("change",show);show();
    const cal=data.calibration.injection_summary.models.candidate.accepted;
    el("covariance-calibration").textContent=`${data.calibrator.accepted} / ${data.calibrator.attempted} nguồn giả qua gate, ${data.calibrator.spatial_blocks.length} vùng nền. Tỷ lệ phủ sau hiệu chuẩn ${fraction(cal.calibrated68_count||0,cal.valid)}.`;
    el("covariance-validation-count").textContent=`${gate.accepted} / ${gate.attempted} nguồn giả qua gate, ${gate.spatial_blocks} vùng nền có mẫu đạt. Bộ mới chỉ được đo sau khi khóa cả hệ số hiệu chuẩn.`;
    el("covariance-parameters").textContent=`C mới = ${fmt(data.calibrator.scale_squared,3)} × (C thô + F). F [Đông, Bắc] = ${JSON.stringify(data.calibrator.floor_arcsec2.map(row=>row.map(x=>Number(x.toFixed(4)))))} arcsec². Không trừ bias khỏi vector.`;
    el("covariance-validation-section").removeAttribute("aria-busy");
  } catch {
    el("covariance-verdict").textContent="Chưa tải được kiểm chứng";
    el("covariance-lock").textContent="Tải lại trang để xem kết quả hiệu chuẩn covariance.";
    el("covariance-validation-section").removeAttribute("aria-busy");
  }
})();

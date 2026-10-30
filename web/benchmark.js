"use strict";

(async function externalBenchmark(){
  const root=document.getElementById("external-benchmark");
  function reveal(){root.removeAttribute("aria-busy");}
  try {
    const response=await fetch("data/benchmark/summary.json");
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const payload=await response.json();
    const fmt=value=>Number.isFinite(value)?value.toLocaleString("vi-VN",{minimumFractionDigits:2,maximumFractionDigits:2}):"—";
    const ratio=(value,total)=>`${value} / ${total}`;
    document.getElementById("benchmark-fields").innerHTML=payload.fields.map(row=>`<figure><img src="data/benchmark/${row.field.id}.png" alt="Ảnh cộng thăm dò SPHEREx thật quanh ${row.field.name}" width="192" height="192" loading="lazy"><figcaption><strong>${row.field.name}</strong><a href="data/benchmark/${row.field.id}.json" download>Kết quả JSON ↓</a></figcaption></figure>`).join("");
    function show(){
      const config=document.getElementById("benchmark-spectrum").value;
      document.getElementById("benchmark-rows").innerHTML=payload.fields.map(row=>{
        const group=row.configurations.find(g=>g.configuration===config);
        if(!group?.real_summary){
          const reason=group?.unavailable_reason||"";
          const count=reason.match(/only (\d+) usable references/);
          const message=reason.startsWith("Fewer than")?"Không đủ hai cặp ảnh tương thích phổ.":count?`Chỉ ${count[1]} sao căn chỉnh đạt điều kiện; cần ít nhất 4.`:"Thiếu dữ liệu hợp lệ.";
          return `<tr><th scope="row">${row.field.name}</th><td colspan="6">Chưa đo được: ${message}</td></tr>`;
        }
        const real=group.real_summary,synthetic=group.injection_summary;
        return `<tr><th scope="row">${row.field.name}<span class="benchmark-pairs">${group.pairs} ảnh mỗi epoch</span></th><td>${ratio(real.valid,real.attempted)}</td><td><strong>${fmt(real.rmse_arcsec)}″</strong></td><td>${fmt(real.p90_error_arcsec)}″</td><td>${ratio(synthetic.valid,synthetic.attempted)}</td><td>${ratio(synthetic.within_one_pixel,synthetic.attempted)}</td><td>${ratio(synthetic.within_68_ellipse,synthetic.attempted)}</td></tr>`;
      }).join("");
      const positive=payload.fields.find(row=>row.field.id==="barnard")?.configurations.find(g=>g.configuration===config)?.positive_control;
      const box=document.getElementById("benchmark-positive");
      box.textContent=positive?(positive.valid?`Barnard’s Star: đo [${positive.measured_east_north_arcsec.map(fmt).join("; ")}]″, dự báo [${positive.expected_east_north_arcsec.map(fmt).join("; ")}]″ (Đông; Bắc). Chênh ${fmt(positive.error_arcsec)}″. χ²r trước/sau: ${fmt(positive.before.reduced_chi2)} / ${fmt(positive.after.reduced_chi2)}; mô hình chưa khớp tốt ảnh.`:`Barnard’s Star: fit không đạt điều kiện. ${positive.reason||"Kiểm tra cờ ảnh và biên nghiệm trước khi kết luận."}`):"Barnard’s Star: chưa có phép đo mục tiêu hợp lệ.";
    }
    document.getElementById("benchmark-spectrum").addEventListener("change",show);
    show();reveal();
  } catch {
    document.getElementById("benchmark-status").textContent="Chưa tải được benchmark. Tải lại trang để xem kết quả.";
    reveal();
  }
})();

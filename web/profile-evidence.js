"use strict";
(() => {
  const el=id=>document.getElementById(id),panel=el("profile-landscape");if(!panel)return;
  let pending=false,loaded=false,report=null;
  const arms=["baseline","corrected"],frames=["2025W46_2A_0214_2","2025W46_2A_0214_3"];
  const finite=x=>typeof x==="number"&&Number.isFinite(x),hash=(x,n)=>typeof x==="string"&&new RegExp(`^[a-f0-9]{${n}}$`).test(x);
  const fmt=x=>finite(x)?x.toLocaleString("vi-VN",{maximumFractionDigits:4}):"—";
  const sum=c=>{if(!c||Array.isArray(c)||Object.entries(c).some(([k,v])=>!["profile_completed","preparation_failed"].includes(k)||!Number.isInteger(v)||v<0))throw Error("mẫu số không hợp lệ");return Object.values(c).reduce((a,b)=>a+b,0);};
  function fail(){throw Error("nguồn hoặc trạng thái báo cáo không khớp");}
  function validate(r){
    if(r?.schema!=="profile-landscape-overview-1"||r.status!=="audited_diagnostic_only"||r.promotion!==false||r.original_calibration_gate_passed!==false||r.assessment_opened!==false||r.prospective_fields_opened!==0||r.planned!==112||sum(r.counts)!==112||!hash(r.protocol_commit,40)||!hash(r.design_sha256,64)||!hash(r.cell_digest,64))fail();
    if(r.frames?.join()!==frames.join()||!Array.isArray(r.sources)||r.sources.length!==14||new Set(r.sources.map(s=>s.source_id)).size!==14||r.sources.some(s=>!/^\d{19}$/.test(s.source_id)||s.planned!==8||sum(s.counts)!==8)||r.sources.reduce((n,s)=>n+(s.counts.profile_completed||0),0)!==r.counts.profile_completed)fail();
    if(!hash(r.audit?.receipt_sha256,64)||r.audit.counts?.verified!==r.counts.profile_completed||r.audit.counts?.verified_unavailable!==r.counts.preparation_failed||Object.keys(r.audit.counts).some(k=>!["verified","verified_unavailable"].includes(k)))fail();
    if(r.download?.path!=="data/profile-landscape/records.json.gz"||!hash(r.download.sha256,64)||!Number.isInteger(r.download.bytes)||r.download.bytes<=0)fail();
    if(!Array.isArray(r.focus)||r.focus.length!==4||new Set(r.focus.map(f=>f.source_id+"/"+f.obs_id)).size!==4||new Set(r.focus.map(f=>f.source_id)).size!==2)fail();
    for(const f of r.focus){
      if(!r.sources.some(s=>s.source_id===f.source_id)||!frames.includes(f.obs_id)||f.figure!==`profile-${f.source_id}-${f.obs_id}.png`||!Array.isArray(f.arms)||f.arms.length!==4||new Set(f.arms.map(a=>a.psf_arm+"/"+a.weight_arm)).size!==4)fail();
      const figure=r.figures?.[f.figure];if(!hash(figure?.sha256,64)||figure.source_id!==f.source_id||figure.obs_id!==f.obs_id||figure.record_checksums?.join()!==f.arms.map(a=>a.record_checksum).join())fail();
      for(const a of f.arms){
        if(!arms.includes(a.psf_arm)||!arms.includes(a.weight_arm)||!hash(a.record_checksum,64)||!Number.isInteger(a.valid_nodes)||!Number.isInteger(a.missing_nodes)||a.valid_nodes<1||a.missing_nodes<0||a.valid_nodes+a.missing_nodes!==2601||!finite(a.sampled_global_minimum_cost)||a.sampled_global_minimum_cost<0)fail();
        for(const family of arms){
          const candidates=a.saved_candidates?.[family];if(!Array.isArray(candidates)||candidates.length!==f.saved_near_best_counts?.[family]||candidates.length<1)fail();
          for(const c of candidates){const d=c.diagnostic;if(!finite(c.saved_delta_cost_in_own_fit)||!d||!finite(d.cost)||d.cost<0||!Array.isArray(d.position_common_px)||d.position_common_px.length!==2||d.position_common_px.some(x=>!finite(x))||!Array.isArray(d.steps)||d.steps.length!==3)fail();
            d.steps.forEach((s,i)=>{if(s.step_common_px!==[.004,.002,.001][i])fail();if(s.error_codes){if(!Array.isArray(s.error_codes)||!s.error_codes.length)fail();}else if(!finite(s.gradient_infinity)||s.gradient_infinity<0||!Array.isArray(s.hessian_cost_eigenvalues)||s.hessian_cost_eigenvalues.length!==2||s.hessian_cost_eigenvalues.some(x=>!finite(x)))fail();});
          }
        }
      }
    }
    return r;
  }
  function option(select,value,label){const o=document.createElement("option");o.value=value;o.textContent=label;select.append(o);}
  function show(){
    if(!report)return;const f=report.focus.find(x=>x.source_id===el("profile-source").value&&x.obs_id===el("profile-frame").value);if(!f)return;
    const path="data/profile-landscape/"+f.figure;el("profile-figure").hidden=false;el("profile-plot").hidden=false;el("profile-plot").src=path;
    el("profile-plot").alt=`Bốn bản đồ chi phí theo vị trí của sao Gaia ${f.source_id}, ảnh ${f.obs_id}. So ePSF gốc/hiệu chỉnh và hai bộ trọng số. Dấu x cam: ứng viên cũ; dấu cộng trắng: ứng viên hiệu chỉnh. Không phải vùng tin cậy.`;
    el("profile-open-plot").href=path;el("profile-selected").textContent=`Gaia ${f.source_id} · ${f.obs_id}. Nhóm nghiệm đã lưu: ${f.saved_near_best_counts.baseline} → ${f.saved_near_best_counts.corrected}.`;
    el("profile-numeric-rows").replaceChildren();
    for(const a of f.arms){const tr=document.createElement("tr"),p=a.saved_candidates.corrected[0].diagnostic.steps[2];
      [a.psf_arm==="baseline"?"Gốc":"Hiệu chỉnh",a.weight_arm==="baseline"?"Gốc":"Sau hiệu chỉnh",fmt(p.gradient_infinity),fmt(p.hessian_cost_eigenvalues?.[0])].forEach((v,i)=>{const td=document.createElement(i===0?"th":"td");if(i===0)td.setAttribute("scope","row");td.textContent=v;tr.append(td);});el("profile-numeric-rows").append(tr);
    }
  }
  function render(r){
    report=r;el("profile-count").textContent=`${r.counts.profile_completed}/112`;el("profile-unavailable").textContent=String(r.counts.preparation_failed);el("profile-assessment").textContent="Chưa mở";
    el("profile-source").replaceChildren();const ids=[...new Set(r.focus.map(f=>f.source_id))];ids.forEach((id,i)=>option(el("profile-source"),id,`Sao ${i===0?"A":"B"} · …${id.slice(-6)}`));el("profile-source").value=ids[0];
    el("profile-frame").replaceChildren();frames.forEach((id,i)=>option(el("profile-frame"),id,i===0?"Ảnh liền trước":"Ảnh bị gate chặn"));el("profile-frame").value=frames[1];
    el("profile-result").hidden=false;el("profile-download").textContent=`112 bản ghi & kiểm toán · ${(r.download.bytes/1e6).toLocaleString("vi-VN",{maximumFractionDigits:1})} MB gzip ↓`;show();
  }
  async function load(){
    if(pending||loaded)return;pending=true;panel.setAttribute("aria-busy","true");el("profile-retry").hidden=true;el("profile-status").textContent="Đang kiểm tra chẩn đoán đã khóa…";
    try{const response=await fetch("data/profile-landscape/overview.json");if(!response.ok)throw Error(`HTTP ${response.status}`);render(validate(await response.json()));loaded=true;el("profile-status").textContent="Kiểm toán số học đạt. Chẩn đoán chưa loại trừ nghiệm phụ; gate hiệu chỉnh vẫn dừng.";}
    catch(error){report=null;el("profile-result").hidden=true;el("profile-figure").hidden=true;el("profile-plot").removeAttribute("src");el("profile-numeric-rows").replaceChildren();for(const id of ["profile-count","profile-unavailable","profile-assessment"])el(id).textContent="—";el("profile-status").textContent=`Chưa đọc được báo cáo: ${error.message}.`;el("profile-retry").hidden=false;}
    finally{pending=false;panel.removeAttribute("aria-busy");}
  }
  el("profile-source").addEventListener("change",show);el("profile-frame").addEventListener("change",show);
  el("profile-plot").addEventListener("error",()=>{el("profile-plot").hidden=true;el("profile-status").textContent="Báo cáo đã đọc, ảnh đồ thị chưa tải được. Có thể thử lại hoặc tải audit.";el("profile-retry").hidden=false;loaded=false;});
  el("profile-plot").addEventListener("load",()=>{if(report){el("profile-status").textContent="Kiểm toán số học đạt. Chẩn đoán chưa loại trừ nghiệm phụ; gate hiệu chỉnh vẫn dừng.";el("profile-retry").hidden=true;loaded=true;}});
  el("profile-retry").addEventListener("click",load);panel.addEventListener("toggle",()=>{if(panel.open)load();});if(panel.open)load();
})();

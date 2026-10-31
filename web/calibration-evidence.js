"use strict";
(() => {
  const el=id=>document.getElementById(id), panel=el("shape-validation");
  if(!panel)return;
  let pending=false,loaded=false;
  const number=x=>typeof x==="number"&&Number.isFinite(x), count=(x,max)=>Number.isInteger(x)&&x>=0&&x<=max;
  const hash=(x,n)=>typeof x==="string"&&new RegExp(`^[a-f0-9]{${n}}$`).test(x);
  const fmt=(x,d=3)=>number(x)?x.toLocaleString("vi-VN",{minimumFractionDigits:d,maximumFractionDigits:d}):"—";
  const arc=x=>number(x)?`${fmt(x)}″`:"—";
  function fail(){throw Error("schema, mẫu số hoặc trạng thái không khớp");}
  function sumCounts(value,max){if(!value||Array.isArray(value)||Object.values(value).some(x=>!count(x,max)))fail();return Object.values(value).reduce((a,b)=>a+b,0);}
  function base(r,schema){if(r?.schema!==schema||r.promotion!==false||!hash(r.protocol_commit,40)||!hash(r.design_sha256,64)||!hash(r.download?.sha256,64)||!count(r.download?.bytes,1e9)||r.download.bytes===0)fail();}
  function validate([learn,point,cov]){
    base(learn,"shape-calibration-overview-1");base(point,"shape-point-overview-1");base(cov,"reference-covariance-overview-1");
    if(learn.planned!==168||sumCounts(learn.counts,168)!==168||learn.status!=="conditional_candidate"||!count(learn.audit?.saved_cells,168)||learn.audit.saved_cells!==learn.counts.information_available)fail();
    if(!number(learn.maximum_source_fraction)||learn.maximum_source_fraction<0||learn.maximum_source_fraction>.35||!Array.isArray(learn.sources)||learn.sources.length!==14||new Set(learn.sources.map(s=>s.source_id)).size!==14||learn.sources.some(s=>s.planned!==12||!count(s.information_available,12))||learn.sources.reduce((n,s)=>n+s.information_available,0)!==learn.audit.saved_cells)fail();
    if(!Array.isArray(learn.coefficients)||learn.coefficients.length!==3||learn.coefficients.some(x=>!number(x))||learn.units?.join()!=="pix2,pix3,pix3"||learn.shape_checks?.passed!==learn.audit.saved_cells||learn.shape_checks.planned!==learn.audit.saved_cells)fail();
    if(!Array.isArray(learn.conditional_standard_errors)||learn.conditional_standard_errors.length!==3||learn.conditional_standard_errors.some(x=>!number(x)||x<0))fail();
    if(point.planned!==420||!count(point.recorded,420)||!count(point.deferred,420)||point.recorded+point.deferred!==420||sumCounts(point.counts,420)!==point.recorded)fail();
    const p=point.primary,g=point.calibration_gate;
    if(typeof g?.assessment_allowed!=="boolean"||g.planned!==168||sumCounts(g.counts,168)!==168||!Array.isArray(g.reasons)||!count(g.comparison_count,168)||!count(g.failure_count,168))fail();
    if(g.comparison_count+g.failure_count!==learn.audit.saved_cells||!Array.isArray(g.failure_cases)||g.failure_cases.length!==g.failure_count||g.failure_cases.some(c=>!Array.isArray(c.key)||c.key.length!==2||!count(c.baseline_near_best_count,100)||!count(c.corrected_near_best_count,100)||!number(c.corrected_mode_maximum_separation_arcsec)))fail();
    const expectedCal=g.failure_count===0&&g.comparison_count===learn.audit.saved_cells&&number(g.linearization_error_p90_common_px)&&g.linearization_error_p90_common_px<=.02&&number(g.linearization_error_max_common_px)&&g.linearization_error_max_common_px<=.05;
    if(g.assessment_allowed!==expectedCal)fail();
    if(p?.planned!==56||!count(p.common_completed_pairs,56)||!count(p.supported_source_count,7)||!count(p.new_numerical_refusals,56)||!Array.isArray(p.source_rows)||p.source_rows.length!==7||new Set(p.source_rows.map(s=>s.source_id)).size!==7)fail();
    if(p.source_rows.some(s=>s.planned!==8||!count(s.pair_count,8)||!Object.values(s.pair_count_by_season||{}).every(x=>count(x,4))||Object.values(s.pair_count_by_season||{}).reduce((a,b)=>a+b,0)!==s.pair_count)||p.source_rows.reduce((n,s)=>n+s.pair_count,0)!==p.common_completed_pairs)fail();
    const metricNames=["equal_source_baseline_mean_radial_arcsec","equal_source_point_mean_radial_arcsec","equal_source_mean_radial_improvement_arcsec","pooled_baseline_p90_radial_arcsec","pooled_point_p90_radial_arcsec","pooled_p90_increase_arcsec","paired_point_rms_radial_arcsec"];
    if(metricNames.some(k=>p.common_completed_pairs?!number(p[k]):p[k]!==null))fail();
    if(!p.gates||Object.keys(p.gates).length!==7||Object.values(p.gates).some(x=>typeof x!=="boolean")||p.developmental_gates_passed!==Object.values(p.gates).every(Boolean)||p.promotion!==false)fail();
    if(sumCounts(p.point_status_counts,56)!==56||sumCounts(p.baseline_status_counts,56)!==56)fail();
    const expectedGates={all_planned_records_available:!p.point_status_counts.missing&&!p.baseline_status_counts.missing,source_season_support:p.supported_source_count>=5,no_new_numerical_refusals:p.new_numerical_refusals===0,equal_source_improvement:number(p.equal_source_mean_radial_improvement_arcsec)&&p.equal_source_mean_radial_improvement_arcsec>=.05,pooled_p90_increase:number(p.pooled_p90_increase_arcsec)&&p.pooled_p90_increase_arcsec<=.05,paired_new_rms:number(p.paired_point_rms_radial_arcsec)&&p.paired_point_rms_radial_arcsec<=.5,paired_new_p90:number(p.pooled_point_p90_radial_arcsec)&&p.pooled_point_p90_radial_arcsec<=1};
    if(Object.entries(expectedGates).some(([key,value])=>p.gates[key]!==value)||p.supported_source_count!==p.source_rows.filter(s=>s.support_gate_met).length||p.source_rows.some(s=>Object.keys(s.pair_count_by_season).length!==2||s.support_gate_met!==Object.values(s.pair_count_by_season).every(n=>n>=2)))fail();
    if(!g.assessment_allowed&&(point.deferred!==252||p.common_completed_pairs!==0||p.developmental_gates_passed))fail();
    if(cov.planned!==420||sumCounts(cov.counts,420)!==420||cov.status!=="descriptive_complete"||!number(cov.heldout_joint?.chi2)||cov.heldout_joint.chi2<0||!count(cov.heldout_joint.dof,840)||cov.heldout_joint.dof===0||!Array.isArray(cov.heldout_sources)||cov.heldout_sources.length!==7)fail();
    if(new Set(cov.heldout_sources.map(s=>s.source_id)).size!==7||cov.heldout_sources.some(s=>!count(s.available,20)||s.dof!==2*s.available||(s.available?(!number(s.chi2)||s.chi2<0):s.chi2!==null))||cov.heldout_sources.reduce((n,s)=>n+s.dof,0)!==cov.heldout_joint.dof)fail();
    return [learn,point,cov];
  }
  function row(id,values){const tr=document.createElement("tr");values.forEach((v,i)=>{const td=document.createElement(i===0?"th":"td");if(i===0)td.setAttribute("scope","row");td.textContent=String(v);tr.append(td);});el(id).append(tr);}
  function render([learn,point,cov]){
    const p=point.primary,g=point.calibration_gate;
    el("shape-learn-count").textContent=`${learn.audit.saved_cells}/168`;
    el("shape-dominance").textContent=`${fmt(learn.maximum_source_fraction*100,1)}%`;
    el("shape-point-count").textContent=`${point.recorded}/420`;
    el("shape-seal-status").textContent="Hệ số đã khóa trước phép thử vị trí";
    el("shape-point-status").textContent=g.assessment_allowed?"Đã qua gate calibration":"Dừng ở gate calibration";
    el("shape-primary-status").textContent=g.assessment_allowed?`${p.common_completed_pairs}/56 cặp có kết quả`:`252 ô dành riêng chưa đánh giá`;
    el("shape-verdict").textContent=!g.assessment_allowed?"Ứng viên dừng ở calibration. Chưa đủ điều kiện kiểm tra phần dành riêng hoặc thay phép đo WISE 0855.":p.developmental_gates_passed?"Qua các ngưỡng phát triển trên tập đã mở. Cần kiểm định độc lập và giữ tín hiệu trước khi áp dụng.":"Chưa đạt các ngưỡng cải thiện đã khóa. Phép đo WISE 0855 vẫn giữ theo mô hình cũ.";
    el("shape-gate-note").textContent=`Sai lệch giữa thay đổi vị trí thực và dự báo tuyến tính: P90 ${fmt(g.linearization_error_p90_common_px,4)} pixel; lớn nhất ${fmt(g.linearization_error_max_common_px,4)} pixel. ${g.failure_count} ô mất hỗ trợ; đủ 168 ô calibration vẫn được giữ.`;
    el("shape-primary-note").textContent=g.assessment_allowed?`${p.supported_source_count}/7 sao đủ cặp ở cả hai mùa; ${p.new_numerical_refusals} ô mất hỗ trợ số học so với baseline. Đây là tập đã mở, chưa phải kiểm định bầu trời mới.`:"56 ô so sánh chính chưa được đo lại vì gate calibration chưa đạt. Chưa có kết quả trước/sau trên phần này.";
    el("shape-metric-rows").replaceChildren();
    row("shape-metric-rows",["Sai lệch trung bình · mỗi sao trọng số bằng nhau",arc(p.equal_source_baseline_mean_radial_arcsec),arc(p.equal_source_point_mean_radial_arcsec)]);
    row("shape-metric-rows",["P90 · 90% sai lệch nằm dưới mức này",arc(p.pooled_baseline_p90_radial_arcsec),arc(p.pooled_point_p90_radial_arcsec)]);
    row("shape-metric-rows",["RMS · nhạy với sai lệch lớn",number(point.baseline_paired_rms_arcsec)?`${fmt(point.baseline_paired_rms_arcsec)}″`:"—",number(p.paired_point_rms_radial_arcsec)?`${fmt(p.paired_point_rms_radial_arcsec)}″`:"—"]);
    el("shape-source-rows").replaceChildren();
    p.source_rows.forEach(s=>row("shape-source-rows",[s.source_id,g.assessment_allowed?`${s.pair_count}/8`:"— /8",s.pair_count?`${fmt(s.baseline_mean_radial_arcsec)}″`:"—",s.pair_count?`${fmt(s.point_mean_radial_arcsec)}″`:"—",!g.assessment_allowed?"Chưa đánh giá":s.support_gate_met?"Đủ hai mùa":"Thiếu hỗ trợ"]));
    el("shape-failures").hidden=g.failure_count===0;el("shape-failure-rows").replaceChildren();
    g.failure_cases.forEach(c=>row("shape-failure-rows",[c.key[0],c.key[1],`${c.baseline_near_best_count} → ${c.corrected_near_best_count}`,arc(c.corrected_mode_maximum_separation_arcsec)]));
    el("shape-coefficient-rows").replaceChildren();
    ["Độ rộng","Lệch hình trục x","Lệch hình trục y"].forEach((name,i)=>row("shape-coefficient-rows",[name,fmt(learn.coefficients[i],7),i===0?"pixel²":"pixel³",fmt(learn.conditional_standard_errors[i],7)]));
    el("shared-reference-count").textContent=`${cov.counts.influence_available}/420`;
    el("shared-reference-ratio").textContent=fmt(cov.heldout_joint.chi2/cov.heldout_joint.dof,2);
    el("shared-reference-note").textContent=`Baseline cũ: chi² ${fmt(cov.heldout_joint.chi2,2)} với ${cov.heldout_joint.dof} bậc tự do trên sao ngoài nghiệm căn chỉnh. Mức lệch còn lớn hơn mô hình sai số dự báo; cần kiểm định độ phủ riêng.`;
    el("shared-source-rows").replaceChildren();
    cov.heldout_sources.forEach(s=>row("shared-source-rows",[s.source_id,`${s.available}/20`,s.available?fmt(s.chi2/s.dof,2):"—"]));
    for(const [id,r] of [["shape-learn-download",learn],["shape-point-download",point],["shared-reference-download",cov]])el(id).textContent=`Audit đầy đủ · ${fmt(r.download.bytes/1e6,1)} MB gzip ↓`;
  }
  async function load(){
    if(pending||loaded)return;pending=true;panel.setAttribute("aria-busy","true");el("shape-retry").hidden=true;
    el("shape-load-status").textContent="Đang kiểm tra ba bản tóm tắt…";
    try{
      const urls=["data/shape-correction/overview.json","data/shape-point-check/overview.json","data/reference-covariance/overview.json"];
      const reports=await Promise.all(urls.map(async url=>{const r=await fetch(url);if(!r.ok)throw Error(`HTTP ${r.status}`);return r.json();}));
      render(validate(reports));loaded=true;el("shape-load-status").textContent="Đã kiểm tra nguồn, mẫu số và trạng thái. Chưa cấp sai số chuyển động đã hiệu chuẩn.";
    }catch(error){
      for(const id of ["shape-metric-rows","shape-source-rows","shape-failure-rows","shape-coefficient-rows","shared-source-rows"])el(id).replaceChildren();
      for(const id of ["shape-learn-count","shape-dominance","shape-point-count","shared-reference-count","shared-reference-ratio"])el(id).textContent="—";
      for(const id of ["shape-verdict","shape-gate-note","shape-primary-note","shared-reference-note"])el(id).textContent="";
      el("shape-load-status").textContent=`Chưa đọc được báo cáo: ${error.message}. Có thể tải JSON nguồn hoặc thử lại.`;el("shape-retry").hidden=false;
    }finally{pending=false;panel.removeAttribute("aria-busy");}
  }
  panel.addEventListener("toggle",()=>{if(panel.open)load();});el("shape-retry").addEventListener("click",load);if(panel.open)load();
})();

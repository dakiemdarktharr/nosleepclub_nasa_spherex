"use strict";
(() => {
  const el=id=>document.getElementById(id),panel=el("signal-controls");if(!panel)return;
  const geometries=["5756942110218608640","5756958431094222592"],arms=["baseline","corrected"],scenes=["isolated","modeled","omitted"];
  const labels={baseline:"Gốc",corrected:"Hiệu chỉnh",isolated:"Nguồn đơn",modeled:"Nguồn chồng đã khai báo",omitted:"Bỏ sót nguồn chồng",matched:"ePSF gốc",gaussian:"Gaussian độc lập"};
  const finite=x=>typeof x==="number"&&Number.isFinite(x),integer=(x,n)=>Number.isInteger(x)&&x>=0&&x<=n;
  const hash=(x,n=64)=>typeof x==="string"&&new RegExp(`^[a-f0-9]{${n}}$`).test(x);
  const fmt=(x,d=3)=>finite(x)?x.toLocaleString("vi-VN",{maximumFractionDigits:d}):"—",percent=x=>finite(x)?fmt(100*x,1)+"%":"—";
  const fail=()=>{throw Error("mẫu số, nguồn hoặc trạng thái báo cáo không khớp");};
  let pending=false,loaded=false,report=null;
  function count(c,allowed){if(!c||Array.isArray(c)||Object.entries(c).some(([k,v])=>!allowed.includes(k)||!integer(v,640)))fail();return Object.values(c).reduce((a,b)=>a+b,0);}
  const statuses=["fit_completed","fit_failed","preparation_failed"];
  const key=r=>[r.section,r.geometry,r.truth,r.phase,r.scene,r.flux,r.arm].join("/");
  function axes(section){
    const result=new Set();
    for(const g of geometries)for(const t of(section==="noiseless"?["matched","gaussian"]:section==="null"?["none"]:["gaussian"]))
      for(const p of(section==="noiseless"?["0","1","2","3"]:["0","3"]))for(const s of(section==="null"?["isolated"]:scenes))
        for(const f of(section==="noiseless"?["600","1200"]:section==="null"?["0"]:["1200"]))for(const a of arms)result.add([section,g,t,p,s,f,a].join("/"));
    return result;
  }
  function metrics(m,n){
    if(!m||m.n!==n||!integer(n,16)||count(m.identity_counts,["target","companion","elsewhere","ambiguous","unknown"])!==n)fail();
    const values=[m.mean_radial_native_px,m.rms_radial_native_px,m.p90_radial_native_px,m.max_radial_native_px,m.mean_flux_ratio,m.mean_flux_ratio_bias];
    if(n===0){if(values.some(x=>x!==null)||m.mean_dx_dy_native_px!==null||m.flux_ratio_mcse!==null)fail();return;}
    if(values.some(x=>!finite(x))||values.slice(0,4).some(x=>x<0)||!Array.isArray(m.mean_dx_dy_native_px)||m.mean_dx_dy_native_px.length!==2||m.mean_dx_dy_native_px.some(x=>!finite(x))||Math.abs(m.mean_flux_ratio_bias-(m.mean_flux_ratio-1))>1e-10||m.flux_ratio_mcse!==null&&(!finite(m.flux_ratio_mcse)||m.flux_ratio_mcse<0))fail();
  }
  function interval(i,n,d){if(!Array.isArray(i)||i.length!==2||i.some(x=>!finite(x)||x<0||x>1)||i[0]>n/d||i[1]<n/d||i[0]>i[1])fail();}
  function validate(r){
    if(r?.schema!=="signal-control-overview-1"||r.protocol_commit!=="9894074fdacbba908b8816d3dbcac1df901731f1"||r.is_synthetic!==true||r.original_image_added!==false||r.old_assessment_blocked!==true||r.assessment_opened!==false||r.prospective_fields_opened!==0||r.promotion!==false||r.planned!==640||!hash(r.design_sha256)||!hash(r.cell_digest)||r.source_ids?.join()!==geometries.join()||r.obs_id!=="2025W46_2A_0214_3")fail();
    if(Object.keys(r.section_counts||{}).sort().join()!=="noiseless,noisy,null"||r.section_counts.noiseless!==192||r.section_counts.noisy!==384||r.section_counts.null!==64||count(r.status_counts,statuses)!==640)fail();
    const expected=new Set([...axes("noiseless"),...axes("noisy")]),totals={};
    if(!Array.isArray(r.strata)||r.strata.length!==216)fail();
    for(const s of r.strata){const k=key(s),n=s.section==="noiseless"?1:16;if(!expected.delete(k)||s.planned!==n||count(s.status_counts,statuses)!==n||!integer(s.numerical_supported,n)||s.numerical_supported>(s.status_counts.fit_completed||0))fail();metrics(s.all_completed,s.status_counts.fit_completed||0);metrics(s.supported_completed,s.numerical_supported);for(const[k,v]of Object.entries(s.status_counts))totals[k]=(totals[k]||0)+v;}
    if(expected.size)fail();
    const nulls=axes("null");if(!Array.isArray(r.null_strata)||r.null_strata.length!==8)fail();
    for(const s of r.null_strata){if(!nulls.delete(key(s))||s.planned!==8||count(s.status_counts,statuses)!==8||!integer(s.positive_supported,s.status_counts.fit_completed||0)||s.signed_flux_jy?.completed!==(s.status_counts.fit_completed||0))fail();interval(s.positive_supported_interval_95,s.positive_supported,8);for(const k of["mean","median","min","max"]){if((s.status_counts.fit_completed||0)?!finite(s.signed_flux_jy[k]):s.signed_flux_jy[k]!==null)fail();}for(const[k,v]of Object.entries(s.status_counts))totals[k]=(totals[k]||0)+v;}
    if(nulls.size||statuses.some(k=>(totals[k]||0)!==(r.status_counts[k]||0)))fail();
    const gate=r.noiseless_clean_gate,guard=r.noiseless_preservation_guard;
    if(gate?.planned!==128||!integer(gate.passed_count,128)||gate.passed!==(gate.passed_count===128)||guard?.planned_pairs!==64||!integer(guard.passed_count,64)||guard.passed!==(guard.passed_count===64))fail();
    const clean=new Set([...axes("noisy")].filter(k=>!k.includes("/omitted/")));if(r.noisy_clean_gates?.length!==16)fail();
    for(const g of r.noisy_clean_gates){if(!clean.delete(key(g))||g.planned!==16||!integer(g.success,16)||g.observed_sample_gate_passed!==(g.success>=15))fail();interval(g.exact_interval_95,g.success,16);}
    if(clean.size||r.noisy_clean_all_gates_passed!==r.noisy_clean_gates.every(g=>g.observed_sample_gate_passed))fail();
    const components=new Set(["matched","gaussian"].flatMap(t=>["isolated","modeled"].flatMap(s=>arms.map(a=>[t,s,a].join("/")))));let joint=0;
    if(r.fidelity_components?.length!==8)fail();for(const c of r.fidelity_components){if(!components.delete([c.truth,c.scene,c.arm].join("/"))||c.planned!==16)fail();for(const k of["completed","supported","position_within_budget","flux_within_budget","position_and_flux_within_budget","joint_passed"])if(!integer(c[k],16))fail();if(c.joint_passed>Math.min(c.supported,c.position_and_flux_within_budget)||c.position_and_flux_within_budget>Math.min(c.position_within_budget,c.flux_within_budget)||Math.max(c.position_within_budget,c.flux_within_budget,c.supported)>c.completed)fail();joint+=c.joint_passed;}if(components.size||joint!==gate.passed_count)fail();
    if(r.paired?.planned!==320||!integer(r.paired.both_completed,320)||r.paired.missing!==320-r.paired.both_completed)fail();
    if(!hash(r.audit?.receipt_sha256)||count(r.audit.counts,["verified","input_checked_unavailable"])!==640||(r.audit.counts.verified||0)!==(r.status_counts.fit_completed||0)||(r.audit.counts.input_checked_unavailable||0)!==640-(r.status_counts.fit_completed||0)||!hash(r.audit.audit_checkpoint_digest))fail();
    if(r.figure?.path!=="data/signal-controls/scene-example.png"||!hash(r.figure.sha256)||r.figure.record_checksums?.length!==2||r.figure.record_checksums.some(x=>!hash(x))||r.download?.path!=="data/signal-controls/records.json.gz"||!hash(r.download.sha256)||!integer(r.download.bytes,100000000)||r.download.bytes<1)fail();
    return r;
  }
  function row(target,values){const tr=document.createElement("tr");values.forEach((v,i)=>{const td=document.createElement(i===0?"th":"td");if(i===0)td.setAttribute("scope","row");td.textContent=v;tr.append(td);});el(target).append(tr);}
  function source(s){return "Sao "+(s.geometry===geometries[0]?"A":"B");}
  function phase(s){return ["¼, ¼","¼, ¾","¾, ¼","¾, ¾"][Number(s.phase)];}
  function filters(){
    if(!report)return;const truth=el("signal-truth").value,scene=el("signal-scene").value;
    for(const id of["signal-noiseless-rows","signal-noisy-rows"])el(id).replaceChildren();
    el("signal-truth-note").textContent=truth==="matched"?"Đối chứng khớp mẫu: nguồn giả được tạo bằng ePSF gốc. Giúp kiểm tra phần mềm; thuận lợi sẵn cho nhánh gốc, chưa kiểm chứng hình nguồn vật lý.":"Đối chứng khác họ: nguồn giả Gaussian xoay 25°, tích phân trên pixel gốc; hai nhánh vẫn fit bằng ePSF. Sai khác gồm cả hình nguồn và quy ước diện tích pixel.";
    el("signal-scene-note").textContent=scene==="omitted"?"Cố tình bỏ sót bạn đồng hành có cùng độ sáng, cách 1,5 pixel gốc. Đây là phép thử lỗi mô hình; không gộp vào tiêu chí cảnh đã khai báo.":scene==="modeled"?"Hai nguồn có cùng độ sáng, cách 1,5 pixel gốc. Fitter biết vị trí bạn đồng hành và đo riêng biên độ có dấu.":"Chỉ có một nguồn giả và nền nghiêng; không có bạn đồng hành trong ảnh hoặc trong mô hình.";
    for(const s of report.strata.filter(s=>s.section==="noiseless"&&s.truth===truth&&s.scene===scene)){
      const m=s.all_completed,ok=s.numerical_supported===1;row("signal-noiseless-rows",[`${source(s)} · (${phase(s)})`,`${s.flux} µJy`,labels[s.arm],fmt(m.mean_radial_native_px),percent(m.mean_flux_ratio),m.n?(ok?"Qua":"Từ chối số"):"Không fit được"]);
    }
    for(const s of report.strata.filter(s=>s.section==="noisy"&&s.scene===scene)){
      const m=s.all_completed,g=report.noisy_clean_gates.find(g=>key(g)===key(s));
      const identity=m.identity_counts;
      row("signal-noisy-rows",[`${source(s)} · (${phase(s)})`,labels[s.arm],`${m.n}/16`,`${s.numerical_supported}/16`,`${fmt(m.mean_dx_dy_native_px?.[0])}; ${fmt(m.mean_dx_dy_native_px?.[1])}`,fmt(m.rms_radial_native_px),percent(m.mean_flux_ratio_bias),g?`${g.success}/16 · ${percent(g.exact_interval_95[0])}–${percent(g.exact_interval_95[1])}`:"Stress · không có gate",`${identity.target||0} / ${identity.companion||0} / ${identity.elsewhere||0} / ${(identity.unknown||0)+(identity.ambiguous||0)}`]);
    }
  }
  function render(r){
    report=r;el("signal-count").textContent=`${r.status_counts.fit_completed||0}/640`;el("signal-clean-count").textContent=`${r.noiseless_clean_gate.passed_count}/128`;el("signal-noisy-count").textContent=`${r.noisy_clean_gates.filter(g=>g.observed_sample_gate_passed).length}/16`;el("signal-preservation").textContent=`${r.noiseless_preservation_guard.passed_count}/64`;
    el("signal-verdict").textContent=`${r.noiseless_clean_gate.passed?"Cảnh không nhiễu đạt tiêu chí đã khóa.":"Cảnh không nhiễu chưa đạt toàn bộ tiêu chí đã khóa."} ${r.noiseless_preservation_guard.passed?"64 cặp không nhiễu không suy giảm vượt ngân sách tương đối; chưa xác nhận độ đúng hay thông lượng tuyệt đối.":"Hiệu chỉnh chưa giữ tín hiệu đồng đều trên mọi cặp."} 252 ô dành riêng và 30 vùng mới vẫn chưa mở; chưa thay phép đo WISE 0855.`;
    el("signal-component-rows").replaceChildren();for(const c of r.fidelity_components)row("signal-component-rows",[`${labels[c.truth]} · ${labels[c.scene]}`,labels[c.arm],`${c.position_within_budget}/16`,`${c.flux_within_budget}/16`,`${c.supported}/16`,`${c.joint_passed}/16`]);
    el("signal-null-rows").replaceChildren();for(const s of r.null_strata)row("signal-null-rows",[`${source(s)} · (${phase(s)})`,labels[s.arm],`${s.status_counts.fit_completed||0}/8`,`${s.positive_supported}/8`,`${percent(s.positive_supported_interval_95[0])}–${percent(s.positive_supported_interval_95[1])}`,fmt(s.signed_flux_jy.median===null?null:s.signed_flux_jy.median*1e6,1)]);
    el("signal-download").textContent=`640 lượt & kiểm toán · ${fmt(r.download.bytes/1e6,1)} MB gzip ↓`;el("signal-provenance").textContent=`Khóa ${r.protocol_commit.slice(0,7)} · 2 hình học sao · 1 exposure · 192 không nhiễu + 384 có nhiễu + 64 không nguồn. Tất cả lượt, kể cả từ chối số, được giữ trong mẫu số.`;
    el("signal-result").hidden=false;el("signal-plot").hidden=false;el("signal-plot").src=r.figure.path;filters();
  }
  function clear(){report=null;el("signal-result").hidden=true;el("signal-plot").removeAttribute("src");for(const id of["signal-noiseless-rows","signal-noisy-rows","signal-component-rows","signal-null-rows"])el(id).replaceChildren();for(const id of["signal-count","signal-clean-count","signal-noisy-count","signal-preservation"])el(id).textContent="—";}
  async function load(){
    if(pending||loaded)return;pending=true;panel.setAttribute("aria-busy","true");el("signal-retry").hidden=true;el("signal-status").textContent="Đang kiểm tra báo cáo đối chứng đã khóa…";
    try{const response=await fetch("data/signal-controls/overview.json");if(!response.ok)throw Error(`HTTP ${response.status}`);render(validate(await response.json()));loaded=true;el("signal-status").textContent="Đã kiểm toán dữ liệu tổng hợp, mục tiêu fit tại các điểm đã lưu và toàn bộ mẫu số. Kết quả dưới đây chỉ áp dụng cho đối chứng này.";}
    catch(error){clear();el("signal-status").textContent=`Chưa đọc được báo cáo: ${error.message}.`;el("signal-retry").hidden=false;}
    finally{pending=false;panel.removeAttribute("aria-busy");}
  }
  for(const id of["signal-truth","signal-scene"])el(id).addEventListener("change",filters);
  el("signal-plot").addEventListener("error",()=>{el("signal-plot").hidden=true;el("signal-status").textContent="Bảng đã đọc, ảnh minh họa chưa tải được. Hãy thử lại hoặc tải audit.";loaded=false;el("signal-retry").hidden=false;});
  el("signal-plot").addEventListener("load",()=>{if(report){el("signal-retry").hidden=true;loaded=true;}});
  el("signal-retry").addEventListener("click",load);panel.addEventListener("toggle",()=>{if(panel.open)load();});if(panel.open)load();
})();

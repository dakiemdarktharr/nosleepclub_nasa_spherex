"use strict";
(() => {
  const el=id=>document.getElementById(id);
  const variants=[
    ["independent","1 · Độ sáng riêng"],
    ["shared_r7_68_a0","2 · Độ sáng theo phổ · chính"],
    ["tilt_r7_68_a0","3 · Phổ + độ nghiêng"],
    ["shared_r7_68_am4","4 · Reference α = −4"],
    ["shared_r7_68_ap4","5 · Reference α = +4"],
    ["shared_qr2_68_a0","6 · Center QR2"],
    ["shared_r7_17_a0","7 · Response 17 kênh"]
  ];
  const n=(value,digits=3)=>Number.isFinite(value)?value.toLocaleString("vi-VN",{minimumFractionDigits:digits,maximumFractionDigits:digits}):"—";
  const signed=value=>Number.isFinite(value)?`${value>0?"+":""}${n(value,6)}`:"—";
  const reasons={multiple_near_best_modes:"nhiều nghiệm cạnh tranh",boundary:"chạm biên",position_rank_or_covariance:"thiếu rank hoặc covariance",irls_not_converged:"IRLS chưa hội tụ",final_mode_audit_failed:"không kiểm tra được nghiệm cuối",better_final_weight_mode:"có nghiệm tốt hơn điểm đã chọn",renderer_metadata_failed:"lỗi metadata renderer"};
  let data=null,pending=false;
  function validate(value){
    const fail=()=>{throw Error("cấu trúc báo cáo chưa tương thích");};
    if(value?.schema!=="wise-linked-overview-1"||value.schema_version!==1||!Array.isArray(value.pairs)||value.pairs.length!==14||!Array.isArray(value.configurations)||value.configurations.length!==2)fail();
    const counts=value.counts;
    if(!counts||counts.planned_epoch_attempts!==28||counts.recorded_epoch_attempts!==28||!Number.isInteger(counts.fit_completed)||counts.fit_completed<0||counts.failures!==28-counts.fit_completed)fail();
    for(const config of ["broad","strict"]){
      const meta=value.configurations.filter(x=>x.configuration===config);
      const rows=value.pairs.filter(x=>x.configuration===config);
      if(meta.length!==1||rows.length!==7||new Set(rows.map(x=>x.variant)).size!==7||rows.some(x=>!variants.some(v=>v[0]===x.variant)))fail();
      for(const row of rows){
        if(!Number.isInteger(row.successful_epoch_fits)||row.successful_epoch_fits<0||row.successful_epoch_fits>2||typeof row.solver_screening_both!=="boolean")fail();
        if(row.east_north_arcsec!==null&&(!Array.isArray(row.east_north_arcsec)||row.east_north_arcsec.length!==2||!row.east_north_arcsec.every(Number.isFinite)))fail();
        let passed=0,completed=0;
        for(const epoch of ["before","after"]){
          const state=row.epoch_status_and_screening?.[epoch];
          if(!state||typeof state.solver_screening_passed!=="boolean"||!Array.isArray(state.reasons)||state.reasons.some(x=>typeof x!=="string"))fail();
          if(state.solver_screening_passed&&(state.status!=="fit_completed"||state.reasons.length||state.near_best_mode_count>1))fail();
          passed+=Number(state.solver_screening_passed);completed+=Number(state.status==="fit_completed");
        }
        if(row.successful_epoch_fits!==completed||row.solver_screening_both!==(passed===2)||((row.east_north_arcsec!==null)!==(completed===2)))fail();
      }
    }
    return value;
  }
  function screenText(row){
    const epochs=row.epoch_status_and_screening;
    const passed=Object.values(epochs).filter(x=>x.solver_screening_passed).length;
    const failed=["before","after"].filter(key=>!epochs[key].solver_screening_passed).map(key=>{
      const e=epochs[key],when=key==="before"?"trước":"sau";
      const details=e.reasons.map(reason=>reason==="multiple_near_best_modes"&&e.near_best_mode_count>1?`${e.near_best_mode_count} nghiệm`:(reasons[reason]||reason));
      if(e.near_best_mode_count>1&&!e.reasons.includes("multiple_near_best_modes"))details.push(`${e.near_best_mode_count} nghiệm`);
      if(e.status!=="fit_completed")details.push(e.failure||e.status);
      return `${when}: ${details.join(", ")||"chưa được hỗ trợ"}`;
    });
    return `${passed}/2${failed.length?" · "+failed.join("; "):" · số học"}`;
  }
  function renderModes(){
    const diagnostic=data.posthoc_mode_diagnostic;
    if(!diagnostic?.variants||diagnostic.variants.length!==2)throw Error("thiếu chẩn đoán hai nhánh");
    const independent=diagnostic.variants.find(x=>x.variant==="independent");
    const shared=diagnostic.variants.find(x=>x.variant==="shared_r7_68_a0");
    if(!independent||!shared)throw Error("thiếu chẩn đoán flux");
    const rows=el("linked-mode-rows");rows.replaceChildren();
    for(const first of independent.frame_deltas){
      const second=shared.frame_deltas.find(x=>x.obs_id===first.obs_id);
      if(!second)throw Error("thiếu exposure đối chứng");
      const tr=document.createElement("tr");
      for(const text of [first.obs_id,signed(first.weighted_chi2_mode1_minus_mode0),signed(second.weighted_chi2_mode1_minus_mode0)]){
        const td=document.createElement("td");td.textContent=text;tr.append(td);
      }
      rows.append(tr);
    }
    el("linked-mode-status").textContent="Replay hậu kiểm tại vị trí và trọng số đã lưu, không tối ưu lại. Chi phí, flux và residual tại điểm đã lưu khớp đúng trên runtime hiện tại.";
  }
  function render(){
    if(!data)return;
    const config=el("linked-configuration").value;
    const rows=data.pairs.filter(x=>x.configuration===config);
    const meta=data.configurations.find(x=>x.configuration===config);
    if(rows.length!==7||!meta)throw Error("bộ ảnh chưa tương thích");
    const primary=rows.find(x=>x.variant==="shared_r7_68_a0");
    const both=rows.filter(x=>x.solver_screening_both).length;
    const ambiguous=rows.filter(x=>Object.values(x.epoch_status_and_screening).some(e=>e.near_best_mode_count>1)).length;
    el("linked-verdict").textContent=`${both}/7 nhánh qua kiểm tra số học ở cả hai đợt. ${ambiguous?`${ambiguous}/7 nhánh có nghiệm cạnh tranh; chưa cấp sai số hiệu chuẩn.`:"Các vector vẫn phụ thuộc giả định phổ; chưa có bằng chứng giảm bias hoặc hiệu chuẩn sai số."}`;
    el("linked-attempts").textContent=`${data.counts.fit_completed}/${data.counts.planned_epoch_attempts}`;
    el("linked-change").textContent=`${n(primary.change_from_independent_arcsec)}″`;
    el("linked-spread").textContent=`${n(meta.max_pairwise_spread_arcsec)}″`;
    const body=el("linked-rows");body.replaceChildren();
    for(const [id,label] of variants){
      const row=rows.find(x=>x.variant===id),tr=document.createElement("tr");
      if(id==="shared_r7_68_a0")tr.className="linked-primary";
      const title=document.createElement("th");title.scope="row";title.textContent=label;tr.append(title);
      for(const text of [n(row.east_north_arcsec?.[0]),n(row.east_north_arcsec?.[1]),n(row.change_from_independent_arcsec),screenText(row)]){
        const td=document.createElement("td");td.textContent=text;tr.append(td);
      }
      body.append(tr);
    }
    el("linked-caption").textContent=`${config==="strict"?"Bộ chặt":"Bộ rộng"} · vector giữa hai đợt · giây cung (″). Giữ cả nhánh không qua screening.`;
    const path=`data/linked-flux/sensitivity-${config}.svg`;
    el("linked-chart").src=path;
    el("linked-chart").alt=`${config==="strict"?"Bộ chặt":"Bộ rộng"}: nhánh phổ chính đổi ${n(primary.change_from_independent_arcsec)} giây cung so độ sáng riêng; khoảng cách lớn nhất giữa mọi vector ${n(meta.max_pairwise_spread_arcsec)} giây cung. Các giá trị đầy đủ trong bảng.`;
    el("linked-download-chart").href=path;
    el("linked-note").textContent=`${meta.frames_per_epoch.before} ảnh trước + ${meta.frames_per_epoch.after} ảnh sau. 28 lượt fit ở thẻ trên là tổng cả hai bộ; bộ chặt nằm trong bộ rộng, dùng chung 20 exposure. Độ đổi là độ nhạy mô hình, chưa phải sai số hoặc độ chính xác. Kiểm tra số học không chứng nhận thiên văn; covariance cục bộ chưa gồm sai số hệ thống hoặc bất định giữa các nghiệm.`;
  }
  async function load(){
    if(pending||data)return;
    pending=true;el("linked-retry").hidden=true;el("linked-flux").setAttribute("aria-busy","true");
    try{
      const response=await fetch("data/linked-flux/overview.json");
      if(!response.ok)throw Error(`HTTP ${response.status}`);
      const next=validate(await response.json());
      data=next;renderModes();render();
    }catch(error){
      data=null;el("linked-rows").replaceChildren();
      el("linked-verdict").textContent=`Chưa tải được đối chứng: ${error.message}. Thử lại hoặc mở JSON nguồn.`;
      el("linked-retry").hidden=false;
    }finally{pending=false;el("linked-flux").removeAttribute("aria-busy");}
  }
  el("linked-configuration").addEventListener("change",render);
  el("linked-retry").addEventListener("click",load);
  load();
})();

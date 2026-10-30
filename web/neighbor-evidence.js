"use strict";
(() => {
  const el=id=>document.getElementById(id),details=el("neighbor-intervention");
  const variants=["plane_nearest_free","plane_nearest_nonnegative","plane_bilinear_free","plane_bilinear_nonnegative","quadratic_nearest_free","quadratic_nearest_nonnegative","quadratic_bilinear_free","quadratic_bilinear_nonnegative"];
  const cases=["plane_300uJy","plane_600uJy","quadratic_300uJy","quadratic_600uJy"];
  const n=(v,d=3)=>Number.isFinite(v)?v.toLocaleString("vi-VN",{minimumFractionDigits:d,maximumFractionDigits:d}):"—";
  const reasons={boundary:"chạm biên",position_rank:"vị trí suy biến",irls_not_converged:"trọng số chưa hội tụ",final_mode_audit_failed:"không kiểm tra được nghiệm cuối",better_final_weight_mode:"có nghiệm tốt hơn điểm đã chọn",multiple_near_best_modes:"nhiều nghiệm cạnh tranh"};
  let data=null,pending=false;
  function validate(value){
    const fail=()=>{throw Error("định dạng hoặc mẫu số chưa tương thích");};
    if(value?.schema!=="neighbor-intervention-overview-1"||value.schema_version!==1||!Array.isArray(value.real?.configurations)||value.real.configurations.length!==2||!Array.isArray(value.controls?.cases)||value.controls.cases.length!==4)fail();
    if(value.counts?.planned!==288||value.counts.recorded!==288||!Number.isInteger(value.counts.fit_completed)||value.counts.fit_completed<0||value.counts.fit_completed>288||value.counts.failed!==288-value.counts.fit_completed)fail();
    for(const config of ["broad","strict"]){
      const matches=value.real.configurations.filter(x=>x.configuration===config);
      if(matches.length!==1||!Array.isArray(matches[0].pairs)||matches[0].pairs.length!==8)fail();
      const rows=matches[0].pairs;
      if(new Set(rows.map(x=>x.variant)).size!==8||rows.some(x=>!variants.includes(x.variant)))fail();
      for(const row of rows){
        const complete=row.before_status==="fit_completed"&&row.after_status==="fit_completed";
        if(typeof row.numerical_support_both!=="boolean"||!Array.isArray(row.before_reasons)||!Array.isArray(row.after_reasons))fail();
        if([row.before_status,row.after_status].some(x=>!["fit_completed","fit_failed","preparation_failed"].includes(x))||[...row.before_reasons,...row.after_reasons].some(x=>typeof x!=="string"))fail();
        if(row.east_north_arcsec!==null&&(!Array.isArray(row.east_north_arcsec)||row.east_north_arcsec.length!==2||!row.east_north_arcsec.every(Number.isFinite)))fail();
        if((row.east_north_arcsec!==null)!==complete||row.numerical_support_both&&(!complete||row.before_reasons.length||row.after_reasons.length))fail();
      }
      if(matches[0].numerical_supported_pairs!==rows.filter(x=>x.numerical_support_both).length)fail();
    }
    if(new Set(value.controls.cases.map(x=>x.case)).size!==4)fail();
    for(const item of value.controls.cases){
      if(!cases.includes(item.case)||item.planned_draws!==16||!Array.isArray(item.arms)||item.arms.length!==2)fail();
      if(new Set(item.arms.map(x=>x.variant)).size!==2||item.arms.some(x=>!variants.slice(0,2).includes(x.variant)))fail();
      for(const arm of item.arms)for(const key of ["all_completed","common_completed","common_numerically_supported"]){
        const stats=arm.selections?.[key];
        if(!stats||!Number.isInteger(stats.n)||stats.n<0||stats.n>16)fail();
        for(const field of ["rms_arcsec","p90_arcsec"])if(stats.n===0?stats[field]!==null:!Number.isFinite(stats[field])||stats[field]<0)fail();
      }
      for(const key of ["common_completed","common_numerically_supported"])if(item.arms[0].selections[key].n!==item.arms[1].selections[key].n)fail();
    }
    return value;
  }
  function epochStatus(row){
    if(row.numerical_support_both)return "2/2 · số học";
    return ["before","after"].map(key=>{
      const label=key==="before"?"Trước":"Sau",status=row[`${key}_status`],list=row[`${key}_reasons`];
      if(status!=="fit_completed")return `${label}: ${status==="preparation_failed"?"lỗi chuẩn bị":"fit thất bại"}`;
      return list.length?`${label}: ${list.map(r=>reasons[r]||r).join(", ")}`:null;
    }).filter(Boolean).join("; ")||"Chưa được hỗ trợ";
  }
  function cells(body,values,firstHeader=false){
    const tr=document.createElement("tr");
    values.forEach((value,i)=>{const td=document.createElement(firstHeader&&i===0?"th":"td");if(i===0&&firstHeader)td.scope="row";td.textContent=value;tr.append(td);});
    body.append(tr);return tr;
  }
  function renderReal(){
    if(!data)return;
    const config=el("neighbor-configuration").value,group=data.real.configurations.find(x=>x.configuration===config);
    const rows=group.pairs,primary=rows.find(x=>x.variant==="plane_nearest_nonnegative");
    el("neighbor-attempts").textContent=`${data.counts.fit_completed}/288`;
    el("neighbor-shift").textContent=`${n(primary.change_from_primary_control_arcsec)}″`;
    el("neighbor-support").textContent=`${group.numerical_supported_pairs}/8`;
    const body=el("neighbor-real-rows");body.replaceChildren();
    variants.forEach((variant,index)=>{
      const row=rows.find(x=>x.variant===variant),parts=variant.split("_");
      const tr=cells(body,[`${index+1} · ${parts[0]==="plane"?"Mặt phẳng":"Bậc hai"}`,parts[1]==="nearest"?"Gần nhất":"Nội suy 4 vùng",parts[2]==="free"?"Có dấu":"Không âm",row.east_north_arcsec?row.east_north_arcsec.map(v=>n(v)).join(" / "):"—",n(row.change_from_primary_control_arcsec),epochStatus(row)],true);
      if(index===1)tr.className="linked-primary";
    });
    el("neighbor-real-status").textContent=`${group.frames_per_epoch.before} ảnh trước + ${group.frames_per_epoch.after} ảnh sau. Khoảng cách lớn nhất giữa mọi vector tính được: ${n(group.max_pairwise_spread_arcsec)}″. Giữ cả nhánh không qua kiểm tra số học; độ đổi giữa các mô hình chưa phải sai số so vị trí đúng.`;
    const path=`data/neighbor-intervention/real-sensitivity-${config}.svg`;
    el("neighbor-real-chart").src=path;el("neighbor-real-chart").hidden=false;
    el("neighbor-real-chart").alt=`${config==="strict"?"Bộ chặt":"Bộ rộng"}: tám giả định nền, ePSF và dấu flux hàng xóm. Các vector đầy đủ và lý do từ chối ở bảng.`;
    el("neighbor-chart-download").href=path;
  }
  function renderControls(){
    if(!data)return;
    const selection=el("neighbor-control-selection").value,body=el("neighbor-control-rows");body.replaceChildren();
    for(const item of data.controls.cases){
      const a=item.arms.find(x=>x.variant===variants[0]),b=item.arms.find(x=>x.variant===variants[1]);
      const first=a.selections[selection],second=b.selections[selection];
      const label=`${item.case.startsWith("plane_")?"Nền plane":"Nền bậc hai"} · ${item.case.includes("300")?"300":"600"} µJy`;
      cells(body,[label,`${first.n}/16`,`${second.n}/16`,`${n(first.rms_arcsec)} / ${n(second.rms_arcsec)}`,`${n(first.p90_arcsec)} / ${n(second.p90_arcsec)}`],true);
    }
    const label=selection==="all_completed"?"Mọi cặp fit được, mẫu riêng từng nhánh":selection==="common_completed"?"Cùng cặp fit được ở cả hai nhánh":"Cùng cặp qua sàng lọc số ở cả hai nhánh";
    el("neighbor-controls-note").textContent=`${label}. RMS/P90 là sai lệch vector so truth Gaussian; cột số cặp luôn giữ mẫu số 16 đã định. 64 draw dùng cùng một geometry, không phải 64 trường trời. Không có covariance hoặc coverage hiệu chuẩn; có thể xem đủ failure và từng draw trong JSON.`;
  }
  async function load(){
    if(data||pending)return;
    pending=true;details.setAttribute("aria-busy","true");el("neighbor-retry").hidden=true;
    el("neighbor-status").textContent="Đang tải tóm tắt đối chứng…";
    try{
      const response=await fetch("data/neighbor-intervention/overview.json");if(!response.ok)throw Error(`HTTP ${response.status}`);
      data=validate(await response.json());renderReal();renderControls();
      el("neighbor-status").textContent="Đối chứng đã hoàn tất. Chưa chọn mô hình hoặc cấp sai số hiệu chuẩn.";
      el("neighbor-control-chart").src="data/neighbor-intervention/control-error-pairs.svg";el("neighbor-control-chart").hidden=false;
    }catch(error){
      data=null;el("neighbor-real-rows").replaceChildren();el("neighbor-control-rows").replaceChildren();
      for(const id of ["neighbor-attempts","neighbor-shift","neighbor-support"])el(id).textContent="—";
      for(const id of ["neighbor-real-status","neighbor-controls-note"])el(id).textContent="";
      el("neighbor-real-chart").hidden=true;el("neighbor-control-chart").hidden=true;
      el("neighbor-status").textContent=`Chưa tải được báo cáo: ${error.message}. Thử lại hoặc mở JSON nguồn.`;el("neighbor-retry").hidden=false;
    }
    finally{pending=false;details.removeAttribute("aria-busy");}
  }
  details.addEventListener("toggle",()=>{if(details.open)load();});
  el("neighbor-configuration").addEventListener("change",renderReal);
  el("neighbor-control-selection").addEventListener("change",renderControls);
  el("neighbor-retry").addEventListener("click",load);
  if(details.open)load();
})();

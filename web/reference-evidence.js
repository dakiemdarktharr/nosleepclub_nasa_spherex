"use strict";
(() => {
  const el=id=>document.getElementById(id),panel=el("reference-presence");
  if(!panel)return;
  const variants=["nearest","bilinear"],caseNames=["plane_null","quadratic_null","plane_300uJy","plane_600uJy","quadratic_300uJy","quadratic_600uJy"];
  const fmt=(v,d=3)=>Number.isFinite(v)?v.toLocaleString("vi-VN",{minimumFractionDigits:d,maximumFractionDigits:d}):"—";
  const integer=(x,n)=>Number.isInteger(x)&&x>=0&&x<=n;
  const hash=(v,n)=>typeof v==="string"&&new RegExp(`^[a-f0-9]{${n}}$`).test(v);
  let stars=null,presence=null,pending=false;
  function fail(){throw Error("báo cáo chưa đủ hoặc mẫu số không khớp");}
  function metric(value,count){
    if(value?.n!==count)fail();
    for(const key of ["rms_arcsec","median_radial_arcsec","p90_radial_arcsec"])
      if(count===0?value[key]!==null:!Number.isFinite(value[key])||value[key]<0)fail();
    if(count===0?value.mean_east_north_arcsec!==null:!Array.isArray(value.mean_east_north_arcsec)||value.mean_east_north_arcsec.length!==2||!value.mean_east_north_arcsec.every(Number.isFinite))fail();
  }
  function starSummary(value,planned){
    if(value?.planned_pairs!==planned||!integer(value.common_completed,planned)||!integer(value.common_numerical,value.common_completed)||!Array.isArray(value.arms)||value.arms.length!==2||new Set(value.arms.map(x=>x.variant)).size!==2)fail();
    for(const arm of value.arms){
      if(!variants.includes(arm.variant)||arm.planned!==planned||!integer(arm.completed,planned)||arm.failed!==planned-arm.completed||!integer(arm.numerically_supported,arm.completed)||!integer(arm.negative_target_flux,arm.completed)||value.common_completed>arm.completed||value.common_numerical>arm.numerically_supported)fail();
      metric(arm.all_completed,arm.completed);metric(arm.common_completed,value.common_completed);metric(arm.common_numerical,value.common_numerical);
    }
    for(const key of ["median_model_shift_arcsec","maximum_model_shift_arcsec"])
      if(value.common_completed===0?value[key]!==null:!Number.isFinite(value[key])||value[key]<0)fail();
    return value;
  }
  function validateStars(value){
    if(value?.schema!=="reference-star-overview-1"||value.promotion!==false||!hash(value.protocol_commit,40)||!hash(value.design_sha256,64)||!hash(value.journal_digest,64))fail();
    const counts=value.counts,s=counts?.statuses;
    if(counts?.expected!==840||counts.recorded!==840||counts.missing!==0||!s||!integer(s.fit_completed,840)||!integer(s.fit_failed,840)||!integer(s.preparation_failed,840)||s.fit_completed+s.fit_failed+s.preparation_failed!==840)fail();
    starSummary(value.summary,420);
    if(!Array.isArray(value.sources)||value.sources.length!==21||new Set(value.sources.map(x=>x.source_id)).size!==21||value.sources.some(x=>typeof x.source_id!=="string"||!/^\d+$/.test(x.source_id)))fail();
    if(!Array.isArray(value.frames)||value.frames.length!==20||new Set(value.frames.map(x=>x.obs_id)).size!==20)fail();
    value.sources.forEach(x=>starSummary(x,20));value.frames.forEach(x=>starSummary(x,21));
    for(const variant of variants){
      const total=value.summary.arms.find(x=>x.variant===variant).completed;
      if(value.sources.reduce((sum,x)=>sum+x.arms.find(a=>a.variant===variant).completed,0)!==total||value.frames.reduce((sum,x)=>sum+x.arms.find(a=>a.variant===variant).completed,0)!==total)fail();
    }
    if(value.summary.arms.reduce((sum,x)=>sum+x.completed,0)!==s.fit_completed)fail();
    return value;
  }
  function validatePresence(value){
    if(value?.schema!=="source-presence-overview-1"||value.promotion!==false||!hash(value.protocol_commit,40)||!hash(value.threshold_commit,40)||!hash(value.geometry_sha256,64)||!Number.isFinite(value.threshold?.value)||value.threshold.value<0||value.threshold.protocol_commit!==value.protocol_commit||value.threshold.threshold_commit!==value.threshold_commit)fail();
    if(value.calibration?.planned!==1998||value.calibration.completed!==1998||value.calibration.failed!==0||value.calibration.missing!==0||value.calibration.recorded!==1998)fail();
    if(value.validation?.planned!==5994||value.validation.missing!==0||value.validation.recorded!==5994||!Array.isArray(value.cases)||value.cases.length!==6||new Set(value.cases.map(x=>x.scenario)).size!==6)fail();
    for(const row of value.cases){
      if(!caseNames.includes(row.scenario)||row.planned!==999||!integer(row.completed,999)||row.failed!==999-row.completed||!integer(row.accepted,row.completed)||!["plane","quadratic"].includes(row.background)||row.one_sided_confidence!==.975)fail();
      const isNull=row.scenario.endsWith("_null"),flux=isNull?0:row.scenario.includes("300")?300:600;
      if(row.role!==(isNull?"null":"positive")||row.flux_ujy!==flux||row.background!==(row.scenario.startsWith("plane")?"plane":"quadratic"))fail();
      const bound=isNull?row.false_accept_upper:row.power_lower;
      if(!Number.isFinite(bound)||bound<0||bound>1||(isNull?row.power_lower!==null:row.false_accept_upper!==null)||row.conservative_events!==(isNull?row.accepted+row.failed:row.accepted))fail();
      if(isNull?bound<row.conservative_events/999:bound>row.accepted/999)fail();
      if(row.gate_pass!==(isNull?bound<=.01:flux===600?bound>=.8:null))fail();
    }
    for(const name of ["completed","failed"])if(value.cases.reduce((sum,x)=>sum+x[name],0)!==value.validation[name])fail();
    if(value.conditional_gates_passed!==value.cases.every(x=>x.gate_pass!==false))fail();
    return value;
  }
  function cells(body,values){
    const tr=document.createElement("tr");values.forEach((value,i)=>{
      const cell=document.createElement(i===0?"th":"td");if(i===0)cell.scope="row";
      cell.textContent=value;tr.append(cell);
    });body.append(tr);
  }
  function renderStars(){
    if(!stars)return;
    const selection=el("rstar-selection").value,summary=stars.summary,body=el("rstar-summary-rows"),sources=el("rstar-source-rows");
    body.replaceChildren();sources.replaceChildren();
    for(const variant of variants){
      const arm=summary.arms.find(x=>x.variant===variant),m=arm[selection];
      cells(body,[variant==="nearest"?"ePSF gần nhất":"ePSF nội suy",`${m.n}/420`,fmt(m.rms_arcsec),fmt(m.median_radial_arcsec),fmt(m.p90_radial_arcsec)]);
    }
    for(const source of stars.sources){
      const a=source.arms.find(x=>x.variant==="nearest")[selection],b=source.arms.find(x=>x.variant==="bilinear")[selection];
      cells(sources,[source.source_id,`${a.n}/20 · ${b.n}/20`,`${fmt(a.rms_arcsec)} / ${fmt(b.rms_arcsec)}`]);
    }
    el("rstar-attempts").textContent=`${stars.counts.statuses.fit_completed}/840`;
    el("rstar-failures").textContent=`${stars.counts.statuses.preparation_failed+stars.counts.statuses.fit_failed}/840`;
    el("rstar-shift").textContent=`${fmt(summary.maximum_model_shift_arcsec)}″`;
    el("rstar-note").textContent=`${summary.common_completed}/420 cặp có kết quả ở cả hai nhánh; ${summary.common_numerical}/420 cặp qua sàng lọc số. Mỗi sao lặp trên 20 ảnh; đây là 21 sao đã từng được chọn từ ảnh, chưa phải tập kiểm định độc lập. Sai lệch so Gaia còn gồm căn chỉnh và mô hình chuyển vị trí.`;
    el("rstar-download").textContent=`840 bản ghi đầy đủ · ${fmt(stars.download.bytes/1e6,1)} MB gzip ↓`;
  }
  function renderPresence(){
    if(!presence)return;
    const body=el("presence-case-rows");body.replaceChildren();
    for(const id of caseNames){
      const row=presence.cases.find(x=>x.scenario===id),isNull=row.role==="null";
      const label=`${row.background==="plane"?"Nền phẳng nghiêng":"Nền bậc hai"} · ${isNull?"không có mục tiêu":`${row.flux_ujy} µJy`}`;
      const bound=isNull?`Báo nhầm ≤ ${fmt(row.false_accept_upper*100,2)}%`:`Thu hồi ≥ ${fmt(row.power_lower*100,2)}%`;
      cells(body,[label,`${row.completed}/999`,`${row.accepted}/999`,String(row.failed),bound,row.gate_pass===null?"Chỉ báo cáo":row.gate_pass?"Đạt trong mô phỏng":"Chưa đạt"]);
    }
    el("presence-threshold").textContent=fmt(presence.threshold.value,4);
    el("presence-counts").textContent=`1.998 lượt học ngưỡng + 5.994 lượt kiểm tra riêng. ${presence.validation.failed} lượt kiểm tra lỗi, vẫn nằm trong mẫu số. Toàn bộ dùng một bố cục ảnh đã mở.`;
    const faint=presence.cases.filter(x=>x.flux_ujy===300).map(x=>x.accepted/999*100);
    el("presence-verdict").textContent=presence.conditional_gates_passed?`Đạt điều kiện đã khóa tại 600 µJy. Ở mức 300 µJy chỉ nhận ${fmt(Math.min(...faint),1)}–${fmt(Math.max(...faint),1)}% lượt thử. Chưa xác nhận khả năng phát hiện trên bầu trời thật.`:"Chưa đạt đủ các ngưỡng đã khóa. Chưa đưa quy tắc này vào quyết định phát hiện trên ảnh thật.";
    el("presence-download").textContent=`7.992 lượt & geometry · ${fmt(presence.download.bytes/1e6,1)} MB gzip ↓`;
  }
  async function load(){
    if(pending||stars&&presence)return;
    pending=true;panel.setAttribute("aria-busy","true");el("reference-retry").hidden=true;
    el("reference-status").textContent="Đang tải hai tóm tắt đã kiểm tra…";
    try{
      const urls=["data/reference-stars/overview.json","data/source-presence/overview.json"];
      const responses=await Promise.all(urls.map(async url=>{const response=await fetch(url);if(!response.ok)throw Error(`HTTP ${response.status}`);return response.json();}));
      const checkedStars=validateStars(responses[0]),checkedPresence=validatePresence(responses[1]);
      for(const value of [checkedStars,checkedPresence])if(!integer(value.download?.bytes,1e9)||value.download.bytes===0||!hash(value.download.sha256,64))fail();
      stars=checkedStars;presence=checkedPresence;renderStars();renderPresence();
      el("reference-status").textContent="Đã kiểm tra xong hai phép thử. Sai số chuyển động WISE 0855 vẫn chưa được hiệu chuẩn.";
    }catch(error){
      stars=null;presence=null;
      for(const id of ["rstar-summary-rows","rstar-source-rows","presence-case-rows"])el(id).replaceChildren();
      for(const id of ["rstar-attempts","rstar-failures","rstar-shift","presence-threshold"])el(id).textContent="—";
      for(const id of ["rstar-note","presence-counts","presence-verdict"])el(id).textContent="";
      el("reference-status").textContent=`Chưa đọc được báo cáo: ${error.message}. Thử lại hoặc tải JSON nguồn.`;el("reference-retry").hidden=false;
    }finally{pending=false;panel.removeAttribute("aria-busy");}
  }
  const tabs=[el("reference-tab-stars"),el("reference-tab-presence")],pages=[el("reference-stars-panel"),el("reference-presence-panel")];
  function selectTab(index,focus=false){tabs.forEach((tab,i)=>{tab.setAttribute("aria-selected",String(i===index));tab.tabIndex=i===index?0:-1;pages[i].hidden=i!==index;});if(focus)tabs[index].focus();}
  tabs.forEach((tab,index)=>{
    tab.addEventListener("click",()=>selectTab(index));
    tab.addEventListener("keydown",event=>{const to=event.key==="ArrowRight"?(index+1)%2:event.key==="ArrowLeft"?(index+1)%2:event.key==="Home"?0:event.key==="End"?1:null;if(to!==null){event.preventDefault();selectTab(to,true);}});
  });
  panel.addEventListener("toggle",()=>{if(panel.open)load();});
  el("rstar-selection").addEventListener("change",renderStars);el("reference-retry").addEventListener("click",load);
  selectTab(0);if(panel.open)load();
})();

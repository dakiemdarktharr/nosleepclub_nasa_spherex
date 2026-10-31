"use strict";
/* One current data context, four task screens, explicit research navigation. */
((root,factory)=>{const api=factory();if(typeof module==="object"&&module.exports)module.exports=api;if(root?.document)api.mount(root);})(typeof window!=="undefined"?window:globalThis,()=>{
  const stepIds={data:"home",compare:"compare-step",check:"check-step",review:"review-step",research:"research"};
  const titles={data:"Chọn dữ liệu",compare:"So ảnh",check:"Kiểm tra",review:"Ghi nhận",research:"Kho kiểm chứng"};
  const reportTitles={"signal-controls":["Tín hiệu và pha pixel","Nguồn giả"],"shape-validation":["Mẫu điểm sáng và sai số","Calibration"],"reference-presence":["Sao tham chiếu và nhận nguồn","Đối chứng"],"neighbor-intervention":["Nguồn chồng","Đối chứng"],"linked-flux":["Độ nhạy vector WISE","Ảnh thật"],validation:["Mask, phổ và diagnostics","Đã mở"],"research-history":["Thí nghiệm 0.5–0.9","Lịch sử"],"next-steps":["Kế hoạch tiếp theo","Chưa mở"]};
  function signature(source,c){
    if(!c?.ready)return null;
    return source==="wise"?JSON.stringify([source,c.analysis_sha256,c.scene_id,c.selection]):JSON.stringify([source,c.query,c.reference?.obs_id,c.current?.obs_id,c.reference_index,c.current_index]);
  }
  function sourceFromSearch(search){const p=new URLSearchParams(search),chosen=p.get("flow_source");return ["wise","irsa"].includes(chosen)?chosen:p.has("sky_ra")?"irsa":"wise";}
  function decide(request,source,context,checked){
    if(request==="data"||request==="research")return {step:request,reason:""};
    if(source==="irsa"&&request==="compare"&&context?.listed)return {step:request,reason:""};
    if(!context?.ready)return {step:"data",reason:source==="wise"?"Chờ bộ ảnh tải xong hoặc chọn lại dữ liệu.":"Tìm và tải ảnh IRSA trước khi tiếp tục."};
    if(source==="irsa"&&request!=="compare"&&!context.paired)return {step:"compare",reason:"Giữ ảnh A, rồi chọn một ảnh B khác để so sánh."};
    if(request==="review"&&checked!==signature(source,context))return {step:"check",reason:"Xem kết quả và giới hạn trước khi ghi nhận."};
    return {step:request,reason:""};
  }
  function mount(w){
    const d=w.document,el=id=>d.getElementById(id);if(!el("workflow-main"))return;
    let source="wise",step="data",checked=null,lastWork="data",pending=null,lastSignature=null,initial=true;
    const views=[...d.querySelectorAll("[data-workflow-view]")],stepLinks=[...d.querySelectorAll("[data-step-link]")],reportRoots=[...d.querySelectorAll("[data-report-root]")];
    const context=()=>source==="wise"?w.SkyApp?.context():w.SkyExplorer?.context();
    const pause=()=>{w.SkyApp?.pause();w.SkyExplorer?.pause();};
    function displaySource(){
      const wise=source==="wise";
      el("workflow-source-wise").setAttribute("aria-pressed",String(wise));el("workflow-source-irsa").setAttribute("aria-pressed",String(!wise));
      for(const id of["workflow-data-wise","workflow-other-scenes","workflow-compare-wise","workflow-check-wise","workflow-review-wise"])el(id).hidden=!wise;
      for(const id of["explore","workflow-compare-irsa","workflow-check-irsa","workflow-review-irsa"])el(id).hidden=wise;
      el("workflow-context-kind").textContent=wise?"Bộ mẫu WISE":"IRSA · tự chọn";
    }
    function label(c){
      if(source==="wise")return c?.ready?`WISE 0855 · ${c.label}`:"WISE 0855 · đang tải";
      if(!c?.query)return "IRSA · chưa chọn ảnh";
      return `IRSA ${c.query.release.toUpperCase()} · D${c.query.det} · RA ${Number(c.query.ra).toFixed(5)}° / Dec ${Number(c.query.dec).toFixed(5)}°`;
    }
    function update(){
      const c=context(),key=signature(source,c);if(key!==lastSignature){checked=null;lastSignature=key;}
      const target=source==="wise"?(c?.selection==="target"?"WISE 0855":c?.selection||"Chưa chọn vùng"):(c?.paired?`Ảnh ${c.reference_index+1} / ${c.current_index+1}`:"Chưa đủ cặp ảnh");
      el("workflow-context").textContent=step==="research"?"Báo cáo đã công bố":label(c);el("workflow-compare-context").textContent=label(c);
      el("workflow-context-kind").textContent=step==="research"?"Kho kiểm chứng":source==="wise"?"Bộ mẫu WISE":"IRSA · tự chọn";
      for(const id of["workflow-check-context","workflow-review-context"])el(id).textContent=`${label(c)} · ${target}`;
      el("workflow-data-next").disabled=!(c?.ready||source==="irsa"&&c?.listed);el("workflow-compare-next").disabled=!c?.ready||source==="irsa"&&!c.paired;
      el("workflow-check-next").disabled=!c?.ready||source==="irsa"&&!c.paired;
      el("workflow-data-processing").textContent=!c?.ready?"—":c?.kind==="coadd"?"Cộng ảnh theo epoch":"Ảnh đơn";
      if(source==="wise"){for(const part of["before","after"]){const image=el("workflow-dataset-"+part);image.hidden=!c?.ready;if(c?.ready)image.src=c[part+"_image"];el("workflow-dataset-"+part+"-date").textContent=c?.ready?`${part==="before"?"Trước":"Sau"} · ${c[part+"_date"]||""}`:"Đang tải ảnh…";}}
      el("workflow-data-state").textContent=source==="wise"?(c?.ready?"Bộ ảnh đã sẵn sàng":"Chưa tải xong bộ ảnh"):(c?.dirty?"Cấu hình chưa truy vấn":c?.ready?`${c.count} quan sát · đã tải ảnh ${c.current_index+1}`:c?.status||"Nhập tọa độ và tìm ảnh");
      el("workflow-frame-status").textContent=source==="irsa"?(c?.status||""):"";
      el("workflow-check-warning").textContent=source==="irsa"?"Ảnh cùng WCS hiển thị · chưa căn chỉnh theo sao hoặc fit chuyển động.":c?.selection!=="target"?"Vùng sai khác chưa gán danh tính · chưa có phép đo chuyển động cho vùng này.":c?.kind!=="coadd"?"Ảnh đơn · fit biên độ ở vị trí dự kiến; chưa đo chuyển động độc lập.":"Phép đo thử nghiệm · sai số chưa hiệu chuẩn · chưa xác nhận chuyển động.";
      el("workflow-selection-check").open=source==="wise"&&c?.selection!=="target";
      const motionContext=source==="wise"&&c?.kind==="coadd"&&c?.selection==="target";
      el("workflow-motion-summary").hidden=!motionContext;el("workflow-measurement-context").hidden=!motionContext;
      const obsLabel=(row,empty)=>row?`${Number.isFinite(row.t_min_mjd)?new Date((row.t_min_mjd-40587)*86400000).toISOString().slice(0,16).replace("T"," ")+" UTC · ":""}${row.obs_id}`:empty;
      el("workflow-frame-a").textContent=obsLabel(c?.reference,"Chưa giữ ảnh A");el("workflow-frame-b").textContent=obsLabel(c?.current,"Chưa chọn ảnh B");
      stepLinks.forEach(a=>{const active=a.dataset.stepLink===step;a.classList.toggle("active",active);if(active)a.setAttribute("aria-current","step");else a.removeAttribute("aria-current");a.setAttribute("data-complete",String(a.dataset.stepLink==="data"&&Boolean(c?.ready)||a.dataset.stepLink==="check"&&checked===key&&Boolean(key)));});
      d.querySelectorAll("#main-nav a").forEach(a=>{const active=a.getAttribute("href")==="#"+stepIds[step];a.classList.toggle("active",active);if(active)a.setAttribute("aria-current","page");else a.removeAttribute("aria-current");});
      d.querySelectorAll(".workflow-library-link").forEach(a=>{if(step==="research")a.setAttribute("aria-current","page");else a.removeAttribute("aria-current");});
      el("workflow-return").href="#"+stepIds[lastWork];
      if(step==="review"){
        const image=source==="wise"?w.SkyApp?.preview():c?.preview;el("workflow-review-image").hidden=!image;if(image)el("workflow-review-image").src=image;else el("workflow-review-image").removeAttribute("src");
        el("workflow-review-caption").textContent=`${target} · ${source==="wise"?"ảnh đang so sánh":"ảnh B"}`;
      }
      return c;
    }
    function choose(next){const url=new URL(w.location.href);url.searchParams.set("flow_source",next);w.history.replaceState(null,"",url);if(next===source)return;pause();source=next;checked=null;pending=null;lastSignature=null;displaySource();update();}
    function requested(){
      let id;try{id=decodeURIComponent(w.location.hash.slice(1));}catch{id="";}
      if(!id)return {id:"home",step:"data"};
      const aliases={home:"data","data-step":"data","compare-step":"compare","check-step":"check","review-step":"review",research:"research",workspace:"compare",review:"review",explore:"data"};
      if(aliases[id])return {id,step:aliases[id],source:id==="workspace"||id==="review"?"wise":id==="explore"?"irsa":null};
      const target=el(id),owner=target?.closest("[data-workflow-view]");
      return owner?{id,step:owner.dataset.workflowView,target,report:target.closest("[data-report-root]")}: {id:"home",step:"data",unknown:true};
    }
    function go(id){if(w.location.hash==="#"+id)navigate(true);else w.location.hash=id;}
    function navigate(focus=false){
      const request=requested();if(request.source)choose(request.source);else{const restored=sourceFromSearch(w.location.search);if(restored!==source)choose(restored);}
      pause();const c=update(),result=decide(request.step,source,c,checked);step=result.step;
      if(step!=="research")lastWork=step;
      pending=result.step!==request.step&&!c?.ready?request.id:null;
      views.forEach(v=>v.hidden=v.dataset.workflowView!==step);
      if(step==="check")checked=signature(source,c);
      el("workflow-route-status").textContent=result.reason||(request.unknown?"Liên kết không còn tồn tại. Hãy chọn dữ liệu.":"");
      if(result.step!==request.step&&!pending){const url=new URL(w.location.href);url.hash=stepIds[step];w.history.replaceState(null,"",url);}
      const report=step==="research"?request.report:null;
      el("workflow-research-index").hidden=Boolean(report);el("workflow-report-nav").hidden=!report;
      reportRoots.forEach(r=>r.hidden=r!==report);
      if(report){
        const text=reportTitles[report.dataset.reportRoot];el("workflow-report-title").textContent=text[0];el("workflow-report-kind").textContent=text[1];
        for(let node=request.target;node&&node!==el("research");node=node.parentElement)if(node.tagName==="DETAILS")node.open=true;
      }
      d.title=`${titles[step]} · NoSleepClub Sky Lab`;
      update();if(step==="compare"&&source==="wise")w.SkyApp?.redraw();
      if(report){el("workflow-report-title").focus({preventScroll:true});w.requestAnimationFrame(()=>request.target.scrollIntoView({block:"start",behavior:"instant"}));}
      else if(focus){el("step-"+(step==="research"?"research":step)+"-title").focus({preventScroll:true});w.scrollTo({top:0,behavior:"instant"});}
      else if(initial)w.scrollTo({top:0,behavior:"instant"});
      initial=false;
    }
    function changed(kind){
      const c=update();if(pending&&c?.ready){const next=pending;pending=null;go(next);return;}
      if(source==="irsa"&&["results","frame"].includes(kind)&&step==="data"&&c?.listed){go("compare-step");return;}
      if((step==="check"||step==="review")&&(!c?.ready||source==="irsa"&&!c.paired))go("home");
    }
    el("workflow-source-wise").addEventListener("click",()=>{choose("wise");go("home");});
    el("workflow-source-irsa").addEventListener("click",()=>{choose("irsa");go("home");});
    for(const[id,dest]of[["workflow-data-next","compare-step"],["workflow-compare-next","check-step"],["workflow-check-next","review-step"]])el(id).addEventListener("click",()=>go(dest));
    d.addEventListener("scene:loading",()=>changed("loading"));d.addEventListener("scene:loaded",()=>changed("loaded"));d.addEventListener("scene:failed",()=>changed("failed"));d.addEventListener("selection:changed",()=>changed("selection"));
    d.addEventListener("explorer:state",event=>{if(source==="irsa")changed(event.detail.kind);});
    d.addEventListener("click",event=>{const link=event.target.closest?.('a[href^="#"]');if(!link)return;if(link.getAttribute("href")==="#workflow-main"){event.preventDefault();el("workflow-main").focus();return;}if(link.getAttribute("href")===w.location.hash){event.preventDefault();navigate(true);}});
    w.addEventListener("hashchange",()=>navigate(true));
    source=sourceFromSearch(w.location.search);
    displaySource();navigate();
    w.SkyWorkflow={source:()=>source,step:()=>step,openCompare:()=>go("compare-step")};
  }
  return {signature,decide,sourceFromSearch,mount};
});

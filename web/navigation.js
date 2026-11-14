"use strict";
/* One current data context, two viewing steps, explicit research navigation. */
((root,factory)=>{const api=factory();if(typeof module==="object"&&module.exports)module.exports=api;if(root?.document)api.mount(root);})(typeof window!=="undefined"?window:globalThis,()=>{
  const t=(vi,en)=>typeof document!=="undefined"&&document.documentElement.lang==="en"?en:vi;
  const pageRoutes=new Set(["orbit","about","night-sky","field-guide"]);
  const stepIds={data:"home",compare:"compare-step",research:"research"};
  const titles={data:"Chọn dữ liệu",compare:"Xem ảnh",research:"Kho kiểm chứng"};
  const englishTitles={data:"Choose data",compare:"View images",research:"Validation reports"};
  const reportTitles={"signal-controls":["Tín hiệu và pha pixel","Nguồn giả"],"shape-validation":["Mẫu điểm sáng và sai số","Calibration"],"reference-presence":["Sao tham chiếu và nhận nguồn","Đối chứng"],"neighbor-intervention":["Nguồn chồng","Đối chứng"],"linked-flux":["Độ nhạy vector WISE","Ảnh thật"],validation:["Mask, phổ và diagnostics","Đã mở"],"research-history":["Thí nghiệm 0.5–0.9","Lịch sử"],"next-steps":["Kế hoạch tiếp theo","Chưa mở"]};
  function signature(source,c){
    if(!c?.ready)return null;
    return source==="wise"?JSON.stringify([source,c.analysis_sha256,c.scene_id,c.selection]):JSON.stringify([source,c.query,c.reference?.obs_id,c.current?.obs_id,c.reference?.detector,c.current?.detector,c.reference?.access_url,c.current?.access_url,c.reference_index,c.current_index]);
  }
  function frameLabel(row,headers={},release=""){
    if(!row)return "";
    const mjd=Number(headers["x-frame-mjd-obs"]),date=new Date((mjd-40587)*86400000);
    const time=headers["x-frame-time-system"]==="UTC"&&Number.isFinite(mjd)&&Number.isFinite(date.getTime())?
      date.toISOString().slice(0,19).replace("T"," ")+" UTC":Number.isFinite(row.t_min_mjd)?`MJD ${row.t_min_mjd.toFixed(5)}`:"";
    const wave=Number(headers["x-frame-center-wavelength-um"]);
    const spectral=headers["x-frame-center-spectral-source"]==="WCS-WAVE"&&Number.isFinite(wave)&&wave>0?`λ ${wave.toFixed(4)} µm · WCS-WAVE`:"";
    return [(headers["x-frame-release"]||row.release||release).toUpperCase(),`D${row.detector??"?"}`,time,spectral,row.obs_id].filter(Boolean).join(" · ");
  }
  function sourceFromSearch(search){const p=new URLSearchParams(search),chosen=p.get("flow_source");return ["wise","irsa"].includes(chosen)?chosen:p.has("sky_ra")?"irsa":"wise";}
  function canonicalStep(request){return request==="check"||request==="review"?"compare":request;}
  function decide(request,source,context){
    request=canonicalStep(request);
    if(request==="data"||request==="research")return {step:request,reason:""};
    if(source==="irsa"&&request==="compare"&&context?.listed)return {step:request,reason:""};
    if(!context?.ready)return {step:"data",reason:source==="wise"?t("Chờ bộ ảnh tải xong hoặc chọn lại dữ liệu.","Wait for the image set or choose different data."):t("Tìm và tải ảnh IRSA trước khi tiếp tục.","Find and load IRSA images to continue.")};
    return {step:"compare",reason:""};
  }
  function mount(w){
    const d=w.document,el=id=>d.getElementById(id);if(!el("workflow-main"))return;
    let source="wise",step="data",lastWork="data",initial=true;
    const views=[...d.querySelectorAll("[data-workflow-view]")],stepLinks=[...d.querySelectorAll("[data-step-link]")],reportRoots=[...d.querySelectorAll("[data-report-root]")];
    const context=()=>source==="wise"?w.SkyApp?.context():w.SkyExplorer?.context();
    const pause=()=>{w.SkyApp?.pause();w.SkyExplorer?.pause();};
    const updateTitle=()=>{d.title=`${t(titles[step],englishTitles[step])} · ${t("SPHEREx đã thấy gì?","What Did SPHEREx See?")}`;};
    function displaySource(){
      const wise=source==="wise";
      el("workflow-source-wise").setAttribute("aria-pressed",String(wise));el("workflow-source-irsa").setAttribute("aria-pressed",String(!wise));
      for(const id of["workflow-data-wise","workflow-other-scenes","workflow-compare-wise","workflow-check-wise","workflow-review-wise"])el(id).hidden=!wise;
      for(const id of["explore","workflow-compare-irsa","workflow-check-irsa","workflow-review-irsa"])el(id).hidden=wise;
      el("workflow-context-kind").textContent=wise?t("Bộ mẫu WISE","WISE sample"):t("IRSA · tự chọn","IRSA · custom");
    }
    function label(c){
      if(source==="wise")return c?.ready?`WISE 0855 · ${c.label}`:t("WISE 0855 · đang tải","WISE 0855 · loading");
      if(!c?.query)return t("IRSA · chưa chọn ảnh","IRSA · no image selected");
      const detectors=c.reference||c.current?`A ${c.reference?"D"+c.reference.detector:"—"} / B ${c.current?"D"+c.current.detector:"—"}`:t(`Truy vấn D${c.query.det}`,`Search D${c.query.det}`);
      return `SPHEREx ${c.query.release.toUpperCase()} · ${detectors} · RA ${Number(c.query.ra).toFixed(5)}° / Dec ${Number(c.query.dec).toFixed(5)}°`;
    }
    function update(){
      const c=context();
      const target=source==="wise"?(c?.selection==="target"?"WISE 0855":c?.selection||t("Chưa chọn vùng","No field selected")) :(c?.linked?"A / B":c?.paired?`${t("Ảnh","Image")} ${c.reference_index+1} / ${c.current_index+1}`:t("Chưa đủ cặp ảnh","No image pair selected"));
      el("workflow-context").textContent=step==="research"?t("Báo cáo đã công bố","Published reports"):label(c);el("workflow-compare-context").textContent=label(c);
      el("workflow-context-kind").textContent=step==="research"?t("Kho kiểm chứng","Validation reports"):source==="wise"?t("Bộ mẫu WISE","WISE sample"):t("IRSA · tự chọn","IRSA · custom");
      for(const id of["workflow-check-context","workflow-review-context"])el(id).textContent=`${label(c)} · ${target}`;
      el("workflow-data-next").disabled=!(c?.ready||source==="irsa"&&c?.listed);
      el("workflow-data-processing").textContent=!c?.ready?"—":c?.kind==="coadd"?t("Cộng ảnh theo epoch","Coadd by epoch"):t("Ảnh đơn","Single exposure");
      if(source==="wise"){for(const part of["before","after"]){const image=el("workflow-dataset-"+part);image.hidden=!c?.ready;if(c?.ready)image.src=c[part+"_image"];el("workflow-dataset-"+part+"-date").textContent=c?.ready?`${part==="before"?t("Trước","Before"):t("Sau","After")} · ${c[part+"_date"]||""}`:t("Đang tải ảnh…","Loading image…");}}
      el("workflow-data-state").textContent=source==="wise"?(c?.ready?t("Bộ ảnh đã sẵn sàng","Image set ready"):t("Chưa tải xong bộ ảnh","Image set still loading")):(c?.dirty?t("Cấu hình chưa truy vấn","Search settings changed"):c?.ready?`${c.count} ${t("quan sát · đã tải ảnh","observations · loaded image")} ${c.current_index+1}`:c?.status||t("Nhập tọa độ và tìm ảnh","Enter coordinates to find images"));
      el("workflow-frame-status").textContent=source==="irsa"?(c?.status||""):"";
      el("workflow-check-warning").textContent=source==="irsa"?t("Ảnh cùng WCS hiển thị · chưa căn chỉnh theo sao hoặc fit chuyển động.","Images share a display WCS. Stellar registration and motion fitting have not been applied."):c?.selection!=="target"?t("Vùng sai khác chưa gán danh tính · chưa có phép đo chuyển động cho vùng này.","This difference region has no assigned identity or motion measurement."):c?.kind!=="coadd"?t("Ảnh đơn · fit biên độ ở vị trí dự kiến; chưa đo chuyển động độc lập.","Single exposure: amplitude fitted at an expected position; motion has not been independently measured."):t("Phép đo thử nghiệm · sai số chưa hiệu chuẩn · chưa xác nhận chuyển động.","Exploratory measurement: uncertainties are uncalibrated and motion is unconfirmed.");
      el("workflow-selection-check").open=source==="wise"&&c?.selection!=="target";
      const motionContext=source==="wise"&&c?.kind==="coadd"&&c?.selection==="target";
      el("workflow-motion-summary").hidden=!motionContext;el("workflow-measurement-context").hidden=!motionContext;
      el("workflow-frame-a").textContent=frameLabel(c?.reference,c?.reference_metadata,c?.query?.release)||t("Chưa giữ ảnh A","No image pinned as A");
      el("workflow-frame-b").textContent=frameLabel(c?.current,c?.current_metadata,c?.query?.release)||t("Chưa chọn ảnh B","No image selected as B");
      stepLinks.forEach(a=>{const active=a.dataset.stepLink===step;a.classList.toggle("active",active);if(active)a.setAttribute("aria-current","step");else a.removeAttribute("aria-current");a.setAttribute("data-complete",String(a.dataset.stepLink==="data"&&Boolean(c?.ready)));});
      d.querySelectorAll("#main-nav a").forEach(a=>{const active=a.getAttribute("href")==="#"+stepIds[step];a.classList.toggle("active",active);if(active)a.setAttribute("aria-current","page");else a.removeAttribute("aria-current");});
      d.querySelectorAll(".workflow-library-link").forEach(a=>{if(step==="research")a.setAttribute("aria-current","page");else a.removeAttribute("aria-current");});
      el("workflow-return").href="#"+stepIds[lastWork];
      if(step==="review"){
        const image=source==="wise"?w.SkyApp?.preview():c?.preview;el("workflow-review-image").hidden=!image;if(image)el("workflow-review-image").src=image;else el("workflow-review-image").removeAttribute("src");
        el("workflow-review-caption").textContent=`${target} · ${source==="wise"?t("ảnh đang so sánh","comparison image"):t("ảnh B","image B")}`;
      }
      return c;
    }
    function choose(next){const url=new URL(w.location.href);url.searchParams.set("flow_source",next);w.history.replaceState(null,"",url);if(next===source)return;pause();source=next;displaySource();update();}
    function requested(){
      let id;try{id=decodeURIComponent(w.location.hash.slice(1));}catch{id="";}
      if(pageRoutes.has(id)||!id&&!w.location.search.includes("sky_ra=")&&!w.location.search.includes("flow_source="))return null;
      if(!id)return {id:"home",step:"data"};
      const aliases={home:"data","data-step":"data","compare-step":"compare","check-step":"compare","review-step":"compare",research:"research",workspace:"compare",review:"compare",explore:"data"};
      if(aliases[id])return {id,step:aliases[id],source:id==="workspace"||id==="review"?"wise":id==="explore"?"irsa":null};
      const target=el(id),owner=target?.closest("[data-workflow-view]");
      return owner?{id,step:canonicalStep(owner.dataset.workflowView),target,report:target.closest("[data-report-root]")}: {id:"home",step:"data",unknown:true};
    }
    function go(id,animated=false){if(w.location.hash==="#"+id)navigate(true);else if(animated&&w.SpherexTransition)w.SpherexTransition(id);else w.location.hash=id;}
    function navigate(focus=false){
      const request=requested();if(!request){pause();return;}if(request.source)choose(request.source);else{const restored=sourceFromSearch(w.location.search);if(restored!==source)choose(restored);}
      pause();const c=update(),result=decide(request.step,source,c);step=result.step;
      if(step!=="research")lastWork=step;
      views.forEach(v=>v.hidden=v.dataset.workflowView!==step);
      el("workflow-route-status").textContent=result.reason||(request.unknown?t("Liên kết không còn tồn tại. Hãy chọn dữ liệu.","This link is unavailable. Choose a dataset."):"");
      if(result.step!==request.step||["check-step","review-step","review"].includes(request.id)){const url=new URL(w.location.href);url.hash=stepIds[step];w.history.replaceState(null,"",url);}
      const report=step==="research"?request.report:null;
      el("workflow-research-index").hidden=Boolean(report);el("workflow-report-nav").hidden=!report;
      reportRoots.forEach(r=>r.hidden=r!==report);
      if(report){
        const text=reportTitles[report.dataset.reportRoot];el("workflow-report-title").textContent=text[0];el("workflow-report-kind").textContent=text[1];
        for(let node=request.target;node&&node!==el("research");node=node.parentElement)if(node.tagName==="DETAILS")node.open=true;
      }
      updateTitle();
      update();if(step==="compare"&&source==="wise")w.SkyApp?.redraw();
      if(report){el("workflow-report-title").focus({preventScroll:true});w.requestAnimationFrame(()=>request.target.scrollIntoView({block:"start",behavior:"instant"}));}
      else if(focus){el("step-"+(step==="research"?"research":step)+"-title").focus({preventScroll:true});w.scrollTo({top:0,behavior:"instant"});}
      else if(initial)w.scrollTo({top:0,behavior:"instant"});
      initial=false;
    }
    function changed(kind){
      if(!requested())return;
      const c=update();
      if(source==="irsa"&&["results","frame"].includes(kind)&&step==="data"&&c?.listed){
        const url=new URL(w.location.href);
        if((url.searchParams.has("from_field")||url.searchParams.has("from_sky"))&&url.hash==="#explore"){
          url.hash="compare-step";
          w.history.replaceState(w.history.state,"",url);
          navigate(true);
        }else go("compare-step");
        return;
      }
    }
    el("workflow-source-wise").addEventListener("click",()=>{choose("wise");go("home");});
    el("workflow-source-irsa").addEventListener("click",()=>{choose("irsa");go("home");});
    el("workflow-data-next").addEventListener("click",()=>go("compare-step",true));
    d.addEventListener("scene:loading",()=>changed("loading"));d.addEventListener("scene:loaded",()=>changed("loaded"));d.addEventListener("scene:failed",()=>changed("failed"));d.addEventListener("selection:changed",()=>changed("selection"));
    d.addEventListener("explorer:state",event=>{if(source==="irsa")changed(event.detail.kind);});
    d.addEventListener("click",event=>{if(event.defaultPrevented)return;const link=event.target.closest?.('a[href^="#"]');if(!link)return;if(link.getAttribute("href")==="#workflow-main"){event.preventDefault();el("workflow-main").focus();return;}if(link.getAttribute("href")===w.location.hash){event.preventDefault();navigate(true);}});
    w.addEventListener("hashchange",()=>navigate(true));
    d.addEventListener("spherex:language",()=>{if(requested()){update();updateTitle();}});
    source=sourceFromSearch(w.location.search);
    displaySource();navigate();
    w.SkyWorkflow={source:()=>source,step:()=>step,openCompare:()=>go("compare-step")};
  }
  return {signature,canonicalStep,decide,sourceFromSearch,frameLabel,mount};
});

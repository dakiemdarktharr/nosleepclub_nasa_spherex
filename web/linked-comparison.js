"use strict";
(() => {
  const copy = {
    comparison: ["So sánh A/B", "Compare A/B"],
    timeline: ["Chuỗi thời gian", "Observation timeline"],
    actions: ["Chế độ xem", "View mode"],
    reset: ["Đặt lại", "Reset"],
    zoomIn: ["Phóng to", "Zoom in"],
    zoomOut: ["Thu nhỏ", "Zoom out"],
    detector: ["Dải danh nghĩa", "Nominal band"],
    time: ["Lần quan sát", "Observation"],
    loading: ["Đang tải ảnh…", "Loading image…"],
    pickFrame: ["Chọn một lần quan sát.", "Choose an observation."],
    looking: ["Đang tìm lần quan sát…", "Finding observations…"],
    retrying: ["Đang thử lại IRSA…", "Retrying IRSA…"],
    retry: ["Thử lại", "Retry"],
    empty: ["Không tìm thấy ảnh ở dải này.", "No images found in this band."],
    noImage: ["Chưa có ảnh.", "No image loaded."],
    missingWave: ["Bước sóng tại tâm chưa xác định", "Center wavelength unavailable"],
    sameGrid: ["Cùng lưới WCS và thang sáng · Bắc ↑, Đông ←", "Shared WCS and display scale · north ↑, east ←"],
    panHelp: ["Kéo hoặc dùng phím mũi tên. Cả hai ảnh di chuyển cùng nhau.", "Drag or use the arrow keys. Both images move together."],
    spectral: ["Các dải hoặc bước sóng khác nhau có thể làm độ sáng thay đổi.", "Differences in wavelength can change apparent brightness."],
    clipped: ["Kết quả IRSA bị giới hạn. Thu hẹp khoảng ngày để tìm thêm ảnh.", "IRSA results were capped. Narrow the date range to find more images."],
    source: ["Nguồn FITS", "Source FITS"],
    visual: ["Ảnh SPHEREx", "SPHEREx image"],
    center: ["tại tâm", "at center"],
    display: ["Thang xám", "Grayscale"],
    masks: ["Cam là pixel đã loại, tím là vùng thiếu.", "Orange marks masked pixels. Purple marks unavailable data."]
  };
  const choose = (key) => copy[key][document.documentElement.lang.startsWith("en") ? 1 : 0];
  const clamp = (value, min, max) => Math.max(min, Math.min(value, max));

  function mount({root, bands, timeLabel, loadFrame, loadObservations, stopTimeline, onPairChange}) {
    const timelineView = root.querySelector("#explorer-display");
    const player = root.querySelector("#explorer-timeline");
    const modes = document.createElement("div");
    modes.className = "linked-switch";
    modes.setAttribute("role", "group");
    const compareButton = button("comparison"), timelineButton = button("timeline");
    const retryTimeline = root.querySelector("#explorer-retry");
    const comparison = document.createElement("div");
    comparison.id = "linked-comparison";
    comparison.className = "linked-comparison";
    const grid = document.createElement("div");
    grid.className = "linked-grid";
    const toolbar = document.createElement("div");
    toolbar.className = "linked-tool";
    const scale = document.createElement("output");
    const plus = button("zoomIn", "+"), minus = button("zoomOut", "−"), reset = button("reset");
    const align = document.createElement("span");
    align.className = "linked-align";
    const help = document.createElement("span");
    help.className = "sr-only";
    help.id = "linked-pan-help";
    toolbar.append(align, minus, scale, plus, reset, help);
    const spectral = document.createElement("p");
    spectral.className = "linked-caveat";
    spectral.hidden = true;
    const panes = ["A","B"].map(createPane);
    comparison.append(toolbar, grid, spectral);
    for (const pane of panes) grid.append(pane.element);
    modes.append(compareButton, timelineButton);
    modes.classList.add("linked-switch-host");
    root.insertBefore(modes, timelineView);
    root.insertBefore(comparison, timelineView);
    if (player) {
      modes.append(player);
      player.addEventListener("click", () => setMode("timeline", false), true);
    }
    if (retryTimeline) modes.append(retryTimeline);
    compareButton.setAttribute("aria-controls", comparison.id);
    timelineButton.setAttribute("aria-controls", timelineView.id);

    const camera = {zoom:1, x:0, y:0};
    let activeQuery, snapshot, mode = "compare", initial = false;
    const observations = new Map();
    const start = () => mode === "compare" && Boolean(activeQuery);

    function button(key, symbol) {
      const element = document.createElement("button");
      element.type = "button";
      element.dataset.linkedCopy = key;
      if (symbol) element.dataset.symbol = symbol;
      return element;
    }

    function createPane(letter) {
      const element = document.createElement("section");
      element.className = "linked-pane";
      element.dataset.pane = letter;
      const header = document.createElement("div");
      header.className = "linked-pane-header";
      const name = document.createElement("h3");
      name.id = "linked-pane-"+letter;
      name.textContent = letter;
      element.setAttribute("aria-labelledby", name.id);
      const filters = document.createElement("div");
      filters.className = "linked-filters";
      const detector = document.createElement("select"), epoch = document.createElement("select");
      detector.id = "linked-band-"+letter; epoch.id = "linked-epoch-"+letter;
      for (const [key, select] of [["time",epoch], ["detector",detector]]) {
        const label=document.createElement("label"), title=document.createElement("span");
        label.htmlFor=select.id;
        title.dataset.linkedCopy=key;
        label.append(title,select);
        filters.append(label);
      }
      bands.forEach(([lower,upper],index)=>detector.add(new Option("D"+(index+1)+" · "+lower.toFixed(2)+"–"+upper.toFixed(2)+" µm", String(index+1))));
      epoch.disabled = true;
      header.append(name, filters);
      const viewport = document.createElement("div");
      viewport.className = "linked-viewport";
      viewport.setAttribute("tabindex","0");
      viewport.setAttribute("role","group");
      viewport.setAttribute("aria-labelledby", name.id);
      viewport.setAttribute("aria-describedby", "linked-pan-help");
      const image = document.createElement("img");
      image.draggable = false;
      image.hidden = true;
      const state = document.createElement("div");
      state.className = "linked-state";
      state.hidden = true;
      const message = document.createElement("div");
      message.setAttribute("role","status");
      const track = document.createElement("div");
      track.className = "linked-progress";
      track.setAttribute("role","progressbar");
      track.setAttribute("aria-labelledby", "linked-progress-"+letter);
      track.hidden = true;
      const fill = document.createElement("span");
      track.append(fill);
      message.id = "linked-progress-"+letter;
      const retry=button("retry");
      retry.hidden = true;
      state.append(message, track, retry);
      viewport.append(image,state);
      const details = document.createElement("details");
      details.className = "linked-metadata";
      details.hidden = true;
      const summary=document.createElement("summary");
      const timestamp=document.createElement("span"), wavelength=document.createElement("span"), integrity=document.createElement("p");
      integrity.className="linked-integrity";
      summary.append(timestamp,wavelength);
      const fit = document.createElement("a");
      fit.target="_blank";
      fit.rel="noopener noreferrer";
      fit.dataset.linkedCopy="source";
      const quality=document.createElement("p");
      details.append(summary,quality,fit,integrity);
      element.append(header,viewport,details);
      const pane={letter,element,detector,epoch,viewport,image,state,message,track,fill,retry,details,timestamp,wavelength,fit,quality,integrity,
        items:[],controller:null,info:null,index:-1,status:null,engaged:false};
      detector.addEventListener("change",()=>{pane.engaged=true;setBand(pane);});
      epoch.addEventListener("change",()=>{pane.engaged=true;selectFrame(pane,Number(epoch.value));});
      retry.addEventListener("click",()=>pane.items[pane.index]?selectFrame(pane,pane.index):setBand(pane));
      return pane;
    }

    function gettext() {
      for (const el of root.querySelectorAll("[data-linked-copy]")) {
        const label=choose(el.dataset.linkedCopy);
        el.textContent=el.dataset.symbol||label;
        if (el.dataset.symbol) el.setAttribute("aria-label",label);
      }
      modes.setAttribute("aria-label",choose("actions"));
      align.textContent=choose("sameGrid");
      help.textContent=choose("panHelp");
      spectral.textContent=choose("spectral");
    }

    function viewStyle() {
      const limit = (camera.zoom - 1) / 2;
      camera.x = clamp(camera.x, -limit, limit); camera.y = clamp(camera.y, -limit, limit);
      comparison.style.setProperty("--linked-zoom", camera.zoom);
      comparison.style.setProperty("--linked-x", camera.x * 100+"%");
      comparison.style.setProperty("--linked-y", camera.y * 100+"%");
      scale.textContent = camera.zoom.toFixed(1)+"×";
      plus.disabled = camera.zoom >= 8;
      minus.disabled = camera.zoom <= 1;
    }

    function zoom(ratio, originX=0, originY=0) {
      const next = clamp(camera.zoom*ratio,1,8), change=next/camera.zoom;
      camera.x=originX+(camera.x-originX)*change;
      camera.y=originY+(camera.y-originY)*change;
      camera.zoom=next;
      viewStyle();
    }

    function clearView() {
      Object.assign(camera,{zoom:1,x:0,y:0});
      viewStyle();
    }

    plus.addEventListener("click",()=>zoom(1.35));
    minus.addEventListener("click",()=>zoom(1/1.35));
    reset.addEventListener("click",clearView);

    for (const {viewport} of panes) {
      let drag;
      viewport.addEventListener("pointerdown",event=>{
        if (!event.isPrimary||event.button!==0||event.target.closest("button")) return;
        const width=viewport.clientWidth, height=viewport.clientHeight;
        if (!width||!height) return;
        drag={id:event.pointerId,x:event.clientX,y:event.clientY,panX:camera.x,panY:camera.y,width,height};
        viewport.setPointerCapture(event.pointerId);
        viewport.classList.add("is-grabbing");
      });
      viewport.addEventListener("pointermove",event=>{
        if (!drag||drag.id!==event.pointerId) return;
        camera.x=drag.panX+(event.clientX-drag.x)/drag.width;
        camera.y=drag.panY+(event.clientY-drag.y)/drag.height;
        viewStyle();
      });
      viewport.addEventListener("lostpointercapture",()=>{drag=null;viewport.classList.remove("is-grabbing");});
      viewport.addEventListener("wheel",event=>{
        const box=viewport.getBoundingClientRect();
        if(!box.width||!box.height||event.ctrlKey||event.metaKey)return;
        event.preventDefault();
        zoom(event.deltaY<0?1.16:1/1.16,(event.clientX-box.left)/box.width-.5,(event.clientY-box.top)/box.height-.5);
      },{passive:false});
      viewport.addEventListener("keydown",event=>{
        if(event.target!==viewport)return;
        const position={ArrowLeft:["x",.06],ArrowRight:["x",-.06],ArrowUp:["y",.06],ArrowDown:["y",-.06]}[event.key];
        if(position){camera[position[0]]+=position[1];viewStyle();}
        else if(event.key==="+"||event.key==="=")zoom(1.35);
        else if(event.key==="-")zoom(1/1.35);
        else if(event.key==="Home")clearView();
        else return;
        event.preventDefault();
      });
    }

    function setMode(next, stop = true) {
      if(next===mode&&comparison.hidden===!start())return;
      if(next==="compare"&&stop)stopTimeline();
      mode=next;
      updateVisibility();
      updatePair();
      if(start()) loadInitial();
    }

    function updateVisibility() {
      modes.hidden=!activeQuery;
      comparison.hidden=!start();
      root.classList.toggle("linked-show-comparison",start());
      compareButton.setAttribute("aria-pressed",String(mode==="compare"));
      timelineButton.setAttribute("aria-pressed",String(mode==="timeline"));
    }

    compareButton.addEventListener("click",()=>setMode("compare"));
    timelineButton.addEventListener("click",()=>setMode("timeline"));

    function begin(pane) {
      pane.controller?.abort();
      pane.controller=new AbortController();
      return pane.controller.signal;
    }

    function dropImage(pane) {
      if(pane.info?.owned) URL.revokeObjectURL(pane.info.src);
      pane.info=null;
      pane.image.hidden=true;
      pane.image.removeAttribute("src");
      pane.details.hidden=true;
      pane.status=null;
      updatePair();
    }

    function updatePair() {
      const frames=panes.map(pane=>pane.info);
      const pair=mode==="compare"&&frames.every(Boolean)&&frames[0].row.access_url!==frames[1].row.access_url?frames:null;
      onPairChange(pair);
    }

    function displayState(pane, key, error="", progress=null) {
      pane.status={key,error,progress};
      const busy=["loading","looking","retrying"].includes(key);
      const message=error||(key?choose(key):"");
      pane.state.hidden=!key&&!error;
      if(pane.message.textContent!==message)pane.message.textContent=message;
      pane.retry.hidden=!error;
      pane.track.hidden=!busy;
      pane.viewport.setAttribute("aria-busy",String(busy));
      if(busy){
        if(progress===null) {
          pane.track.removeAttribute("aria-valuenow");
          pane.track.classList.add("is-indeterminate");
        } else {
          pane.track.classList.remove("is-indeterminate");
          pane.track.setAttribute("aria-valuemin","0"); pane.track.setAttribute("aria-valuemax","100");
          pane.track.setAttribute("aria-valuenow",String(Math.round(progress*100)));
          pane.fill.style.setProperty("--linked-progress",progress);
        }
      }
    }

    function frameReadout(info) {
      const h=info?.headers, center=Number(h?.["x-frame-center-wavelength-um"]);
      const bandwidth=Number(h?.["x-frame-center-bandwidth-um"]);
      const spectral=h?.["x-frame-center-spectral-source"]==="WCS-WAVE"&&center>bandwidth&&bandwidth>0;
      return {center,bandwidth,spectral};
    }

    function perhapsWarn() {
      if(panes.every(pane=>pane.info)){
        const [a,b]=panes.map(pane=>frameReadout(pane.info));
        const bandsDiffer=panes[0].detector.value!==panes[1].detector.value;
        spectral.hidden = !bandsDiffer && (!a.spectral||!b.spectral||
          Math.abs(a.center-b.center)<=.25*Math.max(a.bandwidth,b.bandwidth));
      } else spectral.hidden=true;
    }

    function renderImage(pane) {
      const {info}=pane;
      if(!info)return;
      const h=info.headers;
      const utc=h["x-frame-time-system"]==="UTC"&&h["x-frame-mjd-obs"];
      const time=utc?timeLabel(Number(h["x-frame-mjd-obs"]),"UTC"):timeLabel(info.row.t_min_mjd);
      const {center,bandwidth,spectral:actual}=frameReadout(info);
      pane.timestamp.textContent = time;
      pane.wavelength.textContent = actual ? center.toFixed(4)+" µm · WCS-WAVE" : choose("missingWave");
      pane.image.alt=choose("visual")+" "+pane.letter+" · "+time+" · D"+info.row.detector;
      const contrast=[Number(h["x-frame-contrast-low"]),Number(h["x-frame-contrast-high"])];
      pane.quality.textContent=[(h["x-frame-release"]||info.row.release||"").toUpperCase()+" / D"+info.row.detector+" / "+info.row.obs_id,
        actual?"λ "+center.toFixed(4)+" µm "+choose("center")+" · Δλ "+bandwidth.toFixed(4)+" µm":"",
        contrast.every(Number.isFinite)?choose("display")+" "+contrast.map(value=>value.toFixed(4)).join("–")+" MJy/sr":""].filter(Boolean).join(" · ");
      pane.quality.textContent+=". "+choose("masks");
      pane.fit.href=h["x-frame-cutout-url"];
      pane.fit.hidden=!h["x-frame-cutout-url"];
      pane.integrity.textContent=h["x-frame-cutout-sha256"]?"SHA-256 · "+h["x-frame-cutout-sha256"]:"";
      pane.details.hidden=false;
    }

    async function selectFrame(pane,index) {
      const row=pane.items[index];
      if(!row)return;
      const signal=begin(pane);
      pane.index=index;
      pane.epoch.value=String(index);
      dropImage(pane);
      perhapsWarn();
      displayState(pane,"loading");
      try {
        const info=await loadFrame(row,signal,(value,retry)=>{if(!signal.aborted)displayState(pane,retry?"retrying":"loading","",value);});
        if(signal.aborted){if(info.owned)URL.revokeObjectURL(info.src);return;}
        pane.info={...info, provenance:observations.get(Number(pane.detector.value))?.provenance};
        pane.image.src=info.src;
        pane.image.hidden=false;
        renderImage(pane);
        displayState(pane);
        perhapsWarn();
        updatePair();
      } catch (error) {
        if(!signal.aborted&&error.name!=="AbortError")displayState(pane,null,error.message);
      }
    }

    function listEpochs(pane,items,clipped) {
      pane.items=items;
      pane.epoch.replaceChildren();
      pane.epoch.disabled=!items.length;
      if (!items.length) pane.epoch.add(new Option(choose("noImage"),""));
      items.forEach((row,index)=>pane.epoch.add(new Option(timeLabel(row.t_min_mjd)+" · "+row.obs_id, String(index))));
      pane.epoch.title=clipped?choose("clipped"):"";
    }

    const usable = (rows) => rows.filter(row=>row.access_url&&row.obs_id)
      .sort((a,b)=>(a.t_min_mjd??Infinity)-(b.t_min_mjd??Infinity));

    async function setBand(pane) {
      const band=Number(pane.detector.value);
      const signal=begin(pane);
      dropImage(pane);
      listEpochs(pane,[]);
      pane.index=-1;
      perhapsWarn();
      displayState(pane,"looking");
      try {
        let result=observations.get(band);
        if(!result) {
          const raw=await loadObservations(band,signal);
          if(signal.aborted)return;
          result={items:usable(raw.rows),truncated:raw.truncated,provenance:raw.provenance};
          observations.set(band,result);
        }
        listEpochs(pane,result.items,result.truncated);
        if (!result.items.length){displayState(pane,"empty");return;}
        selectFrame(pane,pane.letter==="A"?0:result.items.length-1);
      } catch(error) {
        if(!signal.aborted&&error.name!=="AbortError")displayState(pane,null,error.message);
      }
    }

    function loadInitial() {
      if(initial||!start()||!snapshot.images.size)return;
      const examples=observations.get(activeQuery.det)?.items;
      if(!examples?.length)return;
      const loaded=examples.map((row,index)=>({row,index})).filter(({row})=>{
        const at=snapshot.rows.indexOf(row);
        return snapshot.images.has(at);
      }).map(item=>item.index);
      if(!loaded.length)return;
      if(!panes[0].engaged&&panes[0].index<0)selectFrame(panes[0],loaded[0]);
      if(snapshot.busy)return;
      initial=true;
      const latest=loaded.length>1?loaded.at(-1):examples.length-1;
      if(!panes[1].engaged){
        if(latest!==loaded[0])selectFrame(panes[1],latest);
        else displayState(panes[1],"noImage");
      }
    }

    function update(next) {
      snapshot=next;
      const query = !next.dirty&&next.rows.some(row=>row.access_url)?next.query:null;
      if(query!==activeQuery){
        activeQuery=query;
        initial=false;
        observations.clear();
        clearView();
        for(const pane of panes){
          pane.controller?.abort();
          dropImage(pane);
          pane.index=-1;
          pane.engaged=false;
          displayState(pane,"noImage");
        }
        spectral.hidden=true;
        if(query){
          const items=usable(next.rows);
          observations.set(query.det,{items,truncated:next.truncated,provenance:next.provenance});
          for(const pane of panes){
            pane.detector.value=String(query.det);
            listEpochs(pane,items,next.truncated);
            pane.epoch.selectedIndex=-1;
            displayState(pane,"pickFrame");
          }
          mode="compare";
        }
      }
      updateVisibility();
      loadInitial();
      if(start()&&!initial){
        for(const pane of panes){
          if(!pane.engaged&&!pane.info&&pane.index<0)displayState(pane,next.busy||next.loading?"loading":"pickFrame");
        }
      }
    }

    document.addEventListener("spherex:language",()=>{
      gettext();
      for(const pane of panes){
        renderImage(pane);
        if(pane.status)displayState(pane,pane.status.key,pane.status.error,pane.status.progress);
      }
    });
    window.addEventListener("hashchange",()=>{
      if(location.hash==="#compare-step")return;
      for(const pane of panes)pane.controller?.abort();
      if(panes.some(pane=>!pane.info))initial=false;
    });
    gettext();
    viewStyle();
    updateVisibility();
    return {update};
  }

  window.SkyLinkedComparison={mount};
})();

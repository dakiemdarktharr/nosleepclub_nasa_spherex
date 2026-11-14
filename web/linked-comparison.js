"use strict";
(() => {
  const copy = {
    comparison: ["So sánh A/B", "Compare A/B"],
    timeline: ["Chuỗi thời gian", "Observation timeline"],
    actions: ["Chế độ xem", "View mode"],
    reset: ["Đặt lại", "Reset"],
    overview: ["Toàn khung", "Overview"],
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
    unavailable: ["Lần quan sát trong liên kết không còn trong kết quả. Chọn một lần quan sát khác.", "The linked observation is not in these results. Choose another observation."],
    missingWave: ["Bước sóng tại tâm chưa xác định", "Center wavelength unavailable"],
    sameGrid: ["Cùng lưới WCS và thang sáng · Bắc ↑, Đông ←", "Shared WCS and display scale · north ↑, east ←"],
    panHelp: ["Kéo ảnh hoặc kéo ô xanh trên bản đồ nhỏ để đổi vùng xem.", "Drag the image or the blue box in the overview to move around."],
    keyboardHelp: ["Dùng phím mũi tên để di chuyển, +/− để đổi độ phóng đại và Home để đặt lại.", "Use arrow keys to pan, +/− to zoom, and Home to reset."],
    overviewHelp: ["Chọn một vị trí để phóng vào, hoặc kéo ô xanh để di chuyển khung nhìn.", "Select a point to zoom in, or drag the blue box to move the view."],
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

  function mount({root, bands, timeLabel, loadFrame, loadObservations, stopTimeline, onPairChange, initialMode = "compare", onModeChange, onViewStateChange}) {
    const timelineView = root.querySelector("#explorer-display");
    const timelineViewport = timelineView.querySelector(".explorer-image-wrap");
    const timelineImage = timelineViewport.querySelector("img");
    timelineViewport.classList.add("linked-viewport");
    timelineViewport.tabIndex = 0;
    timelineViewport.setAttribute("role", "group");
    timelineViewport.setAttribute("aria-describedby", "linked-pan-help");
    timelineViewport.setAttribute("aria-labelledby","explorer-frame-label");
    timelineImage.draggable = false;
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
    const instructions = document.createElement("span");
    instructions.className = "linked-instructions";
    const toolbarCopy = document.createElement("div");
    toolbarCopy.className = "linked-tool-copy";
    toolbarCopy.append(align, instructions, help);
    const zoomControls = document.createElement("div");
    zoomControls.className = "linked-zoom";
    zoomControls.append(minus, scale, plus, reset);
    const overview = document.createElement("button");
    overview.type = "button";
    overview.className = "linked-overview";
    overview.hidden = true;
    const overviewImage = document.createElement("img");
    overviewImage.alt = "";
    overviewImage.draggable = false;
    const overviewBox = document.createElement("span");
    overviewBox.className = "linked-overview-box";
    overviewBox.setAttribute("aria-hidden", "true");
    overview.append(overviewImage, overviewBox);
    toolbar.append(toolbarCopy, zoomControls, overview);
    const spectral = document.createElement("p");
    spectral.className = "linked-caveat";
    spectral.hidden = true;
    const panes = ["A","B"].map(createPane);
    comparison.append(grid, spectral);
    for (const pane of panes) grid.append(pane.element);
    modes.append(compareButton, timelineButton);
    modes.classList.add("linked-switch-host");
    root.insertBefore(modes, timelineView);
    root.insertBefore(toolbar, timelineView);
    root.insertBefore(comparison, timelineView);
    if (player) {
      modes.append(player);
      player.addEventListener("click", () => setMode("timeline", false), true);
    }
    if (retryTimeline) modes.append(retryTimeline);
    compareButton.setAttribute("aria-controls", comparison.id);
    timelineButton.setAttribute("aria-controls", timelineView.id);

    const camera = {zoom:1, x:0, y:0};
    let activeQuery, snapshot, mode = initialMode, initial = false;
    const observations = new Map();
    const start = () => mode === "compare" && Boolean(activeQuery);
    function rememberView() {
      if(!activeQuery||!initial)return;
      const state={camera:{...camera}};
      for(const pane of panes){
        const row=pane.items[pane.index];
        if(row)state[pane.letter.toLowerCase()]={obs:row.obs_id,det:row.detector};
        else if(pane.requested)state[pane.letter.toLowerCase()]=pane.requested;
      }
      onViewStateChange?.(state);
    }

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
        items:[],controller:null,info:null,index:-1,status:null,engaged:false,requested:null};
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
      instructions.textContent=choose("panHelp");
      help.textContent=choose("keyboardHelp");
      overview.setAttribute("aria-label",choose("overview")+". "+choose("overviewHelp")+" "+choose("keyboardHelp"));
      overview.title=choose("overviewHelp");
      spectral.textContent=choose("spectral");
    }

    function viewStyle() {
      // Keep the reference center in view and allow limited overscan at fit.
      const limit = Math.max(.25, (camera.zoom - 1) / 2);
      camera.x = clamp(camera.x, -limit, limit);
      camera.y = clamp(camera.y, -limit, limit);
      root.style.setProperty("--linked-zoom", camera.zoom);
      root.style.setProperty("--linked-x", camera.x * 100+"%");
      root.style.setProperty("--linked-y", camera.y * 100+"%");
      const halfView = .5 / camera.zoom;
      for (const [axis, startEdge, endEdge] of [["x","left","right"], ["y","top","bottom"]]) {
        const center = .5 - camera[axis] / camera.zoom;
        overviewBox.style[startEdge] = clamp(center - halfView, 0, 1) * 100 + "%";
        overviewBox.style[endEdge] = (1 - clamp(center + halfView, 0, 1)) * 100 + "%";
      }
      scale.textContent = new Intl.NumberFormat(document.documentElement.lang, {maximumFractionDigits:1}).format(camera.zoom)+"×";
      plus.disabled = camera.zoom >= 8;
      minus.disabled = camera.zoom <= 1;
      rememberView();
    }

    function updateOverview() {
      const timelineSource = snapshot?.images.values().next().value?.src;
      const source = (mode === "compare" ? panes.find(pane => pane.info)?.info.src : null) || timelineSource;
      overview.hidden = !source;
      if (source && overviewImage.getAttribute("src") !== source) overviewImage.src = source;
      if (!source) overviewImage.removeAttribute("src");
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

    function viewKeys(event) {
      if (event.target !== event.currentTarget) return;
      const position = {ArrowLeft:["x",.06], ArrowRight:["x",-.06], ArrowUp:["y",.06], ArrowDown:["y",-.06]}[event.key];
      if (position) {
        camera[position[0]] += position[1];
        viewStyle();
      } else if (event.key === "+" || event.key === "=") zoom(1.35);
      else if (event.key === "-") zoom(1/1.35);
      else if (event.key === "Home") clearView();
      else return;
      event.preventDefault();
    }

    for (const viewport of [...panes.map(pane => pane.viewport), timelineViewport]) {
      let drag;
      viewport.addEventListener("pointerdown",event=>{
        if (!event.isPrimary||event.button!==0||event.target.closest("button")||viewport.querySelector("img").hidden) return;
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
      viewport.addEventListener("lostpointercapture",()=>{ drag=null; viewport.classList.remove("is-grabbing"); });
      viewport.addEventListener("wheel",event=>{
        const box=viewport.getBoundingClientRect();
        if(!box.width||!box.height||event.ctrlKey||event.metaKey||event.deltaY===0||viewport.querySelector("img").hidden)return;
        event.preventDefault();
        zoom(event.deltaY<0?1.16:1/1.16,(event.clientX-box.left)/box.width-.5,(event.clientY-box.top)/box.height-.5);
      },{passive:false});
      viewport.addEventListener("keydown", viewKeys);
    }

    function overviewPoint(event) {
      const box = overview.getBoundingClientRect();
      return {x:(event.clientX - box.left) / box.width - .5, y:(event.clientY - box.top) / box.height - .5};
    }

    function focusOverview(point) {
      camera.zoom = Math.max(camera.zoom, 2);
      camera.x = -point.x * camera.zoom;
      camera.y = -point.y * camera.zoom;
      viewStyle();
    }

    let overviewDrag;
    overview.addEventListener("pointerdown", event => {
      if (!event.isPrimary || event.button !== 0) return;
      const point = overviewPoint(event);
      overviewDrag = {id:event.pointerId, point, panX:camera.x, panY:camera.y, moved:false};
      overview.setPointerCapture(event.pointerId);
    });
    overview.addEventListener("pointermove", event => {
      if (overviewDrag?.id !== event.pointerId) return;
      const point = overviewPoint(event);
      const dx = point.x - overviewDrag.point.x, dy = point.y - overviewDrag.point.y;
      if (!overviewDrag.moved && Math.hypot(dx, dy) < .025) return;
      overviewDrag.moved = true;
      camera.x = overviewDrag.panX - dx * camera.zoom;
      camera.y = overviewDrag.panY - dy * camera.zoom;
      viewStyle();
    });
    overview.addEventListener("pointerup", event => {
      if (overviewDrag?.id === event.pointerId && !overviewDrag.moved) focusOverview(overviewPoint(event));
    });
    overview.addEventListener("lostpointercapture", () => { overviewDrag = null; });
    overview.addEventListener("click", event => {
      if (event.detail === 0) focusOverview({x:-camera.x/camera.zoom, y:-camera.y/camera.zoom});
    });
    overview.addEventListener("keydown", viewKeys);

    function setMode(next, stop = true) {
      if(next===mode&&comparison.hidden===!start())return;
      if(next==="compare"&&stop)stopTimeline();
      mode=next;
      onModeChange?.(mode);
      updateVisibility();
      updatePair();
      if(start()) loadInitial();
    }

    function updateVisibility() {
      modes.hidden=!activeQuery;
      toolbar.hidden=!activeQuery;
      comparison.hidden=!start();
      root.classList.toggle("linked-show-comparison",start());
      root.classList.toggle("linked-show-timeline",Boolean(activeQuery)&&mode==="timeline");
      compareButton.setAttribute("aria-pressed",String(mode==="compare"));
      timelineButton.setAttribute("aria-pressed",String(mode==="timeline"));
      updateOverview();
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
      onPairChange(pair,frames);
      updateOverview();
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
      pane.requested={obs:row.obs_id,det:row.detector};
      rememberView();
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

    async function setBand(pane, observation) {
      const band=Number(pane.detector.value);
      const signal=begin(pane);
      dropImage(pane);
      listEpochs(pane,[]);
      pane.index=-1;
      pane.requested=observation?{obs:observation,det:band}:null;
      rememberView();
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
        const index=observation?result.items.findIndex(row=>row.obs_id===observation):pane.letter==="A"?0:result.items.length-1;
        if(index<0){pane.epoch.selectedIndex=-1;displayState(pane,"unavailable");return;}
        selectFrame(pane,index);
      } catch(error) {
        if(!signal.aborted&&error.name!=="AbortError")displayState(pane,null,error.message);
      }
    }

    function loadInitial() {
      if(initial||!start())return;
      const examples=observations.get(activeQuery.det)?.items;
      if(!examples?.length)return;
      const loaded=examples.map((row,index)=>({row,index})).filter(({row})=>{
        const at=snapshot.rows.indexOf(row);
        return snapshot.images.has(at);
      }).map(item=>item.index);
      if(snapshot.busy)return;
      initial=true;
      const state=activeQuery.viewState||{};
      if(state.camera)Object.assign(camera,state.camera);
      for(const pane of panes){
        if(pane.engaged||pane.info)continue;
        const restored=state[pane.letter.toLowerCase()];
        if(restored){
          pane.detector.value=String(restored.det);
          void setBand(pane,restored.obs);
        } else {
          const first=loaded[0]??0, last=loaded.length>1?loaded.at(-1):examples.length-1;
          const index=pane.letter==="A"?first:last;
          if(pane.letter==="B"&&index===first)displayState(pane,"noImage");
          else void selectFrame(pane,index);
        }
      }
      viewStyle();
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
          pane.requested=null;
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
          mode=query.view || initialMode;
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
      viewStyle();
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

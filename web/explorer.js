"use strict";
// Discovery and display use public IRSA observations; no motion fit is performed.
(() => {
  const el = id => document.getElementById(id), BANDS = [[.75,1.09],[1.10,1.62],[1.63,2.41],[2.42,3.82],[3.83,4.41],[4.42,5.00]],
    OBSERVATION_SEARCH_RADIUS_DEG=.001, SEQUENCE_SIZE=5;
  const english = () => document.documentElement?.lang?.startsWith("en");
  const t = (vi, en) => english() ? en : vi;
  const presets = {
    wise0855:[133.7601213914074,-7.242127941212259], barnard:[269.44626688537255,4.768222216475269],
    epsilon:[331.04583333,-56.78333333], rwaur:[76.95652603458332,30.401438173888888], rdra:[248.16761083294998,66.75497941722]
  };
  let rows=[], query=null, provenance=null, current=-1, displayed=-1, reference=-1, generation=0, request=null, timer=null, range=null, maskPolicy=null, dirty=true;
  let frameQueue=Promise.resolve(),pendingFrames=new Map();
  let playback=null, truncated=false, sequenceRun=null, retrySequence=null;
  let preparedSequence=null, timelineState=null, selectedSequence=null;
  const publicRoutes = new Set(["#orbit", "#about", "#night-sky"]);
  const searchRoutes = new Set(["#home", "#explore", "#compare-step", "#data-step", "#check-step", "#review-step"]);
  const workspaceActive = () => !publicRoutes.has(location.hash) &&
    (Boolean(location.hash) || /[?&](?:sky_ra|flow_source)=/.test(location.search));
  const searchActive = () => searchRoutes.has(location.hash)||(!location.hash&&workspaceActive());
  const timeline = el("explorer-timeline");
  const timelinePlay = el("explorer-timeline-play"), newSequence = el("explorer-new-sequence");
  const incoming = new URLSearchParams(location.search);
  let requestedView = incoming.get("sky_view") === "compare" ? "compare" : "timeline";
  const images=new Map();
  let comparison, linkedPair=null, linkedFrames=[];
  let restoreView=true;
  function initialViewState() {
    const state={};
    for(const letter of ["a","b"]){
      const obs=incoming.get(`sky_${letter}_obs`),det=Number(incoming.get(`sky_${letter}_det`));
      if(obs&&/^[A-Za-z0-9_-]{1,100}$/.test(obs)&&Number.isInteger(det)&&det>=1&&det<=6)state[letter]={obs,det};
    }
    const zoom=Number(incoming.get("sky_zoom")),x=Number(incoming.get("sky_x")),y=Number(incoming.get("sky_y"));
    if(zoom>=1&&zoom<=2&&Number.isFinite(x+y)&&Math.abs(x)<=4&&Math.abs(y)<=4)state.camera={zoom,x,y};
    return state;
  }
  function shareView(state) {
    if(!query||dirty)return;
    query.viewState=state;
    const share=new URL(location.href);
    for(const letter of ["a","b"]){
      for(const key of ["obs","det"]){
        const name=`sky_${letter}_${key}`;
        if(state[letter])share.searchParams.set(name,String(state[letter][key]));else share.searchParams.delete(name);
      }
    }
    for(const key of ["zoom","x","y"])share.searchParams.set(`sky_${key}`,String(Number(state.camera[key].toFixed(4))));
    history.replaceState(history.state,"",share);
  }
  const noteDrafts=new Map();let noteKey=null;
  const draftMessage = () => t("Nháp trong tab · chưa gửi lên máy chủ","Draft stored in this tab only");
  function saveNote(){if(noteKey){const note=el("explorer-note").value;noteDrafts.set(noteKey,note);const kept=window.SkyDrafts?.set("irsa",noteKey,{note});el("explorer-note-state").textContent=kept?draftMessage():t("Nháp chưa lưu · xuất JSON trước khi tải lại","Unsaved draft · export JSON before reloading");}}
  function restoreNote(){const c=context();noteKey=c.paired?JSON.stringify([query.p.toString(),c.reference.access_url,c.current.access_url]):null;el("explorer-note").value=noteKey?noteDrafts.get(noteKey)??window.SkyDrafts?.get("irsa",noteKey)?.note??"":"";el("explorer-note-state").textContent=el("explorer-note").value?draftMessage():t("Chưa có ghi chú","No note yet");}
  function coordinate(raw, ra) {
    const text=raw.trim().replace(/−/g,"-");if(!text)throw new Error(t("Nhập cả RA và Dec.","Enter both RA and Dec."));
    if(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text)) {
      const n=Number(text);if(!Number.isFinite(n)||(ra?(n<0||n>=360):(n< -90||n>90)))throw new Error(ra?t("RA phải từ 0 đến dưới 360 độ.","RA must be at least 0 and below 360 degrees."):t("Dec phải từ −90 đến +90 độ.","Dec must be between −90 and +90 degrees."));return n;
    }
    const parts=text.replace(/[hHdD°mM′'sS″"]/g," ").trim().split(/[:\s]+/);
    if(parts.length!==3||!/^[-+]?\d+$/.test(parts[0])||!parts.slice(1).every(v=>/^\d+(?:\.\d*)?$/.test(v)))throw new Error(t("Dùng độ thập phân hoặc ba phần giờ/phút/giây (RA), độ/phút/giây (Dec).","Use decimal degrees or three parts for hours/minutes/seconds (RA), and degrees/minutes/seconds (Dec)."));
    const [a,b,c]=parts.map(Number), negative=text.startsWith("-"), value=(Math.abs(a)+b/60+c/3600)*(negative?-1:1)*(ra&&!/[dD°]/.test(text)?15:1);
    if(b>=60||c>=60||!Number.isFinite(value)||(ra?(negative||value>=360):Math.abs(value)>90))throw new Error(t("Tọa độ ngoài phạm vi hoặc phút/giây không hợp lệ.","Coordinates, minutes or seconds are out of range."));
    return value;
  }
  function displayMjd(value, system) {
    if(!Number.isFinite(value))return t("Không có ngày quan sát","Observation date unavailable");
    const date=new Date((value-40587)*86400000);
    return system==="UTC"&&Number.isFinite(date.getTime())?date.toISOString().slice(0,19).replace("T"," ")+" UTC":`MJD ${value.toFixed(5)}`;
  }
  function stop() {
    if(timer){
      clearInterval(timer);
      timer=null;
      playback=null;
      if(images.has(current))draw(images.get(current),current);
      renderList();
    }
    el("explorer-play").textContent=t("Nhấp nháy A / B","Blink A / B");
    timelineControls();
  }
  function context(){
    const ready=Boolean(!dirty&&current>=0&&images.has(current)&&(timer||displayed===current&&!el("explorer-image").hidden));
    const common={dirty,listed:!dirty&&rows.length>0,query:query?{ra:query.ra,dec:query.dec,release:query.release,det:query.det,fov:query.fov,from:query.from,to:query.to}:null,
      count:rows.length,status:el("explorer-status").textContent};
    if(comparison&&requestedView==="compare"&&!dirty)return {...common,ready:Boolean(linkedPair),paired:Boolean(linkedPair),linked:true,
      current:linkedFrames[1]?.row,reference:linkedFrames[0]?.row,
      current_metadata:linkedFrames[1]?.headers,reference_metadata:linkedFrames[0]?.headers,
      reference_index:-1,current_index:-1,preview:linkedFrames[1]?.src};
    return {...common,ready,paired:ready&&reference>=0&&reference!==current&&images.has(reference),
      current:ready?rows[current]:null,reference:reference>=0?rows[reference]:null,
      current_index:current,reference_index:reference,preview:ready?images.get(current).src:null,
      current_metadata:images.get(current)?.headers,reference_metadata:images.get(reference)?.headers};
  }
  function selectLinkedPair(pair,frames=[]){
    if(pair?.[0]===linkedPair?.[0]&&pair?.[1]===linkedPair?.[1]&&frames[0]===linkedFrames[0]&&frames[1]===linkedFrames[1])return;
    saveNote();
    linkedPair=pair;
    linkedFrames=frames;
    restoreNote();
    if(pair)fillFrameMetadata(pair[1]);
    else if(images.has(current))fillFrameMetadata(images.get(current));
    if(pair)el("explorer-status").textContent=frameStatus();
    el("explorer-export").disabled=!context().paired;
    notify("pair");
  }
  function notify(kind){
    if(typeof CustomEvent==="function")document.dispatchEvent(new CustomEvent("explorer:state",{detail:{kind,context:context()}}));
    comparison?.update({query, rows, images, dirty, truncated, provenance, loading:pendingFrames.size>0, busy:Boolean(sequenceRun)});
  }
  function dateSummary(){const a=el("explorer-from").value,b=el("explorer-to").value,fmt=v=>english()?v:v.split("-").reverse().join("/");el("explorer-date-summary").textContent=a&&b?`${t("Khoảng ngày","Date range")} · ${fmt(a)}–${fmt(b)}`:a||b?t("Khoảng ngày · chưa đủ hai ngày","Date range · enter both dates"):t("Khoảng ngày · tùy chọn","Date range · optional");}
  function setStatus(text,error=false) {el("explorer-status").textContent=text;el("explorer-status").classList.toggle("is-error",error);notify("status");}
  function markDirty(){saveNote();dateSummary();dirty=true;sequenceRun=retrySequence=null;preparedSequence=timelineState=selectedSequence=null;stop();noteKey=null;el("explorer-note").value="";for(const id of["explorer-pin","explorer-play","explorer-export"])el(id).disabled=true;notify("dirty");}
  function apiError(response,code) {
    if(response.status===429){
      const retry=response.headers?.get("Retry-After");
      return retry&&/^\d{1,5}$/.test(retry)?t(`Đã đạt giới hạn tạm thời. Thử lại sau ${retry} giây.`,`Rate limit reached. Try again in ${retry} seconds.`):t("Đã đạt giới hạn tạm thời. Hãy thử lại sau.","Rate limit reached. Try again later.");
    }
    if(code==="release_retired")return t("QR2 đã ngừng tìm kiếm. Chọn DR1 để truy vấn bản xử lý lại.","QR2 is no longer searchable. Select DR1 for reprocessed observations.");
    if(code==="upstream_timeout")return t("IRSA phản hồi quá chậm","IRSA took too long to respond");
    if(response.status===503)return t("Dịch vụ tạm chưa sẵn sàng","Service temporarily unavailable");
    if(response.status===502)return t("Chưa đọc được dữ liệu nguồn từ IRSA","Could not read source data from IRSA");
    return t(`Máy chủ chưa xử lý được yêu cầu (HTTP ${response.status})`,`The server could not complete the request (HTTP ${response.status})`);
  }
  async function fetchObservations(url,signal) {
    for(let attempt=0;attempt<2;attempt++){
      if(signal.aborted)throw new DOMException(t("Đã đổi vùng trời","Sky region changed"),"AbortError");
      const response=await fetch(url,{signal});
      const retryAfterHeader=response.headers?.get?.("Retry-After");
      const retryAfter=retryAfterHeader&&/^\d{1,3}$/.test(retryAfterHeader)?Number(retryAfterHeader):NaN;
      const retryable=response.status===502||response.status===504
        ||(response.status===503&&Number.isInteger(retryAfter)&&retryAfter>0&&retryAfter<=120);
      if(attempt===0&&retryable){
        const delay=Number.isInteger(retryAfter)&&retryAfter>0&&retryAfter<=120?retryAfter:.9;
        setStatus(t(`IRSA đang chậm hoặc tạm lỗi. Thử lại sau ${delay} giây…`,`IRSA is slow or temporarily unavailable. Retrying in ${delay} seconds…`));
        await waitForRetry(delay,signal);
        if(signal.aborted)throw new DOMException(t("Đã đổi vùng trời","Sky region changed"),"AbortError");
        setStatus(t("IRSA đang chậm hoặc tạm lỗi. Đang thử lại lần 2/2…","IRSA is slow or temporarily unavailable. Retrying (2/2)…"));
        continue;
      }
      return response;
    }
  }
  function clearImages() {for(const item of images.values())URL.revokeObjectURL(item.src);images.clear();}
  function observationTime(info) {
    const h=info?.headers, mjd=Number(h?.["x-frame-mjd-obs"]);
    return h?.["x-frame-time-system"]==="UTC"&&Number.isFinite(mjd)&&mjd>0?{mjd}:null;
  }
  function spectralSample(info) {
    const h=info?.headers,time=observationTime(info);
    if(!time||h?.["x-frame-center-spectral-source"]!=="WCS-WAVE")return null;
    const center=Number(h["x-frame-center-wavelength-um"]), width=Number(h["x-frame-center-bandwidth-um"]);
    if(!Number.isFinite(center)||!Number.isFinite(width)||!(center>width&&width>0))return null;
    return {...time,low:center-width/2,high:center+width/2,width};
  }
  function timelineBandCaveat(indices=null) {
    const selected=indices||[...images.keys()],samples=selected.map(index=>spectralSample(images.get(index)));
    if(samples.some(sample=>!sample))return t(" Bước sóng tại tọa độ này chưa được đo đầy đủ ở mọi ảnh; khác biệt độ sáng không chỉ phản ánh thay đổi theo thời gian.","The wavelength at this coordinate is not available for every frame; brightness differences may not be caused by time alone.");
    if(!samples.length)return "";
    const low=Math.max(...samples.map(sample=>sample.low)),high=Math.min(...samples.map(sample=>sample.high));
    const widest=Math.max(...samples.map(sample=>sample.width));
    return high-low<.75*widest
      ?t(" Bước sóng đo tại cùng tọa độ thay đổi giữa các ảnh; khác biệt độ sáng cũng có thể do phổ, không chỉ do thời gian.","The sampled wavelength changes at this sky position; brightness differences can reflect spectral response as well as time.")
      :"";
  }
  function gridSignature(info) {
    const headers=info?.headers||{};
    const fields=["x-frame-grid-ra-deg","x-frame-grid-dec-deg","x-frame-grid-scale-arcsec","x-frame-grid-size-px","x-frame-grid-fov-deg"];
    const values=fields.map(key=>Number(headers[key]));
    return values.every(Number.isFinite)?values.join("/"):null;
  }
  function timelineUnavailableReason(indices) {
    const loaded=indices.map(index=>images.get(index)).filter(Boolean);
    if(loaded.some(info=>Number(info.headers?.["x-frame-valid-pixels"])<=0))
      return t("Ít nhất một ảnh không có pixel dữ liệu dùng được.","At least one image has no usable pixels.");
    if(loaded.some(info=>!observationTime(info)))
      return t("Ít nhất một FITS không cung cấp MJD UTC hợp lệ.","At least one FITS file lacks a valid UTC MJD.");
    return t("Các ảnh không cùng release, detector, lưới tọa độ, mask, thời điểm hoặc thang sáng.","The frames do not share a release, detector, sky grid, mask, observation time or display scale.");
  }
  function timelineFrames(indices=null) {
    const requested=indices||preparedSequence?.indices||null;
    if(dirty||!range||maskPolicy==="undeclared"||!query)return [];
    const source=requested?requested.map(index=>[index,images.get(index)]):[...images];
    const entries=source.map(([index,info])=>({index,info,time:observationTime(info),band:spectralSample(info),grid:gridSignature(info)}))
      .filter(({index,info,time,grid})=>{
        const h=info?.headers||{}, low=Number(h["x-frame-contrast-low"]), high=Number(h["x-frame-contrast-high"]);
        return Boolean(info?.decoded&&time&&grid&&Number(h["x-frame-valid-pixels"])>0
          &&(h["x-frame-release"]||info.row.release||query.release).toLowerCase()===query.release
          &&Number(h["x-frame-detector"])===query.det&&h["x-frame-obs-id"]===info.row.obs_id
          &&info.row.detector===query.det&&info.row.obs_id&&h["x-frame-mask-policy"]===maskPolicy
          &&Number.isFinite(low)&&Number.isFinite(high)&&Math.abs(low-range[0])<1e-7&&Math.abs(high-range[1])<1e-7);
      })
      .sort((a,b)=>a.time.mjd-b.time.mjd||String(a.info.row.obs_id).localeCompare(String(b.info.row.obs_id)));
    const unique=[],seenIds=new Set();
    for(const entry of entries){
      const id=entry.info.row.obs_id;
      if(seenIds.has(id))continue;
      seenIds.add(id);unique.push(entry);
    }
    const referenceGrid=unique.find(entry=>entry.index===current)?.grid||unique[0]?.grid;
    const sameGrid=unique.filter(entry=>entry.grid===referenceGrid);
    if(sameGrid.length!==unique.length)return sameGrid.map(entry=>entry.index);
    return unique.map(entry=>entry.index);
  }
  function timelineControls() {
    if(!timeline)return;
    const candidates=sequenceCandidates();
    let selection=selectedSequence;
    if(!selection&&!dirty&&candidates.length>=SEQUENCE_SIZE)selection=selectedSequence=selectRandomSequence();
    const indices=preparedSequence?.indices||selection?.indices||[];
    const frames=timelineFrames(indices),playing=playback==="timeline",loading=Boolean(sequenceRun);
    const complete=indices.length===SEQUENCE_SIZE&&frames.length===SEQUENCE_SIZE&&indices.every(index=>images.has(index));
    const paused=Boolean(timelineState&&!playing&&timelineState.generation===generation);
    const rangeLabel=selection?.indices.length===SEQUENCE_SIZE
      ?`${displayMjd(Number(rows[selection.indices[0]].t_min_mjd),"UTC")} — ${displayMjd(Number(rows[selection.indices.at(-1)].t_min_mjd),"UTC")}`:"";
    timeline.disabled=dirty||loading||playback==="pair"||!selection||Boolean(preparedSequence)||!range||maskPolicy===null||!images.has(current);
    timeline.setAttribute("aria-busy",String(loading));
    timeline.textContent=loading?t("Đang tải đủ 5 ảnh…","Loading all 5 frames…"):
      preparedSequence?t("Đã tải đủ 5 ảnh","All 5 frames are ready"):t("Tải trước 5 ảnh","Preload 5 frames");
    timeline.title=t("Chọn 5 lần chụp liền nhau theo MJD; tải đủ trước khi phát.","Select five consecutive observations by MJD and preload them before playback.");
    const missing=indices.some(index=>!images.get(index)?.decoded);
    timelinePlay.disabled=dirty||loading||!preparedSequence||!complete||playback==="pair";
    timelinePlay.textContent=playing?t("Ⅱ Tạm dừng","Ⅱ Pause"):paused?t("▶ Phát tiếp","▶ Resume"):t("▶ Phát","▶ Play");
    newSequence.hidden=!preparedSequence||!selection||selection.windowCount<2;
    newSequence.disabled=dirty||loading||playback==="pair"||!selection||selection.windowCount<2;
    const hint=el("explorer-timeline-hint");
    if(hint){
      hint.textContent=loading?t("Đang lấy 5 cutout cùng lưới bầu trời từ IRSA. Khi đủ 5 ảnh, nút Phát sẽ sẵn sàng.","Fetching five cutouts on the same sky grid from IRSA. Play becomes available when all five are ready."):
        preparedSequence&&complete?t(`5 ảnh đã giải mã, cùng tâm và tỷ lệ pixel. ${timelineBandCaveat(indices)}`,`All five frames are decoded on the same sky center and pixel scale. ${timelineBandCaveat(indices)}`):
        preparedSequence&&missing?t("Chuỗi chưa đủ ảnh. Bấm Tải lại ảnh để thử lại khung lỗi.","The sequence is incomplete. Retry the failed frames."):"";
      hint.hidden=!loading&&!preparedSequence;
    }
    const summary=el("explorer-sequence-summary");
    if(summary){
      if(dirty)summary.textContent=t("Chạy lại truy vấn để tạo chuỗi.","Run the search again to create a sequence.");
      else if(candidates.length<SEQUENCE_SIZE)summary.textContent=t(`${rows.length} lần quan sát trong kết quả; chỉ ${candidates.length} lần có ảnh dùng được, cần ít nhất 5 để phát.`,`${rows.length} observations returned; only ${candidates.length} have viewable images. At least five are needed for playback.`);
      else if(loading)summary.textContent=t("Đang tải và giải mã đủ 5 ảnh liên tiếp…","Loading and decoding all five consecutive frames…");
      else if(preparedSequence&&complete)summary.textContent=t(`${rows.length} lần quan sát · chuỗi ${selection.start+1}–${selection.start+SEQUENCE_SIZE}/${candidates.length} · ${rangeLabel}. Bấm Phát để xem liền mạch.`,`${rows.length} observations · sequence ${selection.start+1}–${selection.start+SEQUENCE_SIZE}/${candidates.length} · ${rangeLabel}. Press Play for continuous playback.`);
      else if(preparedSequence)summary.textContent=t(`${timelineFrames(indices).length}/5 ảnh qua kiểm tra lưới, mask và thời gian; không bỏ khung. ${timelineUnavailableReason(indices)}`,`${timelineFrames(indices).length}/5 frames passed grid, mask and time checks; frames are not skipped. ${timelineUnavailableReason(indices)}`);
      else summary.textContent=t(`${rows.length} lần quan sát từ IRSA · ${candidates.length} ảnh phát được · đã chọn ngẫu nhiên 5 lần liền nhau (${selection.start+1}–${selection.start+SEQUENCE_SIZE}) · ${rangeLabel}. Tải trước đủ 5 ảnh rồi bấm Phát.`,`${rows.length} IRSA observations · ${candidates.length} viewable images · randomly selected five consecutive frames (${selection.start+1}–${selection.start+SEQUENCE_SIZE}) · ${rangeLabel}. Preload all five, then press Play.`);
      if(truncated)summary.textContent+=t(" Kết quả IRSA bị giới hạn; thu hẹp ngày để xem hết danh sách."," IRSA truncated the result list; narrow the date range to see a complete list.");
    }
  }
  function sequenceCandidates() {
    const sorted=rows.map((row,index)=>({index,row,time:Number(row.t_min_mjd)}))
      .filter(({row,time})=>row.detector===query?.det&&row.access_url&&row.obs_id&&Number.isFinite(time)&&time>0)
      .sort((a,b)=>a.time-b.time||String(a.row.obs_id).localeCompare(String(b.row.obs_id))
        ||String(a.row.access_url).localeCompare(String(b.row.access_url))||a.index-b.index);
    const ids=new Set(),candidates=[];
    for(const item of sorted){
      if(ids.has(item.row.obs_id))continue;
      ids.add(item.row.obs_id);candidates.push(item);
    }
    return candidates;
  }
  function selectRandomSequence(previousStart=null) {
    const candidates=sequenceCandidates(),windowCount=candidates.length-SEQUENCE_SIZE+1;
    if(windowCount<1)return null;
    let start=Math.floor(Math.random()*windowCount);
    if(windowCount>1&&start===previousStart)start=(start+1+Math.floor(Math.random()*(windowCount-1)))%windowCount;
    return {start,windowCount,indices:candidates.slice(start,start+SEQUENCE_SIZE).map(item=>item.index)};
  }
  function resetDisplay() {
    el("explorer-image").hidden=true;el("explorer-image").removeAttribute("src");
    el("explorer-image-wrap").classList.remove("full-detector-view");el("explorer-target-marker").hidden=true;el("explorer-open-full-image").hidden=true;
    for(const id of ["explorer-frame-label","explorer-center-status","explorer-frame-meta","explorer-frame-hash"])el(id).textContent="";
    for(const id of ["explorer-pin","explorer-play","explorer-export","explorer-previous","explorer-next","explorer-current"])el(id).disabled=true;
    el("explorer-current").value="0";el("explorer-current").max="0";
    el("explorer-reference").textContent=t("Chọn một lần quan sát hoặc phát chuỗi theo thời gian.","Choose an observation or play the timeline.");
    for(const id of ["explorer-download-fits","explorer-source-fits"]){el(id).removeAttribute("href");el(id).hidden=true;}
    el("explorer-display").hidden=true;
    timelinePlay.disabled=true;newSequence.hidden=true;
    timelineControls();
  }
  function inputQuery() {
    const ra=coordinate(el("explorer-ra").value,true),dec=coordinate(el("explorer-dec").value,false),fov=Number(el("explorer-fov").value),det=Number(el("explorer-detector").value);
    if(!Number.isFinite(fov)||fov<.06||fov>.40)throw new Error(t("Trường nhìn phải từ 0,06 đến 0,40 độ.","Field of view must be between 0.06 and 0.40 degrees."));
    if(!Number.isInteger(det)||det<1||det>6||!["dr1","qr3"].includes(el("explorer-release").value))throw new Error(t("Chọn detector và bản dữ liệu được hỗ trợ.","Choose a supported detector and data release."));
    const p=new URLSearchParams({ra:ra.toString(),dec:dec.toString(),radius:OBSERVATION_SEARCH_RADIUS_DEG.toString(),release:el("explorer-release").value,detector:det.toString(),maxrec:"500",band_min_um:BANDS[det-1][0].toString(),band_max_um:BANDS[det-1][1].toString()});
    const start=el("explorer-from").value,end=el("explorer-to").value;
    if(Boolean(start)!==Boolean(end))throw new Error(t("Chọn cả ngày bắt đầu và kết thúc, hoặc bỏ trống cả hai.","Enter both dates, or leave both blank."));
    if(start&&end) {
      const a=Date.parse(start+"T00:00:00Z")/86400000+40587,b=Date.parse(end+"T23:59:59Z")/86400000+40587;
      if(!Number.isFinite(a+b)||a>b)throw new Error(t("Khoảng ngày không hợp lệ.","Invalid date range."));
      p.set("time_min_mjd",a.toString());p.set("time_max_mjd",b.toString());
    }
    const release=el("explorer-release").value;
    return {p,ra,dec,fov,det,release,from:start,to:end,view:requestedView,viewState:restoreView?initialViewState():null};
  }
  function renderList() {
    const root=el("explorer-frames");root.replaceChildren();
    rows.forEach((row,index)=>{
      const button=document.createElement("button"),title=document.createElement("strong"),detail=document.createElement("span");
      button.type="button";button.setAttribute("aria-pressed",String(index===current));button.disabled=!row.access_url;
      if(index===displayed)button.setAttribute("aria-current","true");
      if(images.has(index))button.dataset.loaded="true";
      title.textContent=`${index+1}. ${index===reference?t("Ảnh A · ","Image A · "):index===current&&reference>=0?t("Ảnh B · ","Image B · "):""}${displayMjd(row.t_min_mjd)}`;detail.textContent=`D${row.detector??"?"} · ${row.obs_id||t("Không có obs ID","No observation ID")}${row.access_url?"":t(" · Không có URL ảnh"," · Image URL unavailable")}`;
      button.append(title,detail);button.addEventListener("click",()=>show(index));root.append(button);
    });
  }
  async function readFrameBlob(response, progress) {
    const length = Number(response.headers.get("Content-Length"));
    if (!progress || !response.body || !(length > 0)) return response.blob();
    const reader = response.body.getReader(), chunks = [];
    let received = 0;
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      chunks.push(value);
      received += value.byteLength;
      progress(Math.min(received / length, 1));
    }
    return new Blob(chunks, {type:"image/png"});
  }
  function waitForRetry(seconds,signal) {
    return new Promise((resolve,reject)=>{
      let id,done=false;
      const abort=()=>{if(done)return;done=true;clearTimeout(id);reject(new DOMException(t("Đã đổi vùng trời","Sky region changed"),"AbortError"));};
      id=setTimeout(()=>{if(done)return;done=true;signal?.removeEventListener?.("abort",abort);resolve();},Math.min(300,Math.max(.9,seconds))*1000);
      if(done)return;
      if(signal?.aborted){abort();return;}
      signal?.addEventListener?.("abort",abort,{once:true});
    });
  }
  function enqueueFrame(row, signal, active, retry, progress) {
    if(!row?.access_url)throw new Error(t("Quan sát không có URL FITS được hỗ trợ.","This observation has no supported FITS URL."));
    const previous=frameQueue, search=query, seq=generation;
    const assertActive=()=>{
      if(signal.aborted||seq!==generation||!active())throw new DOMException(t("Đã đổi ảnh hoặc vùng trời","Image or sky region changed"),"AbortError");
    };
    const task=(async()=>{
      await previous.catch(()=>{});
      assertActive();
      const p=new URLSearchParams({url:row.access_url,ra:search.ra.toString(),dec:search.dec.toString(),fov_deg:search.fov.toString(),zodi:"subtract"});
      if(range){p.set("low",range[0].toString());p.set("high",range[1].toString());}
      const endpoint=`/api/frame?${p}`;
      let response=await fetch(endpoint,{signal});
      if([502,504].includes(response.status)){
        const failure=await response.json().catch(()=>null);
        if(["upstream_http_error","upstream_timeout","upstream_unavailable","upstream_incomplete"].includes(failure?.error)){
          const retryAfterHeader=response.headers?.get?.("Retry-After");
          const retryAfter=retryAfterHeader&&/^\d{1,3}$/.test(retryAfterHeader)?Number(retryAfterHeader):NaN;
          const delay=Number.isInteger(retryAfter)&&retryAfter>0&&retryAfter<=120?retryAfter:.9;
          await waitForRetry(delay,signal);
          assertActive();
          retry();
          response=await fetch(endpoint,{signal});
        } else throw new Error(apiError(response,failure?.error));
      }
      if(response.status===429&&response.headers?.get("Retry-After")&&/^\d{1,5}$/.test(response.headers.get("Retry-After"))){
        const seconds=Number(response.headers.get("Retry-After"));
        setStatus(t(`IRSA đang giới hạn tốc độ. Tạm chờ ${seconds} giây rồi tiếp tục chuỗi…`,`IRSA rate limit reached. Waiting ${seconds} seconds before continuing the sequence…`));
        await waitForRetry(seconds,signal);
        assertActive();retry();response=await fetch(endpoint,{signal});
      }
      if(!response.ok){let error;try{error=(await response.json()).error;}catch{}throw new Error(apiError(response,error));}
      if(!response.headers.get("Content-Type")?.startsWith("image/png"))throw new Error(t("Máy chủ chưa cung cấp ảnh PNG.","The server did not return a PNG image."));
      const blob=await readFrameBlob(response,progress);
      if(signal.aborted||seq!==generation)throw new DOMException(t("Đã đổi vùng trời","Sky region changed"),"AbortError");
      const info={src:URL.createObjectURL(blob),headers:Object.fromEntries([...response.headers].filter(([key])=>key.startsWith("x-frame-"))),row};
      const incomingPolicy=response.headers.get("X-Frame-Mask-Policy")||"undeclared";
      if(maskPolicy!==null&&incomingPolicy!==maskPolicy){URL.revokeObjectURL(info.src);throw new Error(t("Hai ảnh dùng quy tắc loại pixel khác nhau. Hãy tìm lại vùng trời trước khi so sánh.","These images use different pixel masks. Search again before comparing."));}
      const low=Number(response.headers.get("X-Frame-Contrast-Low")),high=Number(response.headers.get("X-Frame-Contrast-High"));
      const valid=Number(response.headers.get("X-Frame-Valid-Pixels"));
      if(valid>0){
        if(!Number.isFinite(low+high)||low>=high){URL.revokeObjectURL(info.src);throw new Error(t("Thang tương phản của ảnh không hợp lệ.","The image contrast settings are invalid."));}
        if(range&&(Math.abs(low-range[0])>1e-9||Math.abs(high-range[1])>1e-9)){URL.revokeObjectURL(info.src);throw new Error(t("Ảnh không cùng thang tương phản với ảnh đối chiếu.","This image uses different contrast settings from the reference."));}
        if(!range)range=[low,high];
      }
      if(maskPolicy===null)maskPolicy=incomingPolicy;
      return info;
    })();
    frameQueue=task.catch(()=>{});return task;
  }
  function frameInfoFromBlob(blob,rawHeaders,row,signal,seq) {
    if(signal?.aborted||seq!==generation)throw new DOMException(t("Đã đổi vùng trời","Sky region changed"),"AbortError");
    const headers=Object.fromEntries(Object.entries(rawHeaders||{}).map(([key,value])=>[key.toLowerCase(),String(value)]));
    if(headers["x-frame-obs-id"]!==row.obs_id||Number(headers["x-frame-detector"])!==row.detector
      ||headers["x-frame-source-url"]!==row.access_url)throw new Error(t("Ảnh trả về không khớp lần quan sát đã chọn.","The returned image does not match the selected observation."));
    const incomingPolicy=headers["x-frame-mask-policy"]||"undeclared";
    if(maskPolicy!==null&&incomingPolicy!==maskPolicy)throw new Error(t("Hai ảnh dùng quy tắc loại pixel khác nhau. Hãy tìm lại vùng trời trước khi so sánh.","These images use different pixel masks. Search again before comparing."));
    const low=Number(headers["x-frame-contrast-low"]),high=Number(headers["x-frame-contrast-high"]),valid=Number(headers["x-frame-valid-pixels"]);
    if(valid>0){
      if(!Number.isFinite(low+high)||low>=high)throw new Error(t("Thang tương phản của ảnh không hợp lệ.","The image contrast settings are invalid."));
      if(range&&(Math.abs(low-range[0])>1e-9||Math.abs(high-range[1])>1e-9))throw new Error(t("Ảnh không cùng thang tương phản với ảnh đối chiếu.","This image uses different contrast settings from the reference."));
      if(!range)range=[low,high];
    }
    if(maskPolicy===null)maskPolicy=incomingPolicy;
    return {src:URL.createObjectURL(blob),headers,row};
  }
  async function decodeFrameImage(info) {
    if(info.decoded)return info;
    const image=new Image();image.src=info.src;
    try {
      await image.decode();
      const size=Number(info.headers["x-frame-grid-size-px"]);
      if(!Number.isInteger(size)||image.naturalWidth!==size||image.naturalHeight!==size)throw new Error(t("Ảnh trả về sai kích thước lưới.","The returned image dimensions do not match the sky grid."));
    } catch(error) {URL.revokeObjectURL(info.src);throw error;}
    info.decoded=true;
    return info;
  }
  function decodeBase64Image(value) {
    if(typeof value!=="string"||value.length>2_500_000)throw new Error(t("Dữ liệu ảnh chuỗi không hợp lệ.","The sequence image payload is invalid."));
    const binary=atob(value),bytes=new Uint8Array(binary.length);
    for(let index=0;index<binary.length;index++)bytes[index]=binary.charCodeAt(index);
    return new Blob([bytes],{type:"image/png"});
  }
  async function loadSequenceBatch(indices,seq) {
    const payload={ra:query.ra,dec:query.dec,fov_deg:query.fov,zodi:"subtract",low:range[0],high:range[1],
      frames:indices.map(index=>({index,url:rows[index].access_url}))};
    const response=await fetch("/api/sequence",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload),signal:request.signal});
    const data=await response.json().catch(()=>null);
    if(!response.ok)throw new Error(apiError(response,data?.error));
    if(!data||!Array.isArray(data.frames)||!Array.isArray(data.errors))throw new Error(t("Máy chủ trả về danh sách ảnh không hợp lệ.","The server returned an invalid sequence response."));
    const received=new Set(),decodeErrors=[];
    await Promise.all(data.frames.map(async item=>{
      const index=item?.index;
      if(!indices.includes(index)||received.has(index)||!rows[index]||!item.png||!item.headers)return;
      try{
        const info=await decodeFrameImage(frameInfoFromBlob(decodeBase64Image(item.png),item.headers,rows[index],request.signal,seq));
        const previous=images.get(index);if(previous?.src&&previous.src!==info.src)URL.revokeObjectURL(previous.src);
        images.set(index,info);received.add(index);
        const button=el("explorer-frames").children[index];if(button)button.dataset.loaded="true";
      }catch(error){decodeErrors.push({index,error:error?.message||"image_decode_failed"});}
    }));
    const notDecoded=indices.filter(index=>!images.get(index)?.decoded);
    return [...data.errors,...decodeErrors,...notDecoded.filter(index=>!decodeErrors.some(item=>item.index===index)).map(index=>({index,error:"frame_not_returned"}))];
  }
  function load(index,seq,active=()=>seq===generation&&current===index,background=false) {
    if(images.has(index))return images.get(index);
    if(pendingFrames.has(index))return pendingFrames.get(index);
    const jobs=pendingFrames;
    const task=enqueueFrame(rows[index],request.signal,active,
      ()=>{if(!background)setStatus(t("IRSA tạm lỗi khi tải ảnh. Đang thử lại…","IRSA could not return the image. Retrying…"));})
      .then(info=>{images.set(index,info);return info;});
    jobs.set(index,task);task.then(()=>jobs.delete(index),()=>jobs.delete(index));return task;
  }
  async function loadComparisonFrame(row, signal, progress) {
    const index=rows.findIndex(item=>item.access_url===row.access_url);
    if(images.has(index))return {...images.get(index), owned:false};
    if(pendingFrames.has(index)){
      const info=await pendingFrames.get(index).catch(()=>null);
      if(info)return {...info, owned:false};
    }
    const info=await enqueueFrame(row,signal,()=>workspaceActive()&&!dirty,
      ()=>progress(null,true),progress);
    return {...info,owned:true};
  }
  async function comparisonObservations(detector, signal) {
    const params=new URLSearchParams(query.p.toString()), band=BANDS[detector-1];
    params.set("detector",String(detector));
    params.set("band_min_um",String(band[0]));
    params.set("band_max_um",String(band[1]));
    const response=await fetchObservations("/api/observations?"+params,signal);
    const data=await response.json();
    if(!response.ok)throw new Error(apiError(response,data.error));
    return {rows:data.observations, truncated:Boolean(data.truncated), provenance:data.provenance};
  }
  function draw(info,index,sequencePosition="") {
    const img=el("explorer-image");img.src=info.src;img.hidden=false;
    const wrap=el("explorer-image-wrap");wrap.classList.remove("full-detector-view");el("explorer-target-marker").hidden=true;
    const gridSize=Number(info.headers["x-frame-grid-size-px"]);
    if(Number.isInteger(gridSize)&&gridSize>0)wrap.style.setProperty("--linked-grid-width",Math.min(560,gridSize*8)+"px");
    const centerStatus=info.headers["x-frame-center-pixel-status"];
    el("explorer-center-status").textContent=centerStatus==="valid"?t("Tọa độ tâm có pixel dữ liệu.","The center coordinate has a valid data pixel."):
      centerStatus==="masked"?t("Pixel đúng tâm bị loại; các pixel hợp lệ xung quanh vẫn hiển thị.","The exact center pixel is excluded; surrounding valid pixels remain visible."):
      centerStatus==="missing"?t("Tâm tọa độ không có dữ liệu; vùng ảnh vẫn có thể chứa pixel hợp lệ.","The center has no data; valid pixels may still appear elsewhere in the cutout."):"";
    const list=el("explorer-frames");list.children[displayed]?.removeAttribute("aria-current");
    displayed=index;list.children[index]?.setAttribute("aria-current","true");
    const time=info.headers["x-frame-time-system"]==="UTC"&&info.headers["x-frame-mjd-obs"]?displayMjd(Number(info.headers["x-frame-mjd-obs"]),"UTC"):displayMjd(info.row.t_min_mjd);
    const release=(info.row.release||query.release).toUpperCase();
    img.alt=t(`Ảnh SPHEREx ${release}, detector D${info.row.detector}, ${time}, ${info.row.obs_id}. Bắc ở trên, Đông bên trái. Cam là pixel bị loại; tím là pixel thiếu dữ liệu.`,`SPHEREx ${release}, detector D${info.row.detector}, ${time}, ${info.row.obs_id}. North is up and east is left. Orange marks excluded pixels; purple marks missing data.`);
    const band=spectralSample(info),wavelength=band?` · λ ${((band.low+band.high)/2).toFixed(3)} µm`:"";
    el("explorer-frame-label").textContent=`${sequencePosition||`${index+1}/${rows.length}`} · ${time}${wavelength} · ${info.row.obs_id}`;
    if(!linkedPair)fillFrameMetadata(info);
    el("explorer-current").value=String(index);el("explorer-pin").disabled=false;el("explorer-export").disabled=false;
  }
  function fillFrameMetadata(info) {
    const release=(info.row.release||query.release).toUpperCase();
    const counts=["x-frame-valid-pixels","x-frame-masked-pixels","x-frame-missing-pixels"].map(key=>info.headers[key]===undefined?null:Number(info.headers[key]));
    const quality=counts.every(value=>Number.isInteger(value)&&value>=0)?t(` ${counts[0]} pixel có dữ liệu; ${counts[1]} pixel bị loại; ${counts[2]} pixel thiếu.`,` ${counts[0]} valid pixels; ${counts[1]} excluded; ${counts[2]} missing.`):"";
    const contrast=range?range.map(value=>value.toFixed(4)).join("–"):t("theo ảnh","per frame");
    const band=spectralSample(info),spectrum=band?` · WCS-WAVE ${((band.low+band.high)/2).toFixed(3)} µm, Δ${band.width.toFixed(3)} µm`:"";
    const size=Number(info.headers["x-frame-grid-size-px"]),scale=Number(info.headers["x-frame-grid-scale-arcsec"]),fov=Number(info.headers["x-frame-grid-fov-deg"]);
    const grid=Number.isInteger(size)&&size>0?`${size} × ${size} ${t("pixel","pixels")}${Number.isFinite(scale)?` · ${scale.toFixed(2)}″/${t("pixel","pixel")}`:""}${Number.isFinite(fov)?` · ${t("trường nhìn","field of view")} ${(fov*60).toFixed(1)}′`:""}`:"";
    el("explorer-frame-meta").textContent=t(`${release} · D${info.row.detector} · ${grid} · cùng lưới trời Bắc lên, Đông trái · đã trừ ánh sáng hoàng đạo · thang xám chung ${contrast} MJy/sr. Cam: pixel bị loại; tím: thiếu dữ liệu.`,`${release} · D${info.row.detector} · ${grid} · north-up, east-left sky grid · zodiacal light subtracted · shared grayscale stretch ${contrast} MJy/sr. Orange: excluded; purple: missing.`)+quality+spectrum;
    const sha=info.headers["x-frame-cutout-sha256"]||"";
    el("explorer-frame-hash").textContent=sha?`SHA-256 cutout: ${sha}`:t("Hash không có sẵn.","No hash is available.");
    el("explorer-download-fits").href=info.headers["x-frame-cutout-url"]||"";
    el("explorer-download-fits").textContent=t("Tải cutout FITS tại IRSA ↗","Download cutout FITS from IRSA ↗");
    el("explorer-download-fits").hidden=!info.headers["x-frame-cutout-url"];
    const openFull=el("explorer-open-full-image");openFull.removeAttribute("href");openFull.hidden=true;
    el("explorer-source-fits").href=info.headers["x-frame-source-url"]||"";
    el("explorer-source-fits").hidden=!info.headers["x-frame-source-url"];
    el("explorer-limit").textContent=t("Chuỗi dùng cùng một lưới tọa độ và tỷ lệ pixel để nền trời không nhảy theo hướng kính. Mỗi pixel là mẫu dữ liệu thật, không nội suy thêm chi tiết. Detector và bước sóng có thể khác nhau; ảnh biến đổi chưa đủ để kết luận thiên thể đang chuyển động.","Frames share a sky grid and pixel scale so the background does not jump with telescope pointing. Each pixel is a real data sample; no extra detail is interpolated. Detector response and wavelength can vary, so a changing image alone does not confirm motion.");
  }
  function referenceText() {
    if(context().paired)return t(`Đã chọn ảnh A: ${reference+1} · ảnh B: ${current+1}.`,`Image A: ${reference+1} · image B: ${current+1}.`);
    if(reference>=0)return t(`Ảnh A: ${reference+1}. Chọn một ảnh khác làm B.`,`Image A: ${reference+1}. Select another frame as B.`);
    return t("Chọn một lần quan sát hoặc phát chuỗi để xem ảnh theo thời gian.","Choose an observation or play the timeline to view images over time.");
  }
  function frameStatus() {
    return context().paired?t("Cặp A/B đã sẵn sàng. Bước sóng tại từng pixel có thể khác nhau.","A/B pair ready. The wavelength sampled at each pixel can differ."):query?.view==="timeline"?t("Ảnh đã tải. Tải trước đủ 5 khung liền nhau rồi bấm Phát.","Image loaded. Preload five consecutive frames, then press Play."):t("Ảnh đã tải. Chọn ảnh khác nếu muốn so sánh A/B.","Image loaded. Select another observation for A/B comparison.");
  }
  function renderResults() {
    el("explorer-count").textContent=t(`${rows.length} quan sát D${query.det} · ${query.release.toUpperCase()}`,`${rows.length} D${query.det} observations · ${query.release.toUpperCase()}`);
    el("explorer-warning").textContent=truncated?t("Kết quả IRSA bị giới hạn. Thu hẹp khoảng ngày; danh sách chưa đầy đủ.","IRSA truncated the results. Narrow the date range; the list is incomplete."):t("Danh sách gồm mọi lần quan sát IRSA trả về cho truy vấn hiện tại; kho dữ liệu có thể cập nhật.","This lists every observation returned by IRSA for this query; the archive can change.");
    renderList();
  }
  async function show(index) {
    if(!rows[index]||!query)return;
    if(dirty){setStatus(t("Cấu hình đã đổi. Tìm lại ảnh để tiếp tục.","Search settings changed. Search for images to continue."),true);return;}
    sequenceRun=retrySequence=null;timelineState=null;stop();
    saveNote();noteKey=null;el("explorer-note").value="";const seq=generation;current=index;renderList();
    el("explorer-image").hidden=true;for(const id of["explorer-pin","explorer-play","explorer-export"])el(id).disabled=true;
    el("explorer-retry").hidden=true;
    el("explorer-previous").disabled=index===0;el("explorer-next").disabled=index===rows.length-1;
    timelineControls();timeline.disabled=true;
    setStatus(t(`Đang tải ảnh ${index+1}/${rows.length} từ IRSA…`,`Loading image ${index+1}/${rows.length} from IRSA…`));
    try {
      const info=await load(index,seq);
      if(seq!==generation||current!==index)return;
      draw(info,index);restoreNote();el("explorer-reference").textContent=referenceText();setStatus(frameStatus());
      el("explorer-play").disabled=reference<0||reference===index||!images.has(reference);
      timelineControls();notify("frame");return info;
    }catch(error){
      if(error.name!=="AbortError"&&seq===generation&&current===index){
        setStatus(t(`Không tải được cutout: ${error.message}. Chọn ảnh khác hoặc bấm Tải lại ảnh.`,`Could not load the cutout: ${error.message}. Select another image or retry.`),true);
        el("explorer-image").hidden=true;el("explorer-retry").hidden=!rows[index]?.access_url;
      }
    }
  }
  async function loadUserSequence(retry=null) {
    if(dirty||!query||sequenceRun)return;
    const selection=selectedSequence,indices=retry?.indices||selection?.indices;
    if(!indices||indices.length!==SEQUENCE_SIZE||!range||maskPolicy===null){
      setStatus(t("Cần 5 lần quan sát có ảnh và một ảnh đầu để đặt thang hiển thị.","Five viewable observations and one loaded frame are needed to set the display scale."),true);
      return;
    }
    stop();
    preparedSequence={kind:"user",indices:indices.slice(),sourceCount:sequenceCandidates().length,truncated};
    timelineState=null;
    const run={kind:"user",indices:indices.slice()};
    sequenceRun=run;retrySequence=null;timelineControls();
    let errors=[];
    try{errors=await loadSequenceBatch(indices,generation);}
    catch(error){
      if(error.name!=="AbortError")setStatus(t(`Không tải được chuỗi: ${error.message}. Bấm Tải lại ảnh để thử lại.`,`Could not load the sequence: ${error.message}. Retry the failed images.`),true);
      errors=[{error:error.message}];
    }
    if(sequenceRun!==run){timelineControls();notify("sequence-ready");return;}
    sequenceRun=null;
    if(!workspaceActive())return;
    const frames=timelineFrames(indices),missing=indices.some(index=>!images.get(index)?.decoded);
    if(missing){
      retrySequence={indices:indices.slice()};el("explorer-retry").hidden=false;
      const readyCount=indices.filter(index=>images.get(index)?.decoded).length,failed=Math.max(errors.length,indices.length-readyCount);
      setStatus(t(`Đã tải và giải mã ${readyCount}/5 ảnh; ${failed} còn lỗi. Bấm Tải lại ảnh.`,`Loaded and decoded ${readyCount}/5 frames; ${failed} failed. Retry the sequence.`),true);
    }else if(frames.length!==SEQUENCE_SIZE){
      setStatus(t(`Đã tải đủ ảnh nhưng không cùng lưới, mask hoặc thời gian. ${timelineUnavailableReason(indices)}`,`All frames loaded but they do not share a valid grid, mask or time. ${timelineUnavailableReason(indices)}`),true);
    }else{
      el("explorer-retry").hidden=true;current=frames[0];renderList();draw(images.get(current),current,`1/${SEQUENCE_SIZE}`);
      el("explorer-previous").disabled=current===0;el("explorer-next").disabled=current===rows.length-1;
      setStatus(t(`Đã tải và giải mã đủ 5 ảnh liền nhau. Bấm Phát để xem theo thời gian.${timelineBandCaveat(indices)}`,`All five consecutive images are loaded and decoded. Press Play to watch them in time order.${timelineBandCaveat(indices)}`));
      notify("frame");
    }
    timelineControls();
  }  function startTimelinePlayback(frames) {
    if(!frames.length||frames.some(index=>!images.has(index)))return;
    const resume=timelineState?.generation===generation&&timelineState.frames.length===frames.length
      &&timelineState.frames.every((frame,index)=>frame===frames[index]);
    const state=resume?timelineState:{generation,frames:frames.slice(),index:0};
    timelineState=state;playback="timeline";let index=state.index;
    const showPlayingFrame=()=>{current=frames[index];renderList();draw(images.get(frames[index]),frames[index],`${index+1}/${frames.length}`);};
    showPlayingFrame();
    timer=setInterval(()=>{index=(index+1)%frames.length;state.index=index;showPlayingFrame();},1000);
    timelineControls();
    setStatus(t(`Đang phát ${frames.length} ảnh theo thời gian với cùng thang hiển thị.${timelineBandCaveat(frames)} Chưa xác nhận chuyển động hay biến quang.`,
      `Playing ${frames.length} images in time order with one display scale.${timelineBandCaveat(frames)} Motion and variability are unconfirmed.`));
  }
  el("explorer-form").addEventListener("submit",async event=>{
    event.preventDefault();let next;try{next=inputQuery();}catch(error){setStatus(error.message,true);return;}
    saveNote();noteKey=null;el("explorer-note").value="";request?.abort();sequenceRun=retrySequence=null;stop();preparedSequence=timelineState=selectedSequence=null;generation++;const seq=generation;request=new AbortController();clearImages();query=next;dirty=false;range=null;maskPolicy=null;rows=[];current=displayed=reference=-1;provenance=null;frameQueue=Promise.resolve();pendingFrames=new Map();
    resetDisplay();el("explorer-results").hidden=true;el("explorer-search").disabled=true;
    setStatus(t("Đang truy vấn danh sách quan sát SPHEREx từ IRSA…","Searching the IRSA catalog for SPHEREx observations…"));
    try {
      const response=await fetchObservations(`/api/observations?${query.p}`,request.signal),data=await response.json();
      if(!response.ok)throw new Error(apiError(response,data?.error));
      if(seq!==generation)return;
      rows=data.observations.slice().sort((a,b)=>(a.t_min_mjd??Infinity)-(b.t_min_mjd??Infinity)||String(a.obs_id||"").localeCompare(String(b.obs_id||"")));
      provenance=data.provenance;truncated=Boolean(data.truncated);selectedSequence=selectRandomSequence();
      if(!searchActive()||dirty)return;
      el("explorer-results").hidden=false;el("explorer-display").hidden=!rows.length;el("explorer-current").disabled=!rows.length;
      el("explorer-upstream").href=provenance.query_url;el("explorer-upstream").textContent=t("Truy vấn IRSA ↗","IRSA query ↗");el("explorer-current").max=String(Math.max(0,rows.length-1));renderResults();timelineControls();
      const share=new URL(location.href);for(const key of [...share.searchParams.keys()])if(key.startsWith("sky_"))share.searchParams.delete(key);
      for(const key of ["ra","dec","fov","det","release","from","to","view"])if(query[key]!=="")share.searchParams.set(`sky_${key}`,String(query[key]));
      share.searchParams.set("sky_autoload","1");history.replaceState(null,"",share);restoreView=false;
      if(query.view==="compare"&&comparison)el("explorer-status").textContent=t("Chọn thời điểm và dải cho từng ảnh A / B.","Choose an observation and band for each image, A / B.");
      notify("results");if(query.view==="compare"&&comparison)return;
      const first=selectedSequence?.indices[0]??rows.findIndex(row=>row.access_url);
      if(first>=0)await show(first);
      else setStatus(rows.length?t("Danh sách không có URL ảnh hỗ trợ. Quay lại Dữ liệu để đổi truy vấn.","These results have no supported image URLs. Return to Data to change the search."):data.truncated?t("Chưa thấy detector đã chọn trong phần kết quả bị cắt. Hãy thu hẹp truy vấn.","The selected detector did not appear in this truncated result. Narrow the search."):t("Không có quan sát phù hợp. Đổi release hoặc khoảng ngày rồi tìm lại.","No matching observations. Try a different release or date range."));
    }catch(error){
      if(error.name!=="AbortError"&&seq===generation&&searchActive())setStatus(t(`Tìm ảnh chưa thành công: ${error.message}. Thử tìm lại sau.`,`Image search failed: ${error.message}. Try the search again.`),true);
    }
    finally{if(seq===generation)el("explorer-search").disabled=false;}
  });
  el("explorer-preset").addEventListener("change",()=>{const p=presets[el("explorer-preset").value];if(p){el("explorer-ra").value=p[0].toString();el("explorer-dec").value=p[1].toString();el("explorer-fov").value="0.40";}markDirty();});
  el("explorer-previous").addEventListener("click",()=>show(current-1));el("explorer-next").addEventListener("click",()=>show(current+1));
  el("explorer-current").addEventListener("change",()=>show(Number(el("explorer-current").value)));
  el("explorer-retry").addEventListener("click",()=>retrySequence?loadUserSequence(retrySequence):show(current));
  el("explorer-pin").addEventListener("click",()=>{saveNote();stop();if(!context().ready)return;reference=displayed;restoreNote();renderList();el("explorer-reference").textContent=referenceText();el("explorer-play").disabled=true;el("explorer-export").disabled=true;notify("pin");});
  el("explorer-play").addEventListener("click",()=>{
    if(timer){stop();return;}if(dirty||reference<0||reference===current||!images.has(reference)||!images.has(current))return;
    const a=reference,b=current;let index=a;draw(images.get(index),index);el("explorer-play").textContent=t("Dừng phát","Pause");
    playback="pair";
    timelineControls();
    timer=setInterval(()=>{index=index===a?b:a;draw(images.get(index),index);},800);
  });
  timeline?.addEventListener("click",()=>void loadUserSequence());
  timelinePlay?.addEventListener("click",()=>{
    if(timer){
      const state=timelineState,pausedIndex=state?.generation===generation?state.frames[state.index]:displayed;
      stop();
      if(pausedIndex>=0&&images.has(pausedIndex)){
        current=pausedIndex;renderList();draw(images.get(pausedIndex),pausedIndex,`${state.index+1}/${state.frames.length}`);
        el("explorer-previous").disabled=pausedIndex===0;el("explorer-next").disabled=pausedIndex===rows.length-1;
        timelineControls();notify("frame");setStatus(t(`Đã tạm dừng ở ảnh ${state.index+1}/${state.frames.length}. Bấm Phát tiếp để tiếp tục.`,`Paused at image ${state.index+1}/${state.frames.length}. Press Resume to continue.`));
      }
      return;
    }
    const frames=timelineFrames(preparedSequence?.indices||[]);
    if(preparedSequence&&frames.length===SEQUENCE_SIZE&&frames.every(index=>images.has(index)))startTimelinePlayback(frames);
  });
  newSequence?.addEventListener("click",()=>{
    if(dirty||sequenceRun)return;
    const previousStart=selectedSequence?.start??null;stop();preparedSequence=retrySequence=timelineState=null;
    selectedSequence=selectRandomSequence(previousStart);el("explorer-retry").hidden=true;timelineControls();
    const first=selectedSequence?.indices[0];if(first===undefined)return;
    current=first;renderList();if(images.has(first)){draw(images.get(first),first);setStatus(frameStatus());}
    void loadUserSequence();
  });
  el("explorer-export").addEventListener("click",()=>{
    const selected=context();if(!selected.ready||!selected.paired)return;
    const serializedFrames=[...images].map(([index,info])=>({index,...info.row,headers:info.headers}));
    for(const info of linkedPair||[]){
      if(!serializedFrames.some(frame=>frame.access_url===info.row.access_url)){
        serializedFrames.push({index:null,...info.row,headers:info.headers,discovery_provenance:info.provenance});
      }
    }
    const bundle={schema_version:1,kind:"observation-display-evidence",exported_at:new Date().toISOString(),query:{...query,p:query.p.toString()},provenance,
      selected_pair:{reference:selected.reference,current:selected.current,reference_index:selected.linked?null:reference,current_index:selected.linked?null:current},
      observations:rows,display_range_mjy_sr:range,mask_policy:maskPolicy,loaded_frames:serializedFrames,
      review_note:el("explorer-note").value,qualification:"User visual inspection; no registered astrometry, spectral matching, calibrated detection probability or fitted motion. Pixel wavelengths require science calibration."};
    const url=URL.createObjectURL(new Blob([JSON.stringify(bundle,null,2)],{type:"application/json"})),a=document.createElement("a");a.href=url;a.download="spherex-observation-review.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    el("explorer-note-state").textContent=t("Đã tạo JSON · lưu tệp để giữ ghi nhận sau khi đóng tab","JSON created · save the file to keep your note after closing the tab");
  });
  document.addEventListener("visibilitychange",()=>{if(document.hidden)stop();});
  window.addEventListener?.("hashchange",()=>{
    if(workspaceActive())return;
    request?.abort();
    generation++;
    sequenceRun=retrySequence=null;
    if(el("explorer-search").disabled||pendingFrames.size){
      dirty=true;
      el("explorer-search").disabled=false;
      setStatus("");
    }
  });
  document.addEventListener("spherex:language",()=>{
    dateSummary();
    stop();
    if(query&&!el("explorer-results").hidden)renderResults();
    el("explorer-reference").textContent=referenceText();
    if(images.has(current)&&context().ready){draw(images.get(current),current);setStatus(frameStatus());}
    if(el("explorer-note").value)el("explorer-note-state").textContent=draftMessage();
  });
  el("explorer-form").addEventListener("input",markDirty);el("explorer-form").addEventListener("change",markDirty);
  el("explorer-note").addEventListener("input",saveNote);
  if(typeof window!=="undefined")window.SkyExplorer={context,pause:stop};
  comparison=window.SkyLinkedComparison?.mount({root:el("explorer-results"), bands:BANDS, timeLabel:displayMjd,
    loadFrame:loadComparisonFrame, loadObservations:comparisonObservations, stopTimeline:stop, onPairChange:selectLinkedPair,
    initialMode:requestedView, onViewStateChange:shareView, onModeChange(view){
      requestedView=view;
      if(query)query.view=view;
      if(view==="compare"&&sequenceRun){
        sequenceRun=retrySequence=null;
        timelineControls();
        setStatus(frameStatus());
      }
      const share=new URL(location.href);
      share.searchParams.set("sky_view",view);
      history.replaceState(history.state,"",share);
      if(view==="timeline"&&current<0){const first=selectedSequence?.indices[0]??rows.findIndex(row=>row.access_url);if(first>=0)void show(first);}
    }});
  const legacyRelease=incoming.get("sky_release")==="qr2";
  for(const [name,id] of [["ra","explorer-ra"],["dec","explorer-dec"],["fov","explorer-fov"],["det","explorer-detector"],["release","explorer-release"],["from","explorer-from"],["to","explorer-to"]]){
    if(!incoming.has(`sky_${name}`))continue;
    el(id).value=name==="release"&&legacyRelease?"dr1":incoming.get(`sky_${name}`);
  }
  function syncPreset() {
    let selected="custom";
    try {
      const ra=coordinate(el("explorer-ra").value,true),dec=coordinate(el("explorer-dec").value,false);
      selected=Object.keys(presets).find(id=>Math.abs(presets[id][0]-ra)<1e-8&&Math.abs(presets[id][1]-dec)<1e-8)||"custom";
    }catch{}
    el("explorer-preset").value=selected;
  }
  for(const id of ["explorer-ra","explorer-dec"])el(id).addEventListener("input",syncPreset);
  syncPreset();dateSummary();timelineControls();
  if(legacyRelease)setStatus(t("Liên kết QR2 cũ. Chọn Tìm ảnh để tra DR1 đã xử lý lại.","This is a legacy QR2 link. Search to use the reprocessed DR1 release."));
  const resumeLink=["#compare-step","#check-step","#review-step"].includes(location.hash)&&incoming.get("flow_source")!=="wise";
  if(!legacyRelease&&(resumeLink||incoming.get("sky_autoload")==="1")
      &&searchRoutes.has(location.hash)&&incoming.has("sky_ra")&&incoming.has("sky_dec")){
    let attempted=false;
    const autoload=()=>{
      if(attempted||!window.SkyWorkflow||!searchRoutes.has(location.hash))return;
      attempted=true;
      try {
        const next=inputQuery();
        if(!resumeLink&&incoming.get("sky_autoload")!=="1")return;
      }
      catch(error){setStatus(error.message,true);return;}
      el("explorer-form").requestSubmit();
    };
    document.addEventListener("spherex:workspace-ready",autoload,{once:true});
    requestAnimationFrame(autoload);
  }
})();

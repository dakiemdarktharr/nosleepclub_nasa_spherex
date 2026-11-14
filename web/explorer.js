"use strict";
// Discovery and display use public IRSA observations; no motion fit is performed.
(() => {
  const el = id => document.getElementById(id), BANDS = [[.75,1.09],[1.10,1.62],[1.63,2.41],[2.42,3.82],[3.83,4.41],[4.42,5.00]];
  const english = () => document.documentElement?.lang?.startsWith("en");
  const t = (vi, en) => english() ? en : vi;
  const presets = {
    wise0855:[133.7601213914074,-7.242127941212259], barnard:[269.44626688537255,4.768222216475269],
    epsilon:[331.04583333,-56.78333333], rwaur:[76.95652603458332,30.401438173888888], rdra:[248.16761083294998,66.75497941722]
  };
  const epsilonTimeline = {
    id: "epsilon-dr1",
    observations: ["2025W18_1B_0081_3", "2025W18_2B_0011_3", "2025W19_1B_0344_3"]
  };
  const maxTimelineCandidates=6;
  let rows=[], query=null, provenance=null, current=-1, displayed=-1, reference=-1, generation=0, request=null, timer=null, range=null, maskPolicy=null, dirty=true;
  let frameQueue=Promise.resolve(), pendingFrames=new Map();
  let playback=null, truncated=false, sequenceRun=null, retrySequence=null;
  let automaticTimelineAttempted=false, preparedSequence=null, timelineState=null;
  const publicRoutes = new Set(["#orbit", "#about", "#night-sky"]);
  const searchRoutes = new Set(["#home", "#explore", "#compare-step", "#data-step"]);
  const workspaceActive = () => !publicRoutes.has(location.hash) &&
    (Boolean(location.hash) || /[?&](?:sky_ra|flow_source)=/.test(location.search));
  const searchActive = () => searchRoutes.has(location.hash)||(!location.hash&&workspaceActive());
  const timeline = el("explorer-timeline");
  const fallbackLinks=["workflow-frame-status","explorer-status"].map(id=>{
    const link=document.createElement("a");
    link.className="outline-button explorer-saved-sequence";
    link.hidden=true;
    el(id).after(link);
    return link;
  });
  const incoming = new URLSearchParams(location.search);
  let requestedView = incoming.get("sky_view") === "timeline" ? "timeline" : "compare";
  const images=new Map();
  let comparison, linkedPair=null;
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
    if(linkedPair&&!dirty)return {...common,ready:true,paired:true,linked:true,
      current:linkedPair[1].row,reference:linkedPair[0].row,
      reference_index:-1,current_index:-1,preview:linkedPair[1].src};
    return {...common,ready,paired:ready&&reference>=0&&reference!==current&&images.has(reference),
      current:ready?rows[current]:null,reference:reference>=0?rows[reference]:null,
      current_index:current,reference_index:reference,preview:ready?images.get(current).src:null};
  }
  function selectLinkedPair(pair){
    if(pair?.[0]===linkedPair?.[0]&&pair?.[1]===linkedPair?.[1])return;
    saveNote();
    linkedPair=pair;
    restoreNote();
    if(pair)fillFrameMetadata(pair[1]);
    else if(images.has(current))fillFrameMetadata(images.get(current));
    el("explorer-export").disabled=!context().paired;
    notify("pair");
  }
  function notify(kind){
    if(typeof CustomEvent==="function")document.dispatchEvent(new CustomEvent("explorer:state",{detail:{kind,context:context()}}));
    comparison?.update({query, rows, images, dirty, truncated, provenance, loading:pendingFrames.size>0, busy:Boolean(sequenceRun)});
  }
  function dateSummary(){const a=el("explorer-from").value,b=el("explorer-to").value,fmt=v=>english()?v:v.split("-").reverse().join("/");el("explorer-date-summary").textContent=a&&b?`${t("Khoảng ngày","Date range")} · ${fmt(a)}–${fmt(b)}`:a||b?t("Khoảng ngày · chưa đủ hai ngày","Date range · enter both dates"):t("Khoảng ngày · tùy chọn","Date range · optional");}
  function setStatus(text,error=false) {el("explorer-status").textContent=text;el("explorer-status").classList.toggle("is-error",error);notify("status");}
  function markDirty(){saveNote();dateSummary();dirty=true;sequenceRun=retrySequence=null;preparedSequence=timelineState=null;toggleFallback(false);stop();noteKey=null;el("explorer-note").value="";for(const id of["explorer-pin","explorer-play","explorer-export"])el(id).disabled=true;notify("dirty");}
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
      if(attempt===0&&[502,504].includes(response.status)){
        await response.json().catch(()=>{});
        if(signal.aborted)throw new DOMException(t("Đã đổi vùng trời","Sky region changed"),"AbortError");
        setStatus(t("IRSA đang chậm hoặc tạm lỗi. Đang thử lại lần 2/2…","IRSA is slow or temporarily unavailable. Retrying (2/2)…"));continue;
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
  function timelineBandMode(indices=null) {
    const source=(indices||[...images.keys()]).map(index=>images.get(index)).filter(Boolean);
    if(!source.length)return "none";
    const measured=source.map(info=>Boolean(spectralSample(info)));
    return measured.every(Boolean)?"wcs":measured.every(value=>!value)?"nominal":"mixed";
  }
  function timelineBandCaveat(indices=null) {
    return timelineBandMode(indices)==="nominal"
      ?t(" WCS-WAVE tại tâm không có trong các FITS này; ảnh chỉ được ghép theo detector danh định, chưa xác nhận đáp ứng phổ chi tiết hay phép đo độ sáng."," WCS-WAVE is unavailable at the center in these FITS files; frames are grouped by nominal detector only, without verified detailed spectral response or photometry.")
      :"";
  }
  function timelineUnavailableReason(indices) {
    const loaded=indices.map(index=>images.get(index)).filter(Boolean);
    if(loaded.some(info=>info.headers?.["x-frame-center-pixel-status"]!=="valid"))
      return t("Ít nhất một ảnh không có pixel hợp lệ tại tâm truy vấn; không thể so cùng điểm trời qua các epoch.","At least one image has no valid pixel at the query center, so the same sky point cannot be compared across epochs.");
    if(loaded.some(info=>!observationTime(info)))
      return t("Ít nhất một FITS không cung cấp MJD UTC hợp lệ.","At least one FITS file lacks a valid UTC MJD.");
    if(timelineBandMode(indices)==="mixed")
      return t("Chuỗi trộn FITS có và không có WCS-WAVE tại tâm; hãy chọn chuỗi khác để tránh ghép dải phổ chưa xác minh.","This sequence mixes FITS files with and without center WCS-WAVE; choose another sequence to avoid unverified spectral mixing.");
    return t("Có khung không cùng release/detector, mask hoặc thang hiển thị.","A frame differs in release, detector, mask policy or display scale.");
  }
  function timelineFrames(indices=null) {
    const requested=indices||preparedSequence?.indices||null,explicit=Boolean(indices||preparedSequence?.indices);
    if(dirty||!range||maskPolicy==="undeclared"||!query)return [];
    const source=requested?requested.map(index=>[index,images.get(index)]):[...images];
    const entries=source.map(([index,info])=>({index,info,time:observationTime(info),band:spectralSample(info)}))
      .filter(({index,info,time})=>{
        const h=info?.headers||{}, low=Number(h["x-frame-contrast-low"]), high=Number(h["x-frame-contrast-high"]);
        return Boolean(info&&time&&h["x-frame-center-pixel-status"]==="valid"&&h["x-frame-release"]===query.release
          &&Number(h["x-frame-detector"])===query.det&&h["x-frame-obs-id"]===info.row.obs_id
          &&info.row.detector===query.det&&info.row.obs_id&&h["x-frame-mask-policy"]===maskPolicy
          &&Number.isFinite(low)&&Number.isFinite(high)&&Math.abs(low-range[0])<1e-7&&Math.abs(high-range[1])<1e-7);
      })
      .sort((a,b)=>a.time.mjd-b.time.mjd||String(a.info.row.obs_id).localeCompare(String(b.info.row.obs_id)));
    const unique=[],seenTimes=new Set(),seenIds=new Set();
    for(const entry of entries){
      const timeKey=entry.time.mjd.toFixed(8),id=entry.info.row.obs_id;
      if(seenTimes.has(timeKey)||seenIds.has(id))continue;
      seenTimes.add(timeKey);seenIds.add(id);unique.push(entry);
    }
    const mode=timelineBandMode(unique.map(entry=>entry.index));
    if(mode==="mixed")return [];
    if(mode==="wcs"){
      if(explicit&&unique.length!==requested.length)return unique.map(entry=>entry.index);
      if(explicit){
        let low=-Infinity,high=Infinity,widest=0;
        for(const {band} of unique){low=Math.max(low,band.low);high=Math.min(high,band.high);widest=Math.max(widest,band.width);}
        if(high-low<.75*widest)return [];
      }else{
        const anchor=unique.find(entry=>entry.index===current)||unique[0];
        if(!anchor)return [];
        const selected=[anchor],times=new Set([anchor.time.mjd.toFixed(8)]),ids=new Set([anchor.info.row.obs_id]);
        let low=anchor.band.low,high=anchor.band.high,widest=anchor.band.width;
        for(const entry of unique){
          if(entry===anchor)continue;
          const nextLow=Math.max(low,entry.band.low),nextHigh=Math.min(high,entry.band.high),nextWidth=Math.max(widest,entry.band.width);
          if(times.has(entry.time.mjd.toFixed(8))||ids.has(entry.info.row.obs_id)||nextHigh-nextLow<.75*nextWidth)continue;
          selected.push(entry);times.add(entry.time.mjd.toFixed(8));ids.add(entry.info.row.obs_id);low=nextLow;high=nextHigh;widest=nextWidth;
        }
        return selected.sort((a,b)=>a.time.mjd-b.time.mjd).map(entry=>entry.index);
      }
    }
    if(explicit&&unique.length!==requested.length)return unique.map(entry=>entry.index);
    return unique.map(entry=>entry.index);
  }
  function timelineControls() {
    if(!timeline)return;
    const requested=preparedSequence?.indices||null;
    const frames=timelineState?.generation===generation?timelineState.frames:timelineFrames(requested), playing=playback==="timeline";
    const loading=Boolean(sequenceRun);
    const complete=requested?frames.length===requested.length:frames.length>=3;
    timeline.disabled=loading||!complete||playback==="pair";
    timeline.setAttribute("aria-busy",String(loading));
    const paused=Boolean(timelineState&&!playing&&timelineState.generation===generation);
    timeline.textContent=playing?t("Tạm dừng chuỗi","Pause sequence"):
      paused?t(`Phát tiếp chuỗi (${frames.length})`,`Resume sequence (${frames.length})`):
      requested?t(`Phát chuỗi (${frames.length})`,`Play sequence (${frames.length})`):
      t(`Phát ${frames.length} ảnh đã mở`,`Play ${frames.length} loaded images`);
    timeline.title=requested?t(`Chuỗi đã chọn gồm ${requested.length} lần quan sát riêng biệt.`,`${requested.length} distinct observations are selected for this sequence.`):
      t("Phát ảnh đã mở cùng detector, pixel tâm hợp lệ, MJD UTC và dải WCS-WAVE tương thích nếu có.","Play loaded images from the same detector with valid center pixels, UTC MJD, and compatible WCS-WAVE ranges when available.");
    const hint=el("explorer-timeline-hint");
    if(hint){
      hint.textContent=loading?t(`Đang tải ảnh ${sequenceRun.position}/${sequenceRun.indices.length} lần lượt từ IRSA.`,`Loading frame ${sequenceRun.position}/${sequenceRun.indices.length} from IRSA, one at a time.`):
        requested&&!complete?t(`${frames.length}/${requested.length} ảnh đạt điều kiện MJD UTC, pixel tâm, mask và thang hiển thị; nếu có WCS-WAVE thì phải tương thích. Không tự bỏ ảnh.`,`${frames.length}/${requested.length} frames pass UTC MJD, center-pixel, mask and display-scale checks; available WCS-WAVE must be compatible. Frames are not silently dropped.`):
        requested&&complete?t(`Chuỗi ${frames.length} ảnh đã qua kiểm tra, phát theo thứ tự MJD trong FITS.${timelineBandCaveat(requested)}`,`The ${frames.length}-image sequence passed checks and plays in FITS MJD order.${timelineBandCaveat(requested)}`):
        frames.length<3?t("Chọn số khung bên dưới rồi chuẩn bị chuỗi; hoặc mở thêm ảnh để phát mọi khung tương thích đã tải.","Choose a frame count below and prepare a sequence, or open more images to play all compatible frames already loaded."):"";
      hint.hidden=!loading&&((requested&&complete)||(!requested&&frames.length>=3));
    }
    sequenceControls();
  }
  function sequenceCandidates() {
    const sorted=rows.map((row,index)=>({index,row,time:Number(row.t_min_mjd)}))
      .filter(({row,time})=>row.detector===query?.det&&row.access_url&&row.obs_id&&Number.isFinite(time)&&time>0)
      .sort((a,b)=>a.time-b.time||String(a.row.obs_id).localeCompare(String(b.row.obs_id))
        ||String(a.row.access_url).localeCompare(String(b.row.access_url))||a.index-b.index);
    const ids=new Set(),times=new Set(),candidates=[];
    for(const item of sorted){
      const timeKey=item.time.toFixed(8);
      if(ids.has(item.row.obs_id)||times.has(timeKey))continue;
      ids.add(item.row.obs_id);times.add(timeKey);candidates.push(item);
    }
    return candidates;
  }
  function sampleSequence(count,candidates=sequenceCandidates()) {
    if(!Number.isInteger(count)||count<2||candidates.length<count)return [];
    if(count===2)return [candidates[0].index,candidates.at(-1).index];
    return Array.from({length:count},(_,position)=>candidates[Math.round(position*(candidates.length-1)/(count-1))].index);
  }
  function sequenceControls(){
    const countControl=el("explorer-sequence-count"),loadButton=el("explorer-sequence-load"),label=el("explorer-sequence-load-label"),summary=el("explorer-sequence-summary");
    if(!countControl||!loadButton||!label||!summary)return;
    const count=Number(countControl.value)||3,candidates=sequenceCandidates(),loading=Boolean(sequenceRun);
    countControl.disabled=dirty||loading||!rows.length;
    label.textContent=t(`Chuẩn bị ${count} khung`,`Prepare ${count} frames`);
    loadButton.disabled=dirty||loading||candidates.length<count;
    if(loading){summary.textContent=t(`Đang tải lần lượt ${sequenceRun.position}/${sequenceRun.indices.length}; ảnh không tương thích sẽ không được phát.`,`Loading serially, ${sequenceRun.position}/${sequenceRun.indices.length}; incompatible frames will not play.`);return;}
    if(dirty){summary.textContent=t("Cấu hình đã đổi. Chạy lại truy vấn để chuẩn bị chuỗi.","Search settings changed. Run the query again to prepare a sequence.");return;}
    if(!rows.length){summary.textContent=t("Chạy truy vấn để chọn 2, 3, 5 hoặc 10 lần quan sát.","Search first, then choose 2, 3, 5 or 10 observations.");return;}
    if(preparedSequence){
      const compatible=timelineFrames(preparedSequence.indices),ready=compatible.length===preparedSequence.indices.length;
      if(ready){
        const omitted=Math.max(0,preparedSequence.sourceCount-preparedSequence.indices.length);
        summary.textContent=preparedSequence.kind==="curated"?t("Ba ảnh Epsilon Indi B đã tải; dùng chuỗi DR1 đã lưu trong provenance.","Three Epsilon Indi B images are loaded from the provenance-backed DR1 sequence."):
          t(`Đã chuẩn bị ${preparedSequence.indices.length} ảnh theo MJD trong FITS${omitted?`; chọn đều từ ${preparedSequence.sourceCount}, bỏ qua ${omitted} ảnh không nạp`:"; đã dùng tất cả kết quả có URL"}${preparedSequence.truncated?"; phản hồi IRSA bị cắt":""}.${timelineBandCaveat(preparedSequence.indices)}`,`Prepared ${preparedSequence.indices.length} images in FITS MJD order${omitted?`; evenly selected from ${preparedSequence.sourceCount}, with ${omitted} not loaded`:"; all results with URLs were used"}${preparedSequence.truncated?"; IRSA response was truncated":""}.${timelineBandCaveat(preparedSequence.indices)}`);
      }else{
        summary.textContent=t(`Chuỗi đang có ${compatible.length}/${preparedSequence.indices.length} ảnh đạt điều kiện. ${timelineUnavailableReason(preparedSequence.indices)} Không phát thiếu khung; thử lại ảnh lỗi hoặc chọn chuỗi khác.`,`The sequence has ${compatible.length}/${preparedSequence.indices.length} frames that pass checks. ${timelineUnavailableReason(preparedSequence.indices)} Playback will not omit frames; retry a failed image or choose another sequence.`);
      }
      return;
    }
    summary.textContent=t(`${candidates.length} thời điểm riêng biệt có URL ảnh; chọn đều theo thời gian. Phản hồi${truncated?" bị cắt":" chưa bị cắt"}.`,`${candidates.length} distinct times have image URLs; selection is evenly spaced. The response${truncated?" was truncated":" was not truncated"}.`);
  }
  function resetDisplay() {
    el("explorer-image").hidden=true;el("explorer-image").removeAttribute("src");
    for(const id of ["explorer-frame-label","explorer-frame-meta","explorer-frame-hash"])el(id).textContent="";
    for(const id of ["explorer-pin","explorer-play","explorer-export","explorer-previous","explorer-next","explorer-current"])el(id).disabled=true;
    el("explorer-current").value="0";el("explorer-current").max="0";
    el("explorer-reference").textContent=t("Giữ một ảnh đối chiếu rồi chọn ảnh ở thời điểm khác.","Pin a reference image and select another observation.");
    el("explorer-download-fits").removeAttribute("href");el("explorer-download-fits").hidden=true;
    el("explorer-display").hidden=true;
    toggleFallback(false);
    timelineControls();
  }

  function toggleFallback(show) {
    for(const link of fallbackLinks)link.hidden=!show;
  }

  function localizeFallback() {
    const url=new URL(location.href);
    for(const key of [...url.searchParams.keys()])url.searchParams.delete(key);
    url.searchParams.set("lang",english()?"en":"vi");
    url.searchParams.set("field","epsilon");
    url.searchParams.set("view","saved");
    url.hash="#night-sky";
    for(const link of fallbackLinks){
      link.textContent=t("Mở chuỗi Epsilon Indi B đã lưu","Open saved Epsilon Indi B sequence");
      link.href=url.href;
    }
  }
  function inputQuery() {
    const ra=coordinate(el("explorer-ra").value,true),dec=coordinate(el("explorer-dec").value,false),fov=Number(el("explorer-fov").value),det=Number(el("explorer-detector").value);
    if(!Number.isFinite(fov)||fov<.02||fov>.12)throw new Error(t("Trường nhìn phải từ 0,02 đến 0,12 độ.","Field of view must be between 0.02 and 0.12 degrees."));
    if(!Number.isInteger(det)||det<1||det>6||!["dr1","qr3"].includes(el("explorer-release").value))throw new Error(t("Chọn detector và bản dữ liệu được hỗ trợ.","Choose a supported detector and data release."));
    const p=new URLSearchParams({ra:ra.toString(),dec:dec.toString(),radius:(fov/2).toString(),release:el("explorer-release").value,detector:det.toString(),maxrec:"300",band_min_um:BANDS[det-1][0].toString(),band_max_um:BANDS[det-1][1].toString()});
    const start=el("explorer-from").value,end=el("explorer-to").value;
    if(Boolean(start)!==Boolean(end))throw new Error(t("Chọn cả ngày bắt đầu và kết thúc, hoặc bỏ trống cả hai.","Enter both dates, or leave both blank."));
    if(start&&end) {
      const a=Date.parse(start+"T00:00:00Z")/86400000+40587,b=Date.parse(end+"T23:59:59Z")/86400000+40587;
      if(!Number.isFinite(a+b)||a>b)throw new Error(t("Khoảng ngày không hợp lệ.","Invalid date range."));
      p.set("time_min_mjd",a.toString());p.set("time_max_mjd",b.toString());
    }
    const release=el("explorer-release").value;
    const sequence=incoming.get("sky_sequence")===epsilonTimeline.id
      && Math.abs(ra-presets.epsilon[0])<1e-8 && Math.abs(dec-presets.epsilon[1])<1e-8
      && fov===.12 && det===6 && release==="dr1" ? epsilonTimeline.id : "";
    return {p,ra,dec,fov,det,release,from:start,to:end,sequence,view:requestedView};
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
      id=setTimeout(()=>{if(done)return;done=true;signal?.removeEventListener?.("abort",abort);resolve();},Math.min(300,Math.max(1,seconds))*1000);
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
          await new Promise(resolve=>setTimeout(resolve,900));
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
    const response=await fetch("/api/observations?"+params,{signal});
    const data=await response.json();
    if(!response.ok)throw new Error(apiError(response,data.error));
    return {rows:data.observations, truncated:Boolean(data.truncated), provenance:data.provenance};
  }
  function draw(info,index,sequencePosition="") {
    const img=el("explorer-image");img.src=info.src;img.hidden=false;
    const list=el("explorer-frames");
    list.children[displayed]?.removeAttribute("aria-current");
    displayed=index;
    list.children[index]?.setAttribute("aria-current","true");
    const time=info.headers["x-frame-time-system"]==="UTC"&&info.headers["x-frame-mjd-obs"]?displayMjd(Number(info.headers["x-frame-mjd-obs"]),"UTC"):displayMjd(info.row.t_min_mjd);
    const release=(info.row.release||query.release).toUpperCase();
    img.alt=t(`Ảnh SPHEREx ${release}, detector ${info.row.detector}, ${time}, ${info.row.obs_id}. Bắc ở trên, Đông bên trái. Cam là pixel bị mask, tím là thiếu dữ liệu.`,`SPHEREx ${release} image, detector ${info.row.detector}, ${time}, ${info.row.obs_id}. North is up and east is left. Orange pixels are masked and purple pixels are missing.`);
    const band=spectralSample(info);
    const wavelength=band?` · λ ${((band.low+band.high)/2).toFixed(3)} µm`:"";
    el("explorer-frame-label").textContent=`${sequencePosition || `${index+1}/${rows.length}`} · ${time}${wavelength} · ${info.row.obs_id}`;
    if(!linkedPair)fillFrameMetadata(info);
    el("explorer-current").value=String(index);el("explorer-pin").disabled=false;el("explorer-export").disabled=false;
  }
  function fillFrameMetadata(info) {
    const release=(info.row.release||query.release).toUpperCase();
    const counts=["x-frame-valid-pixels","x-frame-masked-pixels","x-frame-missing-pixels"].map(key=>info.headers[key]===undefined?null:Number(info.headers[key]));
    const quality=counts.every(v=>Number.isInteger(v)&&v>=0)?t(` ${counts[0]} pixel khả dụng; ${counts[1]} bị loại; ${counts[2]} thiếu.`,` ${counts[0]} valid pixels, ${counts[1]} masked, ${counts[2]} missing.`):"";
    const contrast=range?range.map(x=>x.toFixed(4)).join("–"):t("theo ảnh","per frame");
    const band=spectralSample(info), spectrum=band?` · WCS-WAVE ${((band.low+band.high)/2).toFixed(3)} µm, Δ${band.width.toFixed(3)} µm`:"";
    const center=info.headers["x-frame-center-pixel-status"]||t("chưa rõ pixel tâm","center pixel unknown");
    el("explorer-frame-meta").textContent=t(`${release} · D${info.row.detector} · 6,15″/pixel · ZODI đã trừ · mức xám ${contrast} MJy/sr. Pixel tâm: ${center}. Cam là mask, tím là thiếu dữ liệu.`,`${release} · D${info.row.detector} · 6.15″/pixel · ZODI subtracted · grayscale ${contrast} MJy/sr. Query-center pixel: ${center}. Orange marks masked pixels and purple marks missing data.`)+quality+spectrum;
    const sha=info.headers["x-frame-cutout-sha256"]||"";
    el("explorer-frame-hash").textContent=sha?`SHA-256 cutout: ${sha}`:t("Hash cutout xem trong gói bằng chứng.","See the cutout hash in the evidence bundle.");
    el("explorer-download-fits").href=info.headers["x-frame-cutout-url"];
    el("explorer-download-fits").hidden=false;
  }
  function referenceText() {
    if(context().paired)return t(`Đã chọn ảnh A: ${reference+1} · ảnh B: ${current+1}. Có thể nhấp nháy hoặc sang Kiểm tra.`,`Image A: ${reference+1} · image B: ${current+1}. Blink the pair or inspect it.`);
    if(reference>=0)return t(`Ảnh A: ${reference+1}. Chọn một ảnh khác làm B.`,`Image A: ${reference+1}. Select another frame as B.`);
    return t("Bước 1: Giữ ảnh hiện tại làm A. Bước 2: Chọn ảnh khác làm B.","Pin this frame as A, then select another frame as B.");
  }
  function frameStatus() {
    return context().paired?t("Cặp A/B đã sẵn sàng. Bước sóng tại từng pixel có thể khác nhau.","A/B pair ready. The wavelength sampled at each pixel can differ."):t("Đã tải ảnh. Chọn cặp A/B để so sánh.","Image loaded. Select an A/B pair to compare.");
  }
  function renderResults() {
    el("explorer-count").textContent=t(`${rows.length} quan sát D${query.det} · ${query.release.toUpperCase()}`,`${rows.length} D${query.det} observations · ${query.release.toUpperCase()}`);
    el("explorer-warning").textContent=truncated?t("Kết quả bị cắt tại giới hạn IRSA. Thu hẹp khoảng ngày; danh sách này chưa chứng minh đầy đủ độ phủ.","IRSA truncated the results. Narrow the date range for a more complete view."):t("Danh sách theo truy vấn tại thời điểm hiện tại; archive có thể cập nhật.","Results reflect the current archive. IRSA may add or update observations.");
    renderList();
  }
  async function show(index, curated) {
    if(!rows[index]||!query)return;
    if(dirty){setStatus(t("Cấu hình đã đổi. Tìm lại ảnh để tiếp tục.","Search settings changed. Search for images to continue."),true);return;}
    if(!curated){sequenceRun=retrySequence=null;timelineState=null;}
    saveNote();stop();noteKey=null;el("explorer-note").value="";const seq=generation;current=index;renderList();
    el("explorer-image").hidden=true;for(const id of["explorer-pin","explorer-play","explorer-export"])el(id).disabled=true;
    el("explorer-retry").hidden=true;
    el("explorer-previous").disabled=index===0;el("explorer-next").disabled=index===rows.length-1;
    timelineControls();
    if(timeline)timeline.disabled=true;
    const progress=curated?`${curated.position}/${curated.indices.length}`:`${index+1}/${rows.length}`;
    setStatus(curated?t(`Đang tải ảnh ${progress} trong chuỗi. IRSA có thể mất vài giây…`,`Loading frame ${progress} in the sequence. IRSA can take several seconds…`):
      t(`Đang tải cutout thật ${progress} từ IRSA…`,`Loading IRSA cutout ${progress}…`));
    try {
      const info=await load(index,seq);
      if(seq!==generation||current!==index||(curated&&sequenceRun!==curated))return;
      draw(info,index);restoreNote();
      el("explorer-reference").textContent=referenceText();
      if(!curated)setStatus(frameStatus());
      el("explorer-play").disabled=reference<0||reference===index||!images.has(reference);
      timelineControls();
      notify("frame");
      if(!curated)void prepareTimeline();
      return info;
    }catch(error){if(error.name!=="AbortError"&&seq===generation&&current===index&&(!curated||sequenceRun===curated)){setStatus(t(`Không tải được cutout: ${error.message}. Chọn ảnh khác trong danh sách hoặc bấm Tải lại ảnh.`,`Could not load the cutout: ${error.message}. Select another image or retry.`),true);el("explorer-image").hidden=true;el("explorer-retry").hidden=!rows[index]?.access_url;}}
  }
  async function loadEpsilonTimeline(indices) {
    const run={kind:"curated",indices,position:0};
    preparedSequence={kind:"curated",indices:indices.slice(),sourceCount:indices.length,truncated:false};
    timelineState=null;
    sequenceRun=run;
    retrySequence=null;
    let lastLoaded;
    for(const index of indices){
      if(sequenceRun!==run)return;
      run.position++;
      if(await show(index,run))lastLoaded=index;
      else break;
    }
    if(sequenceRun!==run)return;
    sequenceRun=null;
    if(lastLoaded!==undefined&&current!==lastLoaded)await show(lastLoaded);
    if(!workspaceActive())return;
    timelineControls();
    if(timelineFrames(indices).length===indices.length){
      toggleFallback(false);
      setStatus(t("Ba ảnh Epsilon Indi B đã sẵn sàng. Chọn Phát chuỗi để xem theo thời gian.","Three Epsilon Indi B images are ready. Select Play timeline to see them in time order."));
    } else {
      toggleFallback(true);
      if(indices.some(index=>!images.has(index))){
        retrySequence={kind:"curated",indices:indices.slice(),sourceCount:indices.length,truncated:false};
        el("explorer-retry").hidden=false;
        setStatus(t("Chưa tải đủ ba ảnh. Bấm Tải lại ảnh để thử các khung còn thiếu hoặc chọn ảnh khác trong danh sách.","The sequence is incomplete. Choose Retry image to load the remaining frames or select another frame from the list."),true);
      } else {
        setStatus(t("Ba ảnh đã tải nhưng chưa đủ điều kiện phổ và pixel tâm để phát chuỗi. Hãy chọn ảnh khác trong danh sách.","All three images loaded, but their spectral bands or center pixels do not meet the timeline criteria. Select another image from the list."),true);
      }
    }
  }

  function spacedCandidates() {
    const candidates=sequenceCandidates();
    if(candidates.length<=maxTimelineCandidates)return candidates.map(item=>item.index);
    const selected=[candidates[0].index,candidates.at(-1).index],occupied=new Set(selected);
    const start=candidates[0].time,end=candidates.at(-1).time;
    for(let i=1;i<maxTimelineCandidates-1;i++){
      const target=start+(end-start)*i/(maxTimelineCandidates-1);
      const nearest=candidates.reduce((best,item)=>!occupied.has(item.index)&&
        (!best||Math.abs(item.time-target)<Math.abs(best.time-target))?item:best,null);
      if(nearest){selected.push(nearest.index);occupied.add(nearest.index);}
    }
    return selected;
  }

  async function prepareTimeline() {
    if(automaticTimelineAttempted||sequenceRun||preparedSequence||query?.sequence||query?.view!=="timeline"||!images.has(current)||timelineFrames().length>=3)return;
    automaticTimelineAttempted=true;
    const candidates=spacedCandidates();
    const pending=candidates.filter(index=>!images.has(index)).slice(0,maxTimelineCandidates-1);
    if(!pending.length)return;
    const run={automatic:true,indices:candidates,position:candidates.filter(index=>images.has(index)).length,total:candidates.length};
    const active=()=>sequenceRun===run&&workspaceActive()&&!dirty&&query?.view==="timeline";
    const seq=generation;
    sequenceRun=run;
    timelineControls();
    for(const index of pending){
      if(!active()||timelineFrames().length>=3)break;
      const stillNeeded=()=>active()||seq===generation&&current===index;
      try{await load(index,seq,stillNeeded,true);}catch(error){if(error.name==="AbortError")break;}
      if(!active())break;
      run.position++;
      timelineControls();
      if(el("explorer-frames").children[index]&&images.has(index))el("explorer-frames").children[index].dataset.loaded="true";
    }
    if(sequenceRun!==run)return;
    sequenceRun=null;
    if(!workspaceActive()||dirty||query?.view!=="timeline")return;
    if(timelineFrames().length<3){
      const compatible=[...images.keys()].find(index=>images.has(index));
      if(compatible!==undefined&&current!==compatible)await show(compatible);
    }
    timelineControls();
    if(timelineFrames().length>=3){
      setStatus(t("Chuỗi đã sẵn sàng. Nhấn Phát để xem các lần quan sát theo thời gian.","Timeline is ready. Select Play to view the observations in chronological order."));
    } else {
      setStatus(t("Chưa đủ ba ảnh tương thích. Chọn thêm lần quan sát trong danh sách để thử.","Fewer than three compatible images are open. Select more observations from the list to try again."));
    }
  }
  async function loadUserSequence(retry=null) {
    if(dirty||!query||sequenceRun)return;
    stop();
    const candidates=sequenceCandidates(),count=Number(el("explorer-sequence-count").value)||3;
    const indices=retry?.indices||sampleSequence(count,candidates);
    const sourceCount=retry?.sourceCount??candidates.length,wasTruncated=retry?.truncated??truncated;
    if(!retry&&indices.length!==count){
      setStatus(t(`Chưa đủ ${count} thời điểm riêng biệt có URL ảnh. Hãy thu hẹp khoảng ngày hoặc chọn ít khung hơn.`,`There are not ${count} distinct observations with image URLs. Narrow the date range or choose fewer frames.`),true);
      return;
    }
    preparedSequence={kind:"user",indices:indices.slice(),sourceCount,truncated:wasTruncated};
    timelineState=null;
    const run={kind:"user",indices:indices.slice(),position:0,sourceCount,truncated:wasTruncated};
    sequenceRun=run;retrySequence=null;timelineControls();
    let lastLoaded;
    for(const [position,index] of indices.entries()){
      if(sequenceRun!==run)return;
      run.position=position+1;
      if(await show(index,run))lastLoaded=index;else break;
    }
    if(sequenceRun!==run)return;
    sequenceRun=null;
    if(lastLoaded!==undefined&&current!==lastLoaded)await show(lastLoaded);
    if(!workspaceActive())return;
    const frames=timelineFrames(indices);
    if(frames.length!==indices.length&&indices.some(index=>!images.has(index))){
      retrySequence={indices:indices.slice(),sourceCount,truncated:wasTruncated};
      el("explorer-retry").hidden=false;
      setStatus(t("Chuỗi chưa tải đủ ảnh. Bấm Tải lại ảnh để thử lại từ khung còn thiếu.","The sequence did not finish loading. Retry the failed frame to continue."),true);
    }else if(frames.length!==indices.length){
      setStatus(t(`Đã tải ${indices.length} ảnh, nhưng chuỗi chưa qua kiểm tra. ${timelineUnavailableReason(indices)}`,`Loaded ${indices.length} images, but the sequence did not pass validation. ${timelineUnavailableReason(indices)}`),true);
    }else{
      setStatus(t(`Đã chuẩn bị đủ ${frames.length} ảnh thật từ IRSA theo thời gian. Chọn Phát chuỗi để xem.${timelineBandCaveat(indices)}`,`Prepared ${frames.length} real IRSA images in time order. Select Play sequence to view them.${timelineBandCaveat(indices)}`));
    }
    timelineControls();
  }
  el("explorer-form").addEventListener("submit",async event=>{
    event.preventDefault();let next;try{next=inputQuery();}catch(error){setStatus(error.message,true);return;}
    saveNote();noteKey=null;el("explorer-note").value="";request?.abort();sequenceRun=retrySequence=null;preparedSequence=timelineState=null;automaticTimelineAttempted=false;stop();generation++;const seq=generation;request=new AbortController();clearImages();query=next;dirty=false;range=null;maskPolicy=null;rows=[];current=displayed=reference=-1;provenance=null;frameQueue=Promise.resolve();pendingFrames=new Map();
    resetDisplay();el("explorer-results").hidden=true;el("explorer-search").disabled=true;
    setStatus(t("Đang truy vấn độ phủ SPHEREx tại IRSA…","Searching SPHEREx coverage at IRSA…"));
    try {
      const response=await fetchObservations(`/api/observations?${query.p}`,request.signal);const data=await response.json();if(!response.ok)throw new Error(apiError(response,data.error));if(seq!==generation)return;
      if(!searchActive()||dirty)return;
      rows=data.observations.slice().sort((a,b)=>(a.t_min_mjd??Infinity)-(b.t_min_mjd??Infinity));provenance=data.provenance;truncated=Boolean(data.truncated);
      el("explorer-results").hidden=false;
      el("explorer-display").hidden=!rows.length;el("explorer-current").disabled=!rows.length;
      el("explorer-upstream").href=provenance.query_url;el("explorer-current").max=String(Math.max(0,rows.length-1));renderResults();
      const share=new URL(location.href);for(const key of [...share.searchParams.keys()])if(key.startsWith("sky_"))share.searchParams.delete(key);
      for(const key of ["ra","dec","fov","det","release","from","to","sequence","view"])if(query[key]!=="")share.searchParams.set(`sky_${key}`,String(query[key]));
      history.replaceState(null,"",share);
      notify("results");const first=rows.findIndex(row=>row.access_url);
      if(query.sequence&&timeline){
        const indices=epsilonTimeline.observations.map(id=>rows.findIndex(row=>row.obs_id===id&&row.detector===6&&row.access_url));
        if(indices.every(index=>index>=0)){await loadEpsilonTimeline(indices);return;}
        toggleFallback(true);
      }
      if(first>=0)await show(first);else setStatus(rows.length?t("Danh sách không có URL ảnh hỗ trợ. Quay lại Dữ liệu để đổi truy vấn.","These results have no supported image URLs. Return to Data to change the search."):data.truncated?t("Chưa thấy detector đã chọn trong phần kết quả bị cắt. Hãy thu hẹp truy vấn.","The selected detector did not appear in this truncated result. Narrow the search."):t("Không có quan sát phù hợp. Đổi release hoặc khoảng ngày rồi tìm lại.","No matching observations. Try a different release or date range."));
    }catch(error){
      if(error.name!=="AbortError"&&seq===generation&&searchActive()){
        toggleFallback(Boolean(query.sequence));
        setStatus(t(`Truy vấn chưa thành công: ${error.message}. Bấm tìm lại hoặc chọn Bộ mẫu WISE 0855.`,`Search failed: ${error.message}. Try again or choose the WISE 0855 sample.`),true);
      }
    }
    finally{if(seq===generation)el("explorer-search").disabled=false;}
  });
  el("explorer-preset").addEventListener("change",()=>{const id=el("explorer-preset").value,p=presets[id];if(p){el("explorer-ra").value=p[0].toString();el("explorer-dec").value=p[1].toString();el("explorer-fov").value=id==="epsilon"?"0.12":"0.06";}markDirty();});
  el("explorer-previous").addEventListener("click",()=>show(current-1));el("explorer-next").addEventListener("click",()=>show(current+1));
  el("explorer-current").addEventListener("change",()=>show(Number(el("explorer-current").value)));
  el("explorer-retry").addEventListener("click",()=>retrySequence?.kind==="curated"?loadEpsilonTimeline(retrySequence.indices):retrySequence?loadUserSequence(retrySequence):show(current));
  el("explorer-sequence-count")?.addEventListener("change",()=>{stop();preparedSequence=timelineState=null;timelineControls();});
  el("explorer-sequence-load")?.addEventListener("click",()=>loadUserSequence());
  el("explorer-pin").addEventListener("click",()=>{saveNote();stop();if(!context().ready)return;reference=displayed;restoreNote();renderList();el("explorer-reference").textContent=referenceText();el("explorer-play").disabled=true;el("explorer-export").disabled=true;notify("pin");});
  el("explorer-play").addEventListener("click",()=>{
    if(timer){stop();return;}if(dirty||reference<0||reference===current||!images.has(reference)||!images.has(current))return;
    const a=reference,b=current;let index=a;draw(images.get(index),index);el("explorer-play").textContent=t("Dừng phát","Pause");
    playback="pair";
    timelineControls();
    timer=setInterval(()=>{index=index===a?b:a;draw(images.get(index),index);},800);
  });
  timeline?.addEventListener("click",()=>{
    if(timer){
      const pausedIndex=timelineState?.generation===generation?timelineState.frames[timelineState.index]:displayed;
      stop();
      if(pausedIndex>=0&&images.has(pausedIndex)){
        current=pausedIndex;renderList();draw(images.get(pausedIndex),pausedIndex,`${timelineState.index+1}/${timelineState.frames.length}`);
        el("explorer-previous").disabled=pausedIndex===0;el("explorer-next").disabled=pausedIndex===rows.length-1;
        timelineControls();notify("frame");
        setStatus(t(`Đã tạm dừng ở ảnh ${timelineState.index+1}/${timelineState.frames.length}. Chọn Phát tiếp để tiếp tục theo thời gian.`,`Paused at image ${timelineState.index+1}/${timelineState.frames.length}. Select Resume to continue in time order.`));
      }
      return;
    }
    const requested=preparedSequence?.indices||null;
    const frames=timelineFrames(requested), complete=requested?frames.length===requested.length:frames.length>=3;
    if(!complete)return;
    const resume=timelineState?.generation===generation&&timelineState.frames.length===frames.length;
    const state=resume?timelineState:{generation,frames,index:0};
    timelineState=state;playback="timeline";let index=state.index;
    const showPlayingFrame=()=>draw(images.get(frames[index]),frames[index],`${index+1}/${frames.length}`);
    showPlayingFrame();
    timer=setInterval(()=>{
      index=(index+1)%frames.length;
      state.index=index;
      showPlayingFrame();
    },950);
    timelineControls();
    setStatus(t(`Đang phát ảnh theo thời gian với cùng thang hiển thị.${timelineBandCaveat(frames)} Chưa xác nhận chuyển động hay biến quang.`,`Playing images in time order with a shared display scale.${timelineBandCaveat(frames)} Motion and variability are unconfirmed.`));
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
    localizeFallback();
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
    initialMode:requestedView, onModeChange(view){
      requestedView=view;
      if(query)query.view=view;
      if(view==="compare"&&sequenceRun?.automatic){
        sequenceRun=null;
        timelineControls();
        setStatus(frameStatus());
      }
      const share=new URL(location.href);
      share.searchParams.set("sky_view",view);
      history.replaceState(history.state,"",share);
      if(view==="timeline")void prepareTimeline();
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
  syncPreset();dateSummary();timelineControls();localizeFallback();
  if(legacyRelease)setStatus(t("Liên kết QR2 cũ. Chọn Tìm ảnh để tra DR1 đã xử lý lại.","This is a legacy QR2 link. Search to use the reprocessed DR1 release."));
  if(!legacyRelease&&(incoming.get("sky_autoload")==="1"||incoming.get("sky_sequence")===epsilonTimeline.id)
      &&["#explore","#compare-step"].includes(location.hash)&&incoming.has("sky_ra")&&incoming.has("sky_dec")){
    let attempted=false;
    const autoload=()=>{
      if(attempted||!window.SkyWorkflow||!["#explore","#compare-step"].includes(location.hash))return;
      attempted=true;
      try {
        const next=inputQuery();
        if(incoming.get("sky_autoload")!=="1"&&!next.sequence)return;
      }
      catch(error){setStatus(error.message,true);return;}
      el("explorer-form").requestSubmit();
    };
    document.addEventListener("spherex:workspace-ready",autoload,{once:true});
    requestAnimationFrame(autoload);
  }
})();

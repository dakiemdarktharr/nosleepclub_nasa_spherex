"use strict";
// Discovery and display use public IRSA observations; no motion fit is performed.
(() => {
  const el = id => document.getElementById(id), BANDS = [[.75,1.09],[1.10,1.62],[1.63,2.41],[2.42,3.82],[3.83,4.41],[4.42,5.00]];
  const presets = {
    wise0855:[133.7601213914074,-7.242127941212259], barnard:[269.44626688537255,4.768222216475269],
    epsilon:[331.04583333,-56.78333333], rwaur:[76.95652603458332,30.401438173888888], rdra:[248.16761083294998,66.75497941722]
  };
  let rows=[], query=null, provenance=null, current=-1, displayed=-1, reference=-1, generation=0, request=null, timer=null, range=null, maskPolicy=null;
  let frameQueue=Promise.resolve(), pendingFrames=new Map();
  const images=new Map();
  function coordinate(raw, ra) {
    const text=raw.trim().replace(/−/g,"-");if(!text)throw new Error("Nhập cả RA và Dec.");
    if(/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text)) {
      const n=Number(text);if(!Number.isFinite(n)||(ra?(n<0||n>=360):(n< -90||n>90)))throw new Error(ra?"RA phải từ 0 đến dưới 360 độ.":"Dec phải từ −90 đến +90 độ.");return n;
    }
    const parts=text.replace(/[hHdD°mM′'sS″"]/g," ").trim().split(/[:\s]+/);
    if(parts.length!==3||!/^[-+]?\d+$/.test(parts[0])||!parts.slice(1).every(v=>/^\d+(?:\.\d*)?$/.test(v)))throw new Error("Dùng độ thập phân hoặc ba phần giờ/phút/giây (RA), độ/phút/giây (Dec).");
    const [a,b,c]=parts.map(Number), negative=text.startsWith("-"), value=(Math.abs(a)+b/60+c/3600)*(negative?-1:1)*(ra&&!/[dD°]/.test(text)?15:1);
    if(b>=60||c>=60||!Number.isFinite(value)||(ra?(negative||value>=360):Math.abs(value)>90))throw new Error("Tọa độ ngoài phạm vi hoặc phút/giây không hợp lệ.");
    return value;
  }
  const displayMjd=v=>Number.isFinite(v)?`MJD ${v.toFixed(5)}`:"Không có MJD";
  function stop() {if(timer){clearInterval(timer);current=displayed;renderList();el("explorer-previous").disabled=current===0;el("explorer-next").disabled=current===rows.length-1;}timer=null;el("explorer-play").textContent="Phát 2 ảnh đã tải";}
  function setStatus(text,error=false) {el("explorer-status").textContent=text;el("explorer-status").classList.toggle("is-error",error);}
  function apiError(response,code) {
    if(response.status===429){const retry=response.headers?.get("Retry-After");return `Đã đạt giới hạn tạm thời${retry&&/^\d{1,5}$/.test(retry)?`. Thử lại sau ${retry} giây`:". Hãy thử lại sau"}`;}
    if(code==="upstream_timeout")return "IRSA phản hồi quá chậm";
    if(response.status===503)return "Dịch vụ tạm chưa sẵn sàng";
    if(response.status===502)return "Chưa đọc được dữ liệu nguồn từ IRSA";
    return `Máy chủ chưa xử lý được yêu cầu (HTTP ${response.status})`;
  }
  async function fetchObservations(url,signal) {
    for(let attempt=0;attempt<2;attempt++){
      if(signal.aborted)throw new DOMException("Đã đổi vùng trời","AbortError");
      const response=await fetch(url,{signal});
      if(attempt===0&&[502,504].includes(response.status)){
        await response.json().catch(()=>{});
        if(signal.aborted)throw new DOMException("Đã đổi vùng trời","AbortError");
        setStatus("IRSA đang chậm hoặc tạm lỗi. Đang thử lại lần 2/2…");continue;
      }
      return response;
    }
  }
  function clearImages() {for(const item of images.values())URL.revokeObjectURL(item.src);images.clear();}
  function resetDisplay() {
    el("explorer-image").hidden=true;el("explorer-image").removeAttribute("src");
    for(const id of ["explorer-frame-label","explorer-frame-meta","explorer-frame-hash"])el(id).textContent="";
    for(const id of ["explorer-pin","explorer-play","explorer-export","explorer-previous","explorer-next","explorer-current"])el(id).disabled=true;
    el("explorer-current").value="0";el("explorer-current").max="0";
    el("explorer-reference").textContent="Giữ một ảnh đối chiếu rồi chọn ảnh ở thời điểm khác.";
    el("explorer-download-fits").removeAttribute("href");el("explorer-download-fits").hidden=true;
    el("explorer-display").hidden=true;
  }
  function inputQuery() {
    const ra=coordinate(el("explorer-ra").value,true),dec=coordinate(el("explorer-dec").value,false),fov=Number(el("explorer-fov").value),det=Number(el("explorer-detector").value);
    if(!Number.isFinite(fov)||fov<.02||fov>.12)throw new Error("Trường nhìn phải từ 0,02 đến 0,12 độ.");
    if(!Number.isInteger(det)||det<1||det>6||!["qr2","qr3"].includes(el("explorer-release").value))throw new Error("Chọn detector và bản dữ liệu được hỗ trợ.");
    const p=new URLSearchParams({ra:ra.toString(),dec:dec.toString(),radius:(fov/2).toString(),release:el("explorer-release").value,detector:det.toString(),maxrec:"300",band_min_um:BANDS[det-1][0].toString(),band_max_um:BANDS[det-1][1].toString()});
    const start=el("explorer-from").value,end=el("explorer-to").value;
    if(Boolean(start)!==Boolean(end))throw new Error("Chọn cả ngày bắt đầu và kết thúc, hoặc bỏ trống cả hai.");
    if(start&&end) {
      const a=Date.parse(start+"T00:00:00Z")/86400000+40587,b=Date.parse(end+"T23:59:59Z")/86400000+40587;
      if(!Number.isFinite(a+b)||a>b)throw new Error("Khoảng ngày không hợp lệ.");
      p.set("time_min_mjd",a.toString());p.set("time_max_mjd",b.toString());
    }
    return {p,ra,dec,fov,det,release:el("explorer-release").value};
  }
  function renderList() {
    const root=el("explorer-frames");root.replaceChildren();
    rows.forEach((row,index)=>{
      const button=document.createElement("button"),title=document.createElement("strong"),detail=document.createElement("span");
      button.type="button";button.setAttribute("aria-pressed",String(index===current));button.disabled=!row.access_url;
      title.textContent=`${index+1}. ${displayMjd(row.t_min_mjd)}`;detail.textContent=`D${row.detector??"?"} · ${row.obs_id||"Không có obs ID"}`;
      button.append(title,detail);button.addEventListener("click",()=>show(index));root.append(button);
    });
  }
  function load(index,seq) {
    if(images.has(index))return images.get(index);
    if(pendingFrames.has(index))return pendingFrames.get(index);
    const row=rows[index];if(!row?.access_url)throw new Error("Quan sát không có URL FITS được hỗ trợ.");
    const previous=frameQueue,jobs=pendingFrames,search=query,signal=request.signal;
    const task=(async()=>{
      await previous.catch(()=>{});
      if(seq!==generation||current!==index)throw new DOMException("Đã đổi ảnh hoặc vùng trời","AbortError");
      const p=new URLSearchParams({url:row.access_url,ra:search.ra.toString(),dec:search.dec.toString(),fov_deg:search.fov.toString(),zodi:"subtract"});
      if(range){p.set("low",range[0].toString());p.set("high",range[1].toString());}
      const response=await fetch(`/api/frame?${p}`,{signal});
      if(!response.ok){let error;try{error=(await response.json()).error;}catch{}throw new Error(apiError(response,error));}
      if(!response.headers.get("Content-Type")?.startsWith("image/png"))throw new Error("Máy chủ chưa cung cấp ảnh PNG.");
      const blob=await response.blob();if(seq!==generation)throw new DOMException("Đã đổi vùng trời","AbortError");
      const info={src:URL.createObjectURL(blob),headers:Object.fromEntries([...response.headers].filter(([key])=>key.startsWith("x-frame-"))),row};
      const incomingPolicy=response.headers.get("X-Frame-Mask-Policy")||"undeclared";
      if(maskPolicy!==null&&incomingPolicy!==maskPolicy){URL.revokeObjectURL(info.src);throw new Error("Hai ảnh dùng quy tắc loại pixel khác nhau. Hãy tìm lại vùng trời trước khi so sánh.");}
      const low=Number(response.headers.get("X-Frame-Contrast-Low")),high=Number(response.headers.get("X-Frame-Contrast-High"));
      const valid=Number(response.headers.get("X-Frame-Valid-Pixels"));
      if(valid>0){
        if(!Number.isFinite(low+high)||low>=high){URL.revokeObjectURL(info.src);throw new Error("Thang tương phản của ảnh không hợp lệ.");}
        if(range&&(Math.abs(low-range[0])>1e-9||Math.abs(high-range[1])>1e-9)){URL.revokeObjectURL(info.src);throw new Error("Ảnh không cùng thang tương phản với ảnh đối chiếu.");}
        if(!range)range=[low,high];
      }
      if(maskPolicy===null)maskPolicy=incomingPolicy;
      images.set(index,info);return info;
    })();
    jobs.set(index,task);frameQueue=task.catch(()=>{});task.then(()=>jobs.delete(index),()=>jobs.delete(index));return task;
  }
  function draw(info,index) {
    const img=el("explorer-image");img.src=info.src;img.hidden=false;
    displayed=index;
    img.alt=`Ảnh SPHEREx ${query.release.toUpperCase()}, detector ${info.row.detector}, ${displayMjd(info.row.t_min_mjd)}, ${info.row.obs_id}. Bắc ở trên, Đông bên trái. Cam là pixel bị mask, tím là thiếu dữ liệu.`;
    el("explorer-frame-label").textContent=`${index+1}/${rows.length} · ${displayMjd(info.row.t_min_mjd)} · ${info.row.obs_id}`;
    const counts=["x-frame-valid-pixels","x-frame-masked-pixels","x-frame-missing-pixels"].map(key=>info.headers[key]===undefined?null:Number(info.headers[key]));
    const quality=counts.every(v=>Number.isInteger(v)&&v>=0)?` ${counts[0]} pixel khả dụng; ${counts[1]} bị loại; ${counts[2]} thiếu.`:"";
    el("explorer-frame-meta").textContent=`${query.release.toUpperCase()} · D${info.row.detector} · 6,15″/pixel · ZODI đã trừ · mức xám ${range?range.map(x=>x.toFixed(4)).join("–"):"theo ảnh"} MJy/sr. Cam: mask; tím: thiếu dữ liệu.${quality}`;
    const sha=info.headers["x-frame-cutout-sha256"]||"";
    el("explorer-frame-hash").textContent=sha?`SHA-256 cutout: ${sha}`:"Hash cutout xem trong gói bằng chứng.";
    el("explorer-download-fits").href=info.headers["x-frame-cutout-url"];
    el("explorer-download-fits").hidden=false;
    el("explorer-current").value=String(index);el("explorer-pin").disabled=false;el("explorer-export").disabled=false;
  }
  async function show(index) {
    if(!rows[index]||!query)return;stop();const seq=generation;current=index;renderList();
    el("explorer-previous").disabled=index===0;el("explorer-next").disabled=index===rows.length-1;
    setStatus(`Đang tải cutout thật ${index+1}/${rows.length} từ IRSA…`);
    try {
      const info=await load(index,seq);if(seq!==generation||current!==index)return;draw(info,index);
      setStatus("Đã tải ảnh. So vị trí với các sao xung quanh; các exposure có thể khác bước sóng tại từng pixel.");
      el("explorer-play").disabled=reference<0||reference===index||!images.has(reference);
    }catch(error){if(error.name!=="AbortError"&&seq===generation&&current===index){setStatus(`Không tải được cutout: ${error.message}. Có thể chọn ảnh khác hoặc thử lại.`,true);el("explorer-image").hidden=true;}}
  }
  el("explorer-form").addEventListener("submit",async event=>{
    event.preventDefault();let next;try{next=inputQuery();}catch(error){setStatus(error.message,true);return;}
    request?.abort();stop();generation++;const seq=generation;request=new AbortController();clearImages();query=next;range=null;maskPolicy=null;rows=[];current=displayed=reference=-1;provenance=null;frameQueue=Promise.resolve();pendingFrames=new Map();
    resetDisplay();el("explorer-results").hidden=true;el("explorer-search").disabled=true;
    setStatus("Đang truy vấn độ phủ SPHEREx tại IRSA…");
    try {
      const response=await fetchObservations(`/api/observations?${query.p}`,request.signal);const data=await response.json();if(!response.ok)throw new Error(apiError(response,data.error));if(seq!==generation)return;
      rows=data.observations.slice().sort((a,b)=>(a.t_min_mjd??Infinity)-(b.t_min_mjd??Infinity));provenance=data.provenance;
      el("explorer-results").hidden=false;el("explorer-count").textContent=`${rows.length} quan sát D${query.det} · ${query.release.toUpperCase()}`;
      el("explorer-display").hidden=!rows.length;el("explorer-current").disabled=!rows.length;
      el("explorer-warning").textContent=data.truncated?"Kết quả bị cắt tại giới hạn IRSA. Thu hẹp khoảng ngày; danh sách này chưa chứng minh đầy đủ độ phủ.":"Danh sách theo truy vấn tại thời điểm hiện tại; archive có thể cập nhật.";
      el("explorer-upstream").href=provenance.query_url;el("explorer-current").max=String(Math.max(0,rows.length-1));renderList();
      const share=new URL(location.href);for(const key of [...share.searchParams.keys()])if(key.startsWith("sky_"))share.searchParams.delete(key);
      for(const key of ["ra","dec","fov","det","release"])share.searchParams.set(`sky_${key}`,String(query[key]));share.hash="explore";history.replaceState(null,"",share);
      if(rows.length)await show(0);else setStatus(data.truncated?"Chưa thấy detector đã chọn trong phần kết quả bị cắt. Hãy thu hẹp truy vấn.":"Không có quan sát phù hợp trong truy vấn này. Có thể thử release hoặc khoảng ngày khác.");
    }catch(error){if(error.name!=="AbortError"&&seq===generation)setStatus(`Truy vấn chưa thành công: ${error.message}. Bản demo WISE phía dưới vẫn mở được.`,true);}
    finally{if(seq===generation)el("explorer-search").disabled=false;}
  });
  el("explorer-preset").addEventListener("change",()=>{const id=el("explorer-preset").value,p=presets[id];if(p){el("explorer-ra").value=p[0].toString();el("explorer-dec").value=p[1].toString();if(id==="epsilon")el("explorer-fov").value="0.12";}});
  el("explorer-previous").addEventListener("click",()=>show(current-1));el("explorer-next").addEventListener("click",()=>show(current+1));
  el("explorer-current").addEventListener("change",()=>show(Number(el("explorer-current").value)));
  el("explorer-pin").addEventListener("click",()=>{stop();reference=displayed;el("explorer-reference").textContent=`Ảnh đối chiếu: ${reference+1}. Chọn một ảnh khác rồi bấm Phát.`;el("explorer-play").disabled=true;});
  el("explorer-play").addEventListener("click",()=>{
    if(timer){stop();return;}if(reference<0||reference===current||!images.has(reference)||!images.has(current))return;
    const a=reference,b=current;let index=a;draw(images.get(index),index);el("explorer-play").textContent="Dừng phát";
    timer=setInterval(()=>{index=index===a?b:a;draw(images.get(index),index);},800);
  });
  el("explorer-export").addEventListener("click",()=>{
    const bundle={schema_version:1,kind:"observation-display-evidence",exported_at:new Date().toISOString(),query:{...query,p:query.p.toString()},provenance,
      observations:rows,display_range_mjy_sr:range,mask_policy:maskPolicy,loaded_frames:[...images].map(([index,info])=>({index,...info.row,headers:info.headers})),
      review_note:el("explorer-note").value,qualification:"User visual inspection; no registered astrometry, spectral matching, calibrated detection probability or fitted motion. Pixel wavelengths require science calibration."};
    const url=URL.createObjectURL(new Blob([JSON.stringify(bundle,null,2)],{type:"application/json"})),a=document.createElement("a");a.href=url;a.download="spherex-observation-review.json";a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  document.addEventListener("visibilitychange",()=>{if(document.hidden)stop();});
  const incoming=new URLSearchParams(location.search);
  for(const [name,id] of [["ra","explorer-ra"],["dec","explorer-dec"],["fov","explorer-fov"],["det","explorer-detector"],["release","explorer-release"]])if(incoming.has(`sky_${name}`))el(id).value=incoming.get(`sky_${name}`);
  function syncPreset() {
    let selected="custom";
    try {
      const ra=coordinate(el("explorer-ra").value,true),dec=coordinate(el("explorer-dec").value,false);
      selected=Object.keys(presets).find(id=>Math.abs(presets[id][0]-ra)<1e-8&&Math.abs(presets[id][1]-dec)<1e-8)||"custom";
    }catch{}
    el("explorer-preset").value=selected;
  }
  for(const id of ["explorer-ra","explorer-dec"])el(id).addEventListener("input",syncPreset);
  syncPreset();
})();

"use strict";
/* Bounded public chunks, verified before making a downloadable Blob. No secrets. */
(()=>{
  const el=id=>document.getElementById(id),path=new URLSearchParams(location.search).get("path");
  let saved;try{saved=localStorage.getItem("spherex.language");}catch{}
  const requested=new URLSearchParams(location.search).get("lang"),language=["en","vi"].includes(requested)?requested:saved==="en"?"en":"vi";
  const t=(vi,en)=>language==="en"?en:vi;
  document.documentElement.lang=language;document.title=t("Tải dữ liệu · SPHEREx đã thấy gì?","Download data · What Did SPHEREx See?");
  for(const node of document.querySelectorAll("[data-en]"))if(language==="en")node.textContent=node.dataset.en;
  el("download-progress").setAttribute("aria-label",t("Tiến độ tải dữ liệu","Data download progress"));
  el("download-back").href=`/?lang=${language}#research`;
  el("download-language").textContent=t("English","Tiếng Việt");
  el("download-language").addEventListener("click",()=>{
    const url=new URL(location.href);url.searchParams.set("lang",language==="en"?"vi":"en");location.assign(url);
  });
  let controller=null,url=null;
  const hash=async buffer=>[...new Uint8Array(await crypto.subtle.digest("SHA-256",buffer))].map(x=>x.toString(16).padStart(2,"0")).join("");
  const names={"data/source-presence/records.json.gz":t("Nhận nguồn · 7.992 lượt","Source presence · 7,992 trials"), "data/reference-stars/records.json.gz":t("Sao tham chiếu · 840 bản ghi","Reference stars · 840 records"), "data/signal-controls/records.json.gz":t("Đối chứng tín hiệu · 640 lượt","Signal controls · 640 trials")};
  el("download-name").textContent=names[path]||path||t("Chưa chọn tệp","No file selected");
  el("download-start").disabled=!path;
  el("download-cancel").addEventListener("click",()=>controller?.abort());
  el("download-start").addEventListener("click",async()=>{
    controller=new AbortController();el("download-start").disabled=true;el("download-cancel").disabled=false;
    el("download-save").hidden=true;if(url)URL.revokeObjectURL(url);url=null;
    try{
      const base=new URLSearchParams({path}),version=new URLSearchParams(location.search).get("v");if(version)base.set("v",version);
      const response=await fetch(`/api/data?${base}&meta=1`,{signal:controller.signal});
      if(!response.ok)throw new Error(t(`Không đọc được thông tin tệp (HTTP ${response.status})`,`Could not read file metadata (HTTP ${response.status})`));
      const meta=await response.json();
      if(meta.encoding!=="identity"||meta.stored_bytes>160*1024*1024||!meta.chunks?.length||meta.chunks.length>160)throw new Error(t("Tệp chưa hỗ trợ tải theo phần.","This file does not support chunked download."));
      base.set("v",meta.stored_sha256);const parts=[];let size=0;el("download-progress").max=meta.stored_bytes;
      for(let i=0;i<meta.chunks.length;i++){
        base.set("chunk",String(i));el("download-status").textContent=t(`Đang tải phần ${i+1}/${meta.chunks.length}…`,`Downloading chunk ${i+1}/${meta.chunks.length}…`);
        const r=await fetch(`/api/data?${base}`,{signal:controller.signal});if(!r.ok)throw new Error(t(`Tải chưa hoàn tất (HTTP ${r.status}). Bấm tải lại để thử lại.`,`Download incomplete (HTTP ${r.status}). Start the download again to retry.`));
        const bytes=await r.arrayBuffer();if(bytes.byteLength!==meta.chunks[i].bytes||await hash(bytes)!==meta.chunks[i].sha256)throw new Error(t("Hash phần tải không khớp; chưa tạo tệp.","Chunk hash mismatch; no file was created."));
        parts.push(bytes);size+=bytes.byteLength;el("download-progress").value=size;
      }
      const blob=new Blob(parts,{type:meta.content_type});
      if(size!==meta.bytes||await hash(await blob.arrayBuffer())!==meta.sha256)throw new Error(t("Hash toàn tệp không khớp; chưa tạo tệp.","Full file hash mismatch; no file was created."));
      url=URL.createObjectURL(blob);const link=el("download-save");link.href=url;link.download=path.split("/").pop();link.hidden=false;
      el("download-status").textContent=t("Đã xác minh SHA-256. Bấm Tải tệp đã xác minh để lưu trên máy.","SHA-256 verified. Select Download verified file to save it on your device.");el("download-hash").textContent=`SHA-256: ${meta.sha256}`;
    }catch(error){el("download-status").textContent=error.name==="AbortError"?t("Đã hủy. Chưa tạo tệp.","Cancelled. No file was created."):error.message;}
    finally{el("download-start").disabled=false;el("download-cancel").disabled=true;}
  });
})();

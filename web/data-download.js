"use strict";
/* Bounded public chunks, verified before making a downloadable Blob. No secrets. */
(()=>{
  const el=id=>document.getElementById(id),path=new URLSearchParams(location.search).get("path");
  let controller=null,url=null;
  const hash=async buffer=>[...new Uint8Array(await crypto.subtle.digest("SHA-256",buffer))].map(x=>x.toString(16).padStart(2,"0")).join("");
  el("download-name").textContent=path||"Chưa chọn tệp";
  el("download-start").disabled=!path;
  el("download-cancel").addEventListener("click",()=>controller?.abort());
  el("download-start").addEventListener("click",async()=>{
    controller=new AbortController();el("download-start").disabled=true;el("download-cancel").disabled=false;
    el("download-save").hidden=true;if(url)URL.revokeObjectURL(url);url=null;
    try{
      const base=new URLSearchParams({path}),version=new URLSearchParams(location.search).get("v");if(version)base.set("v",version);
      const response=await fetch(`/api/data?${base}&meta=1`,{signal:controller.signal});
      if(!response.ok)throw new Error(`Không đọc được thông tin tệp (HTTP ${response.status})`);
      const meta=await response.json();
      if(meta.encoding!=="identity"||meta.stored_bytes>160*1024*1024||!meta.chunks?.length||meta.chunks.length>160)throw new Error("Tệp chưa hỗ trợ tải theo phần.");
      base.set("v",meta.stored_sha256);const parts=[];let size=0;el("download-progress").max=meta.stored_bytes;
      for(let i=0;i<meta.chunks.length;i++){
        base.set("chunk",String(i));el("download-status").textContent=`Đang tải phần ${i+1}/${meta.chunks.length}…`;
        const r=await fetch(`/api/data?${base}`,{signal:controller.signal});if(!r.ok)throw new Error(`Tải chưa hoàn tất (HTTP ${r.status}). Bấm tải lại để thử lại.`);
        const bytes=await r.arrayBuffer();if(bytes.byteLength!==meta.chunks[i].bytes||await hash(bytes)!==meta.chunks[i].sha256)throw new Error("Hash phần tải không khớp; chưa tạo tệp.");
        parts.push(bytes);size+=bytes.byteLength;el("download-progress").value=size;
      }
      const blob=new Blob(parts,{type:meta.content_type});
      if(size!==meta.bytes||await hash(await blob.arrayBuffer())!==meta.sha256)throw new Error("Hash toàn tệp không khớp; chưa tạo tệp.");
      url=URL.createObjectURL(blob);const link=el("download-save");link.href=url;link.download=path.split("/").pop();link.hidden=false;
      el("download-status").textContent="Đã tải đủ và xác minh SHA-256. Bấm Lưu tệp đã kiểm tra.";el("download-hash").textContent=`SHA-256: ${meta.sha256}`;
    }catch(error){el("download-status").textContent=error.name==="AbortError"?"Đã hủy. Chưa tạo tệp.":error.message;}
    finally{el("download-start").disabled=false;el("download-cancel").disabled=true;}
  });
})();

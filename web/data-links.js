"use strict";
/* Large public archives need the verified multipart download screen. */
if(!["localhost","127.0.0.1"].includes(location.hostname)&&document.querySelector('meta[name="data-origin"]')?.content==="mongodb"){
  const large=["/data/source-presence/records.json.gz","/data/reference-stars/records.json.gz","/data/signal-controls/records.json.gz"];
  for(const a of document.querySelectorAll("a[href]")){
    const url=new URL(a.href,location.href);
    if(url.origin===location.origin&&large.includes(url.pathname)){
      a.href="/download.html?"+new URLSearchParams({path:url.pathname.slice(1)});a.removeAttribute("download");
    }
  }
}

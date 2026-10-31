"use strict";
function expandLinkedSection(){
  const target=document.getElementById(location.hash.slice(1));if(!target)return;
  for(let p=target;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true;
}
expandLinkedSection();
window.addEventListener("hashchange",()=>{expandLinkedSection();const target=document.getElementById(location.hash.slice(1));if(target)requestAnimationFrame(()=>target.scrollIntoView({block:"start"}));});
// Keep an incoming section link aligned after asynchronous evidence panels grow.
// Stop as soon as the reader scrolls, types or navigates somewhere else.
(function initialSectionLink(){
  const hash=location.hash;if(!hash)return;
  const target=document.getElementById(hash.slice(1));if(!target)return;
  const controller=new AbortController();let stopped=false,finishing=false;
  const stop=()=>{stopped=true;observer.disconnect();controller.abort();};
  const observer=new MutationObserver(check);
  function check(){
    if(stopped||finishing||document.readyState!=="complete"||document.querySelector('[aria-busy="true"]'))return;
    finishing=true;observer.disconnect();
    Promise.resolve(document.fonts?.ready).then(()=>{
      if(!stopped&&location.hash===hash)target.scrollIntoView({behavior:"instant",block:"start"});
      stop();
    });
  }
  for(const name of ['wheel','touchstart','pointerdown','keydown','hashchange'])window.addEventListener(name,stop,{once:true,passive:true,signal:controller.signal});
  window.addEventListener('load',check,{once:true,signal:controller.signal});
  observer.observe(document.documentElement,{subtree:true,attributes:true,attributeFilter:['aria-busy']});check();
})();

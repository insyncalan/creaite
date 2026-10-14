// @ts-check
/* core/motion.js (BL-231 step 2b): the motion hooks (BL-136): small presentation-only additions to the rest of the page.
   Moved from script/ unchanged, apart from `export`, `shared.` for the shared state (state.js) and the steps that ran at load,
   which are now boot…() functions called by src/main.js in today's order. Pieces: 0156-bl-136-sprint-motion.js */
import { REV } from "./data.js";
import { $, $$, html } from "./dom.js";
import { mPageOf } from "./nav.js";
import { anim, countUp, D, mK, mScroll, reduced, slideDown, store, TODAY } from "./page.js";
import { shared } from "./state.js";
import { REC } from "../panel.js";
import { mFileAt, MLV, MLVAT, MNEWGONE } from "../review.js";
import { mKind, row } from "../settings.js";
import { cell, grpToggle, layoutOf, LCOLL } from "../work.js";
/* ===== BL-136 (sprint-motion) ===== motion hooks: small additions to the code above, each presentation only (see the helpers) */
/* 3. Sliding indicator: when the selected tab, layout or Settings category changes, one element glides from the old to the new
   and is removed (the tab's own style shows at rest). Its colour is read from the theme's own selected style. */
export const MSLIDE=[["#wtabs","bottom"],["#wlay","fill"],["#setcats","left"]];
export const mSelOf=c=>c.querySelector(':scope>button[aria-selected="true"],:scope>button[aria-pressed="true"]');
export const mSelKey=b=>b?(b.dataset.t||b.dataset.lay||b.dataset.scat||b.textContent.trim()):null;
export function mSlide(c,edge){ const was=c._mkey, b=mSelOf(c), k=mSelKey(b); c._mkey=k;
  if(was==null||k==null||was===k||reduced()||!c.offsetParent) return;
  const old=[...c.querySelectorAll(":scope>button")].find(x=>x!==b&&mSelKey(x)===was); if(!old) return;
  const cs=getComputedStyle(b), bg=cs.backgroundColor, rad=cs.borderRadius, col=edge==="bottom"?cs.borderBottomColor:cs.borderLeftColor;
  const L=b.offsetLeft, T=b.offsetTop, W=b.offsetWidth||1, H=b.offsetHeight||1;
  c.querySelectorAll(":scope>.mind").forEach(x=>x.remove()); clearTimeout(c._mt);
  const m=document.createElement("span"); m.className="mind"; m.setAttribute("aria-hidden","true");
  Object.assign(m.style,edge==="bottom"?{left:L+"px",top:(T+H-2)+"px",width:W+"px",height:"2px",background:col}
    :{left:L+"px",top:T+"px",width:W+"px",height:H+"px",background:bg,borderRadius:rad,boxShadow:edge==="left"?`inset 2px 0 0 ${col}`:"none"});
  c.classList.add("mmove"); c.appendChild(m);
  anim(m,[{transform:`translate(${old.offsetLeft-L}px,${old.offsetTop-T}px) scale(${old.offsetWidth/W},${edge==="bottom"?1:old.offsetHeight/H})`},{transform:"none"}],{duration:320});
  c._mt=setTimeout(()=>{ m.remove(); c.classList.remove("mmove"); },320*mK()+40); }
/* 4. Tick: only rows that have just been highlighted draw their tick (a re-render, Select all or a range of more than 12 does not) */
export function mTick(sel,keyOf,prev,paint){ paint(); const now=$$(sel), on=now.filter(e=>e.classList.contains("hl")), fresh=on.filter(e=>!prev.has(keyOf(e)));
  prev.clear(); on.forEach(e=>prev.add(keyOf(e))); now.forEach(e=>{ if(!e.classList.contains("hl")) e.classList.remove("mtick"); });
  if(reduced()||fresh.length>12) return; fresh.forEach(e=>{ e.classList.remove("mtick"); void e.offsetWidth; e.classList.add("mtick"); }); }
/* 5. Filter chips: one chip added scales in; one removed fades from where it was while the rest close up. Several changing at once
   (Clear all, a saved view that changes several, another tab) swap at once. The fading copy is outside the chip row and has no text of its own. */
export const MCHIP=[["#wapplied",".fchip","[data-clr]"],["#rvapplied",".fchip","[data-rvclr]"],["#wviews",".vchip[data-wv]",null]];
export const mCtx=()=>typeof shared.WT==="undefined"?"":shared.WT;   /* another tab is a different row of chips */
export const mChipKey=(e,ks)=>{ if(!ks) return e.dataset.wv||null; const b=e.querySelector(ks); return b?(b.dataset.clr||b.dataset.rvclr||null):null; };
/** @type {(c: PageEl, cs: string, ks: any) => any[]} */
export const mChipEls=(c,cs,ks)=>[...c.querySelectorAll(cs)].map(e=>[mChipKey(e,ks),e]).filter(x=>x[0]!=null);
export function mChipSnap(c,cs,ks){ if(!c.offsetParent){ c._mchips=null; return; } const r0=c.getBoundingClientRect();
  c._mchips=new Map(mChipEls(c,cs,ks).map(([k,e])=>{ const r=e.getBoundingClientRect(); return [k,{x:r.left-r0.left,y:r.top-r0.top,w:r.width,h:r.height,t:e.textContent.replace(/×\s*$/,"").trim(),v:!ks}]; })); c._mctx=mCtx(); }
export function mChips(c,cs,ks){ const prev=c._mchips, same=c._mctx===mCtx(), now=new Map(mChipEls(c,cs,ks)); requestAnimationFrame(()=>mChipSnap(c,cs,ks));
  if(!prev||!same||reduced()||!c.offsetParent) return;
  const added=[...now.keys()].filter(k=>!prev.has(k)), gone=[...prev.keys()].filter(k=>!now.has(k)); if(added.length+gone.length!==1) return;
  if(added.length){ anim(now.get(added[0]),[{opacity:0,transform:"scale(.9)"},{opacity:1,transform:"none"}],{duration:200}); return; }
  const g=prev.get(gone[0]), r0=c.getBoundingClientRect(), gh=document.createElement("span");
  gh.className="mghost"+(g.v?" vg":""); gh.dataset.t=g.t; gh.setAttribute("aria-hidden","true");
  Object.assign(gh.style,{left:(r0.left+g.x)+"px",top:(r0.top+g.y)+"px",width:g.w+"px",height:g.h+"px"}); document.body.appendChild(gh);
  anim(gh,[{opacity:1,transform:"none"},{opacity:0,transform:"scale(.9)"}],{duration:160,easing:"in",fill:"forwards"}); setTimeout(()=>gh.remove(),160*mK()+60);
  now.forEach((e,k)=>{ const p=prev.get(k); if(!p) return; const r=e.getBoundingClientRect(), dx=p.x-(r.left-r0.left), dy=p.y-(r.top-r0.top);
    if(dx||dy) anim(e,[{transform:`translate(${dx}px,${dy}px)`},{transform:"none"}],{duration:160}); }); }
   /* the People page's two tabs (made when People first draws, so found by the body observer below) */
 
export function mNoFade(paint,changed){ const t=document.documentElement, off=shared.MKEYHELD||changed>2||reduced(); if(off) t.classList.add("mnofade"); paint(); if(off){ void getComputedStyle(document.body).color; $$("#workTbl tr,#reviewBody tr,table.ptbl tr").slice(0,1).forEach(r=>void getComputedStyle(r).backgroundColor); void document.body.offsetWidth; t.classList.remove("mnofade"); } }
/* 9. Detail panel: its content slides in from the right with a fade (320ms), its sections follow at 40ms steps (at most 8); the
   panel is usable from the first frame (only opacity and transform move). Closing is instant: the list takes the room back at once. */
/* 11. the message: one at a time; with Undo, a thin line runs down the Undo window */
/* list FLIP: where each keyed row was, then glide the rows to their new places (ease-in-out); more than 30 rows, or reduced, swap at once */
export function mSnapRows(sel,key){ const m=new Map(); $$(sel).forEach(e=>{ const r=e.getBoundingClientRect(); if(r.height) m.set(key(e),r); }); return m; }
export function mFlipRows(snap,sel,key,ms=320,fadeNew=false){ if(reduced()||!snap||snap.size>30) return; const now=$$(sel); if(now.length>30) return;
  now.forEach(e=>{ const f=snap.get(key(e)), r=e.getBoundingClientRect(); if(!r.height) return;
    if(!f){ if(fadeNew) anim(e,[{opacity:0},{opacity:1}],{duration:200}); return; }
    const dy=f.top-r.top, dx=f.left-r.left; if(Math.abs(dy)>.5||Math.abs(dx)>.5) anim(e,[{transform:`translate(${dx}px,${dy}px)`},{transform:"none"}],{duration:ms,easing:"inout"}); }); }
/* 13. Reorder on sort: a Work list (the Chase view is one) and a person's tables (Review has groups, not a sort); never the Board (Alan's exclusion: a card move is not animated) */
/** @type {[string, string, (e: PageEl) => string, string][]} */
export const MSORTS=[["#workTbl","#workTbl tr[data-row]",e=>e.dataset.row,"th[data-col]"],["#v-person","#v-person table.ptbl tr[data-row]",e=>e.dataset.row,"table.ptbl th[data-col]"]];
/* 14. Group collapse (BL-129 groups): the rows below glide to their new places, the opened rows fade in, the chevron turns.
   What is selected is decided by grpToggle exactly as before. Settings' and Prep's disclosures open with their content easing in. */
/* 12. Approve or reject one row in Review: a tinted copy closes up where it was (200ms tint, then 240ms) and the rows below glide up;
   the count and the message say what happened. Bulk decisions (the bar, Approve routine, Approve all) do not come through here. */
export function mRowGone(snap,n,v){ if(!snap) return; const g=snap.g; const still=$(`#reviewBody tr[data-n="${n}"]`);
  if(still){ [...still.querySelectorAll("td")].forEach(td=>anim(td,[{backgroundColor:v==="approved"?"var(--ok-soft)":"var(--bad-soft)",offset:.3},{}],{duration:700})); return; }   /* Review keeps a decided row, marked, until the data reloads: it tints in place */
  const gh=document.createElement("div"); gh.className="mrowghost "+(v==="approved"?"ok":"no"); gh.dataset.t=g.t; gh.setAttribute("aria-hidden","true");
  Object.assign(gh.style,{left:g.r.left+"px",top:g.r.top+"px",width:g.r.width+"px",height:g.r.height+"px"}); document.body.appendChild(gh);
  anim(gh,[{opacity:.6},{opacity:1,offset:.45},{opacity:0,transform:"scaleY(.2)"}],{duration:440,easing:"in",fill:"forwards"}); setTimeout(()=>gh.remove(),440*mK()+60);
  mFlipRows(snap.rows,"#reviewBody tr[data-n]",e=>e.dataset.n,240); }
/* 34. Review cleared: when the last pending item is decided while Review is open, the summary draws one circle and tick, once */
/* 16. Page change: the new page's content rises 4px and fades in over 200ms (the old one goes at once); addresses and Back as before */
/* 31. Landing pulse: arriving on a row from Today, a search result, Show them or an Open link scrolls it into view (instantly when
   reduced) and gives it one soft highlight. Only on arrival: never on a render, a sort or a live refresh. A collapsed group opens first. */
export function landOn(el){ if(!el) return; mScroll(el,{block:"center"}); if(reduced()) return; el.classList.remove("mland"); void el.offsetWidth; el.classList.add("mland"); setTimeout(()=>el.classList.remove("mland"),2800*mK()+100); }
export function mLandRow(){ if(shared.VIEW==="review"){ landOn($("#reviewBody tr.hl")||$("#reviewBody tr.sel")); return; }
  if(shared.VIEW!=="work"||shared.SEL==null) return; let tr=$(`#workTbl tr[data-row="${CSS.escape(String(shared.SEL))}"]`);
  if(!tr&&typeof LCOLL==="object"){ for(const h of $$("#workTbl tr.wgh.coll")){ const k=h.dataset.gk; grpToggle(k); tr=$(`#workTbl tr[data-row="${CSS.escape(String(shared.SEL))}"]`); if(tr) break; grpToggle(k); } }
  landOn(tr); }
/* 15. Skeleton: shown only if a load takes more than 150ms (ask creaite's History, Calendar Import's Refresh), then the content rises in */
export const MSKEL=html`<div class="msk" aria-hidden="true"><i></i><i></i><i></i></div>`;
/* ---- Stage C: numbers, status, ask creaite and ambient ---- */
/* First paint of each page, once per page load (never on a refresh, a live update or a return): 18 count-up, 19 bars, 20 sparks,
   24 the day's events, 27 Today's staggered reveal. Final values are in the page from the start (screen readers and tests). */
export const MFIRST=new Set();
export function mFirst(v){ if(MFIRST.has(v)) return; MFIRST.add(v); if(reduced()) return; const view=$$(".view").find(x=>!x.hidden); if(!view) return; const q=x=>[...view.querySelectorAll(x)];
  q(".th .cnt,.evbox .v").forEach(el=>{ const t=el.textContent.trim(); if(/^\d+$/.test(t)&&+t>0) countUp(el,+t,700); });
  q(".prog i").slice(0,40).forEach((el,i)=>anim(el,[{transform:"scaleX(0)",transformOrigin:"left"},{transform:"none",transformOrigin:"left"}],{duration:700,delay:i*60}));
  q(".spark").slice(0,30).forEach(sp=>[...sp.children].forEach((el,i)=>anim(el,[{transform:"scaleY(0)",transformOrigin:"bottom"},{transform:"none",transformOrigin:"bottom"}],{duration:500,delay:i*50})));
  q(".flc svg").forEach(el=>anim(el,[{opacity:0},{opacity:1}],{duration:900}));
  if(v==="today"){ const att=$$("#attnList>li").slice(0,8), day=$$("#dayMeets .dm");
    q(".th").forEach((el,i)=>anim(el,[{opacity:0,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:320,delay:Math.min(i,5)*40}));
    att.forEach((el,i)=>anim(el,[{opacity:0,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:320,delay:120+i*40}));
    anim($("#dayLine"),[{opacity:0},{opacity:1}],{duration:320,delay:120+att.length*40});
    day.forEach((el,i)=>anim(el,[{opacity:0,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:320,delay:Math.min(160+att.length*40+i*80,680)})); } }
/* 24. Today's now marker: one ripple ring beside the now dot; every animation pauses while the tab is hidden */
export function mNow(){ const d=$("#dayLine .dot.now"); if(!d||d.parentNode.querySelector(".mnow")) return; const c=d.cloneNode(); c.setAttribute("class","mnow"); c.setAttribute("aria-hidden","true"); d.after(c); }
 
/* 22 and 23: after an Apply, an import or a live refresh, cells whose value changed flash once (more than 12: one line instead),
   and a project whose health changed sends one ring from its icon. Compared by key before and after; the first render never flashes. */
export function mCells(){ if(shared.VIEW!=="work") return null; const cols=$$("#workTbl thead th").map(th=>th.dataset.col||""), m=new Map();
  $$("#workTbl tr[data-row]").slice(0,300).forEach(tr=>[...tr.children].forEach((td,i)=>{ if(cols[i]) m.set(tr.dataset.row+"|"+cols[i],td.textContent.trim()); })); return m; }
export function mCounts(){ return shared.VIEW==="today"?new Map($$("#v-today .th .cnt").map(e=>[e.id||e.parentElement.id,e.textContent.trim()])):null; }
/* 26. ask creaite: a live reply's words fade in at 25ms steps (opacity and a trace of blur: no layout change, no scrolling). Never the
   history or a re-opened chat (they don't come through here), and a reply over about 400 words appears whole. */
export function mWords(d){ if(!d||reduced()) return d; const walk=document.createTreeWalker(d,NodeFilter.SHOW_TEXT), nodes=[]; while(walk.nextNode()) nodes.push(walk.currentNode);
  const words=nodes.reduce((n,t)=>n+(t.textContent.match(/\S+/g)||[]).length,0); if(!words||words>400) return d; let i=0;
  nodes.forEach(t=>{ if(t.parentElement&&t.parentElement.closest("pre,code")) { return; } const parts=t.textContent.split(/(\s+)/); if(parts.length<2&&!t.textContent.trim()) return; const f=document.createDocumentFragment();
    parts.forEach(w=>{ if(!w) return; if(/^\s+$/.test(w)){ f.appendChild(document.createTextNode(w)); return; } const s=document.createElement("span"); s.className="mw"; s.style.animationDelay=`${i++*25*mK()}ms`; s.textContent=w; f.appendChild(s); });
    t.replaceWith(f); }); return d; }
/* 38. New since your last visit: Work (with All items and a person's tables), Review and Today's Needs attention. Existing timestamps
   (an item's "created" in Activity, else its raised date; a proposal's file stamp) against a last-viewed time this browser keeps
   (localStorage only: nothing in the vault, the database or staging). First visit: none. A dot fades once its row has been on screen
   for about 2s, or is opened; the page's last-viewed time moves on when the page is left. */
/* BL-250 (sprint-milestone-ui): the joined history, so an item created before Activity's newest 2000 rows keeps its date: ACT's
   "created" lines by table and ID, then the older history's (D.activity_older, BL-250 B) by ID */
export function mCreated(k,id){ if(shared.MCREATEDOF!==shared.ACT){ shared.MCREATEDOF=shared.ACT; shared.MCREATED=new Map(); (shared.ACT||[]).forEach(a=>{ if(/^created/.test(a.change||"")) shared.MCREATED.set(`${a.tbl}:${a.id}`,a.at); });
    Object.entries((D.activity_older||{}).items||{}).forEach(([i,L])=>L.forEach(([at,ch])=>{ if(/^created/.test(ch||"")&&!shared.MCREATED.has("old:"+i)) shared.MCREATED.set("old:"+i,at); })); }
  const at=shared.MCREATED.get(`${k}:${id}`)||shared.MCREATED.get("old:"+id); if(at) return at; const x=REC(k,id); return x&&x.raised?(x.raised.length>10?x.raised.slice(0,16):x.raised+" 99:99"):null; }
export function mIsNew(page,at){ const lv=MLVAT[page]; if(!lv||!at) return false; return at.endsWith(" 99:99")?at.slice(0,10)>lv.slice(0,10):at>lv; }
export function mDots(page){ if(!page) return; if(!(page in MLVAT)) MLVAT[page]=MLV[page]||null; if(!MLVAT[page]) return;
  const add=(row,key,at,cell)=>{ if(!row||MNEWGONE.has(key)||!mIsNew(page,at)||row.querySelector(".mnew")) return; const d=document.createElement("span"); d.className="mnew"; d.dataset.mk=key; d.setAttribute("role","img"); d.setAttribute("aria-label","New since your last visit"); (cell||row.querySelector("td.title")||row.firstElementChild||row).prepend(d); };
  if(page==="work") $$("#workTbl tr[data-row],#v-person table.ptbl tr[data-row],#workBoard .bcard[data-row]").forEach(tr=>{ const id=tr.dataset.row, k=shared.WT&&shared.WT!=="all"&&shared.VIEW!=="person"?shared.WT:mKind(id); add(tr,k+":"+id,mCreated(k,id),tr.matches(".bcard")?tr.querySelector(".bct"):null); });
  if(page==="review") $$("#reviewBody tr[data-n]").forEach(tr=>{ const r=REV.find(x=>x.n===+tr.dataset.n); if(r) add(tr,"rev:"+r.file+"|"+r.n,mFileAt(r.file)); });
  if(page==="today") $$("#attnList>li").forEach(li=>{ const o=li.querySelector("[data-open]"); if(!o) return; const [k,id]=o.dataset.open.split(":"); add(li,k+":"+id,mCreated(k,id),li.querySelector(".tb")); });
  if(!shared.MNEWIO&&"IntersectionObserver" in window) shared.MNEWIO=new IntersectionObserver(es=>es.forEach(e=>{ const d=e.target; clearTimeout(d._mt); if(e.isIntersecting) d._mt=setTimeout(()=>mDotGo(d),2000); }),{threshold:1});
  $$(".mnew").forEach(d=>{ if(!d._mo){ d._mo=1; shared.MNEWIO&&shared.MNEWIO.observe(d); } }); }
export function mDotGo(d){ if(!d||!d.isConnected) return; MNEWGONE.add(d.dataset.mk); shared.MNEWIO&&shared.MNEWIO.unobserve(d); const a=anim(d,[{opacity:1,transform:"none"},{opacity:0,transform:"scale(.2)"}],{duration:600,fill:"forwards"}); setTimeout(()=>d.remove(),reduced()?0:600*mK()+40); }
export function mLeave(page){ if(!page) return; const cur=store.get("creaite-lastviewed",{}); cur[page]=`${TODAY} ${new Date().toTimeString().slice(0,5)}`; store.set("creaite-lastviewed",cur); }   /* read again first: another tab may have written */
/* ===== end BL-136 hooks ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0156's place) */
export function bootMotionHooks(){
{ const mo=new MutationObserver(()=>MSLIDE.forEach(([sel,edge])=>{ const c=$(sel); if(c) mSlide(c,edge); }));
  MSLIDE.forEach(([sel])=>{ const c=$(sel); if(!c) return; c._mkey=mSelKey(mSelOf(c)); mo.observe(c,{subtree:true,childList:true,attributes:true,attributeFilter:["aria-selected","aria-pressed"]}); }); }
MCHIP.forEach(([sel,cs,ks])=>{ const c=$(sel); if(!c) return; mChipSnap(c,cs,ks); new MutationObserver(()=>mChips(c,cs,ks)).observe(c,{childList:true}); });
/* 6. Save: a spinner beside the setting while it is written; the drawn tick and "Saved" come only from a save that worked */
/* ---- Stage B: overlays, lists and structure ---- */
MSLIDE.push(["#ptabs","bottom"]);
/* 36. the highlight cross-fades for J/K and a single click; a held key, a range or a jump changes at once (.mnofade for that one paint) */
document.addEventListener("keydown",e=>{ if(e.repeat) shared.MKEYHELD=true; },true);
document.addEventListener("keyup",()=>{ shared.MKEYHELD=false; },true);
/* the sliding indicator also follows tab lists made later (People): one observer on the page, cheap per batch */
new MutationObserver(()=>MSLIDE.forEach(([sel,edge])=>{ const c=$(sel); if(c&&c._mkey===undefined) c._mkey=mSelKey(mSelOf(c)); else if(c) mSlide(c,edge); })).observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:["aria-selected"]});
{ const pn=$("#panel"); let was=pn&&pn.classList.contains("on");
  if(pn) new MutationObserver(()=>{ const on=pn.classList.contains("on"); if(on&&!was&&!reduced()){ const pk=pn.classList.contains("peek"); anim(pn.querySelector(".pin"),[{opacity:0,transform:`translateX(${pk?28:24}px)`},{opacity:1,transform:"none"}],{duration:pk?160:320});   /* BL-176: the peek slides in over 160ms */
      [...pn.querySelectorAll(".pb>*,.pb .fgrid>*")].slice(0,8).forEach((x,i)=>anim(x,[{opacity:0,transform:"translateY(4px)"},{opacity:1,transform:"none"}],{duration:240,delay:60+i*40})); } was=on; }).observe(pn,{attributes:true,attributeFilter:["class"]}); }
document.addEventListener("click",e=>{ for(const [box,sel,key,trig] of MSORTS){ const t=e.target.closest&&e.target.closest(trig); if(!t||!t.closest(box)||e.target.closest(".colrz")) continue;
    const snap=mSnapRows(sel,key); requestAnimationFrame(()=>mFlipRows(snap,sel,key)); return; } },true);
document.addEventListener("change",e=>{ if(!(e.target.closest&&e.target.closest("#dispMenu"))||layoutOf(shared.WT)==="board") return; const sel="#workTbl tr[data-row]", key=x=>x.dataset.row, snap=mSnapRows(sel,key); requestAnimationFrame(()=>mFlipRows(snap,sel,key)); },true);
document.addEventListener("toggle",e=>{ const d=e.target; if(!(d instanceof HTMLDetailsElement)||!d.open||reduced()) return; [...d.children].filter(x=>x.tagName!=="SUMMARY").forEach(x=>slideDown(x)); },true);
document.addEventListener("click",e=>{ if(e.target.closest&&e.target.closest("#tBrief [data-open],#tBrief [data-nav],.vsr,#cmdkList button,#rvShow,[data-nav]")) requestAnimationFrame(()=>requestAnimationFrame(mLandRow)); },true);
/* 32. Banners: the live-server alert eases in once the page has loaded (never one already showing); a new VIP alert on Today slides in */
requestAnimationFrame(()=>requestAnimationFrame(()=>document.documentElement.classList.add("mready")));
document.querySelector(".view:not([hidden])")&&mFirst(shared.VIEW);
document.addEventListener("visibilitychange",()=>document.documentElement.classList.toggle("mhidden",document.hidden));
document.documentElement.classList.toggle("mhidden",document.hidden);
mNow();
/* 28. the spotlight follows the pointer over the Projects page's table card */
$("#projTbl")?.addEventListener("pointermove",e=>{ if(e.pointerType!=="mouse") return; const r=e.currentTarget.getBoundingClientRect(); e.currentTarget.style.setProperty("--mx",`${e.clientX-r.left}px`); e.currentTarget.style.setProperty("--my",`${e.clientY-r.top+e.currentTarget.scrollTop}px`); });
{
  addEventListener("pagehide",()=>mLeave(mPageOf(shared.VIEW))); mDots(mPageOf(shared.VIEW)); }
}

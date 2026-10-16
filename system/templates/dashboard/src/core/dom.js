// @ts-check
/* core/dom.js (BL-231 step 2b): the DOM helpers, escaping (`html`), the icons and the one tooltip.
   Moved from script/ unchanged, apart from `export`, `shared.` for the shared state (state.js) and the steps that ran at load,
   which are now boot…() functions called by src/main.js in today's order. Pieces: 0002-core.js, 0003-bl-228-d-sprint-escaping.js, 0004-bl-158-sprint-icons.js */
/* ======================= core ======================= */
/* BL-303: an optional root, so a lookup inside a popup or panel searches only there (the page when it is left out). */
/** @param {string} s @param {ParentNode} [root] @returns {any} */
export const $=(s,root=document)=>root.querySelector(s);
/** @param {string} s @param {ParentNode} [root] @returns {any[]} */
export const $$=(s,root=document)=>[...root.querySelectorAll(s)];
export const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
/* ===== BL-228 D (sprint-escaping) ===== escaping by default. New code builds markup with html`…`, never with esc() by hand:
   every ${…} is escaped (& < > " and '), an array is joined with each element treated the same way, null, undefined and false
   print nothing (so ${cond&&html`…`} works; 0 prints "0"), and the result of another html`…` or raw() passes through unchanged.
   raw(s) is only for markup the page builds itself (an icon from ic(), a fragment already built safely); never for data.
   The result is a SafeHTML: use it where markup goes, or join it into a string as it is (String() gives the markup). */
export class SafeHTML{ constructor(s){ this.s=s; } toString(){ return this.s; } }
export const raw=s=>s instanceof SafeHTML?s:new SafeHTML(String(s??""));
export const htmlPart=v=>v instanceof SafeHTML?v.s:Array.isArray(v)?v.map(htmlPart).join(""):v==null||v===false?"":String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
export function html(strings,...vals){ let out=strings[0]; vals.forEach((v,i)=>{ out+=htmlPart(v)+strings[i+1]; }); return new SafeHTML(out); }
/* Step 2: the converted views write markup only through these two. Given html`…` (or raw()) they write it as it is; given
   anything else they escape it, so a plain string that slips through shows as text and never runs. */
export function putHTML(el,h){ el.innerHTML=htmlPart(h); return el; }
export function swapHTML(el,h){ el.outerHTML=htmlPart(h); }
export function addHTML(el,where,h){ el.insertAdjacentHTML(where,htmlPart(h)); }
/* BL-231 step 4: and a whole document into a window (the Prep page's popup), the same way. */
export function writeDoc(w,h){ w.document.write(htmlPart(h)); }
/* ===== end BL-228 D ===== */
/* ===== BL-158 (sprint-icons) ===== One icon set and one tooltip.
   ICONS: the path strings, on a 24px grid, drawn with a 1.8 stroke, round caps and currentColor (so every theme colours them).
   ic(name, o): the <svg> for JavaScript-built markup; o is a class string or {cls, w (stroke width), size}. Static markup writes
   <svg data-ic="name" …its own attributes…></svg> and paintIcons() fills in the paths, so the rail and header keep their look.
   No icon font and no external file. Shapes: creaite's own (the rail, header and section icons) and, for the newer ones, the
   style of the open-source Lucide set; several paths are adapted from Lucide (lucide.dev): ISC License, copyright (c)
   Lucide Contributors 2022 and, for the parts from Feather, Cole Bemis 2013-2022 (MIT). Permission to use, copy, modify and/or
   distribute this software for any purpose with or without fee is hereby granted, provided that the above copyright notice and
   this permission notice appear in all copies. THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES.
   The tooltip: any element with data-tip (and data-key for a shortcut that exists) shows #tip after 250ms of hover and at once
   on keyboard focus; Esc, scrolling, a click or leaving hides it; the pointer can move onto it (WCAG 1.4.13); inverse colours. */
export const ICONS={
  /* the rail, the header and the section headers (unchanged shapes) */
  today:'<circle cx="12" cy="12" r="4"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
  inbox:'<path d="M4 13h4l2 3h4l2-3h4"/><path d="M5.5 5h13L21 13v6H3v-6z"/>',
  projects:'<path d="M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-4H4zM14 4v4h6V4z"/>',
  work:'<path d="M8 6h12M8 12h12M8 18h12"/><path d="m3 6 1 1 2-2M3 12l1 1 2-2M3 18l1 1 2-2"/>',
  people:'<circle cx="9" cy="8" r="3.2"/><path d="M3.5 19v-1a4.5 4.5 0 0 1 4.5-4.5h2a4.5 4.5 0 0 1 4.5 4.5v1"/><path d="M16 5.2a3.2 3.2 0 0 1 0 5.6M18.5 13.8a4.5 4.5 0 0 1 2 3.7V19"/>',
  review:'<path d="M4 5h16v11H8l-4 4z"/><path d="m9 10.5 2 2 4-4"/>',
  activity:'<path d="M12 7v5l3 2"/><circle cx="12" cy="12" r="8.5"/>',
  settings:'<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M4.2 6.5l2.6 1.5M17.2 16l2.6 1.5M4.2 17.5 6.8 16M17.2 8l2.6-1.5"/>',
  /* BL-192 (sprint-polish-themes): a gear for Settings (Lucide's "settings" shape), so it no longer reads as Today's sun or the Display sliders */
  gear:'<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
  search:'<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  chat:'<path d="M4 5h16v11H9l-5 4z"/>',
  history:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  upload:'<path d="M12 15V4M7.5 8.5 12 4l4.5 4.5"/><path d="M4 14v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>',
  bolt:'<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/>',
  video:'<rect x="3" y="6" width="13" height="12" rx="2"/><path d="m16 10 5-3v10l-5-3"/>',
  /* the legend (dev/mockups/icons-mockup.html §6) */
  plus:'<path d="M12 5v14M5 12h14"/>',
  x:'<path d="M18 6 6 18M6 6l12 12"/>',
  door:'<path d="M13 4h3a2 2 0 0 1 2 2v14"/><path d="M2 20h3M13 20h9M10 12v.01"/><path d="M13 4.6v16.2a.5.5 0 0 1-.6.5L5 20V5.6a1 1 0 0 1 .8-1L12.4 3a.5.5 0 0 1 .6.5z"/>',   /* BL-270: Close the day (a door, a step out) */
  check:'<path d="M20 6 9 17l-5-5"/>',
  checks:'<path d="M18 6 7 17l-5-5M22 10l-7.5 7.5L13 16"/>',
  list:'<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>',
  board:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 7v7M12 7v4M16 7v9"/>',
  sliders:'<path d="M21 4h-7M10 4H3M21 12h-9M8 12H3M21 20h-5M12 20H3M14 2v4M8 10v4M16 18v4"/>',
  funnel:'<path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/>',
  flag:'<path d="M4 22V4M4 4h13l-2 4 2 4H4"/>',
  copy:'<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M4 16V5a2 2 0 0 1 2-2h10"/>',
  folder:'<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
  folderopen:'<path d="m6 14 1.5-2.9A2 2 0 0 1 9.2 10H20a2 2 0 0 1 1.9 2.5l-1.5 6a2 2 0 0 1-1.9 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.7.9l.8 1.2a2 2 0 0 0 1.7.9H18a2 2 0 0 1 2 2v2"/>',
  eye:'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  pencil:'<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
  trash:'<path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M10 11v6M14 11v6"/>',
  undo:'<path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/>',
  refresh:'<path d="M21 12a9 9 0 1 1-9-9c2.5 0 4.9 1 6.7 2.7L21 8"/><path d="M21 3v5h-5"/>',
  stop:'<rect x="6" y="6" width="12" height="12" rx="2"/>',
  arrowup:'<path d="M12 19V5M5 12l7-7 7 7"/>',
  external:'<path d="M15 3h6v6M10 14 21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  chevdown:'<path d="m6 9 6 6 6-6"/>',
  calendar:'<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
  filetext:'<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7z"/><path d="M14 2v4a2 2 0 0 0 2 2h4M10 9H8M16 13H8M16 17H8"/>',
  mail:'<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-9.1 5.7a2 2 0 0 1-2 0L2 7"/>',
  handover:'<path d="m15 14 5-5-5-5"/><path d="M20 9H9.5A5.5 5.5 0 0 0 4 14.5V20"/>',
  spark:'<path d="M12 1Q12 12 23 12Q12 12 12 23Q12 12 1 12Q12 12 12 1Z" fill="currentColor" stroke="none"/>',   /* ask creaite's own mark */
  type:'<path d="M4 7V4h16v3M9 20h6M12 4v16"/>',
  clip:'<path d="M21 12.5l-8.5 8.5a5.5 5.5 0 0 1-7.8-7.8l9-9a3.7 3.7 0 0 1 5.2 5.2l-9 9a1.8 1.8 0 0 1-2.6-2.6l8.3-8.3"/>',
  sun:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon:'<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z"/>',
  /* BL-319 (v1.9.2): Today's row actions (dev/mockups/today-one-home-mockup.html), here so they exist before Today first draws */
  play:'<path d="M7 4v16l13-8z"/>',
  calmove:'<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 10h17M8 3v4M16 3v4M12 13v4M10 15h4"/>',
  done:'<circle cx="12" cy="12" r="9"/><path d="M8 12l3 3 5-6"/>',
  dismiss:'<path d="M17.9 17.9A10 10 0 0 1 12 19C5.5 19 2 12 2 12a17 17 0 0 1 4.1-5M9.9 5.2A9 9 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-2.2 3.2M3 3l18 18"/>',
  chasemail:'<rect x="3" y="5" width="14" height="11" rx="2"/><path d="M3.5 6.5 10 11l6.5-4.5M15 19h6M18.5 16.5 21 19l-2.5 2.5"/>',
  /* BL-194 (sprint-ask-creaite-access): the approval card's tiers (Lucide's "triangle-alert" and "shield-alert") */
  alert:'<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4M12 17h.01"/>',
  shield:'<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="M12 8v4M12 16h.01"/>'
};
export function ic(name,o){ o=typeof o==="string"?{cls:o}:(o||{}); const sz=o.size?` width="${o.size}" height="${o.size}" style="width:${o.size}px;height:${o.size}px"`:"";
  return `<svg class="${o.bare?"":"i"}${o.cls?" "+o.cls:""}" viewBox="0 0 24 24"${sz} fill="none" stroke="currentColor" stroke-width="${o.w||1.8}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" data-icn="${name}">${ICONS[name]||""}</svg>`; }
export function paintIcons(root){ (root||document).querySelectorAll("svg[data-ic]").forEach(s=>{ if(!s.dataset.icn){ putHTML(s,raw(ICONS[s.dataset.ic]||"")); s.dataset.icn=s.dataset.ic; s.setAttribute("aria-hidden","true"); } }); }
/* an icon-only button: the same words in aria-label and the tooltip; data-key only for a shortcut that exists */
/** @type {(icon: string, label: string, attrs?: string | SafeHTML, cls?: string, key?: string) => string} */
export const ibtn=(icon,label,attrs="",cls="",key="")=>`<button type="button" class="ib${cls?" "+cls:""}" aria-label="${esc(label)}" data-tip="${esc(label)}"${key?` data-key="${esc(key)}"`:""} ${attrs}>${ic(icon)}</button>`;
export const TIP={el:null,show:0,hide:0,watch:0};
export function tipBox(){ let t=document.getElementById("tip"); if(!t){ addHTML(document.body,"beforeend",html`<div id="tip" role="tooltip"></div>`); t=document.getElementById("tip"); } return t; }
export function tipHide(){ clearTimeout(TIP.show); clearTimeout(TIP.hide); clearInterval(TIP.watch); const t=document.getElementById("tip"); if(t) t.classList.remove("on");
  if(TIP.el&&TIP.el.getAttribute("aria-describedby")==="tip") TIP.el.removeAttribute("aria-describedby"); TIP.el=null; }
export function tipShow(el,delay){ clearTimeout(TIP.show); clearTimeout(TIP.hide); TIP.show=setTimeout(()=>{ const text=el.dataset.tip; if(!text||!el.isConnected) return;
    const t=tipBox(), k=el.dataset.key; putHTML(t,html`<span>${text}</span>${k?html`<kbd>${k}</kbd>`:""}`);
    if(TIP.el&&TIP.el!==el&&TIP.el.getAttribute("aria-describedby")==="tip") TIP.el.removeAttribute("aria-describedby");
    TIP.el=el; if(text!==el.getAttribute("aria-label")&&!el.hasAttribute("aria-describedby")) el.setAttribute("aria-describedby","tip");
    const r=el.getBoundingClientRect(), w=t.offsetWidth, h=t.offsetHeight; let x=Math.max(8,Math.min(innerWidth-w-8,r.left+r.width/2-w/2)), y=r.bottom+8;
    if(y+h>innerHeight-8) y=r.top-h-8;
    if(el.closest(".rail")&&!el.closest("#railMoreMenu")){ x=r.right+10; y=Math.max(8,Math.min(innerHeight-h-8,r.top+r.height/2-h/2)); }   /* BL-319: the sidebar's tooltips sit beside it */
    t.style.left=x+"px"; t.style.top=y+"px"; t.classList.add("on");
    clearInterval(TIP.watch); TIP.watch=setInterval(()=>{ if(!TIP.el||!TIP.el.isConnected||!TIP.el.getClientRects().length) tipHide(); },300); },delay); }
   /* hides the tooltip; Esc still does its own job */
/* a copy icon ticks for a second after copying, so the feedback is not lost with the word */
export function icTick(b){ if(!b) return; const was=b.innerHTML, tip=b.dataset.tip; putHTML(b,raw(ic("check"))); b.classList.add("ticked"); if(tip) b.dataset.tip="Copied";
  clearTimeout(b._tk); b._tk=setTimeout(()=>{ putHTML(b,raw(was)); b.classList.remove("ticked"); if(tip) b.dataset.tip=tip; },1100); }
/* every icon-only button (an icon, no words, an aria-label) gets the one tooltip with the same words, wherever it is drawn: its
   old title goes (two tooltips would show) and a key written in it, "(Esc)", is kept as data-key */
export function tipUp(root){ const L=root.matches&&root.matches("button")?[root]:[...(root.querySelectorAll?root.querySelectorAll("button:not([data-tip])"):[])];
  L.forEach(b=>{ if(b.dataset.tip||b.closest(".rail")) return; const lab=b.getAttribute("aria-label"); if(!lab||!b.querySelector("svg")||b.textContent.trim()) return;
    const k=(b.title||"").match(/\((Esc|Shift\+R|[A-Z])\)\s*$/); b.dataset.tip=lab; if(k&&!b.dataset.key) b.dataset.key=k[1]; b.removeAttribute("title"); }); }
/* ===== end BL-158 (JS: set, helper, tooltip) ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0004's place) */
/* insyncalan/creaite-plan#85: a click is not lost when the page redraws between the press and the release. Chrome sends no click
   at all when the pressed node has been removed from the page (a data refresh, BL-327, BL-253), whether the whole row went, the
   pressed cell inside a row that stayed, or the row was taken out and put back (a keyed reorder). The press remembers its row's
   key (data-row) and the pressed node, and watches for either being removed while the button is down; at the release, if one was
   (or one is not in the page), and the element now under the pointer is the same row by key, the click is made there. A press on
   one row released on another is still no click on either. The swallow below is the safety net if the browser sends its own. */
const PRESS={key:null,el:null,node:null,at:"",sent:false,lost:false,mo:/** @type {MutationObserver|null} */(null)};
/* where a node sits inside its row, as child positions: a press and a release at the same place in the row are one cell's click */
const rowPlace=(top,from)=>{ const out=[]; for(let at=from;at&&at!==top;at=at.parentNode) out.push([...at.parentNode.children].indexOf(at)); return out.join("."); };
/* the node at such a place in a row (the row itself for ""); the row when the place no longer exists */
const placeNode=(top,place)=>{ let n=top; if(place==="") return n; for(const i of place.split(".").reverse()){ const c=n.children[+i]; if(!c) return top; n=c; } return n; };
/* a removal that takes the pressed node out of the page (also one that puts it back): the browser has dropped the click */
const pressRemoved=ms=>{ for(const m of ms) for(const n of m.removedNodes) if(PRESS.node&&n.contains(PRESS.node)) PRESS.lost=true; };
const pressEnd=()=>{ if(PRESS.mo){ pressRemoved(PRESS.mo.takeRecords()); PRESS.mo.disconnect(); } };
export function bootLostClick(){
PRESS.mo=new MutationObserver(pressRemoved);
const pressClear=()=>{ pressEnd(); PRESS.key=null; PRESS.el=null; PRESS.node=null; PRESS.sent=false; PRESS.lost=false; };
document.addEventListener("mousedown",e=>{ pressClear(); if(e.button!==0||!e.target.closest) return;
  const r=e.target.closest("[data-row]"); if(r){ PRESS.key=r.dataset.row; PRESS.el=r; PRESS.node=e.target; PRESS.at=rowPlace(r,e.target);
    /** @type {MutationObserver} */(PRESS.mo).observe(document,{childList:true,subtree:true}); } },true);
document.addEventListener("contextmenu",pressClear,true);   /* Ctrl+click on a Mac is a context menu, and the browser sends no click for it */
document.addEventListener("mouseup",e=>{ pressEnd(); const el=PRESS.el, node=PRESS.node, key=PRESS.key;
  if(!e.isTrusted||e.button!==0||el==null||node==null||key==null||!e.target.closest) return;
  if(!PRESS.lost&&el.isConnected&&node.isConnected) return;
  const landed=e.target.closest("[data-row]"); if(!landed||landed.dataset.row!==key) return;
  PRESS.sent=true;
  /* the same place in the row: that cell; another cell of the row: the row itself, as the browser does for two nodes it shares a parent with */
  const place=rowPlace(landed,e.target)===PRESS.at?rowPlace(landed,e.target):"";
  const tgt=/** @type {Element} */(place===""?landed:e.target);
  setTimeout(()=>{ PRESS.sent=false;   /* the browser's own click, if it sends one, comes with the release; a later trusted click (Enter, Space, a label) is a different click */
    let t=tgt;
    if(!t.isConnected){ const r=document.querySelector(`[data-row="${CSS.escape(key)}"]`); t=r?placeNode(r,place):t; }   /* a second redraw before the timer: find the row again by its key */
    if(t.isConnected) t.dispatchEvent(new MouseEvent("click",{bubbles:true,cancelable:true,view:window,detail:e.detail||1,clientX:e.clientX,clientY:e.clientY,screenX:e.screenX,screenY:e.screenY,
      ctrlKey:e.ctrlKey,shiftKey:e.shiftKey,altKey:e.altKey,metaKey:e.metaKey,button:0})); },0); },true);
document.addEventListener("click",e=>{ if(PRESS.sent&&e.isTrusted){ PRESS.sent=false; e.stopImmediatePropagation(); } },true);   /* a click the browser did send is not handled twice */
}
export function bootTooltips(){
paintIcons();
document.addEventListener("mouseover",e=>{ const t=e.target; if(!t.closest) return; if(t.closest("#tip")){ clearTimeout(TIP.hide); return; }
  const el=t.closest("[data-tip]"); if(el&&el===TIP.el){ clearTimeout(TIP.hide); return; }
  if(el){ tipShow(el,TIP.el?0:250); return; }   /* moving from one icon to the next, the tooltip follows at once */
  clearTimeout(TIP.show); if(TIP.el){ clearTimeout(TIP.hide); TIP.hide=setTimeout(tipHide,120); } });
document.addEventListener("mouseleave",tipHide);
document.addEventListener("focusin",e=>{ const el=e.target.closest&&e.target.closest("[data-tip]"); if(el&&e.target.matches(":focus-visible")) tipShow(el,0); else if(TIP.el) tipHide(); });
document.addEventListener("focusout",e=>{ if(TIP.el&&(e.target===TIP.el||TIP.el.contains(e.target))) tipHide(); });
document.addEventListener("keydown",e=>{ if(e.key==="Escape"&&TIP.el) tipHide(); },true);
document.addEventListener("mousedown",tipHide,true);
document.addEventListener("scroll",()=>{ if(TIP.el) tipHide(); },true);
addEventListener("blur",tipHide);
tipUp(document.body);
new MutationObserver(ms=>{ for(const m of ms) for(const n of m.addedNodes) if(n.nodeType===1) tipUp(n); }).observe(document.body,{childList:true,subtree:true});
}

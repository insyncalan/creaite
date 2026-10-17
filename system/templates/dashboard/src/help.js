// @ts-check
/* help.js (BL-231 step 2b), moved from script/ by dev/tools/convert_area.py: 0091-help-bl-84.js, 0158-bl-155-sprint-ux.js, 0161-bl-169-sprint-polish-2.js, 0162-bl-167-sprint-polish-2.js.
   Unchanged apart from `export`, `shared.` for the shared state (core/state.js) and the load-time steps, now in
   boot…() functions that src/main.js calls in today's order. */
import { drawTabs } from "./components/Tabs.jsx";
import { open } from "./core/data.js";
import { $, $$, addHTML, esc, html, putHTML, raw } from "./core/dom.js";
import { go, navWrite } from "./core/nav.js";
import { cmdBox, D, S, store } from "./core/page.js";
import { snack, viaServer, writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { drawPanel, PDAGE, pdAll, pdPut, pkNew, REC } from "./panel.js";
import { hit } from "./work.js";
import { openChat } from "./ask.js";
/* ===== Help (BL-84) ===== */
/* Three tabs from help.md (built by build_dashboard.help_sections): Start here, How do I… and Reference. Each has an
   address (#help-start, #help-howto, #help-howto-<task>, #help-reference, #help-reference-<section>), so Back and
   Forward work; "?" opens the tab used last. */
export const HD=D.help&&D.help.tabs?{jobs:[],screens:{},news:[],...D.help}:{tabs:[],tasks:[],sections:[],jobs:[],screens:{},news:[]}, HTABS=HD.tabs.map(t=>t.id);
shared.HELPARG="start";
export function helpNorm(a){ a=String(a||""); const i=a.indexOf("-"), tab=i<0?a:a.slice(0,i), rest=i<0?"":a.slice(i+1);
  if(!HTABS.includes(tab)) return null;
  if(rest&&!(tab==="howto"?HD.tasks:tab==="reference"?HD.sections:tab==="whatsnew"?HD.news:[]).some(x=>x.id===rest)) return tab;
  return rest?`${tab}-${rest}`:tab; }
export function renderHelp(arg){ helpSearchClear(); if(!HD.tabs.length){ putHTML($("#helpPane"),html`<div class="hp-wrap"><p>Help isn’t available: system/templates/help.md is missing.</p></div>`); return; }
  const a=helpNorm(arg)||helpNorm(store.get("creaite-help-tab","start"))||HTABS[0], i=a.indexOf("-"), tab=i<0?a:a.slice(0,i), rest=i<0?"":a.slice(i+1), changed=!$("#helpPane").dataset.tab||$("#helpPane").dataset.tab!==tab;
  shared.HELPARG=a; store.set("creaite-help-tab",tab);
  drawTabs($("#helpTabsHost"),{items:HD.tabs.map(t=>({id:t.id,label:t.title,tabId:"htab-"+t.id,data:{help:t.id}})),selected:tab,onSelect:helpGo,label:"Help",className:"tabs",id:"helpTabs",wrap:true});   /* BL-316: the Tabs block */
  if(changed){ const html=HD.tabs.find(t=>t.id===tab).html.replace("<p>[start command]</p>",cmdBox());
    putHTML($("#helpPane"),raw(`<div class="hp-wrap hp-${tab}">${html}</div>`)); $("#helpPane").dataset.tab=tab; $("#helpPane").setAttribute("aria-labelledby","htab-"+tab); }
  $$("#helpPane .hp-task").forEach(t=>t.classList.toggle("hp-hl",!!rest&&tab==="howto"&&t.dataset.task===rest));
  $$("#helpPane .hp-refidx a").forEach(l=>l.toggleAttribute("aria-current",tab==="reference"&&l.dataset.help==="reference-"+rest));
  const target=rest?document.getElementById((tab==="howto"?"ht-":tab==="reference"?"hr-":"hn-")+rest):null;
  if(target){ target.scrollIntoView({block:"start"});   /* the embedded fonts can swap in after this and move it: go there again */
    if(document.fonts&&document.fonts.status!=="loaded") document.fonts.ready.then(()=>{ if(shared.HELPARG===a&&target.isConnected) target.scrollIntoView({block:"start"}); }); }
  else if(changed) $("#v-help").scrollTop=0; }
export function helpGo(arg){ const a=helpNorm(arg); if(!a) return; renderHelp(a); navWrite(true); }
/* First visit: a vault whose help.start_seen is false opens on Help › Start here once, then sets it true (a settings write,
   logged as usual). A link with an address (a bookmark, #review) is never overridden; the setting is only written when the
   dashboard can write without asking (the live server, or a vault folder already connected), so it shows again until it can. */
export let SEENBUSY=false;
export async function markHelpSeen(){ if(S.helpSeen||SEENBUSY||!(viaServer()||shared.VSTATE==="ok")) return false; SEENBUSY=true;
  try{ if(await writeSettings({"help.start_seen":true})){ S.helpSeen=true; return true; } return false; } finally{ SEENBUSY=false; } }
export function firstHelp(){ if(S.helpSeen||shared.HADHASH) return false; go("help","start"); markHelpSeen(); return true; }
/* ===== #158 Phase B: one search over all of Help ===== */
/* The index is built in the page from the text Help already holds (the tabs' HTML in D.help): no request, nothing sent. Each
   entry is one page (a how-to, a Reference section, a release, a Start here section) with its lines. A search is whole words and
   prefixes, case and accent blind; a plural finds the singular (and the other way round, by prefix). */
const hNorm=s=>String(s||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
const hWords=s=>hNorm(s).match(/[a-z0-9]+/g)||[];
const hStems=w=>{ const c=[w]; if(w.length>3){ if(w.endsWith("ies")) c.push(w.slice(0,-3)+"y"); if(w.endsWith("es")) c.push(w.slice(0,-2)); if(w.endsWith("s")) c.push(w.slice(0,-1)); } return c; };
const hHit=(qw,tw)=>hStems(qw).some(c=>c.length>=2&&tw.startsWith(c));
export const HPARTS={start:"Start here",howto:"How do I…",reference:"Reference",whatsnew:"What’s new"};
export const HGROUPS=["howto","reference","whatsnew","start"];
let HIDX=null;
/** @returns {{tab:string,part:string,id:string,title:string,target:string,box:string,sel:string,lines:string[],tw:string[],lw:string[][]}[]} */
export function helpIndex(){ if(HIDX) return HIDX; const out=[], txt=el=>(el.textContent||"").replace(/\s+/g," ").trim();
  const add=(tab,id,title,target,box,sel,els)=>{ const lines=els.map(txt).filter(Boolean); out.push({tab,part:HPARTS[tab],id,title,target,box,sel,lines,tw:hWords(title),lw:lines.map(hWords)}); };
  for(const t of HD.tabs){ const doc=new DOMParser().parseFromString(t.html,"text/html");
    if(t.id==="howto") doc.querySelectorAll(".hp-task").forEach(e=>{ const id=e.getAttribute("data-task"); add("howto",id,txt(e.querySelector("h3")),"howto-"+id,"#ht-"+id,".hp-where,li,.hp-or",[...e.querySelectorAll(".hp-where,li,.hp-or")]); });
    else if(t.id==="reference") doc.querySelectorAll(".hp-ref").forEach(e=>{ const id=e.getAttribute("data-ref"); add("reference",id,txt(e.querySelector("h2")),"reference-"+id,"#hr-"+id,"p,li,td",[...e.querySelectorAll("p,li,td")]); });
    else if(t.id==="whatsnew") doc.querySelectorAll(".hp-new").forEach(e=>{ const id=e.id.slice(3); add("whatsnew",id,txt(e.querySelector("h2")),"whatsnew-"+id,"#hn-"+id,"p,li",[...e.querySelectorAll("p,li")]); });
    else doc.querySelectorAll("section.hp-sec,section.hp-loop").forEach(e=>{ const h=e.querySelector("h2"); if(!h) return; add("start",h.id,txt(h),"start","[aria-labelledby="+h.id+"]","p,li,td,.hp-job span",[...e.querySelectorAll("p,li,td,.hp-job span")]); }); }
  HIDX=out; return out; }
/** The best matches for q: [{e, score, li, line}], best first. Every word of q must be found, in the title or a line. */
export function helpFind(q){ const qw=hWords(q); if(!qw.length) return []; const out=[];
  for(const e of helpIndex()){ let tScore=0, ok=true;
    for(const w of qw){ const inT=e.tw.some(x=>hHit(w,x)); if(inT) tScore+=10; else if(!e.lw.some(l=>l.some(x=>hHit(w,x)))) { ok=false; break; } }
    if(!ok) continue;
    let li=-1, best=0; e.lw.forEach((l,i)=>{ const n=qw.filter(w=>l.some(x=>hHit(w,x))).length; if(n>best){ best=n; li=i; } });
    out.push({e,score:tScore+best*3+(e.tab==="howto"?1:0),li,line:li<0?(e.lines[0]||""):e.lines[li]}); }
  return out.sort((a,b)=>b.score-a.score); }
/** A line with the matching words marked (HTML), cut to about 170 characters around the first one. @param {string} line @param {string} q */
export function helpMark(line,q){ const qw=hWords(q), re=/[\p{L}\p{N}]+/gu; let first=-1, o="", last=0;
  for(const m of line.matchAll(re)){ if(qw.some(w=>hHit(w,hNorm(m[0])))){ if(first<0) first=m.index; o+=esc(line.slice(last,m.index))+"<mark>"+esc(m[0])+"</mark>"; last=m.index+m[0].length; } }
  o+=esc(line.slice(last)); if(first<=60||line.length<=170) return line.length>170&&first<0?esc(line.slice(0,170))+"…":o;
  const cut=line.lastIndexOf(" ",first-40); if(cut<=0) return o; return "…"+helpMark(line.slice(cut+1),q); }
const hPlain=(line,n)=>line.length>n?line.slice(0,n-1)+"…":line;
/** Open a result: its page, scrolled to the matching line (marked for a moment). */
export function helpOpenHit(e,li){ helpSearchClear(); helpGo(e.target);
  if(li>=0){ const box=document.querySelector("#helpPane "+e.box), el=box&&[...box.querySelectorAll(e.sel)].filter(x=>(x.textContent||"").trim())[li];
    if(el){ el.classList.add("hp-found"); el.scrollIntoView({block:"center"}); setTimeout(()=>el.classList.remove("hp-found"),2600); } } }
export function helpSearchClear(){ const q=$("#helpQ"); if(q&&q.value){ q.value=""; } const r=$("#helpResults"); if(r){ r.hidden=true; putHTML(r,raw("")); } const p=$("#helpPane"); if(p) p.hidden=false; }
/** Draw the results for what is typed (or the page again when the box is empty). */
export function helpSearchDraw(){ const q=$("#helpQ").value, r=$("#helpResults"), pane=$("#helpPane");
  if(!q.trim()){ helpSearchClear(); return; }
  const res=helpFind(q); pane.hidden=true; r.hidden=false; r.dataset.q=q;
  if(!res.length){ putHTML(r,html`<div class="hp-none" role="status"><b>Nothing in Help for “${q.trim()}”</b><span>Try another word, or ask creaite.</span><button type="button" class="btn primary" id="helpAsk">ask creaite</button></div>`); return; }
  let h=`<p class="hp-resn" role="status">${res.length} result${res.length===1?"":"s"}</p>`;
  HGROUPS.forEach(g=>{ const grp=res.filter(x=>x.e.tab===g); if(!grp.length) return;
    h+=`<section class="hp-resg" aria-label="${esc(HPARTS[g])}"><h3>${esc(HPARTS[g])}</h3>`+grp.map(x=>`<a class="hp-r" href="#help-${esc(x.e.target)}" data-hit="${HIDX.indexOf(x.e)}" data-li="${x.li}"><span class="hp-rt">${esc(x.e.title)}</span><span class="hp-rl">${helpMark(x.line,q)}</span></a>`).join("")+"</section>"; });
  putHTML(r,raw(h)); }
export function helpFocusSearch(){ const q=$("#helpQ"); if(q){ q.focus(); q.select(); } }
/* ⌘K: the tabs, the how-tos and the Reference sections whose title matches, each under "Help" ("Help: Hand over someone's work"),
   then the best three pages that match by a line ("Help: Reference › the matching line"); they appear once two letters are typed,
   and choosing one opens its tab at that place */
export function helpCk(q){ q=q.toLowerCase(); if(q.trim().length<2) return [];
  const hit=(l,h)=>(l+" "+h).toLowerCase().includes(q), out=[], shown=new Set();
  HD.tabs.forEach(t=>{ if(hit("Help: "+t.title,"")) out.push({g:"Help",l:"Help: "+t.title,h:"",fn:()=>go("help",t.id)}); });
  HD.tasks.forEach(t=>{ if(hit("Help: "+t.title,"How do I…")){ shown.add("howto-"+t.id); out.push({g:"Help",l:"Help: "+t.title,h:"How do I…",fn:()=>go("help","howto-"+t.id)}); } });
  HD.sections.forEach(x=>{ if(hit("Help: "+x.title,"Reference")){ shown.add("reference-"+x.id); out.push({g:"Help",l:"Help: "+x.title,h:"Reference",fn:()=>go("help","reference-"+x.id)}); } });
  helpFind(q).filter(r=>!shown.has(r.e.target)&&r.li>=0).slice(0,3).forEach(r=>out.push({g:"Help",l:"Help: "+r.e.title,h:r.e.part+" › "+hPlain(r.line,90),
    fn:()=>{ go("help",r.e.target); helpOpenHit(r.e,r.li); }}));
  return out; }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootHelp0091(){
document.addEventListener("click",e=>{ const l=e.target.closest("#v-help [data-help]:not([role=tab])"); if(!l) return; e.preventDefault(); helpGo(l.dataset.help); });   /* the tabs are the Tabs block's (BL-316) */
document.addEventListener("input",e=>{ if(e.target.id==="helpQ") helpSearchDraw(); });   /* #158: one search over all of Help (replaces the Reference-only filter) */
document.addEventListener("keydown",e=>{ if(e.target.id!=="helpQ") return;
  if(e.key==="Escape"){ if(e.target.value){ e.stopPropagation(); helpSearchClear(); } }
  else if(e.key==="Enter"){ const a=$("#helpResults a.hp-r"); if(a){ e.preventDefault(); a.click(); } } });
document.addEventListener("click",e=>{ const a=e.target.closest("#helpResults a.hp-r"); if(a){ e.preventDefault(); const h=helpIndex()[+a.dataset.hit]; if(h) helpOpenHit(h,+a.dataset.li); return; }
  if(e.target.closest("#helpAsk")){ const q=$("#helpQ").value.trim(); helpSearchClear(); openChat(); const i=$("#chIn"); if(i){ i.value=q; i.dispatchEvent(new Event("input",{bubbles:true})); i.focus(); } } });
}
/* ===== BL-155 (sprint-ux) ===== the key-hint line under Work's and Review's lists shows until the Keys chip was opened once in
   this browser (localStorage creaite-keys-seen). BL-175 (sprint-peek) removed the chip: Help lists the keys (the ? key), and a
   browser that had opened it keeps the line hidden. BL-316: the chip's own popover, which nothing drew any more, is gone. */
export const KEYSK="creaite-keys-seen";
export function keysSeen(){ try{ return localStorage.getItem(KEYSK)==="1"; }catch(e){ return false; } }
/* ===== end BL-155 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootHelp0158(){
if(keysSeen()) document.body.classList.add("keys-seen");
}
/* ===== BL-169 (sprint-polish-2) ===== the "⌘↵ saves and closes · Esc cancels" line shows only when it helps: once a field
   has changed, or, for a new item, once its first field has focus (it opens there). It stays in its place under the fields,
   above the footer, so it never covers a field. Every redraw of the panel hides it again. */
export function pKeysShow(on){ const k=$("#pKeys"); if(k) k.classList.toggle("pkwait",!(on&&shared.EDITING)); }
/* ===== end BL-169 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootHelp0161(){
for(const ev of ["input","change"]) document.addEventListener(ev,e=>{ if(shared.EDITING&&e.target.closest&&e.target.closest("#pFields")) pKeysShow(true); });
document.addEventListener("focusin",e=>{ if(shared.EDITING&&pkNew()&&e.target.closest&&e.target.closest("#pFields")) pKeysShow(true); });
}
/* ===== BL-167 (sprint-polish-2) ===== an unsaved edit in the side panel survives a reload. While an item (or a new action, RAID
   item or decision) is being edited, the fields Alan changed are kept in this browser (localStorage creaite-panel-drafts), per
   item, with when and the item's own updated_at. Nothing goes to the vault until Save. Opening that item again offers
   Restore unsaved changes or Discard; a draft over 7 days old, or for an item changed since, is dropped with a note. Save,
   Cancel, Esc and Close end the edit and drop its draft, as before; only a reload (or a closed tab) keeps it. */
export function pdKeyOf(){ if(!shared.CUR||!["actions","raid","decisions"].includes(shared.CUR.k)) return null; return shared.CUR.mode==="record"?`${shared.CUR.k}:${shared.CUR.id}`:shared.CUR.mode==="new"?`new:${shared.CUR.k}`:null; }
export function pdRaw(){ const o={}; $$("#pFields [name]").forEach(el=>{ o[el.name]=el.type==="checkbox"?el.checked:el.value; }); return o; }
export function pdStamp(){ const x=shared.CUR&&shared.CUR.mode==="record"?REC(shared.CUR.k,shared.CUR.id):null; return x?String(x.updated_at||x.upd_at||""):""; }
export function pdDrop(key){ if(!key) return; const a=pdAll(); if(key in a){ delete a[key]; pdPut(a); } }
export function pdWrite(){ clearTimeout(shared.PDT); shared.PDT=null; if(!shared.EDITING||!shared.PDKEY||shared.PDKEY!==pdKeyOf()||!shared.PDBASE) return; const now=pdRaw(), ch={};
  for(const n of Object.keys(now)) if(n in shared.PDBASE&&now[n]!==shared.PDBASE[n]) ch[n]=now[n];
  const a=pdAll(); if(!Object.keys(ch).length){ if(shared.PDKEY in a){ delete a[shared.PDKEY]; pdPut(a); } return; }
  a[shared.PDKEY]={fields:ch,at:Date.now(),base:pdStamp()};
  Object.keys(a).sort((p,q)=>a[q].at-a[p].at).slice(30).forEach(k=>delete a[k]); pdPut(a); }   /* the 30 most recent */
export const pdWhen=t=>{ const d=new Date(t), z=n=>String(n).padStart(2,"0"); return `${z(d.getDate())}-${z(d.getMonth()+1)}-${d.getFullYear()} ${z(d.getHours())}:${z(d.getMinutes())}`; };
export function pdBar(html){ let b=$("#pDraft"); if(!b){ addHTML($("#pBody"),"afterbegin",raw('<div class="pdraft" id="pDraft" role="status" hidden></div>')); b=$("#pDraft"); }
  putHTML(b,raw(html||"")); b.hidden=!html; }
export function pdOffer(){ const key=pdKeyOf(); if(!key){ pdBar(""); shared.PDOFFER=null; return; }
  if(shared.PDOFFER&&shared.PDOFFER.key===key){ pdBar(shared.PDOFFER.html); return; }
  const d=pdAll()[key]; if(!d){ pdBar(""); shared.PDOFFER=null; return; }
  const what=shared.CUR.mode==="record"?shared.CUR.id:"this new item", when=pdWhen(d.at), n=Object.keys(d.fields).length;
  const why=Date.now()-d.at>PDAGE?"they are more than 7 days old":(shared.CUR.mode==="record"&&d.base!==pdStamp())?`${shared.CUR.id} has changed since`:"";
  let html;
  if(why){ pdDrop(key); html=`<span class="t">Unsaved changes to ${esc(what)} from ${when} were dropped: ${esc(why)}.</span><button type="button" class="btn" data-pd="ok">OK</button>`; }
  else html=`<span class="t">Unsaved changes to ${esc(what)} from ${when} (${n} field${n===1?"":"s"}), kept in this browser.</span><button type="button" class="btn primary" data-pd="restore">Restore unsaved changes</button><button type="button" class="btn" data-pd="discard">Discard</button>`;
  shared.PDOFFER={key,html,note:!!why}; pdBar(html); }
export function pdRestore(){ const key=pdKeyOf(), d=key&&pdAll()[key]; if(!d) return; shared.PDOFFER=null; pdBar("");
  if(!shared.EDITING){ shared.EDITING=true; drawPanel(); }
  // @ts-expect-error TS2362: true and false subtract as 1 and 0 (the project sorts first)
  const names=Object.keys(d.fields).sort((p,q)=>(q==="p")-(p==="p"));   /* the project first: the workstream list follows it */
  for(const n of names){ const el=$(`#pFields [name="${CSS.escape(n)}"]`); if(!el) continue; el.closest("details")?.setAttribute("open","");
    if(el.type==="checkbox") el.checked=!!d.fields[n]; else el.value=d.fields[n];
    el.dispatchEvent(new Event("input",{bubbles:true})); el.dispatchEvent(new Event("change",{bubbles:true})); }
  pdWrite(); $(`#pFields [name="${CSS.escape(names[0]||"t")}"]`)?.focus(); snack("Unsaved changes restored. Save to keep them"); }
/* ===== end BL-167 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootHelp0162(){
document.addEventListener("click",e=>{ const b=e.target.closest("[data-pd]"); if(!b) return; const a=b.dataset.pd, key=pdKeyOf();
  if(a==="restore") pdRestore(); else { if(a==="discard"){ pdDrop(key); snack("Unsaved changes discarded"); } shared.PDOFFER=null; pdBar(""); } });
for(const ev of ["input","change"]) document.addEventListener(ev,e=>{ if(!shared.EDITING||!shared.PDKEY||!(e.target.closest&&e.target.closest("#pFields"))) return;
  if(shared.PDOFFER&&shared.PDOFFER.key===shared.PDKEY&&!shared.PDOFFER.note){ shared.PDOFFER=null; pdBar(""); }   /* typing afresh replaces the old draft */
  clearTimeout(shared.PDT); shared.PDT=setTimeout(pdWrite,250); });
addEventListener("pagehide",()=>{ if(shared.PDT) pdWrite(); });
}

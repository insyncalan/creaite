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
import { rvHintHtml } from "./review.js";
import { hit, layoutOf, workHint } from "./work.js";
/* ===== Help (BL-84) ===== */
/* Three tabs from help.md (built by build_dashboard.help_sections): Start here, How do I… and Reference. Each has an
   address (#help-start, #help-howto, #help-howto-<task>, #help-reference, #help-reference-<section>), so Back and
   Forward work; "?" opens the tab used last. */
export const HD=D.help&&D.help.tabs?D.help:{tabs:[],tasks:[],sections:[]}, HTABS=HD.tabs.map(t=>t.id);
shared.HELPARG="start";
export function helpNorm(a){ a=String(a||""); const i=a.indexOf("-"), tab=i<0?a:a.slice(0,i), rest=i<0?"":a.slice(i+1);
  if(!HTABS.includes(tab)) return null;
  if(rest&&!(tab==="howto"?HD.tasks:tab==="reference"?HD.sections:[]).some(x=>x.id===rest)) return tab;
  return rest?`${tab}-${rest}`:tab; }
export function renderHelp(arg){ if(!HD.tabs.length){ putHTML($("#helpPane"),html`<div class="hp-wrap"><p>Help isn’t available: system/templates/help.md is missing.</p></div>`); return; }
  const a=helpNorm(arg)||helpNorm(store.get("creaite-help-tab","start"))||HTABS[0], i=a.indexOf("-"), tab=i<0?a:a.slice(0,i), rest=i<0?"":a.slice(i+1), changed=!$("#helpPane").dataset.tab||$("#helpPane").dataset.tab!==tab;
  shared.HELPARG=a; store.set("creaite-help-tab",tab);
  drawTabs($("#helpTabsHost"),{items:HD.tabs.map(t=>({id:t.id,label:t.title,tabId:"htab-"+t.id,data:{help:t.id}})),selected:tab,onSelect:helpGo,label:"Help",className:"tabs",id:"helpTabs",wrap:true});   /* BL-316: the Tabs block */
  if(changed){ const html=HD.tabs.find(t=>t.id===tab).html.replace("<p>[start command]</p>",cmdBox());
    putHTML($("#helpPane"),raw(`<div class="hp-wrap hp-${tab}">${html}</div>`)); $("#helpPane").dataset.tab=tab; $("#helpPane").setAttribute("aria-labelledby","htab-"+tab); }
  $$("#helpPane .hp-task").forEach(t=>t.classList.toggle("hp-hl",!!rest&&tab==="howto"&&t.dataset.task===rest));
  $$("#helpPane .hp-refidx a").forEach(l=>l.toggleAttribute("aria-current",tab==="reference"&&l.dataset.help==="reference-"+rest));
  const target=rest?(tab==="howto"?document.getElementById("ht-"+rest):document.getElementById("hr-"+rest)):null;
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
/* ⌘K: every task and reference section is an entry under "Help" ("Help: Hand over someone's work"); they appear once two
   letters are typed, and choosing one opens its tab at that place */
export function helpCk(q){ q=q.toLowerCase(); if(q.trim().length<2) return [];
  const hit=(l,h)=>(l+" "+h).toLowerCase().includes(q), out=[];
  HD.tabs.forEach(t=>{ if(hit("Help: "+t.title,"")) out.push({g:"Help",l:"Help: "+t.title,h:"",fn:()=>go("help",t.id)}); });
  HD.tasks.forEach(t=>{ if(hit("Help: "+t.title,"How do I…")) out.push({g:"Help",l:"Help: "+t.title,h:"How do I…",fn:()=>go("help","howto-"+t.id)}); });
  HD.sections.forEach(x=>{ if(hit("Help: "+x.title,"Reference")) out.push({g:"Help",l:"Help: "+x.title,h:"Reference",fn:()=>go("help","reference-"+x.id)}); });
  return out; }
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootHelp0091(){
document.addEventListener("click",e=>{ const l=e.target.closest("#v-help [data-help]:not([role=tab])"); if(!l) return; e.preventDefault(); helpGo(l.dataset.help); });   /* the tabs are the Tabs block's (BL-316) */
document.addEventListener("input",e=>{ if(e.target.id!=="helpQ") return; const q=e.target.value.toLowerCase().trim(); $$("#helpPane .hp-ref").forEach(s=>s.classList.toggle("hidden",!!q&&!s.textContent.toLowerCase().includes(q))); });
}
/* ===== BL-155 (sprint-ux) ===== the key-hint line becomes a Keys chip. Work and Review each get a small Keys chip at the end of
   their toolbar; it shows the same hints (workHint for the layout in use, rvHintHtml) in a popover, and Help's keyboard shortcuts
   (the ? key) list them too. The permanent line under the list shows, as before, until the chip has been opened once in this
   browser (localStorage creaite-keys-seen); from then on the hints are one tap away instead of always on screen. */
export const KEYSK="creaite-keys-seen";
export function keysSeen(){ try{ return localStorage.getItem(KEYSK)==="1"; }catch(e){ return false; } }
export function keysMark(){ try{ localStorage.setItem(KEYSK,"1"); }catch(e){} document.body.classList.add("keys-seen"); }
export function keysChip(where,after){ const host=document.querySelector(after); if(!host||$("#"+where+"Keys")) return;
  addHTML(host,"afterend",html`<span class="dd keysdd"><button type="button" class="btn keyschip" id="${raw(where)}Keys" aria-haspopup="dialog" aria-expanded="false" aria-controls="${raw(where)}KeysMenu" title="Keyboard keys for this list">Keys</button><div class="ddmenu keysmenu" id="${raw(where)}KeysMenu" role="dialog" aria-label="Keys" hidden></div></span>`); }
/* BL-175 (sprint-peek): no Keys chip on Work or Review any more; Help lists the keys */
export function keysHtml(where){ const h=where==="w"?((layoutOf(shared.WT)==="board"?$("#whintBoard"):$("#whintList")).innerHTML||workHint(layoutOf(shared.WT))):($("#rvHint").innerHTML||String(rvHintHtml()));   /* the line's own words (All items has its own) */
  return `<h3>Keys</h3><ul>${h.split(" · ").map(x=>`<li>${x}</li>`).join("")}</ul><p class="sub">Press <span class="kbd">?</span> for every shortcut.</p>`; }
export function keysClose(){ $$(".keysmenu").forEach(m=>{ m.hidden=true; m.classList.remove("on"); m.previousElementSibling.setAttribute("aria-expanded","false"); }); }
/* ===== end BL-155 ===== */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootHelp0158(){
if(keysSeen()) document.body.classList.add("keys-seen");
document.addEventListener("click",e=>{ const b=e.target.closest(".keyschip");
  if(b){ e.stopPropagation(); const where=b.id.replace(/Keys$/,""), m=$("#"+where+"KeysMenu"), was=!m.hidden; keysClose(); if(was) return;
    putHTML(m,raw(keysHtml(where))); m.hidden=false; m.classList.add("on"); b.setAttribute("aria-expanded","true"); keysMark(); return; }
  if(!e.target.closest(".keysmenu")) keysClose(); });
document.addEventListener("keydown",e=>{ if(e.key==="Escape"&&$$(".keysmenu").some(m=>!m.hidden)){ e.preventDefault(); e.stopPropagation(); const open=$$(".keysmenu").find(m=>!m.hidden); keysClose(); open?.previousElementSibling?.focus(); } },true);
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

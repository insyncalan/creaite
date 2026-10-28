// @ts-check
/* helpPanel.js (#158 Phase B part 4): the ? key's panel, the quiet foot line on the eight screens, and the "How <screen> works"
   link in their empty states. The lists are `Screen:` lines in help.md (D.help.screens); none of it is a button beside a title.
   - ? opens a panel on the right (ask creaite's side; opening one closes the other) with two to five jobs for the screen, a link
     to the screen's Reference page and "Search all of Help". Esc closes it (it is a layer: it closes before a peek or a
     highlight does) and puts focus back where it was. On a screen with no list, ? opens Help on the tab used last.
   - ? never fires while typing in a field, an editor, a dialog or anything editable (core/keys.js checks that before it asks). */
import { closeChat } from "./ask.js";
import { $, $$, addHTML, esc, ic, putHTML, raw } from "./core/dom.js";
import { go } from "./core/nav.js";
import { S, store } from "./core/page.js";
import { shared } from "./core/state.js";
import { HD, helpSearchFocus } from "./help.js";

/* the view that is each screen, and its name in help.md's Screen: lines */
export const SCREENS={today:"Today",work:"Work",mine:"Work",review:"Review",projects:"Projects",cockpit:"Projects",people:"People",notes:"Notes",inbox:"Intake",files:"Files"};
export const SCREEN_VIEWS={Today:"v-today",Work:"v-work",Review:"v-review",Projects:"v-projects v-cockpit",People:"v-people",Notes:"v-notes",Intake:"v-inbox",Files:"v-files"};
export const screenNow=()=>{ const s=SCREENS[shared.VIEW]; return s&&HD.screens&&HD.screens[s]?s:null; };
let HFROM=/** @type {HTMLElement|null} */(null);
export const helpPanelIsOpen=()=>!!$("#hpanel")&&$("#hpanel").classList.contains("on");
export function helpPanelDraw(screen){ const sc=HD.screens[screen], title=id=>(HD.tasks.find(t=>t.id===id)||{}).title||id, ref=HD.sections.find(x=>x.id===sc.ref);
  putHTML($("#hpanel"),raw(`<div class="hpn-h"><h2 id="hpnT" tabindex="-1">Help with ${esc(screen)}</h2><button type="button" class="ib" data-hp-close aria-label="Close help (Esc)">${ic("x")}</button></div>
    <div class="hpn-b"><p class="hpn-k">Jobs on this screen</p><ul class="hpn-jobs">${sc.jobs.map(id=>`<li><a href="#help-howto-${esc(id)}" data-hp-go="howto-${esc(id)}">${esc(title(id))}</a></li>`).join("")}</ul>
    ${ref?`<p><a class="hpn-ref" href="#help-reference-${esc(ref.id)}" data-hp-go="reference-${esc(ref.id)}">Read how ${esc(screen)} works</a></p>`:""}
    <p><button type="button" class="btn" data-hp-search>Search all of Help</button></p></div>
    <p class="hpn-f">Esc closes this.</p>`)); }
export function helpPanelOpen(screen){ closeChat(); helpPanelDraw(screen); const f=document.activeElement;
  HFROM=f&&f!==document.body&&!$("#hpanel").contains(f)?/** @type {HTMLElement} */(f):null;
  $("#hpanel").classList.add("on"); $("#hpnT").focus(); }
/** Close the panel; `restore` puts focus back where it was before the ? (Esc does; a click elsewhere does not). */
export function helpPanelClose(restore=true){ const p=$("#hpanel"); if(!p||!p.classList.contains("on")) return false; p.classList.remove("on");
  const back=HFROM; HFROM=null; if(restore&&back&&back.isConnected) back.focus(); else if(p.contains(document.activeElement)) /** @type {HTMLElement} */(document.activeElement).blur(); return true; }
/** The ? key: toggles the panel on a screen with a list; anywhere else opens Help on the tab used last. */
export function helpKey(){ if(helpPanelIsOpen()){ helpPanelClose(true); return; } const s=screenNow(); if(s) helpPanelOpen(s); else go("help"); }
/* ---- the foot line and the empty-state links, kept in place as the screens redraw ---- */
export function footHTML(screen){ return `Press <kbd>?</kbd> for help with ${esc(screen)}`; }
const OPENS="Nothing,No ".split(",");
export function helpDecor(){ for(const [screen,ids] of Object.entries(SCREEN_VIEWS)){ const sc=HD.screens&&HD.screens[screen]; if(!sc) continue;
  for(const id of ids.split(" ")){ const sec=document.getElementById(id); if(!sec) continue;
    let f=/** @type {HTMLElement|null} */(sec.querySelector(":scope>.hfoot"));
    if(!f){ f=document.createElement("p"); f.className="hfoot"; putHTML(f,raw(footHTML(screen))); sec.append(f); } else if(sec.lastElementChild!==f) sec.append(f);
    if(sc.ref) $$(".empty,.none",sec).forEach(e=>{ if(e.querySelector(".hp-how")||e.closest(".hp-how")) return; const t=(e.textContent||"").trim();
      if(t.length<8||!OPENS.some(o=>t.startsWith(o))||/matches/.test(t)) return;
      addHTML(e,"beforeend",raw(` <a class="hp-how" href="#help-reference-${esc(sc.ref)}" data-hp-go="reference-${esc(sc.ref)}">How ${esc(screen)} works</a>`)); }); } } }
/* ---- the first-visit line (#158 part 5): once per screen, under the page title, "Press ? for help with <screen>" ---- */
export const LINEK="creaite-help-line-seen";
const LINEMEM=new Set();            /* if storage fails, once per page load */
const lineSeen=screen=>LINEMEM.has(screen)||(store.get(LINEK,[])||[]).includes(screen);
const lineMark=screen=>{ LINEMEM.add(screen); store.set(LINEK,[...new Set([...(store.get(LINEK,[])||[]),screen])]); };
const typingNow=()=>{ const a=document.activeElement; return !!a&&(/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)||/** @type {HTMLElement} */(a).isContentEditable); };
/** Something is open that the line waits for: an item, a dialog, ask creaite, the ? panel, an editing session or a field. */
export function lineBlocked(){ return $("#panel").classList.contains("on")||!!document.querySelector("dialog[open]")||$("#chat").classList.contains("on")
  ||helpPanelIsOpen()||!!shared.EDITING||!!shared.LOADING||typingNow(); }
export function lineClear(){ $$(".hline").forEach(e=>e.remove()); }
export function lineMaybe(){ const screen=screenNow(); if(!screen||!S.pressLine||lineSeen(screen)||lineBlocked()) return false;
  const sec=$(".view:not([hidden])"); if(!sec||sec.querySelector(".hline")) return false; const h1=sec.querySelector("h1"); if(!h1||!h1.offsetParent) return false;
  const anchor=h1.closest(".hhead")||h1, p=document.createElement("p"); p.className="hline"; p.setAttribute("role","note"); putHTML(p,raw(footHTML(screen)));
  anchor.insertAdjacentElement("afterend",p); lineMark(screen); return true; }
let QUEUED=false;
export const helpLineSoon=()=>queue();
const queue=()=>{ if(QUEUED) return; QUEUED=true; requestAnimationFrame(()=>{ QUEUED=false; helpDecor(); lineMaybe(); }); };
export function bootHelpPanel(){
/* the line clears on any key or click and never swallows it (these listeners only look); ? clears it too, and keys.js opens the panel */
for(const ev of ["keydown","mousedown"]) document.addEventListener(ev,()=>lineClear(),true);
/* and it waits for what is open to close: ask creaite, the ? panel, an item, a dialog, a field in use */
{ const retry=()=>queue(); const mo=new MutationObserver(retry); for(const id of ["panel","chat","hpanel"]){ const n=document.getElementById(id); if(n) mo.observe(n,{attributes:true,attributeFilter:["class"]}); }
  document.addEventListener("close",retry,true); document.addEventListener("focusout",retry,true); }
document.addEventListener("click",e=>{ const t=/** @type {Element} */(e.target); const g=t.closest&&t.closest("[data-hp-go]");
  if(g){ e.preventDefault(); helpPanelClose(false); go("help",/** @type {HTMLElement} */(g).dataset.hpGo); return; }
  if(t.closest&&t.closest("[data-hp-close]")){ helpPanelClose(true); return; }
  if(t.closest&&t.closest("[data-hp-search]")){ helpPanelClose(false); go("help"); helpSearchFocus(); } });
document.addEventListener("mousedown",e=>{ if(helpPanelIsOpen()&&!(/** @type {Element} */(e.target)).closest("#hpanel")) helpPanelClose(false); },true);
if(HD.screens){ const mo=new MutationObserver(queue); for(const ids of Object.values(SCREEN_VIEWS)) for(const id of ids.split(" ")){ const s=document.getElementById(id); if(s) mo.observe(s,{childList:true,subtree:true}); }
  helpDecor(); }
}

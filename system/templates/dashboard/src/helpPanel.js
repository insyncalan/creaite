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
let QUEUED=false;
const queue=()=>{ if(QUEUED) return; QUEUED=true; requestAnimationFrame(()=>{ QUEUED=false; helpDecor(); }); };
export function bootHelpPanel(){
document.addEventListener("click",e=>{ const t=/** @type {Element} */(e.target); const g=t.closest&&t.closest("[data-hp-go]");
  if(g){ e.preventDefault(); helpPanelClose(false); go("help",/** @type {HTMLElement} */(g).dataset.hpGo); return; }
  if(t.closest&&t.closest("[data-hp-close]")){ helpPanelClose(true); return; }
  if(t.closest&&t.closest("[data-hp-search]")){ helpPanelClose(false); go("help"); helpSearchFocus(); } });
document.addEventListener("mousedown",e=>{ if(helpPanelIsOpen()&&!(/** @type {Element} */(e.target)).closest("#hpanel")) helpPanelClose(false); },true);
if(HD.screens){ const mo=new MutationObserver(queue); for(const ids of Object.values(SCREEN_VIEWS)) for(const id of ids.split(" ")){ const s=document.getElementById(id); if(s) mo.observe(s,{childList:true,subtree:true}); }
  helpDecor(); }
}

// @ts-check
/* core/keys.js (BL-231 step 2b): the copy-command buttons, closing on an outside click, and the keyboard.
   Moved from script/ unchanged, apart from `export`, `shared.` for the shared state (state.js) and the steps that ran at load,
   which are now boot…() functions called by src/main.js in today's order. Pieces: 0122-after-bl-158-theme.js, 0123-keyboard.js */
import { closeChat, openChat, openCk } from "../ask.js";
import { openCapture } from "../components/notes/CaptureDrawer.jsx";
import { REV } from "./data.js";
import { $, $$ } from "./dom.js";
import { closeCal } from "./fields.js";
import { go, switchProject } from "./nav.js";
import { copied, MAC, START_CMD } from "./page.js";
import { snack } from "./server.js";
import { shared } from "./state.js";
import { openProposal } from "../panel.js";
import { closePanel } from "../projects.js";
import { CHK, decide, isMin, renderReview, RHL, rjKey315, rvSyncChk, toggleGroup } from "../review.js";
import { dayKey } from "../today.js";
import { HL, hlClear, hlKey, openDisp, rvOnly, rvPaint } from "../work.js";
/* click outside closes ask creaite and the detail panel — never while editing */
export const OPENERS="[data-person],#inPrev,[data-gen],#genDlg,[data-nav],[data-proj],[data-psw],#projSw,#runBadge,[data-row],[data-open],[data-revopen],[data-appr],#reviewBody tr,#askBtn,[data-ask],[data-edcur],[data-edproj],[data-ms],[data-msnew],#newBtn,#newMenu,[data-gowork],.snack,.cal,.combo-list,dialog,[data-mg],#chat,#pkStage,.pkpop,#tip,#capDrawer";   /* BL-176: working in ask creaite, the staging pill or a picker leaves the peek open */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0122's place) */
export function bootCopyCommand(){
/* copy the start command */
document.addEventListener("click",e=>{ const b=e.target.closest("[data-copycmd]"); if(!b) return; e.preventDefault();
  const done=()=>{ copied(b); snack("Command copied — paste it into Terminal"); };   /* BL-136: the drawn tick and "Copied" */
  if(navigator.clipboard) navigator.clipboard.writeText(START_CMD).then(done,()=>prompt("Copy this command:",START_CMD)); else prompt("Copy this command:",START_CMD); });
$("#alertCmd").textContent=START_CMD;
document.addEventListener("mousedown",e=>{
  if(e.target.closest(".snack,.cal,dialog")) return;
  if($("#chat").classList.contains("on")&&!e.target.closest("#chat")&&!e.target.closest("#askBtn,[data-ask],#panel.peek,.pkpop,#pkStage,#errBanner,#mvPeek,#mvCal,#mvPop")) closeChat();   /* BL-176: the peek stays usable beside the chat; fix-peek-140: so does the errors banner (closing the chat under the pointer moved its buttons) */
  if($("#panel").classList.contains("on")&&!e.target.closest("#panel")&&!e.target.closest(OPENERS)){
    if(shared.EDITING){ snack(shared.CUR&&shared.CUR.mode==="record"?"You're editing — save or cancel first":"Finish or cancel this first"); $("#pFoot").animate([{transform:"translateX(0)"},{transform:"translateX(-4px)"},{transform:"translateX(4px)"},{transform:"translateX(0)"}],{duration:220}); return; }
    closePanel(); } },true);
}
/* ======================= keyboard ======================= */
export const typing=()=>{ const a=document.activeElement; return a&&(/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)||a.isContentEditable); };
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0123's place) */
export function bootKeyboard(){
document.addEventListener("keydown",e=>{
  if((e.metaKey||e.ctrlKey)&&e.shiftKey&&!e.altKey&&e.key.toLowerCase()==="n"){ e.preventDefault(); openCapture(); return; }   /* BL-301 C: a note, from any page */
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){ e.preventDefault(); openCk(); return; }
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="j"){ e.preventDefault(); $("#chat").classList.contains("on")?closeChat():openChat(); return; }
  if(e.key==="Escape"){ if($("#cmdk").open||$("#boardDlg").open) return; if(shared.CAL){ closeCal(); return; } if(HL.size&&(shared.VIEW==="work"||shared.VIEW==="person")){ hlClear(); return; } if(shared.VIEW==="review"&&(RHL.size||CHK.size)&&!$("#panel").classList.contains("on")){ RHL.clear(); CHK.clear(); renderReview(); return; } if($("#panel").classList.contains("on")){ closePanel(); return; } if($("#chat").classList.contains("on")){ closeChat(); return; } return; }
  if(typing()||e.metaKey||e.ctrlKey||e.altKey) return;
  if(e.key==="/"){ e.preventDefault(); openChat(); return; }
  if((e.key==="n"||e.key==="N")&&!e.shiftKey&&!document.querySelector("dialog[open]")){ e.preventDefault(); openCapture(); return; }   /* BL-301 C (Alan, 14-10-2026): N, the second key for a note: ⌘⇧N is Chrome's incognito window in an ordinary tab */   /* / is always ask creaite, on every page (Alan, 2026-10-09) */
  if((e.key==="f"||e.key==="F")&&(shared.VIEW==="work"||shared.VIEW==="mine")){ e.preventDefault(); if(!$("#moreMenu").classList.contains("on")) $("#moreBtn")?.click(); $("#fpq")?.focus(); return; }   /* BL-130: F opens the field picker */
  if((e.key==="d"||e.key==="D")&&(shared.VIEW==="work"||shared.VIEW==="mine")){ e.preventDefault(); openDisp(); return; }   /* BL-128 */
  if(e.key==="?"){ e.preventDefault(); go("help"); return; }
  if((e.key==="["||e.key==="]")&&shared.VIEW==="cockpit"){ e.preventDefault(); switchProject(e.key==="]"?1:-1); return; }
  if(["[","]","t","T"].includes(e.key)&&shared.VIEW==="today"&&dayKey(e)){ e.preventDefault(); return; }   /* BL-293: [ ] step a day, T back to today */
  if((shared.VIEW==="work"||shared.VIEW==="mine"||shared.VIEW==="person")&&!(shared.VIEW==="person"&&shared.HAND)&&hlKey(e)) return;   /* BL-122: J K move the cursor, Shift extends, Space toggles, Enter and E open */
  /* BL-176 (sprint-peek): no E to edit the open item: the peek is always editable. Review keeps its own E below */
  if(shared.VIEW==="review"){ const trs=$$("#reviewBody tr[data-n]"); if(!trs.length) return; shared.RSEL=Math.max(0,Math.min(shared.RSEL,trs.length-1));   /* BL-133: a cursor past the end after a re-render */
    if((e.key==="Enter"||e.key===" ")&&e.target.closest&&e.target.closest("button,a,input,select,textarea,.bmenu")) return;   /* a focused control does its own job */ if(e.key==="j"){ shared.RSEL=Math.min(shared.RSEL+1,trs.length-1); renderReview(); } else if(e.key==="k"){ shared.RSEL=Math.max(shared.RSEL-1,0); renderReview(); }
    else if(e.key==="Enter"){ e.preventDefault(); const n=+trs[shared.RSEL].dataset.n; rvOnly(n); openProposal(n); rvPaint(); }
    else if(e.key===" "){ e.preventDefault(); const n=+trs[shared.RSEL].dataset.n, r=REV.find(x=>x.n===n); if(r&&!r.done){ RHL.has(n)?(RHL.delete(n),CHK.delete(n)):(RHL.add(n),r.indiv||CHK.add(n)); rvPaint(); } }
    else if(["a","r","x","e"].includes(e.key)){ const n=+trs[shared.RSEL].dataset.n, r=REV.find(x=>x.n===n); if(e.key==="e"){ e.preventDefault(); openProposal(n); return; } if(r.done) return; if(e.key==="a") decide(n,"approved"); if(e.key==="r"){ e.preventDefault(); rjKey315(); }   /* BL-315: R opens the reasons menu (minutes, reports and file changes are rejected as before) */ if(e.key==="x"&&isMin(r)){ toggleGroup(r,trs[shared.RSEL].dataset.g); return; } if(e.key==="x"){ RHL.has(n)?RHL.delete(n):RHL.add(n); rvSyncChk(); renderReview(); } } }   /* BL-133: X is Space: any proposed item can be selected */
});
if(!MAC) $("#kK").textContent="Ctrl K";
}

// @ts-check
/* core/keys.js (BL-231 step 2b): the copy-command buttons, closing on an outside click, and the keyboard.
   Moved from script/ unchanged, apart from `export`, `shared.` for the shared state (state.js) and the steps that ran at load,
   which are now boot…() functions called by src/main.js in today's order. Pieces: 0122-after-bl-158-theme.js, 0123-keyboard.js */
import { closeChat, openChat, openCk } from "../ask.js";
import { openCapture } from "../components/notes/CaptureDrawer.jsx";
import { $ } from "./dom.js";
import { closeCal } from "./fields.js";
import { go, switchProject } from "./nav.js";
import { closeHelpPanel, helpOutsidePress, helpPanelOpen, openHelpPanel, screenKey } from "../helpscreen.js";
import { helpFocusSearch } from "../help.js";
import { copied, MAC, START_CMD } from "./page.js";
import { snack } from "./server.js";
import { shared } from "./state.js";
import { closePanel } from "../projects.js";
import { dayKey } from "../today.js";
import { HL, hlClear, hlKey, openDisp } from "../work.js";
/* click outside closes ask creaite and the detail panel — never while editing */
export const OPENERS="[data-person],#inPrev,[data-gen],#genDlg,[data-nav],[data-proj],[data-psw],#projSw,#runBadge,[data-row],[data-open],[data-revopen],[data-appr],#askBtn,[data-ask],[data-edcur],[data-edproj],[data-ms],[data-msnew],#newBtn,[role=menu],[data-gowork],.snack,.cal,.combo-list,dialog,[data-mg],#chat,#pkStage,.pkpop,#tip,#capDrawer,.linkpop,.linkcorner";   /* #121: the link form and the field's corner button sit outside the peek and must not close it */   /* BL-176: working in ask creaite, the staging pill or a picker leaves the peek open */
/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0122's place) */
export function bootCopyCommand(){
/* copy the start command */
document.addEventListener("click",e=>{ const b=e.target.closest("[data-copycmd]"); if(!b) return; e.preventDefault();
  const done=()=>{ copied(b); snack("Command copied — paste it into Terminal"); };   /* BL-136: the drawn tick and "Copied" */
  if(navigator.clipboard) navigator.clipboard.writeText(START_CMD).then(done,()=>prompt("Copy this command:",START_CMD)); else prompt("Copy this command:",START_CMD); });
$("#alertCmd").textContent=START_CMD;
document.addEventListener("mousedown",e=>{
  helpOutsidePress(e);   /* #249: a press outside the ? panel closes it (not on its opener, not in a layer above it) */
  if(e.target.closest(".snack,.cal,dialog")) return;
  if(HL.size&&(shared.VIEW==="work"||shared.VIEW==="person")&&!e.target.closest(OPENERS)&&!e.target.closest("#wbulk,#panel,#workTbl tr,#v-person tr,.bcard,button,a,input,select,textarea,label,[role=menu],[role=option],[role=dialog],.ddmenu,.ms-menu")) hlClear();   /* #108 (Alan, 15-10-2026): a click outside clears a bulk selection too; the rows, the bulk bar, its menus and any control stay as they were */
  if($("#chat").classList.contains("on")&&!e.target.closest("#chat")&&!e.target.closest("#askBtn,[data-ask],#panel.peek,.pkpop,#pkStage,#errBanner,#mvPeek,#mvCal,#mvPop")) closeChat();   /* BL-176: the peek stays usable beside the chat; fix-peek-140: so does the errors banner (closing the chat under the pointer moved its buttons) */
  if($("#panel").classList.contains("on")&&!e.target.closest("#panel")&&!e.target.closest(OPENERS)){
    if(shared.EDITING){ snack(shared.CUR&&shared.CUR.mode==="record"?"You're editing — save or cancel first":"Finish or cancel this first"); $("#pFoot").animate([{transform:"translateX(0)"},{transform:"translateX(-4px)"},{transform:"translateX(4px)"},{transform:"translateX(0)"}],{duration:220}); return; }
    closePanel(); } },true);
}
/* ======================= keyboard ======================= */
export const typing=()=>{ const a=document.activeElement; return a&&(/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)||a.isContentEditable||!!a.closest?.('.ddmenu [role="option"]')); };   /* BL-316: an option of a filter list takes keys, as its tick box did */

/* BL-231: what this block did at load, run in today's order by src/main.js (piece 0123's place) */
export function bootKeyboard(){
document.addEventListener("keydown",e=>{
  if((e.metaKey||e.ctrlKey)&&e.shiftKey&&!e.altKey&&e.key.toLowerCase()==="n"){ e.preventDefault(); openCapture(); return; }   /* BL-301 C: a note, from any page */
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){ e.preventDefault(); openCk(); return; }   /* #122: ⌘K is the palette, Shift or not; inside a rich editor ⌘⇧K is the link form, caught first (components/EditorBar.jsx) */
  if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="j"){ e.preventDefault(); $("#chat").classList.contains("on")?closeChat():openChat(); return; }
  if(e.key==="Escape"){ if(shared.CAL){ closeCal(); return; } if(document.querySelector("dialog:modal")) return;   /* a modal dialog takes Esc itself (#cmdk, #boardDlg, #llDlg): the peek behind it stays; a calendar open inside it closes first */ if(helpPanelOpen()){ closeHelpPanel(); return; }   /* #158: the ? panel closes first, and focus goes back */ const pk=$("#panel").classList.contains("on");   /* #161: with a peek open, one Esc clears the highlight and closes the peek when the highlight is only the row the peek shows (or empty); with two or more rows highlighted the first Esc clears the selection and the peek stays */
  if(HL.size&&(shared.VIEW==="work"||shared.VIEW==="person")){ const one=HL.size===1&&(!shared.CUR||shared.CUR.mode!=="record"||HL.has(shared.CUR.id)); hlClear(); if(pk&&one) closePanel(); return; }   /* #108: Esc from a peek opened from a row clears the row and closes the peek together, so no row stays highlighted */ if($("#panel").classList.contains("on")){ closePanel(); return; } if($("#chat").classList.contains("on")){ closeChat(); return; } return; }
  if(typing()||e.metaKey||e.ctrlKey||e.altKey) return;
  if(e.key==="/"){ e.preventDefault(); if(shared.VIEW==="help"){ helpFocusSearch(); return; } openChat(); return; }   /* #158: in Help, / is the search box */
  if((e.key==="n"||e.key==="N")&&!e.shiftKey&&!document.querySelector("dialog[open]")){ e.preventDefault(); openCapture(); return; }   /* BL-301 C (Alan, 14-10-2026): N, the second key for a note: ⌘⇧N is Chrome's incognito window in an ordinary tab */   /* / is always ask creaite, on every page (Alan, 2026-10-09) */
  if((e.key==="f"||e.key==="F")&&(shared.VIEW==="work"||shared.VIEW==="mine")){ e.preventDefault(); if(!$("#moreMenu").classList.contains("on")) $("#moreBtn")?.click(); $("#fpq")?.focus(); return; }   /* BL-130: F opens the field picker */
  if((e.key==="d"||e.key==="D")&&(shared.VIEW==="work"||shared.VIEW==="mine")){ e.preventDefault(); openDisp(); return; }   /* BL-128 */
  if(e.key==="?"){ e.preventDefault(); if(document.querySelector("dialog[open]")) return; if(helpPanelOpen()){ closeHelpPanel(); return; } if(!openHelpPanel(screenKey())) go("help"); return; }   /* #158: a panel on the jobs for this screen; no list: Help, on the tab used last */
  if((e.key==="["||e.key==="]")&&shared.VIEW==="cockpit"){ e.preventDefault(); switchProject(e.key==="]"?1:-1); return; }
  if(["[","]","t","T"].includes(e.key)&&shared.VIEW==="today"&&dayKey(e)){ e.preventDefault(); return; }   /* BL-293: [ ] step a day, T back to today */
  if((shared.VIEW==="work"||shared.VIEW==="mine"||shared.VIEW==="person")&&!(shared.VIEW==="person"&&shared.HAND)&&hlKey(e)) return;   /* BL-122: J K move the cursor, Shift extends, Space toggles, Enter and E open */
  /* #232-C2: the Intake page keeps its own keys (components/intakeReview/IntakeReviewPage.jsx); the old Review block is gone */
});
if(!MAC) $("#kK").textContent="Ctrl K";
}

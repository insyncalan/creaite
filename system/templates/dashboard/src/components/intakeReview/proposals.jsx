// @ts-check
/* Intake and Review's proposal rows (#232-B, v2.5.0; the Review side). ProposalGroups draws an open meeting's groups, or the mail
   and other sections: "Needs your decision" first, then "Routine" with one Approve routine (n). ProposalLine is the full row:
   the kind pill, the title, the emphasised line (what it is, in larger semibold type), the quote, the source line (no times;
   Open source opens the whole file), Approve and Reject (with a reason, the reused RejectMenu). A click on a row opens the
   proposal in the peek (the app's right-hand panel: Save, Save and approve, Reject, previous and next).
   The rule for "routine" is the server's (review.hold_reason, the row's `hold`); rvBulkOK reads it. Tokens and the app's own
   classes only (style.css, "#232-B"). */
import { REV, pName } from "../../core/data.js";
import { fd, fdText } from "../../core/page.js";
import { srcParse, weekendNote, wkLong } from "../../core/fields.js";
import { irBulk, irGroupsShown } from "../../core/irFold.js";
import { irLineHead, irLineParts, irVerb } from "../../core/irUpdate.js";
import { linkUrl } from "../../core/linkUrl.js";
import { closePanel, PK, pkOn } from "../../projects.js";
import { reviewViaServer, snack, viaServer } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { draftResponse, NODRAFT_MSG, openProposal, pkEscBusy, pkNote, updPeekable } from "../../panel.js";
import { decide, draftOn, rejectMinutes, rjMenuFor, rvBulkOK, rvDecideMany, rvRejectOK, rvTipText, WKRVF } from "../../review.js";
import { irDone, irHeld, irPeek, irRow, irTick } from "../../stores/intakeReview.js";
import { isConflict } from "../../today.js";
import { IR_GROUP_HEAD } from "./rows.jsx";
import { ConflictBlock } from "./UpdatePeek.jsx";

/** Why a proposal is not routine, in words (the row's `hold`, from review.hold_reason). */
const HOLD_WORDS = { "need a project": "Needs a project", conflict: "Has a conflict to settle", invalid: "Held back: not valid" };
const PEEKABLE = ["actions", "raid", "decisions", "update"];

/** The kind pill's word. @param {any} r */
export function irPill(r) {
  if (r.kind === "raid") return (r.rec && r.rec.type) || "Risk";
  if (r.kind === "draft") return r.ref === "report" ? "Report" : "Minutes";
  return { actions: "Action", decisions: "Decision", update: "Update", files: "File changes" }[/** @type {"actions"} */ (r.kind)] || "Proposal";
}

const irDueWords = (/** @type {string|null|undefined} */ d) => (d ? `due ${fd(d)}` : "No due date");
const noTime = (/** @type {string} */ s) => String(s || "").replace(/(\d{2}-\d{2}-\d{4}) \d{2}:\d{2}/g, "$1").replace(/(\d{4}-\d{2}-\d{2})[ T]\d{2}:\d{2}/g, "$1");
/** A change's column from its words, for a row built before the server named it ("due date" -> due_date). @param {string} field */
const colOf = field => String(field || "").trim().toLowerCase().replace(/\s+/g, "_").replace(/^due$/, "due_date").replace(/^response$/, "response_action").replace(/^client_messaging$/, "client_message");

/** The emphasised line's parts: what the proposal is, owner and date or priority first. @param {any} r @returns {{t: string, warn?: boolean}[]} */
export function irChange(r) {
  const x = r.rec || {}, owner = (/** @type {string} */ o) => (!o || o === "TBC" ? { t: "No owner", warn: true } : { t: o });
  if (r.kind === "actions") return [owner(x.o), { t: irDueWords(x.due), warn: !x.due }, { t: `${x.pr || "Medium"} priority` }];
  if (r.kind === "raid") return [owner(x.o), { t: x.imp && x.lik ? `Impact ${x.imp} · Likelihood ${x.lik}` : "Impact and likelihood not set", warn: !(x.imp && x.lik) }, ...(x.due ? [{ t: irDueWords(x.due) }] : [])];
  if (r.kind === "decisions") return [{ t: x.by ? `Made by ${x.by}` : "Made by not recorded", warn: !x.by }, ...(x.date ? [{ t: fd(x.date) }] : [])];
  if (r.kind === "update") {
    /* B4: "Closes ABC-A-014: Draft the comms plan · status Open → Closed", "Updates ABC-A-002: Book UAT environment · due 20-10-2026 → 23-10-2026 and the latest update":
       the item's title after its ID, and a change to the latest update in words, not as its long text (core/irUpdate.js: the peek's note says the same) */
    const ch = (x.changes && x.changes.length ? x.changes : [{ col: x.col || x.field, field: x.field, from: x.from, to: x.to }]).filter((/** @type {any} */ c) => c.field || c.col)
      .map((/** @type {any} */ c) => ({ col: c.col || colOf(c.field), from: c.from, to: c.to }));
    return [{ t: irLineHead(irVerb(ch), x.table === "projects" ? "" : x.target || "", x.title || "") }, ...irLineParts(ch).map(t => ({ t })), ...(r.dn && r.dn.strength ? [{ t: r.dn.strength }] : [])];
  }
  return [];
}

/** The quote (the evidence): a probably-done update's, else an update's own reason. @param {any} r */
export const irQuote = r => noTime((r.dn && r.dn.ev) || (r.kind === "update" && r.rec && r.rec.why) || "");

/** The source line, without times: where it came from, the match, Open source. @param {any} r */
function SourceLine({ r }) {
  let o = srcParse(r.src);
  if (o && o.type === "Text") {                                    /* a minutes copy is HTML: a file all the same */
    const m = /^((?:projects|system)\/.+?\.html)(?: — (.+))?$/.exec(String(o.text));
    if (m) o = { type: "File", path: m[1], section: m[2] || "", name: m[1].split("/").pop() };
  }
  let where = "", link = null;
  if (r.kind === "draft" || r.kind === "files") where = r.kind === "draft" ? (r.ref === "report" ? "Draft report" : "Draft minutes") : "File changes";
  else if (o && o.type === "File") where = String(o.name || "").replace(/\.[a-z]+$/i, "");
  else if (o && o.type === "Email") where = `Mail${o.From ? ` from ${String(o.From).replace(/\s*<[^>]*>/, "")}` : ""}${o.Subject ? ` · ${o.Subject}` : ""}`;
  else if (o && o.type === "Teams") where = `Teams · ${o.Channel || o.Chat || ""}${o.From ? ` · ${o.From}` : ""}`;
  else where = noTime(String((o && o.text) || ""));
  if (r.nodraft && r.tsrc) link = <a href="#" class="srclink" data-openfile={r.tsrc}>Open source</a>;
  else if (o && o.type === "File") link = <a href="#" class="srclink" data-openfile={o.path}>Open source</a>;
  else if (o && o.Link && linkUrl(o.Link)) link = <a class="srclink" href={/** @type {string} */ (linkUrl(o.Link))} target="_blank" rel="noopener noreferrer">Open source</a>;
  const match = r.p ? null : r.why;
  where = fdText(where);
  return <span class="icsrc">{where}{match ? ` · ${match}` : ""}{link ? <> · {link}</> : null}</span>;
}

/** A due date on a weekend: say so, with the two working days beside it (BL-180); a click edits the proposal (core/fields.js). @param {{r: any}} props */
function WeekendNote({ r }) {
  const f = WKRVF[/** @type {keyof WKRVF} */ (r.kind)], n = f && r.rec && !r.done ? weekendNote(r.rec[f[0]]) : null;
  if (!n) return null;
  return <div class="wkrv"><span class="h-warn">{r.kind === "decisions" ? "Needed" : "Due"} on a {n.day}</span>
    {" "}<button type="button" class="mini" data-wkrv={r.n} data-to={n.prev}>{wkLong(n.prev)}</button>
    {" "}<button type="button" class="mini" data-wkrv={r.n} data-to={n.next}>{wkLong(n.next)}</button></div>;
}

/** Keep current or Use this one: the two choices a conflict has instead of Approve (the live server settles it). @param {{r: any}} props */
function ConflictChoices({ r }) {
  const live = viaServer(), pick = (/** @type {Event} */ e, /** @type {"keep"|"override"} */ how) => { /** @type {HTMLButtonElement} */ (e.currentTarget).disabled = true; reviewViaServer(r, how, []); };
  return <>
    <button type="button" class="mini" data-act="ck" disabled={!live} title={live ? undefined : "Needs the live server"} onClick={e => pick(e, "keep")}>Keep current</button>
    {" "}<button type="button" class="mini ok" data-act="co" disabled={!live} title={live ? undefined : "Needs the live server"} onClick={e => pick(e, "override")}>Use this one</button>
  </>;
}

/** Open the proposal in the peek, with previous and next over the proposals on this page. @param {number} n */
export function irOpenPeek(n) {
  const r = irRow(n);
  if (!r || r.done || !PEEKABLE.includes(r.kind) && r.kind !== "draft") return;
  if (shared.CUR && shared.CUR.mode === "proposal" && shared.CUR.n !== n && PK.dirty && pkOn()) { pkNote("Save or cancel this proposal first: its changes aren't saved yet."); return; }   /* #232 C2: the old Review row's guard (BL-198): edits not yet saved stay */
  shared.PKSRC = {
    view: "intake-review",
    order: () => [...document.querySelectorAll("#v-intake-review tr.irprop")].filter(t => ["actions", "raid", "decisions"].includes(t.getAttribute("data-kind") || "") || t.getAttribute("data-kind") === "update" && updPeekable(irRow(+(t.getAttribute("data-irn") || 0)))).map(t => ({ id: "rv" + t.getAttribute("data-irn"), n: +(t.getAttribute("data-irn") || 0) })),
    step: (/** @type {any} */ o) => { irPeek.value = o.n; openProposal(o.n); },
  };
  irPeek.value = n;
  openProposal(n);
}

/** Approve one proposal (the app's decide: its project, conflict and draft checks all apply). @param {number} n */
export const irApprove = n => decide(n, "approved");

/** Reject: the reasons menu where a proposal can be rejected with one; minutes, reports and file changes on their own. @param {number} n @param {Element|null} anchor */
export function irReject(n, anchor) {
  const r = irRow(n);
  if (!r || r.done) return;
  if (rvRejectOK(r)) rjMenuFor([r], anchor); else if (r.kind === "draft" && r.ref === "meeting") rejectMinutes(r); else decide(n, "rejected");
}

/** Approve routine: the routine group only, in one apply with one Undo (rvDecideMany); never the first group.
    @param {{needs: number[], routine: number[]}} groups */
export async function irApproveRoutine(groups) {
  const list = irBulk(groups, irDone, irHeld).map(irRow).filter(r => rvBulkOK(r));
  if (!list.length) { snack("Nothing routine to approve"); return; }
  const res = await rvDecideMany(list, "approved");
  const failed = res.failed && res.failed.length ? ` · not saved: ${res.failed.join(", ")}` : "";
  snack(`Approved ${res.n} routine${failed}`, res.undo || null);
}

/** The meta line's hover when a proposal has no owner, date or priority to show (minutes, reports, file changes). */
const TIP_FALLBACK = { draft: "Draft minutes or a report: open it to read the Word draft", files: "File changes: open the proposal to see them" };

/** Whether a new risk with no response offers Draft a response (BL-225). @param {any} r */
const canDraftResponse = r => !!r && !r.done && r.kind === "raid" && !String((r.rec && r.rec.resp) || "").trim() && !(r.rec.type && r.rec.type !== "Risk") && draftOn("thinking");

/** One proposal as the full row: the title, ONE meta line (the pill, the emphasised change, whether it is routine, the source; its
    detail is that line's tooltip, #229), and beside it what a person acts on: the quote, a conflict's before and after, the weekend
    note, the no-Word-draft notice. @param {{n: number, child?: boolean}} props */
export function ProposalLine({ n, child }) {
  const tick = irTick.value;       /* a row reads REV, which is not a signal: the tick redraws it when REV changed (an edit, a draft) and its props did not */
  const r = irRow(n);
  if (!r) return null;
  const parts = irChange(r), quote = irQuote(r), held = r.hold ? (HOLD_WORDS[/** @type {keyof HOLD_WORDS} */ (r.hold)] || "approve individually") : "";
  const rej = !!r.kind && r.kind !== "files", conflict = isConflict(r), tip = rvTipText(r) || TIP_FALLBACK[/** @type {keyof TIP_FALLBACK} */ (r.kind)] || "Open it to see the detail";
  return (
    <tr class={`click irprop${child ? " mchild" : ""}`} data-irn={n} data-irtick={tick} data-hold={r.hold || ""} data-kind={r.kind} tabindex={0}
      onClick={e => { if (!(/** @type {Element} */ (e.target)).closest("button,a,input,select")) irOpenPeek(n); }}
      onKeyDown={e => { if (e.target === e.currentTarget && e.key === "Enter") { e.preventDefault(); irOpenPeek(n); } }}>
      <td class="title">
        <b class="icttl">{(r.rec && r.rec.t) || ""}</b>{r.p ? <span class="sub"> · {pName(r.p)}</span> : null}
        {r.drafted ? <>{" "}<span class="tag drrv"><svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 3l1.8 4.7L18.5 9.5l-4.7 1.8L12 16l-1.8-4.7L5.5 9.5l4.7-1.8z" /><path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z" /></svg>{r.drafted === "client" ? "Drafted wording" : "Drafted"}</span></> : null}
        {conflict ? <ConflictBlock rec={r.rec} /> : null}
        <div class="icchg" data-tip={tip || undefined}><span class="ickind">{irPill(r)}</span>
          {parts.map(p => <> · <span class={p.warn ? "h-warn" : ""}>{p.t}</span></>)}
          {held ? <> · <span class="indiv">{held}</span></> : <> · <span class="icroutine">Routine</span></>}
          {canDraftResponse(r) ? <> · <button type="button" class="linkbtn" data-drrisk={r.n} onClick={() => draftResponse(r.n)}>Draft a response</button></> : null}
          {" · "}<SourceLine r={r} /></div>
        {quote ? <div class="icq">{quote}</div> : null}
        {r.ws_suggest && !r.done && (r.flags || []).includes("new-workstream") ? <div class="wsq">New workstream “{r.ws_suggest}” for {r.p || "?"}? <button type="button" class="mini" data-wsq="add" data-n={r.n}>Add workstream</button><button type="button" class="mini" data-wsq="skip" data-n={r.n}>Leave blank</button></div> : null}   {/* BL-58: the old Review row's offer (settings.js handles the buttons); #232 C2 put it back on the Intake page's row */}
        <WeekendNote r={r} />
        {r.nodraft ? <div class="rvnote"><span class="h-warn">No Word draft was made for these minutes</span> · Reject them and process the meeting again</div> : null}
      </td>
      <td class="iracts">
        {r.kind !== "files" ? <button type="button" class="ib sm" data-ira="edit" aria-label="Open in the peek" data-tip="Open in the peek" onClick={() => irOpenPeek(n)}>✎</button> : null}
        {" "}{conflict ? <ConflictChoices r={r} /> : <button type="button" class="mini ok" data-ira="approve" disabled={!!r.nodraft} title={r.nodraft ? NODRAFT_MSG : undefined} onClick={() => irApprove(n)}>Approve</button>}
        {" "}{rej ? <button type="button" class="ib sm no" data-ira="reject" aria-haspopup={rvRejectOK(r) ? "menu" : undefined} aria-label={rvRejectOK(r) ? "Reject, with a reason" : "Reject"}
          data-tip={rvRejectOK(r) ? "Reject, with a reason" : "Reject"} onClick={e => irReject(n, /** @type {Element} */ (e.currentTarget))}>✕</button> : null}
      </td>
    </tr>
  );
}

/** The groups under an open meeting (child rows on its rail) or in the mail and other sections.
    @param {{groups: {needs: number[], routine: number[]}, meet?: string, child?: boolean}} props */
export function ProposalGroups({ groups, meet, child }) {
  return <>{irGroupsShown(groups, irDone, irHeld).map(g => (
    <>
      <tr class={`icsubhead ${g.kind}${child ? " child" : ""}`} data-irg={g.kind}><td colSpan={2}>
        <span class="icsh">{meet ? `${meet} · ` : ""}{IR_GROUP_HEAD[g.kind][0]} · {g.ns.length}</span>
        <span class="icshs">{IR_GROUP_HEAD[g.kind][1]}</span>
        {g.kind === "routine" ? <span class="icshr"><button type="button" class="mini ok" data-ira="routine" title="Approves every routine proposal here; the ones above stay for you"
          onClick={() => irApproveRoutine(groups)}>Approve routine ({g.ns.length})</button></span> : null}
      </td></tr>
      {g.ns.map(n => <ProposalLine n={n} child={child} />)}
    </>
  ))}</>;
}

/* Keys for the proposals (232-B): up and down move between proposal rows, Enter opens the peek, A approves, R rejects with a reason.
   Esc: with the peek open it closes the peek only; the page's own handler then closes the meeting on the next Esc. In the capture
   phase, so it runs before the old Esc handler and the page's. */
let keysBooted = false;
export function bootIrReviewKeys() {
  if (keysBooted) return;
  keysBooted = true;
  document.addEventListener("keydown", e => {
    if (shared.VIEW !== "intake-review" || e.metaKey || e.ctrlKey || e.altKey) return;
    const t = /** @type {HTMLElement} */ (e.target), panel = document.getElementById("panel");
    if (e.key === "Escape") {
      if (irPeek.value == null) return;
      if (pkEscBusy(/** @type {HTMLElement|null} */ (document.activeElement))) return;   /* an open menu, calendar, chat, text field or Draft email keeps its own Esc (panel.js, the same rule) */
      if (panel && panel.classList.contains("on")) { e.stopImmediatePropagation(); closePanel(); }
      irPeek.value = null;
      return;
    }
    if (!t || !t.closest || t.closest("input,textarea,select,[contenteditable=true],[role=menu]")) return;
    const row = /** @type {HTMLElement|null} */ (t.closest("tr.irprop"));
    if (!row || (t.closest("button,a") && !t.matches("tr"))) return;
    const rows = /** @type {HTMLElement[]} */ ([...document.querySelectorAll("#v-intake-review tr.irprop")]), at = rows.indexOf(row), n = +(row.getAttribute("data-irn") || 0);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); e.stopImmediatePropagation();
      const to = rows[Math.max(0, Math.min(rows.length - 1, at + (e.key === "ArrowDown" ? 1 : -1)))];
      if (to) to.focus();
    } else if (e.key === "a" || e.key === "A") { e.preventDefault(); e.stopImmediatePropagation(); irApprove(n); }
    else if (e.key === "r" || e.key === "R") { e.preventDefault(); e.stopImmediatePropagation(); irReject(n, row.querySelector("[data-ira=reject]")); }
  }, true);
}
bootIrReviewKeys();

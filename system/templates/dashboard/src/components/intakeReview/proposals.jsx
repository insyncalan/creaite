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
import { srcParse } from "../../core/fields.js";
import { irBulk, irGroupsShown } from "../../core/irFold.js";
import { linkUrl } from "../../core/linkUrl.js";
import { closePanel } from "../../projects.js";
import { snack } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { NODRAFT_MSG, openProposal, pkEscBusy } from "../../panel.js";
import { decide, rejectMinutes, rjMenuFor, rvBulkOK, rvDecideMany, rvRejectOK } from "../../review.js";
import { irDone, irHeld, irPeek, irRow } from "../../stores/intakeReview.js";
import { IR_GROUP_HEAD } from "./rows.jsx";

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
const irVal = (/** @type {any} */ v) => (v == null || v === "" ? "—" : fd(String(v)));

/** The emphasised line's parts: what the proposal is, owner and date or priority first. @param {any} r @returns {{t: string, warn?: boolean}[]} */
export function irChange(r) {
  const x = r.rec || {}, owner = (/** @type {string} */ o) => (!o || o === "TBC" ? { t: "No owner", warn: true } : { t: o });
  if (r.kind === "actions") return [owner(x.o), { t: irDueWords(x.due), warn: !x.due }, { t: `${x.pr || "Medium"} priority` }];
  if (r.kind === "raid") return [owner(x.o), { t: x.imp && x.lik ? `Impact ${x.imp} · Likelihood ${x.lik}` : "Impact and likelihood not set", warn: !(x.imp && x.lik) }, ...(x.due ? [{ t: irDueWords(x.due) }] : [])];
  if (r.kind === "decisions") return [{ t: x.by ? `Made by ${x.by}` : "Made by not recorded", warn: !x.by }, ...(x.date ? [{ t: fd(x.date) }] : [])];
  if (r.kind === "update") {
    const closing = x.field === "status" && ["Closed", "Cancelled"].includes(String(x.to)), verb = closing ? (x.to === "Cancelled" ? "Cancels" : "Closes") : "Updates";
    const ch = (x.changes && x.changes.length ? x.changes : [{ field: x.field, from: x.from, to: x.to }]).filter((/** @type {any} */ c) => c.field);
    return [{ t: `${verb} ${x.target || ""}`.trim() }, ...ch.map((/** @type {any} */ c) => ({ t: `${String(c.field).toLowerCase()} ${irVal(c.from)} → ${irVal(c.to)}` })),
      ...(r.dn && r.dn.strength ? [{ t: r.dn.strength }] : [])];
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
  return <div class="why icsrc">{where}{match ? ` · ${match}` : ""}{link ? <> · {link}</> : null}</div>;
}

/** Open the proposal in the peek, with previous and next over the proposals on this page. @param {number} n */
export function irOpenPeek(n) {
  const r = irRow(n);
  if (!r || r.done || !PEEKABLE.includes(r.kind) && r.kind !== "draft") return;
  shared.PKSRC = {
    view: "intake-review",
    order: () => [...document.querySelectorAll("#v-intake-review tr.irprop")].filter(t => ["actions", "raid", "decisions"].includes(t.getAttribute("data-kind") || "")).map(t => ({ id: "rv" + t.getAttribute("data-irn"), n: +(t.getAttribute("data-irn") || 0) })),
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

/** One proposal as the full row. @param {{n: number, child?: boolean}} props */
export function ProposalLine({ n, child }) {
  const r = irRow(n);
  if (!r) return null;
  const parts = irChange(r), quote = irQuote(r), held = r.hold ? (HOLD_WORDS[/** @type {keyof HOLD_WORDS} */ (r.hold)] || "approve individually") : "";
  const rej = !!r.kind && r.kind !== "files";
  return (
    <tr class={`click irprop${child ? " mchild" : ""}`} data-irn={n} data-hold={r.hold || ""} data-kind={r.kind} tabindex={0}
      onClick={e => { if (!(/** @type {Element} */ (e.target)).closest("button,a,input,select")) irOpenPeek(n); }}
      onKeyDown={e => { if (e.target === e.currentTarget && e.key === "Enter") { e.preventDefault(); irOpenPeek(n); } }}>
      <td class="title">
        <b class="icttl">{(r.rec && r.rec.t) || ""}</b>{r.p ? <span class="sub"> · {pName(r.p)}</span> : null}
        <div class="icchg"><span class="ickind">{irPill(r)}</span>
          {parts.map(p => <> · <span class={p.warn ? "h-warn" : ""}>{p.t}</span></>)}
          {held ? <> · <span class="indiv">{held}</span></> : <> · <span class="icroutine">Routine</span></>}</div>
        {quote ? <div class="icq">{quote}</div> : null}
        <SourceLine r={r} />
        {r.nodraft ? <div class="why"><span class="h-warn">No Word draft was made for these minutes</span> · Reject them and process the meeting again</div> : null}
      </td>
      <td class="iracts">
        {r.kind !== "files" ? <button type="button" class="ib sm" data-ira="edit" aria-label="Open in the peek" data-tip="Open in the peek" onClick={() => irOpenPeek(n)}>✎</button> : null}
        {" "}<button type="button" class="mini ok" data-ira="approve" disabled={!!r.nodraft} title={r.nodraft ? NODRAFT_MSG : undefined} onClick={() => irApprove(n)}>Approve</button>
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

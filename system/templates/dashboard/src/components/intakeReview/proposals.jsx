// @ts-check
/* Intake and Review's proposal rows (#232-B, v2.5.0; the placeholder from the skeleton, now the full row).
   One proposal is one row: a title; ONE meta line, emphasised (kind pill, what it is or what changes, "approve individually" or
   "Routine", the source and Open source) whose detail (owner, priority, due) is its tooltip and is in the peek (#229); the
   evidence quote on a rail; Approve and a Reject that asks why. What a person must notice stays beside the line, never in it:
   the Drafted tag, the weekend note with its two buttons, the "No Word draft was made" notice, a conflict's block and its two
   choices, and Draft a response. ProposalGroups draws an open meeting's two groups, or the mail and other sections.
   Text only, through JSX. The actions are in proposalActions.js (they use Review's own flows). */
import { Icon } from "../Icon.jsx";
import { IconButton } from "../IconButton.jsx";
import { REV } from "../../core/data.js";
import { irGroupsShown } from "../../core/irFold.js";
import { srcParse, srcShort, weekendNote, wkLong } from "../../core/fields.js";
import { linkUrl } from "../../core/linkUrl.js";
import { fd, OPENST, prio } from "../../core/page.js";
import { viaServer } from "../../core/server.js";
import { shared } from "../../core/state.js";
import { NODRAFT_MSG } from "../../panel.js";
import { draftOn, rvBulkOK, rvDup, rvTipText, WKRVF } from "../../review.js";
import { isConflict } from "../../today.js";
import { irDone, irPeek, irRow } from "../../stores/intakeReview.js";
import { approve, approveRoutine, draftResponse, edit, openPeek, reject, settle } from "./proposalActions.js";

/** The two group heads: the name and the sentence under it (Alan, 18-10-2026: the routine sentence is approved wording). */
export const IR_HEADS = {
  needs: ["Needs your decision", "Approved one by one: minutes, new decisions, new risks, closing updates and other bigger changes."],
  routine: ["Routine", "Each has a project and no conflict, and none is a change you approve one by one."],
};
const KIND_WORDS = { actions: "Action", decisions: "Decision", update: "Update", files: "File changes" };
/** The kind pill's word. @param {any} r */
export const irPill = r => (r.kind === "raid" ? (r.rec && r.rec.type) || "Risk" : r.kind === "draft" ? (r.ref === "meeting" ? "Minutes" : "Report")
  : KIND_WORDS[/** @type {keyof KIND_WORDS} */ (r.kind)] || "Proposal");

const lower = (/** @type {string} */ s) => (s ? s.charAt(0).toLowerCase() + s.slice(1) : s);
const val = (/** @type {any} */ x) => (x == null || x === "" ? "none" : fd(String(x)));
const owner = (/** @type {any} */ o) => (!o || o === "TBC" ? "No owner" : o);
const due = (/** @type {any} */ d) => (d ? fd(d) : "No due date");

/** What the proposal is, or what it changes, in words (the emphasised line). @param {any} r */
export function irSummary(r) {
  const x = r.rec || {};
  if (r.kind === "actions") return [owner(x.o), due(x.due), x.pr || "Medium"].join(" · ");
  if (r.kind === "raid") return [owner(x.o), x.imp && x.lik ? `${x.imp} × ${x.lik} → ${prio(x.imp, x.lik)}` : "Impact and likelihood not set"].join(" · ");
  if (r.kind === "decisions") return x.by ? `Made by ${x.by}` : "Made by not recorded";
  if (r.kind === "update") {
    const ch = x.changes || [], st = ch.find((/** @type {any} */ c) => String(c.field).toLowerCase() === "status");
    const lead = st && st.to && !OPENST(String(st.to)) ? `Closes ${x.target || ""}` : `Changes ${x.target || ""}`;
    return [lead.trim(), ...ch.map((/** @type {any} */ c) => `${lower(String(c.field))} ${val(c.from)} → ${val(c.to)}`), r.dn ? r.dn.strength : ""].filter(Boolean).join(" · ");
  }
  if (r.kind === "draft") {
    const n = REV.filter(k => k.file === r.file && !["draft", "files"].includes(k.kind) && !k.done).length;
    return n ? `${n} item${n === 1 ? "" : "s"} below come${n === 1 ? "s" : ""} from these minutes` : "Draft minutes";
  }
  return "File changes";
}

/** Why it is not routine, or "Routine". @param {any} r */
const stateWords = r => (r.indiv ? "approve individually" : r.hold && !rvBulkOK(r) ? String(r.why || r.hold).toLowerCase() : "Routine");

/** The Open source link: the whole file or the message; no time. @param {{r: any}} props */
function OpenSource({ r }) {
  if (r.nodraft && r.tsrc) return <> · <a href="#" class="srclink" data-openfile={r.tsrc}>Open source</a></>;
  const o = srcParse(r.src);
  if (!o) return null;
  if (o.type === "File") return <> · <a href="#" class="srclink" data-openfile={o.path}>Open source</a></>;
  const u = o.Link ? linkUrl(o.Link) : null;
  return u ? <> · <a href={u} class="srclink" target="_blank" rel="noopener noreferrer">Open source</a></> : null;
}

/** A conflict's before and after, from the proposal. @param {{r: any}} props */
function Conflict({ r }) {
  const ch = r.rec.changes && r.rec.changes.length ? r.rec.changes : r.rec.field ? [{ field: r.rec.field, from: r.rec.from, to: r.rec.to }] : [];
  const v = (/** @type {any} */ x) => (x == null || x === "" ? "(empty)" : /^\d{4}-\d{2}-\d{2}$/.test(String(x)) ? fd(String(x)) : String(x));
  return (
    <div class="cfvs">
      {ch.length ? ch.map((/** @type {any} */ c) => <div><span class="cff">{c.field}</span><span class="cfnow">Now: <b>{v(c.from)}</b></span><span class="cfnew">This one: <b>{v(c.to)}</b></span></div>)
        : <div class="sub">Changed in the tracker after this was proposed.</div>}
    </div>
  );
}

/** The weekend note: a date on a day off, with the two nearest working days as buttons. @param {{r: any}} props */
function WeekendNote({ r }) {
  const f = WKRVF[/** @type {keyof WKRVF} */ (r.kind)], v = f && r.rec ? r.rec[f[0]] : null, n = !shared.LOADING && !r.done ? weekendNote(v) : null;
  if (!n) return null;
  return (
    <div class="wkrv"><span class="h-warn">{r.kind === "decisions" ? "Needed" : "Due"} on a {n.day}</span>{" "}
      <button type="button" class="mini" data-wkrv={r.n} data-to={n.prev}>{wkLong(n.prev)}</button>{" "}
      <button type="button" class="mini" data-wkrv={r.n} data-to={n.next}>{wkLong(n.next)}</button></div>
  );
}

/** One proposal. @param {{n: number, child?: boolean}} props */
export function ProposalLine({ n, child }) {
  const r = irRow(n);
  if (!r) return null;
  const conflict = isConflict(r), live = viaServer();
  const tip = rvTipText(r);
  const noDraft = r.kind === "draft" && r.nodraft && !r.done;
  const respNeeded = !(r.kind !== "raid" || String(r.rec.resp || "").trim() || (r.rec.type && r.rec.type !== "Risk") || !draftOn("thinking"));
  const dup = rvDup(r);
  const o = srcParse(r.src);
  const pass = (/** @type {MouseEvent} */ e) => !(/** @type {Element} */ (e.target)).closest("button,a,input,select,[data-wkrv]");
  return (
    <tr class={`click irprop${child ? " mchild" : ""}${irPeek.value === n ? " sel" : ""}`} data-irn={n} data-n={n} tabindex={0}
      onClick={e => { if (pass(e) && !["draft", "files"].includes(r.kind)) openPeek(n); }}>
      <td class="title">
        <b class="icttl">{r.rec.t || ""}</b>
        {r.drafted ? <> <span class="tag drrv"><Icon name="spark" />{r.drafted === "client" ? "Drafted wording" : "Drafted"}</span></> : null}
        {r.edited ? <> <span class="tag">· edited</span></> : null}
        {dup ? <> <span class="tag">Looks like {dup.id || "another item"}</span></> : null}
        <div class="why icchg" data-tip={tip || undefined}>
          <span class="ickind">{irPill(r)}</span> · {irSummary(r)} · {r.indiv ? <span class="indiv">approve individually</span> : <span class={r.hold ? "" : "icroutine"}>{stateWords(r)}</span>}
          {respNeeded ? <> · <button type="button" class="linkbtn" data-drrisk={r.n} onClick={() => draftResponse(n)}>Draft a response</button></> : null}
          {" · "}{o ? srcShort(r.src) : "—"}<OpenSource r={r} />
        </div>
        {r.dn && r.dn.ev ? <div class="icq">{r.dn.ev}</div> : r.rec.why ? <div class="icq">{r.rec.why}</div> : null}
        {noDraft ? <div class="rvnote"><span class="h-warn">No Word draft was made for these minutes</span> · Reject them and process the meeting again</div> : null}
        <WeekendNote r={r} />
        {conflict ? <Conflict r={r} /> : null}
      </td>
      <td class="iracts">
        <IconButton icon="pencil" label={r.kind === "draft" ? (r.nodraft ? "No Word draft" : "Open draft") : "Edit"} data={{ ira: "edit" }} onClick={() => edit(n)} />{" "}
        {conflict ? <>
          <button type="button" class="mini" data-act="ck" data-ira="keep" disabled={!live} title={live ? undefined : "Needs the live server"} onClick={() => settle(n, "keep")}>Keep current</button>{" "}
          <button type="button" class="mini ok" data-act="co" data-ira="override" disabled={!live} title={live ? undefined : "Needs the live server"} onClick={() => settle(n, "override")}>Use this one</button>
        </> : (
          <button type="button" class="mini ok" data-ira="approve" disabled={!!r.nodraft} title={r.nodraft ? NODRAFT_MSG : undefined} onClick={() => approve(n)}><Icon name="check" />Approve</button>
        )}{" "}
        <IconButton icon="x" label={["draft", "files"].includes(r.kind) ? "Reject" : "Reject, with a reason"} cls="no" data={{ ira: "reject" }} haspopup={["draft", "files"].includes(r.kind) ? undefined : "menu"}
          onClick={e => reject(n, /** @type {Element} */ (e.currentTarget))} />
      </td>
    </tr>
  );
}

/** The groups under an open meeting (child rows on its rail) or in the mail and other sections.
    @param {{groups: {needs: number[], routine: number[]}, meet?: string, child?: boolean}} props */
export function ProposalGroups({ groups, meet, child }) {
  return <>{irGroupsShown(groups, irDone).map(g => (
    <>
      <tr class={`icsubhead ${g.kind}${child ? " child" : ""}`} data-irg={g.kind}><td colSpan={2}>
        <span class="icsh">{meet ? `${meet} · ` : ""}{IR_HEADS[g.kind][0]} · {g.ns.length}</span>
        <span class="icshs">{IR_HEADS[g.kind][1]}</span>
        {g.kind === "routine" ? <span class="icshr"><button type="button" class="mini ok" data-ira="routine" title="Approves every routine item here; the ones above stay for you" onClick={() => approveRoutine(g.ns)}>Approve routine ({g.ns.length})</button></span> : null}
      </td></tr>
      {g.ns.map(n => <ProposalLine n={n} child={child} />)}
    </>
  ))}</>;
}

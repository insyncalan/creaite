// @ts-check
/* MinutesView (v2.1.0 P7, BL-338; #268 Minutes view v2): a meeting's minutes in creaite (#minutes=<the record's stored path>),
   opened from Review's Open draft on a minutes record. It sits under Review in the sidebar: no new top-level page. Built on
   the sheet (P5's Sheet.jsx: the A4 page, fit to width, zoom 50% to 250% with − and +, a pinch or Ctrl and the wheel, and the
   slim bar when the sheet scrolls, as Reporting's `rpt-slim`). The view supplies its own renderers (SummaryText and TextLines
   for text, ItemTable for decisions, risks and issues, and actions), the coverage extra and the checks, keeps the document
   (stores/minutes.js) and makes its own server calls (P4's /api/minutes/*). Beside the sheet, the transcript pane.
   #268: one version only (no distributed version or Internal only marks in the view; the server's distributed code is left
   as it is). The bar is one row: the title (when slim), zoom, Show as exported, the save line, the Track summary ("n work
   items to register · n kept in the minutes only · n removed"), then Transcript (pressed while shown, remembered per browser),
   Export (Word, PDF, HTML and Draft the follow-up email), Re-extract (opens ask creaite with the request written, to send;
   it doesn't re-draft by itself: Cap's #268 review M4) and Approve minutes, the one labelled button.
   Approve minutes is one click: the record is brought in line with the Track column (track.reconcileOps: the existing
   remove, keep-the-line and restore changes), then the minutes and every ticked item are applied in one apply
   (/api/minutes/approve), with Undo on the snack. Only when a ticked item has a real problem does the Before approving box
   ask first. Nothing here sends anything. */
import { render } from "preact";
import { Icon } from "../Icon.jsx";
import { Menu } from "../Menu.jsx";
import { countRedraft, redrafter } from "../report/redraft.js";
import { Sheet } from "../report/Sheet.jsx";
import { ApprovePopup } from "./ApprovePopup.jsx";
import { MinutesCtx } from "./context.js";
import { Coverage } from "./Coverage.jsx";
import { ItemTable } from "./ItemTable.jsx";
import { checksOf } from "./minutesDoc.js";
import { SummaryText, TextLines } from "./TextLines.jsx";
import { approveArgs, approveProblems, reconcileOps, trackCounts, trackSummary } from "./track.js";
import { jumpTo, TranscriptPane } from "./TranscriptPane.jsx";
import { REV } from "../../core/data.js";
import { $ } from "../../core/dom.js";
import { navWrite, tabTitle } from "../../core/nav.js";
import { fd } from "../../core/page.js";
import { reloadData, snack, undoApply } from "../../core/server.js";
import { ckAsk, openChat } from "../../ask.js";
import { openMinutesFollowup } from "../../drafts.js";
import { openProposal } from "../../panel.js";
import { unknownOwner } from "../../settings.js";
import { approveMinutes, approveOpen, changeMinutes, exportMinutes, keptChecks, loadMinutes, minutesBase, minutesBusy, minutesDoc,
  minutesView, paneOpen, paneRemembered, saveMinutesPage, setPane } from "../../stores/minutes.js";
import { signal } from "@preact/signals";

/** @typedef {import("../report/Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {import("./minutesDoc.js").Check} Check */

/** #268: the minutes' zoom, against the fitted scale (1 = fit to width, where they open). Fit to width is capped at the page's
    real size (fitMax: 100%), so a wide screen shows the A4 page centred on the grey; − + and a pinch still go past it. The bar
    says the real size (the scale drawn, so hiding the transcript, which widens the area, says the new size). */
export const MN_ZOOM = { min: 0.5, max: 2.5, fit: 1, fitMax: 1 };
/** The Export menu (Word is an export only: editing the exported file never flows back). */
export const MN_EXPORTS = [
  { id: "docx", name: "Word", line: "The minutes template; an export only, edits to it never come back" },
  { id: "pdf", name: "PDF", line: "Printed from the page" },
  { id: "html", name: "HTML", line: "A read-only page, filed beside the minutes" },
  { id: "sep", sep: true },
  { id: "followup", name: "Draft the follow-up email", line: "From these minutes; copied, never sent" }];

let dirty = false;
const approving = signal(false);

/** The staged item of a row ("@3") in the peek: its Review proposal. @param {string} ref */
function openStaged(ref) {
  const v = minutesView.value, n = Number(String(ref).replace(/^@/, ""));
  const r = v && REV.find(x => x.file === v.proposal && x.ref === n);
  if (r) openProposal(r.n); else snack("That item is no longer pending in Review.");
  return true;
}

/** Page edits not yet saved: saved before anything that changes the record. */
async function mnSaveFirst() {
  const d = minutesDoc.value;
  if (!dirty || !d) return true;
  const s = await saveMinutesPage({ doc: d, base_version: minutesBase.value });
  if (!s.ok) { snack(s.message || "The minutes weren't saved"); return false; }
  dirty = false;
  return true;
}

/** Export, or draft the follow-up email (saved edits first). @param {string} id */
async function exportAs(id) {
  if (!(await mnSaveFirst())) return;
  const v = minutesView.value;
  if (id === "followup") { openMinutesFollowup(v && v.path, "internal"); return; }
  const r = await exportMinutes(id);
  snack(r.ok ? `Exported${r.path ? `: ${String(r.path).split("/").pop()}` : ""}` : String(r.message || "Not exported").split("\n")[0]);
}

/** Re-extract: creaite's chat with the request written, to send when Alan is ready; nothing is re-drafted until he sends it,
    and the outcome is for the planned Re-extract run kind to define (Cap's #268 review M4). Words Alan has typed there and not
    sent are never written over (review LOW): the chat opens with them and the toast says so. @param {SheetDoc} doc */
function reExtract(doc) {
  const box = /** @type {HTMLTextAreaElement|null} */ (document.getElementById("chIn"));
  if (box && box.value.trim()) { openChat(); snack("ask creaite has words you haven't sent: send or clear them, then press Re-extract again"); return; }
  ckAsk(`re-extract the minutes of “${doc.title}” (${fd(doc.date)}) from the transcript`);
}

/** Approve minutes: the Track column first, then one apply. @param {boolean} anyway past the Before approving box */
async function approveNow(anyway) {
  const v = minutesView.value, doc = minutesDoc.value;
  if (!v || !v.plan || !doc || approving.value) return;
  const plan = v.plan.items;
  if (!anyway && approveProblems(doc, plan, unknownOwner).length) { approveOpen.value = true; return; }
  approving.value = true;
  try {
    if (!(await mnSaveFirst())) return;
    const args = approveArgs(doc, plan);                   // review H1: only the ticked rows, never an item with no row
    let made = 0;
    for (const op of reconcileOps(doc, plan)) {
      const r = await changeMinutes(op);
      if (!r.ok) {                                          // review M1: say so when some of the Track column's changes were made
        snack(made ? `${r.message ? `${r.message} ` : ""}Some changes were made to the minutes; press Approve minutes again.`
          : r.message || "The minutes weren't approved; nothing was applied.");
        return;
      }
      made++;
    }
    const r = await approveMinutes(args.group, args.own);
    if (!r.ok) { snack(String(r.message || "The apply didn't run; nothing was changed.").split("\n")[0]); return; }
    const n = r.approved || 0, left = (r.waiting || []).length;
    snack(`Minutes approved · ${n ? `${n} work item${n === 1 ? "" : "s"} registered` : "no work items registered"}${left ? ` · ${left} wait in Review` : ""}`,
      r.apply_id ? async () => { await undoApply(r.apply_id); if (v.proposal) loadMinutes({ file: v.proposal }); } : null);   // Undo: the draft comes back, so does its page
    await reloadData();
    if (v.plan.files[0]) loadMinutes({ path: v.plan.files[0] });
  } finally { approving.value = false; }
}

/** The Track summary with its counts in bold (the words are trackSummary's). @param {{c: {y: number, k: number, n: number}}} props */
function TrackSum({ c }) {
  const parts = trackSummary(c).split(/(\d+)/);
  return <>{parts.map((p, i) => (i % 2 ? <b key={i}>{p}</b> : p))}</>;
}

/** The bar (the sheet's renderBar): one row (two at 900 px). @param {{doc: SheetDoc, zoom: number, setZoom: (z: number) => void, exported: boolean,
    setExported: (on: boolean) => void, status: string, bad: boolean, scale: number}} props */
function Bar({ doc, zoom, setZoom, exported, setExported, status, bad, scale }) {
  const v = minutesView.value, draft = doc.state === "draft", plan = v && v.plan ? v.plan.items : null;
  const c = draft && plan ? trackCounts(doc, plan) : null;
  const z = (/** @type {1|-1} */ d) => setZoom(Math.round((zoom + d * 0.1) * 10) / 10);
  const pc = Math.round((scale || zoom) * 100);              // the real size: the scale the page is drawn at
  return (
    <>
      <span class="sheet-mini"><b>{doc.title}</b><span class="sub">{doc.project_name || ""} · {fd(doc.date)}</span></span>
      <span class="sheet-zoom" role="group" aria-label="Zoom">
        <button type="button" class="btn sm" aria-label="Zoom out" data-tip="Zoom out" onClick={() => z(-1)} disabled={zoom <= MN_ZOOM.min}>−</button>
        <button type="button" class="sheet-zv mnzv" aria-live="polite" data-zoom={zoom} data-tip="Fit to width" aria-label={`Zoom ${pc}%. Fit to width`}
          onClick={() => setZoom(MN_ZOOM.fit)}>{pc}%</button>
        <button type="button" class="btn sm" aria-label="Zoom in" data-tip="Zoom in" onClick={() => z(1)} disabled={zoom >= MN_ZOOM.max}>+</button>
      </span>
      <button type="button" class="ib sm sheet-exp" aria-pressed={exported ? "true" : "false"} aria-label="Show as exported" data-tip="Show as exported"
        onClick={() => setExported(!exported)}><Icon name="filetext" /></button>
      <span class="sub sheet-status" role="status" data-bad={bad ? "1" : undefined}>{status || (doc.version ? `Saved · version ${doc.version}` : "")}</span>
      {c ? <span class="mnsum" id="mnSum" role="status" data-y={c.y} data-k={c.k} data-n={c.n} data-w={c.w}><TrackSum c={c} /></span> : null}
      <span class="sheet-barr"><span class="mnbarr">
        <button type="button" class="ib sm" id="mnTrBtn" aria-pressed={paneOpen.value ? "true" : "false"} aria-label="Transcript" data-tip={paneOpen.value ? "Hide the transcript" : "Show the transcript"}
          onClick={() => setPane(!paneOpen.value)}><Icon name="chat" /></button>
        <Menu label="" icon="download" btnCls="ib sm" ariaLabel="Export" tip="Export" chevron={false} menuLabel="Export the minutes" data={{ mnexport: "" }}
          items={/** @type {any} */ (MN_EXPORTS)} onPick={exportAs} />
        {draft ? <button type="button" class="ib sm" id="mnReBtn" aria-label="Re-extract: opens ask creaite with the request written; it doesn't re-draft the minutes by itself"
          data-tip="Re-extract: opens ask creaite with the request written; it doesn't re-draft the minutes by itself" onClick={() => reExtract(doc)}><Icon name="refresh" /></button> : null}
        {draft ? <button type="button" class="btn sm primary" id="mnApproveBtn" disabled={!(v && v.plan) || approving.value}
          data-tip={v && v.plan ? undefined : "Nothing pending to approve"} onClick={() => approveNow(false)}>{approving.value ? "Approving…" : "Approve minutes"}</button> : null}
      </span></span>
    </>
  );
}

/** Every edit from the sheet: kept on the page, saved by the sheet (⌘S, after a pause) or before the next row change.
    @param {SheetDoc} d @param {string} _why */
function onDoc(d, _why) { minutesDoc.value = d; dirty = true; }

/** One row or coverage change: page edits saved first, then the change; Undo on the toast when there is one.
    @param {Record<string, any>} op @param {Record<string, any>|null} [undo] */
async function change(op, undo) {
  if (!(await mnSaveFirst())) return false;
  const r = await changeMinutes(op);
  if (!r.ok) { snack(r.message || "That didn't change"); return false; }
  snack(r.message || "Changed", undo ? () => { change(undo); } : null);
  return true;
}

/** What a check's button does. @param {Check} c @param {string} action */
function onCheck(c, action) {
  if (action === "keep") keptChecks.value = [...keptChecks.value, c.id];
  else if (action === "show" && c.turn) jumpTo(c.turn);
  else if (action === "use" && c.kind === "due" && c.n && c.words) change({ op: "deadline", n: c.n, words: c.words });
}

const RENDER = { byId: { summary: (/** @type {any} */ ctx) => <SummaryText ctx={ctx} />, decisions: (/** @type {any} */ ctx) => <ItemTable ctx={ctx} />,
  raid: (/** @type {any} */ ctx) => <ItemTable ctx={ctx} />, actions: (/** @type {any} */ ctx) => <ItemTable ctx={ctx} /> },
  byType: { text: (/** @type {any} */ ctx) => <TextLines ctx={ctx} />, header: (/** @type {any} */ ctx) => <TextLines ctx={ctx} /> } };
/** #268: the item sections' headings as the signed-off mockup: a count beside Decisions and Actions, and "Actions" for the
    template's untouched "Action Items" (the view's words only: the record and its exports keep the template's heading).
    @param {import("../report/Sheet.jsx").SheetSection} s */
function mnHeading(s) {
  if (s.id !== "decisions" && s.id !== "actions") return null;
  const rows = /** @type {any[]} */ ((/** @type {any} */ (s)).rows || []).filter(r => r.shown !== false && (r.ref || r.kept_line));
  return { name: s.id === "actions" && s.heading === "Action Items" ? "Actions" : undefined, note: rows.length };
}

const EXTRAS = [{ key: "coverage", after: "open_questions", render: (/** @type {any} */ c) => <Coverage c={c} /> }];

/** The view. */
export function MinutesView() {
  const v = minutesView.value, doc = minutesDoc.value;
  if (!v) return <div class="mnview"><p class="sub">{minutesBusy.value || "Opening the minutes…"}</p></div>;
  if (!v.ok || !doc) return <div class="mnview"><h1 id="mnTitle">Minutes</h1><p class="mnerr" role="alert">{v.message || "Couldn't open the minutes"}</p></div>;
  const draft = doc.state === "draft", turns = (v.turns || { turns: [] }).turns, plan = v.plan ? v.plan.items : null;
  const checks = checksOf(doc, turns, unknownOwner, keptChecks.value);
  const project = String(((doc.meta || {}).projects || [])[0] || doc.project || "");
  const ctx = { checks, onCheck, change, doc, day: doc.date, plan, project, openItem: openStaged };
  const problems = draft && plan ? approveProblems(doc, plan, unknownOwner) : [];
  return (
    <div class="mnview">
      <header class="mnhead">
        <nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="review">Review</a> › <span aria-current="page">Minutes</span></nav>
        <h1 id="mnTitle">{doc.title}</h1>
        <p class="sub mnmeta">{doc.project_name || ""} · {fd(doc.date)} · {draft ? "Draft, not yet approved" : "Approved and filed"}
          {!draft ? " · Filed minutes are never saved over" : ""}</p>
      </header>
      <div class={`mnwrap${paneOpen.value ? " withpane" : ""}`}>
        <div class="mnsheet">
          <MinutesCtx.Provider value={ctx}>
            <Sheet doc={doc} baseVersion={minutesBase.value} scrollKey={`minutes:${v.path}`} readOnly={!draft} zoomMin={MN_ZOOM.min} zoomMax={MN_ZOOM.max} zoomDefault={MN_ZOOM.fit} fitMax={MN_ZOOM.fitMax} continuous headings={mnHeading}
              renderers={RENDER} extras={EXTRAS} checks={checks} onOpenItem={ref => ref.startsWith("@") ? openStaged(ref) : false}
              onChange={onDoc} onSave={async req => {
                const now = minutesView.value;            // a late save of a draft once the minutes are filed is never sent (filed minutes are never saved over)
                if (!now || !now.doc || now.doc.state !== "draft" || req.doc.state !== "draft") return { ok: true, version: minutesBase.value };
                const r = await saveMinutesPage(req); if (r.ok) dirty = false; return r; }}
              ai={{ place: "minutes", project: () => project, confidential: () => false }}
              onRedraft={redrafter(() => ({ path: v.path, version: "internal" }), "minutes")}
              onEvent={ev => { if (ev.type === "reload") loadMinutes({ path: v.path }); else countRedraft(ev, "minutes"); }}
              renderBar={b => <Bar doc={doc} {...b} />} />
          </MinutesCtx.Provider>
        </div>
        <TranscriptPane />
      </div>
      <ApprovePopup problems={problems} checks={checks.filter(c => !(c.kind === "owner" && problems.some(p => p.n === c.n)))} files={v.plan ? v.plan.files : []} transcripts={v.plan ? v.plan.transcripts.length : 0}
        busy={approving.value} onApprove={() => approveNow(true)} />
    </div>
  );
}

let mnMounted = false;
/** Draw the minutes view into #v-minutes and open the minutes: {file} (a proposal), {path} (a record) or the path as a string.
    The transcript is shown or hidden as last chosen (#268). @param {{file?: string, path?: string}|string|null} arg */
export function renderMinutes(arg) {
  const el = $("#v-minutes");
  if (!el) return;
  if (!mnMounted) { render(<MinutesView />, el); mnMounted = true; }
  const a = typeof arg === "string" ? { path: arg } : arg;
  if (a && (a.file || a.path)) {
    dirty = false; keptChecks.value = []; approveOpen.value = false; paneRemembered();
    loadMinutes(a).then(() => { navWrite(false); tabTitle(); });
  }
}

/** The record on screen's stored path (the address keeps it), or null. */
export const minutesPath = () => { const v = minutesView.value; return v && v.ok && v.path ? v.path : null; };

// @ts-check
/* MinutesView (v2.1.0 P7, BL-338): a meeting's minutes in creaite (#minutes=<the record's stored path>), opened from Review's
   Open draft on a minutes record, and later from the meeting's links (P10). It sits under Review in the sidebar: no new
   top-level page. Built on the sheet's contract (dev/sprints/v210-contract.md §4) with the stub sheet for now
   (components/report/SheetStub.jsx); moving to P5's Sheet.jsx is changing the import.
   The view supplies its own renderers (TextLines for text sections, ItemRow for the item tables), the coverage extra and the
   checks, keeps the document (stores/minutes.js) and makes its own server calls (P4's /api/minutes/*). Beside the sheet, the
   transcript pane. The bar: versions, One version or Internal + distributed (with Internal, Distributed and Side by side), the
   transcript, the open checks, Export and Approve minutes. A change to an item row saves any page edits first, then makes the
   change, so the record and its proposal never part. Nothing here sends anything. */
import { render } from "preact";
import { useLayoutEffect, useRef } from "preact/hooks";
import { Menu } from "../Menu.jsx";
import { SheetStub } from "../report/SheetStub.jsx";
import { ApprovePopup } from "./ApprovePopup.jsx";
import { MinutesCtx } from "./context.js";
import { Coverage } from "./Coverage.jsx";
import { ItemRow } from "./ItemRow.jsx";
import { checksOf, distributedOf, leftOut } from "./minutesDoc.js";
import { TextLines } from "./TextLines.jsx";
import { jumpTo, TranscriptPane } from "./TranscriptPane.jsx";
import { REV } from "../../core/data.js";
import { $ } from "../../core/dom.js";
import { openPath } from "../../core/fields.js";
import { navWrite, tabTitle } from "../../core/nav.js";
import { fd } from "../../core/page.js";
import { snack } from "../../core/server.js";
import { openProposal } from "../../panel.js";
import { unknownOwner } from "../../settings.js";
import { approveOpen, changeMinutes, exportMinutes, keptChecks, loadMinutes, minutesBase, minutesBusy, minutesDoc, minutesMode,
  minutesView, paneOpen, saveMinutesPage } from "../../stores/minutes.js";

/** @typedef {import("../report/SheetStub.jsx").SheetDoc} SheetDoc */
/** @typedef {import("./minutesDoc.js").Check} Check */

let dirty = false;

/** Give matching sections, and the blocks marked with ctx.level inside them, the same height on both pages of Side by side, so
    their headings stay level (contract §4.6; P5's sheet does this itself, and then this finds nothing to change).
    @param {HTMLElement|null} box */
export function levelPair(box) {
  const pages = box ? /** @type {HTMLElement[]} */ ([...box.querySelectorAll(".sheet-pair > .page")]) : [];
  if (pages.length !== 2) return;
  const [l, r] = pages;
  const pairs = (/** @type {string} */ sel, /** @type {string} */ attr, /** @type {HTMLElement} */ a, /** @type {HTMLElement} */ b) =>
    /** @type {HTMLElement[]} */ ([...a.querySelectorAll(sel)]).map(x => [x, /** @type {HTMLElement|null} */ (b.querySelector(`${sel.split("[")[0]}[${attr}="${CSS.escape(x.getAttribute(attr) || "")}"]`))]);
  const even = (/** @type {[HTMLElement, HTMLElement|null][]} */ ps) => {
    for (const [a, b] of ps) { a.style.minHeight = ""; if (b) b.style.minHeight = ""; }
    for (const [a, b] of ps) { if (!b) continue; const h = Math.max(a.getBoundingClientRect().height, b.getBoundingClientRect().height); a.style.minHeight = b.style.minHeight = `${h}px`; }
  };
  /* A creaite-only extra between sections (coverage) has no peer on the right: whichever page's next section starts lower, the
     other page's section grows by the difference, top to bottom (margins and all). */
  const nextSec = (/** @type {Element} */ x) => { let n = x.nextElementSibling; while (n && !(n.matches("section[data-id]"))) n = n.nextElementSibling; return /** @type {HTMLElement|null} */ (n); };
  const close = (/** @type {[HTMLElement, HTMLElement|null][]} */ ps) => {
    for (const [a, b] of ps) {
      const an = b && nextSec(a), bn = b && nextSec(b);
      if (!b || !an || !bn) continue;
      const d = an.getBoundingClientRect().top - bn.getBoundingClientRect().top;
      if (d > 0.5) b.style.minHeight = `${b.getBoundingClientRect().height + d}px`;
      else if (d < -0.5) a.style.minHeight = `${a.getBoundingClientRect().height - d}px`;
    }
  };
  const secs = /** @type {[HTMLElement, HTMLElement|null][]} */ (pairs("section[data-id]", "data-id", l, r));
  for (const [a, b] of secs) if (b) even(/** @type {[HTMLElement, HTMLElement|null][]} */ (pairs("[data-level]", "data-level", a, b)));
  even(secs);
  close(secs);
}

/** The staged item of a row ("@3") in the peek: its Review proposal. @param {string} ref */
function openStaged(ref) {
  const v = minutesView.value, n = Number(String(ref).replace(/^@/, ""));
  const r = v && REV.find(x => x.file === v.proposal && x.ref === n);
  if (r) openProposal(r.n); else snack("That item is no longer pending in Review.");
  return true;
}

/** The bar's buttons (the sheet's `toolbar` slot). @param {{doc: SheetDoc, checks: Check[]}} props */
function Bar({ doc, checks }) {
  const v = minutesView.value, versions = (v && v.versions) || [], draft = doc.state === "draft";
  const dist = !!(doc.layout || {}).distributed, mode = minutesMode.value;
  const setDist = (/** @type {boolean} */ on) => { onDoc({ ...doc, layout: { ...(doc.layout || {}), distributed: on } }, on ? "Distributed version on" : "One version"); if (!on) minutesMode.value = "internal"; };
  const exp = async (/** @type {string} */ id) => {
    const [fmt, which] = id.split(":"), version = which === "distributed" ? "distributed" : "internal";
    const out = version === "distributed" ? leftOut(doc, v && v.withheld) : [];
    const r = await exportMinutes(fmt, version);
    const left = out.length ? ` · leaves out ${out.length}: ${out.slice(0, 2).join("; ")}${out.length > 2 ? "…" : ""}` : "";
    snack(r.ok ? `Exported${r.path ? `: ${String(r.path).split("/").pop()}` : ""}${left}` : String(r.message || "Not exported").split("\n")[0]);
  };
  const formats = [{ id: "html", name: "HTML", line: "A read-only page, filed beside the minutes" }, { id: "docx", name: "Word", line: "The minutes template" },
    { id: "pdf", name: "PDF", line: "Printed from the page" }];
  const exports = dist ? [...formats.map(f => ({ ...f, id: `${f.id}:internal`, name: `Internal: ${f.name}` })),
    ...formats.map(f => ({ ...f, id: `${f.id}:distributed`, name: `Distributed: ${f.name}`,
      line: draft ? "Once the internal minutes are approved" : `${f.line}, under a new name` }))] : formats;
  return (
    <span class="mnbarr">
      <Menu label={`Version ${doc.version || 1}`} icon="history" btnCls="btn sm" menuLabel="Versions of these minutes" data={{ mnversions: "" }}
        items={versions.map(x => ({ id: String(x.version), name: `Version ${x.version}${x.current ? " · on screen" : ""}`,
          line: `${x.at ? fd(x.at) : ""}${x.why ? ` · ${x.why}` : ""}${!x.current && x.backup ? " · opens the kept copy" : ""}` }))}
        onPick={id => { const x = versions.find(y => String(y.version) === id); if (x && !x.current && x.backup) openPath(x.backup); }} />
      <span class="seg" role="group" aria-label="Versions to keep">
        <button type="button" aria-pressed={dist ? "false" : "true"} disabled={!draft} onClick={() => setDist(false)}>One version</button>
        <button type="button" aria-pressed={dist ? "true" : "false"} disabled={!draft} onClick={() => setDist(true)}>Internal + distributed</button>
      </span>
      {dist ? <span class="seg" role="group" aria-label="Show">
        {[["internal", "Internal"], ["distributed", "Distributed"], ["side", "Side by side"]].map(([k, l]) =>
          <button key={k} type="button" data-mnmode={k} aria-pressed={mode === k ? "true" : "false"} onClick={() => { minutesMode.value = /** @type {any} */ (k); }}>{l}</button>)}
      </span> : null}
      <button type="button" class="btn sm" aria-pressed={paneOpen.value ? "true" : "false"} onClick={() => { paneOpen.value = !paneOpen.value; }}>Transcript</button>
      {draft && checks.length ? <span class="tag mnckcount" role="status">{checks.length} check{checks.length === 1 ? "" : "s"} open</span> : null}
      <Menu label="Export" icon="filetext" btnCls="btn sm" menuLabel="Export the minutes" data={{ mnexport: "" }}
        items={exports} onPick={exp} />
      {draft ? <button type="button" class="btn sm primary" id="mnApproveBtn" disabled={!(v && v.plan)} data-tip={v && v.plan ? undefined : "Nothing pending to approve"}
        onClick={() => { approveOpen.value = true; }}>Approve minutes</button> : null}
    </span>
  );
}

/** Every edit from the sheet: kept on the page, saved by the sheet (⌘S, Save) or before the next row change.
    @param {SheetDoc} d @param {string} _why */
function onDoc(d, _why) { minutesDoc.value = d; dirty = true; }

/** One row or coverage change: page edits saved first, then the change; Undo on the toast when there is one.
    @param {Record<string, any>} op @param {Record<string, any>|null} [undo] */
async function change(op, undo) {
  const d = minutesDoc.value;
  if (dirty && d) { const s = await saveMinutesPage({ doc: d, base_version: minutesBase.value }); if (!s.ok) { snack(s.message || "The minutes weren't saved"); return false; } dirty = false; }
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
  else if (action === "pick") /** @type {HTMLElement|null} */ (document.querySelector(`[data-owner="${c.n}"]`))?.click();
}

const RENDER = { byType: { text: (/** @type {any} */ ctx) => <TextLines ctx={ctx} />, header: (/** @type {any} */ ctx) => <TextLines ctx={ctx} /> },
  row: { actions: (/** @type {any} */ rc) => <ItemRow rc={rc} />, decisions: (/** @type {any} */ rc) => <ItemRow rc={rc} />, raid: (/** @type {any} */ rc) => <ItemRow rc={rc} /> } };
const EXTRAS = [{ key: "coverage", after: "open_questions", render: (/** @type {any} */ c) => <Coverage c={c} /> }];

/** The view. */
export function MinutesView() {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  const v = minutesView.value, doc = minutesDoc.value, mode = minutesMode.value;
  const dist = !!(doc && (doc.layout || {}).distributed), side = dist && mode === "side";
  useLayoutEffect(() => {
    const el = box.current;
    if (el && !side) /** @type {NodeListOf<HTMLElement>} */ (el.querySelectorAll(".page section[data-id], .page [data-level]")).forEach(x => { x.style.minHeight = ""; });
    if (!side || !el) return;
    levelPair(el);
    const ro = new ResizeObserver(() => levelPair(el));
    el.querySelectorAll(".sheet-pair > .page").forEach(p => ro.observe(p));
    return () => ro.disconnect();
  });
  if (!v) return <div class="mnview"><p class="sub">{minutesBusy.value || "Opening the minutes…"}</p></div>;
  if (!v.ok || !doc) return <div class="mnview"><h1 id="mnTitle">Minutes</h1><p class="mnerr" role="alert">{v.message || "Couldn't open the minutes"}</p></div>;
  const draft = doc.state === "draft", turns = (v.turns || { turns: [] }).turns;
  const checks = checksOf(doc, turns, unknownOwner, keptChecks.value);
  const held = v.withheld || {}, shown = dist && mode === "distributed" ? distributedOf(doc, held) : doc;
  const ctx = { checks, onCheck, change, setDoc: onDoc, doc, day: doc.date, distributed: dist && mode !== "distributed", partner: false, openItem: openStaged, held };
  return (
    <div class="mnview" ref={box}>
      <header class="mnhead">
        <nav class="crumb" aria-label="Breadcrumb"><a href="#" data-go="review">Review</a> › <span aria-current="page">Minutes</span></nav>
        <h1 id="mnTitle">{doc.title}</h1>
        <p class="sub mnmeta">{doc.project_name || ""} · {fd(doc.date)} · {draft ? "Draft, not yet approved" : "Approved and filed"}
          {!draft ? " · Filed minutes are never saved over" : ""}</p>
      </header>
      <div class={`mnwrap${paneOpen.value ? " withpane" : ""}`}>
        <div class="mnsheet">
          <MinutesCtx.Provider value={ctx}>
            <SheetStub doc={shown} baseVersion={minutesBase.value} scrollKey={`minutes:${v.path}:${mode}`} readOnly={!draft || (dist && mode === "distributed")}
              renderers={RENDER} extras={EXTRAS} checks={checks} onOpenItem={ref => ref.startsWith("@") ? openStaged(ref) : false}
              partner={side ? { doc: distributedOf(doc, held), label: "Distributed", readOnly: true, renderers: RENDER, onChange: () => {} } : null}
              onChange={onDoc} onSave={async req => { const r = await saveMinutesPage(req); if (r.ok) dirty = false; return r; }}
              onEvent={ev => { if (ev.type === "reload") loadMinutes({ path: v.path }); }}
              toolbar={<Bar doc={doc} checks={checks} />} />
          </MinutesCtx.Provider>
        </div>
        <TranscriptPane />
      </div>
      <ApprovePopup checks={checks} />
    </div>
  );
}

let mnMounted = false;
/** Draw the minutes view into #v-minutes and open the minutes: {file} (a proposal), {path} (a record) or the path as a string.
    @param {{file?: string, path?: string}|string|null} arg */
export function renderMinutes(arg) {
  const el = $("#v-minutes");
  if (!el) return;
  if (!mnMounted) { render(<MinutesView />, el); mnMounted = true; }
  const a = typeof arg === "string" ? { path: arg } : arg;
  if (a && (a.file || a.path)) {
    dirty = false; keptChecks.value = []; minutesMode.value = "internal";
    loadMinutes(a).then(() => { navWrite(false); tabTitle(); });
  }
}

/** The record on screen's stored path (the address keeps it), or null. */
export const minutesPath = () => { const v = minutesView.value; return v && v.ok && v.path ? v.path : null; };

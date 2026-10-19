// @ts-check
/* ClientParts (v2.1.0 P8, BL-336; #221): what is the client report's OWN. The client report is the same sheet as the internal one
   (ReportSheet, ReportParts.jsx: the header, the health indicator, the tables with their eyes, "Add from the tracker", At a glance, the
   words, Current state); only its audience differs, and this file holds exactly that:
   - Health: the client's flag (Change opens the reason it needs when it differs from the internal one) and its headline; Match
     internal health takes the internal flag and headline.
   - Tables (risks, overdue, asks, decisions): client-visible rows only. "Not in this report" lists what the tracker holds that the
     report leaves out, with Make client-visible… (the standard peek) and, for a Sensitive or partner-only item, the plain reason it can
     never be shown; Add for a row that became client-visible since.
   - Milestones in the client's words (no timeline picture: the client sees the agreed state, not the internal dates).
   - Every section: Matching internal or Edited for the client, and Match internal (clientDoc.matchClientSection: client-safe).
   Everything drawn here is the client document's own content; the internal report is read only. */
import { signal } from "@preact/signals";
import { useEffect, useRef, useState } from "preact/hooks";
import { cellsFor, CLIENT_FLAGS, flagOf, healthDiff, matchState, secOf } from "./clientDoc.js";
import { EyeButton } from "./EyeButton.jsx";
import { AddFromTracker, EyeTable, HealthBlock, ReportHeader } from "./ReportParts.jsx";
import { openRef } from "./Sheet.jsx";
import { Glance } from "./weekly/Glance.jsx";
import { CurrentState, Words } from "./weekly/Notes.jsx";
import { Rich } from "./weekly/Rich.jsx";
import { weeklyLogos } from "../../stores/weekly.js";
import { crCheck, crDirty, crDoc, crInternal, crLogos, matchInternal, runCheck, sameReport } from "../../stores/clientReport.js";
import { FreeText } from "./SheetPage.jsx";
import { api, viaServer } from "../../core/server.js";

/** @typedef {import("./Sheet.jsx").SectionCtx} SectionCtx */
/** @typedef {import("./Sheet.jsx").SheetDoc} SheetDoc */

/** v2.5.1 (#239): Show as exported for the client report is the server's own render (POST /api/report/exported-view): a preview snapshot
    of the report as last saved, built, checked and rendered as the export is, marked Preview; never a page drawn here. An answer is
    used only for the report shown (its project and week, and the version asked for: P12). @param {{doc: SheetDoc, version: number}} props */
export function ServerExported({ doc, version }) {
  const [got, setGot] = useState(/** @type {any} */ (null));
  const asked = `${doc.project}|${doc.date}|${version}`;
  useEffect(() => {
    let live = true;
    setGot(null);
    if (!viaServer()) { setGot({ ok: false, message: "Show as exported needs the live server." }); return undefined; }
    api("/api/report/exported-view", { kind: "client", code: doc.project, week_ending: doc.date }).then(r => {
      const id = (r && r.identity) || {};
      if (live && r && id.code === doc.project && id.week_ending === doc.date) setGot(r);
    });
    return () => { live = false; };
  }, [asked]);
  if (!got) return <p class="sub crx-wait" role="status">Making the page as it is exported…</p>;
  if (!got.ok) {
    const why = (got.findings || []).join("; ") || got.message || "it couldn't be made";
    return <p class="mnerr crx-err" role="alert">This client report can't be exported as it is: {why}</p>;
  }
  return (
    <div class="crx" data-preview={got.preview ? "1" : undefined}>
      {got.preview ? <span class="crx-badge">Preview</span> : null}
      <iframe class="crx-frame" title="The client report as it is exported" sandbox="" srcdoc={got.html} />
    </div>);
}

/** #203: set when Use on the health suggestion records a flag that differs from the internal one: the flag's popover then opens by itself,
    on its reason, so Alan writes why (nothing else forces it). */
export const crAskWhy = signal(false);

/** Take a new client document onto the page: only one of the report that is open (a late answer for another project, week or client,
    from a sheet that awaited the server before another report opened, is dropped). @param {SheetDoc} next */
export function setClientDoc(next) { if (!sameReport(next)) return; crDoc.value = next; crDirty.value = true; }

/** Match one section to the internal report. @param {string} id */
export function matchOne(id) {
  matchInternal([id]);        // behind the client gate: a section with internal wording is held back (stores/clientReport.js)
}

/** The line above a section's body: Matching internal or Edited for the client, and Match internal. Only while editing.
    @param {{ctx: SectionCtx}} props */
function MatchBar({ ctx }) {
  const d = crDoc.value, i = crInternal.value;
  if (!ctx.editing || !d || !i || ctx.peer) return null;     // in Side by side the sheet's own Match internal (partner.match) is drawn
  const st = matchState(d, i, ctx.section.id);
  if (!st) return null;
  return (
    <div class="crmatch" data-match={ctx.section.id}>
      <span class={`crmstate ${st}`}>{st === "matching" ? "Matching internal" : "Edited for the client"}</span>
      <button type="button" class="btn sm" data-matchone={ctx.section.id} disabled={st === "matching"} onClick={() => matchOne(ctx.section.id)}>Match internal</button>
    </div>
  );
}

/** A section's body with its match line. @param {{ctx: SectionCtx, children?: any}} props */
function Sec({ ctx, children }) {
  return <div class="crsec"><MatchBar ctx={ctx} />{children}</div>;
}

/** A popover under its anchor: Esc and a click outside close it, with focus back on the button that opened it.
    @param {{label: string, onClose: () => void, anchor: {current: HTMLElement|null}, children?: any}} props */
function ClientPop({ label, onClose, anchor, children }) {
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  useEffect(() => {
    const a = anchor.current;
    const first = box.current && /** @type {HTMLElement|null} */ (box.current.querySelector("button,textarea,input"));
    if (first) first.focus();
    const away = (/** @type {MouseEvent} */ e) => { if (box.current && !box.current.contains(/** @type {Node} */ (e.target)) && !(a && a.contains(/** @type {Node} */ (e.target)))) onClose(); };
    document.addEventListener("mousedown", away);
    return () => { document.removeEventListener("mousedown", away); if (a && a.isConnected) a.focus(); };
  }, []);
  return <div class="crpop" role="dialog" aria-label={label} ref={box} onKeyDown={e => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } }}>{children}</div>;
}

/** The client's health: flag, headline, and the popover that changes them (a reason is required when it differs).
    @param {{ctx: SectionCtx}} props */
export function ClientHealth({ ctx }) {
  const [open, setOpen] = useState(false);
  const [pick, setPick] = useState("");
  const [why, setWhy] = useState("");
  const btn = useRef(/** @type {HTMLButtonElement|null} */ (null));
  const d = crDoc.value, internal = crInternal.value;
  const flag = flagOf(d) || "On track", inFlag = flagOf(internal), diff = (((d || {}).meta || {}).health_diff) || null;
  const edit = ctx.editing;
  const begin = () => { setPick(flag); setWhy(diff ? String(diff.reason || "") : ""); setOpen(true); };
  const save = () => {
    if (!d) return;
    if (pick !== inFlag && !why.trim()) return;
    const next = { ...secOf(d, "health") };
    setClientDoc({ ...d, sections: d.sections.map(s => s.id === "health" ? { ...s, data: { ...(next.data || {}), flag: pick } } : s),
      meta: healthDiff(d, inFlag, pick, why) });
    setOpen(false);
  };
  const matchHealth = () => { matchOne("health"); setOpen(false); };
  const needWhy = pick !== inFlag && !why.trim();
  const ask = crAskWhy.value, focusWhy = useRef(false);
  useEffect(() => {
    if (!ask || !d || !edit || !diff) return;                  // wait for the document that holds the difference
    crAskWhy.value = false;
    if (!String(diff.reason || "").trim()) { focusWhy.current = true; begin(); }
  }, [ask, diff]);
  useEffect(() => {                                   // the popover opened for the reason: the cursor goes to it (after the popover's own first focus)
    if (open && focusWhy.current) { focusWhy.current = false; setTimeout(() => /** @type {HTMLElement|null} */ (document.getElementById("crWhy"))?.focus(), 0); }
  }, [open]);
  return (
    <>
      <HealthBlock ctx={ctx} flag={flag} trend={null} flagCls="crflag"
        change={<button type="button" class="btn sm wr-chg" ref={btn} aria-haspopup="dialog" aria-expanded={open ? "true" : "false"} data-crflag onClick={() => open ? setOpen(false) : begin()}>Change</button>}
        why={<>
          {edit && inFlag && flag !== inFlag ? <span class="crdif" title={`Internal: ${inFlag}. ${diff && diff.reason ? diff.reason : ""}`} data-crdif>≠ internal: {inFlag}</span> : null}
          <MatchBar ctx={ctx} />
          <Rich ctx={ctx} text={ctx.section.text} label="The client's headline" empty="Say how it is going, for the client" />
        </>} />
      {open ? (
        <ClientPop label="Client health" anchor={btn} onClose={() => setOpen(false)}>
          <b>Client health</b>
          <div class="cropts" role="group" aria-label="Health">
            {CLIENT_FLAGS.map(([name]) => <button key={name} type="button" aria-pressed={pick === name ? "true" : "false"} data-crpick={name} onClick={() => setPick(name)}>{name}</button>)}
          </div>
          <label class="sub" for="crWhy">{pick !== inFlag ? "Why it differs from the internal health (required; kept internally, never on the client's page)" : "The same as the internal health"}</label>
          <textarea id="crWhy" value={why} disabled={pick === inFlag} onInput={e => setWhy(/** @type {HTMLTextAreaElement} */ (e.currentTarget).value)} />
          <div class="crpopacts">
            <button type="button" class="btn sm" data-crmatchhealth onClick={matchHealth}>Match internal health</button>
            <span><button type="button" class="btn sm" onClick={() => setOpen(false)}>Cancel</button>{" "}
              <button type="button" class="btn sm primary" data-crhsave disabled={needWhy} onClick={save}>Save</button></span>
          </div>
        </ClientPop>
      ) : null}
    </>
  );
}

/** The header: the same title block and logos as the internal report. @param {{ctx: SectionCtx}} props */
export function ClientHeader({ ctx }) {
  return <ReportHeader ctx={ctx} logos={crLogos.value} data={weeklyLogos.value} />;
}

/** The milestones in the client's words, with an eye on each to pick the list. @param {{ctx: SectionCtx}} props */
export function MilestonesSection({ ctx }) {
  const s = ctx.section, data = s.data || {}, all = /** @type {string[]} */ (data.timeline || []), listed = /** @type {string[]} */ (data.milestones || all);
  const items = ctx.doc.items || {};
  const flip = (/** @type {string} */ ref) => ctx.update({ data: { ...data, milestones: listed.includes(ref) ? listed.filter(x => x !== ref) : all.filter(x => x === ref || listed.includes(x)) } }, "Milestone list changed");
  const rows = ctx.editing ? all : listed;
  if (!all.length) return <Sec ctx={ctx}><p class="sub">No client-visible milestones yet.</p></Sec>;
  return (
    <Sec ctx={ctx}>
      <div class="wr-tbl">
        <table class="wr-r"><thead><tr>{ctx.editing ? <th class="eyec"><span class="sr">In the list</span></th> : null}<th>Milestone</th><th>Expected</th><th>State</th></tr></thead><tbody>
          {rows.map(ref => { const it = items[ref] || {}, on = listed.includes(ref);
            return <tr key={ref} class={on ? "" : "hidrow"}>
              {ctx.editing ? <td class="eyec"><EyeButton on={on} subject={it.title || ref} data={{ crmile: ref }} onClick={() => flip(ref)} /></td> : null}
              <td>{it.title || ref}</td><td class="num">{it.shown_date || ""}</td><td><span class="crstate">{it.state || it.status || ""}</span></td></tr>; })}
        </tbody></table>
      </div>
    </Sec>
  );
}

/** A table section, drawn with the shared eye table: client-visible rows, the "Not in this report" list, Add for a row that became
    client-visible since, and Add from the tracker. @param {{ctx: SectionCtx}} props */
export function ClientTable({ ctx }) {
  const s = ctx.section, cols = s.columns || [], items = ctx.doc.items || {};
  const check = crCheck.value, group = s.id;
  const left = ctx.editing && check && check.left_out ? check.left_out.items.filter(x => x.group === group && (x.kind === "blocked" || x.kind === "sensitive")) : [];
  const add = ctx.editing && check && check.addable ? check.addable.filter(a => a.section === group) : [];
  const shape = cols.map((c, k) => ({ key: c.key, label: c.label, cell: (/** @type {any} */ r) => <>
    <Rich ctx={ctx} text={r.cells[c.key]} row={r.i} col={c.key} label={c.label} empty="Click to write" />
    {k === 0 && !ctx.exported && s.id === "overdue" && (items[String(r.row.ref)] || {}).client_owned === false ? <span class="crlk">not the client's own</span> : null}</> }));
  const notIn = ctx.editing && (left.length || add.length) ? (
    <div class="crnot" data-crnot={group}>
      <div class="crnoth">Not in this report <button type="button" class="linkbtn" data-crrecheck onClick={() => runCheck()}>Check again</button></div>
      <ul>
        {add.map(a => <li key={"a" + a.row.ref}><ctx.ItemRef id={String(a.row.ref)} /> {(a.item && a.item.title) || ""} <span class="crlk ok">now client-visible</span>{" "}
          <button type="button" class="btn sm" data-cradd={String(a.row.ref)} onClick={() => {
            const d = crDoc.value; if (!d) return;
            setClientDoc({ ...d, items: { ...(d.items || {}), [String(a.row.ref)]: a.item }, sections: d.sections.map(x => x.id === s.id ? { ...x, rows: [...(x.rows || []), a.row] } : x) });
          }}>Add</button></li>)}
        {left.map(x => <li key={x.ref} data-crleft={x.ref}><ctx.ItemRef id={x.ref} /> {x.title} <span class={`crlk${x.kind === "sensitive" ? " lock" : ""}`}>{x.kind === "sensitive" ? "⊘ " : ""}{x.why}</span>{" "}
          {x.kind === "blocked" ? <button type="button" class="btn sm" data-crvisible={x.ref} onClick={() => openRef(x.ref, undefined)}>Make client-visible…</button> : null}</li>)}
      </ul>
    </div>) : null;
  return (
    <Sec ctx={ctx}>
      <EyeTable ctx={ctx} cols={shape} noun={s.heading.toLowerCase()} empty={ctx.editing ? "Nothing client-visible here yet." : ""}
        cellsFor={(sid, item) => cellsFor(sid, item)} leftOut="this client's report" extra={<>{notIn}<AddFromTracker ctx={ctx} /></>} />
    </Sec>
  );
}

/** Summary, Progress and Next steps: the words, in the one editor, with the section's match line. @param {{ctx: SectionCtx}} props */
export function TextSection({ ctx }) {
  return <Sec ctx={ctx}><Words ctx={ctx} label={ctx.section.heading} empty="Say it for the client" /></Sec>;
}

/** Current state, for the client: the panes are edited here, never the project's own. @param {{ctx: SectionCtx}} props */
export function PanesSection({ ctx }) {
  return <Sec ctx={ctx}><CurrentState ctx={ctx} /></Sec>;
}

/** The renderers for the client page, by section id: the shared parts where the internal report has the same section. */
export const CLIENT_RENDERERS = {
  byId: {
    header: (/** @type {SectionCtx} */ ctx) => <ClientHeader ctx={ctx} />,
    health: Object.assign((/** @type {SectionCtx} */ ctx) => <ClientHealth ctx={ctx} />, { ownSpark: true }),
    glance: (/** @type {SectionCtx} */ ctx) => <Glance ctx={ctx} />, milestones: (/** @type {SectionCtx} */ ctx) => <MilestonesSection ctx={ctx} />,
    current_state: (/** @type {SectionCtx} */ ctx) => <PanesSection ctx={ctx} />,
  },
  byType: { text: (/** @type {SectionCtx} */ ctx) => <TextSection ctx={ctx} />, table: (/** @type {SectionCtx} */ ctx) => <ClientTable ctx={ctx} />,
    freetext: (/** @type {SectionCtx} */ ctx) => <Sec ctx={ctx}><FreeText ctx={ctx} /></Sec> },      // #218: a text section, with its Matching internal line when the internal report has it
};

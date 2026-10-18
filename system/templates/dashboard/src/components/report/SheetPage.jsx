// @ts-check
/* SheetPage (v2.1.0 P5, contract §4.2 to §4.7): one A4 page of the sheet. Its sections in list order, each through the view's
   renderers (`byId`, then `byType`, then the default for the §1 type), with the section chrome while editing: a handle to move
   (drag, or Alt+↑ and Alt+↓), a menu (Hide, Move, Reset heading), a heading that is renamed in place, ✦ for a fresh draft, and
   "Remove all tags". Hidden sections are a thin bar with Show. The page's markup uses creaite_doc.render's classes (.page,
   header.doc, section[data-id], h2, table, .figure) so editing and Show as exported differ only by the controls. Text only
   through JSX. */
import { createContext } from "preact";
import { useContext, useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { openMilestone, msFind } from "../../milestones.js";
import { openRecord } from "../../panel.js";
import { kOfId } from "../../work.js";
import { Icon } from "../Icon.jsx";
import { openMenu } from "../Menu.jsx";
import { EyeButton } from "./EyeButton.jsx";
import { SheetEditor, mdNodes } from "./SheetText.jsx";
import { defaultHeading, hideSection, isTextSection, matchLabel, moveBy, moveFigure, moveSection, renameHeading, resetHeading,
  rowCounts, sectionDiffers, setFigureShown, showSection, syncLayout, withTextSection, withoutSection } from "./sheetLib.js";
import { markNewText, takeNewText } from "../../stores/textSection.js";

/** @typedef {import("./Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {import("./Sheet.jsx").SheetSection} SheetSection */
/** @typedef {import("./Sheet.jsx").SheetEvent} SheetEvent */
/** @typedef {import("./Sheet.jsx").SectionCtx} SectionCtx */
/** @typedef {import("./Sheet.jsx").RowCtx} RowCtx */
/** @typedef {import("./Sheet.jsx").SheetTag} SheetTag */
/** @typedef {import("./Sheet.jsx").SheetProps} SheetProps */

/** Open the standard peek (with Sneak peek in it) for a ref: the view's own first, then a milestone's page, then the record's.
    @param {string} ref @param {((r: string) => boolean)|undefined} own */
export function openSheetRef(ref, own) {
  if (own && own(ref)) return;
  if (/-M-\d+$/.test(ref)) openMilestone(ref); else openRecord("all", ref);
}
/** True when the tracker or the document holds the ID (an ID that isn't found is drawn as plain text). @param {string} id @param {SheetDoc} doc */
const known = (id, doc) => !!((doc.items || {})[id] || (/-M-\d+$/.test(id) ? msFind(id).m : kOfId(id)));

/** @typedef {{s: SheetSection, doc: SheetDoc, editing: boolean, exported: boolean, readOnly: boolean, ai: any, checks: any[],
    update: (p: Partial<SheetSection>, why: string) => void, onOpenItem?: (ref: string) => boolean, onEvent: (e: SheetEvent) => void,
    spark: (() => void)|null, sparkInHeading: boolean}} Here */
const SHEET_HERE = createContext(/** @type {Here|null} */ (null));

/** A field of the section as text: the one editor while editing, the exported markup in Show as exported.
    @param {import("./Sheet.jsx").TextProps} props */
function Text({ field = "text", rich = false, row, col, pane, label }) {
  const h = /** @type {Here} */ (useContext(SHEET_HERE)), s = /** @type {any} */ (h.s);
  const cell = row != null && col != null, isPane = pane != null;
  const value = cell ? ((s.rows || [])[/** @type {number} */ (row)] || {}).cells?.[/** @type {string} */ (col)] || "" : isPane ? ((s.panes || [])[/** @type {number} */ (pane)] || {}).text || "" : s[field] || "";
  if (h.exported) return rich || isPane ? <div class="sheet-md">{mdNodes(value)}</div> : <span>{value}</span>;
  const mine = h.checks.map((c, n) => ({ ...c, n })).filter(c => c.section === s.id
    && (cell ? c.row === row && c.field === col : isPane ? c.pane === pane : c.row == null && (c.field || "text") === field));
  const onText = (/** @type {string} */ t) => {
    if (cell) { const rows = (s.rows || []).slice(); rows[/** @type {number} */ (row)] = { ...rows[/** @type {number} */ (row)], cells: { ...(rows[/** @type {number} */ (row)].cells || {}), [/** @type {string} */ (col)]: t } }; h.update({ rows }, "Row edited"); }
    else if (isPane) { const panes = (s.panes || []).slice(); panes[/** @type {number} */ (pane)] = { ...panes[/** @type {number} */ (pane)], text: t }; h.update({ panes }, "Text edited"); }
    else h.update({ [field]: t }, "Text edited");
  };
  const name = label || (cell ? String(col) : isPane ? ((s.panes || [])[/** @type {number} */ (pane)] || {}).title : s.heading) || s.heading;
  return <SheetEditor value={value} rich={rich || isPane} label={name} onText={onText} ai={rich || isPane ? h.ai : undefined} checks={mine}
    multiline={false} editable={h.editing} />;
}

/** An item ID that opens the standard peek; an ID nobody knows is plain text. @param {{id: string}} props */
function ItemRef({ id }) {
  const h = /** @type {Here} */ (useContext(SHEET_HERE));
  if (h.exported || !known(id, h.doc)) return <span>{id}</span>;
  return <button type="button" class="linkbtn sheet-ref" onClick={() => { openSheetRef(id, h.onOpenItem); h.onEvent({ type: "item", ref: id }); }}>{id}</button>;
}

/** @param {SheetTag} t */
const isTimeTag = t => t.ref === "transcript" || t.ref.startsWith("t:");
/** A source tag: a small chip after its line; hover shows ✕. creaite only, never exported. @param {{tag: SheetTag}} props */
function Tag({ tag }) {
  const h = /** @type {Here} */ (useContext(SHEET_HERE));
  if (h.exported) return null;
  const open = () => { if (isTimeTag(tag)) h.onEvent({ type: "tag", tag }); else { openSheetRef(tag.ref, h.onOpenItem); h.onEvent({ type: "item", ref: tag.ref }); } };
  const tags = /** @type {any} */ (h.s).tags || [];
  return <span class="sheet-tagw"><button type="button" class="chip sheet-tag" onClick={open}>{tag.text || tag.ref}</button>
    {h.editing ? <button type="button" class="sheet-tagx" aria-label={`Remove the tag ${tag.text || tag.ref}`} onClick={() => {
      h.update({ tags: tags.filter((/** @type {SheetTag} */ t) => t !== tag) }, "Tag removed"); h.onEvent({ type: "tag", tag, removed: true }); }}>✕</button> : null}</span>;
}
/** ✦ for a renderer that draws its own heading row; nothing when the sheet draws it beside the heading. */
function Spark() {
  const h = /** @type {Here} */ (useContext(SHEET_HERE));
  return h.spark && !h.sparkInHeading && !h.exported ? <SparkButton on={h.spark} heading={h.s.heading} health={h.s.type === "health"} /> : null;
}
/** @param {{on: () => void, heading: string, health?: boolean}} props */
function SparkButton({ on, heading, health }) {
  return <button type="button" class="sheet-spark" aria-label={health ? "Suggest health and reason" : `Suggest a fresh draft of ${heading}`} data-tip="Suggest a fresh draft" onClick={on}><Icon name="spark" /></button>;
}

/** @param {SheetSection} s */
const tagsOf = s => /** @type {SheetTag[]} */ ((/** @type {any} */ (s)).tags || []);

/** The stand-in for every §1 type: text, a table's rows, figures, panes, health, timeline. @param {{ctx: SectionCtx, rowFn?: (c: RowCtx) => any}} props */
function SheetDefault({ ctx, rowFn }) {
  const s = /** @type {any} */ (ctx.section), { Text: T, ItemRef: Ref, Tag: Tg } = ctx;
  const live = ctx.editing;
  if (isTextSection(s)) return <FreeText ctx={ctx} />;
  if (s.type === "table") return <TableBody ctx={ctx} rowFn={rowFn} />;
  if (s.type === "figures") return <Figures ctx={ctx} />;
  if (s.type === "panes") return <div class="panes">{(s.panes || []).map((/** @type {any} */ p, /** @type {number} */ i) => <div key={i}><h3>{p.title}</h3><T pane={i} /></div>)}</div>;
  const extra = s.type === "health" && (s.data || {}).flag ? <p class="flag">{s.data.flag}</p> : null;
  const miles = s.type === "timeline" ? (((s.data || {}).milestones) || []).map((/** @type {string} */ ref) => ({ ref, m: (ctx.doc.items || {})[ref] })) : [];
  return <div>{extra}<T rich />
    {!ctx.exported && (live || tagsOf(s).length) ? <span class="sheet-tags">{tagsOf(s).map(t => <Tg key={`${t.ref}|${t.text}`} tag={t} />)}</span> : null}
    {miles.length ? <ul>{miles.map((/** @type {any} */ x) => <li key={x.ref}><Ref id={x.ref} /> {x.m ? x.m.title || "" : ""}{x.m && x.m.due_date ? ` · ${x.m.due_date}` : ""}</li>)}</ul> : null}</div>;
}

/** A text section (#218): its words in the one editor with the Notes bar and `/` menu (SheetEditor's `text`), whole in Show as exported (the
    same editor, read only). Its heading is the section's own, named by Alan. @param {{ctx: SectionCtx}} props */
export function FreeText({ ctx }) {
  const h = /** @type {Here} */ (useContext(SHEET_HERE)), s = /** @type {any} */ (ctx.section);
  return <SheetEditor value={s.text || ""} rich text={{ code: String(ctx.doc.project || "") }} label={s.heading || "Text section"}
    onText={t => h.update({ text: t }, "Text edited")} ai={h.ai} editable={h.editing}
    placeholder="Write here. Anything you add is part of the report and its exports." />;
}

/** A table section: its shown rows, an eye on each while editing, "Showing 5 of 8". @param {{ctx: SectionCtx, rowFn?: (c: RowCtx) => any}} props */
function TableBody({ ctx, rowFn }) {
  const s = /** @type {any} */ (ctx.section), { Text: T, ItemRef: Ref, Tag: Tg } = ctx, rows = s.rows || [], cols = s.columns || [];
  const live = ctx.editing, [shown, total] = rowCounts(s);
  return <div>
    {s.text ? <T rich /> : null}
    <table><thead><tr>{live ? <th class="eyec"><span class="sheet-sr">Show</span></th> : null}{cols.map((/** @type {any} */ c) => <th key={c.key}>{c.label}</th>)}</tr></thead><tbody>
      {rows.map((/** @type {any} */ row, /** @type {number} */ index) => {
        const off = row.shown === false;
        if (off && !live) return null;
        const setRow = (/** @type {any} */ p, /** @type {string} */ why) => { const r = rows.slice(); r[index] = { ...row, ...p }; ctx.update({ rows: r }, why); };
        const removeRow = (/** @type {string} */ why) => ctx.update({ rows: rows.filter((/** @type {any} */ _, /** @type {number} */ j) => j !== index) }, why);
        /** @type {RowCtx} */
        const rc = { row, index, section: s, item: (ctx.doc.items || {})[row.ref || ""] || null, editing: live, exported: ctx.exported,
          readOnly: ctx.readOnly, setRow, removeRow, Text: T, ItemRef: Ref, Tag: Tg };
        if (rowFn) return rowFn(rc);
        return <tr key={row.ref || index} class={off ? "sheet-rowoff" : ""} data-ref={row.ref || undefined}>
          {live ? <td class="eyec"><EyeButton on={!off} subject={row.ref || "this row"} cls="eye" onClick={() => setRow({ shown: off }, off ? "Row shown" : "Row hidden")} /></td> : null}
          {cols.map((/** @type {any} */ c) => <td key={c.key} data-col={c.key}>{off ? <span>{(row.cells || {})[c.key] || (c.key === "id" ? row.ref : "")}</span> : <T row={index} col={c.key} label={c.label} />}</td>)}
        </tr>;
      })}
    </tbody></table>
    {live && shown < total ? <div class="sheet-count">Showing {shown} of {total}</div> : null}
  </div>;
}

let FIGDRAG = /** @type {string|null} */ (null);
/** At a glance: the shown figures; dragged to reorder, an eye to hide. @param {{ctx: SectionCtx}} props */
function Figures({ ctx }) {
  const h = /** @type {Here} */ (useContext(SHEET_HERE)), s = /** @type {any} */ (ctx.section), figs = s.figures || [];
  const [drag, setDragState] = useState(/** @type {string|null} */ (null));
  const setDrag = (/** @type {string|null} */ k) => { FIGDRAG = k; setDragState(k); };
  const live = ctx.editing;
  const put = (/** @type {any} */ nd, /** @type {string} */ why) => h.update({ figures: nd.sections.find((/** @type {any} */ x) => x.id === s.id).figures }, why);
  const act = (/** @type {SheetDoc} */ nd, /** @type {string} */ why) => put(nd, why);
  return <div class="figures">{figs.map((/** @type {any} */ f) => {
    const off = f.shown === false;
    if (off && !live) return null;
    return <div key={f.key} class={`figure${off ? " sheet-figoff" : ""}${drag === f.key ? " sheet-dragging" : ""}`} data-key={f.key}
      draggable={live} onDragStart={live ? (/** @type {DragEvent} */ e) => { setDrag(f.key); e.dataTransfer?.setData("text/plain", f.key); } : undefined}
      onDragOver={live ? (/** @type {DragEvent} */ e) => { if (FIGDRAG) e.preventDefault(); } : undefined}
      onDrop={live ? (/** @type {DragEvent} */ e) => { e.preventDefault(); const from = FIGDRAG; if (from && from !== f.key) act(moveFigure(ctx.doc, s.id, from, f.key), "Figure moved"); setDrag(null); } : undefined}
      onDragEnd={() => setDrag(null)}>
      {live ? <EyeButton on={!off} subject={f.label} cls="eye sheet-figeye" onClick={() => act(setFigureShown(ctx.doc, s.id, f.key, off), off ? "Figure shown" : "Figure hidden")} /> : null}
      {f.label}<b>{f.value}</b>{f.note}</div>;
  })}</div>;
}

/** Which document is shown (#90): a suggestion is only used on the one it was made from. Two minutes of a project on the same
    day differ by their id, path or title, and the internal and distributed versions by their audience (#90 review K2). @param {any} d */
const docKey = d => JSON.stringify([d.kind, d.project, d.date, d.client || "", d.version || 0, d.id || d.path || d.title || "", d.audience || ""]);

/** The section's own words (its text and panes), as they were when ✦ was pressed: a changed section makes a suggestion stale.
    An edit that puts the words back is not a change. @param {any} s */
const wordsKey = s => JSON.stringify([s.text ?? null, s.panes ?? null, s.type === "health" ? (s.data || {}).flag ?? null : null]);   // #203: a health's flag is part of its words

let DRAGGING = /** @type {string|null} */ (null);

/** One section with its chrome. @param {{s: SheetSection, i: number, p: PageProps, peer: SheetSection|null}} props */
function SectionBlock({ s, i, p, peer }) {
  const { doc, exported, readOnly, onChange, onEvent } = p;
  const editing = !exported && !readOnly;
  const [rd, setRd] = useState(/** @type {any} */ (null));
  const docNow = docKey(doc), wordsNow = wordsKey(s), liveKey = useRef(docNow), liveWords = useRef(wordsNow), used = useRef(false);        // #90: which document a suggestion was made from
  liveKey.current = docNow; liveWords.current = wordsNow;
  const running = useRef(false);                       // #90 review K3: a second ✦ while one is writing is ignored
  /** #90 review K5: a used suggestion that Alan then changes counts once as "edited" (on top of "used"): the words it put in, and
      the words before it, so the render before it lands isn't taken for an edit. Another document drops it uncounted. */
  const afterUse = useRef(/** @type {{doc: string, put: string, before: string}|null} */ (null));
  useEffect(() => {
    const u = afterUse.current;
    if (!u) return;
    if (u.doc !== docNow) { afterUse.current = null; return; }
    if (wordsNow !== u.put && wordsNow !== u.before) { afterUse.current = null; onEvent({ type: "redraft", id: s.id, choice: "edited", ...(s.type === "health" ? { section: "health" } : {}) }); }
  }, [wordsNow, docNow]);
  /** Why a suggestion can't be used: another document, or this section's words changed since ✦. @param {any} r */
  const staleWhy = r => r && r.from && (r.from !== liveKey.current ? "doc" : r.words !== liveWords.current ? "words" : "");
  const [name, setName] = useState(s.heading);
  const [over, setOver] = useState(/** @type {""|"above"|"below"} */ (""));
  const box = useRef(/** @type {HTMLElement|null} */ (null));
  useEffect(() => { setName(s.heading); }, [s.heading]);
  const sec = /** @type {any} */ (s);
  const change = (/** @type {SheetDoc} */ nd, /** @type {string} */ why, /** @type {SheetEvent|null} */ ev) => { onChange(nd, why); if (ev) onEvent(ev); };
  const update = (/** @type {Partial<SheetSection>} */ patch, /** @type {string} */ why) => {
    const sections = doc.sections.slice(); sections[i] = { ...sections[i], ...patch };
    const nd = { ...doc, sections };
    onChange("figures" in patch || "heading" in patch || "hidden" in patch ? syncLayout(nd) : nd, why);       // the layout keeps in step
  };
  const ownRender = (p.renderers.byId || {})[s.id] || (p.renderers.byType || {})[s.type];
  const sparkOn = !!p.onRedraft && !exported && (s.type === "text" || s.type === "panes" || s.type === "health");   // #203: the health row suggests too
  const spark = p.onRedraft && !exported ? async () => {
    if (running.current) return;
    const from = docNow, words = wordsNow;
    used.current = false; running.current = true;
    setRd({ status: "running", from, words });
    try { const a = await p.onRedraft?.(s); const r = { from, words }; setRd(staleWhy(r) ? { status: "stale", ...r, why: staleWhy(r) } : { status: "ready", answer: a, ...r }); } catch (e) { setRd({ status: "failed", message: String((e && /** @type {any} */ (e).message) || "No draft came back") }); }
    finally { running.current = false; }
  } : null;
  const ownSpark = sparkOn && !!ownRender && !!(/** @type {any} */ (ownRender)).ownSpark;   // #203: a renderer with no visible heading (the weekly health row) draws the ✦ itself, with <ctx.Spark />
  const fixed = s.type === "header" && ((p.renderers.byId || {}).header || {}).fixed !== false;
  const grip = (/** @type {KeyboardEvent} */ e) => {
    if (!e.altKey || (e.key !== "ArrowUp" && e.key !== "ArrowDown")) return;
    e.preventDefault();
    const d = e.key === "ArrowUp" ? -1 : 1, to = Math.max(0, Math.min(doc.sections.length - 1, i + d));
    if (to === i) return;
    p.refocus.current = s.id;
    change(moveBy(doc, s.id, d), "Section moved", { type: "section-moved", id: s.id, to });
  };
  /** @type {SectionCtx} */
  const ctx = { section: s, doc, editing, exported, readOnly, update, setDoc: (nd, why) => onChange(nd, why), setMeta: (patch, why) => onChange({ ...doc, meta: { ...(doc.meta || {}), ...patch } }, why),
    Text, ItemRef, Tag, Spark, level: key => ({ "data-level": key }), peer };
  const here = { s, doc, editing, exported, readOnly, ai: p.aiFor(s, readOnly), checks: p.checks, update, onOpenItem: p.onOpenItem, onEvent,
    spark, sparkInHeading: sparkOn && !ownSpark };
  const differs = p.side === "left" && peer ? sectionDiffers(s, peer) : false;
  const tags = tagsOf(s);
  const nowName = (/** @type {string} */ v) => { if (v.trim() && v.trim() !== s.heading) change(renameHeading(doc, s.id, v), "Heading renamed", null); else setName(s.heading); };
  const isText = isTextSection(s);
  const [confirmDel, setConfirmDel] = useState(false);          // #218: deleting a text section that holds words asks first
  const deleteIt = () => { setConfirmDel(false); change(withoutSection(doc, s.id), "Section deleted", { type: "section-deleted", id: s.id }); };
  const headBox = useRef(/** @type {HTMLInputElement|null} */ (null));
  useEffect(() => { if (isText && editing && takeNewText(s.id) && headBox.current) headBox.current.focus(); }, []);     // a text section just added: its heading takes the cursor
  const report = !!p.report;
  const menu = [
    { id: "hide", name: report ? "Leave out of the export" : "Hide this section", icon: "eyeoff" },
    ...(i > 0 ? [{ id: "up", name: "Move up", icon: "arrowup" }] : []), ...(i < doc.sections.length - 1 ? [{ id: "down", name: "Move down", icon: "arrowdown" }] : []),
    ...(report ? [{ id: "addtext", name: "Add a text section below", icon: "type" }] : []),   // ReportSheet's addText(sectionId) is stores/textSection.js addTextSection
    ...(s.heading !== defaultHeading(s) ? [{ id: "reset", name: "Reset the heading", icon: "undo" }] : []),
    ...(isText ? [{ id: "delete", name: "Delete this section", icon: "trash" }] : [])];
  const onPick = (/** @type {string} */ id) => {
    if (id === "hide") change(hideSection(doc, s.id), "Section hidden", { type: "section-hidden", id: s.id });
    else if (id === "reset") change(resetHeading(doc, s.id), "Heading reset", { type: "heading-reset", id: s.id });
    else if (id === "addtext") p.report?.addText?.(s.id);
    else if (id === "delete") { if (String(sec.text || "").trim()) setConfirmDel(true); else deleteIt(); }
    else { const d = id === "up" ? -1 : 1; p.refocus.current = s.id; change(moveBy(doc, s.id, d), "Section moved", { type: "section-moved", id: s.id, to: i + d }); }
  };
  /** The section menu is a popup drawn at the end of the page (Menu.jsx openMenu), not inside the scaled page: it keeps 13 px at any
      zoom, opens under the chevron and stays clear of the side bar and the window's edges. */
  const openSectionMenu = (/** @type {HTMLElement} */ anchor) => {
    const rail = document.querySelector(".rail"), keep = rail ? rail.getBoundingClientRect().right + 8 : 8;
    openMenu(anchor, { label: `${s.heading}: section options`, items: menu, onPick, cls: "rsmenu", minLeft: keep });
  };
  const drop = (/** @type {DragEvent} */ e) => {
    e.preventDefault(); setOver("");
    const from = DRAGGING; DRAGGING = null;
    if (!from || from === s.id) return;
    const rect = /** @type {HTMLElement} */ (box.current).getBoundingClientRect(), below = e.clientY > rect.top + rect.height / 2;
    const fi = doc.sections.findIndex(x => x.id === from);
    let to = i + (below ? 1 : 0); if (fi < to) to -= 1;
    change(moveSection(doc, from, to), "Section moved", { type: "section-moved", id: from, to });
  };
  if (s.type === "header" && ownRender) return <SHEET_HERE.Provider value={here}><section data-id={s.id} ref={box}>{ownRender(ctx)}</section></SHEET_HERE.Provider>;
  return <SHEET_HERE.Provider value={here}>
    <section ref={box} data-id={s.id} class={`${over ? "sheet-over-" + over : ""}${fixed ? " sheet-fixed" : ""}`}
      onDragOver={editing && !fixed ? (/** @type {DragEvent} */ e) => { if (DRAGGING) { e.preventDefault(); const r = /** @type {HTMLElement} */ (box.current).getBoundingClientRect(); setOver(e.clientY > r.top + r.height / 2 ? "below" : "above"); } } : undefined}
      onDragLeave={() => setOver("")} onDrop={editing && !fixed ? drop : undefined}>
      {editing && !fixed ? <div class="sheet-handle">
        <button type="button" class="sheet-grip" draggable aria-label={`Move ${s.heading}. Alt and the arrow keys move it.`} data-tip="Drag to move" data-grip={s.id}
          onKeyDown={grip} onDragStart={(/** @type {DragEvent} */ e) => { DRAGGING = s.id; e.dataTransfer?.setData("text/plain", s.id); }} onDragEnd={() => { DRAGGING = null; setOver(""); }}>⋮⋮</button>
        <button type="button" class="sheet-hbtn" aria-haspopup="menu" aria-expanded="false" aria-label={`${s.heading}: section options`}
          onClick={e => openSectionMenu(/** @type {HTMLElement} */ (e.currentTarget))}><Icon name="chevdown" /></button>
      </div> : null}
      {s.type === "header" || (isText && !editing && !String(s.heading || "").trim()) ? null : <h2>
        {editing ? <input ref={headBox} class="sheet-h" aria-label="Section heading" placeholder={isText ? "Section heading" : undefined} value={name}
          style={{ width: `${Math.max(isText ? 18 : 8, name.length + 1)}ch` }} onInput={e => setName(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
          onBlur={e => nowName(/** @type {HTMLInputElement} */ (e.currentTarget).value)}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); /** @type {HTMLInputElement} */ (e.currentTarget).blur(); } if (e.key === "Escape") setName(s.heading); }} /> : s.heading}
        {editing && s.heading !== defaultHeading(s) ? <button type="button" class="sheet-reset" onClick={() => change(resetHeading(doc, s.id), "Heading reset", { type: "heading-reset", id: s.id })}>Reset</button> : null}
        {sparkOn && !ownSpark && spark ? <SparkButton on={spark} heading={s.heading} health={s.type === "health"} /> : null}
        {editing && tags.length ? <button type="button" class="sheet-untag" onClick={() => { update({ tags: [] }, "Tags removed"); onEvent({ type: "tag", removed: true, all: true, id: s.id }); }}>Remove all tags</button> : null}
        {differs && peer ? <span class="sheet-diff" tabIndex={0} title={`${p.peerLabel} reads differently here`}>≠ {p.peerLabel}</span> : null}
        {isText && !peer && !exported && p.side === "left" && p.addTo ? <span class="sheet-match" data-textonly>Internal only
          {!p.addTo.readOnly ? <> · <button type="button" class="linkbtn" data-addto onClick={() => p.addTo?.one(s.id)}>Add to the {p.peerLabel.toLowerCase()} report</button></> : null}</span> : null}
        {isText && !peer && !exported && p.side === "right" ? <span class="sheet-match" data-textonly>Written for the {p.peerLabel.toLowerCase()}</span> : null}
        {(!isText || peer) && p.side === "right" && !readOnly && !exported && p.match && !p.match.readOnly ? <span class="sheet-match">{p.match.label(s.id)}
          {p.match.differs(s.id) ? <button type="button" class="linkbtn" onClick={() => p.match?.one(s.id)}>Match internal</button> : null}</span> : null}
      </h2>}
      {confirmDel ? <div class="sheet-delask" role="alertdialog" aria-label="Delete this section?">Delete “{s.heading || "this text section"}” and what is written in it?
        <button type="button" class="btn sm" data-delyes onClick={deleteIt}>Delete</button>
        <button type="button" class="btn sm" onClick={() => setConfirmDel(false)}>Keep</button></div> : null}
      {rd ? <Redraft rd={staleWhy(rd) ? { status: "stale", why: staleWhy(rd) } : rd} s={s} readOnly={!editing} close={() => setRd(null)} onUse={(choice, a) => {
        if (staleWhy(rd)) { setRd({ ...rd, status: "stale", why: staleWhy(rd) }); return; }       // never applied from an earlier version
        if (used.current) return;                                                                          // a double click counts and applies once
        used.current = true;
        if (choice === "use") {
          const patch = { ...(a.text != null ? { text: a.text } : {}), ...(a.panes ? { panes: a.panes } : {}),
            ...(a.health ? { data: { ...(sec.data || {}), flag: a.health } } : {}) };
          afterUse.current = { doc: docNow, put: wordsKey({ ...s, ...patch }), before: wordsNow };
          if (a.apply) change(a.apply(doc, s), "Redraft used", null); else update(patch, "Redraft used");   // #203: the client sheet also records why its flag differs
        }
        else if (choice === "add") update({ text: `${sec.text || ""}${sec.text ? "\n" : ""}${(a.lines || []).map((/** @type {string} */ l) => `- ${l}`).join("\n")}` }, "New lines added");
        onEvent({ type: "redraft", id: s.id, choice, ...(s.type === "health" ? { section: "health" } : {}) }); setRd(null);
        if (a.health && !(choice === "use" && a.apply)) setTimeout(() => /** @type {HTMLElement|null} */ (box.current?.querySelector(".sheet-spark"))?.focus(), 0); }}
        onOpen={ref => { openSheetRef(ref, p.onOpenItem); onEvent({ type: "item", ref }); }} known={ref => known(ref, doc)} /> : null}
      {ownRender ? ownRender(ctx) : <SheetDefault ctx={ctx} rowFn={(p.renderers.row || {})[s.id]} />}
    </section></SHEET_HERE.Provider>;
}

/** What to check in a suggestion (#90 review F5): the plain-code check's notes (a date, number or name it lost or added) and each
    sentence that rests on no fact ("No source"). @param {any} a @returns {string[]} */
const checkNotes = a => [...(a.notes || []).map((/** @type {any} */ n) => String(n.note || "")).filter(Boolean),
  ...(a.sentences || []).filter((/** @type {any} */ x) => x.unsourced && String(x.text || "").trim()).map((/** @type {any} */ x) => `No source: “${String(x.text).trim()}”`)];

/** A fresh draft beside Alan's words: Keep mine, Use this, Add the new lines. Nothing changes before a choice.
    @param {{rd: any, s: SheetSection, readOnly: boolean, close: () => void, onUse: (choice: "keep"|"use"|"add", a: any) => void,
      onOpen: (ref: string) => void, known: (ref: string) => boolean}} props */
function Redraft({ rd, s, readOnly, close, onUse, onOpen, known }) {
  if (rd.status === "running") return <div class="sheet-redraft" role="status">Drafting {s.heading}…</div>;
  if (rd.status === "stale") return <div class="sheet-redraft" role="alert">{rd.why === "words" ? "You've changed this section since; the suggestion was made from the earlier words." : "This suggestion was made from an earlier version."}<button type="button" class="btn sm" onClick={close}>Close</button></div>;
  if (rd.status === "failed") return <div class="sheet-redraft" role="alert">{rd.message}<button type="button" class="btn sm" onClick={close}>Close</button></div>;
  const a = rd.answer || {};
  const hl = !!a.health;                                       // #203: a health suggestion: the flag, a difference, the evidence
  return <div class="sheet-redraft" role="region" aria-label={hl ? "Suggested health and reason" : `A fresh draft of ${s.heading}`} tabIndex={hl ? -1 : undefined}
    onKeyDown={hl ? e => { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); onUse("keep", a); } } : undefined}>
    <div class="sheet-rdh"><Icon name="spark" /> {hl ? <>Suggested: <b class={`sheet-hflag ${a.tone || ""}`} data-hflag>{a.health}</b></> : "A fresh draft"}</div>
    {hl && a.diff ? <div class="sheet-hdiff" role="note">{a.diff}</div> : null}
    {a.text != null ? <div class="sheet-md">{mdNodes(a.text)}</div> : null}
    {(a.panes || []).map((/** @type {any} */ x, /** @type {number} */ k) => <div key={k}><h3>{x.title}</h3><div class="sheet-md">{mdNodes(x.text)}</div></div>)}
    {(a.lines || []).length ? <ul class="sheet-lines">{a.lines.map((/** @type {string} */ l, /** @type {number} */ k) => <li key={k}>{l}</li>)}</ul> : null}
    {checkNotes(a).length ? <ul class="sheet-rdnotes" aria-label="Check it">{checkNotes(a).map((n, k) => <li key={k}>{n}</li>)}</ul> : null}
    {hl && (a.evidence || []).length ? <ul class="sheet-hwhy" aria-label="Evidence">{a.evidence.map((/** @type {any} */ e) => <li key={e.ref}>
      {known(e.ref) ? <button type="button" class="linkbtn sheet-ref" onClick={() => onOpen(e.ref)}>{e.ref}</button> : <b>{e.ref}</b>} {e.text}</li>)}</ul> : null}
    {(a.sources || []).length ? <div class="sheet-srcs">{a.sources.map((/** @type {any} */ x) => <span key={x.ref} class="chip">{x.label || x.ref}</span>)}</div> : null}
    <div class="sheet-rdb"><button type="button" class="btn sm" onClick={() => onUse("keep", a)}>{hl ? "Reject" : "Keep mine"}</button>
      {readOnly ? null : <button type="button" class="btn sm primary" data-hsuse={hl ? "" : undefined} onClick={() => onUse("use", a)}>{hl ? "Use" : "Use this"}</button>}
      {readOnly || !(a.lines || []).length ? null : <button type="button" class="btn sm" onClick={() => onUse("add", a)}>Add the new lines</button>}</div>
  </div>;
}

/** @typedef {{doc: SheetDoc, renderers: import("./Sheet.jsx").SheetRenderers, extras: import("./Sheet.jsx").SheetExtra[], exported: boolean, readOnly: boolean,
    peerDoc: SheetDoc|null, peerLabel: string, side: ""|"left"|"right", onChange: (d: SheetDoc, why: string) => void,
    onOpenItem?: (ref: string) => boolean, onEvent: (e: SheetEvent) => void, onRedraft?: (s: SheetSection) => Promise<any>,
    aiFor: (s: SheetSection, ro: boolean) => any, checks: any[], refocus: {current: string|null},
    match: null | {readOnly: boolean, label: (id: string) => string, differs: (id: string) => boolean, one: (id: string) => void},
    report?: {audience: string, addText?: (sectionId: string) => void},
    addTo?: null | {readOnly: boolean, one: (id: string) => void}}} PageProps */      // #218: the left page's "Add to the client report" for a text section the partner lacks

/** One page: the header, its sections in order, the extras between them. @param {PageProps} p */
export function SheetPage(p) {
  const { doc, exported, readOnly, onChange, onEvent } = p;
  const editing = !exported && !readOnly;
  const page = useRef(/** @type {HTMLDivElement|null} */ (null));
  useLayoutEffect(() => {                                   // a moved section keeps the focus on its handle (on this page: the same section is on both)
    const id = p.refocus.current;
    if (id) { p.refocus.current = null; /** @type {HTMLElement|null} */ (page.current && page.current.querySelector(`[data-grip="${CSS.escape(id)}"]`))?.focus(); }
  });
  const setMeta = (/** @type {Record<string, any>} */ patch, /** @type {string} */ why) => onChange({ ...doc, meta: { ...(doc.meta || {}), ...patch } }, why);
  const out = [];
  const extra = (/** @type {import("./Sheet.jsx").SheetExtra} */ x) => <div key={`x-${x.key}`} class="sheet-extra" data-extra={x.key}>
    {x.render({ doc, editing, readOnly, setMeta, ItemRef: ({ id }) => (known(id, doc) && !exported ? <button type="button" class="linkbtn sheet-ref" onClick={() => { openSheetRef(id, p.onOpenItem); onEvent({ type: "item", ref: id }); }}>{id}</button> : <span>{id}</span>) })}</div>;
  doc.sections.forEach((s, i) => {
    if (s.hidden) {
      if (!exported) out.push(<div key={s.id} class="sheet-hidden" data-hidden={s.id}>Hidden: {s.heading}
        {readOnly ? null : <> · <button type="button" class="linkbtn" onClick={() => { onChange(showSection(doc, s.id), "Section shown"); onEvent({ type: "section-shown", id: s.id }); }}>Show</button></>}</div>);
    } else if (exported && s.type === "text" && !String(s.text || "").trim() && !(s.rows || []).length) {
      /* #226: a text section with nothing in it is not drawn in the exported page (the exports of the weekly report had an empty heading) */
    } else out.push(<SectionBlock key={s.id} s={s} i={i} p={p} peer={p.peerDoc ? p.peerDoc.sections.find(x => x.id === s.id) || null : null} />);
    if (!exported) for (const x of p.extras.filter(e => e.after === s.id)) out.push(extra(x));
  });
  if (!exported) for (const x of p.extras.filter(e => e.after == null)) out.push(extra(x));
  const label = { internal: "Internal", client: "Client", distributed: "Distributed" }[/** @type {"internal"} */ (doc.audience || "internal")] || "";
  const addFoot = () => {
    const last = doc.sections[doc.sections.length - 1], nd = withTextSection(doc, last ? last.id : null), nid = nd.sections[nd.sections.length - 1].id;
    markNewText(nid); onChange(nd, "Text section added"); onEvent({ type: "text-added", id: nid });
  };
  return <div class="page" ref={page} data-audience={doc.audience || "internal"} data-report={p.report ? "sheet" : undefined} data-pane={p.side || undefined}>
    {p.report ? null : <header class="doc"><div><h1>{doc.title}</h1><div class="sub">{(/** @type {any} */ (doc)).project_name || ""}{(/** @type {any} */ (doc)).client ? ` · ${(/** @type {any} */ (doc)).client}` : ""}</div></div><div class="sub">{label}</div></header>}
    {out}
    {editing ? <div class="sheet-addfoot"><button type="button" class="btn sheet-addtext" data-addtext onClick={addFoot}><Icon name="plus" /> Add a text section</button></div> : null}
  </div>;
}

/** The label for the right-hand page's "Matching internal" / "Edited for …". @param {SheetDoc} left @param {SheetDoc} right @param {string} id @param {string} label */
export const labelOf = (left, right, id, label) => matchLabel(left, right, id, label);

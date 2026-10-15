// @ts-check
/* SheetStub (v2.1.0, dev/sprints/v210-contract.md §4.9): a stand-in for components/report/Sheet.jsx (P5) with the same props and
   the same slot calls, so P7's parts (the transcript pane, item rows, the deadline popover, coverage) are built now and moved onto
   the real sheet by changing the import. It draws the data block's sections in order, through the view's renderers when given;
   its Text is a plain <textarea> (no one editor, no AI, no checks, no tags drawn by default), zoom is a fixed width, and Side by
   side is two columns without levelling or ≠ markers. The scroll position is kept on every redraw. Text only through JSX. */
import { createContext } from "preact";
import { useContext, useLayoutEffect, useRef, useState } from "preact/hooks";
import { openMilestone } from "../../milestones.js";
import { openRecord } from "../../panel.js";

/** @typedef {{ref: string, text: string}} SheetTag */
/** @typedef {{ref?: string, cells?: Record<string, string>, shown?: boolean, source?: any}} SheetRow */
/** @typedef {{id: string, type: string, heading: string, default_heading?: string, hidden?: boolean, text?: string,
    columns?: {key: string, label: string}[], rows?: SheetRow[], figures?: any[], panes?: {title: string, text: string}[],
    tags?: SheetTag[], data?: any}} SheetSection */
/** @typedef {{kind: string, audience?: string, project: string, title: string, date: string, version?: number,
    layout?: Record<string, any>, sections: SheetSection[], items?: Record<string, any>, sources?: any[], meta?: Record<string, any>,
    [k: string]: any}} SheetDoc */
/** @typedef {{ok: boolean, version?: number|null, conflict?: boolean, message?: string, removed?: any}} SaveAnswer */
/** @typedef {{type: string, [k: string]: any}} SheetEvent */
/** @typedef {{field?: string, rich?: boolean, row?: number, col?: string, label?: string}} TextProps */
/** @typedef {{section: SheetSection, doc: SheetDoc, editing: boolean, exported: boolean, readOnly: boolean,
    update: (patch: Partial<SheetSection>, why: string) => void, setMeta: (patch: Record<string, any>, why: string) => void,
    Text: (p: TextProps) => any, ItemRef: (p: {id: string}) => any, Tag: (p: {tag: SheetTag}) => any, Spark: () => any,
    level: (key: string) => Record<string, string>, peer: SheetSection|null}} SectionCtx */
/** @typedef {{row: SheetRow, index: number, section: SheetSection, item: any, editing: boolean, exported: boolean, readOnly: boolean,
    setRow: (patch: Partial<SheetRow>, why: string) => void, removeRow: (why: string) => void, Text: (p: TextProps) => any,
    ItemRef: (p: {id: string}) => any, Tag: (p: {tag: SheetTag}) => any}} RowCtx */
/** @typedef {{key: string, after: string|null, render: (c: {doc: SheetDoc, editing: boolean, readOnly: boolean,
    setMeta: (patch: Record<string, any>, why: string) => void, ItemRef: (p: {id: string}) => any}) => any}} SheetExtra */
/** @typedef {{byId?: Record<string, (c: SectionCtx) => any>, byType?: Record<string, (c: SectionCtx) => any>,
    row?: Record<string, (c: RowCtx) => any>}} SheetRenderers */
/** @typedef {{text?: string, panes?: {title: string, text: string}[], sources: {ref: string, label: string}[], lines?: string[]}} Redraft */
/** @typedef {{doc: SheetDoc, label: string, baseVersion?: number, scrollKey?: string, renderers?: SheetRenderers, readOnly?: boolean,
    match?: (id: string|null) => SheetDoc,
    onChange: (doc: SheetDoc, why: string) => void, onSave?: (r: {doc: SheetDoc, base_version: number|undefined}) => Promise<SaveAnswer>}} SheetPartner */
/** @typedef {{doc: SheetDoc, baseVersion?: number, scrollKey?: string, zoom?: number, onZoom?: (z: number) => void,
    exported?: boolean, onExported?: (on: boolean) => void, readOnly?: boolean, renderers?: SheetRenderers, extras?: SheetExtra[],
    checks?: any[], ai?: any, onRedraft?: (s: SheetSection) => Promise<Redraft>, onSelectAction?: (id: string, sel: any) => Promise<any>,
    onOpenItem?: (ref: string) => boolean, partner?: SheetPartner|null, onChange: (doc: SheetDoc, why: string) => void,
    onSave?: (r: {doc: SheetDoc, base_version: number|undefined}) => Promise<SaveAnswer>, onEvent?: (e: SheetEvent) => void,
    toolbar?: any}} SheetProps */

const ZOOM_MIN = 0.4, ZOOM_MAX = 0.8;
/** Scroll positions by scrollKey, kept for the page's life. @type {Map<string, number>} */
const SCROLL = new Map();

/** Open the standard peek for a ref (the view's own first). @param {string} ref @param {((r: string) => boolean)|undefined} own */
export function openRef(ref, own) {
  if (own && own(ref)) return;
  if (/-M-\d+$/.test(ref)) openMilestone(ref); else openRecord("all", ref);
}

/** What the stable Text, ItemRef and Tag read: the section being drawn (a component made inside a render would remount, and a
    textarea would lose focus, on every keystroke). @typedef {{s: SheetSection, editing: boolean, exported: boolean, readOnly: boolean,
    update: (p: Partial<SheetSection>, why: string) => void, onOpenItem?: (ref: string) => boolean, onEvent: (e: SheetEvent) => void}} Here */
const HERE = createContext(/** @type {Here|null} */ (null));

/** A field of the section (or a row's cell) as a plain textarea. @param {TextProps} props */
function StubText({ field = "text", row, col, label }) {
  const h = /** @type {Here} */ (useContext(HERE)), s = h.s;
  const v = row != null && col ? ((s.rows || [])[row]?.cells || {})[col] || "" : /** @type {any} */ (s)[field] || "";
  if (!h.editing) return <span class="sheet-text">{v}</span>;
  return <textarea class="sheet-text" aria-label={label || s.heading} value={v} onInput={e => {
    const t = /** @type {HTMLTextAreaElement} */ (e.currentTarget).value;
    if (row != null && col) { const rows = (s.rows || []).slice(); rows[row] = { ...rows[row], cells: { ...(rows[row].cells || {}), [col]: t } }; h.update({ rows }, "Row edited"); }
    else h.update({ [field]: t }, "Text edited");
  }} />;
}

/** An item ID that opens the standard peek. @param {{id: string}} props */
function StubItemRef({ id }) {
  const h = /** @type {Here} */ (useContext(HERE));
  if (h.exported) return <span>{id}</span>;
  return <button type="button" class="linkbtn" onClick={() => { openRef(id, h.onOpenItem); h.onEvent({ type: "item", ref: id }); }}>{id}</button>;
}

/** A source tag: creaite only, never in Show as exported. @param {{tag: SheetTag}} props */
function StubTag({ tag }) {
  const h = /** @type {Here} */ (useContext(HERE));
  if (h.exported) return null;
  return <button type="button" class="chip" onClick={() => { if (tag.ref.startsWith("t:")) h.onEvent({ type: "tag", tag }); else openRef(tag.ref, h.onOpenItem); }}>{tag.text || tag.ref}</button>;
}
const NoSpark = () => null;

/** One page: its sections in order, through the renderers. @param {{doc: SheetDoc, renderers?: SheetRenderers, extras?: SheetExtra[],
    exported: boolean, readOnly: boolean, peerDoc: SheetDoc|null, match?: (id: string|null) => SheetDoc, onChange: (d: SheetDoc, why: string) => void,
    onOpenItem?: (ref: string) => boolean, onEvent: (e: SheetEvent) => void}} props */
function Page({ doc, renderers = {}, extras = [], exported, readOnly, peerDoc, match, onChange, onOpenItem, onEvent }) {
  const editing = !exported && !readOnly;
  const setSection = (/** @type {number} */ i, /** @type {Partial<SheetSection>} */ patch, /** @type {string} */ why) => {
    const sections = doc.sections.slice(); sections[i] = { ...sections[i], ...patch }; onChange({ ...doc, sections }, why);
  };
  const setMeta = (/** @type {Record<string, any>} */ patch, /** @type {string} */ why) => onChange({ ...doc, meta: { ...(doc.meta || {}), ...patch } }, why);
  const here0 = { editing, exported, readOnly, onOpenItem, onEvent };
  const extra = (/** @type {SheetExtra} */ x) => <HERE.Provider key={`x-${x.key}`} value={{ ...here0, s: /** @type {SheetSection} */ ({ id: "", type: "", heading: "" }), update: () => {} }}>
    <div class="sheet-extra">{x.render({ doc, editing, readOnly, setMeta, ItemRef: StubItemRef })}</div></HERE.Provider>;
  const out = [];
  doc.sections.forEach((s, i) => {
    if (s.hidden) {
      if (editing) out.push(<div key={s.id} class="sheet-hidden">Hidden: {s.heading} <button type="button" class="linkbtn"
        onClick={() => { setSection(i, { hidden: false }, "Section shown"); onEvent({ type: "section-shown", id: s.id }); }}>Show</button></div>);
    } else {
      const update = (/** @type {Partial<SheetSection>} */ p, /** @type {string} */ why) => setSection(i, p, why);
      /** @type {SectionCtx} */
      const ctx = { section: s, doc, editing, exported, readOnly, update, setMeta, Text: StubText, ItemRef: StubItemRef, Tag: StubTag, Spark: NoSpark,
        level: key => ({ "data-level": key }), peer: peerDoc ? peerDoc.sections.find(x => x.id === s.id) || null : null };
      const own = (renderers.byId || {})[s.id] || (renderers.byType || {})[s.type];
      out.push(<HERE.Provider key={s.id} value={{ ...here0, s, update }}><section data-id={s.id}>
        <h2>{s.heading}</h2>
        {match && editing ? <div class="sheet-match"><button type="button" class="btn sm" data-sheetmatch={s.id} onClick={() => onChange(match(s.id), "Matched internal")}>Match internal</button></div> : null}
        {own ? own(ctx) : <Default ctx={ctx} rowFn={(renderers.row || {})[s.id]} />}
      </section></HERE.Provider>);
    }
    if (!exported) for (const x of extras.filter(e => e.after === s.id)) out.push(extra(x));
  });
  if (!exported) for (const x of extras.filter(e => e.after == null)) out.push(extra(x));
  return <div class="page">{out}</div>;
}

/** The stand-in for every §1 type: text, a table's shown rows (through the row renderer), figures, panes.
    @param {{ctx: SectionCtx, rowFn?: (c: RowCtx) => any}} props */
function Default({ ctx, rowFn }) {
  const s = ctx.section, { Text, ItemRef, Tag } = ctx;
  if (s.type === "table") {
    const rows = s.rows || [];
    return <table><thead><tr>{(s.columns || []).map(c => <th key={c.key}>{c.label}</th>)}</tr></thead><tbody>
      {rows.map((row, index) => {
        if (row.shown === false && !ctx.editing) return null;
        const setRow = (/** @type {Partial<SheetRow>} */ p, /** @type {string} */ why) => { const r = rows.slice(); r[index] = { ...row, ...p }; ctx.update({ rows: r }, why); };
        const removeRow = (/** @type {string} */ why) => ctx.update({ rows: rows.filter((_, j) => j !== index) }, why);
        /** @type {RowCtx} */
        const rc = { row, index, section: s, item: (ctx.doc.items || {})[row.ref || ""] || null, editing: ctx.editing, exported: ctx.exported,
          readOnly: ctx.readOnly, setRow, removeRow, Text, ItemRef, Tag };
        return rowFn ? rowFn(rc) : <tr key={row.ref || index}>{(s.columns || []).map(c => <td key={c.key}><Text row={index} col={c.key} label={c.label} /></td>)}</tr>;
      })}
    </tbody></table>;
  }
  if (s.type === "figures") return <div class="figures">{(s.figures || []).filter(f => f.shown !== false).map(f => <div key={f.key} class="figure"><b>{f.value}</b>{f.label}</div>)}</div>;
  if (s.type === "panes") return <div class="panes">{(s.panes || []).map((p, i) => <div key={i}><h3>{p.title}</h3><p>{p.text}</p></div>)}</div>;
  return <div><Text rich />{(s.tags || []).map(t => <Tag key={t.ref} tag={t} />)}</div>;
}

/** The stub sheet: the same props as Sheet.jsx (contract §4.1); see the file's description for what it leaves out.
    @param {SheetProps} props */
export function SheetStub(props) {
  const { doc, baseVersion, scrollKey = "", zoom = ZOOM_MAX, exported = false, readOnly = false, partner = null, onSave, onEvent = () => {} } = props;
  const box = useRef(/** @type {HTMLDivElement|null} */ (null));
  const [base, setBase] = useState(baseVersion);
  const [line, setLine] = useState("");
  useLayoutEffect(() => {                                  // the scroll position is restored after every redraw, never reset
    const el = box.current; if (el && SCROLL.has(scrollKey)) el.scrollTop = SCROLL.get(scrollKey) || 0;
  });
  const save = async () => {
    if (!onSave || readOnly) return;
    const answer = await onSave({ doc, base_version: base });
    if (answer.ok) { setBase(answer.version ?? undefined); setLine(`Saved · version ${answer.version}`); onEvent({ type: "saved", version: answer.version, answer }); }
    else { setLine(answer.message || "Not saved."); onEvent({ type: "save-failed", answer }); }
  };
  const width = `${Math.round(Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, zoom)) * 100)}%`;
  const page = (/** @type {SheetDoc} */ d, /** @type {SheetPartner|null} */ p) => <Page doc={d} renderers={p ? p.renderers || props.renderers : props.renderers}
    extras={p ? [] : props.extras} exported={exported} readOnly={readOnly || !!(p && p.readOnly)} peerDoc={p ? doc : partner ? partner.doc : null} match={p ? p.match : undefined}
    onChange={p ? p.onChange : props.onChange} onOpenItem={props.onOpenItem} onEvent={onEvent} />;
  return (
    <div class="sheet-stub" onKeyDown={e => { if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); save(); } }}>
      <div class="sheet-bar" role="toolbar" aria-label="Report">
        <button type="button" class="btn" aria-pressed={exported ? "true" : "false"} onClick={() => { props.onExported?.(!exported); onEvent({ type: "exported", on: !exported }); }}>Show as exported</button>
        {partner && partner.match && !readOnly && !partner.readOnly ? <button type="button" class="btn" data-sheetmatchall onClick={() => partner.onChange(/** @type {(id: string|null) => SheetDoc} */ (partner.match)(null), "Matched internal")}>Match internal for every section</button> : null}
        {onSave && !readOnly ? <button type="button" class="btn" onClick={save}>Save</button> : null}
        <span class="sub" role="status">{line}</span>
        {props.toolbar || null}
      </div>
      <div class="sheet-scroll" ref={box} onScroll={e => SCROLL.set(scrollKey, /** @type {HTMLDivElement} */ (e.currentTarget).scrollTop)}>
        <div class={partner ? "sheet-pair" : "sheet-one"} style={{ width: partner ? "100%" : width, margin: "0 auto", display: partner ? "flex" : "block" }}>
          {page(doc, null)}
          {partner ? page(partner.doc, partner) : null}
        </div>
      </div>
    </div>
  );
}

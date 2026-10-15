// @ts-check
/* Sheet (v2.1.0 P5, dev/sprints/v210-contract.md §4): the A4 page every report and the minutes are edited on. It knows the data
   block (§1) and nothing about weekly, client or minutes: a view mounts it, supplies the renderers for its own sections and rows,
   and does its own server calls. It is a drop-in for SheetStub.jsx's props (the stub's types are exported from here now).

   - True A4 (210 × 297 mm, 16 mm padded, so 265 mm of content a page), drawn at 40% to 80% of the sheet area's width: − and + in
     the bar, a trackpad pinch (a ctrl wheel), ⌘+ ⌘− ⌘0. The point under the pointer (or the top of the view) stays put.
   - THE SCROLL POSITION IS NEVER RESET BY A REDRAW (P5's first rule): per scrollKey it remembers the top-most visible section and the
     offset into it, and puts that back after a zoom, a move, Show as exported, a doc replaced by a save or reload, and on switching
     views. Nothing else sets scrollTop.
   - Sections move (drag, Alt+↑ ↓) and hide; headings are renamed in place with Reset; the layout keeps in step (sheetLib.syncLayout).
   - ✦ per section (`onRedraft`), the one editor's AI bar (`ai`, places "report", "minutes" and "client"), inline checks, source tags, Find the
     source (`onSelectAction`), the standard peek with Sneak peek on every item ID, Side by side (levelled, ≠ markers, Match internal).
   - Saves 1.5 s after the last change, on ⌘S and on unmount, one at a time; a conflict stops saving and offers Reload.
   Text only through JSX. */
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { snack } from "../../core/server.js";
import { aiAction } from "../../stores/aiEdit.js";
import { SheetPage, openSheetRef, labelOf } from "./SheetPage.jsx";
import { A4_W, CONTENT_MM, MM, PAD_MM, SHEET_ZOOM_DEFAULT, clampZoom, matchAll, matchSection, pageBreaks, pinchZoom, sectionDiffers, stepZoom } from "./sheetLib.js";

export { openSheetRef as openRef };

/** @typedef {{ref: string, text: string, turn?: number, time?: string}} SheetTag */
/** @typedef {{ref?: string, cells?: Record<string, string>, shown?: boolean, source?: any}} SheetRow */
/** @typedef {{id: string, type: string, heading: string, default_heading?: string, hidden?: boolean, text?: string,
    columns?: {key: string, label: string}[], rows?: SheetRow[], figures?: any[], panes?: {title: string, text: string}[],
    tags?: SheetTag[], data?: any}} SheetSection */
/** @typedef {{kind: string, audience?: string, project: string, title: string, date: string, version?: number,
    layout?: Record<string, any>, sections: SheetSection[], items?: Record<string, any>, sources?: any[], meta?: Record<string, any>,
    [k: string]: any}} SheetDoc */
/** @typedef {{ok: boolean, version?: number|null, conflict?: boolean, message?: string, removed?: any}} SaveAnswer */
/** @typedef {{type: string, [k: string]: any}} SheetEvent */
/** @typedef {{field?: string, rich?: boolean, row?: number, col?: string, pane?: number, label?: string}} TextProps */
/** @typedef {{section: SheetSection, doc: SheetDoc, editing: boolean, exported: boolean, readOnly: boolean,
    update: (patch: Partial<SheetSection>, why: string) => void, setMeta: (patch: Record<string, any>, why: string) => void,
    Text: (p: TextProps) => any, ItemRef: (p: {id: string}) => any, Tag: (p: {tag: SheetTag}) => any, Spark: () => any,
    level: (key: string) => Record<string, string>, peer: SheetSection|null}} SectionCtx */
/** @typedef {{row: SheetRow, index: number, section: SheetSection, item: any, editing: boolean, exported: boolean, readOnly: boolean,
    setRow: (patch: Partial<SheetRow>, why: string) => void, removeRow: (why: string) => void, Text: (p: TextProps) => any,
    ItemRef: (p: {id: string}) => any, Tag: (p: {tag: SheetTag}) => any}} RowCtx */
/** @typedef {{key: string, after: string|null, render: (c: {doc: SheetDoc, editing: boolean, readOnly: boolean,
    setMeta: (patch: Record<string, any>, why: string) => void, ItemRef: (p: {id: string}) => any}) => any}} SheetExtra */
/** @typedef {{byId?: Record<string, any>, byType?: Record<string, (c: SectionCtx) => any>,
    row?: Record<string, (c: RowCtx) => any>}} SheetRenderers */
/** @typedef {{text?: string, panes?: {title: string, text: string}[], sources: {ref: string, label: string}[], lines?: string[],
    notes?: {id: string, note: string}[], sentences?: {text: string, refs: string[], unsourced: boolean}[]}} Redraft */
/** @typedef {{id: string, section: string, field?: string, row?: number, pane?: number, quote: string, note?: string, last?: string,
    actions?: {id: string, label: string}[]}} SheetCheck */
/** @typedef {{doc: SheetDoc, label: string, baseVersion?: number, scrollKey?: string, renderers?: SheetRenderers, readOnly?: boolean,
    match?: (id: string) => void,
    onChange: (doc: SheetDoc, why: string) => void, onSave?: (r: {doc: SheetDoc, base_version: number|undefined}) => Promise<SaveAnswer>}} SheetPartner */
/** @typedef {{doc: SheetDoc, baseVersion?: number, scrollKey?: string, zoom?: number, onZoom?: (z: number) => void,
    exported?: boolean, onExported?: (on: boolean) => void, readOnly?: boolean, leftReadOnly?: boolean, renderers?: SheetRenderers, extras?: SheetExtra[],
    checks?: SheetCheck[], ai?: {place: string, project?: () => string, confidential?: () => boolean, key?: () => string,
      document?: () => ({kind: string, code: string, week_ending: string, client: string}|null)},
    onRedraft?: (s: SheetSection) => Promise<Redraft>, onSelectAction?: (id: string, sel: any) => Promise<any>,
    onOpenItem?: (ref: string) => boolean, partner?: SheetPartner|null, onChange: (doc: SheetDoc, why: string) => void,
    onSave?: (r: {doc: SheetDoc, base_version: number|undefined}) => Promise<SaveAnswer>, onEvent?: (e: SheetEvent) => void,
    toolbar?: any}} SheetProps */

/** Where each page was left, by scrollKey (in memory, for the page's life): the zoom, and per pane the section at the top and the
    offset into it in unscaled pixels. @type {Map<string, {id: string, off: number, vy: number}>} */
const ANCHORS = new Map();
/** @type {Map<string, number>} */
const ZOOMS = new Map();
/** Find the source, by sheet: set while a Sheet is mounted. @type {Map<number, (range: any, h: any) => void>} */
const SHEET_SOURCES = new Map();
let SHEET_SEQ = 0;

/* The "Find the source" item of the AI bar in the report and minutes places (and in the read-only one, where it is the only item). */
aiAction({ id: "source", name: "Find the source", line: "Where this comes from", places: ["report", "minutes", "client", "readonly"],
  run: (range, h, ai) => { const run = SHEET_SOURCES.get(/** @type {any} */ (ai).sheetId); if (run) run(range, h); else snack("Finding the source isn't available here"); } });

const SAVE_WAIT = 1500;

/** The saving of one page: 1.5 s after the last change, on demand, on unmount; one at a time, a change during a save is saved after
    it; a conflict stops it. @param {{baseVersion?: number, onSave?: SheetProps["onSave"], readOnly: boolean, onEvent: (e: SheetEvent) => void}} a */
function useSaver(a) {
  const st = useRef({ base: a.baseVersion, latest: /** @type {SheetDoc|null} */ (null), dirty: false, busy: false, again: false, stopped: false,
    timer: /** @type {any} */ (0), a });
  st.current.a = a;
  const [line, setLine] = useState("");
  const [conflict, setConflict] = useState(/** @type {string|null} */ (null));
  const [removed, setRemoved] = useState(/** @type {string} */ (""));
  useEffect(() => {                                           // a newer version from outside (Reload, a refetch) is the new base
    const s = st.current;
    if (a.baseVersion !== s.base && a.baseVersion != null) { s.base = a.baseVersion; if (s.stopped) { s.stopped = false; s.dirty = false; setConflict(null); } }
  }, [a.baseVersion]);
  /** @type {() => Promise<void>} */
  const flush = async () => {
    const s = st.current;
    clearTimeout(s.timer);
    if (!s.a.onSave || s.a.readOnly || s.stopped || !s.dirty || !s.latest) return;
    if (s.busy) { s.again = true; return; }
    s.busy = true; s.dirty = false;
    let r;
    try { r = await s.a.onSave({ doc: s.latest, base_version: s.base }); } catch (e) { r = { ok: false, message: "Not saved." }; }
    s.busy = false;
    if (r.ok) {
      s.base = r.version == null ? s.base : r.version;
      setLine(`Saved · version ${r.version}`); setConflict(null);
      setRemoved(removedLine(r.removed));
      s.a.onEvent({ type: "saved", version: r.version, answer: r });
    } else {
      if (r.conflict) { s.stopped = true; setConflict(r.message || "This changed somewhere else."); } else s.dirty = true;
      setLine(r.message || "Not saved.");
      s.a.onEvent({ type: "save-failed", answer: r });
    }
    if (s.again) { s.again = false; if (s.dirty) flush(); }
  };
  const change = (/** @type {SheetDoc} */ doc) => {
    const s = st.current;
    if (s.a.readOnly || !s.a.onSave) return;
    s.latest = doc; s.dirty = true; clearTimeout(s.timer);
    if (!s.stopped) { setLine("Unsaved changes"); s.timer = setTimeout(flush, SAVE_WAIT); }
  };
  const reload = () => { const s = st.current; s.stopped = false; s.dirty = false; clearTimeout(s.timer); setConflict(null); setLine(""); };
  useEffect(() => () => { const s = st.current; if (s.dirty) flush(); }, []);   // unmounting with unsaved changes saves them
  return { line, conflict, removed, change, flush, reload };
}
/** What a save left out of a client document, as a line. @param {any} r */
function removedLine(r) {
  if (!r || (Array.isArray(r) && !r.length)) return "";
  const list = Array.isArray(r) ? r : [r];
  return `Left out of this version: ${list.map(x => (typeof x === "string" ? x : x && (x.label || x.ref || x.id || x.heading)) || "an item").join(", ")}`;
}

/** The scroller of one page (or of both, scrolling together): it measures its width, draws what it is given at the scale that width
    and the zoom make, and remembers and restores the section at the top of the view. Nothing else sets scrollTop.
    @param {{pk: string, zoom: number, pages: number, regRestore: (fn: () => void) => () => void, onPinch: (dy: number, y: number, pk: string) => void,
    children: (scale: number) => any}} props */
function Pane({ pk, zoom, pages, regRestore, onPinch, children }) {
  const sc = useRef(/** @type {HTMLDivElement|null} */ (null));
  const [w, setW] = useState(0);
  const avail = Math.max(0, w - 32 - (pages > 1 ? 16 * (pages - 1) : 0)) / pages;
  const scale = avail > 0 ? (zoom * avail) / (A4_W * MM) : 0;
  const sref = useRef(scale); sref.current = scale;
  const pinch = useRef(onPinch); pinch.current = onPinch;
  const capture = () => {
    const el = sc.current, page = el && el.querySelector(".page");
    if (!el || !page || !sref.current) return;
    const top = el.getBoundingClientRect().top;
    for (const s of /** @type {NodeListOf<HTMLElement>} */ (page.querySelectorAll(":scope > section[data-id]"))) {
      const r = s.getBoundingClientRect();
      if (r.bottom - top > 1) { ANCHORS.set(pk, { id: /** @type {string} */ (s.dataset.id), off: (top - r.top) / sref.current, vy: 0 }); return; }
    }
  };
  const restore = () => {
    const el = sc.current, a = ANCHORS.get(pk);
    if (!el || !a || !sref.current) return;
    const s = /** @type {HTMLElement|null} */ (el.querySelector(`.page > section[data-id="${CSS.escape(a.id)}"]`));
    if (!s) return;
    const top = el.getBoundingClientRect().top, at = s.getBoundingClientRect().top - top + el.scrollTop;
    const want = Math.max(0, at + a.off * sref.current - a.vy);
    if (Math.abs(el.scrollTop - want) > 1) el.scrollTop = want;
  };
  useLayoutEffect(() => { const el = sc.current; if (el) setW(el.clientWidth); }, []);
  useLayoutEffect(() => regRestore(restore), [pk, scale]);
  useLayoutEffect(restore);
  useEffect(() => {
    const el = /** @type {HTMLDivElement} */ (sc.current);
    const ro = new ResizeObserver(() => setW(el.clientWidth));
    ro.observe(el);
    const wheel = (/** @type {WheelEvent} */ e) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      const page = el.querySelector(".page"), top = el.getBoundingClientRect().top;
      if (page) for (const s of /** @type {NodeListOf<HTMLElement>} */ (page.querySelectorAll(":scope > section[data-id]"))) {
        const r = s.getBoundingClientRect();
        if (r.bottom > e.clientY) { ANCHORS.set(pk, { id: /** @type {string} */ (s.dataset.id), off: (e.clientY - r.top) / sref.current, vy: e.clientY - top }); break; }
      }
      pinch.current(e.deltaY, e.clientY, pk);
    };
    el.addEventListener("wheel", wheel, { passive: false });
    return () => { ro.disconnect(); el.removeEventListener("wheel", wheel); };
  }, [pk]);
  return <div class="sheet-scroll" ref={sc} onScroll={capture} data-pk={pk}>
    <div class={pages > 1 ? "sheet-pair" : "sheet-one"} style={{ visibility: scale ? "visible" : "hidden" }}>{children(scale)}</div>
  </div>;
}

/** One page drawn at a scale: the A4 page transformed, in a box of the scaled size. @param {{scale: number, breaks: number[], children: any}} props */
function SheetFrame({ scale, breaks, children }) {
  return <div class="sheet-fit" data-scale={scale} style={{ width: `${A4_W * MM * scale}px` }}>
    <div class="sheet-a4" style={{ transform: `scale(${scale})` }}>
      {children}
      {breaks.map((y, k) => <div key={y} class="sheet-break" aria-hidden="true" style={{ top: `${PAD_MM * MM + y}px` }}><span>Page {k + 2}</span></div>)}
    </div>
  </div>;
}

/** Give matching blocks and sections the same height on both pages (the shorter padded at its foot), set the extra top margin a
    section needs to start on the next page, and size each page's box. @param {HTMLElement} root @returns {number[][]} the break marks per page */
function relayout(root) {
  const pages = /** @type {HTMLElement[]} */ ([...root.querySelectorAll(".sheet-a4 > .page")]);
  for (const pg of pages) for (const el of /** @type {NodeListOf<HTMLElement>} */ (pg.querySelectorAll("section[data-id], [data-level]"))) { el.style.minHeight = ""; el.style.marginTop = ""; }
  if (pages.length === 2) {
    const [a, b] = pages;
    for (const x of /** @type {NodeListOf<HTMLElement>} */ (a.querySelectorAll("section[data-id]"))) {
      const y = /** @type {HTMLElement|null} */ (b.querySelector(`:scope > section[data-id="${CSS.escape(x.dataset.id || "")}"]`));
      if (!y) continue;
      const lv = (/** @type {HTMLElement} */ e) => new Map([...e.querySelectorAll("[data-level]")].map(n => [/** @type {HTMLElement} */ (n).dataset.level, /** @type {HTMLElement} */ (n)]));
      const la = lv(x), lb = lv(y);
      for (const [k, n] of la) { const m = lb.get(k); if (m) { const h = Math.max(n.offsetHeight, m.offsetHeight); n.style.minHeight = m.style.minHeight = `${h}px`; } }
      const h = Math.max(x.offsetHeight, y.offsetHeight);
      x.style.minHeight = y.style.minHeight = `${h}px`;
    }
    /* An extra that only one page has (the minutes' coverage) pushes the sections after it down: whichever page's next section starts
       lower, the other page's section grows by the difference, top to bottom, so the pairs stay level. */
    const next = (/** @type {Element} */ e) => { let n = e.nextElementSibling; while (n && !n.matches("section[data-id]")) n = n.nextElementSibling; return /** @type {HTMLElement|null} */ (n); };
    for (const x of /** @type {NodeListOf<HTMLElement>} */ (a.querySelectorAll(":scope > section[data-id]"))) {
      const y = /** @type {HTMLElement|null} */ (b.querySelector(`:scope > section[data-id="${CSS.escape(x.dataset.id || "")}"]`));
      const xn = y && next(x), yn = y && next(y);
      if (!y || !xn || !yn) continue;
      const d = xn.offsetTop - yn.offsetTop;                  // unscaled: the page is zoomed by a transform
      if (d > 0.5) y.style.minHeight = `${y.offsetHeight + d}px`;
      else if (d < -0.5) x.style.minHeight = `${x.offsetHeight - d}px`;
    }
  }
  const y0 = PAD_MM * MM, per = CONTENT_MM * MM;
  return pages.map(pg => {
    const secs = /** @type {HTMLElement[]} */ ([...pg.querySelectorAll(":scope > section[data-id]")]);
    const kids = /** @type {HTMLElement[]} */ ([...pg.children]);
    const last = kids[kids.length - 1], total = last ? last.offsetTop + last.offsetHeight - y0 : 0;
    const { pushes, marks } = pageBreaks(secs.map(s => [s.offsetTop - y0, s.offsetHeight]), per, total);
    secs.forEach((s, i) => { if (pushes[i]) s.style.marginTop = `${pushes[i] + 16}px`; });   // the 16px above it collapses into the margin
    const fit = /** @type {HTMLElement|null} */ (pg.closest(".sheet-fit")), sc = Number(fit && fit.dataset.scale) || 0;
    if (fit && sc) fit.style.height = `${pg.parentElement ? pg.parentElement.offsetHeight * sc : 0}px`;
    return marks;
  });
}

/** The A4 sheet. @param {SheetProps} props */
export function Sheet(props) {
  const { doc, partner = null, scrollKey = "", checks = [], onEvent = () => {} } = props;
  const P = useRef(props); P.current = props;
  const sid = useRef(++SHEET_SEQ).current;
  const root = useRef(/** @type {HTMLDivElement|null} */ (null));
  const restorers = useRef(/** @type {Set<() => void>} */ (new Set()));
  const refocus = useRef(/** @type {string|null} */ (null));
  const [zl, setZl] = useState(() => clampZoom(props.zoom ?? ZOOMS.get(scrollKey) ?? SHEET_ZOOM_DEFAULT));
  const [xl, setXl] = useState(false);
  const [together, setTogether] = useState(true);
  const [breaks, setBreaks] = useState(/** @type {number[][]} */ ([]));
  const [pop, setPop] = useState(/** @type {null | {check: SheetCheck, x: number, y: number}} */ (null));
  const [found, setFound] = useState(/** @type {null | {items?: any[], message?: string, x: number, y: number}} */ (null));
  const zoom = props.zoom == null ? zl : clampZoom(props.zoom);
  const exported = props.exported == null ? xl : !!props.exported;
  const leftRO = !!props.readOnly || (!!partner && !!props.leftReadOnly);      // Side by side with the left page read only (P8)
  const readOnly = !!props.readOnly || exported;
  const zref = useRef(zoom); zref.current = zoom;
  const eref = useRef(exported); eref.current = exported;

  const main = useSaver({ baseVersion: props.baseVersion, onSave: props.onSave, readOnly: leftRO, onEvent });
  const side = useSaver({ baseVersion: partner ? partner.baseVersion : undefined, onSave: partner ? partner.onSave : undefined,
    readOnly: !partner || !!partner.readOnly, onEvent });

  const setZoom = (/** @type {number} */ z) => {
    const n = clampZoom(z);
    if (n === zref.current) return;
    zref.current = n; ZOOMS.set(scrollKey, n);
    if (props.zoom == null) setZl(n);
    props.onZoom?.(n); onEvent({ type: "zoom", zoom: n });
  };
  const setExported = (/** @type {boolean} */ on) => {
    if (props.exported == null) setXl(on);
    props.onExported?.(on); onEvent({ type: "exported", on });
  };
  useEffect(() => { if (props.zoom == null) setZl(clampZoom(ZOOMS.get(scrollKey) ?? SHEET_ZOOM_DEFAULT)); }, [scrollKey]);

  const changeMain = (/** @type {SheetDoc} */ nd, /** @type {string} */ why) => { if (leftRO) return; props.onChange(nd, why); main.change(nd); };
  const changeSide = (/** @type {SheetDoc} */ nd, /** @type {string} */ why) => { if (!partner || partner.readOnly) return; partner.onChange(nd, why); side.change(nd); };

  const aiFor = (/** @type {SheetSection} */ s, /** @type {boolean} */ ro) => {
    const a = P.current.ai;
    if (!a) return undefined;
    return { place: ro || eref.current ? "readonly" : a.place, sheetId: sid, project: () => (P.current.ai && P.current.ai.project ? P.current.ai.project() : ""),
      confidential: () => !!(P.current.ai && P.current.ai.confidential && P.current.ai.confidential()), key: () => `sheet:${sid}:${s.id}`,
      document: () => (P.current.ai && P.current.ai.document ? P.current.ai.document() : null) };
  };
  useEffect(() => {
    SHEET_SOURCES.set(sid, async (range, h) => {
      const at = h.el.getBoundingClientRect(), sectionId = (h.el.closest("section[data-id]") || {}).dataset?.id;
      const place = { x: Math.max(8, Math.min(at.left, window.innerWidth - 340)), y: Math.min(at.bottom + 6, window.innerHeight - 160) };
      if (!P.current.onSelectAction) { setFound({ ...place, message: "Finding the source isn't available here." }); return; }
      setFound({ ...place, message: "Looking…" });
      try { const a = await P.current.onSelectAction("source", { sectionId, text: range.text }); setFound({ ...place, items: (a && a.found) || [], message: a && a.found && a.found.length ? "" : "No source found." }); }
      catch (e) { setFound({ ...place, message: "Couldn't look for the source." }); }
    });
    return () => { SHEET_SOURCES.delete(sid); };
  }, []);

  const partnerDoc = partner ? partner.doc : null;
  const match = partner && partnerDoc ? { readOnly: !!partner.readOnly, label: (/** @type {string} */ id) => labelOf(doc, partnerDoc, id, partner.label),
    differs: (/** @type {string} */ id) => sectionDiffers(doc.sections.find(s => s.id === id), partnerDoc.sections.find(s => s.id === id)),
    one: (/** @type {string} */ id) => { if (partner.match) partner.match(id); else changeSide(matchSection(doc, partnerDoc, id), "Matched internal"); } } : null;

  useLayoutEffect(() => {                                     // levelled, page-broken and scroll-kept after every redraw
    const el = root.current;
    if (!el) return;
    const marks = relayout(el);
    if (JSON.stringify(marks) !== JSON.stringify(breaks)) setBreaks(marks);
    restorers.current.forEach(fn => fn());
  });
  useEffect(() => {                                           // content that grows or shrinks (typing, fonts) moves the breaks
    const el = /** @type {HTMLElement} */ (root.current);
    let raf = 0;
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const marks = relayout(el);
        setBreaks(prev => (JSON.stringify(prev) === JSON.stringify(marks) ? prev : marks));
        restorers.current.forEach(fn => fn());
      });
    });
    el.querySelectorAll(".sheet-a4 > .page").forEach(p => ro.observe(p));
    return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  }, [!!partner, together, exported, doc.sections.length, partnerDoc ? partnerDoc.sections.length : 0]);

  const onKey = (/** @type {KeyboardEvent} */ e) => {
    const mod = e.metaKey || e.ctrlKey;
    if (!mod) return;
    if (e.key === "s" || e.key === "S") { e.preventDefault(); main.flush(); side.flush(); return; }
    if (e.key === "+" || e.key === "=") { e.preventDefault(); setZoom(stepZoom(zref.current, 1)); }
    else if (e.key === "-" || e.key === "_") { e.preventDefault(); setZoom(stepZoom(zref.current, -1)); }
    else if (e.key === "0") { e.preventDefault(); setZoom(SHEET_ZOOM_DEFAULT); }
  };
  const onClick = (/** @type {MouseEvent} */ e) => {
    const t = /** @type {HTMLElement} */ (e.target), c = t.closest && t.closest(".claim[data-c]");
    if (c && !exported) {
      const k = checks[Number(/** @type {HTMLElement} */ (c).dataset.c)];
      if (k) { const r = c.getBoundingClientRect(); setPop({ check: k, x: Math.max(8, Math.min(r.left, window.innerWidth - 340)), y: Math.min(r.bottom + 6, window.innerHeight - 180) }); return; }
    }
    if (!t.closest || (!t.closest(".sheet-pop") && pop)) setPop(null);
    if (!t.closest || (!t.closest(".sheet-found") && found)) setFound(null);
  };
  const pinch = (/** @type {number} */ dy) => setZoom(pinchZoom(zref.current, dy));

  const pageProps = (/** @type {SheetDoc} */ d, /** @type {SheetPartner|null} */ p, /** @type {""|"left"|"right"} */ sd) => ({
    doc: d, renderers: (p ? p.renderers || props.renderers : props.renderers) || {}, extras: p ? [] : props.extras || [], exported,
    readOnly: p ? !!p.readOnly || !!props.readOnly : leftRO, peerDoc: p ? doc : partnerDoc, peerLabel: partner ? partner.label : "",
    side: sd, onChange: p ? changeSide : changeMain, onOpenItem: props.onOpenItem, onEvent, onRedraft: p ? undefined : props.onRedraft,
    aiFor, checks: p ? [] : checks, refocus, match: p ? match : null });
  const frame = (/** @type {SheetDoc} */ d, /** @type {SheetPartner|null} */ p, /** @type {number} */ scale, /** @type {number} */ k) =>
    <SheetFrame key={p ? "r" : "l"} scale={scale} breaks={breaks[k] || []}><SheetPage {...pageProps(d, p, partner ? (p ? "right" : "left") : "")} /></SheetFrame>;
  const reg = (/** @type {() => void} */ fn) => { restorers.current.add(fn); return () => { restorers.current.delete(fn); }; };

  const openChecks = checks.length;
  const note = main.conflict;
  return (
    <div class="sheet-root" ref={root} onKeyDown={onKey} onClick={onClick}>
      <div class="sheet-bar" role="toolbar" aria-label="Report">
        <span class="sheet-zoom" role="group" aria-label="Zoom">
          <button type="button" class="btn sm" aria-label="Zoom out" onClick={() => setZoom(stepZoom(zoom, -1))} disabled={zoom <= 0.4}>−</button>
          <span class="sheet-zv" aria-live="polite" data-zoom={zoom}>{Math.round(zoom * 100)}%</span>
          <button type="button" class="btn sm" aria-label="Zoom in" onClick={() => setZoom(stepZoom(zoom, 1))} disabled={zoom >= 0.8}>+</button>
        </span>
        <button type="button" class="btn" aria-pressed={exported ? "true" : "false"} onClick={() => setExported(!exported)}>Show as exported</button>
        {partner && !exported ? <label class="sheet-tog"><input type="checkbox" checked={together} onChange={e => setTogether(/** @type {HTMLInputElement} */ (e.currentTarget).checked)} /> Scroll together</label> : null}
        {partner && !exported && !partner.readOnly ? <button type="button" class="btn" onClick={() => { if (partner.match) { for (const x of doc.sections) if (match && match.differs(x.id)) partner.match(x.id); } else changeSide(matchAll(doc, partner.doc), "Matched internal"); }}>Match internal for every section</button> : null}
        <span class="sub sheet-status" role="status">{main.line}{partner && side.line ? ` · ${partner.label}: ${side.line}` : ""}</span>
        {openChecks && !exported ? <span class="sheet-checks" data-checks={openChecks}>{openChecks} {openChecks === 1 ? "check" : "checks"} open</span> : null}
        <span class="sheet-barr">{props.toolbar || null}</span>
      </div>
      {note ? <div class="sheet-note" role="alert">{note} <button type="button" class="btn sm" onClick={() => { main.reload(); onEvent({ type: "reload" }); }}>Reload</button></div> : null}
      {main.removed ? <div class="sheet-note sheet-removed" role="status">{main.removed}</div> : null}
      {partner && side.conflict ? <div class="sheet-note" role="alert">{partner.label}: {side.conflict} <button type="button" class="btn sm" onClick={() => { side.reload(); onEvent({ type: "reload", partner: true }); }}>Reload</button></div> : null}
      <div class={`sheet-area${partner && !together ? " sheet-split" : ""}${exported ? " sheet-exported" : ""}`}>
        {partner && !together
          ? <>
            <Pane pk={scrollKey} zoom={zoom} pages={1} regRestore={reg} onPinch={pinch}>{scale => frame(doc, null, scale, 0)}</Pane>
            <Pane pk={`${scrollKey}|${partner.scrollKey || "partner"}`} zoom={zoom} pages={1} regRestore={reg} onPinch={pinch}>{scale => frame(partner.doc, partner, scale, 1)}</Pane>
          </>
          : <Pane pk={scrollKey} zoom={zoom} pages={partner ? 2 : 1} regRestore={reg} onPinch={pinch}>{scale => <>
            {frame(doc, null, scale, 0)}
            {partner ? frame(partner.doc, partner, scale, 1) : null}
          </>}</Pane>}
      </div>
      {pop ? <div class="sheet-pop" role="dialog" aria-label="Check" style={{ left: `${pop.x}px`, top: `${pop.y}px` }}>
        <p>{pop.check.note}</p>{pop.check.last ? <p class="sub">{pop.check.last}</p> : null}
        <div class="sheet-pops">{(pop.check.actions || []).map(a => <button key={a.id} type="button" class="btn sm" onClick={() => { onEvent({ type: "check", id: pop.check.id, action: a.id }); setPop(null); }}>{a.label}</button>)}
          <button type="button" class="btn sm" onClick={() => setPop(null)}>Close</button></div>
      </div> : null}
      {found ? <div class="sheet-found" role="dialog" aria-label="Find the source" style={{ left: `${found.x}px`, top: `${found.y}px` }}>
        {found.message ? <p>{found.message}</p> : null}
        {(found.items || []).length ? <ul>{(found.items || []).map((it, k) => <li key={k}><button type="button" class="linkbtn" onClick={() => {
          onEvent({ type: "source", ref: it.ref }); if (/^[A-Z][A-Z0-9]{2,6}-(?:[A-Z]-)?\d{3}$/.test(it.ref)) openSheetRef(it.ref, props.onOpenItem); setFound(null); }}>{it.label || it.ref}</button>
          {it.quote ? <span class="sub"> “{it.quote}”</span> : null}</li>)}</ul> : null}
        <button type="button" class="btn sm" onClick={() => setFound(null)}>Close</button>
      </div> : null}
    </div>
  );
}

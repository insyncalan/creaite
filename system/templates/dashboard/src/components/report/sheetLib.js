// @ts-check
/* sheetLib (v2.1.0 P5, dev/sprints/v210-contract.md §4): the sheet's pure parts, no DOM and no Preact, so a test can run them
   on a plain document. Zoom limits, the changes Sheet makes to a data block (move, hide, show, rename, reset, figures, rows)
   with the layout kept in step (`syncLayout`: order, hidden, headings and glance always follow the sections, so P3's
   `remember_layout` gets a consistent layout), what differs between two pages (Side by side's ≠) and where the page breaks fall. */

export const SHEET_ZOOM_MIN = 0.4, SHEET_ZOOM_MAX = 0.8, SHEET_ZOOM_STEP = 0.05, SHEET_ZOOM_DEFAULT = 0.8;
/** CSS pixels in a millimetre (96 dpi). */
export const MM = 96 / 25.4;
/** A4 at its own size, the page's padding and the content one page holds (297 − 2 × 16 = 265 mm; contract §4.1). */
export const A4_W = 210, A4_H = 297, PAD_MM = 16, CONTENT_MM = 265;

/** A zoom held between 40% and 80% (a number that isn't one gives 80%). @param {number} z */
export const clampZoom = z => Math.round(Math.min(SHEET_ZOOM_MAX, Math.max(SHEET_ZOOM_MIN, Number.isFinite(z) ? z : SHEET_ZOOM_DEFAULT)) * 1000) / 1000;
/** One step of the − and + buttons and ⌘− ⌘+: 5 points, on the grid. @param {number} z @param {1|-1} dir */
export const stepZoom = (z, dir) => clampZoom(Math.round((z + dir * SHEET_ZOOM_STEP) / SHEET_ZOOM_STEP) * SHEET_ZOOM_STEP);
/** A trackpad pinch (a ctrl wheel): smooth, so a hand's small movements make small changes. @param {number} z @param {number} deltaY */
export const pinchZoom = (z, deltaY) => clampZoom(z * Math.exp(-Math.max(-60, Math.min(60, deltaY)) * 0.01));

/** The heading creaite would give a section. @param {{heading: string, default_heading?: string}} s */
export const defaultHeading = s => (s.default_heading == null ? s.heading : s.default_heading);

/** The document with its layout made to agree with its sections: `order` (every section id, in page order), `hidden`, `headings`
    (the headings that differ from creaite's own; ids the document doesn't hold are kept) and `glance` (the shown figures of the
    first figures section, in order). Other layout keys are kept as they were. @template {any} D @param {D} doc @returns {D} */
export function syncLayout(doc) {
  const d = /** @type {any} */ (doc), lay = { ...(d.layout || {}) }, secs = d.sections || [];
  lay.order = secs.map((/** @type {any} */ s) => s.id);
  lay.hidden = secs.filter((/** @type {any} */ s) => s.hidden).map((/** @type {any} */ s) => s.id);
  const heads = { ...(lay.headings || {}) };
  for (const s of secs) { if (s.heading !== defaultHeading(s)) heads[s.id] = s.heading; else delete heads[s.id]; }
  lay.headings = heads;
  const fig = secs.find((/** @type {any} */ s) => s.type === "figures" && !s.hidden);
  if (fig) lay.glance = (fig.figures || []).filter((/** @type {any} */ f) => f.shown !== false).map((/** @type {any} */ f) => f.key);
  return /** @type {D} */ ({ ...d, layout: lay });
}

/** @param {any} doc @param {string} id @param {(s: any, i: number) => any} fn */
function mapSection(doc, id, fn) {
  const sections = doc.sections.map((/** @type {any} */ s, /** @type {number} */ i) => (s.id === id ? fn(s, i) : s));
  return syncLayout({ ...doc, sections });
}

/** Move a section to index `to` (clamped); the list's order and `layout.order` change together. @param {any} doc @param {string} id @param {number} to @param {number} [lo] the first index a section may take (fixed sections above it stay put) */
export function moveSection(doc, id, to, lo = 0) {
  const from = doc.sections.findIndex((/** @type {any} */ s) => s.id === id);
  if (from < 0) return doc;
  const at = Math.max(lo, Math.min(doc.sections.length - 1, to));
  if (at === from || from < lo) return doc;
  const sections = doc.sections.slice(), [s] = sections.splice(from, 1);
  sections.splice(at, 0, s);
  return syncLayout({ ...doc, sections });
}
/** One place up (−1) or down (+1). @param {any} doc @param {string} id @param {number} delta @param {number} [lo] */
export function moveBy(doc, id, delta, lo = 0) {
  const from = doc.sections.findIndex((/** @type {any} */ s) => s.id === id);
  return from < 0 ? doc : moveSection(doc, id, from + delta, lo);
}
/** Hide a section: it becomes a thin bar in place and is left out of the export; its content is dropped when the document is saved
    (creaite_doc.clean), kept here so Show brings it back at once. @param {any} doc @param {string} id */
export const hideSection = (doc, id) => mapSection(doc, id, s => ({ ...s, hidden: true }));
/** Show a hidden section (a section that was saved hidden comes back empty of its type: the view refills it). @param {any} doc @param {string} id */
export const showSection = (doc, id) => mapSection(doc, id, s => ({ ...s, hidden: false }));
/** A section saved hidden has lost its content (§1): true when the view must refill it after Show. @param {any} s */
export const isStub = s => s.type === "table" ? !Array.isArray(s.rows) && !s.text : s.type === "figures" ? !Array.isArray(s.figures)
  : s.type === "panes" ? !Array.isArray(s.panes) : !("text" in s) || s.text == null;

/** A new heading (one line, never empty); equal to creaite's own, it leaves `layout.headings`. @param {any} doc @param {string} id @param {string} text */
export function renameHeading(doc, id, text) {
  const t = String(text || "").replace(/\s+/g, " ").trim();
  return t ? mapSection(doc, id, s => ({ ...s, heading: t })) : doc;
}
/** Back to creaite's own heading. @param {any} doc @param {string} id */
export const resetHeading = (doc, id) => mapSection(doc, id, s => ({ ...s, heading: defaultHeading(s) }));

/** Reorder a figures section: move the figure `key` to where `before` is (null: the end). @param {any} doc @param {string} id @param {string} key @param {string|null} before */
export function moveFigure(doc, id, key, before) {
  return mapSection(doc, id, s => {
    const figs = (s.figures || []).slice(), from = figs.findIndex((/** @type {any} */ f) => f.key === key);
    if (from < 0 || key === before) return s;
    const [f] = figs.splice(from, 1), at = before == null ? -1 : figs.findIndex((/** @type {any} */ x) => x.key === before);
    figs.splice(at < 0 ? figs.length : at, 0, f);
    return { ...s, figures: figs };
  });
}
/** Show or hide a figure (its eye). @param {any} doc @param {string} id @param {string} key @param {boolean} shown */
export const setFigureShown = (doc, id, key, shown) => mapSection(doc, id, s => ({
  ...s, figures: (s.figures || []).map((/** @type {any} */ f) => (f.key === key ? { ...f, shown } : f)) }));
/** Show or hide a table row (its eye): this document's only, never part of the layout. @param {any} doc @param {string} id @param {number} index @param {boolean} shown */
export const setRowShown = (doc, id, index, shown) => mapSection(doc, id, s => ({
  ...s, rows: (s.rows || []).map((/** @type {any} */ r, /** @type {number} */ i) => (i === index ? { ...r, shown } : r)) }));
/** "Showing 5 of 8": how many rows a table shows, of how many. @param {any} s @returns {[number, number]} */
export const rowCounts = s => [(s.rows || []).filter((/** @type {any} */ r) => r.shown !== false).length, (s.rows || []).length];

/** What a section shows, reduced to what Side by side compares: heading, text, the shown rows (cells), the shown figures,
    the panes and the health flag. Hidden sections compare as hidden. @param {any} s */
export function shownOf(s) {
  if (!s) return null;
  if (s.hidden) return { hidden: true };
  return { heading: s.heading, text: s.text || "", flag: (s.data || {}).flag || "",
    rows: (s.rows || []).filter((/** @type {any} */ r) => r.shown !== false).map((/** @type {any} */ r) => [r.ref || "", r.cells || {}]),
    figures: (s.figures || []).filter((/** @type {any} */ f) => f.shown !== false).map((/** @type {any} */ f) => [f.key, f.value, f.label, f.note || ""]),
    panes: (s.panes || []).map((/** @type {any} */ p) => [p.title, p.text]) };
}
/** True when two sections differ in what they show (the ≠ marker). @param {any} a @param {any} b */
export const sectionDiffers = (a, b) => JSON.stringify(shownOf(a)) !== JSON.stringify(shownOf(b));

/** The type of a text section (#218): a section Alan adds anywhere, named by him, written in the one editor with the Notes profile.
    creaite_doc.TEXT_TYPE is the same word. */
export const TEXT_TYPE = "freetext";
/** @param {any} s */
export const isTextSection = s => !!s && s.type === TEXT_TYPE;

/** A fresh id for a text section: `free_` and a short random word, so the internal and the client report never give two different
    sections the same one. @param {any} doc */
export function newTextId(doc) {
  const have = new Set((doc.sections || []).map((/** @type {any} */ s) => s.id));
  for (;;) {
    const id = `free_${Math.random().toString(36).slice(2, 8)}`;
    if (!have.has(id)) return id;
  }
}

/** The document with a new, empty text section after the section `afterId` (null or an id the document doesn't hold: at the end). Its
    heading is empty for Alan to name; it belongs to the report it was made in (`audience`: "internal", or "client" in a client report).
    @param {any} doc @param {string|null} afterId @param {string} [id] */
export function withTextSection(doc, afterId, id = newTextId(doc)) {
  const at = afterId == null ? -1 : doc.sections.findIndex((/** @type {any} */ s) => s.id === afterId);
  const sec = { id, type: TEXT_TYPE, heading: "", default_heading: "", hidden: false, text: "", audience: (doc.audience || "internal") === "internal" ? "internal" : "client" };
  const sections = doc.sections.slice();
  sections.splice(at < 0 ? sections.length : at + 1, 0, sec);
  return syncLayout({ ...doc, sections });
}

/** The document without a section (a text section deleted); its heading leaves the layout too. @param {any} doc @param {string} id */
export function withoutSection(doc, id) {
  const out = syncLayout({ ...doc, sections: doc.sections.filter((/** @type {any} */ s) => s.id !== id) });
  const heads = { ...((out.layout || {}).headings || {}) };
  delete heads[id];
  return { ...out, layout: { ...out.layout, headings: heads } };
}

/** The partner document with a copy of the left page's text section added where it stood (after the nearest earlier section the partner
    has, else at the end), marked as the partner's own (`audience`): Match internal for a text section the client report doesn't have.
    @param {any} left @param {any} right @param {any} src */
export function addTextCopy(left, right, src) {
  const copy = { ...JSON.parse(JSON.stringify(src)), hidden: false, audience: (right.audience || "internal") === "internal" ? "internal" : "client" };
  delete copy.tags;
  const order = left.sections.map((/** @type {any} */ s) => s.id), k = order.indexOf(src.id), have = new Set(right.sections.map((/** @type {any} */ s) => s.id));
  let after = null;
  for (let j = k - 1; j >= 0; j--) if (have.has(order[j])) { after = order[j]; break; }
  const at = after == null ? right.sections.length : right.sections.findIndex((/** @type {any} */ s) => s.id === after) + 1;
  const sections = right.sections.slice();
  sections.splice(at, 0, copy);
  return syncLayout({ ...right, sections });
}

/** Match internal for one section: the left section's content copied to the right page, keeping the right page's hidden state,
    its row eyes and its figure eyes. Returns the partner document. A text section the partner doesn't have is added there (that is the
    one way an internal text section reaches the client report). @param {any} left @param {any} right @param {string} id */
export function matchSection(left, right, id) {
  const src = left.sections.find((/** @type {any} */ s) => s.id === id), mine = right.sections.find((/** @type {any} */ s) => s.id === id);
  if (src && !mine && isTextSection(src)) return addTextCopy(left, right, src);
  if (!src || !mine) return right;
  if (isTextSection(src)) return mapSection(right, id, s => ({ ...s, heading: src.heading, text: src.text || "" }));
  const copy = JSON.parse(JSON.stringify(src));
  copy.hidden = !!mine.hidden;
  if (Array.isArray(copy.rows)) {
    const eyes = new Map((mine.rows || []).filter((/** @type {any} */ r) => r.ref).map((/** @type {any} */ r) => [r.ref, r.shown !== false]));
    copy.rows = copy.rows.map((/** @type {any} */ r) => (r.ref && eyes.has(r.ref) ? { ...r, shown: eyes.get(r.ref) } : r));
  }
  if (Array.isArray(copy.figures)) {
    const eyes = new Map((mine.figures || []).map((/** @type {any} */ f) => [f.key, f.shown !== false]));
    copy.figures = copy.figures.map((/** @type {any} */ f) => (eyes.has(f.key) ? { ...f, shown: eyes.get(f.key) } : f));
  }
  return mapSection(right, id, () => copy);
}
/** "Matching internal" or "Edited for the client", worked out by comparing, not stored. @param {any} left @param {any} right @param {string} id @param {string} label */
export function matchLabel(left, right, id, label) {
  const a = left.sections.find((/** @type {any} */ s) => s.id === id), b = right.sections.find((/** @type {any} */ s) => s.id === id);
  return sectionDiffers(a, b) ? `Edited for ${label === "Distributed" ? "distribution" : "the " + label.toLowerCase()}` : "Matching internal";
}

/** Where a page breaks. `sections` are the sections' natural [top, height] in content pixels (top measured from the top of the
    page's content, as laid out with no push); `page` is the content one page holds, in the same pixels. A section that would
    straddle a break and fits on one page is pushed down to the next page's top, as Chrome prints `break-inside: avoid-page`.
    Returns the `pushes` (the extra top margin each section needs, 0 for none) and the `marks` (the content y of each break).
    @param {[number, number][]} sections @param {number} page @param {number} total the content's natural height */
export function pageBreaks(sections, page, total) {
  let cum = 0;
  const pushes = sections.map(([t, h]) => {
    const top = t + cum, p = Math.floor(top / page);
    if (h <= page && h > 0 && top > p * page && top + h > (p + 1) * page) { const push = (p + 1) * page - top; cum += push; return push; }
    return 0;
  });
  const end = total + cum, marks = [];
  for (let k = 1; k * page < end - 1; k++) marks.push(k * page);
  return { pushes, marks };
}

/* #202 / #207: the header's rule (headerPolicy and its three constants) is shared with the app's top bar, so it lives in core/scrollPolicy.js (Sheet.jsx imports it from there). */

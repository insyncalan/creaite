// @ts-check
/* ===== #122 step C ===== work-item links, once, for every rich editor (Notes, Current state): what the `#` list offers, the text a link
   carries, and the chip drawn over it.

   A link is stored as plain Markdown, the same everywhere: `[ABC-A-012 · Action: Send the revised plan](creaite:item/ABC-A-012)`. The
   address (`creaite:item/<ID>`) is what finds the item; the words are 'ID · Designation: title' as they were when the link was made
   (Alan, 15-10-2026). Older links, whose words are only the ID, still resolve and open the item. Word, reports and the read view
   show the words (docx_tools.INLINE; panel.js mdInline); nothing but the editor draws a chip. */
import { Decoration, DecorationSet, Extension, Plugin, PluginKey } from "tiptap";
import { A, DEC, R } from "./data.js";
import { fd, TODAY } from "./page.js";

export const ITEM_HREF = /^creaite:item\/(.+)$/;

/** @typedef {{id: string, label: string, sub?: string, icon?: string, open?: boolean}} ItemOption */

/** The tracker row for an ID and its kind ("actions", "raid", "decisions"), or null. @param {string} id */
export function itemOf(id) {
  const a = A.find(x => x.id === id); if (a) return { k: "actions", x: a };
  const r = R.find(x => x.id === id); if (r) return { k: "raid", x: r };
  const d = DEC.find(x => x.id === id); if (d) return { k: "decisions", x: d };
  return null;
}
/** The item's designation, in the dashboard's own words (core/page.js kindOf, capitalised): Action, Decision, or the RAID type
    (Risk, Issue, Assumption, Dependency). "" when the item is not in the tracker. @param {string} id */
export function designation(id) {
  const hit = itemOf(id);
  if (!hit) return "";
  const x = /** @type {any} */ (hit.x);
  return hit.k === "actions" ? "Action" : hit.k === "raid" ? String(x.type || "Risk") : "Decision";
}
/** 'ID · Designation: title', on one line, with no square brackets (they would end the Markdown link early). @param {string} id */
export function itemText(id) {
  const hit = itemOf(id), t = hit ? String(/** @type {any} */ (hit.x).t || "").replace(/\s+/g, " ").replace(/[[\]]/g, m => (m === "[" ? "(" : ")")).trim() : "";
  const d = designation(id);
  return d ? `${id} · ${d}${t ? `: ${t}` : ""}` : id;
}
/** The Tiptap content for a chosen item: the whole of 'ID · Designation: title' as one link, then a space. @param {string} id */
export function itemContent(id) {
  return [{ type: "text", text: itemText(id), marks: [{ type: "link", attrs: { href: `creaite:item/${id}` } }] }, { type: "text", text: " " }];
}
/** An item's live state for its chip: the dot's tone ("bad", "warn", "ok", "off") and a few words.
    @param {string} id @returns {{tone: string, words: string, title: string}} */
export function itemState(id) {
  const hit = itemOf(id);
  if (!hit) return { tone: "off", words: "not in the tracker", title: `${id}: not in the tracker` };
  const x = /** @type {any} */ (hit.x), st = String(x.st || ""), open = /^(Open|Delayed|Pending|Proposed)$/i.test(st);
  let tone = open ? "warn" : "ok", words = st;
  if (hit.k === "actions") {
    if (open && x.due && x.due < TODAY) { tone = "bad"; words = `${st}, overdue ${fd(x.due)}`; }
    else if (open && x.due) words = `${st}, due ${fd(x.due)}`;
    if (x.o) words += ` · ${x.o}`;
  } else if (hit.k === "raid") { if (open && x.pr === "Urgent") tone = "bad"; words = `${x.type || "Risk"} · ${st}${x.pr ? ` · ${x.pr}` : ""}`; }
  else words = `Decision · ${st}`;
  return { tone, words, title: `${id} · ${x.t || ""} · ${words}` };
}

/** The items the `#` list offers, open ones first: a project's own (every project for "_portfolio"), filtered by what is typed
    against the ID, the designation or the title. Each row's words are 'ID · Designation: title'. @param {string} code @param {string} q @returns {ItemOption[]} */
export function itemOptions(code, q) {
  const ql = q.toLowerCase(), L = [];
  for (const [rows, icon] of /** @type {[any[], string][]} */ ([[A, "check"], [R, "alert"], [DEC, "flag"]]))
    for (const x of rows) {
      if (code !== "_portfolio" && x.p !== code) continue;
      if (ql && !(x.id.toLowerCase().includes(ql) || String(x.t || "").toLowerCase().includes(ql) || designation(x.id).toLowerCase().includes(ql))) continue;
      L.push({ id: x.id, label: itemText(x.id), icon, open: /^(Open|Delayed|Pending)$/i.test(x.st || "") });
    }
  return L.sort((a, b) => Number(!!b.open) - Number(!!a.open)).slice(0, 8);
}

/** The chip decoration for one text node that carries an item link (or null): drawn only, never written. @param {any} node @param {number} pos */
export function itemChip(node, pos) {
  const link = node.marks.find((/** @type {any} */ m) => m.type.name === "link"), im = link ? ITEM_HREF.exec(String(link.attrs.href || "")) : null;
  if (!im) return null;
  const s = itemState(im[1]);
  return Decoration.inline(pos, pos + node.nodeSize, { class: `nchip ${s.tone}`, "data-item": im[1], title: `${s.title} (click to open)` });
}
/** An extension that draws the chips over a document's item links (Current state; Notes draws them with its own decorations). */
export function itemChips() {
  return Extension.create({ name: "cxItemChips", addProseMirrorPlugins: () => [new Plugin({ key: new PluginKey("cxItemChips"),
    props: { decorations: state => {
      /** @type {any[]} */
      const out = [];
      state.doc.descendants((/** @type {any} */ node, /** @type {number} */ pos) => { if (node.isText) { const d = itemChip(node, pos); if (d) out.push(d); } });
      return DecorationSet.create(state.doc, out);
    } } })] });
}
/** A click on a chip: the item's ID, or "" (an Alt-click is the editor's, to edit inside the chip). @param {MouseEvent} e */
export function chipClicked(e) {
  if (e.altKey) return "";
  const t = /** @type {Element} */ (e.target), c = t && t.closest ? t.closest("[data-item]") : null;
  return c ? c.getAttribute("data-item") || "" : "";
}

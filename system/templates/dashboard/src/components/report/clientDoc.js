// @ts-check
/* clientDoc.js (v2.1.0 P8, BL-336): the client report's pure helpers, no screen and no server. Everything that can put the
   internal report's words on the client's page goes through matchClientSection, and it only ever copies what the client may see:
   text and the choice of which client-visible rows show, never an internal row, never a tag. The server checks again at save,
   approve and export (client_leak.py), so a slip here is caught there, and the left-out check says so. */

import { TEXT_TYPE, addTextCopy } from "./sheetLib.js";

/** @typedef {import("./Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {import("./Sheet.jsx").SheetSection} SheetSection */

/** The health flags creaite knows, with the class the page paints them in. */
export const CLIENT_FLAGS = /** @type {const} */ ([["On track", "g"], ["At risk", "a"], ["Off track", "r"]]);

/** A section by id. @param {SheetDoc|null|undefined} doc @param {string} id @returns {SheetSection|undefined} */
export const secOf = (doc, id) => doc ? doc.sections.find(s => s.id === id) : undefined;

/** The flag of a document's health section, or "". @param {SheetDoc|null|undefined} doc */
export const flagOf = doc => String(((secOf(doc, "health") || {}).data || {}).flag || "");

/** A document with one section replaced. @param {SheetDoc} doc @param {string} id @param {Partial<SheetSection>} patch @returns {SheetDoc} */
export const withClientSection = (doc, id, patch) => ({ ...doc, sections: doc.sections.map(s => s.id === id ? { ...s, ...patch } : s) });

/** The cells of a client table row, rebuilt from the item as the document holds it (a row hidden by its eye keeps only its ref, so
    showing it again fills it from the item, which is already client-safe: client wording only).
    @param {string} sectionId @param {any} item @returns {Record<string, string>} */
export function cellsFor(sectionId, item) {
  const it = item || {};
  const day = (/** @type {string} */ iso) => iso && /^\d{4}-\d{2}-\d{2}/.test(iso) ? `${iso.slice(8, 10)}-${iso.slice(5, 7)}-${iso.slice(0, 4)}` : "";
  if (sectionId === "risks") return { type: it.type || "", risk: it.title || "" };
  if (sectionId === "overdue") return { action: it.title || "", owner: it.owner || "", due: day(it.due_date) };
  if (sectionId === "asks") return { ask: it.title || "", from: it.owner || "", by: day(it.due_date), why: "" };
  if (sectionId === "decisions") return { decision: it.title || "", date: day(it.date) };
  return {};
}

/** The refs a table section shows. @param {SheetSection|undefined} s */
export const shownRefs = s => (s && !s.hidden ? (s.rows || []).filter(r => r.shown !== false && r.ref).map(r => String(r.ref)) : []);

/** Whether a client section matches its internal peer, worked out by comparing, never stored: Matching internal, or Edited for the
    client. Null when the section has no peer to compare (the header, At a glance). @param {SheetDoc} client @param {SheetDoc|null} internal @param {string} id */
export function matchState(client, internal, id) {
  const c = secOf(client, id), i = secOf(internal, id);
  if (!c || !i || c.hidden || c.type === "header" || c.type === "figures") return null;
  if (c.type === "health") return flagOf(client) === flagOf(internal) && (c.text || "").trim() === (i.text || "").trim() ? "matching" : "edited";
  if (c.type === "table") {
    const want = shownRefs(i).filter(r => (c.rows || []).some(x => x.ref === r)).sort().join(), have = shownRefs(c).sort().join();
    return want === have ? "matching" : "edited";
  }
  if (c.type === "timeline") return JSON.stringify(((c.data || {}).milestones || []).slice().sort()) === JSON.stringify((((i.data || {}).milestones || (i.data || {}).timeline) || []).filter((/** @type {string} */ m) => ((c.data || {}).timeline || []).includes(m)).sort()) ? "matching" : "edited";
  if (c.type === "panes") return JSON.stringify((c.panes || []).map(p => (p.text || "").trim())) === JSON.stringify((i.panes || []).map(p => (p.text || "").trim())) ? "matching" : "edited";
  return (c.text || "").trim() === (i.text || "").trim() ? "matching" : "edited";
}

/** The client document with one section matched to the internal one (Match internal). Text and Current state take the internal
    words (tags are never copied); Health takes the internal flag and headline; a table keeps its own client-visible rows and
    shows the ones the internal report shows; the milestone list takes the internal list. What is client-only stays: hidden
    sections, logos, the row eyes of rows the internal report doesn't list are closed, and the heading.
    @param {SheetDoc} client @param {SheetDoc} internal @param {string} id @returns {SheetDoc} */
export function matchClientSection(client, internal, id) {
  const c = secOf(client, id), i = secOf(internal, id);
  if (i && i.type === TEXT_TYPE && !i.hidden) {      // #218: a text section is internal until Alan matches it: this is the match (a copy, never tags)
    return c ? withClientSection(client, id, { heading: i.heading, text: i.text || "", audience: "client" }) : addTextCopy(internal, client, i);
  }
  if (!c || !i || c.hidden || c.type === "header" || c.type === "figures") return client;
  if (c.type === "health") {
    const meta = { ...(client.meta || {}) };
    delete meta.health_diff;
    return { ...withClientSection(client, id, { text: i.text || "", data: { ...(c.data || {}), flag: flagOf(internal) } }), meta };
  }
  if (c.type === "table") {
    const on = shownRefs(i);
    return withClientSection(client, id, { rows: (c.rows || []).map(r => on.includes(String(r.ref)) ? { ...r, shown: true, cells: r.cells || cellsFor(id, (client.items || {})[String(r.ref)]) } : { ref: r.ref, shown: false }) });
  }
  if (c.type === "timeline") {
    const all = (c.data || {}).timeline || [], listed = (((i.data || {}).milestones || (i.data || {}).timeline) || []).filter((/** @type {string} */ m) => all.includes(m));
    return withClientSection(client, id, { data: { ...(c.data || {}), milestones: listed } });
  }
  if (c.type === "panes") return withClientSection(client, id, { panes: (i.panes || []).map(p => ({ title: p.title, text: p.text })) });
  return withClientSection(client, id, { text: i.text || "", tags: [] });
}

/** Match internal for every section (client-only choices stay). @param {SheetDoc} client @param {SheetDoc} internal */
export const matchClientAll = (client, internal) => client.sections.reduce((d, s) => matchClientSection(d, internal, s.id), client);

/** The health difference kept on the document (contract §1 `meta`): the internal flag, the client's and the reason; null when they agree.
    @param {SheetDoc} client @param {string} internalFlag @param {string} clientFlag @param {string} reason */
export function healthDiff(client, internalFlag, clientFlag, reason) {
  const meta = { ...(client.meta || {}) };
  if (clientFlag === internalFlag) delete meta.health_diff;
  else meta.health_diff = { internal: internalFlag, client: clientFlag, reason: reason.trim() };
  return meta;
}

/** The items of one left-out group as plain words: "ABC-005 (not client-visible), ABC-006 (Sensitive) and 2 more".
    @param {{ref: string, why: string}[]} list */
export function leftLine(list) {
  const shown = list.slice(0, 4).map(x => `${x.ref} (${x.why})`).join(", ");
  return `${shown}${list.length > 4 ? ` and ${list.length - 4} more` : ""}`;
}

export const GROUP_LABEL = /** @type {Record<string, string>} */ ({ risks: "risks and issues", overdue: "overdue actions", decisions: "decisions", milestones: "milestones" });

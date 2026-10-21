// @ts-check
/* stores/workstreams.js (#247): a project's own workstreams, edited on its settings page (Alan, 19-10-2026: they move out of
   Settings). The tracker's workstreams table (D.ws_table, BL-58): add one (with the details suggested from the items), change its
   lead and keywords, rename it (its items follow), merge it into another of the project's (its items move, it is retired) and
   retire it (closed: no longer offered for new items; its items keep the name). Each change is one proposal with Undo (save). */
import { A, R } from "../core/data.js";
import { D, S, TODAY } from "../core/page.js";
import { save, snack } from "../core/server.js";
import { WSD, ownerFinal, wsNewOf, wsRow, wsSuggest } from "../settings.js";

/** the project's active workstreams, by name @param {string} code */
export const wsActive = code => WSD().filter(w => w.p === code && w.st === "Active").sort((a, b) => a.name.localeCompare(b.name));
/** @param {string} code @param {string} name */
const itemsOf = (code, name) => [...A, ...R].filter(x => x.p === code && String(x.ws || "").toLowerCase() === name.toLowerCase());
/** @param {any} x */
const tableOf = x => A.includes(x) ? "actions" : "raid";

/** @param {string} v */
const clean = v => String(v || "").replace(/\s+/g, " ").trim();
/** A lead typed or picked, as the register's full name ("" for none; null when the person prompt was cancelled). @param {string} lead */
async function leadOf(lead) { const v = clean(lead); if (!v) return ""; const o = await ownerFinal(v); return o === null ? null : o; }

/** @param {string} code @param {{name: string, lead: string, keywords: string}} v @returns {Promise<string>} "" when saved, else the problem */
export async function wsAdd(code, v) {
  const name = clean(v.name);
  if (!name) return "Give the workstream a name.";
  if (wsRow(code, name)) return `This project already has “${name}”.`;
  const lead = await leadOf(v.lead); if (lead === null) return "Not saved.";
  const s = wsSuggest(code, name), made = wsNewOf({ project: code, name, lead, keywords: clean(v.keywords) || s.keywords, aliases: s.aliases, channel: s.channel }, `${S.me} (dashboard), ${TODAY}`);
  const ok = await save(`Workstream ${name} added`, [made.item], null, () => { if (!D.ws_table) D.ws_table = []; D.ws_table.push(made.row); },
    () => { const i = WSD().indexOf(made.row); if (i >= 0) D.ws_table.splice(i, 1); });
  return ok === false ? "Not saved." : "";
}

/** Change a workstream's name, lead or keywords; a rename moves its items. @param {string} id @param {{name: string, lead: string, keywords: string}} v
    @returns {Promise<string>} */
export async function wsUpdate(id, v) {
  const w = WSD().find(x => x.id === id); if (!w) return "That workstream isn't here any more.";
  const name = clean(v.name); if (!name) return "Give the workstream a name.";
  const lead = await leadOf(v.lead); if (lead === null) return "Not saved.";
  /** @type {Record<string, string|null>} */
  const changes = {}, next = { name, lead, keywords: clean(v.keywords) };
  Object.entries(next).forEach(([k, x]) => { if (x !== (w[k] || "")) changes[k] = x || null; });
  if (!Object.keys(changes).length) return "";
  if (changes.name && WSD().some(x => x !== w && x.p === w.p && x.name.toLowerCase() === name.toLowerCase())) return `This project already has “${name}”: use Merge into to join them.`;
  const before = { ...w }, old = w.name, moved = changes.name ? itemsOf(w.p, old) : [];
  const ok = await save(`Workstream ${old} ${changes.name ? `renamed ${name}` : "updated"}`, [{ op: "update", table: "workstreams", id, changes, based_on: w.updated_at }], null,
    () => { Object.assign(w, Object.fromEntries(Object.entries(changes).map(([k, x]) => [k, x || ""]))); moved.forEach(x => { x.ws = name; }); },
    () => { Object.assign(w, before); moved.forEach(x => { x.ws = old; }); });
  return ok === false ? "Not saved." : "";
}

/** Merge a workstream into another of the project's: its items move to that one, and it is retired. @param {string} id @param {string} intoId */
export async function wsMerge(id, intoId) {
  const w = WSD().find(x => x.id === id), to = WSD().find(x => x.id === intoId);
  if (!w || !to || w === to || w.p !== to.p) return false;
  const moved = itemsOf(w.p, w.name);
  const ops = [...moved.map(x => ({ op: "update", table: tableOf(x), id: x.id, changes: { workstream: to.name }, based_on: x.updated_at })),
    { op: "cancel", table: "workstreams", id, based_on: w.updated_at }];
  const ok = await save(`Workstream ${w.name} merged into ${to.name}`, ops, null,
    () => { moved.forEach(x => { x.ws = to.name; }); w.st = "Closed"; }, () => { moved.forEach(x => { x.ws = w.name; }); w.st = "Active"; });
  return ok !== false;
}

/** Retire a workstream: it is no longer offered for new items; its items keep the name. @param {string} id */
export async function wsRetire(id) {
  const w = WSD().find(x => x.id === id); if (!w) return false;
  const ok = await save(`Workstream ${w.name} retired`, [{ op: "cancel", table: "workstreams", id, based_on: w.updated_at }], null,
    () => { w.st = "Closed"; }, () => { w.st = "Active"; });
  if (ok === false) snack("Not saved");
  return ok !== false;
}

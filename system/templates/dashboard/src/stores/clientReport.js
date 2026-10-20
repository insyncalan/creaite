// @ts-check
/* stores/clientReport.js (v2.1.0 P8, BL-336, dev/COMPONENTS.md §2): the client view's state, one store for the area. Everything
   comes from P3's report routes (/api/report/draft, save, approve, export) and the read-only /api/report/check (the left-out
   check). The client's report and the week's internal report are two documents; the internal one is only read here (P6 edits it). */
import { signal } from "@preact/signals";
import { api, oneLine, viaServer } from "../core/server.js";
import { saveExport } from "./exportSave.js";
import { readLogos } from "./weekly.js";
import { matchClientSection, secOf } from "../components/report/clientDoc.js";

/** @typedef {import("../components/report/Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {{group: string, ref: string, title: string, why: string, kind: string}} LeftItem */
/** @typedef {{items: LeftItem[], sections: {id: string, heading: string}[], logos: string[], tags: number,
    health: {internal: string, client: string, reason: string}|null, findings: string[], ready: boolean, not_ready: string,
    facts_week: string|null}} LeftOut */
/** @typedef {{section: string, row: any, item: any}} Addable */
/** @typedef {{ok: boolean, left_out?: LeftOut, addable?: Addable[], message?: string}} Check */

/** What the view was opened with: the project code, the week ending (a Friday, or empty for the latest) and the client. */
export const crArg = signal(/** @type {{code: string, week?: string, client?: string}|null} */ (null));
/** The open's outcome: ok, or a message. */
export const crOpen = signal(/** @type {{ok: boolean, message?: string}|null} */ (null));
/** The client's report on screen (the view keeps it; the sheet hands back a new one on every edit). */
export const crDoc = signal(/** @type {SheetDoc|null} */ (null));
/** The week's internal report, read only here. */
export const crInternal = signal(/** @type {SheetDoc|null} */ (null));
/** The version the client page was opened at, sent with each save. */
export const crBase = signal(/** @type {number|undefined} */ (undefined));
/** What the draft route said about the client report: where it is (draft, filed, new), the internal week it locks to, readiness. */
export const crInfo = signal(/** @type {{where: string, filed: boolean, ready: boolean, not_ready: string, baseline: {date: string, path: string, version: number}|null, findings: string[]}|null} */ (null));
export const crMode = signal(/** @type {"client"|"side"} */ ("client"));
/** The last left-out check, for the page's "Not in this report" lists and the dialog. */
export const crCheck = signal(/** @type {Check|null} */ (null));
/** The project's logo files the page may draw ([{kind, path}]); their pictures are read into stores/weekly.js's weeklyLogos. */
export const crLogos = signal(/** @type {{kind: string, path: string}[]} */ ([]));
export const crBusy = signal("");
export const crDialog = signal(false);
export const crDirty = signal(false);
/** What the last Match internal held back: null, or {copied: heading[], held: [{id, heading, findings}], message}. The dialog reads it. */
export const crHeld = signal(/** @type {{copied: string[], held: {id: string, heading: string, findings: string[]}[], skipped: {id: string, heading: string}[], message: string}|null} */ (null));

let crAsked = 0;

/** Which report is open: the open's number, what it was opened with, and the document's project, week and client. Anything that awaits
    the server and then writes the client page compares this before and after, so a late answer never lands in another report.
    @param {SheetDoc|null} [d] */
export function crIdentity(d) {
  const x = d === undefined ? crDoc.value : d;
  return x ? `${crAsked}|${JSON.stringify(crArg.value)}|${x.project}|${x.date}|${x.client || ""}` : "";
}

/** Two versions of the same report: the same project, week and client. @param {SheetDoc|null|undefined} a @param {SheetDoc|null|undefined} b */
const sameDoc = (a, b) => !!a && !!b && a.project === b.project && a.date === b.date && (a.client || "") === (b.client || "");
/** The same report (project, week and client) as the one open now, whichever version of it. @param {SheetDoc} d */
export const sameReport = d => sameDoc(crDoc.value, d);

/** Open (or reload) the client report: the week's internal report (read only; built from the tracker when none is saved) and the
    client's. `fresh` rebuilds the client's report from the tracker (the approved week's locked facts when there is one),
    leaving its saved draft as it is until Save. @param {{code: string, week?: string, client?: string}} arg @param {boolean} [fresh] */
export async function loadClientReport(arg, fresh) {
  const mine = ++crAsked;
  crArg.value = arg;
  crCheck.value = null;
  crDirty.value = false;
  if (!viaServer()) { crOpen.value = { ok: false, message: "The client view needs the live server." }; return; }
  crBusy.value = "Opening the client report…";
  const base = { code: arg.code, week_ending: arg.week || undefined };
  const [i, c] = await Promise.all([api("/api/report/draft", { kind: "weekly", ...base }), api("/api/report/draft", { kind: "client", ...base, client: arg.client || undefined, fresh: fresh || undefined })]);
  if (mine !== crAsked) return;
  crBusy.value = "";
  if (!c || !c.ok || !c.doc) { crOpen.value = { ok: false, message: oneLine((c && c.message) || "") || "Couldn't open the client report" }; crDoc.value = null; return; }
  crInternal.value = i && i.ok ? i.doc : null;
  crDoc.value = c.doc;
  crLogos.value = c.logos || [];
  readLogos(arg.code, c.logos || []);
  crBase.value = Number(c.doc.version) || undefined;
  crInfo.value = { where: c.where, filed: !!c.filed, ready: !!c.ready, not_ready: c.not_ready || "", baseline: c.baseline || null, findings: c.findings || [] };
  crOpen.value = { ok: true };
  runCheck();
}

/** The left-out check of the document on screen (read only; nothing is written). Keeps the answer for the page's lists. */
export async function runCheck() {
  const d = crDoc.value, opened = crIdentity(d);
  if (!d || !viaServer()) return null;
  const r = /** @type {Check} */ (await api("/api/report/check", { doc: d }));
  if (crIdentity() !== opened) return null;            // another report opened meanwhile: its lists (and their Add buttons) are never this one's
  crCheck.value = r && r.ok ? r : { ok: false, message: oneLine((r && r.message) || "") || "The check didn't run" };
  return crCheck.value;
}

/** Save the client page as the draft (the sheet's onSave). @param {{doc: SheetDoc, base_version?: number}} req */
export async function saveClientPage(req) {
  const r = await api("/api/report/save", { doc: req.doc, base_version: req.base_version });
  if (r && r.ok) {
    crBase.value = Number(r.version) || crBase.value; crDirty.value = false;
    if (crInfo.value && crInfo.value.where === "new") crInfo.value = { ...crInfo.value, where: "draft" };
  }
  return r;
}

/** Approve the client report (saving the page first). @param {boolean} [force] */
export async function approveClientReport(force) {
  const a = crArg.value, d = crDoc.value;
  if (!a || !d) return { ok: false, message: "Nothing is open." };
  return api("/api/report/approve", { kind: "client", code: a.code, week_ending: d.date, client: d.client || a.client || undefined, doc: d, base_version: crBase.value, force: !!force });
}

/** Export the client report (the page saved first); the route runs the left-out check again and answers with it. v2.5.1 (#239): the
    server makes every client file from the report's checked snapshot (client_snapshot.client_export), so no page is ever posted for
    one. @param {"html"|"docx"|"pdf"} fmt */
export async function exportClientReport(fmt) {
  const a = crArg.value, d = crDoc.value;
  if (!a || !d) return { ok: false, message: "Nothing is open." };
  const opened = crIdentity(d);
  if (crDirty.value || (crInfo.value && crInfo.value.where === "new")) { const s = await saveClientPage({ doc: d, base_version: crBase.value }); if (!s.ok) return s; }
  if (crIdentity() !== opened) return { ok: false, message: "Another report opened while this one was saving, so nothing was exported." };
  return saveExport({ kind: "client", code: a.code, week_ending: d.date, client: d.client || a.client || undefined, fmt });
}

let matchChain = Promise.resolve();

/** Whether an internal report is the client report's own week of its own project (#234). @param {SheetDoc|null} i @param {SheetDoc} c */
const sameWeek = (i, c) => !!i && !!c && i.project === c.project && i.date === c.date;

/** Match internal, behind the client gate (v2.5.0): each section's matched text is checked by the server (client_leak.findings through
    /api/report/match-check, read only) BEFORE it is copied; a section whose matched text brings a finding the client report did not
    already have is held (the client section stays as it was) and named in crHeld, the clean ones are copied. Nothing is copied when
    the check cannot run. The client page therefore never holds unsaved internal words after Match internal. One at a time, so
    Match internal for every section never races itself. @param {string[]|null} ids the sections, or null for every one */
export function matchInternal(ids) {
  const asked = crIdentity();            // a match queued behind another runs only if the report it was asked on is still the one open
  matchChain = matchChain.then(() => crIdentity() === asked ? matchInternalNow(ids) : undefined).catch(() => undefined);
  return matchChain;
}

/** @param {string[]|null} ids */
async function matchInternalNow(ids) {
  const d0 = crDoc.value, i = crInternal.value, opened = crIdentity(d0);
  if (!d0 || !i || !sameWeek(i, d0)) return;                             // #234: never another project's or week's internal report
  // the race fix (v2.5.0): after every await, a different open report (another project, week or client, or a reload) drops the match
  // silently: nothing is copied, nothing is said on the other report's page
  const moved = () => crIdentity() !== opened || !sameReport(d0) || !sameWeek(crInternal.value, d0);   // the same open, project, week and client, and its own internal report
  const heading = (/** @type {string} */ id) => String((secOf(i, id) || secOf(d0, id) || { heading: id }).heading || id);
  const all = ids ? ids : d0.sections.map(s => s.id).concat(i.sections.filter(s => !secOf(d0, s.id)).map(s => s.id));
  // #218: "every section" never brings an internal-audience text section over; it is named instead, and matched only one at a time
  const internalText = (/** @type {string} */ id) => { const x = secOf(i, id); return !!x && x.type === "freetext" && x.audience === "internal"; };
  const want = ids ? all : all.filter(id => !internalText(id));
  const skipped = ids ? [] : all.filter(internalText).map(id => ({ id, heading: heading(id) }));
  const cands = want.map(id => ({ id, doc: matchClientSection(d0, i, id) })).filter(c => c.doc !== d0);
  if (!cands.length) { crHeld.value = skipped.length ? { copied: [], held: [], skipped, message: "" } : null; return; }
  const failed = () => { crHeld.value = { copied: [], skipped, held: cands.map(c => ({ id: c.id, heading: heading(c.id), findings: [] })), message: "Not matched: the check of internal wording didn't run, so nothing was copied." }; };
  if (!viaServer()) { failed(); return; }
  const r = await api("/api/report/match-check", { docs: [d0, ...cands.map(c => c.doc)] });
  if (moved()) return;
  if (!r || !r.ok || !Array.isArray(r.findings) || r.findings.length !== cands.length + 1) { failed(); return; }
  const codes = (/** @type {{code: string}[]} */ fs) => fs.reduce((m, f) => m.set(f.code, (m.get(f.code) || 0) + 1), /** @type {Map<string, number>} */ (new Map()));
  const base = codes(r.findings[0]);
  const fresh_of = (/** @type {{code: string, message: string}[]} */ fs) => { const seen = /** @type {Map<string, number>} */ (new Map()); return fs.filter(f => { const n = (seen.get(f.code) || 0) + 1; seen.set(f.code, n); return n > (base.get(f.code) || 0); }); };   // by stable code (and how many), never by sentence
  const done = /** @type {string[]} */ ([]), held = /** @type {{id: string, heading: string, findings: string[]}[]} */ ([]), clean = /** @type {string[]} */ ([]);
  cands.forEach((c, n) => {
    const fresh = fresh_of(r.findings[n + 1]).map(f => f.message);
    if (fresh.length) held.push({ id: c.id, heading: heading(c.id), findings: fresh });
    else clean.push(c.id);
  });
  /** the clean sections copied onto the page as it is now; a section Alan changed while the check ran keeps his edit
      (the sheet replaces only the section it edits, so an untouched one is the same object as before) @param {SheetDoc} on */
  const kept = (/** @type {SheetDoc} */ on) => sameDoc(on, d0) ? clean.filter(id => secOf(on, id) === secOf(d0, id)) : [];   // never onto another report (a section neither has is "unchanged" only on this one)
  const onto = (/** @type {SheetDoc} */ on) => kept(on).reduce((x, id) => matchClientSection(x, i, id), on);
  if (clean.length) {                   // the clean sections together are checked once more: a finding the parts did not make alone holds all back
    for (let tries = 0; ; tries++) {
      const now = crDoc.value;
      if (!now || moved()) return;
      const d = onto(now);
      const last = await api("/api/report/match-check", { docs: [d] });
      if (moved()) return;
      const extra = last && last.ok && last.findings && last.findings[0] ? fresh_of(last.findings[0]) : null;
      if (!extra || extra.length) { failed(); return; }
      if (crDoc.value === now) { kept(now).forEach(id => done.push(heading(id))); crDoc.value = d; crDirty.value = true; break; }
      if (tries >= 2) { crHeld.value = { copied: [], skipped, held: [], message: "Not matched: the report kept changing while its wording was checked, so nothing was copied. Try again." }; return; }
    }                                   // the page changed while the check ran: copy onto the page as it is now and check that once more
  }
  crHeld.value = held.length || skipped.length ? { copied: done, held, skipped, message: !held.length ? "" : `Not matched: ${held.map(h => h.heading).join(", ")} ${held.length === 1 ? "has" : "have"} internal wording.` } : null;
}

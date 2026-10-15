// @ts-check
/* stores/reporting.js (BL-337, v2.1.0 P9): the reporting space and the Reports page, worked out in the browser from what the
   page already holds: the filed reports (D.files, the project's reports folder), the reports waiting in Review, each project's
   client-report rhythm and the weekly-report day and time in Settings. Read only: nothing here writes, runs a report or approves
   one; Open, Approve and Export belong to the report editor (BL-335, BL-336).

   STUBBED until the report records of P3 land (dev/sprints/v210-contract.md): `reportRecord()` is the one place that would read
   them (the data block's kind, audience, client, date, state "draft" or "approved"). Today it reads `D.reports`, an optional list
   of {project, kind: "weekly"|"client", client, date, state, path, edited, health, differs, sections_hidden}; when none is
   there, a report's state comes from its filed file, or a draft waiting in Review. Also stubbed: more than one client per
   project (the cockpit's "Client / partner" line is the one client), and the editor itself (components/reporting/ReportEditorStub.jsx).

   The week is the reminder's: the last weekly-report day (Friday) at or before today, from its time on that day. */
import { signal } from "@preact/signals";
import { FILES, P, REV } from "../core/data.js";
import { D, nowStamp, S, TODAY } from "../core/page.js";
import { setRailCount } from "./rail.js";

/** @typedef {"ok"|"warn"|"bad"|""} Tone */
/** @typedef {{key: string, label: string, tone: Tone, path?: string, edited?: string}} RepState */
/** @typedef {{client: string, rhythm: string, state: RepState, due: boolean, differs: string}} ClientRep */
/** @typedef {{week: string, internal: RepState, clients: ClientRep[], files: any[], needs: boolean}} WeekView */

/** bumped when the data reloads or a page is shown, so a mounted page redraws */
export const repTick = signal(0);
/** Reports page: Needs me or All projects */
export const repFilter = signal(/** @type {"need"|"all"} */ ("need"));
/** the week the Reports page shows (YYYY-MM-DD, a Friday), or "" for this week */
export const repWeek = signal("");

const REP_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const GAP = /** @type {Record<string, number>} */ ({ Weekly: 7, Fortnightly: 14, Monthly: 30 });
const MS = 864e5;

/** @param {string} d @param {number} n */
export const repAddDays = (d, n) => new Date(Date.parse(d) + n * MS).toISOString().slice(0, 10);
/** @param {string} a @param {string} b whole days from b to a */
const between = (a, b) => Math.round((Date.parse(a) - Date.parse(b)) / MS);

/** The week now being reported: the last report day (Settings, Friday by default) at or before today, or the one before if
    it is that day but before the reminder's time (as the Friday reminder is, build_dashboard.reminders).
    @param {string} [today] @param {string} [hm] */
export function thisWeek(today = TODAY, hm = nowStamp().slice(11, 16)) {
  const day = Math.max(0, REP_DAYS.indexOf(String(S.weeklyDay || "Friday")));
  const wd = (new Date(today).getUTCDay() + 6) % 7;
  let start = repAddDays(today, -((wd - day + 7) % 7));
  if (start === today && hm < String(S.weeklyTime || "12:00")) start = repAddDays(start, -7);
  return start;
}
/** The week the Reports page shows. */
export const shownWeek = () => repWeek.value || thisWeek();

/** STUB: the report record for a report, from D.reports until P3's records are read.
    @param {string} code @param {"weekly"|"client"} kind @param {string} week @param {string} [client] @returns {any} */
export function reportRecord(code, kind, week, client) {
  const L = /** @type {any[]} */ (D.reports || []);
  return L.find(r => r.project === code && r.kind === kind && r.date === week && (kind === "weekly" || !client || r.client === client)) || null;
}

/** @param {string} code @param {"weekly"|"client"} kind a report for this project in Review: a draft nobody has approved */
const inReview = (code, kind) => REV.some(r => !r.done && r.kind === "draft" && r.ref === "report" && r.p === code
  && (kind === "weekly" ? /weekly/i : /client/i).test((r.rec && r.rec.t) || ""));

/** The project's filed reports of one kind: [file], newest first.
    @param {string} code @param {"weekly"|"client"} kind */
function filed(code, kind) {
  const re = kind === "weekly" ? /Weekly report/ : /Client report/;
  return FILES.filter(f => f.p === code && f.f === "reports" && re.test(f.n) && f.date).sort((a, b) => b.date.localeCompare(a.date));
}

/** The week's files for a project: its reports whose name date falls in the seven days ending on `week`.
    @param {string} code @param {string} week */
export function weekFiles(code, week) {
  const from = repAddDays(week, -6);
  return FILES.filter(f => f.p === code && f.f === "reports" && f.date && f.date >= from && f.date <= week).sort((a, b) => a.n.localeCompare(b.n));
}

/** One report's state for a week.
    @param {string} code @param {"weekly"|"client"} kind @param {string} week @param {string} [client] @param {string} [rhythm] @returns {{state: RepState, due: boolean}} */
function stateOf(code, kind, week, client, rhythm) {
  const cur = week === thisWeek(), rec = reportRecord(code, kind, week, client);
  if (rec) {
    const s = String(rec.state || "draft");
    return { state: { key: s, label: s === "approved" ? "Approved" : "Draft", tone: s === "approved" ? "ok" : "warn", path: rec.path, edited: rec.edited }, due: s !== "approved" };
  }
  const L = filed(code, kind), from = repAddDays(week, -6);
  const found = L.find(f => kind === "weekly" ? f.n.startsWith(week + " ") : f.date >= from && f.date <= week);
  if (found) return { state: { key: "filed", label: "Filed", tone: "ok", path: found.path }, due: false };
  if (cur && inReview(code, kind)) return { state: { key: "draft", label: "Draft", tone: "warn" }, due: true };
  if (kind === "weekly") return { state: cur ? { key: "due", label: "Not drafted", tone: "warn" } : { key: "missing", label: "Not filed", tone: "" }, due: cur };
  const gap = GAP[rhythm || "Weekly"] || 7, last = L.find(f => f.date < from);
  const due = !last || between(week, last.date) >= gap;
  if (!due) return { state: { key: "notdue", label: `Not due (${(rhythm || "Weekly").toLowerCase()})`, tone: "" }, due: false };
  return cur ? { state: { key: "due", label: "Due", tone: "warn" }, due: true } : { state: { key: "missing", label: "Not filed", tone: "" }, due: false };
}

/** A project's week: the internal report, each client's report (STUB: the one client the cockpit names), the week's files.
    @param {string} code @param {string} [week] @returns {WeekView} */
export function weekView(code, week = thisWeek()) {
  const p = P.find(x => x.code === code) || /** @type {any} */ ({});
  const w = stateOf(code, "weekly", week);
  const rhythm = p.rhythm || "Weekly", name = (p.client || "").trim() || "Client";
  const c = stateOf(code, "client", week, name, rhythm), rec = reportRecord(code, "client", week, name);
  const clients = [{ client: name, rhythm, state: c.state, due: c.due, differs: rec && rec.differs ? String(rec.differs) : "" }];
  return { week, internal: w.state, clients, files: weekFiles(code, week), needs: !["filed", "approved", "notdue"].includes(w.state.key) || clients.some(x => ["due", "draft"].includes(x.state.key)) };
}

/** The weeks a project's space lists, newest first: this week, the three before, and any older week with a filed report.
    @param {string} code */
export function spaceWeeks(code) {
  const cur = thisWeek(), set = new Set([0, 1, 2, 3].map(i => repAddDays(cur, -7 * i)));
  FILES.filter(f => f.p === code && f.f === "reports" && f.date).forEach(f => {
    const wd = (new Date(f.date).getUTCDay() + 6) % 7, day = Math.max(0, REP_DAYS.indexOf(String(S.weeklyDay || "Friday")));
    const end = repAddDays(f.date, (day - wd + 7) % 7);
    if (end <= cur) set.add(end);
  });
  return [...set].sort().reverse().slice(0, 12);
}

/** The projects with a report to check or a client report due this week (the count on Reports in the menu).
    @returns {string[]} codes */
export const needsMe = () => P.filter(p => weekView(p.code).needs).map(p => p.code);   /* this week only: weekView's default */

/** The count on Reports in the menu. */
export function reportsBadge() {
  const n = needsMe().length;
  setRailCount("reports", n, `${n} project${n === 1 ? "" : "s"} with a report to check or a client report due`);
}

/** The project whose reporting space is open, the week and the editor view ("", "internal", "client" or "side"). */
export const spaceCode = signal("");
export const spaceWeek = signal("");
export const spaceEdit = signal(/** @type {""|"internal"|"client"|"side"} */ (""));

/** P8's client view (origin/v210-p8-client; not on this base, so the address does nothing until P8 merges): #client-report=CODE/week/client.
    @param {string} code @param {string} week @param {string} client */
export const clientReportHref = (code, week, client) => `#client-report=${code}/${week}/${encodeURIComponent(client)}`;

/** @param {string} week */
export const weekLabel = week => week.split("-").reverse().join("-");

/** The address of a project's reporting space. @param {string} code @param {string} [week] @param {string} [edit] */
export function reportingHref(code, week, edit) {
  return `#reporting=${code}${week ? `&w=${week}` : ""}${edit ? `&e=${edit}` : ""}`;
}
/** The state of "#reporting=ABC&w=2026-10-09&e=client", or null. @param {string} hash @param {(c: string) => boolean} known */
export function parseReporting(hash, known) {
  const m = /^#?reporting=([A-Z][A-Z0-9]{2,6})((?:&[a-z]=[^&]*)*)$/.exec(String(hash || ""));
  if (!m || !known(m[1])) return null;
  const kv = Object.fromEntries(m[2].split("&").filter(Boolean).map(x => x.split("=")));
  return { code: m[1], week: /^\d{4}-\d{2}-\d{2}$/.test(kv.w || "") ? kv.w : "", edit: ["internal", "client", "side"].includes(kv.e) ? kv.e : "" };
}

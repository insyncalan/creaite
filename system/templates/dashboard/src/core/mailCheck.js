// @ts-check
/* core/mailCheck.js (#358): the true line a mail check shows while it runs, and how it ends. Pure functions, no imports, no DOM, no
   state: dev/tests/test_mail_check.py runs this file under Node. The page (src/ask.js) holds the state and calls these.

   The rule that keeps it private: the classifier is an allow-list on WHOLE labels. It knows only the fixed describe_tool form
   "Microsoft 365: <tool name>" and the fixed plain_step phrases, matched exactly. Everything else (a Bash label, which may carry a
   mail subject, ToolSearch, Read and Write labels, "Staging what the sweep found", the followed-people commands) gives nothing.
   A subject that contains "mail", "Teams" or "Calendar" therefore changes nothing. Every string drawn here is a fixed phrase or a
   whole number: no label text, subject, sender or name ever reaches the line. There is no total, no "of N" and no percentage, and
   no place is ever called finished: the words are "Looked in". */

/** The exact first event of a typed mail check (live_server.PANEL_SWEEP_STEP; test_mail_check.py pins the two together). */
export const MC_MARKER = "Sweeping (stages proposals only)";

/** @typedef {{places: string[], searches: number, reads: number}} McState */

const PLACE_NAMES = { mail: "Outlook mail", teams: "Teams", calendar: "calendar" };
const PLACE_SHORT = { mail: "mail", teams: "Teams", calendar: "calendar" };
const PLACE_ORDER = ["mail", "teams", "calendar"];

/** describe_tool's form for a Microsoft 365 tool, tool name with spaces. place: where it looked; null: a search that names no place. */
const CHAT = {
  "outlook email search": "mail",
  "chat message search": "teams", "teams list chats": "teams", "teams list channels": "teams",
  "teams list channel messages": "teams", "teams list teams": "teams",
  "outlook calendar search": "calendar", "find meeting availability": "calendar",
  "sharepoint search": null, "sharepoint folder search": null,
};
/** plain_step's fixed phrases (live_server.PLAIN_M365). */
const PLAIN = {
  "Searching mail": "mail", "Searching Teams chats": "teams", "Reading Teams chats": "teams", "Reading Teams channels": "teams",
  "Reading Teams": "teams", "Reading the calendar": "calendar", "Searching SharePoint and OneDrive": null,
};
const READ_CHAT = "read resource", READ_PLAIN = "Reading a meeting, a message or a chat";
const CHAT_PREFIX = "Microsoft 365: ";

/** What one finished step is: a search in a place, a search that names no place, an item read, or nothing.
    @param {unknown} label @returns {{kind: "search", place: string|null} | {kind: "read"} | null} */
export function mcClassify(label) {
  if (typeof label !== "string") return null;
  /** @type {string} */ let tool = "";
  if (label.startsWith(CHAT_PREFIX)) tool = label.slice(CHAT_PREFIX.length);
  if (tool) {
    if (tool === READ_CHAT) return { kind: "read" };
    return Object.prototype.hasOwnProperty.call(CHAT, tool) ? { kind: "search", place: CHAT[tool] } : null;
  }
  if (label === READ_PLAIN) return { kind: "read" };
  return Object.prototype.hasOwnProperty.call(PLAIN, label) ? { kind: "search", place: PLAIN[label] } : null;
}

/** @returns {McState} */
export const mcNew = () => ({ places: [], searches: 0, reads: 0 });

/** The state after one finished step. A failed call never has an event, so it is never counted.
    @param {McState} s @param {unknown} label @returns {McState} */
export function mcStep(s, label) {
  const c = mcClassify(label);
  if (!c) return s;
  if (c.kind === "read") return { ...s, reads: s.reads + 1 };
  const places = c.place && !s.places.includes(c.place) ? PLACE_ORDER.filter(p => p === c.place || s.places.includes(p)) : s.places;
  return { places, searches: s.searches + 1, reads: s.reads };
}

/** @param {McState} s @param {Record<string,string>} names */
const placeList = (s, names) => s.places.map(p => names[p]).join(", ");
const mcPlural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

/** The working line, replacing the quip. @param {McState} s */
export function mcLine(s) {
  if (!s.places.length) return "Starting";
  return `Looked in so far: ${placeList(s, PLACE_NAMES)} · ${mcPlural(s.searches, "search", "searches")}, ${mcPlural(s.reads, "item", "items")} read`;
}

/** The badge's label: places only, never a counter. @param {McState} s */
export const mcBadge = s => (s.places.length ? `Mail check: ${placeList(s, PLACE_SHORT)}` : "Mail check: starting");

/** The places alone, for the live node (it is written only when this text changes). @param {McState} s */
export const mcPlaces = s => (s.places.length ? `Looked in so far: ${placeList(s, PLACE_NAMES)}` : "");

/** Whether a run is a mail check, from the run record the server sends (never from the words typed).
    @param {{sweep?: boolean, kind?: string}|null|undefined} run */
export const mcIsRun = run => !!run && (run.sweep === true || run.kind === "sweep");

/** The check's own files: proposed-YYYY-MM-DD-HHMM-sweep[-n].json (sweep.py stage). A file made on the dashboard never matches.
    @param {unknown} file @returns {string|null} the minute stamp "YYYY-MM-DDTHH:MM", or null */
export function mcFileStamp(file) {
  const m = /^proposed-(\d{4}-\d{2}-\d{2})-(\d{2})(\d{2})-sweep(?:-\d+)?\.json$/.exec(String(file || "").split("/").pop() || "");
  return m ? `${m[1]}T${m[2]}:${m[3]}` : null;
}
/** A local ISO time cut to its minute. @param {string} iso */
const minute = iso => String(iso || "").slice(0, 16);

/** Found N: the new items among the Review rows that are the check's own files, stamped from the minute the run started to the minute it ended.
    Rows Alan made on the dashboard, or from another file, are never counted. An update to an existing item is not new: it is counted
    apart (upd), so a check that saved only updates is not described as having found nothing.
    @param {{file?: string, op?: string, p?: string|null}[]} rows @param {string} startedIso @param {string} endedIso
    @returns {{n: number, need: number, upd: number}} */
export function mcFound(rows, startedIso, endedIso) {
  const a = minute(startedIso), b = minute(endedIso);
  let n = 0, need = 0, upd = 0;
  for (const r of rows || []) {
    const st = mcFileStamp(r && r.file);
    if (!st || !a || !b || st < a || st > b || !r) continue;
    if (r.op === "new") { n++; if (!r.p) need++; }
    else if (r.op === "update") upd++;
  }
  return { n, need, upd };
}

/** The closing line. outcome: "done", "stopped" (Stop pressed) or "early" (timed out or failed). found: from mcFound, or null when the
    page could not read Review. Found N counts new items only; updates to existing items are said apart.
    @param {"done"|"stopped"|"early"} outcome @param {McState} s @param {{n: number, need: number, upd?: number}|null} found */
export function mcEnd(outcome, s, found) {
  const looked = s.places.length ? ` Looked in ${placeList(s, PLACE_NAMES)}.` : "";
  const need = n => (n === 0 ? "none need a project" : n === 1 ? "1 needs a project" : `${n} need a project`);
  const upd = found && found.upd ? found.upd : 0;
  const updText = upd === 1 ? "1 update to an existing item" : `${upd} updates to existing items`;
  const done = outcome === "done";
  if (done && !found) return "Finished. Open Review to see what it found.";
  if (!done && !found) return `${outcome === "early" ? "Stopped early." : "Stopped."}${looked}`;
  const head = done ? "Finished." : outcome === "early" ? "Stopped early." : "Stopped.";
  const so = done ? "" : " so far";
  if (found.n) return `${head}${looked} Found ${found.n} new${so}, ${need(found.need)}${upd ? `, and ${updText}` : ""}.`;
  if (upd) return `${head}${looked} No new items; ${updText}${so}.`;
  return done ? "Finished. Nothing new to review." : `${head}${looked} Nothing saved yet.`;
}

/** The fixed phrase a mail check's steps list shows for a live step. A label is shown only when it is one of the fixed phrases the
    classifier knows, or creaite's own marker; every other label is "A creaite step". @param {unknown} label */
export function mcStepText(label) {
  if (label === MC_MARKER) return MC_MARKER;
  const c = mcClassify(label);
  return c ? String(label) : "A creaite step";
}

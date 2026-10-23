// @ts-check
/* core/irFold.js (#232-0, v2.5.0): Intake and Review's folding rules and live counts, as pure functions over the merged row model
   (build_dashboard.intake_review_model, D.intake_review). No imports, no DOM, no state: dev/tests/test_intake_review_fold.py runs
   this file under Node. The page's store (stores/intakeReview.js) holds the state and calls these.

   The rules (brief, locked mockup 18-10-2026b):
   - Nothing is open when the page opens. One click on a meeting with proposals opens it in place; a second click on it closes it.
     One meeting is open at a time: opening another closes the first. A meeting with nothing to check (arrived, approved) never
     opens; its row's buttons act instead.
   - An open meeting stays open through an apply, a refresh and a decision (Stark's risk 2): it closes only when Alan closes it,
     or when it has left the list. With all its proposals decided it stays open and shows "All checked".
   - Inside an open meeting: "Needs your decision" first, "Routine" second, both open; an empty group is not drawn.
   - Sections of the page: the meetings (open), From mail and Teams (open), Other proposals (open), Later and Not needed (folded,
     one click shows and one hides).
   - The stage counts (Arrived, Drafted, Approved) are a filter: one click shows only that stage, a second click (or Show all)
     shows all.
   `done(n)` says whether proposal n has been decided on the page (REV's done flag); the server's lists are not changed. */

/** @typedef {{needs: number[], routine: number[]}} IrGroups */
/** @typedef {{id: string, stage: string, state: string, groups: IrGroups, path?: string|null}} IrMeeting */
/** @typedef {{meetings: IrMeeting[], mail: IrGroups, other: IrGroups, later: any[], not_needed: any[], counts: Record<string, number>}} IrModel */

export const IR_STAGES = ["arrived", "drafted", "approved"];
export const IR_SECTIONS = ["meetings", "mail", "other", "later", "not_needed"];
/** Sections folded when the page opens. */
export const IR_FOLDED = ["later", "not_needed"];

/** Whether a meeting can open in place (it has proposals to check). @param {IrMeeting} m */
export const irOpenable = m => !!m && m.stage === "drafted";

/** The open meeting after a click on meeting `id`: opens it, closes it if it was open, or leaves things be if it can't open.
    @param {string|null} cur @param {string} id @param {IrModel} model @returns {string|null} */
export function irToggle(cur, id, model) {
  if (cur === id) return null;
  const m = (model.meetings || []).find(x => x.id === id);
  return irOpenable(m) ? id : cur;
}

/** The open meeting after new data (an apply, a refresh): kept while the meeting is still in the list, whatever its proposals.
    @param {string|null} cur @param {IrModel} model @returns {string|null} */
export function irKeepOpen(cur, model) {
  return cur && (model.meetings || []).some(x => x.id === cur) ? cur : null;
}

/** A group's proposals still waiting on the page. `held(n)` (optional) says a proposal now has a hold that the server's group did not
    know (a peek edit made an Issue a Risk): it moves from Routine to Needs, never the other way (clearing a hold leaves it where it is).
    @param {IrGroups} g @param {(n:number)=>boolean} done @param {(n:number)=>boolean} [held] @returns {IrGroups} */
export function irLive(g, done, held) {
  const keep = (/** @type {number[]} */ a) => (a || []).filter(n => !done(n));
  const needs = keep(g && g.needs), routine = keep(g && g.routine);
  if (!held) return { needs, routine };
  return { needs: [...needs, ...routine.filter(held)], routine: routine.filter(n => !held(n)) };
}

/** The groups drawn inside an open meeting (or the mail and other sections), in order, empty ones left out.
    @param {IrGroups} g @param {(n:number)=>boolean} done @param {(n:number)=>boolean} [held] @returns {{kind: "needs"|"routine", ns: number[], open: boolean}[]} */
export function irGroupsShown(g, done, held) {
  const l = irLive(g, done, held);
  return /** @type {const} */ (["needs", "routine"]).filter(k => l[k].length).map(k => ({ kind: k, ns: l[k], open: true }));
}

/** What "Approve routine (n)" approves: the routine group only, never the first. @param {IrGroups} g @param {(n:number)=>boolean} done @param {(n:number)=>boolean} [held] */
export const irBulk = (g, done, held) => irLive(g, done, held).routine;

/* The hold, recomputed after a peek edit: the page's mirror of review.hold_reason (the server's one rule). The server sends each row's
   `hold`; an edit in the peek can change only what the peek edits: the project, a RAID item's type and an update's status. So these are
   recomputed here, and every other hold (client wording, a drafted update, minutes, a change to an owner...) is kept as the server sent
   it. dev/tests/test_intake_review_peek_fix.py compares this with review.hold_reason on the same cases. */
const IR_CLOSING = ["Closed", "Cancelled", "Done", "Dropped"];
const IR_EDITED_HOLDS = ["need a project", "new risk", "new decision", "closing update", "decision made", "status change"];
/** @param {{p?: string|null, kind?: string, op?: string, rec?: any, flags?: string[], hold?: string}} r @returns {string} "" is routine */
export function irHold(r) {
  const flags = r.flags || [], rec = r.rec || {};
  if (!r.p) return "need a project";
  if (flags.includes("conflict")) return "conflict";
  if (flags.includes("invalid")) return "invalid";
  if (r.op === "new" && r.kind === "decisions") return "new decision";
  if (r.op === "new" && r.kind === "raid" && rec.type === "Risk") return "new risk";
  if (r.op === "update" && rec.field === "status") {
    const t = String(rec.target || ""), letter = (/-([A-Z])-/.exec(t) || [])[1] || "R";          /* a RAID item's ID has no letter */
    if (letter === "D") return ["Made", "Withdrawn"].includes(rec.to) ? "decision made" : "status change";
    if (letter === "A" || letter === "R") return IR_CLOSING.includes(rec.to) ? "closing update" : "status change";
  }
  return IR_EDITED_HOLDS.includes(r.hold || "") ? "" : r.hold || "";
}

/** The stage filter after a click on a stage's count ("all" is Show all). @param {string} cur @param {string} g */
export const irStageClick = (cur, g) => (g === "all" || cur === g ? "all" : IR_STAGES.includes(g) ? g : cur);

/** The meetings the list shows under a stage filter. @param {IrModel} model @param {string} stage */
export const irFiltered = (model, stage) => (model.meetings || []).filter(m => stage === "all" || m.stage === stage);

/** A section's fold after one click: folded sections open, open ones fold. @param {Record<string, boolean>} folded @param {string} sec */
export function irFoldClick(folded, sec) { return { ...folded, [sec]: !irIsFolded(folded, sec) }; }
/** Whether a section is folded (its default until clicked). @param {Record<string, boolean>} folded @param {string} sec */
export const irIsFolded = (folded, sec) => (sec in (folded || {}) ? !!folded[sec] : IR_FOLDED.includes(sec));

/** The kinds a file can be (#232-A5). */
export const IR_KINDS = ["transcript", "minutes"];
/** A file whose kind cannot be switched: a .vtt or .srt is always a transcript (the server also says so, `fixed`). @param {any} m */
export const irFixed = m => !!m && m.src === "upload" && (!!m.fixed || /\.(vtt|srt)$/i.test(String(m.path || m.title || "")));
/** A file's kind: the person's choice for that file (`kinds`, by path), else the server's guess (`ft`, "" when it could not tell).
    A choice counts only for the file it was made for: it records the file's size and day, and an entry that no longer matches (the
    file was replaced by another with the same path) is ignored. A .vtt or .srt is a transcript whatever was chosen. Everything that is
    not an uploaded file is a transcript. @param {any} m @param {Record<string, any>} [kinds] {path: {k, size, day}} */
export function irKindOf(m, kinds) {
  if (!m || m.src !== "upload" || irFixed(m)) return "transcript";
  const e = kinds && m.path ? kinds[m.path] : null;
  if (e && typeof e === "object" && IR_KINDS.includes(e.k) && e.size === (m.size || 0) && e.day === (m.day || "")) return e.k;
  return m.ft || "";
}
/** Whether a file name may be sent to ask creaite inside a command: no control character (a newline, tab or NUL), backtick, double
    quote or angle bracket. Such a file must be renamed first. @param {string|null|undefined} name */
export function irNameOk(name) {
  for (const ch of String(name == null ? "" : name)) { const c = ch.charCodeAt(0); if (c < 32 || c === 127 || "`\"<>".includes(ch)) return false; }
  return true;
}
/** Whether a file row's kind is not known yet: it is not ready to process, and not in the badge. */
export const irUnsure = (/** @type {any} */ m, /** @type {Record<string, any>} */ kinds) => !!m && m.src === "upload" && !irKindOf(m, kinds);

/** #325/#323: a meeting's state, defined once. The chip on its row, the stage boxes' counts and the Group by / filter all read this.
    "waiting" (no transcript yet), "ready" (transcript here, not drafted), "check" (suggestions still to decide), "done" (everything
    decided). `left` is how many of its suggestions are still waiting on the page. @param {{stage: string, state?: string}} m @param {number} left */
export function irMeetingState(m, left) {
  if (m.stage === "approved") return "done";
  if (m.stage === "drafted") return left > 0 ? "check" : "done";
  return m.state === "waiting" ? "waiting" : "ready";
}
/** The state's words (the chip's), and the stage the stage boxes count it under. */
export const IR_STATE_CHIP = { waiting: "Waiting for the transcript", check: "Suggestions to check", done: "Done" };
export const IR_STATE_STAGE = { waiting: "arrived", ready: "arrived", check: "drafted", done: "approved" };
/** A meeting's state on the live model: the proposals left are the ones not yet decided on the page. @param {IrMeeting} m @param {(n:number)=>boolean} done */
export function irStateOf(m, done) { const l = irLive(m.groups, done); return irMeetingState(m, l.needs.length + l.routine.length); }

/** How many meetings are in each state, live: the numbers the Group by / filter shows beside its choices.
    @param {IrModel} model @param {(n:number)=>boolean} done @returns {Record<string, number>} */
export function irStateCounts(model, done) {
  const o = { waiting: 0, ready: 0, check: 0, done: 0 };
  for (const m of model.meetings || []) o[irStateOf(m, done)]++;
  return o;
}

/** The live counts: the server's, less what the page has decided since. A meeting whose proposals are all decided counts as
    approved. @param {IrModel} model @param {(n:number)=>boolean} done */
export function irCounts(model, done, kinds) {
  const ms = model.meetings || [];
  const stage = (/** @type {IrMeeting} */ m) => IR_STATE_STAGE[irStateOf(m, done)];     /* the same state the chip shows */
  const all = [...ms.flatMap(m => [...(m.groups.needs || []), ...(m.groups.routine || [])]),
    ...["mail", "other"].flatMap(k => [...((/** @type {any} */ (model)[k] || {}).needs || []), ...((/** @type {any} */ (model)[k] || {}).routine || [])])];
  const toApprove = new Set(all.filter(n => !done(n))).size;
  const arrivedReady = ms.filter(m => m.stage === "arrived" && m.state === "ready"), needType = arrivedReady.filter(m => irUnsure(m, kinds)).length;
  const ready = arrivedReady.length - needType;       /* a file whose kind is not known is not ready (the mockup's nProc) and not in the badge */
  return { need_type: needType, arrived: ms.filter(m => stage(m) === "arrived").length, ready, drafted: ms.filter(m => stage(m) === "drafted").length,
    approved: ms.filter(m => stage(m) === "approved").length, to_approve: toApprove, badge: ready + toApprove,
    all: ms.length };   /* #232-A4: the fourth box, Show all: every meeting and file on the page */
}

/** Esc: the peek closes first, then the open meeting. @param {{peek: any, open: string|null}} st */
export const irEsc = st => (st.peek != null ? { ...st, peek: null } : { ...st, open: null });

/** The three views and their names; the first is the default. */
export const IR_VIEWS = [["list", "List"], ["board", "Board"], ["two", "Two panes"]];
/** A remembered view made safe. @param {any} v */
export const irViewNorm = v => (IR_VIEWS.some(x => x[0] === v) ? v : "list");

/* The Search box (#232-A6): a client-side filter. Every word typed must be found (any case) somewhere in the row's fields. */
/** @param {string} q */
export const irQueryWords = q => String(q || "").toLowerCase().split(/\s+/).filter(Boolean);
/** Whether a row matches the search `q`: an empty search matches everything. @param {string} q @param {(string|null|undefined)[]} fields */
export function irMatches(q, fields) {
  const w = irQueryWords(q);
  if (!w.length) return true;
  const hay = (fields || []).filter(Boolean).join("\n").toLowerCase();
  return w.every(x => hay.includes(x));
}

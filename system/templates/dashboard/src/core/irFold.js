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
/** @typedef {{id: string, stage: string, state: string, groups: IrGroups}} IrMeeting */
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

/** A group's proposals still waiting on the page. @param {IrGroups} g @param {(n:number)=>boolean} done @returns {IrGroups} */
export function irLive(g, done) {
  const keep = (/** @type {number[]} */ a) => (a || []).filter(n => !done(n));
  return { needs: keep(g && g.needs), routine: keep(g && g.routine) };
}

/** The groups drawn inside an open meeting (or the mail and other sections), in order, empty ones left out.
    @param {IrGroups} g @param {(n:number)=>boolean} done @returns {{kind: "needs"|"routine", ns: number[], open: boolean}[]} */
export function irGroupsShown(g, done) {
  const l = irLive(g, done);
  return /** @type {const} */ (["needs", "routine"]).filter(k => l[k].length).map(k => ({ kind: k, ns: l[k], open: true }));
}

/** What "Approve routine (n)" approves: the routine group only, never the first. @param {IrGroups} g @param {(n:number)=>boolean} done */
export const irBulk = (g, done) => irLive(g, done).routine;

/** The stage filter after a click on a stage's count ("all" is Show all). @param {string} cur @param {string} g */
export const irStageClick = (cur, g) => (g === "all" || cur === g ? "all" : IR_STAGES.includes(g) ? g : cur);

/** The meetings the list shows under a stage filter. @param {IrModel} model @param {string} stage */
export const irFiltered = (model, stage) => (model.meetings || []).filter(m => stage === "all" || m.stage === stage);

/** A section's fold after one click: folded sections open, open ones fold. @param {Record<string, boolean>} folded @param {string} sec */
export function irFoldClick(folded, sec) { return { ...folded, [sec]: !irIsFolded(folded, sec) }; }
/** Whether a section is folded (its default until clicked). @param {Record<string, boolean>} folded @param {string} sec */
export const irIsFolded = (folded, sec) => (sec in (folded || {}) ? !!folded[sec] : IR_FOLDED.includes(sec));

/** The live counts: the server's, less what the page has decided since. A meeting whose proposals are all decided counts as
    approved. @param {IrModel} model @param {(n:number)=>boolean} done */
export function irCounts(model, done) {
  const ms = model.meetings || [], left = (/** @type {IrMeeting} */ m) => { const l = irLive(m.groups, done); return l.needs.length + l.routine.length; };
  const stage = (/** @type {IrMeeting} */ m) => (m.stage === "drafted" && !left(m) ? "approved" : m.stage);
  const all = [...ms.flatMap(m => [...(m.groups.needs || []), ...(m.groups.routine || [])]),
    ...["mail", "other"].flatMap(k => [...((/** @type {any} */ (model)[k] || {}).needs || []), ...((/** @type {any} */ (model)[k] || {}).routine || [])])];
  const toApprove = new Set(all.filter(n => !done(n))).size;
  const ready = ms.filter(m => m.stage === "arrived" && m.state === "ready").length;
  return { arrived: ms.filter(m => stage(m) === "arrived").length, ready, drafted: ms.filter(m => stage(m) === "drafted").length,
    approved: ms.filter(m => stage(m) === "approved").length, to_approve: toApprove, badge: ready + toApprove };
}

/** Esc: the peek closes first, then the open meeting. @param {{peek: any, open: string|null}} st */
export const irEsc = st => (st.peek != null ? { ...st, peek: null } : { ...st, open: null });

/** The three views and their names; the first is the default. */
export const IR_VIEWS = [["list", "List"], ["board", "Board"], ["two", "Two panes"]];
/** A remembered view made safe. @param {any} v */
export const irViewNorm = v => (IR_VIEWS.some(x => x[0] === v) ? v : "list");

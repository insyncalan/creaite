// @ts-check
/* IntakeReviewPage (#232-0 skeleton, v2.5.0): Intake and Review on one page, #intake-review; the old #intake, #inbox and #review
   addresses open it (core/nav.js parseHash). One sidebar entry (stores/rail.js: the "review" item, titled Intake and Review).
   Three views chosen by each person (List, Board, Two panes), remembered in this browser (stores/intakeReview.js).
   The model is the server's (D.intake_review); the folding rules are core/irFold.js.
   Who builds what next (dev/proposals/intake-review-232/README.md):
   - 232-A (Intake side): MeetingRow's actions (Process with progress, Later, Not needed with a reason and undo), Process all ready,
     Upload files (drop anywhere), the Later and Not needed sections' Restore, keys Enter, N, H.
   - 232-B (Review side): ProposalLine becomes the full proposal row; Approve routine (rvDecideMany), Approve, Reject with a
     reason; the peek for mail and Teams proposals (Save, Save and approve, previous and next); keys arrows, Esc.
   - 232-C: the rail badge and Today's Intake and Review count from irLiveCounts(); the old pages' tests and the snapshots. */
import { render } from "preact";
import { $ } from "../../core/dom.js";
import { IR_STAGES, IR_VIEWS, irEsc, irFiltered, irIsFolded } from "../../core/irFold.js";
import { shared } from "../../core/state.js";
import { irAfterData, irClickFold, irClickMeeting, irClickStage, irFolded, irLiveCounts, irModel, irOpen, irPeek, irSel, irSetView, irStage, irTick, irView } from "../../stores/intakeReview.js";
import { BoardView, ListView, TwoPanes } from "./views.jsx";

const STN = { arrived: "Arrived", drafted: "Drafted", approved: "Approved" };
const VIEWICON = {
  list: <path d="M4 6h16M4 12h16M4 18h16" />,
  board: <><rect x="3" y="4" width="5" height="16" rx="1" /><rect x="10" y="4" width="5" height="10" rx="1" /><rect x="17" y="4" width="4" height="13" rx="1" /></>,
  two: <><rect x="3" y="4" width="8" height="16" rx="1" /><rect x="13" y="4" width="8" height="16" rx="1" /></>,
};
const plural = (/** @type {number} */ n, /** @type {string} */ w) => `${n} ${w}${n === 1 ? "" : "s"}`;

/** The stage counts: each a filter (one click shows that stage, a second shows all). @param {{c: Record<string, number>}} props */
export function StagePipe({ c }) {
  const sub = { arrived: `${c.ready} ready to process`, drafted: `${plural(c.to_approve, "proposal")} to check`, approved: "this week" };
  return (
    <div class="icpipe" role="group" aria-label="Stages">
      {IR_STAGES.map((g, i) => <>
        {i ? <span class="ar" aria-hidden="true">→</span> : null}
        <div class="evbox click" role="button" tabindex={0} data-irstage={g} aria-pressed={String(irStage.value === g)}
          onClick={() => irClickStage(g)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); irClickStage(g); } }}>
          <div class="v">{c[g]}</div><div class="l">{STN[/** @type {keyof STN} */ (g)]}</div><div class="icsub">{sub[/** @type {keyof sub} */ (g)]}</div>
        </div>
      </>)}
      <button type="button" class="btn" data-irstage="all" onClick={() => irClickStage("all")}>Show all</button>
    </div>
  );
}

/** A folded section's heading (Later, Not needed). @param {{sec: string, title: string, n: number, children: any}} props */
function FoldSection({ sec, title, n, children }) {
  const folded = irIsFolded(irFolded.value, sec);
  return (
    <div class="rgroup irsec" data-irsec={sec}>
      <h2>{title} <span class="sub rgc">{n}</span> <button type="button" class="linkbtn" data-irfold={sec} aria-expanded={String(!folded)} onClick={() => irClickFold(sec)}>{folded ? "Show" : "Hide"}</button></h2>
      {folded ? null : children}
    </div>
  );
}

function IntakeReviewView() {
  irTick.value;
  const model = irModel(), c = irLiveCounts(), view = irView.value;
  const list = irFiltered(model, irStage.value);
  return (
    <div class="wrapmax irpage">
      <h1 id="irTitle">Intake and Review</h1>
      <p class="sub" id="irSub" style={{ margin: "4px 0 0" }}>{c.ready} ready to process · {plural(c.to_approve, "proposal")} to approve</p>
      <div class="toolbar rvtools">
        <span class="sp"></span>
        <span class="seg" role="group" aria-label="How you see Intake and Review">
          {IR_VIEWS.map(([v, l]) => (
            <button type="button" data-irview={v} aria-pressed={String(view === v)} title={l} onClick={() => irSetView(v)}>
              <svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">{VIEWICON[/** @type {keyof VIEWICON} */ (v)]}</svg>
              <span style={{ marginLeft: "6px" }}>{l}</span>
            </button>
          ))}
        </span>
      </div>
      {view === "board" ? <BoardView model={model} /> : view === "two" ? <TwoPanes model={model} list={model.meetings} /> : <><StagePipe c={c} /><ListView model={model} list={list} /></>}
      <FoldSection sec="later" title="Later" n={model.later.length}>
        {model.later.length ? <ul class="irlist">{model.later.map(x => <li data-irkey={x.key}>{x.title}</li>)}</ul> : <div class="empty">Nothing set aside for later. A meeting comes back here when its transcript arrives.</div>}
      </FoldSection>
      <FoldSection sec="not_needed" title="Not needed" n={model.not_needed.length}>
        {model.not_needed.length ? <ul class="irlist">{model.not_needed.map(x => <li data-irkey={x.key}>{x.title}{x.reason ? <span class="sub"> · {x.reason}</span> : null}</li>)}</ul> : <div class="empty">Nothing marked Not needed.</div>}
      </FoldSection>
      <p class="sub irold">While this page is being built, the earlier pages are here: <a href="#" data-go="inbox">Intake</a> · <a href="#" data-go="review">Review</a></p>
    </div>
  );
}

let mounted = false;
/** go()'s renderer for Intake and Review. */
export function renderIntakeReview() {
  const el = $("#v-intake-review");
  if (!el) return;
  irAfterData();
  if (!mounted) { render(<IntakeReviewView />, el); mounted = true; bootIrKeys(); }
}

/* Keyboard (stubs): up and down move between meetings, Enter opens or closes the one with focus (232-A: Enter processes a ready
   one), Esc closes the peek and then the open meeting. N (Not needed) and H (Later) are 232-A's. */
function bootIrKeys() {
  document.addEventListener("keydown", e => {
    if (shared.VIEW !== "intake-review" || e.metaKey || e.ctrlKey || e.altKey) return;
    const t = /** @type {HTMLElement} */ (e.target);
    if (t && t.closest && t.closest("input,textarea,select,[contenteditable=true]")) return;
    const rows = /** @type {HTMLElement[]} */ ([...document.querySelectorAll("#v-intake-review [data-irm]")]);
    const at = rows.indexOf(/** @type {HTMLElement} */ (t.closest ? t.closest("[data-irm]") : null));
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (!rows.length) return; e.preventDefault();
      const r = rows[Math.max(0, Math.min(rows.length - 1, at < 0 ? 0 : at + (e.key === "ArrowDown" ? 1 : -1)))];
      r.focus(); irSel.value = r.dataset.irm || null; return;
    }
    if (e.key === "Enter" && at >= 0) { e.preventDefault(); irClickMeeting(rows[at].dataset.irm || ""); return; }
    if (e.key === "Escape" && (irPeek.value != null || irOpen.value)) { const s = irEsc({ peek: irPeek.value, open: irOpen.value }); irPeek.value = s.peek; irOpen.value = s.open; }
  });
}

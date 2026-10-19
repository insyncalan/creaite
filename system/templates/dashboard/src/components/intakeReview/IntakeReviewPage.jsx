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
import { useLayoutEffect, useRef } from "preact/hooks";
import { $ } from "../../core/dom.js";
import { IR_STAGES, IR_VIEWS, irEsc, irFiltered, irIsFolded } from "../../core/irFold.js";
import { fd } from "../../core/page.js";
import { shared } from "../../core/state.js";
import { irAfterData, irAside, irBlocked, irClickFold, irClickMeeting, irClickStage, irFolded, irLiveCounts, irModel, irOpen, irPeek, irSel, irSetView, irStage, irTick, irView } from "../../stores/intakeReview.js";
import { irAddFiles, irAskReason, irCanProcess, irCanSetAside, IR_REASONS, irLater, irNotNeeded, irProcess, irProcessAll, irReady, irRestore, IR_UPLOAD_TYPES } from "./actions.js";
import { BoardView, IR_STAGE_NAMES, ListView, TwoPanes } from "./views.jsx";
import { MenuPanel, menuItemsIn } from "../Menu.jsx";

export * from "./actions.js";   /* #232-A: the Intake actions are on window for the tests, as the page's other exports are */

const VIEWICON = {
  list: <path d="M4 6h16M4 12h16M4 18h16" />,
  board: <><rect x="3" y="4" width="5" height="16" rx="1" /><rect x="10" y="4" width="5" height="10" rx="1" /><rect x="17" y="4" width="4" height="13" rx="1" /></>,
  two: <><rect x="3" y="4" width="8" height="16" rx="1" /><rect x="13" y="4" width="8" height="16" rx="1" /></>,
};
const irPlural = (/** @type {number} */ n, /** @type {string} */ w) => `${n} ${w}${n === 1 ? "" : "s"}`;

/** The stage counts: each a filter (one click shows that stage, a second shows all). @param {{c: Record<string, number>}} props */
export function StagePipe({ c }) {
  const sub = { arrived: `${c.ready} ready to process`, drafted: `${irPlural(c.to_approve, "proposal")} to check`, approved: "this week" };
  return (
    <div class="icpipe" role="group" aria-label="Stages">
      {IR_STAGES.map((g, i) => <>
        {i ? <span class="ar" aria-hidden="true">→</span> : null}
        <div class="evbox click" role="button" tabindex={0} data-irstage={g} aria-pressed={irStage.value === g}
          onClick={() => irClickStage(g)} onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); irClickStage(g); } }}>
          <div class="v">{c[g]}</div><div class="l">{IR_STAGE_NAMES[/** @type {keyof IR_STAGE_NAMES} */ (g)]}</div><div class="icsub">{sub[/** @type {keyof sub} */ (g)]}</div>
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
      <h2>{title} <span class="sub rgc">{n}</span> <button type="button" class="linkbtn" data-irfold={sec} aria-expanded={!folded} onClick={() => irClickFold(sec)}>{folded ? "Show" : "Hide"}</button></h2>
      {folded ? null : children}
    </div>
  );
}


/** Process all ready (n): the meetings and files whose transcript is ready, one after another. */
function ProcessAll() {
  const n = irReady().length, blocked = irBlocked();
  return <button type="button" class="btn" data-ira="processall" disabled={!n || blocked}
    title={blocked ? "ask creaite is busy; try again when it's finished" : n ? "" : "Nothing is ready to process"} onClick={() => irProcessAll()}>Process all ready ({n})</button>;
}

/** Upload files: choose them here, or drop them anywhere on the page. */
function UploadFiles() {
  const pick = useRef(/** @type {HTMLInputElement | null} */ (null));
  return <>
    <button type="button" class="btn" data-irpick="1" title={`Drop files anywhere on this page: ${IR_UPLOAD_TYPES.join(" ")}, up to 25 MB each`} onClick={() => pick.current && pick.current.click()}>Upload files</button>
    <input type="file" ref={pick} multiple hidden accept={IR_UPLOAD_TYPES.join(",")} aria-label="Choose transcripts or minutes to add"
      onChange={e => { const el = /** @type {HTMLInputElement} */ (e.currentTarget); irAddFiles([...(el.files || [])]); el.value = ""; }} />
  </>;
}

/** The Not needed reasons menu, under the button that opened it. */
function AsideMenu() {
  const a = irAside.value, box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const close = (/** @type {boolean} */ back) => { const was = irAside.value; irAside.value = null; if (back && was && was.anchor && was.anchor.isConnected) was.anchor.focus({ preventScroll: true }); };
  useLayoutEffect(() => {
    const el = box.current; if (!a || !el) return;
    const r = a.anchor && a.anchor.isConnected ? a.anchor.getBoundingClientRect() : { left: innerWidth / 2, right: innerWidth / 2, bottom: innerHeight / 3, top: innerHeight / 3 };
    const w = el.offsetWidth, h = el.offsetHeight;
    let top = r.bottom + 4; if (top + h > innerHeight - 8) top = Math.max(8, r.top - h - 4);
    el.style.top = `${Math.max(8, Math.min(top, innerHeight - h - 8))}px`; el.style.left = `${Math.max(8, Math.min(r.right - w, innerWidth - w - 8))}px`;
    /** @type {HTMLElement | undefined} */ (menuItemsIn(el)[0])?.focus({ preventScroll: true });
  }, [a]);
  if (!a) return null;
  const m = irModel().meetings.find((/** @type {any} */ x) => x.id === a.id);
  if (!m) return null;
  const pick = (/** @type {string} */ reason) => { close(false); irNotNeeded(m, reason); };
  return (
    <MenuPanel bare cls="rvreason rjmenu" id="irAside" label="Not needed because" boxRef={box} anchor={a.anchor} onClose={how => close(how === "esc")} onKey={e => {
      if (/^[1-4]$/.test(e.key) && !e.metaKey && !e.ctrlKey && !e.altKey) { e.preventDefault(); e.stopPropagation(); pick(IR_REASONS[+e.key - 1]); }
    }} autoFocus={false}>
      <div class="rjh" aria-hidden="true">Not needed because</div>
      {IR_REASONS.map((r, i) => (
        <button type="button" role="menuitem" data-reason={r} onClick={() => pick(r)}><span>{r}</span><span class="kbd" aria-hidden="true">{i + 1}</span></button>
      ))}
    </MenuPanel>
  );
}

function IntakeReviewView() {
  const tick = irTick.value;   /* read for real: a bare `irTick.value;` is dropped by the bundler and nothing would redraw */
  const model = irModel(), c = irLiveCounts(), view = irView.value;
  const list = irFiltered(model, irStage.value);
  return (
    <div class="wrapmax irpage" data-irtick={tick}>
      <h1 id="irTitle">Intake and Review</h1>
      <p class="sub" id="irSub" style={{ margin: "4px 0 0" }}>{c.ready} ready to process · {irPlural(c.to_approve, "proposal")} to approve</p>
      <div class="toolbar rvtools">
        <ProcessAll />
        <UploadFiles />
        <span class="sp"></span>
        <span class="seg" role="group" aria-label="How you see Intake and Review">
          {IR_VIEWS.map(([v, l]) => (
            <button type="button" data-irview={v} aria-pressed={view === v} title={l} onClick={() => irSetView(v)}>
              <svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">{VIEWICON[/** @type {keyof VIEWICON} */ (v)]}</svg>
              <span style={{ marginLeft: "6px" }}>{l}</span>
            </button>
          ))}
        </span>
      </div>
      {view === "board" ? <BoardView model={model} /> : view === "two" ? <TwoPanes model={model} list={model.meetings} /> : <><StagePipe c={c} /><ListView model={model} list={list} /></>}
      <FoldSection sec="later" title="Later" n={model.later.length}>
        {model.later.length ? <ul class="irlist">{model.later.map(x => <li data-irkey={x.key}>{x.title}{x.day ? <span class="sub"> · {fd(x.day)}{x.start ? ` ${x.start}` : ""}</span> : null} <button type="button" class="linkbtn" data-ira="restore" onClick={() => irRestore([x.key])}>Restore</button></li>)}</ul> : <div class="empty">Nothing set aside for later. A meeting comes back here when its transcript arrives.</div>}
      </FoldSection>
      <FoldSection sec="not_needed" title="Not needed" n={model.not_needed.length}>
        {model.not_needed.length ? <ul class="irlist">{model.not_needed.map(x => <li data-irkey={x.key}>{x.title}{x.day ? <span class="sub"> · {fd(x.day)}{x.start ? ` ${x.start}` : ""}</span> : null}{x.reason ? <span class="sub"> · {x.reason}</span> : null}{x.note ? <span class="sub"> · {x.note}</span> : null} <button type="button" class="linkbtn" data-ira="restore" onClick={() => irRestore([x.key])}>Restore</button></li>)}</ul> : <div class="empty">Nothing marked Not needed.</div>}
      </FoldSection>
      <AsideMenu />
      <p class="sub irold">While this page is being built, the earlier pages are here: <a href="#" data-go="inbox">Intake</a> · <a href="#" data-go="review">Review</a></p>
    </div>
  );
}

let irMounted = false;
/** go()'s renderer for Intake and Review. */
export function renderIntakeReview() {
  const el = $("#v-intake-review");
  if (!el) return;
  irAfterData();
  if (!irMounted) { render(<IntakeReviewView />, el); irMounted = true; bootIrKeys(); bootIrDrop(); }
}

/* Keyboard: up and down move between meetings; Enter processes the one with focus when its transcript is ready and otherwise opens
   or closes it (232-A); N asks why it is Not needed and H sets it aside for Later (232-A; here, not in core/keys.js); Esc closes the
   peek and then the open meeting. The Review side's keys (232-B) are core/keys.js's. */
function bootIrKeys() {
  document.addEventListener("keydown", e => {
    if (shared.VIEW !== "intake-review" || e.metaKey || e.ctrlKey || e.altKey) return;
    const t = /** @type {HTMLElement} */ (e.target);
    if (t && t.closest && t.closest("input,textarea,select,[contenteditable=true],[role=menu]")) return;
    const rows = /** @type {HTMLElement[]} */ ([...document.querySelectorAll("#v-intake-review [data-irm]")]);
    const rowEl = /** @type {HTMLElement | null} */ (t.closest ? t.closest("[data-irm]") : null), at = rows.indexOf(/** @type {HTMLElement} */ (rowEl));
    const m = at >= 0 ? irModel().meetings.find((/** @type {any} */ x) => x.id === rows[at].dataset.irm) : null;
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (!rows.length) return; e.preventDefault();
      const r = rows[Math.max(0, Math.min(rows.length - 1, at < 0 ? 0 : at + (e.key === "ArrowDown" ? 1 : -1)))];
      r.focus(); irSel.value = r.dataset.irm || null; return;
    }
    /* N is also the page's note key (core/keys.js): on a meeting this listener runs first (capture) and keeps it */
    const mine = () => { e.preventDefault(); e.stopImmediatePropagation(); };
    if (e.key === "Enter" && m && !(t.closest && t.closest("button,a"))) { mine(); if (irCanProcess(m)) irProcess(m); else irClickMeeting(m.id); return; }
    if ((e.key === "n" || e.key === "N") && !e.shiftKey && m && irCanSetAside(m)) { mine(); irAskReason(m, rowEl); return; }
    if ((e.key === "h" || e.key === "H") && !e.shiftKey && m && irCanSetAside(m)) { mine(); irLater(m); return; }
    if (e.key === "Escape" && (irPeek.value != null || irOpen.value)) { const s = irEsc({ peek: irPeek.value, open: irOpen.value }); irPeek.value = s.peek; irOpen.value = s.open; }
  }, true);
}

/* Upload files: a file dropped anywhere on the page becomes a row (the drop target is the whole view, not a zone). */
function bootIrDrop() {
  const over = (/** @type {boolean} */ on) => { const el = $("#v-intake-review"); if (el) el.classList.toggle("irdrop", on); };
  const files = (/** @type {DragEvent} */ e) => e.dataTransfer && [...e.dataTransfer.types].includes("Files");
  const inChat = (/** @type {Event} */ e) => e.target instanceof Element && !!e.target.closest("#chat");
  document.addEventListener("dragover", e => { if (shared.VIEW === "intake-review" && files(e)) { if (inChat(e)) over(false); else { e.preventDefault(); over(true); } } });
  document.addEventListener("dragleave", e => { if (shared.VIEW === "intake-review" && !e.relatedTarget) over(false); });
  document.addEventListener("drop", e => {
    if (shared.VIEW !== "intake-review") return;
    over(false);
    /* a drop the ask panel (or anything else) already took is not ours: the panel attaches its own images */
    if (e.defaultPrevented || inChat(e)) return;
    const list = e.dataTransfer ? [...e.dataTransfer.files] : [];
    if (!list.length) return;
    e.preventDefault(); irAddFiles(list);
  });
}

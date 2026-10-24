// @ts-check
/* PrepPopup (BL-286 parts A and B): the top of the Prep popup, the header and the one toolbar, and the facts line and
   invite above its lists. The lists themselves (open actions, risks and issues, decisions, early warnings, recent reports)
   are still drawn by drawPrep() into #prepBody, in two columns; old code never writes into the containers mounted here. */
import { render } from "preact";
import { useEffect, useRef, useState } from "preact/hooks";
import { cardGroup, hoverAttach } from "../../core/hover.js";
import { loadPeek, peeks } from "../../stores/prepPopup.js";
import { PrepFacts } from "./PrepFacts.jsx";
import { PrepHead } from "./PrepHead.jsx";
import { PrepToolbar } from "./PrepToolbar.jsx";

export function PrepPopup() {
  return (
    <>
      <PrepHead />
      <PrepToolbar />
    </>
  );
}

/** Mount the popup's components once, into the dialog's #prepTop and #prepLead.
    @param {Element} top @param {Element} lead */
export function mountPrepPopup(top, lead) {
  render(<PrepPopup />, top);
  render(<PrepFacts />, lead);
}

/* ===== The Prep peek (#111 piece B) ===== */

/** One hover peek, on the shared card group (core/hover.js: CARD_OPEN to open, CARD_CLOSE to close, focus at once, Esc to close).
    Returns the refs to put on the trigger and on the peek, and whether it shows. The peek stays inside `wrap`, so focus moving
    from the trigger into it keeps it open and focus leaving both closes it.
    @param {boolean} [on] false while the trigger is not drawn
    @returns {{open: boolean, trigger: import("preact").RefObject<HTMLElement>, panel: import("preact").RefObject<HTMLElement>,
      shut: (refocus?: boolean) => void, onFocusOut: (e: FocusEvent) => void}} */
export function usePeek(on = true) {
  const [open, setOpen] = useState(false), trigger = useRef(/** @type {HTMLElement | null} */ (null)), panel = useRef(/** @type {HTMLElement | null} */ (null));
  const shown = useRef(false);
  shown.current = open;
  useEffect(() => {
    const t = trigger.current;
    if (!on || !t) return undefined;
    return hoverAttach(t, { group: cardGroup, open: () => setOpen(true), close: () => setOpen(false), panel: () => panel.current, isOpen: () => shown.current });
  }, [on]);
  /** @param {boolean} [refocus] */
  const shut = refocus => { cardGroup.close(); setOpen(false); if (refocus && trigger.current) trigger.current.focus(); };
  /** @param {FocusEvent} e */
  const onFocusOut = e => {
    const to = /** @type {Node | null} */ (e.relatedTarget);
    if (to && ((trigger.current && trigger.current.contains(to)) || (panel.current && panel.current.contains(to)))) return;
    if (to) setOpen(false);                       // focus went elsewhere in the page; a window blur (no target) keeps it
  };
  return { open, trigger, panel, shut, onFocusOut };
}

/** @typedef {{mkey: string, day: string, title: string, bits: string[], plan?: string | null, page?: string | null, pageWhen?: string,
    live: boolean, id: string, panel: import("preact").Ref<HTMLElement>, onEsc: () => void, open: (path: string) => void}} PeekProps */

/** A labelled block of the peek. @param {{label: string, children: any}} props */
const Block = ({ label, children }) => <div class="pkb"><div class="pkl">{label}</div>{children}</div>;

/** The peek: the 30-second version of the prep page (#111 C, Alan's pick of a quick peek then the page). Title, when, who; your aim,
    the three things to raise, the ask, since last time; then Open the prep page. Read only, Internal, never sent.
    @param {PeekProps} p */
export function PrepPeek(p) {
  const { mkey: key, day, title, bits, plan, page, pageWhen, live, id } = p;
  const dated = /^\d{4}-\d{2}-\d{2}\|/.test(key) ? key : `${day}|${key}`;
  useEffect(() => { loadPeek(dated); }, [dated]);
  const pk = peeks.value[dated], L = pk && pk.lines, off = live ? undefined : "creaite isn’t running";
  return (
    <div class="dmpop prpeek" role="dialog" id={id} ref={/** @type {any} */ (p.panel)} aria-label={`Prep peek for ${title}`}
      onKeyDown={e => { if (e.key === "Escape") { e.stopPropagation(); p.onEsc(); } }}>
      <h4>{title}</h4>
      <div class="pm">{bits.join(" · ")}</div>
      {!pk ? <p class="sub" role="status">Reading the prep…</p> : null}
      {L && L.aim ? <Block label="Your aim"><div class="pkt">{L.aim}</div></Block> : null}
      {L && L.raise.length ? <Block label={L.shaped ? "Raise" : "In play"}><ul class="pkul">{L.raise.map(r => <li>{r}</li>)}</ul></Block> : null}
      {L && L.ask ? <Block label="Ask"><div class="pkt">{L.ask}</div></Block> : null}
      {L && L.since ? <Block label="Since last time"><div class="sub">{L.since}</div></Block> : null}
      {L && !L.shaped && !L.confidential ? <p class="sub agnone">Not shaped yet. Open the prep page to set your aim.</p> : null}
      {plan ? <p class="sub agnone">Worth preparing: {plan}</p> : null}
      {pk && !L ? <p class="sub agnone">{live ? "The peek couldn't be read. The prep page may still open." : "The peek needs creaite to be running."}</p> : null}
      {page ? <div class="agsaved"><span class="agok" aria-hidden="true">✓</span>
        <span class="agw"><b>Agenda saved</b><small>Prep page made {pageWhen || ""}</small></span></div> : null}
      <div class="agrow">
        <button type="button" class="btn primary" data-prepgo={key} data-prepgoday={day} aria-label={`Open the prep page for ${title}`}
          aria-disabled={live ? undefined : "true"} data-tip={off}>Open the prep page</button>
        {page ? <button type="button" class="linkbtn" aria-disabled={live ? undefined : "true"} data-tip={off || "Open the saved agenda in a new tab"}
          onClick={() => p.open(page)}>Open the file</button> : null}
      </div>
    </div>
  );
}

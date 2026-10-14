// @ts-check
/* ToDecide (BL-319, v1.9.2): the first section after Today's day band. What waits for Alan's say-so, newest first: proposals
   in Review, transcripts ready in Intake, and messages from people he follows (BL-288: never labelled; the row says
   "Message"). The top five show; "+n more" (a [data-more] button, today.js's handler) opens the rest in place; then "Open Review (n)".
   Each row: its kind as a quiet tag, the title (a proposal opens highlighted in Review, a transcript opens Intake, a message
   opens in Outlook or Teams), one line of where it is from, and its icon actions (IconButton), calm until the row is pointed
   at or tabbed into. today.js builds the rows (toDecideRows) and does the actions (tdAct); this only draws them.
   Approve and save is offered only for what may be approved on its own row: never minutes, a report, a file change, a new
   decision, a new risk or any other one-at-a-time item, nor one that needs a project or has a conflict. Those get
   "Open in Review" instead (the bulk rule, FR-81). A message's two actions keep BL-296's data-alertdo buttons, so the
   page-wide handler in settings.js runs them, with their Undo.
   BL-334: a message row is a conversation's card: its summary, then each candidate item (a quiet tag for its type, the item,
   its owner and due date) with Create work item and Dismiss (the same data-alertdo buttons, naming the item). A conversation
   with nothing for Alan is a quiet row (td-quiet): one line, no buttons. */
import { render } from "preact";
import { IconButton } from "../IconButton.jsx";

/** @typedef {{id: string, icon: string, label: string, name?: string, primary?: boolean, why?: string, data?: Record<string, string>, haspopup?: string}} TdAct */
/** @typedef {{key: string, tag: string, t: string, sub?: string, acts: TdAct[]}} TdCand */
/** @typedef {{key: string, kind: "review"|"transcript"|"message"|"quiet", tag: string, tone?: string, t: string, meta: string, link?: string,
    summary?: string, cands?: TdCand[], acts: TdAct[]}} TdRow */
/** @typedef {{rows: TdRow[], total: number, cap: number, open: boolean, onAct: (row: TdRow, act: TdAct, btn: HTMLElement) => void,
    onOpen: (row: TdRow) => void, onReview: () => void, blocked: (why: string) => void}} ToDecideProps */

/** One row. @param {{r: TdRow, hidden: boolean, p: ToDecideProps}} props */
function TdLine({ r, hidden, p }) {
  /** @param {MouseEvent} e */
  const open = e => { e.preventDefault(); p.onOpen(r); };
  /** @param {TdAct[]} list */
  const acts = list => list.map(a => (
    <IconButton key={a.id} icon={a.icon} label={a.label} name={a.name} primary={a.primary} why={a.why} haspopup={a.haspopup}
      data={{ tdact: a.id, ...(a.data || {}) }} onBlocked={() => p.blocked(a.why || "")}
      onClick={a.data && a.data.alertdo ? undefined : e => p.onAct(r, a, /** @type {HTMLElement} */ (e.currentTarget))} />
  ));
  return (
    <li class={`tdrow td-${r.kind}`} data-td={r.key} hidden={hidden}>
      {r.tag ? <span class={`tag tdtag${r.tone ? " " + r.tone : ""}`}>{r.tag}</span> : null}
      <div class="tb">
        {r.kind === "quiet"
          ? <span class="t">{r.t}</span>
          : r.link
            ? <a class="t" href={r.link} target="_blank" rel="noopener">{r.t}</a>
            : <a class="t" href="#" onClick={open}>{r.t}</a>}
        <p>{r.meta}</p>
        {r.summary ? <p class="tdsum">{r.summary}</p> : null}
        {r.cands && r.cands.length
          ? <ul class="tdcands" aria-label="What it came to">
              {r.cands.map(c => (
                <li class="tdcand" key={c.key} data-tdc={c.key}>
                  <span class="tag tdctag">{c.tag}</span>
                  <span class="ct">{c.t}{c.sub ? <span class="cs">{` · ${c.sub}`}</span> : null}</span>
                  <span class="tacts">{acts(c.acts)}</span>
                </li>
              ))}
            </ul>
          : null}
      </div>
      {r.acts.length ? <span class="tacts">{acts(r.acts)}</span> : null}
    </li>
  );
}

/** The list and its foot. @param {ToDecideProps} props */
export function ToDecide(props) {
  const { rows, total, cap, open, onReview } = props, more = rows.length - cap;
  /** @param {MouseEvent} e */
  const review = e => { e.preventDefault(); onReview(); };
  return (
    <>
      <ol class="bl tdlist" id="tdList" aria-labelledby="hTd">
        {rows.map((r, i) => <TdLine key={r.key} r={r} hidden={!open && i >= cap} p={props} />)}
      </ol>
      <div class="moreline tdfoot">
        {more > 0 ? <><button type="button" class="qa" aria-expanded={open ? "true" : "false"} data-more="td">{open ? "Show fewer" : `+${more} more`}</button>{" · "}</> : null}
        {total ? <a href="#" class="s" id="tdReview" onClick={review}>{`Open Review (${total})`}</a> : <span class="none">Nothing waits in Review.</span>}
      </div>
    </>
  );
}

/** Draw To decide into #tdBody (only today.js calls it). @param {Element} host @param {ToDecideProps} props */
export function drawToDecide(host, props) {
  render(<ToDecide {...props} />, host);
}

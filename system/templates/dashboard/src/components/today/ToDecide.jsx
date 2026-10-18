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
   with nothing for Alan is a quiet row (td-quiet): one line, no buttons. A confidential conversation's card carries a quiet
   "Confidential" mark beside its title (the candidate tag's style); its summary shows like any other (Alan, 15-10-2026).
   BL-342 Part 3 B: a card whose matched action looks done says why in one quiet line; once its close is staged, "Staged for
   Review" with Undo (a data-alertdo button, run by settings.js).
   BL-342 Part 5: Alan's own promises in the thread, one line each ("You promised Sara Example: ...") with Add a promise and
   Dismiss, then "Staged for Review" with Undo; and a promise that looks kept, said in one quiet line like a close. */
import { render } from "preact";
import { IconButton } from "../IconButton.jsx";
import { LINK_REL, linkUrl } from "../../core/linkUrl.js";

/** @typedef {{id: string, icon: string, label: string, name?: string, primary?: boolean, why?: string, data?: Record<string, string>, haspopup?: string}} TdAct */
/** @typedef {{key: string, tag: string, t: string, sub?: string, acts: TdAct[]}} TdCand */
/** @typedef {{key: string, pkey: string, card: string, tag: string, t: string, sub?: string, staged?: boolean, acts: TdAct[]}} TdProm */
/** @typedef {{key: string, kind: "review"|"transcript"|"message"|"quiet", tag: string, tone?: string, t: string, meta: string, link?: string,
    mark?: string, summary?: string, cands?: TdCand[], acts: TdAct[], ask?: string, due?: string, overdue?: boolean, dueText?: string,
    owners?: string, files?: string, rel?: string, relId?: string, relT?: string, relWhy?: string, count?: string,
    closeWhy?: string, closeStaged?: string, closeCard?: string, proms?: TdProm[], keptWhy?: string, keptStaged?: string,
    keptCard?: string}} TdRow */
/** @typedef {{key: string, n: number, text: string, go: string}} TdPart */
/** @typedef {{rows: TdRow[], line?: TdPart[], total: number, cap: number, open: boolean, onAct: (row: TdRow, act: TdAct, btn: HTMLElement) => void,
    onOpen: (row: TdRow) => void, onReview: () => void, onGo?: (page: string) => void, blocked: (why: string) => void}} ToDecideProps */

/** One row. @param {{r: TdRow, hidden: boolean, p: ToDecideProps}} props */
function TdLine({ r, hidden, p }) {
  /** @param {MouseEvent} e */
  const open = e => { e.preventDefault(); p.onOpen(r); };
  /** a message's address from mail or Teams: only what core/linkUrl.js accepts is a link (#159) */
  const href = linkUrl(r.link);
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
          : href
            ? <a class="t" href={href} target="_blank" rel={LINK_REL}>{r.t}</a>
            : <a class="t" href="#" onClick={open}>{r.t}</a>}
        {r.mark ? <>{" "}<span class="tag tdctag tdmark">{r.mark}</span></> : null}
        <p>{r.meta}</p>
        {r.summary ? <p class="tdsum">{r.summary}</p> : null}
        {r.rel ? (
          <p class="tdrel">
            <span class={`tag tdctag tdrelchip tdrel-${r.rel.toLowerCase()}`}>{r.rel}</span>
            {r.relId ? <>{" "}<span class="tdrelitem">{r.relId}{r.relT ? `: ${r.relT}` : ""}</span></> : null}
            {r.count ? <>{" "}<span class="tag tdctag tdcount">{r.count}</span></> : null}
            {r.relWhy ? <span class="tdwhy">{r.relWhy}</span> : null}
          </p>
        ) : null}
        {r.closeWhy ? <p class="tdwhy tddone">{r.closeWhy}</p> : null}
        {r.closeStaged ? (
          <p class="tdstaged">{`Close of ${r.closeStaged}: Staged for Review`}{" · "}
            <button type="button" class="qa" data-alertdo="closeundo" data-id={r.closeCard}
              aria-label={`Undo the staged close of ${r.closeStaged}`}>Undo</button></p>
        ) : null}
        {r.keptWhy ? <p class="tdwhy tddone">{r.keptWhy}</p> : null}
        {r.keptStaged ? (
          <p class="tdstaged">{`${r.keptStaged} kept: Staged for Review`}{" · "}
            <button type="button" class="qa" data-alertdo="keptundo" data-id={r.keptCard}
              aria-label={`Undo ${r.keptStaged} kept`}>Undo</button></p>
        ) : null}
        {r.ask ? <p class="tdask"><span class="tdlab">Ask</span>{" "}{r.ask}</p> : null}
        {r.owners || r.dueText ? (
          <p class="tdwho">
            {r.owners ? <><span class="tdlab">For</span>{" "}{r.owners}</> : null}
            {r.dueText ? <>{r.owners ? " · " : ""}<span class={r.overdue ? "tdover" : "tddue"}>{r.overdue ? `overdue, ${r.dueText}` : r.dueText}</span></> : null}
          </p>
        ) : null}
        {r.files ? <p class="tdfiles">{r.files}</p> : null}
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
        {r.proms && r.proms.length
          ? <ul class="tdcands tdproms" aria-label="Your promises">
              {r.proms.map(c => (
                <li class="tdcand" key={c.key} data-tdc={c.key}>
                  <span class="tag tdctag">{c.tag}</span>
                  <span class="ct">{c.t}{c.sub ? <span class="cs">{` · ${c.sub}`}</span> : null}</span>
                  {c.staged
                    ? <span class="tdstaged">{"Staged for Review · "}
                        <button type="button" class="qa" data-alertdo="promiseundo" data-id={c.card}
                          data-pkey={c.pkey} aria-label={`Undo the promise: ${c.t}`}>Undo</button></span>
                    : <span class="tacts">{acts(c.acts)}</span>}
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
  const line = props.line || [];
  /** @param {string} page @param {MouseEvent} e */
  const go = (page, e) => { e.preventDefault(); if (props.onGo) props.onGo(page); else onReview(); };
  return (
    <>
      {line.length ? (
        <p class="tdline" id="tdLine">
          {line.map((x, i) => (
            <>{i ? (i === line.length - 1 ? " and " : ", ") : ""}<a href="#" class="s" data-tdline={x.key} onClick={e => go(x.go, e)}>{x.text}</a></>
          ))}
        </p>
      ) : null}
      <ol class="bl tdlist" id="tdList" aria-labelledby="hTd">
        {rows.map((r, i) => <TdLine key={r.key} r={r} hidden={!open && i >= cap} p={props} />)}
      </ol>
      <div class="moreline tdfoot">
        {more > 0 ? <><button type="button" class="qa" aria-expanded={open ? "true" : "false"} data-more="td">{open ? "Show fewer" : `+${more} more`}</button>{" · "}</> : null}
        {line.length || !rows.length ? null : <span class="none">Nothing waits in Review.</span>}
      </div>
    </>
  );
}

/** Draw Intake and Review (was To decide) into #tdBody (only today.js calls it). @param {Element} host @param {ToDecideProps} props */
export function drawToDecide(host, props) {
  render(<ToDecide {...props} />, host);
}

// @ts-check
/* TranscriptPane (v2.1.0 P7, BL-338 point 4): the transcript beside the minutes, as speaker turns with their times (P4's
   minutes_record.turns: VTT cue times, else the speaker turns). Searchable (the words found are marked, with a count, and Enter
   goes to the next turn that has them) and closable. A time tag on the minutes (jumpTo) scrolls the pane to the turn that was
   said then and highlights it; the pane's own scroller moves, never the page. Read only: nothing here changes the transcript. */
import { useEffect, useRef } from "preact/hooks";
import { IconButton } from "../IconButton.jsx";
import { minutesView, paneOpen, paneQuery, paneTurn } from "../../stores/minutes.js";

/** Scroll the pane to a turn and highlight it (a time tag's click). @param {number} turn */
export function jumpTo(turn) {
  paneOpen.value = true;
  paneTurn.value = null;                                   // the same turn again still scrolls and flashes
  queueMicrotask(() => { paneTurn.value = turn; });
}

/** A turn's words with what was searched for marked. @param {{text: string, q: string}} props */
function Marked({ text, q }) {
  if (!q) return <span>{text}</span>;
  const out = [], low = text.toLowerCase(), k = q.toLowerCase();
  let i = 0, j = low.indexOf(k);
  while (j >= 0) { out.push(text.slice(i, j)); out.push(<mark key={j}>{text.slice(j, j + k.length)}</mark>); i = j + k.length; j = low.indexOf(k, i); }
  out.push(text.slice(i));
  return <span>{out}</span>;
}

/** The pane. */
export function TranscriptPane() {
  const list = useRef(/** @type {HTMLOListElement|null} */ (null));
  const v = minutesView.value, tr = (v && v.turns) || { timed: false, turns: [] };
  const q = paneQuery.value.trim(), on = paneTurn.value;
  const hits = q ? tr.turns.filter(t => t.text.toLowerCase().includes(q.toLowerCase()) || String(t.who || "").toLowerCase().includes(q.toLowerCase())) : [];
  useEffect(() => {
    const ol = list.current, li = ol && on != null ? /** @type {HTMLElement|null} */ (ol.querySelector(`[data-turn="${on}"]`)) : null;
    if (ol && li) ol.scrollTop = li.offsetTop - ol.offsetTop - ol.clientHeight / 3;
  }, [on, paneOpen.value]);
  if (!paneOpen.value) return null;
  const next = () => { if (!hits.length) return; const after = hits.find(t => on == null || t.n > on) || hits[0]; paneTurn.value = after.n; };
  return (
    <aside class="mnpane" aria-labelledby="mnPaneH">
      <div class="mnpane-h">
        <h2 id="mnPaneH">Transcript</h2>
        <IconButton icon="x" label="Close the transcript" onClick={() => { paneOpen.value = false; }} data={{ mnpane: "close" }} />
      </div>
      <div class="mnpane-q">
        <input type="search" class="pkdt" id="mnPaneQ" aria-label="Search the transcript" placeholder="Search the transcript" value={paneQuery.value}
          onInput={e => { paneQuery.value = /** @type {HTMLInputElement} */ (e.currentTarget).value; }}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); next(); } }} />
        <span class="sub" role="status">{q ? `${hits.length} turn${hits.length === 1 ? "" : "s"}` : tr.turns.length ? `${tr.turns.length} turns` : ""}</span>
      </div>
      {tr.turns.length ? (
        <ol class="mnturns" ref={list} tabIndex={0} aria-label="Speaker turns">
          {tr.turns.map(t => (
            <li key={t.n} data-turn={t.n} class={`${t.n === on ? "on" : ""}${q && !hits.includes(t) ? " dim" : ""}`} aria-current={t.n === on ? "true" : undefined}>
              <span class="mnwho">{t.who || "Someone"}{t.start ? <span class="mntime"> · {t.start}</span> : null}</span>
              <Marked text={t.text} q={q} />
            </li>
          ))}
        </ol>
      ) : <p class="sub mnpane-none">No transcript was kept with these minutes.</p>}
    </aside>
  );
}

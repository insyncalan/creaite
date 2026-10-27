// @ts-check
/* ShareReview (#329; Alan, 27-10-2026): "Review these lines before sharing". A Shareable export or follow-up email that the server
   refused because a line may describe something kept out of the shareable version (minutes_record.describing_lines) opens this
   box: each line, the item it may describe, and its answers by kind (ANSWERS): a line or a row, Hold back with it (left out while
   its item is) or Keep (it stays until its words change); a heading or the title, Use a plain heading or Keep; a line of the
   meeting's details (or the project's name), Keep only, with a note to change it before sharing. Export again saves the answers (one change, /api/minutes/save op
   "shareable") and tries again; Cancel makes nothing. The server checks again, so nothing is shared until every line is answered.
   The classes are the approve popup's. */
import { signal } from "@preact/signals";
import { Dialog } from "../Dialog.jsx";
import { changeMinutes } from "../../stores/minutes.js";

/** @typedef {{key: string, kind?: string, text: string, item: string, ref: string, refs?: string[]}} ReviewLine */

/** The answers each kind of line takes, as [answer, button label] (minutes_record.ANSWERS_OF; the server checks them again). */
const ANSWERS = /** @type {Record<string, [string, string][]>} */ ({
  line: [["hold", "Hold back with it"], ["keep", "Keep"]], row: [["hold", "Hold back with it"], ["keep", "Keep"]],
  heading: [["plain", "Use a plain heading"], ["keep", "Keep"]], title: [["plain", "Use a plain title"], ["keep", "Keep"]],
  header: [["keep", "Keep"]] });
/** What a line is, in words, before it. */
const WHAT = /** @type {Record<string, string>} */ ({ row: "A row", heading: "A heading", title: "The title", header: "The meeting's details" });

/** The box's state: the lines, the answers so far ({key: "hold" | "keep"}), what to do again, and a refusal in words. */
export const shareAsk = /** @type {import("@preact/signals").Signal<{lines: ReviewLine[], answers: Record<string, string>, again: () => void, error: string}|null>} */ (signal(null));

/** Open the box for a refused Shareable copy. @param {ReviewLine[]} lines @param {() => void} again */
export function askShare(lines, again) { shareAsk.value = { lines: lines || [], answers: {}, again, error: "" }; }

const close = () => { shareAsk.value = null; };

/** One answer. @param {string} key @param {string} what */
function answer(key, what) {
  const a = shareAsk.value;
  if (a) shareAsk.value = { ...a, answers: { ...a.answers, [key]: what }, error: "" };
}

/** Export again: the answers saved, then the same export. */
async function exportAgain() {
  const a = shareAsk.value;
  if (!a) return;
  const answers = a.lines.map(l => ({ key: l.key, ref: l.ref, refs: l.refs || [l.ref], answer: a.answers[l.key] }));
  const r = await changeMinutes({ op: "shareable", answers });
  if (!r.ok) { shareAsk.value = { ...a, error: r.message || "Your answers weren't saved." }; return; }
  close();
  a.again();
}

/** The box. */
export function ShareReview() {
  const a = shareAsk.value, done = !!a && a.lines.every(l => a.answers[l.key]);
  return (
    <Dialog open={!!a} onClose={close} labelledBy="mnShareH" id="mnShare" class="mnapprove" focus="#mnShareHold0">
      {a ? <div class="mnap">
        <h2 id="mnShareH">Review these lines before sharing</h2>
        <p class="sub">These lines may describe something kept out of the shareable version.</p>
        <ul class="mnap-l">{a.lines.map((l, i) => <li key={l.key} data-share-key={l.key} style="display:block">
          <div>{l.text}</div>
          <div class="sub">{WHAT[l.kind || ""] ? `${WHAT[l.kind || ""]}. ` : ""}May describe: {l.item}</div>
          {l.kind === "header" ? <div class="sub">This can't be held back: change it in the minutes before sharing if it shouldn't go out.</div> : null}
          <div role="group" aria-label={`For the line: ${l.text.slice(0, 60)}`} style="display:flex;gap:6px;margin-top:6px">
            {(ANSWERS[l.kind || "line"] || ANSWERS.line).map(([what, label], j) => <button type="button" class="btn sm" key={what} id={j ? undefined : `mnShareHold${i}`}
              data-share={what} aria-pressed={a.answers[l.key] === what ? "true" : "false"} onClick={() => answer(l.key, what)}>{label}</button>)}
          </div>
        </li>)}</ul>
        {a.error ? <p class="sub" role="alert" style="color:var(--bad, #b00020)">{a.error}</p> : null}
        <div class="mnap-foot">
          <button type="button" class="btn" id="mnShareNo" onClick={close}>Cancel</button>
          <button type="button" class="btn primary" id="mnShareGo" disabled={!done} data-tip={done ? undefined : "Answer each line first"}
            onClick={() => { exportAgain(); }}>Export again</button>
        </div>
      </div> : null}
    </Dialog>
  );
}

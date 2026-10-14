// @ts-check
/* RejectsList (BL-315): Activity › Quality › What you rejected. The latest rejects, newest first (POST /api/review/rejects),
   each with the chip Review's rejected rows have ("Rejected · Chatter", which reopens the reasons menu to change it),
   Approve instead (the reject undone and the item approved in one step; minutes, new decisions and new risks go back to
   Review for their own approval) and Undo (back in Review, waiting). A list of rows; every control is a button with its
   full name. Text only through JSX. */
import { render } from "preact";
import { rjRecent } from "../../stores/rejects.js";

/** @typedef {import("../../stores/rejects.js").RjRecent} RecentReject */
/** @typedef {{onReason: (r: RecentReject, el: HTMLElement) => void, onApprove: (r: RecentReject) => void, onUndo: (r: RecentReject) => void,
      name: (code: string) => string, when: (at: string) => string}} RejectsListProps */

/** @param {RejectsListProps} props */
export function RejectsList({ onReason, onApprove, onUndo, name, when }) {
  const { state, items, message } = rjRecent.value;
  if (state === "idle") return null;                     /* read when Quality opens */
  if (state === "off") return <p class="sub" id="rjListMsg">What you rejected needs the live server.</p>;
  if (state === "error") return <p class="sub" id="rjListMsg">{message || "The list couldn't be read."}</p>;
  if (state === "loading" && !items.length) return <p class="sub" id="rjListMsg" role="status">Reading what you rejected…</p>;
  if (!items.length) return <p class="sub" id="rjListMsg">Nothing has been rejected.</p>;
  return (
    <ul class="rjlist" aria-label="What you rejected">
      {items.map(r => {
        const reason = r.reason || "No reason", text = r.text || r.key;
        const chip = `Rejected · ${reason}${r.duplicate_of ? ` (${r.duplicate_of})` : ""}`;
        return (
          <li key={r.key} data-rjkey={r.key}>
            <span class="rjt" title={text}>{text.length > 90 ? text.slice(0, 89) + "…" : text}</span>
            <span class="sub rjm">{[r.project ? name(r.project) : "", r.kind || "", r.at ? when(r.at) : ""].filter(Boolean).join(" · ")}</span>
            <span class="rjacts">
              <button type="button" class="tag bad rjchip" data-rjchip={r.key} aria-haspopup="menu" aria-label={`${chip}: change the reason`} title="Change the reason"
                onClick={e => onReason(r, /** @type {HTMLElement} */ (e.currentTarget))}>{chip}</button>
              <button type="button" class="mini ok" data-rjok={r.key} aria-label={`Approve instead: ${text}`} onClick={() => onApprove(r)}>Approve instead</button>
              <button type="button" class="mini" data-rjundo={r.key} aria-label={`Undo the reject: ${text}`} onClick={() => onUndo(r)}>Undo</button>
            </span>
          </li>
        );
      })}
    </ul>
  );
}

/** Mount the list into Activity › Quality's box (BL-315). @param {Element | null} box @param {RejectsListProps} props */
export function mountRejectsList(box, props) { if (box) render(<RejectsList {...props} />, box); }

// @ts-check
/* WeekMenu (#221 H1; mockup: "Menu" week navigation, Round 10): the week's date as one button that opens a list of weeks, each with
   its health dot and the internal and client status, and a box to jump to a date. No arrows. Esc, ↑ ↓ and a click away are
   MenuPanel's. The client status is left out when the project has no client report. */
import { useRef, useState } from "preact/hooks";
import { Icon } from "../../Icon.jsx";
import { MenuPanel } from "../../Menu.jsx";
import { S, fd } from "../../../core/page.js";
import { weekEndingFor } from "./hubLib.js";

/** @typedef {import("./hubLib.js").WeekRow} WeekRow */

const WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

/** @param {{week: string, tone: string, rows: WeekRow[], clientOn: boolean, onPick: (week: string) => void}} props */
export function WeekMenu({ week, tone, rows, clientOn, onPick }) {
  const [open, setOpen] = useState(false);
  const btn = useRef(/** @type {HTMLButtonElement|null} */ (null));
  const close = (/** @type {string} */ how) => { setOpen(false); if (how === "esc" && btn.current) btn.current.focus({ preventScroll: true }); };
  const jump = (/** @type {string} */ typed) => {
    const m = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$/.exec(typed.trim());                        // DD-MM-YYYY as Alan types it; YYYY-MM-DD also works
    const value = m ? `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}` : typed.trim();
    const w = weekEndingFor(value, Math.max(0, WEEK_DAYS.indexOf(String(S.weeklyDay || "Friday"))));
    if (!w) return;
    setOpen(false); onPick(w);
  };
  return (
    <span class="hubwkhost rb-x">
      <button type="button" class="btn hubwkb" id="hubWeek" ref={btn} aria-haspopup="menu" aria-expanded={open ? "true" : "false"}
        data-tip="Choose a week" aria-label={`Week ending ${fd(week)}. Choose a week`} onClick={() => setOpen(!open)}>
        <i class={`wkdot ${tone}`} aria-hidden="true" /><span><span class="wkwords">Week ending </span>{fd(week)}</span><Icon name="chevdown" cls="nch" />
      </button>
      {open ? (
        <MenuPanel label="Weeks" bare cls="wkpop" anchor={btn.current} onClose={close}>
          <h4>Weeks</h4>
          {rows.map(r => (
            <button type="button" role="menuitemradio" tabIndex={-1} key={r.week} class="wkrow" data-w={r.week} aria-checked={r.week === week ? "true" : "false"}
              aria-current={r.week === week ? "true" : undefined} onClick={() => { setOpen(false); onPick(r.week); }}>
              <i class={r.tone} aria-hidden="true" />
              <span>Week ending {fd(r.week)}</span>
              <span class="s">Internal: {r.internal.toLowerCase()}</span>
              {clientOn ? <span class="s">Client: {r.client.toLowerCase()}</span> : null}
            </button>
          ))}
          <h4>Jump to</h4>
          <div class="wkjump">
            <input type="text" id="wkJump" class="pkdt" inputmode="numeric" placeholder="DD-MM-YYYY" aria-label="Week ending date, DD-MM-YYYY" autocomplete="off"
              onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); jump(/** @type {HTMLInputElement} */ (e.currentTarget).value); } }}
              onChange={e => { if (/^\d{4}-\d{2}-\d{2}$/.test(e.currentTarget.value.trim())) jump(e.currentTarget.value); }} />
            <button type="button" class="btn sm" id="wkGo" onClick={e => { const i = /** @type {HTMLInputElement|null} */ (document.getElementById("wkJump")); if (i) jump(i.value); }}>Go</button>
          </div>
        </MenuPanel>
      ) : null}
    </span>
  );
}

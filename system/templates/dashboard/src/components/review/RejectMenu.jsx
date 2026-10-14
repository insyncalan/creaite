// @ts-check
/* RejectMenu (BL-315): the one reasons menu, for one row or many. "Reject n because", then the seven reasons on 1 to 7,
   Use each guess (G) and No reason (0); one key rejects with that reason and Esc closes. Opened from the Review bar's
   Reject with a reason (R), a row's ✕ or ▾, the row's or the peek's menu, and a reject's chip ("Rejected · Chatter", to
   change its reason). A menu (dev/COMPONENTS.md's Menu): the box is the Menu block's MenuPanel (BL-316), so ↑ ↓ Home End
   move, Enter or Space picks, Esc closes and puts focus back on what opened it, Tab or a click away closes. Duplicate with no item named asks
   for the item: the look-alikes creaite finds (BL-297's list), an ID typed, or none. Text only through JSX. */
import { render } from "preact";
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { rjCloseMenu, rjMenu, rjReasons } from "../../stores/rejects.js";
import { menuItemsIn, MenuPanel } from "../Menu.jsx";
const ID = /^[A-Za-z][A-Za-z0-9]{1,6}-(?:[A-Za-z]-)?\d{3,}$/;

/** The open menu, from the store; nothing when none is open. */
export function RejectMenu() {
  const m = rjMenu.value;
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [stage, setStage] = useState(/** @type {"reasons" | "dup"} */ ("reasons"));
  const [cands, setCands] = useState(/** @type {import("../../stores/rejects.js").RjCandidate[] | null} */ (null));
  const [typed, setTyped] = useState("");
  const [bad, setBad] = useState("");
  /* a new menu starts on the reasons */
  useLayoutEffect(() => { setStage("reasons"); setCands(null); setTyped(""); setBad(""); }, [m]);
  /* placed under what opened it, kept in the window; focus to the first choice */
  useLayoutEffect(() => {
    const el = box.current; if (!m || !el) return;
    const r = m.anchor && m.anchor.isConnected ? m.anchor.getBoundingClientRect() : { left: innerWidth / 2, right: innerWidth / 2, bottom: innerHeight / 3, top: innerHeight / 3 };
    const w = el.offsetWidth, h = el.offsetHeight;
    let top = r.bottom + 4; if (top + h > innerHeight - 8) top = Math.max(8, r.top - h - 4);
    el.style.top = `${Math.max(8, Math.min(top, innerHeight - h - 8))}px`; el.style.left = `${Math.max(8, Math.min(r.right - w, innerWidth - w - 8))}px`;   /* set here, so it is visible before focus moves */
    const first = stage === "dup" ? el.querySelector("input") : menuItemsIn(el)[0]; /** @type {HTMLElement | null} */ (first)?.focus({ preventScroll: true });
  }, [m, stage, cands === null]);
  if (!m) return null;

  const n = m.rows.length, reasons = rjReasons.value, guessed = m.rows.filter(r => r.guess).length;
  const one = n === 1 ? m.rows[0] : null, now = one && m.mode === "reason" ? one.reason || "" : null;
  /** the item a Duplicate repeats, when every row names one (their guess, or the reject's own) */
  const dupOf = /** @param {import("../../stores/rejects.js").RjRow} r */ r => r.dup || (r.guess && r.guess.reason === "Duplicate" && r.guess.of) || null;
  /** @param {import("../../stores/rejects.js").RjChoice} c */
  const pick = c => { rjCloseMenu(false); m.onPick(c); };
  /** @param {string | null} reason */
  const choose = reason => {
    if (reason !== "Duplicate") { pick({ reason }); return; }
    const missing = m.rows.filter(r => !dupOf(r));
    if (missing.length !== 1 || !m.candidates) { pick({ reason, dup: n === 1 ? dupOf(m.rows[0]) : null }); return; }
    setStage("dup"); m.candidates().then(L => setCands(L || []), () => setCands([]));
  };
  const useTyped = () => { const id = typed.trim().toUpperCase(); if (!ID.test(id)) { setBad("Type an item ID, like ABC-A-009"); return; } pick({ reason: "Duplicate", dup: id }); };

  /** Its own keys, before the menu's (MenuPanel: ↑ ↓ Home End, Esc, Tab). @param {KeyboardEvent} e */
  const keys = e => {
    const inField = /** @type {HTMLElement} */ (e.target).tagName === "INPUT";
    const stop = () => { e.preventDefault(); e.stopPropagation(); };
    if (e.key === "Escape") { if (stage === "dup") { stop(); setStage("reasons"); } return; }
    if (e.key === "Tab") return;
    if (inField) { if (e.key === "Enter") { stop(); useTyped(); } else if (e.key === "ArrowDown") { stop(); menuItemsIn(box.current)[0]?.focus(); } else e.stopPropagation(); return; }
    if (["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (stage === "reasons") {
      if (/^[1-9]$/.test(e.key) && reasons[+e.key - 1]) { stop(); choose(reasons[+e.key - 1]); return; }
      if ((e.key === "g" || e.key === "G") && guessed) { stop(); pick({ reason: null, guess: true }); return; }
      if (e.key === "0") { stop(); pick({ reason: null }); return; }
    }
    if (e.key !== "Enter" && e.key !== " ") e.stopPropagation();   /* the page's own keys wait while the menu is open */
  };

  const title = m.mode === "reason" ? (n === 1 ? "Rejected because" : `Change the reason for ${n}`) : `Reject ${n === 1 ? "this" : n} because`;
  return (
    <MenuPanel bare cls="rvreason rjmenu" id="rvReason" label={stage === "dup" ? "Duplicate of which item?" : title} boxRef={box}
      anchor={m.anchor} onClose={how => rjCloseMenu(how === "esc")} onKey={keys} autoFocus={false}>
      {stage === "reasons" ? <>
        <div class="rjh" aria-hidden="true">{title}</div>
        {reasons.map((r, i) => (
          <button type="button" role="menuitem" key={r} data-reason={r} aria-current={now === r ? "true" : undefined} onClick={() => choose(r)}>
            <span>{r}{r === "Duplicate" && one && dupOf(one) ? <span class="rjof"> of {dupOf(one)}</span> : null}{now === r ? <span class="rjnow"> · now</span> : null}</span>
            <span class="kbd" aria-hidden="true">{i + 1}</span>
          </button>
        ))}
        <div class="rjsep" role="separator"></div>
        <button type="button" role="menuitem" data-reason="guess" aria-disabled={guessed ? undefined : "true"}
          title={guessed ? (guessed < n ? `${guessed} of ${n} have a guess; the rest are rejected with no reason` : "Each row's own guess") : "creaite has no guess for these"}
          onClick={() => { if (guessed) pick({ reason: null, guess: true }); }}>
          <span>Use each guess{n === 1 && one && one.guess ? <span class="rjof"> ({one.guess.reason})</span> : null}</span><span class="kbd" aria-hidden="true">G</span>
        </button>
        <button type="button" role="menuitem" data-reason="" aria-current={now === "" ? "true" : undefined} onClick={() => pick({ reason: null })}>
          <span>No reason{now === "" ? <span class="rjnow"> · now</span> : null}</span><span class="kbd" aria-hidden="true">0</span>
        </button>
      </> : <>
        <div class="rjh" id="rjDupH">Duplicate of which item?</div>
        {cands === null ? <div class="rjwait sub" role="status">Looking for look-alikes…</div>
          : cands.map(c => (
            <button type="button" role="menuitem" key={c.id} data-dupof={c.id} title={c.t} onClick={() => pick({ reason: "Duplicate", dup: c.id })}>
              <span><b>{c.id}</b> <span class="rjct">{c.t.length > 60 ? c.t.slice(0, 59) + "…" : c.t}</span>{c.strength ? <span class="rjof"> · {c.strength}</span> : null}</span>
            </button>
          ))}
        <div class="rvother">
          <input type="text" id="rjDupId" maxLength={20} placeholder="Or type its ID" aria-label="The item it duplicates, by ID" autocomplete="off"
            value={typed} aria-invalid={bad ? "true" : undefined} aria-describedby={bad ? "rjDupBad" : undefined}
            onInput={e => { setTyped(/** @type {HTMLInputElement} */ (e.currentTarget).value); setBad(""); }} />
          <button type="button" class="mini no" onClick={useTyped}>Reject</button>
        </div>
        {bad ? <div class="rjbad" id="rjDupBad" role="alert">{bad}</div> : null}
        <div class="rjsep" role="separator"></div>
        <button type="button" role="menuitem" data-dupof="" onClick={() => pick({ reason: "Duplicate", dup: null })}><span>Don't name it</span></button>
      </>}
    </MenuPanel>
  );
}

/** Mount the menu once, in its own box at the end of the page (BL-315). */
export function mountRejectMenu() {
  if (document.getElementById("rjMenuHost")) return;
  const host = document.createElement("div"); host.id = "rjMenuHost"; document.body.appendChild(host);
  render(<RejectMenu />, host);
}

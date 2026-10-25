// @ts-check
/* RailMore (BL-319 part 6; #156, #139; #295): the avatar at the foot of the sidebar, where More was, out of the eye line. It is
   an initials circle and the user's name (settings' identity.name, through railName: never a name in code), with a second line:
   "Settings and health" when nothing is wrong, or the first Health problem in plain words, in --bad, with the red count on
   the circle. Expanded (188px): circle, name, second line; collapsed with labels (76px): circle, first name under it; icons
   only (56px): circle and badge. With no name set: a person icon and "You". Its name for a screen reader is
   "<name>, menu, 1 problem" (creaite has no accounts, so never "account menu").
   Its menu is More's, opened on a click only (#295: no hover-open), beside the rail and bottom-aligned with the button: a header
   row (initials, name, "creaite · v<VERSION>"), then the pages kept there (Files, Activity, Settings by default) in the saved
   order, with Health (its problems, amber) before Settings and Help after it, then the Customise sidebar block at its foot
   (Labels when collapsed is in that dialog only, #214). Intake's own count shows inside. A menu (dev/COMPONENTS.md's Menu):
   aria-haspopup and aria-expanded on the button; the box is the Menu block's MenuPanel (BL-316): ↑ ↓ Home End move, Enter or
   Space picks, Esc closes and puts focus back on the avatar, Tab or a click away closes; → or ↑ on the button opens it with
   focus inside. Always shown, even with nothing in railCfg.more: Health, Help and Customise sidebar live in it. The ids stay
   More's (#railMore, #railMoreMenu, railMoreOpen, railCfg.more), so saved sidebars, ⌘K and focus return need no migration.
   Its items stay in the page while it is closed, so their badges (#inboxBadge …) are always there. */
import { effect } from "@preact/signals";
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { tipHide } from "../../core/dom.js";
import { menuGroup } from "../../core/hover.js";
import { S } from "../../core/page.js";
import { railCfg, railInitials, railMode, railMoreOpen, railName, railView } from "../../stores/rail.js";
import { healthCount, healthFirst } from "../../stores/settings.js";
import { MenuPanel, menuItemsIn } from "../Menu.jsx";
import { capCount, RailButton } from "./RailButton.jsx";
import { RailIcon } from "./RailIcon.jsx";

/** "1 problem", "2 problems". @param {number} n */
const probs = n => `${n} ${n === 1 ? "problem" : "problems"}`;

/** @typedef {{onGo: (id: string) => void, onCustomise: (opener: HTMLElement) => void,
    onHealth: () => void, onHelp: () => void}} RailMoreProps */

/** @param {RailMoreProps} props */
export function RailMore({ onGo, onCustomise, onHealth, onHelp }) {
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [at, setAt] = useState(/** @type {Record<string, string>} */ ({}));
  const [ptr, setPtr] = useState(false);                     /* opened by the pointer: focus stays where it was */
  const open = railMoreOpen.value, mode = railMode.value, more = railCfg.value.more;
  const name = railName.value, who = name || "You", init = railInitials(name);
  const bd = useRef(/** @type {HTMLSpanElement | null} */ (null));
  const isOpen = useRef(false); isOpen.current = open;
  /* its name and badge follow the problems at once (a synchronous effect, as RailButton's): amber, "<name>, menu, 1 problem" */
  useLayoutEffect(() => effect(() => {
    const b = btn.current, s = bd.current; if (!b || !s) return;
    const n = healthCount.value;
    b.setAttribute("aria-label", `${railName.value || "You"}, menu${n ? `, ${probs(n)}` : ""}`);
    s.textContent = capCount(n); s.style.display = n ? "" : "none";
    s.setAttribute("aria-label", probs(n));
  }), []);

  /* any navigation (go, ⌘K) folds an open menu, as it does Projects and Work */
  useEffect(() => effect(() => { void railView.value; if (isOpen.current) close(false); }), []);
  /** @param {boolean} focusBack */
  const close = focusBack => { if (menuGroup.current === btn.current) menuGroup.close(); railMoreOpen.value = false; if (focusBack) btn.current?.focus(); };
  /* placed beside the rail, bottom-aligned with the button, kept in the window */
  useLayoutEffect(() => {
    if (!open || !btn.current) return;
    tipHide();
    const r = btn.current.getBoundingClientRect(), rail = btn.current.closest(".rail")?.getBoundingClientRect() || r;
    setAt({ left: `${rail.right + 4}px`, bottom: `${Math.max(8, innerHeight - r.bottom)}px` });
  }, [open, mode]);

  /** @param {string} id */
  const go = id => { close(false); onGo(id); };
  const n = healthCount.value, first = healthFirst.value;
  const line = n ? first || `${probs(n)} to fix` : "Settings and health";
  /** The initials circle (a person icon with no name), with the badge on it when given. @param {any} badge */
  const circle = badge => <span class="av" aria-hidden="true">{init ? <span class="avi" key="i">{init}</span> : <RailIcon key="u" name="user" />}{badge}</span>;   /* keyed: the badge (written by the effect) is never reused */
  const health = (
    <button type="button" class="nv" role="menuitem" id="railHealth" key="health" onClick={() => { close(false); onHealth(); }}>
      <RailIcon name="pulse" />
      <span class="rl">Health</span>
      <span class="badge warn" id="railHealthBadge" style={n ? "" : "display:none"} aria-label={probs(n)}>{capCount(n)}</span>
      <span class="vh">{n ? `: ${probs(n)}` : ""}</span>
    </button>);
  const help = (
    <button type="button" class="nv" role="menuitem" id="railHelp" key="help" onClick={() => { close(false); onHelp(); }}>
      <RailIcon name="help" />
      <span class="rl">Help</span>
    </button>);
  const rows = [];
  more.forEach(id => { if (id === "settings") rows.push(health); rows.push(<RailButton key={id} id={id} inMenu onGo={go} />); if (id === "settings") rows.push(help); });
  if (!more.includes("settings")) rows.push(health, help);
  return (
    <div class="railmore">
      <button type="button" class={`nv avbtn${n ? " avwarn" : ""}`} id="railMore" ref={btn} aria-haspopup="menu"
        aria-expanded={open ? "true" : "false"} aria-controls="railMoreMenu"
        onClick={() => {
          menuGroup.release(btn.current); setPtr(false);
          if (!open && menuGroup.current && menuGroup.current !== btn.current) menuGroup.close();   /* one menu open at a time */
          railMoreOpen.value = !open; if (open && menuGroup.current === btn.current) menuGroup.close();
        }}
        onKeyDown={e => {
          if (e.key !== "ArrowUp" && e.key !== "ArrowRight") return;
          e.preventDefault(); menuGroup.release(btn.current); setPtr(false);
          if (open) menuItemsIn(box.current)[0]?.focus({ preventScroll: true }); else railMoreOpen.value = true;
        }}>
        {circle(<span class="badge warn" id="railMoreBadge" key="b" ref={bd} style="display:none"></span>)}
        <span class="avt">
          <span class="rl avn">{mode === "labels" ? who.split(/\s+/)[0] : who}</span>
          <span class="avs">{line}</span>
        </span>
      </button>
      <MenuPanel bare id="railMoreMenu" label={who} hidden={!open} style={at} anchor={btn.current} boxRef={box} autoFocus={!ptr}
        onClose={how => close(how === "esc")}>
        <div class="avhead" role="presentation">
          {circle(null)}
          <span class="avt"><span class="avn">{who}</span><span class="avv">{S.version ? `creaite · v${S.version}` : "creaite"}</span></span>
        </div>
        <div role="separator" class="railsep"></div>
        {rows}
        <div role="separator" class="railsep"></div>
        <div class="fsec2" role="presentation">Customise sidebar</div>
        <button type="button" class="nv" role="menuitem" id="railCustBtn" aria-haspopup="dialog"
          onClick={() => { close(false); onCustomise(btn.current); }}>
          <RailIcon name="sliders" />
          <span class="rl">Customise sidebar…</span>
        </button>
      </MenuPanel>
    </div>
  );
}

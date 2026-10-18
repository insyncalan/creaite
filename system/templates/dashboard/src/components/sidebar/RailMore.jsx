// @ts-check
/* RailMore (BL-319 part 6; #156, #139): More, at the bottom of the sidebar, out of the eye line. Its menu opens beside it on hover
   (core/hover.js: MENU_OPEN, MENU_CLOSE, the safe triangle) as well as on a click, upwards (sideways when collapsed), on the pages
   kept there (Intake, Files, Activity, Settings by default), with Health (its problems, amber) before Settings and Help after it,
   then the Customise sidebar block at its foot: the entry that opens the dialog (Labels when collapsed is in that dialog only, #214). Its badge
   is amber and means a problem (Health: "More, 1 problem"); Intake's own count shows inside. A menu (dev/COMPONENTS.md's Menu):
   aria-haspopup and aria-expanded on the button; the box is the Menu block's MenuPanel (BL-316): ↑ ↓ Home End move, Enter or
   Space picks, Esc closes and puts focus back on More, Tab or a click away closes; → or ↑ on the button opens it with focus
   inside. Hidden when More is empty.
   Its items stay in the page while it is closed, so their badges (#inboxBadge …) are always there. */
import { effect } from "@preact/signals";
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { tipHide } from "../../core/dom.js";
import { hoverAttach, menuGroup } from "../../core/hover.js";
import { railCfg, railMode, railMoreOpen, railView } from "../../stores/rail.js";
import { healthCount } from "../../stores/settings.js";
import { MenuPanel, menuItemsIn } from "../Menu.jsx";
import { capCount, RailButton } from "./RailButton.jsx";
import { RailIcon } from "./RailIcon.jsx";

/** @typedef {{onGo: (id: string) => void, onCustomise: (opener: HTMLElement) => void,
    onHealth: () => void, onHelp: () => void}} RailMoreProps */

/** @param {RailMoreProps} props */
export function RailMore({ onGo, onCustomise, onHealth, onHelp }) {
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [at, setAt] = useState(/** @type {Record<string, string>} */ ({}));
  const [ptr, setPtr] = useState(false);                     /* opened by the pointer: focus stays where it was */
  const open = railMoreOpen.value, mode = railMode.value, more = railCfg.value.more;
  const bd = useRef(/** @type {HTMLSpanElement | null} */ (null));
  const isOpen = useRef(false); isOpen.current = open;
  /* its name and badge follow the problems at once (a synchronous effect, as RailButton's): amber, "More, 1 problem" */
  useLayoutEffect(() => effect(() => {
    const b = btn.current, s = bd.current; if (!b || !s) return;
    const n = healthCount.value;
    b.setAttribute("aria-label", `More${n ? `, ${n} ${n === 1 ? "problem" : "problems"}` : ""}`);
    s.textContent = capCount(n); s.style.display = n ? "" : "none";
    s.setAttribute("aria-label", `${n} ${n === 1 ? "problem" : "problems"}`);
  }), [more.length > 0]);
  /* the hover standard's wiring; the flyout is More's own menu */
  useEffect(() => {
    const b = btn.current; if (!b) return;
    return hoverAttach(b, { group: menuGroup, focusOpens: false, panel: () => box.current,
      open: () => { if (isOpen.current) return; tipHide(); setPtr(true); railMoreOpen.value = true; }, close: () => { railMoreOpen.value = false; } });
  }, [more.length > 0]);

  /* any navigation (go, ⌘K) folds an open More, as it does Projects and Work */
  useEffect(() => effect(() => { void railView.value; if (isOpen.current) close(false); }), []);
  /** @param {boolean} focusBack */
  const close = focusBack => { if (menuGroup.current === btn.current) menuGroup.close(); railMoreOpen.value = false; if (focusBack) btn.current?.focus(); };
  /* placed beside the button, kept in the window: above it (expanded) or to the right of the rail (collapsed) */
  useLayoutEffect(() => {
    if (!open || !btn.current) return;
    tipHide();
    const r = btn.current.getBoundingClientRect(), rail = btn.current.closest(".rail")?.getBoundingClientRect() || r;
    setAt({ left: `${rail.right + 4}px`, bottom: `${Math.max(8, innerHeight - r.bottom)}px` });
  }, [open, mode]);
  if (!more.length) return null;

  /** @param {string} id */
  const go = id => { close(false); onGo(id); };
  const n = healthCount.value;
  const health = (
    <button type="button" class="nv" role="menuitem" id="railHealth" key="health" onClick={() => { close(false); onHealth(); }}>
      <RailIcon name="pulse" />
      <span class="rl">Health</span>
      <span class="badge warn" id="railHealthBadge" style={n ? "" : "display:none"} aria-label={`${n} ${n === 1 ? "problem" : "problems"}`}>{capCount(n)}</span>
      <span class="vh">{n ? `: ${n} ${n === 1 ? "problem" : "problems"}` : ""}</span>
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
      <button type="button" class="nv" id="railMore" ref={btn} aria-haspopup="menu" aria-expanded={open ? "true" : "false"}
        aria-controls="railMoreMenu"
        onClick={() => { menuGroup.release(btn.current); setPtr(false); railMoreOpen.value = !open; if (open && menuGroup.current === btn.current) menuGroup.close(); }}
        onKeyDown={e => {
          if (e.key !== "ArrowUp" && e.key !== "ArrowRight") return;
          e.preventDefault(); menuGroup.release(btn.current); setPtr(false);
          if (open) menuItemsIn(box.current)[0]?.focus({ preventScroll: true }); else railMoreOpen.value = true;
        }}>
        <RailIcon name="more" />
        <span class="rl">More</span>
        <span class="badge warn" id="railMoreBadge" ref={bd} style="display:none"></span>
      </button>
      <MenuPanel bare id="railMoreMenu" label="More" hidden={!open} style={at} anchor={btn.current} boxRef={box} autoFocus={!ptr}
        onClose={how => close(how === "esc")}>
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

// @ts-check
/* RailMore (BL-319 part 6): More, at the bottom of the sidebar, out of the eye line. It opens upwards (sideways when the
   sidebar is collapsed) on the pages kept there (Intake, Files, Activity, Settings by default), then Customise
   sidebar… at its foot. Its badge adds up what the pages inside have waiting, and its name says which ("More: Intake
   has 2 waiting"). A menu (dev/COMPONENTS.md's Menu): aria-haspopup and aria-expanded on the button; ↑ ↓ Home End move,
   Enter or Space opens, Esc closes and puts focus back on More, Tab or a click away closes. Hidden when More is empty.
   Its items stay in the page while it is closed, so their badges (#inboxBadge …) are always there. */
import { effect } from "@preact/signals";
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { railCfg, railCollapsed, railMoreOpen, railMoreWaiting } from "../../stores/rail.js";
import { RailButton } from "./RailButton.jsx";
import { RailIcon } from "./RailIcon.jsx";

/** @typedef {{onGo: (id: string) => void, onCustomise: (opener: HTMLElement) => void}} RailMoreProps */

/** @param {HTMLElement | null} menu */
const railMenuItems = menu => /** @type {HTMLButtonElement[]} */ ([...(menu ? menu.querySelectorAll("[role=menuitem]") : [])]);

/** @param {RailMoreProps} props */
export function RailMore({ onGo, onCustomise }) {
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const menu = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [at, setAt] = useState(/** @type {Record<string, string>} */ ({}));
  const open = railMoreOpen.value, collapsed = railCollapsed.value, more = railCfg.value.more;
  const bd = useRef(/** @type {HTMLSpanElement | null} */ (null));
  /* its name, tooltip and badge follow what waits inside at once (a synchronous effect, as RailButton's) */
  useLayoutEffect(() => effect(() => {
    const b = btn.current, s = bd.current; if (!b || !s) return;
    const w = railMoreWaiting.value, total = w.reduce((a, x) => a + x[1], 0);
    const name = `More${w.length ? ": " + w.map(([t, n]) => `${t} has ${n} waiting`).join(", ") : ""}`;
    b.setAttribute("aria-label", name);
    if (railCollapsed.value) b.setAttribute("data-tip", name); else b.removeAttribute("data-tip");
    s.textContent = String(total); s.style.display = total ? "" : "none";
  }), [more.length > 0]);

  /** @param {boolean} focusBack */
  const close = focusBack => { railMoreOpen.value = false; if (focusBack) btn.current?.focus(); };
  /* placed beside the button, kept in the window: above it (expanded) or to the right of the rail (collapsed) */
  useLayoutEffect(() => {
    if (!open || !btn.current) return;
    const r = btn.current.getBoundingClientRect(), rail = btn.current.closest(".rail")?.getBoundingClientRect() || r;
    setAt(collapsed ? { left: `${rail.right + 8}px`, bottom: `${Math.max(8, innerHeight - r.bottom)}px` }
      : { left: `${r.left}px`, bottom: `${Math.max(8, innerHeight - r.top + 6)}px` });
    railMenuItems(menu.current)[0]?.focus();
  }, [open, collapsed]);
  useEffect(() => {
    if (!open) return;
    /** @param {PointerEvent} e */
    const away = e => { const t = /** @type {Element} */ (e.target); if (!menu.current?.contains(t) && !btn.current?.contains(t)) close(false); };
    document.addEventListener("pointerdown", away, true);
    return () => document.removeEventListener("pointerdown", away, true);
  }, [open]);
  if (!more.length) return null;

  /** @param {KeyboardEvent} e */
  const keys = e => {
    const L = railMenuItems(menu.current), i = L.indexOf(/** @type {HTMLButtonElement} */ (document.activeElement));
    if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(true); }
    else if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); L[(i + (e.key === "ArrowDown" ? 1 : -1) + L.length) % L.length]?.focus(); }
    else if (e.key === "Home" || e.key === "End") { e.preventDefault(); (e.key === "Home" ? L[0] : L[L.length - 1])?.focus(); }
    else if (e.key === "Tab") close(false);
  };
  /** @param {string} id */
  const go = id => { close(false); onGo(id); };
  return (
    <div class="railmore">
      <button type="button" class="nv" id="railMore" ref={btn} aria-haspopup="menu" aria-expanded={open ? "true" : "false"}
        aria-controls="railMoreMenu"
        onClick={() => { railMoreOpen.value = !open; }}
        onKeyDown={e => { if (e.key === "ArrowUp" && !open) { e.preventDefault(); railMoreOpen.value = true; } }}>
        <RailIcon name="more" />
        <span class="rl">More</span>
        <span class="badge" id="railMoreBadge" ref={bd} style="display:none" aria-hidden="true"></span>
      </button>
      <div id="railMoreMenu" role="menu" aria-label="More" ref={menu} hidden={!open} style={at} onKeyDown={keys}>
        {more.map(id => <RailButton key={id} id={id} inMenu onGo={go} />)}
        <div role="separator" class="railsep"></div>
        <button type="button" class="nv" role="menuitem" id="railCustBtn" aria-haspopup="dialog"
          onClick={() => { close(false); onCustomise(btn.current); }}>
          <RailIcon name="sliders" />
          <span class="rl">Customise sidebar…</span>
        </button>
      </div>
    </div>
  );
}

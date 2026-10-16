// @ts-check
/* RailMore (BL-319 part 6): More, at the bottom of the sidebar, out of the eye line. It opens upwards (sideways when the
   sidebar is collapsed) on the pages kept there (Intake, Files, Activity, Settings by default), then Customise
   sidebar… at its foot. Its badge adds up what the pages inside have waiting, and its name says which ("More: Intake
   has 2 waiting"). A menu (dev/COMPONENTS.md's Menu): aria-haspopup and aria-expanded on the button; the box is the Menu
   block's MenuPanel (BL-316): ↑ ↓ Home End move, Enter or Space opens, Esc closes and puts focus back on More, Tab or a
   click away closes. Hidden when More is empty.
   Its items stay in the page while it is closed, so their badges (#inboxBadge …) are always there. */
import { effect } from "@preact/signals";
import { tipHide } from "../../core/dom.js";
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { railCfg, railCollapsed, railMoreOpen, railMoreWaiting } from "../../stores/rail.js";
import { MenuPanel, useHoverMenu } from "../Menu.jsx";
import { RailButton } from "./RailButton.jsx";
import { RailIcon } from "./RailIcon.jsx";

/** @typedef {{onGo: (id: string) => void, onCustomise: (opener: HTMLElement) => void}} RailMoreProps */

/** @param {RailMoreProps} props */
export function RailMore({ onGo, onCustomise }) {
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const [at, setAt] = useState(/** @type {Record<string, string>} */ ({}));
  const open = railMoreOpen.value, collapsed = railCollapsed.value, more = railCfg.value.more;
  const bd = useRef(/** @type {HTMLSpanElement | null} */ (null));
  const h = useHoverMenu({ hover: true, open, setOpen: v => { railMoreOpen.value = v; }, btn });   /* #139: the one hover behaviour of the rail's flyouts */
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
  const close = focusBack => h.close(focusBack ? "esc" : "pick");
  /* placed beside the button, kept in the window: above it (expanded) or to the right of the rail (collapsed) */
  useLayoutEffect(() => {
    if (!open || !btn.current) return;
    tipHide();
    const r = btn.current.getBoundingClientRect(), rail = btn.current.closest(".rail")?.getBoundingClientRect() || r;
    setAt(collapsed ? { left: `${rail.right + 8}px`, bottom: `${Math.max(8, innerHeight - r.bottom)}px` }
      : { left: `${r.left}px`, bottom: `${Math.max(8, innerHeight - r.top + 6)}px` });
  }, [open, collapsed]);
  if (!more.length) return null;

  /** @param {string} id */
  const go = id => { close(false); onGo(id); };
  return (
    <div class="railmore" onMouseEnter={h.pointIn} onMouseLeave={h.pointOut}>
      <button type="button" class="nv" id="railMore" ref={btn} aria-haspopup="menu" aria-expanded={open ? "true" : "false"}
        aria-controls="railMoreMenu"
        onClick={e => {
          if (open && h.byMouse.current && e.detail > 0 && Date.now() - h.openedAt.current < 400) { h.noFocus.current = false; h.bump(n => n + 1); return; }   /* a click as the pointer arrives is "open it" */
          h.byMouse.current = e.detail > 0; h.noFocus.current = false; if (open) h.close("pick"); else railMoreOpen.value = true;
        }}
        onKeyDown={e => {
          if ((e.key === "ArrowUp" || e.key === "ArrowRight") && !open) { e.preventDefault(); h.byMouse.current = false; h.noFocus.current = false; railMoreOpen.value = true; }
          else if ((e.key === "ArrowUp" || e.key === "ArrowRight") && open) { e.preventDefault(); h.byMouse.current = false; h.noFocus.current = false; h.bump(n => n + 1); }
        }}>
        <RailIcon name="more" />
        <span class="rl">More</span>
        <span class="badge" id="railMoreBadge" ref={bd} style="display:none" aria-hidden="true"></span>
      </button>
      <MenuPanel bare id="railMoreMenu" label="More" hidden={!open} style={at} anchor={btn.current} autoFocus={!h.noFocus.current} focusKey={h.noFocus.current}
        onClose={how => close(how === "esc")}>
        {more.map(id => <RailButton key={id} id={id} inMenu onGo={go} />)}
        <div role="separator" class="railsep"></div>
        <button type="button" class="nv" role="menuitem" id="railCustBtn" aria-haspopup="dialog"
          onClick={() => { close(false); onCustomise(btn.current); }}>
          <RailIcon name="sliders" />
          <span class="rl">Customise sidebar…</span>
        </button>
      </MenuPanel>
    </div>
  );
}

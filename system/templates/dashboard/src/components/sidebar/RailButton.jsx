// @ts-check
/* RailButton (BL-319 part 6): one page in the sidebar or in More. Its icon, its name and its count. The current page
   keeps the accent bar (aria-current="page"). Collapsed, the name is hidden, so the button's accessible name and the
   one tooltip (data-tip, BL-158) carry it, and the count becomes a small badge on the icon. The badge keeps its id
   (#revBadge, #inboxBadge, #vipBadge) and its own label.
   The parts that change (current page, count, name, tooltip) follow the store's signals through a synchronous effect
   (an effect of its own), so `go(…)` or `renderBadge()` is visible on the very next line, as it was before the sidebar moved to
   Preact (@preact/signals' own prop bindings wait for the next frame). */
import { effect } from "@preact/signals";
import { useLayoutEffect, useRef, useState } from "preact/hooks";
import { tipHide } from "../../core/dom.js";
import { MenuItems, MenuPanel, useHoverMenu } from "../Menu.jsx";
import { railCollapsed, railCounts, railItem, railView } from "../../stores/rail.js";
import { RailIcon } from "./RailIcon.jsx";

/** @typedef {{id: string, inMenu?: boolean, onGo: (id: string) => void, fly?: () => import("../Menu.jsx").MenuItem[],
    onFly?: (id: string, pick: string) => void}} RailButtonProps
    `fly` (#139): the page has a hover flyout (Projects, Work): `fly()` gives its items as it opens, `onFly` runs a pick. */

/** Set or remove an attribute. @param {Element} el @param {string} k @param {string | undefined} v */
const attr = (el, k, v) => { if (v == null) el.removeAttribute(k); else if (el.getAttribute(k) !== v) el.setAttribute(k, v); };

/** @param {RailButtonProps} props */
export function RailButton({ id, inMenu, onGo, fly, onFly }) {
  const it = railItem(id), hasFly = !!fly && !inMenu;
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const bd = useRef(/** @type {HTMLSpanElement | null} */ (null));
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [open, setOpen] = useState(false);
  const h = useHoverMenu({ hover: hasFly, open, setOpen, btn });
  useLayoutEffect(() => effect(() => {
    const b = btn.current; if (!b) return;
    const c = railCounts.value[id] || { n: 0, label: undefined };
    attr(b, "aria-current", railView.value === id ? "page" : "false");
    attr(b, "aria-label", `${it.title}${c.n ? `, ${c.n} waiting` : ""}`);
    attr(b, "data-tip", !inMenu && railCollapsed.value && !open ? it.title : undefined);   /* the tooltip gives way to the flyout */
    const s = bd.current;
    if (s) { if (s.textContent !== String(c.n)) s.textContent = String(c.n); s.style.display = c.n ? "" : "none"; attr(s, "aria-label", c.label); }
  }), [id, inMenu, open]);
  /* the flyout sits beside the rail (to the right of it, collapsed or not), level with its button, kept inside the window */
  useLayoutEffect(() => {
    const el = box.current, b = btn.current; if (!open || !el || !b) return;
    tipHide();
    const r = b.getBoundingClientRect(), rail = b.closest(".rail")?.getBoundingClientRect() || r;
    el.style.left = `${Math.round(rail.right + 4)}px`;
    el.style.top = `${Math.round(Math.max(8, Math.min(r.top - 4, innerHeight - el.offsetHeight - 8)))}px`;
  }, [open, railCollapsed.value]);
  /** @param {KeyboardEvent} e */
  const key = e => {
    if (!hasFly || (e.key !== "ArrowRight" && e.key !== "ArrowDown")) return;
    e.preventDefault(); h.byMouse.current = false; h.noFocus.current = false;
    if (open) h.bump(n => n + 1); else setOpen(true);   /* open: focus goes into it */
  };
  const items = open && fly ? fly() : [];
  return (
    <>
      <button type="button" class="nv" data-v={id} role={inMenu ? "menuitem" : undefined} ref={btn}
        aria-haspopup={hasFly ? "menu" : undefined} aria-expanded={hasFly ? (open ? "true" : "false") : undefined}
        onMouseEnter={hasFly ? h.pointIn : undefined} onMouseLeave={hasFly ? h.pointOut : undefined} onKeyDown={hasFly ? key : undefined}
        onClick={() => { if (hasFly && open) h.close("pick"); onGo(id); }}>
        <RailIcon name={it.icon} />
        <span class="rl">{it.title}</span>
        {it.badge ? <span class="badge" id={it.badge} ref={bd} style="display:none"></span> : null}
      </button>
      {hasFly && open ? (
        <MenuPanel bare cls="railfly" id={`railFly-${id}`} label={it.title} boxRef={box} anchor={btn.current}
          autoFocus={!h.noFocus.current} focusKey={h.noFocus.current} onEnter={h.pointIn} onLeave={h.pointOut}
          onClose={how => h.close(how)} onKey={e => { if (e.key === "ArrowLeft") { e.preventDefault(); e.stopPropagation(); h.close("esc"); } }}>
          <MenuItems items={items} onPick={x => { h.close("pick"); onFly && onFly(id, x.id); }} />
        </MenuPanel>
      ) : null}
    </>
  );
}

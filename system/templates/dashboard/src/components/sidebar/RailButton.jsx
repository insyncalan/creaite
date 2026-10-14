// @ts-check
/* RailButton (BL-319 part 6): one page in the sidebar or in More. Its icon, its name and its count. The current page
   keeps the accent bar (aria-current="page"). Collapsed, the name is hidden, so the button's accessible name and the
   one tooltip (data-tip, BL-158) carry it, and the count becomes a small badge on the icon. The badge keeps its id
   (#revBadge, #inboxBadge, #vipBadge) and its own label.
   The parts that change (current page, count, name, tooltip) follow the store's signals through a synchronous effect
   (an effect of its own), so `go(…)` or `renderBadge()` is visible on the very next line, as it was before the sidebar moved to
   Preact (@preact/signals' own prop bindings wait for the next frame). */
import { effect } from "@preact/signals";
import { useLayoutEffect, useRef } from "preact/hooks";
import { railCollapsed, railCounts, railItem, railView } from "../../stores/rail.js";
import { RailIcon } from "./RailIcon.jsx";

/** @typedef {{id: string, inMenu?: boolean, onGo: (id: string) => void}} RailButtonProps */

/** Set or remove an attribute. @param {Element} el @param {string} k @param {string | undefined} v */
const attr = (el, k, v) => { if (v == null) el.removeAttribute(k); else if (el.getAttribute(k) !== v) el.setAttribute(k, v); };

/** @param {RailButtonProps} props */
export function RailButton({ id, inMenu, onGo }) {
  const it = railItem(id);
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const bd = useRef(/** @type {HTMLSpanElement | null} */ (null));
  useLayoutEffect(() => effect(() => {
    const b = btn.current; if (!b) return;
    const c = railCounts.value[id] || { n: 0, label: undefined };
    attr(b, "aria-current", railView.value === id ? "page" : "false");
    attr(b, "aria-label", `${it.title}${c.n ? `, ${c.n} waiting` : ""}`);
    attr(b, "data-tip", !inMenu && railCollapsed.value ? it.title : undefined);
    const s = bd.current;
    if (s) { if (s.textContent !== String(c.n)) s.textContent = String(c.n); s.style.display = c.n ? "" : "none"; attr(s, "aria-label", c.label); }
  }), [id, inMenu]);
  return (
    <button type="button" class="nv" data-v={id} role={inMenu ? "menuitem" : undefined} ref={btn} onClick={() => onGo(id)}>
      <RailIcon name={it.icon} />
      <span class="rl">{it.title}</span>
      {it.badge ? <span class="badge" id={it.badge} ref={bd} style="display:none"></span> : null}
    </button>
  );
}

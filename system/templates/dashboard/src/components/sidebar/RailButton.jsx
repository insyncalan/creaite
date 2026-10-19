// @ts-check
/* RailButton (BL-319 part 6; #156, #139): one page in the sidebar or in More. Its icon, its name and its count. The current page
   is a tonal pill with the accent bar (aria-current="page"). Collapsed with labels, the name sits under the icon; icons only, the
   button's accessible name and the one tooltip (data-tip, BL-158; core/hover.js's TIP_ times) carry it. The count is an accent pill
   (a small badge on the icon's corner when collapsed, 99+ at most). The badge keeps its id (#revBadge, #inboxBadge, #vipBadge)
   and its own label.
   #139: Projects and Work open a flyout beside the rail on hover (core/hover.js: MENU_OPEN, MENU_CLOSE, the safe triangle), with
   the keyboard too (→ or ↓ opens it with focus inside, arrows move, Enter picks, Esc closes with focus back on the button). The
   icon alone still goes to the page. A flyout is the shared hover group's: one menu open at a time across the page.
   The parts that change (current page, count, name, tooltip) follow the store's signals through a synchronous effect
   (an effect of its own), so `go(…)` or `renderBadge()` is visible on the very next line, as it was before the sidebar moved to
   Preact (@preact/signals' own prop bindings wait for the next frame). */
import { effect } from "@preact/signals";
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { tipHide } from "../../core/dom.js";
import { hoverAttach, menuGroup } from "../../core/hover.js";
import { MenuPanel, menuItemsIn } from "../Menu.jsx";
import { StatusDot } from "../StatusDot.jsx";
import { railCounts, railItem, railMode, railView } from "../../stores/rail.js";
import { RailIcon } from "./RailIcon.jsx";

/** @typedef {{id: string, name?: string, health?: string, count?: number, note?: string}} FlyItem */
/** @typedef {{id: string, inMenu?: boolean, onGo: (id: string) => void, fly?: () => FlyItem[],
    onFly?: (id: string, pick: string) => void}} RailButtonProps
    `fly` (#139): the page has a hover flyout (Projects, Work): `fly()` gives its items as it opens, `onFly` runs a pick. */

/** Set or remove an attribute. @param {Element} el @param {string} k @param {string | undefined} v */
const attr = (el, k, v) => { if (v == null) el.removeAttribute(k); else if (el.getAttribute(k) !== v) el.setAttribute(k, v); };
/** A count as the badge shows it: 99+ at most. @param {number} n */
export const capCount = n => (n > 99 ? "99+" : String(n));

/** @param {RailButtonProps} props */
export function RailButton({ id, inMenu, onGo, fly, onFly }) {
  const it = railItem(id), hasFly = !!fly && !inMenu;
  const btn = useRef(/** @type {HTMLButtonElement | null} */ (null));
  const bd = useRef(/** @type {HTMLSpanElement | null} */ (null));
  const box = useRef(/** @type {HTMLDivElement | null} */ (null));
  const [open, setOpen] = useState(false);
  const byPointer = useRef(false), isOpen = useRef(false); isOpen.current = open;
  useLayoutEffect(() => effect(() => {
    const b = btn.current; if (!b) return;
    const c = railCounts.value[id] || { n: 0, label: undefined };
    attr(b, "aria-current", railView.value === id ? "page" : "false");
    attr(b, "aria-label", `${it.title}${c.n ? `, ${c.n} waiting` : ""}`);
    attr(b, "data-tip", !inMenu && !hasFly && railMode.value === "icons" ? it.title : undefined);   /* a tooltip only where no label shows, and where no flyout opens */
    const s = bd.current;
    if (s) { const t = capCount(c.n); if (s.textContent !== t) s.textContent = t; s.style.display = c.n ? "" : "none"; attr(s, "aria-label", c.label); }
  }), [id, inMenu, hasFly]);
  /* #139: the hover standard's wiring (pointer, safe triangle, one menu at a time) */
  useEffect(() => {
    const b = btn.current; if (!hasFly || !b) return;
    return hoverAttach(b, { group: menuGroup, focusOpens: false, panel: () => box.current,
      open: () => { if (isOpen.current) return; byPointer.current = true; tipHide(); setOpen(true); }, close: () => setOpen(false) });
  }, [hasFly]);
  /* any navigation (go, ⌘K) folds an open flyout */
  useEffect(() => effect(() => { void railView.value; if (isOpen.current) shut(false); }), []);
  /** @param {boolean} back */
  function shut(back) { if (menuGroup.current === btn.current) menuGroup.close(); setOpen(false); if (back) btn.current?.focus(); }
  /* the flyout sits beside the rail, level with its button, kept inside the window */
  useLayoutEffect(() => {
    const el = box.current, b = btn.current; if (!open || !el || !b) return;
    const r = b.getBoundingClientRect(), rail = b.closest(".rail")?.getBoundingClientRect() || r;
    el.style.left = `${Math.round(rail.right + 4)}px`;
    el.style.top = `${Math.round(Math.max(8, Math.min(r.top - 4, innerHeight - el.offsetHeight - 8)))}px`;
  }, [open, railMode.value]);
  /** @param {KeyboardEvent} e */
  const key = e => {
    if (!hasFly || (e.key !== "ArrowRight" && e.key !== "ArrowDown")) return;
    e.preventDefault(); menuGroup.release(btn.current); byPointer.current = false;
    if (open) menuItemsIn(box.current)[0]?.focus({ preventScroll: true }); else setOpen(true);   /* opening from the keys puts focus inside */
  };
  const items = open && fly ? fly() : [];
  return (
    <>
      <button type="button" class="nv" data-v={id} role={inMenu ? "menuitem" : undefined} ref={btn}
        aria-haspopup={hasFly ? "menu" : undefined} aria-expanded={hasFly ? (open ? "true" : "false") : undefined}
        aria-controls={hasFly && open ? `railFly-${id}` : undefined} onKeyDown={hasFly ? key : undefined}
        onClick={() => { if (hasFly) { menuGroup.release(btn.current); shut(false); } onGo(id); }}>
        <RailIcon name={it.icon} />
        <span class="rl" data-short={it.short}>{it.title}</span>
        {it.badge ? <span class="badge" id={it.badge} ref={bd} style="display:none"></span> : null}
      </button>
      {hasFly && open ? (
        <MenuPanel bare cls="railfly" id={`railFly-${id}`} label={it.title} boxRef={box} anchor={btn.current}
          autoFocus={!byPointer.current} onClose={how => shut(how === "esc")}
          onKey={e => { if (e.key === "ArrowLeft") { e.preventDefault(); e.stopPropagation(); shut(true); } }}>
          {items.map(x => x.note ? <div key={x.id} class="mnote sub" role="presentation">{x.note}</div> : (
            <button key={x.id} type="button" role="menuitem" tabIndex={-1} class="fi" data-pick={x.id}
              onClick={() => { shut(false); onFly && onFly(id, x.id); }}>
              <span class="mname">{x.name}</span>
              {x.health ? <StatusDot health={x.health} /> : null}
              {x.count != null ? <span class="fcount">{x.count}</span> : null}
            </button>
          ))}
        </MenuPanel>
      ) : null}
    </>
  );
}

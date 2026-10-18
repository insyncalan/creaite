// @ts-check
/* CustomiseSidebar (BL-319 part 6): two lists, "In the sidebar" and "In More". A page moves by dragging its handle (within
   a list or across to the other), by its arrow buttons (Move up, Move down, Move to More or Move to the sidebar), or
   with Alt and an arrow key on its row (↑ ↓ within the list, ← → across). Today always comes first in the sidebar;
   Settings can live in either. Icons only collapses the sidebar to icons (what older versions saved as display "icons"), and
   Icon size (#182; Small (today's), Medium or Large, saved to dashboard.rail_icon_size) is a three-way choice below the two switches.
   Labels when collapsed (#156; the same setting as More's switch) puts each label under its icon when it is collapsed; turning one
   on turns the other off. Reset to default puts back the default lists.
   Nothing is saved until Done (Cancel, Esc or a click outside with nothing changed leave it as it was); Done saves to
   dashboard.rail through the page's one settings route. The Dialog building block (dev/COMPONENTS.md §3): named by its
   heading, focus to the first control, Esc closes, focus goes back to where it was opened from (the owner's onClose,
   told once it has closed). Each move is said
   aloud (a polite live region). */
import { useEffect, useLayoutEffect, useRef, useState } from "preact/hooks";
import { Dialog, closeDialog } from "../Dialog.jsx";
import { RAIL_DEF, railCfg, railCustOpen, railIconSize, railItem, railLabelsOn } from "../../stores/rail.js";
import { RailIcon } from "./RailIcon.jsx";

/** @typedef {import("../../stores/rail.js").RailCfg} RailCfg */
/** @typedef {{onSave: (cfg: RailCfg, labels: boolean, size: string) => void, onClose: () => void}} CustomiseSidebarProps */
/** @typedef {{top: string[], more: string[], icons: boolean, labels: boolean, size: string}} Draft */

/** @param {RailCfg} c @returns {Draft} */
const draftOf = c => ({ top: [...c.order], more: [...c.more], icons: c.display === "icons", labels: railLabelsOn.value, size: railIconSize.value });
/** @param {Draft} a @param {Draft} b */
const same = (a, b) => a.top.join() === b.top.join() && a.more.join() === b.more.join() && a.icons === b.icons && a.labels === b.labels && a.size === b.size;

/** Move `id` to `zone` at `at` (Today stays first; nothing else may go above it).
    @param {Draft} d @param {string} id @param {"top"|"more"} zone @param {number} at @returns {Draft} */
function placed(d, id, zone, at) {
  const top = d.top.filter(x => x !== id), more = d.more.filter(x => x !== id), L = zone === "top" ? top : more;
  L.splice(Math.max(zone === "top" ? 1 : 0, Math.min(at, L.length)), 0, id);
  return { ...d, top, more };
}

/** @param {CustomiseSidebarProps} props */
export function CustomiseSidebar({ onSave, onClose }) {
  const open = railCustOpen.value;
  const zones = useRef(/** @type {Record<string, HTMLUListElement | null>} */ ({}));
  const focusNext = useRef(/** @type {[string, string] | null} */ (null));
  const [d, setD] = useState(() => draftOf(railCfg.value));
  const [said, setSaid] = useState("");
  const [drag, setDrag] = useState(/** @type {string | null} */ (null));
  const dRef = useRef(d); dRef.current = d;

  useLayoutEffect(() => {          /* each opening starts from the saved sidebar (before the Dialog opens and focuses) */
    if (open) { setD(draftOf(railCfg.value)); setSaid(""); }
  }, [open]);
  useLayoutEffect(() => {          /* after a move, focus stays on the control used (or its row, when that control is now disabled) */
    const f = focusNext.current, box = document.getElementById("railCust"); if (!f || !box) return; focusNext.current = null;
    const li = /** @type {HTMLElement | null} */ (box.querySelector(`li[data-rid="${f[0]}"]`));
    const b = /** @type {HTMLButtonElement | null} */ (li && li.querySelector(`[data-mv="${f[1]}"]`));
    (b && !b.disabled ? b : li)?.focus();
  });
  useEffect(() => {                /* dragging a handle: the row follows the pointer, within a list or across to the other */
    if (!drag) return;
    /** @param {PointerEvent} e */
    const move = e => {
      /** @param {"top"|"more"} k */
      const off = k => { const r = zones.current[k]?.getBoundingClientRect(); return r ? Math.abs(e.clientX - (r.left + r.width / 2)) : Infinity; };
      const zone = off("top") <= off("more") ? "top" : "more";
      const rows = [...(zones.current[zone]?.querySelectorAll("li[data-rid]") || [])].filter(li => /** @type {HTMLElement} */ (li).dataset.rid !== drag);
      let at = rows.findIndex(li => { const r = li.getBoundingClientRect(); return e.clientY < r.top + r.height / 2; });
      if (at < 0) at = rows.length;
      const next = placed(dRef.current, drag, zone, at);
      if (!same(next, dRef.current)) setD(next);
    };
    const up = () => { const id = drag; setDrag(null); setSaid(`${railItem(id).title} moved`); };
    document.addEventListener("pointermove", move); document.addEventListener("pointerup", up);
    return () => { document.removeEventListener("pointermove", move); document.removeEventListener("pointerup", up); };
  }, [drag]);

  /** @param {string} id @param {"up"|"down"|"swap"} how */
  const mv = (id, how) => {
    const zone = d.top.includes(id) ? "top" : "more", L = zone === "top" ? d.top : d.more, i = L.indexOf(id);
    if (id === "today") return;
    if (how === "swap") { const to = zone === "top" ? "more" : "top"; setD(placed(d, id, to, (to === "top" ? d.top : d.more).length));
      setSaid(`${railItem(id).title} moved to ${to === "top" ? "the sidebar" : "More"}`); }
    else { const j = i + (how === "up" ? -1 : 1); if (j < (zone === "top" ? 1 : 0) || j >= L.length) return;
      setD(placed(d, id, zone, j)); setSaid(`${railItem(id).title} moved ${how}, ${j + 1} of ${L.length}`); }
    focusNext.current = [id, how];
  };
  /** @param {KeyboardEvent} e */
  const rowKeys = e => {
    const li = /** @type {HTMLElement | null} */ (/** @type {Element} */ (e.target).closest("li[data-rid]"));
    if (!li || !e.altKey) return; const id = li.dataset.rid, inTop = d.top.includes(id);
    const how = { ArrowUp: "up", ArrowDown: "down", ArrowLeft: inTop ? null : "swap", ArrowRight: inTop ? "swap" : null }[e.key];
    if (!how) return; e.preventDefault(); mv(id, /** @type {"up"|"down"|"swap"} */ (how));
  };
  const done = () => { onSave({ order: d.top, more: d.more, hidden: [], display: d.icons ? "icons" : "titles" }, d.labels, d.size); closeDialog("railCust"); };
  /* Esc and the scrim close it; the owner is told (onClose) once it has closed, so its focus return lands outside the modal */
  const shut = () => { const el = /** @type {HTMLDialogElement | null} */ (document.getElementById("railCust")); if (el && el.open) el.close(); else onClose(); };

  /** @param {string} id @param {"top"|"more"} zone @param {number} i @param {number} n */
  const row = (id, zone, i, n) => {
    const it = railItem(id), fixed = id === "today", to = zone === "top" ? "More" : "the sidebar";
    return (
      <li key={id} data-rid={id} tabindex={-1} class={`rpi${drag === id ? " dragging" : ""}`} aria-label={it.title}>
        <span class="grip" data-rgrip aria-hidden="true" hidden={fixed}
          onPointerDown={e => { if (e.button !== 0) return; e.preventDefault(); try { /** @type {Element} */ (e.currentTarget).setPointerCapture(e.pointerId); } catch (x) { /* a synthetic pointer */ } setDrag(id); }}>
          <RailIcon name="grip" />
        </span>
        <span class="rpn"><RailIcon name={it.icon} /><span class="rpt"><span>{it.title}</span>{fixed ? <span class="why">Always first</span> : null}</span></span>
        {fixed ? null : <>
          <button type="button" class="ib sm" data-mv="up" aria-label={`Move ${it.title} up`} data-tip={`Move ${it.title} up`}
            disabled={i <= (zone === "top" ? 1 : 0)} onClick={() => mv(id, "up")}><RailIcon name="up" /></button>
          <button type="button" class="ib sm" data-mv="down" aria-label={`Move ${it.title} down`} data-tip={`Move ${it.title} down`}
            disabled={i >= n - 1} onClick={() => mv(id, "down")}><RailIcon name="down" /></button>
          <button type="button" class="ib sm" data-mv="swap" aria-label={`Move ${it.title} to ${to}`} data-tip={`Move to ${to}`}
            onClick={() => mv(id, "swap")}><RailIcon name={zone === "top" ? "right" : "left"} /></button>
        </>}
      </li>
    );
  };
  return (
    <Dialog open={open} onClose={shut} id="railCust" labelledBy="railCustH" describedBy="railCustSub"
      dirty={!same(d, draftOf(railCfg.value))}>
      <h2 id="railCustH">Customise sidebar</h2>
      <p class="sub" id="railCustSub">Drag a handle between the two lists, or use the arrows (Alt with an arrow key on a row). Today always comes first; Settings can live in either.</p>
      <div class="rccols" onKeyDown={rowKeys}>
        <div><h3 id="railCustTop">In the sidebar</h3>
          <ul aria-labelledby="railCustTop" data-zone="top" ref={el => { zones.current.top = el; }}>{d.top.map((id, i) => row(id, "top", i, d.top.length))}</ul></div>
        <div><h3 id="railCustMore">In More</h3>
          <ul aria-labelledby="railCustMore" data-zone="more" ref={el => { zones.current.more = el; }}>{d.more.map((id, i) => row(id, "more", i, d.more.length))}</ul>
          {d.more.length ? null : <p class="sub rcempty">Empty: More is hidden.</p>}</div>
      </div>
      <label class="rcicons"><input type="checkbox" class="switch" role="switch" id="railCustLabels" checked={d.labels && !d.icons}
        onChange={e => { const on = /** @type {HTMLInputElement} */ (e.currentTarget).checked; setD({ ...d, labels: on, icons: on ? false : d.icons }); }} /> Labels when collapsed</label>
      <label class="rcicons"><input type="checkbox" class="switch" role="switch" id="railCustIcons" checked={d.icons}
        onChange={e => { const on = /** @type {HTMLInputElement} */ (e.currentTarget).checked; setD({ ...d, icons: on, labels: on ? false : d.labels }); }} /> Icons only</label>
      <div class="rcsize" role="group" aria-labelledby="railCustSizeH"><h3 id="railCustSizeH">Icon size</h3>
        <div class="rcszs">{[["small", "Small"], ["medium", "Medium"], ["large", "Large"]].map(([k, l]) => (
          <button type="button" class="rcsz" data-size={k} aria-pressed={d.size === k ? "true" : "false"} onClick={() => { setD({ ...d, size: k }); setSaid(`${l} icons`); }}>
            <span class="rcszi" aria-hidden="true"><RailIcon name="today" /></span><span>{l}</span></button>))}</div></div>
      <p class="vh" aria-live="polite">{said}</p>
      <div class="rcfoot">
        <button type="button" class="btn quiet" id="railCustReset"
          onClick={() => { setD({ ...draftOf(RAIL_DEF), labels: true, size: "small" }); setSaid("Back to the default sidebar"); }}>Reset to default</button>
        <span class="grow"></span>
        <button type="button" class="btn" id="railCustCancel" onClick={() => closeDialog("railCust")}>Cancel</button>
        <button type="button" class="btn primary" id="railCustDone" onClick={done}>Done</button>
      </div>
    </Dialog>
  );
}

// @ts-check
/* rail.js: the sidebar (BL-163, BL-191; BL-319 part 6). The items, the saved choice and the signals are in
   stores/rail.js; the sidebar is drawn by the components in components/sidebar/ (dev/COMPONENTS.md), mounted here into
   the shell's containers: the collapse toggle (#railTogBox, before the wordmark), the pages (#railMain), More
   (#railFoot) and Customise sidebar (#railCustBox, a modal dialog). Old code reaches the sidebar only through the store
   (setRailView, setRailCount), never its DOM.

   The choice is settings.json's dashboard.rail = {order, more, hidden, display}, written through writeSettings (a backup
   and a log line); a write that fails is put back. display "icons" is the collapsed sidebar, the 56px rail of icons; the
   toggle and ⌘\ (Ctrl+\) change it. A right-click on the sidebar (or Shift+F10 on a page in it), More's Customise
   sidebar… and Settings › General › Appearance open Customise. */
import { effect } from "@preact/signals";
import { h, render } from "preact";
import { CustomiseSidebar } from "./components/sidebar/CustomiseSidebar.jsx";
import { RailMore } from "./components/sidebar/RailMore.jsx";
import { RailNav } from "./components/sidebar/RailNav.jsx";
import { RailToggle } from "./components/sidebar/RailToggle.jsx";
import { $, addHTML, html, ic, ICONS } from "./core/dom.js";
import { P } from "./core/data.js";
import { go } from "./core/nav.js";
import { MAC, S } from "./core/page.js";
import { writeSettings } from "./core/server.js";
import { shared } from "./core/state.js";
import { RAIL_DEF, RAIL_ITEMS, railCfg, railCollapsed, railCustOpen, railItem, railMoreOpen, railNarrow, railNorm, setRailView } from "./stores/rail.js";
import { row, SETSECTIONS } from "./settings.js";
import { WTABS, workTabGo } from "./work.js";

export { RAIL_DEF, RAIL_ITEMS, railItem, railNorm };   /* the store's, on the page for the tests and ⌘K */

/** Where Customise was opened from: focus goes back there when it closes. */
export let RAILOPENER = /** @type {HTMLElement | null} */ (null);

/* every change is drawn at once and written to settings.json (a backup and a log line); if the write fails it is put back */
/** @param {any} cfg */
export async function railSave(cfg) {
  const was = railCfg.value; railCfg.value = railNorm(cfg); S.rail = railCfg.value;
  const ok = await writeSettings({ "dashboard.rail": railCfg.value });
  if (!ok) { railCfg.value = was; S.rail = was; }
  return ok;
}
/** Collapse or expand the sidebar (the toggle, ⌘\ and ⌘K), remembered in dashboard.rail's display. */
export function railToggle() { if (!railNarrow.value) railSave({ ...railCfg.value, display: railCollapsed.value ? "titles" : "icons" }); }
/** Open Customise sidebar; focus goes back to `opener` (or the current page's button) when it closes.
    @param {Element | null} [opener] */
export function railCustomise(opener) {
  railMoreOpen.value = false;
  RAILOPENER = /** @type {HTMLElement | null} */ (opener || document.querySelector('.rail button[aria-current="page"]') || $("#railMore"));
  railCustOpen.value = true;
}
/** ⌘K's "Customise the rail" (ask.js, Team 1's) calls this name: the same dialog. */
export const railPopOpen = railCustomise;
function railCustClosed() { railCustOpen.value = false; const o = RAILOPENER; RAILOPENER = null; if (o && o.isConnected && o.getClientRects().length) o.focus(); else $("#railMore")?.focus(); }
/** The current page's rail key, from the view (a project page is Projects, a person People, Help Settings). */
export function renderRail() {
  let cur = "";
  try { cur = { cockpit: "projects", mine: "work", help: "settings", person: "people", milestones: "projects", meeting: "today" }[shared.VIEW] || shared.VIEW; } catch (x) { /* VIEW not set yet */ }
  setRailView(cur);
}

/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootRail0007() {
  /* icons other screens draw with ic() (the panel's ⋯, drag handles, Move down), added here since BL-163 */
  Object.assign(ICONS, { grip: '<circle cx="9" cy="6" r="1"/><circle cx="15" cy="6" r="1"/><circle cx="9" cy="12" r="1"/><circle cx="15" cy="12" r="1"/><circle cx="9" cy="18" r="1"/><circle cx="15" cy="18" r="1"/>',
    arrowdown: '<path d="M12 5v14M19 12l-7 7-7-7"/>', more: '<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>' });
  Object.defineProperty(shared, "RAILCFG", { configurable: true, enumerable: true, get: () => railCfg.value, set: v => { railCfg.value = railNorm(v); } });
  railCfg.value = railNorm(S.rail);
  const mq = matchMedia("(max-width:1199px)"); railNarrow.value = mq.matches; mq.addEventListener("change", e => { railNarrow.value = e.matches; });
  effect(() => {        /* the shell follows the choice: the rail's width (--rail-w) and its icons-only look */
    const c = railCollapsed.value, nav = $(".rail");
    document.documentElement.classList.toggle("railicons", c);
    if (nav) { nav.classList.toggle("icons", c); nav.classList.toggle("collapsed", c); }
  });
  const onGo = (/** @type {string} */ id) => go(id);
  render(h(RailToggle, { onToggle: railToggle, keyName: MAC ? "⌘\\" : "Ctrl+\\" }), $("#railTogBox"));
  /* #139: Projects and Work open a list on hover (the active projects, the Work lists); a pick opens it, the icon alone still goes to the page */
  const flyouts = {
    projects: () => { const a = P.filter(p => p.active !== false && !p.archived);
      return a.length ? a.map(p => ({ id: p.code, name: p.name, health: p.health || "" })) : [{ id: "-", note: "No active projects" }]; },
    work: () => WTABS.map(t => ({ id: t.id, name: t.label })),
  };
  const onFly = (/** @type {string} */ id, /** @type {string} */ pick) => {
    if (id === "projects") go("cockpit", pick);
    else if (id === "work") { if (shared.VIEW !== "work") go("work"); if (shared.WT !== pick) workTabGo(pick); }
  };
  render(h(RailNav, { onGo, flyouts, onFly }), $("#railMain"));
  render(h(RailMore, { onGo, onCustomise: railCustomise }), $("#railFoot"));
  addHTML(document.body, "beforeend", html`<div id="railCustBox"></div>`);
  render(h(CustomiseSidebar, { onSave: railSave, onClose: railCustClosed }), $("#railCustBox"));
  document.addEventListener("click", e => { const t = /** @type {Element} */ (e.target); if (t.closest && t.closest("[data-railcust]")) railCustomise(t.closest("[data-railcust]")); });
  /* BL-191: a right-click anywhere on the sidebar (or the context-menu key, Shift+F10, on a focused page) opens Customise */
  document.addEventListener("contextmenu", e => { const t = /** @type {Element} */ (e.target); const nav = t.closest && t.closest(".rail"); if (!nav) return; e.preventDefault();
    const byKey = !e.clientX && !e.clientY, a = document.activeElement;
    railCustomise(t.closest(".rail button") || (byKey && a && a.closest && a.closest(".rail button")) || null); });
  /* ⌘\ (Ctrl+\ elsewhere) collapses or expands the sidebar, wherever focus is */
  document.addEventListener("keydown", e => { if ((e.metaKey || e.ctrlKey) && !e.altKey && !e.shiftKey && e.key === "\\") { e.preventDefault(); railToggle(); } });
  renderRail();
}
/* ===== BL-163 (sprint-rail) ===== Settings › General › Appearance: "Sidebar: Customise…" opens the same dialog as a right-click on the sidebar (BL-191) */
/* BL-231: what this block did at load, run in today's order by src/main.js */
export function bootRail0077() {
  const ap = SETSECTIONS.find(x => x.id === "appearance"), r0 = ap.render; ap.kw += " left rail sidebar navigation hide reorder order icons only titles customise collapse more";
  ap.render = () => r0() + row("Sidebar", `<button type="button" class="btn" id="railCustSet" data-railcust aria-haspopup="dialog">${ic("sliders")}Customise…</button>`, "Choose what is in the sidebar and what is in More, put them in your own order, or show icons only");
}

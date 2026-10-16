// @ts-check
/* stores/rail.js (BL-319 part 6, dev/COMPONENTS.md): the sidebar's store. The items, the saved choice and the signals
   the sidebar's components read: the choice (railCfg), the page it marks (railView), the counts on its badges
   (railCounts), whether More is open, whether the window is narrow. Old code changes them only through the functions
   here (setRailView, setRailCount); nothing writes into the sidebar's DOM.

   The saved choice is settings.json's dashboard.rail = {order, more, hidden, display}:
   - order: the pages in the sidebar, top to bottom; Today is always first;
   - more: the pages in More, at the bottom (BL-319: Intake, Files, Activity, Settings by default);
   - hidden: kept for the shape older versions wrote; a page it names now goes into More, so nothing is ever lost;
   - display: "titles", or "icons". "icons" is what older versions saved for the collapsed rail of icons only; it still works
     (#156): it means Labels when collapsed OFF, and the rail starts collapsed in a browser that has not chosen yet. Nothing
     writes it any more except the Customise sidebar dialog's "Icons only".

   #156 (the rail's three states): expanded (224px, labels beside the icons), collapsed with labels (76px, each label under its
   icon; the setting dashboard.rail_labels, default on), collapsed icons only (56px). The wordmark toggles it, remembered in this
   browser (localStorage). With no choice yet, the rail is expanded at 1100px and wider and collapsed below that; under 900px it
   is always collapsed. */
import { computed, signal } from "@preact/signals";
import { store } from "../core/page.js";

/** @typedef {{id: string, title: string, icon: string, badge?: string, group: "top"|"more", fixed?: boolean}} RailItem */
/** @typedef {{order: string[], more: string[], hidden: string[], display: "titles"|"icons"}} RailCfg */
/** @typedef {{n: number, label?: string}} RailCount */

/** Every page the sidebar can show. id is the view (and each button's data-v, so every handler and test that finds a
    button by it still works); badge is the id of its count; group is where it goes by default; Today is fixed first.
    @type {RailItem[]} */
export const RAIL_ITEMS = [
  { id: "today", title: "Today", icon: "today", badge: "vipBadge", group: "top", fixed: true },
  { id: "work", title: "Work", icon: "work", group: "top" },
  { id: "review", title: "Review", icon: "review", badge: "revBadge", group: "top" },
  { id: "projects", title: "Projects", icon: "projects", group: "top" },
  { id: "people", title: "People", icon: "people", group: "top" },
  { id: "inbox", title: "Intake", icon: "inbox", badge: "inboxBadge", group: "more" },
  { id: "files", title: "Files", icon: "folder", group: "more" },
  { id: "activity", title: "Activity", icon: "activity", group: "more" },
  { id: "settings", title: "Settings", icon: "gear", group: "more" },
];
/** @type {RailCfg} */
export const RAIL_DEF = {
  order: RAIL_ITEMS.filter(i => i.group === "top").map(i => i.id),
  more: RAIL_ITEMS.filter(i => i.group === "more").map(i => i.id),
  hidden: [],
  display: "titles",
};
/** @param {string} id */
export const railItem = id => RAIL_ITEMS.find(i => i.id === id);

/** The saved choice, made safe: unknown ids are left out, each page is in one list once, Today comes first and is never
    in More, a page in neither list is appended to its default group (so a later page never disappears), and a choice
    saved before More existed (no `more` list) takes the default More plus the pages it had hidden.
    @param {any} c
    @returns {RailCfg} */
export function railNorm(c) {
  c = c && typeof c === "object" ? c : {};
  const known = new Set(RAIL_ITEMS.map(i => i.id));
  const seen = new Set(["today"]);
  /** @param {any} a */
  const keep = a => (Array.isArray(a) ? a : []).filter(id => typeof id === "string" && known.has(id) && !seen.has(id) && !!seen.add(id));
  const hidden = Array.isArray(c.hidden) ? c.hidden : [];
  const more = keep(Array.isArray(c.more) ? [...c.more, ...hidden] : [...RAIL_DEF.more, ...hidden]);
  const order = ["today", ...keep(c.order)];
  for (const it of RAIL_ITEMS) if (!seen.has(it.id)) { seen.add(it.id); (it.group === "more" ? more : order).push(it.id); }
  return { order, more, hidden: [], display: c.display === "icons" ? "icons" : "titles" };
}

/** The saved choice (normalised). */
export const railCfg = signal(RAIL_DEF);
/** The page the sidebar marks as current (the rail key: Projects for a project page, People for a person …). */
export const railView = signal("today");
/** The counts on the badges, by page id: {n, label}. */
export const railCounts = signal(/** @type {Record<string, RailCount>} */ ({}));
/** Whether More's menu is open. */
export const railMoreOpen = signal(false);
/** Whether Customise sidebar is open. */
export const railCustOpen = signal(false);
/** The setting "Labels when collapsed" (dashboard.rail_labels, on by default). */
export const railLabelsOn = signal(true);
/** The window is 1100px wide or more: with no choice made yet the rail starts expanded. */
export const railWide = signal(true);
/** Under 900px the rail is always collapsed (the pinned rail), so the page keeps its room. */
export const railNarrow = signal(false);
const RAIL_KEY = "creaite-rail-collapsed";
/** This browser's choice (the wordmark toggle): true collapsed, false expanded, null none yet. */
export const railUser = signal(/** @type {boolean | null} */ (null));
/** Read the remembered choice (a private window or blocked storage: none). */
export function railLoadUser() { try { const v = store.get(RAIL_KEY, null); railUser.value = typeof v === "boolean" ? v : null; } catch (x) { railUser.value = null; } }
/** Remember the choice. @param {boolean} v */
export function railSetUser(v) { railUser.value = v; try { store.set(RAIL_KEY, v); } catch (x) { /* storage blocked: it holds for this page only */ } }
/** Collapsed: by the wordmark; else by what was saved before (display "icons") or the window's width. */
export const railCollapsed = computed(() => railNarrow.value
  || (railUser.value !== null ? railUser.value : railCfg.value.display === "icons" || !railWide.value));
/** Collapsed with each label under its icon (76px). */
export const railLabelled = computed(() => railCollapsed.value && railLabelsOn.value && railCfg.value.display !== "icons");
/** "expanded", "labels" or "icons". */
export const railMode = computed(() => !railCollapsed.value ? "expanded" : railLabelled.value ? "labels" : "icons");
/** What waits inside More: [title, count] for each page in More with a count. */
export const railMoreWaiting = computed(() => railCfg.value.more
  .map(id => /** @type {[string, number]} */ ([railItem(id).title, (railCounts.value[id] || { n: 0 }).n]))
  .filter(x => x[1] > 0));

/** @param {string} key the rail key of the page now shown */
export function setRailView(key) { railView.value = key; }
/** Set the count on a page's badge (0 hides it); `label` is what a screen reader hears for it.
    @param {string} id @param {number} n @param {string} [label] */
export function setRailCount(id, n, label) {
  const was = railCounts.value[id];
  if (was && was.n === n && was.label === label) return;
  railCounts.value = { ...railCounts.value, [id]: { n, label } };
}

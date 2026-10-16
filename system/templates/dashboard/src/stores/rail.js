// @ts-check
/* stores/rail.js (BL-319 part 6, dev/COMPONENTS.md): the sidebar's store. The items, the saved choice and the signals
   the sidebar's components read: the choice (railCfg), the page it marks (railView), the counts on its badges
   (railCounts), whether More is open, whether the window is narrow. Old code changes them only through the functions
   here (setRailView, setRailCount); nothing writes into the sidebar's DOM.

   The saved choice is settings.json's dashboard.rail = {order, more, hidden, display}:
   - order: the pages in the sidebar, top to bottom; Today is always first;
   - more: the pages in More, at the bottom (BL-319: Intake, Files, Activity, Settings by default);
   - hidden: kept for the shape older versions wrote; a page it names now goes into More, so nothing is ever lost;
   - display: "titles", or "icons" (collapsed: the 56px rail of icons). The collapse toggle and ⌘\ write it. */
import { computed, signal } from "@preact/signals";

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
/** Counts every navigation (go), so an open rail flyout folds whichever way it was opened. */
export const railNav = signal(0);
/** The counts on the badges, by page id: {n, label}. */
export const railCounts = signal(/** @type {Record<string, RailCount>} */ ({}));
/** Whether More's menu is open. */
export const railMoreOpen = signal(false);
/** Whether Customise sidebar is open. */
export const railCustOpen = signal(false);
/** A window under 1200px wide always shows the rail of icons (the toggle is hidden there), so the 212px sidebar never
    squeezes the page, the side peek or the top bar on a smaller screen. */
export const railNarrow = signal(false);
/** Collapsed: the 56px rail of icons. */
export const railCollapsed = computed(() => railNarrow.value || railCfg.value.display === "icons");
/** What waits inside More: [title, count] for each page in More with a count. */
export const railMoreWaiting = computed(() => railCfg.value.more
  .map(id => /** @type {[string, number]} */ ([railItem(id).title, (railCounts.value[id] || { n: 0 }).n]))
  .filter(x => x[1] > 0));

/** @param {string} key the rail key of the page now shown */
export function setRailView(key) { railView.value = key; railNav.value++; railMoreOpen.value = false; }   /* #139: every navigation folds any open flyout */
/** Set the count on a page's badge (0 hides it); `label` is what a screen reader hears for it.
    @param {string} id @param {number} n @param {string} [label] */
export function setRailCount(id, n, label) {
  const was = railCounts.value[id];
  if (was && was.n === n && was.label === label) return;
  railCounts.value = { ...railCounts.value, [id]: { n, label } };
}

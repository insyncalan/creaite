// @ts-check
/* stores/rejects.js (BL-315, dev/COMPONENTS.md): the reject reasons' store. The seven reasons, creaite's guess per pending
   row (from /api/review/guesses), the reasons menu that is open (RejectMenu reads it), the rows rejected while Review is
   open (drawn greyed with their chip until Review is left) and Activity › What you rejected's list. Old code changes them
   only through the functions here; nothing writes into the menu's DOM. */
import { signal } from "@preact/signals";

/** The seven, in the menu's order (tracker.REJECT_REASONS); the server's list replaces it when it answers. */
export const REASONS = ["Not an action", "Duplicate", "Chatter", "Already done", "Wrong project", "Doesn't need tracking", "For another team"];
export const rjReasons = signal(REASONS);

/** @typedef {{reason: string, why?: string, of?: string | null}} RjGuess */
/** creaite's guess per pending row, keyed "<file>#<ref>". @type {import("@preact/signals").Signal<Record<string, RjGuess>>} */
export const rjGuesses = signal({});
/** The pending rows the guesses were fetched for (so a re-render doesn't fetch again). */
export const rjGuessFor = signal("");

/** A row the menu acts on: its key, its file and item, its text, its guess and, for a reject, its reason now.
    @typedef {{key: string, file: string, ref: any, t: string, guess?: RjGuess | null, reason?: string | null, dup?: string | null}} RjRow */
/** What a pick means: one reason (and the item a Duplicate repeats), each row's own guess, or no reason.
    @typedef {{reason: string | null, dup?: string | null, guess?: boolean}} RjChoice */
/** @typedef {{id: string, t: string, strength?: string, why?: string}} RjCandidate */
/** The open menu: "reject" (Reject n because) or "reason" (a reject's reason changed).
    @typedef {{rows: RjRow[], anchor: HTMLElement | null, mode: "reject" | "reason", guesses: boolean, onPick: (c: RjChoice) => any,
      candidates?: () => Promise<RjCandidate[]>, onClose?: () => void}} RjMenu */
/** @type {import("@preact/signals").Signal<RjMenu | null>} */
export const rjMenu = signal(null);

/** Open the reasons menu. @param {RjMenu} m */
export function rjOpenMenu(m) { rjMenu.value = m; }
/** Close it; focus goes back to what opened it when `back`. @param {boolean} [back] */
export function rjCloseMenu(back) {
  const m = rjMenu.value; rjMenu.value = null;
  if (m && m.onClose) m.onClose();
  if (back && m && m.anchor && m.anchor.isConnected) m.anchor.focus({ preventScroll: true });
}

/** A row rejected while Review is open: greyed, with its reason as a chip, until Review is left.
    @typedef {{key: string, rk: string, file: string, ref: any, kind: string, p: string | null, rec: any, src: string, why: string,
      reason: string | null, dup: string | null, at: number, server: boolean}} RjGone */
/** @type {import("@preact/signals").Signal<RjGone[]>} */
export const rjGone = signal([]);
/** Add rows (a row rejected again replaces its earlier entry). @param {RjGone[]} L */
export function rjAddGone(L) { const keys = new Set(L.map(g => g.key)); rjGone.value = [...rjGone.value.filter(g => !keys.has(g.key)), ...L]; }
/** Take rows out (undone, or approved instead). @param {string[]} keys */
export function rjDropGone(keys) { const k = new Set(keys); rjGone.value = rjGone.value.filter(g => !k.has(g.key)); }
/** Change rows' reason. @param {string[]} keys @param {(g: RjGone) => Partial<RjGone>} f */
export function rjSetGone(keys, f) { const k = new Set(keys); rjGone.value = rjGone.value.map(g => k.has(g.key) ? { ...g, ...f(g) } : g); }
/** Review was left: the greyed rows go. */
export function rjLeave() { if (rjGone.value.length) rjGone.value = []; }

/** One of Activity's recent rejects (POST /api/review/rejects).
    @typedef {{key: string, file: string, ref: any, applied?: boolean, project?: string, table?: string, kind?: string, text?: string,
      reason?: string | null, duplicate_of?: string | null, at?: string}} RjRecent */
/** @type {import("@preact/signals").Signal<{state: "idle" | "loading" | "ok" | "off" | "error", items: RjRecent[], message?: string}>} */
export const rjRecent = signal({ state: "idle", items: [] });

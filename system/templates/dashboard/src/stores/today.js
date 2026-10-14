// @ts-check
/* stores/today.js (BL-293, dev/COMPONENTS.md §2): Today's shared state. The day the band shows is kept here only, in memory:
   never in the address, storage or settings, so a reload, a new visit or a new day opens on today (Alan, 13-10-2026). */
import { signal } from "@preact/signals";

/** The day the band shows (YYYY-MM-DD), or "" for today. */
export const selDay = signal("");

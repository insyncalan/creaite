// @ts-check
/* stores/capture.js (BL-301 C, dev/COMPONENTS.md §2): the capture drawer's shared state.
   - `capOpen`: whether the drawer is open (⌘⇧N, ⌘K "New note", "Note for this meeting" and the tests set it through
     openCapture in components/notes/CaptureDrawer.jsx).
   A note the drawer opens in full (Done and find updates, a recent note) goes through B's own way to a note, openNoteAt in
   notes.js: the project's Notes tab with that note open (#notes=ABC&n=<file>; Unfiled #notes=_portfolio&n=…), and for Done and
   find updates part E's Find updates beside it (&find=1), so a reload keeps it. */
import { signal } from "@preact/signals";

/** Whether the capture drawer is open. */
export const capOpen = signal(false);

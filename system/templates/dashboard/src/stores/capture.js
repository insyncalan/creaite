// @ts-check
/* stores/capture.js (BL-301 C, dev/COMPONENTS.md §2): the capture drawer's shared state, and the one way the page asks for a note
   to be opened in full.
   - `capOpen`: whether the drawer is open (⌘⇧N, ⌘K "New note", "Note for this meeting" and the tests set it through
     openCapture in components/notes/CaptureDrawer.jsx).
   - `noteRequest`: a note to open on its project's Notes tab, {code, path, find}. Done and find updates sets it with
     find: true (part E's panel opens beside the note), a recent note with find: false. The Notes tab (part B) reads it and
     clears it; the address is B's note page with E's flag (#notes=ABC&n=<file>&find=1; Unfiled #notes=_portfolio&n=…), so a
     reload keeps it. */
import { signal } from "@preact/signals";

/** Whether the capture drawer is open. */
export const capOpen = signal(false);

/** @typedef {{code: string, path: string, find: boolean}} NoteRequest */
/** The note the page has been asked to open in full, or null. @type {import("@preact/signals").Signal<NoteRequest|null>} */
export const noteRequest = signal(/** @type {NoteRequest|null} */ (null));

/** The address of a note on B's note page: #notes=<code>&n=<file name>, and &find=1 for Find updates (Unfiled notes are the
    portfolio's, #notes=_portfolio). @param {NoteRequest} r */
export function noteHref(r) {
  const file = String(r.path || "").split("/").pop() || "";
  return `#notes=${encodeURIComponent(r.code || "_portfolio")}&n=${encodeURIComponent(file)}${r.find ? "&find=1" : ""}`;
}

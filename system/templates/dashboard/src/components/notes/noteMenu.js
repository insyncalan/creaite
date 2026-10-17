// @ts-check
/* noteMenu (#194, Alan 17-10-2026): the one definition of the note's … menu. The open note's … button and a right-click (or the
   context-menu key, Shift+F10) on a note in the list both build their items here and run their picks here, so the two cannot drift.
   The menu always acts on the open note: the list opens the note first. */
import { noteMeta } from "../../stores/notes.js";
import { askDeleteNote } from "./DeleteNote.jsx";

/** The items for a note. @param {{pinned: boolean, confidential: boolean, path: string}} n @returns {import("../Menu.jsx").MenuItem[]} */
export function noteMenuItems({ pinned, confidential, path }) {
  return [{ id: "pin", name: pinned ? "Unpin" : "Pin", line: pinned ? "Take it off the top of the list" : "Keep it at the top of the list", icon: "flag" },
    { id: "conf", name: confidential ? "Not confidential" : "Mark confidential", line: confidential ? "Prep pages and Claude may read it again" : "Kept out of Prep pages; asks before its text goes to Claude", icon: "shield" },
    { id: "file", name: "Show the file", line: path, icon: "folder" },
    { id: "sep", sep: true }, { id: "del", name: "Delete note…", line: "Moves it to the archive; restore it from Files", icon: "trash", cls: "bad" }];
}

/** Run a pick on the open note. @param {string} id @param {{pinned: boolean, confidential: boolean, path: string}} n @param {(path: string) => void} onOpenFile */
export function noteMenuPick(id, { pinned, confidential, path }, onOpenFile) {
  if (id === "pin") noteMeta({ pinned: !pinned }, true);
  else if (id === "conf") noteMeta({ confidential: !confidential }, true);
  else if (id === "del") askDeleteNote();
  else onOpenFile(path);
}

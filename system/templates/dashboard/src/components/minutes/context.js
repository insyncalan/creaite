// @ts-check
/* The minutes view's own context (v2.1.0 P7; #268): what its section and extra renderers need beyond the sheet's SectionCtx:
   the open checks and what a check's button does, one change to the record (P4's ops), the whole document, the meeting's
   day for deadlines, the approve plan (each item's group, for the Track defaults and Approve minutes), the project's code,
   and opening a staged item. The view provides it around the sheet; the sheet itself knows nothing about minutes.
   #268: one version only: no distributed version, no Internal only marks. */
import { createContext } from "preact";

/** @typedef {import("./minutesDoc.js").Check} Check */
/** @typedef {import("../report/Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {import("./track.js").PlanItem} PlanItem */
/** @typedef {{checks: Check[], onCheck: (c: Check, action: string) => void,
    change: (op: Record<string, any>, undo?: Record<string, any>|null) => Promise<boolean>,
    doc: SheetDoc, day: string, plan: PlanItem[]|null, project: string, openItem: (ref: string) => void}} MinutesCtxValue */

export const MinutesCtx = createContext(/** @type {MinutesCtxValue|null} */ (null));

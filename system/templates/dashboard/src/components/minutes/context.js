// @ts-check
/* The minutes view's own context (v2.1.0 P7): what its section, row and extra renderers need beyond the sheet's SectionCtx and
   RowCtx (dev/sprints/v210-contract.md §4.3): the open checks and what a check's button does, one change to the record (P4's
   ops), the whole document's layout (Internal only marks), the meeting's day for deadlines, and whether the distributed version
   is on. The view provides it around the sheet; the sheet itself knows nothing about minutes. */
import { createContext } from "preact";

/** @typedef {import("./minutesDoc.js").Check} Check */
/** @typedef {import("../report/SheetStub.jsx").SheetDoc} SheetDoc */
/** @typedef {{checks: Check[], onCheck: (c: Check, action: string) => void,
    change: (op: Record<string, any>, undo?: Record<string, any>|null) => Promise<boolean>,
    setDoc: (doc: SheetDoc, why: string) => void, doc: SheetDoc, day: string, distributed: boolean, partner: boolean,
    openItem: (ref: string) => void}} MinutesCtxValue */

export const MinutesCtx = createContext(/** @type {MinutesCtxValue|null} */ (null));

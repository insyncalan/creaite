// @ts-check
/* Intake's icons (#232-A, v2.6.0): the shapes the locked mockup (intake-review-combined-v2, 19-10-2026) draws, as element data, so
   a component draws them with Preact and nothing here is HTML. The same 24px grid, 1.8 stroke, round caps and currentColor as
   core/dom.js ic() and components/Icon.jsx (the shared ICONS table is 232-C's file; the tray here is the mockup's, Q8). */
import { h } from "preact";

/** @typedef {[string, Record<string, string>]} Shape */
/** Each icon as its shapes. @type {Record<string, Shape[]>} */
export const IR_ICONS = {
  /* the stages: Arrived (a tray), Drafted (a document with lines), Approved (a ticked circle), Show all (layers) */
  tray: [["path", { d: "M4 13l2.5-8h11L20 13v6H4z" }], ["path", { d: "M4 13h5l1 2h4l1-2h5" }]],
  drafted: [["path", { d: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" }], ["path", { d: "M14 3v5h5M9 13h6M9 17h4" }]],
  approved: [["circle", { cx: "12", cy: "12", r: "9" }], ["path", { d: "M8 12.5l3 3 5-6" }]],
  all: [["path", { d: "M12 3l9 5-9 5-9-5z" }], ["path", { d: "M3 13l9 5 9-5" }]],
  /* the page's controls */
  upload: [["path", { d: "M12 16V4M7 9l5-5 5 5M4 20h16" }]],
  stop: [["rect", { x: "6", y: "6", width: "12", height: "12", rx: "2" }]],     /* the refresh's Stop while it runs (core/dom.js's stop) */
  refresh: [["path", { d: "M3 12a9 9 0 0 1 15.5-6.2L21 8M21 3v5h-5M21 12a9 9 0 0 1-15.5 6.2L3 16M3 21v-5h5" }]],
  /* a row's kind: a calendar meeting or a file */
  meeting: [["rect", { x: "4", y: "5", width: "16", height: "15", rx: "2" }], ["path", { d: "M4 10h16M9 3v4M15 3v4" }]],
  file: [["path", { d: "M6 3h8l4 4v14H6z" }], ["path", { d: "M14 3v4h4" }]],
  /* the kinds of proposal (the mockup's KI), for the proposal rows */
  Action: [["path", { d: "M9 11l3 3 8-8" }], ["path", { d: "M5 12v7h14v-7" }]],
  Risk: [["path", { d: "M12 3l10 18H2z" }], ["path", { d: "M12 10v5M12 18v.4" }]],
  Issue: [["circle", { cx: "12", cy: "12", r: "9" }], ["path", { d: "M12 7.5v5.5M12 16.2v.4" }]],
  Dependency: [["path", { d: "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1" }], ["path", { d: "M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1" }]],
  Decision: [["path", { d: "M5 21V4M5 4h13l-3 4 3 4H5" }]],
  Minutes: [["path", { d: "M6 3h8l4 4v14H6z" }], ["path", { d: "M14 3v4h4" }]],
};

/** An icon as an <svg>. @param {{name: string, cls?: string}} props */
export function IrIcon({ name, cls }) {
  return h("svg", { class: `i${cls ? " " + cls : ""}`, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", "stroke-width": "1.8",
    "stroke-linecap": "round", "stroke-linejoin": "round", "aria-hidden": "true", "data-iric": name },
  (IR_ICONS[name] || []).map(([tag, attrs], i) => h(tag, { key: i, ...attrs })));
}

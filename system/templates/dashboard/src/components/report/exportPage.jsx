// @ts-check
/* exportPage (#226, #219): the report's HTML and PDF export is the sheet's own "Show as exported" page. This draws that page once more,
   off screen, in a throwaway frame fixed to the light theme (so a dark dashboard never reaches a file), with the same SheetPage and the
   same renderers the screen uses, and hands back what the server needs to make the file: the page's markup, the style rules that
   apply to it (the dashboard's own stylesheet, cut down to the rules some element of the page matches, so the file draws as the screen
   does and carries no rule it doesn't use), the palette's name and the version drawn. The logos are already data addresses (the
   weekly view's logo store), so the file needs nothing else. The server never trusts this: it rebuilds the markup through an
   allow-list and checks it against its own copy of the report (export_page.py). Nothing is sent from here. */
import { render } from "preact";
import { SheetPage } from "./SheetPage.jsx";

/** @typedef {import("./Sheet.jsx").SheetDoc} SheetDoc */
/** @typedef {{viewId: string, viewClass: string, sheetClass: string}} ExportView */

export const WEEKLY_EXPORT = { viewId: "v-weekly", viewClass: "wrview", sheetClass: "wrsheet" };
export const CLIENT_EXPORT = { viewId: "v-clientreport", viewClass: "crview", sheetClass: "crsheet" };

const PSEUDO_ELEMENT = /::?(?:before|after|first-line|first-letter|marker|selection|placeholder|backdrop|file-selector-button)|::[\w-]+/g;
const NOOP = () => {};

/** Whether some element of the frame's page matches a selector list (pseudo-elements stripped; a selector the browser can't read is kept).
    @param {Document} d @param {string} selector */
function used(d, selector) {
  try { return !!d.querySelector(selector.replace(PSEUDO_ELEMENT, "")); } catch (e) { return true; }
}

/** The style rules of the dashboard that the frame's page uses, in order, with the media and supports blocks that hold at the frame's
    size flattened (a file has no dashboard layout to switch between) and the dark-scheme ones left out.
    @param {Window} win @param {Document} d @param {Document} from @returns {string} */
function usedRules(win, d, from) {
  /** @type {string[]} */
  const out = [];
  const walk = (/** @type {CSSRuleList} */ rules) => {
    for (const r of Array.from(rules)) {
      if (r.constructor.name === "CSSStyleRule") { if (used(d, /** @type {CSSStyleRule} */ (r).selectorText)) out.push(r.cssText); }
      else if (r.constructor.name === "CSSMediaRule") {
        const m = /** @type {CSSMediaRule} */ (r), cond = m.conditionText || m.media.mediaText;
        if (!/prefers-color-scheme\s*:\s*dark/i.test(cond) && win.matchMedia(cond).matches) walk(m.cssRules);
      } else if (r.constructor.name === "CSSSupportsRule") {
        const sr = /** @type {CSSSupportsRule} */ (r);
        if (win.CSS.supports(sr.conditionText)) walk(sr.cssRules);
      }
    }
  };
  for (const sheet of Array.from(from.styleSheets)) { try { walk(sheet.cssRules); } catch (e) { /* a sheet from elsewhere can't be read: none of ours is */ } }
  return out.join("\n");
}

/** The report drawn as it is exported, as the post the export route takes. Resolves null when the page can't be drawn (the route then
    makes the plain file). @param {SheetDoc} doc the saved report @param {any} renderers the view's renderers
    @param {ExportView} view the view's wrapper names @param {number} version the saved version @returns {Promise<null | {html: string, css: string, palette: string, version: number}>} */
export async function reportExportPage(doc, renderers, view, version) {
  const frame = document.createElement("iframe");
  frame.setAttribute("aria-hidden", "true"); frame.tabIndex = -1;
  frame.style.cssText = "position:fixed;left:-12000px;top:0;width:1200px;height:1600px;border:0;visibility:hidden;pointer-events:none";
  document.body.append(frame);
  try {
    const w = /** @type {Window} */ (frame.contentWindow), d = /** @type {Document} */ (frame.contentDocument);
    const palette = document.documentElement.dataset.palette || "";
    d.open(); d.write(`<!doctype html><html data-theme="light"${palette ? ` data-palette="${palette.replace(/[^\w -]/g, "")}"` : ""}><head><meta charset="utf-8"></head><body></body></html>`); d.close();
    for (const st of Array.from(document.querySelectorAll("style"))) { const c = d.createElement("style"); c.textContent = st.textContent; d.head.append(c); }
    const host = d.createElement("div"); host.id = view.viewId; host.className = "export-view"; d.body.append(host);
    const props = { doc, renderers, extras: [], exported: true, readOnly: true, peerDoc: null, peerLabel: "", side: /** @type {""} */ (""), onChange: NOOP,
      onOpenItem: undefined, onEvent: NOOP, onRedraft: undefined, aiFor: () => undefined, checks: [], refocus: { current: null }, match: null };
    render(<div class={view.viewClass}><div class={view.sheetClass}><div class="sheet-root"><div class="sheet-area sheet-exported"><div class="sheet-scroll"><div class="sheet-one">
      <div class="sheet-fit"><div class="sheet-a4"><SheetPage {...props} /></div></div></div></div></div></div></div></div>, host);
    await new Promise(r => setTimeout(r, 250));                       // the timeline fits itself to its box after the first draw
    await Promise.all(Array.from(d.images).map(i => i.complete ? null : new Promise(r => { i.onload = i.onerror = () => r(null); })));
    const html = host.outerHTML, css = usedRules(w, d, document);
    render(null, host);
    return html && css ? { html, css, palette, version } : null;
  } catch (e) {
    console.error("export page:", e);                                  // the route then makes the plain file
    return null;
  } finally {
    frame.remove();
  }
}

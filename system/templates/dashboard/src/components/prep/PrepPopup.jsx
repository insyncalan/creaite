// @ts-check
/* PrepPopup (BL-286 parts A and B): the top of the Prep popup, the header and the one toolbar, and the facts line and
   invite above its lists. The lists themselves (open actions, risks and issues, decisions, early warnings, recent reports)
   are still drawn by drawPrep() into #prepBody, in two columns; old code never writes into the containers mounted here. */
import { render } from "preact";
import { PrepFacts } from "./PrepFacts.jsx";
import { PrepHead } from "./PrepHead.jsx";
import { PrepToolbar } from "./PrepToolbar.jsx";

export function PrepPopup() {
  return (
    <>
      <PrepHead />
      <PrepToolbar />
    </>
  );
}

/** Mount the popup's components once, into the dialog's #prepTop and #prepLead.
    @param {Element} top @param {Element} lead */
export function mountPrepPopup(top, lead) {
  render(<PrepPopup />, top);
  render(<PrepFacts />, lead);
}

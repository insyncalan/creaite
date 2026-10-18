// @ts-check
/* #202 (lifted here for #207, the app's top bar uses the same rule; behaviour unchanged): the report header's rule, in one place (mockup report-banner, option A, as Jarvis read Alan's note; not yet confirmed by Alan,
   so change it here and nowhere else). Any scroll down hides the search bar and the title block at once (HEADER_HIDE_OVER 0 px);
   scrolling up never brings them back (HEADER_SHOW_ON_UP Infinity px); they return only with the top of the report at the top
   (scrollTop at or under HEADER_SHOW_AT_TOP). */
export const HEADER_HIDE_OVER = 0;
export const HEADER_SHOW_ON_UP = Infinity;
export const HEADER_SHOW_AT_TOP = 0;
/** What the header does after a scroll. @param {number} top scrollTop now @param {number} delta px moved since the last scroll event (down is +)
    @param {number} up px scrolled up in a row @returns {"hide"|"show"|"keep"} */
export function headerPolicy(top, delta, up) {
  if (top <= HEADER_SHOW_AT_TOP) return "show";
  if (delta > HEADER_HIDE_OVER) return "hide";
  if (delta < 0 && up >= HEADER_SHOW_ON_UP) return "show";
  return "keep";
}

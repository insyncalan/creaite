// @ts-check
/* hovertime (#140, #147; the one hover standard, #143): the times a hover popup waits, named once. Nothing that pops up on
   hover is instant (Alan, 16-10-2026), and no feature carries a number of its own. Same names and values as #143's
   core/hover.js (CARD_OPEN, CARD_CLOSE, MENU_OPEN, MENU_CLOSE), so that module replaces this one when it lands.
   A card opens after the pointer has rested on its trigger and closes after a short grace, so the pointer can travel from the
   trigger onto the card; a keyboard focus opens it at once. */
/** A hover card opens this long after the pointer rests on its trigger (ms). */
export const CARD_OPEN = 600;
/** A hover card closes this long after the pointer leaves the trigger and the card (ms). */
export const CARD_CLOSE = 300;
/** A hover menu opens this long after the pointer rests on its button (ms). */
export const MENU_OPEN = 200;
/** A hover menu closes this long after the pointer leaves (ms). */
export const MENU_CLOSE = 300;

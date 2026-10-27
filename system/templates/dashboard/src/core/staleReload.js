// @ts-check
/* core/staleReload.js (#370): what the event stream does when the server refuses it as stale (a tab left open across a restart).
   Pure: the page passes in the storage and the reload, dev/tests/test_stale_events_370.py runs this file under Node.
   The first stale refusal reloads the page once (the new page has the new token); the mark that says so lives in sessionStorage.
   A second stale refusal after that reload shows the existing banner instead, so a page never reloads in a loop. A refusal that
   is not stale never reloads. A stream that opens clears the mark, so a later restart gets its own reload. */
export const STALE_RELOAD_KEY = "creaite.staleReload";

/** @param {any} mem a Storage, or anything with getItem, setItem and removeItem */
function read(mem){ try{ return !!mem&&mem.getItem(STALE_RELOAD_KEY)==="1"; }catch(e){ return false; } }
/** @param {any} mem */
export function staleMarkClear(mem){ try{ if(mem) mem.removeItem(STALE_RELOAD_KEY); }catch(e){ return; } }

/** What to do with a refused stream: "reload", "banner" or "none".
 *  @param {number} code the reply's code
 *  @param {any} body the reply's JSON, or null
 *  @param {any} mem sessionStorage
 *  @param {() => void} reload location.reload */
export function staleEventsAct(code,body,mem,reload){
  if(code!==403||!body||body.stale!==true) return "none";
  if(read(mem)) return "banner";
  try{ if(!mem) return "banner"; mem.setItem(STALE_RELOAD_KEY,"1"); }catch(e){ return "banner"; }   /* no mark can be kept: never risk a loop */
  reload(); return "reload"; }

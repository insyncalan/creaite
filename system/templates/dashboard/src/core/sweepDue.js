// @ts-check
/* core/sweepDue.js (#370): which Today line the mail and Teams check shows, and which routes a Health fix may call. Pure functions,
   no imports, no DOM: dev/tests/test_sweep_failed_370.py runs this file under Node. */

/** The one route a Health fix may make the page call itself (Check now starts the server's own catch-up). */
export const FIX_CALLS = ["/api/day/catchup"];

/** Whether the page may post to this fix's `call`: only a route in FIX_CALLS. @param {any} call */
export const fixCallAllowed = call => typeof call === "string" && FIX_CALLS.includes(call);

/** Which line Today shows for the check: "failed" (it didn't run; not dismissible while it holds), "due" (not checked yet; can be
 *  dismissed) or "" (none). @param {any} sd the build's sweep_due
 *  @param {{dev?: boolean, setupBlocks?: boolean, dismissed?: boolean}} [ctx] */
export function sweepDueLine(sd, ctx){
  const c=ctx||{};
  if(!(sd&&sd.due)||c.dev||c.setupBlocks) return "";
  if(sd.failed) return "failed";
  return c.dismissed?"":"due";
}

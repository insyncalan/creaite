// @ts-check
/* core/finderReveal.js (#374): what Show in Finder asks the server to do for a changed file. Pure: no page, no network.
   The server's rule (live_server OPEN_OK) is mirrored here so the button is only offered where the server would act.

   FINDER_REVEAL is the one switch (on since the route was re-checked):
   - false: the button opens the file's PARENT FOLDER through /api/open (today's behaviour);
   - true: the button sends the file to the existing token-checked /api/report/reveal (report_server.reveal_route), which selects
     it in its folder (Finder, Explorer). The request carries reveal:true, which the page uses to choose the route and which is
     never sent on to the server. */
export const FINDER_REVEAL=true;
export const FINDER_OPEN_OK=/^(projects|inbox|system\/staging\/drafts)\/.+$/;
const safe=p=>FINDER_OPEN_OK.test(p)&&!p.split("/").includes("..");
/* finderRequest(path[, reveal]) -> the request (the page picks the route from reveal), or null when no button is offered. */
export function finderRequest(path, reveal=FINDER_REVEAL){ const p=String(path||"");
  if(reveal) return safe(p)?{path:p,reveal:true}:null;
  const parent=p.split("/").slice(0,-1).join("/"); return safe(parent)?{path:parent}:null; }
/* A Deleted row, or a create that was undone, has no file to show. */
export function finderCanShow(c){ return !((c.op==="delete"&&!c.undone)||(c.op==="create"&&c.undone)); }

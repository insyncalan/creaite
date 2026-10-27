// @ts-check
/* core/pageErrors.js (#370): where a page error came from, as the function name and the line of the top stack frame and nothing
   else. Pure functions, no imports, no DOM: dev/tests/test_page_errors_370.py runs this file under Node. The page's error hooks
   (core/server.js diagHook) send the result as `source` and `line`; the server logs "view: message (source:line)".
   Never the path, the address or any text of the message: only a short name made of letters, digits, _ $ and . and a whole number. */

/** The top frame of a stack as {source, line}, or null when the stack has no frame this can read.
 *  @param {any} stack */
export function topFrame(stack){
  if(typeof stack!=="string") return null;
  for(const ln of stack.split("\n").slice(0,40)){
    const t=ln.trim();
    let m=/^at\s+(?:async\s+)?(?:new\s+)?([^\s(]+)\s+\(.*?:(\d+):\d+\)$/.exec(t);          /* V8: at name (address:line:col) */
    if(!m) m=/^at\s+()\S*?:(\d+):\d+$/.exec(t);                                           /* V8: at address:line:col (no name) */
    if(!m) m=/^([^@\s]*)@.*?:(\d+):\d+$/.exec(t);                                          /* Firefox and Safari: name@address:line:col */
    if(!m) continue;
    const name=String(m[1]||"").split(/[./]/).pop().replace(/[^\w$]/g,"").slice(0,60), line=Number(m[2]);
    if(!Number.isFinite(line)||line<0||line>9999999) continue;
    return {source:name||"anonymous",line};
  }
  return null; }
/** What an error object gives the hook, or null (the hook then does what it did before).
 *  @param {any} err */
export function errorFrame(err){ return err&&typeof err==="object"?topFrame(err.stack):null; }

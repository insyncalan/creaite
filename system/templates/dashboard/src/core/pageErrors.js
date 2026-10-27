// @ts-check
/* core/pageErrors.js (#370): where a page error came from, as the function name and the line of the top stack frame and nothing
   else. Pure functions, no imports, no DOM: dev/tests/test_page_errors_370.py runs this file under Node. The page's error hooks
   (core/server.js diagHook) send the result as `source` and `line`; the server logs "view: message (source:line)".
   Never the path, the address or any text of the message: only a short name made of letters, digits, _ $ and . and a whole number. */

/** The top frame of a stack as {source, line}, or null when the stack has no frame this can read.
 *  @param {any} stack */
export function topFrame(stack){
  if(typeof stack!=="string") return null;
  let lines=stack.split("\n");
  const first=lines.findIndex(l=>/^\s+at\s/.test(l));        /* V8: the message (any number of lines) comes before the first "    at " frame, and is never read as a frame */
  if(first>0) lines=lines.slice(first);
  else if(first<0&&/^[\w$.]*(Error|Exception)(:|\s|$)/.test(lines[0])) return null;      /* a V8 message with no frame: nothing in it is a frame */
  for(const ln of lines.slice(0,40)){
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

/** The frame when the error has one, else today's values. @param {any} err @param {any} source @param {any} line */
export function withFrame(err,source,line){ const f=errorFrame(err); return f?{source:f.source,line:f.line}:{source,line}; }
/** What the page's "error" hook sends for an ErrorEvent: {message, source, line}. @param {any} e */
export function errorReport(e){ const f=withFrame(e&&e.error,e&&e.filename,e&&e.lineno); return {message:e&&e.message,source:f.source,line:f.line}; }
/** What the "unhandledrejection" hook sends for a PromiseRejectionEvent: {message, source, line}. @param {any} e */
export function rejectionReport(e){ const r=e&&e.reason, f=withFrame(r,"promise",0);
  return {message:r&&r.message?r.message:r,source:f.source,line:f.line}; }

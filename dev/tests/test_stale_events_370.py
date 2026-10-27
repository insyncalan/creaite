"""#370 (D2): a tab left open across a server restart reloads once when the event stream is refused as stale, and says so
(the existing banner, with the server's STALE_PAGE words) if the reload does not clear it. A refusal that is not stale never reloads.

Run: python3 dev/tests/test_stale_events_370.py     (needs Node for the decision; skipped otherwise)

1. src/core/staleReload.js under Node, with a fake storage and a counting reload: first stale 403 reloads, the second shows the banner,
   a plain 403 or a 200 does nothing, a storage that throws never reloads, a stream that opened clears the mark.
2. The page: the fetch wrapper (milestones.js) hands every refused /api call to it; the stream reader (server.js) uses its answer.
3. The server's stale body is the shape the page reads (pinned by text, live_server.py is not imported).
4. Mutants.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
MOD = REPO / "system/templates/dashboard/src/core/staleReload.js"
SERVER_JS = REPO / "system/templates/dashboard/src/core/server.js"
LIVE = REPO / "system/scripts/live_server.py"
MILESTONES = REPO / "system/templates/dashboard/src/milestones.js"

SCRIPT = """
const f = await import(%s); const out = {};
const mk = () => { const m = new Map(); return { getItem: k => m.has(k) ? m.get(k) : null, setItem: (k, v) => m.set(k, String(v)), removeItem: k => m.delete(k), m }; };
const body = { ok: false, stale: true, message: "The live server was restarted since this page was opened." };
let n = 0; const reload = () => { n++; };
const st = mk();
out.first = f.staleEventsAct(403, body, st, reload); out.afterFirst = n;
out.second = f.staleEventsAct(403, body, st, reload); out.afterSecond = n;
const st2 = mk();
out.plain = [f.staleEventsAct(403, { ok: false, message: "Not allowed" }, st2, reload), f.staleEventsAct(403, null, st2, reload), f.staleEventsAct(403, { stale: "yes" }, st2, reload),
  f.staleEventsAct(200, body, st2, reload), f.staleEventsAct(500, body, st2, reload)];
out.plainReloads = n - 1; out.plainMark = st2.m.size;
f.staleMarkClear(st); out.third = f.staleEventsAct(403, body, st, reload); out.afterClear = n;
const bad = { getItem() { throw new Error("blocked"); }, setItem() { throw new Error("blocked"); }, removeItem() { throw new Error("blocked"); } };
const before = n; out.blocked = f.staleEventsAct(403, body, bad, reload); out.blockedReloads = n - before;
out.nostore = f.staleEventsAct(403, body, null, reload); out.nostoreReloads = n - before;
f.staleMarkClear(bad); f.staleMarkClear(null);
/* the fetch wrapper: ANY /api refusal decides, whichever call is refused first */
const w = mk(); let wn = 0; const wr = () => { wn++; };
out.wHere = f.staleApiAct("/api/here", 403, body, w, wr); out.wHereReloads = wn;
out.wEvents = f.staleApiAct("/api/events", 403, body, w, wr); out.wEventsReloads = wn;
const w2 = mk(); let wn2 = 0; const wr2 = () => { wn2++; };
out.wOther = [f.staleApiAct("/app/x.js", 403, body, w2, wr2), f.staleApiAct("", 403, body, w2, wr2), f.staleApiAct(undefined, 403, body, w2, wr2),
  f.staleApiAct("/api/data", 403, { ok: false }, w2, wr2), f.staleApiAct("/api/data", 200, body, w2, wr2)];
out.wOtherReloads = wn2; out.wOtherMark = w2.m.size;
const w3 = mk(); out.wPulse = f.staleApiAct("/api/pulse?x=1", 403, body, w3, () => {});
/* the stream's answer: an opened stream clears the mark, a refusal leaves it, nothing else touches it */
const s1 = mk(); s1.setItem(f.STALE_RELOAD_KEY, "1");
out.sSkip = [f.staleStreamAnswer(500, false, true, s1), f.staleStreamAnswer(200, true, false, s1)]; out.sSkipMark = s1.m.size;
out.sRefused = f.staleStreamAnswer(403, false, true, s1); out.sRefusedMark = s1.m.size;
out.sOpen = f.staleStreamAnswer(200, true, true, s1); out.sOpenMark = s1.m.size;
out.sNull = f.staleStreamAnswer(200, true, true, null);
process.stdout.write(JSON.stringify(out));
"""


def run_node(path=MOD):
    tmp = Path(tempfile.mkdtemp(prefix="se370"))
    try:
        f = tmp / "staleReload.mjs"
        f.write_text(Path(path).read_text(encoding="utf-8"), encoding="utf-8")
        r = subprocess.run(["node", "--input-type=module", "-e", SCRIPT % json.dumps(f.as_uri())], capture_output=True, text=True, timeout=60)
        if r.returncode:
            raise RuntimeError(r.stderr[-800:])
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _events_ok(o):
    return (o["first"] == "reload" and o["afterFirst"] == 1 and o["second"] == "banner" and o["afterSecond"] == 1
            and o["plain"] == ["none"] * 5 and o["plainReloads"] == 0 and o["plainMark"] == 0
            and o["third"] == "reload" and o["afterClear"] == 2)


def _storage_ok(o):
    return (o["blocked"] == "banner" and o["blockedReloads"] == 0 and o["nostore"] == "banner" and o["nostoreReloads"] == 0)


def _wrapper_ok(o):
    return (o["wHere"] == "reload" and o["wHereReloads"] == 1 and o["wEvents"] == "banner" and o["wEventsReloads"] == 1
            and o["wOther"] == ["none"] * 5 and o["wOtherReloads"] == 0 and o["wOtherMark"] == 0 and o["wPulse"] == "reload")


def _stream_ok(o):
    return (o["sSkip"] == ["skip", "skip"] and o["sSkipMark"] == 1 and o["sRefused"] == "refused" and o["sRefusedMark"] == 1
            and o["sOpen"] == "open" and o["sOpenMark"] == 0 and o["sNull"] == "open")


def good(o):
    return _events_ok(o) and _storage_ok(o) and _wrapper_ok(o) and _stream_ok(o)


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Decision(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.o = run_node()

    def test_the_first_stale_refusal_reloads_once(self):
        self.assertEqual((self.o["first"], self.o["afterFirst"]), ("reload", 1))

    def test_the_second_shows_the_banner_and_does_not_reload_again(self):
        self.assertEqual((self.o["second"], self.o["afterSecond"]), ("banner", 1))

    def test_a_refusal_that_is_not_stale_never_reloads(self):
        self.assertEqual(self.o["plain"], ["none"] * 5)
        self.assertEqual((self.o["plainReloads"], self.o["plainMark"]), (0, 0))

    def test_an_opened_stream_clears_the_mark_so_a_later_restart_reloads_again(self):
        self.assertEqual((self.o["third"], self.o["afterClear"]), ("reload", 2))

    def test_storage_that_cannot_be_used_never_risks_a_loop(self):
        self.assertEqual((self.o["blocked"], self.o["blockedReloads"], self.o["nostore"], self.o["nostoreReloads"]), ("banner", 0, "banner", 0))


    def test_whichever_api_call_is_refused_first_reloads_once_then_the_banner(self):
        """The review's case: /api/here is refused before /api/events. The first reloads; the next shows the banner."""
        self.assertEqual((self.o["wHere"], self.o["wHereReloads"]), ("reload", 1))
        self.assertEqual((self.o["wEvents"], self.o["wEventsReloads"]), ("banner", 1))
        self.assertEqual(self.o["wPulse"], "reload")

    def test_outside_the_api_or_not_stale_the_wrapper_does_nothing(self):
        self.assertEqual(self.o["wOther"], ["none"] * 5)
        self.assertEqual((self.o["wOtherReloads"], self.o["wOtherMark"]), (0, 0))

    def test_an_opened_stream_clears_the_mark_and_nothing_else_does(self):
        self.assertEqual((self.o["sSkip"], self.o["sSkipMark"]), (["skip", "skip"], 1))
        self.assertEqual((self.o["sRefused"], self.o["sRefusedMark"]), ("refused", 1))
        self.assertEqual((self.o["sOpen"], self.o["sOpenMark"], self.o["sNull"]), ("open", 0, "open"))


class Wired(unittest.TestCase):
    def setUp(self):
        self.js = SERVER_JS.read_text(encoding="utf-8")

    def test_the_fetch_wrapper_decides_for_every_api_refusal(self):
        ms = MILESTONES.read_text(encoding="utf-8")
        self.assertIn('import { staleApiAct, staleStore } from "./core/staleReload.js"', ms)
        self.assertRegex(ms, r'const a=staleApiAct\(String\(typeof u==="string"\?u:\(u&&u\.url\)\|\|""\),r\.status,j,staleStore\(\),\(\)=>location\.reload\(\)\)')
        self.assertRegex(ms, r'if\(a==="banner"\) staleShow\(j\.message\); else if\(a==="reload"\) shared\.STALE=true;')
        self.assertNotRegex(ms, r"if\(j&&j\.stale\) staleShow")           # the old, unconditional banner

    def test_the_stream_reader_uses_the_answer_and_the_banner_uses_the_servers_words(self):
        self.assertIn('import { staleStreamAnswer, staleStore } from "./staleReload.js"', self.js)
        self.assertRegex(self.js, r'export async function evRead\(res,ctl\)\{ if\(staleStreamAnswer\(res\.status,res\.ok,!!res\.body,staleStore\(\)\)!=="open"\) return;')
        self.assertNotIn("evRefused", self.js)

    def test_the_reply_shape_the_page_reads_is_the_servers(self):
        t = LIVE.read_text(encoding="utf-8")
        self.assertIn('self.send(403, {"ok": False, "stale": True, "message": STALE_PAGE})', t)
        self.assertRegex(t, r'STALE_PAGE = "The live server was restarted since this page was opened\.')


@unittest.skipUnless(shutil.which("node"), "needs Node")
class Mutants(unittest.TestCase):
    def caught(self, old, new):
        src = MOD.read_text(encoding="utf-8")
        self.assertIn(old, src)
        tmp = Path(tempfile.mkdtemp(prefix="se370m"))
        try:
            m = tmp / "m.js"
            m.write_text(src.replace(old, new, 1), encoding="utf-8")
            try:
                return not good(run_node(m))
            except RuntimeError:
                return True
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_each_mutant_is_caught(self):
        self.assertTrue(self.caught('if(code!==403||!body||body.stale!==true) return "none";', 'if(code!==403) return "none";'), "reloads on a plain 403")
        self.assertTrue(self.caught('if(read(mem)) return "banner";', ''), "reloads every time")
        self.assertTrue(self.caught('try{ if(!mem) return "banner"; mem.setItem(STALE_RELOAD_KEY,"1"); }catch(e){ return "banner"; }', 'try{ if(mem) mem.setItem(STALE_RELOAD_KEY,"1"); }catch(e){}'), "reloads when the mark cannot be kept")
        self.assertTrue(self.caught('if(mem) mem.removeItem(STALE_RELOAD_KEY);', ''), "never clears the mark")
        self.assertTrue(self.caught('reload(); return "reload"; }', 'return "reload"; }'), "says reload but does not")
        self.assertTrue(self.caught('String(url||"").includes("/api/")?staleEventsAct(code,body,mem,reload):"none"', 'staleEventsAct(code,body,mem,reload)'), "acts outside /api")
        self.assertTrue(self.caught('String(url||"").includes("/api/")?staleEventsAct(code,body,mem,reload):"none"', 'url==="/api/events"?staleEventsAct(code,body,mem,reload):"none"'), "only the stream decides")
        self.assertTrue(self.caught("  staleMarkClear(mem); return \"open\"; }", "  return \"open\"; }"), "evRead never clears the mark")
        self.assertTrue(self.caught("  if(code===403) return \"refused\";\n", ""), "a refusal is read as a stream")


if __name__ == "__main__":
    unittest.main()

"""BL-262: reopening ask creaite shows the chat at once, as it was, never redrawn. A real browser against the real live server,
with a stand-in `claude` whose runs can be held part-way (a "gated" message waits for a release file in the vault).

- Closing and reopening the panel, mid-run and after a run, changes nothing: the log's nodes are the same ones.
- A reattach to the run already shown never clears the log: it adds only what is new since the last event drawn.
- A reload draws the chat in one step: no step-by-step replay (no working line, no words fading in) of what had arrived.
- /api/ask/attach takes a sequence number and sends only newer events; the history says how far it reaches.
- The greeting appears at once.

Run: python3 dev/tests/test_ask_reopen.py   (needs Google Chrome; skipped otherwise)
"""
import json
import re
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
message = args[args.index("--") + 1].split("\n")[0]
session = args[args.index("--resume") + 1] if "--resume" in args else "sess-" + os.urandom(4).hex()
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": session})
name = message.split()[-1]
if message.startswith("gated"):
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Read",
                                                       "input": {"file_path": "CLAUDE.md"}}]}})
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}})
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Part one of " + name + "."}]}})
    for _ in range(600):
        if os.path.exists("release-" + name):
            break
        time.sleep(0.1)
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Part two of " + name + "."}]}})
    out({"type": "result", "result": "Part two of " + name + ".", "session_id": session})
else:
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Reply to: " + message}]}})
    out({"type": "result", "result": "ok", "session_id": session})
'''

# Recorded from the first line of the page: every node added to #chLog that is a working line or a word fading in, and how
# often a bubble's text was set again (the greeting typed out).
WATCH = r'''(()=>{ window.SEEN={working:0,mw:0,typed:0};
  const go=()=>{ const log=document.getElementById("chLog"); if(!log){ requestAnimationFrame(go); return; }
    new MutationObserver(list=>list.forEach(m=>{ if(m.type==="characterData"||(m.type==="childList"&&m.target.classList&&m.target.classList.contains("msg")&&!m.addedNodes.length)) SEEN.typed++;
      m.addedNodes.forEach(n=>{ if(n.nodeType!==1) return; if(n.matches(".step.working")||n.querySelector(".step.working")) SEEN.working++;
        if(n.matches(".mw")||n.querySelector(".mw")) SEEN.mw++; }); })).observe(log,{childList:true,subtree:true,characterData:true}); };
  document.addEventListener("DOMContentLoaded",go); })();'''


class AskReopen(LiveBrowserCase):
    width, height = 1400, 900
    reduced_motion = False          # a live reply's words fade in: a replay would show it

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.v.root / "fake_claude.py")}

    # ── helpers ──
    def token(self):
        html = urllib.request.urlopen(self.base + "/").read().decode()
        return json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def post(self, path, body, stream=False):
        numbered = {"X-Creaite-Seq": "1"} if body.pop("seq", False) else {}       # as the page asks (BL-262)
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token(), **numbered})
        r = urllib.request.urlopen(req, timeout=90)
        if stream:
            return [json.loads(x.decode()[6:]) for x in r if x.decode().startswith("data: ")]
        return json.loads(r.read())

    def ask_in_background(self, message, run):
        """Start a run as another page would (or this page before a reload); its stream is read to the end, never acknowledged."""
        out = {}
        t = threading.Thread(target=lambda: out.update(events=self.post("/api/ask", {"message": message, "run": run, "seq": True}, stream=True)))
        t.start()
        return t, out

    def release(self, name):
        (self.v.root / f"release-{name}").write_text("go")

    def until_history_has(self, text, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            for f in (self.v.root / "system/staging/ask").glob("*.json"):
                if text in f.read_text(encoding="utf-8"):
                    return json.loads(f.read_text(encoding="utf-8"))
            time.sleep(0.1)
        self.fail(f"the history never had {text!r}")

    def tag(self):
        """Mark every node in the log, to check later that none was replaced (the working line comes and goes as a run works)."""
        return self.b.eval("(()=>{ const all=[document.getElementById('chLog'),...document.querySelectorAll('#chLog *')].filter(n=>!n.closest('.step.working')); window.KEPT=all; return all.length; })()")

    def kept(self):
        return self.b.eval("KEPT.filter(n=>!n.isConnected).length")

    def count(self, text):
        return self.b.eval(f"[...document.querySelectorAll('#chLog .msg.a')].filter(m=>m.textContent.includes({json.dumps(text)})).length")

    def reload_watched(self):
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source=WATCH)
        self.b.reload("typeof go==='function' && LIVE")

    # ── the tests ──
    def test_the_greeting_appears_at_once(self):
        b = self.b
        greet = b.eval("GREET")
        self.assertEqual(b.eval("openChat(); document.querySelector('#chLog .msg.a')?.textContent"), greet)
        b.eval("newChat()")
        self.assertEqual(b.eval("document.querySelector('#chLog .msg.a')?.textContent"), greet)

    def test_closing_and_reopening_mid_run_and_after_changes_nothing(self):
        b = self.b
        b.eval("openChat()")
        b.eval("$('#chIn').value='gated a'; send()", wait=False)
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part one of a'))", 20)
        run = b.eval("RUN&&RUN.id")
        n = self.tag()
        b.eval("closeChat()")
        b.pump(0.4)
        b.eval("openChat()")
        b.pump(0.4)
        self.assertEqual(self.kept(), 0, "reopening mid-run replaced nodes in the log")
        self.assertEqual(b.eval("[...document.querySelectorAll('#chLog *')].filter(n=>!n.closest('.step.working')).length+1"), n)
        self.release("a")
        b.wait("!RUN && [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of a'))", 20)
        b.pump(0.5)
        self.tag()
        b.eval("closeChat()")
        b.pump(0.3)
        b.eval("openChat()")
        b.pump(0.3)
        self.assertEqual(self.kept(), 0, "reopening after the run replaced nodes in the log")
        # a reattach to the run already shown (the live server coming back) adds only what is new: here, nothing
        b.eval(f"attachRun({{id:{json.dumps(run)},kind:'ask',chat:ASKCHAT,done:true,message:'gated a',confirmed:false}})")
        b.pump(1.0)
        b.wait("!RUN", 10)
        self.assertEqual(self.kept(), 0, "a reattach to the run on screen cleared and redrew the log")
        self.assertEqual((self.count("Part one of a"), self.count("Part two of a")), (1, 1))

    def test_a_reload_after_a_finished_run_draws_it_at_once_and_never_replays_it(self):
        t, _ = self.ask_in_background("gated b", "r-test-bbbbbb")
        self.until_history_has("Part one of b")
        self.release("b")
        t.join(30)
        self.reload_watched()                                          # the run finished while no page watched it
        b = self.b
        b.eval("openChat()")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of b'))", 20)
        b.pump(1.0)
        seen = b.eval("SEEN")
        self.assertEqual(seen["working"], 0, "the finished run was replayed step by step")
        self.assertEqual(seen["mw"], 0, "the finished run's words faded in again")
        self.assertEqual((self.count("Part one of b"), self.count("Part two of b")), (1, 1))
        self.assertIsNone(self.post("/api/ask/running", {})["run"])   # seen now: never offered again

    def test_a_reload_mid_run_shows_what_is_there_at_once_and_streams_only_the_new(self):
        t, _ = self.ask_in_background("gated c", "r-test-cccccc")
        self.until_history_has("Part one of c")
        self.reload_watched()
        b = self.b
        b.eval("openChat()")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part one of c'))", 20)
        b.pump(0.5)
        self.assertEqual(b.eval("SEEN.mw"), 0, "what had already arrived was drawn again word by word")
        self.tag()
        self.release("c")
        t.join(30)
        b.wait("!RUN && [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of c'))", 20)
        self.assertEqual(self.kept(), 0)
        self.assertEqual((self.count("Part one of c"), self.count("Part two of c")), (1, 1))
        self.assertGreater(b.eval("SEEN.mw"), 0)                       # only the new text streams in, as now

    def test_attach_from_a_sequence_number_sends_only_newer_events(self):
        t, out = self.ask_in_background("gated d", "r-test-dddddd")
        self.until_history_has("Part one of d")
        self.release("d")
        t.join(30)
        full = out["events"]
        self.assertEqual([e["seq"] for e in full], list(range(1, len(full) + 1)))       # every event is numbered
        later = self.post("/api/ask/attach", {"run": "r-test-dddddd", "after": 2, "seq": True}, stream=True)
        self.assertEqual([e["seq"] for e in later], list(range(3, len(full) + 1)))
        self.assertEqual(later[-1]["type"], "done")
        rec = self.post("/api/chat", {"chat": later[-1]["chat"]})
        self.assertEqual(rec["seq"].get("r-test-dddddd"), len(full) - 1)    # the history reaches every event but the end
        plain = self.post("/api/ask/attach", {"run": "r-test-dddddd", "after": 2}, stream=True)
        self.assertNotIn("seq", plain[0])                                    # unnumbered unless asked: other readers are unchanged
        self.assertEqual(len(plain), len(later))
        self.post("/api/ask/ack", {"run": "r-test-dddddd"})


if __name__ == "__main__":
    unittest.main()

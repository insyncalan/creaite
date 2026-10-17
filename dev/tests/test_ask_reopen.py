"""BL-262: reopening ask creaite shows the chat at once, as it was, never redrawn. A real browser against the real live server,
with a stand-in `claude` whose runs can be held part-way (a "gated" message waits for a release file in the vault).

- Closing and reopening the panel, mid-run and after a run, changes nothing: the log's nodes are the same ones.
- A reattach to the run already shown never clears the log: it adds only what is new since the last event drawn.
- A reload draws the chat in one step: no step-by-step replay (no working line, no words fading in) of what had arrived.
- /api/ask/attach takes a sequence number and sends only newer events; the history says how far it reaches.
- The greeting appears at once.
- #130: Esc never stops a run. In the chat box it closes the panel and the run carries on (the top-bar button keeps its working
  dot, reopening or a reload shows the run); Esc with no run just closes; the Stop button is the only thing that stops one.
  At 1400px and at 900px.

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

CHAT_ON = "document.getElementById('chat').classList.contains('on')"

FAKE = r'''#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
message = args[args.index("--") + 1].split("\n")[0]
session = args[args.index("--resume") + 1] if "--resume" in args else "sess-" + os.urandom(4).hex()
out = lambda o: print(json.dumps(o), flush=True)
def big_text(name):      # 700 words in seven paragraphs: well over the 400 words that a live reply fades in up to
    return "\n\n".join(" ".join("w%d" % i for i in range(k * 100, k * 100 + 100)) for k in range(7)) + "\n\nEND" + name
out({"type": "system", "subtype": "init", "session_id": session})
name = message.split()[-1]
if message.startswith("gated"):
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Read",
                                                       "input": {"file_path": "CLAUDE.md"}}]}})
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}})
    if " big " in message:      # a large reply, then a tool step: its text event is out at once, and the run waits for the release
        out({"type": "assistant", "message": {"content": [{"type": "text", "text": big_text(name)}]}})
        out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "CLAUDE.md"}}]}})
        out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t2", "content": "ok"}]}})
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Part one of " + name + "."}]}})
    for _ in range(600):
        if os.path.exists("release-" + name):
            break
        time.sleep(0.1)
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Part two of " + name + "."}]}})
    out({"type": "result", "result": "Part two of " + name + ".", "session_id": session})
elif message.startswith("big"):
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": big_text(name)}]}})
    out({"type": "result", "result": "ok", "session_id": session})
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

# Sampled on every frame from the first line of the page: how much of each reply is there, and whether the log ever went empty
# after it had content. A reply must be full length the first time it is seen and never shrink.
SAMPLE = r'''(()=>{ window.FR={frames:[],maxlog:0,blank:0,mutations:0,nodes:new Set()}; let first=true;
  const go=()=>{ const log=document.getElementById("chLog"); if(!log){ requestAnimationFrame(go); return; }
    new MutationObserver(l=>{ FR.mutations+=l.length; }).observe(log,{childList:true,subtree:true,characterData:true});
    const tick=()=>{ const n=[...log.children].filter(c=>!c.matches('.step.working')).length, lens=[...log.querySelectorAll(".msg.a")].map(m=>m.textContent.length);
      log.querySelectorAll('.msg.a').forEach(m=>{ if(m.textContent.length>1000) FR.nodes.add(m); }); if(n<FR.maxlog) FR.blank++; FR.maxlog=Math.max(FR.maxlog,n); FR.frames.push([n,lens,log.querySelectorAll(".mw").length]); requestAnimationFrame(tick); };
    tick(); };
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

    def sample_reload(self):
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source=SAMPLE)
        self.b.reload("typeof go==='function' && LIVE")

    def long_frames(self, marker):
        """The reply lengths (per frame) of the reply holding `marker`, from the frame it first appeared."""
        frames = self.b.eval("FR.frames")
        return [[l for l in lens] for n, lens, mw in frames if any(l for l in lens)], frames

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

    def sent_long_reply_then_reload(self, name):
        """Send a long message from this page, let it finish, then reload with the frame sampler running."""
        b = self.b
        b.eval("openChat()")
        b.eval(f"$('#chIn').value='big {name}'; send()", wait=False)
        b.wait(f"[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('END{name}'))", 20)
        b.wait("!RUN", 20)
        b.pump(0.3)
        full = b.eval("[...document.querySelectorAll('#chLog .msg.a')].pop().textContent.length")
        self.sample_reload()
        b.wait("document.getElementById('chLog').children.length>0", 20)      # the saved chat is drawn behind the closed panel
        b.pump(0.5)
        return full

    def test_a_long_saved_reply_is_there_whole_on_open_and_never_changes(self):
        b = self.b
        full = self.sent_long_reply_then_reload("f")
        self.assertGreater(full, 3000)       # 700 words: over the 400 a live reply fades in up to
        b.eval("FR.opened=FR.frames.length; FR.muts0=FR.mutations; FR.mw0=document.querySelectorAll('#chLog .mw').length; openChat()")
        b.pump(1.0)
        shown = [lens for n, lens, mw in b.eval("FR.frames.slice(FR.opened)") if lens]
        self.assertTrue(shown)
        self.assertEqual(set(l for lens in shown for l in lens if l > 200), {full}, "the reply was not whole on the first frame")
        self.assertEqual(b.eval("FR.mutations-FR.muts0"), 0, "the log changed after the panel opened")
        self.assertEqual(b.eval("FR.blank"), 0, "the log went empty after it had content")
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .mw').length"), 0)
        # and the reply was never smaller than whole on any frame of the whole load
        allseen = [l for n, lens, mw in b.eval("FR.frames") for l in lens if l > 200]
        self.assertEqual(set(allseen), {full})

    def test_the_saved_chat_is_drawn_once_even_if_the_panel_is_opened_during_the_load(self):
        b = self.b
        b.eval("openChat()")
        b.eval("$('#chIn').value='big j'; send()", wait=False)
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('ENDj'))", 20)
        b.wait("!RUN", 20)
        b.call("Page.addScriptToEvaluateOnNewDocument", source="(()=>{ const t=setInterval(()=>{ if(typeof openChat==='function'&&typeof LIVE!=='undefined'){ clearInterval(t); openChat(); } },1); })();")
        self.sample_reload()
        b.pump(1.0)
        self.assertEqual(b.eval("FR.blank"), 0)
        draws = b.eval("FR.frames.filter((x,i,a)=>i&&a[i-1][1].length&&x[1].length&&JSON.stringify(x[1])!==JSON.stringify(a[i-1][1])).length")
        self.assertEqual(draws, 0, "the saved reply changed after it was first shown")
        self.assertEqual(b.eval("FR.nodes.size"), 1, "the saved chat was drawn more than once")

    def test_the_scroll_position_is_kept_across_close_and_open(self):
        b = self.b
        self.sent_long_reply_then_reload("k")
        b.eval("openChat()")
        b.pump(0.3)
        b.eval("$('#chLog').scrollTop=400")
        b.pump(0.3)
        self.assertEqual(round(b.eval("$('#chLog').scrollTop")), 400)
        b.eval("closeChat()")
        b.pump(0.2)
        b.eval("openChat()")
        b.pump(0.3)
        self.assertEqual(round(b.eval("$('#chLog').scrollTop")), 400, "the panel jumped when it was reopened")

    def test_a_finished_run_replayed_is_drawn_plain_and_a_live_one_still_fades(self):
        t, _ = self.ask_in_background("gated i", "r-test-iiiiii")
        self.until_history_has("Part one of i")
        self.release("i")
        t.join(30)
        self.reload_watched()
        b = self.b
        b.eval("openChat()")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of i'))", 20)
        b.pump(0.5)
        # the history lacks the run (as an older record would): the whole run is replayed, and it is finished
        b.eval("window.SEEN.mw=0; $('#chLog').textContent=''; SHOWN=null")
        b.eval("attachRun({id:'r-test-iiiiii',kind:'ask',chat:null,done:true,message:'gated i',confirmed:false})")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of i'))", 20)
        b.pump(0.8)
        self.assertEqual(b.eval("SEEN.mw"), 0, "a finished run's replay faded its words in")
        self.post("/api/ask/ack", {"run": "r-test-iiiiii"})

    def test_the_backlog_an_attach_opens_with_is_drawn_plain(self):
        t, _ = self.ask_in_background("gated l", "r-test-llllll")
        self.until_history_has("Part one of l")
        self.release("l")
        t.join(30)                                         # the run ended between the page asking and attaching: all of it is backlog
        b = self.b
        b.eval("window.SEEN={mw:0}; new MutationObserver(l=>l.forEach(m=>m.addedNodes.forEach(n=>{ if(n.nodeType===1&&(n.matches('.mw')||n.querySelector('.mw'))) SEEN.mw++; }))).observe(document.getElementById('chLog'),{childList:true,subtree:true})")
        b.eval("$('#chLog').textContent=''; SHOWN=null")
        b.eval("attachRun({id:'r-test-llllll',kind:'ask',chat:null,done:false,message:'gated l',confirmed:false})")
        b.wait("!RUN && [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of l'))", 20)
        b.pump(0.8)
        self.assertEqual(b.eval("SEEN.mw"), 0, "the backlog an attach opens with faded in")


    def test_a_large_reply_still_arriving_at_reopen_is_not_redrawn_and_the_new_text_streams(self):
        t, _ = self.ask_in_background("gated big m", "r-test-mmmmmm")
        self.until_history_has("Part one of m")
        self.b.call("Page.addScriptToEvaluateOnNewDocument", source=WATCH)
        self.sample_reload()
        b = self.b
        b.wait("document.getElementById('chLog').children.length>0 && RUN", 20)     # drawn behind the closed panel; the run followed
        b.eval("openChat()")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('ENDm'))", 20)
        b.pump(0.6)
        self.assertEqual(b.eval("SEEN.mw"), 0, "the large reply that had already arrived was animated")
        self.tag()
        b.eval("FR.mw0=SEEN.mw")
        self.release("m")
        t.join(30)
        b.wait("!RUN && [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of m'))", 20)
        self.assertEqual(self.kept(), 0, "finished text was redrawn while the run went on")
        self.assertEqual(b.eval("FR.nodes.size"), 1, "the large reply was drawn more than once")
        self.assertEqual(b.eval("FR.blank"), 0)
        self.assertGreater(b.eval("SEEN.mw"), 0)                       # the new text streams in, as before
        self.assertEqual((self.count("ENDm"), self.count("Part two of m")), (1, 1))


    def test_a_finished_run_replayed_slowly_is_still_drawn_plain(self):
        """Finished is known from the run (done), not from how fast its events arrive: a replay held up for 400 ms is not animated."""
        t, _ = self.ask_in_background("gated n", "r-test-nnnnnn")
        self.until_history_has("Part one of n")
        self.release("n")
        t.join(30)
        b = self.b
        b.eval("window.SEEN={mw:0}; new MutationObserver(l=>l.forEach(m=>m.addedNodes.forEach(n=>{ if(n.nodeType===1&&(n.matches('.mw')||n.querySelector('.mw'))) SEEN.mw++; }))).observe(document.getElementById('chLog'),{childList:true,subtree:true})")
        b.eval("""window.__f=fetch; window.fetch=async(u,o)=>{ const r=await __f(u,o); if(!String(u).includes('/api/ask/attach')) return r; const rd=r.body.getReader();
          return new Response(new ReadableStream({async start(c){ await new Promise(x=>setTimeout(x,400)); for(;;){ const {value,done}=await rd.read(); if(done){ c.close(); return; } c.enqueue(value); } }}),{status:r.status,headers:r.headers}); }""")
        b.eval("$('#chLog').textContent=''; SHOWN=null")
        b.eval("attachRun({id:'r-test-nnnnnn',kind:'ask',chat:null,done:true,message:'gated n',confirmed:false})")
        b.wait("!RUN && [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of n'))", 20)
        b.pump(0.8)
        b.eval("window.fetch=__f")
        self.assertEqual(b.eval("SEEN.mw"), 0, "a finished run replayed slowly faded its words in")


    def test_opening_the_panel_while_the_saved_chat_loads_asks_for_it_once(self):
        b = self.b
        b.eval("openChat()")
        b.eval("$('#chIn').value='big p'; send()", wait=False)
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('ENDp'))", 20)
        b.wait("!RUN", 20)
        b.call("Page.addScriptToEvaluateOnNewDocument", source="""(()=>{ window.__asks=0; const f=window.fetch; window.fetch=function(u,o){ if(String(u)==="/api/chat"){ __asks++;
          return new Promise(r=>setTimeout(r,700)).then(()=>f.apply(this,arguments)); } return f.apply(this,arguments); }; })();""")
        self.sample_reload()
        b.eval("openChat()")                        # while the history is still on its way
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('ENDp'))", 20)
        b.pump(1.2)
        self.assertEqual(b.eval("__asks"), 1, "the saved chat was asked for twice")
        self.assertEqual(b.eval("FR.nodes.size"), 1, "the saved reply was drawn twice")


    # ── #130: Esc never stops a run ──
    def watch_stops(self):
        """Count the calls to /api/ask/stop the page makes."""
        self.b.eval("window.STOPS=0; const f=window.fetch; window.fetch=function(u,o){ if(String(u).includes('/api/ask/stop')) STOPS++; return f.apply(this,arguments); }; 1")

    def start_gated(self, name):
        b = self.b
        b.eval("openChat()")
        b.eval(f"$('#chIn').value='gated {name}'; send()", wait=False)
        b.wait(f"[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part one of {name}'))", 20)
        b.eval("$('#chIn').focus()")
        self.assertTrue(b.eval("!!RUN && document.getElementById('chSend').getAttribute('aria-label')==='Stop'"))

    def esc_with_a_run(self, name):
        b = self.b
        self.watch_stops()
        self.start_gated(name)
        run = b.eval("RUN.id")
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        b.pump(0.6)
        self.assertEqual(b.eval("STOPS"), 0, "Esc called /api/ask/stop")
        self.assertTrue(b.eval("!!RUN && !RUN.stopping"), "Esc stopped the run")
        self.assertTrue(b.eval("document.getElementById('askBtn').classList.contains('working')"), "the top-bar button shows no run while the panel is closed")
        self.assertEqual(b.eval("[document.getElementById('askBtn').getAttribute('aria-label'), document.getElementById('askBtn').title]"),
                         ["ask creaite (working)"] * 2, "the working state has no accessible name")
        self.assertEqual(self.post("/api/ask/running", {})["run"]["id"], run)           # the server is still running it
        b.eval("openChat()")                                                             # reopening shows it, still going
        self.assertTrue(b.eval("!!RUN && document.getElementById('chSend').getAttribute('aria-label')==='Stop'"))
        self.release(name)
        b.wait("!RUN && [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of %s'))" % name, 20)
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .step.stopped').length"), 0)
        b.wait("!document.getElementById('askBtn').classList.contains('working')", 10)   # cleared when it ends
        self.assertEqual(b.eval("[document.getElementById('askBtn').getAttribute('aria-label'), document.getElementById('askBtn').title]"), [None, ""])
        self.assertEqual(b.eval("STOPS"), 0)

    def test_esc_in_the_box_with_a_run_closes_the_panel_and_the_run_carries_on(self):
        self.esc_with_a_run("e")

    def test_esc_with_a_run_at_900px_wide(self):
        self.b.call("Emulation.setDeviceMetricsOverride", width=900, height=900, deviceScaleFactor=1, mobile=False)
        self.esc_with_a_run("f")

    def test_esc_with_a_run_then_a_reload_reattaches_and_shows_it_going(self):
        b = self.b
        self.start_gated("g")
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        self.reload_watched()                                                            # panel closed, page reloaded mid-run
        b.wait("document.getElementById('askBtn').classList.contains('working')", 20)    # the sign shows before the panel is opened
        b.eval("openChat()")
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part one of g'))", 20)
        self.assertTrue(b.eval("document.getElementById('chSend').getAttribute('aria-label')==='Stop'"))
        self.release("g")
        b.wait("!RUN && [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of g'))", 20)
        b.wait("!document.getElementById('askBtn').classList.contains('working')", 10)

    def esc_from(self, name, focus_js):
        """Esc with focus somewhere other than the box: the panel closes, nothing is stopped, the run carries on."""
        b = self.b
        self.watch_stops()
        self.start_gated(name)
        b.eval(focus_js)
        self.assertTrue(b.eval("document.getElementById('chat').contains(document.activeElement) && document.activeElement.id!=='chIn'"))
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        b.pump(0.6)
        self.assertEqual(b.eval("STOPS"), 0, "Esc called /api/ask/stop")
        self.assertTrue(b.eval("!!RUN && !RUN.stopping"))
        self.release(name)
        b.wait("!RUN && [...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part two of %s'))" % name, 20)
        self.assertEqual(b.eval("document.querySelectorAll('#chLog .step.stopped').length + STOPS"), 0)

    def test_esc_with_focus_on_the_stop_button_closes_the_panel_and_the_run_carries_on(self):
        self.esc_from("j", "document.getElementById('chSend').focus()")

    def test_esc_with_focus_in_the_panel_body_closes_the_panel_and_the_run_carries_on(self):
        self.esc_from("k", "(()=>{ const l=document.getElementById('chLog'); l.tabIndex=-1; l.focus(); })()")

    def test_esc_with_no_run_closes_the_panel(self):
        b = self.b
        self.watch_stops()
        b.eval("openChat(); $('#chIn').focus()")
        self.assertTrue(b.eval("!RUN && document.getElementById('chSend').getAttribute('aria-label')==='Send'"))
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        self.assertEqual(b.eval("STOPS"), 0)

    def test_esc_on_the_autocomplete_closes_only_the_list_even_with_a_run(self):
        b = self.b
        self.start_gated("h")
        b.eval("$('#chIn').value='/'; $('#chIn').dispatchEvent(new Event('input',{bubbles:true}))")
        b.wait("!document.getElementById('acMenu').hidden", 10)
        b.key("Escape")
        b.wait("document.getElementById('acMenu').hidden", 10)
        self.assertTrue(b.eval("document.getElementById('chat').classList.contains('on') && !!RUN"))   # the panel stays, the run too
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")                                                                          # the second Esc closes the panel
        self.assertTrue(b.eval("!!RUN && !RUN.stopping"))
        self.release("h")
        b.wait("!RUN", 20)

    def test_the_stop_button_is_the_only_thing_that_stops_a_run(self):
        b = self.b
        self.watch_stops()
        self.start_gated("i")
        self.assertIsNone(b.eval("document.getElementById('chSend').dataset.key||null"))   # no "Esc" shown on Stop
        b.click("#chSend")
        b.wait("STOPS===1 && !RUN", 20)
        b.wait("document.querySelector('#chLog .step.stopped')", 10)
        self.assertTrue(b.eval(CHAT_ON))                                                   # the panel stays open
        b.wait("!document.getElementById('askBtn').classList.contains('working')", 10)
        self.assertEqual(b.eval("document.getElementById('chSend').dataset.key"), "Enter")


if __name__ == "__main__":
    unittest.main()

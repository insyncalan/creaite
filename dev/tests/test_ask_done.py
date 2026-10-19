"""#231: a small "done" indication on the ask creaite button when a run finishes with the panel closed. A real browser against
the real live server, with a stand-in `claude` that can be quick, slow (to be stopped), failing, or held (gated).

- Done with the panel closed: a green tick and "Done" on the button, announced once ("ask creaite has finished", aria-live polite).
- Panel open at the end of the run: nothing is shown. Opening the panel (button, Ctrl+J) clears it at once.
- It hides by itself after 30 seconds (the real timer is checked with a spy on setTimeout; a short override proves the callback).
- Stopped looks different from done (grey square, "Stopped", also 30 seconds); failed looks different again (red "!", "Failed")
  and stays until the panel is opened.
- Esc closing the panel never stops or restarts a run; the indication then appears when the run ends.
- A second run starting clears the previous indication.
- Light and dark, creaite and Cursor palettes; reduced motion holds the countdown line still.

Run: python3 dev/tests/test_ask_done.py   (needs Google Chrome; skipped otherwise)
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES, LiveBrowserCase  # noqa: E402

CHAT_ON = "document.getElementById('chat').classList.contains('on')"

FAKE = r'''#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
message = args[args.index("--") + 1].split("\n")[0]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
name = message.split()[-1]
if message.startswith("slow"):
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Started."}]}})
    time.sleep(30)
    sys.exit(0)
if message.startswith("fail"):
    sys.stderr.write("the stand-in claude failed\n")
    sys.exit(3)
if message.startswith("gated"):
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Part one of " + name + "."}]}})
    for _ in range(600):
        if os.path.exists("release-" + name):
            break
        time.sleep(0.1)
if message.startswith("pause"):
    time.sleep(2.2)
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "All done."}]}})
out({"type": "result", "result": "All done.", "session_id": "sess-1"})
'''

STATE = """(()=>{ const b=document.getElementById('askBtn'), m=b.querySelector('.askmark'), l=b.querySelector('.asklab'), f=b.querySelector('.asklife'),
  live=document.getElementById('askLive'), mr=m?m.getBoundingClientRect():null, br=b.getBoundingClientRect();
  return {st:b.dataset.st||'', mark:m?getComputedStyle(m).display:'none', markText:m?m.textContent.trim():'', markHasSvg:!!(m&&m.querySelector('svg')),
    label:l?l.textContent:'', labelShown:l?getComputedStyle(l).display!=='none':false, lifeShown:f?getComputedStyle(f).display!=='none':false,
    title:b.getAttribute('title')||'', live:live?live.textContent:null, liveRole:live&&live.getAttribute('role'), liveAria:live&&live.getAttribute('aria-live'),
    liveInside:live?b.contains(live):null, markBg:m?getComputedStyle(m).backgroundColor:'', markColor:m?getComputedStyle(m).color:'',
    border:getComputedStyle(b).borderTopColor, overflow:getComputedStyle(b).overflow,
    markInside: mr?(mr.top>=br.top-4&&mr.right<=br.right+4&&mr.width>0):false, chat:CHATON}; })()""".replace("CHATON", CHAT_ON)


class AskDone(LiveBrowserCase):
    width, height = 1400, 900

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
    def s(self):
        return self.b.eval(STATE)

    def start(self, message, closed=True):
        """Begin a run as Process selected or Generate does; the panel is closed unless `closed` is False."""
        b = self.b
        for _ in range(12):                                                                    # a stopped run's process takes a moment to go (a 409 cancels the badge)
            b.eval(f"window.P=askLive({message!r},null).catch(()=>{{}}); {'closeChat()' if closed else 'openChat()'}")
            b.pump(0.4)
            if b.eval("RB.state") in ("running", "done", "failed"):
                break
            b.pump(1.0)
        b.wait("RB.state!==''", 20)

    def finished(self, state=None):
        self.b.wait("window.P&&RB.state!=='running'", 40)
        if state:
            self.assertEqual(self.b.eval("RB.state"), state)
        for _ in range(40):                                                                    # the server takes a moment to let go of a stopped run
            if self.b.eval("api('/api/ask/running').then(r=>!(r.ok&&r.run&&!r.run.done))"):
                break
            self.b.pump(0.25)

    def spy_timeouts(self):
        """Record the callbacks of every 30-second timer the page sets (so the 30 s is checked without waiting 30 s)."""
        self.b.eval("window.TO=[]; if(!window.TOSPY){ window.TOSPY=window.setTimeout; window.setTimeout=function(f,ms){ if(ms===30000) TO.push(f); return TOSPY.apply(this,arguments); }; } 1")

    def watch_fetches(self):
        self.b.eval("window.STOPS=0; window.ASKS=0; if(!window.FSPY){ window.FSPY=window.fetch; window.fetch=function(u,o){ const s=String(u); if(s.includes('/api/ask/stop')) STOPS++; if(s.split('?')[0].endsWith('/api/ask')) ASKS++; return FSPY.apply(this,arguments); }; } 1")

    def idle(self):
        s = self.s()
        self.assertEqual((s["st"], s["mark"], s["label"], s["live"], s["title"]), ("", "none", "", "", ""), s)

    # ── done ──
    def test_done_with_the_panel_closed_shows_the_tick_and_is_announced(self):
        self.start("hello")
        self.finished("done")
        s = self.s()
        self.assertEqual(s["st"], "done")
        self.assertEqual((s["mark"], s["markHasSvg"], s["label"], s["labelShown"], s["lifeShown"]), ("grid", True, "Done", True, True), s)
        self.assertEqual(s["live"], "ask creaite has finished")
        self.assertEqual((s["liveRole"], s["liveAria"], s["liveInside"]), ("status", "polite", False))       # a live region of its own, outside the button
        self.assertIn("30 seconds", s["title"])
        self.assertTrue(s["markInside"], "the mark is drawn on the button, not clipped away")
        self.assertEqual(s["overflow"], "visible")

    def test_with_the_panel_open_at_the_end_nothing_is_shown(self):
        b = self.b
        b.eval("openChat(); window.P=askLive('pause a bit',null).catch(()=>{}); 0")
        b.wait("RB.state==='running'")
        b.wait("window.P&&RB.state!=='running'", 40)
        b.pump(0.3)
        self.idle()
        b.eval("closeChat()")                                                                  # closing it afterwards shows nothing either
        self.idle()

    def test_opening_the_panel_clears_it_at_once_by_button_ctrl_j_and_the_palette(self):
        b = self.b
        for how in ("button", "ctrlj", "palette"):
            self.start("hello")
            self.finished("done")
            self.assertEqual(self.s()["st"], "done", how)
            if how == "button":
                b.click("#askBtn")
            elif how == "ctrlj":
                b.key("j", 2)
            else:
                b.eval("ckAsk('')")
            b.wait(CHAT_ON, 5)
            self.idle()                                                                        # at once: no timer, no wait
            b.eval("closeChat()")
            self.idle()

    def test_it_hides_by_itself_after_30_seconds(self):
        b = self.b
        self.spy_timeouts()
        self.start("hello")
        self.finished("done")
        self.assertEqual(self.s()["st"], "done")
        self.assertEqual(b.eval("TO.length"), 1, "one 30-second timer")
        self.assertEqual(b.eval("ASKDONE.ms"), 30000)
        b.eval("S.motion='Full'; applyMotion()")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#askBtn .asklife')).animationDuration"), "30s")      # the line runs out over the same 30 s
        b.eval("TO[0]()")                                                                      # the timer fires
        self.idle()

    def test_the_real_timer_clears_it_with_a_short_override(self):
        b = self.b
        b.eval("ASKDONE.ms=3000")
        self.start("hello")
        self.finished("done")
        self.assertEqual(self.s()["st"], "done")
        b.pump(3.6)
        self.idle()
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#askBtn .asklife')).display"), "none")

    # ── stopped and failed ──
    def test_stopped_looks_different_from_done_and_hides_after_30_seconds(self):
        b = self.b
        self.spy_timeouts()
        self.start("hello")
        self.finished("done")
        done = self.s()
        self.start("slow think")
        self.assertEqual(self.s()["st"], "", "a new run clears the earlier indication")
        b.eval("stopAsk()")
        self.finished("stopped")
        s = self.s()
        self.assertEqual((s["st"], s["label"], s["markText"]), ("stopped", "Stopped", "■"), s)
        self.assertEqual(s["live"], "ask creaite was stopped")
        self.assertNotEqual(s["markBg"], done["markBg"])
        self.assertNotEqual(s["border"], done["border"])
        self.assertTrue(s["lifeShown"])
        self.assertEqual(b.eval("TO.length"), 2, "done and stopped each set the 30 s timer")
        b.eval("TO[TO.length-1]()")
        self.idle()

    def test_failed_looks_different_and_stays_until_the_panel_is_opened(self):
        b = self.b
        self.spy_timeouts()
        self.start("hello")
        self.finished("done")
        done = self.s()
        self.assertEqual(done["st"], "done")
        b.eval("TO.length=0; ASKDONE.ms=300")                                                  # a short timer would hide done and stopped; failed must ignore it
        self.start("fail now")
        self.finished("failed")
        s = self.s()
        self.assertEqual((s["st"], s["label"], s["markText"]), ("failed", "Failed", "!"), s)
        self.assertEqual(s["live"], "ask creaite failed")
        self.assertNotEqual(s["markBg"], done["markBg"])
        self.assertNotEqual(s["border"], done["border"])
        self.assertFalse(s["lifeShown"], "no countdown on a failure")
        b.pump(1.5)
        self.assertEqual(self.s()["st"], "failed")                                             # still there
        self.assertEqual(b.eval("TO.length"), 0)
        b.eval("openChat()")
        self.idle()

    # ── Esc, a second run ──
    def test_esc_closing_the_panel_never_stops_or_restarts_the_run(self):
        b = self.b
        self.watch_fetches()
        b.eval("openChat()")
        b.eval("$('#chIn').value='gated one'; send()", wait=False)
        b.wait("[...document.querySelectorAll('#chLog .msg.a')].some(m=>m.textContent.includes('Part one of one'))", 20)
        b.eval("$('#chIn').focus()")
        self.assertTrue(b.eval("!!RUN"))
        b.key("Escape")
        b.wait(f"!{CHAT_ON}")
        b.pump(0.6)
        self.assertEqual(b.eval("STOPS"), 0, "Esc called /api/ask/stop")
        self.assertEqual(b.eval("ASKS"), 1, "Esc started a second request")
        self.assertTrue(b.eval("!!RUN && !RUN.stopping"))
        self.assertEqual(self.s()["st"], "", "while it runs there is no finish mark")
        (self.v.root / "release-one").write_text("go")
        b.wait("!RUN", 30)
        b.pump(0.3)
        s = self.s()
        self.assertEqual(s["st"], "done", s)                                                   # it ran to its end, and the button says so
        self.assertEqual((b.eval("STOPS"), b.eval("ASKS")), (0, 1))
        b.key("Escape")                                                                        # Esc on the page does not clear it, nor stop anything
        self.assertEqual(b.eval("STOPS"), 0)

    def test_a_second_run_starting_clears_the_previous_indication(self):
        self.start("fail now")
        self.finished("failed")
        self.assertEqual(self.s()["st"], "failed")
        self.start("gated two")
        s = self.s()
        self.assertEqual((s["st"], s["live"], s["mark"]), ("", "", "none"), s)
        (self.v.root / "release-two").write_text("go")
        self.finished("done")
        s = self.s()
        self.assertEqual((s["st"], s["live"]), ("done", "ask creaite has finished"))           # announced again for the new run

    # ── themes and motion ──
    def test_it_reads_in_every_theme_and_mode(self):
        b = self.b

        def lum(c):
            v = [float(x) / 255 for x in re.findall(r"[\d.]+", c)[:3]]
            v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
            return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

        def ratio(a, c):
            x, y = lum(a), lum(c)
            return (max(x, y) + 0.05) / (min(x, y) + 0.05)
        self.start("hello")
        self.finished("done")
        for state in ("done", "stopped", "failed"):
            b.eval(f"ASKDONE.ms=3e6; askMarkSet({state!r}, '')")
            for pal in TEST_PALETTES:
                for mode in ("Light", "Dark"):
                    b.eval(f"S.palette={pal!r}; S.theme={mode!r}; applyTheme()")
                    b.pump(0.15)
                    mark_bg, mark_ink, btn_bg, lab = b.eval("""(()=>{ const b=document.getElementById('askBtn'), m=b.querySelector('.askmark');
                      return [getComputedStyle(m).backgroundColor, getComputedStyle(m).color, getComputedStyle(b).backgroundColor, getComputedStyle(b.querySelector('.asklab')).color]; })()""")
                    self.assertGreaterEqual(ratio(mark_ink, mark_bg), 3.0, (state, pal, mode, "glyph"))
                    self.assertGreaterEqual(ratio(mark_bg, btn_bg), 1.5, (state, pal, mode, "mark against the button"))
                    self.assertGreaterEqual(ratio(lab, btn_bg), 4.5, (state, pal, mode, "label"))
        b.eval("askMarkClear()")

    def test_the_countdown_line_holds_still_under_reduced_motion(self):
        b = self.b
        self.start("hello")
        self.finished("done")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#askBtn .asklife')).animationName"), "none")        # the suite runs with reduced motion
        b.eval("S.motion='Full'; applyMotion()")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#askBtn .asklife')).animationName"), "asklife")
        b.eval("S.motion='Reduce'; applyMotion()")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#askBtn .asklife')).animationName"), "none")

    def test_idle_button_is_as_it_was(self):
        s = self.s()
        self.assertEqual((s["st"], s["mark"], s["label"], s["title"]), ("", "none", "", ""))
        self.assertEqual(self.b.eval("document.getElementById('askBtn').textContent.replace(/\\s+/g,' ').trim()"), "ask creaite /")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""BL-139: ask creaite's running and finished badge, bottom right. A real browser against the real live server, with a stand-in
`claude` that can be quick, slow (to be stopped), or fail.

Run: python3 dev/tests/test_run_badge.py   (needs Google Chrome; skipped otherwise)
"""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import TEST_PALETTES, LiveBrowserCase  # noqa: E402

FAKE = r'''#!/usr/bin/env python3
import json, sys, time
args = sys.argv[1:]
message = args[args.index("--") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
if message.startswith("Draft the Current state"):
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Recovery is **on track**.\n\nSOURCES:\n- tracker"}]}})
    out({"type": "result", "result": "ok", "session_id": "sess-g"})
    sys.exit(0)
if message.startswith("slow"):
    out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Started."}]}})
    time.sleep(30)
    sys.exit(0)
if message.startswith("fail"):
    sys.stderr.write("the stand-in claude failed\n")
    sys.exit(3)
if message.startswith("pause"):
    time.sleep(2.2)
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "All done."}]}})
out({"type": "result", "result": "All done.", "session_id": "sess-1"})
'''
PALETTES = TEST_PALETTES   # creaite and Cursor only (live_browser.TEST_PALETTES)


class RunBadge(LiveBrowserCase):
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

    def go_work(self):
        self.b.eval("go('work')")
        self.b.wait("VIEW==='work'")

    def start(self, message, label=""):
        """Begin a run from a page other than the chat, as Process selected or Generate does (the chat is closed again)."""
        b = self.b
        for _ in range(12):                                                                    # a stopped run's process takes a moment to go (a 409 cancels the badge)
            b.eval(f"RUNLABEL={label!r}; window.P=askLive({message!r},null).catch(()=>{{}}); closeChat()")
            b.pump(0.4)
            if b.eval("RB.state")=="running" or b.eval("RB.state")=="done" or b.eval("RB.state")=="failed":
                break
            b.pump(1.0)
        b.wait("RB.state!==''", 20)

    def done(self, state):
        self.b.wait("window.P&&RB.state!=='running'", 40)
        self.assertEqual(self.b.eval("RB.state"), state)
        for _ in range(40):                                                                    # the server takes a moment to let go of a stopped run
            if self.b.eval("api('/api/ask/running').then(r=>!(r.ok&&r.run&&!r.run.done))"):
                break
            self.b.pump(0.25)

    def badge(self):
        return self.b.eval("""(()=>{ const e=document.getElementById('runBadge'), r=e.getBoundingClientRect(), cs=getComputedStyle(e);
          return {shown:!e.hidden&&cs.display!=='none', text:e.innerText.replace(/\\s+/g,' ').trim(), state:e.dataset.state||'', role:e.getAttribute('role'), live:e.getAttribute('aria-live'),
            right:Math.round(innerWidth-r.right), bottom:Math.round(innerHeight-r.bottom), pos:cs.position, close:!document.getElementById('rbX').hidden}; })()""")

    # ── running ──

    def test_a_run_shows_the_badge_on_another_page_with_the_clock(self):
        b = self.b
        self.go_work()
        self.start("slow think")
        o = self.badge()
        self.assertTrue(o["shown"])
        self.assertEqual((o["pos"], o["right"], o["bottom"]), ("fixed", 20, 20))             # fixed at the bottom right
        self.assertIn("ask creaite is working…", o["text"])
        self.assertRegex(o["text"], r"\d+:\d\d")                                              # and how long it has taken
        self.assertEqual((o["role"], o["live"]), ("status", "polite"))
        self.assertFalse(o["close"])                                                          # no × while it runs
        self.assertTrue(b.eval("document.getElementById('askBtn').classList.contains('working')"))       # the top-bar dot stays
        self.assertEqual(b.eval("document.getElementById('rbE').getAttribute('aria-hidden')"), "true")    # the clock is not read out every second
        b.eval("rbStop(); RB.t0-=84000; rbTick()")
        self.assertRegex(self.badge()["text"], r"1:2[4-6]")                                      # the clock shows minutes and seconds
        b.eval("stopAsk()")
        self.done("stopped")

    def test_it_names_what_is_running_where_known(self):
        b = self.b
        self.start("slow x", "Processing 3 meetings")
        self.assertIn("Processing 3 meetings", self.badge()["text"])
        b.eval("stopAsk()")
        self.done("stopped")
        for q, words in (("weekly report ABC", "Drafting the weekly report"), ("refresh calendar", "Refreshing the calendar"),
                         ("sweep", "Checking mail and Teams"), ("process inbox/x.vtt", "Processing a meeting")):
            self.assertEqual(self.b.eval(f"rbGuess({q!r})"), words)

    def test_a_transcript_job_and_generate_and_a_search_all_show_it(self):
        b = self.b
        b.eval("window.SEEN=[]; const d=rbDraw; rbDraw=function(){ SEEN.push([RB.state,RB.label]); d(); }")
        b.eval("window.J=jobLive('/api/transcripts/check',{id:'nope'}).catch(()=>{}); 0")
        b.wait("window.J&&SEEN.length>1", 20)
        b.pump(1.5)
        self.assertIn(["running", "Checking a transcript"], b.eval("SEEN"))
        b.eval("SEEN.length=0; window.G=runGen({code:'ABC',from:'2026-10-01',to:'2026-10-09',sources:[],note:'',audience:'internal',length:'standard'}); 0")
        b.wait("window.G&&SEEN.some(s=>s[0]!=='running')", 40)
        b.pump(0.5)
        self.assertIn(["running", "Drafting the current state"], b.eval("SEEN"))
        self.assertEqual(b.eval("RB.state"), "done")

    # ── finished, stopped, failed ──

    def test_finished_stays_until_dismissed_and_says_how_long(self):
        b = self.b
        self.go_work()
        self.start("hello")
        self.done("done")
        o = self.badge()
        self.assertTrue(o["shown"])
        self.assertIn("ask creaite has finished", o["text"])
        self.assertRegex(o["text"], r"took \d+:\d\d")
        self.assertTrue(o["close"])
        self.assertFalse(b.eval("document.getElementById('askBtn').classList.contains('working')"))
        b.pump(3.0)                                                                           # no timer takes it away
        self.assertTrue(self.badge()["shown"])
        self.assertEqual(b.eval("document.getElementById('askDone')"), None)                 # the old 15-second note is gone
        b.click("#rbX")                                                                       # dismissed
        self.assertFalse(self.badge()["shown"])

    def test_the_next_run_replaces_it(self):
        b = self.b
        self.start("hello")
        self.done("done")
        self.start("slow again")
        o = self.badge()
        self.assertEqual(o["state"], "running")
        self.assertIn("ask creaite is working…", o["text"])
        b.eval("stopAsk()")
        self.done("stopped")

    def test_stopped_and_failed_say_so_in_words(self):
        b = self.b
        self.start("slow think")
        b.eval("stopAsk()")
        self.done("stopped")
        o = self.badge()
        self.assertIn("ask creaite was stopped", o["text"])
        self.assertEqual(o["state"], "stopped")
        self.start("fail now")
        self.done("failed")
        o = self.badge()
        self.assertIn("ask creaite stopped with a problem", o["text"])
        self.assertEqual(o["state"], "failed")
        self.assertNotEqual(b.eval("document.getElementById('rbI').textContent"), "")         # an icon as well as the words

    # ── the chat panel ──

    def test_hidden_while_the_chat_is_open_and_back_when_it_is_closed_during_the_run(self):
        b = self.b
        self.go_work()
        self.start("slow think")
        self.assertTrue(self.badge()["shown"])
        b.eval("openChat()")
        self.assertFalse(self.badge()["shown"])                                               # the chat shows the run
        b.eval("closeChat()")
        self.assertTrue(self.badge()["shown"])                                                # and the badge returns
        b.eval("stopAsk()")
        self.done("stopped")
        b.eval("openChat()")                                                                  # opening the chat dismisses a finished badge
        b.eval("closeChat()")
        self.assertFalse(self.badge()["shown"])

    def test_a_run_that_ends_while_the_chat_is_open_leaves_nothing_to_flag(self):
        b = self.b
        b.eval("openChat(); window.P=askLive('pause a bit',null).catch(()=>{}); 0")
        b.wait("RB.state==='running'")
        b.wait("window.P&&RB.state!=='running'", 40)
        b.eval("closeChat()")
        self.assertEqual(b.eval("RB.state"), "")
        self.assertFalse(self.badge()["shown"])

    # ── the tab, motion, themes ──

    def test_the_title_gets_a_mark_only_while_the_tab_is_hidden(self):
        b = self.b
        base = b.eval("document.title")
        self.start("hello")
        self.done("done")
        self.assertEqual(b.eval("document.title"), base)                                      # visible tab: no mark
        b.eval("rbDismiss()")
        b.eval("Object.defineProperty(document,'hidden',{get:()=>true,configurable:true})")
        self.start("hello")
        self.done("done")
        self.assertTrue(b.eval("document.title").startswith("✓ ask creaite finished · "))
        b.eval("Object.defineProperty(document,'hidden',{get:()=>false,configurable:true}); document.dispatchEvent(new Event('visibilitychange'))")
        self.assertEqual(b.eval("document.title"), base)                                      # gone once the tab is seen

    def test_the_pulse_stops_under_reduced_motion_and_runs_under_full(self):
        b = self.b
        self.start("slow think")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#rbI')).animationName"), "none")      # the suite runs with reduced motion
        b.eval("S.motion='Full'; applyMotion()")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#rbI')).animationName"), "mrbp")
        b.eval("S.motion='Reduce'; applyMotion()")
        self.assertEqual(b.eval("getComputedStyle(document.querySelector('#rbI')).animationName"), "none")
        b.eval("stopAsk()")
        self.done("stopped")

    def test_it_reads_in_every_theme_and_mode(self):
        b = self.b

        def lum(c):
            v = [float(x) / 255 for x in re.findall(r"[\d.]+", c)[:3]]
            v = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
            return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]

        def ratio(a, c):
            x, y = lum(a), lum(c)
            return (max(x, y) + 0.05) / (min(x, y) + 0.05)
        for state in ("running", "done", "stopped", "failed"):
            b.eval(f"RB.state={state!r}; RB.took='0:09'; rbDraw()")
            for pal in PALETTES:
                for mode in ("Light", "Dark"):
                    b.eval(f"S.palette={pal!r}; S.theme={mode!r}; applyTheme()")
                    b.pump(0.15)
                    surface, ink, icon = b.eval("""(()=>{ const e=document.getElementById('runBadge'), i=document.getElementById('rbI');
                      return [getComputedStyle(e).backgroundColor, getComputedStyle(document.getElementById('rbT')).color, getComputedStyle(i).backgroundColor]; })()""")
                    self.assertGreaterEqual(ratio(ink, surface), 4.5, (state, pal, mode, "words"))
                    self.assertGreaterEqual(ratio(icon, surface), 3.0, (state, pal, mode, "icon"))
        b.eval("RB.state=''; rbDraw()")


if __name__ == "__main__":
    unittest.main(verbosity=2)

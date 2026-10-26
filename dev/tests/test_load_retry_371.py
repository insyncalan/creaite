"""#371 (2.6.9): Process loads a meeting's transcript first. When that Load ends without reaching Microsoft 365 (no step at all), the
page looks again once and says so; a second failure stops with the plain line; no other failure and no Stop is retried. Real Chrome
against the live server (support: ir_harden_support.py); the Load runs are scripted in the page.

Run: CREAITE_BROWSER_SLOTS=6 python3 dev/tests/test_load_retry_371.py
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ir_harden_support import IrHardenCase  # noqa: E402

NO_REACH = "Claude Code did not reach Microsoft 365, so it never looked for the meeting's calendar event and nothing was loaded. Press Process to try again."
SCRIPT = r"""
window.SCRIPT=%s; window.RUNS=[];
jobLive=async(url,body)=>{ LOADED.push([url,body.id]); const c=SCRIPT.shift()||{ok:false,line:"creaite stopped."}; shared.LASTCLOSE=c;
  if(c.ok){ const t="WEBVTT\n\nEvent ID: "+body.id+"\n\n00:00:01.000 --> 00:00:05.000\nHello\n";
    await api("/api/inbox/upload",{name:"2026-10-05 "+body.id+".vtt",data:btoa(t)}); } };
"""


class Base(IrHardenCase):
    def run_load(self, script):
        b = self.b
        b.eval(SCRIPT % json.dumps(script))
        b.click(self.sel("Vendor check-in", ' [data-ira="process"]'))
        b.wait("irBusy.value.length===0 && LOADED.length>0", 30)
        b.wait("irBusy.value.length===0", 30)
        return b.eval("LOADED.length"), b.eval("PROC.length")


class Failures(Base):
    def test_two_misses_stop_with_the_plain_line(self):
        n, procs = self.run_load([{"ok": False, "line": NO_REACH}, {"ok": False, "line": NO_REACH}])
        self.assertEqual((n, procs), (2, 0))                                  # exactly one retry, nothing processed
        self.assertIn("Looked again, and Microsoft 365 still could not be reached. Nothing was loaded. Press Process to try again.",
                      self.text("Vendor check-in"))

    def test_another_failure_is_not_retried(self):
        n, _ = self.run_load([{"ok": False, "line": "The meeting's calendar event was found but could not be read, so nothing was loaded. Press Process to try again."}])
        self.assertEqual(n, 1)
        self.assertNotIn("Looking again", self.text("Vendor check-in"))

    def test_a_stopped_run_is_not_retried(self):
        n, _ = self.run_load([{"ok": False, "stopped": True, "line": NO_REACH}])
        self.assertEqual(n, 1)

    def test_the_event_never_opened_is_not_retried(self):
        n, _ = self.run_load([{"ok": False, "line": "Claude Code searched Microsoft 365 but never opened the meeting's calendar event, so nothing was loaded. Press Process to try again."}])
        self.assertEqual(n, 1)


class Success(Base):
    def test_a_miss_then_a_find_loads_and_says_so(self):
        n, procs = self.run_load([{"ok": False, "line": NO_REACH}, {"ok": True, "line": "Loaded."}])
        self.assertEqual((n, procs), (2, 1))                                  # one retry, then Process went on with the file
        self.assertEqual(self.snack(), "Found it on the second look.")


if __name__ == "__main__":
    unittest.main()

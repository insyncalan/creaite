"""BL-201: a refused command is said plainly. Each shape the guard refuses (a redirect, a pipe, `&&`, a heredoc, a
substitution, another program…) gives one plain sentence that never holds the command; the command is under "Show the
command"; a refusal the run recovered from has no warning sign. Display and wording only: the guard is unchanged (its own
tests, test_reach, test_admin_card and test_permissions, prove that).

Run: python3 dev/tests/test_refusal_words.py   (the browser part needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
import live_server  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

SHAPES = {
    "redirect": ("python3 system/scripts/propose.py new-project spec.json > /tmp/mer.json", "save the output"),
    "pipe": ("python3 system/scripts/tracker.py list | head -5", "pass the output"),
    "and": ("python3 system/scripts/tracker.py a && python3 system/scripts/tracker.py b", "together with another command"),
    "heredoc": ("python3 system/scripts/propose.py stage - <<'EOF'\n{}\nEOF", "input inline"),
    "substitution": ("python3 system/scripts/report.py weekly $(date +%F)", "from another command"),
    "program": ("node /tmp/build.js", "isn't one of creaite's scripts"),
    "cd": ("cd /some/vault && python3 system/scripts/report.py weekly ABC", "change folder"),
}


def bash(cmd, tid=None):
    d = {"tool_name": "Bash", "tool_input": {"command": cmd}}
    if tid:
        d["tool_use_id"] = tid
    return d


class PlainSentences(unittest.TestCase):
    def test_each_shape_gives_one_plain_sentence_without_the_command(self):
        for kind, (cmd, words) in SHAPES.items():
            line = live_server.refused_plain(bash(cmd))
            self.assertIn(words, line, kind)
            self.assertTrue(line.startswith("I tried"), kind)
            self.assertNotIn("\n", line, kind)
            self.assertNotIn("{", line, kind)
            self.assertNotIn("/tmp", line, kind)                            # never the command, its paths or arguments
            self.assertNotIn("$(", line, kind)
            self.assertNotIn("EOF", line, kind)
            self.assertLess(len(line), 200, kind)

    def test_the_redirect_example_reads_as_alan_asked(self):
        line = live_server.refused_plain(bash(SHAPES["redirect"][0]))
        self.assertEqual(line, "I tried to save the output of the change script (propose.py) to a file. That isn't allowed "
                               "and wasn't needed; I'll use the script's own option instead.")

    def test_the_other_kinds(self):
        self.assertIn("never runs", live_server.refused_plain(bash("python3 system/scripts/permissions.py add x")))
        self.assertIn("approval card", live_server.refused_plain(bash("python3 system/scripts/propose.py setting a 1")))
        self.assertIn("build.js directly", live_server.refused_plain({"tool_name": "Write", "tool_input": {"file_path": "/tmp/build.js"}}))
        self.assertIn("never reads", live_server.refused_plain({"tool_name": "Read", "tool_input": {"file_path": "~/.ssh/config"}}))
        self.assertNotIn(".ssh", live_server.refused_plain({"tool_name": "Read", "tool_input": {"file_path": "~/.ssh/config"}}))
        self.assertIn("nothing was sent", live_server.refused_plain({"tool_name": "mcp__claude_ai_Microsoft_365__outlook_send_mail"}))

    def test_the_view_keeps_the_command_for_the_fold_out_and_knows_a_recovery(self):
        d = bash(SHAPES["pipe"][0], "t1")
        v = live_server.refusal_view(d, live_server.recovered_after(["t1", "t2"], {"t2"}, d))
        self.assertEqual(v["raw"], "Bash: " + SHAPES["pipe"][0])
        self.assertTrue(v["recovered"])
        self.assertFalse(live_server.recovered_after(["t1", "t2"], {"t2"}, bash("x", "t2")))   # nothing after it succeeded
        self.assertFalse(live_server.recovered_after(["t1"], set(), bash("x")))                 # no id: kept as a stop

    def test_the_wrapper_form_names_its_script_like_the_python3_form(self):
        # BL-278: `system/scripts/run tracker.py …` once read "I tried to run run, which isn't one of creaite's scripts"
        for prefix in ("python3 system/scripts/", "system/scripts/run "):
            line = live_server.refused_plain(bash(prefix + "tracker.py read actions > actions.txt"))
            self.assertTrue(line.startswith("I tried to save the output of the tracker (tracker.py) to a file"), prefix)
            self.assertNotIn("run run", line)
            self.assertIn("isn't on my allow list", live_server.refused_plain(bash(prefix + "tracker.py frobnicate")), prefix)
            self.assertIn("pass the output of the tracker", live_server.refused_plain(bash(prefix + "tracker.py list | head")))
            self.assertEqual(live_server.refused_shape(bash(prefix + "tracker.py read actions > a.txt")),
                             "tracker.py with a redirect", prefix)
        self.assertIn("isn't one of creaite's scripts", live_server.refused_plain(bash("system/scripts/run")))

    def test_the_debug_log_shape_is_unchanged(self):
        self.assertEqual(live_server.refused_shape(bash(SHAPES["redirect"][0])), "propose.py with a redirect")


FAKE = r'''#!/usr/bin/env python3
import json, sys
args = sys.argv[1:]
message = args[args.index("--") + 1]
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-1"})
cmd = "python3 system/scripts/propose.py new-project spec.json > /tmp/mer.json"
out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": cmd}}]}})
out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": True, "content": "refused"}]}})
if message.startswith("recover"):
    out({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t2", "name": "Bash",
         "input": {"command": "python3 system/scripts/propose.py new-project spec.json --out mer.json"}}]}})
    out({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t2", "content": "saved"}]}})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}})
out({"type": "result", "result": "Done.", "session_id": "sess-1",
     "permission_denials": [{"tool_name": "Bash", "tool_use_id": "t1", "tool_input": {"command": cmd}}]})
'''


class RefusalInTheChat(LiveBrowserCase):
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

    def say(self, text):
        b = self.b
        b.eval("openChat()")
        b.pump(0.3)
        b.eval("$('#chIn').focus()")
        b.type(text)
        b.key("Enter")
        b.wait("document.querySelector('#chLog .step.refused') && !RUN && !BUSY", 20)
        b.pump(0.2)
        return b.eval("""(()=>{ const s=document.querySelector('#chLog .step.refused');
          return {line:s.querySelector('.rfline').textContent, warn:!!s.querySelector('.rfwarn'), stop:s.classList.contains('stop'),
                  open:s.querySelector('details').open, summary:s.querySelector('summary').textContent,
                  raw:s.querySelector('details code').textContent, old:document.querySelector('#chLog').textContent.includes('Refused:')}; })()""")

    def test_a_refusal_that_stops_has_the_sign_and_a_fold_out(self):
        r = self.say("stops here")
        self.assertIn("save the output of the change script", r["line"])
        self.assertNotIn("/tmp", r["line"])                                 # the command isn't in the line
        self.assertNotIn(">", r["line"])
        self.assertTrue(r["warn"] and r["stop"])
        self.assertFalse(r["open"])                                         # folded away until wanted
        self.assertEqual(r["summary"], "Show the command")
        self.assertIn("> /tmp/mer.json", r["raw"])                       # there for troubleshooting
        self.assertFalse(r["old"])                                          # no raw "Refused: Bash {…}" line

    def test_a_recovered_refusal_has_no_warning_sign(self):
        r = self.say("recover from it")
        self.assertIn("save the output", r["line"])
        self.assertFalse(r["warn"] or r["stop"])


if __name__ == "__main__":
    unittest.main()

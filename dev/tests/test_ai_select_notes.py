"""BL-301 D in the Notes tab (B): AI on selected text in a note, and its hook into Find updates (E).

- selecting text in a note shows the bar with the notes' options, and "Make this an action, a risk, a decision or an update"
  listed before "Or say what you want…";
- an option sends only the selection (place "notes", the note's project) to a Claude run with no tools; Accept puts the
  suggestion in the note as an edit; draft-stats.json gets counts, never text;
- "Make this an action…" opens Find updates beside the note on the selection's line only (no edit run, no counts);
- a selection over two lines, or none, runs nothing and says why;
- a confidential note asks before its text goes to Claude.

Run: python3 dev/tests/test_ai_select_notes.py   (needs Google Chrome; skipped otherwise)
The real live server in a throwaway vault (notes_find_fixture's Falcon Data Platform and its catch-up note); Claude is a
stand-in that answers both runs and records how each was started. Never a real model call.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notes_find_fixture as fx  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

# The stand-in: an edit-ai prompt (its <<<TEXT block) gets "Clearly: <text>"; a Find updates prompt gets the fixture's rows.
# Each kind keeps its own prompt and argv beside the script.
FAKE = r'''#!/usr/bin/env python3
import json, re, sys
ROWS = json.loads(%r)
args = sys.argv[1:]
p = args[args.index("--") + 1]
m = re.search(r"<<<TEXT\n(.*?)\nTEXT>>>", p, re.S)
kind = "edit" if m else "find"
open(__file__ + "." + kind + ".prompt", "w", encoding="utf-8").write(p)
open(__file__ + "." + kind + ".argv.json", "w", encoding="utf-8").write(json.dumps(args))
if m:
    reply = "<<<SUGGESTION\nClearly: " + m.group(1) + "\nSUGGESTION>>>"
else:
    rows = []
    for n, t in re.findall(r"^\[p(\d+)\] (.*)$", p, re.M):
        for k, rs in ROWS.items():
            if k in t:
                rows += [dict(r, p=int(n)) for r in rs]
    reply = "```json\n" + json.dumps({"rows": rows}) + "\n```"
out = lambda o: print(json.dumps(o), flush=True)
out({"type": "system", "subtype": "init", "session_id": "sess-d"})
out({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}})
out({"type": "result", "result": reply, "session_id": "sess-d"})
''' % json.dumps(fx.ROWS)

NOTES_OPTIONS = ["rewrite", "shorter", "longer", "executive", "spelling", "format", "checklist", "summary", "fu-line", "custom"]
LINE4 = "Phase 1 go-live probably moves two weeks"


class AiInANote(LiveBrowserCase):
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        fx.load(v)
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(FAKE)
        cls.fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake), "CREAITE_NOW": fx.NOW}

    FILE = fx.NOTE.rsplit("/", 1)[1]

    def open_note(self):
        b = self.b
        b.eval(f"location.hash='#notes=FAL&n='+encodeURIComponent({json.dumps(self.FILE)})")
        b.wait(f"noteCur.value&&noteCur.value.path==={json.dumps(fx.NOTE)}&&!!document.querySelector('#v-notes .nbody [data-p]')", 20)

    def select(self, words, upto=None):
        """Select from `words` to the end of `upto` (or of `words`) in the note, as a person would."""
        self.b.click("#v-notes .nbody")
        self.b.eval("""(()=>{ const h=document.querySelector('#v-notes .nbody').cxed, doc=h.editor.state.doc;
          const find=w=>{ let at=-1; doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf(w); if(i>=0) at=pos+i; } }); return at; };
          const a=find(%s), z=find(%s)+%d; h.focus(); h.editor.commands.setTextSelection({from:a,to:z}); })()"""
                    % (json.dumps(words), json.dumps(upto or words), len(upto or words)))
        self.b.wait("document.querySelector('#aiLayer .aibar')")

    def menu(self):
        b = self.b
        b.click("#aiLayer .aibar button[aria-haspopup]")
        b.wait("document.querySelector('#aiLayer [role=menu]')")
        return b.eval("[...document.querySelectorAll('#aiLayer [role=menu] [data-ai]')].map(e=>e.dataset.ai)")

    def stats(self):
        p = self.v.root / "system/staging/draft-stats.json"
        return (json.loads(p.read_text()).get("edit", {}), p.read_text()) if p.exists() else ({}, "")

    def ready(self):
        self.b.wait("document.querySelector('#aiLayer .aisug .aitext')||document.querySelector('#aiLayer .aisug [role=alert]')", 20)

    def test_the_bar_offers_the_notes_options_and_make_this_an_action_before_say_what_you_want(self):
        self.open_note()
        self.select("Sandbox access granted")
        self.assertEqual(self.menu(), NOTES_OPTIONS)
        name = self.b.eval("document.querySelector('#aiLayer [role=menu] [data-ai=\"fu-line\"]').textContent")
        self.assertIn("Make this an action, a risk, a decision or an update", name)
        self.b.key("Escape")
        self.assertEqual(self.b.errors, [])

    def test_an_option_sends_only_the_selection_to_a_run_with_no_tools_and_accept_edits_the_note(self):
        b = self.b
        self.open_note()
        self.select("Sandbox access granted yesterday.")
        self.menu()
        b.click("#aiLayer [role=menu] [data-ai=rewrite]")
        self.ready()
        prompt = Path(str(self.fake) + ".edit.prompt").read_text()
        self.assertIn("<<<TEXT\nSandbox access granted yesterday.\nTEXT>>>", prompt)
        self.assertIn("Falcon Data Platform", prompt)                        # the note's project
        self.assertNotIn("probably moves", prompt)                          # never the rest of the note
        args = json.loads(Path(str(self.fake) + ".edit.argv.json").read_text())
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertEqual(args[args.index("--allowedTools") + 1], "")
        self.assertIn("--strict-mcp-config", args)
        self.assertNotIn("--add-dir", args)
        self.assertIn("Clearly: Sandbox access granted yesterday.", b.eval("document.querySelector('#aiLayer .aitext').textContent"))
        b.click("#aiLayer .aisug [data-aifirst]")                                                   # Accept
        b.wait("!document.querySelector('#aiLayer .aisug')")
        b.wait("document.querySelector('#v-notes .nbody').cxed.value().includes('Clearly: Sandbox access granted yesterday.')")
        b.wait("['typing','saving','saved'].includes(noteSave.value.state)", 10)            # an edit, saved as typing is
        b.pump(0.5)                                                                                  # the counts are posted, not awaited
        got, raw = self.stats()
        self.assertEqual((got.get("offered"), got.get("used")), (1, 1))
        self.assertNotIn("Sandbox", raw)
        self.assertNotIn("Clearly", raw)
        self.assertEqual(b.errors, [])

    def test_make_this_an_action_opens_find_updates_on_that_line_only(self):
        b = self.b
        self.open_note()
        self.select("probably moves two weeks")
        self.menu()
        b.click("#aiLayer [role=menu] [data-ai=\"fu-line\"]")
        b.wait("!!document.querySelector('#noteSide aside.fu') && ['ready','none','error','ask'].includes(fuState.value)", 40)
        self.assertEqual(b.eval("fuState.value"), "ready")
        self.assertEqual(b.eval("noteFindP.value"), 4)
        self.assertFalse(Path(str(self.fake) + ".edit.prompt").exists())                           # no edit run
        prompt = Path(str(self.fake) + ".find.prompt").read_text()
        self.assertIn(f"[p4] - {LINE4}", prompt)
        for n in (1, 2, 3, 5, 6, 7):
            self.assertNotIn(f"[p{n}] ", prompt)                                                 # that line only
        rows = b.eval("[...document.querySelectorAll('#noteSide .fu-r')].map(r=>r.dataset.p)")
        self.assertEqual(rows, ["4", "4"])                                                       # the milestone and its confirm action
        self.assertEqual(self.stats()[0], {})                                                    # no AI counts for a hand-over
        self.assertFalse(b.eval("!!document.querySelector('#aiLayer .aisug')"))
        self.assertEqual(b.errors, [])

    def test_a_selection_over_two_lines_runs_nothing_and_says_why(self):
        b = self.b
        self.open_note()
        self.select("Sandbox access", upto="probably moves")
        self.menu()
        b.click("#aiLayer [role=menu] [data-ai=\"fu-line\"]")
        b.wait("document.getElementById('snack').classList.contains('on')")
        self.assertIn("one line of the note", b.eval("document.getElementById('snackT').textContent"))
        b.pump(0.5)
        self.assertFalse(b.eval("!!document.querySelector('#noteSide aside.fu')"))
        self.assertFalse(Path(str(self.fake) + ".find.prompt").exists())
        self.assertEqual(b.errors, [])

    def test_a_confidential_note_asks_before_its_text_goes_to_claude(self):
        b = self.b
        self.open_note()
        b.eval("noteMeta({confidential: true}, true)")
        b.wait("noteCur.value.meta && noteCur.value.meta.confidential === true")
        self.select("Sandbox access granted")
        self.menu()
        b.click("#aiLayer [role=menu] [data-ai=rewrite]")
        b.wait("document.querySelector('#aiLayer .aisug [data-aifirst]')")
        self.assertIn("Send the selected text to Claude", b.eval("document.querySelector('#aiLayer .aisug').textContent"))
        b.pump(0.3)
        self.assertFalse(Path(str(self.fake) + ".edit.prompt").exists())                          # nothing sent yet
        b.click("#aiLayer .aisug [data-aifirst]")                                                   # Send to Claude
        self.ready()
        self.assertTrue(Path(str(self.fake) + ".edit.prompt").exists())
        b.key("Escape")
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()

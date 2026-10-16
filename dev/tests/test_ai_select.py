"""BL-301 D: AI on selected text, in every editor.

Run: python3 dev/tests/test_ai_select.py   (the browser tests need Google Chrome; skipped otherwise)

Done when (BL-301 D): each AI option returns a suggestion that changes nothing until Accept, with the fact check shown; the route
has no tools. Also: each place chooses its options; Accept is one undoable transaction; ⌘A then the bar, and Alt+/ from the
keyboard; "Or say what you want…"; a confidential text asks once; counts only in draft-stats.json; 320px. Claude is a stand-in
(never a real model call) that records how it was started.
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
META, ALT = 4, 1

FAKE = r'''#!/usr/bin/env python3
import json, re, sys
args = sys.argv[1:]
open(__file__ + ".argv.json", "w", encoding="utf-8").write(json.dumps(args))
p = args[args.index("--") + 1]
open(__file__ + ".prompt", "w", encoding="utf-8").write(p)
text = re.search(r"<<<TEXT\n(.*?)\nTEXT>>>", p, re.S).group(1)
if "The text is one line" in p:
    out = "Clearly: " + text + "\nand a second line"
elif "Make the text shorter" in p:
    out = text.split(".")[0] + ". Due 20-10-2026."
elif "Correct the spelling" in p:
    out = text.replace("teh", "the")
elif "Do what Alan asks" in p:
    out = text.upper()
else:
    out = "Clearly: " + text
reply = "<<<SUGGESTION\n" + out + "\nSUGGESTION>>>"
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-e"}), flush=True)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}}), flush=True)
print(json.dumps({"type": "result", "result": reply, "session_id": "sess-e"}), flush=True)
'''


def edit_ai(v, cmd, body=None):
    r = subprocess.run([sys.executable, "system/scripts/edit_ai.py", cmd], input=json.dumps(body or {}), capture_output=True,
                       text=True, cwd=v.root)
    return json.loads(r.stdout)


class TheScript(unittest.TestCase):
    """edit_ai.py: the options, what the prompt holds, the refusals and the plain-code check."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def test_each_place_chooses_its_options_and_the_page_lists_the_same(self):
        got = edit_ai(self.v, "options")
        ids = {p: [o["id"] for o in L] for p, L in got.items()}
        self.assertEqual(ids["notes"][0], "notes")                         # Format notes leads where blocks exist
        self.assertNotIn("spelling", [i for L in ids.values() for i in L])  # no separate spelling option (BL-117)
        self.assertIn("checklist", ids["notes"])
        self.assertNotIn("checklist", ids["current"])                     # Current state takes no checklists
        self.assertFalse({"format", "checklist", "summary"} & set(ids["plain"]))   # plain text stays plain
        self.assertTrue({"formal", "warmer"} <= set(ids["email"]))         # the Draft email adds More formal and Warmer
        self.assertTrue(all(L[-1] == "custom" for L in ids.values()))      # "Or say what you want…" last everywhere
        page = (REPO / "system/templates/dashboard/src/stores/aiEdit.js").read_text()
        block = re.search(r"AI_PLACES = /\*\* .*? \*/ \(\{(.*?)\}\);", page, re.S).group(1)
        page_ids = {m.group(1): re.findall(r'"(\w+)"', m.group(2)) for m in re.finditer(r"(\w+): \[(.*?)\]", block)}
        self.assertEqual(page_ids, ids)
        groups = re.search(r"AI_GROUPS = /\*\* .*? \*/ \(\{(.*?)\}\);", page, re.S).group(1)       # the bar's groups hold only offered options
        for place, body in re.findall(r"(\w+): \[(\[.*?\])\],?\n", groups):
            grouped = set(re.findall(r'"(\w+)"', re.sub(r'\["[A-Z][\w ]*",', "[", body)))
            self.assertLessEqual(grouped, set(ids[place]), place)
            self.assertEqual(grouped, set(ids[place]) - {"notes", "custom"}, place)   # every other option is in a group
        # each place's option set, as the issue lists it
        self.assertEqual(ids["email"], ["rewrite", "shorter", "longer", "formal", "warmer", "custom"])
        self.assertEqual(ids["plain"], ["rewrite", "shorter", "executive", "custom"])
        self.assertEqual(ids["line"], ids["plain"])
        self.assertNotIn("checklist", ids["current"])

    def test_the_prompt_holds_the_text_the_option_and_the_projects_name_people_and_open_ids_only(self):
        ctx = edit_ai(self.v, "context", {"option": "shorter", "text": "Escalate the data access issue.", "code": "ABC", "place": "current"})
        p = ctx["prompt"]
        self.assertIn("Escalate the data access issue.", p)
        self.assertIn("Make the text shorter", p)
        self.assertIn("Example Programme", p)
        self.assertRegex(p, r"Its open item IDs: ABC-")
        self.assertNotIn("Build is two weeks behind", p)                  # the project's Current state is never sent
        self.assertNotIn("You have tools", p)
        self.assertIn("no tools", p)

    def test_every_reshape_fixes_spelling_and_grammar_and_format_notes_keeps_every_point(self):
        for opt in ("rewrite", "shorter", "longer", "executive", "format", "checklist", "summary", "notes"):
            ctx = edit_ai(self.v, "context", {"option": opt, "text": "First point.\n\nSecond point.", "code": "ABC", "place": "notes"})
            self.assertIn("spelling, grammar and punctuation, in British English", ctx["prompt"], opt)
        notes = edit_ai(self.v, "context", {"option": "notes", "text": "met sara\n\nlate by 2 weeks 20-10-2026", "place": "notes"})
        self.assertIn("Keep every point", notes["prompt"])
        self.assertIn("add nothing", notes["prompt"])
        self.assertIn("keep those headings", notes["prompt"])               # a Working session note keeps its own
        custom = edit_ai(self.v, "context", {"option": "custom", "instruction": "Make it louder", "text": "x", "place": "plain"})
        self.assertNotIn("spelling, grammar", custom["prompt"])              # Ask… does only what was asked
        lost = edit_ai(self.v, "result", {"context": {"original": "Met Sara Khan on 20-10-2026, 40% done, ABC-A-001.", "people": ["Sara Khan"]},
                                          "reply": "<<<SUGGESTION\n## Notes\n- Met on 20-10-2026.\nSUGGESTION>>>"})
        self.assertTrue({"ids-lost", "names-lost"} <= {n["id"] for n in lost["notes"]})   # the check names what the sort lost

    def test_make_it_executive_carries_the_executive_voice(self):
        ctx = edit_ai(self.v, "context", {"option": "executive", "text": "We are late.", "code": "ABC", "place": "plain"})
        self.assertIn("Bottom line first", ctx["prompt"])

    def test_requests_it_refuses(self):
        for body, why in (({"option": "nope", "text": "x", "place": "plain"}, "offered"),
                          ({"option": "spelling", "text": "x", "place": "notes"}, "offered"),         # gone (BL-117)
                          ({"option": "notes", "text": "One paragraph only.", "place": "notes"}, "two or more"),
                          ({"option": "notes", "text": "x\n\ny", "place": "plain"}, "offered"),
                          ({"option": "checklist", "text": "x", "place": "plain"}, "offered"),
                          ({"option": "rewrite", "text": "x", "place": "elsewhere"}, "place"),
                          ({"option": "rewrite", "text": "  ", "place": "plain"}, "Select"),
                          ({"option": "rewrite", "text": "x" * 13000, "place": "plain"}, "too much"),
                          ({"option": "custom", "text": "x", "place": "plain"}, "Say what")):
            self.assertIn(why, edit_ai(self.v, "context", body).get("refused", ""), body)

    def test_the_check_notes_every_date_number_name_and_id_lost_or_added(self):
        got = edit_ai(self.v, "result", {"context": {"original": "Sara Khan to confirm ABC-A-001 by 16-10-2026, 40% done.",
                                                     "people": ["Sara Khan"]},
                                         "reply": "<<<SUGGESTION\nOmar Ali confirms by 20-10-2026.\nSUGGESTION>>>"})
        self.assertEqual(got["text"], "Omar Ali confirms by 20-10-2026.")
        notes = " | ".join(n["note"] for n in got["notes"])
        for word in ("16-10-2026", "40%", "20-10-2026", "ABC-A-001", "Sara Khan", "Omar Ali"):
            self.assertIn(word, notes)
        self.assertNotIn("001,", notes)                                   # an ID's digits aren't a number of their own
        same = edit_ai(self.v, "result", {"context": {"original": "Sara Khan by 16-10-2026."},
                                          "reply": "<<<SUGGESTION\nSara Khan by 16-10-2026.\nSUGGESTION>>>"})
        self.assertEqual(same["notes"], [])

    def test_a_one_line_field_asks_for_one_line_and_gets_one_line(self):
        ctx = edit_ai(self.v, "context", {"option": "shorter", "text": "Data access is late", "code": "ABC", "place": "line"})
        self.assertIn("one line of plain text only", ctx["prompt"])
        self.assertEqual(ctx["format"], "line")
        got = edit_ai(self.v, "result", {"context": ctx, "reply": "<<<SUGGESTION\nData access\n\n  late again\nSUGGESTION>>>"})
        self.assertEqual(got["text"], "Data access late again")
        self.assertIn("refused", edit_ai(self.v, "context", {"option": "longer", "text": "x", "place": "line"}))

    def test_a_reply_without_its_markers_is_taken_whole(self):
        got = edit_ai(self.v, "result", {"context": {"original": "a"}, "reply": "Just the text.\n"})
        self.assertEqual(got["text"], "Just the text.")


class AiOnSelection(LiveBrowserCase):
    """The bar, the suggestion and the route, in a real browser against the live server, with a stand-in Claude."""

    shared_server = True
    width, height = 1280, 900

    @classmethod
    def load(cls, v):
        populate(v)
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(FAKE)
        cls.fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake)}

    def setUp(self):
        super().setUp()
        self.b.eval("AI_PLACE_TABLE.plain.ai=true; AI_PLACE_TABLE.line.ai=true; true")     # v2.2.0's places, switched on for these tests
        self.addCleanup(lambda: self.b and self.b.eval("AI_PLACE_TABLE.plain.ai=false; AI_PLACE_TABLE.line.ai=false; true"))

    def test_the_place_table_lists_every_place_and_off_places_show_no_ai_element(self):
        b = self.b
        b.eval("AI_PLACE_TABLE.plain.ai=false; AI_PLACE_TABLE.line.ai=false; true")
        self.assertEqual(b.eval("Object.fromEntries(Object.entries(AI_PLACE_TABLE).map(([k,v])=>[k,v.ai]))"),
                         {"notes": True, "current": True, "email": False, "plain": False, "line": False})
        for place in ("email", "plain", "line"):
            b.eval("""(p=>{ document.getElementById('offx')?.remove(); const el=document.createElement('div'); el.id='offx';
              el.style.cssText='position:fixed;top:120px;left:120px;width:400px;z-index:100;background:var(--surface)';
              document.body.appendChild(el); const h=creaiteEditor(el,{features:'plain',text:'Some text here.',ai:{place:p}});
              h.focus(); h.editor.commands.selectAll(); })(%s)""" % json.dumps(place))
            b.pump(0.4)
            self.assertFalse(b.eval("!!document.querySelector('#aiLayer .aispark, #aiLayer .aibar')"), place)
            b.eval("document.getElementById('offx').cxed.destroy(); document.getElementById('offx').remove(); true")

    def stats(self):
        p = self.v.root / "system/staging/draft-stats.json"
        return json.loads(p.read_text()).get("edit", {}) if p.exists() else {}

    def open_current(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard [data-edcur]')")
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("!!(document.getElementById('curEd')&&document.getElementById('curEd').cxed)")
        self.addCleanup(lambda: self.b and self.b.eval("shared.CURED&&curDrop()"))

    def select_words(self, el, words):
        """Select `words` in the editor on `el` (the cursor there), as a person would."""
        self.b.click(el)
        self.b.eval("""(()=>{ const h=document.querySelector(%s).cxed, doc=h.editor.state.doc; let at=-1;
          doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf(%s); if(i>=0) at=pos+i; } });
          h.focus(); h.editor.commands.setTextSelection({from:at,to:at+%d}); })()""" % (json.dumps(el), json.dumps(words), len(words)))
        self.b.wait("document.querySelector('#aiLayer .aispark')")
        self.b.click("#aiLayer .aispark")                                   # the sparkle in the margin opens the bar
        self.b.wait("document.querySelector('#aiLayer .aibar')")

    GROUP = {"rewrite": "improve", "shorter": "improve", "longer": "improve", "executive": "improve", "format": "structure",
             "checklist": "structure", "summary": "structure", "formal": "tone", "warmer": "tone"}

    def open_group(self, group):
        self.b.click(f'#aiLayer .aibar button[data-tip="AI: {group}"]')
        self.b.wait("document.querySelector('#aiLayer [role=menu]')")

    def pick(self, option):
        b = self.b
        self.open_group(self.GROUP[option])
        b.click(f"#aiLayer [role=menu] [data-ai={option}]")

    def bar_options(self):
        """Every AI option the open bar offers, group by group: [(group, [ids])], then Ask… and Format notes if present."""
        b = self.b
        out = []
        for g in b.eval("[...document.querySelectorAll('#aiLayer .aibar .aiai button[aria-haspopup]')].map(x=>x.dataset.tip.slice(4))"):
            self.open_group(g)
            out.append((g, b.eval("[...document.querySelectorAll('#aiLayer [role=menu] [data-ai]')].map(e=>e.dataset.ai)")))
            b.key("Escape")
            b.wait("!document.querySelector('#aiLayer [role=menu]')")
        return out

    def ready(self):
        self.b.wait("document.querySelector('#aiLayer .aisug .aitext')||document.querySelector('#aiLayer .aisug [role=alert]')", 20)
        return self.b.eval("document.querySelector('#aiLayer .aisug').textContent")

    def test_a_suggestion_changes_nothing_until_accept_and_one_undo_takes_it_back(self):
        b = self.b
        self.open_current()
        before = b.eval("edValue(document.getElementById('curEd'))")
        sentence = "Build is two weeks behind because data access is late"
        self.select_words("#curEd", sentence)
        self.assertEqual(self.bar_options(), [("improve", ["rewrite", "shorter", "longer", "executive"]), ("structure", ["format", "summary"])])
        self.assertFalse(b.eval("!!document.querySelector('#aiLayer .aifmt')"))          # Current state: no Turn into
        self.assertFalse(b.eval("!!document.querySelector('#aiLayer [data-ai=notes]')"))  # one sentence: no Format notes
        self.assertTrue(b.eval("!!document.querySelector('#aiLayer [data-ai=custom]')"))   # Ask… stays
        self.open_group("improve")
        b.click("#aiLayer [role=menu] [data-ai=shorter]")
        card = self.ready()
        self.assertIn("Shorter", card)
        self.assertIn("unchanged until you accept", card)
        self.assertEqual(b.eval("edValue(document.getElementById('curEd'))"), before)          # nothing changed yet
        self.assertIn("20-10-2026", b.eval("document.querySelector('#aiLayer .ainotes').textContent"))   # the check, under it
        self.assertEqual(b.eval("document.activeElement.textContent"), "Accept")
        b.click("#aiLayer .aisug button[aria-pressed]")                                          # Show changes
        b.wait("document.querySelector('#aiLayer .aisug ins.aiins')")
        self.assertIn("Due", b.eval("document.querySelector('#aiLayer .aisug ins.aiins').textContent"))
        self.assertTrue(b.eval("!!document.querySelector('#aiLayer .aisug del.aidel')"))
        b.click("#aiLayer .aisug [data-aifirst]")                                               # Accept
        b.wait("!document.querySelector('#aiLayer .aisug')")
        after = b.eval("edValue(document.getElementById('curEd'))")
        self.assertIn("Build is two weeks behind because data access is late. Due 20-10-2026.", after)
        self.assertIn("UAT preparation continues on masked data.", after)                         # the rest untouched
        b.eval("document.getElementById('curEd').cxed.focus()")
        b.key("z", META)
        b.wait("edValue(document.getElementById('curEd'))===%s" % json.dumps(before))           # one ⌘Z, all of it

    def test_discard_try_again_and_the_counts_hold_no_text(self):
        b = self.b
        self.open_current()
        start = self.stats()
        self.select_words("#curEd", "UAT preparation continues")
        self.pick("rewrite")
        self.ready()
        b.click("#aiLayer .aisug .aiacts button:nth-child(2)")                                   # Try again
        self.ready()
        before = b.eval("edValue(document.getElementById('curEd'))")
        b.key("Escape")                                                                           # Discard
        b.wait("!document.querySelector('#aiLayer .aisug')")
        self.assertEqual(b.eval("edValue(document.getElementById('curEd'))"), before)
        self.assertTrue(b.eval("!!document.getElementById('curEd')"))                           # Esc left the editor open
        b.pump(0.5)                                                                               # the counts are posted, not awaited
        got = self.stats()
        self.assertEqual(got.get("offered", 0) - start.get("offered", 0), 2)
        self.assertEqual(got.get("rejected", 0) - start.get("rejected", 0), 2)
        raw = (self.v.root / "system/staging/draft-stats.json").read_text()
        self.assertNotIn("UAT", raw)

    def test_select_all_then_alt_slash_and_say_what_you_want(self):
        b = self.b
        self.open_current()
        b.eval("document.getElementById('curEd').cxed.focus()")
        b.key("a", META)                                                                          # ⌘A: the whole pane
        b.wait("document.querySelector('#aiLayer .aispark')")                                   # the sparkle, bar still closed
        self.assertFalse(b.eval("!!document.querySelector('#aiLayer .aibar')"))
        b.key("/", ALT)
        b.wait("document.querySelector('#aiLayer [role=menu]')&&document.activeElement.closest('[role=menu]')")
        b.key("Escape")
        b.click("#aiLayer .aibar [data-ai=custom]")
        b.wait("document.activeElement&&document.activeElement.matches('#aiLayer .aiask input')")
        b.type("Make it louder")
        b.key("Enter")
        self.ready()
        self.assertIn("BUILD IS TWO WEEKS BEHIND", b.eval("document.querySelector('#aiLayer .aitext').textContent"))
        self.assertIn("Make it louder", b.eval("document.getElementById('aiSugH').textContent"))
        self.assertIn("Do what Alan asks with the text, and only that. His instruction: Make it louder",
                      Path(str(self.fake) + ".prompt").read_text())
        b.key("Escape")

    def test_the_route_runs_claude_with_no_tools_at_all(self):
        self.open_current()
        self.select_words("#curEd", "UAT preparation")
        self.pick("rewrite")
        self.ready()
        args = json.loads(Path(str(self.fake) + ".argv.json").read_text())
        self.assertEqual(args[args.index("--tools") + 1], "")
        self.assertIn("--strict-mcp-config", args)
        self.assertNotIn("--add-dir", args)
        self.assertNotIn("--settings", args)
        self.assertEqual(args[args.index("--allowedTools") + 1], "")
        denied = args[args.index("--disallowedTools") + 1].split(",")
        for tool in ("Read", "Grep", "Glob", "Bash", "Write", "Edit", "WebFetch", "WebSearch"):
            self.assertIn(tool, denied)
        self.b.key("Escape")

    def test_a_confidential_text_asks_once_before_it_goes_to_claude(self):
        b = self.b
        prompt = Path(str(self.fake) + ".prompt")
        b.eval("""(()=>{ document.getElementById('cfx')?.remove(); const el=document.createElement('div'); el.id='cfx';
          el.style.cssText='position:fixed;top:120px;left:120px;width:400px;z-index:100;background:var(--surface)';
          document.body.appendChild(el); creaiteEditor(el,{features:'plain',text:'A confidential plan for the board.',
          ai:{place:'plain',confidential:()=>true,key:()=>'note-1'}}); })()""")
        for asked in (True, False):
            mark = prompt.stat().st_mtime if prompt.exists() else 0
            self.select_words("#cfx", "confidential plan")
            self.pick("rewrite")
            if asked:
                b.wait("document.querySelector('#aiLayer .aisug [data-aifirst]')")
                self.assertIn("Send the selected text to Claude", b.eval("document.querySelector('#aiLayer .aisug').textContent"))
                b.pump(0.3)
                self.assertEqual(prompt.stat().st_mtime if prompt.exists() else 0, mark)      # nothing sent yet
                b.click("#aiLayer .aisug [data-aifirst]")                                       # Send to Claude
            self.ready()
            self.assertIn("Clearly: confidential plan", b.eval("document.querySelector('#aiLayer .aitext').textContent"))
            b.key("Escape")
            b.wait("!document.querySelector('#aiLayer .aisug')")
        b.eval("document.getElementById('cfx').cxed.destroy(); document.getElementById('cfx').remove()")

    def test_the_peeks_longer_fields_offer_the_plain_text_options(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        id_ = b.eval("A.find(x=>x.p==='ABC').id")
        b.eval(f"openRecord('actions',{id_!r})")
        b.wait("!!(document.getElementById('pkDesc')&&document.getElementById('pkDesc').cxed)")
        self.addCleanup(lambda: self.b and self.b.eval("closePanel&&closePanel()"))
        b.eval("document.getElementById('pkDesc').cxed.setValue('Sara to send teh plan.')")
        b.click("#pkDesc")
        b.key("a", META)                                                                          # ⌘A: all of the field
        b.wait("document.querySelector('#aiLayer .aispark')")
        b.click("#aiLayer .aispark")
        b.wait("document.querySelector('#aiLayer .aibar')")
        self.assertEqual(self.bar_options(), [("improve", ["rewrite", "shorter", "executive"])])   # a plain field: Improve only
        self.pick("rewrite")
        self.ready()
        self.assertIn("Keeps your dates", b.eval("document.querySelector('#aiLayer .aisug').textContent"))
        self.assertIn("Spelling and grammar fixed too", b.eval("document.querySelector('#aiLayer .aisug').textContent"))
        b.click("#aiLayer .aisug [data-aifirst]")
        b.wait("document.getElementById('pkDesc').textContent==='Clearly: Sara to send teh plan.'")

    def test_the_peeks_title_stays_one_line(self):
        """Alan, 14-10-2026: the title has AI on a selection too; the suggestion is one line and Accept never breaks it."""
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        id_ = b.eval("A.find(x=>x.p==='ABC').id")
        b.eval(f"openRecord('actions',{id_!r})")
        b.wait("!!(document.getElementById('pkTitle')&&document.getElementById('pkTitle').cxed)")
        self.addCleanup(lambda: self.b and self.b.eval("closePanel&&closePanel()"))
        b.eval("document.getElementById('pkTitle').cxed.setValue('Confirm data access date')")
        b.click("#pkTitle")
        b.key("a", META)
        b.wait("document.querySelector('#aiLayer .aispark')")
        b.click("#aiLayer .aispark")
        b.wait("document.querySelector('#aiLayer .aibar')")
        self.assertEqual(self.bar_options(), [("improve", ["rewrite", "shorter", "executive"])])
        self.pick("rewrite")
        self.ready()
        self.assertIn("The text is one line", Path(str(self.fake) + ".prompt").read_text())
        self.assertEqual(b.eval("document.querySelector('#aiLayer .aitext').textContent"),
                         "Clearly: Confirm data access date and a second line")             # the reply's break is gone
        b.click("#aiLayer .aisug [data-aifirst]")
        b.wait("!document.querySelector('#aiLayer .aisug')")
        self.assertEqual(b.eval("[document.getElementById('pkTitle').textContent, document.querySelectorAll('#pkTitle p').length]"),
                         ["Clearly: Confirm data access date and a second line", 1])

    def test_make_it_executive_is_an_option_of_ai_beside_save(self):
        b = self.b
        self.open_current()
        self.assertFalse(b.eval("!!document.querySelector('.curacts > [data-exec]')"))           # no button of its own now
        b.click("#curAi button[aria-haspopup]")
        b.wait("document.querySelector('#curAi [role=menu]')")
        self.assertTrue(b.eval("!!document.querySelector('#curAi [role=menu] [data-exec]')"))
        self.assertIn("Make it executive", b.eval("document.querySelector('#curAi [role=menu] [data-exec]').textContent"))
        b.key("Escape")

    def test_at_320px_the_suggestion_fits_and_nothing_scrolls_sideways(self):
        b = self.b
        b.resize(320, 700)
        self.addCleanup(lambda: self.b and self.b.resize(self.width, self.height))
        self.open_current()
        self.select_words("#curEd", "UAT preparation continues")
        self.pick("shorter")
        self.ready()
        box = b.eval("(()=>{ const r=document.querySelector('#aiLayer .aisug').getBoundingClientRect(); return [r.left,r.right,innerWidth]; })()")
        self.assertGreaterEqual(box[0], 0)
        self.assertLessEqual(box[1], box[2])
        self.assertLessEqual(b.eval("document.documentElement.scrollWidth"), b.eval("innerWidth"))
        heights = b.eval("[...document.querySelectorAll('#aiLayer .aisug .aiacts button')].map(x=>x.getBoundingClientRect().height)")
        self.assertTrue(all(h >= 24 for h in heights), heights)                                   # 24px targets
        b.key("Escape")


if __name__ == "__main__":
    unittest.main()

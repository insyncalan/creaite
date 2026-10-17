"""#117: the selection bar on the shared editor: the margin sparkle, the grouped hover bar, Turn into (no AI) kept apart from the AI
zone, Format notes, and the place table that switches the places on.

Run: python3 dev/tests/test_ai_117.py   (the browser tests need Google Chrome; skipped otherwise)

Done when (#117, Alan's decisions 15-10-2026): the place table lists notes, current, email, plain and line and says on or off for each
(v2.1.0: notes and current on; the others are built and OFF, and show no AI element); Turn into is Notes only and uses the editor's own
commands (so Current state's reversible heading mapping would apply); Format notes is offered for two or more paragraphs, with each
place's own heading levels (a note `#` to `###`; Current state `###` to `#####`, and no `## ` line is ever written into it); there is no
spelling option and the card says spelling is fixed too; the bar sits near the selection (flips above at the bottom), at 1400 and 900;
the keyboard flow, dark and forced colours, 24 px targets. The bar sets its own attribute names and none of the `/` menu's on the editor.
Claude is a stand-in (never a real model call) that reads the prompt after `--` and answers with a reply the test chose.
"""
import json
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_tracker import Vault  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system/scripts"))
import edit_ai  # noqa: E402

META, ALT = 4, 1
LAYER = "#aiLayer"
NOTE = "Agree the approach with legal.\n\nthe uat dates is not confirmed\n\nSend the revised agrement by friday"
CURRENT = "### Where we are\n\nBuild is two weeks behind because data access is late.\n\nUAT preparation has started."

# The stand-in: reads the prompt after `--`, keeps it and the argv beside itself, answers with the reply the test wrote to <script>.reply
# (else "Clearly: <the text>").
FAKE = r'''#!/usr/bin/env python3
import json, os, re, sys
args = sys.argv[1:]
p = args[args.index("--") + 1]
open(__file__ + ".prompt", "w", encoding="utf-8").write(p)
open(__file__ + ".argv.json", "w", encoding="utf-8").write(json.dumps(args))
text = re.search(r"<<<TEXT\n(.*?)\nTEXT>>>", p, re.S).group(1)
out = open(__file__ + ".reply", encoding="utf-8").read() if os.path.exists(__file__ + ".reply") else "Clearly: " + text
reply = "<<<SUGGESTION\n" + out + "\nSUGGESTION>>>"
print(json.dumps({"type": "system", "subtype": "init", "session_id": "sess-117"}), flush=True)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": reply}]}}), flush=True)
print(json.dumps({"type": "result", "result": reply, "session_id": "sess-117"}), flush=True)
'''

# one editor of a place in a box of its own (fixed, so the page's layout never matters); `top` sets how far down it sits
MOUNT = """((place,md,top,left)=>{ document.getElementById('aiFix')?.remove(); aiSug.value=null; aiBar.value=null;
  const box=document.createElement('div'); box.id='aiFix';
  box.style.cssText=`position:fixed;top:${top}px;left:${left}px;width:520px;z-index:100;background:var(--surface);padding:8px;color:var(--ink)`;
  document.body.appendChild(box); const el=document.createElement('div'); el.id='aiEd'; el.className='ned nbody'; box.appendChild(el);
  const f=place==='notes'?'notes':place==='current'?'current':'plain';
  window.AIE=creaiteEditor(el,{features:f,...(f==='plain'?{text:md}:{markdown:md}),headShift:place==='current'?2:0,
    ai:{place,project:()=>'ABC'},multiline:place!=='line'});
  return true; })"""
CLEAN = "aiSug.value=null; aiBar.value=null; window.AIE&&AIE.destroy(); document.getElementById('aiFix')?.remove(); true"


class TheServerSide(unittest.TestCase):
    """edit_ai.py: the places, the per-place Markdown rules, Format notes, the spelling sentence and Current state's heading guard."""

    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        from test_dashboard import populate
        populate(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def ctx(self, body):
        r = subprocess.run([sys.executable, "system/scripts/edit_ai.py", "context"], input=json.dumps(body), capture_output=True,
                           text=True, cwd=self.v.root)
        return json.loads(r.stdout)

    def result(self, body):
        r = subprocess.run([sys.executable, "system/scripts/edit_ai.py", "result"], input=json.dumps(body), capture_output=True,
                           text=True, cwd=self.v.root)
        return json.loads(r.stdout)

    def test_places_options_and_the_room_for_a_client_place(self):
        self.assertEqual(sorted(edit_ai.PLACES), ["current", "email", "line", "minutes", "notes", "plain", "readonly", "report"])
        self.assertEqual(set(edit_ai.PLACES), set(edit_ai.FORMATS))             # a new place (`client`) is one entry in each of these
        self.assertEqual(set(edit_ai.PLACES), set(edit_ai.FORMAT_RULES))
        self.assertEqual(edit_ai.PLACES["notes"], ["notes", "rewrite", "shorter", "longer", "executive", "format", "checklist", "summary", "custom"])
        self.assertEqual(edit_ai.PLACES["current"], ["notes", "rewrite", "shorter", "longer", "executive", "format", "summary", "custom"])
        self.assertEqual(edit_ai.PLACES["plain"], ["rewrite", "shorter", "executive", "custom"])
        self.assertEqual(edit_ai.PLACES["line"], edit_ai.PLACES["plain"])
        self.assertEqual(edit_ai.PLACES["email"], ["rewrite", "shorter", "longer", "formal", "warmer", "custom"])
        self.assertNotIn("spelling", edit_ai.OPTIONS)                           # no spelling item
        self.assertEqual(edit_ai.OPTIONS["format"][0], "Add headings and bold")        # renamed rows
        self.assertEqual(edit_ai.OPTIONS["checklist"][0], "Pull out the tasks")
        self.assertEqual(edit_ai.OPTIONS["notes"][0], "Format notes")
        for p, ids in edit_ai.PLACES.items():
            self.assertLessEqual(set(ids), set(edit_ai.OPTIONS), p)

    def test_format_rules_per_place(self):
        notes, cur = edit_ai.FORMAT_RULES["notes"], edit_ai.FORMAT_RULES["current"]
        self.assertIn('"# ", "## " and "### "', notes)
        self.assertIn("task items", notes)
        self.assertIn('"### ", "#### " and "##### "', cur)                      # Current state is stored shifted; the AI sees the stored levels
        self.assertIn('never "# " or "## "', cur)
        self.assertNotIn("task items", cur)                                     # no checklists in Current state
        for p in ("plain", "email"):
            self.assertIn("plain text", edit_ai.FORMAT_RULES[p])
        self.assertIn("one line", edit_ai.FORMAT_RULES["line"])
        # the rule reaches the prompt of its own place
        self.assertIn('"### ", "#### " and "##### "', self.ctx({"option": "rewrite", "text": "### A\n\nx", "place": "current"})["prompt"])
        self.assertIn('"# ", "## " and "### "', self.ctx({"option": "rewrite", "text": "# A\n\nx", "place": "notes"})["prompt"])

    def test_every_option_but_ask_fixes_spelling_and_grammar(self):
        for place, ids in edit_ai.PLACES.items():
            if place in edit_ai.SHEET_PLACES:                                   # the sheet's prompts stay as shipped (below)
                continue
            for opt in ids:
                if opt == "custom":
                    continue
                text = "First point.\n\nSecond point." if opt == "notes" else "A point."
                p = self.ctx({"option": opt, "text": text, "place": place})["prompt"]
                self.assertIn("Also correct any spelling, grammar and punctuation, in British English", p, (place, opt))
        p = self.ctx({"option": "custom", "instruction": "Make it louder", "text": "x", "place": "notes"})["prompt"]
        self.assertNotIn("spelling, grammar", p)                                # Ask… does only what was asked

    def test_the_sheets_places_stay_exactly_as_v210_shipped(self):
        """Safety (#117 merged onto v2.1.0): the A4 sheet's places ("report" is the client report's) keep their shipped option sets,
        format, Markdown rule and prompt; #117 adds no option, no spelling sentence and no format rule to them."""
        self.assertEqual(edit_ai.SHEET_PLACES, ("report", "minutes", "readonly"))
        self.assertEqual(edit_ai.PLACES["report"], ["shorter", "executive", "polish", "custom"])
        self.assertEqual(edit_ai.PLACES["minutes"], edit_ai.PLACES["report"])
        self.assertEqual(edit_ai.PLACES["readonly"], [])
        self.assertEqual({p: edit_ai.FORMATS[p] for p in edit_ai.SHEET_PLACES},
                         {"report": "markdown", "minutes": "markdown", "readonly": "plain"})
        shipped = ('The text is Markdown. Reply in Markdown, using only bold, italic, "- " bullets, numbered lists, "### " '
                   'sub-headings, quotes, links. Keep any link, image or HTML comment exactly as it is.')
        self.assertEqual(edit_ai.FORMAT_RULES["report"], shipped)
        self.assertEqual(edit_ai.FORMAT_RULES["minutes"], shipped)
        self.assertEqual(edit_ai.FORMAT_RULES["readonly"], edit_ai.FORMAT_RULES["plain"])
        self.assertEqual(edit_ai.OPTIONS["polish"][2][:17], "Polish the text: ")
        for place in ("report", "minutes"):
            for opt in edit_ai.PLACES[place]:
                body = {"option": opt, "text": "UAT slipped two weeks.", "place": place, "code": "ABC"}
                if opt == "custom":
                    body["instruction"] = "Tighten it"
                p = self.ctx(body)["prompt"]
                self.assertNotIn("Also correct any spelling", p, (place, opt))   # no #117 sentence on the sheet
                self.assertIn(shipped, p, (place, opt))
                self.assertNotIn("task items", p, (place, opt))
            for opt in ("notes", "rewrite", "longer", "format", "checklist", "summary", "formal", "warmer"):
                self.assertIn("offered", self.ctx({"option": opt, "text": "One\n\nTwo", "place": place})["refused"], (place, opt))
        self.assertIn("offered", self.ctx({"option": "shorter", "text": "x", "place": "readonly"})["refused"])
        self.assertEqual(edit_ai.relevel("## x", "report"), "## x")             # no heading shift on the sheet

    def test_format_notes_needs_two_or_more_paragraphs_and_a_place_that_has_it(self):
        self.assertIn("two or more", self.ctx({"option": "notes", "text": "One paragraph only.", "place": "notes"})["refused"])
        self.assertIn("two or more", self.ctx({"option": "notes", "text": "  \n One\n\n ", "place": "current"})["refused"])
        self.assertNotIn("refused", self.ctx({"option": "notes", "text": "One\n\nTwo", "place": "notes"}))
        self.assertNotIn("refused", self.ctx({"option": "notes", "text": "One\n\nTwo", "place": "current"}))
        for place in ("plain", "line", "email"):
            self.assertIn("offered", self.ctx({"option": "notes", "text": "One\n\nTwo", "place": place})["refused"])
        self.assertIn("offered", self.ctx({"option": "spelling", "text": "x", "place": "notes"})["refused"])      # gone
        self.assertIn("offered", self.ctx({"option": "checklist", "text": "x", "place": "current"})["refused"])

    def test_current_state_never_gets_a_heading_that_would_cut_its_section(self):
        c = self.ctx({"option": "notes", "text": "### Plan\n\nrough bits\n\nmore bits", "place": "current"})
        reply = "# Top\n\n## Stray\n- a\n\n### Kept\n#### Deeper\n```\n## in code\n```\n> ## quoted"
        got = self.result({"context": c, "reply": "<<<SUGGESTION\n" + reply + "\nSUGGESTION>>>"})["text"]
        self.assertFalse(re.search(r"^(#|##) ", re.sub(r"```.*?```", "", got, flags=re.S), re.M), got)      # no `# ` or `## ` line outside code
        self.assertIn("#### Stray", got)                                        # a stray ## ends as ####
        self.assertIn("### Top", got)
        self.assertIn("### Kept", got)
        self.assertIn("#### Deeper", got)
        self.assertIn("## in code", got)                                        # fenced code is left alone
        self.assertIn("> #### quoted", got)
        # a note keeps what it was given
        n = self.ctx({"option": "notes", "text": "x\n\ny", "place": "notes"})
        self.assertIn("## Stray", self.result({"context": n, "reply": "<<<SUGGESTION\n## Stray\n- a\nSUGGESTION>>>"})["text"])
        self.assertEqual(edit_ai.relevel("## x", "notes"), "## x")
        self.assertEqual(edit_ai.relevel("## x", "current"), "#### x")

    def test_the_run_is_not_touched(self):
        """#117 must not change how the AI run is started (live_server.py KIND_ARGS["edit-ai"], its tool-less run and pins)."""
        src = (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
        self.assertIn('"edit-ai"', src)
        self.assertRegex(src, r'--tools",\s*""')
        self.assertIn("--strict-mcp-config", src)


class Bar117(LiveBrowserCase):
    shared_server = True        # nothing it does is written
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(FAKE)
        cls.fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake)}

    def setUp(self):
        super().setUp()
        Path(str(self.fake) + ".reply").unlink(missing_ok=True)
        self.addCleanup(lambda: Path(str(self.fake) + ".reply").unlink(missing_ok=True))
        self.addCleanup(lambda: self.b and self.b.eval(CLEAN))

    # ---- helpers -----------------------------------------------------------------------------------------------------------
    def mount(self, place, md, top=80, left=140):
        self.b.eval(f"{MOUNT}({json.dumps(place)},{json.dumps(md)},{top},{left})")
        self.b.wait("!!document.querySelector('#aiEd.ProseMirror')")

    def select_all(self, spark=True, bar=True):
        b = self.b
        b.click("#aiEd")
        b.key("a", META)
        if spark:
            b.wait(f"document.querySelector('{LAYER} .aispark')")
        if bar:
            b.click(f"{LAYER} .aispark")
            b.wait(f"document.querySelector('{LAYER} .aibar')")

    def select_words(self, words, bar=True):
        b = self.b
        b.click("#aiEd")
        b.eval("""(w=>{ const h=AIE, doc=h.editor.state.doc; let at=-1;
          doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf(w); if(i>=0) at=pos+i; } });
          h.focus(); h.editor.commands.setTextSelection({from:at,to:at+w.length}); })(%s)""" % json.dumps(words))
        b.wait(f"document.querySelector('{LAYER} .aispark')")
        if bar:
            b.click(f"{LAYER} .aispark")
            b.wait(f"document.querySelector('{LAYER} .aibar')")

    def groups(self):
        """Every group the open bar lists, in order: [(name, [option ids])], read by opening each in turn (a click opens, Esc folds)."""
        b = self.b
        out = []
        for g in b.eval("[...document.querySelectorAll('#aiLayer .aibar .aiai button[aria-haspopup]')].map(x=>x.dataset.tip.slice(4))"):
            b.click(f'{LAYER} .aibar button[data-tip="AI: {g}"]')
            b.wait(f"document.querySelector('{LAYER} [role=menu]')")
            out.append((g, b.eval(f"[...document.querySelectorAll('{LAYER} [role=menu] [data-ai]')].map(e=>e.dataset.ai)")))
            b.key("Escape")
            b.wait(f"!document.querySelector('{LAYER} [role=menu]')")
        return out

    def turn_menu(self):
        b = self.b
        b.click(f"{LAYER} .aibar .aifmt button[aria-haspopup]")
        b.wait(f"document.querySelector('{LAYER} [role=menu]')")

    def ready(self):
        self.b.wait(f"document.querySelector('{LAYER} .aisug .aitext')||document.querySelector('{LAYER} .aisug [role=alert]')", 20)
        return self.b.eval(f"document.querySelector('{LAYER} .aisug').textContent")

    def reply(self, text):
        Path(str(self.fake) + ".reply").write_text(text, encoding="utf-8")

    # ---- the place table ---------------------------------------------------------------------------------------------------
    def test_the_place_table_lists_every_place_and_says_on_or_off(self):
        b = self.b
        want = {"notes": dict(ai=True, turnInto=True, formatNotes=True, improveOnly=False),
                "current": dict(ai=True, turnInto=False, formatNotes=True, improveOnly=False),
                "email": dict(ai=False, turnInto=False, formatNotes=False, improveOnly=True),
                "plain": dict(ai=False, turnInto=False, formatNotes=False, improveOnly=True),
                "line": dict(ai=False, turnInto=False, formatNotes=False, improveOnly=True)}
        sheet = {"report", "minutes", "readonly"}
        self.assertEqual({k: v for k, v in b.eval("AI_PLACE_TABLE").items() if k not in sheet}, want)
        self.assertEqual([k for k in b.eval("Object.keys(AI_PLACE_TABLE)") if k not in sheet], list(want))
        self.assertEqual(set(b.eval("Object.keys(AI_PLACES)")), set(want) | sheet)             # the page, edit_ai.py and the groups list the same
        self.assertEqual(set(b.eval("Object.keys(AI_GROUPS)")), set(want) | sheet)
        self.assertEqual(set(edit_ai.PLACES), set(want) | sheet)
        self.assertEqual(b.eval("Object.keys(AI_PLACE_TABLE).filter(p=>['report','minutes','readonly'].includes(p))"),
                         ["report", "minutes", "readonly"])                    # the sheet's places stay on, with no Turn into or Format notes
        for p in ("report", "minutes", "readonly"):
            self.assertEqual(b.eval(f"AI_PLACE_TABLE.{p}"), dict(ai=True, turnInto=False, formatNotes=False, improveOnly=False), p)
        for place, row in want.items():
            self.assertEqual(b.eval(f"aiPlaceOn({json.dumps(place)})"), row["ai"], place)
        for place, row in want.items():
            self.mount(place, NOTE)
            b.click("#aiEd")
            b.key("a", META)
            b.pump(0.3)
            on = bool(b.eval(f"!!document.querySelector('{LAYER} .aispark')"))
            self.assertEqual(on, row["ai"], f"{place}: the sparkle is shown exactly when the place is on")
            if not row["ai"]:
                b.key("/", ALT)                                                           # Alt+/ in an off place does nothing at all
                b.pump(0.3)
                self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aispark, {LAYER} .aibar, {LAYER} .aisug')"), place)
                self.assertFalse(b.eval("document.getElementById('snack').classList.contains('on')"), place)
                self.assertIsNone(b.eval("AIE.el.getAttribute('data-aibar')"))
            b.eval(CLEAN)

    def test_off_places_switch_on_without_rework_and_list_improve_only(self):
        """v2.2.0 is flipping the flag: with `ai` on, the email and plain places offer their Improve (and Tone) groups and Ask…, no Turn into."""
        b = self.b
        self.addCleanup(lambda: self.b and self.b.eval("for(const p of ['email','plain','line']) AI_PLACE_TABLE[p].ai=false; true"))
        want = {"email": [("improve", ["rewrite", "shorter", "longer"]), ("tone", ["formal", "warmer"])],
                "plain": [("improve", ["rewrite", "shorter", "executive"])], "line": [("improve", ["rewrite", "shorter", "executive"])]}
        for place, groups in want.items():
            b.eval(f"AI_PLACE_TABLE.{place}.ai=true")
            self.mount(place, "Some plain text\nOn two lines" if place != "line" else "A one line title")
            self.select_all()
            self.assertEqual(self.groups(), groups, place)
            self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aifmt, {LAYER} [data-ai=notes]')"), place)
            self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} [data-ai=custom]')"), place)
            b.eval(CLEAN)
            b.eval(f"AI_PLACE_TABLE.{place}.ai=false")

    # ---- option sets per place ---------------------------------------------------------------------------------------------
    def test_notes_offers_turn_into_apart_from_the_ai_zone_and_current_does_not(self):
        b = self.b
        self.mount("notes", NOTE)
        self.select_all()
        self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} .aibar .aifmt')"))
        self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aibar .aiai').contains(document.querySelector('{LAYER} .aifmt'))"))
        self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} .aibar .aiai .ailab')"))          # the tinted zone carries the sparkle label
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aibar .aifmt').getAttribute('aria-label')"), "Formatting")
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aibar .aiai').getAttribute('aria-label')"), "AI")
        self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} [data-ai=notes]')"))              # three paragraphs: Format notes leads
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aiai [data-ai]').dataset.ai"), "notes")
        self.assertEqual(self.groups(), [("improve", ["rewrite", "shorter", "longer", "executive"]),
                                         ("structure", ["format", "checklist", "summary"]), ("make into", ["fu-line"])])
        names = b.eval(f"[...document.querySelectorAll('{LAYER} .aiai button[aria-haspopup] ')].map(e=>e.textContent)")
        self.assertEqual(names, ["Improve", "Structure", "Make into"])
        b.eval(CLEAN)
        self.mount("current", CURRENT)
        self.select_all()
        self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aifmt')"))                      # Current state: no Turn into
        self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} [data-ai=notes]')"))              # but Format notes (3 blocks)
        self.assertEqual(self.groups(), [("improve", ["rewrite", "shorter", "longer", "executive"]), ("structure", ["format", "summary"])])
        self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} [data-ai=custom]')"))

    def test_make_into_keeps_the_single_find_updates_item(self):
        """The Product Manager has not answered about four separate items: one item, as it is today."""
        b = self.b
        self.mount("notes", NOTE)
        self.select_words("the uat dates is not confirmed")
        got = [g for g in self.groups() if g[0] == "make into"]
        self.assertEqual(got, [("make into", ["fu-line"])])
        self.assertFalse(b.eval("AI_ACTIONS.filter(a=>a.places&&a.places.includes('notes')).length>1"))

    def test_one_paragraph_selected_has_no_format_notes_and_a_whole_note_has(self):
        b = self.b
        self.mount("notes", NOTE)
        self.select_words("the uat dates is not confirmed")
        self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} [data-ai=notes]')"))
        b.key("Escape")
        b.eval(CLEAN)
        self.mount("notes", NOTE)
        self.select_all()
        self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} [data-ai=notes]')"))
        # a hand-made run on one paragraph is stopped on the page as well
        b.eval("""(()=>{ AIE.focus(); const d=AIE.editor.state.doc; AIE.editor.commands.setTextSelection({from:2,to:8}); })()""")
        b.eval("aiRun('notes','',{h:AIE,ai:{place:'notes'}})")
        self.assertIn("two or more paragraphs", b.eval("document.getElementById('snackT').textContent"))
        self.assertIsNone(b.eval("aiSug.value"))

    # ---- Turn into ---------------------------------------------------------------------------------------------------------
    def test_turn_into_each_block_kind_writes_the_markdown_and_undoes(self):
        b = self.b
        self.mount("notes", "Alpha line\n\nBeta line")
        names = []
        want = [("text", "Text", "Alpha line\n\nBeta line"), ("h1", "Heading 1", "# Alpha line\n\n# Beta line"),
                ("h2", "Heading 2", "## Alpha line\n\n## Beta line"), ("h3", "Heading 3", "### Alpha line\n\n### Beta line"),
                ("ul", "Bulleted list", "- Alpha line\n- Beta line"), ("ol", "Numbered list", "1. Alpha line\n2. Beta line"),
                ("task", "Checklist", "- [ ] Alpha line\n- [ ] Beta line"), ("quote", "Quote", "> Alpha line\n>\n> Beta line")]
        self.select_all()
        for kind, _name, md in want:
            self.turn_menu()
            if not names:
                names = b.eval(f"[...document.querySelectorAll('{LAYER} [role=menu] [data-turn]')].map(e=>e.textContent.trim())")
                self.assertEqual(names, [w[1] for w in want])                                   # Text, Heading 1-3, Bulleted, Numbered, Checklist, Quote
                self.assertEqual(b.eval(f"document.querySelector('{LAYER} [role=menu]').getAttribute('aria-label')"), "Turn into")
                self.assertEqual(b.eval(f"document.querySelector('{LAYER} [role=menu] [data-turn]').getAttribute('role')"), "menuitemradio")
            b.click(f"{LAYER} [role=menu] [data-turn={kind}]")
            b.wait(f"AIE.value()=={json.dumps(md)}", 5)
            self.assertEqual(b.eval("AIE.value()"), md, kind)
            self.assertIn("Turned into", b.eval("document.getElementById('snackT').textContent"))
            self.assertFalse(b.eval("!!window.aiSug.value"))                                     # no Claude run, no suggestion
            self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} .aibar')"))                # the bar stays open for the next turn
            self.turn_menu()
            self.assertEqual(b.eval(f"document.querySelector('{LAYER} [role=menu] [data-turn={kind}]').getAttribute('aria-checked')"), "true", kind)
            b.key("Escape")
            b.pump(0.6)                                                                          # the editor's history groups edits made within half a second
        # the toast's Undo and ⌘Z: both use the editor's own history
        b.click("#snack button, #snackU")
        b.wait("AIE.value()=='- [ ] Alpha line\\n- [ ] Beta line'")
        b.eval("AIE.focus(); true")
        b.key("z", META)
        b.wait("AIE.value()=='1. Alpha line\\n2. Beta line'")

    def test_turn_into_mixed_selection_and_a_single_line(self):
        b = self.b
        self.mount("notes", "# Title\n\n- one\n- two\n\n> quoted\n\nplain")
        self.select_all()
        self.turn_menu()
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} [role=menu] [aria-checked=true]')"), None)   # mixed: none ticked
        b.click(f"{LAYER} [role=menu] [data-turn=ul]")
        b.wait("AIE.value().startsWith('- Title')")
        self.assertEqual(b.eval("AIE.value()"), "- Title\n- one\n- two\n- quoted\n- plain")
        # a single line
        self.select_words("quoted")
        self.turn_menu()
        b.click(f"{LAYER} [role=menu] [data-turn=h2]")
        b.wait("/## quoted/.test(AIE.value())")
        self.assertEqual(b.eval("AIE.value()"), "- Title\n- one\n- two\n\n## quoted\n\n- plain")

    def test_turn_into_uses_the_editors_commands_so_current_states_heading_mapping_applies(self):
        """Turn into is OFF in Current state, but the commands are the editor's: a heading turned there is written `###`..`#####`."""
        b = self.b
        self.mount("current", "Plan\n\nBuild is late")
        b.eval("AIE.focus(); AIE.editor.commands.selectAll(); edTurnInto(AIE,'h2')")
        self.assertEqual(b.eval("AIE.value()"), "#### Plan\n\n#### Build is late")
        b.eval("edTurnInto(AIE,'h1')")
        self.assertEqual(b.eval("AIE.value()"), "### Plan\n\n### Build is late")
        self.assertFalse(b.eval("/^## /m.test(AIE.value())"))
        # and the page refuses it from the bar: the place table says no
        self.select_all()
        b.eval("aiTurn('h3')")
        self.assertEqual(b.eval("AIE.value()"), "### Plan\n\n### Build is late")

    # ---- Format notes, the suggestion card, the heading rule ----------------------------------------------------------------
    def test_format_notes_suggestion_card_accept_show_changes_and_command_z(self):
        b = self.b
        self.reply("## Purpose\n- Agree the approach with legal.\n\n## Open\n- The UAT dates are not confirmed.\n- Send the revised agreement by Friday.")
        self.mount("notes", NOTE)
        self.select_all()
        before = b.eval("AIE.value()")
        b.click(f"{LAYER} .aibar [data-ai=notes]")
        card = self.ready()
        self.assertIn("Format notes", card)
        self.assertIn("Spelling and grammar fixed too", card)                                   # the card says so
        self.assertIn("A suggestion: your text is unchanged until you accept it.", card)
        self.assertEqual(b.eval("AIE.value()"), before)                                          # nothing changed yet
        prompt = Path(str(self.fake) + ".prompt").read_text()
        self.assertIn("Keep every point", prompt)
        self.assertIn('"# ", "## " and "### "', prompt)
        self.assertIn("Also correct any spelling, grammar and punctuation, in British English", prompt)
        b.click(f"{LAYER} .aisug button[aria-pressed]")                                          # Show changes
        b.wait(f"document.querySelector('{LAYER} .aitext del, {LAYER} .aitext ins')")
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aisug button[aria-pressed]').getAttribute('aria-pressed')"), "true")
        b.click(f"{LAYER} .aisug button[aria-pressed]")
        b.click(f"{LAYER} .aisug [data-aifirst]")                                                # Accept
        b.wait("/## Purpose/.test(AIE.value())")
        self.assertTrue(b.eval("/^## Purpose/m.test(AIE.value())&&/^- Send the revised/m.test(AIE.value())"))
        self.assertIsNone(b.eval("aiSug.value"))
        b.eval("AIE.focus(); true")
        b.key("z", META)                                                                         # one ⌘Z undoes the whole suggestion
        b.wait("!/## Purpose/.test(AIE.value())")
        self.assertEqual(b.eval("AIE.value().replace(/\\s+$/,'')"), before.replace("\r", "").rstrip())
        args = json.loads(Path(str(self.fake) + ".argv.json").read_text())
        self.assertEqual(args[args.index("--tools") + 1], "")                                    # still the tool-less run

    def test_format_notes_in_current_state_never_writes_a_heading_that_cuts_its_section(self):
        b = self.b
        self.reply("# Where we are\n\n## Build\n- Two weeks behind: data access is late.\n\n## UAT\n- Preparation has started.\n\n#### Deep one")
        self.mount("current", CURRENT)
        self.select_all()
        b.click(f"{LAYER} .aibar [data-ai=notes]")
        self.ready()
        shown = b.eval(f"document.querySelector('{LAYER} .aitext').textContent")
        self.assertFalse(re.search(r"^(#|##) ", shown, re.M), shown)                             # the card already shows the stored levels
        prompt = Path(str(self.fake) + ".prompt").read_text()
        self.assertIn('"### ", "#### " and "##### "', prompt)
        self.assertIn("### Where we are", prompt)                                                # the AI saw the stored levels
        b.click(f"{LAYER} .aisug [data-aifirst]")
        b.wait("/Two weeks behind/.test(AIE.value())&&/UAT/.test(AIE.value())")
        got = b.eval("AIE.value()")
        self.assertFalse(re.search(r"^(#|##) ", got, re.M), got)
        self.assertIn("### Where we are", got)
        self.assertIn("#### Build", got)
        self.assertIn("#### UAT", got)
        self.assertIn("#### Deep one", got)

    def test_the_page_guard_alone_relevels_a_stray_heading_for_current_and_leaves_notes(self):
        """Whatever the card holds (the page also checks, so a reply that skipped edit_ai.py still can't cut the section)."""
        b = self.b
        self.mount("current", "Line one\n\nLine two")
        self.select_all(bar=False)
        b.eval("""(()=>{ aiSug.value={h:AIE, ai:{place:'current'}, range:edSelection(AIE), option:'notes', instruction:'', label:'Format notes',
          status:'ready', text:'## Stray\\n- a\\n\\n# Top'}; return true; })()""")
        b.wait(f"document.querySelector('{LAYER} .aisug')")
        b.click(f"{LAYER} .aisug [data-aifirst]")
        b.wait("/Stray/.test(AIE.value())")
        self.assertEqual(b.eval("AIE.value()"), "#### Stray\n\n- a\n\n### Top")
        self.assertEqual(b.eval("headsSafe('# a\\n## b\\n### c\\n```\\n## d\\n```', 2)"), "### a\n#### b\n### c\n```\n## d\n```")
        self.assertEqual(b.eval("headsSafe('## b', 0)"), "## b")
        b.eval(CLEAN)
        self.mount("notes", "Line one\n\nLine two")
        self.select_all(bar=False)
        b.eval("""(()=>{ aiSug.value={h:AIE, ai:{place:'notes'}, range:edSelection(AIE), option:'notes', instruction:'', label:'Format notes',
          status:'ready', text:'## Stray\\n- a'}; return true; })()""")
        b.wait(f"document.querySelector('{LAYER} .aisug')")
        b.click(f"{LAYER} .aisug [data-aifirst]")
        b.wait("/Stray/.test(AIE.value())")
        self.assertEqual(b.eval("AIE.value()"), "## Stray\n\n- a")

    def test_a_confidential_reshape_still_asks_and_ask_has_no_spelling_note(self):
        b = self.b
        self.mount("notes", NOTE)
        self.select_words("Agree the approach with legal.")
        b.click(f"{LAYER} .aibar [data-ai=custom]")
        b.wait("document.activeElement&&document.activeElement.matches('#aiLayer .aiask input')")
        b.type("Make it louder")
        b.key("Enter")
        card = self.ready()
        self.assertNotIn("Spelling and grammar fixed too", card)                                  # Ask… does only what was asked

    # ---- placement ---------------------------------------------------------------------------------------------------------
    def rects(self):
        return self.b.eval("""(()=>{ const r=e=>{ if(!e) return null; const x=e.getBoundingClientRect(); return {l:x.left,t:x.top,r:x.right,b:x.bottom,w:x.width,h:x.height}; };
          const v=AIE.editor.view, s=AIE.editor.state.selection, a=v.coordsAtPos(s.from), z=v.coordsAtPos(s.to);
          return { spark:r(document.querySelector('#aiLayer .aispark')), bar:r(document.querySelector('#aiLayer .aibar')),
            ed:r(AIE.el), selTop:a.top, selBottom:z.bottom, selLeft:Math.min(a.left,z.left), side:(document.querySelector('#aiLayer .aibar')||{dataset:{}}).dataset.side,
            vw:document.documentElement.clientWidth, vh:innerHeight }; })()""")

    def check_placement(self, width):
        b = self.b
        b.resize(width, 900)
        b.pump(0.3)
        self.mount("notes", NOTE, top=120, left=140 if width > 1000 else 60)
        self.select_all()
        r = self.rects()
        self.assertEqual(r["side"], "below")
        self.assertGreaterEqual(r["bar"]["t"], r["selBottom"], "the bar sits under the selection")
        self.assertLess(r["bar"]["t"] - r["selBottom"], 24)                                       # and near it
        self.assertLessEqual(abs(r["bar"]["l"] - r["selLeft"]), 2)                                # at its left edge
        self.assertGreaterEqual(r["bar"]["l"], 0)
        self.assertLessEqual(r["bar"]["r"], r["vw"])
        self.assertLess(r["spark"]["r"], r["ed"]["l"] + 1, "the sparkle is in the margin, left of the text")
        self.assertGreaterEqual(r["spark"]["l"], 4)
        self.assertLessEqual(abs(r["spark"]["t"] - r["selTop"]), 14, "level with the selection's first line")
        # near the bottom of the window the bar flips above the selection
        b.eval(CLEAN)
        self.mount("notes", NOTE, top=700, left=140 if width > 1000 else 60)
        self.select_all()
        r = self.rects()
        self.assertEqual(r["side"], "above")
        self.assertLessEqual(r["bar"]["b"], r["selTop"] + 1, "above the selection, never over it")
        self.assertGreaterEqual(r["bar"]["t"], 0)

    def test_the_bar_sits_by_the_selection_at_1400(self):
        self.check_placement(1400)

    def test_the_bar_sits_by_the_selection_at_900(self):
        self.check_placement(900)

    def test_the_suggestion_card_sits_by_the_selection_and_follows_the_same_placement(self):
        b = self.b
        self.mount("notes", NOTE, top=120)
        self.select_all()
        b.click(f"{LAYER} .aibar [data-ai=notes]")
        self.ready()
        r = b.eval("""(()=>{ const c=document.querySelector('#aiLayer .aisug').getBoundingClientRect(), s=AIE.editor.view.coordsAtPos(AIE.editor.state.selection.to);
          return {t:c.top,b:c.bottom,l:c.left,r:c.right,selBottom:s.bottom,vw:innerWidth,vh:innerHeight}; })()""")
        self.assertGreaterEqual(r["t"], r["selBottom"])
        self.assertLessEqual(r["r"], r["vw"])
        self.assertLessEqual(r["b"], r["vh"])

    def test_a_hover_menu_near_the_foot_of_the_window_opens_upward(self):
        b = self.b
        self.mount("notes", NOTE, top=640)
        self.select_all()
        b.click(f'{LAYER} .aibar .aifmt button[aria-haspopup]')
        b.wait(f"document.querySelector('{LAYER} [role=menu]')")
        r = b.eval(f"(()=>{{ const m=document.querySelector('{LAYER} [role=menu]').getBoundingClientRect(); return {{t:m.top,b:m.bottom,vh:innerHeight}}; }})()")
        self.assertGreaterEqual(r["t"], 0)
        self.assertLessEqual(r["b"], r["vh"])
        b.key("Escape")

    def test_pointing_at_a_group_opens_it_and_leaving_folds_it(self):
        b = self.b
        self.mount("notes", NOTE)
        self.select_all()
        box = b.box(f'{LAYER} .aibar button[data-tip="AI: improve"]')
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=box["x"], y=box["y"], button="none")
        b.wait(f"document.querySelector('{LAYER} [role=menu]')")
        self.assertFalse(b.eval("document.activeElement.closest('[role=menu]')!==null"))           # hover leaves the focus where it was
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=700, y=800, button="none")
        b.wait(f"!document.querySelector('{LAYER} [role=menu]')", 3)

    # ---- coexistence and the keyboard --------------------------------------------------------------------------------------
    def test_the_bar_uses_its_own_attribute_names_not_the_slash_menus(self):
        b = self.b
        self.mount("notes", NOTE)
        self.select_all(bar=False)
        for a in ("aria-expanded", "aria-haspopup", "aria-controls", "aria-activedescendant"):
            self.assertIsNone(b.eval(f"AIE.editor.view.dom.getAttribute('{a}')"), a)           # none of the `/` menu's, with the sparkle up
        b.click(f"{LAYER} .aispark")
        b.wait(f"document.querySelector('{LAYER} .aibar')")
        for a in ("aria-expanded", "aria-haspopup", "aria-controls", "aria-activedescendant"):
            self.assertIsNone(b.eval(f"AIE.editor.view.dom.getAttribute('{a}')"), a)
        self.assertEqual(b.eval("AIE.editor.view.dom.getAttribute('data-aibar')"), "open")
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aispark').getAttribute('aria-expanded')"), "true")
        self.assertEqual(b.eval(f"document.querySelector('{LAYER} .aispark').getAttribute('aria-controls')"), "aiBarBox")
        b.key("Escape")                                                                           # Esc folds the bar (the sparkle stays on a selection)
        b.wait(f"!document.querySelector('{LAYER} .aibar')")
        self.assertEqual(b.eval("AIE.editor.view.dom.getAttribute('data-aibar')"), "spark")
        self.assertTrue(b.eval("document.activeElement===AIE.editor.view.dom||AIE.el.contains(document.activeElement)"))

    def test_the_slash_menu_and_the_bar_never_show_together(self):
        b = self.b
        self.mount("notes", "Some words here\n\n")
        self.select_words("Some words", bar=False)
        self.assertEqual(b.eval("AIE.editor.view.dom.getAttribute('data-aibar')"), "spark")
        b.eval("""(()=>{ const e=AIE.editor; e.commands.focus('end'); })()""")
        b.wait(f"!document.querySelector('{LAYER} .aispark')")                                    # a caret, no selection: no sparkle
        b.type("/")
        b.pump(0.3)
        self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aispark, {LAYER} .aibar')"))
        self.assertIsNone(b.eval("AIE.editor.view.dom.getAttribute('data-aibar')"))
        b.key("Escape")                                                                           # Esc is the `/` menu's here, not the bar's

    def test_alt_slash_opens_the_bar_with_the_first_ai_menu_open_and_arrows_and_esc_work(self):
        b = self.b
        self.mount("notes", NOTE)
        self.select_all(bar=False)
        b.key("/", ALT)
        b.wait(f"document.querySelector('{LAYER} [role=menu]')&&document.activeElement.closest('[role=menu]')")
        self.assertEqual(b.eval("document.activeElement.closest('[role=menu]').getAttribute('aria-label')"), "Improve")   # an AI menu, not Turn into
        b.key("ArrowDown")
        self.assertEqual(b.eval("document.activeElement.dataset.ai"), "shorter")
        b.key("Escape")                                                                           # folds the menu, focus back on its button
        b.wait(f"!document.querySelector('{LAYER} [role=menu]')")
        self.assertTrue(b.eval(f"document.activeElement===document.querySelector('{LAYER} .aibar button[data-tip=\"AI: improve\"]')"))
        b.key("ArrowRight")
        self.assertEqual(b.eval("document.activeElement.dataset.tip"), "AI: structure")
        b.key("ArrowLeft")
        b.key("ArrowLeft")                                                                        # past Improve: the Format notes button
        self.assertEqual(b.eval("document.activeElement.dataset.ai"), "notes")
        b.key("Home")
        self.assertEqual(b.eval("document.activeElement.closest('.aifmt')!==null"), True)         # first on the bar: Turn into
        b.key("ArrowDown")                                                                        # ↓ opens it, focus in
        b.wait(f"document.querySelector('{LAYER} [role=menu]')&&document.activeElement.closest('[role=menu]')")
        b.key("Escape")
        b.key("Escape")                                                                           # closes the bar; focus back in the text
        b.wait(f"!document.querySelector('{LAYER} .aibar')")
        self.assertTrue(b.eval("AIE.el.contains(document.activeElement)"))
        self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} .aispark')"))

    def test_alt_slash_with_a_composition_is_ignored_and_without_a_selection_says_so(self):
        b = self.b
        self.mount("notes", NOTE)
        self.select_all(bar=False)
        b.eval("""AIE.el.dispatchEvent(new KeyboardEvent('keydown',{key:'/',code:'Slash',altKey:true,isComposing:true,bubbles:true,cancelable:true}))""")
        b.pump(0.2)
        self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aibar')"))                   # an input method is composing: not ours
        b.eval("AIE.editor.commands.setTextSelection(3)")
        b.wait(f"!document.querySelector('{LAYER} .aispark')")
        b.key("/", ALT)
        self.assertIn("Select some text first", b.eval("document.getElementById('snackT').textContent"))

    def test_ask_box_enter_and_esc_with_a_composition_and_command_enter(self):
        b = self.b
        self.mount("notes", NOTE)
        self.select_all()
        b.click(f"{LAYER} .aibar [data-ai=custom]")
        b.wait("document.activeElement&&document.activeElement.matches('#aiLayer .aiask input')")
        b.type("Make it louder")
        b.eval("""document.activeElement.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',isComposing:true,bubbles:true,cancelable:true}))""")
        b.pump(0.2)
        self.assertTrue(b.eval("document.activeElement.matches('#aiLayer .aiask input')"))        # a composition's Esc is the input method's
        b.key("Enter", META)                                                                      # ⌘↵ asks, and goes no further (the host's save waits)
        card = self.ready()
        self.assertIn("Make it louder", card)
        self.assertTrue(b.eval("!!aiSug.value"))

    def test_command_enter_in_the_card_accepts_and_the_hosts_save_waits(self):
        b = self.b
        self.mount("notes", "Alpha line\n\nBeta line")
        b.eval("window.HOSTSAVE=0; AIE.el.addEventListener('keydown',e=>{ if(e.key==='Enter'&&(e.metaKey||e.ctrlKey)) HOSTSAVE++; })")
        self.select_all()
        b.click(f"{LAYER} .aibar [data-ai=notes]")
        self.ready()
        self.assertTrue(b.eval("document.activeElement.matches('#aiLayer .aisug [data-aifirst]')"))
        b.key("Enter", META)
        b.wait("/Clearly/.test(AIE.value())")
        self.assertEqual(b.eval("HOSTSAVE"), 0)

    # ---- looks -------------------------------------------------------------------------------------------------------------
    def test_targets_are_24px_and_the_bar_reads_in_dark_and_forced_colours(self):
        b = self.b
        self.mount("notes", NOTE)
        self.select_all()
        small = b.eval(f"""[...document.querySelectorAll('{LAYER} .aispark, {LAYER} .aibar button')].filter(e=>{{ const r=e.getBoundingClientRect(); return r.height<24||r.width<24; }}).map(e=>e.className+':'+e.textContent)""")
        self.assertEqual(small, [])
        self.turn_menu()
        small = b.eval(f"""[...document.querySelectorAll('{LAYER} [role=menu] button')].filter(e=>e.getBoundingClientRect().height<24).map(e=>e.textContent)""")
        self.assertEqual(small, [])
        b.key("Escape")
        light = b.eval(f"getComputedStyle(document.querySelector('{LAYER} .aiai')).backgroundColor")
        b.eval("document.documentElement.dataset.theme='dark'")
        b.pump(0.2)
        dark = b.eval(f"getComputedStyle(document.querySelector('{LAYER} .aiai')).backgroundColor")
        bar = b.eval(f"getComputedStyle(document.querySelector('{LAYER} .aibar')).backgroundColor")
        self.assertNotEqual(light, dark)                                                            # the tint follows the theme
        self.assertNotEqual(dark, bar)                                                              # and the AI zone is still apart from the bar
        sp = b.eval(f"getComputedStyle(document.querySelector('{LAYER} .aispark')).color")
        self.assertNotEqual(sp, bar)
        b.eval("delete document.documentElement.dataset.theme")
        b.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "active"}])
        b.pump(0.3)
        for sel in (".aispark", ".aibar", ".aibar .aiai"):
            self.assertNotEqual(b.eval(f"getComputedStyle(document.querySelector('{LAYER} {sel}')).borderTopStyle"), "none", sel)
        b.call("Emulation.setEmulatedMedia", features=[{"name": "forced-colors", "value": "none"}])


@unittest.skipUnless(os.environ.get("CREAITE_SHOTS_117"), "set CREAITE_SHOTS_117 to a folder to take the screenshots")
class Shots117(LiveBrowserCase):
    """Screenshots of the sparkle, the bar and the suggestion in Notes and Current state (not a test: it makes the pictures)."""

    shared_server = True
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        from test_dashboard import populate
        populate(v)
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(FAKE)
        cls.fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake)}

    def snap(self, name):
        out = Path(os.environ["CREAITE_SHOTS_117"])
        out.mkdir(parents=True, exist_ok=True)
        self.b.pump(0.4)
        self.b.screenshot(str(out / f"{name}.png"))

    def test_shots(self):
        b = self.b
        notes_md = NOTE
        for width in (1400, 900):
            b.resize(width, 900)
            for theme in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.theme={json.dumps(theme)}")
                for place, md in (("notes", notes_md), ("current", CURRENT)):
                    b.eval(f"{MOUNT}({json.dumps(place)},{json.dumps(md)},150,{140 if width > 1000 else 70})")
                    b.wait("!!document.querySelector('#aiEd.ProseMirror')")
                    b.click("#aiEd")
                    b.key("a", META)
                    b.wait(f"document.querySelector('{LAYER} .aispark')")
                    self.snap(f"{place}-{theme}-{width}-1-sparkle")
                    b.click(f"{LAYER} .aispark")
                    b.wait(f"document.querySelector('{LAYER} .aibar')")
                    self.snap(f"{place}-{theme}-{width}-2-bar")
                    b.click(f"{LAYER} .aibar button[data-tip=\"AI: improve\"]")
                    b.wait(f"document.querySelector('{LAYER} [role=menu]')")
                    self.snap(f"{place}-{theme}-{width}-3-menu")
                    b.key("Escape")
                    if place == "notes":
                        b.click(f"{LAYER} .aibar .aifmt button[aria-haspopup]")
                        b.wait(f"document.querySelector('{LAYER} [role=menu]')")
                        self.snap(f"{place}-{theme}-{width}-4-turninto")
                        b.key("Escape")
                    b.click(f"{LAYER} .aibar [data-ai=notes]")
                    b.wait(f"document.querySelector('{LAYER} .aisug .aitext')", 20)
                    self.snap(f"{place}-{theme}-{width}-5-suggestion")
                    b.eval(CLEAN)

    def test_current_state_page(self):
        """The real Current state editor on the project page: the sparkle, the bar and the card, in place."""
        b = self.b
        for width in (1400, 900):
            b.resize(width, 900)
            for theme in ("light", "dark"):
                b.eval(f"document.documentElement.dataset.theme={json.dumps(theme)}")
                b.eval("go('cockpit','ABC')")
                b.wait("document.querySelector('#v-cockpit .curcard [data-edcur]')")
                b.click("#v-cockpit .curcard [data-edcur]")
                b.wait("!!(document.getElementById('curEd')&&document.getElementById('curEd').cxed)")
                b.click("#curEd")
                b.key("a", META)
                b.wait(f"document.querySelector('{LAYER} .aispark')")
                self.snap(f"page-current-{theme}-{width}-1-sparkle")
                b.click(f"{LAYER} .aispark")
                b.wait(f"document.querySelector('{LAYER} .aibar')")
                self.snap(f"page-current-{theme}-{width}-2-bar")
                b.click(f"{LAYER} .aibar button[data-tip=\"AI: improve\"]")
                b.wait(f"document.querySelector('{LAYER} [role=menu]')")
                self.snap(f"page-current-{theme}-{width}-3-menu")
                b.key("Escape")
                b.click(f"{LAYER} .aibar [data-ai=custom]") if not b.eval(f"!!document.querySelector('{LAYER} .aibar [data-ai=notes]')") else b.click(f"{LAYER} .aibar [data-ai=notes]")
                b.wait(f"document.querySelector('{LAYER} .aisug')", 20)
                b.pump(1.0)
                self.snap(f"page-current-{theme}-{width}-5-suggestion")
                b.eval("aiSug.value=null; shared.CURED&&curDrop(); true")


if __name__ == "__main__":
    unittest.main()

"""#133 (v2.2.0): the plain profile and Draft email on the shared editor.

Run: python3 dev/tests/test_editor_plain.py   (the browser tests need Google Chrome; skipped otherwise)

Done when (#133):
- the plain-profile selection bar (#117's margin sparkle, hover groups, Ask…) with Improve and Ask only in the item panel's longer fields
  (and its one-line title), Prep notes and the Prep popup's draft boxes, and Find updates' title, decision and memory-line boxes; each
  place's option set is tested; no Turn into, no Format notes, no formatting bar, no `/` menu;
- the excluded fields (keys and short labels: the item panel's Revisit and Source, Find updates' person name, role and organisation)
  have no bar at all;
- Draft email's preview is a host of the shared editor with the Email place (Improve: Rewrite, Shorter, Longer; Tone: More formal,
  Warmer), and its Copy output, HTML and text, is identical to the old preview's for an unedited draft;
- an edited email keeps its table and its colours, a suggestion never crosses a cell, and typing `# ` or `- ` starts nothing;
- desktop and 900px.
Claude is a stand-in (never a real model call).
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
import notes_find_fixture as fx  # noqa: E402
import test_ai_117 as t117  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "system/templates/dashboard/src"
META = 4
LAYER = "#aiLayer"
CLEAN = t117.CLEAN + ";document.getElementById('plFix')?.remove(); true"

# Draft email's data, as the existing popup tests set it (fictional people, items and dates).
PREP = r"""
  S.ownDomains=["brightwater.example"]; S.me="Alan Carter";
  const mkA=(id,t,due,client,extra)=>({id,p:"ABC",t,ws:"",o:"Sara Example",pr:"Medium",due,st:"Open",raised:"2026-09-01",closed:null,upd:"",client:!!client,cm:"",src:"ABC Example Programme/minutes/2026-10-01 Steering.docx",...extra});
  A.length=0; R.length=0;
  A.push(mkA("ABC-A-101","Send the revised SOW","2026-10-02",true,{pr:"Urgent",upd:"Waiting on legal"}), mkA("ABC-A-102","Internal budget note",TODAY,false), mkA("ABC-A-103","Client workshop booked","2099-01-01",true));
  R.push({id:"ABC-001",p:"ABC",type:"Issue",t:"Test licences not ordered",ws:"",o:"Sara Example",resp:"Order raised with procurement",due:null,imp:"Medium",lik:"High",pr:"High",st:"Open",raised:"2026-09-01",client:false,cm:"",src:"x",upd:""});
  REG.length=0; REG.push({name:"Sara Example",email:"sara@brightwater.example",aliases:[],org:"",role:"",extra:{}});
  window.CLIP=[];
  Object.defineProperty(navigator,"clipboard",{configurable:true,value:{ write:async items=>{ const it=items[0]; CLIP.push([await it.__t["text/html"].text(),await it.__t["text/plain"].text()]); }, writeText:async t=>CLIP.push(["",t]) }});
  window.ClipboardItem=function(map){ this.__t=map; this.types=Object.keys(map); };
  true"""


class _Base(LiveBrowserCase):
    shared_server = True        # nothing it does is written
    width, height = 1400, 900

    @classmethod
    def load(cls, v):
        populate(v)
        cls.fake = v.root / "fake_claude.py"
        cls.fake.write_text(t117.FAKE)
        cls.fake.chmod(0o755)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake)}

    def setUp(self):
        super().setUp()
        Path(str(self.fake) + ".reply").unlink(missing_ok=True)
        self.addCleanup(lambda: Path(str(self.fake) + ".reply").unlink(missing_ok=True))
        self.addCleanup(lambda: self.b and self.b.eval(CLEAN))

    def reply(self, text):
        Path(str(self.fake) + ".reply").write_text(text, encoding="utf-8")

    def sparked(self):
        return bool(self.b.eval(f"!!document.querySelector('{LAYER} .aispark')"))

    def select_in(self, sel, words=None):
        """Select `words` (or everything) in the editor on `sel`, by the editor's own selection after a real click into it."""
        b = self.b
        b.click(sel)
        if words is None:
            b.key("a", META)
        else:
            b.eval("""((s,w)=>{ const h=edOf(document.querySelector(s)); let at=-1; h.editor.state.doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf(w); if(i>=0) at=pos+i; } });
              h.focus(); h.editor.commands.setTextSelection({from:at,to:at+w.length}); })(%s,%s)""" % (json.dumps(sel), json.dumps(words)))
        b.pump(0.35)

    def open_bar(self):
        b = self.b
        b.wait(f"document.querySelector('{LAYER} .aispark')")
        b.click(f"{LAYER} .aispark")
        b.wait(f"document.querySelector('{LAYER} .aibar')")

    def groups(self):
        return t117.Bar117.groups(self)

    def ready(self):
        self.b.wait(f"document.querySelector('{LAYER} .aisug .aitext')||document.querySelector('{LAYER} .aisug [role=alert]')", 20)
        return self.b.eval(f"document.querySelector('{LAYER} .aisug').textContent")

    def pick(self, group, option):
        b = self.b
        b.click(f'{LAYER} .aibar button[data-tip="AI: {group}"]')
        b.wait(f"document.querySelector('{LAYER} [role=menu]')")
        b.click(f"{LAYER} [role=menu] [data-ai={option}]")


class ThePlainProfile(_Base):
    """The place table, and each plain place's option set."""

    def test_every_place_is_on_and_the_plain_ones_offer_improve_and_ask_only(self):
        b = self.b
        want = {"notes": dict(ai=True, turnInto=True, formatNotes=True, improveOnly=False),
                "current": dict(ai=True, turnInto=False, formatNotes=True, improveOnly=False),
                "email": dict(ai=True, turnInto=False, formatNotes=False, improveOnly=True),
                "plain": dict(ai=True, turnInto=False, formatNotes=False, improveOnly=True),
                "line": dict(ai=True, turnInto=False, formatNotes=False, improveOnly=True)}
        sheet = {"report", "minutes", "client", "readonly"}      # the A4 sheets stay on as the gate has them
        self.assertEqual({k: v for k, v in b.eval("AI_PLACE_TABLE").items() if k not in sheet}, want)
        groups = {"plain": [("improve", ["rewrite", "shorter", "executive"])], "line": [("improve", ["rewrite", "shorter", "executive"])]}
        for place, g in groups.items():
            self.mount_plain(place, "Some plain text\nOn two lines" if place == "plain" else "A one line title")
            self.select_in("#plEd")
            self.open_bar()
            self.assertEqual(self.groups(), g, place)
            self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aifmt, {LAYER} [data-ai=notes]')"), place)    # no Turn into, no Format notes
            self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} [data-ai=custom]')"), place)                      # Ask… is there
            self.assertFalse(b.eval("!!document.querySelector('.edbar, .edslash, [data-edbar]')"), place)                 # no formatting bar, no / menu
            b.eval(CLEAN)

    def mount_plain(self, place, text):
        b = self.b
        b.eval(CLEAN)
        b.eval("""((place,text)=>{ const box=document.createElement('div'); box.id='plFix';
          box.style.cssText='position:fixed;top:80px;left:140px;width:520px;z-index:100;background:var(--surface);padding:8px;color:var(--ink)';
          document.body.appendChild(box); const el=document.createElement('div'); el.id='plEd'; box.appendChild(el);
          window.AIE=creaiteEditor(el,{features:'plain',text,multiline:place!=='line',ai:{place,project:()=>'ABC'}}); return true; })(%s,%s)"""
               % (json.dumps(place), json.dumps(text)))
        b.wait("!!document.querySelector('#plEd.ProseMirror')")

    def test_a_suggestion_is_one_line_in_a_one_line_field_and_text_in_a_longer_one(self):
        b = self.b
        self.mount_plain("line", "A one line title")
        self.reply("Line one\nLine two")
        self.select_in("#plEd")
        self.open_bar()
        self.pick("improve", "rewrite")
        self.assertIn("Line one", self.ready())
        b.click(f"{LAYER} .aisug button[data-aifirst]")
        b.wait("AIE.value()==='Line one Line two'")
        self.assertEqual(b.eval("AIE.editor.state.doc.childCount"), 1)
        self.mount_plain("plain", "teh first\nsecond")
        self.reply("The first\nSecond")
        self.select_in("#plEd")
        self.open_bar()
        self.pick("improve", "shorter")
        self.ready()
        b.click(f"{LAYER} .aisug button[data-aifirst]")
        b.wait("AIE.value()==='The first\\nSecond'")

    def test_at_900px_the_bar_fits_and_nothing_scrolls_sideways(self):
        b = self.b
        b.resize(900, 900)
        self.addCleanup(lambda: self.b and self.b.resize(1400, 900))
        self.mount_plain("plain", "Some plain text\nOn two lines")
        self.select_in("#plEd")
        self.open_bar()
        r = b.eval(f"(()=>{{ const r=document.querySelector('{LAYER} .aibar').getBoundingClientRect(); return [r.left>=0, r.right<=innerWidth, document.documentElement.scrollWidth<=innerWidth]; }})()")
        self.assertEqual(r, [True, True, True])


class TheItemPanel(_Base):
    """pkEdMount (panel.js): the item panel's fields. The longer ones and the title get the bar; keys and short labels get none."""

    FIELDS = """(()=>{ document.getElementById('plFix')?.remove(); const box=document.createElement('div'); box.id='plFix';
      box.style.cssText='position:fixed;top:60px;left:140px;width:560px;z-index:100;background:var(--surface);padding:8px;color:var(--ink)';
      box.innerHTML=`<h2 class="pk-title pked" id="pkTitle" data-pkf="t" contenteditable="plaintext-only" style="display:block;min-height:24px">Send the revised SOW</h2>
        <div class="pk-desc pked" id="pkDesc" data-pkml="1" contenteditable="plaintext-only" style="display:block;min-height:24px">The statement of work needs legal sign-off first.</div>
        <div class="pk-vtext pked" id="pkRev" data-pkf="revisit" contenteditable="plaintext-only" style="display:block;min-height:24px">After the audit</div>
        <div class="pk-vtext pked" id="pkOpts" data-pkf="opts" data-pkml="1" contenteditable="plaintext-only" style="display:block;min-height:24px">Three options were considered here.</div>
        <div class="pk-desc pked pk-srcin" id="pkSrcIn" data-pkf="srcIn" contenteditable="plaintext-only" style="display:block;min-height:24px">ABC Example Programme/minutes/2026-10-01 Steering.docx</div>`;
      document.body.appendChild(box); pkEdMount(box); return true; })()"""

    def test_the_longer_fields_and_the_title_have_the_bar_and_the_keys_have_none(self):
        b = self.b
        b.eval(self.FIELDS)
        b.wait("!!document.querySelector('#plFix #pkSrcIn.ProseMirror')")
        got = {}
        for fid in ("pkTitle", "pkDesc", "pkOpts", "pkRev", "pkSrcIn"):
            b.eval("aiBar.value=null; true")
            self.select_in(f"#plFix #{fid}")
            got[fid] = self.sparked()
            if got[fid]:
                self.open_bar()
                self.assertEqual(self.groups(), [("improve", ["rewrite", "shorter", "executive"])], fid)
                b.key("Escape")
            b.key("Escape")
        self.assertEqual(got, {"pkTitle": True, "pkDesc": True, "pkOpts": True, "pkRev": False, "pkSrcIn": False})
        for fid in ("pkRev", "pkSrcIn"):                                       # and Alt+/ does nothing in them
            self.select_in(f"#plFix #{fid}")
            b.key("/", 1)
            b.pump(0.3)
            self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aispark, {LAYER} .aibar, {LAYER} .aisug')"), fid)

    def test_the_prep_boxes_are_mounted_in_the_plain_place(self):
        """Prep's notes and questions, and the Prep popup's shaped notes: the host passes place "plain" (read from the source)."""
        for name in ("components/prep/PrepPage.jsx", "components/prep/PrepShape.jsx"):
            src = (SRC / name).read_text(encoding="utf-8")
            self.assertRegex(src, r'place: "plain"', name)
            self.assertIn("ai={", src, name)
        # the item panel's mount, the same way: only the longer fields and the title carry `ai`
        pan = (SRC / "panel.js").read_text(encoding="utf-8")
        self.assertRegex(pan, r'el\.dataset\.pkml\|\|el\.id==="pkTitle"\?\{ai:')


class FindUpdatesFields(_Base):
    """Find updates' boxes: a title, a decision or a memory line is a sentence (the line place); a person's fields are keys."""

    @classmethod
    def load(cls, v):
        fx.load(v)
        cls.fake = fx.install(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake), "CREAITE_NOW": fx.NOW}

    def test_titles_and_memory_lines_have_the_bar_and_a_persons_fields_have_none(self):
        import test_find_updates_panel as tf
        b = self.b
        b.eval(tf.MOUNT % (json.dumps(fx.NOTE), json.dumps(tf.LINES)))
        b.wait("['ready','none','error','ask'].includes(fuState.value)", 40)
        self.assertEqual(b.eval("fuState.value"), "ready")

        def open_row(text):
            b.eval("aiBar.value=null; true")
            row = f"[...document.querySelectorAll('#fuCol .fu-r')].find(r=>r.textContent.includes({json.dumps(text)}))"
            b.eval(f"{row}.querySelector('.fu-open').click()")
            b.wait(f"{row}.querySelector('.fu-peek')")
            return row

        def first_box(row):
            b.wait(f"{row}.querySelector('.fu-fields .ProseMirror')")
            return b.eval(f"{row}.querySelector('.fu-fields .ProseMirror').id")

        title = first_box(open_row("Book a 30-minute"))
        self.select_in("#" + title)
        self.assertTrue(self.sparked(), "an item's title")
        self.open_bar()
        self.assertEqual(self.groups(), [("improve", ["rewrite", "shorter", "executive"])])
        b.key("Escape")
        b.key("Escape")
        name = first_box(open_row("Rania Haddad"))
        self.select_in("#" + name)
        self.assertFalse(self.sparked(), "a person's name is a key")
        b.eval("aiBar.value=null; true")
        for sel in b.eval("[...document.querySelectorAll('#fuCol .fu-peek .fu-fields .ProseMirror')].map(e=>'#'+e.id)"):
            self.select_in(sel)
            self.assertFalse(self.sparked(), sel)                               # name, role and organisation: none has the bar
        mem = first_box(open_row("Omar Ali reports"))
        self.select_in("#" + mem)
        self.assertTrue(self.sparked(), "a memory line")


class DraftEmail(_Base):
    """Draft email's preview on the shared editor."""

    def open_email(self):
        b = self.b
        b.eval(PREP)
        b.eval('openDraftEmail("Sara Example"); true')
        b.wait("!!document.querySelector('#dePrev.ProseMirror')")

    def copy(self, rich=True):
        b = self.b
        b.eval("CLIP.length=0; true")
        b.click("#deCopyHtml" if rich else "#deCopyText")
        b.wait("CLIP.length>0")
        return b.eval("CLIP[0]")

    def test_the_preview_is_a_shared_editor_host_and_an_unedited_copy_is_byte_for_byte_todays(self):
        b = self.b
        self.open_email()
        self.assertEqual(b.eval("(()=>{ const e=document.getElementById('dePrev'); return [e.isContentEditable, e.getAttribute('role'), edOf(e).features]; })()"),
                         [True, "textbox", "email"])
        html, text = self.copy(True)
        # today's copy: the builder's HTML set into a plain contenteditable and read back as innerHTML
        old = b.eval("""(()=>{ const d=document.createElement('div'); d.contentEditable='true'; const em=deBuild(); putHtml(d, em.html); return [d.innerHTML, em.text]; })()""")
        self.assertEqual(html, old[0])
        self.assertEqual(text, old[1])
        self.assertIn("<table", html)
        self.assertNotIn("ProseMirror", html)
        plain = self.copy(False)
        self.assertEqual(plain[1], old[1])
        self.assertFalse(b.eval("DE.edited"))

    def test_the_email_place_offers_improve_tone_and_ask_inside_one_paragraph_only(self):
        b = self.b
        self.open_email()
        self.select_in("#dePrev", "I hope you're well")
        self.assertTrue(self.sparked())
        self.open_bar()
        self.assertEqual(self.groups(), [("improve", ["rewrite", "shorter", "longer"]), ("tone", ["formal", "warmer"])])
        self.assertFalse(b.eval(f"!!document.querySelector('{LAYER} .aifmt, {LAYER} [data-ai=notes]')"))
        self.assertTrue(b.eval(f"!!document.querySelector('{LAYER} [data-ai=custom]')"))
        b.key("Escape")
        b.key("Escape")
        b.eval("aiBar.value=null; true")
        self.select_in("#dePrev")                                              # everything: the table and the colours are not for the AI
        self.assertFalse(self.sparked())
        # a selection across two cells has no bar either
        b.eval("""(()=>{ const h=edOf(document.getElementById('dePrev')); let a=-1,z=-1; h.editor.state.doc.descendants((n,pos)=>{ if(n.isText&&n.text==='ABC-A-101') a=pos+1;
          if(n.isText&&n.text.startsWith('Send the revised')) z=pos+4; }); h.focus(); h.editor.commands.setTextSelection({from:a,to:z}); })()""")
        b.pump(0.35)
        self.assertFalse(self.sparked())

    def test_an_accepted_suggestion_edits_the_email_and_the_copy_keeps_the_table_and_the_colours(self):
        b = self.b
        self.open_email()
        self.reply("I trust you are well.")
        self.select_in("#dePrev", "I hope you're well")
        self.open_bar()
        self.pick("tone", "formal")
        self.assertIn("I trust you are well.", self.ready())
        b.click(f"{LAYER} .aisug button[data-aifirst]")
        b.wait("DE.edited===true")
        html, text = self.copy(True)
        self.assertIn("I trust you are well.", html)
        self.assertNotIn("I hope you're well", html)
        self.assertIn("I trust you are well.", text)
        self.assertNotIn("ProseMirror", html)
        for kept in ('<table cellpadding="6" cellspacing="0" border="0"', "border-collapse:collapse", 'align="left"', "background:#F1F3F4",
                     "color:#B3261E", "font-family:Calibri,Arial,sans-serif", "<td ", "<th "):
            self.assertIn(kept, html, kept)
        self.assertRegex(html, r'^<div style="font-family:Calibri,Arial,sans-serif;font-size:11pt;color:#1E1F1E;background:#FFFFFF;">')
        self.assertNotRegex(html, r"<td[^>]*><p")                                # a cell's text is not wrapped in a paragraph (its margin would grow every row)
        # changing an option after an edit asks first, as before
        b.eval("document.getElementById('deUpd').click(); true")
        self.assertTrue(b.eval("!document.getElementById('deNote').hidden"))
        self.assertIn("I trust you are well.", b.eval("document.getElementById('dePrev').innerText"))

    def test_typing_markdown_marks_starts_nothing_and_typing_edits_the_email(self):
        b = self.b
        self.open_email()
        b.eval("edOf(document.getElementById('dePrev')).focus('start'); true")
        b.wait("document.activeElement===document.getElementById('dePrev')", 5)   # Tiptap's focus lands on the next frame
        b.type("# not a heading")
        b.eval("edOf(document.getElementById('dePrev')).editor.commands.setTextSelection(1); true")
        b.type("- not a list")
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('#dePrev h1,#dePrev h2,#dePrev ul,#dePrev ol,#dePrev li').length"), 0)
        self.assertTrue(b.eval("DE.edited"))
        html, _ = self.copy(True)
        self.assertIn("not a heading", html)
        self.assertIn("not a list", html)

    def test_the_email_has_no_link_mark_so_nothing_links_and_a_pasted_link_is_flattened(self):
        b = self.b
        self.open_email()
        self.assertTrue(b.eval("edOf(document.getElementById('dePrev')).editor.schema.marks.link===undefined"))
        b.eval("edOf(document.getElementById('dePrev')).focus('start'); true")
        b.wait("document.activeElement===document.getElementById('dePrev')", 5)   # Tiptap's focus lands on the next frame
        b.type("see www.example.com ")
        b.eval("""(()=>{ const e=edOf(document.getElementById('dePrev')).editor; e.view.pasteHTML('<a href="https://evil.example/x">pasted words</a>');
          })()""")
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('#dePrev a').length"), 0)
        html, _ = self.copy(True)
        self.assertIn("www.example.com", html)
        self.assertIn("pasted words", html)
        self.assertNotIn("<a ", html)
        self.assertNotIn("href", html)

    def test_the_ai_bar_is_off_for_an_outside_recipient_and_on_for_an_internal_one(self):
        # #133's interim, kept by #186 until the server decides the audience itself: no Ask... sparkle for an outside recipient while
        # the server doesn't answer /api/edit/ai/caps (the #186 proposal not applied); with it applied the bar is on there too
        # (test_email_client_facts_186 tests that side), back when the recipient is internal
        b = self.b
        self.open_email()
        self.assertFalse(b.eval("DE.outside"))
        self.select_in("#dePrev", "I hope you're well")
        self.assertTrue(self.sparked(), "internal recipient: the bar is there")
        b.eval(CLEAN)
        b.eval('REG[0].email="sara@client.example"; openDraftEmail("Sara Example"); true')   # the recipient becomes outside
        b.wait("!!document.querySelector('#dePrev.ProseMirror')")
        self.select_in("#dePrev", "I hope you're well")
        self.assertTrue(b.eval("DE.outside"))
        self.assertEqual(self.sparked(), b.eval("deAiSafe()"), "outside recipient: the bar only once the server decides the audience")
        b.eval(CLEAN)
        b.eval('REG[0].email="sara@brightwater.example"; openDraftEmail("Sara Example"); true')   # and internal again
        b.wait("!!document.querySelector('#dePrev.ProseMirror')")
        self.select_in("#dePrev", "I hope you're well")
        self.assertTrue(self.sparked(), "internal again: the bar is back")

    def test_at_900px_the_email_bar_fits(self):
        b = self.b
        b.resize(900, 900)
        self.addCleanup(lambda: self.b and self.b.resize(1400, 900))
        self.open_email()
        self.select_in("#dePrev", "I hope you're well")
        self.open_bar()
        r = b.eval(f"(()=>{{ const r=document.querySelector('{LAYER} .aibar').getBoundingClientRect(); return [r.left>=0, r.right<=innerWidth]; }})()")
        self.assertEqual(r, [True, True])
        self.assertTrue(b.eval("document.getElementById('deDlg').scrollWidth<=document.getElementById('deDlg').clientWidth"))


class TheSources(unittest.TestCase):
    def test_the_old_preview_is_gone_and_the_draft_email_keeps_the_builder_as_its_source(self):
        src = (SRC / "drafts.js").read_text(encoding="utf-8")
        self.assertNotIn("prev.innerHTML", src)                                 # Copy no longer reads the editor's DOM
        self.assertRegex(src, r'creaiteEditor\(el,\{ features:"email"')
        self.assertIn("DE.built", src.replace("shared.DE.built", "DE.built"))
        self.assertTrue(re.search(r"place:\s*\"email\"", src))


if __name__ == "__main__":
    unittest.main()

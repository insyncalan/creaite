"""H5 / #218: the text section of the weekly and client report, in a real browser on the real live server (LiveBrowserCase; no Claude runs).

Run: python3 dev/tests/test_report_text_section_ui.py      (Chrome tier; skipped without Chrome)

- Add: the "Add a text section" button at the foot of the report, the "Add a text section below" item of a section's menu, and the
  `addTextSection(afterId)` entry point (what any menu calls); a new section starts with an empty heading that has the cursor.
- The editor profile: the Notes bar (Heading, B I S code, List, quote, Link, Insert, undo, redo) with the Notes menus, Insert has Table and
  Picture only (no note, person or work-item pickers), and the `/` menu's rows.
- What each tool writes is what Notes writes (the Markdown the one editor's own writer gives); saved with the report; reloading gives it back
  and the one editor's round trip leaves it byte for byte.
- A picture is filed under `_images/` in the Reports folder and drawn again after a reload.
- Move up and down, leave out of the export (Hide), delete (asks first when it holds words), Show as exported (no controls).
- The client report: an internal text section is "Internal only" beside the client page until "Add to the client report"; one written in
  the client report is "Written for the client"; Match internal on a matched one copies its words.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
import test_reports as R  # noqa: E402
from test_report_text_section import png  # noqa: E402

J = json.dumps
FT = "#v-reporting section[data-id^=free_]"
BAR = ".sheet-rtebar"
NOTES_BAR = ["m-heading", "b", "i", "s", "code", "m-list", "quote", "link", "m-insert", "undo", "redo"]
RICH = ("# Heading one\n\n## Heading two\n\n### Heading three\n\nPlain **bold** *italic* ~~struck~~ `code` and a [link](https://example.com/a).\n\n"
        "- bullet\n  - nested\n\n1. first\n2. second\n\n- [ ] open\n- [x] done\n\n> a quote\n\n```\nlet x = 1;\n```\n\n"
        "| Name | Role |\n| --- | --- |\n| Mia | Lead |\n")


class Base(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)

    def setUp(self):
        super().setUp()
        self.b.eval("go('reporting','ABC')")
        self.b.wait("document.querySelector('#v-reporting section[data-id=current_state]')", 20)

    def ev(self, js):
        return self.b.eval(js)

    def ids(self):
        return self.ev("[...document.querySelectorAll('#v-reporting .page>section[data-id]')].map(s=>s.dataset.id)")

    def add_foot(self):
        self.b.click("#v-reporting [data-addtext]")
        self.b.wait(f"!!document.querySelector({J(FT + ' .sheet-ft.ProseMirror')})", 10)
        return self.ev(f"document.querySelector({J(FT)}).dataset.id")

    def editor(self, sid=None):
        sel = f"#v-reporting section[data-id={sid}] .sheet-ft" if sid else FT + " .sheet-ft"
        return sel

    def put(self, md, sid=None):
        """Set the section's text as an edit (the editor's own insert, so the page sees a change and saves it)."""
        sel = self.editor(sid)
        self.ev(f"(()=>{{ const e=document.querySelector({J(sel)}).cxed.editor; e.chain().focus().setContent('',{{emitUpdate:false}}).insertContent({J(md)},{{contentType:'markdown'}}).run(); }})()")

    def value(self, sid=None):
        return self.ev(f"document.querySelector({J(self.editor(sid))}).cxed.value()")

    def saved(self):
        self.b.wait("/Saved · version/.test(document.querySelector('#v-reporting .sheet-status').textContent)", 15)

    def draft_data(self):
        draft = next((self.v.root / "system/staging/drafts").glob("*Weekly report*.html"))
        return json.loads(draft.read_text(encoding="utf-8").split('id="creaite-data">', 1)[1].split("</script>", 1)[0])


class AddAndEdit(Base):
    def test_the_foot_button_adds_a_text_section_at_the_end_with_the_cursor_in_its_heading(self):
        self.assertEqual(self.ev("document.querySelectorAll('#v-reporting [data-addtext]').length"), 1)
        sid = self.add_foot()
        self.assertTrue(sid.startswith("free_"))
        self.assertEqual(self.ids()[-1], sid)
        self.assertTrue(self.ev(f"document.activeElement===document.querySelector({J(FT + ' .sheet-h')})"), "the heading has the cursor")
        self.assertEqual(self.ev(f"document.querySelector({J(FT + ' .sheet-h')}).placeholder"), "Section heading")
        self.assertEqual(self.ev(f"document.querySelector({J(FT + ' .sheet-ft')}).getAttribute('contenteditable')"), "true")

    def test_the_sections_menu_adds_one_below_it(self):
        b = self.b
        b.click("#v-reporting section[data-id=summary] .sheet-hbtn")
        b.wait("[...document.querySelectorAll('[role=menu] [role^=menuitem]')].some(x=>/Add a text section below/.test(x.textContent))", 5)
        self.ev("[...document.querySelectorAll('[role=menu] [role^=menuitem]')].find(x=>/Add a text section below/.test(x.textContent)).click()")
        b.wait(f"!!document.querySelector({J(FT)})", 10)
        ids = self.ids()
        sid = ids[ids.index("summary") + 1]
        self.assertTrue(sid.startswith("free_"), ids)
        self.assertEqual(self.ev("document.querySelectorAll('#v-reporting section[data-id^=free_]').length"), 1)

    def test_the_entry_point_other_menus_call(self):
        self.assertTrue(self.ev("addTextSection('summary')"))
        self.b.wait(f"!!document.querySelector({J(FT)})", 10)
        ids = self.ids()
        self.assertTrue(ids[ids.index("summary") + 1].startswith("free_"), ids)
        self.assertTrue(self.ev("addTextSection(null)"))
        self.b.wait("document.querySelectorAll('#v-reporting section[data-id^=free_]').length==2", 10)
        self.assertTrue(self.ids()[-1].startswith("free_"))

    def test_the_heading_is_named_in_place_and_saved(self):
        sid = self.add_foot()
        self.ev(f"(()=>{{ const i=document.querySelector({J(FT + ' .sheet-h')}); i.value='Vendor notes'; i.dispatchEvent(new Event('input',{{bubbles:true}})); i.blur(); }})()")
        self.b.wait(f"document.querySelector({J(FT + ' .sheet-h')}).value==='Vendor notes'", 5)
        self.saved()
        sec = next(s for s in self.draft_data()["sections"] if s["id"] == sid)
        self.assertEqual((sec["type"], sec["heading"], sec["audience"]), ("freetext", "Vendor notes", "internal"))

    def test_the_editor_has_the_notes_bar_and_menus_and_no_pickers_of_internal_things(self):
        b = self.b
        self.add_foot()
        b.click(self.editor())
        b.wait(f"!!document.querySelector({J(FT + ' ' + BAR)})")
        self.assertEqual(self.ev(f"[...document.querySelectorAll({J(FT + ' ' + BAR + ' [data-nt]')})].map(x=>x.dataset.nt)"), NOTES_BAR)

        def menu(name):
            b.click(f"{FT} {BAR} [data-nt={name}]")
            b.wait(f"!!document.querySelector({J(FT + ' ' + BAR + ' [role=menu] [data-cmd]')})", 5)
            got = self.ev(f"[...document.querySelectorAll({J(FT + ' ' + BAR + ' [role=menu] [data-cmd]')})].map(x=>x.dataset.cmd)")
            b.eval(f"document.querySelector({J(self.editor())}).focus()")
            return got
        self.assertEqual(menu("m-heading"), ["text", "h1", "h2", "h3", "clear"])
        self.assertEqual(menu("m-list"), ["ul", "ol", "task", "indent", "outdent"])
        self.assertEqual(menu("m-insert"), ["table", "image"])

    def test_the_slash_menu_has_the_notes_blocks_and_no_internal_pickers(self):
        b = self.b
        self.add_foot()
        b.click(self.editor())
        b.type("/")
        b.wait("!!document.querySelector('.slashroot [role=option]')", 5)
        rows = self.ev("[...document.querySelectorAll('.slashroot [role=option]')].map(x=>x.textContent)")
        text = " | ".join(rows)
        for want in ("Text", "Heading 1", "Heading 2", "Heading 3", "Bulleted list", "Numbered list", "Checklist", "Quote", "Code", "Table", "Image", "Link"):
            self.assertIn(want, text)
        for never in ("Work item", "Person", "Note", "Stakeholder", "Lessons learned", "Working session"):
            self.assertNotRegex(text, rf"\b{never}\b(?! list)", f"{never} is not offered in a report")

    def test_every_tool_writes_what_notes_writes(self):
        b = self.b
        self.add_foot()
        cases = [("m-heading", "h1", "x", r"(?m)^# x$"), ("m-heading", "h2", "x", r"(?m)^## x$"), ("m-heading", "h3", "x", r"(?m)^### x$"),
                 (None, "b", "word", r"\*\*word\*\*"), (None, "i", "word", r"(\*|_)word\1"), (None, "s", "word", r"~~word~~"),
                 (None, "code", "word", r"`word`"), ("m-list", "ul", "x", r"(?m)^[-*] x$"), ("m-list", "ol", "x", r"(?m)^1\. x$"),
                 ("m-list", "task", "x", r"(?m)^[-*] \[ \] x$"), (None, "quote", "x", r"(?m)^> x$")]
        for menu, cmd, text, rx in cases:
            self.ev(f"(()=>{{ const el=document.querySelector({J(self.editor())}); el.cxed.setValue({J(text)}); el.cxed.focus('end'); el.cxed.editor.commands.selectAll(); }})()")
            b.wait(f"document.activeElement===document.querySelector({J(self.editor())})", 5)
            b.frames(3)
            if menu:
                b.click(f"{FT} {BAR} [data-nt={menu}]")
                b.wait(f"!!document.querySelector({J(FT + ' ' + BAR + ' [role=menu] [data-cmd=' + cmd + ']')})", 5)
                b.click(f"{FT} {BAR} [role=menu] [data-cmd={cmd}]")
            else:
                b.click(f"{FT} {BAR} [data-nt={cmd}]")
            self.assertRegex(self.value(), rx, cmd)

    def test_table_and_code_block_are_inserted_the_way_notes_inserts_them(self):
        b = self.b
        self.add_foot()
        b.click(self.editor())
        b.click(f"{FT} {BAR} [data-nt=m-insert]")
        b.wait(f"!!document.querySelector({J(FT + ' ' + BAR + ' [role=menu] [data-cmd=table]')})", 5)
        b.click(f"{FT} {BAR} [role=menu] [data-cmd=table]")
        b.wait(f"!!document.querySelector({J(FT + ' .sheet-ft table')})", 5)
        self.assertRegex(self.value(), r"(?m)^\| +\| +\| +\|$")
        self.ev(f"document.querySelector({J(self.editor())}).cxed.setValue('')")
        b.click(self.editor())
        b.type("/code")
        b.wait("!!document.querySelector('.slashroot [role=option]')", 5)
        b.key("Enter")
        b.wait(f"!!document.querySelector({J(FT + ' .sheet-ft pre')})", 5)
        b.type("let x = 1;")
        self.assertRegex(self.value(), r"```\nlet x = 1;\n```")

    def test_what_is_written_is_saved_with_the_report_and_comes_back_byte_for_byte(self):
        b = self.b
        sid = self.add_foot()
        self.put(RICH)
        self.saved()
        text = next(s for s in self.draft_data()["sections"] if s["id"] == sid)["text"]
        for want in ("# Heading one", "**bold**", "~~struck~~", "`code`", "https://example.com/a", "- [ ] open", "- [x] done", "> a quote",
                     "```", "| Name", "| Mia"):
            self.assertIn(want, text)
        b.eval("go('reporting','ABC')")
        b.wait(f"!!document.querySelector({J(FT + ' .sheet-ft.ProseMirror')})", 20)
        self.assertEqual(self.value(sid), text, "the one editor's round trip leaves what was saved as it was")

    def test_raw_html_in_the_text_never_becomes_page_markup(self):
        self.add_foot()
        self.put('<script>window.__x=1</script> <span style="color:red" onclick="window.__y=1">red</span>')
        self.saved()
        self.assertFalse(self.ev("window.__x||window.__y||false"))
        self.assertEqual(self.ev(f"document.querySelectorAll({J(FT + ' .sheet-ft script, ' + FT + ' .sheet-ft span[style]')}).length"), 0)
        page = next((self.v.root / "system/staging/drafts").glob("*Weekly report*.html")).read_text(encoding="utf-8")
        self.assertEqual(page.count("</script>"), 1, "the data block's own closing tag only")
        self.assertNotIn("<script>window.__x", page)


    def test_pasted_rich_text_brings_its_words_and_marks_but_never_its_styles(self):
        sid = self.add_foot()
        self.b.click(self.editor())
        self.ev(f"""(()=>{{ const el=document.querySelector({J(self.editor())}); el.focus(); const dt=new DataTransfer();
          dt.setData('text/html','<p style="color:red;font-size:40px">Hello <b style="background:yellow">there</b> <span style="position:fixed">span</span></p><div onclick="window.__z=1">next</div>');
          dt.setData('text/plain','Hello there span next');
          el.dispatchEvent(new ClipboardEvent('paste',{{clipboardData:dt,bubbles:true,cancelable:true}})); }})()""")
        self.b.wait(f"/Hello/.test(document.querySelector({J(self.editor())}).textContent)", 5)
        self.saved()
        text = next(s for s in self.draft_data()["sections"] if s["id"] == sid)["text"]
        self.assertIn("Hello **there**", text)
        for leak in ("style", "color", "position", "onclick", "<span", "<div"):
            self.assertNotIn(leak, text)
        page = next((self.v.root / "system/staging/drafts").glob("*Weekly report*.html")).read_text(encoding="utf-8")
        self.assertNotIn("position:fixed", page)


class Pictures(Base):
    def test_a_picture_is_filed_in_the_reports_folder_and_drawn_again_after_a_reload(self):
        b = self.b
        sid = self.add_foot()
        shot = self.v.root / "shot.png"
        shot.write_bytes(png(30, 12, (0, 120, 200, 255)))
        b.click(self.editor())
        b.set_files(f"{FT} input.sheet-imgfile", [str(shot)])
        b.wait(f"!!document.querySelector({J(FT + ' .sheet-ft figure img')})", 10)
        self.saved()
        text = next(s for s in self.draft_data()["sections"] if s["id"] == sid)["text"]
        m = re.search(r"!\[[^\]]*\]\((_images/[^)]+\.png)\)", text)
        self.assertIsNotNone(m, text)
        self.assertEqual(next((self.v.root / "projects").glob(f"ABC*/reports/{m.group(1)}")).read_bytes(), shot.read_bytes())
        b.eval("go('reporting','ABC')")
        b.wait(f"!!document.querySelector({J(FT + ' .sheet-ft figure img')})", 20)
        self.assertTrue(self.ev(f"document.querySelector({J(FT + ' .sheet-ft figure img')}).src.startsWith('data:image/png;base64,')"))

    def test_a_picture_over_two_megabytes_or_of_another_kind_is_refused_with_a_sentence(self):
        b = self.b
        self.add_foot()
        big = self.v.root / "big.png"
        big.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024 + 10))
        gif = self.v.root / "x.gif"
        gif.write_bytes(b"GIF89a")
        b.click(self.editor())
        b.set_files(f"{FT} input.sheet-imgfile", [str(big)])
        b.wait(f"/2 MB/.test((document.querySelector({J(FT + ' .sheet-ftmsg')})||{{}}).textContent||'')", 10)
        self.assertEqual(self.ev(f"document.querySelectorAll({J(FT + ' .sheet-ft figure')}).length"), 0)


class MoveHideDelete(Base):
    def menu_do(self, sid, name):
        b = self.b
        b.click(f"#v-reporting section[data-id={sid}] .sheet-hbtn")
        b.wait(f"[...document.querySelectorAll('[role=menu] [role^=menuitem]')].some(x=>x.textContent.includes({J(name)}))", 5)
        self.ev(f"[...document.querySelectorAll('[role=menu] [role^=menuitem]')].find(x=>x.textContent.includes({J(name)})).click()")

    def test_it_moves_up_and_down_like_any_section_and_the_layout_follows(self):
        sid = self.add_foot()
        n = len(self.ids())
        self.menu_do(sid, "Move up")
        self.b.wait(f"[...document.querySelectorAll('#v-reporting .page>section[data-id]')].map(s=>s.dataset.id).indexOf({J(sid)})=={n - 2}", 5)
        self.menu_do(sid, "Move down")
        self.b.wait(f"[...document.querySelectorAll('#v-reporting .page>section[data-id]')].map(s=>s.dataset.id).indexOf({J(sid)})=={n - 1}", 5)
        self.saved()
        data = self.draft_data()
        self.assertEqual(data["layout"]["order"][-1], sid)
        self.assertEqual([s["id"] for s in data["sections"]][-1], sid)

    def test_it_can_be_left_out_of_the_export_and_brought_back_with_its_words(self):
        sid = self.add_foot()
        self.put("walrus words")
        self.saved()
        self.menu_do(sid, "Leave out of the export")
        self.b.wait(f"!!document.querySelector('[data-hidden={sid}]')", 5)
        self.saved()
        sec = next(s for s in self.draft_data()["sections"] if s["id"] == sid)
        self.assertTrue(sec["hidden"])
        self.ev("document.querySelector('#v-reporting #hubExp').click()")
        self.b.wait("document.querySelector('#v-reporting .sheet-exported')", 5)
        self.assertNotIn("walrus", self.ev("document.querySelector('#v-reporting .page').innerText"))
        self.ev("document.querySelector('#v-reporting #hubExp').click()")
        self.b.wait(f"!!document.querySelector('[data-hidden={sid}]')", 5)
        self.b.eval(f"document.querySelector('[data-hidden={sid}] .linkbtn').click()")
        self.b.wait(f"!!document.querySelector({J(FT + ' .sheet-ft.ProseMirror')})", 10)
        self.assertEqual(self.value(sid).strip(), "walrus words", "a hidden text section keeps Alan's words")

    def test_delete_asks_first_when_it_holds_words_and_removes_it_from_the_file(self):
        sid = self.add_foot()
        self.put("words to lose")
        self.saved()
        self.menu_do(sid, "Delete this section")
        self.b.wait("!!document.querySelector('.sheet-delask')", 5)
        self.b.click(".sheet-delask .btn:not([data-delyes])")                            # Keep
        self.b.wait("!document.querySelector('.sheet-delask')", 5)
        self.assertIn(sid, self.ids())
        self.menu_do(sid, "Delete this section")
        self.b.wait("!!document.querySelector('.sheet-delask')", 5)
        self.b.click(".sheet-delask [data-delyes]")
        self.b.wait(f"!document.querySelector('#v-reporting section[data-id={sid}]')", 5)
        self.saved()
        data = self.draft_data()
        self.assertNotIn(sid, [s["id"] for s in data["sections"]])
        self.assertNotIn(sid, data["layout"]["order"])
        self.assertNotIn(sid, (data["layout"].get("headings") or {}))

    def test_an_empty_one_is_deleted_without_asking_and_only_text_sections_can_be_deleted(self):
        sid = self.add_foot()
        self.menu_do(sid, "Delete this section")
        self.b.wait(f"!document.querySelector('#v-reporting section[data-id={sid}]')", 5)
        self.b.click("#v-reporting section[data-id=summary] .sheet-hbtn")
        self.b.wait("!!document.querySelector('[role=menu] [role^=menuitem]')", 5)
        self.assertFalse(self.ev("[...document.querySelectorAll('[role=menu] [role^=menuitem]')].some(x=>/Delete this section/.test(x.textContent))"))
        self.b.key("Escape")

    def test_show_as_exported_draws_the_section_whole_with_no_controls(self):
        sid = self.add_foot()
        self.ev(f"(()=>{{ const i=document.querySelector({J(FT + ' .sheet-h')}); i.value='Vendor notes'; i.dispatchEvent(new Event('input',{{bubbles:true}})); i.blur(); }})()")
        self.put(RICH)
        self.ev("document.querySelector('#v-reporting #hubExp').click()")
        self.b.wait("document.querySelector('#v-reporting .sheet-exported')", 5)
        sec = f"#v-reporting section[data-id={sid}]"
        self.assertEqual(self.ev(f"document.querySelector({J(sec + ' h2')}).textContent"), "Vendor notes")
        self.assertEqual(self.ev(f"document.querySelectorAll({J(sec + ' .sheet-h, ' + sec + ' .sheet-handle, ' + sec + ' .sheet-rtebar')}).length"), 0)
        self.assertEqual(self.ev(f"document.querySelector({J(sec + ' .sheet-ft')}).getAttribute('contenteditable')"), "false")
        self.assertEqual(self.ev("document.querySelectorAll('#v-reporting [data-addtext]').length"), 0)
        for sel in ("h1", "h2", "h3", "strong", "em", "s", "code", "ul ul", "ol", "ul[data-type=taskList]", "blockquote", "pre", "table", "a[href]"):
            self.assertGreaterEqual(self.ev(f"document.querySelectorAll({J(sec + ' .sheet-ft ' + sel)}).length"), 1, sel)


class ClientRuleUI(LiveBrowserCase):
    """The client report beside the internal one."""

    @classmethod
    def load(cls, v):
        R.populate(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": R.NOW, "CREAITE_NO_LAUNCH": "1"}

    def api(self, path, body):
        return self.b.eval(f"fetch({J(path)},{{method:'POST',headers:{{'Content-Type':'application/json','X-Creaite-Token':D.token}},body:{J(json.dumps(body))}}}).then(r=>r.json()).then(j=>{{window.__r=j}})") or None

    def post(self, path, body):
        self.b.eval("window.__r=null")
        self.api(path, body)
        self.b.wait("window.__r!==null", 20)
        return self.b.eval("window.__r")

    def internal_with_text(self):
        r = self.post("/api/report/draft", {"kind": "weekly", "code": "ABC", "week_ending": "2026-10-09"})
        doc = r["doc"]
        next(s for s in doc["sections"] if s["id"] == "health")["text"] = "UAT start slipped two weeks."
        at = next(i for i, s in enumerate(doc["sections"]) if s["id"] == "summary") + 1
        doc["sections"].insert(at, {"id": "free_int", "type": "freetext", "heading": "Vendor notes", "default_heading": "", "hidden": False,
                                    "text": "INTERNAL walrus words", "audience": "internal"})
        doc["layout"]["order"] = [s["id"] for s in doc["sections"]]
        self.assertTrue(self.post("/api/report/save", {"doc": doc, "base_version": 0})["ok"])

    def open_side(self):
        self.b.eval("go('reporting','ABC'); hubView.value='client'")
        self.b.wait("document.querySelector('#v-reporting .wr-health')", 20)
        self.b.click("#hubSeg [data-hv='side']")
        self.b.wait("document.querySelectorAll('#v-reporting .sheet-pair > .sheet-fit').length===2", 10)

    def pages(self, k):
        return f"document.querySelectorAll('#v-reporting .sheet-pair > .sheet-fit')[{k}]"

    def test_an_internal_text_section_is_internal_only_until_it_is_added_to_the_client_report(self):
        self.internal_with_text()
        self.b.eval("go('reporting','ABC'); hubView.value='client'")
        self.b.wait("document.querySelector('#v-reporting .wr-health')", 20)
        self.assertNotIn("walrus", self.b.eval("document.querySelector('#v-reporting .page').innerText"), "the client page opens without it")
        self.assertEqual(self.b.eval("document.querySelectorAll('#v-reporting section[data-id=free_int]').length"), 0)
        self.open_side()
        left = self.pages(0)
        self.assertIn("Internal only", self.b.eval(f"{left}.querySelector('section[data-id=free_int] .sheet-match').textContent"))
        self.assertEqual(self.b.eval(f"{self.pages(1)}.querySelectorAll('section[data-id=free_int]').length"), 0)
        self.b.eval(f"{left}.querySelector('section[data-id=free_int] [data-addto]').click()")
        self.b.wait(f"{self.pages(1)}.querySelectorAll('section[data-id=free_int]').length===1", 10)
        self.b.wait(f"{self.pages(1)}.querySelector('section[data-id=free_int]').innerText.includes('walrus')", 10)
        ids = self.b.eval(f"[...{self.pages(1)}.querySelectorAll('.page > section[data-id]')].map(s=>s.dataset.id)")
        self.assertEqual(ids[ids.index("free_int") - 1], "summary", "it lands where it stood")

    def test_match_internal_for_every_section_does_not_bring_an_internal_text_section_over(self):
        self.internal_with_text()
        self.open_side()
        self.b.eval("document.querySelector('#v-reporting [data-crmatchall]').click()")
        self.b.wait("!!document.querySelector('[data-crskipsec=free_int]')", 10)     # the match has finished (it names the skipped section)
        self.assertEqual(self.b.eval(f"{self.pages(1)}.querySelectorAll('section[data-id=free_int]').length"), 0)
        self.assertEqual(self.b.eval("document.querySelector('[data-crskipsec=free_int]').textContent"),
                         "Vendor notes: internal only, add it to the client report yourself")

    def test_match_internal_for_every_section_leaves_a_client_written_section_alone_and_says_nothing_without_internal_text(self):
        self.internal_with_text()
        self.open_side()
        self.b.click("#v-reporting .sheet-pair > .sheet-fit + .sheet-fit [data-addtext]")
        self.b.wait(f"{self.pages(1)}.querySelectorAll('section[data-id^=free_]').length===1", 10)
        mine = self.b.eval(f"{self.pages(1)}.querySelector('section[data-id^=free_]').dataset.id")
        self.b.eval("document.querySelector('#v-reporting [data-crmatchall]').click()")
        self.b.pump(1)
        self.assertEqual(self.b.eval(f"{self.pages(1)}.querySelectorAll('section[data-id=free_int]').length"), 0)
        self.assertEqual(self.b.eval(f"{self.pages(1)}.querySelectorAll('section[data-id={mine}]').length"), 1, "the client-written section stays")
        self.assertNotIn("walrus", self.b.eval(f"{self.pages(1)}.innerText"))
        self.assertEqual(self.b.eval(f"document.querySelectorAll('[data-crskipsec={mine}]').length"), 0, "only internal-only sections are named")

    def test_a_section_written_in_the_client_report_says_so_and_an_added_one_matches_internal(self):
        self.internal_with_text()
        self.open_side()
        self.b.click("#v-reporting .sheet-pair > .sheet-fit + .sheet-fit [data-addtext]")
        self.b.wait(f"{self.pages(1)}.querySelectorAll('section[data-id^=free_]').length===1", 10)
        self.assertIn("Written for the client", self.b.eval(f"{self.pages(1)}.querySelector('section[data-id^=free_] .sheet-match').textContent"))
        self.b.eval(f"{self.pages(0)}.querySelector('section[data-id=free_int] [data-addto]').click()")
        self.b.wait(f"{self.pages(1)}.querySelectorAll('section[data-id=free_int]').length===1", 10)
        self.assertEqual(self.b.eval(f"{self.pages(1)}.querySelector('section[data-id=free_int] .sheet-match').textContent.includes('Matching internal')"), True)
        self.b.wait(f"!!{self.pages(1)}.querySelector('section[data-id=free_int] .sheet-ft.ProseMirror')", 10)
        self.b.eval(f"{self.pages(1)}.querySelector('section[data-id=free_int] .sheet-ft').cxed.editor.chain().focus('end').insertContent(' edited for you').run()")
        mine = []
        for _ in range(40):                                  # the sheet saves 1.5 s after the last change
            client = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": "2026-10-09"})["doc"]
            mine = [s for s in client["sections"] if s["type"] == "freetext"]
            if len(mine) == 2:
                break
            self.b.pump(0.5)
        self.assertEqual(sorted(s["audience"] for s in mine), ["client", "client"], "both belong to the client report once written or added there")
        copy = next(s for s in mine if s["id"] == "free_int")
        self.assertIn("walrus", copy["text"])
        self.assertIn("edited for you", copy["text"])


if __name__ == "__main__":
    unittest.main()

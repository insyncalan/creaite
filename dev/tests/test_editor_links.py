"""#120: links (insert, edit, remove) in the rich editors, in a real browser against the real live server.

Run: python3 dev/tests/test_editor_links.py   (needs Google Chrome; skipped otherwise)

Done when (the issue's Done-when and the link mockup, dev/mockups/editor-link-mockup.html):
- ONE address validator (core/linkUrl.js) allows http, https and mailto and refuses everything else, in every disguise;
- the editor, the popover, load and paste all use it: a hostile address in an existing file shows as plain text, a command or a
  paste cannot make one, and an untouched text is still written back as it came;
- four ways in: the toolbar button, the / menu's Link row, Cmd/Ctrl+Shift+K and pasting an address;
- the popover is a labelled dialog the keyboard can operate (Tab stays inside, Enter applies, Esc cancels and gives the cursor back);
- a click on a link only shows its popover; Open is a new tab with rel="noopener noreferrer"; Edit and Remove work;
- a paste makes a link with an Undo toast, and a refused paste is plain text;
- the Markdown is [text](address) and survives a reload of the text; work-item chips are not touched.
Desktop and 900 px only.
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META, SHIFT, CTRL = 4, 8, 2
REFUSED = "Only http, https and mailto addresses can be linked."

ACCEPT = {
    "https://example.com": "https://example.com",
    "http://example.com/a?b=1&c=2#d": "http://example.com/a?b=1&c=2#d",
    "HTTPS://Example.com/Path": "https://Example.com/Path",
    "https://example.com:8443/x": "https://example.com:8443/x",
    "https://sub.example.co.uk/a_(b)": "https://sub.example.co.uk/a_(b)",
    "https://[2001:db8::1]/x": "https://[2001:db8::1]/x",
    "mailto:pmo@example.com": "mailto:pmo@example.com",
    "MAILTO:pmo@example.com?subject=Plan%20review": "mailto:pmo@example.com?subject=Plan%20review",
}
REFUSE = [
    "javascript:alert(1)", "JAVASCRIPT:alert(1)", "JaVaScRiPt:alert(1)", "jav\tascript:alert(1)", "java\nscript:alert(1)",
    "java\rscript:alert(1)", "java&#x09;script:alert(1)", "&#106;avascript:alert(1)", "javascript&colon;alert(1)", "javascript&Tab;:alert(1)",
    " javascript:alert(1)", "\njavascript:alert(1)", "\u0000javascript:alert(1)", "\u0001https://example.com", "\u200bhttps://example.com",
    "\ufeffhttps://example.com", "data:text/html,<script>alert(1)</script>", "DATA:text/html;base64,PHNjcmlwdD4=", "file:///etc/passwd",
    "FILE:///etc/passwd", "vbscript:msgbox(1)", "blob:https://example.com/x", "about:blank", "ftp://example.com/x", "tel:+441234567890",
    "creaite:item/ABC-A-001", "//evil.example/x", "\\\\evil.example\\x", "/relative/path", "relative", "example.com", "www.example.com",
    "https://", "https:", "https:example.com", "https:///x", "http://", "https://user@example.com", "https://user:pw@example.com",
    "https://bank.example@evil.example/", " https://example.com", "https://example.com ", "https://exa mple.com", "https://example.com/a b",
    "https://example.com/\"onmouseover=alert(1)", "https://example.com/<script>", "https://example.com/`x`", "https://exa%20mple.com",
    "mailto:", "mailto:nobody", "mailto:a@example.com,b@example.com", "mailto:a@b@example.com", "mailto: pmo@example.com",
    "", " ", None, 5, "x" * 3000, "https://example.com/" + "x" * 2100,
]
TYPED = {
    "example.com": "https://example.com", "  www.example.com/plan  ": "https://www.example.com/plan",
    "sub.example.co.uk/a?b=1": "https://sub.example.co.uk/a?b=1", "example.com:8080/x": "https://example.com:8080/x",
    "pmo@example.com": "mailto:pmo@example.com", "https://example.com": "https://example.com", "\nhttps://example.com\n": "https://example.com",
}
TYPED_REFUSE = ["javascript:alert(1)", "java\nscript:alert(1)", "data:text/html,x", "file:///etc/passwd", "//evil.example", "\\evil.example", "word",
                "two words.com", "", "   ", "ftp://example.com", "https://user@example.com", "a@b", "http://"]


class Links(LiveBrowserCase):
    width, height = 1400, 1000

    def mod(self):
        return META if self.b.is_mac() else CTRL

    def memory(self):
        return next((self.v.root / "projects").glob("ABC */CLAUDE.md"))

    def make_note(self, title="Link test"):
        b = self.b
        b.eval("go('notes','ABC')")
        b.wait("!!document.getElementById('notesNew')")
        b.click("#notesNew")
        b.wait("document.getElementById('newNoteDlg').open")
        b.eval(f"(()=>{{ const i=document.getElementById('nnTitle'); i.value={title!r}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        b.eval("document.querySelector('#newNoteDlg input[value=\"blank\"]').click()")
        b.click("#nnMake")
        b.wait("!!document.querySelector('.nbody.ProseMirror')", 15)
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)

    def value(self):
        return self.b.eval("document.querySelector('.nbody').cxed.value()")

    def setmd(self, md):
        self.b.eval(f"document.querySelector('.nbody').cxed.setValue({json.dumps(md)})")
        self.b.pump(0.2)

    def select(self, word):
        """Select `word` in the note and focus it; the position it was found at."""
        at = self.b.eval("(w=>{ const h=document.querySelector('.nbody').cxed, e=h.editor; let at=-1;"
                         " e.state.doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf(w); if(i>=0) at=pos+i; } });"
                         " e.commands.focus(); e.commands.setTextSelection({from:at,to:at+w.length}); return at; })(%s)" % json.dumps(word))
        self.assertGreater(at, 0, f"{word!r} is in the note")
        self.b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        return at

    def popup(self):
        return self.b.eval("(()=>{ const p=document.querySelector('.linkpop'); return p?{cls:p.className,role:p.getAttribute('role'),label:p.getAttribute('aria-label'),"
                           "active:document.activeElement&&document.activeElement.id||'',activeIn:p.contains(document.activeElement),err:(p.querySelector('.linkerr')||{}).textContent||''}:null; })()")

    def paste(self, text=None, html=None):
        js = ("(t,h)=>{ const e=document.querySelector('.nbody').cxed.editor, dt=new DataTransfer(); if(t!==null) dt.setData('text/plain',t); if(h!==null) dt.setData('text/html',h);"
              " const ev=new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}); e.view.dom.dispatchEvent(ev); return ev.defaultPrevented; }")
        got = self.b.eval(f"({js})({json.dumps(text)},{json.dumps(html)})")
        self.b.pump(0.2)
        return got

    # ---- the one validator ---------------------------------------------------------------------------------------------------

    def test_the_validator_allows_http_https_and_mailto_and_refuses_every_disguise(self):
        b = self.b
        got = b.eval("(c=>c.map(s=>linkUrl(s)))(%s)" % json.dumps(list(ACCEPT)))
        self.assertEqual(got, list(ACCEPT.values()))
        bad = b.eval("(c=>c.map(s=>linkUrl(s)))(%s)" % json.dumps(REFUSE))
        self.assertEqual([(r, g) for r, g in zip(REFUSE, bad) if g is not None], [], "refused addresses that got through")
        typed = b.eval("(c=>c.map(s=>typedLinkUrl(s)))(%s)" % json.dumps(list(TYPED)))
        self.assertEqual(typed, list(TYPED.values()))
        tbad = b.eval("(c=>c.map(s=>typedLinkUrl(s)))(%s)" % json.dumps(TYPED_REFUSE))
        self.assertEqual([(r, g) for r, g in zip(TYPED_REFUSE, tbad) if g is not None], [], "typed addresses that got through")
        # a typed scheme is never guessed at: the validator judges it as written
        self.assertIsNone(b.eval("typedLinkUrl('javascript:alert(1)')"))
        # what a document may keep: web and mail addresses, and creaite's own item and person links, nothing else
        keep = b.eval("(c=>c.map(s=>keepHref(s)))(%s)" % json.dumps(["https://example.com", "mailto:a@example.com", "creaite:item/ABC-A-001",
                                                                       "creaite:person/Mia%20Hale", "javascript:alert(1)", "creaite:other/x", "creaite:item/a b", "file:///x"]))
        self.assertEqual(keep, [True, True, True, True, False, False, False, False])

    # ---- load, command and paste cannot make a hostile link ------------------------------------------------------------------

    def test_a_hostile_address_in_an_existing_text_shows_as_plain_text(self):
        b = self.b
        md = ("See [one](javascript:alert(1)) and [two](JaVaScRiPt:alert(2)) and [three](data:text/html,x) and [four](//evil.example/x) "
              "and [five](file:///etc/passwd) and the [good one](https://example.com/plan) and [mail](mailto:pmo@example.com).")
        for features in ("notes", "current"):
            got = b.eval("""(()=>{ const d=document.createElement('div'); d.id='probe'; d.setAttribute('contenteditable','true'); document.body.appendChild(d);
              const h=creaiteEditor(d,{features:%s,markdown:%s});
              const hrefs=[...d.querySelectorAll('a')].map(a=>a.getAttribute('href')), text=d.textContent, v0=h.value(), same=v0===%s;
              h.editor.commands.insertContentAt(h.editor.state.doc.content.size-1,' x'); const v1=h.value();
              const out={hrefs,text,same,v1,touched:h.touched()}; h.destroy(); d.remove(); return out; })()""" % (json.dumps(features), json.dumps(md), json.dumps(md)))
            self.assertEqual(got["hrefs"], ["https://example.com/plan", "mailto:pmo@example.com"], features)
            for w in ("one", "two", "three", "four", "five"):
                self.assertIn(w, got["text"], features)
            self.assertTrue(got["same"], f"{features}: an untouched text is written back as it came")
            self.assertNotIn("javascript", got["v1"].lower(), features)
            self.assertNotIn("file:", got["v1"], features)
            self.assertIn("[good one](https://example.com/plan)", got["v1"], features)

    def test_a_command_or_setvalue_cannot_make_a_hostile_link(self):
        b = self.b
        self.make_note("Commands")
        self.setmd("Some words to link here.")
        self.select("words")
        b.eval("document.querySelector('.nbody').cxed.editor.chain().setLink({href:'javascript:alert(1)'}).run()")
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a[href^=javascript]').length"), 0)
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 0)
        b.eval("document.querySelector('.nbody').cxed.editor.chain().insertContent({type:'text',text:'sneaky',marks:[{type:'link',attrs:{href:'data:text/html,x'}}]}).run()")
        b.pump(0.2)
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 0)
        self.assertIn("sneaky", b.eval("document.querySelector('.nbody').textContent"))
        self.assertNotIn("data:", self.value())
        self.setmd("Back to [fine](https://example.com/x) and [bad](vbscript:msgbox(1)).")
        self.assertEqual(b.eval("[...document.querySelectorAll('.nbody a')].map(a=>a.getAttribute('href'))"), ["https://example.com/x"])

    def test_work_item_and_person_links_are_left_alone(self):
        b = self.b
        self.make_note("Chips")
        self.setmd("Look at [ABC-A-001](creaite:item/ABC-A-001) and @[Mia Hale](creaite:person/Mia%20Hale) and [web](https://example.com).")
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 3)
        b.eval("document.querySelector('.nbody').cxed.editor.commands.insertContentAt(1,'x')")
        v = self.value()
        self.assertIn("(creaite:item/ABC-A-001)", v)
        self.assertIn("(creaite:person/Mia%20Hale)", v)
        # the link form will not write a web link over a chip
        self.select("ABC-A-001")
        b.key("k", self.mod() | SHIFT)
        b.pump(0.3)
        self.assertIsNone(self.popup())
        self.assertIn("(creaite:item/ABC-A-001)", self.value())

    # ---- the four ways in -----------------------------------------------------------------------------------------------------

    def test_the_toolbar_button_adds_a_link_in_a_labelled_dialog(self):
        b = self.b
        self.make_note("Toolbar")
        b.type("see the plan today")
        self.select("the plan")
        b.click(".nbar [data-nt=link]")
        b.wait("!!document.querySelector('.linkpop')", 5)
        p = self.popup()
        self.assertEqual((p["role"], p["label"]), ("dialog", "Link"))
        self.assertTrue(p["activeIn"])
        self.assertEqual(p["active"].split("-")[-1], "a", "the words are there already, so the cursor is in Address")
        self.assertEqual(b.eval("document.querySelector('.linkpop input').value"), "the plan")
        self.assertEqual(b.eval("[...document.querySelectorAll('.linkpop label')].map(l=>document.getElementById(l.htmlFor)&&l.textContent)"), ["Text", "Address"])
        b.type("example.com/plan")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertIn("see [the plan](https://example.com/plan) today", self.value())
        self.assertEqual(b.eval("document.activeElement===document.querySelector('.nbody')"), True, "the cursor is back in the text")

    def test_the_shortcut_adds_a_link_with_no_words_selected(self):
        b = self.b
        self.make_note("Shortcut")
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        self.assertFalse(b.eval("document.getElementById('cmdk').open"), "Cmd+Shift+K in an editor is the link, not the palette")
        self.assertEqual(self.popup()["active"].split("-")[-1], "a", "the cursor starts in Address")
        b.type("https://example.com/x")
        b.key("Tab", SHIFT)
        b.type("Plan")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertIn("[Plan](https://example.com/x)", self.value())

    def test_an_address_alone_is_its_own_text(self):
        b = self.b
        self.make_note("Alone")
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        b.type("pmo@example.com")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertIn("[mailto:pmo@example.com](mailto:pmo@example.com)", self.value())

    def test_the_slash_menu_has_a_link_row(self):
        b = self.b
        self.make_note("Slash")
        b.type("go to /link")
        b.wait("!!document.querySelector('.slashmenu [data-slash=link]')", 5)
        self.assertEqual(b.eval("document.querySelector('.slashmenu [data-slash=link] .t').textContent"), "Link")
        self.assertTrue(b.eval("!!document.querySelector('.slashmenu [data-slash=link] .d').textContent.trim()"))
        b.key("Enter")
        b.wait("!!document.querySelector('.linkpop')", 5)
        self.assertEqual(b.eval("document.querySelector('.nbody').textContent"), "go to ", "the typed /link goes")
        b.type("pmo@example.com")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertIn("go to [mailto:pmo@example.com](mailto:pmo@example.com)", self.value())

    # ---- refusals ---------------------------------------------------------------------------------------------------------------

    def test_a_refused_address_says_why_and_inserts_nothing(self):
        b = self.b
        self.make_note("Refuse")
        b.type("bad link here")
        for hostile in ("javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "//evil.example", "JaVaScRiPt:alert(1)"):
            self.select("link")
            b.key("k", self.mod() | SHIFT)
            b.wait("!!document.querySelector('.linkpop')", 5)
            b.eval("document.querySelector('.linkpop input[id$=\"-a\"]').select()")
            b.type(hostile)
            b.key("Enter")
            b.pump(0.2)
            p = self.popup()
            self.assertIsNotNone(p, f"{hostile}: the popover stays open")
            self.assertEqual(p["err"], REFUSED, hostile)
            self.assertEqual(b.eval("document.querySelector('.linkpop input[id$=\"-a\"]').getAttribute('aria-invalid')"), "true")
            self.assertEqual(self.value().strip(), "bad link here", f"{hostile}: nothing is inserted")
            b.key("Escape")
            b.wait("!document.querySelector('.linkpop')", 5)
        # an empty address asks for one
        self.select("link")
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        b.key("Enter")
        self.assertEqual(self.popup()["err"], "Enter an address.")

    # ---- the keyboard -------------------------------------------------------------------------------------------------------------

    def test_the_popover_is_a_small_dialog_the_keyboard_runs(self):
        b = self.b
        self.make_note("Keys")
        b.type("alpha beta gamma")
        self.select("beta")
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        order = []
        for _ in range(6):
            order.append(b.eval("(()=>{ const a=document.activeElement; return a.dataset.lk||a.id.split('-').pop(); })()"))
            b.key("Tab")
        self.assertEqual(order, ["a", "apply", "cancel", "t", "a", "apply"], "Tab stays inside the popover and wraps")
        b.eval("document.querySelector('.linkpop input[id$=\"-t\"]').focus()")
        b.key("Tab", SHIFT)
        self.assertEqual(b.eval("document.activeElement.dataset.lk"), "cancel", "Shift+Tab wraps backwards")
        b.key("Escape")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertTrue(b.eval("document.activeElement===document.querySelector('.nbody')"), "Esc gives the cursor back")
        self.assertEqual(self.value().strip(), "alpha beta gamma", "and changes nothing")
        self.assertEqual(b.eval("(()=>{ const s=window.getSelection(); return s.rangeCount?s.toString():''; })()"), "", "the text is not left selected on a link that was never made")

    def test_the_view_popover_is_reached_by_tab_and_closed_by_esc(self):
        b = self.b
        self.make_note("View keys")
        self.setmd("Read [the plan](https://example.com/plan) now.")
        b.click(".nbody a")
        b.wait("!!document.querySelector('.linkpop.view')", 5)
        b.eval("document.querySelector('.nbody').cxed.focus()")
        b.key("Tab")
        self.assertTrue(b.eval("document.querySelector('.linkpop').contains(document.activeElement)"), "Tab from the text moves into the popover")
        self.assertEqual(b.eval("document.activeElement.dataset.lk"), "open")
        b.key("Escape")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertTrue(b.eval("document.activeElement===document.querySelector('.nbody')"))

    # ---- an existing link -----------------------------------------------------------------------------------------------------------

    def test_a_click_shows_the_popover_and_never_leaves_the_page(self):
        b = self.b
        self.make_note("Click")
        self.setmd("Read [the plan](https://example.com/plan) now.")
        here = b.eval("location.href")
        b.click(".nbody a")
        b.wait("!!document.querySelector('.linkpop.view')", 5)
        b.pump(0.3)
        self.assertEqual(b.eval("location.href"), here)
        self.assertEqual(b.eval("document.querySelectorAll('.linkpop').length"), 1)
        o = b.eval("(()=>{ const a=document.querySelector('.linkpop a[data-lk=open]'); return {href:a.getAttribute('href'),target:a.target,rel:a.rel,text:a.textContent}; })()")
        self.assertEqual(o["href"], "https://example.com/plan")
        self.assertEqual(o["target"], "_blank")
        self.assertEqual(sorted(o["rel"].split()), ["noopener", "noreferrer"])
        self.assertEqual(b.eval("document.querySelector('.linkpop .linkaddr').textContent"), "https://example.com/plan")
        self.assertEqual(b.eval("[...document.querySelectorAll('.linkpop button')].map(x=>x.textContent)"), ["Edit", "Remove"])
        # the link in the text itself is never an anchor that a click follows
        self.assertEqual(b.eval("document.querySelector('.nbody a').dataset.lk||null"), None)

    def test_remove_keeps_the_words(self):
        b = self.b
        self.make_note("Remove")
        self.setmd("Read [the plan](https://example.com/plan) now.")
        b.click(".nbody a")
        b.wait("!!document.querySelector('.linkpop.view')", 5)
        b.click(".linkpop [data-lk=remove]")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 0)
        self.assertIn("Read the plan now.", self.value())

    def test_edit_changes_the_words_and_the_address(self):
        b = self.b
        self.make_note("Edit")
        self.setmd("Read [the plan](https://example.com/plan) now.")
        b.click(".nbody a")
        b.wait("!!document.querySelector('.linkpop.view')", 5)
        b.click(".linkpop [data-lk=edit]")
        b.wait("!!document.querySelector('.linkpop.form')", 5)
        self.assertEqual(b.eval("[...document.querySelectorAll('.linkpop input')].map(i=>i.value)"), ["the plan", "https://example.com/plan"])
        self.assertEqual(b.eval("[...document.querySelectorAll('.linkpop button, .linkpop a')].map(x=>x.textContent)"), ["Apply", "Remove link", "Open ↗", "Cancel"])
        b.eval("document.querySelector('.linkpop input[id$=\"-t\"]').select()")
        b.type("the new plan")
        b.key("Tab")
        b.type("https://example.com/new")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertIn("Read [the new plan](https://example.com/new) now.", self.value())
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 1)

    def test_the_shortcut_edits_the_link_under_the_cursor(self):
        b = self.b
        self.make_note("Edit key")
        self.setmd("Read [the plan](https://example.com/plan) now.")
        self.select("plan")
        b.eval("document.querySelector('.nbody').cxed.editor.commands.setTextSelection(%d)" % (self.select("the plan") + 4))
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop.form')", 5)
        self.assertEqual(b.eval("document.querySelector('.linkpop input[id$=\"-a\"]').value"), "https://example.com/plan")
        b.eval("document.querySelector('.linkpop input[id$=\"-a\"]').select()")
        b.type("pmo@example.com")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertIn("Read [the plan](mailto:pmo@example.com) now.", self.value())

    # ---- paste ------------------------------------------------------------------------------------------------------------------------

    def test_a_pasted_address_over_selected_words_links_them_with_an_undo_toast(self):
        b = self.b
        self.make_note("Paste over")
        self.setmd("Agree the data sharing agreement soon.")
        self.select("data sharing agreement")
        self.assertTrue(self.paste("https://example.com/dsa"))
        self.assertIn("Agree the [data sharing agreement](https://example.com/dsa) soon.", self.value())
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), "Linked")
        self.assertEqual(b.eval("document.getElementById('snackU').textContent"), "Undo")
        b.click("#snackU")
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 0)
        self.assertIn("Agree the data sharing agreement soon.", self.value())

    def test_a_pasted_bare_address_becomes_a_link_with_an_undo_toast(self):
        b = self.b
        self.make_note("Paste bare")
        b.type("Source: ")
        self.assertTrue(self.paste("  https://example.com/a_(b)  "))
        self.assertEqual(b.eval("[...document.querySelectorAll('.nbody a')].map(a=>[a.getAttribute('href'),a.textContent])"), [["https://example.com/a_(b)"] * 2])
        self.assertIn("Source: https://example.com/a_(b)", self.value(), "an address that is its own text is written bare")
        v = self.value()
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), "Pasted as a link")
        b.click("#snackU")
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 0)
        self.assertNotIn("example.com", self.value())
        self.setmd(v)
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 1, "and a bare address is a link again when the text is opened")
        self.setmd("")
        # typing after a pasted link is outside it
        self.paste("mailto:pmo@example.com")
        b.type(" after")
        self.assertIn("(mailto:pmo@example.com) after", self.value())

    def test_a_refused_or_ordinary_paste_is_plain_text_never_a_link(self):
        b = self.b
        self.make_note("Paste plain")
        for text in ("javascript:alert(1)", "data:text/html,x", "just some words"):
            self.paste(text)
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 0)
        self.assertIn("javascript:alert(1)", b.eval("document.querySelector('.nbody').textContent"), "a refused address is pasted as the text it is")
        # an address inside a longer text may be linked by the editor's own autolink, and then only if the one check allows it
        self.paste("two words https://example.com and more ")
        self.assertTrue(b.eval("[...document.querySelectorAll('.nbody a')].every(a=>linkUrl(a.getAttribute('href')))"))
        # a link made of rich text is judged by the same check
        self.paste(html='<p>see <a href="javascript:alert(1)">evil</a> and <a href="https://example.com/ok">fine</a></p>', text=None)
        b.pump(0.3)
        self.assertTrue(b.eval("[...document.querySelectorAll('.nbody a')].map(a=>a.getAttribute('href')).includes('https://example.com/ok')"))
        self.assertTrue(b.eval("[...document.querySelectorAll('.nbody a')].every(a=>linkUrl(a.getAttribute('href')))"))
        self.assertIn("evil", b.eval("document.querySelector('.nbody').textContent"))
        self.assertNotIn("](javascript", self.value().lower())

    # ---- Current state, the markdown, the AI bar, 900 px -----------------------------------------------------------------------------

    def open_current(self, state):
        b = self.b
        mem = self.memory()
        text = mem.read_text(encoding="utf-8")
        mem.write_text(re.sub(r"(## Current state\n).*?(?=\n## |\Z)", lambda m: m.group(1) + f"\n{state}\n", text, flags=re.S), encoding="utf-8")
        self.v.run(script="build_dashboard.py")
        b.reload("typeof go==='function' && LIVE")
        b.eval("go('cockpit','ABC')")
        b.wait("document.querySelector('#v-cockpit .curcard [data-edcur]')")
        b.click("#v-cockpit .curcard [data-edcur]")
        b.wait("!!(document.getElementById('curEd')&&document.getElementById('curEd').cxed)")

    def test_current_state_has_the_same_link_control_and_check(self):
        b = self.b
        self.open_current("### Top\n\nRead the plan, [bad](javascript:alert(1)) and [ok](https://example.com/ok).")
        self.assertEqual(b.eval("[...document.querySelectorAll('#curEd a')].map(a=>a.getAttribute('href'))"), ["https://example.com/ok"])
        b.eval("""(()=>{ const e=document.getElementById('curEd').cxed.editor; let at=-1;
          e.state.doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf('the plan'); if(i>=0) at=pos+i; } });
          e.commands.focus(); e.commands.setTextSelection({from:at,to:at+8}); })()""")
        b.click("#v-cockpit [data-nt=link]")
        b.wait("!!document.querySelector('.linkpop')", 5)
        b.type("https://example.com/plan")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        v = b.eval("document.getElementById('curEd').cxed.value()")
        self.assertIn("### Top", v)
        self.assertIn("Read [the plan](https://example.com/plan), bad and [ok](https://example.com/ok).", v)
        self.assertNotIn("javascript", v.lower())
        b.eval("document.getElementById('curEd').cxed.setValue(document.getElementById('curEd').cxed.value())")
        b.pump(0.2)
        self.assertEqual(b.eval("[...document.querySelectorAll('#curEd a')].map(a=>a.getAttribute('href'))"), ["https://example.com/plan", "https://example.com/ok"])

    def test_the_markdown_round_trips_through_the_editor(self):
        b = self.b
        self.make_note("Round trip")
        md = ("A [plain](https://example.com/a), a [paren](https://example.com/a_(b)), a [query](https://example.com/q?x=1&y=2#z), "
              "a [mail](mailto:pmo@example.com?subject=Hello) and **[bold link](https://example.com/b)**.")
        self.setmd(md)
        self.assertEqual(self.value(), md, "untouched, it comes back as it was")
        b.eval("document.querySelector('.nbody').cxed.editor.commands.insertContentAt(1,'New ')")
        v = self.value()
        for part in ("[plain](https://example.com/a)", "[paren](https://example.com/a_(b))", "[query](https://example.com/q?x=1&y=2#z)",
                     "[mail](mailto:pmo@example.com?subject=Hello)", "[**bold link**](https://example.com/b)"):
            self.assertIn(part, v)
        # and again through a reload of the saved text
        self.setmd(v)
        self.assertEqual(b.eval("document.querySelectorAll('.nbody a').length"), 5)

    def test_the_link_form_puts_the_ai_bar_away_and_fits_at_900px(self):
        b = self.b
        for width in (1400, 900):
            b.resize(width, 1000)
            self.make_note(f"Fit {width}")
            b.type("alpha beta gamma")
            self.select("beta")
            b.pump(0.4)
            b.key("k", self.mod() | SHIFT)
            b.wait("!!document.querySelector('.linkpop')", 5)
            b.pump(0.3)
            self.assertIsNone(b.eval("document.getElementById('aiBarBox')"), "the AI bar is put away while the form is open")
            r = b.eval("(()=>{ const r=document.querySelector('.linkpop').getBoundingClientRect(); return {l:r.left,t:r.top,r:r.right,b:r.bottom,w:innerWidth,h:innerHeight}; })()")
            self.assertGreaterEqual(r["l"], 0)
            self.assertLessEqual(r["r"], r["w"])
            self.assertGreaterEqual(r["t"], 0)
            self.assertLessEqual(r["b"], r["h"])
            b.key("Escape")
            b.wait("!document.querySelector('.linkpop')", 5)


if __name__ == "__main__":
    unittest.main()

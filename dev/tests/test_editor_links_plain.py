"""#121: links in the plain-text fields, and links shown everywhere that text is shown, in a real browser against the real live server.

Run: python3 dev/tests/test_editor_links_plain.py   (needs Google Chrome; skipped otherwise)

Done when (the issue's Done-when):
- the Link control and popover are in the plain fields that hold free text (an item's update, response, reasoning, options and client
  messaging; Prep's notes and questions), using #120's ONE address validator (core/linkUrl.js): the corner button, Cmd/Ctrl+Shift+K and a
  paste (a plain field has no `/` menu); the saved value is `[words](address)`;
- an address the validator refuses is never a link, however it got there (load, set by code, a command, a paste): it stays the literal
  characters it is, and the text is written back as it came;
- a click on a link in a field never leaves the page; Open is a new tab with rel="noopener noreferrer";
- the keys and short labels (the title, Revisit, Source, Find updates' one-line boxes) have no link control;
- wherever the text is SHOWN (the Work tables, the project page, Review, Today, Draft email rich and plain, the peek's history) it reads as
  the words, a link where a link can work, and the raw `[words](address)` never shows. Every place is in PLACES below, with a hostile
  matrix run through each.
Desktop and 900 px only.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

META, SHIFT, CTRL = 4, 8, 2
REFUSED = "Only http, https and mailto addresses can be linked."
GOOD = ["https://example.com/plan", "mailto:pmo@example.com"]
BAD = ["javascript:alert(1)", "JaVaScRiPt:alert(2)", "data:text/html,x", "file:///etc/passwd", "//evil.example/x", "vbscript:msgbox(1)",
       "https://user@evil.example/x", "ftp://example.com/x", "https://example.com/<script>", "https://exa%20mple.com", "relative/path",
       "https://example.com/&#106;avascript"]
# one text holding every case: two good links, then every hostile one
MATRIX = ("See [the plan](https://example.com/plan) and [mail us](mailto:pmo@example.com) then "
          + " ".join(f"[bad{i}]({a})" for i, a in enumerate(BAD)) + ".")


def probe_js(html_expr, anchor="a.tlink"):
    """JS that parses the markup `html_expr` makes and reports what a reader would see."""
    return ("(()=>{ const t=document.createElement('div'); t.innerHTML=" + html_expr + ";"
            " const a=[...t.querySelectorAll(" + json.dumps(anchor) + ")];"
            " return { hrefs:a.map(x=>x.getAttribute('href')), targets:a.map(x=>x.getAttribute('target')), rels:a.map(x=>x.getAttribute('rel')),"
            " words:a.map(x=>x.textContent), text:t.textContent, tags:[...t.querySelectorAll('*')].filter(x=>!x.matches(" + json.dumps(anchor) + ")).map(x=>x.tagName.toLowerCase()),"
            " attrs:[...t.querySelectorAll('*')].flatMap(x=>[...x.attributes].map(y=>y.name)).filter(n=>/^on/i.test(n)) }; })()")


class Base(LiveBrowserCase):
    width, height = 1400, 1000

    @classmethod
    def load(cls, v):
        populate(v)
        v.propose("links", [
            {"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"latest_update": MATRIX}, "decision": "approved"},
            {"n": 2, "op": "update", "table": "raid", "id": "ABC-003", "changes": {"response_action": MATRIX}, "decision": "approved"},
            {"n": 3, "op": "update", "table": "decisions", "id": "ABC-D-005", "changes": {"reasoning": MATRIX, "options": MATRIX}, "decision": "approved"},
        ])
        v.run("apply")

    def mod(self):
        return META if self.b.is_mac() else CTRL

    def open(self, kind="actions", id_="ABC-A-001"):
        b = self.b
        b.eval(f"WT={kind!r}; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        b.eval(f"openRecord({kind!r},{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.3)

    def field(self, sel="#pkDesc"):
        return f"document.querySelector({sel!r}).cxed"

    def setv(self, text, sel="#pkDesc"):
        self.b.eval(f"{self.field(sel)}.setValue({json.dumps(text)})")
        self.b.pump(0.2)

    def value(self, sel="#pkDesc"):
        return self.b.eval(f"{self.field(sel)}.value()")

    def select(self, word, sel="#pkDesc"):
        at = self.b.eval("(w=>{ const h=document.querySelector(%s).cxed, e=h.editor; let at=-1;"
                         " e.state.doc.descendants((n,pos)=>{ if(at<0&&n.isText){ const i=n.text.indexOf(w); if(i>=0) at=pos+i; } });"
                         " e.commands.focus(); e.commands.setTextSelection({from:at,to:at+w.length}); return at; })(%s)" % (json.dumps(sel), json.dumps(word)))
        self.assertGreater(at, 0, f"{word!r} is in the field")
        self.b.wait(f"document.activeElement===document.querySelector({sel!r})", 5)
        return at

    def popup(self):
        return self.b.eval("(()=>{ const p=document.querySelector('.linkpop'); return p?{cls:p.className,role:p.getAttribute('role'),label:p.getAttribute('aria-label'),"
                           "err:(p.querySelector('.linkerr')||{}).textContent||''}:null; })()")

    def paste(self, text, sel="#pkDesc", html=None):
        js = ("(t,h)=>{ const e=document.querySelector(%s).cxed.editor, dt=new DataTransfer(); dt.setData('text/plain',t); if(h) dt.setData('text/html',h);"
              " const ev=new ClipboardEvent('paste',{clipboardData:dt,bubbles:true,cancelable:true}); e.view.dom.dispatchEvent(ev); return ev.defaultPrevented; }" % json.dumps(sel))
        got = self.b.eval(f"({js})({json.dumps(text)},{json.dumps(html)})")
        self.b.pump(0.2)
        return got

    def hrefs(self, sel="#pkDesc"):
        return self.b.eval(f"[...document.querySelector({sel!r}).querySelectorAll('a')].map(a=>a.getAttribute('href'))")

    def staged_values(self):
        """What the dashboard staged for the item, field by field (the proposals it wrote)."""
        out = {}
        for p in sorted((self.v.root / "system/staging").glob("proposed-*dashboard*.json")):
            for it in json.loads(p.read_text(encoding="utf-8")).get("items", []):
                out.update(it.get("changes") or {})
        return out


class Editor(Base):
    """The link control in a plain field."""

    def test_a_link_is_read_and_written_as_words_and_address(self):
        b = self.b
        self.open()                                   # ABC-A-001's latest update is the matrix: two good links and every hostile one
        self.assertEqual(self.hrefs(), GOOD)
        self.assertTrue(b.eval(f"{self.field()}.links"))
        shown = b.eval("document.querySelector('#pkDesc').innerText")
        self.assertTrue(shown.startswith("See the plan and mail us then "), "the field shows the words, never the brackets")
        self.assertNotIn("[the plan]", shown)
        self.assertEqual(self.value(), MATRIX, "an untouched text is written back as it came")
        self.assertFalse(b.eval(f"{self.field()}.touched()"))
        b.eval(f"{self.field()}.editor.commands.insertContentAt(1,'A ')")
        self.assertEqual(self.value(), "A " + MATRIX, "touched: the same text, with the change")
        self.assertEqual(self.hrefs(), GOOD)

    def test_brackets_and_backslashes_in_the_words_survive(self):
        b = self.b
        self.open()
        self.setv("x")
        b.eval(f"{self.field()}.editor.chain().focus().insertContent({{type:'text',text:'v[1] a\\\\b',marks:[{{type:'link',attrs:{{href:'https://example.com/a_(b)'}}}}]}}).run()")
        v = self.value()
        self.assertIn("[v\\[1\\] a\\\\b](https://example.com/a_(b))", v)
        self.setv(v)
        self.assertEqual(b.eval("document.querySelector('#pkDesc a').innerText"), "v[1] a\\b")
        self.assertEqual(self.hrefs(), ["https://example.com/a_(b)"])
        self.assertEqual(self.value(), v, "and the written form reads back to the same text")

    def test_a_hostile_address_is_the_literal_text_it_is_and_is_written_back_as_it_came(self):
        b = self.b
        self.open()
        shown = b.eval("document.querySelector('#pkDesc').innerText")
        for i, a in enumerate(BAD):
            self.assertIn(f"[bad{i}]({a})", shown, a)
        b.eval(f"{self.field()}.editor.commands.insertContentAt(1,'x')")
        v = self.value()
        for i, a in enumerate(BAD):
            self.assertIn(f"[bad{i}]({a})", v, a)
        self.assertEqual(self.hrefs(), GOOD)

    def test_a_command_or_a_paste_cannot_make_a_hostile_link(self):
        b = self.b
        self.open()
        self.setv("Some words to link here.")
        self.select("words")
        b.eval(f"{self.field()}.editor.chain().setMark('link',{{href:'javascript:alert(1)'}}).run()")
        b.pump(0.2)
        self.assertEqual(self.hrefs(), [])
        b.eval(f"{self.field()}.editor.chain().insertContent({{type:'text',text:'sneaky',marks:[{{type:'link',attrs:{{href:'data:text/html,x'}}}}]}}).run()")
        b.pump(0.2)
        self.assertEqual(self.hrefs(), [])
        self.assertNotIn("data:", self.value())
        self.assertIn("sneaky", b.eval("document.querySelector('#pkDesc').innerText"))
        # pasted rich text with a hostile anchor, and a pasted hostile address
        self.paste("evil", html='<a href="javascript:alert(1)">evil</a> and <a href="https://example.com/ok">ok</a>')
        self.assertEqual(self.hrefs(), ["https://example.com/ok"])
        self.paste("javascript:alert(1)")
        self.assertEqual(self.hrefs(), ["https://example.com/ok"], "a refused address pastes as the plain text it is")
        self.assertIn("javascript:alert(1)", b.eval("document.querySelector('#pkDesc').innerText"))

    def test_the_corner_button_the_shortcut_and_a_paste_are_the_ways_in(self):
        b = self.b
        self.open()
        self.setv("see the plan today")
        self.assertEqual(b.eval("document.querySelectorAll('.linkcorner').length"), 0, "the corner button shows while the cursor is in the field")
        b.click("#pkDesc")
        b.wait("!!document.querySelector('.linkcorner')", 5)
        c = b.eval("(()=>{ const c=document.querySelector('.linkcorner'), f=document.querySelector('#pkDesc').getBoundingClientRect(), r=c.getBoundingClientRect();"
                   " return {label:c.getAttribute('aria-label'), inside:r.right<=f.right+1&&r.left>=f.left&&r.top>=f.top-1&&r.bottom<=f.bottom+1}; })()")
        self.assertIn("link", c["label"].lower())
        self.assertTrue(c["inside"], "in the field's corner")
        # 1. the corner button
        self.select("the plan")
        b.click(".linkcorner")
        b.wait("!!document.querySelector('.linkpop')", 5)
        p = self.popup()
        self.assertEqual((p["role"], p["label"]), ("dialog", "Link"))
        self.assertEqual(b.eval("document.querySelector('.linkpop input').value"), "the plan")
        b.type("example.com/plan")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertEqual(self.value(), "see [the plan](https://example.com/plan) today")
        # 2. the shortcut, with nothing selected: the address is its own text
        b.eval(f"{self.field()}.editor.commands.focus('end')")
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        self.assertFalse(b.eval("document.getElementById('cmdk').open"), "Cmd+Shift+K in a field is the link, not the palette")
        b.type("pmo@example.com")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertEqual(self.value(), "see [the plan](https://example.com/plan) today[mailto:pmo@example.com](mailto:pmo@example.com)")
        # 3. a paste over selected words
        self.setv("read the notes now")
        self.select("the notes")
        self.assertTrue(self.paste("https://example.com/notes"))
        b.wait("!!document.querySelector('.toast, #snack, .snack')", 5)
        self.assertEqual(self.value(), "read [the notes](https://example.com/notes) now")
        # and a hostile address is refused with a reason, nothing inserted
        self.setv("bad link here")
        for hostile in ("javascript:alert(1)", "data:text/html,x", "file:///etc/passwd", "//evil.example", "JaVaScRiPt:alert(1)"):
            self.select("link")
            b.key("k", self.mod() | SHIFT)
            b.wait("!!document.querySelector('.linkpop')", 5)
            b.eval("document.querySelector('.linkpop input[id$=\"-a\"]').select()")
            b.type(hostile)
            b.key("Enter")
            b.pump(0.2)
            self.assertEqual(self.popup()["err"], REFUSED, hostile)
            self.assertEqual(self.value(), "bad link here", f"{hostile}: nothing is inserted")
            b.key("Escape")
            b.wait("!document.querySelector('.linkpop')", 5)

    def test_the_corner_button_goes_when_focus_leaves_the_link_form_for_elsewhere(self):
        b = self.b
        self.open()
        self.setv("see the plan today")
        b.click("#pkDesc")
        b.wait("!!document.querySelector('.linkcorner')", 5)
        self.select("the plan")
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        self.assertEqual(b.eval("document.querySelectorAll('.linkcorner').length"), 1, "the corner button stays while the form is open")
        b.eval("(()=>{ const i=document.createElement('input'); i.id='elsewhere'; document.body.appendChild(i); i.focus(); })()")
        b.pump(0.3)
        self.assertEqual(b.eval("document.querySelectorAll('.linkcorner').length"), 0, "focus went elsewhere: the corner button is put away")
        b.eval("document.getElementById('elsewhere').remove()")

    def test_the_link_is_staged_as_words_and_address(self):
        b = self.b
        self.open()
        b.click("#pkDesc")
        b.type("Plan is here")
        self.select("Plan")
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        b.type("https://example.com/plan")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        b.eval("document.activeElement.blur()")
        b.wait("PKS.length>=1", 15)
        b.pump(0.5)
        self.assertIn("[Plan](https://example.com/plan) is here", self.staged_values().get("latest_update", ""))

    def test_a_click_on_a_link_shows_its_popover_and_never_leaves_the_page(self):
        b = self.b
        self.open("actions", "ABC-A-002")
        b.click("#pkDesc")
        b.type("Read the plan now.")
        self.select("the plan")
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        b.type("https://example.com/plan")
        b.key("Enter")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertEqual(self.value(), "Read [the plan](https://example.com/plan) now.")
        here = b.eval("location.href")
        b.click("#pkDesc a")
        b.wait("!!document.querySelector('.linkpop.view')", 5)
        b.pump(0.3)
        self.assertEqual(b.eval("location.href"), here)
        o = b.eval("(()=>{ const a=document.querySelector('.linkpop a[data-lk=open]'); return {href:a.getAttribute('href'),target:a.target,rel:a.rel}; })()")
        self.assertEqual((o["href"], o["target"]), ("https://example.com/plan", "_blank"))
        self.assertEqual(sorted(o["rel"].split()), ["noopener", "noreferrer"])
        prevented = b.eval("(()=>{ const a=document.querySelector('#pkDesc a'); const e=new MouseEvent('click',{bubbles:true,cancelable:true,ctrlKey:true}); a.dispatchEvent(e); return e.defaultPrevented; })()")
        self.assertTrue(prevented, "even a modified click in the field is the editor's, never a navigation")
        b.click(".linkpop [data-lk=remove]")
        b.wait("!document.querySelector('.linkpop')", 5)
        self.assertEqual(self.value(), "Read the plan now.", "Remove keeps the words")

    def test_keys_and_short_labels_have_no_link_control(self):
        b = self.b
        self.open()
        for sel in ("#pkTitle",):
            self.assertFalse(b.eval(f"!!{self.field(sel)}.links"), sel)
            b.click(sel)
            b.pump(0.3)
            self.assertEqual(b.eval("document.querySelectorAll('.linkcorner').length"), 0, f"{sel}: no corner button")
            self.paste("https://example.com/title", sel)
            self.assertEqual(self.hrefs(sel), [], f"{sel}: a paste stays text")
            b.key("k", self.mod() | SHIFT)
            b.pump(0.3)
            self.assertIsNone(self.popup(), f"{sel}: no link form")
        self.assertTrue(b.eval(f"!!{self.field('#pkDesc')}.links"), "the longer text fields have it")
        b.eval("document.activeElement.blur()")
        b.pump(0.2)
        # Details: Revisit (a short label) has none; Options considered (free text) has
        self.open("decisions", "ABC-D-005")
        b.eval("(()=>{ const t=document.getElementById('pkDetT'); if(t.getAttribute('aria-expanded')!=='true') t.click(); })()")
        b.wait("!!document.querySelector('#pkDet [data-pkf=opts]')", 5)
        self.assertFalse(b.eval("!!document.querySelector('#pkDet [data-pkf=revisit]').cxed.links"))
        self.assertTrue(b.eval("!!document.querySelector('#pkDet [data-pkf=opts]').cxed.links"))
        self.assertEqual(b.eval("document.querySelector('#pkDet [data-pkf=opts]').cxed.value()"), MATRIX)


def cut(markup):
    """The part of a row's markup that is the matrix (from its first word to its last), so the row's own links and chips are not judged."""
    end = "avascript)."
    return markup[markup.index("See "):markup.rindex(end) + len(end)]


class Places(Base):
    """Every place the text is shown (PLACES), each given the hostile matrix: the words, a link only for a good address, never the brackets."""

    def check(self, got, where, words=("the plan", "mail us"), strict_tags=True):
        self.assertEqual(got["hrefs"], GOOD, where)
        self.assertEqual(got["words"], list(words), where)
        self.assertEqual(got["targets"], ["_blank"] * 2, where)
        for r in got["rels"]:
            self.assertEqual(sorted((r or "").split()), ["noopener", "noreferrer"], where)
        if strict_tags:
            self.assertEqual(got["tags"], [], f"{where}: nothing but anchors was made")
        self.assertEqual(got["attrs"], [], where)
        for i, a in enumerate(BAD):
            self.assertIn(f"[bad{i}]({a})", got["text"], f"{where}: {a} stays the literal text it is")
        self.assertNotIn("[the plan]", got["text"], where)
        self.assertNotIn("](https://example.com/plan)", got["text"], where)
        self.assertNotIn("[mail us]", got["text"], where)

    def test_work_table_update_and_response(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        row = b.eval("(()=>{ const r=[...document.querySelectorAll('#workTbl tbody tr[data-row]')].find(t=>t.textContent.includes('ABC-A-001')); return r?r.querySelector('td.title .x').innerHTML:null; })()")
        self.assertIsNotNone(row)
        self.check(b.eval(probe_js(json.dumps(cut(row)))), "Work, actions: the latest update under the title")
        b.eval("WT='raid'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        cell = b.eval("(()=>{ const r=[...document.querySelectorAll('#workTbl tbody tr[data-row]')].find(t=>t.textContent.includes('ABC-003')); const c=r&&r.querySelector('td[data-f=resp]'); return c?c.innerHTML:null; })()")
        self.assertIsNotNone(cell, "Response is one of a risk's default columns")
        self.check(b.eval(probe_js(json.dumps(cut(cell)))), "Work, risks and issues: the response")

    def test_the_project_page_risk_card(self):
        b = self.b
        b.eval("go('cockpit','ABC')")
        b.wait("!!document.querySelector('.rkrow .rk-txt')", 10)
        cell = b.eval("[...document.querySelectorAll('.rkrow')].map(r=>r.querySelector('.rk-txt').innerHTML).find(h=>h.includes('example.com/plan'))")
        self.assertIsNotNone(cell, "the response is on the project page")
        self.check(b.eval(probe_js(json.dumps(cut(cell)))), "Project page, top risks")

    def test_review_detail_draft_email_and_the_peek_history(self):
        b = self.b
        # Review's line for a proposed risk
        h = b.eval("revDetail({kind:'raid',rec:{type:'Risk',o:'Sara Example',imp:'High',lik:'High',resp:%s}})" % json.dumps(MATRIX))
        self.check(b.eval(probe_js(json.dumps(cut(h)))), "Review, a proposed risk's response")
        # Draft email: the rich copy is anchors with the colour written in; the plain copy reads "words (address)"
        item = "{k:'raid',id:'ABC-003',type:'Risk',t:'Data',due:null,pr:'High',resp:%s,upd:%s,client:false,src:'',cm:''}" % (json.dumps(MATRIX), json.dumps(MATRIX))
        rich = b.eval("deRowHtml(%s,{today:TODAY,includeUpdate:true})" % item)
        got = b.eval(probe_js(json.dumps(rich), anchor="a"))
        self.assertEqual(got["hrefs"], GOOD + GOOD, "the response and the latest update, each with its two good links")
        for i, a in enumerate(BAD):
            self.assertIn(f"[bad{i}]({a})", got["text"], a)
        self.assertNotIn("[the plan]", got["text"])
        self.assertEqual(got["attrs"], [])
        self.assertIn("style=", rich, "the colour is written in: a mail program drops classes")
        # #183: an email's anchor is href and style only (Outlook's create-draft takes no more); a mail program opens it in a new window anyway
        self.assertEqual(got["targets"], [None] * 4)
        self.assertEqual(got["rels"], [None] * 4)
        self.assertNotIn("<span", rich)
        plain = b.eval("deTextRows([%s],{today:TODAY,includeUpdate:true})" % item)
        plain = "\n".join(plain) if isinstance(plain, list) else plain
        self.assertIn("the plan (https://example.com/plan)", plain)
        self.assertIn("mail us (pmo@example.com)", plain)
        self.assertNotIn("[the plan]", plain)
        for i, a in enumerate(BAD):
            self.assertIn(f"[bad{i}]({a})", plain)
        # the peek's history and the brief
        self.assertEqual(b.eval("pkShort('a [the plan](https://example.com/plan) b')"), "a the plan b")

    def test_today_shows_the_words_where_the_text_is_cut(self):
        b = self.b
        words = b.eval("linkWords(%s)" % json.dumps(MATRIX))
        self.assertTrue(words.startswith("See the plan and mail us then [bad0](javascript:alert(1))"))
        self.assertEqual(b.eval("linkWithAddress('x [w](https://example.com/a) [m](mailto:a@example.com)')"), "x w (https://example.com/a) m (a@example.com)")

    def test_the_link_text_functions_agree_with_the_one_validator(self):
        b = self.b
        for a in GOOD + ["HTTPS://Example.com/Path"]:
            self.assertEqual(b.eval("linkSegments('[w](%s)')" % a)[0].get("href"), b.eval("linkUrl(%s)" % json.dumps(a)))
        for a in BAD:
            self.assertEqual(b.eval("linkSegments(%s).filter(s=>s.href).length" % json.dumps(f"[w]({a})")), 0, a)
        self.assertEqual(b.eval("linkWrite('x]','javascript:alert(1)')"), None)
        self.assertEqual(b.eval("linkWrite('a [b]','https://example.com/x')"), "[a \\[b\\]](https://example.com/x)")

    def test_a_click_on_a_shown_link_opens_it_and_does_nothing_else(self):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl a.tlink')", 10)
        b.click('#wdens [data-dens="cmf"]')
        b.wait("document.getElementById('workWrap').classList.contains('cmf')")
        b.pump(0.5)
        b.wait("(()=>{ const a=[...document.querySelectorAll('#workTbl a.tlink')].find(a=>{ const r=a.getBoundingClientRect(); "
               "const x=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2); return x&&x.closest('a.tlink')===a }); "
               "if(a) a.classList.add('__shown'); return !!a })()", 5)
        before = b.eval("document.getElementById('panel').classList.contains('on')")
        # a real click on the link: the row it sits in must not also open the peek, and the link itself is the only thing that happens
        b.eval("window.__saw=0; window.__links=0; "
               "window.addEventListener('click',e=>{ if(e.target.closest('a.tlink')){ window.__saw++; e.preventDefault(); } },true); "   # the test stops the new tab opening
               "document.addEventListener('click',e=>{ if(e.target.closest('a.tlink')) window.__links++; }); 0")
        # #241: in the compact list the links beside a long title are clipped away; the comfortable list shows them, so click there
        b.click("#workTbl a.tlink.__shown", exact=True)
        b.pump(0.4)
        self.assertEqual(b.eval("window.__saw"), 1, "the click reached the link")
        self.assertEqual(b.eval("window.__links"), 0, "and no handler of the page's own after it (the row, a card, a button)")
        self.assertEqual(b.eval("document.getElementById('panel').classList.contains('on')"), before, "the row did not open the peek")


    def test_the_python_check_is_never_looser_than_the_one_validator(self):
        """system/scripts/linktext.py cannot call JavaScript, so it holds the same rules again for the reports, exports and search. It may only be
        stricter: every address it accepts, core/linkUrl.js accepts too, and returns the same text."""
        from test_editor_links import ACCEPT, REFUSE
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import linktext
        cands = [c for c in list(ACCEPT) + REFUSE + GOOD + BAD + ["https://exa_mple.com", "http://1.2.3.4/x", "http://999.1.1.1/x", "https://[::1]/x",
                 "https://[:::]/x", "https://example.com:65535/x", "https://example.com:65536/x", "https://example.com:0/x", "mailto:a%40b.co", "mailto:a@b.co?subject=x",
                 "http://-a.com", "http://a..com", "http://a.b-.com", "https://münchen.example/x", "HTTP://EXAMPLE.COM"] if isinstance(c, str)]
        theirs = self.b.eval("(c=>c.map(s=>linkUrl(s)))(%s)" % json.dumps(cands))
        ours = [linktext.valid_address(c) for c in cands]
        looser = [(c, o, t) for c, o, t in zip(cands, ours, theirs) if o is not None and o != t]
        self.assertEqual(looser, [], "the Python check accepted what the dashboard's refuses (or wrote it differently)")
        for a, want in ACCEPT.items():
            self.assertEqual(linktext.valid_address(a), want, a)
        self.assertEqual([c for c in REFUSE if isinstance(c, str) and linktext.valid_address(c) is not None], [])


class Plain900(Base):
    width, height = 900, 800

    def test_the_field_and_its_corner_button_at_900px(self):
        b = self.b
        self.open()
        b.click("#pkDesc")
        b.wait("!!document.querySelector('.linkcorner')", 5)
        r = b.eval("(()=>{ const c=document.querySelector('.linkcorner').getBoundingClientRect(); return {l:c.left,r:c.right,t:c.top,b:c.bottom,w:document.documentElement.clientWidth,h:innerHeight}; })()")
        self.assertTrue(0 <= r["l"] and r["r"] <= r["w"] and 0 <= r["t"] and r["b"] <= r["h"], "the button is on screen")
        b.key("k", self.mod() | SHIFT)
        b.wait("!!document.querySelector('.linkpop')", 5)
        box = b.eval("(()=>{ const p=document.querySelector('.linkpop').getBoundingClientRect(); return {l:p.left,r:p.right,w:document.documentElement.clientWidth}; })()")
        self.assertTrue(box["l"] >= 0 and box["r"] <= box["w"])


if __name__ == "__main__":
    unittest.main()

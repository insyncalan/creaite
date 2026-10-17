"""BL-301 E (v20-find-updates): the Find updates panel (components/notes/FindUpdates.jsx), mounted on a fixture note page of its own:
the note's lines (each with data-p) on the left, the panel in the right-hand column, as the Notes tab (part B) will host it.

- the mockup's catch-up note gives the mockup's rows, grouped, with numbered markers matching the note's lines; hovering one
  highlights the other;
- the bulk rule: new risks, milestone moves and memory lines unticked; a hedged milestone move locked; routine rows ticked;
- clicking a row opens it in the peek's layout to edit it first; Esc closes it and focus returns;
- Apply writes the ticked rows in one apply; Undo in the snackbar reverses all of it;
- Save for later leaves them pending in Review;
- a second run skips sent lines; a confidential note asks first; text is escaped; nothing scrolls sideways at 320 px.

Run: python3 dev/tests/test_find_updates_panel.py   (needs Google Chrome; skipped otherwise)
The real live server in a throwaway vault; Claude is a stand-in (notes_find_fixture.FAKE), so no model is called.
"""
import json
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
import notes_find_fixture as fx  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

import notes  # noqa: E402

LINES = notes.paragraphs(notes.parse(fx.NOTE_TEXT)[1])

MOUNT = """(lines=>{ document.getElementById('fuFix')?.remove(); const box=document.createElement('div'); box.id='fuFix';
  box.style.cssText='display:grid;grid-template-columns:minmax(0,1fr) minmax(0,400px);gap:16px;padding:16px;background:var(--bg)';
  const doc=document.createElement('article'); doc.id='fuNote'; for(const [n,t] of lines){ const p=document.createElement('p'); p.dataset.p=n;
  p.textContent=t; doc.append(p); } const col=document.createElement('div'); col.id='fuCol'; box.append(doc,col);
  document.body.prepend(box); window.__fuClosed=0;
  window.__fu=mountFindUpdates(%s, col, {noteEl:doc, onClose:()=>{ window.__fuClosed++; }}); return true; })(%s)"""


class Panel(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        fx.load(v)
        cls.fake = fx.install(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake), "CREAITE_NOW": fx.NOW}

    def mount(self, path=fx.NOTE, lines=None):
        b = self.b
        b.eval(MOUNT % (json.dumps(path), json.dumps(lines or LINES)))
        b.wait("['ready','none','error','ask'].includes(fuState.value)", 40)

    def db(self, sql):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            return con.execute(sql).fetchall()

    def test_the_mockup_rows_grouped_with_markers_and_the_bulk_rule(self):
        b = self.mount() or self.b
        groups = b.eval("[...document.querySelectorAll('#fuCol .fu-g')].map(x=>x.textContent)")
        self.assertEqual(groups, ["New", "Updates to existing items", "Milestones", "Project information"])
        self.assertEqual(b.eval("document.querySelectorAll('#fuCol .fu-r').length"), 8)
        self.assertEqual(b.eval("document.querySelectorAll('#fuCol .fu-tick:checked').length"), 5)
        self.assertEqual(b.eval("document.getElementById('fuApply').textContent"), "Apply 5 changes")
        self.assertIn("8 found · 5 ticked · 1 line left as a note", b.eval("document.querySelector('#fuCol .fu-sum').textContent"))
        # markers: each line that gave a change is numbered, matching its rows; the last line has none
        marks = b.eval("[...document.querySelectorAll('#fuNote [data-p]')].map(p=>p.getAttribute('data-fu-mk'))")
        self.assertEqual(marks, ["1", "2", "3", "4", "5", "6", None])
        row_marks = b.eval("[...document.querySelectorAll('#fuCol .fu-r')].map(r=>[r.dataset.p, r.querySelector('.fu-mk').textContent])")
        self.assertTrue(all(m == f"Line {p}" for p, m in row_marks), row_marks)
        risk = "[...document.querySelectorAll('#fuCol .fu-r')].find(r=>r.textContent.includes('Test data refresh'))"
        self.assertFalse(b.eval(f"{risk}.querySelector('.fu-tick').checked"))
        ms = "[...document.querySelectorAll('#fuCol .fu-r')].find(r=>r.textContent.includes('Phase 1 go-live'))"
        self.assertEqual(b.eval(f"[{ms}.querySelector('.fu-tick').checked, {ms}.querySelector('.fu-tick').disabled]"), [False, True])
        self.assertIn("Tentative", b.eval(f"{ms}.textContent"))
        upd = b.eval("document.querySelector('#fuCol .fu-r[data-p=\"1\"] .fu-ch').textContent")
        self.assertTrue(upd.startswith("Due 16-10-2026") and upd.endswith("20-10-2026"), upd)
        # hovering a row highlights its line, and hovering a line highlights its rows
        b.eval(f"{risk}.dispatchEvent(new MouseEvent('mouseenter'))")
        b.wait("document.querySelector('#fuNote [data-p=\"5\"]').hasAttribute('data-fu-hl')")
        b.eval("document.querySelector('#fuNote [data-p=\"3\"]').dispatchEvent(new MouseEvent('mouseover',{bubbles:true}))")
        b.wait("document.querySelector('#fuCol .fu-r[data-p=\"3\"]').classList.contains('hl')")
        names = b.eval("[...document.querySelectorAll('#fuCol .fu-tick')].map(c=>c.getAttribute('aria-label'))")
        self.assertTrue(all(n.startswith("Include: ") for n in names), names)
        self.assertEqual(b.errors, [])

    def test_a_row_opens_in_the_peek_layout_to_edit_it_first(self):
        b = self.mount() or self.b
        row = "[...document.querySelectorAll('#fuCol .fu-r')].find(r=>r.textContent.includes('Book a 30-minute'))"
        b.eval(f"{row}.querySelector('.fu-open').click()")
        b.wait(f"{row}.querySelector('.fu-peek')")
        self.assertEqual(b.eval(f"{row}.querySelector('.fu-open').getAttribute('aria-expanded')"), "true")
        labels = b.eval(f"[...{row}.querySelectorAll('.fu-fields dt')].map(x=>x.textContent)")
        self.assertEqual(labels, ["Title", "Owner", "Due", "Priority"])
        due = f"{row}.querySelector('.fu-fields input[placeholder=\"DD-MM-YYYY\"]')"
        self.assertEqual(b.eval(f"{due}.value"), "19-10-2026")
        b.eval(f"const i={due}; i.value='21-10-2026'; i.dispatchEvent(new Event('change',{{bubbles:true}}))")
        self.assertEqual(b.eval("fuRows.value.find(r=>r.text.startsWith('Book')).item.values.due_date"), "2026-10-21")
        b.eval(f"{due}.focus()")
        b.key("Escape")
        b.wait(f"!{row}.querySelector('.fu-peek')")
        self.assertTrue(b.eval(f"document.activeElement==={row}.querySelector('.fu-open')"))
        self.assertEqual(b.errors, [])

    def test_apply_writes_the_ticked_rows_in_one_apply_and_undo_reverses_it(self):
        b = self.mount() or self.b
        before = self.db("SELECT COUNT(*) FROM actions")[0][0]
        b.click("#fuApply")
        b.wait("fuState.value==='done' || fuRows.value.length===3", 40)
        b.wait("document.getElementById('snack').classList.contains('on')")
        self.assertIn("5 changes applied to Falcon Data Platform", b.eval("document.getElementById('snackT').textContent"))
        self.assertEqual(self.db("SELECT due_date FROM actions WHERE id='FAL-A-002'")[0][0], "2026-10-20")
        self.assertEqual(self.db("SELECT status FROM actions WHERE id='FAL-A-001'")[0][0], "Closed")
        self.assertEqual(self.db("SELECT COUNT(*) FROM actions")[0][0], before + 2)
        self.assertEqual(self.db("SELECT forecast_date FROM milestones")[0][0], "2026-10-30")     # hedged: never moved
        applies = self.db("SELECT COUNT(*) FROM applies WHERE undone_at IS NULL")[0][0]
        self.assertEqual(self.db("SELECT COUNT(DISTINCT apply_id) FROM change_log WHERE apply_id=(SELECT MAX(apply_id) FROM applies)")[0][0], 1)
        sent = json.loads((self.v.root / "system/staging/notes-sent.json").read_text())["notes"][fx.NOTE]
        self.assertEqual(sorted(r["p"] for r in sent), [1, 2, 3, 4, 6])
        b.click("#snackU")
        b.wait("fuRows.value.length===8", 30)
        self.assertEqual(self.db("SELECT due_date FROM actions WHERE id='FAL-A-002'")[0][0], "2026-10-16")
        self.assertEqual(self.db("SELECT COUNT(*) FROM actions")[0][0], before)
        self.assertEqual(self.db("SELECT COUNT(*) FROM applies WHERE undone_at IS NULL")[0][0], applies - 1)
        self.assertFalse((self.v.root / "system/staging/notes-sent.json").exists() and
                         fx.NOTE in json.loads((self.v.root / "system/staging/notes-sent.json").read_text())["notes"])
        self.assertEqual(b.errors, [])

    def test_save_for_later_and_a_second_run_skips_sent_lines(self):
        b = self.mount() or self.b
        b.click("#fuLater")
        b.wait("fuState.value==='done' || fuRows.value.length===3", 30)
        staged = list((self.v.root / "system/staging").glob("proposed-*-note.json"))
        self.assertEqual(len(staged), 1)
        data = json.loads(staged[0].read_text())
        self.assertEqual({it["decision"] for it in data["items"]}, {"pending"})
        self.assertEqual(data["source_run"], "note")
        self.assertIn("saved for Review", b.eval("document.getElementById('snackT').textContent"))
        b.eval("fuFind()")
        b.wait("['ready','none'].includes(fuState.value)", 40)
        self.assertEqual(b.eval("[...new Set(fuRows.value.map(r=>r.p))]"), [5])               # only the risk's line is new
        self.assertEqual(b.errors, [])

    def test_a_confidential_note_asks_first_and_text_is_escaped(self):
        note = self.v.root / fx.NOTE
        note.write_text(note.read_text().replace("confidential: false", "confidential: true")
                        .replace("Sandbox access granted yesterday.", "Sandbox access granted yesterday. <b>bold</b>"))
        lines = notes.paragraphs(notes.parse(note.read_text())[1])
        b = self.mount(lines=lines) or self.b
        self.assertEqual(b.eval("fuState.value"), "ask")
        self.assertIn("confidential", b.eval("document.querySelector('#fuCol .fu-ask').textContent"))
        b.eval("[...document.querySelectorAll('#fuCol .fu-ask button')].find(x=>x.textContent==='Send to Claude').click()")
        b.wait("fuState.value!=='ask' && fuState.value!=='busy'", 40)
        self.assertEqual(b.eval("[fuState.value, fuMsg.value]"), ["ready", ""])
        self.assertEqual(b.eval("document.querySelectorAll('#fuNote b, #fuCol b.fu-x, #fuCol .fu-r b').length"), 0)
        self.assertEqual(b.errors, [])

    def test_an_items_source_names_the_note_and_its_line(self):
        b = self.b
        src = fx.NOTE + "#p4"
        self.assertEqual(b.eval(f"(o=>[o.type,o.path,o.line,o.section])(srcParse({json.dumps(src)}))"),
                         ["File", fx.NOTE, 4, "line 4"])
        b.eval("const d=document.createElement('div'); d.id='srcFix'; "
               f"document.body.prepend(d); d.insertAdjacentHTML('afterbegin', srcHTML({json.dumps(src)}))")
        self.assertEqual(b.eval("(a=>[a.dataset.openfile,a.dataset.noteline])(document.querySelector('#srcFix .srclink'))"), [fx.NOTE, "4"])
        self.assertEqual(b.eval("typeof NOTE_OPEN.fn"), "function")          # set by the Notes tab; the click: InTheNotesTab

    def test_it_fits_at_320_px_and_esc_closes(self):
        b = self.b
        b.call("Emulation.setDeviceMetricsOverride", width=320, height=800, deviceScaleFactor=1, mobile=False)
        self.mount()
        b.eval("document.getElementById('fuFix').style.gridTemplateColumns='minmax(0,1fr)'")
        self.assertLessEqual(b.eval("document.getElementById('fuCol').scrollWidth"), b.eval("document.getElementById('fuCol').clientWidth"))
        small = b.eval("[...document.querySelectorAll('#fuCol button, #fuCol input')].filter(e=>{ const r=e.getBoundingClientRect(); "
                       "return r.width && (r.width<24||r.height<24); }).map(e=>e.className||e.tagName)")
        self.assertEqual(small, [])
        b.eval("document.querySelector('#fuCol .fu-tick').focus()")
        b.key("Escape")
        b.wait("window.__fuClosed===1")
        self.assertEqual(b.eval("document.querySelectorAll('#fuCol .fu').length"), 0)
        self.assertEqual(b.eval("document.querySelectorAll('#fuNote [data-fu-mk]').length"), 0)


class InTheNotesTab(LiveBrowserCase):
    """The same panel hosted by the real Notes tab (BL-301 B and E wired on v20-base): the ✦ Find updates button in the note's
    header, the panel in the right-hand column, its markers drawn on the editor's lines, #notes=…&find=1, and a source opening the
    note at its line."""

    @classmethod
    def load(cls, v):
        fx.load(v)
        cls.fake = fx.install(v)

    @classmethod
    def server_env(cls):
        return {"CREAITE_CLAUDE": str(cls.fake), "CREAITE_NOW": fx.NOW}

    FILE = fx.NOTE.rsplit("/", 1)[1]
    LINE = "document.querySelector('#v-notes .nbody [data-p=\"%s\"]')"

    def open_note(self, find=False):
        b = self.b
        b.eval(f"location.hash='#notes=FAL&n='+encodeURIComponent({json.dumps(self.FILE)})+{json.dumps('&find=1' if find else '')}")
        b.wait(f"noteCur.value&&noteCur.value.path==={json.dumps(fx.NOTE)}&&!!document.querySelector('#v-notes .nbody [data-p]')", 20)

    def test_find_1_opens_the_panel_beside_the_note_with_markers_on_its_lines(self):
        b = self.b
        self.open_note(find=True)
        b.wait("!!document.querySelector('#noteSide aside.fu') && ['ready','none','error','ask'].includes(fuState.value)", 40)
        self.assertEqual(b.eval("fuState.value"), "ready")
        self.assertEqual(b.eval("document.querySelectorAll('#noteSide .fu-r').length"), 8)
        self.assertIsNone(b.eval("document.querySelector('#noteSide .nctx')"))           # the context comes back on Close
        self.assertEqual(b.eval("document.getElementById('noteFind').getAttribute('aria-expanded')"), "true")
        self.assertTrue(b.eval("location.hash.endsWith('&find=1')"))
        # the markers are drawn by the editor in a later frame than the panel's rows (#152: not yet there on a slow macOS runner)
        b.wait("document.querySelectorAll('#v-notes .nbody [data-fu-mk]').length===6", 10)
        marks = b.eval("[...document.querySelectorAll('#v-notes .nbody [data-p]')].map(p=>[p.dataset.p, p.getAttribute('data-fu-mk')])")
        self.assertEqual(marks, [[str(n), str(n) if n < 7 else None] for n in range(1, 8)])
        risk = "[...document.querySelectorAll('#noteSide .fu-r')].find(r=>r.textContent.includes('Test data refresh'))"
        b.eval(f"{risk}.dispatchEvent(new MouseEvent('mouseenter'))")
        b.wait(f"{self.LINE % 5}.hasAttribute('data-fu-hl')")
        b.eval(f"{self.LINE % 3}.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}))")
        b.wait("document.querySelector('#noteSide .fu-r[data-p=\"3\"]').classList.contains('hl')")
        self.assertIn(b.eval("noteSave.value.state"), ["", "saved"])                                    # drawing markers is never an edit
        b.click("#noteSide .fu-x")
        b.wait("!document.querySelector('#noteSide aside.fu') && !!document.querySelector('#noteSide .nctx')")
        b.wait("document.querySelectorAll('#v-notes .nbody [data-fu-mk]').length===0", 10)                     # taken off a frame later
        self.assertEqual(b.eval("document.querySelectorAll('#v-notes .nbody [data-fu-mk]').length"), 0)
        self.assertEqual(b.eval("document.activeElement.id"), "noteFind")
        self.assertEqual(b.errors, [])

    def test_the_button_writes_the_note_first_and_opens_the_panel(self):
        b = self.b
        self.open_note()
        self.assertEqual(b.eval("document.querySelector('#noteFindSlot #noteFind').textContent"), "✦ Find updates")
        b.eval("document.querySelector('.nbody').cxed.focus('end')")
        b.wait("document.activeElement===document.querySelector('.nbody')", 5)
        b.type(" More.")
        b.wait("['typing','saving','saved'].includes(noteSave.value.state)", 10)
        b.click("#noteFind")
        b.wait("!!document.querySelector('#noteSide aside.fu') && ['ready','none','error'].includes(fuState.value)", 40)
        self.assertIn("More.", (self.v.root / fx.NOTE).read_text())                       # saved before Claude read it
        self.assertEqual(b.eval("fuState.value"), "ready")
        self.assertEqual(b.errors, [])

    def test_a_source_link_opens_the_note_at_its_line_highlighted(self):
        b = self.b
        b.eval("go('today')")
        b.eval("const d=document.createElement('div'); d.id='srcFix'; document.body.prepend(d); "
               f"d.insertAdjacentHTML('afterbegin', srcHTML({json.dumps(fx.NOTE + '#p4')}))")
        b.click("#srcFix .srclink")
        b.wait(f"VIEW==='notes' && !!{self.LINE % 4} && {self.LINE % 4}.classList.contains('nflash')", 20)
        self.assertEqual(b.eval("document.querySelectorAll('#v-notes .nbody .nflash').length"), 1)
        self.assertEqual(b.errors, [])

    TICKS = "[...document.querySelectorAll('#v-notes .nbody [data-sent]')].map(p=>[p.dataset.p, p.dataset.sent])"

    def test_lines_already_sent_show_a_margin_tick(self):
        """BL-301 B: a line notes-sent.json holds (by fingerprint) has a tick, wherever it moved; an edited one loses it."""
        b = self.b
        lines = dict(LINES)
        (self.v.root / "system/staging/notes-sent.json").write_text(json.dumps({"version": 1, "notes": {fx.NOTE: [
            {"p": 1, "fp": notes.fingerprint(lines[1]), "ids": ["FAL-A-002"], "at": "2026-10-13 10:00"},
            {"p": 9, "fp": notes.fingerprint(lines[3]), "ids": ["FAL-A-001"], "at": "2026-10-13 10:00"}]}}))
        self.open_note()
        b.wait(f"{self.LINE % 1}.hasAttribute('data-sent')", 10)
        self.assertEqual(b.eval(self.TICKS), [["1", "FAL-A-002"], ["3", "FAL-A-001"]])
        tick = b.eval(f"getComputedStyle({self.LINE % 3},'::after').content")
        self.assertIn("✓", tick)
        self.assertIn(b.eval("noteSave.value.state"), ["", "saved"])                                    # drawing ticks is never an edit
        b.eval(f"(()=>{{ const ed=document.querySelector('.nbody').cxed.editor, el={self.LINE % 3}; "
               "const pos=ed.view.posAtDOM(el,0); ed.chain().focus().insertContentAt(pos+2,'Not ').run(); })()")
        b.wait(f"!{self.LINE % 3}.hasAttribute('data-sent')", 10)
        self.assertEqual(b.eval(self.TICKS), [["1", "FAL-A-002"]])
        self.assertEqual(b.errors, [])

    def test_apply_ticks_the_sent_lines_and_undo_takes_the_ticks_away(self):
        b = self.b
        self.open_note(find=True)
        b.wait("fuState.value==='ready'", 40)
        self.assertEqual(b.eval(self.TICKS), [])
        b.click("#fuApply")
        b.wait("document.getElementById('snack').classList.contains('on')", 40)
        b.wait("document.querySelectorAll('#v-notes .nbody [data-sent]').length===5", 10)
        self.assertEqual([t[0] for t in b.eval(self.TICKS)], ["1", "2", "3", "4", "6"])
        b.click("#snackU")
        b.wait("document.querySelectorAll('#v-notes .nbody [data-sent]').length===0", 30)
        self.assertEqual(b.errors, [])


if __name__ == "__main__":
    unittest.main()

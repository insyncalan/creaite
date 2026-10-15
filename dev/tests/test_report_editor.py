"""v2.1.0 P5 (BL-335, BL-338; dev/sprints/v210-contract.md section 4): the A4 sheet, components/report/Sheet.jsx, in a real browser on a
fixture document (a weekly report's data block), with the page's own server and no network.

The Done-when: zoom held between 40% and 80% (the buttons, the keys, a trackpad pinch); the scroll kept after a click (and after a zoom,
a move, Show as exported and a document replaced by a save or reload: the section at the top of the view stays at the top); move and
hide (handle keys, the menu, the bar that holds a hidden section's place); the layout remembered per project (the layout the sheet hands
back always agrees with its sections, so P3's remember_layout and normal_layout keep it as it is). Also: true A4, page breaks, renaming
with Reset, rows and figures with eyes, source tags, a section's fresh draft, checks, saving (1.5 s after the last change, one at a
time, a conflict stops it), Show as exported (the controls gone, render's markup), Side by side (levelled, ≠, Match internal) and the
standard peek on an item ID.

Run: python3 dev/tests/test_report_editor.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
from live_browser import LiveBrowserCase  # noqa: E402

ALT = 1
LONG = "\n\n".join(f"Paragraph {i}. The data platform migration continues; the wave plan holds and the open risks are tracked." for i in range(1, 7))

# The fixture: a weekly report's data block, a Sheet mounted on it in a column that fills the window, and a record of everything it
# does (changes, saves, events). `SH.draw()` draws it again with the current document, as a view that keeps the doc in its store does.
FIXTURE = """((ref, long) => {
  document.getElementById('shFix')?.remove();
  const el = document.createElement('div'); el.id = 'shFix';
  el.style.cssText = 'position:fixed;inset:0;z-index:12;display:flex;flex-direction:column;background:var(--bg)';
  document.body.appendChild(el);
  const rows = (n, p) => Array.from({length: n}, (_, i) => ({ref: i === 0 && p === 'asks' ? ref : `${p}-${i}`, shown: true,
    cells: {id: i === 0 && p === 'asks' ? ref : `${p}-${i}`, title: `${p} row ${i}`, owner: 'Sam Patel'}}));
  const cols = [{key: 'id', label: 'ID'}, {key: 'title', label: 'Item'}, {key: 'owner', label: 'Owner'}];
  const sec = (id, type, heading, extra) => ({id, type, heading, default_heading: heading, hidden: false, ...extra});
  const doc = {format: 'creaite-doc', schema: 1, kind: 'weekly', audience: 'internal', project: 'ABC', project_name: 'Example Programme',
    title: 'Weekly report', date: '2026-10-16', client: null, version: 3, state: 'draft', layout: {}, items: {}, sources: [], meta: {},
    sections: [
      sec('summary', 'text', 'Summary', {text: long, tags: [{ref, text: 'SOW signed'}, {ref: 'transcript', text: '00:14', turn: 4}]}),
      sec('glance', 'figures', 'At a glance', {figures: [{key: 'overdue', label: 'Overdue', value: '3', shown: true},
        {key: 'high_risks', label: 'High risks', value: '2', shown: true}, {key: 'next_milestone', label: 'Next milestone', value: '06-11', shown: true}]}),
      sec('asks', 'table', 'What we need from people', {columns: cols, rows: rows(8, 'asks')}),
      sec('this_week', 'text', 'This week', {text: long}),
      sec('risks', 'table', 'Risks and issues', {columns: cols, rows: rows(6, 'risks')}),
      sec('current_state', 'panes', 'Current state', {panes: [{title: 'Done', text: 'Wave two finished.'}, {title: 'Next', text: 'Wave three starts.'}]}),
      sec('next_week', 'text', 'Next week', {text: long})]};
  const SH = window.SH = {doc, partner: null, el, base: 3, changes: [], saves: [], events: [], answers: [], exported: false, checks: [],
    redraft: null, zoomSeen: [], key: 'weekly:ABC:2026-10-16:internal', readOnly: false, ai: undefined};
  SH.draw = () => { mount(Sheet, {doc: SH.doc, baseVersion: SH.base, scrollKey: SH.key, exported: SH.exported, readOnly: SH.readOnly,
    onExported: on => { SH.exported = on; SH.draw(); }, onZoom: z => SH.zoomSeen.push(z), checks: SH.checks, ai: SH.ai,
    onRedraft: SH.redraft, partner: SH.partner, toolbar: {type: 'button', props: {type: 'button', class: 'btn', id: 'shExtra', children: 'Approve'}, key: undefined, ref: undefined, constructor: undefined, __v: 0},
    onChange: (d, why) => { SH.doc = d; SH.changes.push(why); SH.draw(); },
    onSave: async r => { SH.saves.push({base: r.base_version, doc: r.doc}); const a = SH.answers.shift() || {ok: true, version: (r.base_version || 0) + 1}; return a; },
    onEvent: e => SH.events.push(e)}, el); return true; };
  SH.draw();
  return true; })"""

TOP = """(() => { const sc = document.querySelector('#shFix .sheet-scroll'), t = sc.getBoundingClientRect().top;
  for (const s of document.querySelectorAll('#shFix .sheet-a4 > .page > section[data-id]')) { const r = s.getBoundingClientRect();
    if (r.bottom - t > 1) return [s.dataset.id, Math.round(t - r.top)]; } return null; })()"""


class SheetCase(LiveBrowserCase):
    shared_server = True        # the fixture changes no data

    def setUp(self):
        super().setUp()
        self.b.eval("window.confirm=()=>true")
        self.ref = self.b.eval("(typeof A!=='undefined' && A.length ? A[0].id : 'ABC-A-001')")
        self.b.eval(f"{FIXTURE}({json.dumps(self.ref)}, {json.dumps(LONG)})")
        self.b.wait("document.querySelectorAll('#shFix .sheet-a4 .page section[data-id]').length===7 && document.querySelector('#shFix .sheet-fit').offsetWidth>0")

    def sh(self, js):
        return self.b.eval(f"window.SH.{js}")

    def zoom(self):
        return self.b.eval("Number(document.querySelector('#shFix .sheet-zv').dataset.zoom)")

    def scroll_to(self, section, off=0):
        """Scroll as a person would (the scroller's own position), and wait for the sheet to take note of it."""
        self.b.eval(f"""(() => {{ const sc = document.querySelector('#shFix .sheet-scroll'), s = document.querySelector('#shFix .sheet-a4 > .page > section[data-id="{section}"]');
          sc.scrollTop = s.getBoundingClientRect().top - sc.getBoundingClientRect().top + sc.scrollTop + {off}; }})()""")
        self.b.wait(f"({TOP})[0]==='{section}'")
        self.b.eval("new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")     # the scroll event has been seen

    def tap(self, selector):
        """A real mouse click where the element is now. The driver's own click scrolls its target to the middle first, which would hide
        exactly what these tests are about (a click must not move the page)."""
        pos = self.b.eval(f"""(() => {{ const r = document.querySelector({json.dumps(selector)}).getBoundingClientRect(); return {{x: r.left + r.width / 2, y: r.top + r.height / 2}}; }})()""")
        for kind in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.b.call("Input.dispatchMouseEvent", type=kind, x=pos["x"], y=pos["y"], button="left", clickCount=1)
        self.b.pump(0.05)

    def order(self):
        return self.sh("doc.sections.map(s=>s.id)")


class ZoomTests(SheetCase):
    def test_it_starts_at_80_and_the_page_is_a_true_a4(self):
        self.assertEqual(self.zoom(), 0.8)
        got = self.b.eval("""(() => { const sc = document.querySelector('#shFix .sheet-scroll'), fit = document.querySelector('#shFix .sheet-fit'),
          pg = document.querySelector('#shFix .sheet-a4 .page'); return [fit.offsetWidth / (sc.clientWidth - 32), pg.offsetWidth, pg.offsetHeight >= 1122,
          document.querySelector('#shFix .sheet-zv').textContent]; })()""")
        self.assertAlmostEqual(got[0], 0.8, delta=0.02)               # the page is 80% of the sheet area's width
        self.assertAlmostEqual(got[1], 793.7, delta=1)                # 210 mm
        self.assertTrue(got[2])                                       # at least 297 mm
        self.assertEqual(got[3], "80%")

    def test_the_buttons_hold_the_zoom_between_40_and_80(self):
        b = self.b
        self.assertTrue(b.eval("document.querySelector('#shFix [aria-label=\"Zoom in\"]').disabled"))
        for _ in range(12):
            b.eval("document.querySelector('#shFix [aria-label=\"Zoom out\"]:not(:disabled)')?.click()")
        self.assertEqual(self.zoom(), 0.4)
        self.assertTrue(b.eval("document.querySelector('#shFix [aria-label=\"Zoom out\"]').disabled"))
        w = b.eval("document.querySelector('#shFix .sheet-fit').offsetWidth / (document.querySelector('#shFix .sheet-scroll').clientWidth - 32)")
        self.assertAlmostEqual(w, 0.4, delta=0.02)
        b.click("#shFix [aria-label='Zoom in']")
        self.assertEqual(self.zoom(), 0.45)                           # steps of 5 points
        self.assertEqual(self.sh("zoomSeen.slice(-1)[0]"), 0.45)

    def test_the_keys_zoom_and_never_leave_the_range(self):
        b = self.b
        key = "document.querySelector('#shFix .sheet-bar').dispatchEvent(new KeyboardEvent('keydown',{key:'%s',metaKey:true,bubbles:true,cancelable:true}))"
        for _ in range(3):
            b.eval(key % "-")
        self.assertEqual(self.zoom(), 0.65)
        b.eval(key % "0")
        self.assertEqual(self.zoom(), 0.8)
        b.eval(key % "=")
        self.assertEqual(self.zoom(), 0.8)                            # 80% is the most
        for _ in range(12):
            b.eval(key % "-")
        self.assertEqual(self.zoom(), 0.4)

    def test_a_trackpad_pinch_zooms_with_its_default_prevented(self):
        b = self.b
        pinch = """(dy) => { const sc = document.querySelector('#shFix .sheet-scroll'); const e = new WheelEvent('wheel',
          {deltaY: dy, ctrlKey: true, clientX: 300, clientY: 300, bubbles: true, cancelable: true}); sc.dispatchEvent(e); return e.defaultPrevented; }"""
        self.assertTrue(b.eval(f"({pinch})(60)"))
        self.assertLess(self.zoom(), 0.8)
        for _ in range(30):
            b.eval(f"({pinch})(60)")
        self.assertEqual(self.zoom(), 0.4)
        for _ in range(30):
            b.eval(f"({pinch})(-60)")
        self.assertEqual(self.zoom(), 0.8)


class ScrollTests(SheetCase):
    def test_the_scroll_is_kept_after_a_click_and_a_zoom(self):
        b = self.b
        self.scroll_to("asks", 30)
        before = b.eval(TOP)
        top = b.eval("document.querySelector('#shFix .sheet-scroll').scrollTop")
        self.assertGreater(top, 200)
        self.tap("#shFix section[data-id='asks'] tbody tr:nth-child(3) td:nth-child(3) .sheet-ed")       # a click into a cell
        self.assertAlmostEqual(b.eval("document.querySelector('#shFix .sheet-scroll').scrollTop"), top, delta=3)
        b.type("x")
        b.wait("SH.changes.length>0")
        self.assertEqual(b.eval(TOP)[0], before[0])
        self.assertAlmostEqual(b.eval("document.querySelector('#shFix .sheet-scroll').scrollTop"), top, delta=3)
        self.tap("#shFix [aria-label='Zoom out']")                    # a zoom: the section at the top stays at the top
        b.wait("document.querySelector('#shFix .sheet-zv').textContent==='75%'")
        self.assertEqual(b.eval(TOP)[0], "asks")
        self.assertLess(abs(b.eval(TOP)[1] * 0.75 / 0.8 - before[1] * 0.75 / 0.8), 40)

    def test_the_scroll_is_kept_on_an_eye_a_toggle_and_a_document_replaced(self):
        b = self.b
        self.scroll_to("this_week", 20)
        top = b.eval("document.querySelector('#shFix .sheet-scroll').scrollTop")
        b.eval("document.querySelector('#shFix section[data-id=\"risks\"] .eye').click()")             # an eye, lower down
        b.wait("SH.changes.includes('Row hidden')")
        self.assertAlmostEqual(b.eval("document.querySelector('#shFix .sheet-scroll').scrollTop"), top, delta=3)
        b.click("#shFix .sheet-bar .btn[aria-pressed]")              # Show as exported
        b.wait("document.querySelectorAll('#shFix .sheet-handle').length===0")
        self.assertEqual(b.eval(TOP)[0], "this_week")
        b.click("#shFix .sheet-bar .btn[aria-pressed]")
        b.wait("document.querySelectorAll('#shFix .sheet-handle').length>0")
        self.assertEqual(b.eval(TOP)[0], "this_week")
        # a save or a reload gives the view a new document and version: drawn again, the view stays where it was
        b.eval("SH.doc = JSON.parse(JSON.stringify(SH.doc)); SH.doc.version = 4; SH.base = 4; SH.draw();")
        self.assertEqual(b.eval(TOP)[0], "this_week")
        self.assertAlmostEqual(b.eval(TOP)[1], 20, delta=12)           # the section is where it was (the exported page is a few pixels different)

    def test_each_page_keeps_its_own_place_when_you_switch_views(self):
        b = self.b
        self.scroll_to("risks", 10)
        b.eval("SH.key = 'weekly:ABC:2026-10-16:client'; SH.draw();")      # another view's page, at the top
        b.eval("document.querySelector('#shFix .sheet-scroll').scrollTop = 0")
        b.eval("SH.key = 'weekly:ABC:2026-10-16:internal'; SH.draw();")    # back: the place is returned
        b.wait("(" + TOP + ")[0]==='risks'")


class MoveHideTests(SheetCase):
    def grip(self, sec):
        self.b.eval(f"document.querySelector('#shFix [data-grip=\"{sec}\"]').focus()")
        self.b.wait(f"document.activeElement===document.querySelector('#shFix [data-grip=\"{sec}\"]')")

    def rename(self, sec, text):
        self.b.click(f"#shFix section[data-id='{sec}'] .sheet-h")
        self.b.eval("document.activeElement.select()")
        self.b.type(text)
        self.b.key("Enter")

    def test_alt_arrows_move_a_section_and_the_layout_goes_with_it(self):
        b = self.b
        self.grip("this_week")
        b.key("ArrowUp", ALT)
        b.wait("SH.changes.includes('Section moved')")
        self.assertEqual(self.order()[:4], ["summary", "glance", "this_week", "asks"])
        self.assertEqual(self.sh("doc.layout.order.slice(0,4)"), ["summary", "glance", "this_week", "asks"])
        self.assertEqual(self.sh("events.filter(e=>e.type==='section-moved').pop().id"), "this_week")
        # the handle keeps the focus, so the next press moves it again
        b.wait("document.activeElement===document.querySelector('#shFix [data-grip=\"this_week\"]')")
        b.key("ArrowDown", ALT)
        b.wait("SH.doc.sections[3].id==='this_week'")

    def test_a_section_can_be_dragged_to_a_new_place(self):
        b = self.b
        b.eval("""(() => { const g = document.querySelector('#shFix [data-grip="next_week"]'), t = document.querySelector('#shFix .sheet-a4 > .page > section[data-id="glance"]');
          const dt = new DataTransfer(); g.dispatchEvent(new DragEvent('dragstart', {dataTransfer: dt, bubbles: true}));
          const r = t.getBoundingClientRect(); t.dispatchEvent(new DragEvent('dragover', {dataTransfer: dt, bubbles: true, cancelable: true, clientY: r.top + 2}));
          t.dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true, clientY: r.top + 2})); })()""")
        b.wait("SH.changes.includes('Section moved')")
        self.assertEqual(self.order()[:3], ["summary", "next_week", "glance"])
        self.assertEqual(self.sh("doc.layout.order"), self.order())

    def test_hide_leaves_a_bar_and_show_brings_it_back(self):
        b = self.b
        b.click("#shFix section[data-id='asks'] .sheet-hbtn")
        b.eval("[...document.querySelectorAll('[role^=menuitem]')].find(x=>/Hide this section/.test(x.textContent)).click()")
        b.wait("SH.doc.sections.find(s=>s.id==='asks').hidden===true")
        self.assertEqual(self.sh("doc.layout.hidden"), ["asks"])
        self.assertFalse(b.eval("!!document.querySelector('#shFix section[data-id=\"asks\"]')"))
        self.assertIn("Hidden: What we need from people", b.eval("document.querySelector('#shFix [data-hidden=\"asks\"]').textContent"))
        self.assertEqual(self.sh("events.filter(e=>e.type==='section-hidden').pop().id"), "asks")
        b.click("#shFix [data-hidden='asks'] .linkbtn")
        b.wait("SH.doc.sections.find(s=>s.id==='asks').hidden===false")
        self.assertEqual(self.sh("doc.layout.hidden"), [])
        self.assertEqual(self.sh("events.filter(e=>e.type==='section-shown').pop().id"), "asks")
        self.assertTrue(b.eval("!!document.querySelector('#shFix section[data-id=\"asks\"]')"))

    def test_rename_in_place_and_reset(self):
        b = self.b
        self.rename("summary", "Executive summary")
        b.wait("SH.doc.sections[0].heading==='Executive summary'")
        self.assertEqual(self.sh("doc.layout.headings"), {"summary": "Executive summary"})
        b.click("#shFix section[data-id='summary'] .sheet-reset")
        b.wait("SH.doc.sections[0].heading==='Summary'")
        self.assertEqual(self.sh("doc.layout.headings"), {})
        self.assertEqual(self.sh("events.filter(e=>e.type==='heading-reset').length"), 1)

    def test_the_layout_handed_back_is_one_the_report_server_keeps_as_it_is(self):
        """The layout is remembered per project by report_doc.remember_layout (normal_layout); a layout that agrees with the sections
        comes out of it unchanged for the sections it names."""
        import report_doc
        b = self.b
        self.grip("risks")
        b.key("ArrowUp", ALT)
        b.wait("SH.changes.includes('Section moved')")
        b.click("#shFix section[data-id='next_week'] .sheet-hbtn")
        b.eval("[...document.querySelectorAll('[role^=menuitem]')].find(x=>/Hide this section/.test(x.textContent)).click()")
        b.wait("SH.doc.layout.hidden.length===1")
        self.rename("glance", "The figures")
        b.wait("SH.doc.layout.headings.glance==='The figures'")
        b.click("#shFix section[data-id='glance'] .figure:nth-child(2) .eye")
        b.wait("SH.doc.layout.glance.length===2")
        lay = self.sh("doc.layout")
        ids = self.order()
        norm = report_doc.normal_layout("weekly", lay)
        mine = [i for i in norm["order"] if i in ids]
        self.assertEqual(mine, lay["order"])                           # the order the sheet shows is the order that is kept
        self.assertEqual(norm["hidden"], lay["hidden"])
        self.assertEqual(norm["headings"], lay["headings"])
        self.assertEqual(norm["glance"], lay["glance"])
        self.assertEqual(lay["glance"], ["overdue", "next_milestone"])


class RowFigureTests(SheetCase):
    def test_a_row_eye_greys_the_row_and_counts_what_is_shown(self):
        b = self.b
        b.click("#shFix section[data-id='risks'] tbody tr:nth-child(2) .eye")
        b.wait("SH.changes.includes('Row hidden')")
        self.assertEqual(self.sh("doc.sections.find(s=>s.id==='risks').rows[1].shown"), False)
        self.assertIn("Showing 5 of 6", b.eval("document.querySelector('#shFix section[data-id=\"risks\"] .sheet-count').textContent"))
        self.assertEqual(b.eval("document.querySelectorAll('#shFix section[data-id=\"risks\"] tr.sheet-rowoff').length"), 1)
        self.assertEqual(self.sh("doc.layout.rows"), None)             # a row hidden by its eye is this document's only

    def test_figures_reorder_and_hide(self):
        b = self.b
        b.eval("""(() => { const f = [...document.querySelectorAll('#shFix section[data-id="glance"] .figure')], dt = new DataTransfer();
          f[2].dispatchEvent(new DragEvent('dragstart', {dataTransfer: dt, bubbles: true}));
          f[0].dispatchEvent(new DragEvent('dragover', {dataTransfer: dt, bubbles: true, cancelable: true}));
          f[0].dispatchEvent(new DragEvent('drop', {dataTransfer: dt, bubbles: true, cancelable: true})); })()""")
        b.wait("SH.changes.includes('Figure moved')")
        self.assertEqual(self.sh("doc.layout.glance"), ["next_milestone", "overdue", "high_risks"])
        b.click("#shFix section[data-id='glance'] .figure:nth-child(1) .eye")
        b.wait("SH.changes.includes('Figure hidden')")
        self.assertEqual(self.sh("doc.layout.glance"), ["overdue", "high_risks"])


class PageTests(SheetCase):
    def test_page_breaks_are_marked_every_265_mm_at_the_pages_own_scale(self):
        b = self.b
        b.wait("document.querySelectorAll('#shFix .sheet-break').length>=1")
        got = b.eval("""[...document.querySelectorAll('#shFix .sheet-break')].map(e => [parseFloat(e.style.top), e.textContent])""")
        mm = 96 / 25.4
        self.assertAlmostEqual(got[0][0], 16 * mm + 265 * mm, delta=1)
        self.assertEqual(got[0][1], "Page 2")
        if len(got) > 1:
            self.assertAlmostEqual(got[1][0] - got[0][0], 265 * mm, delta=1)

    def test_a_section_that_would_straddle_a_break_starts_on_the_next_page(self):
        b = self.b
        b.wait("document.querySelectorAll('#shFix .sheet-break').length>=1")
        ok = b.eval("""(() => { const per = 265 * 96 / 25.4, y0 = 16 * 96 / 25.4;
          return [...document.querySelectorAll('#shFix .sheet-a4 > .page > section[data-id]')].every(s => {
            const t = s.offsetTop - y0 + 1, h = s.offsetHeight; if (h > per) return true;
            return Math.floor(t / per) === Math.floor((t + h - 1) / per); }); })()""")
        self.assertTrue(ok)

    def test_show_as_exported_draws_renders_markup_with_no_controls(self):
        b = self.b
        b.click("#shFix .sheet-bar .btn[aria-pressed]")
        b.wait("document.querySelectorAll('#shFix .sheet-handle').length===0")
        got = b.eval("""(() => { const q = s => document.querySelectorAll('#shFix ' + s).length;
          return {controls: q('.sheet-handle') + q('.eye') + q('.sheet-tags') + q('.sheet-spark') + q('.sheet-h') + q('[role=textbox]') + q('.sheet-extra'),
          markup: [q('.page header.doc h1'), q('.page > section[data-id] > h2'), q('.page table'), q('.page .figure'), q('.page .panes')],
          size: [getComputedStyle(document.querySelector('#shFix .page')).fontSize, getComputedStyle(document.querySelector('#shFix td')).fontSize],
          press: document.querySelector('#shFix .sheet-bar .btn[aria-pressed]').getAttribute('aria-pressed')}; })()""")
        self.assertEqual(got["controls"], 0)
        self.assertEqual(got["markup"], [1, 7, 2, 3, 1])
        self.assertEqual(got["size"], ["14px", "12.5px"])
        self.assertEqual(got["press"], "true")
        self.assertEqual(self.sh("changes.length"), 0)


class TextTests(SheetCase):
    def test_a_section_s_text_is_the_one_editor_and_an_edit_is_a_change(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelectorAll('#shFix section[data-id=\"this_week\"] .sheet-rich.ProseMirror').length"), 1)
        b.click("#shFix section[data-id='this_week'] .sheet-rich p")
        b.type("Edited. ")
        b.wait("SH.changes.includes('Text edited')")
        self.assertIn("Edited. ", self.sh("doc.sections.find(s=>s.id==='this_week').text"))

    def test_tags_open_the_item_or_tell_the_view_and_can_be_removed(self):
        b = self.b
        b.eval("[...document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-tag')].find(x=>x.textContent==='00:14').click()")
        self.assertEqual(self.sh("events.filter(e=>e.type==='tag').pop().tag.ref"), "transcript")      # a time tag is the view's
        b.eval("[...document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-tagx')][1].click()")
        b.wait("SH.changes.includes('Tag removed')")
        self.assertEqual(self.sh("doc.sections[0].tags.length"), 1)
        b.click("#shFix section[data-id='summary'] .sheet-untag")
        b.wait("SH.changes.includes('Tags removed')")
        self.assertEqual(self.sh("doc.sections[0].tags"), [])
        self.assertEqual(b.eval("document.querySelectorAll('#shFix .sheet-tag').length"), 0)

    def test_an_item_id_opens_the_standard_peek(self):
        b = self.b
        b.eval("document.getElementById('shFix').style.zIndex = 1")
        b.eval("""SH.doc = {...SH.doc, items: {[%s]: {table: 'actions', id: %s}}}; SH.draw();""" % (json.dumps(self.ref), json.dumps(self.ref)))
        b.eval("[...document.querySelectorAll('#shFix .sheet-tag')].find(x=>x.textContent==='SOW signed').click()")
        b.wait("document.getElementById('panel').classList.contains('on')")
        self.assertEqual(self.sh("events.filter(e=>e.type==='item').pop().ref"), self.ref)

    def test_the_view_s_own_peek_comes_first(self):
        b = self.b
        b.eval("""SH.own = []; const d = SH.draw; SH.draw = function() { mount(Sheet, {doc: SH.doc, scrollKey: SH.key, onChange: (x, w) => { SH.doc = x; SH.draw(); },
          onOpenItem: r => { SH.own.push(r); return true; }}, SH.el); };
          SH.draw();""")
        b.wait("document.querySelector('#shFix .sheet-tag')")
        b.eval("[...document.querySelectorAll('#shFix .sheet-tag')].find(x=>x.textContent==='SOW signed').click()")
        self.assertEqual(self.sh("own"), [self.ref])
        self.assertFalse(b.eval("document.getElementById('panel').classList.contains('on')"))


class RedraftCheckTests(SheetCase):
    def test_the_spark_shows_a_fresh_draft_beside_the_words_and_nothing_changes_before_a_choice(self):
        b = self.b
        self.assertEqual(b.eval("document.querySelectorAll('#shFix .sheet-spark').length"), 0)        # no onRedraft, no ✦
        b.eval("""SH.redraft = async s => ({text: 'A fresh draft of ' + s.heading, sources: [{ref: 'X-1', label: 'Week facts'}], lines: ['New line one']}); SH.draw();""")
        b.wait("document.querySelectorAll('#shFix .sheet-spark').length===4")                          # text and panes sections only
        before = self.sh("doc.sections[0].text")
        b.click("#shFix section[data-id='summary'] .sheet-spark")
        b.wait("document.querySelector('#shFix .sheet-redraft .sheet-md')")
        self.assertEqual(self.sh("doc.sections[0].text"), before)
        self.assertIn("A fresh draft of Summary", b.eval("document.querySelector('#shFix .sheet-redraft').textContent"))
        b.eval("[...document.querySelectorAll('#shFix .sheet-redraft button')].find(x=>x.textContent==='Keep mine').click()")
        self.assertEqual(self.sh("doc.sections[0].text"), before)
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').pop().choice"), "keep")
        b.click("#shFix section[data-id='summary'] .sheet-spark")
        b.wait("document.querySelector('#shFix .sheet-redraft .sheet-md')")
        b.eval("[...document.querySelectorAll('#shFix .sheet-redraft button')].find(x=>x.textContent==='Use this').click()")
        b.wait("SH.doc.sections[0].text==='A fresh draft of Summary'")
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').pop().choice"), "use")

    def test_a_check_underlines_its_quote_and_its_button_goes_to_the_view(self):
        b = self.b
        b.eval("""SH.checks = [{id: 'c1', section: 'summary', quote: 'wave plan holds', note: 'Not in this week\\'s facts.', last: 'Last recorded: 3 overdue on 14-10-2026',
          actions: [{id: 'use', label: 'Use that'}, {id: 'keep', label: 'Keep mine'}]}]; SH.draw();""")
        b.wait("document.querySelectorAll('#shFix section[data-id=\"summary\"] .claim').length>=1")
        self.assertIn("wave plan holds", b.eval("document.querySelector('#shFix section[data-id=\"summary\"] .claim').textContent"))
        self.assertIn("1 check open", b.eval("document.querySelector('#shFix .sheet-checks').textContent"))
        self.assertNotIn("claim", self.sh("doc.sections[0].text"))                                     # never saved
        b.click("#shFix section[data-id='summary'] .claim")
        b.wait("document.querySelector('#shFix .sheet-pop')")
        self.assertIn("Last recorded", b.eval("document.querySelector('#shFix .sheet-pop').textContent"))
        b.eval("[...document.querySelectorAll('#shFix .sheet-pop button')].find(x=>x.textContent==='Use that').click()")
        self.assertEqual(self.sh("events.filter(e=>e.type==='check').pop()"), {"type": "check", "id": "c1", "action": "use"})
        b.click("#shFix .sheet-bar .btn[aria-pressed]")                                                # not in Show as exported
        b.wait("document.querySelectorAll('#shFix .sheet-handle').length===0")
        self.assertEqual(b.eval("document.querySelectorAll('#shFix .claim').length + document.querySelectorAll('#shFix .sheet-checks').length"), 0)


class SaveTests(SheetCase):
    def edit(self):
        self.b.click("#shFix section[data-id='this_week'] .sheet-rich p")
        self.b.type("x")
        self.b.wait("SH.changes.length>0")

    def test_it_saves_1_5_seconds_after_the_last_change_with_the_base_version(self):
        b = self.b
        self.edit()
        self.assertEqual(self.sh("saves.length"), 0)
        self.assertIn("Unsaved", b.eval("document.querySelector('#shFix .sheet-status').textContent"))
        b.wait("SH.saves.length===1", timeout=6)
        self.assertEqual(self.sh("saves[0].base"), 3)
        b.wait("/Saved · version 4/.test(document.querySelector('#shFix .sheet-status').textContent)")
        self.assertEqual(self.sh("events.filter(e=>e.type==='saved').pop().version"), 4)
        b.type("y")                                                                                    # the next save takes version 4 as its base
        b.wait("SH.saves.length===2", timeout=6)
        self.assertEqual(self.sh("saves[1].base"), 4)

    def test_cmd_s_saves_at_once_and_a_change_during_a_save_is_saved_after_it(self):
        b = self.b
        self.edit()
        b.eval("""SH.hold = null; SH.answers = []; const first = SH.draw; window.SHgo = null;""")
        b.eval("document.querySelector('#shFix .sheet-root').dispatchEvent(new KeyboardEvent('keydown',{key:'s',metaKey:true,bubbles:true,cancelable:true}))")
        b.wait("SH.saves.length===1", timeout=3)

    def test_a_conflict_stops_saving_and_reload_is_the_view_s(self):
        b = self.b
        b.eval("SH.answers = [{ok: false, conflict: true, message: 'This report changed in another window.'}]")
        self.edit()
        b.wait("document.querySelector('#shFix .sheet-note[role=alert]')", timeout=6)
        self.assertIn("changed in another window", b.eval("document.querySelector('#shFix .sheet-note').textContent"))
        self.assertEqual(self.sh("events.filter(e=>e.type==='save-failed').length"), 1)
        b.type("z")
        b.wait("SH.changes.length>1")
        b.eval("new Promise(r => setTimeout(r, 2000))")
        self.assertEqual(self.sh("saves.length"), 1)                                                    # nothing more is saved
        b.eval("[...document.querySelectorAll('#shFix .sheet-note button')].find(x=>x.textContent==='Reload').click()")
        self.assertEqual(self.sh("events.filter(e=>e.type==='reload').length"), 1)
        self.assertFalse(b.eval("!!document.querySelector('#shFix .sheet-note[role=alert]')"))

    def test_a_client_leak_the_server_removed_is_shown_under_the_bar(self):
        b = self.b
        b.eval("SH.answers = [{ok: true, version: 4, removed: [{label: 'Confidential note'}]}]")
        self.edit()
        b.wait("document.querySelector('#shFix .sheet-removed')", timeout=6)
        self.assertIn("Confidential note", b.eval("document.querySelector('#shFix .sheet-removed').textContent"))

    def test_unmounting_with_unsaved_changes_saves_them(self):
        b = self.b
        self.edit()
        b.eval("mount(function(){ return null }, {}, SH.el); true")
        b.wait("SH.saves.length===1", timeout=3)

    def test_a_read_only_sheet_has_no_editing_controls_and_no_saves(self):
        b = self.b
        b.eval("SH.readOnly = true; SH.draw();")
        b.wait("document.querySelectorAll('#shFix .sheet-handle').length===0")
        self.assertEqual(b.eval("document.querySelectorAll('#shFix .eye, #shFix .sheet-h, #shFix .sheet-untag').length"), 0)
        b.wait("[...document.querySelectorAll('#shFix .sheet-rich')].every(e => e.getAttribute('contenteditable') === 'false')")
        self.assertEqual(self.sh("saves.length"), 0)


class SideBySideTests(SheetCase):
    def setUp(self):
        super().setUp()
        self.b.eval("""(() => { const p = JSON.parse(JSON.stringify(SH.doc)); p.audience = 'client'; p.client = 'Kestrel Group';
          p.sections.find(s => s.id === 'summary').text = 'Short client text.';
          SH.partner = {doc: p, label: 'Client', baseVersion: 1, scrollKey: 'p', onChange: (d, why) => { SH.partner.doc = d; SH.changes.push('partner:' + why); SH.draw(); },
            onSave: async r => { SH.saves.push({partner: true, base: r.base_version}); return {ok: true, version: 2}; }}; SH.draw(); })()""")
        self.b.wait("document.querySelectorAll('#shFix .sheet-a4 > .page').length===2")

    def test_matching_sections_are_the_same_height_and_a_difference_is_marked(self):
        b = self.b
        b.wait("""(() => { const q = id => [...document.querySelectorAll('#shFix .sheet-a4 > .page > section[data-id="' + id + '"]')].map(e => e.offsetHeight);
          const a = q('summary'); return a.length === 2 && a[0] === a[1] && a[0] > 100; })()""")
        self.assertEqual(b.eval("document.querySelectorAll('#shFix .sheet-diff').length"), 1)
        self.assertIn("≠ Client", b.eval("document.querySelector('#shFix .sheet-diff').textContent"))
        self.assertEqual(b.eval("document.querySelector('#shFix .sheet-diff').closest('section').dataset.id"), "summary")

    def test_match_internal_copies_one_section_or_all_and_keeps_the_clients_hidden_ones(self):
        b = self.b
        b.eval("""(() => { const p = SH.partner.doc.sections.find(s => s.id === 'risks'); p.hidden = true; SH.draw(); })()""")
        self.assertIn("Edited for the client", b.eval("document.querySelectorAll('#shFix .sheet-match')[0].textContent"))
        b.eval("[...document.querySelectorAll('#shFix .sheet-match .linkbtn')][0].click()")
        b.wait("SH.partner.doc.sections.find(s=>s.id==='summary').text===SH.doc.sections.find(s=>s.id==='summary').text")
        self.assertIn("partner:Matched internal", self.sh("changes"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#shFix .sheet-diff')].map(e => e.closest('section').dataset.id)"), ["risks"])   # shown here, hidden there
        b.eval("[...document.querySelectorAll('#shFix .sheet-bar .btn')].find(x=>/Match internal for every section/.test(x.textContent)).click()")
        b.wait("SH.changes.filter(c=>c==='partner:Matched internal').length===2")
        self.assertTrue(self.sh("partner.doc.sections.find(s=>s.id==='risks').hidden"))               # the client's own hidden section stays hidden

    def test_the_left_page_can_be_read_only_while_the_right_stays_editable(self):
        b = self.b
        b.eval("""(() => { SH.draw = () => { mount(Sheet, {doc: SH.doc, baseVersion: SH.base, scrollKey: SH.key, leftReadOnly: true, partner: SH.partner,
          onChange: (d, why) => { SH.doc = d; SH.changes.push(why); SH.draw(); }, onSave: async r => { SH.saves.push({base: r.base_version}); return {ok: true, version: 9}; }, onEvent: e => SH.events.push(e)}, SH.el); return true; };
          SH.draw(); return 1; })()""")
        b.wait("document.querySelectorAll('#shFix .sheet-a4 > .page').length===2")
        got = b.eval("""[...document.querySelectorAll('#shFix .sheet-a4 > .page')].map(p => [p.querySelectorAll('.sheet-handle').length, p.querySelectorAll('.eye').length])""")
        self.assertEqual(got[0], [0, 0])
        self.assertGreater(got[1][0], 0)
        self.assertEqual(self.sh("saves.length"), 0)

    def test_a_views_own_match_hook_is_used_when_given(self):
        b = self.b
        b.eval("SH.hooked = []; SH.partner.match = id => SH.hooked.push(id); SH.draw();")
        b.eval("[...document.querySelectorAll('#shFix .sheet-match .linkbtn')][0].click()")
        self.assertEqual(self.sh("hooked"), ["summary"])
        self.assertNotIn("partner:Matched internal", self.sh("changes"))                               # the generic copy is not made

    def test_each_page_saves_through_its_own_save_and_scroll_together_can_be_turned_off(self):
        b = self.b
        b.click("#shFix .sheet-pair > .sheet-fit:nth-child(2) section[data-id='this_week'] .sheet-rich p")
        b.type("c")
        b.wait("SH.saves.some(s=>s.partner)", timeout=6)
        self.assertEqual(b.eval("document.querySelectorAll('#shFix .sheet-scroll').length"), 1)
        b.eval("document.querySelector('#shFix .sheet-tog input').click()")
        b.wait("document.querySelectorAll('#shFix .sheet-scroll').length===2")


class AiPlaceTests(SheetCase):
    def test_the_sheet_gives_its_editors_the_report_place_and_a_read_only_one_the_find_the_source_only(self):
        b = self.b
        b.eval("SH.ai = {place: 'report', project: () => 'ABC'}; SH.draw();")
        b.wait("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-rich.ProseMirror')")
        self.assertEqual(b.eval("AI_PLACES.report"), ["shorter", "executive", "polish", "custom"])
        names = b.eval("aiItems('report').map(x=>x.name)")
        self.assertEqual(names, ["Shorten", "Make it executive", "Polish", "Find the source", "Or say what you want…"])
        self.assertEqual(b.eval("aiItems('readonly').map(x=>x.name)"), ["Find the source"])
        self.assertEqual(b.eval("aiItems('minutes').map(x=>x.name)"), names)


if __name__ == "__main__":
    unittest.main()

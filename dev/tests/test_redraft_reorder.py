"""#90 (v2.1.0): a ✦ redraft lands on the section it was asked for, by its id, even after a reorder; and it is a suggestion that
is accepted or dismissed, never applied alone. 
Run: python3 dev/tests/test_redraft_reorder.py   (needs Google Chrome; skipped otherwise)
test_report_editor's fixture: a weekly report on the Sheet, with a record of every change and event. The draft is held back
(a promise the test settles later), the sections are moved while it is pending, and then it arrives.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_report_editor import ALT, SheetCase  # noqa: E402

# the redraft waits for the test: SH.settle(id) answers the pending one with a draft that names the section it was asked for
PENDING = """(() => { SH.asked = []; SH.waiting = {};
  SH.redraft = s => new Promise(res => { SH.asked.push(s.id); SH.waiting[s.id] = () => res({text: 'Fresh draft for ' + s.id, sources: [{ref: 'S1', label: 'Week facts'}]}); });
  SH.settle = id => SH.waiting[id](); SH.draw(); return true; })()"""


class ReorderTests(SheetCase):
    def spark(self, sid):
        self.b.click(f"#shFix section[data-id='{sid}'] .sheet-spark")
        self.b.wait(f"SH.asked.includes('{sid}')")

    def where(self):
        """{section id: its pending redraft's text, or None}: which section's block holds the suggestion."""
        return self.b.eval("""(() => { const o = {}; for (const s of document.querySelectorAll('#shFix section[data-id]'))
          o[s.dataset.id] = s.querySelector(':scope > .sheet-redraft')?.textContent || null; return o; })()""")

    def test_a_redraft_pending_while_sections_move_lands_on_its_own_section(self):
        b = self.b
        b.eval(PENDING)
        b.wait("document.querySelectorAll('#shFix .sheet-spark').length===4")
        self.spark("summary")
        b.wait("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-redraft')")      # "Drafting Summary…"
        before = self.sh("doc.sections[0].text")
        # the person moves Summary down twice, and This week up, while the draft is pending (the keys; the layout goes with them)
        self.b.click("#shFix [data-grip='summary']")
        b.key("ArrowDown", ALT)
        b.wait("SH.doc.sections[1].id==='summary'")
        b.key("ArrowDown", ALT)
        b.wait("SH.doc.sections[2].id==='summary'")
        self.assertNotEqual(self.order()[0], "summary")
        self.spark("this_week")
        self.sh("settle('this_week')")
        b.wait("document.querySelector('#shFix section[data-id=\"this_week\"] .sheet-md')")
        self.sh("settle('summary')")
        b.wait("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-md')")
        got = self.where()
        self.assertIn("Fresh draft for summary", got["summary"])
        self.assertIn("Fresh draft for this_week", got["this_week"])
        self.assertEqual([k for k, v in got.items() if v], ["summary", "this_week"] if self.order().index("summary") < self.order().index("this_week") else ["this_week", "summary"])
        # nothing changed before a choice
        self.assertEqual(self.sh("doc.sections.find(s=>s.id==='summary').text"), before)
        self.assertNotIn("redraft", [e["type"] for e in self.sh("events")])

    def test_use_this_after_a_reorder_changes_only_that_section(self):
        b = self.b
        b.eval(PENDING)
        b.wait("document.querySelectorAll('#shFix .sheet-spark').length===4")
        self.spark("this_week")
        self.b.click("#shFix [data-grip='this_week']")
        b.key("ArrowUp", ALT)
        b.wait("SH.doc.sections[2].id==='this_week'")
        b.key("ArrowUp", ALT)
        b.wait("SH.doc.sections[1].id==='this_week'")
        texts = self.b.eval("Object.fromEntries(SH.doc.sections.map(s => [s.id, s.text || null]))")
        self.sh("settle('this_week')")
        b.wait("document.querySelector('#shFix section[data-id=\"this_week\"] .sheet-md')")
        b.eval("[...document.querySelectorAll('#shFix section[data-id=\"this_week\"] .sheet-redraft button')].find(x=>x.textContent==='Use this').click()")
        b.wait("SH.doc.sections.find(s=>s.id==='this_week').text==='Fresh draft for this_week'")
        after = self.b.eval("Object.fromEntries(SH.doc.sections.map(s => [s.id, s.text || null]))")
        self.assertEqual({k: v for k, v in after.items() if k != "this_week"}, {k: v for k, v in texts.items() if k != "this_week"})
        ev = self.sh("events.filter(e=>e.type==='redraft')")
        self.assertEqual([(e["id"], e["choice"]) for e in ev], [("this_week", "use")])

    def test_dismissing_keeps_the_words_and_counts_a_rejection(self):
        b = self.b
        b.eval(PENDING)
        b.wait("document.querySelectorAll('#shFix .sheet-spark').length===4")
        before = self.sh("doc.sections[0].text")
        self.spark("summary")
        self.sh("settle('summary')")
        b.wait("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-md')")
        b.eval("[...document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-redraft button')].find(x=>x.textContent==='Keep mine').click()")
        self.assertEqual(self.sh("doc.sections[0].text"), before)
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').pop().choice"), "keep")
        self.assertIsNone(self.where()["summary"])


class StaleTests(SheetCase):
    """A suggestion belongs to the document it was made from: after a new version loads, or another report is shown (same section
    ids, no remount), "Use this" never applies it; and a double click applies once."""

    def ready(self, sid="summary"):
        b = self.b
        b.eval(PENDING)
        b.wait("document.querySelectorAll('#shFix .sheet-spark').length===4")
        b.click(f"#shFix section[data-id='{sid}'] .sheet-spark")
        b.wait(f"SH.asked.includes('{sid}')")

    def settle_draft(self, sid="summary"):
        self.sh(f"settle('{sid}')")
        self.b.wait(f"document.querySelector('#shFix section[data-id=\"{sid}\"] .sheet-redraft')?.textContent.length>0")

    def assert_stale_and_unapplied(self, sid, text):
        b = self.b
        b.wait(f"/earlier version/.test(document.querySelector('#shFix section[data-id=\"{sid}\"] .sheet-redraft')?.textContent||'')")
        self.assertEqual(b.eval(f"document.querySelectorAll('#shFix section[data-id=\"{sid}\"] .sheet-redraft button').length"), 1)   # Close only
        self.assertEqual(self.b.eval(f"SH.doc.sections.find(s=>s.id==='{sid}').text"), text)
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').length"), 0)

    def test_a_suggestion_pending_while_a_new_version_loads_is_not_used(self):
        b = self.b
        self.ready()
        b.eval("SH.doc = {...SH.doc, version: SH.doc.version + 1, sections: SH.doc.sections.map(s => s.id === 'summary' ? {...s, text: 'Newer words.'} : s)}; SH.draw();")
        self.settle_draft()
        self.assert_stale_and_unapplied("summary", "Newer words.")

    def test_it_goes_stale_when_the_version_changes_after_the_draft_is_shown(self):
        b = self.b
        self.ready()
        self.settle_draft()
        b.wait("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-redraft button.primary')")
        b.eval("SH.doc = {...SH.doc, version: SH.doc.version + 1, sections: SH.doc.sections.map(s => s.id === 'summary' ? {...s, text: 'Newer words.'} : s)}; SH.draw();")
        self.assert_stale_and_unapplied("summary", "Newer words.")

    def test_another_report_shown_without_a_remount_keeps_no_suggestion_for_the_same_section_id(self):
        b = self.b
        self.ready()
        self.settle_draft()
        b.eval("SH.doc = {...SH.doc, project: 'DEF', project_name: 'Other', date: '2026-10-23', sections: SH.doc.sections.map(s => s.id === 'summary' ? {...s, text: 'Another report.'} : s)}; SH.draw();")
        self.assert_stale_and_unapplied("summary", "Another report.")

    def test_a_double_click_on_use_this_applies_and_counts_once(self):
        b = self.b
        self.ready()
        self.settle_draft()
        b.eval("""(() => { const u = [...document.querySelectorAll('#shFix section[data-id="summary"] .sheet-redraft button')].find(x => x.textContent === 'Use this');
          u.click(); u.click(); return true; })()""")
        b.wait("SH.doc.sections[0].text==='Fresh draft for summary'")
        self.assertEqual(self.sh("changes.filter(c => c === 'Redraft used').length"), 1)
        self.assertEqual(self.sh("events.filter(e => e.type === 'redraft').length"), 1)

    def test_a_section_edited_after_the_spark_is_stale_and_use_this_changes_nothing(self):
        b = self.b
        self.ready()
        b.eval("SH.doc = {...SH.doc, sections: SH.doc.sections.map(s => s.id === 'summary' ? {...s, text: 'Typed since.'} : s)}; SH.draw();")
        self.settle_draft()
        b.wait("/changed this section since/.test(document.querySelector('#shFix section[data-id=\"summary\"] .sheet-redraft')?.textContent||'')")
        self.assertEqual(b.eval("document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-redraft button').length"), 1)
        self.assertEqual(b.eval("SH.doc.sections[0].text"), "Typed since.")
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').length"), 0)
        # edited after the draft was shown: Use this is refused too
        self.b.eval("[...document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-redraft button')].find(x=>x.textContent==='Close').click()")
        self.ready("this_week")
        self.settle_draft("this_week")
        b.eval("SH.doc = {...SH.doc, sections: SH.doc.sections.map(s => s.id === 'this_week' ? {...s, text: 'Typed after.'} : s)}; SH.draw();")
        b.wait("/changed this section since/.test(document.querySelector('#shFix section[data-id=\"this_week\"] .sheet-redraft')?.textContent||'')")
        self.assertEqual(b.eval("SH.doc.sections.find(s=>s.id==='this_week').text"), "Typed after.")
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').length"), 0)

    def test_no_edit_and_use_this_applies_as_before(self):
        b = self.b
        self.ready()
        self.settle_draft()
        b.eval("[...document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-redraft button')].find(x=>x.textContent==='Use this').click()")
        b.wait("SH.doc.sections[0].text==='Fresh draft for summary'")
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').map(e=>e.choice)"), ["use"])

    def test_an_edit_that_puts_the_words_back_is_not_stale(self):
        b = self.b
        self.ready()
        orig = b.eval("SH.doc.sections[0].text")
        b.eval("SH.doc = {...SH.doc, sections: SH.doc.sections.map(s => s.id === 'summary' ? {...s, text: 'Typed.'} : s)}; SH.draw();")
        b.eval(f"SH.doc = {{...SH.doc, sections: SH.doc.sections.map(s => s.id === 'summary' ? {{...s, text: {json.dumps(orig)}}} : s)}}; SH.draw();")
        self.settle_draft()
        self.assertFalse(b.eval("/changed this section|earlier version/.test(document.querySelector('#shFix section[data-id=\"summary\"] .sheet-redraft').textContent)"))
        b.eval("[...document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-redraft button')].find(x=>x.textContent==='Use this').click()")
        b.wait("SH.doc.sections[0].text==='Fresh draft for summary'")


class ReviewTests(SheetCase):
    """#90 review (Team Cap): K3 a second ✦ while one is writing, K2 a mode switch or another minutes of the same day mid-write,
    K5 the "edited" wiring, F5 the reply's checks on the page."""
    ready, settle_draft, assert_stale_and_unapplied = StaleTests.ready, StaleTests.settle_draft, StaleTests.assert_stale_and_unapplied

    def stale_after(self, js):
        b = self.b
        self.ready()
        b.eval(js + "; SH.draw();")
        self.settle_draft()
        self.assert_stale_and_unapplied("summary", self.b.eval("SH.doc.sections[0].text"))

    def test_a_second_spark_while_one_is_writing_is_ignored(self):
        b = self.b
        self.ready()
        b.click("#shFix section[data-id='summary'] .sheet-spark")
        b.pump(0.2)
        self.assertEqual(self.sh("asked"), ["summary"])
        self.assertIn("Drafting", b.eval("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-redraft').textContent"))
        self.settle_draft()
        b.wait("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-redraft button.primary')")
        self.assertIn("Fresh draft for summary", b.eval("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-redraft').textContent"))

    def test_a_switch_to_the_distributed_version_mid_write_makes_it_stale(self):
        self.stale_after("SH.doc = {...SH.doc, audience: 'distributed'}")

    def test_another_minutes_of_the_same_project_and_day_mid_write_makes_it_stale(self):
        self.stale_after("SH.doc = {...SH.doc, title: 'Budget review'}")

    def test_an_id_or_path_that_differs_makes_it_stale(self):
        self.stale_after("SH.doc = {...SH.doc, path: 'projects/ABC/minutes/2026-10-16 Budget review.html'}")

    def test_a_used_draft_then_changed_counts_edited_once(self):
        b = self.b
        self.ready()
        self.settle_draft()
        b.eval("[...document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-redraft button')].find(x=>x.textContent==='Use this').click()")
        b.wait("SH.doc.sections[0].text==='Fresh draft for summary'")
        b.pump(0.2)
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').map(e=>e.choice)"), ["use"])   # used, not yet edited
        b.eval("SH.doc = {...SH.doc, sections: SH.doc.sections.map(s => s.id === 'summary' ? {...s, text: 'Changed after use.'} : s)}; SH.draw();")
        b.wait("SH.events.some(e=>e.type==='redraft'&&e.choice==='edited')")
        b.eval("SH.doc = {...SH.doc, sections: SH.doc.sections.map(s => s.id === 'summary' ? {...s, text: 'Changed again.'} : s)}; SH.draw();")
        b.pump(0.2)
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').map(e=>e.choice)"), ["use", "edited"])

    def test_a_used_draft_on_another_document_is_never_counted_edited(self):
        b = self.b
        self.ready()
        self.settle_draft()
        b.eval("[...document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-redraft button')].find(x=>x.textContent==='Use this').click()")
        b.wait("SH.doc.sections[0].text==='Fresh draft for summary'")
        b.eval("SH.doc = {...SH.doc, project: 'DEF', sections: SH.doc.sections.map(s => s.id === 'summary' ? {...s, text: 'Another report.'} : s)}; SH.draw();")
        b.pump(0.3)
        self.assertEqual(self.sh("events.filter(e=>e.type==='redraft').map(e=>e.choice)"), ["use"])

    def test_the_replys_checks_and_no_source_marks_reach_the_page(self):
        b = self.b
        answer = {"ok": True, "section": "summary", "text": "UAT slipped by 20 days. Omar Ali is escalating it.",
                  "sources": [{"ref": "S1", "text": "Week facts"}],
                  "notes": [{"id": "figures-added", "note": "It adds 20, which your text didn't have: check it."},
                            {"id": "names-added", "note": "It adds Omar Ali, which your text didn't have: check it."}],
                  "sentences": [{"text": "UAT slipped by 20 days.", "refs": ["S1"], "unsourced": False},
                                {"text": "Omar Ali is escalating it.", "refs": [], "unsourced": True}]}
        b.eval(f"SH.redraft = s => Promise.resolve(redraftAnswer({json.dumps(answer)}, s)); SH.draw(); true")
        b.wait("document.querySelectorAll('#shFix .sheet-spark').length===4")
        b.click("#shFix section[data-id='summary'] .sheet-spark")
        b.wait("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-rdnotes')")
        notes = b.eval("[...document.querySelectorAll('#shFix section[data-id=\"summary\"] .sheet-rdnotes li')].map(li=>li.textContent)")
        self.assertEqual(b.eval("document.querySelector('#shFix section[data-id=\"summary\"] .sheet-rdnotes').getAttribute('aria-label')"), "Check it")
        self.assertTrue(any("20" in n for n in notes), notes)
        self.assertTrue(any("Omar Ali" in n and "adds" in n for n in notes), notes)
        self.assertIn("No source: “Omar Ali is escalating it.”", notes)
        self.assertFalse(any("UAT slipped" in n for n in notes), notes)            # a sentence with a source has no mark
        # an answer for another section is refused by redraftAnswer itself
        msg = b.eval(f"(() => {{ try {{ redraftAnswer({json.dumps({**answer, 'section': 'this_week'})}, {{id: 'summary'}}); return ''; }} catch (e) {{ return e.message; }} }})()")
        self.assertIn("another section", msg)


if __name__ == "__main__":
    unittest.main()

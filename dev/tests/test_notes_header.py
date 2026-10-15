"""#115: the Notes header in a real browser against the real live server (desktop 1400 and 900 px only).

Run: python3 dev/tests/test_notes_header.py   (needs Google Chrome; skipped otherwise)

  - readDate, the shared typed-date reader: last/next/this weekday, N days, ago, DD-MM-YYYY, bad input;
  - the title row (title, Saved, Find updates, more) is one line, the properties one line, the tags their own line;
  - + New note is Work's tonal .newb tile and opens the New note dialog; the list's collapse control is quiet, at the right;
  - the date: typed words show "Reads as ..." before Enter, the calendar picks, unreadable text keeps the old date;
  - tags: add, rename, remove, no duplicates, trimmed, capped; handlers act on the note as it is now; saved in the file's tags.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_notes_tab_browser import NotesTab  # noqa: E402,F401

WED = "2026-10-14"
READ = [  # (text, today, expected)
    ("today", WED, "2026-10-14"), ("Yesterday", WED, "2026-10-13"), ("tomorrow", WED, "2026-10-15"),
    ("last monday", WED, "2026-10-12"), ("last wednesday", WED, "2026-10-07"), ("last friday", WED, "2026-10-09"),
    ("next friday", WED, "2026-10-16"), ("next wednesday", WED, "2026-10-21"), ("next monday", WED, "2026-10-19"),
    ("friday", WED, "2026-10-16"), ("this friday", WED, "2026-10-16"), ("this monday", WED, "2026-10-12"),
    ("this wednesday", WED, "2026-10-14"), ("this sunday", WED, "2026-10-18"), ("next sun", WED, "2026-10-18"),
    ("in 3 days", WED, "2026-10-17"), ("in 1 day", WED, "2026-10-15"), ("3 days ago", WED, "2026-10-11"),
    ("1 day ago", WED, "2026-10-13"), ("in 20 days", WED, "2026-11-03"),
    ("12-10-2026", WED, "2026-10-12"), ("12/10/2026", WED, "2026-10-12"), ("1.2.2026", WED, "2026-02-01"),
    ("2026-10-12", WED, "2026-10-12"), ("29-02-2028", WED, "2028-02-29"),
]
BAD = ["", "  ", "soon", "32-10-2026", "31-02-2026", "29-02-2027", "next", "last", "last fooday", "in days", "3 days", "12-10-26", "tomorrow please"]


class NotesHeader(LiveBrowserCase):
    width, height = 1400, 1000
    log, notes_dir, make, type_end = NotesTab.log, NotesTab.notes_dir, NotesTab.make, NotesTab.type_end

    def rect(self, sel):
        return self.b.eval(f"(()=>{{const r=document.querySelector({json.dumps(sel)}).getBoundingClientRect();return [r.left,r.top,r.right,r.bottom];}})()")

    def tags_now(self):
        return self.b.eval("noteCur.value.meta.tags")

    def saved(self, f, text):
        for _ in range(150):
            if f.is_file() and text in f.read_text():
                return True
            self.b.pump(0.1)
        return False

    def type_into(self, sel, text, enter=False, idx=0):
        b = self.b
        b.eval(f"(()=>{{const i=document.querySelectorAll({json.dumps(sel)})[{idx}]; i.focus(); i.select&&i.select();}})()")
        b.type(text)
        if enter:
            b.key("Enter")

    def test_read_date_table(self):
        b = self.b
        for text, today, want in READ:
            self.assertEqual(b.eval(f"readDate({json.dumps(text)},{json.dumps(today)})"), want, text)
        for text in BAD:
            self.assertIsNone(b.eval(f"readDate({json.dumps(text)},{json.dumps(WED)})"), repr(text))
        # the laptop's own date is the default
        self.assertEqual(b.eval("readDate('today')"), b.eval("TODAY"))

    def test_the_header_is_tidy_at_1400_and_900(self):
        b = self.b
        self.make("Workshop", "working-session")
        for w in (1400, 900):
            b.resize(w, 900)
            b.pump(0.4)
            tops = b.eval("[...document.querySelectorAll('.trow > *')].map(e=>Math.round(e.getBoundingClientRect().top+e.getBoundingClientRect().height/2))")
            self.assertEqual(len(tops), 4, tops)          # title, Saved, Find updates, more
            self.assertLessEqual(max(tops) - min(tops), 4, f"title row wraps at {w}: {tops}")
            find, title, more = self.rect("#noteFind"), self.rect("#noteTitle"), self.rect(".trow .nmorewrap")
            self.assertGreater(find[0], title[0])
            self.assertGreater(more[0], find[0])
            self.assertEqual(b.eval("document.getElementById('noteSave').textContent.startsWith('Saved')||document.getElementById('noteSave').textContent===''"), True)
            props, tags, trow = self.rect(".nhead .props"), self.rect("#noteTags"), self.rect(".trow")
            self.assertGreaterEqual(props[1], trow[3] - 1)
            self.assertGreaterEqual(tags[1], props[3] - 1)
            self.assertNotIn("Working session", b.eval("document.querySelector('.nhead .props').textContent"))
            self.assertEqual(b.eval("document.documentElement.scrollWidth-document.documentElement.clientWidth"), 0)

    def test_new_note_is_works_tile_and_the_list_control_is_quiet(self):
        b = self.b
        self.make("First")
        self.assertTrue(b.eval("document.getElementById('notesNew').classList.contains('newb')"))
        self.assertEqual(b.eval("document.getElementById('notesNew').getAttribute('aria-label')"), "New note")
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('notesNew')).height"), "32px")
        b.eval("document.getElementById('notesNew').focus()")
        b.key("Enter")
        b.wait("document.getElementById('newNoteDlg').open")
        b.key("Escape")
        b.wait("!document.getElementById('newNoteDlg').open")
        col, lh = self.rect("#notesCollapse"), self.rect(".nlist .lhead")
        word = self.rect(".nlist .lhead b")
        self.assertGreater(col[0] - word[2], 60, "away from the word Notes")
        self.assertLess(lh[2] - col[2], 8, "at the right edge")
        self.assertEqual(b.eval("document.getElementById('notesCollapse').getAttribute('aria-expanded')"), "true")
        self.assertIn("(", b.eval("document.getElementById('notesCollapse').dataset.tip"))
        d_open = b.eval("document.querySelector('#notesCollapse svg').innerHTML")
        b.click("#notesCollapse")
        b.wait("document.getElementById('notesSplit').classList.contains('collapsed')")
        self.assertEqual(b.eval("document.getElementById('notesCollapse').getAttribute('aria-expanded')"), "false")
        self.assertEqual(b.eval("document.getElementById('notesCollapse').getAttribute('aria-label')"), "Show the notes list")
        self.assertNotEqual(b.eval("document.querySelector('#notesCollapse svg').innerHTML"), d_open, "the chevrons flip")
        self.assertTrue(b.eval("document.getElementById('notesNew').offsetWidth>0"))

    def test_date_typed_words_read_as_then_picked_and_unreadable_keeps_the_old(self):
        import datetime
        b = self.b
        self.make("Workshop", "working-session")
        f = self.notes_dir() / "Workshop.md"
        today = datetime.date.today()
        last_mon = today - datetime.timedelta(days=(today.weekday() or 7))
        self.type_into("#noteWsDate", "last monday")
        b.wait("!!document.getElementById('noteDatePop')")
        read = b.eval("document.getElementById('noteDateRead').textContent")
        self.assertIn("Reads as Monday " + last_mon.strftime("%d-%m-%Y"), read)
        self.assertIn("Enter to use", read)
        self.assertEqual(b.eval("noteCur.value.meta.date"), b.eval("noteCur.value.note.date"), "not accepted yet")
        b.key("Enter")
        b.wait("!document.getElementById('noteDatePop')")
        self.assertEqual(b.eval("document.getElementById('noteWsDate').value"), last_mon.strftime("%d-%m-%Y"))
        b.eval("noteFlush()")
        self.assertTrue(self.saved(f, f"date: {last_mon.isoformat()}"), f.read_text())
        # unreadable: says so, keeps the old date on leaving
        self.type_into("#noteWsDate", "sometime soon")
        b.wait("document.getElementById('noteDateRead').classList.contains('bad')")
        self.assertIn("Not a date I can read", b.eval("document.getElementById('noteDateRead').textContent"))
        b.eval("document.getElementById('noteWsWith').focus()")
        b.wait("!document.getElementById('noteDatePop')")
        self.assertEqual(b.eval("document.getElementById('noteWsDate').value"), last_mon.strftime("%d-%m-%Y"))
        self.assertEqual(b.eval("noteCur.value.meta.date"), last_mon.isoformat())
        # the calendar: today ringed, a day picked, month arrows
        b.click("#noteDateBtn")
        b.wait("!!document.getElementById('noteDatePop')")
        self.assertEqual(b.eval("document.querySelectorAll('#noteDatePop .g button.t').length"), 1)
        self.assertEqual(b.eval("document.querySelectorAll('#noteDatePop .g button.s').length"), 1)
        before = b.eval("document.querySelector('#noteDatePop .mh b').textContent")
        b.click("#noteDatePrev")
        self.assertNotEqual(b.eval("document.querySelector('#noteDatePop .mh b').textContent"), before)
        b.click("#noteDatePop .foot [data-q=yesterday]")
        b.wait("!document.getElementById('noteDatePop')")
        y = today - datetime.timedelta(days=1)
        self.assertEqual(b.eval("noteCur.value.meta.date"), y.isoformat())
        # Esc closes the pop-up and puts the old date back
        self.type_into("#noteWsDate", "tomorrow")
        b.wait("!!document.getElementById('noteDatePop')")
        b.key("Escape")
        b.wait("!document.getElementById('noteDatePop')")
        self.assertEqual(b.eval("document.getElementById('noteWsDate').value"), y.strftime("%d-%m-%Y"))

    def test_date_keyboard_pick_returns_focus_and_esc_closes_without_reopening(self):
        import datetime
        b = self.b
        self.make("Workshop", "working-session")
        active = "(document.activeElement.id||document.activeElement.tagName)"
        # M1: calendar button, ArrowDown, ArrowRight, Enter: the day is used and focus is back in the date box
        b.eval("document.getElementById('noteWsDate').focus()")
        b.wait("!!document.getElementById('noteDatePop')")
        b.key("ArrowDown")
        b.wait("document.activeElement.dataset&&!!document.activeElement.dataset.d")
        b.key("ArrowRight")
        b.pump(0.1)
        want = b.eval("document.activeElement.dataset.d")
        b.key("Enter")
        b.wait("!document.getElementById('noteDatePop')")
        self.assertEqual(b.eval(active), "noteWsDate", "focus is back in the date box, not on the page")
        self.assertEqual(b.eval("noteCur.value.meta.date"), want)
        b.pump(0.3)
        self.assertFalse(b.eval("!!document.getElementById('noteDatePop')"), "picking a day does not reopen the pop-up")
        # M2: Esc from a day returns focus to the box and the pop-up stays closed (one Esc is enough)
        b.key("ArrowDown")
        b.wait("document.activeElement.dataset&&!!document.activeElement.dataset.d")
        b.key("Escape")
        b.wait("!document.getElementById('noteDatePop')")
        b.pump(0.3)
        self.assertEqual(b.eval(active), "noteWsDate")
        self.assertFalse(b.eval("!!document.getElementById('noteDatePop')"), "Esc leaves it closed")
        self.assertEqual(b.eval("document.getElementById('noteDateBtn').getAttribute('aria-expanded')"), "false")
        # typing opens it again with the reads-as line; Tab out settles the field
        self.type_into("#noteWsDate", "tomorrow")
        b.wait("!!document.getElementById('noteDatePop')")
        self.assertIn("Reads as", b.eval("document.getElementById('noteDateRead').textContent"))
        for _ in range(12):                    # Tab through the calendar button and the pop-up until focus leaves the date property
            b.key("Tab")
            if not b.eval("!!document.querySelector('.nprop').contains(document.activeElement)"):
                break
        b.wait("!document.getElementById('noteDatePop')")
        tom = datetime.date.today() + datetime.timedelta(days=1)
        self.assertEqual(b.eval("noteCur.value.meta.date"), tom.isoformat())
        # a click on the box opens it, and the calendar button's day pick by mouse also lands focus in the box
        b.click("#noteDateBtn")
        b.wait("!!document.getElementById('noteDatePop')")
        b.click("#noteDatePop .foot [data-q=yesterday]")
        b.wait("!document.getElementById('noteDatePop')")
        self.assertEqual(b.eval(active), "noteWsDate")

    def test_tags_esc_cancels_rename_is_cleaned_and_twenty_is_the_limit(self):
        b = self.b
        self.make("Tagged")
        # M3: Esc in + Tags adds nothing, whatever was typed; Enter adds; blur with text adds
        b.click("#noteTagAdd")
        b.wait("!!document.getElementById('noteTagNew')")
        b.type("tmp")
        b.key("Escape")
        b.wait("!document.getElementById('noteTagNew')")
        b.pump(0.3)
        self.assertEqual(self.tags_now(), [])
        self.assertEqual(b.eval("document.activeElement.id"), "noteTagAdd")
        b.click("#noteTagAdd")
        b.wait("!!document.getElementById('noteTagNew')")
        b.type("kept")
        b.eval("document.getElementById('noteTagNew').blur()")
        b.wait("noteCur.value.meta.tags.length===1")
        self.assertEqual(self.tags_now(), ["kept"])
        # L1: a rename is cleaned like an add (commas and runs of spaces become one space), so the screen and the file agree
        self.type_into("#noteTags .chip .t", "  two,   words ", enter=True, idx=0)
        b.wait("noteCur.value.meta.tags[0]==='two words'")
        self.assertEqual(b.eval("document.querySelectorAll('#noteTags .chip .t')[0].value"), "two words")
        b.eval("noteFlush()")
        f = self.notes_dir() / "Tagged.md"
        self.assertTrue(self.saved(f, "tags: [two words]"), f.read_text())
        b.wait("noteSave.value.state==='saved'", 15)
        # L2: 20 tags, the server's limit; the 21st is refused with a plain message
        b.eval("(()=>{const a=document.getElementById('noteTagAdd'); a.click();})()")
        b.wait("!!document.getElementById('noteTagNew')")
        b.wait("document.activeElement.id==='noteTagNew'")
        b.type(",".join(f"t{k}" for k in range(19)))
        b.key("Enter")
        b.wait("noteCur.value.meta.tags.length===20")
        b.click("#noteTagAdd")
        b.wait("!!document.getElementById('noteTagNew')")
        b.type("one-too-many")
        b.key("Enter")
        b.wait("!document.getElementById('noteTagNew')")
        b.pump(0.3)
        self.assertEqual(len(self.tags_now()), 20)
        self.assertNotIn("one-too-many", self.tags_now())
        self.assertIn("Notes keep up to 20 tags", b.eval("document.getElementById('toastHost').textContent"))
        b.eval("noteFlush()")
        b.pump(1)
        meta_tags = [x for x in f.read_text().split("\n") if x.startswith("tags:")][0]
        self.assertEqual(meta_tags.count(",") + 1, 20, meta_tags)

    def test_the_popup_is_not_clipped_at_900(self):
        b = self.b
        self.make("Workshop", "working-session")
        b.resize(900, 800)
        b.pump(0.3)
        b.click("#noteDateBtn")
        b.wait("!!document.getElementById('noteDatePop')")
        r = self.rect("#noteDatePop")
        self.assertGreaterEqual(r[0], 0)
        self.assertLessEqual(r[2], 900)
        self.assertLessEqual(r[3], 800)

    def test_tags_add_rename_remove_without_duplicates(self):
        b = self.b
        self.make("Tagged")
        f = self.notes_dir() / "Tagged.md"
        self.assertTrue(b.eval("!!document.getElementById('noteTagSugg')"))
        b.click("#noteTagAdd")
        b.wait("!!document.getElementById('noteTagNew')")
        b.type("  alpha  ")
        b.key("Enter")
        b.wait("document.querySelectorAll('#noteTags .chip').length===1")
        self.assertFalse(b.eval("!!document.getElementById('noteTagSugg')"), "suggestions go once there are tags")
        for t in ("beta", "ALPHA", "gamma"):      # ALPHA is a duplicate of alpha
            b.click("#noteTagAdd")
            b.wait("!!document.getElementById('noteTagNew')")
            b.type(t)
            b.key("Enter")
            b.wait("!document.getElementById('noteTagNew')")
        self.assertEqual(self.tags_now(), ["alpha", "beta", "gamma"])
        # remove the first, then rename the (now first) second: acts on the list as it is now
        b.eval("document.querySelector('#noteTags .chip .x').click()")
        b.wait("document.querySelectorAll('#noteTags .chip').length===2")
        self.assertEqual(self.tags_now(), ["beta", "gamma"])
        self.type_into("#noteTags .chip .t", "delta", enter=True, idx=1)
        b.wait("noteCur.value.meta.tags[1]==='delta'")
        self.assertEqual(self.tags_now(), ["beta", "delta"])
        # a rename onto an existing tag is refused; an empty one removes; the length is capped
        self.type_into("#noteTags .chip .t", "BETA", enter=True, idx=1)
        b.pump(0.3)
        self.assertEqual(self.tags_now(), ["beta", "delta"])
        self.assertEqual(b.eval("document.querySelectorAll('#noteTags .chip .t')[1].value"), "delta")
        b.click("#noteTagAdd")
        b.wait("!!document.getElementById('noteTagNew')")
        b.eval("(()=>{const i=document.getElementById('noteTagNew'); i.maxLength=500; i.value='x'.repeat(80); })()")
        b.key("Enter")
        b.wait("noteCur.value.meta.tags.length===3")
        self.assertEqual(len(self.tags_now()[2]), 60)       # the server's own cap (notes.py clean_changes)
        b.eval("document.querySelectorAll('#noteTags .chip .t')[0].focus()")
        b.eval("(()=>{const i=document.querySelectorAll('#noteTags .chip .t')[0]; i.value=''; i.blur();})()")
        b.wait("noteCur.value.meta.tags.length===2")
        self.assertEqual(self.tags_now()[0], "delta")
        # Esc puts a half-typed rename back
        b.eval("document.querySelectorAll('#noteTags .chip .t')[0].focus()")
        b.type("zzz")
        b.key("Escape")
        b.pump(0.2)
        self.assertEqual(self.tags_now()[0], "delta")
        b.eval("noteFlush()")
        self.assertTrue(self.saved(f, "tags: [delta, "), f.read_text())
        # the Internal chip is unchanged
        self.assertEqual(b.eval("document.querySelector('#noteTags .tag').textContent"), "Internal")
        self.assertEqual(b.eval("document.querySelectorAll('#noteTags .chip .x')[0].getAttribute('aria-label')"), "Remove tag delta")

    def test_the_save_line_stays_in_the_title_row(self):
        b = self.b
        self.make("Saving")
        self.type_end("Words.")
        b.eval("noteFlush()")
        b.wait("noteSave.value.state==='saved'", 15)
        self.assertEqual(b.eval("document.querySelector('.trow #noteSave').textContent.startsWith('Saved ')"), True)


del NotesTab

if __name__ == "__main__":
    unittest.main()

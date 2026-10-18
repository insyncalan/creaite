"""#127: the client gate on every client path, part 2 of 3 (the fixture is in client_gate_support.py). The data is fictional.

Run: python3 dev/tests/test_client_gate_reviews.py      (quick tier: no Chrome, no model)
"""
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_reports as R  # noqa: E402
from client_gate_support import INTERNAL_ID, PERSON, REASON, DOC, WEEKLY_DOC, SECTION, Base, TIMER, TOO_LONG  # noqa: E402


ENCODED_REASON = "https://x.example.com/?r=ZEBRAINTERNAL%20vendor%20is%20failing%20to%20deliver"


class TheReviewOf2a77459(Base):
    """#127 review of 2a77459: what Word shows is what the gate reads; the health reason and a marker in a link address; linear
    patterns; the scheme in any case; prose that mentions creaite: is not a link."""

    def plain(self, text):
        return self.py(f"print(json.dumps(client_leak.plain_findings(client_leak.connect(), 'ABC', {text!r})))")

    def test_text_that_plain_words_delete_but_word_shows_is_found(self):
        """Finding 1: _plain's link pattern crosses spaces and line breaks and drops a title and an image's words; the gate also
        reads the stored strings."""
        for text in (f"[t](https://x.example.com/a b {INTERNAL_ID})", f"[s](https://x.example.com/\n{INTERNAL_ID})",
                     f'[x](https://e.example.org/ "{INTERNAL_ID}")', f"![{INTERNAL_ID} for {PERSON}](images/plan.png)",
                     f"| A | B |\n|---|---|\n| [x](https://x.example.com/a | {INTERNAL_ID}) |"):
            got = self.findings(f"Progress. {text}")
            self.assertTrue(any(f.startswith(f"{INTERNAL_ID} isn't client-visible") for f in got), (text, got))
        self.assertIn(f"{PERSON} is named but owns only items a client report can't show",
                      self.findings(f"Progress. ![{PERSON}](images/plan.png)"))
        for ok in ("[the client site](https://client.example.com/documents/plan.pdf)", "![Delivery plan](images/plan.png)",
                   "[Example](https://example.com/a_(b))"):
            self.assertEqual(self.findings(f"Progress continues. {ok}"), [], ok)      # control: stored words that are client-safe

    def test_the_health_reason_and_a_marker_in_an_address_are_found_everywhere(self):
        """Finding 2: on approve and export (findings) and the plain path (plain_findings)."""
        for link, why in ((f"[s](https://x.example.com/{REASON.replace(' ', '-')})", "it holds the internal health reason"),
                          ("[s](https://x.example.com/internal-only/page)", "it holds an internal-only marker"),
                          (f"[s]({ENCODED_REASON})", "it holds the internal health reason")):
            self.assertIn(why, self.findings(f"Progress. {link}"), link)
            self.assertIn(why, self.plain(f"Progress. {link}"), link)
        self.assertEqual(self.plain("Progress. [s](https://x.example.com/page)"), [])        # control
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:   # a test vault: set directly
            con.execute("UPDATE actions SET client_message = ? WHERE id = 'ABC-A-002'",
                        (R.CLIENT_MSG.replace("The signed statement of work.", f"The [signed]({ENCODED_REASON}) statement."),))
            con.commit()
        got = self.py("print(json.dumps(client_leak.findings(report_doc.client_doc('ABC'))))")
        self.assertIn("it holds the internal health reason", got)

    def test_an_encoded_marker_in_the_health_section_and_an_items_address_are_found(self):
        marker = "[s](https://x.example.com/internal%2Donly/page)"            # only the decoded address says internal-only
        got = self.py("d = report_doc.client_doc('ABC')\n"
                      f"next(s for s in d['sections'] if s.get('type') == 'health')['text'] = 'Behind plan. ' + {marker!r}\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertIn("it holds an internal-only marker", got)
        got = self.py("d = report_doc.client_doc('ABC')\nk = next(iter(d['items']))\n"
                      f"d['items'][k]['title'] = 'UAT [start]({ENCODED_REASON})'\n"
                      "print(json.dumps([k, client_leak.findings(d)]))")
        self.assertIn("it holds the internal health reason", got[1], got[0])

    def test_every_check_is_linear_on_brackets(self):
        """Finding 3: creaite_doc._plain and docx_tools.md_runs took tens of seconds on 100 KB of "["."""
        code = (TIMER + "import docx_tools\ncon = client_leak.connect()\nout = {}\n"
                "def doc(s):\n    d = report_doc.client_doc('ABC')\n"
                "    next(x for x in d['sections'] if x['id'] == 'summary')['text'] = s\n    return d\n"
                "RUNS = (('findings', lambda s, d: client_leak.findings(d)), ('plain', lambda s, d: client_leak.plain_findings(con, 'ABC', s)),"
                " ('client_problems', lambda s, d: edit_ai.client_problems('ABC', s)), ('md_runs', lambda s, d: docx_tools.md_runs(s)))\n"
                "for name, u, k in (('[', '[', 100000), ('[a](', '[a](', 25000), ('![a](', '![a](', 20000)):\n"
                "    small, large = u * (k // 4), u * k\n    ds, dl = doc(small), doc(large)\n"
                "    for f, run in RUNS:\n"
                "        out[name + ' ' + f] = [took(lambda: run(small, ds)), took(lambda: run(large, dl))]\n"
                "print(json.dumps(out))")
        self.assert_linear(self.py(code))

    def test_the_scheme_in_capitals_is_found_and_dropped(self):
        link = f"[p](CREAITE:item/{INTERNAL_ID})"
        self.assertTrue(any(f.startswith(f"{INTERNAL_ID} isn't client-visible") for f in self.findings(f"Progress. {link}")))
        for link in (link, f"[p](CREAITE%3Aitem/{INTERNAL_ID})", f"[p](CREAITE:{INTERNAL_ID})"):   # (not case-folded on the way)
            self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', 'Before. {link} After.')))"),
                             "Before.  After.", link)

    def test_a_creaite_person_link_split_by_a_line_break_is_read(self):
        """SCHEME_GAP in link_addresses: without the join, the address of a split creaite:person link is only "creaite:"."""
        self.assertIn(f"{PERSON} is named but owns only items a client report can't show",
                      self.findings("Progress. [the auditor](creaite:\nperson/Quentin%20Marlow)"))

    def test_prose_mentioning_creaite_is_not_a_link(self):
        """Finding 6: ordinary prose passes and is kept; real creaite: links are still found and dropped."""
        prose = "Text creaite: notes/ are kept"
        self.assertEqual(self.findings(prose), [])
        self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {prose!r})))"), prose)
        for link in ("creaite:notes/7", "[n](creaite: note/7)", "[n](creaite:\nnote/7)", "creaite: notes/7"):
            got = self.findings(f"Progress. {link}")
            self.assertTrue(any(f.startswith("a creaite link a client can't open") for f in got), (link, got))
            text = f"Before. {link} After."
            self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {text!r})))").split(),
                             ["Before.", "After."], link)

    def test_word_shows_only_the_words_of_any_creaite_link(self):
        """Finding 5: md_runs reads the scheme as the gate does (any case, encoded) and words with [brackets] in them."""
        got = self.py("import docx_tools\nprint(json.dumps([docx_tools.plain(t) for t in ("
                      "'See [p](CREAITE:item/ABC-A-002).', 'See [p](creaite%3Aitem/ABC-A-002).', 'See [p](creaite&#58;item/ABC-A-002).', "
                      "'See [a [b] c](creaite:item/ABC-A-002).', 'See [a [b] c](https://example.com/x).')]))")
        self.assertEqual(got, ["See p.", "See p.", "See p.", "See a [b] c.", "See a [b] c (https://example.com/x)."])


class TheRegisterFailsClosed(Base):
    """Part 4: a people register that is missing, can't be decoded or has no People table makes every names check refuse, with a
    plain message; a readable one checks the names (the control)."""
    REGISTER = Path("projects/_portfolio/people-register.md")

    def broken(self):
        reg = self.v.root / self.REGISTER
        good = reg.read_bytes()
        yield "missing", lambda: reg.unlink()
        yield "not text", lambda: reg.write_bytes(b"\xff\xfe\x00broken")
        yield "no People table", lambda: reg.write_text("# People register\n\nNothing here.\n", encoding="utf-8")
        reg.write_bytes(good)

    def test_the_gate_the_client_place_and_the_section_draft_refuse(self):
        summary = "Phase two can start once the paperwork is signed."
        self.assertEqual(self.findings(summary), [])                        # control: a readable register, a clean report
        self.assertIn(f"{PERSON} is named but owns only items a client report can't show", self.findings(f"{PERSON} helps."))
        for what, breaks in self.broken():
            breaks()
            got = self.findings(summary)
            self.assertTrue(any("people register couldn't be read" in f for f in got), (what, got))
            req = {"option": "polish", "text": "Testing could start late.", "code": "ABC", "place": "client", "document": DOC}
            ctx = self.py(f"try:\n    print(json.dumps(edit_ai.context({req!r})))\n"
                          "except edit_ai.Refused as e:\n    print(json.dumps({'refused': str(e)}))")
            self.assertIn("people register couldn't be read", ctx.get("refused", ""), (what, ctx))
            sec = self.ctx({**SECTION, "document": DOC})
            self.assertIn("people register couldn't be read", sec.get("refused", ""), (what, sec))
            if what != "not text":              # (an undecodable register already stops the internal facts elsewhere: not #127's)
                self.assertNotIn("refused", self.ctx({**SECTION, "document": WEEKLY_DOC}), what)   # internal: no names check
        self.assertEqual(self.findings(summary), [])                        # restored: passes again


PAD = "a" * 2100                                              # longer than the gate reads of one address (LONG_TOKEN)


class TheReviewOf199ac40(Base):
    """#127 review of 199ac40: an address longer than the gate reads, or holding a quote, is read to where Word's link ends or
    fails closed; no quadratic pattern is left; names are found however they are spaced; a label check is reported only for the
    labels; a creaite: link with a space after its colon, or encoded six times, is dropped."""

    def plain(self, text):
        return self.py(f"print(json.dumps(client_leak.plain_findings(client_leak.connect(), 'ABC', {text!r})))")

    def both(self, text):
        return self.findings(f"Progress. {text}"), self.plain(f"Progress. {text}")

    def test_an_address_longer_than_the_gate_reads_fails_closed(self):
        tails = ("/ZEBRAINTERNAL%20vendor%20is%20failing%20to%20deliver", "?who=Quentin%20Marlow", "/internal%2Donly",
                 "?r=ABC%2DA%2D004")
        for tail in tails:
            address = f"https://x.example.com/{PAD}{tail}"
            for text in (f"[s]({address})", address, f'<a href="{address}">s</a>'):
                for got in self.both(text):
                    self.assertTrue(any(f.startswith(TOO_LONG) for f in got), (tail, text[:30], got))
        underscores = f"[s](https://x.example.com/{'_' * 2100}{tails[1]})"   # the words drop the underscores; Word shows them
        for got in self.both(underscores):
            self.assertTrue(any(f.startswith(TOO_LONG) for f in got), got)
        got = self.py("import docx_tools\nprint(json.dumps(docx_tools.plain(" + repr(f"[s](https://x.example.com/{PAD}{tails[1]})") + ")))")
        self.assertTrue(got.endswith("Quentin%20Marlow)"), got[-40:])               # what Word shows: the whole address
        for got in self.both(f"A long word {PAD} and a short [link](https://x.example.com/page)."):
            self.assertEqual(got, [])                                                # control: a long word holding no link

    def test_an_address_with_a_quote_or_an_angle_is_read_to_where_words_link_ends(self):
        for text, why in (('[s](https://x.example.com/"Quentin%20Marlow)', f"{PERSON} is named"),
                          ('[s](https://x.example.com/"ZEBRAINTERNAL%20vendor%20is%20failing%20to%20deliver)',
                           "it holds the internal health reason"),
                          ("[s](https://x.example.com/<Quentin%20Marlow>)", f"{PERSON} is named"),
                          ('[s](https://x.example.com/"ABC%2DA%2D004")', f"{INTERNAL_ID} isn't client-visible"),
                          ("[s](https://x.example.com/it's/ABC%2DA%2D004)", f"{INTERNAL_ID} isn't client-visible")):
            for got in self.both(text):
                self.assertTrue(any(f.startswith(why) for f in got), (text, got))
        for got in self.both("[plan](https://client.example.com/it's/\"q\"/plan.pdf)"):
            self.assertEqual(got, [])                                                # control: a quote in a client-safe address

    def test_emphasis_and_images_are_linear(self):
        """100 KB of "![", "*a " or "_a " took up to 15 s in md_runs and creaite_doc._plain (the old unbounded patterns)."""
        code = (TIMER + "import docx_tools\ncon = client_leak.connect()\nout = {}\n"
                "def doc(s):\n    d = report_doc.client_doc('ABC')\n"
                "    next(x for x in d['sections'] if x['id'] == 'summary')['text'] = s\n    return d\n"
                "RUNS = (('findings', lambda s, d: client_leak.findings(d)), ('plain', lambda s, d: client_leak.plain_findings(con, 'ABC', s)),"
                " ('client_problems', lambda s, d: edit_ai.client_problems('ABC', s)), ('md_runs', lambda s, d: docx_tools.md_runs(s)))\n"
                "for name, p in (('![', '!['), ('*a ', '*a '), ('_a ', '_a ')):\n"
                "    small, large = (p * 50000)[:25000], (p * 50000)[:100000]\n    ds, dl = doc(small), doc(large)\n"
                "    for f, run in RUNS:\n"
                "        out[name + ' ' + f] = [took(lambda: run(small, ds)), took(lambda: run(large, dl))]\n"
                "out['_plain 300 KB'] = [took(lambda: creaite_doc._plain('![' * 37500)), took(lambda: creaite_doc._plain('![' * 150000))]\n"
                "print(json.dumps(out))")
        self.assert_linear(self.py(code))
        got = self.py("import docx_tools\nprint(json.dumps([docx_tools.plain(t) for t in ('**Bold** and _italic_ and *it* and ~~gone~~',"
                      " 'snake_case_word stays', '2 * 3 * 4')]))")
        self.assertEqual(got, ["Bold and italic and it and gone", "snake_case_word stays", "2 * 3 * 4"])     # unchanged

    def test_a_name_is_found_however_it_is_spaced(self):
        found = f"{PERSON} is named but owns only items a client report can't show"
        for text in ("Waiting on Quentin  Marlow.", "Waiting on Quentin\nMarlow for sign-off.", "Waiting on Quentin Marlow.",
                     "Waiting on Quentin\tMarlow.", "Waiting on Quen​tin Marlow.", "Waiting on Quentin​ Marlow.",
                     "See [the auditor](https://x.example.com/%28Quentin%20Marlow%29).",
                     "See [the auditor](https://x.example.com/%28Quentin%C2%A0%20Marlow%29)."):
            for got in self.both(text):
                self.assertIn(found, got, repr(text))
            self.assertIn(f"{PERSON} isn't named in the text",
                          self.py(f"print(json.dumps(edit_ai.client_problems('ABC', {text!r})))"), repr(text))
        got = self.py("print(json.dumps(sorted(client_leak.named('Waiting on Quentin Marlow.', ['Quentin\u00a0 Marlow', 'Ada\u200b Vale']))))")
        self.assertEqual(got, ["Quentin\u00a0 Marlow"])                          # a name stored oddly spaced is read the same way
        for got in self.both("Waiting on Quentin Marlowe's team."):
            self.assertEqual(got, [])                                                # control: a longer name isn't this one

    def test_a_creaite_link_with_a_space_after_its_colon_is_dropped_whole(self):
        for link in (f"creaite: item/{INTERNAL_ID}", f"[p](creaite: item/{INTERNAL_ID})", f"CREAITE :item/{INTERNAL_ID}",
                     f"creaite: item/{INTERNAL_ID}", "creaite: note/7", "[the auditor](creaite: person/Quentin%20Marlow)"):
            text = f"Before. {link} After."
            self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {text!r})))").split(),
                             ["Before.", "After."], repr(link))
        prose = "Text creaite: notes/ are kept"
        self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {prose!r})))"), prose)

    def test_an_address_encoded_past_what_the_gate_decodes_fails_closed(self):
        six, seven = "creaite%25252525253a", "creaite%2525252525253a"     # "creaite:" %-encoded six and seven times
        for link in (f"[p]({seven}item/{INTERNAL_ID})", f"<{seven}item/{INTERNAL_ID}>", f"{seven}item/{INTERNAL_ID}",
                     f'<a href="{seven}item/{INTERNAL_ID}">p</a>', f"[p]({seven}note/7)", f"[p]({six}item/{INTERNAL_ID})"):
            for got in self.both(link):
                self.assertTrue(any(f.startswith("a link address encoded more than") for f in got), (link, got))
            text = f"Before. {link} After."
            got = self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {text!r})))")
            self.assertNotIn("004", got, link)
            self.assertNotIn("note", got, link)
        five = "creaite%252525253a"                              # five times: read, and a client-visible item's link stays
        text = f"See [p]({five}item/ABC-A-002)."
        self.assertEqual(self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', {text!r})))"), text)
        self.assertEqual(self.findings(text), [])

    def client_findings(self, setup=""):
        if not (self.v.root / "system/staging/drafts/probe-client.html").exists():     # the draft, made while the labels work
            self.py("from pathlib import Path\nd = report_doc.client_doc('ABC')\n"
                    f"next(s for s in d['sections'] if s['id'] == 'summary')['text'] = 'See {INTERNAL_ID}.'\n"
                    "p = Path('system/staging/drafts/probe-client.html'); p.parent.mkdir(parents=True, exist_ok=True)\n"
                    "p.write_text(creaite_doc.dumps(d))\nprint(1)")
        return self.py("import review, tracker\np = 'system/staging/drafts/probe-client.html'\nclosed = []\nreal = tracker.connect\n"
                       "class Con:\n    def __init__(s): s.c = real()\n    def execute(s, *a): return s.c.execute(*a)\n"
                       "    def close(s): closed.append(1); s.c.close()\n    def __getattr__(s, n): return getattr(s.c, n)\n"
                       "tracker.connect = Con\n" + setup +
                       "out = {}\nfor name, blk in (('doc', {'draft': p, 'project': 'ABC'}), ('word', {'draft': 'x.docx', 'project': 'ABC'})):\n"
                       f"    review.draft_lines = lambda _p: ['See {INTERNAL_ID}.']\n"
                       "    out[name] = review.client_findings(blk)\nout['closed'] = len(closed)\nprint(json.dumps(out))")

    def test_a_label_check_failure_is_reported_only_for_the_labels_and_keeps_the_other_findings(self):
        ok = self.client_findings()
        self.assertEqual(ok["closed"], 2)                                             # the connection is closed each time
        for k in ("doc", "word"):
            self.assertEqual(ok[k], [f"{INTERNAL_ID} isn't client-visible but its ID appears"], k)
        got = self.client_findings("import sqlite3\nfor f in ('findings', 'plain_findings'):\n"
                                   "    setattr(client_leak, f, lambda *a: (_ for _ in ()).throw(sqlite3.OperationalError('no such table: actions')))\n")
        for k in ("doc", "word"):
            self.assertEqual(len(got[k]), 1, got[k])
            self.assertTrue(got[k][0].startswith("Couldn't check the client report against the tracker"), got[k])
            self.assertIn("no such table: actions", got[k][0])
        self.assertEqual(got["closed"], 2)
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:     # a test vault: break the labels directly
            con.execute("DROP TABLE labels")
            con.execute("CREATE VIEW labels AS SELECT name FROM item_labels")
            con.commit()
        got = self.client_findings()
        for k in ("doc", "word"):
            self.assertTrue(got[k][0].startswith("Couldn't check the label exclusions"), got[k])
            self.assertIn(f"{INTERNAL_ID} isn't client-visible but its ID appears", got[k][1:])
        self.assertEqual(got["closed"], 2)


# #127 round 4: characters Word shows as nothing (format characters, variation selectors, fillers), as code points


if __name__ == "__main__":
    unittest.main()

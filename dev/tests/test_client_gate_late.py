"""#127: the client gate on every client path, part 3 of 3 (the fixture is in client_gate_support.py). The data is fictional.

Run: python3 dev/tests/test_client_gate_late.py      (quick tier: no Chrome, no model)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client_gate_support import INTERNAL_ID, PERSON, Base, TOO_LONG  # noqa: E402


UNSEEN = [0x2065, 0x2066, 0x2067, 0x2068, 0x2069, 0x206A, 0x206F, 0x061C, 0x034F, 0xFE00, 0xFE0F, 0xE0041, 0xE0020, 0x17B4,
          0x17B5, 0x115F, 0x3164, 0xFFF9, 0x0600, 0x1D173, 0x200B]
NAMED = f"{PERSON} is named but owns only items a client report can't show"
HIDDEN = f"{INTERNAL_ID} isn't client-visible but its ID appears"


class TheReviewOf55967e3(Base):
    """#127 round 4 (review of 55967e3): an invisible character hides no name, ID or marker; %- or entity-encoded words outside
    any address are read; a name is found however its words are joined; the long-address check counts only the address and words
    its finding for what it found; the prompt filter drops more forms of a creaite: link, and the gate flags creaite:\\note."""

    def gate(self, texts):
        """{text: [findings, plain_findings, client_problems]}, each after "Progress. ", in one run."""
        return dict(zip(texts, self.py(
            "con = client_leak.connect()\nout = []\n"
            f"for t in {texts!r}:\n"
            "    t = 'Progress. ' + t\n    d = report_doc.client_doc('ABC')\n"
            "    next(s for s in d['sections'] if s['id'] == 'summary')['text'] = t\n"
            "    out.append([client_leak.findings(d), client_leak.plain_findings(con, 'ABC', t), edit_ai.client_problems('ABC', t)])\n"
            "print(json.dumps(out))")))

    def assert_found(self, cases, kinds=(0, 1, 2)):
        """Each text gets a finding starting with its reason on every path in `kinds` (0 the document, 1 plain, 2 the ✦)."""
        got = self.gate([t for t, _ in cases])
        for text, why in cases:
            for k in kinds:
                want = why if k < 2 else {NAMED: f"{PERSON} isn't named", HIDDEN: f"{INTERNAL_ID} isn't client-visible"}.get(
                    why, why.replace("it holds ", ""))             # the ✦'s own words
                self.assertTrue(any(f.startswith(want) for f in got[text][k]), (repr(text), k, want, got[text][k]))

    def test_an_invisible_character_hides_no_name_id_or_marker(self):
        cases = []
        for cp in UNSEEN:
            ch = chr(cp)
            cases += [(f"Waiting on Quen{ch}tin Marlow.", NAMED), (f"Blocked by ABC-A-0{ch}04.", HIDDEN),
                      (f"Note: internal{ch}-only.", "it holds an internal-only marker"), (f"A confi{ch}dential note.", "contains")]
        self.assert_found(cases)
        got = self.py("con = client_leak.connect()\nd = report_doc.client_doc('ABC')\n"     # a marker where the reason may stand
                      "next(s for s in d['sections'] if s.get('type') == 'health')['text'] = 'Behind plan. internal\\u2066-only.'\n"
                      "print(json.dumps([client_leak.findings(d), client_leak.plain_findings(con, 'ABC', "
                      "'OFF TRACK internal\\u2066-only.\\nProgress.')]))")
        for g in got:
            self.assertIn("it holds an internal-only marker", g)
        self.assertEqual(self.py("print(json.dumps(drafts.internal_findings(client_leak.connect(), 'ABC', "
                                 "'internal\\u200b-only', 'internal-only')))"), [])      # the original held it: not added
        for got in self.gate(["The build is on time️ and the paperwork is signed."]).values():
            self.assertEqual(got, [[], [], []])                    # control: an emoji's selector in client-safe text

    def test_encoded_words_outside_any_address_are_read(self):
        reason = "it holds the internal health reason"
        pad = "a" * 1000
        self.assert_found([
            ("See Quentin%20Marlow.", NAMED), ("See ABC%2DA%2D004.", HIDDEN), ("See internal%2Donly.", "it holds an internal-only marker"),
            ("See ZEBRAINTERNAL%20vendor%20is%20failing%20to%20deliver%20the%20build%20on%20time.", reason),
            ("[s](https://x.example.com/ ?who=Quentin%20Marlow)", NAMED),
            ("[s](https://x.example.com/　?r=ABC%2DA%2D004)", HIDDEN),
            ("See Quentin&#32;Marlow and nothing else.", NAMED), ("See ABC&#45;A&#45;004.", HIDDEN),
            ("See x.example.com/?who=Quentin%20Marlow", NAMED),
            ("See [a](https://x.example.com/Quentin&#37;20Marlow).", NAMED),
            (f"[s](https://x.example.com/{pad}\u0085{pad}a?who=Quentin%20Marlow)", NAMED),
            (f"[s](https://x.example.com/{pad}　{pad}a?who=Quentin%20Marlow)", NAMED)])
        for got in self.gate(["Phase two is 95% complete & tested; see https://client.example.com/a%20plan."]).values():
            self.assertEqual(got, [[], [], []])                    # control: a % and an & that hide nothing

    def test_a_name_is_found_however_its_words_are_joined(self):
        self.assert_found([(t, NAMED) for t in (
            "Waiting on Quentin-Marlow.", "Waiting on Quentin_Marlow.", "Waiting on Quentin.Marlow.", "Waiting on QuentinMarlow.",
            "Waiting on Quentin­Marlow.", "Mail quentin.marlow@example.com today.", "Waiting on Marlow, Quentin.",
            "Waiting on Quentín Marlow.", "Waiting on Quentin Marlów.", "See [a](https://x.example.com/QuentinMarlow).",
            "Waiting on **Quentin** Marlow.", "Waiting on [Quentin](https://x.example.com/) Marlow.",
            "Waiting _on Quentin Marlow_.")])
        got = self.py("print(json.dumps([sorted(client_leak.named(t, ['Max Well', 'Ada Vale', 'Quentin Marlow'])) for t in "
                      "('maxwell and adavale', 'Max-Well', 'Quentin Marlowe', 'QuentinMarlowe', 'xQuentinMarlow', 'Ada, Vale')]))")
        self.assertEqual(got, [[], ["Max Well"], [], [], [], []])  # short names never run together; a longer word isn't a name

    def test_the_long_address_check_reads_only_the_address_and_says_what_it_found(self):
        base = "https://x.example.com/"
        got = self.py("print(json.dumps([client_leak.unreadable_findings(t) for t in " + repr([
            f"[s]({base}{'a' * (2000 - len(base))})", f"[the plan]({base}{'a' * (2000 - len(base))}).",
            f"[s]({base}{'a' * (2001 - len(base))})", "%41" * 700, "&#65;" * 500, f"[s]({'a' * 2001})",
            "documents/" + "a" * 2001, "x" * 2500, "进度良好，完成率95%。" * 200]) + "]))")
        self.assertEqual(got[:2], [[], []])                        # an address of exactly 2000 characters, its label not counted
        self.assertTrue(got[2][0].startswith(TOO_LONG), got[2])
        for g in got[3:5]:                                          # a run of only %XX or only entities: not a link, still unread
            self.assertEqual(len(g), 1, g)
            self.assertTrue(g[0].startswith("text too long to check"), g)
        for g in got[5:7]:                                          # a relative address, in a link or bare
            self.assertTrue(g and g[0].startswith(TOO_LONG), g)
        self.assertEqual(got[7:], [[], []])                         # a long word, and a paragraph whose % encodes nothing

    def test_the_prompt_filter_drops_more_forms_and_the_gate_flags_a_note(self):
        links = [f"creaite:item/{w}{INTERNAL_ID}" for w in (" ", "\t", " ", "　", "\n", " ", "  ", " \n ")] + [
            f"[p](creaite:item/ {INTERNAL_ID})", f"creaite⁦:item/{INTERNAL_ID}", f"creaite:/ /item/{INTERNAL_ID}",
            f"creaite: item/ {INTERNAL_ID}", f"creaite\u2066: item/ {INTERNAL_ID}", "creaite:\\note/7", "creaite:\\\\note/7"]
        got = self.py("print(json.dumps([client_leak.drop_item_links('ABC', 'Before. ' + t + ' After.') for t in "
                      f"{links!r}]))")
        for link, g in zip(links, got):
            self.assertEqual(g.split(), ["Before.", "After."], repr(link))
        kept = ["Text creaite: notes/ are kept", "See [p](creaite://item/ABC-A-002)."]
        self.assertEqual(self.py(f"print(json.dumps([client_leak.drop_item_links('ABC', t) for t in {kept!r}]))"), kept)
        self.assert_found([("See creaite:\\note/7 now.", "a creaite link a client can't open"),
                           ("See creaite:\\\\note/7 now.", "a creaite link a client can't open")], (0, 1))


MARKER = "it holds an internal-only marker"


class TheReviewOf62593f6(Base):
    """#127 round 5 (review of 62593f6): every default-ignorable character is unseen, assigned or not, and the braille blank is a
    space; combining and enclosing marks hide no ID, marker or name; decoded text keeps its punctuation for the marker; more ways
    of writing a name and a backslash-escaped ID."""
    gate, assert_found = TheReviewOf55967e3.gate, TheReviewOf55967e3.assert_found

    def test_every_default_ignorable_character_is_unseen(self):
        cps = [cp for a, b in ((0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5),
                               (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164),
                               (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3),
                               (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF)) for cp in (a, (a + b) // 2, b)]
        cps += [0xE0080, 0xE0100, 0xE01EF, 0xE01F0]               # the reviewer's, and the variation selectors supplement
        got = self.py(f"print(json.dumps([edit_ai.unseen('a' + chr(cp) + 'b') for cp in {cps + [0x2800]!r}]))")
        self.assertEqual(got[:-1], ["ab"] * len(cps), [hex(c) for c, g in zip(cps, got) if g != "ab"])
        self.assertEqual(got[-1], "a b")                          # the braille blank draws as a space
        self.assert_found([(f"Waiting on Quen{chr(0xFFF0)}tin Marlow.", NAMED), (f"Blocked by ABC-A-0{chr(0xE0080)}04.", HIDDEN),
                           (f"Note: internal{chr(0xE01F0)}-only.", MARKER), (f"Waiting on Quentin{chr(0x2800)}Marlow.", NAMED),
                           (f"Blocked by ABC-A-0{chr(0xE0100)}04.", HIDDEN)])
        got = self.py(f"print(json.dumps(client_leak.drop_item_links('ABC', 'Before. creaite' + chr(0xFFF0) + "
                      f"':item/{INTERNAL_ID} After.')))")
        self.assertEqual(got.split(), ["Before.", "After."])

    def test_combining_marks_hide_no_id_marker_or_name(self):
        self.assert_found([(f"Blocked by ABC-A-0{chr(0x301)}04.", HIDDEN), (f"Note: internal{chr(0x336)}-only.", MARKER),
                           (f"Blocked by ABC-A-0{chr(0x20DD)}04.", HIDDEN), (f"Waiting on Quen{chr(0x20DD)}tin Marlow.", NAMED)])
        hindi = "\u0905\u0928\u093f\u0932 \u0915\u0941\u092e\u093e\u0930"          # a name whose vowels are marks, both folded
        got = self.py("print(json.dumps([sorted(client_leak.named(t, [" + repr(hindi) + ", 'Zo\u00eb Kent'])) for t in "
                      + repr([f"Met {hindi} today.", "Met Zoe\u0308 Kent today.", "Met Zoe Kent today.", "Met Zo Kent."]) + "]))")
        self.assertEqual(got, [[hindi], ["Zo\u00eb Kent"], ["Zo\u00eb Kent"], []])
        got = self.py("import sqlite3\nc = sqlite3.connect('system/tracker.db')\n"   # a test vault: an accented health reason
                      "c.execute(\"UPDATE projects SET health_reason = 'R\u00e9sum\u00e9 d\u00e9lay\u00e9' WHERE code = 'ABC'\")\n"
                      "c.commit()\nprint(json.dumps(drafts.internal_findings(client_leak.connect(), 'ABC', "
                      "'The R\u00e9sum\u00e9 d\u00e9lay\u00e9.')))")
        self.assertEqual(got, ["the internal health reason"])

    def test_decoded_text_keeps_its_punctuation_for_the_marker(self):
        oks = ["Costs are internal, only the licence is external &amp; billed separately.",   # "internal, only" isn't the marker
               "See https://client.example.com/documents%2Fplan for the plan."]           # an external page's path isn't creaite's
        for got in self.gate(oks).values():
            self.assertEqual(got, [[], [], []])
        self.assert_found([("Note: health%5Fdiff.", MARKER), ("Note: internal%2Donly.", MARKER)])
        link = "See [plan](https://client.example.com/documents/plan) and more"         # the documents/ safeguard, decoded too
        self.assertEqual(self.findings(f"Progress. {link} &amp; less."), [])
        got = self.py("d = report_doc.client_doc('ABC')\n"                 # an encoded marker where the reason may stand
                      "next(s for s in d['sections'] if s.get('type') == 'health')['text'] = 'Behind plan. internal%2Donly.'\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertIn(MARKER, got)

    def test_a_name_however_written_and_a_backslash_escaped_id(self):
        self.assert_found([(t, NAMED) for t in (
            "Waiting on Quentin J. Marlow.", "Waiting on Quentin J Marlow.", "Waiting on Marlow Quentin.", "Waiting on Quentin/Marlow.",
            "Waiting on Quentin|Marlow.", "Waiting on Quentin;Marlow.", "Waiting on Quentin\\Marlow.")] + [
            ("Blocked by ABC\\-A\\-004.", HIDDEN)])
        got = self.py("print(json.dumps([sorted(client_leak.named(t, [\"Ada O'Neill\", 'Ida O\u2019Hare', 'Al Mortimer', 'Al Lee', "
                      "'Quentin Marlow'])) "
                      "for t in ('Met Ada O\u2019Neill.', \"Met Ida O'Hare.\", 'see almortimer', 'Al Mortimer', 'Lee Al', "
                      "'Quentin Smarlow', 'Quentin a. Marlowe')]))")
        self.assertEqual(got, [["Ada O'Neill"], ["Ida O\u2019Hare"], [], ["Al Mortimer"], [], [], []])   # controls: short, longer



class TheReviewOfce5d66b(Base):
    """#127 round 6 (review of ce5d66b): control characters and noncharacters are read as Word draws them (gone, or a line break
    where a Word export breaks the line), and docx_tools.esc never writes one XML doesn't allow."""
    gate, assert_found = TheReviewOf55967e3.gate, TheReviewOf55967e3.assert_found

    def test_control_characters_and_noncharacters_are_unseen(self):
        gone = ["\x00", "\x07", "\x1b", "\x1f", "\x7f", "\x80", "\x9d", "\ufdd0", "\ufdef", "\ufffe", "\uffff", "\U0001fffe",
                "\U0010ffff"]
        breaks = ["\x0b", "\x0c", "\x1c", "\x1e", "\x85"]
        cases = gone + breaks + ["\t", "\r"]
        got = self.py(f"print(json.dumps([edit_ai.unseen('a' + c + 'b') for c in {cases!r}]))")
        self.assertEqual(got, ["ab"] * len(gone) + ["a\nb"] * len(breaks) + ["a\tb", "a\rb"])
        self.assert_found([("Waiting on Quen\x9dtin Marlow.", NAMED), ("Waiting on Quen\x07tin Marlow.", NAMED),
                           ("Note: internal\x9d-only.", MARKER), ("Note: internal\x07-only.", MARKER),
                           ("Blocked by ABC-A-0\ufdd004.", HIDDEN), ("Blocked by ABC-A-0\x0004.", HIDDEN)])

    def test_esc_writes_only_characters_xml_allows(self):
        got = self.py("import docx_tools, xml.etree.ElementTree as ET\nout = []\n"
                      "for c in ['\\x00', '\\x07', '\\x0b', '\\x0c', '\\x1f', '\\ufffe', '\\uffff', '\\ud800']:\n"
                      "    x = '<t>' + docx_tools.esc('a' + c + 'b<&>') + '</t>'\n"
                      "    out.append(ET.fromstring(x.encode('utf-8')).text)\n"
                      "print(json.dumps(out))")
        self.assertEqual(got, ["ab<&>", "ab<&>", "a b<&>", "a b<&>", "ab<&>", "ab<&>", "ab<&>", "ab<&>"])


    def test_common_word_names_are_not_read_in_prose(self):
        """Finding 1: the surname first without a comma counts only with both words capitalised, and an initial only in capitals."""
        reg = ["Will Price", "Grace Day", "Mark Field", "Rose Hill", "Quentin Marlow"]
        prose = ["The price will rise after the contract review.", "A 30 day grace period applies.", "Field mark-up is due on Friday.",
                 "Hill rose to the occasion.", "Will a price cap apply?", "Waiting on Quentin j. Marlow.", "Waiting on marlow quentin."]
        names = ["Waiting on Marlow, Quentin.", "Waiting on Quentin J. Marlow.", "Waiting on MARLOW Quentin.",
                 "Waiting on Marlow Quentin.", "Waiting on quentin marlow.", "Price Will signed it."]
        got = self.py(f"print(json.dumps([sorted(client_leak.named(t, {reg!r}, every=True)) for t in {prose + names!r}]))")
        self.assertEqual(got, [[]] * len(prose) + [["Quentin Marlow"]] * 5 + [["Will Price"]])

    def test_a_comma_reads_the_same_decoded_and_every_name_is_reported(self):
        """Finding 5: "Quentin,Marlow" is a name and "Quentin, Marlow" a list, with an &amp; elsewhere or not; every register name
        that matches is reported on the gate's paths (Quentin and Quentin Marlow)."""
        got = self.py("print(json.dumps([sorted(client_leak.named(client_leak.with_decoded(t), ['Quentin Marlow'])) for t in "
                      "('Waiting on Quentin,Marlow.', 'Waiting on Quentin,Marlow &amp; co.', 'Waiting on Quentin, Marlow.', "
                      "'Waiting on Quentin, Marlow &amp; co.')]))")
        self.assertEqual(got, [["Quentin Marlow"], ["Quentin Marlow"], [], []])
        got = self.py("con = client_leak.connect()\n"
                      "client_leak.people = lambda con, code, blocking=None: (set(), {'Quentin', 'Quentin Marlow'})\n"
                      "edit_ai._register_names = lambda: ['Quentin', 'Quentin Marlow']\n"
                      "t = 'Waiting on Quentin; Marlow.'\n"
                      "print(json.dumps([client_leak.name_findings(con, 'ABC', t), edit_ai.client_problems('ABC', t), "
                      "sorted(edit_ai.names(t, ['Quentin', 'Quentin Marlow'])), edit_ai.client_problems('ABC', t, t)]))")
        self.assertEqual([sorted(f.split(" is")[0] for f in got[0]), sorted(f.split(" isn")[0] for f in got[1] if "named" in f),
                          got[2]], [["Quentin", "Quentin Marlow"], ["Quentin", "Quentin Marlow"], ["Quentin Marlow"]])
        self.assertEqual([f for f in got[3] if "named" in f], [])          # the original names both: neither is new

    def test_sentence_punctuation_keeps_the_marker_apart_and_spaced_marks_join_it(self):
        """Findings 3 and 4: in the words form "internal. Only" (any of . ; ! ? : with an &amp; elsewhere) is prose; "internal ; only",
        "internal . only" and "internal:only" are the marker with or without one; an underscore joins it when decoded."""
        oks = ["Planning is internal. Only their PMO attends &amp; signs.", "Costs are internal; only the licence &amp; support.",
               "Planning is internal! Only the PMO &amp; sponsor.", "Is it internal? Only the PMO &amp; sponsor know.",
               "Costs are internal: only the licence &amp; support are external.", "Costs are internal; only the licence is billed.",
               "Planning is internal. Only their PMO attends."]
        for text, got in self.gate(oks).items():
            self.assertEqual(got, [[], [], []], text)
        self.assert_found([(t, MARKER) for t in ("Note: internal ; only.", "Note: internal . only.", "Note: internal:only.",
                                                 "Note: internal ; only &amp; more.", "Note: internal:only &amp; more.")])
        self.assert_found([("Note: internal_only &amp; more.", MARKER)], kinds=(0, 1))

    def test_every_apostrophe_folds(self):
        got = self.py("print(json.dumps([sorted(client_leak.named(t, [\"Ada O'Neill\"])) for t in "
                      "('Met Ada O\u2018Neill.', 'Met Ada O\u02bcNeill.', 'Met Ada O\u2032Neill.', 'Met Ada O\u2019Neill.')]))")
        self.assertEqual(got, [["Ada O'Neill"]] * 4)


    def test_emphasis_marks_hide_no_marker_wording_or_id(self):
        """The coordinator's finding: the exports take Markdown's marks off ("internal _only_" shows "internal only"), so the gate
        reads the text as they show it too (client_leak.as_shown), nested marks, strike-through and backticks included."""
        wraps = ["_{}_", "*{}*", "**{}**", "~~{}~~", "`{}`", "**_{}_**", "**~~{}~~**", "_**{}**_"]
        cases = [(f"Note: internal {w.format('only')} now.", MARKER) for w in wraps]
        cases += [(f"Note: {w.format('internal')}-only now.", MARKER) for w in wraps]
        cases += [(f"Blocked by {w.format(INTERNAL_ID)} now.", HIDDEN) for w in ("~~{}~~", "**_{}_**", "`{}`")]
        self.assert_found(cases)
        wording = [f"Note: Line up the {w.format('quiet')} audit." for w in wraps]
        for text, got in self.gate(wording).items():
            for k in range(3):
                self.assertTrue(any("wording appears" in f for f in got[k]), (text, k, got[k]))
        got = self.py("d = report_doc.client_doc('ABC')\n"                 # a marker where the reason may stand
                      "next(s for s in d['sections'] if s.get('type') == 'health')['text'] = 'Behind plan. internal ~~only~~.'\n"
                      "print(json.dumps(client_leak.findings(d)))")
        self.assertIn(MARKER, got)
        for got in self.gate(["The *quick* review and the _snake_case_ field are **done**."]).values():
            self.assertEqual(got, [[], [], []])                          # control: emphasis on client-safe words


class TheReviewOfc39f6c4(Base):
    """#127 round 7 (review of c39f6c4): no check reads from one form of a text into the next (as written, as shown, decoded); a
    shorter name inside an allowed one is not someone else; an initial in any script; one rule for the punctuated marker; emphasis
    inside a word and nesting of any depth read as the HTML and PDF exports show them; a lone surrogate hides nothing."""
    gate, assert_found = TheReviewOf55967e3.gate, TheReviewOf55967e3.assert_found

    def assert_clean(self, texts, gate=None):
        for text, got in (gate or self.gate)(texts).items():
            self.assertEqual(got, [[], [], []], text)

    def gate_as_is(self, texts):
        """gate, with each text as the whole summary (no "Progress. " before it): where it starts matters here."""
        return dict(zip(texts, self.py(
            "con = client_leak.connect()\nout = []\n"
            f"for t in {texts!r}:\n"
            "    d = report_doc.client_doc('ABC')\n"
            "    next(s for s in d['sections'] if s['id'] == 'summary')['text'] = t\n"
            "    out.append([client_leak.findings(d), client_leak.plain_findings(con, 'ABC', t), edit_ai.client_problems('ABC', t)])\n"
            "print(json.dumps(out))")))

    def test_no_check_reads_across_two_forms_of_a_text(self):
        """Finding 1: the as-written text ends "…internal", its shown or decoded copy starts "Only…": not the marker; nor a name
        ending one form and starting the next. The marker hidden by emphasis is still found."""
        self.assert_clean(["Only _two_ reviewers are needed; the rest of the review is internal",
                           "Only **approved** figures go to the board; drafts stay internal",
                           "Only the `export` file changes. The rest stays internal",
                           "Only A &amp; B go out; the rest stays internal",
                           "Marlow said **yes** to Quentin", "Marlow said yes &amp; thanks to Quentin"], gate=self.gate_as_is)
        self.assert_found([("Note: internal _only_.", MARKER), ("Note: _internal-only_.", MARKER)])
        for text, got in self.gate(["See creaite:item/\nABC-A-004 now."]).items():     # the join is never shown in a finding
            self.assertTrue(got[0] and got[1], text)
            self.assertFalse([f for k in got for f in k if "qqjoinqq" in f], got)

    def test_a_shorter_name_inside_an_allowed_one_is_not_another_person(self):
        """Finding 2: Sam Patel may be shown; "Sam" is another person's alias. "Sam Patel will run it" names only Sam Patel; a Sam
        standing on its own still counts."""
        got = self.py("client_leak.people = lambda con, code, blocking=None: ({'Sam Patel'}, set())\n"
                      "edit_ai._register_names = lambda: ['Sam Patel', 'Sam Jones', 'Sam']\n"
                      "print(json.dumps([[f for f in edit_ai.client_problems('ABC', t) if 'named' in f] for t in "
                      "('Sam Patel will run the rehearsal.', 'Waiting on Sam Patel.', 'Sam Patel and Sam will run it.')]))")
        self.assertEqual(got, [[], [], ["Sam isn't named in the text"]])

    def test_a_list_separator_inside_an_allowed_name_hides_no_one(self):
        """Round 8: an allowed name's match joined by ; / | or a full stop after a word is two people, so it hides neither."""
        texts = ["We met Sam. Patel will run the rehearsal.", "Thanks to Sam; Patel signs off.", "Ask Sam / Patel for it.",
                 "Ask Sam | Patel for it.", "Sam; Patel; Khan attend.", "Ali; Khan attend.", "Sam Patel will run the rehearsal.",
                 "Sam-Patel will run it.", "Sam P. Patel will run it.", "Sam Patel and Sam will run it."]
        got = self.py("client_leak.people = lambda con, code, blocking=None: ({'Sam Patel', 'Ali Khan'}, set())\n"
                      "edit_ai._register_names = lambda: ['Sam Patel', 'Ali Khan', 'Sam', 'Patel', 'Khan', 'Ali']\n"
                      f"print(json.dumps([sorted(f.split(' isn')[0] for f in edit_ai.client_problems('ABC', t) if 'named' in f) "
                      f"for t in {texts!r}]))")
        self.assertEqual(got, [["Patel", "Sam"]] * 4 + [["Khan", "Patel", "Sam"], ["Ali", "Khan"], [], [], [], ["Sam"]])

    def test_an_initial_in_any_script(self):
        """Finding 3: a capital initial outside Latin-1, and a single letter in a script with no case, between a name's words."""
        reg = ["Quentin Marlow", "\u0418\u0432\u0430\u043d \u041f\u0435\u0442\u0440\u043e\u0432", "\u738b \u660e"]
        texts = ["Waiting on Quentin \u0141. Marlow.", "Waiting on \u0418\u0432\u0430\u043d \u0411. \u041f\u0435\u0442\u0440\u043e\u0432.",
                 "\u738b \u5c0f \u660e", "Waiting on Quentin \u0142. Marlow.", "Will a price cap apply?"]
        got = self.py(f"print(json.dumps([sorted(client_leak.named(t, {reg + ['Will Price']!r}, every=True)) for t in {texts!r}]))")
        self.assertEqual(got, [[reg[0]], [reg[1]], [reg[2]], [], []])

    def test_an_ideographic_character_is_an_initial_only_in_an_ideographic_name_or_with_a_dot(self):
        """Round 8: "Mark 中 Field" and "Mark の Field" are not Mark Field (a CJK or kana character is a word, not an initial),
        "Mark 中. Field" is; between the words of a name in that script it may still stand alone ("王 小 明" for 王 明)."""
        reg = ["Mark Field", "王 明", "山田 太郎"]
        texts = ["Mark 中 Field items.", "Mark の Field items.", "Mark 中. Field items.", "王 小 明",
                 "山田 の 太郎", "Mark ب Field items."]
        got = self.py(f"print(json.dumps([sorted(client_leak.named(t, {reg!r}, every=True)) for t in {texts!r}]))")
        self.assertEqual(got, [[], [], [reg[0]], [reg[1]], [reg[2]], [reg[0]]])

    def test_one_rule_for_the_punctuated_marker(self):
        """Finding 4: up to three of . : ; , with no space is the marker, unless "Only" starts a sentence or the word runs on into a
        file name, domain or address; with a space before, only when nothing but punctuation follows "only"."""
        self.assert_clean(["See internal.only.yaml for it.", "Host internal.only.example.org is up.",
                           "Mail internal.only@example.com today.", "Keep it internal.Only the totals go.",
                           "Costs are internal : only licences go.", "Note: internal ; Only the totals."])
        self.assert_found([(f"Note: {t}.", MARKER) for t in ("internal ; only", "internal . only", "internal:only", "internal;only",
                                                             "internal,only", "internal::only", "internal..only", "internal;;only",
                                                             "INTERNAL.ONLY")])
        self.assert_found([(f"Keep it {t}.", MARKER) for t in ("internal,only", "internal::only", "internal..only",
                                                                "internal;;only")])   # round 8: mid-sentence, not after a label

    def test_the_marker_exceptions_need_a_sentence_or_a_lower_case_run_on(self):
        """Round 8: "Only" starts a sentence only with a space and a lower-case word after it, and a file name, domain, address or
        path runs on only in lower case (a path only inside one); a marker standing alone as a status is the marker."""
        self.assert_found([(t, MARKER) for t in (
            "Internal.Only", "Internal:Only", "Internal;Only", "INTERNAL:Only", "Note: internal.Only.", "**Internal.Only**",
            "Status: internal . Only", "Note: internal ;\nOnly", "INTERNAL.ONLY.DRAFT", "Label: internal.only.Do not forward.",
            "internal.only.Final", "Status: internal:only/draft", "Status: internal.only/v2", "Note: internal.only\\draft",
            "Status: internal ; only do not forward", "Keep it internal:Only.", "Keep it internal ; Only.",
            "Note: INTERNAL.ONLY@ACME", "Note: internal.only@")])
        self.assert_clean(["Config lives in internal.only.yaml in the repo.", "Point DNS at internal.only.example.org today.",
                           "Write to internal.only@example.com for access.", "Keep it internal. Only the totals go.",
                           "The path is /srv/internal.only/data on the server.", "Version internal.only.v2 is the public label.",
                           "Item: Internal . Only the board signs.", "Scope remains internal ; only the training is shared.",
                           "Data is internal:Only aggregated data leaves.", "The path internal.only/config holds it."])
        bare = ["internal.only\\draft", "Internal.Only", "INTERNAL.ONLY.DRAFT", "internal.only.Final", "Status: internal . Only"]
        self.assertEqual(self.py(f"print(json.dumps([client_leak.marked(t) for t in {bare!r}]))"), [True] * len(bare))

    def test_emphasis_inside_a_word_and_any_depth_of_nesting(self):
        """Finding 5: the HTML and PDF exports draw emphasis inside a word ("inter*nal*-only" shows "internal-only"), and nesting
        is undone until nothing changes; an underscore inside a word and "2*3*4" stay as they are."""
        self.assert_found([("Note: inter*nal*-only.", MARKER), ("Note: inter****nal-only.", MARKER),
                           ("Note: ~~**__*_internal_*__**~~-only.", MARKER), ("Blocked by ABC-A-0*0*4 now.", HIDDEN),
                           ("Waiting on Quen*tin* Marlow.", NAMED)])
        self.assert_found([(t, MARKER) for t in ("Note: inter~~nal~~-only.", "Note: inter~~nal-only.", "Note: in~~ter~~nal~~-only.",
                                                 "Note: inter~~nal~~~~-only.", "Note: inter~~nal~~-o~~nly")])   # round 8: ~~ too
        for text, got in self.gate(["Note: Line up the q*uie*t audit."]).items():
            for k in range(3):
                self.assertTrue(any("wording appears" in f for f in got[k]), (text, k, got[k]))
        self.assert_clean(["Ratio 2*3*4 holds.", "The snake_case_field and my_internal_value are done."])

    def test_the_shown_form_is_worked_out_once(self):
        """Round 8, speed: a text with no emphasis inside a word is shown once, not twice, and the same text read by several
        checks is worked out once; the result is the same."""
        got = self.py("calls = []\nreal = client_leak._plain_shown\n"
                      "client_leak._plain_shown = lambda t: calls.append(t) or real(t)\n"
                      "a = client_leak.as_shown('Note: **bold** text.')\nb = client_leak.as_shown('Note: **bold** text.')\n"
                      "c = client_leak.as_shown('Note: inter*nal*-only.')\nn = len(calls)\n"
                      "client_leak.named('Quen*tin* Marlow', ['Quentin Marlow'])\nclient_leak.named('Quen*tin* Marlow', ['Quentin Marlow'])\n"
                      "print(json.dumps([n, a == b, c.split(client_leak.JOIN), client_leak._words_shown.cache_info().hits]))")
        self.assertEqual(got, [3, True, ["Note: inter*nal*-only.", "Note: internal-only."], 1])

    def test_a_lone_surrogate_is_unseen(self):
        """Finding 6: docx_tools.esc drops a lone surrogate, so the check does too."""
        self.assertEqual(self.py("print(json.dumps(edit_ai.unseen('a\\ud800b\\udfffc')))"), "abc")
        self.assert_found([("Waiting on Quen\ud800tin Marlow.", NAMED), ("Blocked by ABC-A-0\udfff04.", HIDDEN),
                           ("Note: internal\ud800-only.", MARKER)])


if __name__ == "__main__":
    unittest.main()

"""#265 review M1, M2, L1, L2: what the saved calendar keeps of a meeting.

Run: python3 dev/tests/test_calendar_sanitise.py      (quick tier: plain code and throwaway vaults, no Chrome, no Claude)

- M1: no join link, passcode, PIN, meeting ID or dial-in number reaches calendar.json, in the invite's body, the place, the title,
  an attachment name, an attendee name or the organiser, however it is written (other languages, full-width letters, zero-width
  characters, split by tags, escaped, URL-encoded, an unlisted provider, a short link). Ordinary text and links survive.
- M2: the sensitivity is read after case, spacing, zero-width characters and look-alike forms; anything but empty, normal or none
  is confidential; private or personal is "Busy".
- L1: the empty-reply guard counts the meetings that are KEPT (after filtering), from today on.
- L2: days outside the window are dropped, an ID repeated on a day is kept once, an oversize reply is refused cleanly.

All names, addresses and numbers are made up.
"""
import json
import sys
import time
import unittest
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import invite_clean  # noqa: E402
import sweep  # noqa: E402
from test_tracker import Vault  # noqa: E402

ZW = "​"
KEEP = "Agenda: budget"

# each is one body line (or a few) that must not survive; fictional hosts, numbers and codes
BODIES = {
    "teams link": "Join here https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc",
    "keyed zoom link": "https://us02web.zoom.us/j/81230000?pwd=abc",
    "zoom vanity room": "https://acme.zoom.us/my/room",
    "meet": "meet.google.com/abc-defg-hij",
    "webex": "https://acme.webex.com/acme/j.php?MTID=m1",
    "goto": "https://meet.goto.com/123456789",
    "gotomeeting": "https://global.gotomeeting.com/join/123456789",
    "bluejeans": "https://bluejeans.com/123456789/4321",
    "chime": "https://chime.aws/1234567890",
    "whereby": "https://whereby.com/acme-room",
    "short link": "Join: https://bit.ly/3xYzAbC",
    "safelink wrapper": "https://eur01.safelinks.example.test/?url=https%3A%2F%2Fzoom.us%2Fj%2F1%3Fpwd%3Dabc",
    "encoded key": "https://video.example.net/j/1%3Fpwd%3Dabc",
    "tel with pin": "tel:+15550001111,,123456#",
    "dial-in with hash code": "Dial 0800 000 0000 then 998877#",
    "meeting id": "Meeting ID: 812 3456 7890",
    "access code": "Access code: 2468 1357",
    "conference code": "Conference code 778899",
    "participant code": "Participant code: 112233",
    "host code": "Host code: 556677",
    "german": "Kenncode: 4j7Kq2\nPasswort: abc123\nZugangscode 4455",
    "french": "Code secret : 9988\nMot de passe : abc",
    "spanish": "Código de acceso: 5544\nContraseña: xyz1",
    "arabic": "رمز المرور: 1234\nكلمة المرور: ١٢٣٤",
    "chinese": "会议密码：123456",
    "full-width PIN": "ＰＩＮ: 4321",
    "full-width link": "ｈｔｔｐｓ://zoom.us/j/1?pwd=abc",
    "split across paragraphs": "<p>Pass</p><p>code: 4321</p>",
    "split by a tag": "<p>Pass<span>code</span>: 4321</p>",
    "label then value on the next line": "<p>Passcode:</p><p>4321</p>",
    "table label and value": "<p>PIN</p><p>445566</p>",
    "meeting id alone": "Meeting ID\n812 345 678",
    "link in an href only": '<a href="https://zoom.us/j/1?pwd=abc">Click to join</a>',
    "unlisted provider, join text": '<a href="https://video.example.net/r/xyz">Click to join</a>',
    "unlisted provider, bare link": "Join the call: https://video.example.net/r/xyz",
    "escaped link": "https&#58;//zoom&#46;us/j/1?pwd=abc",
    "double-escaped": "https&amp;#58;//zoom&amp;#46;us/j/1",
    "zero-width inside the host": "https://zoom" + ZW + ".us/j/1",
    "zero-width inside the label": "Pass" + ZW + "code: 4321",
    "cyrillic look-alike label": "P\u0430sscode: 4321",
    "cyrillic look-alike host": "https://z\u043e\u043em.us/j/1",
    "password": "Meeting password 7788",
    "webinar id": "Webinar ID: 812 345 678",
    "bare id": "ID: 812 345 678",
    "hyphenated meeting-id": "Meeting-ID 812 345 678",
    "passkey": "Passkey: tr0ub4",
    "host key": "Host key 456789",
    "key": "Key: tr0ub4dor",
    "token": "Token: abcdef",
    "otp": "OTP: 123456",
    "access": "Access: 445566",
    "conference bridge": "Conference bridge: 55512",
    "italian": "Codice: 99887\nPassword riunione: abc",
    "portuguese": "C\u00f3digo da reuni\u00e3o: 777",
    "dutch": "Vergadercode: 1234",
    "turkish": "\u015eifre: 1234\nToplant\u0131 kimli\u011fi: 812 345",
    "russian": "\u041a\u043e\u0434 \u043a\u043e\u043d\u0444\u0435\u0440\u0435\u043d\u0446\u0438\u0438: 4444",
    "japanese": "\u4f1a\u8b70\uff29\uff24: 812 345 678",
    "korean": "\ud68c\uc758 \uc554\ud638: 1234",
    "german tel with extension": "Tel.: +49 30 1234567 ext. 445566",
    "number with pause": "0800 000 0000 pause 445566",
    "number with extension": "+44 20 7946 0000 x 445566",
    "international number": "+1 555 000 1111",
    "label then blank lines": "Passcode:\n\nab12cd",
    "label then two blank lines": "Passcode:\n\n\nab12cd",
    "table with an empty row": "<table><tr><td>PIN</td></tr><tr><td></td></tr><tr><td>445566</td></tr></table>",
    "pwd": "Pwd: 7788",
    "pin and number": "PIN number 998877",
    "dial-in word": "Dial-in: +44 20 0000 0000",
    "skype scheme": "skype:acme.room?call",
    "url with key": "Join URL https://example.net/j/9 id 1 secret 77",
}

# ordinary lines that must stay
BENIGN = ["Agenda: budget and the pilot plan", "Pinned items: three risks", "Code review of the supplier SOW",
          "Release 2.4 planning, see https://docs.example.test/plan/v2", "Passwords policy review",
          "Please read https://docs.example.test/a/b.pdf before", "Room 101", "Budget 2026 total 1,200,000 #3",
          "Call Sam about the pilot", "Attendees: Jane Doe, Sam Lee", "Key takeaways: three risks",
          "Review on 20.10.2026, 15 attendees expected", "Access to the building from 08:00"]


def event(**kw):
    return {"id": "ev-1", "title": "Pilot readiness review", "where": "Room 2", "teams": True, "organiser": "Jane Doe",
            "sensitivity": "normal", "body": "Notes", "attendees": ["Sam Lee"], **kw}


class BodyAndFields(unittest.TestCase):
    """M1: sweep.invite_text and sweep.calendar_row, in this process (no vault needed)."""

    def test_no_join_link_or_key_survives_in_a_body(self):
        for name, line in BODIES.items():
            with self.subTest(name):
                out = sweep.invite_text(KEEP + "\n" + line + "\nEnd")
                self.assertEqual(" ".join(out.split()), KEEP + " End", out)

    def test_ordinary_lines_survive(self):
        for line in BENIGN:
            with self.subTest(line):
                self.assertEqual(sweep.invite_text(line), line)

    def test_the_place_and_title_carry_no_join_link_or_key(self):
        cases = [("https://us02web.zoom.us/j/8123?pwd=abcdef", ""), ("https://zoom.us/j/8123", ""),
                 ("Zoom: https://acme.zoom.us/my/room", "Zoom:"), ("Room 2 (PIN 4321)", "Room 2"), ("Room 2", "Room 2"),
                 ("tel:+15550001111,,123456#", ""), ("Microsoft Teams Meeting", "Microsoft Teams Meeting")]
        for where, want in cases:
            with self.subTest(where):
                row = sweep.calendar_row(event(where=where), "09:00", "10:00", False)
                self.assertEqual(row["where"], want)
        row = sweep.calendar_row(event(title="Sync https://zoom.us/j/1?pwd=abc"), "09:00", "10:00", False)
        self.assertEqual(row["title"], "Sync")
        row = sweep.calendar_row(event(title="Budget (PIN 4321)"), "09:00", "10:00", False)
        self.assertEqual(row["title"], "Budget")                                 # v2.6 review: only the key and its value go
        for title, want in (("Code 2 review", "review"), ("Board Meeting ID 123 456 789 sync", "Board sync"),
                            ("Sync Passcode: 4321", "Sync"), ("PIN 4321", "Meeting")):
            with self.subTest(title):
                self.assertEqual(sweep.calendar_row(event(title=title), "09:00", "10:00", False)["title"], want)
        row = sweep.calendar_row(event(title="Kickoff", organiser="Jane https://bit.ly/abc123"), "09:00", "10:00", False)
        self.assertEqual(row["organiser"], "Jane")

    def test_attachment_and_attendee_names_carry_no_join_link_or_key(self):
        ev = event(attachments=[{"name": "agenda.docx"}, {"name": "join https://zoom.us/j/1?pwd=abc PIN 1234.ics"},
                                "Passcode 4321.txt"],
                   attendees=[{"name": "Dial-in PIN 4321", "email": "x@example.test"}, {"name": "Passcode: 9", "email": ""},
                              {"name": "Sam Lee", "email": "sam.lee@example.test"}])
        row = sweep.calendar_row(ev, "09:00", "10:00", False)
        self.assertEqual(row["attachments"], ["agenda.docx"])
        self.assertEqual([(a["name"], a["email"]) for a in row["attendees"]],
                         [("x@example.test", "x@example.test"), ("Sam Lee", "sam.lee@example.test")])
        self.assertNotIn("4321", json.dumps(row))


    def test_a_label_cut_from_its_value_by_a_very_long_line_does_not_let_the_value_through(self):
        """A line over the look-at limit is cut at a space; "Meeting" at the end of one piece and "ID 812 345" at the start of the
        next must not let the value through, wherever the cut falls."""
        for label in ("Meeting ID", "Passcode", "PIN", "Host key"):
            for pad in range(1950, 2010, 4):
                with self.subTest(label=label, pad=pad):
                    line = "word " * (pad // 5) + label + " 812345678 end"
                    self.assertNotIn("812345678", sweep.invite_text(line))

    def test_a_cleaned_row_cleans_to_itself(self):
        row = sweep.calendar_row(event(body="Agenda: budget\nPasscode: 4321", where="Room 2", attachments=["pack.pdf"]),
                                 "09:00", "10:00", False)
        self.assertEqual(invite_clean.clean_row({"id": "e", **row}), {"id": "e", **row})


class Timing(unittest.TestCase):
    """Round 2: a crafted invite cannot stall the calendar save. Every case is 60,000 characters (the body's look-at limit; a title
    or name 20,000 and 60,000) and must finish well inside two seconds; the times are printed."""

    N = 60000
    BODIES = {
        "unclosed a href": "<a href=" * (N // 8), "a repeated": "<a " * (N // 3), "li repeated": "<p><li " * (N // 7),
        "script repeated": "<p><script " * (N // 11), "style then script": "<p><style>" + "<script " * (N // 8),
        "one a href and text": "<a href=" + "x" * N, "spaces": "a" + " " * N, "zero-width": "a\u200b" * (N // 2),
        "combining marks": "a" + "\u0301" * N, "nested tags": "<div><span>" * (N // 11), "digit run": "1" * N,
        "digits and spaces": "1 " * (N // 2), "many %3F": "%3F" * (N // 3), "dotted": "a." * (N // 2),
        "pass repeated": "pass " * (N // 5), "meeting repeated": "meeting " * (N // 8), "dial repeated": "dial 1 " * (N // 7),
        "pin repeated": "pin " * (N // 4), "scheme repeated": "http://" * (N // 7), "at signs": "a@" * (N // 2),
        "angle at": "<a@b>" * (N // 5), "hash digits": "123#" * (N // 4), "plus digits": "+1 " * (N // 3),
        "entities": "&amp;" * (N // 5), "long label then digits": "Meeting ID " + "1" * N,
        "tags with spaces": "<br " + " " * N, "unclosed comment": "<!--" * (N // 4), "html then long text": "<p>" + "a b " * (N // 4),
    }
    FIELDS = {"20k words": "a. " * 6666, "60k dots": "a." * (N // 2), "60k spaces": "x" + " " * N, "60k digits": "1" * N,
              "60k words": "a.b " * (N // 4), "60k at signs": "a@" * (N // 2), "60k urls": "http://a.b/ " * (N // 12)}

    def timed(self, name, fn, *args):
        start = time.perf_counter()
        fn(*args)
        took = time.perf_counter() - start
        print(f"  timing {name:28} {took:6.2f}s", file=sys.stderr)
        self.assertLess(took, 2.0, f"{name} took {took:.1f}s")

    def test_adversarial_bodies(self):
        for name, body in self.BODIES.items():
            with self.subTest(name):
                self.timed("body: " + name, sweep.invite_text, body)

    def test_adversarial_titles_places_and_names(self):
        for name, text in self.FIELDS.items():
            with self.subTest(name):
                ev = event(title=text, where=text, organiser=text, attendees=[{"name": text, "email": text}], attachments=[text])
                self.timed("event: " + name, sweep.calendar_row, ev, "09:00", "10:00", False)

    def test_thousands_of_attendees_and_attachments(self):
        ev = event(attendees=[{"name": f"Person {i}", "email": f"p{i}@example.test"} for i in range(20000)],
                   attachments=[f"file {i}.pdf" for i in range(20000)])
        rows = []
        self.timed("20,000 attendees", lambda: rows.append(sweep.calendar_row(ev, "09:00", "10:00", False)))
        self.assertLessEqual((len(rows[0]["attendees"]), len(rows[0]["attachments"])), (80, 40))

    def test_a_whole_event_of_the_worst_cases(self):
        ev = event(body=self.BODIES["unclosed a href"], title=self.FIELDS["60k dots"], where=self.FIELDS["60k digits"])
        self.timed("whole event", sweep.calendar_row, ev, "09:00", "10:00", False)


class Sensitivity(unittest.TestCase):
    """M2: the sensitivity fails closed."""

    def row(self, **kw):
        return sweep.calendar_row(event(organiser_email="jane.doe@example.test", recurrence="weekly", **kw), "09:00", "10:00", False)

    def test_anything_but_normal_is_confidential_and_keeps_only_title_and_times(self):
        values = ["confidential", "Confidential", "CONFIDENTIAL", " confidential", "confidential ", "Confidential" + ZW,
                  "Con" + ZW + "fidential", "C\u043enfidential", "Ｃonfidential", "highly confidential", "restricted", "secret",
                  "Strictly Confidential", "confidentiality", "2", 2, "unknown", True, "null", "Secret\n"]
        for v in values:
            with self.subTest(repr(v)):
                row = self.row(sensitivity=v)
                self.assertEqual(row, {"start": "09:00", "end": "10:00", "all_day": False, "title": "Pilot readiness review",
                                       "where": "", "teams": False, "private": False, "organiser": False,
                                       "sensitivity": "confidential"})

    def test_a_confidential_title_still_carries_no_join_link(self):
        row = self.row(sensitivity="restricted", title="Board https://zoom.us/j/1?pwd=abc")
        self.assertEqual(row["title"], "Board")

    def test_private_and_personal_are_busy(self):
        for v in ("private", "Private ", "PRIVATE", "personal", "Personal", "Priv" + ZW + "ate", "strictly private"):
            with self.subTest(v):
                row = self.row(sensitivity=v)
                self.assertEqual((row["title"], row["private"], row["where"], row["organiser"]), ("Busy", True, "", False))
                self.assertNotIn("body", row)
        row = self.row(sensitivity="confidential", private=True)
        self.assertEqual((row["title"], row["private"]), ("Busy", True))

    def test_the_private_flag_as_text(self):
        self.assertEqual(self.row(private="true")["title"], "Busy")
        self.assertEqual(self.row(private=1)["title"], "Busy")
        self.assertEqual(self.row(private="false")["title"], "Pilot readiness review")
        self.assertEqual(self.row(private=0)["title"], "Pilot readiness review")

    def test_normal_none_and_not_stated_keep_the_details(self):
        for v in ("normal", "Normal", " NORMAL ", "none", "", None):
            with self.subTest(repr(v)):
                row = self.row(sensitivity=v)
                self.assertEqual((row["where"], row["body"], row["sensitivity"]), ("Room 2", "Notes", "normal"))
        ev = event(organiser_email="jane.doe@example.test")
        del ev["sensitivity"]
        self.assertEqual(sweep.calendar_row(ev, "09:00", "10:00", False)["where"], "Room 2")

    def test_the_built_in_private_rule_and_the_followed_card_marker_read_variants(self):
        rule = {"builtin": "private", "on": True}
        for kind in ("mail", "teams", "calendar"):
            for value, private in (("Private ", True), ("personal", True), ("Priv\u200bate", True), ("Strictly Confidential", False),
                                   ("normal", False), (None, False), ("", False)):
                with self.subTest(kind=kind, value=value):
                    self.assertEqual(sweep.rule_matches(rule, {"kind": kind, "sensitivity": value}), private)
        for value, marker in (("Private ", "private"), ("PERSONAL", "private"), ("Strictly Confidential", "confidential"),
                              ("restricted", "confidential"), ("confidential", "confidential"), ("private", "private"),
                              ("normal", None), ("Normal ", None), (None, None), ("", None)):
            with self.subTest(marker=value):
                self.assertEqual(sweep.marker_of({"sensitivity": value}), marker)
        self.assertIsNone(sweep.marker_of({}))

    def test_the_ignore_rule_reads_the_same_sensitivity(self):
        self.assertTrue(sweep.message_of_event(event(sensitivity="Private​"))["private"])
        self.assertFalse(sweep.message_of_event(event(sensitivity="restricted"))["private"])


class SavedCalendar(unittest.TestCase):
    """L1, L2 through sweep.py calendar, in a throwaway vault."""

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        self.v.run("init")
        self.today = date.today().isoformat()
        self.tomorrow = (date.today() + timedelta(days=1)).isoformat()
        self.cal = self.v.root / "system/staging/calendar.json"

    def save(self, days):
        spec = self.v.root / "system/staging/drafts/calendar.json"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(json.dumps({"days": days}))
        return self.v.run("calendar", str(spec), script="sweep.py", ok=False)

    def held(self):
        return json.loads(self.cal.read_text())["days"]

    def meeting(self, **kw):
        return {"id": "ev-1", "start": "09:00", "end": "09:30", "title": "Pilot readiness review", **kw}

    def seed(self):
        self.assertEqual(self.save({self.tomorrow: [self.meeting(), self.meeting(id="ev-2", start="11:00", end="11:30")]}).returncode, 0)
        return self.cal.read_text()

    def test_one_event_with_unreadable_times_never_wipes_a_saved_calendar(self):
        kept = self.seed()
        r = self.save({self.tomorrow: [self.meeting(id="z", start="xx", end="yy")]})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("kept the saved calendar", r.stdout)
        self.assertEqual(self.cal.read_text(), kept)

    def test_a_reply_of_only_past_days_never_wipes_a_saved_calendar(self):
        kept = self.seed()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        r = self.save({yesterday: [self.meeting(id="old")]})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.cal.read_text(), kept)

    def test_a_reply_of_only_ignored_events_never_wipes_a_saved_calendar(self):
        kept = self.seed()
        r = self.save({self.tomorrow: [self.meeting(id="t", title="ToDo: tidy desk"), self.meeting(id="p", private=True)]})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertEqual(self.cal.read_text(), kept)

    def test_a_reply_with_one_meeting_to_keep_replaces_the_calendar(self):
        self.seed()
        r = self.save({self.tomorrow: [self.meeting(id="only"), self.meeting(id="z", start="xx", end="yy")]})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual([e["id"] for e in self.held()[self.tomorrow]], ["only"])

    def test_a_day_after_the_window_is_dropped(self):
        far = (date.today() + timedelta(days=4000)).isoformat()
        r = self.save({self.tomorrow: [self.meeting()], far: [self.meeting(id="far")]})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(list(self.held()), [self.tomorrow])

    def test_a_repeated_id_on_a_day_is_kept_once(self):
        r = self.save({self.tomorrow: [self.meeting(), self.meeting(), self.meeting(title="Forged")]})
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual([e["title"] for e in self.held()[self.tomorrow]], ["Pilot readiness review"])
        r = self.save({self.tomorrow: [self.meeting(id=""), self.meeting(id="", start="10:00", end="10:30")]})
        self.assertEqual(len(self.held()[self.tomorrow]), 2)             # no ID: nothing to repeat

    def test_too_many_meetings_are_refused_and_the_saved_calendar_stays(self):
        kept = self.seed()
        r = self.save({self.tomorrow: [self.meeting(id=f"e{i}") for i in range(501)]})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("too large", r.stdout)
        self.assertEqual(self.cal.read_text(), kept)

    def test_an_oversize_calendar_is_refused_and_the_saved_calendar_stays(self):
        kept = self.seed()
        body = " ".join(f"word{i}" for i in range(4000))
        r = self.save({self.tomorrow: [self.meeting(id=f"e{i}", body=body) for i in range(400)]})
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("too large", r.stdout)
        self.assertEqual(self.cal.read_text(), kept)

    def test_the_size_limit_counts_bytes(self):
        """Under 6 million characters but over 6 million bytes (Japanese text is three bytes a character) is refused."""
        kept = self.seed()
        body = "\u4f1a\u8b70\u306e\u8b70\u984c" * 3800
        spec = self.v.root / "system/staging/drafts/calendar.json"
        spec.write_text(json.dumps({"days": {self.tomorrow: [self.meeting(id=f"e{i}", body=body) for i in range(150)]}},
                                   ensure_ascii=False), encoding="utf-8")
        r = self.v.run("calendar", str(spec), script="sweep.py", ok=False)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("too large", r.stdout)
        self.assertEqual(self.cal.read_text(), kept)

    def test_days_that_are_not_an_object_give_a_message_and_keep_the_saved_calendar(self):
        kept = self.seed()
        for days in ([self.meeting()], "x", 7, [[]]):
            with self.subTest(days=days):
                r = self.save(days)
                self.assertEqual(r.returncode, 1, r.stdout)
                self.assertIn("not a calendar", r.stdout)
                self.assertNotIn("Traceback", r.stdout + r.stderr)
                self.assertEqual(self.cal.read_text(), kept)
        spec = self.v.root / "system/staging/drafts/calendar.json"
        spec.write_text("[1, 2]")
        r = self.v.run("calendar", str(spec), script="sweep.py", ok=False)
        self.assertEqual((r.returncode, "not a calendar" in r.stdout), (1, True))

    def test_the_bad_times_message_never_carries_a_key_from_a_title(self):
        bad = [self.meeting(id="b1", start="xx", end="yy", title="Sync Passcode: 4321"),
               self.meeting(id="b2", start="xx", end="yy", title="Board https://zoom.us/j/1?pwd=abc", sensitivity="confidential"),
               self.meeting(id="b3", start="xx", end="yy", title="Secret plan", private=True),
               self.meeting(id="b4", start="xx", end="yy", title="Budget review")]
        r = self.save({self.tomorrow: [self.meeting(id="ok"), *bad]})
        self.assertEqual(r.returncode, 0, r.stdout)
        out = r.stdout + r.stderr
        for gone in ("4321", "pwd", "zoom", "Board", "Secret plan"):
            self.assertNotIn(gone, out)
        self.assertIn("Budget review", out)                                          # an ordinary title is still named
        self.assertIn("Skipped (bad times)", out)

    def test_rows_saved_by_an_earlier_version_are_cleaned_when_kept(self):
        """Past days of the saved calendar are kept as saved, but now through the same cleaning."""
        settings = self.v.root / "system/config/settings.json"
        cfg = json.loads(settings.read_text())
        cfg.setdefault("inbox", {})["meetings_from"] = 5
        settings.write_text(json.dumps(cfg))
        past = (date.today() - timedelta(days=2)).isoformat()
        old = [{"id": "o1", "start": "09:00", "end": "10:00", "all_day": False, "title": "Sync Passcode: 4321", "where":
                "https://zoom.us/j/1?pwd=abc", "teams": True, "private": False, "organiser": "Jane Doe", "sensitivity": "restricted",
                "body": "Notes\nPasscode: 4321\nPIN 998877", "attendees": [{"name": "Sam Lee", "email": "sam@example.test"}]},
               {"id": "o2", "start": "11:00", "end": "12:00", "all_day": False, "title": "Budget", "where": "Room 2", "teams": False,
                "private": False, "organiser": True, "sensitivity": "normal", "body": "Agenda: budget\nJoin https://bit.ly/abc",
                "attachments": ["pack.pdf", "PIN 4321.ics"], "attendees": [{"name": "Dial-in PIN 4321", "email": "x@example.test"}]}]
        self.cal.write_text(json.dumps({"fetched": past + " 08:00", "days": {past: old}}))
        self.assertEqual(self.save({self.tomorrow: [self.meeting()]}).returncode, 0)
        rows = {r["id"]: r for r in self.held()[past]}
        self.assertEqual(rows["o1"], {"id": "o1", "start": "09:00", "end": "10:00", "all_day": False, "title": "Sync", "where": "",
                                      "teams": False, "private": False, "organiser": False, "sensitivity": "confidential"})
        self.assertEqual((rows["o2"]["body"], rows["o2"]["attachments"], rows["o2"]["attendees"][0]["name"]),
                         ("Agenda: budget", ["pack.pdf"], "x@example.test"))
        for gone in ("4321", "pwd", "bit.ly", "998877", "zoom"):
            self.assertNotIn(gone, self.cal.read_text())

    def test_a_saved_calendar_holds_no_key_from_a_whole_event(self):
        ev = self.meeting(where="https://us02web.zoom.us/j/8123?pwd=abcdef", body="Agenda: budget\nPasscode: 4321\nhttps://bit.ly/3xYzAbC",
                          attachments=["pack.pdf"], attendees=[{"name": "Sam Lee", "email": "sam.lee@example.test"}])
        self.assertEqual(self.save({self.tomorrow: [ev]}).returncode, 0)
        text = self.cal.read_text()
        for gone in ("pwd", "4321", "bit.ly", "zoom"):
            self.assertNotIn(gone, text)
        self.assertIn("Agenda: budget", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)

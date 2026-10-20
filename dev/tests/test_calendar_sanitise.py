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
import unittest
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
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
          "Call Sam about the pilot", "Attendees: Jane Doe, Sam Lee"]


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
                 ("Zoom: https://acme.zoom.us/my/room", "Zoom:"), ("Room 2 (PIN 4321)", ""), ("Room 2", "Room 2"),
                 ("tel:+15550001111,,123456#", ""), ("Microsoft Teams Meeting", "Microsoft Teams Meeting")]
        for where, want in cases:
            with self.subTest(where):
                row = sweep.calendar_row(event(where=where), "09:00", "10:00", False)
                self.assertEqual(row["where"], want)
        row = sweep.calendar_row(event(title="Sync https://zoom.us/j/1?pwd=abc"), "09:00", "10:00", False)
        self.assertEqual(row["title"], "Sync")
        row = sweep.calendar_row(event(title="Budget (PIN 4321)"), "09:00", "10:00", False)
        self.assertEqual(row["title"], "Meeting")
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

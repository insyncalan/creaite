"""#375 E1 (2.6.9 items 2 and 3): the gateway's read() on malformed rows and files, and the long-line rule of invite_filter.

Run: python3 dev/tests/test_calendar_gateway_robust.py
Findings 12 and 16 (gateway) and L12, L13 (long lines) of dev/proposals/375/ADVERSARIAL.md as plain tests, plus a 50,000-body property
test of subset (P1) and idempotence (P2) on very long lines, CRLF, tabs, bidi controls and many blank lines, for all three orders.
LONG-LINE RULE: a converted line longer than CAP (1,500) is dropped whole (fail-closed), before the label layers run; the output never
ends in a blank line. Truncation is not used (it would break the subset property). Fictional data only.
"""
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import calendar_gateway as G  # noqa: E402
import invite_filter as F  # noqa: E402

N = 50000
FULL = bool(__import__('os').environ.get('FULL'))


def good(**kw):
    r = {"id": "e1", "start": "10:00", "end": "11:00", "all_day": False, "title": "Budget review", "where": "Room 204", "teams": True,
         "private": False, "organiser": "Mia Hale", "sensitivity": "normal", "organiser_email": "mia.hale@example.test",
         "recurrence": "weekly", "body": "Hello\nBye", "attachments": ["plan.docx"],
         "attendees": [{"name": "Omar Reyes", "type": "required", "response": "accepted"}], "clean": G.CLEAN}
    r.update(kw)
    return r


class Robust(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "calendar.json"
        G.clear_cache()

    def tearDown(self):
        G.clear_cache()
        self.tmp.cleanup()

    def put(self, rows):
        self.path.write_text(json.dumps({"fetched": "2026-10-12T08:00", "to": "2026-10-19", "days": {"2026-10-12": rows}}), encoding="utf-8")

    def read_all(self):
        out = {}
        for p in G.purpose_names():
            G.clear_cache()
            out[p] = G.read(p, self.path)["days"]["2026-10-12"]
        return out

    def test_attendees_not_a_list(self):
        for bad in (3, "x", {"a": 1}, None, True, [1, "a", None, ["b"]]):
            self.put([good(attendees=bad)])
            for p, rows in self.read_all().items():
                self.assertEqual(len(rows), 1, p)
                self.assertIsInstance(rows[0].get("attendees", []), list)

    def test_wrong_types_in_stamped_rows(self):
        bads = [{"title": ["a"]}, {"title": 5}, {"start": 10}, {"body": 7}, {"body": ["Passcode: 4417"]}, {"attachments": 3},
                {"attachments": [1, {"a": 1}, "ok.docx"]}, {"where": {"x": 1}}, {"id": [1]}, {"teams": "yes"}, {"all_day": 1},
                {"private": [1]}, {"sensitivity": 3}, {"organiser": None}, {"organiser_email": 4}, {"recurrence": []}]
        for b in bads:
            self.put([good(**b)])
            for p, rows in self.read_all().items():
                self.assertEqual(len(rows), 1, (b, p))
                for k, v in rows[0].items():
                    if k in ("attendees", "attachments"):
                        self.assertIsInstance(v, list, (b, p, k))
                        if k == "attachments":
                            self.assertTrue(all(isinstance(f, str) for f in v), (b, p))
                    elif k in ("all_day", "teams", "private"):
                        self.assertIsInstance(v, bool, (b, p, k))
                    else:
                        self.assertIsInstance(v, str, (b, p, k))

    def test_malformed_stamped_body_is_refiltered(self):
        G.FILTER = lambda t: "\n".join(x for x in t.split("\n") if "4417" not in x)
        try:
            self.put([good(attendees=3, body="Hello\nPasscode: 4417\nBye")])
            G.clear_cache()
            rows = G.read("agenda", self.path)["days"]["2026-10-12"]
            self.assertNotIn("4417", json.dumps(rows))
        finally:
            G.FILTER = None
            G.clear_cache()

    def test_non_dict_attendee_entries_and_odd_rows(self):
        self.put([good(attendees=[None, 3, "x", {"name": 5, "type": "t"}, {"name": "Ada"}]), 5, "x", None, [1]])
        for rows in self.read_all().values():
            self.assertEqual(len(rows), 1)
        self.assertIn({"name": "Ada"}, self.read_all()["day"][0]["attendees"])

    def test_private_with_odd_types_still_reduced(self):
        self.put([good(private="true", title=["secret"], body="x", attendees=3)])
        for rows in self.read_all().values():
            self.assertNotIn("body", rows[0])
            self.assertNotIn("attendees", rows[0])

    def test_view_directly_on_junk(self):
        for junk in ({"attendees": 3, "clean": 1}, {"title": []}, {}, {"body": {}}):
            for p in G.purpose_names():
                self.assertIsInstance(G.view(junk, p), dict)

    def test_deep_json_is_value_error(self):
        self.path.write_text("[" * 10 ** 6 + "]" * 10 ** 6, encoding="utf-8")
        with self.assertRaises(ValueError):
            G.read("day", self.path)
        self.path.write_text('{"days": {"2026-10-12": [{"attendees": ' + "[" * 10 ** 6 + "]" * 10 ** 6 + "}]}}", encoding="utf-8")
        with self.assertRaises(ValueError):
            G.read("day", self.path)

    def test_partial_and_huge_json(self):
        full = json.dumps({"fetched": "x", "days": {"2026-10-12": [good(body="Hello\n" * 5000)]}})
        for cut in (0, 1, 7, len(full) // 3, len(full) - 1):
            self.path.write_text(full[:cut], encoding="utf-8")
            G.clear_cache()
            with self.assertRaises(ValueError):
                G.read("agenda", self.path)
        self.path.write_text(full, encoding="utf-8")
        G.clear_cache()
        body = G.read("agenda", self.path)["days"]["2026-10-12"][0].get("body", "")
        self.assertLessEqual(len(body), G.BODY_CAP)
        rows = [good(id="e%d" % i, body="x " * 3000) for i in range(300)]
        self.put(rows)
        G.clear_cache()
        self.assertEqual(len(G.read("prep_page", self.path)["days"]["2026-10-12"]), 300)

    def test_other_shapes_raise_only_value_or_os_error(self):
        for doc in ("[]", "3", '"x"', "null", '{"days": 3}', '{"days": {"2026-10-12": 3}}', '{"days": {"bad": []}}', "NaN", "\xff"):
            self.path.write_bytes(doc.encode("latin-1"))
            G.clear_cache()
            try:
                G.read("day", self.path)
            except (OSError, ValueError):
                pass


def conv(t):
    return t.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def rand_body(rng):
    parts = []
    for _ in range(rng.randint(1, 10)):
        k = rng.random()
        if k < 0.2:
            parts.append(rng.choice(["word ", "x ", "agenda item ", "a"]) * rng.choice([260, 300, 400, 760, 800, 1000, 1499, 1500, 1501, 2001]))
        elif k < 0.3:
            parts.append("x " * rng.randint(600, 900) + rng.choice(["Passcode: 4417 ", "Meeting ID: 412 889 330 ", "PIN 8825 "]) + "y " * rng.randint(600, 900))
        elif k < 0.45:
            parts.append("")
        elif k < 0.55:
            parts.append("\t" * rng.randint(0, 3) + rng.choice(["Budget\treview", "  \t  ", "‮evil‬ line", "⁦x⁩"]))
        else:
            parts.append(rng.choice(["Hello team", "Agenda: budget", "Passcode: 4417", "Meeting ID: 412 889 330", "Join: https://m.example.test/j/1",
                                     "See you Monday.", "____", "PIN", "8825", "Pass 4417", "Hasło : 7679"]))
    sep = rng.choice(["\n", "\r\n", "\n\n", "\r"])
    return sep.join(parts)


class LongLines(unittest.TestCase):
    def test_L12_idempotent_after_the_cap(self):
        t = "Hi.\n\n" + "word " * 400 + "\n\nBye."
        for fn in (F.filter_text, lambda x: F.filter_text_with_scrub(x)):
            once = fn(t)
            self.assertEqual(fn(once), once)
            self.assertFalse(once.endswith("\n"))
        self.assertEqual(F.filter_text(t), "Hi.\n\n\nBye.")  # plain filter_text keeps blank lines

    def test_L13_no_fragment(self):
        t = "Hi.\n\n" + "x " * 800 + "Passcode: 4417 " + "x " * 800 + "\n\nBye."
        for order in F.ORDERS:
            out = F.filter_text_with_scrub(t, order=order)
            self.assertNotIn("4417", out)
            if order != "scrub_raw_first":
                self.assertTrue(all(ln in set(conv(t)) for ln in out.split("\n")), order)
            else:
                self.assertTrue(all(len(ln) <= F.CAP for ln in out.split("\n")))

    def test_boundary(self):
        def line(n):
            return ("hello " * n)[:n - 1] + "!"
        for n in (1499, 1500, 1501, 2000, 2001, 5000):
            out = F.filter_text(line(n) + "\nBye.")
            self.assertEqual(out, "Bye." if n > 1500 else line(n) if n == 1500 else out)
            self.assertEqual(F.filter_text(out), out)
        self.assertEqual(F.filter_text(line(1500)), line(1500))
        self.assertEqual(F.filter_text(line(1501) + "\nBye."), "Bye.")

    def check_one(self, t, i, i_orders, bad):
        lines = set(conv(t))
        for order in i_orders:
            once = F.filter_text_with_scrub(t, order=order)
            if once != F.filter_text_with_scrub(once, order=order):
                bad.append(("P2", order, i))
            if order != "scrub_raw_first" and not all(ln in lines for ln in once.split("\n") if ln):
                bad.append(("P1", order, i))
            if once.endswith("\n") or len(once) > F.CAP:
                bad.append(("cap", order, i))
        if i % 5 == 0:
            a = F.filter_text(t)
            if a != F.filter_text(a) or not all(ln in lines for ln in a.split("\n") if ln) or a.endswith("\n"):
                bad.append(("plain", i))

    def test_props(self):
        rng = random.Random(375269)
        bad = []
        for i in range(N):
            # scrub_raw_first runs the 2.6.8 scrub on the whole raw body (about 35 ms a body): every 40th body (all of them with FULL=1)
            orders = ("anchors_first", "scrub_first") + (("scrub_raw_first",) if FULL or i % 40 == 0 else ())
            self.check_one(rand_body(rng), i, orders, bad)
            if len(bad) > 5:
                break
        self.assertEqual(bad, [])


if __name__ == "__main__":
    unittest.main()

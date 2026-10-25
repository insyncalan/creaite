"""#375 E1 integration: the 27 invite fixtures as unstamped calendar rows, read through calendar_gateway with the real filter.

Run: python3 dev/tests/test_calendar_e1_integration.py      (quick tier: plain code)

No stand-ins: FILTER and SHORT stay at their defaults (invite_filter.filter_text with html auto, invite_clean.clean_row).
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "system" / "scripts"))
import calendar_gateway as G  # noqa: E402
import invite_filter as F  # noqa: E402

FIX = HERE / "fixtures" / "invites"
INVISIBLE = dict((ord(c), None) for c in "​‌‍⁠﻿­")
BODY_PURPOSES = ("prep_rank", "prep_panel", "prep_page", "agenda", "shape")
KEEP_PURPOSES = ("prep_rank", "prep_panel", "prep_page", "agenda")


def fixtures():
    out = []
    for meta in sorted(FIX.glob("*.json")):
        src = [p for p in FIX.glob(meta.stem + ".*") if p.suffix in (".html", ".txt")][0]
        with open(str(src), encoding="utf-8", newline="") as fh:
            body = fh.read()
        out.append((meta.stem, body, json.loads(meta.read_text(encoding="utf-8"))))
    return out


def row(i, body):
    return {"id": i, "start": "10:00", "end": "11:00", "all_day": False, "title": "Design review", "where": "Room 204", "teams": True,
            "private": False, "organiser": "Mia Hale", "sensitivity": "normal", "organiser_email": "mia.hale@example.test",
            "recurrence": "", "body": body, "attendees": [], "attachments": []}


# lines the 2.6.8 scrub (the body label layer of option c) removes after a label inside its window
SCRUB_WINDOW_LOSS = {
    "label_same_cell_br": ("Room 204", "Notes are kept on the team page."),
    # composition D (scrub_raw_first, the default since PLAN 1d): must_keep 50 of 59, the scrub's own windows on the raw lines
    "pre_block": ("End.",),
    "outlook_footer": ("Please confirm attendance.",),
    "nested_lists": ("Open actions", "Decisions needed"),
    "entities_and_hidden": ("Q&A session \u2013 bring questions \u2039in writing>.",),
    "definition_list": ("Questions welcome.",),
    "broken_html": ("Second paragraph", "Contract review with legal."),
}


class E1Integration(unittest.TestCase):
    def setUp(self):
        G.clear_cache()
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "calendar.json"
        self.cases = fixtures()
        rows = [row("f%02d" % n, body) for n, (_name, body, _m) in enumerate(self.cases)]
        self.path.write_text(json.dumps({"fetched": "2026-10-26T07:00", "to": "2026-11-01", "days": {"2026-10-26": rows}}), encoding="utf-8")

    def tearDown(self):
        G.clear_cache()
        self.tmp.cleanup()

    def views(self, purpose):
        return G.read(purpose, self.path)["days"]["2026-10-26"]

    def test_defaults_are_the_real_filter(self):
        self.assertIsNone(G.FILTER)
        self.assertIsNone(G.SHORT)
        self.assertGreaterEqual(len(self.cases), 27)

    def test_no_planted_secret_in_any_purpose(self):
        for purpose in G.purpose_names():
            for (name, _b, meta), v in zip(self.cases, self.views(purpose)):
                blob = json.dumps(v, ensure_ascii=False).translate(INVISIBLE)
                for secret in meta["planted_secrets"]:
                    with self.subTest(purpose=purpose, fixture=name, secret=secret):
                        self.assertNotIn(secret.translate(INVISIBLE), blob)

    def test_must_keep_in_agenda_and_prep_views(self):
        for purpose in KEEP_PURPOSES:
            for (name, _b, meta), v in zip(self.cases, self.views(purpose)):
                lines = v.get("body", "").split("\n")
                for line in meta["must_keep"]:
                    if line in SCRUB_WINDOW_LOSS.get(name, ()):
                        continue            # option (c): the 2.6.8 scrub's label window removes it (documented cost, PLAN.md 1b)
                    with self.subTest(purpose=purpose, fixture=name, line=line):
                        self.assertIn(line, lines)

    def test_day_and_meta_carry_no_body(self):
        for purpose in ("day", "meta"):
            for v in self.views(purpose):
                self.assertNotIn("body", v)

    def test_views_are_filter_output(self):
        for (name, body, _m), v in zip(self.cases, self.views("agenda")):
            with self.subTest(fixture=name):
                self.assertEqual(v.get("body", ""), G.filter_body(body))
                self.assertEqual(F.filter_text(v.get("body", "")), v.get("body", ""))

    def test_file_bytes_unchanged_by_reads(self):
        before = self.path.read_bytes()
        for purpose in G.purpose_names():
            G.read(purpose, self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_stamped_rows_served_as_stored(self):
        stored = "Agenda\nhttps://meet.example.test/j/123456789?pwd=Zx81"
        r = row("s1", stored)
        r["clean"] = G.CLEAN
        self.path.write_text(json.dumps({"fetched": "x", "to": "y", "days": {"2026-10-26": [r]}}), encoding="utf-8")
        G.clear_cache()
        self.assertEqual(G.read("agenda", self.path)["days"]["2026-10-26"][0]["body"], stored)


class FilterHtmlParameter(unittest.TestCase):
    def test_auto_converts_html_and_matches_forced(self):
        for name, body, _m in fixtures():
            if body.lstrip().startswith("<"):
                with self.subTest(fixture=name):
                    self.assertEqual(F.filter_text(body), F.filter_text(body, html=True))

    def test_subset_of_converted_lines_and_idempotent(self):
        import invite_blocks as B
        for name, body, _m in fixtures():
            kept = F.filter_text(body).split("\n") if F.filter_text(body) else []
            with self.subTest(fixture=name):
                ref = B.to_lines(body) if B.looks_like_html(body) else body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
                it = iter(ref)
                self.assertTrue(all(any(k == y for y in it) for k in kept))
                self.assertEqual(F.filter_text("\n".join(kept)), "\n".join(kept))

    def test_blocks_from_html_is_blocks(self):
        import invite_blocks as B
        for _n, body, _m in fixtures():
            self.assertEqual(F.blocks_from_html(body), B.blocks(body))

    def test_accented_label_still_read(self):
        self.assertEqual(F.filter_text("Agenda\nPašswörd: hunter3694x\nBye"), "Agenda\nBye")

    def test_crlf_plain_equals_lf_plain(self):
        t = "Agenda\r\n1. Scope\r\nPasscode: 3321 4490\r\n"
        self.assertEqual(F.filter_text(t), F.filter_text(t.replace("\r\n", "\n")))
        self.assertNotIn("\r", F.filter_text(t))


if __name__ == "__main__":
    unittest.main()

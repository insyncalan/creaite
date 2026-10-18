"""BL-342 Part 3 B: the one check with the card fields, its reply's checks and the close suggestions (step 9), part 1 of 3 (the fixture is in vip_single_call_support.py).

Run: python3 dev/tests/test_vip_single_call.py
"""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vip_single_call_support import (  # noqa: E402
    ALAN,
    Base,
    MAIL_ID,
    OFF,
    SARA,
    SECRET,
    closing,
    py,
    thread,
    vip_file,
)


class ZoneTests(Base):
    def test_the_zone_is_the_laptops_and_every_time_carries_its_offset(self):
        z = py(self.v, "z = sweep.local_zone(); print(json.dumps([z['offset'], z['zone'], sweep.zoned_out('2026-10-08 09:16', z)]))")
        self.assertEqual(z, ["+04:00", "Alan's local time, UTC+04:00", "2026-10-08T09:16+04:00"])
        got = py(self.v, "z = sweep.local_zone(); print(json.dumps([sweep.zoned_in(t, z) for t in "
                         "['2026-10-08T05:16Z', '2026-10-08 05:16', '2026-10-08T09:16+04:00', '2026-10-08T07:16+02:00', 'soon']]))")
        self.assertEqual(got, [["2026-10-08 09:16", True], None, ["2026-10-08 09:16", False], ["2026-10-08 09:16", True], None])

    def test_without_the_test_offset_the_laptops_own_zone_is_used(self):
        z = py(self.v, "z = sweep.local_zone(); print(json.dumps([z['tz'] is None, z['offset']]))", CREAITE_TZ_OFFSET="")
        self.assertTrue(z[0])
        self.assertRegex(z[1], r"^[+-]\d\d:\d\d$")


class CleanTests(Base):
    """The probe's failure modes, each dropped or converted as Part 3 B step 2 says."""

    def test_a_time_without_an_offset_is_dropped(self):
        found, counts = self.clean([thread(last="2026-10-08 09:00")])
        self.assertEqual((found, counts.get("no_zone")), ([], 1))

    def test_utc_is_converted_to_local_and_counted(self):
        found, counts = self.clean([thread(last="2026-10-08T05:16Z")])
        self.assertEqual(found[0]["last"], "2026-10-08 09:16")
        self.assertEqual(counts.get("other_zone"), 1)

    def test_a_future_last_is_dropped_and_a_future_reply_ignored(self):
        found, counts = self.clean([thread(last=f"2026-10-20T09:00{OFF}")])
        self.assertEqual((found, counts.get("future")), ([], 1))
        found, counts = self.clean([thread(replied=f"2026-10-20T09:00{OFF}")])
        self.assertEqual(len(found), 1)
        self.assertNotIn("replied", found[0])
        self.assertEqual(counts.get("future"), 1)
        found, _ = self.clean([thread(last=f"2026-10-08T09:31{OFF}")])                     # a minute ahead: a clock's slack
        self.assertEqual(len(found), 1)

    def test_an_internet_message_id_and_a_slip_are_never_a_key(self):
        for bad in ("<DX1234567890ABCDEF@EXAMPLE.OUTLOOK.COM>", "DX1234567890ABCDEF@EXAMPLE.OUTLOOK.COM", MAIL_ID[:20] + "!" + MAIL_ID[21:],
                    MAIL_ID[:10] + " " + MAIL_ID[11:], "short"):
            with self.subTest(bad):
                found, counts = self.clean([thread(conversation=bad)])
                self.assertIsNone(found[0]["conversation"])
                self.assertEqual(counts.get("bad_id"), 1)
        self.check([thread(conversation="<DX1234567890ABCDEF@EXAMPLE.OUTLOOK.COM>")])
        a = self.cards()[0]
        self.assertIsNone(a["conv"])
        self.assertTrue(all(not k.startswith("id:") for k in a["keys"]))                     # keyed by link and local key
        self.assertTrue({k.split(":")[0] for k in a["keys"]} >= {"link", "loc"})
        self.assertNotIn("DX1234567890ABCDEF", json.dumps(a))

    def test_a_teams_chat_id_and_a_mail_conversation_id_are_kept(self):
        found, counts = self.clean([thread(), {**thread(), "kind": "teams", "conversation": "19:chat-plan@thread.v2",
                                                "link": "https://teams.microsoft.com/l/chat/19:chat-plan"}])
        self.assertEqual(sorted(f["conversation"] for f in found), sorted([MAIL_ID + "1", "19:chat-plan@thread.v2"]))
        self.assertNotIn("bad_id", counts)

    def test_calendar_invites_are_left_out_unless_invites_are_on(self):
        invites = [{**thread(1), "kind": "calendar"}, thread(2, subject="Accepted: Steering", title="Accepted: Steering"),
                   thread(3, subject="Updated invitation: Steering", title="Updated invitation: Steering"),
                   thread(4, subject="Canceled: Steering", title="Canceled: Steering")]
        found, counts = self.clean(invites)
        self.assertEqual((found, counts.get("invite")), ([], 4))
        found, counts = self.clean(invites, invites=True)
        self.assertEqual(len(found), 4)
        self.assertNotIn("invite", counts)

    def test_a_thread_nobody_asked_about_is_dropped(self):
        found, counts = self.clean([thread(**{"from": "Zed Other <zed@other.example>"})])
        self.assertEqual((found, counts.get("unasked")), ([], 1))
        found, counts = self.clean([{"kind": "mail", "conversation": MAIL_ID + "9", "replied": f"2026-10-08T09:10{OFF}"}])
        self.assertEqual((found, counts.get("unasked")), ([], 1))                             # reply-only, no such card

    def test_an_old_thread_is_dropped_unless_it_is_an_open_cards(self):
        found, counts = self.clean([thread(last=f"2026-10-08T07:00{OFF}")])
        self.assertEqual((found, counts.get("old")), ([], 1))
        self.check([thread(last=f"2026-10-08T08:10{OFF}")])
        found, counts = self.clean([thread(last=f"2026-10-08T07:00{OFF}", **{"from": "Zed Other <zed@other.example>"})])
        self.assertEqual(len(found), 1)                                                      # the open card's, by its ID

    def test_two_objects_for_one_conversation_keep_the_newest_and_fifty_at_most(self):
        found, counts = self.clean([thread(last=f"2026-10-08T09:05{OFF}", summary="Newer."), thread(summary="Older.")])
        self.assertEqual([f["summary"] for f in found], ["Newer."])
        self.assertEqual(counts.get("dup"), 1)
        many = [thread(n, last=f"2026-10-08T09:{n % 30:02d}{OFF}") for n in range(60)]
        found, counts = self.clean(many)
        self.assertEqual((len(found), counts.get("over")), (50, 10))

    def test_the_fields_are_cut_to_shape(self):
        found, _ = self.clean([thread(type="urgent", ask="x" * 300, due="2026-02-30", owners=["A", 3, "B", "C", "D", "E", "F", "G"],
                                      match={"id": "ABC-A-007", "relation": "update", "why": "y" * 300})])
        f = found[0]
        self.assertEqual((f["type"], len(f["ask"]), f["due"], f["owners"]), ("fyi", 140, None, ["A", "B", "C", "D", "E", "F"]))
        self.assertEqual(len(f["match"]["why"]), 140)

    def test_last_from_is_kept_only_for_someone_in_the_thread_or_alan(self):
        found, counts = self.clean([thread(last_from="zed@other.example"), thread(2, last_from=ALAN), thread(3, last_from=SARA)])
        by = {f["conversation"][-1]: f.get("last_from") for f in found}
        self.assertEqual(by, {"1": None, "2": ALAN, "3": SARA})
        self.assertEqual(counts.get("bad_from"), 1)

    def test_the_codes_own_keys_never_come_from_the_reply(self):
        found, _ = self.clean([thread(_reply="abc", _alan_last=True)])
        self.assertNotIn("_reply", found[0])
        self.assertNotIn("_alan_last", found[0])
        self.check([thread(_alan_last=True, match={"id": "ABC-A-007", "relation": "chase", "why": "Waiting."})])
        self.assertEqual(self.cards()[0]["match"]["relation"], "update")                     # no evidence Alan wrote last

    def test_a_reply_only_object_closes_an_open_card_and_never_makes_one(self):
        self.check([thread()])
        aid = self.cards()[0]["id"]
        got = self.check([{"kind": "mail", "conversation": MAIL_ID + "1", "replied": f"2026-10-08T09:20{OFF}"},
                          {"kind": "mail", "conversation": MAIL_ID + "7", "replied": f"2026-10-08T09:20{OFF}"}])
        self.assertEqual(got["new"], [aid])
        self.assertEqual(got["counts"].get("replied"), 1)
        self.assertEqual(len(self.cards()), 1)
        self.assertEqual((self.cards()[0]["state"], self.cards()[0]["replied_at"]), ("replied", "2026-10-08 09:20"))

    def test_a_reply_only_object_finds_its_card_by_card_id_link_and_a_merged_cards_id(self):
        self.check([thread(conversation=None)])
        a = self.cards()[0]
        st = vip_file(self.v)
        st["alerts"][0]["ids"] = ["0123456789ab"]
        (self.v.root / "system/staging/vip.json").write_text(json.dumps(st))
        for ref in (a["id"], "0123456789ab"):
            with self.subTest(ref):
                found, counts = self.clean([{"kind": "mail", "conversation": ref, "replied": f"2026-10-08T09:20{OFF}"}])
                self.assertEqual(found[0]["_reply"], a["id"])
        found, _ = self.clean([{"kind": "mail", "conversation": None, "link": a["link"], "replied": f"2026-10-08T09:20{OFF}"}])
        self.assertEqual(found[0]["_reply"], a["id"])

    def test_a_reply_after_the_last_message_is_evidence_alan_wrote_last(self):
        self.check([thread(replied=f"2026-10-08T09:10{OFF}", match={"id": "ABC-A-007", "relation": "chase", "why": "Waiting."})])
        a = self.cards()[0]
        self.assertEqual(a["state"], "replied")
        self.assertEqual(a["match"]["relation"], "chase")


class PromptPartsTests(Base):
    def test_the_open_cards_and_the_open_work(self):
        self.check([thread(1), thread(2, last=f"2026-10-08T09:05{OFF}"),
                    {**thread(3), "kind": "teams", "conversation": "19:chat-3@thread.v2", "link": "https://teams.example/3"}])
        st = vip_file(self.v)
        next(a for a in st["alerts"] if a["conv"] == MAIL_ID + "1")["seen"] = "2026-10-08 09:20"   # a seen card isn't asked about
        (self.v.root / "system/staging/vip.json").write_text(json.dumps(st))
        parts = py(self.v, "p = sweep.vip_prompt_parts(); p['offered'] = sorted(p['offered']); p['offered_promises'] = sorted(p['offered_promises']); print(json.dumps(p))")
        asked = json.loads(parts["open"])
        self.assertEqual([a["conversation"] for a in asked], [MAIL_ID + "2", "19:chat-3@thread.v2"])  # newest first
        self.assertEqual(asked[0], {"conversation": MAIL_ID + "2", "kind": "mail", "subject": "Project Falcon revised plan 2",
                                    "last": "2026-10-08T09:05+04:00"})
        self.assertNotIn("subject", asked[1])                                                # mail only
        work = json.loads(parts["open_work"])
        self.assertEqual(sorted(work), ["ABC", "XYZ"])
        self.assertNotIn("ABC-A-003", [w["id"] for w in work["ABC"]])                        # closed
        self.assertEqual(work["ABC"][0], {"id": "ABC-A-001", "t": "Filler action 1", "owner": "Ben Ito", "due": "2026-10-11"})
        self.assertEqual(parts["offered"], sorted([w["id"] for c in work.values() for w in c]))
        self.assertNotRegex(json.dumps(parts), r"(?i)\bvip\b")
        self.assertNotIn(SECRET, json.dumps(parts))

    def test_at_most_15_a_project_and_60_in_all(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            for code in ("P1", "P2", "P3", "P4", "P5"):
                con.execute("INSERT INTO projects (code, name) VALUES (?, ?)", (code + "AB", f"Project {code}"))
                for i in range(1, 21):
                    con.execute("INSERT INTO actions (id, project, description, owner, raised, due_date, source) VALUES "
                                "(?, ?, ?, 'Ben Ito', '2026-10-01', ?, 'Email · test')",
                                (f"{code}AB-A-{i:03d}", code + "AB", f"Task {i} " + "word " * 30, f"2026-11-{i:02d}"))
            con.commit()
        parts = py(self.v, "p = sweep.vip_prompt_parts(); p['offered'] = sorted(p['offered']); p['offered_promises'] = sorted(p['offered_promises']); print(json.dumps(p))")
        work = json.loads(parts["open_work"])
        self.assertTrue(all(len(v) <= 15 for v in work.values()))
        self.assertEqual(sum(len(v) for v in work.values()), 60)
        self.assertEqual(len(parts["offered"]), 60)
        self.assertTrue(all(len(w["t"]) <= 80 for v in work.values() for w in v))
        self.assertEqual([w["id"] for w in work["P1AB"]][:2], ["P1AB-A-001", "P1AB-A-002"])  # by due date


class CheckMinutesTests(Base):
    def test_check_minutes_is_held_between_10_and_240(self):
        cfg = self.v.root / "system/config/settings.json"
        for given, read in ((1, 10), (0.02, 10), (45, 45), (1000, 240), ("often", 30), (None, 30), (30, 30)):
            with self.subTest(given):
                d = json.loads(cfg.read_text())
                d.setdefault("vip", {})["check_minutes"] = given
                cfg.write_text(json.dumps(d))
                self.assertEqual(py(self.v, "print(json.dumps(sweep.vip_settings()['check_minutes']))"), read)
        self.assertEqual(py(self.v, "print(json.dumps([sweep.VIP_MIN_MINUTES, sweep.VIP_MAX_MINUTES]))"), [10, 240])

    def test_the_settings_field_takes_10_to_240(self):
        src = (Path(__file__).resolve().parents[2] / "system/templates/dashboard/src/components/settings/Essentials.jsx").read_text()
        block = src[src.index('case "vip.check_minutes":'):][:700]
        self.assertIn("min={10} max={240}", block)
        self.assertIn("v < 10 || v > 240", block)


if __name__ == "__main__":
    unittest.main()

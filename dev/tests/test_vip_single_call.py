"""BL-342 Part 3 B: the one check with the card fields, its reply's checks and the close suggestions (step 9).

Run: python3 dev/tests/test_vip_single_call.py
A throwaway vault with fictional people and actions (project ABC: open actions ABC-A-007, owned by Sara Example, and
ABC-A-008, owned by Ben Ito; ABC-A-003 closed; project XYZ: open action XYZ-A-001). Probe-style fixtures: the reply a model
gave, fed to plain code (never Microsoft 365, never a real Claude). Covers the laptop's zone in and out, every probe failure
(no offset, UTC, future times, invented and one-character-off IDs, internet message IDs, calendar invites), a thread nobody
asked about, a reply-only object, the prompt's parts (the open cards and at most 15 open actions a project, 60 in all), and
the close suggestion's rules: a wrong match, New, a closed or other project's ID, an ID not offered, someone other than the
owner or Alan, a confidential thread, the switch off.
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import unittest
import urllib.request
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_live_server import free_port  # noqa: E402
from test_sweep_alerts import check_since, vip_file, vip_vault  # noqa: E402
from test_tracker import action  # noqa: E402

NOW = "2026-10-08 09:30"
OFF = "+04:00"
MIA = "Mia Hale <mia@client.example>"
SARA = "Sara Example <sara@brightwater.example>"
BEN = "Ben Ito <ben@brightwater.example>"
ALAN = "Alan Carter <alan@brightwater.example>"
SECRET = "SECRET MESSAGE TEXT"
REGISTER = """# People register

## People

| Full name | Email | Aliases | Organisation | Role | Hidden | VIP |
|---|---|---|---|---|---|---|
| Mia Hale | mia@client.example | Mia | Client | Sponsor | | client |
| Ben Ito | ben@brightwater.example | Ben | Brightwater | Director | | |
| Sara Example | sara@brightwater.example | Sara | Brightwater | Lead | | |
| Alan Carter | alan@brightwater.example | Alan | Brightwater | Programme manager | | |
"""
MAIL_ID = "AAQkADAwATM0MDAAMS1hYjI3LTJiOTQtMDACLTAwCgAQAN"


def thread(n=1, **extra):
    """A mail thread as the model returns it, in the laptop's zone."""
    subject = "Project Falcon revised plan" + (f" {n}" if n > 1 else "")
    return {"kind": "mail", "conversation": f"{MAIL_ID}{n}", "title": subject, "subject": subject, "from": MIA,
            "people": [MIA, SARA], "last": f"2026-10-08T09:00{OFF}", "last_from": "mia@client.example",
            "link": f"https://outlook.example/owa/?ItemID=t{n}", "sensitivity": "normal",
            "summary": "Mia asks for the revised plan.", "type": "action", "ask": "Send the revised plan", "due": "2026-10-12",
            "owners": ["Sara Example"], "items": [], "body": SECRET, **extra}


def py(v, code, **env):
    """Run code in the vault with sweep importable; returns stdout as JSON."""
    r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep, paths\n" + code],
                       cwd=v.root, capture_output=True, text=True,
                       env={**os.environ, "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF, **env})
    if r.returncode:
        raise AssertionError(r.stdout + r.stderr)
    return json.loads(r.stdout)


def seed(v):
    """Project ABC with ABC-A-001 to 008 (003 closed), project XYZ with XYZ-A-001; Alan's identity."""
    cfg = v.root / "system/config/settings.json"
    d = json.loads(cfg.read_text())
    d["identity"] = {"name": "Alan Carter", "short_forms": ["Alan"], "own_domains": ["brightwater.example"]}
    cfg.write_text(json.dumps(d, indent=2))
    (v.root / "projects/_portfolio/people-register.md").write_text(REGISTER)
    rows = [action(i, description=f"Filler action {i}", owner="Ben Ito", due_date=f"2026-10-{10 + i}") for i in range(1, 7)]
    rows += [action(7, description="Send the revised plan to Mia", owner="Sara Example", due_date="2026-10-12"),
             action(8, description="Book the rehearsal room", owner="Ben Ito", due_date="2026-10-20")]
    v.propose("seed", rows)
    v.run("apply")
    with closing(sqlite3.connect(v.root / "system/tracker.db")) as con:
        con.execute("UPDATE actions SET status = 'Closed', closed = '2026-10-03' WHERE id = 'ABC-A-003'")
        con.execute("INSERT INTO projects (code, name) VALUES ('XYZ', 'Project Other')")
        con.execute("INSERT INTO actions (id, project, description, owner, raised, source) VALUES "
                    "('XYZ-A-001', 'XYZ', 'Send the revised plan', 'Sara Example', '2026-10-01', 'Email · test')")
        con.commit()


CLEAN = ("found, counts = sweep.vip_clean(json.loads(sys.argv[1]), '2026-10-08 09:00', sweep.local_zone(), "
         "sweep.vip_state()['alerts'], invites=json.loads(sys.argv[2]))\nprint(json.dumps([found, counts]))")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = vip_vault()
        seed(self.v)

    def tearDown(self):
        self.v.cleanup()

    def clean(self, found, invites=False):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep\n" + CLEAN,
                            json.dumps(found), json.dumps(invites)], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF})
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return json.loads(r.stdout)

    def check(self, found, offered=None):
        """What the live server's check does with a reply: vip_clean, then vip_record with what was offered."""
        code = ("st = sweep.vip_state(); parts = sweep.vip_prompt_parts(st)\n"
                "found, counts = sweep.vip_clean(json.loads(sys.argv[1]), '2026-10-08 08:00', sweep.local_zone(), st['alerts'])\n"
                "offered = set(json.loads(sys.argv[2])) if sys.argv[2] != 'null' else parts['offered']\n"
                "checked = {'offered': offered, 'counts': counts}\n"
                "new = sweep.vip_record(found, 'check', checked=checked)\n"
                "print(json.dumps({'new': [a['id'] for a in new], 'counts': checked['counts']}))")
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep\n" + code,
                            json.dumps(found), json.dumps(offered)], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF})
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return json.loads(r.stdout)

    def cards(self):
        return vip_file(self.v)["alerts"]


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
        parts = py(self.v, "p = sweep.vip_prompt_parts(); p['offered'] = sorted(p['offered']); print(json.dumps(p))")
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
        parts = py(self.v, "p = sweep.vip_prompt_parts(); p['offered'] = sorted(p['offered']); print(json.dumps(p))")
        work = json.loads(parts["open_work"])
        self.assertTrue(all(len(v) <= 15 for v in work.values()))
        self.assertEqual(sum(len(v) for v in work.values()), 60)
        self.assertEqual(len(parts["offered"]), 60)
        self.assertTrue(all(len(w["t"]) <= 80 for v in work.values() for w in v))
        self.assertEqual([w["id"] for w in work["P1AB"]][:2], ["P1AB-A-001", "P1AB-A-002"])  # by due date


def owner_done(**extra):
    """Sara Example, the owner of ABC-A-007, says in the thread that she sent it."""
    return thread(**{"from": MIA, "last_from": "sara@brightwater.example",
                     "match": {"id": "ABC-A-007", "relation": "update", "why": "The plan was sent."},
                     "closes": {"id": "ABC-A-007", "evidence": "Sara says the revised plan went out"}, **extra})


class CloseTests(Base):
    """Step 9: a close suggestion only when code agrees with the model."""

    def closes(self):
        return self.cards()[0].get("closes")

    def test_the_owner_saying_done_gives_a_close(self):
        got = self.check([owner_done()])
        c = self.closes()
        self.assertEqual(c, {"id": "ABC-A-007", "evidence": "Sara says the revised plan went out", "who": "Sara Example",
                             "at": "2026-10-08 09:00"})
        self.assertEqual(got["counts"].get("closes_kept"), 1)

    def test_a_wrong_match_never_suggests(self):
        cases = {"other id": {"match": {"id": "ABC-A-008", "relation": "update", "why": "x"}},
                 "new": {"match": {"id": None, "relation": "new", "why": "x"}},
                 "invented": {"match": {"id": "ABC-A-099", "relation": "update", "why": "x"},
                              "closes": {"id": "ABC-A-099", "evidence": "Done"}}}
        for name, extra in cases.items():
            with self.subTest(name):
                got = self.check([owner_done(**extra)])
                self.assertIsNone(self.closes())
                self.assertEqual(got["counts"].get("closes_wrong_match"), 1)
                (self.v.root / "system/staging/vip.json").unlink()

    def test_a_closed_or_other_projects_id_never_suggests(self):
        for bad in ("ABC-A-003", "XYZ-A-001"):
            with self.subTest(bad):
                self.check([owner_done(match={"id": bad, "relation": "update", "why": "x"}, closes={"id": bad, "evidence": "Done now"})])
                self.assertEqual(self.cards()[0]["match"]["relation"], "new")               # code had already made it New
                self.assertIsNone(self.closes())
                (self.v.root / "system/staging/vip.json").unlink()

    def test_an_id_not_offered_never_suggests(self):
        got = self.check([owner_done()], offered=["ABC-A-008"])
        self.assertIsNone(self.closes())
        self.assertEqual(got["counts"].get("closes_not_offered"), 1)

    def test_someone_else_saying_done_never_suggests(self):
        got = self.check([owner_done(last_from="mia@client.example")])
        self.assertIsNone(self.closes())
        self.assertEqual(got["counts"].get("closes_not_owner"), 1)

    def test_alans_sent_delivery_on_an_open_card_closes_it_and_offers_the_close(self):
        self.check([thread(match={"id": "ABC-A-007", "relation": "update", "why": "About the plan."})])
        got = self.check([{"kind": "mail", "conversation": MAIL_ID + "1", "replied": f"2026-10-08T09:20{OFF}",
                           "closes": {"id": "ABC-A-007", "evidence": "Alan sent the revised plan the action asked for"}}])
        a = self.cards()[0]
        self.assertEqual(a["state"], "replied")
        self.assertEqual(a["closes"], {"id": "ABC-A-007", "evidence": "Alan sent the revised plan the action asked for",
                                       "who": "Alan Carter", "at": "2026-10-08 09:20"})
        self.assertEqual(got["counts"].get("closes_kept"), 1)

    def test_a_confidential_thread_keeps_only_the_fixed_words_and_a_private_one_none(self):
        self.check([owner_done(sensitivity="confidential")])
        self.assertEqual(self.closes()["evidence"], "The thread shows it finished.")
        (self.v.root / "system/staging/vip.json").unlink()
        self.check([owner_done(sensitivity="private")])
        self.assertIsNone(self.closes())

    def test_the_switch_off_suggests_nothing(self):
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.setdefault("drafting", {})["done"] = False
        cfg.write_text(json.dumps(d))
        got = self.check([owner_done()])
        self.assertIsNone(self.closes())
        self.assertEqual(got["counts"].get("closes_off"), 1)

    def test_evidence_that_quotes_or_copies_the_summary_is_refused(self):
        for ev in ('She wrote "the revised plan is attached here for everyone to review now"', "Mia asks for the revised plan.", " "):
            with self.subTest(ev):
                self.check([owner_done(closes={"id": "ABC-A-007", "evidence": ev})])
                self.assertIsNone(self.closes())
                (self.v.root / "system/staging/vip.json").unlink()

    def test_evidence_in_single_curly_or_guillemet_quotes_or_copied_unquoted_is_refused(self):
        run = "the revised plan is attached here for everyone to review now ok"
        summary = f"Mia said {run}, thanks."
        for ev in (f"She wrote '{run}'", f"She wrote \u2018{run}\u2019", f"\u00ab{run}\u00bb", f"\u201c{run}\u201d",
                   f"Sara: {run.upper()} thanks", f"Sara: {run.replace(' ', ', ')} thanks"):
            with self.subTest(ev):
                got = self.check([owner_done(summary=summary, closes={"id": "ABC-A-007", "evidence": ev})])
                self.assertIsNone(self.closes())
                self.assertEqual(got["counts"].get("closes_quoted"), 1)
                (self.v.root / "system/staging/vip.json").unlink()

    def test_short_evidence_and_apostrophes_still_pass(self):
        summary = "Mia said the revised plan is attached here for everyone to review now ok, thanks."
        for ev in ("Alan sent the revised plan", "Sara's plan isn't late; Ben's room is booked and Mia's team agreed",
                   "Sara said 'sent' and 'done' today", "Sara: the revised plan is attached here for everyone"):
            with self.subTest(ev):
                self.check([owner_done(summary=summary, closes={"id": "ABC-A-007", "evidence": ev})])
                self.assertEqual(self.closes()["evidence"], ev)
                (self.v.root / "system/staging/vip.json").unlink()

    def test_an_action_raised_after_the_message_never_closes(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("UPDATE actions SET raised = '2026-10-09' WHERE id = 'ABC-A-007'")
            con.commit()
        got = self.check([owner_done()])
        self.assertIsNone(self.closes())
        self.assertEqual(got["counts"].get("closes_raised_after"), 1)

    def test_a_later_message_without_a_close_takes_the_suggestion_back(self):
        self.check([owner_done()])
        self.assertIsNotNone(self.closes())
        self.check([thread(last=f"2026-10-08T09:10{OFF}", match={"id": "ABC-A-007", "relation": "update", "why": "More."})])
        self.assertIsNone(self.closes())

    def test_no_label_and_no_message_text(self):
        self.check([owner_done()])
        text = json.dumps(vip_file(self.v))
        self.assertNotIn(SECRET, text)
        self.assertNotRegex(text.replace('"vip', ""), r"\bVIP\b")


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


class StageTests(Base):
    """Step 9: one click stages one pending close for Review; nothing is applied; Undo leaves nothing."""

    def setUp(self):
        super().setUp()
        self.check([owner_done()])
        self.aid = self.cards()[0]["id"]

    def call(self, fn, aid=None):
        return py(self.v, f"import sys\ntry:\n    print(json.dumps(sweep.{fn}({json.dumps(aid or self.aid)})))\n"
                          "except (LookupError, ValueError) as e:\n    print(json.dumps({'refused': str(e)}))")

    def staged(self):
        out = []
        for f in sorted((self.v.root / "system/staging").glob("proposed-*-dashboard*.json")):
            out += [(f.name, i) for i in json.loads(f.read_text())["items"]]
        return out

    def test_the_click_stages_one_pending_close_with_based_on_and_the_thread_as_source(self):
        got = self.call("vip_close_stage")
        self.assertEqual((got["id"], got["state"]), ("ABC-A-007", "staged"))
        [(name, item)] = self.staged()
        self.assertEqual(name, got["proposal"])
        self.assertEqual((item["op"], item["table"], item["id"], item["decision"]), ("update", "actions", "ABC-A-007", "pending"))
        self.assertEqual(item["changes"]["status"], "Closed")
        self.assertTrue(item["based_on"])
        self.assertEqual(item["changes"]["latest_update"].splitlines()[-1],
                         "08-10-2026: Looks done: Sara says the revised plan went out (from a mail thread)")
        done = item["suggested"]["done"]
        self.assertEqual((done["strength"], done["evidence"]["said"], done["evidence"]["who"], done["evidence"]["kind"]),
                         ("Looks done", "Sara says the revised plan went out", "Sara Example", "mail"))
        self.assertIn("https://outlook.example/owa/?ItemID=t1", item["source"])
        self.assertEqual(item["suggested"]["closes"], [self.aid])
        self.assertEqual(item["why"], "Looks done: Sara says the revised plan went out")
        self.assertEqual(self.cards()[0]["closes"]["staged"]["proposal"], name)
        self.assertEqual(self.call("vip_close_stage"), {"refused": "Already staged for Review."})   # again: nothing new
        self.assertEqual(len(self.staged()), 1)
        self.assertEqual(self.v.rows("actions")[6]["status"], "Open")                                # nothing applied

    def test_review_holds_it_on_its_own_and_shows_looks_done_in_creaites_words(self):
        self.call("vip_close_stage")
        [(name, item)] = self.staged()
        rule = py(self.v, "import review\nprint(json.dumps(review.individual_only(json.load(open('system/staging/" + name + "'))['items'][0])))")
        self.assertEqual(rule, "closing update")
        self.v.run("bulk", script="review.py")                                              # Approve routine leaves it
        self.assertEqual(self.staged()[0][1]["decision"], "pending")
        rows = py(self.v, "import build_dashboard, tracker\ncon = tracker.connect()\n"
                          "print(json.dumps([r.get('dn') for r in build_dashboard.review_queue(con) if r.get('dn')]))")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["strength"], "Looks done")
        self.assertEqual(rows[0]["ev"], "Mail 08-10-2026 09:00 by Sara Example: Sara says the revised plan went out")
        self.assertNotRegex(rows[0]["ev"], "[“”\"]")                                        # creaite's words, not a quote

    def test_undo_leaves_nothing_and_a_decided_one_is_refused(self):
        self.call("vip_close_stage")
        self.assertEqual(self.call("vip_close_unstage")["state"], "undone")
        self.assertEqual(self.staged(), [])
        self.assertNotIn("staged", self.cards()[0]["closes"])
        self.call("vip_close_stage")
        [(name, item)] = self.staged()
        f = self.v.root / "system/staging" / name
        spec = json.loads(f.read_text())
        spec["items"][0]["decision"] = "approved"
        f.write_text(json.dumps(spec))
        self.assertEqual(self.call("vip_close_unstage"), {"refused": "Already decided in Review."})
        self.assertEqual(self.call("vip_close_stage"), {"refused": "Already decided in Review."})

    def test_log_and_close_make_one_pending_proposal_either_way(self):
        self.call("vip_log")
        self.call("vip_close_stage")
        [(name, item)] = self.staged()
        lines = item["changes"]["latest_update"].splitlines()
        self.assertEqual(len([ln for ln in lines if "Looks done" in ln]), 1)
        self.assertEqual(len(item["suggested"]["lines"]), 1)                                 # Log's line kept
        self.assertEqual(item["changes"]["status"], "Closed")
        self.call("vip_close_unstage")                                                       # back to Log's line only
        [(name2, item)] = self.staged()
        self.assertEqual(name2, name)
        self.assertNotIn("status", item["changes"])
        self.assertNotIn("done", item["suggested"])
        self.assertFalse(any("Looks done" in ln for ln in item["changes"]["latest_update"].splitlines()))
        self.assertTrue(item["why"].startswith("Logged from a thread"))
        for f in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json"):
            f.unlink()
        st = vip_file(self.v)
        st["alerts"][0]["match"].pop("logged", None)
        st["alerts"][0]["closes"].pop("staged", None)
        (self.v.root / "system/staging/vip.json").write_text(json.dumps(st))
        self.call("vip_close_stage")                                                         # close then Log: the same
        self.call("vip_log")
        [(name, item)] = self.staged()
        self.assertEqual(item["changes"]["status"], "Closed")
        self.assertEqual(len(item["suggested"]["lines"]), 1)
        self.call("vip_close_unstage")
        [(name, item)] = self.staged()
        self.assertTrue(item["why"].startswith("Logged from a thread"))

    def test_a_second_card_on_the_same_item_adds_its_line_to_the_same_item(self):
        self.call("vip_close_stage")
        self.check([owner_done(conversation=MAIL_ID + "2", subject="Project Falcon plan, the other thread",
                               title="Project Falcon plan, the other thread", link="https://outlook.example/owa/?ItemID=t2",
                               closes={"id": "ABC-A-007", "evidence": "Sara confirms the plan reached Mia"})])
        other = next(a["id"] for a in self.cards() if a["id"] != self.aid)
        self.call("vip_close_stage", other)
        [(name, item)] = self.staged()
        self.assertEqual(item["suggested"]["closes"], [self.aid, other])
        self.assertEqual(len([ln for ln in item["changes"]["latest_update"].splitlines() if "Looks done" in ln]), 2)
        self.call("vip_close_unstage", other)
        [(name, item)] = self.staged()
        self.assertEqual((item["suggested"]["closes"], item["changes"]["status"]), ([self.aid], "Closed"))

    def test_handled_before_a_click_stages_nothing_and_a_private_card_none(self):
        py(self.v, "print(json.dumps(sweep.vip_handled([" + json.dumps(self.aid) + "])))")
        self.assertEqual(self.staged(), [])
        self.assertEqual(self.call("vip_close_stage", "nope"), {"refused": "That thread isn't on Today any more."})

    def edit_card(self, **fields):
        st = vip_file(self.v)
        st["alerts"][0].update(fields)
        (self.v.root / "system/staging/vip.json").write_text(json.dumps(st))

    def test_the_click_checks_the_card_again(self):
        """Review point 5: the card may have changed since the check offered the close."""
        card = self.cards()[0]
        cases = {"handled": ({"state": "handled", "seen": "2026-10-08 09:20"}, "This thread is handled: nothing to stage."),
                 "seen": ({"seen": "2026-10-08 09:20"}, "This thread was marked seen: nothing to stage."),
                 "private": ({"marker": "private"}, "Nothing to close for a private conversation."),
                 "other match": ({"match": {**card["match"], "id": "ABC-A-008"}}, "This thread isn't matched to ABC-A-007 any more."),
                 "now new": ({"match": {"id": None, "relation": "new", "why": "x"}}, "This thread isn't matched to ABC-A-007 any more.")}
        for name, (fields, said) in cases.items():
            with self.subTest(name):
                self.edit_card(**{k: card.get(k) for k in ("state", "seen", "marker", "match")})          # back as checked
                self.edit_card(**fields)
                self.assertEqual(self.call("vip_close_stage"), {"refused": said})
                self.assertEqual(self.staged(), [])
        self.edit_card(**{k: card.get(k) for k in ("state", "seen", "marker", "match")})
        self.edit_card(match={**card["match"], "id": "abc-a-007"})                           # the same ID, any case
        self.assertEqual(self.call("vip_close_stage")["state"], "staged")

    def test_the_switch_turned_off_after_the_check_stages_nothing(self):
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.setdefault("drafting", {})["done"] = False
        cfg.write_text(json.dumps(d))
        self.assertEqual(self.call("vip_close_stage"), {"refused": "Looks done suggestions are switched off in Settings."})
        self.assertEqual(self.staged(), [])

    def test_handled_after_the_check_refuses_the_click(self):
        py(self.v, "print(json.dumps(sweep.vip_handled([" + json.dumps(self.aid) + "])))")
        self.assertEqual(self.call("vip_close_stage"), {"refused": "This thread is handled: nothing to stage."})
        self.assertEqual(self.staged(), [])

    def test_a_closed_item_is_refused(self):
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("UPDATE actions SET status = 'Closed', closed = '2026-10-08' WHERE id = 'ABC-A-007'")
            con.commit()
        self.assertEqual(self.call("vip_close_stage"), {"refused": "ABC-A-007 isn't open any more."})


MERGE = ("st = sweep.vip_state(); keep, drop = [next(a for a in st['alerts'] if a['id'] == x) for x in sys.argv[1:3]]\n"
         "sweep.card_merge(st, keep, drop); sweep.vip_save(st)\nprint(json.dumps(keep))")


class MergeCloseTests(Base):
    """Review point 6: merging two cards for one thread keeps a staged close and its match; Undo on the kept card reaches it."""

    def setUp(self):
        super().setUp()
        self.check([owner_done()])
        self.a = self.cards()[0]["id"]

    def second(self, close=False):
        extra = {"conversation": MAIL_ID + "2", "subject": "Project Falcon plan, again", "title": "Project Falcon plan, again",
                 "link": "https://outlook.example/owa/?ItemID=t2"}
        self.check([owner_done(**extra) if close else
                    thread(**extra, match={"id": "ABC-A-007", "relation": "update", "why": "About the plan."})])
        return next(a["id"] for a in self.cards() if a["id"] != self.a)

    def merge(self, keep, drop):
        r = subprocess.run([sys.executable, "-c", "import sys, json; sys.path.insert(0, 'system/scripts'); import sweep\n" + MERGE,
                            keep, drop], cwd=self.v.root, capture_output=True, text=True,
                           env={**os.environ, "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF})
        if r.returncode:
            raise AssertionError(r.stdout + r.stderr)
        return json.loads(r.stdout)

    def stage(self, fn, aid):
        return StageTests.call(self, fn, aid)

    def proposals(self):
        return StageTests.staged(self)

    def test_a_staged_close_on_the_card_merged_away_moves_to_the_kept_card_and_undo_reaches_it(self):
        b = self.second()
        self.assertIsNone(next(a for a in self.cards() if a["id"] == b).get("closes"))
        self.assertEqual(self.stage("vip_close_stage", self.a)["state"], "staged")
        kept = self.merge(b, self.a)
        self.assertEqual((kept["closes"]["id"], kept["match"]["id"]), ("ABC-A-007", "ABC-A-007"))
        self.assertIn("staged", kept["closes"])
        self.assertEqual(self.stage("vip_close_stage", b), {"refused": "Already staged for Review."})
        self.assertEqual(self.stage("vip_close_unstage", b)["state"], "undone")
        self.assertEqual(self.proposals(), [])                                              # nothing orphaned
        self.assertNotIn("staged", next(a for a in self.cards() if a["id"] == b)["closes"])

    def test_a_staged_close_on_the_kept_card_stays_and_wins_over_an_unstaged_one(self):
        b = self.second(close=True)
        self.stage("vip_close_stage", self.a)
        kept = self.merge(self.a, b)
        self.assertIn("staged", kept["closes"])
        self.assertEqual(self.stage("vip_close_unstage", self.a)["state"], "undone")
        self.assertEqual(self.proposals(), [])

    def test_when_both_have_a_close_the_staged_one_is_kept_either_way(self):
        b = self.second(close=True)
        self.stage("vip_close_stage", self.a)
        kept = self.merge(b, self.a)                                                         # the unstaged card kept
        self.assertIn("staged", kept["closes"])
        self.assertEqual(self.stage("vip_close_unstage", b)["state"], "undone")
        self.assertEqual(self.proposals(), [])

    def test_an_older_staged_close_without_its_card_is_found_by_the_merged_id(self):
        b = self.second()
        self.stage("vip_close_stage", self.a)
        st = vip_file(self.v)
        next(a for a in st["alerts"] if a["id"] == self.a)["closes"]["staged"].pop("card")   # staged before this fix
        (self.v.root / "system/staging/vip.json").write_text(json.dumps(st))
        self.merge(b, self.a)
        self.assertEqual(self.stage("vip_close_unstage", b)["state"], "undone")
        self.assertEqual(self.proposals(), [])


class ConfidentialStageTests(Base):
    def test_a_confidential_close_holds_no_thread_words(self):
        subject = "Project Falcon board secrets"
        self.check([owner_done(sensitivity="confidential", subject=subject, title=subject,
                               summary="The board discussed the secret plan figures.")])
        aid = self.cards()[0]["id"]
        py(self.v, f"print(json.dumps(sweep.vip_close_stage({json.dumps(aid)})))")
        [item] = [i for f in (self.v.root / "system/staging").glob("proposed-*-dashboard*.json")
                  for i in json.loads(f.read_text())["items"]]
        staged = json.dumps({k: item[k] for k in ("why", "source", "changes", "suggested")})
        for word in ("board", "secret", "Board", "Sara says", subject):
            self.assertNotIn(word, staged)
        self.assertEqual(item["why"], "Looks done: from a confidential thread")
        self.assertEqual(item["changes"]["latest_update"].splitlines()[-1], "08-10-2026: Looks done (from a confidential thread)")
        self.assertEqual(item["suggested"]["done"]["evidence"]["said"], "The thread shows it finished.")
        self.assertNotIn("who", item["suggested"]["done"]["evidence"])
        self.assertNotRegex(staged, r"\bVIP\b")


TOOLS = ["mcp__claude_ai_Microsoft_365__outlook_email_search", "mcp__claude_ai_Microsoft_365__chat_message_search",
         "mcp__claude_ai_Microsoft_365__outlook_calendar_search", "mcp__claude_ai_Microsoft_365__read_resource"]
FAKE = r"""#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
here = Path(__file__).parent
n = len(list(here.glob("vip-call-*.json"))) + 1
(here / f"vip-call-{n}.json").write_text(json.dumps({"args": args, "headless": os.environ.get("CREAITE_HEADLESS_RUN")}))
if (here / "start-a-sweep").exists():
    (here / "system/staging/sweep.lock").write_text(os.environ["CREAITE_NOW"] + "\n")
replies = json.loads((here / "vip-replies.json").read_text())
found = replies[min(n, len(replies)) - 1]
print(json.dumps({"type": "result", "result": "Here they are: " + json.dumps(found), "total_cost_usd": 0.3027}))
"""
REPLY = [owner_done(), {**thread(2), "kind": "calendar"}, thread(3, subject="Accepted: Steering", title="Accepted: Steering"),
         thread(4, conversation="<DX1234567890ABCDEF@EXAMPLE.OUTLOOK.COM>"), thread(5, last="2026-10-08 09:00"),
         thread(6, **{"from": "Zed Other <zed@other.example>"})]


class ServerCheck:
    """The live server's own check, with a stand-in claude; check_minutes stays 30, so only the start-up check runs."""

    def start(self, reply, sweep=False):
        self.v = v = vip_vault()
        seed(v)
        check_since(v)
        (v.root / "vip-replies.json").write_text(json.dumps([reply]))
        if sweep:
            (v.root / "start-a-sweep").write_text("1")
        fake = v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.proc = subprocess.Popen([sys.executable, str(v.root / "system/scripts/live_server.py")], cwd=v.root,
                                     env={**os.environ, "CREAITE_PORT": str(self.port), "CREAITE_CLAUDE": str(fake),
                                          "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF},
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                urllib.request.urlopen(self.base + "/health", timeout=1)
                break
            except OSError:
                time.sleep(0.1)
        html = urllib.request.urlopen(self.base + "/").read().decode()
        self.token = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))["token"]

    def stop(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self.v.cleanup()

    def post(self, path, body):
        req = urllib.request.Request(self.base + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Creaite-Token": self.token})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())

    def calls(self):
        return [json.loads(f.read_text()) for f in sorted(self.v.root.glob("vip-call-*.json"))]

    def log(self):
        return "\n".join(f.read_text() for f in (self.v.root / "system/logs").glob("debug-*.log"))

    def wait(self, test, what):
        for _ in range(150):
            if test():
                return
            time.sleep(0.1)
        self.fail(f"never {what}")


class SingleCallServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = ServerCheck()
        cls.s.fail = lambda what: (_ for _ in ()).throw(AssertionError(what))
        cls.s.start(REPLY)
        cls.s.wait(lambda: re.search(r"INFO\s+vip\s", cls.s.log()), "a check logged")
        time.sleep(1.0)

    @classmethod
    def tearDownClass(cls):
        cls.s.stop()

    def test_one_call_per_check_with_the_read_only_tools_and_no_model(self):
        calls = self.s.calls()
        self.assertEqual(len(calls), 1)                                                      # one check, one call
        args = calls[0]["args"]
        self.assertEqual(args[0], "-p")
        self.assertTrue(args[1].startswith("--"))                                            # an option follows -p
        self.assertEqual(args[-2], "--")                                                     # #91: the prompt last
        self.assertEqual(args.count("--"), 1)
        self.assertEqual(args[args.index("--allowedTools") + 1].split(","), TOOLS)
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import live_server
        self.assertEqual(args[args.index("--disallowedTools") + 1].split(","), live_server.DENY_TOOLS)
        self.assertEqual(live_server.VIP_TOOLS, TOOLS)
        self.assertNotIn("--model", args)
        self.assertEqual(calls[0]["headless"], "1")                                          # run_env()

    def test_the_prompt_names_the_zone_leaves_invites_out_and_asks_for_the_fields(self):
        prompt = self.s.calls()[0]["args"][-1]
        self.assertIn("since 2026-10-08T07:00+04:00 (Alan's local time, UTC+04:00)", prompt)
        self.assertIn("give every time in Alan's local time, UTC+04:00 as YYYY-MM-DDTHH:MM+04:00, never in any other zone", prompt)
        self.assertIn("Leave out calendar invites, meeting requests, meeting updates and replies to them", prompt)
        self.assertIn('"kind": "teams"|"mail",', prompt)
        self.assertNotIn('"calendar"', prompt)
        self.assertIn("copy every ID exactly as the tool gave it, character for character", prompt)
        self.assertIn("never the message's internet message ID", prompt)
        for field in ('"type"', '"ask"', '"due"', '"owners"', '"match"', '"last_from"', '"replied"', '"closes"'):
            self.assertIn(field, prompt)
        self.assertIn('"ABC-A-007"', prompt)                                                 # OPEN WORK filled
        self.assertIn("OPEN: []", prompt)                                                    # no open cards yet
        self.assertIn("Never for a private conversation", prompt)
        self.assertEqual(re.findall(r"VIP", prompt.replace("creaite VIP check.", "").replace("Never use the word VIP", "")), [])

    def test_the_reply_is_checked_before_it_is_recorded(self):
        alerts = vip_file(self.s.v)["alerts"]
        self.assertEqual(sorted(a["title"] for a in alerts),
                         ["Project Falcon revised plan", "Project Falcon revised plan 4"])         # invites, no zone, unasked out
        bad = next(a for a in alerts if a["title"].endswith(" 4"))
        self.assertIsNone(bad["conv"])
        good = next(a for a in alerts if a["title"] == "Project Falcon revised plan")
        self.assertEqual(good["closes"]["id"], "ABC-A-007")
        self.assertEqual(good["last"], "2026-10-08 09:00")
        self.assertNotIn(SECRET, json.dumps(vip_file(self.s.v)))

    def test_the_debug_log_has_one_line_of_counts_seconds_and_dollars(self):
        lines = [ln for ln in self.s.log().splitlines() if re.search(r"\s+vip\s", ln)]
        self.assertEqual(len(lines), 1, lines)
        line = lines[0]
        self.assertRegex(line, r"check: 6 returned, 2 kept, dropped .*invite 2.*, 2 new or updated, 0 replied, closes kept 1, "
                               r"\d+\.\ds, \$0\.3027")
        for word in ("Falcon", "mia@", "AAQk", "DX123", "Sara", SECRET, "Project"):
            self.assertNotIn(word, line)

    def test_z_the_close_route_stages_and_undoes_and_says_no_label(self):
        aid = next(a["id"] for a in vip_file(self.s.v)["alerts"] if a.get("closes"))
        said = [self.s.post("/api/alerts/close", {"id": aid})]
        self.assertEqual((said[0]["ok"], said[0]["state"], said[0]["id"]), (True, "staged", "ABC-A-007"))
        self.assertEqual(said[0]["closes"]["staged"]["proposal"], said[0]["proposal"])
        said.append(self.s.post("/api/alerts/close", {"id": aid}))
        self.assertEqual((said[1]["ok"], said[1]["error"]), (False, "Already staged for Review."))
        said.append(self.s.post("/api/vip", {}))
        card = next(a for a in said[-1]["alerts"] if a["id"] == aid)
        self.assertIn("staged", card["closes"])
        said.append(self.s.post("/api/alerts/close", {"id": aid, "undo": True}))
        self.assertEqual((said[-1]["ok"], said[-1]["state"]), (True, "undone"))
        self.assertEqual(list((self.s.v.root / "system/staging").glob("proposed-*-dashboard*.json")), [])
        said.append(self.s.post("/api/alerts/close", {"id": "nope"}))
        self.assertFalse(said[-1]["ok"])
        self.assertNotRegex(json.dumps(said), r"\bVIP\b")


class SweepDuringTheCallTests(ServerCheck, unittest.TestCase):
    def test_a_sweep_starting_during_the_call_drops_the_result(self):
        self.start([owner_done()], sweep=True)
        try:
            self.wait(lambda: "check dropped" in self.log(), "the result dropped")
            st = vip_file(self.v)
            self.assertEqual((st["alerts"], st["last_check"]), ([], "2026-10-08 07:00"))
            self.assertEqual(len(self.calls()), 1)
        finally:
            self.stop()


class FailedCheckTests(ServerCheck, unittest.TestCase):
    def test_a_reply_that_is_not_a_list_changes_nothing_and_logs_the_failure(self):
        self.start({"not": "a list"})
        try:
            self.wait(lambda: "check failed" in self.log(), "the failure logged")
            st = vip_file(self.v)
            self.assertEqual((st["alerts"], st["last_check"]), ([], "2026-10-08 07:00"))
            self.assertRegex(self.log(), r"check failed after \d+\.\ds, \$0\.3027")
            self.assertIn("didn't finish", self.post("/api/vip", {})["error"])
        finally:
            self.stop()


TIMER = """import sys, json, time
sys.path.insert(0, 'system/scripts')
import live_server
sleeps = []
def nap(s):
    sleeps.append(s)
    if len(sleeps) >= 2:
        raise KeyboardInterrupt        # not an Exception: it ends the loop after its second wait
time.sleep = nap
try:
    live_server.vip_timer()
except KeyboardInterrupt:
    pass
print("RESULT " + json.dumps({"sleeps": sleeps, "error": live_server.VIP_STATUS["last_error"]}))
"""


class HandEditedSettingsTests(Base):
    """Review point 4: a hand-edited "vip" or "drafting" that isn't a block reads as the defaults; the timer never dies."""

    def loop(self, **blocks):
        cfg = self.v.root / "system/config/settings.json"
        self.orig = getattr(self, "orig", None) or cfg.read_text()
        d = {**json.loads(self.orig), **blocks}                                              # only this case's blocks
        cfg.write_text(json.dumps(d))
        for f in self.v.root.glob("vip-call-*.json"):
            f.unlink()
        check_since(self.v)                                                                  # a fresh vip.json each time
        fake = self.v.root / "fake_claude.py"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        (self.v.root / "vip-replies.json").write_text(json.dumps([[owner_done()]]))
        r = subprocess.run([sys.executable, "-c", TIMER], cwd=self.v.root, capture_output=True, text=True, timeout=120,
                           env={**os.environ, "CREAITE_CLAUDE": str(fake), "CREAITE_NOW": NOW, "CREAITE_TZ_OFFSET": OFF})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return json.loads(r.stdout.split("RESULT ", 1)[1]), len(list(self.v.root.glob("vip-call-*.json")))

    def test_vip_or_drafting_off_null_or_a_list_runs_the_check_with_the_defaults(self):
        for name, blocks in (("vip off", {"vip": "off"}), ("drafting off", {"drafting": "off"}), ("vip null", {"vip": None}),
                             ("vip list", {"vip": []}), ("both off", {"vip": "off", "drafting": "off"})):
            with self.subTest(name):
                got, calls = self.loop(**blocks)
                self.assertEqual(calls, 2)                                                   # it survived a loop
                self.assertEqual(got, {"sleeps": [1800.0, 1800.0], "error": None})           # check_minutes 30
                self.assertEqual(self.cards()[0]["closes"]["id"], "ABC-A-007")               # drafting.done on

    def test_the_readers_take_a_non_block_as_empty(self):
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.update({"vip": "off", "drafting": [], "identity": "x"})
        cfg.write_text(json.dumps(d))
        got = py(self.v, "import extraction\nprint(json.dumps([sweep.vip_settings(), extraction.switched_on('done'), "
                         "sweep.my_name(), extraction.is_alan('Alan Carter')]))")
        self.assertEqual(got, [{"enabled": True, "check_minutes": 30, "notify": True}, True, "", False])


DEEP = "[" * 100000 + "]" * 100000


class DeepReplyTests(ServerCheck, unittest.TestCase):
    """Review point 3: a reply nested too deeply to read is an unfinished check (RecursionError on Python 3.9)."""

    def test_vip_reply_treats_a_recursion_error_as_unfinished(self):
        from types import SimpleNamespace
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import live_server
        r = SimpleNamespace(stdout=json.dumps({"result": DEEP, "total_cost_usd": 0.1}), stderr="")
        real = live_server.json

        class Deep:
            dumps = staticmethod(real.dumps)

            @staticmethod
            def loads(text):
                if text.startswith("[["):
                    raise RecursionError("maximum recursion depth exceeded")
                return real.loads(text)
        live_server.json = Deep
        try:
            self.assertEqual(live_server.vip_reply(r), (None, "RecursionError", 0.1))
        finally:
            live_server.json = real

    def test_a_deeply_nested_reply_records_nothing_and_the_server_keeps_running(self):
        self.start(DEEP)
        try:
            self.wait(lambda: re.search(r"INFO\s+vip\s", self.log()), "a check logged")
            st = vip_file(self.v)
            self.assertEqual(st["alerts"], [])                                               # a newer Python reads it: no card
            if sys.version_info < (3, 12):                                                   # 3.9 to 3.11 can't read it
                self.assertEqual(st["last_check"], "2026-10-08 07:00")
                self.assertIn("check failed", self.log())
                self.assertIn("didn't finish", self.post("/api/vip", {})["error"])
            self.assertEqual(urllib.request.urlopen(self.base + "/health", timeout=5).status, 200)
        finally:
            self.stop()


class InvitesFlipTests(unittest.TestCase):
    def test_vip_invites_true_puts_the_bl334_sentence_back(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import live_server
        zone = {"tz": None, "offset": OFF, "zone": "Alan's local time, UTC+04:00"}
        parts = {"open": "[]", "open_work": "{}"}
        off = live_server.vip_prompt("2026-10-08 07:00", {"mia@client.example": "Mia Hale"}, zone, parts)
        try:
            live_server.VIP_INVITES = True
            on = live_server.vip_prompt("2026-10-08 07:00", {"mia@client.example": "Mia Hale"}, zone, parts)
        finally:
            live_server.VIP_INVITES = False
        self.assertIn("and calendar invites or updates", on)
        self.assertIn('"kind": "teams"|"mail"|"calendar"', on)
        self.assertNotIn("Leave out calendar invites", on)
        self.assertIn("Leave out calendar invites", off)
        self.assertIsInstance(live_server.VIP_INVITES, bool)
        self.assertFalse(live_server.VIP_INVITES)


if __name__ == "__main__":
    unittest.main()

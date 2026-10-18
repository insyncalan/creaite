"""BL-342 Part 3 B: the one check with the card fields, its reply's checks and the close suggestions (step 9), part 3 of 3 (the fixture is in vip_single_call_support.py).

Run: python3 dev/tests/test_vip_single_call_close.py
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vip_single_call_support import (  # noqa: E402
    Base,
    DEEP,
    FAKE,
    MAIL_ID,
    NOW,
    OFF,
    SECRET,
    ServerCheck,
    TIMER,
    check_since,
    closing,
    owner_done,
    py,
    thread,
    urllib,
    vip_file,
)


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

    def test_evidence_in_single_curly_or_guillemet_quotes_is_refused(self):
        run = "the revised plan is attached here for everyone to review now ok"
        summary = f"Mia said {run}, thanks."
        for ev in (f"She wrote '{run}'", f"She wrote \u2018{run}\u2019", f"\u00ab{run}\u00bb", f"\u201c{run}\u201d",
                   f'Sara: "{run}"'):
            with self.subTest(ev):
                got = self.check([owner_done(summary=summary, closes={"id": "ABC-A-007", "evidence": ev})])
                self.assertIsNone(self.closes())
                self.assertEqual(got["counts"].get("closes_quoted"), 1)
                (self.v.root / "system/staging/vip.json").unlink()

    def test_evidence_that_restates_the_summary_in_its_own_words_passes(self):
        # Review (e), for Alan to confirm: the summary is the model's words, not the message's, so a long run shared with
        # it is not a quotation; only the quote rules and the whole-summary rule refuse.
        summary = "Mia asks whether the SOW went out; Sara confirmed the signed statement of work was sent to the client on Tuesday."
        for ev in ("Sara confirmed the signed statement of work was sent to the client.",
                   "Sara: THE SIGNED STATEMENT OF WORK WAS SENT TO THE CLIENT ON TUESDAY, done"):
            with self.subTest(ev):
                got = self.check([owner_done(summary=summary, closes={"id": "ABC-A-007", "evidence": ev})])
                self.assertEqual(self.closes()["evidence"], ev)
                self.assertNotIn("closes_quoted", got["counts"])
                (self.v.root / "system/staging/vip.json").unlink()
        got = self.check([owner_done(summary=summary, closes={"id": "ABC-A-007", "evidence":
                                     'Sara wrote "the signed statement of work was sent to the client on Tuesday"'})])
        self.assertIsNone(self.closes())                                                     # a quoted run still refused
        self.assertEqual(got["counts"].get("closes_quoted"), 1)

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

    def test_vip_null_a_list_or_a_stray_value_or_drafting_off_runs_the_check_with_the_defaults(self):
        for name, blocks in (("drafting off", {"drafting": "off"}), ("vip null", {"vip": None}), ("vip list", {"vip": []}),
                             ("vip on", {"vip": "on"}), ("vip 5", {"vip": 5}), ("vip True", {"vip": True})):
            with self.subTest(name):
                got, calls = self.loop(**blocks)
                self.assertEqual(calls, 2)                                                   # it survived a loop
                self.assertEqual(got, {"sleeps": [1800.0, 1800.0], "error": None})           # check_minutes 30
                self.assertEqual(self.cards()[0]["closes"]["id"], "ABC-A-007")               # drafting.done on

    def test_vip_off_false_no_0_or_false_turns_the_check_off_and_the_timer_lives(self):
        # Review (b), for Alan to confirm: a hand edit that says off means off, never the defaults' on.
        for value in ("off", " OFF ", "False", "no", "0", False, 0, 0.0):
            with self.subTest(repr(value)):
                got, calls = self.loop(vip=value, drafting="off")
                self.assertEqual(calls, 0)                                                   # no check at all
                self.assertEqual(got, {"sleeps": [1800.0, 1800.0], "error": None})           # the timer still loops
                said = py(self.v, "print(json.dumps(sweep.vip_settings()))")
                self.assertEqual(said, {"enabled": False, "check_minutes": 30, "notify": True})

    def test_the_readers_take_a_non_block_as_empty(self):
        cfg = self.v.root / "system/config/settings.json"
        d = json.loads(cfg.read_text())
        d.update({"vip": "off", "drafting": [], "identity": "x"})
        cfg.write_text(json.dumps(d))
        got = py(self.v, "import extraction\nprint(json.dumps([sweep.vip_settings(), extraction.switched_on('done'), "
                         "sweep.my_name(), extraction.is_alan('Alan Carter')]))")
        self.assertEqual(got, [{"enabled": False, "check_minutes": 30, "notify": True}, True, "", False])   # "off" is off (b)


class HandEditedIdentityTests(Base):
    """Review F4 (missed reader): a hand-edited "identity" that isn't a block ("Alan", [], null) reads as no identity in
    every reader on the VIP path (sweep._alan_identity, propose.identity_person), so vip_clean and vip_closes still run."""

    def test_identity_alan_a_list_or_null_still_records_the_card_and_its_close(self):
        cfg = self.v.root / "system/config/settings.json"
        orig = cfg.read_text()
        for name, value in (("a string", "Alan"), ("a list", []), ("null", None)):
            with self.subTest(name):
                cfg.write_text(json.dumps({**json.loads(orig), "identity": value}))
                check_since(self.v)
                got = self.check([owner_done()])
                self.assertEqual(len(got["new"]), 1)                                         # the check survived
                self.assertEqual(self.cards()[0]["closes"]["id"], "ABC-A-007")               # vip_closes ran
                said = py(self.v, "import propose\nprint(json.dumps([list(sweep._alan_identity()[:1]), "
                                  "propose.identity_person(), len(propose.people_legacy_names())]))")
                self.assertEqual(said, [[""], None, 2])


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


class FailedCheckWordsTests(ServerCheck, unittest.TestCase):
    """Review point 7a: a failed check shows fixed words and a count, never the model's prose."""

    def test_the_models_prose_never_reaches_the_error(self):
        self.start(f"Sorry, I could not finish: {SECRET}")
        try:
            self.wait(lambda: "check failed" in self.log(), "the failure logged")
            error = self.post("/api/vip", {})["error"]
            self.assertIn("the VIP check didn't finish: its reply couldn't be used (", error)
            self.assertRegex(error, r"\(\d+ characters held back\)$")
            self.assertNotIn(SECRET, error + self.log())
            self.assertNotIn("Sorry", error)
        finally:
            self.stop()

    def test_the_fixed_reasons_are_shown_as_they_are(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import live_server
        self.assertEqual(live_server.vip_why(live_server.VIP_TIMED_OUT), "it timed out")
        self.assertEqual(live_server.vip_why(live_server.VIP_NOT_STARTED), "claude couldn't be started")
        self.assertEqual(live_server.vip_why("Mia wrote " + SECRET), f"its reply couldn't be used ({10 + len(SECRET)} characters held back)")


class InvitesFlipTests(unittest.TestCase):
    def test_vip_invites_true_puts_the_bl334_sentence_back(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import live_server
        zone = {"tz": None, "offset": OFF, "zone": "Alan's local time, UTC+04:00"}
        parts = {"open": "[]", "open_work": "{}", "open_promises": "{}"}
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

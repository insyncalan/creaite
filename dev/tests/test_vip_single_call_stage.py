"""BL-342 Part 3 B: the one check with the card fields, its reply's checks and the close suggestions (step 9), part 2 of 3 (the fixture is in vip_single_call_support.py).

Run: python3 dev/tests/test_vip_single_call_stage.py
"""
import json
import os
import re
import sqlite3
import subprocess
import time
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vip_single_call_support import (  # noqa: E402
    Base,
    MAIL_ID,
    MERGE,
    NOW,
    OFF,
    REPLY,
    SECRET,
    ServerCheck,
    TOOLS,
    closing,
    owner_done,
    py,
    thread,
    vip_file,
)


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

    def alan_sets(self, status):
        [(name, item)] = self.staged()
        f = self.v.root / "system/staging" / name
        spec = json.loads(f.read_text())
        spec["items"][0]["changes"]["status"] = status                                       # his edit in Review
        spec["items"][0]["edited_in"] = "dashboard"
        f.write_text(json.dumps(spec))

    def test_undo_keeps_a_status_alan_set_on_the_pending_item(self):
        # Review (c): Undo takes out only what the stage added.
        self.call("vip_log")
        self.alan_sets("Closed")                                                             # before the click
        self.call("vip_close_stage")
        self.call("vip_close_unstage")
        [(name, item)] = self.staged()
        self.assertEqual(item["changes"]["status"], "Closed")                                # his status stays
        self.assertNotIn("status_before", item["suggested"])
        self.assertFalse(any("Looks done" in ln for ln in item["changes"]["latest_update"].splitlines()))

    def test_undo_keeps_a_status_alan_changed_after_the_stage(self):
        self.call("vip_log")
        self.call("vip_close_stage")
        self.alan_sets("Cancelled")                                                          # after the click
        self.call("vip_close_unstage")
        [(name, item)] = self.staged()
        self.assertEqual(item["changes"]["status"], "Cancelled")

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

    def test_when_both_closes_are_staged_undo_on_the_kept_card_leaves_no_proposal_for_either(self):
        # Review (d): the dropped card's staged close is carried, so it is never left pending with nothing pointing to it.
        b = self.second(close=True)
        self.stage("vip_close_stage", self.a)
        self.stage("vip_close_stage", b)
        [(name, item)] = self.proposals()                                                    # one pending item, both lines
        self.assertEqual(item["suggested"]["closes"], [self.a, b])
        kept = self.merge(self.a, b)
        self.assertEqual([m["card"] for m in kept["closes"]["staged"]["merged"]], [b])
        self.assertEqual(self.stage("vip_close_unstage", self.a)["state"], "undone")
        self.assertEqual(self.proposals(), [])                                              # neither close left

    def test_when_both_closes_are_staged_after_a_log_undo_leaves_logs_line_only(self):
        b = self.second(close=True)
        self.stage("vip_log", self.a)
        self.stage("vip_close_stage", self.a)
        self.stage("vip_close_stage", b)
        self.merge(b, self.a)
        self.stage("vip_close_unstage", b)
        [(name, item)] = self.proposals()
        self.assertNotIn("status", item["changes"])
        self.assertNotIn("closes", item["suggested"])
        self.assertFalse(any("Looks done" in ln for ln in item["changes"]["latest_update"].splitlines()))

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


class MergePinTests(unittest.TestCase):
    """BL-342 Part 3 B v2: what the rebuild on main must keep from both sides (main's VIP security fix, 9c1a0c2f, and
    Part 3 B's limits and prompt parts)."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system/scripts"))
        import live_server
        import sweep
        cls.ls, cls.sw = live_server, sweep

    def test_main_security_fix_is_kept(self):
        self.assertFalse(hasattr(self.ls, "VIP_ARGS"))                                       # #116: no --tools flag
        deny = self.ls.vip_deny()
        for t in self.ls.DENY_TOOLS + self.ls.VIP_BUILTIN_DENIES:
            self.assertIn(t, deny)
        self.assertNotIn("ToolSearch", deny)                                                 # it loads the deferred M365 tools

    def test_the_command_line_has_both_and_one_launch(self):
        src = Path(self.ls.__file__).read_text(encoding="utf-8")
        body = src[src.index("def vip_check("):src.index("\ndef ", src.index("def vip_check(") + 1)]
        self.assertEqual(body.count("prompt_last("), 1)                                      # one command
        self.assertEqual(body.count("subprocess.run("), 1)                                   # one launch
        self.assertIn('"--disallowedTools", ",".join(vip_deny())], prompt)', body)
        self.assertNotIn("join(DENY_TOOLS)", body)
        cmd = self.ls.prompt_last(["claude", "-p", "--allowedTools", ",".join(self.ls.VIP_TOOLS),
                                   "--disallowedTools", ",".join(self.ls.vip_deny())], "PROMPT")
        self.assertEqual(cmd[-2:], ["--", "PROMPT"])                                         # the prompt, alone, after --
        self.assertEqual(cmd.count("--"), 1)
        self.assertNotIn("--tools", cmd)

    def test_the_real_checks_argv_is_mains_exactly_to_the_end(self):
        # The real vip_check with a stand-in claude recording its argv: the whole command, so an argument added
        # anywhere (before -p's options, between them, or after the prompt) fails here too (review: v2 MergePinTests).
        s = ServerCheck()
        s.fail = self.fail
        s.start(REPLY)
        try:
            s.wait(lambda: s.calls(), "a call recorded")
            args = s.calls()[0]["args"]
        finally:
            s.stop()
        self.assertEqual(args[:-1], ["-p", "--output-format", "json", "--allowedTools", ",".join(self.ls.VIP_TOOLS),
                                     "--disallowedTools", ",".join(self.ls.vip_deny()), "--"])
        self.assertTrue(args[-1].startswith("creaite VIP check."))                          # the prompt, alone, last
        self.assertNotIn("ToolSearch", args[args.index("--disallowedTools") + 1].split(","))

    def test_part_3b_limits_and_prompt_parts_are_unchanged(self):
        self.assertEqual((self.sw.VIP_MIN_MINUTES, self.sw.VIP_MAX_MINUTES), (10, 240))
        self.assertEqual((self.sw.VIP_WORK_PER_PROJECT, self.sw.VIP_WORK_MAX), (15, 60))
        for ph in ("{open}", "{open_work}", "{since}", "{zone}", "{offset}", "{sources}", "{kinds}", "{addresses}"):
            self.assertIn(ph, self.ls.VIP_PROMPT)

    def test_part_5_adds_one_placeholder_and_its_limits_only(self):
        # BL-342 Part 5: the prompt gains {open_promises} (filled by plain code, at most 10 a project and 30 in all) and
        # nothing else; the placeholders are exactly these nine, so a new one can't slip in unpinned.
        self.assertEqual((self.sw.VIP_PROMISES_PER_PROJECT, self.sw.VIP_PROMISES_MAX), (10, 30))
        self.assertEqual(self.ls.VIP_PROMPT.count("{open_promises}"), 1)
        names = set(re.findall(r"(?<!\{)\{([a-z_]+)\}(?!\})", self.ls.VIP_PROMPT))
        self.assertEqual(names, {"open", "open_work", "open_promises", "since", "zone", "offset", "sources", "kinds", "addresses"})
        src = Path(self.ls.__file__).read_text(encoding="utf-8")
        body = src[src.index("def vip_prompt("):src.index("\ndef ", src.index("def vip_prompt(") + 1)]
        self.assertIn('open_promises=parts["open_promises"]', body)
        self.assertEqual(src.count("prompt_last([claude_path(), \"-p\", \"--output-format\", \"json\", \"--allowedTools\", "
                                   "\",\".join(VIP_TOOLS),"), 1)                              # the check's one command line


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
        self.assertEqual(args[args.index("--disallowedTools") + 1].split(","), live_server.vip_deny())   # main's 9c1a0c2f
        self.assertNotIn("--tools", args[:args.index("--")])                                 # #116: no --tools flag
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


if __name__ == "__main__":
    unittest.main()

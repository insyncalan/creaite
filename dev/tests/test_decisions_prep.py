"""BL-113: meeting prep and the sweep learn decisions needed (Sprint 5's hand-offs).

Run: python3 dev/tests/test_decisions_prep.py   (the last class needs Google Chrome; skipped otherwise)

  - sweep.py stage no longer dates a pending decision, and a message that makes (or withdraws) a pending decision is staged as an
    update to it, the way minutes.py stages one;
  - meeting prep (the brief and the Prep page's context) lists the project's pending decisions and the made decisions whose revisit
    date has come.
"""
import json
import subprocess
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_dashboard import today as _cx_today  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

TODAY = _cx_today()


def d(n):
    return (TODAY + timedelta(days=n)).isoformat()


SRC = f"{ABC}/minutes/{d(-5)} Steering.docx — Decisions"


def email(subject="[ABC] Pilot", sender="Sara Example <sara@client.example>", link="d1", sent="2026-10-08"):
    return (f"Email · From: {sender} · Subject: {subject} · Sent: {sent} 10:15 · "
            f"Link: https://outlook.office365.com/owa/?ItemID={link}")


def dec(n, **v):
    return {"n": n, "op": "new", "table": "decisions", "match": "strong", "flags": [], "decision": "approved",
            "values": {"project": "ABC", "source": SRC, **v}}


class SweepBase(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", [dec(1, decision="Extend the pilot by two weeks", status="Pending", made_by="Omar Ali", needed_by="2026-10-12"),
                                dec(2, decision="Use the shared tenant", date="2026-10-01", made_by="Alan Carter")])
        self.v.run("apply")
        self.drafts = self.v.root / "system/staging/drafts"
        self.drafts.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.v.cleanup()

    def stage(self, items, ok=True):
        f = self.drafts / "sweep.json"
        f.write_text(json.dumps({"window": {"start": "2026-10-07 08:00", "end": "2026-10-09 08:00"}, "items": items}))
        return self.v.run("stage", str(f), script="sweep.py", ok=ok).stdout

    def staged(self):
        files = self.sweeps()
        return json.loads(files[-1].read_text()) if files else None

    def sweeps(self):
        return sorted((self.v.root / "system/staging").glob("proposed-2*-sweep*.json"), key=lambda p: p.stat().st_mtime_ns)

    def row(self, id_):
        return next(r for r in self.v.rows("decisions") if r["id"] == id_)

    def update(self, item_id="ABC-D-001", set_=None, **extra):
        return {"op": "update", "table": "decisions", "id": item_id, "set": set_ if set_ is not None else {"status": "Made"},
                "why": "Sara confirmed by email", "source": email(), **extra}


class PendingDecisionsFromMail(SweepBase):
    n = 0

    def new(self, **v):
        self.n += 1                                          # a fresh message each time: the same one twice is skipped
        return {"table": "decisions", "match": "strong", "values": {"project": "ABC", "decision": f"Confirm the UAT venue {self.n}",
                                                                   "made_by": "Alan Carter", "source": email(link=f"n{self.n}"), **v}}

    def test_a_pending_decision_is_not_dated(self):
        for extra in ({"status": "Pending"}, {"status": "Pending", "date": ""}):
            self.stage([self.new(**extra)])
            v = self.staged()["items"][-1]["values"]
            self.assertNotIn("date", v, extra)
            self.assertEqual(v["status"], "Pending")
        self.v.propose("sweep-apply", [{**i, "decision": "approved"} for i in self.staged()["items"]])
        self.v.run("apply")
        rows = [r for r in self.v.rows("decisions") if r["decision"].startswith("Confirm the UAT venue")]
        self.assertTrue(rows)
        self.assertEqual({(r["status"], r["date"]) for r in rows}, {("Pending", None)})

    def test_a_made_decision_is_still_dated_the_day_it_is_staged(self):
        for extra in ({}, {"date": ""}):
            self.stage([self.new(**extra)])
            v = self.staged()["items"][-1]["values"]
            self.assertEqual(v["date"], TODAY.isoformat(), extra)
        self.stage([self.new(date="2026-10-07")])
        self.assertEqual(self.staged()["items"][-1]["values"]["date"], "2026-10-07")


class DecisionUpdatesFromMail(SweepBase):
    def test_a_message_that_makes_a_pending_decision_is_staged_as_an_update(self):
        out = self.stage([self.update(set_={"status": "Made", "reasoning": "Sara agreed on the 8th"})])
        item = self.staged()["items"][0]
        self.assertEqual((item["op"], item["table"], item["id"], item["decision"]), ("update", "decisions", "ABC-D-001", "pending"))
        self.assertEqual(item["changes"], {"status": "Made", "reasoning": "Sara agreed on the 8th", "date": "2026-10-08"})   # the Sent day
        self.assertEqual(item["based_on"], self.row("ABC-D-001")["updated_at"])
        self.assertEqual(item["why"], "Sara confirmed by email")
        self.assertEqual(item["source"], email())
        self.assertNotIn("invalid", item["flags"])
        self.assertIn("Sweep: 1 item", out)
        review = self.v.run("list", "--json", script="review.py").stdout
        self.assertIn("ABC-D-001", review)

    def test_approving_it_makes_the_decision_and_keeps_its_number(self):
        self.stage([self.update(set_={"status": "Made", "date": "2026-10-07"})])
        data = self.staged()
        data["items"][0]["decision"] = "approved"
        self.sweeps()[-1].write_text(json.dumps(data))
        self.v.run("apply")
        row = self.row("ABC-D-001")
        self.assertEqual((row["status"], row["date"], row["made_by"], row["needed_by"]), ("Made", "2026-10-07", "Omar Ali", "2026-10-12"))
        self.assertEqual(len(self.v.rows("decisions")), 2)                                        # no second decision

    def test_a_message_can_withdraw_one_or_move_the_date_it_is_needed_by(self):
        self.stage([self.update(set_={"needed_by": "2026-10-20"}, why="Sara asked for more time")])
        self.assertEqual(self.staged()["items"][0]["changes"], {"needed_by": "2026-10-20"})
        self.stage([self.update(set_={"status": "Withdrawn"}, source=email(link="w1"))])
        self.assertEqual(self.staged()["items"][0]["changes"], {"status": "Withdrawn"})

    def test_two_messages_about_one_decision_merge_into_one_update(self):
        self.stage([self.update(set_={"needed_by": "2026-10-20"}), self.update(set_={"made_by": "Sara Example"}, source=email(link="d2"))])
        items = self.staged()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["changes"], {"made_by": "Sara Example", "needed_by": "2026-10-20"})

    def test_what_is_refused_says_why(self):
        out = self.stage([self.update("ABC-D-002"),                                               # already made
                          self.update("ABC-D-009"),                                               # not in the tracker
                          self.update(set_={"owner": "Sara Example"}, source=email(link="r1")),   # not a field a message may change
                          {**self.update(source=email(link="r2")), "table": "actions", "id": "ABC-A-001"},
                          self.update(source="somewhere"),                                         # not a structured source
                          self.update(set_={"status": "Pending"}, source=email(link="r3"))])      # no change
        self.assertIsNone(self.staged())
        self.assertIn("rejected update: ABC-D-002 is Made; only open items are updated", out)
        self.assertIn("rejected update: ABC-D-009 isn't in the tracker", out)
        self.assertIn("owner can't be changed from minutes", out)
        self.assertIn("a message may change latest_update, due_date only, not status", out)   # BL-297: actions move forward, never close
        self.assertIn("skipped (no structured Email/Teams source): update to ABC-D-001", out)
        self.assertIn("no change to ABC-D-001", out)

    def test_the_same_message_twice_is_not_proposed_twice(self):
        self.stage([self.update()])
        out = self.stage([self.update()])
        self.assertIn("skipped (proposed before from the same message): update to ABC-D-001", out)
        self.assertEqual(len(self.sweeps()), 1)

    def test_an_ignore_rule_applies_and_the_message_is_logged_as_raising_it_again(self):
        out = self.stage([self.update(source=email(subject="[ABC] ToDo pilot", link="i1"))])
        self.assertIn("ignore rule", out)
        self.assertIsNone(self.staged())
        self.stage([self.update()])
        mentions = (self.v.root / "system/staging/mentions.jsonl").read_text(encoding="utf-8")
        self.assertIn('"id": "ABC-D-001"', mentions)
        self.assertIn('"run": "cx-sweep"', mentions)

    def test_a_stale_update_becomes_a_conflict_not_a_silent_overwrite(self):
        self.stage([self.update(set_={"needed_by": "2026-10-20"})])
        self.v.propose("edit", [{"n": 1, "op": "update", "table": "decisions", "id": "ABC-D-001", "changes": {"needed_by": "2026-10-15"},
                                 "match": "strong", "flags": [], "decision": "approved"}])
        self.v.run("apply")
        files = self.sweeps()
        data = json.loads(files[-1].read_text())
        data["items"][0]["decision"] = "approved"
        files[-1].write_text(json.dumps(data))
        self.v.run("apply")
        self.assertEqual(self.row("ABC-D-001")["needed_by"], "2026-10-15")                       # held for review, not applied
        self.assertIn("conflict", json.loads(files[-1].read_text())["items"][0]["flags"])


def prep_world(v):
    """ABC with a pending decision (late), another (no date), a made one whose revisit date has come, one revisit still ahead,
    and a pending decision of DEF; a meeting today called "ABC weekly"."""
    populate(v)
    v.propose("dec", [
        dec(1, decision="Extend the pilot by two weeks", status="Pending", made_by="Sara Example", needed_by=d(-3)),
        dec(2, decision="Choose the UAT venue", status="Pending", made_by="Alan Carter"),
        dec(3, decision="Use masked data for UAT", date=d(-40), made_by="Jane Doe", revisit=d(-1)),
        dec(4, decision="Keep the weekly cadence", date=d(-40), made_by="Jane Doe", revisit=d(30)),
        dec(5, project="DEF", decision="Approve the pilot budget", status="Pending", made_by="Omar Ali"),
    ])
    v.run("apply")
    (v.root / "system/staging/calendar.json").write_text(json.dumps({"fetched": f"{TODAY} 07:00", "days": {TODAY.isoformat(): [
        {"id": "t1", "start": "09:00", "end": "10:00", "title": "ABC weekly", "where": "Teams", "teams": True, "organiser": "Jane Doe",
         "all_day": False, "private": False, "sensitivity": "normal", "body": "Agenda: pilot extension; UAT venue",
         "attendees": [{"name": "Sara Example", "type": "required", "response": "accepted"}]}]}}))


class PrepData(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        prep_world(self.v)

    def tearDown(self):
        self.v.cleanup()

    def context(self):
        r = self.v.run("context", "09:00|ABC weekly", script="prep_page.py")
        try:
            return json.loads(r.stdout[r.stdout.index("{"):])           # a "Note:" line may come first
        except ValueError:
            raise AssertionError(f"not JSON:\n{r.stdout}\n{r.stderr}")

    def test_the_prep_page_context_lists_both_kinds_with_their_dates(self):
        ctx = self.context()
        by = {i["id"]: i for i in ctx["items"] if i["table"] == "decisions"}
        ids = {i: (x["type"], x["due"], x["status"]) for i, x in by.items()}
        pending = [i for i, x in by.items() if x["type"] == "Decision needed"]
        self.assertEqual(sorted(pending), ["ABC-D-006"])                                          # BL-126: one with no needed-by date isn't due
        late = by["ABC-D-006"]
        self.assertEqual((late["type"], late["due"], late["owner"], late["status"]), ("Decision needed", d(-3), "Sara Example", "Pending"))
        self.assertNotIn("ABC-D-007", by)
        rev = next(x for x in by.values() if x["type"] == "Decision to revisit")
        self.assertEqual((rev["text"], rev["due"]), ("Use masked data for UAT", d(-1)))
        self.assertNotIn("Keep the weekly cadence", [x["text"] for x in by.values()])             # revisit still ahead
        self.assertNotIn("DEF-D-002", ids)                                                         # another project's

    def test_the_prompt_tells_claude_what_the_two_types_mean(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import prep_page
        flat = " ".join(prep_page.PROMPT.split())
        self.assertIn('Items of type "Decision needed"', flat)
        self.assertIn('"Decision to revisit"', flat)

    def test_the_built_page_lists_them_in_the_work_items_table(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "system" / "scripts"))
        import prep_page
        ctx = self.context()
        html = prep_page.render(ctx, {})
        self.assertIn("Decision needed", html)
        self.assertIn("Decision to revisit", html)
        self.assertIn("Extend the pilot by two weeks", html)

    def test_the_invite_ranks_a_pending_decision_it_mentions(self):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/build_dashboard.py")], capture_output=True, text=True,
                           cwd=self.v.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        data = json.loads(__import__("re").search(r'id="data">(.*?)</script>', html, __import__("re").S).group(1).replace("<\\/", "</"))
        rank = data["prep"]["meetings"]["09:00|ABC weekly"]["rank"]["decisions"]
        self.assertIn("ABC-D-006", rank)                                                          # "pilot extension" is in the invite
        self.assertIn("ABC-D-007", rank)                                                          # "UAT venue" too


class PrepBrief(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        prep_world(v)

    def open_prep(self):
        b = self.b
        b.eval("openPrep(prepTimed()[0])")
        b.wait("document.querySelector('#prepBody .prepsec')")
        return b

    def section(self, ident):
        return self.b.eval(f"(()=>{{ const s=document.getElementById('{ident}'); return s?[...s.querySelectorAll('.wlist > div')].map(x=>x.textContent):null; }})()")

    def test_the_brief_lists_the_decisions_needed_and_those_to_revisit(self):
        self.open_prep()
        needed = self.section("prepDecNeeded")
        self.assertEqual(len(needed), 2)
        self.assertIn("Extend the pilot by two weeks", needed[0])
        self.assertIn("from Sara Example", needed[0])
        self.assertIn("3 days late", needed[0])                                                    # late first
        self.assertIn("Choose the UAT venue", needed[1])
        self.assertIn("asked of you", needed[1])
        self.assertIn("no date needed by", needed[1])
        rev = self.section("prepDecRevisit")
        self.assertEqual(len(rev), 1)
        self.assertIn("Use masked data for UAT", rev[0])
        self.assertIn("revisit date", rev[0])
        titles = self.b.eval("[...document.querySelectorAll('#prepBody .prepsec h3')].map(h=>h.textContent.replace(/\\s+/g,' ').trim())")
        self.assertLess([i for i, t in enumerate(titles) if t.startswith("Decisions since")][0],
                        [i for i, t in enumerate(titles) if t.startswith("Decisions needed")][0])   # after "Decisions since then"
        self.assertEqual(self.b.eval("document.querySelectorAll('#prepDecs').length"), 1)

    def test_an_item_opens_its_panel_and_the_invite_ranks_first(self):
        self.open_prep()
        why = self.b.eval("document.querySelector('#prepDecNeeded .prepwhy')?.textContent || ''")
        self.assertTrue(why)
        self.b.eval("document.querySelector('#prepDecNeeded [data-open]').click()")
        self.b.wait("CUR&&CUR.id==='ABC-D-006'")

    def test_drawing_the_brief_twice_does_not_repeat_the_sections(self):
        self.open_prep()
        self.b.eval("drawPrep()")
        self.assertEqual(self.b.eval("document.querySelectorAll('#prepDecNeeded').length"), 1)

    def test_a_portfolio_meeting_lists_every_projects_decisions(self):
        self.open_prep()
        try:
            self.b.eval("choosePrep('_portfolio')")
            self.b.wait("document.querySelector('#prepDecNeeded')&&document.querySelectorAll('#prepDecNeeded .wlist > div').length===3")
            self.assertTrue(any("Approve the pilot budget" in t for t in self.section("prepDecNeeded")))
        finally:                                                       # the choice is remembered for the series: put it back
            self.b.eval("choosePrep('ABC')")
            self.b.wait("document.querySelectorAll('#prepDecNeeded .wlist > div').length===2")


if __name__ == "__main__":
    unittest.main()

"""BL-297 (sprint-smart-updates): Smarter updates. Mail, Teams and minutes move existing items forward instead of raising new ones.

- A: `sweep.py expected` lists a project's open items (minutes.py expected's JSON), best matches first, never one raised after the
  message; a message that moves one forward is staged as an update (latest update and due date), never a new item.
- B: plain-code matching (extraction.py): the item ID, the project, the timeframe, the same thread, people and less common words,
  with the two strengths (Very likely from 0.75, Possible from 0.5).
- C: the skill's `repeat: same` makes a Very likely mark on its own, when the item is open and in the item's project.
- D: `review.py retarget` (and `unmerge`, `candidates`; the live server's routes) and Activity › Quality's counts.
- E: an update changing only the due date and latest update is routine; anything else is approved on its own.

The trigger (13-10-2026), with sample names: a reply on "Re: Discuss FalconAI Commercials" asking to rebook the commercials
discussion with Dana for next week, with Tom, should move FAL-A-007 "Reach out to Dana on back to back commercials" forward.

Run: python3 dev/tests/test_smart_updates.py
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "system" / "scripts"))
import extraction  # noqa: E402
import review  # noqa: E402

NOW = "2026-10-15 09:00"
THREAD = ("Email · From: Dana Okoye <dana@kestrel.example> · Subject: Discuss FalconAI Commercials · Sent: 2026-10-06 10:00 · "
          "Link: https://outlook.office365.com/owa/?ItemID=t1")
REPLY = ("Email · From: Dana Okoye <dana@kestrel.example> · Subject: RE: [EXT] Discuss  FalconAI Commercials · Sent: 2026-10-13 16:20 · "
         "Link: https://outlook.office365.com/owa/?ItemID=r1")
OTHER = ("Email · From: Omar Ali <omar@def.example> · Subject: Lunch · Sent: 2026-10-13 11:00 · "
         "Link: https://outlook.office365.com/owa/?ItemID=o1")
REBOOK = "Rebook the FalconAI commercials discussion with Dana Okoye for next week, with Tom"
REGISTER = [{"name": "Dana Okoye", "emails": ["dana@kestrel.example"], "aliases": ["Dana"]},
            {"name": "Tom Reid", "emails": [], "aliases": ["Tom"]}]


def add_fal(v):
    """The FAL project, and Dana and Tom in the people register."""
    reg = v.root / "projects/_portfolio/project-register.md"
    reg.write_text(reg.read_text().replace("|  |  |  |  |  |  |  |  |",
                                           "| FAL | Falcon AI Programme | FAL Falcon AI Programme | FalconAI | Dana Okoye (client) | "
                                           "kestrel.example | FAL core | commercials |", 1))
    people = v.root / "projects/_portfolio/people-register.md"
    people.write_text(people.read_text().replace(
        "| Sara Example |", "| Dana Okoye | dana@kestrel.example | Dana | Kestrel Group | Commercial lead |  |  |\n"
        "| Tom Reid |  | Tom | Kestrel Group | Engineer |  |  |\n| Sara Example |", 1))
    v.run("init")
    for sub in ("minutes", "transcripts"):
        (v.root / "projects/FAL Falcon AI Programme" / sub).mkdir(parents=True, exist_ok=True)


def seed(v):
    """Six unrelated FAL actions, the commercials action as FAL-A-007, one raised after the reply, and an ABC look-alike."""
    mine = "Alan Carter"
    rows = ["Prepare the data platform architecture review", "Book the steering committee room for November",
            "Send the pilot results summary to the sponsor", "Confirm the GPU capacity with infrastructure",
            "Draft the change request for phase two", "Update the risk log after the workshop"]
    items = [action(i, project="FAL", description=t, owner=mine, raised="2026-10-01", due_date="2026-10-20",
                    source="projects/FAL Falcon AI Programme/minutes/2026-10-01 Sync.docx — Actions")
             for i, t in enumerate(rows, 1)]
    items.append(action(7, project="FAL", description="Reach out to Dana on back to back commercials", owner=mine,
                        raised="2026-10-06", due_date="2026-10-14", source=THREAD))
    items.append(action(8, project="FAL", description="Rebook the commercials discussion with Dana and Tom", owner=mine,
                        raised="2026-10-14", due_date="2026-10-24", source=THREAD))
    items.append(action(9, project="ABC", description="Reach out to Dana on back to back commercials", owner="Omar Ali",
                        raised="2026-10-06"))
    items.append(action(10, project="FAL", description="Agree the energy pricing model", owner=mine, raised="2026-07-20",
                        status="Closed", closed="2026-08-01",                   # closed over RECENT_DAYS (60) ago
                        source="projects/FAL Falcon AI Programme/minutes/2026-09-01 Sync.docx — Actions"))
    v.propose("seed", items)
    v.run("apply")
    return {r["description"]: r["id"] for r in v.rows("actions")}


class Case(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        add_fal(self.v)
        self.ids = seed(self.v)
        self.target = self.ids["Reach out to Dana on back to back commercials"]

    def run_(self, script, *args, ok=True):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], cwd=self.v.root,
                           env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
        if ok and r.returncode not in (0, 3):
            raise AssertionError(f"{script} {args}: {r.stdout}{r.stderr}")
        return r

    def sweep(self, *items):
        spec = self.v.root / "system/staging/drafts/sweep.json"
        spec.write_text(json.dumps({"window": {"start": "2026-10-13 08:00", "end": NOW}, "items": list(items)}))
        out = self.run_("sweep.py", "stage", str(spec)).stdout
        prop = sorted((self.v.root / "system/staging").glob("proposed-*-sweep*.json"))[-1]
        return out, prop, json.loads(prop.read_text())

    def new(self, text, source=REPLY, **v):
        return {"table": "actions", "match": "strong",
                "values": {"project": "FAL", "description": text, "owner": "Alan Carter", "source": source, **v}}

    def number(self, prop, ref):
        rows = json.loads(self.run_("review.py", "list", "--json").stdout)
        return next(r["n"] for r in rows if r["file"] == prop.name and r["ref"] == ref)

    def settings(self, **drafting):
        p = self.v.root / "system/config/settings.json"
        s = json.loads(p.read_text())
        s["drafting"] = {**(s.get("drafting") or {}), **drafting}
        p.write_text(json.dumps(s))


class TheTrigger(Case):
    def test_the_target_is_fal_a_007(self):
        self.assertEqual(self.target, "FAL-A-007")

    def test_the_skills_update_is_staged_as_an_update_not_a_new_action(self):
        _, prop, data = self.sweep({"op": "update", "table": "actions", "id": self.target, "source": REPLY,
                                    "set": {"latest_update": "13-10-2026: Dana asked to rebook for next week, with Tom",
                                            "due_date": "2026-10-23"}, "why": "“rebook for next week, with Tom”"})
        [it] = data["items"]
        self.assertEqual((it["op"], it["id"], it["changes"]),
                         ("update", self.target, {"latest_update": "13-10-2026: Dana asked to rebook for next week, with Tom",
                                                  "due_date": "2026-10-23"}))
        self.assertIsNone(review.individual_only(it))                       # E: date and latest update only, so routine
        self.run_("review.py", "list")
        self.assertIn("Approved 1.", self.run_("review.py", "bulk").stdout)
        self.run_("tracker.py", "apply")
        row = next(r for r in self.v.rows("actions") if r["id"] == self.target)
        self.assertEqual((row["due_date"], row["latest_update"][:10]), ("2026-10-23", "13-10-2026"))
        self.assertEqual(len(self.v.rows("actions")), 10)                    # never a new item

    def test_without_the_update_looks_like_marks_it_very_likely(self):
        out, _, data = self.sweep(self.new(REBOOK))
        ll = data["items"][0]["looks_like"]
        self.assertEqual((ll["id"], ll["strength"], ll["same"]), (self.target, "Very likely", True))
        for bit in ("Same thread", "Dana", "due this week"):
            self.assertIn(bit, ll["why"])
        self.assertNotIn("%", json.dumps(ll))
        self.assertIn("Looks like an existing item: 1", out)

    def test_an_item_raised_after_the_message_is_never_matched(self):
        _, _, data = self.sweep(self.new("Rebook the commercials discussion with Dana and Tom next week"))
        self.assertEqual(data["items"][0]["looks_like"]["id"], self.target)    # not FAL-A-008, raised the next day

    def test_an_unrelated_item_in_the_same_project_is_not_marked(self):
        _, _, data = self.sweep(self.new("Order the team lunch for the offsite", source=OTHER))
        self.assertNotIn("looks_like", data["items"][0])

    def test_a_progress_update_may_not_close_or_change_the_owner(self):
        out, _, _ = self.sweep(self.new("Order the team lunch for the offsite", source=OTHER),
                               {"op": "update", "table": "actions", "id": self.target, "source": REPLY, "set": {"status": "Closed"}},
                               {"op": "update", "table": "actions", "id": self.target, "source": REPLY, "set": {"owner": "Tom Reid"}})
        self.assertEqual(out.count("a message may change latest_update, due_date only"), 2)

    def test_spot_repeats_off_turns_off_the_signals_and_the_judgement(self):
        self.settings(repeat=False)
        item = self.new("Order the team lunch for the offsite", source=OTHER)
        item["repeat"] = {"id": self.ids["Book the steering committee room for November"], "judged": "same"}
        _, _, data = self.sweep(self.new(REBOOK), item)
        self.assertFalse(any("looks_like" in i for i in data["items"]))


class Expected(Case):
    def expected(self, *args):
        return json.loads(self.run_("sweep.py", "expected", "FAL", *args).stdout)

    def test_the_same_json_as_minutes_expected(self):
        e = self.expected()
        m = json.loads(self.run_("minutes.py", "expected", "FAL").stdout)
        self.assertEqual(set(e), set(m))
        self.assertEqual([a["id"] for a in e["actions"]], [a["id"] for a in m["actions"]])

    def test_ranked_by_the_message_and_never_raised_after_it(self):
        e = self.expected("--date", "2026-10-13", "--subject", "RE: Discuss FalconAI Commercials", "--text", REBOOK)
        first = e["actions"][0]
        self.assertEqual((first["id"], first["match"]["strength"]), (self.target, "Very likely"))
        self.assertNotIn("FAL-A-008", [a["id"] for a in e["actions"]])
        self.assertTrue(all("ABC" not in a["id"] for a in e["actions"]))
        self.assertIsNone(e["actions"][-1]["match"]["strength"])


class Signals(unittest.TestCase):
    """Each signal on its own, in plain code."""
    ROW = {"id": "FAL-A-007", "project": "FAL", "text": "Reach out to Dana on back to back commercials", "owner": "Alan Carter",
           "workstream": None, "state": "open", "raised": "2026-10-06", "due": "2026-10-14", "closed": None, "source": THREAD}

    def ctx(self, text="Plan the next workshop", source=OTHER, day="2026-10-13"):
        item = {"op": "new", "table": "actions", "values": {"project": "FAL", "description": text, "source": source}}
        return {**extraction.message_context(item, REGISTER), "day": day}

    def score(self, text, source=OTHER, row=None, owner="Tom Reid", rare=frozenset()):
        v = {"project": "FAL", "description": text, "owner": owner, "source": source}
        return extraction.match_score(v, "actions", row or self.ROW, self.ctx(text, source), set(rare))

    def test_an_item_id_in_the_text_is_certain(self):
        s, why = self.score("Chase FAL-A-007 with procurement")
        self.assertEqual((s, why), (1.0, "Names FAL-A-007"))
        self.assertEqual(self.score("Chase FAL-A-017 with procurement")[0] < 0.5, True)

    def test_the_same_thread_is_strong_and_normalised(self):
        self.assertEqual(extraction.thread_of(REPLY), "discuss falconai commercials")
        self.assertEqual(extraction.thread_of(REPLY.replace("RE: [EXT]", "Fw: re:")), "discuss falconai commercials")
        self.assertEqual(extraction.thread_of("Teams · Chat: x · Subject: Discuss FalconAI Commercials"), "")
        with_thread, why = self.score("Plan the next workshop", REPLY)
        without, _ = self.score("Plan the next workshop", OTHER)
        self.assertAlmostEqual(with_thread - without, extraction.W_THREAD)
        self.assertIn("Same thread", why)

    def test_a_person_in_both_texts_counts(self):
        self.assertEqual(extraction.people_in("Call Dana about it", self.ROW["text"], REGISTER), ["Dana"])
        self.assertEqual(extraction.people_in("Call Tom about it", self.ROW["text"], REGISTER), [])
        a, why = self.score("Call Dana about the workshop")
        b, _ = self.score("Call Omar about the workshop")
        self.assertGreaterEqual(a - b, extraction.W_PERSON)
        self.assertIn("Dana", why)

    def test_a_less_common_word_counts_for_more(self):
        rows = [self.ROW, {**self.ROW, "id": "FAL-A-001", "text": "Review the commercials deck"}]
        self.assertEqual(extraction.rare_words(rows) & {"commercial", "deck", "reach"}, {"deck", "reach"})
        rare, _ = self.score("Reach the sponsor", rare={"reach"})
        common, _ = self.score("Reach the sponsor", rare=set())
        self.assertAlmostEqual(rare - common, extraction.W_RARE)

    def test_the_timeframe(self):
        r = self.ROW
        self.assertEqual(extraction.time_signal(r, "2026-10-13"), (extraction.W_WINDOW, "due this week"))
        self.assertEqual(extraction.time_signal(r, "2026-10-30"), (extraction.W_WINDOW, "overdue"))       # open: still current
        self.assertEqual(extraction.time_signal({**r, "due": "2027-01-30"}, "2026-10-13")[0], extraction.W_LONG)
        closed = {**r, "state": "closed", "closed": "2026-10-07"}
        self.assertEqual(extraction.time_signal(closed, "2026-10-30")[0], 0.0)                          # past its window
        self.assertTrue(extraction.raised_after(r, "2026-10-05"))
        self.assertFalse(extraction.raised_after(r, "2026-10-06"))

    def test_another_projects_item_is_marked_only_when_it_is_a_close_match(self):   # #333
        row = {**self.ROW, "id": "ABC-A-009", "project": "ABC", "owner": "Omar Ali", "text": "Reach out to Dana on back to back commercials"}
        def mark(text):
            item = {"op": "new", "table": "actions", "values": {"project": "FAL", "description": text, "owner": "Omar Ali", "source": OTHER}}
            real = extraction.candidate_rows
            extraction.candidate_rows = lambda *a, **k: [row]
            try:
                return extraction.best_repeat(None, item, REGISTER)
            finally:
                extraction.candidate_rows = real
        self.assertIsNone(mark("Reach out to the vendor about licences"))                    # shares words, not the same action
        self.assertEqual((mark("Reach out to Dana on back to back commercials") or {}).get("id"), "ABC-A-009")

    def test_the_two_thresholds(self):
        self.assertEqual([extraction.strength_of(x) for x in (1.0, 0.75, 0.74, 0.5, 0.49, 0.0)],
                         ["Very likely", "Very likely", "Possible", "Possible", None, None])


class Judged(Case):
    def test_judged_same_stands_on_its_own(self):
        other = self.ids["Book the steering committee room for November"]
        item = self.new("Order the team lunch for the offsite", source=OTHER)
        item["repeat"] = {"id": other, "judged": "same"}
        _, _, data = self.sweep(item)
        ll = data["items"][0]["looks_like"]
        self.assertEqual((ll["id"], ll["strength"], ll["why"]), (other, "Very likely", "Judged the same at extraction"))

    def test_judged_same_on_another_project_a_closed_or_a_missing_item_is_ignored_with_a_note(self):
        items, abc = [], next(r["id"] for r in self.v.rows("actions") if r["project"] == "ABC")
        for bad, what in ((self.ids["Agree the energy pricing model"], "lunch"), (abc, "dinner"), ("FAL-A-099", "coffee")):
            it = self.new(f"Order the team {what} for the offsite", source=OTHER)
            it["repeat"] = {"id": bad, "judged": "same"}
            items.append(it)
        out, _, data = self.sweep(*items)
        self.assertFalse(any("looks_like" in i for i in data["items"]))
        self.assertEqual(out.count("was ignored"), 3)


class Retarget(Case):
    def staged(self, *items):
        _, prop, _ = self.sweep(*items)
        return prop

    def item(self, prop, ref=1):
        return next(i for i in json.loads(prop.read_text())["items"] if i["n"] == ref)

    def test_retarget_an_unmarked_item_then_undo(self):
        other = self.ids["Book the steering committee room for November"]
        prop = self.staged(self.new("Order the team lunch for the offsite", source=OTHER, due_date="2026-10-30"))
        n = self.number(prop, 1)
        cands = json.loads(self.run_("review.py", "candidates", str(n), "--json").stdout)
        self.assertNotIn("FAL-A-008", [c["id"] for c in cands])                    # raised after the message
        self.run_("review.py", "retarget", str(n), other)
        it = self.item(prop)
        self.assertEqual((it["op"], it["id"], it["changes"], it["decision"]), ("update", other, {"due_date": "2026-10-30"}, "pending"))
        self.assertEqual((it["retargeted"]["to"], it["retargeted"]["marked"]), (other, None))
        self.assertIsNone(review.individual_only(it))
        q = json.loads(self.run_("quality.py", "--json").stdout)["repeats"]
        self.assertEqual((q["retargeted"], q["unmarked"]["n"], q["missed"]), (1, 1, [other]))
        self.run_("review.py", "unmerge", str(self.number(prop, 1)))
        back = self.item(prop)
        self.assertEqual((back["op"], back["values"]["description"], back["decision"]), ("new", "Order the team lunch for the offsite",
                                                                                       "pending"))
        self.assertNotIn("retargeted", back)
        self.assertEqual(json.loads(self.run_("quality.py", "--json").stdout)["repeats"]["total"], 0)

    def test_retarget_onto_the_marked_item_is_counted_on_the_mark(self):
        prop = self.staged(self.new(REBOOK, latest_update="13-10-2026: Dana asked to rebook"))
        self.run_("review.py", "retarget", str(self.number(prop, 1)), self.target)
        it = self.item(prop)
        self.assertEqual(it["retargeted"]["marked"], self.target)
        self.assertEqual(it["changes"], {"latest_update": "13-10-2026: Dana asked to rebook"})
        q = json.loads(self.run_("quality.py", "--json").stdout)["repeats"]
        self.assertEqual((q["total"], q["unmarked"]["n"], q["missed"]), (1, 0, []))

    def test_nothing_new_rejects_it_as_the_duplicate_and_undo_puts_it_back(self):
        prop = self.staged(self.new("Order the team lunch for the offsite", source=OTHER))
        self.run_("review.py", "retarget", str(self.number(prop, 1)), self.target)
        it = self.item(prop)
        self.assertEqual((it["decision"], it["duplicate_of"], it["reject_reason"]), ("rejected", self.target, "Duplicate"))
        self.run_("review.py", "unmerge", f"{prop.name}#1")                    # rejected: no review number, so by file and item
        self.assertEqual(self.item(prop)["decision"], "pending")

    def test_refusals(self):
        prop = self.staged(self.new("Order the team lunch for the offsite", source=OTHER, due_date="2026-10-30"))
        n = str(self.number(prop, 1))
        abc = next(r["id"] for r in self.v.rows("actions") if r["project"] == "ABC")
        for target, said in ((self.ids["Agree the energy pricing model"], "only an open item"), (abc, "another project"),
                             ("FAL-005", "isn't an action"), ("nonsense", "isn't an item ID")):
            r = self.run_("review.py", "retarget", n, target, ok=False)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn(said, r.stdout)
        self.assertEqual(self.item(prop)["op"], "new")
        self.assertEqual(self.run_("review.py", "unmerge", n, ok=False).returncode, 1)

    def test_merge_is_undoable_too(self):
        prop = self.staged(self.new(REBOOK, due_date="2026-10-23"))
        self.run_("review.py", "merge", str(self.number(prop, 1)))
        self.assertEqual(self.item(prop)["op"], "update")
        q = json.loads(self.run_("quality.py", "--json").stdout)["repeats"]
        self.assertEqual((q["merged"], q["total"]), (1, 1))
        self.run_("review.py", "unmerge", str(self.number(prop, 1)))
        self.assertEqual(self.item(prop)["looks_like"]["id"], self.target)


class Routine(unittest.TestCase):
    """E: the exact boundary of the bulk rule for updates."""
    def upd(self, table, **changes):
        return {"op": "update", "table": table, "id": "ABC-A-001", "changes": changes}

    def test_date_and_latest_update_only_are_routine(self):
        for it in (self.upd("actions", due_date="2026-10-23"), self.upd("actions", latest_update="13-10-2026: x"),
                   self.upd("actions", due_date="2026-10-23", latest_update="13-10-2026: x"), self.upd("raid", due_date="2026-10-23"),
                   self.upd("decisions", needed_by="2026-10-23"), self.upd("actions")):
            self.assertIsNone(review.individual_only(it), it)

    def test_anything_else_is_approved_on_its_own(self):
        cases = {("actions", "status", "Delayed"): "status change", ("actions", "owner", "Tom Reid"): "owner change",
                 ("actions", "description", "x"): "title change", ("actions", "project", "DEF"): "project change",
                 ("actions", "priority", "High"): "change to priority", ("raid", "response_action", "x"): "response change",
                 ("raid", "latest_update", "x"): "change to latest update", ("decisions", "reasoning", "x"): "change to reasoning",
                 ("actions", "status", "Closed"): "closing update", ("decisions", "status", "Made"): "decision made"}
        for (table, field, value), why in cases.items():
            self.assertEqual(review.individual_only(self.upd(table, due_date="2026-10-23", **{field: value})
                                                    if table != "decisions" else self.upd(table, **{field: value})), why)

    def test_the_rule_never_widens(self):
        self.assertEqual(review.individual_only({"op": "new", "table": "decisions", "values": {}}), "new decision")
        self.assertEqual(review.individual_only({"op": "new", "table": "raid", "values": {"type": "Risk"}}), "new risk")
        self.assertEqual(review.individual_only({"op": "update", "table": "projects", "id": "ABC", "changes": {"health": "Red"}}),
                         "health change")
        self.assertEqual(review.individual_only({**self.upd("actions", latest_update="x"), "drafted": "update"}), "drafted update")
        self.assertEqual(review.individual_only({"op": "update", "table": "milestones", "id": "ABC-M-001",
                                                 "changes": {"baseline_date": "2026-12-01"}}), "rebaseline")


class Server(unittest.TestCase):
    def test_the_routes_run_review_py(self):
        import live_server
        calls = []

        def fake(script, *args):
            calls.append((script, *args))
            if args[:1] == ("list",):
                return 0, json.dumps([{"n": 4, "file": "p.json", "ref": 2}])
            return 0, '[{"id": "FAL-A-007"}]' if args[0] == "candidates" else "4: now an update to FAL-A-007."

        class H:
            def send(self, code, body):
                self.got = (code, body)

        old, live_server.run = live_server.run, fake
        had, real_fp = hasattr(live_server, "current_fp"), getattr(live_server, "current_fp", None)
        live_server.current_fp = lambda file, ref: "a" * 12          # 2.6.4 (#345): the check itself is test_expect_routes_345
        try:
            h = H()
            live_server.REVIEW_WORK_ROUTES["/api/review/retarget"](h, {"file": "p.json", "ref": 2, "id": "FAL-A-007", "expect": "a" * 12})
            self.assertTrue(h.got[1]["ok"])
            live_server.REVIEW_WORK_ROUTES["/api/review/retarget"](h, {"file": "../p.json", "ref": 2, "undo": True})
            live_server.REVIEW_WORK_ROUTES["/api/review/candidates"](h, {"file": "p.json", "ref": 2})
            self.assertEqual(h.got[1]["items"], [{"id": "FAL-A-007"}])
            live_server.REVIEW_WORK_ROUTES["/api/review/retarget"](h, {"file": "gone.json", "ref": 2, "id": "FAL-A-007"})
            self.assertFalse(h.got[1]["ok"])
        finally:
            live_server.run = old
            if had:
                live_server.current_fp = real_fp
            else:
                del live_server.current_fp
        self.assertIn(("review.py", "retarget", "4", "FAL-A-007"), calls)
        self.assertIn(("review.py", "unmerge", "p.json#2"), calls)
        self.assertIn(("review.py", "candidates", "4", "--json"), calls)


# ── BL-297 D: Review's picker, "Update an existing item instead", against the real live server ──────────────────────────
from live_browser import LiveBrowserCase  # noqa: E402

PICKED = '#pkPropTop [data-rvrt]'
NEW_ROW = 'REV.find(r=>!r.done&&r.kind==="actions"&&r.rec&&String(r.rec.t).startsWith("Rebook"))'


class PickerBrowserTests(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        add_fal(v)
        cls.ids = seed(v)
        cls.target = cls.ids["Reach out to Dana on back to back commercials"]
        cls.prop = v.propose("rebook", [
            {**action(1, project="FAL", description=REBOOK, raised="2026-10-13", due_date="2026-10-23",
                      latest_update="13-10-2026: Dana asked to rebook for next week, with Tom", source=REPLY),
             "decision": "pending"},
            {"n": 2, "op": "update", "table": "actions", "id": cls.ids["Draft the change request for phase two"],
             "changes": {"due_date": "2026-10-30"}, "why": "Re-dated", "source": OTHER, "match": "strong", "flags": [],
             "decision": "pending"}])
        v.run(script="build_dashboard.py")

    @classmethod
    def server_env(cls):
        return {"CREAITE_NOW": NOW}

    def setUp(self):
        super().setUp()
        self.b.eval("S.autoApply=false")

    def item(self, ref=1):
        return next(i for i in json.loads(self.prop.read_text())["items"] if i["n"] == ref)

    def open_new(self):
        self.b.eval(f'go("intake-review", {NEW_ROW}.n)')                                   # #232 C2: the Intake page
        self.b.wait(f'!!{NEW_ROW}')
        self.b.eval(f'openProposal({NEW_ROW}.n)')
        self.b.wait(f'!!document.querySelector({json.dumps(PICKED)})')

    def test_the_intake_list_itself_is_unchanged(self):
        self.b.eval('go("intake-review")')
        self.b.wait('!!document.querySelector("#v-intake-review tr.irprop")')
        self.assertFalse(self.b.eval('!!document.querySelector("#v-intake-review [data-rvrt]")'))   # only the peek has it (the row menu went with the old page)

    def test_pick_an_item_then_undo(self):
        b, sel = self.b, json.dumps(PICKED)
        before = self.v.snapshot()
        self.open_new()
        btn = b.eval(f'(e=>[e.textContent.trim(),e.getAttribute("aria-haspopup"),e.getAttribute("aria-expanded")])(document.querySelector({sel}))')
        self.assertEqual(btn, ["Update an existing item instead", "listbox", "false"])
        b.click(PICKED)
        b.wait('!!document.querySelector(".pkpop [role=listbox] [role=option]")')
        self.assertEqual(b.eval('document.querySelector(".pkpop [role=listbox]").getAttribute("aria-label")'), "Update which action instead")
        opts = b.eval('[...document.querySelectorAll(".pkpop [role=option]")].map(o=>o.textContent)')
        self.assertTrue(opts[0].startswith(f"{self.target} · Reach out to Dana"), opts)   # the best match first
        self.assertIn("Very likely", opts[0])
        self.assertFalse(any("FAL-A-008" in o for o in opts))                          # raised after the message
        self.assertFalse(any("%" in o or "VIP" in o for o in opts))                      # words, never a percentage; BL-288
        self.assertEqual(b.eval(f'document.querySelector({sel}).getAttribute("aria-expanded")'), "true")
        self.assertTrue(b.eval('document.activeElement.matches(".pkpop [role=option]")'))
        b.key("ArrowDown")
        self.assertTrue(b.eval('document.activeElement===document.querySelectorAll(".pkpop [role=option]")[1]'))
        b.key("Escape")                                                                   # Esc closes, focus back to the button
        b.wait('!document.querySelector(".pkpop")')
        self.assertTrue(b.eval(f'document.activeElement===document.querySelector({sel})'))
        self.assertEqual(b.eval(f'document.querySelector({sel}).getAttribute("aria-expanded")'), "false")
        self.assertEqual(self.item()["op"], "new")                                       # nothing changed yet
        b.key("Enter")                                                                    # open it again from the keyboard
        b.wait('!!document.querySelector(".pkpop [role=option]")')
        b.key("Enter")                                                                    # and choose the first
        b.wait(f'/Now an update to {self.target}/.test(document.getElementById("snackT").textContent)')
        it = self.item()
        self.assertEqual((it["op"], it["id"], it["decision"]), ("update", self.target, "pending"))
        self.assertEqual(it["retargeted"]["to"], self.target)
        self.assertEqual(self.v.snapshot()[0], before[0])                                 # the tracker is untouched
        b.wait(f'REV.some(r=>!r.done&&r.kind==="update"&&r.rec&&r.rec.target==={json.dumps(self.target)})')
        self.assertFalse(b.eval('document.getElementById("panel").classList.contains("on")'))
        b.eval('UNDO()')
        b.wait('/Back to a new item/.test(document.getElementById("snackT").textContent)')
        it = self.item()
        self.assertEqual((it["op"], it["values"]["description"], it["decision"]), ("new", REBOOK, "pending"))
        b.wait(f'!!{NEW_ROW}')

    def test_the_peek_offers_it_on_a_new_item_only(self):
        """#232 C2: the old row's right-click menu entry went with the page; the peek's button is the way in."""
        b = self.b
        b.eval('go("intake-review")')
        b.wait('!!document.querySelector("#v-intake-review tr.irprop")')
        upd = b.eval('REV.find(r=>!r.done&&r.kind==="update").n')
        b.eval(f"openProposal({upd})")
        b.wait("CUR&&CUR.mode==='proposal'&&document.getElementById('panel').classList.contains('on')")
        self.assertFalse(b.eval(f"!!document.querySelector({json.dumps(PICKED)})"))        # an update names its item already
        b.eval("closePanel()")
        self.open_new()
        b.click(PICKED)
        b.wait('!!document.querySelector(".pkpop [role=listbox] [role=option]")')
        self.assertTrue(b.eval('document.activeElement.matches(".pkpop [role=option]")'))
        b.key("Escape")
        b.wait('!document.querySelector(".pkpop")')
        self.assertEqual(self.item()["op"], "new")

    def test_the_picker_still_opens_when_the_peek_is_drawn_again_while_the_server_answers(self):
        """The candidates come from the server; if the peek is redrawn meanwhile (a refresh, slow CI), the picker opens on the new button."""
        b = self.b
        self.open_new()
        b.eval("""{ const a=api; api=function(u,body){ const p=a.apply(this,arguments); return u==='/api/review/candidates'?p.then(r=>{ drawPanel(); return r; }):p; }; }""")
        b.click(PICKED)
        b.wait('!!document.querySelector(".pkpop [role=listbox] [role=option]")')
        b.key("Escape")


if __name__ == "__main__":
    unittest.main()

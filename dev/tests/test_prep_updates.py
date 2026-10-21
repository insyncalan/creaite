"""Tests for prep updates (BL-65): cx-minutes proposes updates to the open items a meeting discusses.

Run: python3 dev/tests/test_prep_updates.py
Each test builds a throwaway vault (test_tracker.Vault) with fictional items and runs the real scripts there.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard import CHROME  # noqa: E402
from test_tracker import ABC, Vault, action  # noqa: E402

DAY, TITLE = "2026-10-07", "[ABC] Steering committee"
SRC = f"{ABC}/minutes/2026-10-01 Steering.docx — Actions"


def raid(n, type_="Risk", **v):
    values = {"project": "ABC", "type": type_, "description": "Data access delayed, so UAT may slip", "impact": "High",
              "likelihood": "High", "raised": "2026-10-01", "source": SRC, **v}
    return {"n": n, "op": "new", "table": "raid", "values": values, "match": "strong", "flags": [], "decision": "approved"}


class PrepBase(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", [
            action(1, description="Send revised SOW to client", owner="Omar Ali", due_date="2026-10-09"),
            action(2, description="Book the UAT environment", owner="Alan Carter"),
            raid(3),
            raid(4, "Issue", description="Test licences not ordered", response_action="Ordering them this week"),
            action(5, description="Chase legal", project="ABC", status="Closed", closed="2026-10-02"),
        ])
        self.v.run("apply")
        (self.v.root / "inbox/steering.vtt").write_text("WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<v Omar Ali>Hello</v>")

    def tearDown(self):
        self.v.cleanup()

    def spec(self, items, **extra):
        draft = self.v.root / "system/staging/drafts/steering.docx"   # BL-260: a transcript is staged with its draft
        if not draft.exists():
            shutil.copy(self.v.root / "system/templates/minutes-template.docx", draft)
        return {"title": TITLE, "date": DAY, "projects": ["ABC"], "transcript": "inbox/steering.vtt",
                "draft": "system/staging/drafts/steering.docx", "items": items, **extra}

    def stage(self, items, ok=True, **extra):
        f = self.v.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps(self.spec(items, **extra)))
        r = self.v.run("stage", str(f), script="minutes.py", ok=ok)
        return r

    def staged(self):
        files = sorted((self.v.root / "system/staging").glob("proposed-2*.json"))
        return json.loads(files[-1].read_text()) if files else None

    def row(self, table, item_id):
        return next(r for r in self.v.rows(table) if r["id"] == item_id)


class StageUpdateTests(PrepBase):
    def update(self, item_id, set_, table="actions", **extra):
        return {"op": "update", "table": table, "id": item_id, "set": set_, "why": "Said in the meeting",
                "section": "Actions", **extra}

    def test_an_update_is_staged_with_based_on_and_its_source(self):
        out = self.stage([self.update("ABC-A-001", {"due_date": "2026-10-16", "latest_update": "07-10-2026: sent a draft"})]).stdout
        data = self.staged()
        item = data["items"][0]
        self.assertEqual((item["op"], item["table"], item["id"], item["decision"]), ("update", "actions", "ABC-A-001", "pending"))
        self.assertEqual(item["changes"], {"due_date": "2026-10-16", "latest_update": "07-10-2026: sent a draft"})
        self.assertEqual(item["based_on"], self.row("actions", "ABC-A-001")["updated_at"])        # exact, for conflicts
        self.assertEqual(item["why"], "Said in the meeting")
        self.assertEqual(item["source"], f"{ABC}/minutes/2026-10-07 Steering committee.docx — Actions")   # BL-260: staged with its draft
        self.assertIn("1 · ABC · Update · ABC-A-001: due_date → 16-10-2026; latest_update → 07-10-2026: sent a draft", out)
        self.assertNotIn("invalid", item["flags"])                                               # it validates

    def test_a_given_source_is_kept(self):
        self.stage([self.update("ABC-A-001", {"status": "Delayed"}, source="my own source — Notes")])
        self.assertEqual(self.staged()["items"][0]["source"], "my own source — Notes")

    def test_a_change_after_staging_is_held_as_a_conflict_at_apply(self):
        self.stage([self.update("ABC-A-001", {"status": "Closed"})])
        proposal = next((self.v.root / "system/staging").glob("proposed-2*.json"))
        data = json.loads(proposal.read_text())
        data["items"][0]["decision"] = "approved"
        data["meeting"]["minutes_decision"] = "approved"
        proposal.write_text(json.dumps(data))
        self.v.propose("later", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001",
                                  "changes": {"due_date": "2026-11-01"}, "decision": "approved", "match": "strong", "flags": []}])
        self.v.run("apply", str(self.v.root / "system/staging/proposed-later.json"))        # someone else changes it first
        out = self.v.run("apply", str(proposal)).stdout
        self.assertIn("held 1", out)
        self.assertEqual(self.row("actions", "ABC-A-001")["status"], "Open")                  # nothing was overwritten
        self.assertIn("conflict", json.loads(proposal.read_text())["items"][0]["flags"])

    def test_an_approved_update_applies(self):
        self.stage([self.update("ABC-A-001", {"status": "Closed"}),
                    self.update("ABC-003", {"response_action": "Escalated to the CIO", "due_date": "2026-10-20"}, table="raid")])
        proposal = next((self.v.root / "system/staging").glob("proposed-2*.json"))
        data = json.loads(proposal.read_text())
        for i in data["items"]:
            i["decision"] = "approved"
        data["meeting"]["minutes_decision"] = "approved"
        proposal.write_text(json.dumps(data))
        self.v.run("apply", str(proposal))
        a, r = self.row("actions", "ABC-A-001"), self.row("raid", "ABC-003")
        self.assertEqual((a["status"], bool(a["closed"])), ("Closed", True))
        self.assertEqual((r["response_action"], r["due_date"]), ("Escalated to the CIO", "2026-10-20"))

    def test_the_fields_an_update_may_change(self):
        for table, item_id, field in (("actions", "ABC-A-001", "owner"), ("actions", "ABC-A-001", "description"),
                                      ("actions", "ABC-A-001", "project"), ("actions", "ABC-A-001", "response_action"),
                                      ("raid", "ABC-003", "owner"), ("raid", "ABC-003", "latest_update"),
                                      ("raid", "ABC-003", "impact")):
            out = self.stage([self.update(item_id, {field: "x"}, table=table)]).stdout
            self.assertIn(f"rejected update: {item_id}: {field} can't be changed from minutes", out, (table, field))
            self.assertEqual(self.staged()["items"], [], (table, field))                         # not even the allowed part
            for f in (self.v.root / "system/staging").glob("proposed-2*.json"):
                f.unlink()
        self.stage([self.update("ABC-A-001", {"status": "Delayed", "due_date": "2026-11-01", "latest_update": "x"})])
        self.assertEqual(len(self.staged()["items"]), 1)

    def test_closed_wrong_project_and_missing_items_are_rejected_by_name(self):
        out = self.stage([self.update("ABC-A-005", {"status": "Open"}),
                          self.update("ABC-A-099", {"status": "Closed"}),
                          self.update("ABC-M-001", {"status": "Done"}, table="milestones"),
                          self.update("ABC-A-001", {"latest_update": "x"})]).stdout
        self.assertIn("rejected update: ABC-A-005 is Closed; only open items are updated", out)
        self.assertIn("rejected update: ABC-A-099 isn't in the tracker", out)
        self.assertIn("rejected update: ABC-M-001: updates change actions, RAID items, pending decisions and open promises only, not milestones", out)
        self.assertEqual([i["id"] for i in self.staged()["items"]], ["ABC-A-001"])
        # another project's item
        self.v.propose("def", [action(1, project="ABC", description="Other")])
        con_sql = __import__("sqlite3").connect(self.v.root / "system/tracker.db")
        con_sql.execute("INSERT INTO projects (code, name, updated_at) VALUES ('DEF', 'Digital', '2026-10-01 00:00:00')")
        con_sql.execute("UPDATE actions SET project = 'DEF', id = 'DEF-A-001' WHERE id = 'ABC-A-002'")
        con_sql.commit()
        con_sql.close()
        for f in (self.v.root / "system/staging").glob("proposed-2*.json"):
            f.unlink()
        out = self.stage([self.update("DEF-A-001", {"status": "Closed"})]).stdout
        self.assertIn("rejected update: DEF-A-001 belongs to DEF, which isn't one of this meeting's projects", out)

    def test_unchanged_updates_are_only_a_mention(self):
        out = self.stage([self.update("ABC-A-001", {"due_date": "2026-10-09", "status": "Open"})]).stdout
        self.assertIn("no change to ABC-A-001", out)
        self.assertEqual(self.staged()["items"], [])
        mentions = [json.loads(x) for x in (self.v.root / "system/staging/mentions.jsonl").read_text().splitlines()]
        self.assertEqual([m["id"] for m in mentions], ["ABC-A-001"])

    def test_two_updates_to_one_item_are_merged(self):
        self.stage([self.update("ABC-A-001", {"status": "Delayed"}), self.update("ABC-A-001", {"due_date": "2026-11-01"})])
        items = self.staged()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["changes"], {"due_date": "2026-11-01", "status": "Delayed"})


class DedupeTests(PrepBase):
    def new_action(self, **v):
        return {"table": "actions", "section": "Actions",
                "values": {"project": "ABC", "description": "Send revised SOW to client", "owner": "Omar Ali", **v}}

    def mentions(self):
        p = self.v.root / "system/staging/mentions.jsonl"
        return [json.loads(x)["id"] for x in p.read_text().splitlines()] if p.exists() else []

    def test_a_duplicate_with_a_new_date_becomes_an_update(self):
        out = self.stage([self.new_action(due_date="2026-10-16")]).stdout
        items = self.staged()["items"]
        self.assertEqual([(i["op"], i["id"], i["changes"]) for i in items], [("update", "ABC-A-001", {"due_date": "2026-10-16"})])
        self.assertIn("already in the tracker as ABC-A-001, so staged as an update to it (due_date)", out)
        self.assertEqual(items[0]["why"], f"Raised again in {TITLE}")
        self.assertEqual(self.mentions(), ["ABC-A-001"])                                         # still a mention

    def test_a_duplicate_with_nothing_new_is_only_a_mention(self):
        out = self.stage([self.new_action(due_date="2026-10-09")]).stdout
        self.assertEqual(self.staged()["items"], [])
        self.assertIn("skipped (already in the tracker as ABC-A-001)", out)
        self.assertEqual(self.mentions(), ["ABC-A-001"])

    def test_a_repeated_risk_gets_its_response_as_an_update(self):
        item = {"table": "raid", "section": "Risks", "values": {"project": "ABC", "type": "Risk",
                "description": "Data access delayed, so UAT may slip", "response_action": "Escalate to the CIO"}}
        self.stage([item])
        items = self.staged()["items"]
        self.assertEqual([(i["table"], i["id"], i["changes"]) for i in items], [("raid", "ABC-003", {"response_action": "Escalate to the CIO"})])

    def test_a_genuinely_new_item_is_still_new_and_a_decision_is_never_an_update(self):
        self.stage([self.new_action(description="Brand new action"),
                    {"table": "decisions", "values": {"project": "ABC", "decision": "Go-live stays", "made_by": "Jane"}}])
        self.assertEqual([i["op"] for i in self.staged()["items"]], ["new", "new"])

    def test_an_explicit_update_and_a_duplicate_of_the_same_item_make_one_update(self):
        self.stage([{"op": "update", "table": "actions", "id": "ABC-A-001", "set": {"status": "Delayed"}, "why": "slipping"},
                    self.new_action(due_date="2026-10-16")])
        items = self.staged()["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["changes"], {"due_date": "2026-10-16", "status": "Delayed"})


class ExpectedTests(PrepBase):
    def expected(self, *args):
        import os
        import subprocess
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/minutes.py"), "expected", *args], cwd=self.v.root,
                           capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": "2026-10-07 10:00"})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_lists_the_open_items_of_the_project(self):
        e = self.expected("ABC", "--title", TITLE)
        self.assertEqual([a["id"] for a in e["actions"]], ["ABC-A-001", "ABC-A-002"])                 # open; the closed one is left out
        self.assertEqual(e["actions"][0]["due_date"], "2026-10-09")                                   # soonest first, undated last
        self.assertEqual({a["description"] for a in e["actions"]}, {"Send revised SOW to client", "Book the UAT environment"})
        self.assertEqual([r["id"] for r in e["risks_and_issues_without_response"]], ["ABC-003"])      # the issue has a response
        self.assertEqual([r["id"] for r in e["other_open_raid"]], ["ABC-004"])
        self.assertEqual((e["project"], e["name"], e["date"]), ("ABC", "Example Programme", "2026-10-07"))
        self.assertIn("updated_at", e["actions"][0])                                                  # what stage will use for based_on

    def test_other_projects_and_closed_items_are_not_expected(self):
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(self.v.root / "system/tracker.db")) as con:
            con.execute("INSERT INTO projects (code, name, updated_at) VALUES ('DEF', 'Digital', '2026-10-01 00:00:00')")
            con.execute("UPDATE actions SET project = 'DEF', id = 'DEF-A-001' WHERE id = 'ABC-A-002'")
            con.execute("UPDATE raid SET status = 'Closed' WHERE id = 'ABC-003'")
            con.commit()
        e = self.expected("ABC", "--title", TITLE)
        self.assertEqual([a["id"] for a in e["actions"]], ["ABC-A-001"])
        self.assertEqual(e["risks_and_issues_without_response"], [])
        self.assertEqual([a["id"] for a in self.expected("DEF")["actions"]], ["DEF-A-001"])

    def test_the_series_and_when_it_last_met_come_from_the_brief_logic(self):
        for rel in (f"{ABC}/minutes/2026-09-30 Steering committee.docx", f"{ABC}/transcripts/2026-09-23 Steering committee.vtt",
                    f"{ABC}/minutes/2026-10-07 Steering committee.docx", f"{ABC}/minutes/2026-09-29 Weekly sync.docx"):
            (self.v.root / rel).write_bytes(b"x")
        e = self.expected("ABC", "--title", "[ABC] Steering committee 12")
        self.assertEqual((e["series"], e["last_meeting"], e["since"]), ("steering committee", "2026-09-30", "2026-09-30"))
        self.assertEqual(e["series_project"], {"p": "ABC", "how": "matched"})
        e = self.expected("ABC", "--title", "Weekly sync")
        self.assertEqual((e["last_meeting"], e["series_project"]["how"]), ("2026-09-29", "unsure"))
        e = self.expected("ABC", "--title", "Never met before")
        self.assertEqual((e["last_meeting"], e["since"]), (None, "2026-09-30"))                       # a week back
        # Alan's remembered choice for the series wins, as in the brief
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["prep"] = {"series": {"steering committee": "_portfolio"}}
        cfg.write_text(json.dumps(data))
        self.assertEqual(self.expected("ABC", "--title", "[ABC] Steering committee")["series_project"],
                         {"p": "_portfolio", "how": "remembered"})

    def test_it_is_read_only_and_refuses_an_unknown_project(self):
        import subprocess
        before = self.v.snapshot()
        self.expected("ABC", "--title", TITLE)
        self.assertEqual(self.v.snapshot(), before)
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts/minutes.py"), "expected", "ZZZ"], cwd=self.v.root,
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("ZZZ isn't a project", r.stderr)


SCRIPT = r"""
<script>
(async()=>{
  const FILES=JSON.parse(document.getElementById("seed").textContent), wait=ms=>new Promise(r=>setTimeout(r,ms)), out={errors:[]};
  VW={ async read(p){ if(!(p in FILES)) throw new Error("not found: "+p); return FILES[p]; }, async write(p,t){ FILES[p]=t; },
       async remove(p){ delete FILES[p]; }, async exists(p){ return p in FILES; }, async append(p,t){ FILES[p]=(FILES[p]||"")+t; } };
  VSTATE="ok"; needVault=async()=>true;   /* the page's own vault check can finish late and reset the fake vault (slow CI) */ S.autoApply=false;
  const rowsNow=()=>[...document.querySelectorAll("#v-intake-review tr.irprop")].map(tr=>[tr.className.includes("mchild")?"child":"row",tr.querySelector("td.title").textContent.replace(/\s+/g," ").trim()]);
  try{
    const m0=REV.find(r=>r.kind==="draft"&&r.ref==="meeting"); go("intake-review",m0.n); await wait(200); out.layout=rowsNow();   /* #232 C2: the Intake page, the minutes' meeting open */
    const ups=REV.filter(r=>r.kind==="update");
    out.updates=ups.map(r=>({t:r.rec.t,why:r.rec.why,src:r.src,indiv:r.indiv,whyCol:r.why,label:kindLabel(r),detail:revDetail(r).replace(/<[^>]+>/g,"")}));
    const m=REV.find(r=>r.kind==="draft"&&r.ref==="meeting");
    document.querySelector("#v-intake-review tr.icsubhead.routine [data-ira=routine]").click(); await wait(300);   /* Approve routine: the minutes' own routine group */
    out.afterGroup=REV.filter(r=>r.file===m.file).map(r=>[r.kind,r.rec.target||r.rec.t.slice(0,20),r.done||"pending"]);
    out.routineKids=REV.filter(r=>r.file===m.file&&!r.done&&!r.indiv&&r.p).length;
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
</script>
"""


class ReviewTests(PrepBase):
    """Updates nest under their minutes (BL-41) with before → after, and closing ones are never routine."""

    def setUp(self):
        super().setUp()
        self.stage([{"op": "update", "table": "actions", "id": "ABC-A-001", "set": {"due_date": "2026-10-16", "latest_update": "07-10-2026: draft sent"},
                     "why": "Omar: pushed to the 16th", "section": "Actions"},
                    {"op": "update", "table": "actions", "id": "ABC-A-002", "set": {"status": "Closed"}, "why": "Alan: the UAT environment is booked",
                     "section": "Actions"},
                    {"op": "update", "table": "raid", "id": "ABC-003", "set": {"response_action": "Escalate to the CIO"}, "why": "Agreed in the meeting",
                     "section": "Risks"},
                    {"table": "actions", "section": "Actions", "values": {"project": "ABC", "description": "Brand new action", "owner": "Omar Ali"}}])

    def rows(self):
        return json.loads(self.v.run("list", "--json", script="review.py").stdout)

    def test_review_list_nests_the_updates_with_before_and_after(self):
        out = self.v.run("list", script="review.py").stdout
        lines = [ln for ln in out.splitlines() if re.match(r"\s*(↳ )?\d+ ·", ln)]
        self.assertTrue(lines[0].lstrip().startswith("1 ·") and "Minutes" in lines[0])
        kids = lines[1:]
        self.assertTrue(all(ln.startswith("   ↳ ") for ln in kids), kids)                  # every update is under the minutes
        text = "\n".join(kids)
        self.assertIn("Update · ABC-A-001 Send revised SOW to client: due 09-10-2026 → 16-10-2026; latest update — → 07-10-2026: draft sent", text)
        self.assertIn("Update · ABC-A-002 Book the UAT environment: status Open → Closed", text)
        self.assertIn("Update · ABC-003 Data access delayed, so UAT may slip: response — → Escalate to the CIO", text)
        self.assertIn("Omar: pushed to the 16th", text)                                        # what was said
        self.assertIn("2026-10-07 Steering committee.docx — Actions", text.replace("minutes/", ""))
        self.assertIn("closing update", text)                                                  # why it's one by one

    def test_the_rows_say_update_and_closing_ones_are_individual(self):
        rows = [r for r in self.rows() if r["ref"] != "meeting"]
        by = {r["text"].split(":")[0].split(" ")[0]: r for r in rows if r["kind"] == "Update"}
        self.assertEqual(set(by), {"ABC-A-001", "ABC-A-002", "ABC-003"})
        self.assertTrue(all(r["child"] and r["nest"] for r in by.values()))
        self.assertEqual((by["ABC-A-002"]["section"], by["ABC-A-002"]["why"]), (2, "closing update"))
        self.assertEqual((by["ABC-A-001"]["section"], by["ABC-A-001"]["why"]), (3, None))
        self.assertEqual(next(r for r in rows if r["kind"] == "Action")["kind"], "Action")

    def test_approve_routine_skips_closing_updates(self):
        out = self.v.run("bulk", script="review.py").stdout
        self.assertIn("1 closing update", out)                                                 # held back
        data = json.loads(next((self.v.root / "system/staging").glob("proposed-2*.json")).read_text())
        done = {i.get("id") or i["values"]["description"]: i["decision"] for i in data["items"]}
        # BL-297 part E: a RAID item's new response is approved on its own; a due date and latest update only stay routine
        self.assertIn("1 response change", out)
        self.assertEqual(done, {"ABC-A-001": "approved", "ABC-A-002": "pending", "ABC-003": "pending", "Brand new action": "approved"})

    def test_a_cx_edit_change_keeps_its_label(self):
        self.v.propose("edit", [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"status": "Delayed"},
                                 "decision": "pending", "match": "strong", "flags": []}])
        row = next(r for r in self.rows() if r["file"] == "proposed-edit.json")
        self.assertEqual((row["kind"], row["text"]), ("Change", "ABC-A-001: status → Delayed"))

    @unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
    def test_dashboard_shows_the_updates_under_their_minutes(self):
        v = self.v
        v.run(script="build_dashboard.py")
        seed = {f"system/staging/{p.name}": p.read_text(encoding="utf-8") for p in (v.root / "system/staging").glob("proposed-*.json")}
        html = (v.root / "dashboard.html").read_text(encoding="utf-8")
        tag = '<script type="application/json" id="seed">' + json.dumps(seed).replace("</", "<\\/") + "</script>"
        harness = v.root / "harness-prep.html"
        harness.write_text(html.replace("</body>", tag + SCRIPT + "</body>"), encoding="utf-8")
        profile = tempfile.mkdtemp(prefix="creaite-chrome-")
        cmd = [str(CHROME), "--headless", "--disable-gpu", f"--user-data-dir={profile}", "--no-first-run",
               "--disable-component-update", "--disable-background-networking", "--virtual-time-budget=8000",
               "--dump-dom", harness.as_uri()]
        try:
            out = subprocess.run(cmd, capture_output=True, timeout=60).stdout
        except subprocess.TimeoutExpired as e:
            out = e.stdout or b""
        finally:
            shutil.rmtree(profile, ignore_errors=True)
        m = re.search(r'<pre id="result">(.*?)</pre>', out.decode("utf-8", "ignore"), re.S)
        self.assertTrue(m, "the page didn't finish")
        r = json.loads(m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&"))
        self.assertEqual(r["errors"], [])
        children = " | ".join(t for k, t in r["layout"] if k == "child")
        for title in ("Send revised SOW to client", "Book the UAT environment", "Data access delayed, so UAT may slip", "Brand new action"):
            self.assertIn(title, children)                                                    # the 3 updates and the new action, under their minutes
        titles = {u["t"]: u for u in r["updates"]}
        self.assertEqual(set(titles), {"ABC-A-001 Send revised SOW to client", "ABC-A-002 Book the UAT environment",
                                       "ABC-003 Data access delayed, so UAT may slip"})
        due = titles["ABC-A-001 Send revised SOW to client"]
        self.assertEqual(due["label"], "Update")
        self.assertIn("due date: 09-10-2026 → 16-10-2026", due["detail"])                      # before → after
        self.assertIn("latest update: — → 07-10-2026: draft sent", due["detail"])
        self.assertIn("“Omar: pushed to the 16th”", due["detail"])
        self.assertTrue(due["src"].endswith("Steering committee.docx — Actions"))
        closing = titles["ABC-A-002 Book the UAT environment"]
        self.assertIn("status: Open → Closed", closing["detail"])
        self.assertEqual((closing["indiv"], closing["whyCol"], due["indiv"]), (True, "Closing update", False))
        states = {a[1]: a[2] for a in r["afterGroup"] if a[0] != "draft"}                      # "Approve all from these minutes"
        self.assertEqual(states["ABC-A-001"], "approved")
        self.assertEqual(states["ABC-A-002"], "pending")                                       # closing: left for you
        self.assertEqual(r["routineKids"], 0)


if __name__ == "__main__":
    unittest.main()

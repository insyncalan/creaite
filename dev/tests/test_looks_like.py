"""BL-221 (sprint-drafts-extraction): "Looks like", a proposal that repeats an existing item. Staging marks it (plain code, no model),
Review merges it as an update, keeps it as new, or rejects it as a duplicate (BL-133's path), and the page shows the mark.

Run: python3 dev/tests/test_looks_like.py
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault, action  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402

NOW = "2026-10-08 09:00"
EMAIL = ("Email · From: Jane Doe <jane@client.com> · Subject: [ABC] SOW · Sent: 2026-10-07 09:12 · "
         "Link: https://outlook.office365.com/owa/?ItemID=ll1")


def add_def(v):
    reg = v.root / "projects/_portfolio/project-register.md"
    reg.write_text(reg.read_text().replace("|  |  |  |  |  |  |  |  |",
                                           "| DEF | Digital Enablement | DEF Digital Enablement | Enable | Sam (sponsor) | "
                                           "def.example | DEF core | portal |"))
    v.run("init")
    for sub in ("minutes", "transcripts"):
        (v.root / "projects/DEF Digital Enablement" / sub).mkdir(parents=True, exist_ok=True)


class LooksLike(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        add_def(self.v)
        self.v.propose("seed", [
            action(1, description="Send the revised SOW to the client legal team", owner="Sara Example", due_date="2026-10-09"),
            action(2, description="Book the UAT environment for the data migration", owner="Omar Ali", status="Closed",
                   closed="2026-10-02"),
            action(3, project="DEF", description="Confirm the portal hosting contract with procurement", owner="Sara Example",
                   source="projects/DEF Digital Enablement/minutes/2026-10-01 Sync.docx — Actions")])
        self.v.run("apply")
        self.ids = {a["description"].split()[0]: a["id"] for a in self.v.rows("actions")}

    def run_(self, script, *args, ok=True):
        r = subprocess.run([sys.executable, str(self.v.root / "system/scripts" / script), *args], cwd=self.v.root,
                           env={**os.environ, "CREAITE_NOW": NOW}, capture_output=True, text=True)
        if ok and r.returncode not in (0, 3):
            raise AssertionError(f"{script} {args}: {r.stdout}{r.stderr}")
        return r

    def sweep(self, *items):
        spec = self.v.root / "system/staging/drafts/sweep.json"
        spec.write_text(json.dumps({"window": {"start": "2026-10-07 08:00", "end": NOW}, "items": list(items)}))
        out = self.run_("sweep.py", "stage", str(spec)).stdout
        prop = sorted((self.v.root / "system/staging").glob("proposed-*-sweep*.json"))[-1]
        return out, prop, json.loads(prop.read_text())

    def new(self, text, project="ABC", **v):
        return {"table": "actions", "match": "strong", "values": {"project": project, "description": text, "source": EMAIL, **v}}

    def number(self, prop, ref):
        rows = json.loads(self.run_("review.py", "list", "--json").stdout)
        return next(r["n"] for r in rows if r["file"] == prop.name and r["ref"] == ref)

    def stats(self):
        p = self.v.root / "system/staging/draft-stats.json"
        return json.loads(p.read_text()).get("repeat", {}) if p.exists() else {}

    def test_a_near_duplicate_is_marked_and_merges_into_an_update(self):
        out, prop, data = self.sweep(self.new("Send revised SOW to client legal", owner="Sara Example", due_date="2026-10-16"))
        ll = data["items"][0]["looks_like"]
        self.assertEqual((ll["id"], ll["state"], ll["same"]), (self.ids["Send"], "open", True))
        self.assertIn(ll["strength"], ("Very likely", "Possible"))
        self.assertNotIn("%", json.dumps(ll))                                     # words, never a percentage
        self.assertIn("Looks like an existing item: 1", out)
        self.assertEqual(self.stats().get("offered"), 1)
        n = self.number(prop, 1)
        listed = self.run_("review.py", "list").stdout
        self.assertIn(f"Looks like {ll['id']} (same project, open)", listed)
        self.run_("review.py", "merge", str(n))
        it = json.loads(prop.read_text())["items"][0]
        self.assertEqual((it["op"], it["id"], it["changes"]), ("update", ll["id"], {"due_date": "2026-10-16"}))
        self.assertEqual(it["decision"], "pending")
        self.assertEqual(self.stats().get("used"), 1)
        self.run_("review.py", "approve", str(self.number(prop, 1)))
        self.run_("tracker.py", "apply")
        row = next(a for a in self.v.rows("actions") if a["id"] == ll["id"])
        self.assertEqual(row["due_date"], "2026-10-16")
        self.assertEqual(len(self.v.rows("actions")), 3)                          # never a second item

    def test_a_different_item_is_not_marked(self):
        _, _, data = self.sweep(self.new("Draft the communications plan for the launch event", owner="Jane Doe"))
        self.assertNotIn("looks_like", data["items"][0])

    def test_a_closed_repeat_is_shown_as_closed_and_not_merged(self):
        _, prop, data = self.sweep(self.new("Book UAT environment for data migration", owner="Omar Ali"))
        ll = data["items"][0]["looks_like"]
        self.assertEqual((ll["id"], ll["state"]), (self.ids["Book"], "closed"))
        r = self.run_("review.py", "merge", str(self.number(prop, 1)), ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("is closed", r.stdout)
        self.assertEqual(json.loads(prop.read_text())["items"][0]["op"], "new")

    def test_cross_project_is_flagged_not_merged(self):
        _, prop, data = self.sweep(self.new("Confirm portal hosting contract with procurement", owner="Sara Example"))
        ll = data["items"][0]["looks_like"]
        self.assertEqual((ll["same"], ll["project"]), (False, "DEF"))
        r = self.run_("review.py", "merge", str(self.number(prop, 1)), ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("another project", r.stdout)

    def test_keep_as_new_drops_the_mark_and_reject_records_duplicate_of(self):
        _, prop, data = self.sweep(self.new("Send revised SOW to client legal", owner="Sara Example"),
                                   self.new("Send the revised SOW to client legal team today", owner="Sara Example"))
        target = data["items"][0]["looks_like"]["id"]
        self.run_("review.py", "keep-new", str(self.number(prop, 1)))
        items = json.loads(prop.read_text())["items"]
        self.assertTrue(items[0]["looks_like"]["kept"])
        self.assertNotIn("Looks like", next(r for r in json.loads(self.run_("review.py", "list", "--json").stdout)
                                            if r["file"] == prop.name and r["ref"] == 1)["note"])
        self.run_("review.py", "reject", f"{self.number(prop, 2)}", f"--duplicate-of={target}")
        self.run_("tracker.py", "apply")
        rej = self.v.rows("rejected")
        self.assertEqual([r["duplicate_of"] for r in rej], [target])
        self.assertEqual((self.stats().get("rejected"), self.stats().get("used")), (1, 1))

    def test_nothing_new_to_carry_rejects_it_as_the_duplicate(self):
        _, prop, data = self.sweep(self.new("Send revised SOW to client legal", owner="Sara Example"))
        self.run_("review.py", "merge", str(self.number(prop, 1)))
        it = json.loads(prop.read_text())["items"][0]
        self.assertEqual((it["decision"], it["duplicate_of"], it["reject_reason"]), ("rejected", data["items"][0]["looks_like"]["id"],
                                                                                     "Duplicate"))

    def test_the_skill_can_judge_a_pair_different(self):
        item = self.new("Send revised SOW to client legal", owner="Sara Example")
        item["repeat"] = {"id": self.ids["Send"], "judged": "different"}
        _, _, data = self.sweep(item)
        self.assertNotIn("looks_like", data["items"][0])

    def test_minutes_staging_marks_repeats_too(self):
        spec = self.v.root / "system/staging/drafts/meeting.json"
        (self.v.root / "system/staging/drafts/m.docx").write_bytes((self.v.root / "system/templates/minutes-template.docx").read_bytes())
        (self.v.root / "inbox/m.vtt").write_text("WEBVTT\n")
        spec.write_text(json.dumps({"title": "ABC weekly", "date": "2026-10-07", "projects": ["ABC"],
                                    "draft": "system/staging/drafts/m.docx", "transcript": "inbox/m.vtt",
                                    "items": [{"table": "actions", "section": "Actions",
                                               "values": {"project": "ABC", "description": "Send revised SOW to client legal",
                                                          "owner": "Sara Example"}}]}))
        self.run_("minutes.py", "stage", str(spec))
        prop = next(p for p in (self.v.root / "system/staging").glob("proposed-*.json") if "sweep" not in p.name)
        self.assertEqual(json.loads(prop.read_text())["items"][0]["looks_like"]["state"], "open")


class Page(unittest.TestCase):
    def test_the_page_says_looks_like_with_compare_merge_and_keep(self):
        page = readable_page()     # BL-231: the source; the bundle reprints the code
        for bit in ('id="llDlg"', "Looks like ${esc(d.id)}", "Merge as an update to", "Keep as new", "/api/review/repeat",
                    "data-rvdup"):
            self.assertIn(bit, page)
        self.assertNotIn("Possible duplicate of ${esc(r.dup.id)}", page)
        server = (Path(__file__).resolve().parents[2] / "system/scripts/live_server.py").read_text()
        self.assertIn('REVIEW_WORK_ROUTES["/api/review/repeat"]', server)


if __name__ == "__main__":
    unittest.main()

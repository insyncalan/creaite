"""BL-111: recode a project (its code, and optionally its name and folder) everywhere.

Run: python3 dev/tests/test_recode.py
Throwaway vaults only. The default layout (folders start with the code) and the OneDrive layout (folders without a code) are both covered.
"""
import hashlib
import json
import shutil
import sqlite3
import sys
import unittest
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_onedrive_projects import OneDriveCase  # noqa: E402
from test_tracker import ABC, REPO, Vault  # noqa: E402

sys.path.insert(0, str(REPO / "system" / "scripts"))
import tracker  # noqa: E402

SRC = f"{ABC}/minutes/2026-10-01 Steering.docx — Actions"
TABLES = ("projects", "milestones", "workstreams", "actions", "raid", "decisions", "promises", "links", "item_labels", "updates", "rejected")


def item(n, table, values, decision="approved", **extra):
    return {"n": n, "op": "new", "table": table, "values": values, "match": "strong", "flags": [], "decision": decision, **extra}


def seed_items(src=SRC):
    base = {"project": "ABC", "raised": "2026-10-01", "source": src, "owner": "Alan Carter"}
    return [
        item(1, "milestones", {"project": "ABC", "name": "Go-live", "baseline_date": "2026-12-01", "source": src}),
        item(2, "workstreams", {"project": "ABC", "name": "Data", "source": src}),
        item(3, "actions", {**base, "description": "Send revised SOW to client"}),
        item(4, "actions", {**base, "description": "Book the steering room"}),
        item(5, "raid", {**base, "type": "Risk", "description": "Data access slips", "impact": "High", "likelihood": "Medium"}),
        item(6, "raid", {**base, "type": "Issue", "description": "Licence not signed"}),
        item(7, "decisions", {"project": "ABC", "decision": "Use the shared tenant", "date": "2026-10-01", "source": src, "made_by": "Alan Carter"}),
        item(8, "updates", {"week_ending": "2026-10-02", "project": "ABC", "health": "On track", "summary": "Steady week"}),
        item(9, "actions", {**base, "description": "Rejected idea"}, decision="rejected"),
        item(10, "promises", {"project": "ABC", "promised_by": "Alan Carter", "promised_to": "Example Person", "description": "Share the plan",
                              "raised": "2026-10-01", "source": src}),
    ]


def link_items(src=SRC):
    """The second batch (seed_items gave ABC-A-001, ABC-A-002, ABC-003, ABC-004, ABC-D-005 and ABC-P-006: one number sequence
    per project): milestone links, a decision that replaces the first, a blocking link, a label and a rejected label."""
    ok = {"match": "strong", "flags": [], "decision": "approved"}
    return [{"n": 1, "op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"milestone": "ABC-M-001"}, **ok},
            {"n": 2, "op": "update", "table": "raid", "id": "ABC-003", "changes": {"milestone": "ABC-M-001"}, **ok},
            item(3, "decisions", {"project": "ABC", "decision": "Use a separate tenant", "date": "2026-10-02", "source": src,
                                  "made_by": "Alan Carter", "replaces": "ABC-D-005"}),
            item(4, "links", {"from_item": "ABC-003", "to_item": "ABC-A-002", "source": src}),
            item(5, "item_labels", {"item_id": "ABC-A-001", "label": "Sensitive"}),
            item(6, "item_labels", {"item_id": "ABC-A-002", "label": "Sensitive"}, decision="rejected")]


class Recode:
    """Shared steps for both layouts."""

    def db(self, sql, *args):
        with closing(sqlite3.connect(self.v.root / "system" / "tracker.db")) as con:
            con.row_factory = sqlite3.Row
            return [dict(r) for r in con.execute(sql, args)]

    def state(self):
        """Every table, the change log as seeded, and the files recode may touch."""
        data = {t: self.db(f"SELECT * FROM {t} ORDER BY 1, 2") for t in TABLES}
        data["change_log"] = self.db("SELECT at, apply_id, tbl, item_id, field, old_value, new_value, op, via FROM change_log "
                                     "WHERE apply_id <= ? ORDER BY rowid", self.seed_applies)
        files = {}
        for sub in ("system/staging/mentions.jsonl", "system/search"):
            p = self.v.root / sub
            for f in ([p] if p.is_file() else sorted(p.glob("*.json")) if p.is_dir() else []):
                text = f.read_text(encoding="utf-8")
                if sub == "system/search" and "path" not in json.loads(text):         # the index's own build stamp
                    continue
                files[f.relative_to(self.v.root).as_posix()] = text
        files["register"] = (self.register_path()).read_text(encoding="utf-8")
        files["memory"] = self.memory_path("ABC").read_text(encoding="utf-8")
        return data, files

    def seed(self):
        self.v.propose("seed", seed_items())
        self.v.run("apply")
        self.v.propose("link", link_items())
        self.v.run("apply")
        self.seed_applies = self.db("SELECT max(apply_id) m FROM applies")[0]["m"]
        (self.v.root / "system/staging/mentions.jsonl").write_text(
            json.dumps({"at": "2026-10-05", "id": "ABC-A-001", "run": "sweep", "source": "mail"}) + "\n"
            + json.dumps({"at": "2026-10-05", "id": "XYZ-A-001", "run": "sweep", "source": "mail"}) + "\n", encoding="utf-8")
        self.v.run("index")

    def recode(self, *args, ok=True):
        return self.v.run("recode", *args, script="propose.py", ok=ok)

    def ids(self, table):
        return [r["id"] for r in self.db(f"SELECT id FROM {table} ORDER BY id")]

    def check_recoded(self, new="XPL", name="Example Plus"):
        proj = self.db("SELECT * FROM projects WHERE code != 'DEF'")           # (the OneDrive layout also has DEF)
        self.assertEqual([(p["code"], p["name"]) for p in proj], [(new, name)])
        self.assertEqual(self.ids("actions"), [f"{new}-A-001", f"{new}-A-002"])            # numbers kept
        self.assertEqual(self.ids("raid"), [f"{new}-003", f"{new}-004"])
        self.assertEqual(self.ids("decisions"), [f"{new}-D-005", f"{new}-D-007"])
        self.assertEqual(self.ids("promises"), [f"{new}-P-006"])
        self.assertEqual(self.db("SELECT replaces FROM decisions WHERE id = ?", f"{new}-D-007")[0]["replaces"], f"{new}-D-005")
        self.assertEqual(self.db("SELECT from_item, to_item FROM links"), [{"from_item": f"{new}-003", "to_item": f"{new}-A-002"}])
        self.assertEqual(self.db("SELECT item_id, label FROM item_labels"), [{"item_id": f"{new}-A-001", "label": "Sensitive"}])
        self.assertEqual(self.ids("milestones"), [f"{new}-M-001"])
        self.assertEqual(self.ids("workstreams"), [f"{new}-W-001"])
        self.assertEqual({r["project"] for t in ("actions", "raid", "decisions", "promises", "milestones", "workstreams", "updates")
                          for r in self.db(f"SELECT project FROM {t}")}, {new})
        self.assertEqual(self.db("SELECT milestone FROM actions WHERE id = ?", f"{new}-A-001")[0]["milestone"], f"{new}-M-001")
        self.assertEqual(self.db("SELECT milestone FROM raid WHERE id = ?", f"{new}-003")[0]["milestone"], f"{new}-M-001")
        out = self.v.run("read", "actions", "--project", "ABC").stdout
        self.assertEqual(json.loads(out), [])                                                # nothing left under the old code
        log = self.db("SELECT item_id, field, old_value, new_value FROM change_log WHERE tbl != 'recode'")
        self.assertFalse([r for r in log if str(r["item_id"]).startswith("ABC-") or "|ABC" in str(r["item_id"])])
        self.assertTrue([r for r in log if r["item_id"] == f"{new}-A-001"])                  # each item's history follows it
        ml = [r for r in log if r["item_id"] == f"{new}-A-001" and r["field"] == "milestone"]
        self.assertEqual([r["new_value"] for r in ml], [f"{new}-M-001"])


class DefaultLayoutTests(Recode, unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.seed()

    def tearDown(self):
        self.v.cleanup()

    def register_path(self):
        return self.v.root / "projects/_portfolio/project-register.md"

    def memory_path(self, code):
        return self.v.root / ("projects/XPL Example Plus/CLAUDE.md" if code == "XPL" else f"{ABC}/CLAUDE.md")

    def rename_folder(self):
        shutil.move(str(self.v.root / ABC), str(self.v.root / "projects/XPL Example Plus"))
        self.memory_path = lambda code: self.v.root / "projects/XPL Example Plus/CLAUDE.md"

    def test_the_default_layout_needs_the_folder_renamed_first(self):
        r = self.recode("ABC", "XPL", ok=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("start with the code", r.stdout + r.stderr)
        r = self.recode("ABC", "XPL", "--folder", "XPL Example Plus", ok=False)
        self.assertIn("doesn't exist", r.stdout + r.stderr)

    def test_dry_run_and_the_pending_refusal_change_nothing(self):
        self.rename_folder()
        before = self.state()
        out = self.recode("ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus", "--dry-run").stdout
        self.assertIn("Recode ABC → XPL; name: Example Programme → Example Plus", out)
        self.assertIn("actions: 2 (e.g. ABC-A-001 → XPL-A-001)", out)
        self.assertIn("raid: 2", out)
        self.assertIn("promises: 1 (e.g. ABC-P-006 → XPL-P-006)", out)
        self.assertIn("links: 2 reference(s) to ABC- items follow", out)
        self.assertIn("labels on these items: 1 reference(s) to ABC- items follow", out)
        self.assertIn("rejected items carried over: 2", out)
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*-edit.json")), [])
        self.assertEqual(self.state(), before)
        self.v.propose("later", [item(1, "actions", {"project": "ABC", "description": "Still pending", "raised": "2026-10-02", "source": SRC})])
        r = self.recode("ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("pending proposal(s) still mention ABC: proposed-later.json", r.stdout.replace("waiting suggestion(s)", "pending proposal(s)"))     # #292: the new words are the same fact
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*-edit.json")), [])
        self.assertEqual(self.state(), before)

    def test_apply_recodes_everything_and_undo_restores_the_exact_state(self):
        self.rename_folder()
        (self.v.root / "system/search").mkdir(parents=True, exist_ok=True)
        old_rel = f"{ABC}/minutes/2026-10-01 Steering.docx"
        sidecar = self.v.root / "system/search" / (hashlib.sha256(old_rel.encode()).hexdigest() + ".json")
        sidecar.write_text(json.dumps({"path": old_rel, "summary": "Steering", "tags": ["a", "b", "c"]}), encoding="utf-8")
        before = self.state()
        out = self.recode("ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus").stdout
        self.assertIn("Staged and approved", out)
        self.assertIn("Check:", out)
        applied = self.v.run("apply").stdout
        self.assertIn("Apply 3: written 1", applied)
        self.check_recoded()
        # the sources follow the renamed folder
        self.assertTrue(all(r["source"].startswith("projects/XPL Example Plus/") for r in self.db("SELECT source FROM actions")))
        # the register: new row, old code retired, the memory heading, mentions, the sidecar
        reg = self.register_path().read_text(encoding="utf-8")
        self.assertRegex(reg, r"\| XPL \| Example Plus \| XPL Example Plus \|")
        self.assertRegex(reg, r"\| ABC \| Example Programme \(recoded to XPL\) \| \d{4}-\d{2}-\d{2} \|")
        self.assertNotRegex(reg, r"\| ABC \| Example Plus")
        self.assertTrue(self.memory_path("XPL").read_text(encoding="utf-8").startswith("# XPL — Example Plus"))
        lines = (self.v.root / "system/staging/mentions.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual([json.loads(ln)["id"] for ln in lines], ["XPL-A-001", "XYZ-A-001"])    # another project's id is left alone
        self.assertFalse(sidecar.exists())
        new_rel = "projects/XPL Example Plus/minutes/2026-10-01 Steering.docx"
        moved = self.v.root / "system/search" / (hashlib.sha256(new_rel.encode()).hexdigest() + ".json")
        self.assertEqual(json.loads(moved.read_text())["path"], new_rel)
        # the rejected item is still remembered under the new code
        fp = tracker.fingerprint(item(9, "actions", {"project": "XPL", "description": "Rejected idea"}))
        self.assertIn(fp, [r["fingerprint"] for r in self.db("SELECT fingerprint FROM rejected")])
        fp = tracker.fingerprint(item(6, "item_labels", {"item_id": "XPL-A-002", "label": "Sensitive"}))      # a rejected label follows too
        self.assertIn(fp, [r["fingerprint"] for r in self.db("SELECT fingerprint FROM rejected")])
        self.assertTrue(all("ABC" not in (r["project"] or "").split() for r in self.db("SELECT project FROM vault_search")))
        # undo restores the exact previous state
        self.assertIn("Undid apply 3", self.v.run("undo").stdout)
        after = self.state()
        self.assertEqual(after[0], before[0])
        self.assertEqual({k: v for k, v in after[1].items() if k != "register"}, {k: v for k, v in before[1].items() if k != "register"})
        self.assertEqual(after[1]["register"], before[1]["register"])
        # the recode comes back to staging, ready to apply again
        self.assertEqual(len(list((self.v.root / "system/staging").glob("proposed-*-edit.json"))), 1)

    def test_ordinary_work_continues_after_a_recode_and_its_undo(self):
        self.rename_folder()
        self.recode("ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus")
        self.v.run("apply")
        self.v.propose("close", [{"n": 1, "op": "update", "table": "actions", "id": "XPL-A-001", "changes": {"status": "Closed"},
                                  "match": "strong", "flags": [], "decision": "approved"},
                                 item(2, "actions", {"project": "XPL", "description": "A new one", "raised": "2026-10-03", "source": SRC})])
        self.v.run("apply")
        self.assertEqual(self.ids("actions"), ["XPL-A-001", "XPL-A-002", "XPL-A-008"])   # the sequence continues under the new code
        self.v.run("undo")                                                                   # the ordinary apply
        self.assertEqual(self.db("SELECT status FROM actions WHERE id = 'XPL-A-001'")[0]["status"], "Open")
        self.assertEqual(self.ids("actions"), ["XPL-A-001", "XPL-A-002"])
        self.v.run("undo")                                                                   # the recode itself
        self.assertEqual(self.ids("actions"), ["ABC-A-001", "ABC-A-002"])

    def test_a_recode_is_applied_on_its_own(self):
        self.rename_folder()
        self.recode("ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus")
        self.v.propose("other", [item(1, "decisions", {"project": "XPL", "decision": "Unrelated", "date": "2026-10-03",
                                                              "source": "projects/XPL Example Plus/minutes/2026-10-03 Call.docx — Decisions"})])
        out = self.v.run("apply").stdout
        self.assertIn("applying it first, on its own" if "is a recode" in out else "saving it first, on its own", out)     # #292: the new words are the same fact
        self.assertEqual(self.ids("decisions"), ["XPL-D-005", "XPL-D-007"])                  # the other proposal waits
        self.assertIn("written 1", self.v.run("apply").stdout)
        self.assertEqual(self.ids("decisions"), ["XPL-D-005", "XPL-D-007", "XPL-D-008"])

    def test_refusals_say_why(self):
        self.rename_folder()
        self.v.propose("def", [item(1, "projects", {"code": "DEF", "name": "Other"})])
        self.v.run("apply")
        for new, text in (("DEF", "already a project"), ("ABC", "already the code"), ("AB", "3 to 7 capital letters"),
                          ("abc1", "3 to 7 capital letters"), ("TOOLONG1", "3 to 7 capital letters")):
            r = self.recode("ABC", new, "--folder", f"{new} Example Programme", ok=False)
            self.assertNotEqual(r.returncode, 0, new)
            self.assertIn(text, r.stdout + r.stderr, new)
        reg = self.register_path()
        reg.write_text(reg.read_text(encoding="utf-8").rstrip("\n") + "\n| OLDX | Old thing | 2026-01-01 |\n", encoding="utf-8")
        r = self.recode("ABC", "OLDX", "--folder", "OLDX Example Programme", ok=False)
        self.assertIn("already in the project register", r.stdout + r.stderr)

    def test_the_recode_knows_every_table_or_refuses(self):
        with closing(sqlite3.connect(":memory:")) as con:
            con.executescript((REPO / "system/scripts/schema.sql").read_text(encoding="utf-8"))
            self.assertEqual(tracker.recode_unclassified(con), [],
                             "the schema has a table or column that carries a project or item ID: add it to RECODE_COLUMNS in tracker.py")
            con.execute("CREATE TABLE widgets (id TEXT PRIMARY KEY, project TEXT, from_item TEXT)")
            self.assertEqual(tracker.recode_unclassified(con), ["widgets"])
            con.execute("ALTER TABLE actions ADD COLUMN replaces TEXT")
            self.assertEqual(tracker.recode_unclassified(con), ["actions.replaces", "widgets"])
        self.rename_folder()
        with closing(sqlite3.connect(self.v.root / "system" / "tracker.db")) as con:
            con.execute("CREATE TABLE widgets (project TEXT)")
            con.commit()
        r = self.recode("ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus", ok=False)
        self.assertIn("doesn't know how to recode widgets", r.stdout + r.stderr)

    def test_references_from_another_project_follow_the_recode(self):
        with closing(sqlite3.connect(":memory:")) as con:
            con.row_factory = sqlite3.Row
            con.executescript((REPO / "system/scripts/schema.sql").read_text(encoding="utf-8"))
            for code in ("ABC", "DEF"):
                con.execute("INSERT INTO projects (code, name) VALUES (?, ?)", (code, code))
                con.execute("INSERT INTO decisions (id, project, decision, date, source) VALUES (?, ?, 'x', '2026-10-01', 's')", (f"{code}-D-001", code))
                con.execute("INSERT INTO actions (id, project, description, raised, source) VALUES (?, ?, 'x', '2026-10-01', 's')", (f"{code}-A-001", code))
            con.execute("UPDATE decisions SET replaces = 'ABC-D-001' WHERE id = 'DEF-D-001'")
            con.execute("INSERT INTO links (from_item, to_item, source) VALUES ('DEF-A-001', 'ABC-A-001', 'projects/Other/x')")
            con.execute("INSERT INTO item_labels (item_id, label) VALUES ('ABC-A-001', 'Sensitive')")
            con.execute("INSERT INTO applies (apply_id, at, proposals) VALUES (1, '2026-10-01', '[]')")
            con.execute("INSERT INTO change_log (at, apply_id, tbl, item_id, field, old_value, new_value, op, via) "
                        "VALUES ('2026-10-01', 1, 'links', 'DEF-A-001|ABC-A-001|blocks', 'to_item', NULL, 'ABC-A-001', 'insert', 'test')")
            con.execute("INSERT INTO change_log (at, apply_id, tbl, item_id, field, old_value, new_value, op, via) "
                        "VALUES ('2026-10-01', 1, 'item_labels', 'ABC-A-001|Sensitive', 'item_id', NULL, 'ABC-A-001', 'insert', 'test')")
            tracker.rewrite_project(con, "ABC", "XPL")
            self.assertEqual(con.execute("SELECT replaces FROM decisions WHERE id = 'DEF-D-001'").fetchone()[0], "XPL-D-001")
            self.assertEqual(tuple(con.execute("SELECT from_item, to_item FROM links").fetchone()), ("DEF-A-001", "XPL-A-001"))
            self.assertEqual(con.execute("SELECT item_id FROM item_labels").fetchone()[0], "XPL-A-001")
            self.assertEqual([tuple(r) for r in con.execute("SELECT item_id, new_value FROM change_log ORDER BY rowid")],
                             [("DEF-A-001|XPL-A-001|blocks", "XPL-A-001"), ("XPL-A-001|Sensitive", "XPL-A-001")])
            tracker.rewrite_project(con, "XPL", "ABC")                                       # undo is the same step the other way
            self.assertEqual(con.execute("SELECT replaces FROM decisions WHERE id = 'DEF-D-001'").fetchone()[0], "ABC-D-001")
            self.assertEqual(tuple(con.execute("SELECT from_item, to_item FROM links").fetchone()), ("DEF-A-001", "ABC-A-001"))

    def test_a_dashboard_builds_with_a_staged_recode(self):
        self.rename_folder()
        self.recode("ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus")
        self.v.run(script="build_dashboard.py")
        self.assertTrue((self.v.root / "dashboard.html").is_file())
        import review
        kind, text, _, _ = review.describe({"op": "recode", "table": "projects", "id": "ABC", "changes": {"code": "XPL"}})
        self.assertEqual((kind, text), ("Recode", "ABC: code → XPL"))


class OneDriveLayoutTests(Recode, OneDriveCase):
    """The live vault's layout: the engagement folder has no code in its name, so a recode needs no folder change."""

    def setUp(self):
        super().setUp()
        self.seed_applies = 0
        src = "projects/Example Programme/02 Meetings/Minutes/2026-10-01 Steering.docx — Actions"
        self.v.propose("seed", seed_items(src))
        self.v.run("apply")
        self.v.propose("link", link_items(src))
        self.v.run("apply")
        self.seed_applies = self.db("SELECT max(apply_id) m FROM applies")[0]["m"]
        self.v.run("index")

    def register_path(self):
        return self.root / "_Portfolio" / "project-register.md"

    def memory_path(self, code):
        return self.eng("ABC", "CLAUDE.md")

    def test_name_and_code_change_with_the_folder_left_alone(self):
        before = self.state()
        out = self.recode("ABC", "XPL", "--name", "Example Plus").stdout
        self.assertIn("Check: The folder “Example Programme” still carries", out)
        self.v.run("apply")
        self.check_recoded()
        self.assertTrue(all(r["source"].startswith("projects/Example Programme/") for r in self.db("SELECT source FROM actions")))
        reg = self.register_path().read_text(encoding="utf-8")
        self.assertRegex(reg, r"\| XPL \| Example Plus \| Example Programme \|")              # the folder cell is unchanged
        self.assertTrue(self.memory_path("ABC").read_text(encoding="utf-8").startswith("# XPL — Example Plus"))
        self.v.run("undo")
        after = self.state()
        self.assertEqual(after, before)

    def test_a_renamed_engagement_folder_is_followed(self):
        before = self.state()
        shutil.move(str(self.eng("ABC")), str(self.root / "Example Plus"))
        self.recode("ABC", "XPL", "--name", "Example Plus", "--folder", "Example Plus")
        self.v.run("apply")
        self.check_recoded()
        self.assertTrue(all(r["source"].startswith("projects/Example Plus/") for r in self.db("SELECT source FROM actions")))
        self.assertTrue((self.root / "Example Plus" / "CLAUDE.md").read_text(encoding="utf-8").startswith("# XPL — Example Plus"))
        self.v.run("undo")
        shutil.move(str(self.root / "Example Plus"), str(self.eng("ABC")))
        self.assertEqual(self.state(), before)


if __name__ == "__main__":
    unittest.main()

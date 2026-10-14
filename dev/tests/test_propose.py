"""Tests for propose.py (cx-edit's exact parts).

Run: python3 dev/tests/test_propose.py
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import ABC, Vault, action  # noqa: E402


class ProposeTests(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        self.v.propose("seed", [action(1)])
        self.v.run("apply")

    def tearDown(self):
        self.v.cleanup()

    def p(self, *args, ok=True):
        return self.v.run(*args, script="propose.py", ok=ok)

    def spec(self, data, name="spec.json"):
        f = self.v.root / "system/staging/drafts" / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(data))
        return str(f)

    def staged(self):
        return sorted((self.v.root / "system/staging").glob("proposed-*-edit.json"))

    def test_update_preview_stage_apply(self):
        s = self.spec({"items": [{"op": "update", "table": "actions", "id": "ABC-A-001",
                                  "changes": {"status": "Closed", "due_date": "2026-10-20"}}]})
        out = self.p("preview", s).stdout
        self.assertIn("ABC-A-001 · Status: Open → Closed; Due: — → 20-10-2026", out)
        self.assertEqual(self.staged(), [])                                   # preview writes nothing
        self.assertIn("Staged and approved", self.p("stage", s).stdout)
        data = json.loads(self.staged()[0].read_text())
        self.assertEqual((data["source_run"], data["items"][0]["decision"]), ("cx-edit", "approved"))
        self.assertIn("based_on", data["items"][0])                            # conflicts are caught
        self.v.run("apply")
        row = self.v.rows("actions")[0]
        self.assertEqual((row["status"], row["due_date"]), ("Closed", "2026-10-20"))
        self.assertIsNotNone(row["closed"])

    def test_invalid_change_not_staged(self):
        s = self.spec({"items": [{"op": "update", "table": "actions", "id": "ABC-A-001", "changes": {"status": "Done"}}]})
        r = self.p("stage", s, ok=False)
        self.assertIn("Open, Delayed, Closed, Cancelled", r.stdout)
        self.assertIn("Not staged.", r.stdout)
        self.assertEqual(self.staged(), [])

    def test_memory_change_and_conflict(self):
        path = f"{ABC}/CLAUDE.md"
        old = (self.v.root / path).read_text()
        s = self.spec({"file_changes": {"title": "ABC memory", "project": "ABC",
                                        "file_ops": [{"op": "write", "path": path,
                                                      "content": old + "- Sponsor prefers one-page updates.\n"}]}})
        out = self.p("preview", s).stdout
        self.assertIn(f"Change {path}:", out)
        self.assertIn("+- Sponsor prefers one-page updates.", out)
        self.p("stage", s)
        self.v.run("apply")
        self.assertIn("one-page updates", (self.v.root / path).read_text())
        self.v.run("undo")
        self.assertEqual((self.v.root / path).read_text(), old)                # undo restores the file exactly
        stale = self.spec({"file_changes": {"title": "x", "file_ops": [{"op": "write", "path": path, "content": "new",
                                                                        "previous": "something else"}]}})
        self.assertIn("the file changed since", self.p("preview", stale, ok=False).stdout)

    def test_write_already_made_does_not_block_apply(self):
        # two proposals made from the same text: the first applies, and the second (same result) must not fail the apply
        path = f"{ABC}/CLAUDE.md"
        old = (self.v.root / path).read_text()
        new = old + "- Sponsor prefers one-page updates.\n"
        for n in ("one.json", "two.json"):
            self.p("stage", self.spec({"file_changes": {"title": n, "file_ops": [{"op": "write", "path": path, "content": new}]}}, n))
        self.assertEqual(len(self.staged()), 2)
        self.v.run("apply")
        self.assertEqual((self.v.root / path).read_text(), new)
        self.assertEqual(self.staged(), [])
        self.v.run("undo")
        self.assertEqual((self.v.root / path).read_text(), old)

    def stage_ops(self, ops, n):
        self.p("stage", self.spec({"file_changes": {"title": n, "file_ops": ops}}, n + ".json"))

    def apply_fails(self):
        r = self.v.run("apply", ok=False)
        self.assertNotEqual(r.returncode, 0)
        return r.stdout + r.stderr

    def test_write_with_previous_already_made_passes(self):
        # the cx-edit memory change carries `previous`: the second of two, made from the same text, finds the change in place
        path = f"{ABC}/CLAUDE.md"
        old = (self.v.root / path).read_text()
        new = old + "- Sponsor prefers one-page updates.\n"
        for n in ("one", "two"):
            self.stage_ops([{"op": "write", "path": path, "content": new, "previous": old}], n)
        self.assertIn("one-page updates", self.p("preview", self.spec({"file_changes": {"title": "x", "file_ops": [
            {"op": "write", "path": path, "content": new, "previous": old}]}})).stdout)
        self.v.run("apply")
        self.assertEqual((self.v.root / path).read_text(), new)
        self.assertEqual(self.staged(), [])
        # staged again after the change is in place: not a conflict at preview either
        self.p("preview", self.spec({"file_changes": {"title": "y", "file_ops": [
            {"op": "write", "path": path, "content": new, "previous": old}]}}, "y.json"))
        self.v.run("undo")
        self.assertEqual((self.v.root / path).read_text(), old)

    def test_register_change_already_made_passes(self):
        path = "projects/_portfolio/project-register.md"
        old = (self.v.root / path).read_text()
        new = old + "\n<!-- note -->\n"
        for n in ("one", "two"):
            self.stage_ops([{"op": "write", "path": path, "content": new, "previous": old}], n)
        self.v.run("apply")
        self.assertEqual((self.v.root / path).read_text(), new)

    def test_write_conflict_still_stops_the_apply(self):
        path = f"{ABC}/CLAUDE.md"
        old = (self.v.root / path).read_text()
        self.stage_ops([{"op": "write", "path": path, "content": old + "- Proposed.\n", "previous": old}], "one")
        (self.v.root / path).write_text(old + "- Someone else changed this.\n")                   # the file moved on
        self.assertIn("changed since this proposal was made", self.apply_fails())
        self.assertIn("Someone else", (self.v.root / path).read_text())
        # a new file that appeared since, with other content, is refused too
        other = f"{ABC}/documents/new.txt"
        for f in self.staged():
            f.unlink()
        self.stage_ops([{"op": "write", "path": other, "content": "mine"}], "two")
        (self.v.root / other).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / other).write_text("different")
        self.assertIn("already exists", self.apply_fails())
        self.assertEqual((self.v.root / other).read_text(), "different")

    def test_chained_writes_to_one_file_apply_in_order(self):
        # two edits of one file, the second made on the first's result (a dashboard register edit while the first is pending)
        path = f"{ABC}/CLAUDE.md"
        old = (self.v.root / path).read_text()
        mid, new = old + "- First.\n", old + "- First.\n- Second.\n"
        self.stage_ops([{"op": "write", "path": path, "content": mid, "previous": old}], "one")
        self.stage_ops([{"op": "write", "path": path, "content": new, "previous": old}], "two")     # staging checks the disk, so base it there...
        second = next(p for p in self.staged() if json.loads(p.read_text())["file_changes"]["file_ops"][0]["content"] == new)
        data = json.loads(second.read_text())
        data["file_changes"]["file_ops"][0]["previous"] = mid                                      # ...then chain it, as the dashboard does
        second.unlink()
        (second.parent / "proposed-z-edit.json").write_text(json.dumps(data))                      # and make sure it sorts last, as a later save does
        self.v.run("apply")
        self.assertEqual((self.v.root / path).read_text(), new)

    def test_stale_write_stops_before_the_backup_and_names_the_proposal(self):
        path = f"{ABC}/CLAUDE.md"
        old = (self.v.root / path).read_text()
        self.stage_ops([{"op": "write", "path": path, "content": old + "- A.\n", "previous": old}], "one")
        self.stage_ops([{"op": "write", "path": path, "content": old + "- B.\n", "previous": old}], "two")   # made from the same text
        backups = lambda: sorted((self.v.root / "system/backups").glob("tracker-*-apply.db"))
        before = backups()
        out = self.apply_fails()
        self.assertIn("Apply stopped", out)
        self.assertIn("changed since this proposal was made", out)
        self.assertRegex(out, r"proposed-[^\s]*-edit(-\d+)?\.json file_changes")
        self.assertEqual(backups(), before)                                                          # nothing was backed up or written
        self.assertEqual((self.v.root / path).read_text(), old)

    def test_copy_already_made_passes_and_conflict_stops(self):
        src, dst = f"{ABC}/documents/a.txt", f"{ABC}/documents/b.txt"
        (self.v.root / src).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / src).write_text("same")
        for n in ("one", "two"):
            self.stage_ops([{"op": "copy", "from": src, "to": dst}], n)
        self.v.run("apply")
        self.assertEqual((self.v.root / dst).read_text(), "same")
        self.assertEqual(self.staged(), [])
        self.v.run("undo")                                                                           # the copy made once is undone once
        self.assertFalse((self.v.root / dst).exists())
        (self.v.root / dst).write_text("other content")                                              # a different file there: refused
        self.stage_ops([{"op": "copy", "from": src, "to": dst}], "three")
        self.assertIn("already exists; it is never overwritten", self.apply_fails())
        self.assertEqual((self.v.root / dst).read_text(), "other content")

    def test_remove_and_mkdir_already_done_pass(self):
        gone, folder = f"{ABC}/documents/none.txt", f"{ABC}/documents/sub"
        (self.v.root / folder).mkdir(parents=True, exist_ok=True)
        self.stage_ops([{"op": "remove", "path": gone}, {"op": "mkdir", "path": folder}], "one")
        self.v.run("apply")
        self.assertTrue((self.v.root / folder).is_dir())
        self.assertEqual(self.staged(), [])

    def test_new_project_and_undo(self):
        register = (self.v.root / "projects/_portfolio/project-register.md").read_text()
        out = self.p("new-project", "--code", "DEF", "--name", "Digital Enablement", "--sponsor", "Omar Ali",
                     "--client", "Enable Ltd", "--rhythm", "fortnightly").stdout
        s = self.spec(json.loads(out), "def.json")
        preview = self.p("preview", s).stdout
        self.assertIn("New project: ", preview)
        self.assertIn("Create folder projects/DEF Digital Enablement/minutes/", preview)
        self.assertIn("+| DEF | Digital Enablement | DEF Digital Enablement | Enable Ltd | Omar Ali (sponsor) |", preview)
        self.p("stage", s)
        self.v.run("apply")
        folder = self.v.root / "projects/DEF Digital Enablement"
        memory = (folder / "CLAUDE.md").read_text()
        self.assertTrue((folder / "documents").is_dir())
        self.assertIn("# DEF — Digital Enablement", memory)
        self.assertIn("**Client / partner:** Enable Ltd", memory)
        self.assertIn("**Client report rhythm:** fortnightly", memory)
        self.assertIn("DEF", [p["code"] for p in self.v.rows("projects")])
        self.v.run("undo")
        self.assertFalse(folder.exists())
        self.assertEqual((self.v.root / "projects/_portfolio/project-register.md").read_text(), register)
        self.assertNotIn("DEF", [p["code"] for p in self.v.rows("projects")])

    def test_codes_in_use_or_retired_refused(self):
        self.assertIn("already used", self.p("new-project", "--code", "ABC", "--name", "X", ok=False).stderr)
        reg = self.v.root / "projects/_portfolio/project-register.md"
        reg.write_text(reg.read_text().replace("| Code | Project | Closed |\n|------|---------|--------|",
                                               "| Code | Project | Closed |\n|------|---------|--------|\n| OLD | Old one | 2025-01-31 |"))
        self.assertIn("already used", self.p("new-project", "--code", "OLD", "--name", "Y", ok=False).stderr)
        self.assertIn("3 to 7 capital letters", self.p("new-project", "--code", "2X", "--name", "Y", ok=False).stderr)

    def test_close_project(self):
        r = self.p("close-project", "ABC")
        self.assertEqual(json.loads(r.stdout)["items"][0]["changes"], {"active": 0})
        self.assertIn("Open items in Example Programme: ABC-A-001", r.stderr)

    def register(self):
        return (self.v.root / "projects/_portfolio/project-register.md").read_text(encoding="utf-8")

    def row(self, code):
        return next(ln for ln in self.register().splitlines() if ln.startswith(f"| {code} |"))

    def test_learn_a_sender_then_undo(self):
        """BL-28: a signal Alan confirms is added to the register through an approved proposal; undo removes it."""
        before = self.register()
        out = self.p("learn", "ABC", "sender", "sara.khan@client.com").stdout
        self.assertIn("+| ABC |", out.replace("    ", ""))
        self.v.run("apply")
        self.assertTrue(self.row("ABC").rstrip(" |").endswith("sara.khan@client.com"))   # Senders column
        self.v.run("undo")
        self.assertEqual(self.register(), before)

    def test_learn_guardrails(self):
        check = lambda *a: json.loads(self.p("learn", *a, "--check").stdout)  # noqa: E731
        self.assertFalse(check("ABC", "keyword", "pilot")["ok"])                          # weak: never learnt
        own = check("ABC", "sender", "someone@brightwater.example")
        self.assertIn("own company's domain", own["reason"])
        self.assertIn("already a signal for ABC", check("ABC", "domain", "client.com")["reason"])
        shared = check("ABC", "stakeholder", "Example Person")
        self.assertIn("Shared", shared["reason"])
        self.assertEqual(self.p("learn", "ABC", "sender", "x@brightwater.example", ok=False).returncode, 1)
        self.assertEqual(self.staged(), [])

    def test_learn_into_shared_never_two_rows(self):
        self.p("new-project", "--code", "DEF", "--name", "Digital Enablement")    # spec only; add the row by hand
        reg = self.v.root / "projects/_portfolio/project-register.md"
        reg.write_text(reg.read_text().replace("|  |  |  |  |  |  |  |  |  |  |",
                                               "| DEF | Digital Enablement | DEF Digital Enablement |  |  |  |  |  |  |  |"))
        self.v.propose("def", [{"n": 1, "op": "new", "table": "projects", "values": {"code": "DEF", "name": "Digital Enablement"},
                                "match": "strong", "flags": [], "decision": "approved"}])
        self.v.run("apply")
        res = json.loads(self.p("learn", "DEF", "domain", "client.com", "--check").stdout)
        self.assertTrue(res["needs_shared"] and res["owners"] == ["ABC"])
        self.p("learn", "DEF", "domain", "client.com", "--shared")
        self.v.run("apply")
        self.assertNotIn("client.com", self.row("ABC"))
        self.assertIn("| client.com | Email domain | ABC, DEF |", self.register())

    def test_register_columns_added_to_an_old_register(self):
        reg = self.v.root / "projects/_portfolio/project-register.md"
        reg.write_text("# Project register\n\n## Projects\n\n"
                       "| Code | Project name | Folder under projects/ | Aliases / client names | Key stakeholders | "
                       "Email domains | Teams channels | Keywords |\n|---|---|---|---|---|---|---|---|\n"
                       "| ABC | Example Programme | ABC Example Programme | Example | Jane Doe | client.com | ABC – Core | MVP |\n\n"
                       "## Shared (not a signal on their own)\n\n| Item | Type | Projects |\n|---|---|---|\n")
        self.assertNotIn("Senders", self.register())
        self.p("register-columns")
        self.v.run("apply")
        head = next(ln for ln in self.register().splitlines() if ln.startswith("| Code |"))
        self.assertTrue(head.endswith("| Senders | Exclude |"))
        self.assertEqual(self.row("ABC").count("|"), head.count("|"))

    def test_health_better_than_evidence(self):
        """BL-52: cx-edit shows the evidence and needs a reason for a health better than it."""
        urgent = lambda n, t: {"n": n, "op": "new", "table": "raid", "match": "strong", "flags": [], "decision": "approved",  # noqa: E731
                               "values": {"project": "ABC", "type": t, "description": f"Urgent {n}", "impact": "High",
                                          "likelihood": "High", "raised": "2026-10-01", "source": "s"}}
        self.v.propose("risky", [urgent(1, "Risk"), urgent(2, "Issue")])          # two Urgent: the criteria say Off track
        self.v.run("apply")
        bare = self.spec({"items": [{"op": "update", "table": "projects", "id": "ABC", "changes": {"health": "On track"}}]})
        out = self.p("preview", bare, ok=False).stdout
        self.assertIn("Evidence suggests Off track", out)
        self.assertIn("give a health_reason", out)
        ok = self.spec({"items": [{"op": "update", "table": "projects", "id": "ABC",
                                   "changes": {"health": "On track", "health_reason": "Both risks are mitigated today"}}]}, "ok.json")
        self.assertEqual(self.p("preview", ok).returncode, 0)

    def test_settings(self):
        out = self.p("setting", "sweep.due_from", "06:30").stdout
        self.assertIn('sweep.due_from: "07:00" → "06:30"', out)
        settings = json.loads((self.v.root / "system/config/settings.json").read_text())
        self.assertEqual(settings["sweep"]["due_from"], "06:30")
        self.assertTrue(list((self.v.root / "system/backups").glob("settings-*.json")))
        log = (self.v.root / "system/config/settings-log.jsonl").read_text().splitlines()
        self.assertEqual(json.loads(log[-1])["key"], "sweep.due_from")
        self.assertIn("expects a int", self.p("setting", "review.stale_after_days", '"ten"', ok=False).stderr)
        self.assertIn("HH:MM", self.p("setting", "sweep.due_from", "6.30", ok=False).stderr)
        self.assertIn("No setting", self.p("setting", "sweep.nope", "1", ok=False).stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)

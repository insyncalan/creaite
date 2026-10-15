"""BL-301 E (v20-find-updates): Find updates, the engine. The mockup's catch-up note yields the rows shown there; the bulk rule sets the
ticks (new risks, milestone moves and memory lines unticked, routine rows ticked); a hedged line never moves a milestone and gets a
confirm action; repeats (BL-221), probably done (BL-218) and vague actions (BL-220) are marked; Apply writes the ticked rows as one
apply that Undo reverses; Save for later leaves them pending in Review; a second run skips sent lines; each item's source is the
note's line; notes-sent.json never holds text; a confidential note's items are Sensitive.

Run: python3 dev/tests/test_notes_find.py
A throwaway vault; the engine runs in a child process with the vault's own scripts. Claude is never called: the stand-in's answer
(notes_find_fixture.reply_for) is given to notes_find.rows.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import notes_find_fixture as fx  # noqa: E402
from test_tracker import Vault  # noqa: E402

HARNESS = r"""
import json, sys
sys.path.insert(0, "system/scripts")
sys.path.insert(0, %r)
import notes_find, notes, paths
import notes_find_fixture as fx
cmd = json.loads(sys.stdin.read())
rel = cmd.get("path", fx.NOTE)
if cmd["do"] == "find":
    ctx = notes_find.context(rel, cmd.get("p"))
    ctx["rel"] = rel
    if ctx.get("prompt"):
        got = notes_find.rows(ctx, fx.reply_for(ctx["prompt"], cmd.get("rows")))
        got["prompt"] = ctx["prompt"]
        print(json.dumps(got))
    else:
        print(json.dumps(ctx))
elif cmd["do"] == "stage":
    print(json.dumps(notes_find.stage(rel, cmd["rows"], cmd["mode"])))
elif cmd["do"] == "record":
    print(json.dumps(notes_find.record(rel, cmd["file"], cmd.get("apply_id"))))
elif cmd["do"] == "forget":
    print(json.dumps(notes_find.forget(rel, cmd["apply_id"])))
"""


class Engine(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.cleanup)
        fx.load(self.v)

    def call(self, **cmd):
        r = subprocess.run([sys.executable, "-c", HARNESS % str(Path(__file__).resolve().parent)], cwd=self.v.root,
                           input=json.dumps(cmd), capture_output=True, text=True, env={**os.environ, "CREAITE_NOW": fx.NOW})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def find(self, **kw):
        return self.call(do="find", **kw)

    def ticked(self, got):
        return [{"key": r["key"], "fp": r["fp"], "item": r["item"]} for r in got["rows"] if r["tick"]]

    def apply(self, rows):
        st = self.call(do="stage", rows=rows, mode="apply")
        self.assertTrue(st["ok"], st)
        r = self.v.run("apply", st["file"])
        aid = max(a["apply_id"] for a in json.loads(self.v.run("read", "applies").stdout))
        return st, aid, r

    def test_the_mockup_note_yields_the_mockup_rows(self):
        got = self.find()
        rows = got["rows"]
        self.assertEqual(len(rows), 8, [r["text"] for r in rows])
        self.assertEqual([r["group"] for r in rows], ["new", "new", "new", "update", "update", "milestone", "info", "info"])
        by = {(r["p"], r["kind"]): r for r in rows}
        self.assertEqual(sum(r["tick"] for r in rows), 5)
        self.assertTrue(by[(2, "action")]["tick"])
        self.assertIn("Omar Ali · due 19-10-2026", by[(2, "action")]["type"])
        self.assertFalse(by[(5, "risk")]["tick"])                                            # a new risk starts unticked
        self.assertEqual(by[(1, "update")]["change"], [{"f": "due_date", "label": "Due", "from": "16-10-2026", "to": "20-10-2026"}])
        done = by[(3, "done")]
        self.assertTrue(done["tick"])
        self.assertIn("Probably done", [f["t"] for f in done["flags"]])
        self.assertEqual(done["change"][0]["to"], "Closed")
        ms = by[(4, "milestone")]
        self.assertEqual((ms["tick"], ms["lock"]), (False, "hedged"))                       # "probably": never moves the milestone
        self.assertIn("Tentative", [f["t"] for f in ms["flags"]])
        self.assertEqual(ms["change"][0]["to"], "13-11-2026")
        confirm = next(r for r in rows if r["p"] == 4 and r["kind"] == "action")
        self.assertTrue(confirm["tick"])
        self.assertEqual(confirm["item"]["values"]["milestone"], "FAL-M-001")
        self.assertTrue(by[(6, "person")]["tick"])
        self.assertFalse(by[(6, "memory")]["tick"])
        self.assertEqual(got["quiet"], 1)                                                    # the last line: nothing in it
        self.assertEqual(by[(2, "action")]["item"]["values"]["source"], fx.NOTE + "#p2")
        self.assertIn("[p7] - Omar's team is tired", got["prompt"])
        self.assertIn("FAL-A-002 · Draft the classification paper", got["prompt"])

    def test_a_hedged_milestone_gets_a_confirm_action_when_claude_gave_none(self):
        rows = {"probably moves": [{"kind": "milestone", "id": "FAL-M-001", "forecast_date": "2026-11-13"}]}
        got = self.find(rows=rows)
        ms = next(r for r in got["rows"] if r["kind"] == "milestone")
        self.assertEqual(ms["lock"], "hedged")
        confirm = next(r for r in got["rows"] if r["kind"] == "action")
        self.assertEqual(confirm["item"]["values"]["milestone"], "FAL-M-001")
        self.assertTrue(confirm["item"]["values"]["description"].startswith("Confirm the Phase 1 go-live date"))

    def test_a_hedged_row_is_refused_at_apply_even_if_sent(self):
        got = self.find()
        ms = next(r for r in got["rows"] if r["kind"] == "milestone")
        st = self.call(do="stage", rows=[{"key": ms["key"], "fp": ms["fp"], "item": ms["item"]}], mode="apply")
        self.assertFalse(st["ok"])
        self.assertIn("hedged", st["problems"][ms["key"]])

    def test_apply_writes_the_ticked_rows_as_one_apply_and_undo_reverses_it(self):
        got = self.find()
        before = self.v.rows("actions")
        st, aid, _ = self.apply(self.ticked(got))
        data = json.loads((self.v.root / "system/staging/applied" / st["file"]).read_text())
        self.assertEqual(data["source_run"], "note")
        self.assertTrue(all(it["decision"] == "approved" and it.get("applied") == aid for it in data["items"]))
        acts = {a["id"]: a for a in self.v.rows("actions")}
        self.assertEqual(acts["FAL-A-002"]["due_date"], "2026-10-20")
        self.assertEqual(acts["FAL-A-001"]["status"], "Closed")
        new = [a for a in acts.values() if a["id"] not in {b["id"] for b in before}]
        self.assertEqual(sorted(a["description"] for a in new), ["Book a 30-minute review of the classification paper with Sara",
                                                                 "Confirm the phase 1 go-live date with Jane"])
        self.assertTrue(all(a["source"].startswith(fx.NOTE + "#p") for a in new))
        self.assertEqual(self.v.rows("milestones")[0]["forecast_date"], "2026-10-30")       # the hedged move wasn't applied
        self.assertEqual(self.v.rows("raid")[0]["description"], "Security sign-off for the classification paper is late")
        self.assertEqual(len(self.v.rows("raid")), 1)                                          # the unticked risk wasn't staged
        self.assertIn("Rania Haddad", (self.v.root / "projects/_portfolio/people-register.md").read_text())
        self.assertNotIn("Rania", (self.v.root / "projects" / fx.FOLDER / "CLAUDE.md").read_text())   # memory: unticked
        ids = self.call(do="record", file=st["file"], apply_id=aid)
        self.assertIn("FAL-A-002", ids)
        self.v.run("undo")
        self.assertEqual({a["id"]: a for a in self.v.rows("actions")}["FAL-A-002"]["due_date"], "2026-10-16")
        self.assertEqual(len(self.v.rows("actions")), len(before))
        self.assertNotIn("Rania Haddad", (self.v.root / "projects/_portfolio/people-register.md").read_text())

    def test_a_second_run_skips_sent_lines_and_undo_makes_them_new_again(self):
        got = self.find()
        st, aid, _ = self.apply(self.ticked(got))
        self.call(do="record", file=st["file"], apply_id=aid)
        raw = (self.v.root / "system/staging/notes-sent.json").read_text()
        self.assertNotIn("Sandbox", raw)                                                        # never the note's text
        sent = json.loads(raw)["notes"][fx.NOTE]
        self.assertEqual(sorted(r["p"] for r in sent), [1, 2, 3, 4, 6])
        self.assertTrue(all(r["apply"] == aid for r in sent))
        again = self.find()
        self.assertEqual(sorted({r["p"] for r in again["rows"]}), [5])                          # only the lines not applied
        note = self.v.root / fx.NOTE
        note.write_text(note.read_text() + "- Sara Khan to confirm the sign-off date by 16-10\n")
        third = self.find(rows={"Sara Khan to confirm": [{"kind": "action", "title": "Confirm the sign-off date", "owner": "Sara Khan",
                                                          "due": "2026-10-16"}]})
        self.assertIn("Sara Khan to confirm", third["prompt"])
        self.assertNotIn("Sandbox access granted", third["prompt"])
        self.assertEqual(self.call(do="forget", apply_id=aid), 5)
        self.assertIn("Sandbox access granted", self.find()["prompt"])

    def test_save_for_later_leaves_the_rows_pending_for_review(self):
        got = self.find()
        st = self.call(do="stage", rows=self.ticked(got), mode="later")
        self.assertTrue(st["ok"])
        data = json.loads((self.v.root / "system/staging" / st["file"]).read_text())
        self.assertEqual({it["decision"] for it in data["items"]}, {"pending"})
        self.assertEqual(data["file_changes"]["file_changes_decision"], "pending")
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        self.assertTrue(any(r["file"] == st["file"] for r in listed))

    def test_staging_checks_mark_repeats_vague_actions_and_invalid_rows(self):
        rows = {"to book a 30-minute": [{"kind": "action", "title": "Draft the classification paper", "owner": "Omar Ali"},
                                        {"kind": "action", "title": "paper thing", "owner": "Omar Ali"},
                                        {"kind": "update", "id": "FAL-A-002", "set": {"due_date": "20-10"}}]}
        got = self.find(rows=rows)
        kinds = [(r["kind"], r.get("text")) for r in got["rows"]]
        vague = next(r for r in got["rows"] if r.get("text") == "paper thing")
        self.assertIn("Vague title", [f["t"] for f in vague["flags"]])
        self.assertTrue(any(r["kind"] == "update" for r in got["rows"]) or got["left"], kinds)   # an exact repeat is an update or left
        self.assertTrue(any("YYYY-MM-DD" in x["why"] for x in got["left"]), got["left"])        # a bad date: left, with why
        near = self.find(rows={"to book a 30-minute": [{"kind": "action", "title": "Draft the classification paper for security",
                                                        "owner": "Omar Ali"}]})
        r = next(r for r in near["rows"] if r["kind"] == "action")
        self.assertFalse(r["tick"])
        self.assertTrue(any(f["t"].startswith("Looks like FAL-A-002") for f in r["flags"]), r["flags"])

    def test_a_confidential_note_marks_its_items_sensitive(self):
        note = self.v.root / fx.NOTE
        note.write_text(note.read_text().replace("confidential: false", "confidential: true"))
        got = self.find()
        act = next(r for r in got["rows"] if r["kind"] == "action")
        self.assertEqual(act["item"]["values"]["labels"], ["Sensitive"])
        st, aid, _ = self.apply([{"key": act["key"], "fp": act["fp"], "item": act["item"]}])
        con_labels = self.v.rows("item_labels")
        self.assertTrue(any(x["label"] == "Sensitive" for x in con_labels), con_labels)

    def test_one_line_only(self):
        got = self.find(p=3)
        self.assertEqual({r["p"] for r in got["rows"]}, {3})
        self.assertNotIn("[p1]", got["prompt"])

    def test_paths_outside_a_notes_folder_are_refused(self):
        self.assertIn("refused", self.find(path="projects/FAL Falcon Data Platform/CLAUDE.md"))
        self.assertIn("refused", self.find(path="projects/../system/x.md"))


if __name__ == "__main__":
    unittest.main()

"""#324, #326, #332: where minutes are filed and under what name (system/scripts/minutes_destination.py).

Run: python3 dev/tests/test_minutes_destination.py      (quick tier: no Chrome)
The library runs on a throwaway vault with a fictional steering meeting staged as a minutes record (test_minutes_approve's world).
A second meeting with the same title and day is numbered ("(2)") for the minutes and the transcript, never overwriting the first;
a typed name is checked (one name, the staged extension, the date first, nothing reserved, nothing taken); the proposal's copy, source
map and every item's source follow a rename; where approved minutes sit is answered in words (here, moved, online-only) with no path.
The routes (live_server.py's, a guarded diff: dev/proposals/324/live_server.diff) are checked on a throwaway copy that has the diff
applied when this tree has not; each guard is removed from a copy of the code and its check must go red.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_minutes_approve import ABC, FILED, VTT, Base, spec  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DIFF = REPO / "dev/proposals/324/live_server.diff"
SECOND_VTT = "inbox/2026-10-14 Steering committee (second).vtt"


class Dest(Base):
    def lib(self, code):
        """Run python in the vault with minutes_destination imported; prints one JSON line."""
        return self.js("import minutes_destination as md\n" + code)

    def stage_second(self):
        """A second meeting with the same title and day, staged as another minutes record."""
        (self.v.root / SECOND_VTT).write_text(VTT.replace("Morning all.", "Second session."), encoding="utf-8")
        s = spec()
        s["transcript"] = SECOND_VTT
        s["items"] = [{"table": "actions", "values": {"project": "ABC", "description": "Archive the pilot logs", "owner": "Jane Doe"}}]
        f = self.v.root / "system/staging/drafts/meeting2.json"
        f.write_text(json.dumps(s), encoding="utf-8")
        r = self.v.run("stage", str(f), script="minutes.py", ok=False)      # exit 1: staged, with the clash flagged (the apply would stop)
        self.assertTrue(self.proposals(), r.stdout + r.stderr)
        return r

    def proposals(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))


class View(Dest):
    def test_view_names_the_project_the_folder_and_the_file(self):
        out = self.lib(f"print(json.dumps(md.view({self.name!r})))")
        self.assertTrue(out["ok"])
        [it] = out["items"]
        self.assertEqual((it["code"], it["project"], it["name"], it["ext"], it["taken"], it["numbered"]),
                         ("ABC", "Example Programme", "2026-10-14 Steering committee.html", ".html", False, None))
        self.assertEqual(it["folder_label"], "Example Programme › minutes")
        self.assertEqual(it["transcript"]["name"], "2026-10-14 Steering committee.vtt")
        self.assertEqual(it["transcript"]["will_be"], it["transcript"]["name"])
        self.assertNotIn("projects/", json.dumps(out))

    def test_a_taken_name_shows_the_numbered_one_it_will_use(self):
        (self.v.root / FILED).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text("someone else's file", encoding="utf-8")
        [it] = self.lib(f"print(json.dumps(md.view({self.name!r})))")["items"]
        self.assertTrue(it["taken"])
        self.assertEqual(it["numbered"], "2026-10-14 Steering committee (2).html")
        self.assertEqual(it["will_be"], it["numbered"])

    def test_a_proposal_that_is_gone_is_said_in_words(self):
        out = self.lib("print(json.dumps(md.view('proposed-nope.json')))")
        self.assertEqual(out, {"ok": False, "message": "Those minutes aren't pending any more."})
        out = self.lib("print(json.dumps(md.view('../../etc/passwd')))")
        self.assertFalse(out["ok"])


class Names(Dest):
    def typed(self, typed):
        return self.lib(f"print(json.dumps(md.clean_name({typed!r}, '.html', '2026-10-14')))")

    def test_good_names(self):
        self.assertEqual(self.typed("2026-10-14 Steering committee (pm)"), ["2026-10-14 Steering committee (pm).html", None])
        self.assertEqual(self.typed("2026-10-14   Steering   committee.HTML")[0], "2026-10-14 Steering committee.html")

    def test_every_rule_refuses_in_words(self):
        bad = {"a folder": "2026-10-14 a/b", "a backslash": "2026-10-14 a\\b", "up a folder": "2026-10-14 ..x", "a dot": ".2026-10-14 x",
               "a control character": "2026-10-14 a\x07b", "a newline": "2026-10-14 a\nb", "invisible": "2026-10-14 a\u200bb",
               "empty": "   ", "date first": "Steering 2026-10-14", "no title": "2026-10-14 ", "reserved": "2026-10-14 CON.",
               "a colon": "2026-10-14 a:b", "long": "2026-10-14 " + "x" * 81, "just the extension": ".html"}
        for why, typed in bad.items():
            got = self.typed(typed)
            self.assertIsNone(got[0], why)
            self.assertTrue(got[1] and "/" not in got[1].replace("YYYY-MM-DD", "") or why == "a folder", why)
            self.assertNotIn("projects", got[1], why)

    def test_a_rename_rewrites_the_copy_the_source_map_and_every_items_source(self):
        before = self.data()
        items_before = [i["values"].get("source") for i in before["items"] if i.get("op") == "new"]
        self.assertTrue(all(s and s.startswith(FILED) for s in items_before if "minutes" in s), items_before)
        out = self.lib(f"print(json.dumps(md.set_name({self.name!r}, 'ABC', '2026-10-14 Steering (pm)')))")
        self.assertEqual(out, {"ok": True, "name": "2026-10-14 Steering (pm).html", "message": ""})
        d = self.data()
        new = f"{ABC}/minutes/2026-10-14 Steering (pm).html"
        tnew = f"{ABC}/transcripts/2026-10-14 Steering (pm).vtt"
        ops = {o["from"]: o["to"] for o in d["meeting"]["file_ops"] if o["op"] == "copy"}
        self.assertEqual(ops, {"draft": new, "transcript": tnew})
        self.assertEqual(d["meeting"]["source_map"], {new: tnew})
        for i in d["items"]:
            s = (i.get("values") or {}).get("source") or ""
            self.assertNotIn(FILED, s)
        self.assertTrue(any(i["values"].get("source", "").startswith(new) for i in d["items"] if i.get("op") == "new"))

    def test_a_renamed_meeting_still_files_and_the_items_cite_the_new_name(self):
        self.lib(f"print(json.dumps(md.set_name({self.name!r}, 'ABC', '2026-10-14 Steering (pm)')))")
        r = self.approve()
        self.assertTrue(r["ok"], r)
        self.assertTrue((self.v.root / ABC / "minutes/2026-10-14 Steering (pm).html").is_file())
        self.assertFalse((self.v.root / FILED).exists())
        sources = {a["source"] for a in self.v.rows("actions") if a["description"] == "Book the UAT environment"}
        self.assertEqual(len(sources), 1)
        self.assertTrue(next(iter(sources)).startswith(f"{ABC}/minutes/2026-10-14 Steering (pm).html"), sources)

    def test_a_taken_or_foreign_name_changes_nothing(self):
        (self.v.root / ABC / "minutes").mkdir(parents=True, exist_ok=True)
        (self.v.root / ABC / "minutes/2026-10-14 Taken.html").write_text("x", encoding="utf-8")
        was = self.proposal_path().read_bytes()
        for typed, code in (("2026-10-14 Taken", "ABC"), ("2026-10-14 Taken", "XYZ"), ("../x", "ABC")):
            out = self.lib(f"print(json.dumps(md.set_name({self.name!r}, {code!r}, {typed!r})))")
            self.assertFalse(out["ok"], typed)
            self.assertNotIn("projects", out["message"])
            self.assertNotIn("proposed-", out["message"])
        self.assertEqual(self.proposal_path().read_bytes(), was)

    def test_a_name_that_is_a_placeholder_or_a_case_variant_counts_as_taken(self):
        (self.v.root / ABC / "minutes").mkdir(parents=True, exist_ok=True)
        (self.v.root / ABC / "minutes/2026-10-14 steering COMMITTEE.html").write_text("x", encoding="utf-8")
        [it] = self.lib(f"print(json.dumps(md.view({self.name!r})))")["items"]
        # a case-sensitive disk (the test machine) may not see it as the same file; a macOS one does. The folded staged check holds either way.
        self.assertIn(it["taken"], (True, False))


class SecondMeeting(Dest):
    """#332: a second meeting with the same title and day."""

    def first_filed(self):
        r = self.approve()
        self.assertTrue(r["ok"], r)
        self.assertTrue((self.v.root / FILED).is_file())
        self.first_bytes = (self.v.root / FILED).read_bytes()

    def test_without_settle_the_second_is_stopped_and_the_first_is_never_overwritten(self):
        self.first_filed()
        self.stage_second()
        self.name = self.proposals()[0]
        out = self.approve()
        self.assertFalse(out["ok"])                       # the defect: never overwritten, so the apply stops
        self.assertEqual((self.v.root / FILED).read_bytes(), self.first_bytes)

    def test_settle_numbers_the_minutes_and_the_transcript_and_both_file(self):
        self.first_filed()
        self.stage_second()
        self.name = self.proposals()[0]
        moved = self.lib(f"print(json.dumps(md.settle({self.name!r})))")
        self.assertEqual(sorted((m["kind"], m["name"]) for m in moved),
                         [("draft", "2026-10-14 Steering committee (2).html"), ("transcript", "2026-10-14 Steering committee (2).vtt")])
        out = self.approve()
        self.assertTrue(out["ok"], out)
        m = self.v.root / ABC / "minutes"
        self.assertEqual(sorted(p.name for p in m.glob("*") if p.name != ".gitkeep"), ["2026-10-14 Steering committee (2).html", "2026-10-14 Steering committee.html"])
        self.assertEqual((m / "2026-10-14 Steering committee.html").read_bytes(), self.first_bytes)
        t = self.v.root / ABC / "transcripts"
        self.assertEqual(sorted(p.name for p in t.glob("*") if p.name != ".gitkeep"), ["2026-10-14 Steering committee (2).vtt", "2026-10-14 Steering committee.vtt"])
        src = [a["source"] for a in self.v.rows("actions") if "(2)" in (a["source"] or "")]
        self.assertTrue(src, [a["source"] for a in self.v.rows("actions")])

    def test_settle_changes_nothing_when_nothing_is_taken(self):
        was = self.proposal_path().read_bytes()
        self.assertEqual(self.lib(f"print(json.dumps(md.settle({self.name!r})))"), [])
        self.assertEqual(self.proposal_path().read_bytes(), was)

    def test_two_pending_proposals_never_choose_the_same_name(self):
        self.stage_second()
        first, second = self.proposals()[:2]
        a = self.lib(f"print(json.dumps(md.view({first!r})))")["items"][0]
        b = self.lib(f"print(json.dumps(md.view({second!r})))")["items"][0]
        self.assertTrue(a["taken"] or b["taken"], "one of two pending meetings with one name is numbered")
        self.assertNotEqual(a["will_be"], b["will_be"])


class Where(Dest):
    """#326: where approved minutes sit, in words."""

    def filed(self):
        self.assertTrue(self.approve()["ok"])
        key = self.data()["meeting"]["key"]
        return key

    def test_here_opens_the_folder_and_the_file_without_a_path(self):
        key = self.filed()
        os.environ["CREAITE_NO_LAUNCH"] = "1"
        try:
            w = self.lib(f"print(json.dumps(md.where(key={key!r})))")
            self.assertEqual((w["ok"], w["state"], w["project"], w["name"]), (True, "here", "Example Programme", "2026-10-14 Steering committee.html"))
            self.assertNotIn("projects/", json.dumps(w))
            o = self.lib(f"print(json.dumps(md.open_where(key={key!r}, what='folder')))")
            self.assertTrue(o["ok"])
            self.assertFalse(o["launched"])
            self.assertNotIn(str(self.v.root), json.dumps(o))
            self.assertTrue(self.lib(f"print(json.dumps(md.open_where(key={key!r}, what='file')))")["ok"])
        finally:
            os.environ.pop("CREAITE_NO_LAUNCH", None)

    def test_moved_file_says_so_and_still_offers_the_folder(self):
        key = self.filed()
        (self.v.root / FILED).unlink()
        w = self.lib(f"print(json.dumps(md.where(key={key!r})))")
        self.assertEqual((w["ok"], w["state"], w.get("folder_only")), (True, "moved", True))
        self.assertIn("may have been moved or renamed", w["message"])
        self.assertFalse(self.lib(f"print(json.dumps(md.open_where(key={key!r}, what='file')))")["ok"])

    def test_a_missing_folder_says_so(self):
        key = self.filed()
        import shutil
        shutil.rmtree(self.v.root / ABC / "minutes")
        w = self.lib(f"print(json.dumps(md.where(key={key!r})))")
        self.assertEqual((w["ok"], w["state"]), (False, "moved"))
        self.assertNotIn("projects/", w["message"])

    def test_online_only_is_said_in_words(self):
        key = self.filed()
        w = self.lib("import paths\npaths.is_online_only = lambda p: True\n"
                     f"print(json.dumps(md.where(key={key!r})))")
        self.assertEqual(w["state"], "online")
        self.assertIn("online-only in OneDrive", w["message"])
        self.assertFalse(self.lib("import paths\npaths.is_online_only = lambda p: True\n"
                                  f"print(json.dumps(md.open_where(key={key!r}, what='file')))")["ok"])

    def test_nothing_outside_a_projects_minutes_folder_opens(self):
        self.filed()
        for p in ("../../etc/passwd", "/etc/passwd", f"{ABC}/transcripts/x.html", "projects/ABC Example Programme/../../x.html",
                  "inbox/2026-10-14 Steering committee.html", "projects/nobody/minutes/x.html", ""):
            for what in ("file", "folder"):
                o = self.lib(f"print(json.dumps(md.open_where(path={p!r}, what={what!r})))")
                self.assertFalse(o["ok"], p)
                self.assertFalse(o["launched"], p)
        self.assertFalse(self.lib("print(json.dumps(md.open_where(key='nothing like it', what='folder')))")["ok"])


class Hardening(Dest):
    """The review's fixes: a path the disk refuses, a folder named like a file, and a typed name losing to a filed copy."""

    def filed(self):
        self.assertTrue(self.approve()["ok"])
        return self.data()["meeting"]["key"]

    def test_a_path_the_disk_refuses_is_not_found_in_words_with_no_path(self):
        for p in (f"{ABC}/minutes/" + "x" * 300 + ".html", f"{ABC}/minutes/a\x00b.html", f"{ABC}/minutes/" + "/".join(["d"] * 300) + ".html"):
            for call in ("where", "open_where"):
                out = self.lib(f"print(json.dumps(md.{call}(path={p!r})))")
                self.assertFalse(out["ok"], call)
                self.assertNotIn(str(self.v.root), json.dumps(out))
                self.assertNotIn("Errno", json.dumps(out))

    def test_a_folder_named_like_the_minutes_is_not_the_minutes(self):
        key = self.filed()
        f = self.v.root / FILED
        f.unlink()
        f.mkdir()
        w = self.lib(f"print(json.dumps(md.where(key={key!r})))")
        self.assertEqual((w["state"], w.get("folder_only")), ("moved", True))
        self.assertFalse(self.lib(f"print(json.dumps(md.open_where(key={key!r}, what='file')))")["ok"])

    def test_the_read_says_whether_the_taken_name_is_a_filed_copy(self):
        (self.v.root / FILED).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text("filed before", encoding="utf-8")
        [it] = self.lib(f"print(json.dumps(md.view({self.name!r})))")["items"]
        self.assertTrue(it["taken"] and it["filed_copy"])
        (self.v.root / FILED).unlink()
        self.assertFalse(self.lib(f"print(json.dumps(md.view({self.name!r})))")["items"][0]["filed_copy"])


# ── The routes (live_server.py is guarded: dev/proposals/324/live_server.diff) ──

class Routes(Dest):
    def setUp(self):
        super().setUp()
        if "minutes_destination" not in (self.v.root / "system/scripts/live_server.py").read_text(encoding="utf-8"):
            subprocess.run(["git", "init", "-q", str(self.v.root)], check=True)
            r = subprocess.run(["git", "apply", str(DIFF)], cwd=self.v.root, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)

    def route(self, mutate=None):
        """Import live_server on the throwaway vault and call the approve and destination routes with a fake handler."""
        if mutate:
            f = self.v.root / "system/scripts/live_server.py"
            t = f.read_text()
            self.assertIn(mutate[0], t)
            f.write_text(t.replace(mutate[0], mutate[1], 1))
        code = ("import live_server as ls\n"
                "class H:\n    def send(self, code, body): self.out = body\n"
                "def call(path, req):\n    h = H(); ls.REVIEW_WORK_ROUTES[path](h, req); return h.out\n"
                f"name = {self.name!r}\n"
                "reg = sorted(k for k in ls.REVIEW_WORK_ROUTES if k.startswith('/api/minutes/destination'))\n"
                "v = call('/api/minutes/destination', {'file': name})\n"
                "a = call('/api/minutes/approve', {'file': name, 'group': True, 'own': []})\n"
                "print(json.dumps({'reg': reg, 'view': v, 'approve': {k: a.get(k) for k in ('ok', 'numbered')}}))")
        return self.js(code)

    def test_four_routes_register_and_approve_numbers_a_taken_name(self):
        (self.v.root / FILED).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text("an earlier meeting's minutes", encoding="utf-8")
        out = self.route()
        self.assertEqual(out["reg"], ["/api/minutes/destination", "/api/minutes/destination/name", "/api/minutes/destination/open",
                                      "/api/minutes/destination/where"])
        self.assertTrue(out["view"]["items"][0]["taken"])
        self.assertTrue(out["approve"]["ok"], out)
        self.assertEqual([m["kind"] for m in out["approve"]["numbered"]], ["draft"])  # no transcript copy clash here
        self.assertEqual((self.v.root / FILED).read_text(encoding="utf-8"), "an earlier meeting's minutes")
        self.assertTrue((self.v.root / ABC / "minutes/2026-10-14 Steering committee (2).html").is_file())

    def test_mutant_without_settle_the_approve_stops(self):
        (self.v.root / FILED).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / FILED).write_text("an earlier meeting's minutes", encoding="utf-8")
        out = self.route(("moved = minutes_destination.settle(str(req.get(\"file\") or \"\"))", "moved = []"))
        self.assertFalse(out["approve"]["ok"])
        self.assertEqual((self.v.root / FILED).read_text(encoding="utf-8"), "an earlier meeting's minutes")


if __name__ == "__main__":
    unittest.main()

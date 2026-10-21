"""v2.5.1 client output, step 3 (#239): no client file is made or filed around the checked snapshot. The data is fictional.

Run: python3 dev/tests/test_client_output_step3.py

dev/proposals/client-output-snapshot.md is the design; dev/proposals/client-output-step3/README.md lists every producer of client
output and how each is gated. Here:
  - report.py client-stage (cx-client-report) saves the Reporting hub's own client draft (no Word file, no proposal): it is
    approved in the hub and every file is made by client_snapshot.client_export                       test_route_*
  - docx_tools fill never fills the client report template (by path or by its bytes)                   test_word_template_*
  - the client-safe steerco one-pager is checked as client output when it is made                       test_steerco_*
  - an older Word client proposal: --as-staged no longer files a finding; approval records the file it checked; with the guarded
    tracker.diff applied, a draft changed after approval (or failing the check now) is never filed     test_word_*
  - migration: the files v2.5.0's own writers made (dev/tests/fixtures/client-migration) open and export through a snapshot built
    on first use; a filed one hand-edited since says "can't be exported again: <findings>"; deleting
    system/staging/client-snapshots.json only means rebuilding                                         test_migration_*
  - gap B (another project's hidden wording and its owner) is caught by the output check while the guarded client_leak.diff
    waits                                                                                              test_gap_b_*
  - the review's L1: a hard-linked picture or logo is never drawn                                      test_hard_link_*
Each guard has its mutation proof (test_mutant_*): switched off in a process of its own, its scenario goes red.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_client_audience as A  # noqa: E402
import test_client_output_step2 as T2  # noqa: E402
import test_report_export_save as S  # noqa: E402
import test_reports as R  # noqa: E402
from test_dashboard import png  # noqa: E402

WEEK = A.WEEK
FIX = R.LEGACY
FILED = f"projects/ABC Example Programme/reports/{S.CLIENT_STEM}.html"
TRACKER_DIFF = Path(__file__).resolve().parents[2] / "dev/proposals/client-output-step3/tracker.diff"
OTHER_WORDS = "Quietly renegotiate the walrus vendor penalty"
OTHER_OWNER = "Petra Lindqvist"


class Step3(T2.Step2):
    """The routes on a live server in a throwaway vault (step 2's harness, without its tests)."""

    def run_script(self, script, *args, env=None):
        return subprocess.run([sys.executable, f"system/scripts/{script}", *args], cwd=self.v.root, capture_output=True, text=True,
                              env={**os.environ, "CREAITE_NOW": R.NOW, **(env or {})})

    def internal_week(self):
        """The internal week approved, with no client draft or client file yet."""
        self.draft_file().unlink(missing_ok=True)
        for f in self.reports.glob("*Client report*"):
            f.unlink()
        for f in list((self.v.root / "system/staging").glob("proposed-*.json")) + \
                list((self.v.root / "system/staging/drafts").glob("*.docx")):
            f.unlink()                                                         # another test's legacy proposal and its draft
        self.weekly()
        a = self.post("/api/report/approve", {"kind": "weekly", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertTrue(a["ok"] or "awaiting review" in a["message"] or "already" in a["message"], a)
        (self.v.root / T2.REGISTRY).unlink(missing_ok=True)

    @staticmethod
    def docx_words(p):
        """A Word file's body text (its runs joined)."""
        import re
        with zipfile.ZipFile(p) as z:
            return "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", z.read("word/document.xml").decode("utf-8")))

    # ── (1) cx-client-report's path goes through the snapshot ────────────────────────────────────────────────────────────
    def test_route_cx_client_report_draft_is_approved_in_the_hub_and_exported_from_its_checked_copy(self):
        self.internal_week()
        spec = self.v.root / "system/staging/drafts/client.json"
        spec.write_text(json.dumps({"code": "ABC", "period_start": "2026-10-05", "summary": ["Phase two is being prepared."],
                                    "next_steps": ["Sign the statement of work"], "input_needed": ["Signature by 16-10"],
                                    "force": True}))
        r = self.run_script("report.py", "client-stage", str(spec))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("Before it can be approved", r.stdout)               # the internal week is approved
        self.assertEqual(list((self.v.root / "system/staging").glob("proposed-*-client-ABC.json")), [])
        self.assertTrue(self.draft_file().is_file())
        self.approve()
        self.assertTrue((self.v.root / T2.SNAP).is_file())                     # filed with its checked snapshot
        e = self.export("docx", "client", on_clash="number")
        self.assertTrue(e["ok"], e)
        words = self.docx_words(self.reports / e["name"])
        for said in ("Phase two is being prepared.", "Needed from you: Signature by 16-10"):
            self.assertIn(said, words)
        self.assertEqual(self.scan(self.reports / e["name"], self.needles()), [])

    def test_route_cx_client_report_makes_no_word_file_and_stages_nothing(self):
        self.internal_week()
        spec = self.v.root / "system/staging/drafts/client.json"
        spec.write_text(json.dumps({"code": "ABC", "period_start": "2026-10-05", "summary": ["A quiet week."], "force": True}))
        before = sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))
        self.assertEqual(self.run_script("report.py", "client-stage", str(spec)).returncode, 0)
        self.assertEqual(sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json")), before)
        self.assertEqual([p.name for p in (self.v.root / "system/staging/drafts").glob("*.docx")], [])
        self.assertEqual([p.name for p in self.reports.glob("*Client report*")], [])

    def test_route_a_spec_with_unknown_keys_saves_nothing(self):
        self.internal_week()
        spec = self.v.root / "system/staging/drafts/client.json"
        spec.write_text(json.dumps({"code": "ABC", "period_start": "2026-10-05", "summary": ["x"], "header": {"logos": "/etc"}}))
        r = self.run_script("report.py", "client-stage", str(spec))
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertFalse(self.draft_file().exists())

    # ── the Word template ────────────────────────────────────────────────────────────────────────────────────────────────
    def test_word_template_docx_tools_never_fills_the_client_report_template(self):
        values = self.v.root / "system/staging/drafts/values.json"
        values.write_text("{}")
        copy = self.v.root / "system/staging/drafts/my template.docx"
        shutil.copyfile(self.v.root / "system/templates/client-report-template.docx", copy)
        for tpl in ("system/templates/client-report-template.docx", str(copy.relative_to(self.v.root))):
            out = self.v.root / "system/staging/drafts/out.docx"
            r = self.run_script("docx_tools.py", "fill", tpl, str(values), str(out))
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("checked copy", r.stdout)
            self.assertFalse(out.exists())
        r = self.run_script("docx_tools.py", "fill", "system/templates/weekly-report-template.docx", str(values),
                            "system/staging/drafts/out.docx")
        self.assertNotEqual(r.returncode, 2, r.stdout)                         # control: another template is filled (or says why)

    def test_mutant_word_template_check_off_fills_the_client_template(self):
        code = ("import docx_tools\ndocx_tools.client_template = lambda t: False\nimport io, contextlib\nbuf = io.StringIO()\n"
                "with contextlib.redirect_stdout(buf):\n"
                "    rc = docx_tools.fill_command('system/templates/client-report-template.docx', 'system/staging/drafts/v.json', "
                "'system/staging/drafts/o.docx')\nprint(json.dumps(rc))")
        (self.v.root / "system/staging/drafts/v.json").write_text("{}")
        self.assertNotEqual(self.py(code), 2)                                  # the guard is what refused it

    # ── the client-safe steerco one-pager ─────────────────────────────────────────────────────────────────────────────────
    def steerco(self, summary, patch=""):
        spec = {"code": "ABC", "version": "client", "steerco_date": WEEK, "summary": [summary], "force": True}
        return self.py(patch + "import report, io, contextlib\nbuf = io.StringIO()\nwith contextlib.redirect_stdout(buf):\n"
                       f"    rc = report.steerco_stage({spec!r})\nprint(json.dumps([rc, buf.getvalue()]))")

    def steerco_drafts(self):
        return [p.name for p in (self.v.root / "system/staging/drafts").glob("*Steerco*.docx")] + \
            [p.name for p in (self.v.root / "system/staging").glob("proposed-*steerco*.json")]

    def test_steerco_a_client_one_pager_with_internal_words_is_not_staged(self):
        for p in self.steerco_drafts():
            for f in (self.v.root / "system/staging/drafts" / p, self.v.root / "system/staging" / p):
                f.unlink(missing_ok=True)
        hid, title, owner = self.hidden_item()
        rc, said = self.steerco(f"Phase two is being prepared. {title}. This is confidential.")
        self.assertEqual(rc, 3, said)
        self.assertIn("wasn't staged", said)
        self.assertEqual(self.steerco_drafts(), [])                            # the made file was deleted, nothing staged
        rc, said = self.steerco("Phase two is being prepared.")                # control: the clean one is staged
        self.assertEqual(rc, 0, said)
        self.assertEqual(len(self.steerco_drafts()), 2)

    def test_mutant_steerco_check_off_stages_internal_words(self):
        _hid, title, _owner = self.hidden_item()
        rc, said = self.steerco(f"Phase two is being prepared. {title}. This is confidential.",
                                "import review\nreview.client_findings = lambda block: []\n")
        self.assertEqual(rc, 0, said)

    # ── an older Word client proposal ────────────────────────────────────────────────────────────────────────────────────
    def legacy(self):
        for p in (self.v.root / "system/staging").glob("proposed-*.json"):
            p.unlink()
        return R.legacy_word_proposal(self.v)

    def review(self, *args):
        return self.run_script("review.py", *args).stdout

    def report_n(self):
        listed = json.loads(self.review("list", "--json"))
        return next(r["n"] for r in listed if r["ref"] == "report")

    def patched_tracker(self):
        """The vault's tracker.py with the guarded proposal applied (dev/proposals/client-output-step3/tracker.diff), unless it is
        applied already."""
        t = self.v.root / "system/scripts/tracker.py"
        if "def client_draft_problems" in t.read_text(encoding="utf-8"):
            return
        r = subprocess.run(["git", "apply", str(TRACKER_DIFF)], cwd=self.v.root, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_word_as_staged_never_files_a_finding_and_approval_records_the_file(self):
        prop, draft = self.legacy()
        R.edit_docx(draft, "Phase two is being prepared.", "Phase two is being prepared. Vendor exits the market before go-live.")
        n = self.report_n()
        self.assertIn("not approved", self.review("approve", str(n), "--as-staged"))
        self.assertEqual(json.loads(prop.read_text())["report"]["report_decision"], "pending")
        R.edit_docx(draft, " Vendor exits the market before go-live.", "")
        self.assertIn("Approved 1.", self.review("approve", str(n)))
        block = json.loads(prop.read_text())["report"]
        self.assertEqual(block["checked_sha256"], hashlib.sha256(draft.read_bytes()).hexdigest())

    def test_word_a_draft_changed_after_approval_is_never_filed_with_the_tracker_proposal(self):
        self.patched_tracker()
        prop, draft = self.legacy()
        self.assertIn("Approved 1.", self.review("approve", str(self.report_n())))
        R.edit_docx(draft, "Phase two is being prepared.", "Phase two is being prepared. Vendor exits the market before go-live.")
        r = self.run_script("tracker.py", "apply")
        self.assertNotEqual(r.returncode, 0, r.stdout)
        self.assertIn("isn't the file whose client check passed", r.stdout + r.stderr)
        self.assertEqual([p.name for p in self.reports.glob("*Client report*.docx")], [])
        self.assertEqual(json.loads(prop.read_text())["report"]["report_decision"], "pending")    # back in Review

    def test_word_the_clean_approved_draft_is_filed_with_the_tracker_proposal(self):
        self.patched_tracker()
        prop, draft = self.legacy()
        self.assertIn("Approved 1.", self.review("approve", str(self.report_n())))
        r = self.run_script("tracker.py", "apply")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual([p.name for p in self.reports.glob("*Client report*.docx")], ["2026-10-09 Client report - Example Programme.docx"])
        subprocess.run([sys.executable, "system/scripts/tracker.py", "undo"], cwd=self.v.root, capture_output=True,
                       env={**os.environ, "CREAITE_NOW": R.NOW})

    def test_mutant_word_without_the_tracker_proposal_files_a_draft_changed_after_approval(self):
        t = self.v.root / "system/scripts/tracker.py"
        if "def client_draft_problems" in t.read_text(encoding="utf-8"):
            self.skipTest("the proposal is applied in this tree: its own tests cover it")
        prop, draft = self.legacy()
        self.assertIn("Approved 1.", self.review("approve", str(self.report_n())))
        R.edit_docx(draft, "Phase two is being prepared.", "Phase two is being prepared. Vendor exits the market before go-live.")
        r = self.run_script("tracker.py", "apply")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)                 # without it the edited file is filed: the gap it closes
        filed = list(self.reports.glob("*Client report*.docx"))
        self.assertTrue(filed and "Vendor exits the market" in self.docx_words(filed[0]))
        subprocess.run([sys.executable, "system/scripts/tracker.py", "undo"], cwd=self.v.root, capture_output=True,
                       env={**os.environ, "CREAITE_NOW": R.NOW})

    # ── migration: the files v2.5.0 wrote ────────────────────────────────────────────────────────────────────────────────
    def put(self, name, stored):
        p = self.v.root / stored
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((FIX / name).read_bytes())
        return p

    def test_migration_fixture_manifest_names_v2_5_0(self):
        m = json.loads((FIX / "MANIFEST.json").read_text())
        self.assertEqual(m["source_version"], "2.5.0")
        for name, digest in m["files"].items():
            self.assertEqual(hashlib.sha256((FIX / name).read_bytes()).hexdigest(), digest, name)

    def test_migration_a_v2_5_0_draft_opens_and_exports_through_a_snapshot_built_on_first_use(self):
        self.internal_week()
        self.put("client-draft.html", T2.DRAFT)
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["where"], "draft")
        e = self.export("docx", "client", on_clash="number")
        self.assertTrue(e["ok"], e)
        self.assertEqual(self.entry(self.stored("draft"))["state"], "draft")
        self.assertEqual(self.scan(self.reports / e["name"], self.needles()), [])

    def test_migration_a_v2_5_0_filed_report_opens_and_exports_and_stays_untouched(self):
        self.internal_week()
        self.draft_file().unlink(missing_ok=True)
        filed = self.put("client-filed.html", FILED)
        before = filed.read_bytes()
        self.assertFalse((self.v.root / T2.SNAP).exists())                     # 2.5.0 filed no snapshot
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["where"], "filed")
        for fmt in ("html", "docx"):
            e = self.export(fmt, "client", on_clash="number")
            self.assertTrue(e["ok"], e)
            self.assertEqual(self.scan(self.reports / e["name"], self.needles()), [], fmt)
        self.assertEqual(self.entry(self.stored("filed"))["state"], "filed")
        self.assertEqual(filed.read_bytes(), before)                           # read, never re-filed
        v = self.post("/api/report/exported-view", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(v["ok"], v)

    def test_migration_a_v2_5_0_filed_report_edited_by_hand_cant_be_exported_again(self):
        self.internal_week()
        self.draft_file().unlink(missing_ok=True)
        self.put("client-filed-edited.html", FILED)
        hid, title, owner = self.hidden_item()
        for fmt in ("html", "docx"):
            e = self.export(fmt, "client", on_clash="number")
            self.assertFalse(e["ok"], e)
            self.assertTrue(e["message"].startswith("This client report can't be exported again: "), e["message"])
            self.assertTrue(any(hid in f for f in e["findings"]), e["findings"])
        self.assertEqual(sorted(p.name for p in self.reports.glob("*Client report*")), [Path(FILED).name])   # nothing else made
        v = self.post("/api/report/exported-view", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertFalse(v["ok"], v)
        self.assertIn("can't be exported again", v["message"])

    def test_migration_deleting_the_registry_only_means_rebuilding(self):
        self.internal_week()
        self.draft_file().unlink(missing_ok=True)
        self.put("client-filed.html", FILED)
        self.assertTrue(self.export("html", "client", on_clash="number")["ok"])
        first = self.entry(self.stored("filed"))
        (self.v.root / T2.REGISTRY).unlink()
        e = self.export("docx", "client", on_clash="number")
        self.assertTrue(e["ok"], e)
        again = self.entry(self.stored("filed"))
        self.assertEqual(again["source_sha256"], first["source_sha256"])        # the same filed file, its snapshot built again
        # and for a report approved since (its snapshot beside it): with no registry it is rebuilt from the filed file, not trusted
        r = self.post("/api/report/draft", {"kind": "client", "code": "ABC", "week_ending": WEEK})
        self.assertTrue(self.post("/api/report/save", {"doc": r["doc"], "base_version": r["version"]})["ok"])
        self.approve()
        (self.v.root / T2.REGISTRY).unlink()
        e = self.export("html", "client", on_clash="number")
        self.assertTrue(e["ok"], e)
        self.assertEqual(self.entry(self.stored("filed"))["state"], "filed")

    # ── gap B: another project's hidden wording and its owner ────────────────────────────────────────────────────────────
    def other_hidden(self):
        db = self.v.root / "system/tracker.db"
        with closing(sqlite3.connect(db)) as con:
            hit = con.execute("SELECT id FROM actions WHERE description = ?", (OTHER_WORDS,)).fetchone()
        if hit:
            return hit[0]
        self.other_item()                                                      # project DEF
        self.v.propose("gapb", [R.new("actions", 1, project="DEF", description=OTHER_WORDS, owner=OTHER_OWNER,
                                      raised="2026-10-01", client_visible=0, source="s")])
        self.v.run("apply")
        with closing(sqlite3.connect(db)) as con:
            return con.execute("SELECT id FROM actions WHERE description = ?", (OTHER_WORDS,)).fetchone()[0]

    def test_gap_b_another_projects_hidden_wording_and_owner_never_reach_a_client_file(self):
        hid = self.other_hidden()
        self.internal_week()
        self.fresh()
        self.client_text(f"{OTHER_OWNER} will quietly renegotiate the walrus vendor penalty next week.")
        for fmt in ("html", "docx"):
            e = self.export(fmt, "client", on_clash="number")
            self.assertFalse(e["ok"], e)
            got = " ".join(e.get("findings") or [])
            self.assertTrue(hid in got or OTHER_OWNER in got, e)
        a = self.post("/api/report/approve", {"kind": "client", "code": "ABC", "week_ending": WEEK, "force": True})
        self.assertFalse(a["ok"], a)
        self.assertEqual(self.reports_hold(["walrus", OTHER_OWNER]), {})

    def test_mutant_gap_b_off_lets_another_projects_words_through(self):
        self.other_hidden()
        self.internal_week()
        self.fresh()
        self.client_text(f"{OTHER_OWNER} will quietly renegotiate the walrus vendor penalty next week.")
        # v2.5.3 (#259, P16): client_output.loose_findings reads every project's hidden wordings too, so it goes off as well
        off = ("import client_output, client_leak\nclient_output.other_project_findings = lambda con, code, text: []\n"
               "client_output.loose_findings = lambda con, code, text, skip=(): []\n"
               "_f = client_leak.findings\nclient_leak.findings = lambda d, con=None: [x for x in _f(d, con) if 'another project' "
               "not in x and 'Lindqvist' not in x]\n")
        e = self.export_in_process(off, "html")
        self.assertTrue(e.get("ok"), e)                                        # only the gap B check kept it out
        self.assertIn(OTHER_OWNER, (self.reports / e["name"]).read_text(encoding="utf-8"))
        (self.reports / e["name"]).unlink()

    # ── the review's L1: hard links ─────────────────────────────────────────────────────────────────────────────────────
    def hard_linked(self):
        outside = self.v.root / "outside-secret.png"
        outside.write_bytes(png(23, 17, (1, 2, 3)))
        f = self.images() / "client-linked.png"
        f.unlink(missing_ok=True)
        os.link(outside, f)
        return f

    def text_image(self, patch=""):
        return self.py(patch + "d = {'kind': 'client', 'project': 'ABC', 'date': '" + WEEK + "'}\n"
                       "f = creaite_doc.text_image(d, '_images/client-linked.png')\nprint(json.dumps(f is not None))")

    def test_hard_link_a_hard_linked_client_picture_is_never_drawn(self):
        f = self.hard_linked()
        self.assertFalse(self.text_image())
        f.unlink()
        f.write_bytes(png(23, 17, (1, 2, 3)))                                  # control: the same picture as a file of its own
        self.assertTrue(self.text_image())

    def test_mutant_hard_link_check_off_draws_it(self):
        self.hard_linked()
        old = ("import creaite_doc as _c\nfrom pathlib import Path as _P\n"
               "_c._own_picture = lambda root, f: f.is_file() and not f.is_symlink()\n")
        self.assertTrue(self.text_image(old))


for _name in [n for n in dir(T2.Step2) if n.startswith("test_")]:
    setattr(Step3, _name, None)                               # only this file's tests run here


if __name__ == "__main__":
    unittest.main()

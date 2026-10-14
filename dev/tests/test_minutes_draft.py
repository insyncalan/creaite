"""BL-260: minutes are never staged without their Word draft, and Review, doctor and the dashboard say so plainly when one is missing."""
# ===== BL-260 (fix-minutes-draft) =====
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
from test_tracker import ABC, Vault  # noqa: E402

DAY, TITLE = "2026-10-12", "[ABC] Catch up"
TRANSCRIPT = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\n<v Omar Ali>I'll send the SOW.</v>\n"
ITEMS = [{"table": "actions", "section": "Action Items",
          "values": {"project": "ABC", "description": "Send the SOW", "owner": "Omar Ali"}}]
LIVE = {"key": "fp:2026-10-12|catch up|1", "title": "Catch up", "date": DAY, "projects": ["ABC"], "draft": None,
        "transcript": "inbox/catch-up.vtt", "minutes_decision": "pending", "file_ops": [],
        "source_map": {f"{ABC}/minutes/2026-10-12 Catch up.docx": f"{ABC}/transcripts/2026-10-12 Catch up.vtt"}}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.v.run("init")
        (self.v.root / "inbox/catch-up.vtt").write_text(TRANSCRIPT)

    def tearDown(self):
        self.v.cleanup()

    def stage(self, ok=True, **spec):
        f = self.v.root / "system/staging/drafts/meeting.json"
        f.write_text(json.dumps({"title": TITLE, "date": DAY, "projects": ["ABC"], "items": ITEMS, **spec}))
        return f, self.v.run("stage", str(f), script="minutes.py", ok=ok)

    def proposals(self):
        return sorted((self.v.root / "system/staging").glob("proposed-*.json"))

    def draft(self):
        d = self.v.root / "system/staging/drafts/2026-10-12 Catch up.docx"
        shutil.copy(self.v.root / "system/templates/minutes-template.docx", d)
        return "system/staging/drafts/2026-10-12 Catch up.docx"


class StageTests(Base):
    def test_a_transcript_without_a_draft_is_refused_and_nothing_is_written(self):
        f, r = self.stage(ok=False, transcript="inbox/catch-up.vtt")
        self.assertEqual(r.returncode, 1)
        self.assertIn("No draft minutes: run step 3 (docx_tools.py fill) first", r.stdout)
        self.assertEqual(self.proposals(), [])
        self.assertTrue(f.exists())                                  # kept, so the run can fill the draft and stage again
        self.assertTrue((self.v.root / "inbox/catch-up.vtt").exists())

    def test_a_draft_that_does_not_exist_is_refused(self):
        _, r = self.stage(ok=False, transcript="inbox/catch-up.vtt", draft="system/staging/drafts/never-made.docx")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Draft minutes not found: system/staging/drafts/never-made.docx", r.stdout)
        self.assertEqual(self.proposals(), [])

    def test_a_transcript_with_its_draft_still_stages(self):
        draft = self.draft()
        _, r = self.stage(transcript="inbox/catch-up.vtt", draft=draft)
        self.assertIn(f"Draft minutes: {draft}", r.stdout)
        meeting = json.loads(self.proposals()[0].read_text())["meeting"]
        self.assertEqual(meeting["draft"], draft)

    def test_a_quick_note_still_stages_without_a_draft(self):
        note = f"{ABC}/minutes/2026-10-12 Quick note - Corridor chat.md"
        (self.v.root / note).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / note).write_text("# Corridor chat\n\nOmar will send the SOW.\n")
        self.stage(note=note, title="Corridor chat")
        meeting = json.loads(self.proposals()[0].read_text())["meeting"]
        self.assertEqual((meeting["note"], meeting["draft"]), (note, None))


class MissingDraftTests(Base):
    """A minutes row already staged with no draft (the live defect), or whose draft has gone."""

    def setUp(self):
        super().setUp()
        self.v.propose("2026-10-12-1546", [], meeting=LIVE)

    def review_rows(self):
        self.v.run(script="build_dashboard.py")
        html = (self.v.root / "dashboard.html").read_text(encoding="utf-8")
        data = json.loads(re.search(r'id="data">(.*?)</script>', html, re.S).group(1).replace("<\\/", "</"))
        return [r for r in data["review"] if r["kind"] == "draft"]

    def test_the_dashboard_marks_the_row_and_keeps_the_transcript(self):
        draft = self.draft()
        _, _ = self.stage(transcript="inbox/catch-up.vtt", draft=draft)
        rows = {r["file"]: r for r in self.review_rows()}
        live = rows["proposed-2026-10-12-1546.json"]
        self.assertEqual((live.get("nodraft"), live.get("tsrc")), (True, "inbox/catch-up.vtt"))
        good = next(r for f, r in rows.items() if f != "proposed-2026-10-12-1546.json")
        self.assertNotIn("nodraft", good)
        (self.v.root / draft).unlink()                                     # the draft has gone since
        gone = next(r for r in self.review_rows() if r["file"] == good["file"])
        self.assertTrue(gone.get("nodraft"))

    def test_doctor_lists_staged_minutes_with_no_draft(self):
        out = self.v.run(script="doctor.py", ok=False).stdout
        line = next(ln for ln in out.splitlines() if "Staged minutes have their Word draft" in ln)
        self.assertTrue(line.startswith("WARN"), line)
        self.assertIn("1 staged minutes with no Word draft: proposed-2026-10-12-1546.json (Catch up)", line)
        self.assertIn("Reject them in Review and process the meeting again", line)

    def test_doctor_passes_when_every_draft_is_there(self):
        (self.v.root / "system/staging/proposed-2026-10-12-1546.json").unlink()
        out = self.v.run(script="doctor.py", ok=False).stdout
        self.assertIn("PASS  Staged minutes have their Word draft", out)

    @unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
    def test_edit_says_there_is_no_draft_and_opens_nothing(self):
        v = self.v
        v.run(script="build_dashboard.py")
        html = (v.root / "dashboard.html").read_text(encoding="utf-8")
        harness = v.root / "harness-nodraft.html"
        harness.write_text(html.replace("</body>", SCRIPT + "</body>"), encoding="utf-8")
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
        self.assertEqual(r["opened"], [])                                  # nothing opened, not even a blank path
        self.assertEqual(r["snacks"], ["No Word draft was made for these minutes: Reject them and process the meeting again"])
        self.assertIn("No Word draft", r["button"])
        self.assertIn("No Word draft was made for these minutes", r["row"])
        self.assertEqual(r["source"], "inbox/catch-up.vtt")                 # Open source still opens the transcript
        self.assertFalse(r["panel"])


SCRIPT = r"""
<script>
(async()=>{
  const wait=ms=>new Promise(r=>setTimeout(r,ms)), out={errors:[],opened:[],snacks:[]};
  try{
    await wait(300); openPath=p=>out.opened.push(p); snack=m=>out.snacks.push(m);
    go("review"); await wait(100);
    const r=REV.find(x=>x.kind==="draft"&&x.ref==="meeting"), tr=document.querySelector(`#reviewBody tr[data-n="${r.n}"]`);
    const b=tr.querySelector('[data-act="e"]'); out.button=(b.getAttribute("title")||"")+" "+(b.getAttribute("aria-label")||"")+" "+b.textContent;
    out.row=tr.textContent.replace(/\s+/g," "); const src=tr.querySelector("[data-openfile]"); out.source=src?src.dataset.openfile:null;
    b.click(); await wait(100);
    out.panel=document.querySelector("#panel").classList.contains("on");
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
</script>
"""
# ===== end BL-260 =====


# ===== BL-260 point 4 (fix-minutes-approve) =====
TCOPY = f"{ABC}/transcripts/2026-10-12 Catch up.vtt"
LIVE_OPS = {**LIVE, "file_ops": [{"op": "copy", "from": "transcript", "to": TCOPY},
                                 {"op": "remove", "path": "inbox/catch-up.vtt"}]}
ACTION = {"n": 1, "op": "new", "table": "actions", "decision": "approved", "match": "strong",
          "values": {"project": "ABC", "description": "Send the SOW", "owner": "Omar Ali",
                     "source": f"{ABC}/minutes/2026-10-12 Catch up.docx — Action Items"}}


class ApproveRefusedTests(Base):
    """Approving minutes with no Word draft is refused: by apply, by review approve and bulk, and in the dashboard."""

    def setUp(self):
        super().setUp()
        self.prop = self.v.propose("2026-10-12-1546", [dict(ACTION)], meeting=dict(LIVE_OPS))

    def processed(self):
        f = self.v.root / "system/processed.txt"
        return f.read_text() if f.exists() else ""

    def meeting_n(self):
        listed = json.loads(self.v.run("list", "--json", script="review.py").stdout)
        return next(r["n"] for r in listed if r["ref"] == "meeting")

    def test_apply_refuses_minutes_with_no_draft_and_files_nothing(self):
        data = json.loads(self.prop.read_text())
        data["meeting"]["minutes_decision"] = "approved"                   # approved outside Review (the live defect)
        self.prop.write_text(json.dumps(data))
        before = self.processed()
        r = self.v.run("apply", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Apply stopped. Nothing was written.", r.stdout)
        self.assertIn("No draft minutes to file", r.stdout)
        self.assertTrue((self.v.root / "inbox/catch-up.vtt").exists())    # the transcript is not filed or removed
        self.assertFalse((self.v.root / TCOPY).exists())
        self.assertEqual(self.processed(), before)                          # not marked processed
        self.assertEqual(self.v.rows("actions"), [])
        meeting = json.loads(self.prop.read_text())["meeting"]
        self.assertEqual(meeting["minutes_decision"], "pending")           # still in Review
        self.assertNotIn("applied", meeting)

    def test_a_missing_draft_file_is_refused_too(self):
        data = json.loads(self.prop.read_text())
        data["meeting"].update(minutes_decision="approved", draft="system/staging/drafts/gone.docx")
        self.prop.write_text(json.dumps(data))
        r = self.v.run("apply", ok=False)
        self.assertIn("No draft minutes to file", r.stdout)
        self.assertFalse((self.v.root / TCOPY).exists())

    def test_rejecting_them_still_files_the_transcript(self):
        out = self.v.run("reject", str(self.meeting_n()), script="review.py").stdout
        self.assertIn("Rejected 1.", out)
        self.v.run("apply")
        self.assertTrue((self.v.root / TCOPY).exists())
        self.assertIn("2026-10-12 Catch up.vtt", self.processed())

    def test_review_approve_skips_them_with_a_message(self):
        out = self.v.run("approve", str(self.meeting_n()), script="review.py").stdout
        self.assertIn("Approved 0.", out)
        self.assertIn("not approved — No draft minutes to file", out)
        self.assertEqual(json.loads(self.prop.read_text())["meeting"]["minutes_decision"], "pending")

    def test_bulk_approve_names_them(self):
        out = self.v.run("bulk", script="review.py").stdout
        self.assertIn("1 set of minutes with no Word draft (reject it and process the meeting again)", out)
        self.assertEqual(json.loads(self.prop.read_text())["meeting"]["minutes_decision"], "pending")

    def test_a_quick_note_still_applies(self):
        note = f"{ABC}/minutes/2026-10-12 Quick note - Corridor chat.md"
        (self.v.root / note).parent.mkdir(parents=True, exist_ok=True)
        (self.v.root / note).write_text("# Corridor chat\n")
        self.prop.unlink()
        self.v.propose("2026-10-12-1600", [], meeting={"key": "fp:2026-10-12|corridor chat|1", "title": "Corridor chat",
                                                       "date": DAY, "projects": ["ABC"], "draft": None, "note": note,
                                                       "kind": "quick note", "minutes_decision": "approved", "file_ops": []})
        self.v.run("apply")
        self.assertIn("corridor chat", self.processed())

    @unittest.skipUnless(CHROME.exists(), "Google Chrome not installed")
    def test_the_dashboard_approve_is_unavailable(self):
        v = self.v
        v.run(script="build_dashboard.py")
        html = (v.root / "dashboard.html").read_text(encoding="utf-8")
        harness = v.root / "harness-noapprove.html"
        harness.write_text(html.replace("</body>", APPROVE_SCRIPT + "</body>"), encoding="utf-8")
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
        self.assertTrue(r["disabled"])
        self.assertIn("No Word draft", r["title"])
        self.assertEqual(r["snacks"], ["No Word draft was made for these minutes: Reject them and process the meeting again"])
        self.assertEqual(r["edits"], 0)                                     # nothing saved, the row is still pending
        self.assertFalse(r["done"])
        self.assertTrue(r["menuDisabled"])
        self.assertTrue(r["rejectOn"])


APPROVE_SCRIPT = r"""
<script>
(async()=>{
  const wait=ms=>new Promise(r=>setTimeout(r,ms)), out={errors:[],snacks:[],edits:0};
  try{
    await wait(300); snack=m=>out.snacks.push(m); editProposal=async()=>{ out.edits++; };
    go("review"); await wait(100);
    const r=REV.find(x=>x.kind==="draft"&&x.ref==="meeting"), tr=document.querySelector(`#reviewBody tr[data-n="${r.n}"]`);
    const b=tr.querySelector('[data-act="a"]'); out.disabled=b.disabled; out.title=b.getAttribute("title")||"";
    out.rejectOn=!tr.querySelector('[data-act="r"]').disabled;
    await decide(r.n,"approved"); out.done=!!r.done;                       /* the keyboard and menu paths go through decide */
    out.menuDisabled=!!cxReview(r,tr)[0].disabled;
  }catch(e){ out.errors.push(String(e&&e.stack||e)); }
  const pre=document.createElement("pre"); pre.id="result"; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
</script>
"""
# ===== end BL-260 point 4 =====

if __name__ == "__main__":
    unittest.main()

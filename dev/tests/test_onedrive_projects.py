"""BL-85: project folders outside the vault, in a OneDrive-style root (the `locations` setting).

Run: python3 dev/tests/test_onedrive_projects.py

Everything here is fictional and temporary: a fake home folder, an "Engagements" root laid out like Alan's template (the
template's folder names only: no real engagement name, file name or content), two engagements (ABC Example Programme and
DEF Digital Enablement, in folders named without a code) and Teams-named transcripts. The vault itself stays a normal local
throwaway vault, as in production; only `locations.projects_root` points outside it (written with `~`, as it is in the
live vault, and resolved against the fake home). Never touches a real OneDrive.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_minutes_review import DAY, TRANSCRIPT, fill_values, meeting_spec  # noqa: E402
from test_tracker import Vault  # noqa: E402

TENANT = "OneDrive-TestCo"
ROOT_SETTING = f"~/Library/CloudStorage/{TENANT}/Documents/Engagements"
TEMPLATE_DIRS = ["00 Admin/Contract", "00 Admin/Commercial", "01 Inputs/Research", "02 Meetings/Transcripts", "02 Meetings/Minutes",
                 "02 Meetings/Agendas", "03 Delivery/Design", "04 Reporting/Weekly", "04 Reporting/Steerco", "04 Reporting/Adhoc",
                 "04 Reporting/Milestones", "05 Governance/RAID", "05 Governance/Decisions", "05 Governance/Change Requests",
                 "06 Closure", "07 Growth", "_Archive"]
ENGAGEMENTS = {"ABC": "Example Programme", "DEF": "Digital Enablement"}      # code -> folder (the folder name has no code)
LOCATIONS = {"projects_root": ROOT_SETTING, "portfolio": "_Portfolio", "skeleton": "_Templates/_Skeleton",
             "folders": {"transcripts": "02 Meetings/Transcripts", "minutes": "02 Meetings/Minutes", "weekly_reports": "04 Reporting/Weekly",
                         "client_reports": "04 Reporting/Weekly", "adhoc_documents": "04 Reporting/Adhoc", "images": "04 Reporting/Content"},
             "never_index": ["_Archive", "_Templates", "99 System"], "offsite_backup": "_Portfolio/99 System/creaite backups"}


def touch(path, text="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode() if isinstance(text, str) else text)
    return path


def make_template(base):
    for d in TEMPLATE_DIRS:
        (base / d).mkdir(parents=True, exist_ok=True)
        touch(base / d / ".keep", "")


class OneDriveCase(unittest.TestCase):
    """A local vault whose projects live in a fake OneDrive Engagements folder under a fake home."""

    locations = LOCATIONS

    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="creaite-home-")).resolve()
        self.env = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        self.env.start()
        self.root = self.home / "Library" / "CloudStorage" / TENANT / "Documents" / "Engagements"
        self.v = Vault()
        make_template(self.root / "_Templates" / "_Skeleton")
        (self.root / "_Portfolio" / "02 Meetings" / "Minutes").mkdir(parents=True)
        (self.root / "_Portfolio" / "02 Meetings" / "Transcripts").mkdir(parents=True)
        for code, name in ENGAGEMENTS.items():
            make_template(self.root / name)
            touch(self.root / name / "CLAUDE.md", f"# {code} — {name}\n\n## Brief\n\n- **Client / partner:** Example Client Ltd\n"
                                                  "- **Client report rhythm:** weekly\n\n## Current state\n\nOn track.\n")
        reg = (self.v.root / "projects/_portfolio/project-register.md").read_text(encoding="utf-8")
        rows = "".join(f"| {c} | {n} | {n} | Example |  |  |  |  |  |  |\n" for c, n in ENGAGEMENTS.items())
        row = next(ln for ln in reg.splitlines() if ln.startswith("| ABC |"))
        (self.root / "_Portfolio" / "project-register.md").write_text(reg.replace(row + "\n", rows), encoding="utf-8")
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"] = self.locations
        cfg.write_text(json.dumps(data, indent=2))
        self.v.run("init")

    def tearDown(self):
        self.v.cleanup()
        shutil.rmtree(self.home, ignore_errors=True)
        self.env.stop()

    # ── helpers ──
    def py(self, code):
        """Run Python inside the vault's own scripts folder and return what it prints as JSON."""
        src = f"import sys, json; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r})\n{code}"
        r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir())
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def eng(self, code, *parts):
        return self.root.joinpath(ENGAGEMENTS[code], *parts)


class ProjectPathsTests(OneDriveCase):
    """BL-85 item 1: one place for every project path."""

    def test_the_setting_is_stored_with_a_tilde_and_resolved_against_home(self):
        saved = json.loads((self.v.root / "system/config/settings.json").read_text())["locations"]["projects_root"]
        self.assertEqual(saved, ROOT_SETTING)                                   # home-relative, never absolute
        self.assertFalse(Path(saved).is_absolute())
        o = self.py("import paths; print(json.dumps([str(paths.projects_root()), paths.external(), str(paths.PROJECTS), str(paths.portfolio_dir())]))")
        self.assertEqual(o, [str(self.root), True, str(self.root), str(self.root / "_Portfolio")])

    def test_every_kind_of_file_has_its_mapped_folder(self):
        o = self.py("""import paths
print(json.dumps({k: str(paths.folder('ABC', k)) for k in ('minutes','transcripts','weekly_reports','client_reports','adhoc_documents','images')}
                 | {'extract': [str(d) for d in paths.extract_dirs('ABC')], 'dir': str(paths.project_dir('DEF')),
                    'portfolio_minutes': str(paths.folder('_portfolio', 'minutes'))}))""")
        base = self.eng("ABC")
        self.assertEqual(o["minutes"], str(base / "02 Meetings" / "Minutes"))
        self.assertEqual(o["transcripts"], str(base / "02 Meetings" / "Transcripts"))
        self.assertEqual(o["weekly_reports"], str(base / "04 Reporting" / "Weekly"))
        self.assertEqual(o["client_reports"], str(base / "04 Reporting" / "Weekly"))      # with the weekly reports; Steerco is separate
        self.assertEqual(o["adhoc_documents"], str(base / "04 Reporting" / "Adhoc"))
        self.assertEqual(o["images"], str(base / "04 Reporting" / "Content"))
        self.assertEqual(o["extract"], [str(base / "02 Meetings" / "Minutes"), str(base / "02 Meetings" / "Transcripts")])   # only these
        self.assertEqual(o["dir"], str(self.eng("DEF")))                      # the register maps DEF to a folder with no code in its name
        self.assertEqual(o["portfolio_minutes"], str(self.root / "_Portfolio" / "02 Meetings" / "Minutes"))

    def test_stored_paths_use_the_logical_prefix_and_survive_moving_the_root(self):
        f = touch(self.eng("ABC", "02 Meetings", "Minutes", "2026-10-01 Steering.docx"))
        pf = touch(self.root / "_Portfolio" / "PORTFOLIO.md")
        o = self.py(f"import paths; from pathlib import Path; print(json.dumps([paths.rel(Path({str(f)!r})), paths.rel(Path({str(pf)!r})), str(paths.resolve('projects/_portfolio/PORTFOLIO.md'))]))")
        self.assertEqual(o[0], "projects/Example Programme/02 Meetings/Minutes/2026-10-01 Steering.docx")
        self.assertEqual(o[1], "projects/_portfolio/PORTFOLIO.md")            # the portfolio keeps its logical name
        self.assertEqual(o[2], str(pf))
        # move the whole root, change one setting: the same stored paths resolve to the new place
        moved = self.home / "Documents" / "Moved Engagements"
        moved.parent.mkdir(parents=True)
        shutil.move(str(self.root), str(moved))
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"]["projects_root"] = "~/Documents/Moved Engagements"
        cfg.write_text(json.dumps(data, indent=2))
        again = self.py("import paths; print(json.dumps([str(paths.resolve('projects/Example Programme/02 Meetings/Minutes/2026-10-01 Steering.docx')), str(paths.resolve('projects/_portfolio/PORTFOLIO.md'))]))")
        self.assertEqual(again, [str(moved / "Example Programme/02 Meetings/Minutes/2026-10-01 Steering.docx"), str(moved / "_Portfolio/PORTFOLIO.md")])
        self.assertTrue(Path(again[0]).is_file())

    def test_the_default_layout_is_unchanged_without_the_setting(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.pop("locations")
        cfg.write_text(json.dumps(data, indent=2))
        o = self.py("import paths; print(json.dumps([paths.external(), str(paths.PROJECTS), str(paths.folder('ABC','minutes')), str(paths.folder('ABC','weekly_reports')), paths.rel(paths.PROJECTS / 'x')]))")
        self.assertEqual(o[0], False)
        self.assertEqual(o[1], str(self.v.root.resolve() / "projects"))
        self.assertEqual(o[2], str(self.v.root.resolve() / "projects/ABC Example Programme/minutes"))
        self.assertEqual(o[3], str(self.v.root.resolve() / "projects/ABC Example Programme/reports"))
        self.assertEqual(o[4], "projects/x")

    def test_the_index_reads_minutes_transcripts_reports_and_documents_but_not_the_archive(self):
        touch(self.eng("ABC", "02 Meetings", "Transcripts", "Weekly sync-20261001_093000-Meeting Transcript.docx"))
        touch(self.eng("ABC", "02 Meetings", "Transcripts", "Kick-off-20260915.vtt"), "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nhello kickoff words\n")
        touch(self.eng("ABC", "02 Meetings", "Minutes", "2026-10-01 Weekly sync.docx"))
        touch(self.eng("ABC", "02 Meetings", "Agendas", "Agenda 1 October.docx"))
        touch(self.eng("ABC", "04 Reporting", "Weekly", "2026-10-02 Weekly report.docx"))
        touch(self.eng("ABC", "04 Reporting", "Weekly", "2026-10-09 Client report.docx"))
        touch(self.eng("ABC", "04 Reporting", "Steerco", "Steerco pack.pptx"))                       # Alan's own steering material
        touch(self.eng("ABC", "04 Reporting", "Adhoc", "Risk register.xlsx"))
        touch(self.eng("ABC", "00 Admin", "Contract", "Statement of work.docx"))
        touch(self.eng("ABC", "01 Inputs", "Research", "Market notes.md"), "market notes about pilots")
        touch(self.eng("ABC", "_Archive", "Old plan.docx"))
        touch(self.root / "_Templates" / "_Skeleton" / "00 Admin" / "Contract" / "Template contract.docx")
        touch(self.eng("DEF", "03 Delivery", "Design", "Design notes.md"), "design notes")
        touch(self.eng("DEF", "02 Meetings", "Minutes", "2026-10-03 Design review.docx"))
        touch(self.root / "_Portfolio" / "02 Meetings" / "Minutes" / "2026-10-04 Portfolio review.docx")
        o = self.py("""import paths, tracker
files = tracker.index_files()
print(json.dumps(sorted([paths.rel(f).split('/', 1)[1], kind, code] for f, kind, code in files)))""")
        got = {(p, kind, code) for p, kind, code in o}
        a = "Example Programme/"
        self.assertEqual(got, {
            (a + "02 Meetings/Transcripts/Weekly sync-20261001_093000-Meeting Transcript.docx", "transcripts", "ABC"),
            (a + "02 Meetings/Transcripts/Kick-off-20260915.vtt", "transcripts", "ABC"),
            (a + "02 Meetings/Minutes/2026-10-01 Weekly sync.docx", "minutes", "ABC"),
            (a + "04 Reporting/Weekly/2026-10-02 Weekly report.docx", "reports", "ABC"),
            (a + "04 Reporting/Weekly/2026-10-09 Client report.docx", "reports", "ABC"),
            (a + "04 Reporting/Steerco/Steerco pack.pptx", "reports", "ABC"),                     # BL-87: a report folder of its own, read and never written to
            (a + "04 Reporting/Adhoc/Risk register.xlsx", "reports", "ABC"),
            (a + "02 Meetings/Agendas/Agenda 1 October.docx", "agendas", "ABC"),               # BL-135: their own kind (stored as a document in the index)
            (a + "00 Admin/Contract/Statement of work.docx", "documents", "ABC"),
            (a + "01 Inputs/Research/Market notes.md", "documents", "ABC"),
            ("Digital Enablement/03 Delivery/Design/Design notes.md", "documents", "DEF"),
            ("Digital Enablement/02 Meetings/Minutes/2026-10-03 Design review.docx", "minutes", "DEF"),
            ("_portfolio/02 Meetings/Minutes/2026-10-04 Portfolio review.docx", "minutes", "_portfolio")})
        names = " ".join(p for p, _, _ in o)
        for left_out in ("Old plan", "Template contract", "CLAUDE.md", ".keep"):
            self.assertNotIn(left_out, names)                                                  # _Archive, _Templates, memory, hidden files
        self.assertNotIn("_Portfolio/", names)                                                # (it is listed under its logical name)

    def test_the_files_view_lists_the_same_folders_with_their_kinds(self):
        touch(self.eng("ABC", "02 Meetings", "Minutes", "2026-10-01 Weekly sync.docx"))
        touch(self.eng("ABC", "00 Admin", "Contract", "Statement of work.docx"))
        touch(self.eng("ABC", "_Archive", "Old plan.docx"))
        o = self.py("""import build_dashboard as bd, paths
folders = {c: paths.project_dir(c) for c in ('ABC', 'DEF')}
print(json.dumps([[f['p'], f['f'], f['n'], f['sub'], f['path']] for f in bd.files(folders, True) if f['p'] != 'inbox']))""")   # documents shown (they are set aside by default: BL-87)
        rows = {tuple(r[:4]): r[4] for r in o}
        self.assertIn(("ABC", "minutes", "2026-10-01 Weekly sync.docx", ""), rows)
        self.assertEqual(rows[("ABC", "documents", "Statement of work.docx", "00 Admin › Contract")],
                         "projects/Example Programme/00 Admin/Contract/Statement of work.docx")
        self.assertFalse([r for r in o if "Old plan" in r[2]])

    def test_safe_path_refuses_anything_outside_the_vault_and_the_root(self):
        o = self.py("""import tracker, paths
out = {}
for name, rel in (('inside', 'projects/Example Programme/02 Meetings/Minutes/x.docx'), ('portfolio', 'projects/_portfolio/PORTFOLIO.md'),
                  ('staging', 'system/staging/x.docx'), ('up', 'projects/../../escape.docx'), ('absolute', '/tmp/escape.docx'),
                  ('home', 'projects/Example Programme/../../../../escape.docx'), ('system', 'system/scripts/tracker.py')):
    try:
        out[name] = tracker.safe_path(rel, 'write').as_posix()
    except tracker.Invalid as e:
        out[name] = 'refused: ' + str(e)
print(json.dumps(out))""")
        self.assertTrue(o["inside"].endswith("Engagements/Example Programme/02 Meetings/Minutes/x.docx"))
        self.assertTrue(o["portfolio"].endswith("Engagements/_Portfolio/PORTFOLIO.md"))
        self.assertTrue(o["staging"].endswith("system/staging/x.docx"))
        for bad in ("up", "absolute", "home", "system"):
            self.assertTrue(o[bad].startswith("refused"), (bad, o[bad]))

    def test_the_live_servers_file_rules_follow_the_mapping(self):
        o = self.py("""import live_server as ls, paths
print(json.dumps([ls.allowed('read', 'projects/Example Programme/CLAUDE.md'), ls.allowed('write', 'projects/Example Programme/CLAUDE.md'),
                  ls.allowed('exists', 'projects/Example Programme/04 Reporting/Content/x.png'), ls.allowed('exists', 'projects/Example Programme/images/x.png'),
                  ls.allowed('read', 'projects/Example Programme/02 Meetings/Minutes/x.docx'), str(paths.resolve('projects/Example Programme/CLAUDE.md'))]))""")
        self.assertEqual(o[:5], [True, True, True, False, False])                  # only the mapped images folder, and nothing else under it
        self.assertEqual(o[5], str(self.eng("ABC", "CLAUDE.md")))

    def test_minutes_are_filed_into_the_mapped_folders_with_creaite_names_and_sources_resolve(self):
        v = self.v
        transcript = "inbox/Recording 2026-10-01.vtt"
        touch(v.root / transcript, TRANSCRIPT)
        stem = v.run("filename", "--date", DAY, "--title", "[ABC] Steering committee", script="minutes.py").stdout.strip()
        draft = f"system/staging/drafts/{stem}.docx"
        values = v.root / "system/staging/values.json"
        values.write_text(json.dumps(fill_values()))
        v.run("fill", "system/templates/minutes-template.docx", str(values), str(v.root / draft), script="docx_tools.py", cwd=v.root)
        spec = v.root / "system/staging/meeting.json"
        spec.write_text(json.dumps(meeting_spec(draft, transcript)))
        v.run("stage", str(spec), script="minutes.py")
        prop = next((v.root / "system/staging").glob("proposed-*.json"))
        data = json.loads(prop.read_text())
        mine = "projects/Example Programme/02 Meetings"
        self.assertIn({"op": "copy", "from": "draft", "to": f"{mine}/Minutes/2026-10-01 Steering committee.docx"}, data["meeting"]["file_ops"])
        self.assertIn({"op": "copy", "from": "transcript", "to": f"{mine}/Transcripts/2026-10-01 Steering committee.vtt"}, data["meeting"]["file_ops"])
        self.assertEqual(data["items"][0]["values"]["source"], f"{mine}/Minutes/2026-10-01 Steering committee.docx — Action Items")
        # approve the minutes and apply: the files land in OneDrive's folders, nothing in the vault's own projects/
        data["meeting"]["minutes_decision"] = "approved"
        for i in data["items"]:
            i["decision"] = "approved"
        prop.write_text(json.dumps(data))
        out = v.run("apply").stdout
        self.assertIn("filed", out)
        self.assertTrue(self.eng("ABC", "02 Meetings", "Minutes", "2026-10-01 Steering committee.docx").is_file())
        self.assertTrue(self.eng("ABC", "02 Meetings", "Transcripts", "2026-10-01 Steering committee.vtt").is_file())
        self.assertFalse((v.root / "projects/ABC Example Programme/minutes/2026-10-01 Steering committee.docx").exists())
        self.assertEqual(v.rows("actions")[0]["source"], f"{mine}/Minutes/2026-10-01 Steering committee.docx — Action Items")
        # the stored source resolves to the real file, and an undo takes both files away again
        real = self.py("import paths; print(json.dumps(str(paths.resolve('projects/Example Programme/02 Meetings/Minutes/2026-10-01 Steering committee.docx'))))")
        self.assertTrue(Path(real).is_file())
        v.run("undo")
        self.assertFalse(self.eng("ABC", "02 Meetings", "Minutes", "2026-10-01 Steering committee.docx").exists())

    def test_report_paths_follow_the_mapping(self):
        out = self.v.run("current-context", "ABC", script="report.py", ok=False)       # the context lists files from the mapped folders
        self.assertEqual(out.returncode, 0, out.stderr)
        stage = self.py("""import report, paths
from pathlib import Path
print(json.dumps([str(paths.rel(paths.folder('ABC', 'weekly_reports') / '2026-10-02 Weekly report.docx')), str(paths.rel(paths.folder('ABC', 'client_reports') / '2026-10-09 Client report.docx'))]))""")
        self.assertEqual(stage, ["projects/Example Programme/04 Reporting/Weekly/2026-10-02 Weekly report.docx",
                                 "projects/Example Programme/04 Reporting/Weekly/2026-10-09 Client report.docx"])

    def test_an_image_is_filed_into_a_content_folder_that_does_not_exist_yet(self):
        v = self.v
        self.assertFalse(self.eng("ABC", "04 Reporting", "Content").exists())                      # the skeleton doesn't have it
        from test_dashboard import png
        touch(v.root / "system/staging/uploads/20261008-plan.png", png(40, 30, (10, 100, 120)))
        dest = "projects/Example Programme/04 Reporting/Content/2026-10-08-plan.png"
        spec = {"source_run": "cx-edit", "items": [], "file_changes": {"title": "ABC current state", "project": "ABC", "file_changes_decision": "approved",
                "file_ops": [{"op": "copy", "from": "system/staging/uploads/20261008-plan.png", "to": dest},
                             {"op": "remove", "path": "system/staging/uploads/20261008-plan.png"}]}}
        (v.root / "system/staging/img.json").write_text(json.dumps(spec))
        v.run("stage", str(v.root / "system/staging/img.json"), script="propose.py")
        self.assertIn("filed", v.run("apply").stdout)
        self.assertTrue(self.eng("ABC", "04 Reporting", "Content", "2026-10-08-plan.png").is_file())     # made on first use, no error
        self.assertEqual(sorted(p.name for p in self.eng("ABC", "04 Reporting", "Steerco").iterdir() if not p.name.startswith(".")), [])   # Steerco untouched
        v.run("undo")
        self.assertFalse(self.eng("ABC", "04 Reporting", "Content", "2026-10-08-plan.png").exists())

    def test_a_current_state_image_is_found_in_the_mapped_images_folder(self):
        mem = self.eng("ABC", "CLAUDE.md")
        mem.write_text(mem.read_text().replace("On track.", "On track.\n\n![Plan](images/plan.png)\n"))
        from test_dashboard import png
        touch(self.eng("ABC", "04 Reporting", "Content", "plan.png"), png(40, 30, (10, 100, 120)))
        o = self.py("""import build_dashboard as bd, paths, report
folder = paths.project_dir('ABC')
m = bd.memory(folder)
print(json.dumps([[i['ref'], i['src'][:22]] for i in m['images']], ), )""")
        self.assertEqual(o, [["images/plan.png", "data:image/png;base64,"]])      # the reference stays `images/…`, with no spaces
        im = self.py("import report, paths; print(json.dumps(report.memory_images(paths.project_dir('ABC'))))")
        self.assertEqual(im[0]["image"], "projects/Example Programme/04 Reporting/Content/plan.png")


class RegisterAndNewProjectTests(OneDriveCase):
    """BL-85 item 2: the register maps codes to the engagement folders; add project copies the skeleton."""

    def test_the_register_maps_a_code_to_an_existing_folder_with_no_code_in_its_name(self):
        o = self.py("import paths; print(json.dumps([str(paths.project_dir('ABC')), str(paths.project_dir('DEF')), paths.register_folders()]))")
        self.assertEqual(o[0], str(self.eng("ABC")))
        self.assertEqual(o[2], {"ABC": "Example Programme", "DEF": "Digital Enablement"})
        err = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(self.v.root / 'system/scripts')!r}); import paths; paths.project_dir('ZZZ')"],
                             capture_output=True, text=True).stderr
        self.assertIn("has no folder in the register", err)                       # a code that isn't registered is a clear error

    def test_add_project_copies_the_skeleton_and_the_folder_is_named_without_a_code(self):
        touch(self.root / "_Templates" / "_Skeleton" / "00 Admin" / "Contract" / "Contract checklist.docx", "checklist")
        r = self.v.run("new-project", "--code", "GHI", "--name", "Green Harbour Pilot", "--client", "Example Client", script="propose.py")
        spec = json.loads(r.stdout)
        ops = spec["file_changes"]["file_ops"]
        self.assertIn({"op": "mkdir", "path": "projects/Green Harbour Pilot"}, ops)
        self.assertIn({"op": "mkdir", "path": "projects/Green Harbour Pilot/02 Meetings/Transcripts"}, ops)
        self.assertIn({"op": "copy", "from": "projects/_Templates/_Skeleton/00 Admin/Contract/Contract checklist.docx",
                       "to": "projects/Green Harbour Pilot/00 Admin/Contract/Contract checklist.docx"}, ops)
        self.assertEqual([o["path"] for o in ops if o["op"] == "write"], ["projects/Green Harbour Pilot/CLAUDE.md", "projects/_portfolio/project-register.md"])
        self.assertIn("| GHI | Green Harbour Pilot | Green Harbour Pilot |", next(o for o in ops if o.get("path", "").endswith("project-register.md"))["content"])
        spec_file = self.v.root / "system/staging/newproj.json"
        spec_file.write_text(r.stdout)
        self.v.run("stage", str(spec_file), script="propose.py")
        self.v.run("apply")
        new = self.root / "Green Harbour Pilot"
        for d in TEMPLATE_DIRS:
            self.assertTrue((new / d).is_dir(), d)                              # the whole template, not the vault's default folders
        self.assertTrue((new / "00 Admin/Contract/Contract checklist.docx").is_file())
        self.assertTrue((new / "CLAUDE.md").is_file())
        self.assertFalse((self.v.root / "projects" / "GHI Green Harbour Pilot").exists())
        self.assertEqual(self.py("import paths; print(json.dumps(str(paths.project_dir('GHI'))))"), str(new))
        self.v.run("undo")                                                       # nothing is left behind
        self.assertFalse(new.exists())

    def test_adding_an_existing_engagement_adopts_it_as_it_is(self):
        mine = touch(self.root / "Orchard Pilot" / "00 Admin" / "Contract" / "Their own file.docx", "mine")
        mem = touch(self.root / "Orchard Pilot" / "CLAUDE.md", "# my own notes\n")
        r = self.v.run("new-project", "--code", "ORX", "--name", "Orchard Pilot", script="propose.py")
        ops = json.loads(r.stdout)["file_changes"]["file_ops"]
        self.assertEqual([o["op"] for o in ops], ["write"])                      # only the register row: no folders, no copies, no memory overwrite
        self.assertTrue(ops[0]["path"].endswith("project-register.md"))
        (self.v.root / "system/staging/adopt.json").write_text(r.stdout)
        self.v.run("stage", str(self.v.root / "system/staging/adopt.json"), script="propose.py")
        self.v.run("apply")
        self.assertEqual((mine.read_bytes(), mem.read_text()), (b"mine", "# my own notes\n"))

    def test_the_default_layout_still_creates_its_subfolders(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.pop("locations")
        cfg.write_text(json.dumps(data, indent=2))
        ops = json.loads(self.v.run("new-project", "--code", "JKL", "--name", "Local One", script="propose.py").stdout)["file_changes"]["file_ops"]
        self.assertEqual([o["path"] for o in ops if o["op"] == "mkdir"], [f"projects/JKL Local One/{s}" for s in ("minutes", "transcripts", "documents", "reports", "notes")])   # notes: BL-301


class TeamsNamesTests(OneDriveCase):
    """BL-85 item 3: Teams' own file names give the meeting date; Alan's files are never renamed."""

    NAMES = {
        "2026-10-01 Steering committee.docx": ("2026-10-01", "Steering committee", "creaite"),
        "Weekly sync-20261001_093000-Meeting Transcript.docx": ("2026-10-01", "Weekly sync", "teams"),
        "Weekly sync-20261001_093000UTC-Meeting Transcript.docx": ("2026-10-01", "Weekly sync", "teams"),
        "Kick-off - phase 2-20260915.docx": ("2026-09-15", "Kick-off - phase 2", "teams"),
        "Design review-20261002-Meeting Recording.mp4": ("2026-10-02", "Design review", "teams"),
        "Notes from the call.docx": (None, "Notes from the call", None),
        "Weekly sync-Meeting Transcript.docx": (None, "Weekly sync", None),
        "Stand-up-20261399.docx": (None, "Stand-up-20261399", None),                # not a real date
    }

    def test_dates_are_read_from_creaite_and_teams_names(self):
        o = self.py(f"import paths; print(json.dumps({{n: list(paths.name_date(n)) for n in {list(self.NAMES)!r}}}))")
        for name, want in self.NAMES.items():
            self.assertEqual(tuple(o[name]), want, name)

    def test_a_dateless_name_takes_the_files_own_date(self):
        f = touch(self.eng("ABC", "02 Meetings", "Transcripts", "Notes from the call.docx"))
        os.utime(f, (1790000000, 1790000000))                                     # 2026-09-21
        o = json.loads(self.v.run("filedate", str(f), script="minutes.py").stdout)
        self.assertEqual((o["date"], o["how"], o["from_name"], o["title"]), ("2026-09-21", "file", False, "Notes from the call"))
        o = json.loads(self.v.run("filedate", "Weekly sync-20261001_093000-Meeting Transcript.docx", script="minutes.py").stdout)
        self.assertEqual((o["date"], o["how"], o["from_name"], o["title"]), ("2026-10-01", "teams", True, "Weekly sync"))

    def test_new_lists_only_minutes_and_transcripts_not_yet_processed(self):
        touch(self.eng("ABC", "02 Meetings", "Transcripts", "Weekly sync-20261001_093000-Meeting Transcript.docx"), "t1")
        touch(self.eng("ABC", "02 Meetings", "Transcripts", "Planning-20260915.docx"), "t2")
        touch(self.eng("ABC", "02 Meetings", "Minutes", "2026-09-20 Board update.docx"), "m1")
        touch(self.eng("ABC", "02 Meetings", "Agendas", "Agenda-20261001.docx"), "agenda")            # a document, not a meeting
        touch(self.eng("ABC", "04 Reporting", "Weekly", "2026-10-02 Weekly report.docx"))
        touch(self.eng("ABC", "_Archive", "Old call-20250101.docx"))
        touch(self.eng("DEF", "02 Meetings", "Transcripts", "Design review-20261002_140000UTC-Meeting Transcript.docx"), "t3")
        out = json.loads(self.v.run("new", script="minutes.py").stdout)
        got = {(r["project"], r["date"], r["title"], r["how"]) for r in out}
        self.assertEqual(got, {("ABC", "2026-10-01", "Weekly sync", "teams"), ("ABC", "2026-09-15", "Planning", "teams"),
                               ("ABC", "2026-09-20", "Board update", "creaite"), ("DEF", "2026-10-02", "Design review", "teams")})
        self.assertEqual([r["date"] for r in out if r["project"] == "ABC"], ["2026-09-15", "2026-09-20", "2026-10-01"])   # oldest first
        self.assertEqual(len(json.loads(self.v.run("new", "DEF", script="minutes.py").stdout)), 1)
        key = next(r["key"] for r in out if r["title"] == "Planning")
        (self.v.root / "system/processed.txt").write_text(f"2026-10-02 | {key} | Planning\n")
        again = json.loads(self.v.run("new", "ABC", script="minutes.py").stdout)
        self.assertEqual({r["title"] for r in again}, {"Weekly sync", "Board update"})                  # a processed meeting drops out

    def _stage_in_place(self, transcript_name, date, flagged):
        v = self.v
        t = touch(self.eng("ABC", "02 Meetings", "Transcripts", transcript_name), TRANSCRIPT)
        before = t.read_bytes()
        stem = v.run("filename", "--date", date, "--title", "Weekly sync", script="minutes.py").stdout.strip()
        draft = f"system/staging/drafts/{stem}.docx"
        values = v.root / "system/staging/values.json"
        values.write_text(json.dumps(fill_values()))
        v.run("fill", "system/templates/minutes-template.docx", str(values), str(v.root / draft), script="docx_tools.py", cwd=v.root)
        rel = f"projects/Example Programme/02 Meetings/Transcripts/{transcript_name}"
        spec = {**meeting_spec(draft, rel), "date": date, "title": "Weekly sync"}
        (v.root / "system/staging/meeting.json").write_text(json.dumps(spec))
        v.run("stage", str(v.root / "system/staging/meeting.json"), script="minutes.py")
        prop = next((v.root / "system/staging").glob("proposed-*.json"))
        data = json.loads(prop.read_text())
        ops = data["meeting"]["file_ops"]
        self.assertEqual([o["op"] for o in ops], ["copy", "remove"])                  # the minutes in, the draft out: the transcript is left alone
        self.assertEqual(ops[0]["to"], f"projects/Example Programme/02 Meetings/Minutes/{date} Weekly sync.docx")
        self.assertFalse(any(o.get("path") == rel or o.get("from") == "transcript" for o in ops))
        self.assertEqual(data["items"][0]["values"]["source"], f"projects/Example Programme/02 Meetings/Minutes/{date} Weekly sync.docx — Action Items")
        self.assertEqual(all("date-from-file" in i["flags"] for i in data["items"]), flagged)
        self.assertEqual(data["meeting"].get("date_from_file", False), flagged)
        return t, before, data, prop

    def test_a_transcript_already_in_the_projects_folder_is_never_copied_or_renamed(self):
        t, before, data, prop = self._stage_in_place("Weekly sync-20261001_093000-Meeting Transcript.docx", "2026-10-01", flagged=False)
        data["meeting"]["minutes_decision"] = "approved"
        for i in data["items"]:
            i["decision"] = "approved"
        prop.write_text(json.dumps(data))
        self.v.run("apply")
        self.assertEqual(t.read_bytes(), before)                                  # Alan's file: same name, same bytes
        names = sorted(p.name for p in t.parent.iterdir() if not p.name.startswith("."))
        self.assertEqual(names, ["Weekly sync-20261001_093000-Meeting Transcript.docx"])   # and no creaite-named copy beside it
        self.assertTrue(self.eng("ABC", "02 Meetings", "Minutes", "2026-10-01 Weekly sync.docx").is_file())   # what creaite files keeps its form
        self.v.run("undo")
        self.assertEqual(t.read_bytes(), before)                                   # undo leaves it too

    def test_a_dateless_name_flags_the_items_for_review(self):
        self._stage_in_place("Weekly sync-Meeting Transcript.docx", "2026-10-01", flagged=True)
        o = self.py("""import build_dashboard as bd, tracker
con = tracker.connect()
print(json.dumps([[r['why'], r['kind']] for r in bd.review_queue(con) if r['kind'] == 'actions']))""")
        self.assertTrue(o and all(w == "Meeting date taken from the file" for w, _ in o))

    def test_the_index_and_the_files_view_take_teams_dates(self):
        touch(self.eng("ABC", "02 Meetings", "Transcripts", "Weekly sync-20261001_093000-Meeting Transcript.docx"), "weekly sync words")
        o = self.py("""import build_dashboard as bd, paths, tracker
tracker.build_index()
con = tracker.connect()
rows = [[r[0].split('/')[-1], r[1]] for r in con.execute("SELECT path, date FROM vault_search")]
files = [[f['n'], f['date']] for f in bd.files({'ABC': paths.project_dir('ABC')}) if f['f'] == 'transcripts']
print(json.dumps([rows, files]))""")
        self.assertIn(["Weekly sync-20261001_093000-Meeting Transcript.docx", "2026-10-01"], o[0])
        self.assertEqual(o[1], [["Weekly sync-20261001_093000-Meeting Transcript.docx", "2026-10-01"]])


class SetupHelperTests(OneDriveCase):
    """BL-85 item 4: locations.py (check, inspect, portfolio-spec) and minutes.py baseline."""

    def loc(self, *args, ok=True):
        r = self.v.run(*args, script="locations.py", ok=ok)
        return json.loads(r.stdout) if ok else r

    def test_check_accepts_company_onedrive_and_local_and_refuses_personal_and_other_sync(self):
        company = self.loc("check", str(self.root))
        self.assertEqual((company["kind"], company["tenant"], company["refuse"], company["exists"]), ("company-onedrive", "TestCo", None, True))
        self.assertEqual(company["folder"], ROOT_SETTING)                                   # stored with ~
        personal = self.home / "Library/CloudStorage/OneDrive-Personal/Engagements"
        personal.mkdir(parents=True)
        self.assertIn("personal OneDrive", self.loc("check", str(personal))["refuse"])
        icloud = self.home / "Library/Mobile Documents/com~apple~CloudDocs/Work"
        icloud.mkdir(parents=True)
        self.assertEqual(self.loc("check", str(icloud))["kind"], "other-sync")
        self.assertTrue(self.loc("check", str(icloud))["refuse"])
        local = self.home / "work"
        local.mkdir()
        self.assertEqual((self.loc("check", str(local))["kind"], self.loc("check", str(local))["refuse"]), ("local", None))
        gone = self.loc("check", str(self.home / "Library/CloudStorage/OneDrive-Gone/Engagements"))
        self.assertFalse(gone["exists"])
        self.assertIn("isn't reachable", gone["warnings"][0])

    def test_inspect_finds_the_template_the_engagements_and_the_mapping(self):
        o = self.loc("inspect", str(self.root))
        self.assertEqual(o["engagements"], ["Digital Enablement", "Example Programme"])          # not _Templates, _Portfolio or hidden
        self.assertEqual((o["template"], o["skeleton"], o["portfolio"]), ("_Templates/_Skeleton", "_Templates/_Skeleton", {"folder": "_Portfolio", "exists": True}))
        m = {k: v["path"] for k, v in o["mapping"].items()}
        self.assertEqual(m, {"transcripts": "02 Meetings/Transcripts", "minutes": "02 Meetings/Minutes", "weekly_reports": "04 Reporting/Weekly",
                             "client_reports": "04 Reporting/Weekly", "adhoc_documents": "04 Reporting/Adhoc", "images": "04 Reporting/Content"})
        shutil.rmtree(self.root / "_Templates")                                                  # no skeleton: read the first engagement
        o = self.loc("inspect", str(self.root))
        self.assertEqual((o["template"], o["skeleton"]), ("Digital Enablement (the first engagement)", None))
        self.assertEqual(o["mapping"]["minutes"]["path"], "02 Meetings/Minutes")

    def test_an_ambiguous_name_is_offered_as_candidates_not_guessed(self):
        (self.root / "Digital Enablement" / "02 Meetings" / "Old Minutes").mkdir()
        shutil.rmtree(self.root / "_Templates")
        o = self.loc("inspect", str(self.root))
        self.assertIsNone(o["mapping"]["minutes"]["path"])
        self.assertEqual(sorted(o["mapping"]["minutes"]["candidates"]), ["02 Meetings/Minutes", "02 Meetings/Old Minutes"])

    def test_portfolio_spec_makes_only_what_is_missing(self):
        shutil.rmtree(self.root / "_Portfolio" / "02 Meetings")                                    # (the fixture has them; take them away)
        ops = self.loc("portfolio-spec")["file_changes"]["file_ops"]
        self.assertEqual([(o["op"], o["path"]) for o in ops],
                         [("mkdir", "projects/_portfolio/02 Meetings/Minutes"), ("mkdir", "projects/_portfolio/02 Meetings/Transcripts"),
                          ("write", "projects/_portfolio/PORTFOLIO.md"), ("write", "projects/_portfolio/people-register.md")])   # the register is already there
        spec = self.v.root / "system/staging/portfolio.json"
        spec.write_text(json.dumps(self.loc("portfolio-spec")))
        self.v.run("stage", str(spec), script="propose.py")
        self.v.run("apply")
        for p in ("PORTFOLIO.md", "people-register.md", "02 Meetings/Minutes", "02 Meetings/Transcripts"):
            self.assertTrue((self.root / "_Portfolio" / p).exists(), p)
        self.assertEqual([o["op"] for o in self.loc("portfolio-spec")["file_changes"]["file_ops"]], [])   # a second run has nothing to do

    def _meetings(self):
        today = __import__("datetime").date.today()
        for weeks_ago, title in ((10, "Old planning"), (6, "Mid review"), (1, "Last week sync"), (0, "This week sync")):
            d = today - __import__("datetime").timedelta(weeks=weeks_ago)
            touch(self.eng("ABC", "02 Meetings", "Transcripts", f"{title}-{d:%Y%m%d}_100000-Meeting Transcript.docx"), title)
        return today

    def new(self):
        return {r["title"] for r in json.loads(self.v.run("new", "ABC", script="minutes.py").stdout)}

    def test_baseline_marks_all_or_only_the_older_ones_and_never_by_default(self):
        self._meetings()
        r = self.v.run("baseline", "ABC", script="minutes.py", ok=False)
        self.assertEqual(r.returncode, 2)                                                        # it must be told which
        self.assertIn("--all", r.stdout)
        self.assertEqual(self.new(), {"Old planning", "Mid review", "Last week sync", "This week sync"})   # nothing marked
        dry = json.loads(self.v.run("baseline", "ABC", "--all", "--dry-run", script="minutes.py").stdout)
        self.assertEqual((dry["existing"], dry["marked_processed"], dry["dry_run"]), (4, 4, True))
        self.assertEqual(len(self.new()), 4)                                                     # a dry run writes nothing
        out = json.loads(self.v.run("baseline", "ABC", "--keep-weeks", "4", script="minutes.py").stdout)
        self.assertEqual((out["existing"], out["marked_processed"], out["left_to_process"]), (4, 2, 2))
        self.assertEqual(self.new(), {"Last week sync", "This week sync"})                        # the last N weeks stay to be processed
        log = (self.v.root / "system/processed.txt").read_text()
        self.assertIn("baseline: existing projects/Example Programme/02 Meetings/Transcripts/Old planning", log)
        self.assertEqual(json.loads(self.v.run("baseline", "ABC", "--all", script="minutes.py").stdout)["marked_processed"], 2)
        self.assertEqual(self.new(), set())                                                      # nothing extracted: only marked
        self.assertEqual(self.v.rows("actions"), [])


class OffsiteBackupTests(OneDriveCase):
    """BL-85 item 5, BL-323: the day's closed zip (with the daily backup inside) is copied into the projects folder; the live
    database never is. Retention there is Tidy up's (dev/tests/test_backups.py)."""

    def daily(self, day):
        f = self.v.root / "system/backups" / f"tracker-{day}.db"
        f.parent.mkdir(parents=True, exist_ok=True)
        import sqlite3
        con = sqlite3.connect(f)
        con.execute("CREATE TABLE t (x)")
        con.execute("INSERT INTO t VALUES (?)", (day,))
        con.commit()
        con.close()
        self.py(f"import backup; backup.make_zip('{day}'); print(1)")      # BL-323: the day's zip
        return f.parent / f"creaite-backup-{day}.zip"

    def offsite(self):
        return self.root / "_Portfolio" / "99 System" / "creaite backups"

    def copy(self):
        return self.py("import tracker; print(json.dumps(tracker.offsite_copy()))")

    def test_the_newest_daily_backup_is_copied_atomically_and_the_live_database_never_is(self):
        self.daily("2026-10-01")
        newest = self.daily("2026-10-02")
        out = self.copy()
        self.assertEqual(out["error"], None)
        self.assertEqual(out["copied"], "projects/_portfolio/99 System/creaite backups/creaite-backup-2026-10-02.zip")
        self.assertEqual(sorted(p.name for p in self.offsite().iterdir()), ["creaite-backup-2026-10-02.zip"])   # the newest only; no temporary file left
        self.assertEqual((self.offsite() / "creaite-backup-2026-10-02.zip").read_bytes(), newest.read_bytes())
        self.assertFalse((self.root / "_Portfolio" / "tracker.db").exists())
        self.assertFalse(list(self.root.rglob("tracker.db")))                                       # the live database is never in the projects folder
        self.assertEqual(self.copy()["copied"], None)                                               # already there: nothing to do

    def test_the_copy_itself_removes_nothing(self):
        import datetime
        start = datetime.date(2026, 9, 1)
        for n in range(20):
            self.daily((start + datetime.timedelta(days=n)).isoformat())
            self.copy()
        kept = sorted(p.name for p in self.offsite().iterdir())
        self.assertEqual(len(kept), 20)                                       # BL-323: the "latest 14" rule is retired
        self.assertEqual(kept[-1], "creaite-backup-2026-09-20.zip")
        self.assertEqual(len(list((self.v.root / "system/backups").glob("tracker-2026-*.db"))), 20)      # local copies all stay

    def test_the_session_start_makes_the_copy_and_says_when_it_cannot(self):
        r = self.v.run("start", "--force", script="session.py")
        self.assertTrue(list(self.offsite().glob("creaite-backup-*.zip")))                          # the day's zip was copied
        shutil.rmtree(self.root / "_Portfolio" / "99 System")
        os.rename(self.root, self.root.parent / "Engagements-away")                                # OneDrive not reachable
        try:
            out = self.copy()
        finally:
            os.rename(self.root.parent / "Engagements-away", self.root)
        self.assertIn("isn't reachable", out["error"])

    def test_doctor_reports_the_last_copy(self):
        d = self.v.run("doctor.py", script="doctor.py", ok=False)
        self.assertRegex(d.stdout, r"WARN  Off-laptop backup copy — no copy yet")
        self.v.run("start", "--force", script="session.py")
        d = self.v.run("doctor.py", script="doctor.py", ok=False)
        self.assertRegex(d.stdout, r"PASS  Off-laptop backup copy — last copy \d\d-\d\d-\d{4}")

    def test_the_folders_are_made_on_first_use_and_a_missing_one_never_stops_the_backup(self):
        self.assertFalse((self.root / "_Portfolio" / "99 System").exists())                       # neither folder exists yet
        self.daily("2026-10-02")
        out = self.copy()
        self.assertEqual((out["error"], bool(out["copied"])), (None, True))
        self.assertTrue(self.offsite().is_dir())
        shutil.rmtree(self.root / "_Portfolio" / "99 System")                                        # gone again: made again, no failure
        self.daily("2026-10-03")
        self.assertEqual(self.copy()["error"], None)
        self.assertEqual([p.name for p in self.offsite().iterdir()], ["creaite-backup-2026-10-03.zip"])
        r = self.v.run("start", "--force", script="session.py")
        self.assertNotIn("not made", r.stdout)

    def test_doctor_warns_only_when_the_folder_cannot_be_written(self):
        self.v.run("start", "--force", script="session.py")
        self.assertIn("PASS  Off-laptop backup copy — last copy", self.v.run("doctor.py", script="doctor.py", ok=False).stdout)
        shutil.rmtree(self.root / "_Portfolio" / "99 System")
        portfolio = self.root / "_Portfolio"
        portfolio.chmod(0o555)                                                                       # the nearest folder that exists can't be written
        try:
            d = self.v.run("doctor.py", script="doctor.py", ok=False).stdout
        finally:
            portfolio.chmod(0o755)
        self.assertRegex(d, r"WARN  Off-laptop backup copy — can't write to _Portfolio/99 System/creaite backups")

    def test_doctor_names_the_old_folder_only_once_the_new_one_holds_a_copy(self):
        old = self.root / "_Portfolio" / "creaite backups"
        old.mkdir(parents=True)
        for n in (1, 2, 3):
            (old / f"tracker-2026-09-0{n}.db").write_bytes(b"x")
        d = self.v.run("doctor.py", script="doctor.py", ok=False).stdout
        self.assertIn("no copy yet", d)
        self.assertNotIn("old folder", d)                                                            # nothing in the new folder yet
        self.v.run("start", "--force", script="session.py")
        d = self.v.run("doctor.py", script="doctor.py", ok=False).stdout
        self.assertRegex(d, r"WARN  Off-laptop backup copy — last copy \d\d-\d\d-\d{4}; the old folder _Portfolio/creaite backups still holds 3 copies and can be removed")
        self.assertEqual(len(list(old.glob("tracker-*.db"))), 3)                                     # creaite never touches them

    def test_99_system_is_never_listed_indexed_or_read_even_with_the_old_list_saved(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"]["never_index"] = ["_Archive", "_Templates"]                              # a list saved by an older release
        cfg.write_text(json.dumps(data))
        hidden = touch(self.root / "_Portfolio" / "99 System" / "creaite backups" / "tracker-2026-10-01.db")
        notes = touch(self.root / "_Portfolio" / "99 System" / "notes.md", "system file")
        touch(self.root / "_Portfolio" / "Strategy" / "plan.md", "a plan")
        o = self.py("""import paths
print(json.dumps({'never': paths.never_index(), 'docs': [paths.rel(f) for f in paths.document_files('_portfolio')],
                  'patterns': paths.never_index_patterns(), 'problem': paths.project_path_problem('projects/_portfolio/99 System/notes.md')}))""")
        self.assertEqual(o["never"], ["_Archive", "_Templates", "99 System"])
        self.assertTrue(any("Strategy/plan.md" in f for f in o["docs"]))
        self.assertFalse(any("99 System" in f for f in o["docs"]))
        self.assertIn("**/99 System/**", o["patterns"])
        self.assertIn("99 System is never read or written", o["problem"])
        self.v.run("index")
        found = json.loads(self.v.run("query", "system file", script="tracker.py").stdout)
        self.assertFalse(any("99 System" in str(r) for r in found))
        self.assertTrue(hidden.exists() and notes.exists())

    def test_nothing_happens_when_the_projects_are_in_the_vault(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"]["projects_root"] = ""
        cfg.write_text(json.dumps(data))
        self.daily("2026-10-02")
        self.assertEqual(self.copy(), {"copied": None, "error": None})
        d = self.v.run("doctor.py", script="doctor.py", ok=False)
        self.assertIn("PASS  Off-laptop backup copy — not used", d.stdout)


class DoctorTests(OneDriveCase):
    """BL-85 item 6: doctor's checks for a projects folder, and online-only (OneDrive placeholder) files."""

    def doctor(self):
        r = self.v.run("doctor.py", script="doctor.py", ok=False)
        return {ln.split("  ", 1)[1].split(" — ")[0]: ln.split("  ", 1)[0] for ln in r.stdout.splitlines() if ln[:4] in ("PASS", "WARN", "FAIL")}, r.stdout

    def test_a_healthy_projects_folder_passes(self):
        got, out = self.doctor()
        for name in ("Projects folder reachable", "Projects folders present", "Vault is local, not synced", "Online-only files",
                     "Extraction never reads documents/ or reports/"):
            self.assertEqual(got[name], "PASS", out)
        self.assertIn(f"{ROOT_SETTING} (company onedrive)", out)

    def test_an_unreachable_root_fails_and_a_missing_mapped_folder_warns(self):
        shutil.rmtree(self.eng("ABC", "04 Reporting", "Weekly"))
        got, out = self.doctor()
        self.assertEqual(got["Projects folders present"], "WARN")
        self.assertEqual(out.count("ABC: 04 Reporting/Weekly"), 1, out)                    # client reports share it: said once
        os.rename(self.root, self.root.parent / "Engagements-away")
        try:
            got, out = self.doctor()
        finally:
            os.rename(self.root.parent / "Engagements-away", self.root)
        self.assertEqual(got["Projects folder reachable"], "FAIL")
        self.assertIn("isn't reachable", out)

    def test_a_vault_in_a_synced_folder_fails(self):
        o = self.py("""import paths, doctor
from pathlib import Path
paths.ROOT = Path('/Users/x/Library/CloudStorage/OneDrive-TestCo/Documents/creaite')
a = doctor.vault_not_synced()
paths.ROOT = Path('/Users/x/creaite')
print(json.dumps([a[0], doctor.vault_not_synced()[0]]))""")
        self.assertEqual(o, [False, True])

    def test_overlapping_meeting_and_report_folders_fail_the_extraction_check(self):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"]["folders"]["client_reports"] = "02 Meetings/Minutes"
        cfg.write_text(json.dumps(data))
        got, out = self.doctor()
        self.assertEqual(got["Extraction never reads documents/ or reports/"], "FAIL")
        self.assertIn("overlap", out)

    def test_processed_files_must_be_in_a_meeting_folder(self):
        (self.v.root / "system/processed.txt").write_text("2026-10-02 | fp:2026-10-01|x|abc | projects/Example Programme/04 Reporting/Weekly/2026-10-02 Weekly report.docx\n")
        got, out = self.doctor()
        self.assertEqual(got["Extraction never reads documents/ or reports/"], "FAIL")
        self.assertIn("was taken from a report folder", out)

    def test_old_layout_and_keys_with_bars_are_not_flagged(self):
        # a meeting key holds "|", a line can list two files, and entries from before the move point at the old layout
        (self.v.root / "system/processed.txt").write_text(
            "# date processed | file path | items created\n"
            "2026-10-06 | fp:2026-09-28|prep for fal design authority|397e36cee3c0 | projects/FAL Falcon Data Platform/minutes/"
            "2026-09-28 Prep.docx; projects/FAL Falcon Data Platform/transcripts/2026-09-28 Prep.docx | 0\n")
        got, out = self.doctor()
        self.assertEqual(got["Extraction never reads documents/ or reports/"], "PASS", out)

    def test_online_only_files_are_skipped_and_listed_never_read(self):
        touch(self.eng("ABC", "02 Meetings", "Transcripts", "Here-20261001.docx"), "here")
        touch(self.eng("ABC", "02 Meetings", "Transcripts", "ONLINE-There-20261002.docx"), "placeholder")
        touch(self.eng("ABC", "02 Meetings", "Minutes", "ONLINE-2026-10-03 Minutes.docx"), "placeholder")
        touch(self.eng("ABC", "00 Admin", "Contract", "ONLINE-SOW.docx"), "placeholder")
        o = self.py("""import paths, minutes, tracker, doctor, build_dashboard as bd
paths.is_online_only = lambda p: p.name.startswith('ONLINE-')            # what a OneDrive placeholder looks like
reads = []
real = tracker.text_of
tracker.text_of = lambda f: (reads.append(f.name), real(f))[1]
tracker.build_index()
ok, detail = doctor.online_only()
print(json.dumps({'new': [r['title'] for r in minutes.meeting_files('ABC')], 'indexed': sorted(f.name for f, k, c in tracker.index_files()),
                  'read': sorted(set(reads)), 'doctor': [ok, detail], 'files_view': sorted(f['n'] for f in bd.files({'ABC': paths.project_dir('ABC')}))}))""")
        self.assertEqual(o["new"], ["Here"])                                                      # never offered for extraction
        self.assertEqual(o["indexed"], ["Here-20261001.docx"])                                   # not indexed, not read
        self.assertEqual(o["read"], ["Here-20261001.docx"])
        self.assertIn("ONLINE-There-20261002.docx", o["files_view"])                              # but still listed in the Files view
        self.assertIsNone(o["doctor"][0])                                                        # a warning, with the fix
        self.assertIn("3 online-only file(s), not read or indexed", o["doctor"][1])
        self.assertIn("Always keep on this device", o["doctor"][1])

    def test_the_real_check_reads_the_dataless_flag_or_zero_blocks(self):
        f = touch(self.eng("ABC", "02 Meetings", "Transcripts", "Real-20261001.docx"), "content")
        o = self.py(f"""import paths
from pathlib import Path
from unittest import mock
p = Path({str(f)!r})
real = Path.stat
class St:
    def __init__(self, flags, size, blocks): self.st_flags, self.st_size, self.st_blocks, self.st_mtime = flags, size, blocks, 0
out = [paths.is_online_only(p)]
with mock.patch.object(Path, 'stat', lambda self, **k: St(0x40000000, 100, 8) if self == p else real(self, **k)): out.append(paths.is_online_only(p))
with mock.patch.object(Path, 'stat', lambda self, **k: St(0, 100, 0) if self == p else real(self, **k)): out.append(paths.is_online_only(p))
with mock.patch.object(Path, 'stat', lambda self, **k: St(0, 0, 0) if self == p else real(self, **k)): out.append(paths.is_online_only(p))
print(json.dumps(out))""")
        self.assertEqual(o, [False, True, True, False])          # a normal file; dataless; size but no blocks; an empty file is not a placeholder


if __name__ == "__main__":
    unittest.main()

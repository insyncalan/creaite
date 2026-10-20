"""BL-101 (Sprint 4b): the full project name everywhere, the short code only as the prefix of a work item's ID.

Run: python3 dev/tests/test_project_names.py   (the page tests need Google Chrome; skipped otherwise)

The dashboard is rendered with the sample projects (ABC "Example Programme", DEF "Digital Enablement": names that can't be mistaken
for their codes) and every visible word is scanned for a bare code. Exceptions, by design: a work item's ID ("ABC-A-003"), where a code
is defined or typed (Settings › Projects, the Add project form, search and filter boxes, commands), file paths and names, and the
command a reminder tells Alan to say. The Word reports and the lines creaite prints are checked below the page tests.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

SCAN = r"""(()=>{ const codes=P.map(p=>p.code), re=new RegExp("(?<![A-Za-z0-9_#=/.\\-])("+codes.join("|")+")(?![A-Za-z0-9_])(?!-[A-Z0-9])","g");
  const root=document.getElementById(ROOT)||document.body, out=[];
  const skip=el=>el.closest("[data-codeok],[data-openfile],script,style,textarea,input,code,kbd,.kbd,.hp-say,#cmdkIn");
  const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  for(let n=w.nextNode();n;n=w.nextNode()){ const el=n.parentElement; if(!el||skip(el)) continue;
    if(el.tagName!=="OPTION"&&!el.getClientRects().length) continue; if(el.tagName==="OPTION"&&!el.closest("select")) continue;
    for(const m of n.textContent.matchAll(re)) out.push((n.textContent.slice(Math.max(0,m.index-30),m.index+40)).replace(/\s+/g," ").trim()); }
  return out; })()"""


class Page(LiveBrowserCase):
    shared_server = True
    width, height = 1500, 1000

    LITERAL = ("ABC Steering", "ABC weekly sync")        # titles from the sample data: a meeting's own name, not a project reference

    def codes_shown(self, root):
        found = self.b.eval(f"(()=>{{ const ROOT={root!r}; return {SCAN}; }})()")
        return [x for x in found if not any(t in x for t in self.LITERAL)]

    def view(self, name, arg=None, wait="true"):
        a = json.dumps(arg)
        self.b.eval(f"go({name!r}, {a})")
        self.b.wait(wait)
        self.b.pump(0.3)

    def assert_clean(self, root, label):
        shown = self.codes_shown(root)
        self.assertEqual(shown, [], f"{label}: a bare project code is on screen")

    # ── every view ──
    def test_today(self):
        self.view("today")
        self.assert_clean("v-today", "Today")

    def test_projects_list(self):
        self.view("projects")
        self.assert_clean("v-projects", "Projects")

    def test_a_project_page(self):
        self.view("cockpit", "ABC", "document.querySelector('#v-cockpit h1')")
        self.assert_clean("v-cockpit", "Project page")
        self.assertIn("Example Programme", self.b.eval("document.querySelector('#v-cockpit h1').textContent"))

    def test_work_lists_filters_and_board(self):
        for tab in ("actions", "raid", "decisions"):
            self.b.eval(f"WT={tab!r}; go('work'); renderWork()")
            self.b.pump(0.3)
            self.assert_clean("v-work", f"Work {tab}")
            self.b.eval("document.querySelector('#projBtn')&&document.querySelector('#projBtn').click()")      # the open Project menu
            self.b.pump(0.2)
            self.assert_clean("v-work", f"Work {tab}, Project menu")
            self.b.eval("document.body.click()")
        self.b.eval("WT='actions'; PROJF.clear(); PROJF.add('ABC'); go('work'); renderWork()")
        self.b.pump(0.3)
        self.assert_clean("v-work", "Work filtered to a project")
        self.b.eval("PROJF.clear(); setLayout('actions','board')")
        for g in ("due", "status", "owner", "milestone"):
            pick = 'PROJF.add("ABC");' if g == "milestone" else ""        # outside the f-string: Python 3.9 has no backslash there
            self.b.eval(f"WGRP.actions={g!r}; PROJF.clear(); {pick} renderWork()")
            self.b.pump(0.3)
            self.assert_clean("v-work", f"Work board by {g}")
        self.b.eval("PROJF.clear(); setLayout('actions','list')")

    def test_the_side_panel_and_new_item_form(self):
        self.b.eval("go('work'); WT='actions'; renderWork()")
        self.b.pump(0.3)
        self.b.eval("openRecord('actions', A[0].id)")
        self.b.pump(0.4)
        self.assert_clean("panel", "Item panel (read)")
        self.b.eval("EDITING=true; drawPanel()")
        self.b.pump(0.3)
        self.assert_clean("panel", "Item panel (edit)")
        self.b.eval("EDITING=false; closePanel(); openNew('actions')")
        self.b.pump(0.4)
        self.assert_clean("panel", "New action")
        self.b.eval("closePanel()")

    def test_intake_and_files_and_activity_and_people(self):
        for v, root in (("intake-review", "v-intake-review"), ("files", "v-files"), ("activity", "v-activity"), ("people", "v-people")):   # #232 C2: Review and Intake are one page
            self.view(v)
            self.assert_clean(root, v)

    def test_a_person_page(self):
        self.b.eval("go('person', 'Sara Example')")
        self.b.pump(0.4)
        self.assert_clean("v-person", "Person page")

    def test_the_command_palette_and_search(self):
        self.b.eval("openCk(); document.getElementById('cmdkIn').value=''; CK=ckItems(''); drawCk()")
        self.b.pump(0.3)
        self.assert_clean("cmdk", "Command palette")
        self.b.eval("document.getElementById('cmdk').close()")

    def test_the_draft_email_and_help_and_settings(self):
        self.b.eval("go('today'); openDraftEmail('Sara Example')")
        self.b.pump(0.6)
        self.assert_clean("deDlg", "Draft email")
        self.assertEqual(self.b.eval("document.getElementById('deDlg').querySelectorAll('.pph').length>0"), True)
        self.b.eval("document.getElementById('deDlg').close()")
        self.view("help")
        self.assert_clean("v-help", "Help")
        for cat in ("essentials", "people", "advanced", "health"):          # BL-320
            self.b.eval(f"go('settings',{cat!r})")
            self.b.pump(0.3)
            self.assert_clean("v-settings", f"Settings {cat}")

    def test_a_project_filter_chip_and_the_open_menu_use_the_name(self):
        self.b.eval("WT='actions'; PROJF.clear(); PROJF.add('ABC'); go('work'); renderWork()")
        self.b.pump(0.3)
        self.assertIn("Example Programme", self.b.eval("document.getElementById('projBtn').textContent"))
        self.assertIn("Example Programme", self.b.eval("document.getElementById('wapplied').textContent"))
        self.b.eval("PROJF.clear(); renderWork()")

    def test_reminders_say_the_name_and_keep_the_code_in_the_command(self):
        texts = self.b.eval("(D.reminders||[]).map(r=>[r.text||'', r.cmd||''])")
        for text, cmd in texts:
            self.assertNotRegex(text, r"\b(ABC|DEF)\b", text)               # the sentence uses the project's name
            self.assertRegex(cmd, r"\b(ABC|DEF)\b")                         # the command Alan can run keeps the code
        self.assertTrue(any("Example Programme" in t for t, _ in texts) or not texts)

    def test_settings_projects_may_show_the_code_as_the_code(self):
        self.b.eval("go('settings','projects')")
        self.b.pump(0.3)
        self.assertRegex(self.b.eval("document.getElementById('settingsBody').innerText"), r"\bABC\b")        # where a code is defined, it is shown


class Prints(unittest.TestCase):
    """What creaite writes and prints for a person to read."""

    @classmethod
    def setUpClass(cls):
        from test_tracker import Vault
        cls.v = Vault()
        populate(cls.v)

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def script(self, name, *args):
        return subprocess.run([sys.executable, str(self.v.root / "system/scripts" / name), *args], cwd=self.v.root, capture_output=True, text=True)

    def test_the_session_start_lines_say_the_name_and_keep_the_code_in_the_command(self):
        out = self.script("session.py", "start", "--force").stdout
        lines = [ln for ln in out.splitlines() if "report" in ln and " is due" in ln]
        self.assertTrue(lines)
        for line in lines:
            text, _, command = line.partition(" — say ")
            self.assertNotRegex(text, r"\b(ABC|DEF)\b", line)
            self.assertRegex(command, r"\b(ABC|DEF)\b", line)
            self.assertRegex(text, r"Example Programme|Digital Enablement")

    def test_the_review_lists_group_by_name(self):
        out = self.script("review.py", "pending").stdout + self.script("review.py", "list").stdout
        self.assertNotRegex(out.split("ABC-")[0], r"(^|\n)(## )?(ABC|DEF)[: ]")

    def test_a_one_off_document_names_the_project_in_its_table_and_headings(self):
        code = ("import sys, json; sys.path.insert(0,'system/scripts'); import report; "
                "spec={'title':'Open actions','sections':[{'heading':'By project','tracker':{'table':'actions','group_by':'project'}},"
                "{'heading':'With the project column','tracker':{'table':'actions','columns':['id','project','description']}}]}; "
                "print(json.dumps(report.adhoc_spec(spec)))")
        out = json.loads(subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True).stdout.strip().splitlines()[-1])
        headings = [sec.get("heading") for sec in out["sections"]]
        self.assertIn("Example Programme", headings)
        self.assertIn("Digital Enablement", headings)
        self.assertNotIn("ABC", headings)
        table = next(sec["table"] for sec in out["sections"] if sec.get("heading") == "With the project column")
        self.assertIn("Example Programme", [row[1] for row in table["rows"]])
        self.assertNotIn("ABC", [row[1] for row in table["rows"]])

    def test_report_file_names_use_the_project_name(self):
        code = ("import sys; sys.path.insert(0,'system/scripts'); import report; "
                "print(report.report_file('2026-10-09', 'Weekly report', 'Example Programme'), "
                "report.report_file('2026-10-09', 'Client report', 'A/B: test? name'))")
        out = subprocess.run([sys.executable, "-c", code], cwd=self.v.root, capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "2026-10-09 Weekly report - Example Programme.docx 2026-10-09 Client report - A B test name.docx")

    def test_the_earlier_file_names_are_still_recognised_as_filed(self):
        folder = next((self.v.root / "projects").glob("ABC *")) / "reports"
        folder.mkdir(exist_ok=True)
        (folder / "2026-10-02 Weekly report.docx").write_text("x")                  # named the earlier way: never renamed, still counts
        out = self.script("report.py", "weekly-data", "ABC", "--week-ending", "2026-10-02").stdout
        self.assertTrue(json.loads(out[out.index("{"):])["already_filed"])


if __name__ == "__main__":
    unittest.main()

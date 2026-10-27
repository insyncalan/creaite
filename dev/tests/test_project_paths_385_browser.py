"""#385 phase 2 in a real browser: Project settings shows a project's real folder and sets or clears its own folder
(locations.project_paths, through the settings save and the server's checks), Today says when one can't be reached, and
Settings › Undo update warns before going back to an engine that doesn't read the setting.

Fictional and temporary: a fake home holding a OneDrive-style projects folder (DEF "Digital Enablement" in it) and ABC's folder of
its own at ~/Work/Acme/Programme. The live server and the scripts run with that home.

Run: python3 dev/tests/test_project_paths_385_browser.py   (needs Google Chrome; skipped otherwise)
"""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_dashboard  # noqa: E402
from live_browser import LiveBrowserCase  # noqa: E402

TENANT = "OneDrive-TestCo"
ROOT_SETTING = f"~/Library/CloudStorage/{TENANT}/Documents/Engagements"
ABC, DEF = "ABC Example Programme", "DEF Digital Enablement"
OWN = "~/Work/Acme/Programme"
FOLDERS = {"minutes": "minutes", "transcripts": "transcripts", "weekly_reports": "reports", "client_reports": "reports",
           "adhoc_documents": "reports", "images": "images", "steerco": "steerco", "agendas": "agendas", "notes": "notes"}
HOME = {"dir": None}


class OwnFolderPage(LiveBrowserCase):
    shared_server = False

    @classmethod
    def server_env(cls):
        return {"HOME": HOME["dir"]}

    @classmethod
    def load(cls, v):
        test_dashboard.populate(v)
        home = Path(HOME["dir"])
        root = home / "Library" / "CloudStorage" / TENANT / "Documents" / "Engagements"
        root.mkdir(parents=True)
        shutil.move(str(v.root / "projects/_portfolio"), str(root / "_Portfolio"))
        shutil.move(str(v.root / "projects" / DEF), str(root / DEF))
        (home / "Work" / "Acme").mkdir(parents=True)
        shutil.move(str(v.root / "projects" / ABC), str(home / "Work" / "Acme" / "Programme"))
        cfg = v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data["locations"] = dict(data.get("locations") or {}, projects_root=ROOT_SETTING, portfolio="_Portfolio",
                                 folders=FOLDERS, project_paths={ABC: OWN})
        cfg.write_text(json.dumps(data, indent=2))
        v.run(script="build_dashboard.py")

    def setUp(self):
        HOME["dir"] = tempfile.mkdtemp(prefix="creaite-home-")
        self.addCleanup(shutil.rmtree, HOME["dir"], True)
        self._home = os.environ.get("HOME")
        os.environ["HOME"] = HOME["dir"]
        self.addCleanup(lambda: os.environ.__setitem__("HOME", self._home) if self._home else os.environ.pop("HOME", None))
        super().setUp()
        self.home = Path(HOME["dir"])
        self.b.eval("window.__errs=[]; addEventListener('error',e=>__errs.push(e.message))")

    def saved(self):
        return json.loads((self.v.root / "system/config/settings.json").read_text())["locations"].get("project_paths")

    def open(self, code):
        self.b.eval(f"go('psettings', {code!r}); psCat.value='general'; navWrite(false)")
        self.b.wait("VIEW==='psettings' && !!document.querySelector('#psFolder')")
        time.sleep(0.3)

    def text(self, sel):
        return self.b.eval(f"(document.querySelector({sel!r})||{{}}).textContent||''")

    def type_and_save(self, value):
        self.b.eval(f"(()=>{{ const el=document.querySelector('#psOwn'); el.scrollIntoView({{block:'center'}}); el.value={value!r}; }})()")
        self.b.click("#psOwnSave")

    def test_the_folder_row_set_refuse_and_save(self):
        self.open("ABC")
        self.assertEqual(self.text("#psFolder"), OWN)
        self.assertEqual(self.b.eval("document.querySelector('#psOwn').value"), OWN)
        self.open("DEF")
        self.assertEqual(self.text("#psFolder"), f"{ROOT_SETTING}/{DEF}")
        self.assertEqual(self.b.eval("document.querySelector('#psOwn').value"), "")
        self.type_and_save("/Users/someone/Work/Digital")                     # refused on the page
        self.b.wait("(document.querySelector('#psOwnErr')||{}).textContent.includes('~')")
        self.type_and_save(OWN + "/Sub")                                       # refused by the server: inside ABC's folder
        self.b.wait("(document.querySelector('#psOwnErr')||{}).textContent.includes('inside')", 15)
        self.assertEqual(self.saved(), {ABC: OWN})
        (self.home / "Work" / "Other").mkdir(parents=True)
        root = self.home / "Library" / "CloudStorage" / TENANT / "Documents" / "Engagements"
        shutil.move(str(root / DEF), str(self.home / "Work" / "Other" / "Digital"))
        self.type_and_save("~/Work/Other/Digital/")
        deadline = time.time() + 15
        while time.time() < deadline and self.saved() != {ABC: OWN, DEF: "~/Work/Other/Digital"}:
            time.sleep(0.2)
        self.assertEqual(self.saved(), {ABC: OWN, DEF: "~/Work/Other/Digital"})
        self.b.wait("(document.querySelector('#psFolder')||{}).textContent==='~/Work/Other/Digital'", 15)
        self.b.wait("!!document.querySelector('#psOwnClear')")
        self.b.eval("document.querySelector('#psOwnClear').scrollIntoView({block:'center'})")
        self.b.click("#psOwnClear")
        deadline = time.time() + 15
        while time.time() < deadline and self.saved() != {ABC: OWN}:
            time.sleep(0.2)
        self.assertEqual(self.saved(), {ABC: OWN})                             # ABC's entry kept
        self.assertEqual(self.b.eval("__errs"), [])

    def test_today_says_when_a_folder_cant_be_reached_and_creates_nothing(self):
        own = self.home / "Work" / "Acme" / "Programme"
        shutil.move(str(own), str(self.home / "Work" / "Acme" / "Elsewhere"))
        self.b.eval("reloadData().then(()=>{ go('today'); renderToday(); })")
        self.b.wait("!document.querySelector('#ownFolders').hidden", 15)
        t = self.text("#ownFolders")
        self.assertIn("Example Programme's folder can't be reached", t)
        self.assertIn(OWN, t)
        self.assertNotIn("ABC", t)                                             # projects by name
        self.assertFalse(own.exists())

    def test_undo_update_warns_with_the_names(self):
        w = self.b.eval("undoOwnFoldersWarning('2.6.8')")
        self.assertIn("Example Programme", w)
        self.assertIn("Nothing is lost", w)
        self.assertEqual(self.b.eval("undoOwnFoldersWarning('2.6.10')"), "")


if __name__ == "__main__":
    unittest.main()

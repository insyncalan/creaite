"""#374 piece 2 (Alan, 27-10-2026): Show in Finder reveals the FILE (selects it in its folder), not its parent folder.

Run: python3 dev/tests/test_reveal_in_finder_374.py

No guarded change: the page uses the existing token-checked POST /api/report/reveal (report_server.reveal_route, also used by the
report export's Show in Finder), whose path rule is widened to projects/, inbox/ and system/staging/drafts/ (REVEAL_OK).
Two halves:
  - the page's request (core/finderReveal.js, run by node; skipped without node): with the FINDER_REVEAL switch (on) the
    file is sent to the reveal route, otherwise its parent folder to /api/open; where no button is offered; a Deleted row (or an
    undone create) offers none;
  - the route itself, in process (a vault subprocess with subprocess.Popen, sys.platform and os.name patched, CREAITE_NO_LAUNCH
    unset): the exact argv on macOS, Windows and Linux for a file and a folder, never shell=True, odd names (leading dash, comma,
    quotes, spaces) as one argument, every refusal launches nothing (the checks run first), and a symlink inside projects/ that
    leads outside projects/, inbox/ and system/staging/drafts/ is refused (an inside one is allowed).
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_tracker import Vault  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
MOD = ROOT / "system/templates/dashboard/src/core/finderReveal.js"
PATHS = ["projects/ABC Example Programme/minutes/2026-10-20 Steering.docx", "projects/_portfolio/notes/New name.md",
         "inbox/Loose file.txt", "system/staging/drafts/Draft.docx", "CLAUDE.md", "system/config/settings.json",
         "projects/ABC Example Programme/../../system/tracker.db", "", "projects/"]


class PageRequest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("node"):
            raise unittest.SkipTest("needs node")
        d = Path(tempfile.mkdtemp())
        shutil.copy(MOD, d / "finder.mjs")
        (d / "run.mjs").write_text('import * as F from "./finder.mjs"; const ps=JSON.parse(process.argv[2]);'
                                   'const rows=[{op:"edit"},{op:"delete"},{op:"delete",undone:1},{op:"create"},{op:"create",undone:1},{op:"move"}];'
                                   'console.log(JSON.stringify({show:rows.map(F.finderCanShow),sw:F.FINDER_REVEAL,rev:ps.map(p=>F.finderRequest(p,true)),'
                                   'old:ps.map(p=>F.finderRequest(p,false)),dflt:ps.map(p=>F.finderRequest(p))}));')
        r = subprocess.run(["node", str(d / "run.mjs"), json.dumps(PATHS)], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
        cls.out = json.loads(r.stdout)
        shutil.rmtree(d, ignore_errors=True)

    def test_reveal_sends_the_file(self):
        rev = self.out["rev"]
        self.assertEqual(rev[0], {"path": PATHS[0], "reveal": True})
        self.assertEqual(rev[1], {"path": PATHS[1], "reveal": True}, "a move: the target file")
        self.assertEqual(rev[3], {"path": PATHS[3], "reveal": True})

    def test_a_file_directly_in_intake_can_now_be_shown_but_nothing_the_server_refuses(self):
        rev = self.out["rev"]
        self.assertEqual(rev[2], {"path": PATHS[2], "reveal": True}, "the allow list now judges the file, and inbox/<file> is allowed")
        for i in (4, 5, 6, 7, 8):
            self.assertIsNone(rev[i], PATHS[i])

    def test_without_reveal_it_is_todays_parent_folder(self):
        old = self.out["old"]
        self.assertEqual(old[0], {"path": "projects/ABC Example Programme/minutes"})
        self.assertEqual(old[1], {"path": "projects/_portfolio/notes"})
        self.assertIsNone(old[2], "inbox/<file>: its folder is 'inbox', which the server refuses")
        for i in (4, 5, 6, 7, 8):
            self.assertIsNone(old[i], PATHS[i])
        for o in old:
            self.assertTrue(o is None or "reveal" not in o)

    def test_a_deleted_row_or_an_undone_create_offers_no_button(self):
        self.assertEqual(self.out["show"], [True, False, True, True, False, True])

    def test_the_switch_is_on(self):
        self.assertIs(self.out["sw"], True)

    def test_the_default_follows_the_one_switch(self):
        self.assertEqual(self.out["dflt"], self.out["rev"] if self.out["sw"] else self.out["old"])


SCRIPT = r'''
import json, os, sys, types
from pathlib import Path
root = Path(sys.argv[1]); sys.path.insert(0, str(root / "system/scripts"))
os.environ.pop("CREAITE_NO_LAUNCH", None)
import paths, report_server as rs
calls = []
class Fake:
    def __init__(self, *a, **kw): calls.append({"a": [list(x) if isinstance(x, list) else x for x in a], "kw": sorted(kw)})
rs.subprocess = types.SimpleNamespace(Popen=Fake)
class OS:
    def __init__(self, name): self.name = name
    def __getattr__(self, k): return getattr(os, k)
class SYS:
    def __init__(self, plat): self.platform = plat
class H:
    def send(self, st, body): self.out = (st, body)
def reveal(plat, name, rel):
    rs.sys, rs.os = SYS(plat), OS(name)
    del calls[:]; h = H()
    rs.reveal_route(h, {"path": rel})
    return {"ok": h.out[1]["ok"], "launched": h.out[1].get("launched"), "calls": list(calls)}
proj = "projects/ABC Test"
names = ["plain.docx", "-n x.docx", "--help.docx", "a,b.docx", "it's.docx", 'say "hi".docx', "two  spaces.docx"]
files = [f"{proj}/minutes/{n}" for n in names] + ["inbox/Loose, file.txt", "system/staging/drafts/Draft.docx"]
folders = [f"{proj}/minutes"]
out = {"ok": {}, "refused": {}}
for plat, name in (("darwin", "posix"), ("win32", "nt"), ("linux", "posix")):
    for rel in files + folders:
        out["ok"][plat + "|" + rel] = reveal(plat, name, rel)
bad = ["system/tracker.db", "CLAUDE.md", "system/config/settings.json", "system/logs/debug.log", "system/backups/x.db", "system/staging/proposed-x.json",
       "projects/../CLAUDE.md", f"{proj}/../../CLAUDE.md", f"{proj}/minutes/Missing.docx", "", "projects/", "inbox/", "system/staging/drafts/",
       f"{proj}/out-link", f"{proj}/out-dir-link/secret.txt", f"{proj}/out-dir-link"]
for plat, name in (("darwin", "posix"), ("win32", "nt"), ("linux", "posix")):
    for rel in bad:
        out["refused"][plat + "|" + rel] = reveal(plat, name, rel)
out["inside_link"] = reveal("linux", "posix", f"{proj}/in-link")
out["root"] = str(root)
print(json.dumps(out))
'''



class RouteLaunch(unittest.TestCase):
    """report_server.reveal_route run in process, with the launch and the platform patched."""

    @classmethod
    def setUpClass(cls):
        cls.v = v = Vault()
        r = v.root
        for rel in ("projects/ABC Test/minutes", "inbox", "system/staging/drafts", "system/logs", "system/backups", "system/config"):
            (r / rel).mkdir(parents=True, exist_ok=True)
        for n in ("plain.docx", "-n x.docx", "--help.docx", "a,b.docx", "it's.docx", 'say "hi".docx', "two  spaces.docx"):
            (r / "projects/ABC Test/minutes" / n).write_text("x", encoding="utf-8")
        for rel in ("inbox/Loose, file.txt", "system/staging/drafts/Draft.docx", "system/logs/debug.log", "system/backups/x.db",
                    "system/staging/proposed-x.json", "system/config/settings.json"):
            (r / rel).write_text("x", encoding="utf-8")
        cls.outside = Path(tempfile.mkdtemp())
        (cls.outside / "secret.txt").write_text("x", encoding="utf-8")
        proj = r / "projects/ABC Test"
        (proj / "out-link").symlink_to(cls.outside / "secret.txt")
        (proj / "out-dir-link").symlink_to(cls.outside, target_is_directory=True)
        (proj / "in-link").symlink_to(proj / "minutes" / "plain.docx")
        res = subprocess.run([sys.executable, "-c", SCRIPT, str(r)], capture_output=True, text=True, cwd=str(r), timeout=120)
        assert res.returncode == 0, res.stderr
        cls.out = json.loads(res.stdout.strip().splitlines()[-1])

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.outside, ignore_errors=True)
        cls.v.cleanup()

    def argv(self, plat, rel):
        root = self.v.root
        real = str(root / rel)
        is_file = (root / rel).is_file()
        if plat == "darwin":
            return ["open", "-R", real] if is_file else ["open", real]
        if plat == "win32":
            return ["explorer", "/select,", real] if is_file else ["explorer", real]
        return ["xdg-open", str(Path(real).parent) if is_file else real]

    def test_the_exact_launch_on_each_platform_for_a_file_and_a_folder(self):
        self.assertTrue(self.out["ok"])
        for key, r in self.out["ok"].items():
            plat, rel = key.split("|", 1)
            self.assertEqual((r["ok"], r["launched"]), (True, True), key)
            self.assertEqual(len(r["calls"]), 1, key)
            self.assertEqual(r["calls"][0]["a"], [self.argv(plat, rel)], key)

    def test_never_a_shell_and_never_an_option_from_a_name(self):
        for key, r in self.out["ok"].items():
            for c in r["calls"]:
                self.assertEqual(c["kw"], [], f"{key}: no keyword at all, so no shell=True")
                for arg in c["a"][0][1:]:
                    self.assertTrue(arg.startswith("/") or arg == "/select," or arg == "-R", (key, arg))   # absolute, so "-n x.docx" is a path

    def test_linux_opens_the_files_folder_not_the_file(self):
        c = self.out["ok"]["linux|projects/ABC Test/minutes/plain.docx"]["calls"][0]["a"][0]
        self.assertEqual(c, ["xdg-open", str(self.v.root / "projects/ABC Test/minutes")])

    def test_every_refusal_launches_nothing_on_every_platform(self):
        self.assertTrue(self.out["refused"])
        for key, r in self.out["refused"].items():
            self.assertEqual((r["ok"], r["calls"]), (False, []), key)

    def test_a_symlink_leading_outside_is_refused_and_one_leading_inside_is_allowed(self):
        for rel in ("out-link", "out-dir-link/secret.txt", "out-dir-link"):
            self.assertFalse(self.out["refused"]["linux|projects/ABC Test/" + rel]["ok"], rel)
        self.assertTrue(self.out["inside_link"]["ok"])

    def test_nothing_in_system_outside_staging_drafts(self):
        for rel in ("system/tracker.db", "system/config/settings.json", "system/logs/debug.log", "system/backups/x.db", "system/staging/proposed-x.json"):
            self.assertIn("linux|" + rel, self.out["refused"], rel)
            self.assertFalse(self.out["refused"]["linux|" + rel]["ok"], rel)


if __name__ == "__main__":
    unittest.main()

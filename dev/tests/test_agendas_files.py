"""BL-135 (sprint prep-files): Agendas are their own folder in the Files view.

Run: python3 dev/tests/test_agendas_files.py   (the last class needs Google Chrome; skipped otherwise)

  - paths.project_files returns agendas as their own kind, in the default layout and with an outside projects root, whether or not
    documents are walked, and nothing under Documents repeats them;
  - a prep page (HTML) and a Word agenda both appear; subfolders are listed with their path;
  - search still indexes them, as documents (internal);
  - the Files tree shows Agendas beside Minutes and Transcripts with its own count, the Documents switch off.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_onedrive_projects import OneDriveCase, touch  # noqa: E402
from test_tracker import ABC, Vault  # noqa: E402

PAGE = "2026-10-08 Prep - ABC weekly.html"
WORD = "Steering agenda 15 October.docx"


def run_py(vault, code):
    src = f"import sys, json; sys.path.insert(0, {str(vault.root / 'system/scripts')!r})\n{code}"
    r = subprocess.run([sys.executable, "-c", src], capture_output=True, text=True, cwd=tempfile.gettempdir())
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


FILES = """import build_dashboard as bd, paths
print(json.dumps([[f['p'], f['f'], f['n'], f['sub'], f['path']] for f in bd.files({'ABC': paths.project_dir('ABC')}, %s) if f['p'] == 'ABC']))"""


class Checks:
    """The assertions, shared by the two layouts. `agendas(show)` and `search(text)` come from the case."""

    def test_agendas_are_listed_with_documents_off_and_counted_once(self):
        rows = self.agendas(False)
        self.assertEqual(sorted((r[2], r[3]) for r in rows), [(PAGE, ""), ("Notes.docx", "Older"), (WORD, "")])   # a prep page, a Word agenda, a subfolder's
        self.assertEqual(len(rows), len({r[4] for r in rows}))

    def test_nothing_under_documents_repeats_them(self):
        show = self.files(True)
        self.assertEqual(sum(1 for r in show if r[2] == PAGE), 1)
        self.assertEqual(sum(1 for r in show if r[2] == WORD), 1)
        self.assertFalse([r for r in show if r[1] == "documents" and r[2] in (PAGE, WORD, "Notes.docx")])
        self.assertIn(("ABC", "documents", "Plan.md"), {(r[0], r[1], r[2]) for r in show})                          # the documents are still there
        self.assertEqual({r[2] for r in self.agendas(True)}, {r[2] for r in self.agendas(False)})                # the switch changes nothing here

    def test_search_still_indexes_them_as_documents(self):
        o = run_py(self.v, "import tracker\nprint(json.dumps(sorted(paths_kind for paths_kind in set((f.name, k) for f, k, c in tracker.index_files()))))")
        self.assertIn([PAGE, "agendas"], o)
        self.assertIn([WORD, "agendas"], o)
        hit = run_py(self.v, """import search
out = {}
for q in ('steering', 'prep'):
    r = search.search(q, refresh=True)
    out[q] = [[x['title'], x['kind']] for x in r['groups']['documents']]
print(json.dumps(out))""")
        self.assertIn(["Steering agenda 15 October", "document"], hit["steering"])                                 # "Document · internal" still
        self.assertIn(["2026-10-08 Prep - ABC weekly", "document"], hit["prep"])


class DefaultLayout(Checks, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v = Vault()
        populate(cls.v)
        abc = cls.v.root / ABC
        touch(abc / "agendas" / PAGE, "<html><body>prep notes</body></html>")
        touch(abc / "agendas" / WORD)
        touch(abc / "agendas" / "Older" / "Notes.docx")
        touch(abc / "documents" / "Plan.md", "plan")

    @classmethod
    def tearDownClass(cls):
        cls.v.cleanup()

    def files(self, show):
        return run_py(self.v, FILES % show)

    def agendas(self, show):
        return [r for r in self.files(show) if r[1] == "agendas"]

    def test_the_default_layout_has_no_agendas_under_the_portfolio(self):
        o = run_py(self.v, "import build_dashboard as bd\nprint(json.dumps([f['f'] for f in bd.files({}, False) if f['p'] == '_portfolio']))")
        self.assertNotIn("agendas", o)


class OutsideRoot(Checks, OneDriveCase):
    locations = {**OneDriveCase.locations, "folders": {**OneDriveCase.locations["folders"], "agendas": "02 Meetings/Agendas"}}

    def setUp(self):
        super().setUp()
        touch(self.eng("ABC", "02 Meetings", "Agendas", PAGE), "<html><body>prep notes</body></html>")
        touch(self.eng("ABC", "02 Meetings", "Agendas", WORD))
        touch(self.eng("ABC", "02 Meetings", "Agendas", "Older", "Notes.docx"))
        touch(self.eng("ABC", "00 Admin", "Contract", "Plan.md"), "plan")
        touch(self.eng("ABC", "99 Archive", "Agendas", "Never.docx"))                                              # never indexed, whatever the kind

    def files(self, show):
        return run_py(self.v, FILES % show)

    def agendas(self, show):
        return [r for r in self.files(show) if r[1] == "agendas"]

    def test_a_never_indexed_folder_is_still_never_listed(self):
        self.assertNotIn("Never.docx", {r[2] for r in self.files(True)})

    def test_an_online_only_agenda_is_listed_but_never_read(self):
        o = run_py(self.v, """import paths
real = paths.is_online_only
paths.is_online_only = lambda p: p.name == 'Steering agenda 15 October.docx'
print(json.dumps([sorted(f.name for f, k, s in paths.project_files('ABC', online=o) if k == 'agendas') for o in (False, True)]))""")
        self.assertNotIn(WORD, o[0])
        self.assertIn(WORD, o[1])


class FilesTree(LiveBrowserCase):
    shared_server = True

    @classmethod
    def load(cls, v):
        populate(v)
        abc = v.root / ABC
        touch(abc / "agendas" / PAGE, "<html></html>")
        touch(abc / "agendas" / WORD)

    def test_agendas_sit_beside_minutes_and_transcripts_with_their_own_count(self):
        b = self.b
        b.eval("go('files')")
        b.wait("document.querySelector('#tree [data-toggle]')")
        b.eval("document.querySelector('#tree [data-toggle=\"ABC\"]').click()")
        b.wait("document.querySelector('#tree .l2[data-f=\"agendas\"]')")
        order = b.eval("[...document.querySelectorAll('#tree .l2')].filter(x=>x.dataset.p==='ABC').map(x=>x.dataset.f)")
        self.assertEqual(order[:3], ["minutes", "transcripts", "agendas"])
        self.assertNotIn("documents", order)                                                                       # the switch is off; Agendas shows anyway
        self.assertEqual(b.eval("document.querySelector('#tree .l2[data-f=\"agendas\"] .n').textContent"), "2")
        b.eval("document.querySelector('#tree .l2[data-f=\"agendas\"]').click()")
        b.wait("document.querySelectorAll('#filesTbl tbody tr[data-fp]').length===2")
        names = b.eval("[...document.querySelectorAll('#filesTbl tbody tr[data-fp] a')].map(a=>a.textContent)")
        self.assertEqual(sorted(names), sorted([PAGE, WORD]))
        total = b.eval("FILES.length")
        self.assertEqual(int(b.eval("document.querySelector('#tree button[data-p=\"All\"] .n').textContent")), total)   # All files counts them
        self.assertEqual(b.eval("FILES.filter(f=>f.p==='ABC'&&f.f==='agendas').length"), 2)

    def test_the_other_shortcuts_are_unchanged(self):
        b = self.b
        b.eval("go('files')")
        b.wait("document.querySelector('#fmBtn')")
        self.assertEqual(b.eval("FILES.filter(f=>f.f==='minutes'||f.f==='transcripts').length>=0"), True)
        b.eval("(()=>{ if(!document.querySelector('#fmenu.on')) document.querySelector('#fmBtn').click(); document.querySelector('#fmenu input[name=fsView][value=week]').click(); })()")
        self.assertFalse(b.eval("FILES.filter(f=>f.f==='agendas'&&f.date>=WEEKSTART&&(f.f==='minutes'||f.f==='transcripts')).length"))


if __name__ == "__main__":
    unittest.main()

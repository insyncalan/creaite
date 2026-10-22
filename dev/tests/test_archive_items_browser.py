"""BL-10 fixes in the page (v1.9.5, hand checks 26 and 27; board #81): items archived for their age, shown and opened.

- With Show archived projects on, an age-archived item is back in Work and its row is tagged Archived (Files' tag); a live
  item is not. The switch's help, in Settings › Work and reports › Opening views (v2.6), mentions items archived for
  their age.
- Opening an age-archived item from search (switch off) opens it in its panel, as any item; its project is live.
- Opening an archived project's item from search (switch off) says the project is archived and names the real switch and
  where it is.

Run: python3 dev/tests/test_archive_items_browser.py   (needs Google Chrome; skipped otherwise)
"""
import json
import os
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402

LATER = (date.today() + timedelta(days=214)).isoformat() + " 09:00"      # seven months on: the closed action is six months old


def close_and_archive(v):
    """Close ABC's "Book UAT environment" today, then run the archiving seven months on: it is archived for its age."""
    aid = next(r["id"] for r in v.rows("actions") if r["description"] == "Book UAT environment")
    v.propose("close", [{"n": 1, "op": "update", "table": "actions", "id": aid, "changes": {"status": "Closed"},
                         "decision": "approved", "match": "strong", "flags": []}])
    v.run("apply")
    r = subprocess.run([sys.executable, str(v.root / "system/scripts/archive.py"), "items"], cwd=v.root, capture_output=True,
                       text=True, env={**os.environ, "CREAITE_NOW": LATER})
    assert r.returncode == 0 and "Archived 1 item" in r.stdout, r.stdout + r.stderr
    return aid


class AgeArchivedInThePage(LiveBrowserCase):
    quiet_jobs = False        # exercises backups or archiving: keeps the shipped settings

    @classmethod
    def load(cls, v):
        populate(v)
        cls.aid = close_and_archive(v)

    def show_archived(self, on):
        cfg = self.v.root / "system/config/settings.json"
        data = json.loads(cfg.read_text())
        data.setdefault("dashboard", {})["show_archived"] = on
        cfg.write_text(json.dumps(data, indent=2))
        self.b.reload("typeof go==='function' && LIVE")

    def found(self, q, item_id):
        """The search result for this item, as the page gets it from the live server."""
        return self.b.eval(f"searchFetch({json.dumps(q)},[]).then(r=>Object.values(r.groups).flat().find(x=>x.id==={json.dumps(item_id)}))")

    def test_shown_it_is_tagged_archived_in_work(self):
        b = self.b
        self.show_archived(True)
        try:
            b.eval("go('work'); WT='actions'; clearAllFilters(); applyFilters({st:['Closed','Open']}); renderWork()")
            # #241 b: the Closed group starts folded where nothing is saved; open it, as a person does, to see the closed item
            b.wait("!!document.querySelector('#workTbl tr.wgh.coll[data-gk=\"actions|due|closed\"]')", 15)
            b.click('#workTbl [data-gtog="actions|due|closed"]')
            b.wait(f"!!document.querySelector('#workTbl tr[data-row=\"{self.aid}\"]')", 15)
            tags = b.eval(f"[...document.querySelectorAll('#workTbl tr[data-row=\"{self.aid}\"] td.title .tag')].map(t=>t.textContent)")
            self.assertIn("Archived", tags)
            live = b.eval("[...document.querySelectorAll('#workTbl tr[data-row] td.title .tag')].filter(t=>t.textContent==='Archived').length")
            self.assertEqual(live, 1)                                     # only the archived one
            b.eval("go('settings','views')")                              # v2.6 (#246): Work and reports › Opening views
            b.wait("!!document.querySelector('#set-views [data-k=showArchived]')", 15)
            help_ = b.eval("[...document.querySelectorAll('.srow')].find(r=>/Show archived projects/.test(r.textContent)).querySelector('small').textContent")
            self.assertIn("archived for their age", help_)
        finally:
            self.show_archived(False)

    def test_from_search_an_age_archived_item_opens(self):
        b = self.b
        r = self.found("Book UAT environment", self.aid)
        self.assertTrue(r and r["opens"]["archived"], r)
        b.eval(f"openFound({json.dumps(r)})")
        b.wait(f"CUR&&CUR.id==={json.dumps(self.aid)}&&document.getElementById('panel').classList.contains('on')", 15)
        self.assertNotIn("project is archived", b.eval("document.getElementById('snackT').textContent"))

    def test_from_search_an_archived_projects_item_names_the_real_switch(self):
        b = self.b
        r = self.found("Book UAT environment", self.aid)
        r["opens"]["project_archived"] = True                             # as search marks an archived project's item
        b.eval("document.getElementById('snackT').textContent=''")
        b.eval(f"openFound({json.dumps(r)})")
        b.wait("/project is archived/.test(document.getElementById('snackT').textContent)", 10)
        msg = b.eval("document.getElementById('snackT').textContent")
        self.assertIn("Show archived projects", msg)
        self.assertIn("Settings › Work and reports › Opening views", msg)        # v2.6 (#246): the switch moved there
        self.assertNotIn("Advanced", msg)


if __name__ == "__main__":
    unittest.main()

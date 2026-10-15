"""Fixes before 1.4.0 (fix-peek-140): BL-187 (the peek's owner suggestions and Add workstream…), BL-188 (staged peek changes
show in every window) and BL-180's banner beside ask creaite. A real browser against the real live server.

Run: python3 dev/tests/test_peek_fixes.py   (needs Google Chrome; skipped otherwise)
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from test_dashboard import populate  # noqa: E402
from test_workstreams import ws  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from split_dashboard import readable_page  # noqa: E402


class FixCase(LiveBrowserCase):
    @classmethod
    def load(cls, v):
        populate(v)
        v.propose("ws", [ws(1, name="Data", lead="Sara Example"), ws(2, name="Testing", aliases="UAT")])
        v.run("apply")

    def open(self, id_=None):
        b = self.b
        b.eval("WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        id_ = id_ or b.eval("A.find(x=>x.p==='ABC').id")
        b.eval(f"openRecord('actions',{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}&&document.getElementById('panel').classList.contains('peek')")
        b.pump(0.2)
        return id_

    def chip(self, f):
        b = self.b
        b.eval(f"document.querySelector('#panel [data-pkp=\"{f}\"]').click()")
        b.wait("document.querySelector('.pkpop')")

    def typed(self, text):
        b = self.b
        b.eval(f"(()=>{{ const i=document.querySelector('.pkpop .pkq'); i.value={text!r}; i.dispatchEvent(new Event('input',{{bubbles:true}})); }})()")
        return b.eval("[...document.querySelectorAll('.pkpop .pkopt')].map(o=>(o.querySelector('span')||o).firstChild.textContent.trim())")

    def option(self, starts):
        self.b.eval(f"[...document.querySelectorAll('.pkpop .pkopt')].find(o=>(o.querySelector('span')||o).textContent.trim().startsWith({starts!r})).click()")

    def staged(self):
        return sorted((self.v.root / "system/staging").glob("proposed-*dashboard*.json"))


class OwnerSuggestions(FixCase):
    """BL-187: the owner list suggests from the register as the old combo did (one matcher, ownerMatches)."""

    def test_aliases_emails_likely_matches_and_new_people(self):
        b = self.b
        self.open()
        self.chip("o")
        self.assertEqual(self.typed("Sara E")[0], "Sara Example")                                   # an alias finds the person
        self.assertEqual(self.typed("omar@def.example")[0], "Omar Ali")                            # so does an email
        likely = self.typed("Sarah Example")
        self.assertEqual(likely[0], "Is “Sarah Example” Sara Example?")                             # a likely match, asked
        self.assertIn("New person “Sarah Example”…", likely)
        self.assertEqual(self.typed("Zed Quill")[0], "New person “Zed Quill”…")
        self.assertTrue(self.typed("Zed Quill")[-1].startswith("Open "))                            # the person's page stays
        self.assertTrue(self.typed("")[-1].startswith("Open "))
        self.assertTrue(b.eval("ownerMatches('Sara E',peopleAll()).items[0].n==='Sara Example'"))  # the combo's own matcher
        src = readable_page()      # BL-231: the source; BL-316: the form's owner field (a Combobox) uses the same matcher
        start = src.index("function ownerOptions(")
        self.assertIn("ownerMatches(typed?q:\"\",pool)", src[start:start + 600])

    def test_picking_a_likely_match_remembers_the_alias_and_stages_the_owner(self):
        b = self.b
        id_ = self.open()
        self.chip("o")
        self.typed("Sarah Example")
        self.option("Is “Sarah Example”")
        b.wait("curObj().o==='Sara Example'&&PKS.length===1", timeout=15)
        self.assertTrue(b.eval("REG.find(p=>p.name==='Sara Example').aliases.includes('Sarah Example')"))
        upd = [json.loads(p.read_text()) for p in self.staged()]
        changes = [i for d in upd for i in d["items"] if i.get("id") == id_]
        self.assertEqual(changes[0]["changes"], {"owner": "Sara Example"})
        self.assertEqual(b.errors, [])


class AddWorkstream(FixCase):
    """BL-187: "Add workstream…" in the peek's list, through the old panel's route (the new workstream ahead of the item)."""

    def test_add_a_workstream_from_an_existing_item_undo_and_apply(self):
        b = self.b
        id_ = self.open()
        b.eval("PK.det[pkCid()]=true; pkDraw()")
        self.chip("ws")
        self.assertEqual(self.typed(""), ["Data", "Testing", "None", "Add workstream…"])
        self.assertEqual(self.typed("Reporting"), ["Add “Reporting” as a workstream…"])
        self.option("Add “Reporting”")
        b.wait("document.querySelector('.pkws')")
        self.assertEqual(b.eval("document.querySelector('.pkws [data-wsn=\"name\"]').value"), "Reporting")
        self.assertEqual(b.eval("document.querySelector('.pkws').getAttribute('role')"), "dialog")
        b.eval("document.querySelector('.pkws [data-wsn=\"keywords\"]').value='pack'; document.querySelector('.pkws [data-wsf=\"add\"]').click()")
        b.wait("curObj().ws==='Reporting'&&PKS.length===1", timeout=15)
        data = json.loads(self.staged()[0].read_text())
        self.assertEqual([(i["table"], i["op"]) for i in data["items"]], [("workstreams", "new"), ("actions", "update")])
        self.assertEqual(data["items"][0]["values"]["keywords"], "pack")
        self.assertIn("Reporting", b.eval("wsFor('ABC')"))
        b.click("#pkUndo")                                                                          # Undo last removes both
        b.wait("PKS.length===0&&!wsFor('ABC').includes('Reporting')", timeout=15)
        self.assertEqual(self.staged(), [])
        self.chip("ws")
        self.typed("Reporting")
        self.option("Add “Reporting”")
        b.wait("document.querySelector('.pkws')")
        b.eval("document.querySelector('.pkws [data-wsf=\"add\"]').click()")
        b.wait("PKS.length===1", timeout=15)
        self.assertEqual([w["name"] for w in self.v.rows("workstreams") if w["name"] == "Reporting"], [])   # staged, not applied
        b.click("#pkApply")
        b.wait("PKS.length===0", timeout=20)
        self.assertEqual([w["status"] for w in self.v.rows("workstreams") if w["name"] == "Reporting"], ["Active"])
        self.assertEqual(next(a for a in self.v.rows("actions") if a["id"] == id_)["workstream"], "Reporting")
        self.assertEqual(b.errors, [])

    def test_a_new_item_carries_its_new_workstream_in_its_one_proposal(self):
        b = self.b
        b.eval("go('work'); openNew('actions')")
        nid = b.eval("CUR.nid")
        b.eval(f"pkCommit('actions',{nid!r},{{p:'ABC'}},'Project','','')")
        b.eval(f"pkCommit('actions',{nid!r},{{t:'Draft the comms plan'}},'Action','','')")
        b.wait("CUR.staged", timeout=15)
        b.eval("PK.det[pkCid()]=true; pkDraw()")
        self.chip("ws")
        self.typed("Comms")
        self.option("Add “Comms”")
        b.wait("document.querySelector('.pkws')")
        b.eval("document.querySelector('.pkws [data-wsf=\"add\"]').click()")
        b.wait("CUR.draft.ws==='Comms'", timeout=15)
        b.eval("pkQuiet()")
        b.pump(0.5)
        items = json.loads(self.staged()[0].read_text())["items"]
        self.assertEqual([(i["table"], i["op"], i["n"]) for i in items], [("workstreams", "new", 1), ("actions", "new", 2)])
        b.click("#pkApply")
        b.wait("PKS.length===0", timeout=20)
        acts = {a["description"]: a["workstream"] for a in self.v.rows("actions")}
        self.assertEqual(acts["Draft the comms plan"], "Comms")
        self.assertEqual(b.errors, [])

    def test_a_proposal_in_review_keeps_its_own_route(self):
        b = self.b
        self.assertFalse(b.eval("CUR=null; (()=>{ const c=CUR; CUR={mode:'proposal'}; const r=pkWsAddOK(); CUR=c; return r; })()"))


class StagedInEveryWindow(FixCase):
    """BL-188: two windows on one live server. One stages; the other shows the pill, "staged" and the staged value after its
    data refreshes, never the first window's unstaged text, and can apply it."""

    def second(self):
        from cdp import Browser
        b2 = Browser(self.width, self.height, reduced_motion=True)
        self.addCleanup(b2.close)
        b2.goto(self.base + "/")
        b2.wait("typeof go==='function' && LIVE")
        return b2

    def test_the_other_window_shows_and_applies_what_one_staged(self):
        a = self.b
        id_ = self.open(a.eval("A.find(x=>x.p==='ABC'&&x.st==='Open'&&x.pr!=='Low').id"))
        b = self.second()
        b.eval(f"WT='actions'; go('work'); openRecord('actions',{id_!r})")
        b.wait(f"CUR&&CUR.id==={id_!r}")
        self.assertEqual(b.eval("[PKS.length, document.getElementById('pkStage').hidden]"), [0, True])
        a.eval(f"pkCommit('actions',{id_!r},{{pr:'Low'}},'Priority',curObj().pr,'Low')")
        a.wait("PKS.length===1", timeout=15)
        a.eval("const d=document.getElementById('pkDesc'); d.focus(); d.textContent='Half typed, not staged'")   # never leaves this window
        data = json.loads(self.staged()[0].read_text())
        self.assertEqual((data["peek"]["k"], data["peek"]["id"], data["peek"]["patch"]), ("actions", id_, {"pr": "Low"}))
        b.eval("reloadData()")                                                                    # the page's own data refresh
        b.wait("PKS.length===1&&!document.getElementById('pkStage').hidden", timeout=15)
        b.wait("curObj().pr==='Low'")
        self.assertEqual(b.eval("document.getElementById('pkStN').textContent"), "1 change staged on 1 item")
        self.assertEqual(b.eval("document.querySelector('#panel [data-pkp=\"pr\"]').getAttribute('aria-label')"), "Priority: Low")
        self.assertEqual(b.eval("[...document.querySelectorAll('#pkFeed .pk-fe')].filter(e=>e.querySelector('.pk-pill.st')).map(e=>e.textContent.includes('Low'))"), [True])
        self.assertTrue(b.eval(f"!!document.querySelector('#workTbl tr[data-row=\"{id_}\"] .pkdot')"))
        self.assertNotIn("Half typed", b.eval("document.getElementById('panel').textContent"))
        b.click("#pkApply")                                                                       # any window can apply it
        b.wait("PKS.length===0", timeout=20)
        self.assertEqual(next(r for r in self.v.rows("actions") if r["id"] == id_)["priority"], "Low")
        a.eval("reloadData()")
        a.wait("PKS.length===0", timeout=15)
        self.assertEqual(a.errors + b.errors, [])

    def test_a_reload_shows_another_windows_staged_change_and_undo_last_works_there(self):
        a = self.b
        id_ = self.open()
        a.eval(f"pkCommit('actions',{id_!r},{{due:'2026-12-01'}},'Due date','','01-12-2026')")
        a.wait("PKS.length===1", timeout=15)
        b = self.second()                                                                         # a fresh window: on load
        b.wait("PKS.length===1&&!document.getElementById('pkStage').hidden", timeout=15)
        self.assertEqual(b.eval(f"REC('actions',{id_!r}).due"), "2026-12-01")
        b.click("#pkUndo")
        b.wait("PKS.length===0", timeout=15)
        self.assertEqual(self.staged(), [])
        self.assertNotEqual(b.eval(f"REC('actions',{id_!r}).due"), "2026-12-01")
        self.assertEqual(a.errors + b.errors, [])


class BannerBesideTheChat(FixCase):
    """BL-180's banner with ask creaite open over the page (BL-173): its actions stay in view and clickable at 1400, 1100 and
    900px, it ends at the chat's edge, and opening the chat never changes its height or the page's width."""
    shared_server = True

    @classmethod
    def load(cls, v):
        """Errors of four kinds in today's debug log, so the banner's line of kinds is long."""
        from datetime import datetime
        super().load(v)
        now = datetime.now()
        logs = v.root / "system/logs"
        logs.mkdir(parents=True, exist_ok=True)
        with open(logs / f"debug-{now:%Y-%m-%d}.log", "a", encoding="utf-8") as f:
            for area, msg in (("sweep", "sweep failed 1"), ("sweep", "sweep failed 1"), ("server", "request failed"),
                              ("run", "run failed"), ("build", "rebuild failed")):
                f.write(f"{now:%Y-%m-%d %H:%M:%S} ERROR {area:<12} {msg}\n")

    HIT = """(()=>{ const ch=document.getElementById('chat'), edge=ch.classList.contains('on')?ch.getBoundingClientRect().left:innerWidth;
      return ['ebInv','ebAsk','ebX'].map(id=>{ const e=document.getElementById(id), r=e.getBoundingClientRect(),
        t=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2); return e.contains(t)&&r.right<=edge&&r.width>0; }); })()"""
    SIZE = "[Math.round(document.getElementById('errBanner').getBoundingClientRect().height),Math.round(document.querySelector('.content').getBoundingClientRect().width),scrollX]"

    def test_the_actions_stay_clickable_beside_the_chat(self):
        b = self.b
        b.wait("!document.getElementById('errBanner').hidden", timeout=15)
        self.assertRegex(b.eval("document.querySelector('#errBanner .eb-w').textContent"), r"^4 errors \(5 times\) in the last day")
        b.eval("go('work')")
        self.assertEqual(b.eval("document.getElementById('ebAsk').textContent"), "ask creaite to look")    # BL-105: lower case
        for w in (1400, 1100, 900):
            b.resize(w, 900)
            b.eval("closeChat()")
            b.pump(0.3)
            closed = b.eval(self.SIZE)
            self.assertEqual(b.eval(self.HIT), [True, True, True], f"{w}px, chat closed")
            b.eval("openChat()")
            b.wait("document.getElementById('chat').classList.contains('on')")
            b.pump(0.3)
            self.assertEqual(b.eval(self.HIT), [True, True, True], f"{w}px, chat open")
            self.assertEqual(b.eval(self.SIZE), closed, f"{w}px: the page doesn't move")
            self.assertIn("errors", b.eval("document.querySelector('#errBanner .eb-w').title"))         # the whole text on hover
        b.click("#ebX")                                                                                  # a real click, chat open
        b.wait("document.getElementById('errBanner').hidden")
        self.assertTrue(b.eval("document.getElementById('chat').classList.contains('on')"))             # the chat stays open


if __name__ == "__main__":
    unittest.main()

"""BL-167 (sprint-polish-2): an unsaved side-panel edit survives a reload, in a real browser against the real live server.

Run: python3 dev/tests/test_panel_drafts.py   (needs Google Chrome; skipped otherwise)

An edit, a reload, then Restore brings the changed fields back; Discard drops them; a draft over 7 days old is dropped with a
note; nothing is staged before Create; Create, Cancel and Close drop the draft. BL-176 (sprint-peek): this now applies to the
forms that remain (a new item); an existing item is the peek, where a change is staged as it is made and survives a reload.
BL-179 (sprint-peek-new): a new item is the peek too; its unstaged draft uses the same store, keyed "new:<kind>", and New
offers it back in the peek (#pkDraft) with Restore or Discard.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402

META = 4


class Drafts(LiveBrowserCase):
    def staged(self):
        return sorted(p.name for p in (self.v.root / "system/staging").glob("proposed-*.json"))

    def first(self):
        return self.b.eval("A.find(x=>x.p==='ABC'&&OPENST(x.st)).id")

    def open_item(self, id_):
        b = self.b
        b.eval(f"go('work'); openRecord('actions', {id_!r})")
        b.wait(f"CUR && CUR.id==={id_!r} && document.getElementById('panel').classList.contains('on')")

    def new_and_type(self, text):
        """BL-179: a new item is the peek; what is typed is kept in this browser until it is staged."""
        b = self.b
        self.open_new()
        b.type(text)
        b.wait(f"((JSON.parse(localStorage.getItem('creaite-panel-drafts')||'{{}}')['new:actions']||{{}}).fields||{{}}).t==={text!r}", 5)

    def open_new(self):
        self.b.eval("go('work'); openNew('actions')")
        self.b.wait("CUR && CUR.mode==='new' && document.activeElement.id==='pkTitle'")

    def reload(self):
        self.b.reload()
        self.b.wait("typeof go==='function' && LIVE")

    def bar(self):
        return self.b.eval("(()=>{ const d=document.getElementById('pkDraft'); return d&&!d.hidden?d.textContent:''; })()")

    def drafts(self):
        return self.b.eval("JSON.parse(localStorage.getItem('creaite-panel-drafts')||'{}')")

    def test_restore_brings_the_changed_fields_back_and_nothing_is_staged(self):
        before = self.staged()
        self.new_and_type("Escalate to the CIO by Friday")
        self.reload()
        self.assertEqual(self.staged(), before)                                    # nothing reaches the vault before Create
        self.open_new()
        self.assertIn("An unsaved new action from", self.bar())
        self.assertIn("Escalate to the CIO by Friday", self.bar())
        self.b.click('[data-pknd="restore"]')
        self.assertEqual(self.b.eval("document.getElementById('pkTitle').textContent"), "Escalate to the CIO by Friday")
        self.assertEqual(self.bar(), "")
        self.assertEqual(self.staged(), before)                                    # restoring writes nothing either
        self.b.eval("pkCommit('actions',CUR.nid,{p:'ABC'},'Project','','')")       # a project, then ⌘↵ stages, applies and closes
        self.b.key("Enter", modifiers=META)
        self.b.wait("!document.getElementById('panel').classList.contains('on')", 30)
        self.b.wait("/created/.test(document.getElementById('snackT').textContent)", 15)
        self.assertIn("Escalate to the CIO by Friday", [r["description"] for r in self.v.rows("actions")])
        self.assertNotIn("new:actions", self.drafts())                             # created: the draft is gone

    def test_discard_drops_them(self):
        self.new_and_type("Something I didn't mean")
        self.reload()
        self.open_new()
        self.b.click('[data-pknd="discard"]')
        self.assertEqual(self.bar(), "")
        self.assertNotIn("new:actions", self.drafts())
        self.b.eval("closePanel()")
        self.open_new()
        self.assertEqual(self.bar(), "")
        self.assertEqual(self.b.eval("document.getElementById('pkTitle').textContent"), "")

    def test_an_existing_item_keeps_nothing_unsaved_its_staged_change_survives_a_reload(self):
        """BL-176: the peek retires BL-167 for existing items: a change is staged as it is made, so a reload keeps it (the bar
        comes back with it) and no draft is kept or offered."""
        id_ = self.first()
        b = self.b
        b.eval(f"go('work'); openRecord('actions', {id_!r})")
        b.wait("document.getElementById('panel').classList.contains('peek')")
        b.click("#pkTitle")
        b.eval("(()=>{ const t=document.getElementById('pkTitle'); t.textContent='My edit'; t.blur(); })()")
        b.wait("PKS.length===1", 10)
        self.assertNotIn(f"actions:{id_}", self.drafts())
        self.reload()
        b.wait("PKS.length===1&&!document.getElementById('pkStage').hidden", 10)
        self.assertEqual(b.eval(f"REC('actions',{id_!r}).t"), "My edit")          # shown as staged on the fresh page
        b.eval(f"go('work'); openRecord('actions', {id_!r})")
        b.wait("document.getElementById('panel').classList.contains('peek')")
        self.assertEqual(self.bar(), "")
        self.assertEqual(b.eval("document.getElementById('pkTitle').textContent"), "My edit")
        self.assertNotEqual(next(r for r in self.v.rows("actions") if r["id"] == id_)["description"], "My edit")   # not applied

    def test_a_draft_over_seven_days_old_is_dropped_with_a_note(self):
        self.new_and_type("Old thought")
        self.reload()
        self.b.eval("(()=>{ const a=JSON.parse(localStorage.getItem('creaite-panel-drafts')); a['new:actions'].at=Date.now()-8*864e5; localStorage.setItem('creaite-panel-drafts',JSON.stringify(a)); })()")
        self.open_new()
        self.assertIn("more than 7 days old", self.bar())
        self.assertNotIn("new:actions", self.drafts())

    def test_discard_and_an_empty_close_drop_the_draft(self):
        self.new_and_type("Cancelled thought")
        self.b.click("#pkClose")                                                   # it has a title: Keep or Discard
        self.b.wait("!document.getElementById('pkAsk').hidden")
        self.b.click('#pkAsk [data-pkask="discard"]')
        self.b.wait("!CUR")
        self.assertNotIn("new:actions", self.drafts())
        self.new_and_type("Closed thought")
        self.b.eval("document.getElementById('pkTitle').textContent=''; document.getElementById('pkTitle').dispatchEvent(new Event('input',{bubbles:true}))")
        self.b.click("#pkClose")                                                   # empty again: it just closes
        self.b.wait("!CUR")
        self.assertNotIn("new:actions", self.drafts())

    def test_a_new_item_is_offered_back_too(self):
        b = self.b
        self.new_and_type("A new thought")
        before = self.staged()
        self.reload()
        self.assertEqual(self.staged(), before)
        self.open_new()
        self.assertIn("A new thought", self.bar())
        b.click('[data-pknd="restore"]')
        self.assertEqual(b.eval("document.getElementById('pkTitle').textContent"), "A new thought")


if __name__ == "__main__":
    unittest.main()

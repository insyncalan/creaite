"""#357 (a calm confirmation on a bulk save): after the Save bar's Save, the waiting bar goes and one confirmation in the ok tint says
"Saved N changes" with a single Undo (the whole save), for as long as Undo is there; a new change waiting brings the bar back and
the confirmation goes; Undo reverses the save. No motion of its own. Measured against the page's own boxes; desktop and 900 px.

Run: python3 dev/tests/test_calm_save_357.py   (needs Google Chrome; skipped otherwise)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_browser import LiveBrowserCase  # noqa: E402
from live_browser import theme_names  # noqa: E402


class CalmSave(LiveBrowserCase):
    width, height = 1400, 900

    def stage_two(self):
        b = self.b
        b.eval("S.autoApply=true; WT='actions'; go('work')")
        b.wait("document.querySelector('#workTbl tbody tr[data-row]')")
        ids = b.eval("A.filter(x=>x.st==='Open').map(x=>x.id)")
        self.assertGreaterEqual(len(ids), 2)
        for i, id_ in enumerate(ids[:2]):
            b.eval(f"openRecord('actions',{id_!r})")
            b.wait(f"CUR&&CUR.id==={id_!r}")
            b.eval(f"pkCommit('actions',{id_!r},{{t:'Calm {i}'}},'Title',curObj().t,'Calm {i}')")
            b.wait(f"PKS.length==={i + 1}", timeout=15)
            b.eval("closePanel()")
        return ids[:2]

    def save(self):
        b = self.b
        b.eval("pkApply()")
        b.wait("PKS.length===0&&document.getElementById('snack').classList.contains('on')", timeout=20)

    def test_the_bar_goes_and_one_calm_confirmation_with_one_undo_takes_its_place(self):
        b = self.b
        self.stage_two()
        self.assertFalse(b.eval("document.getElementById('pkStage').hidden"))
        self.save()
        self.assertTrue(b.eval("document.getElementById('pkStage').hidden"))
        self.assertEqual(b.eval("document.getElementById('snackT').textContent"), "Saved 2 changes")
        self.assertTrue(b.eval("document.getElementById('snack').classList.contains('ok')"))
        self.assertEqual(b.eval("[...document.querySelectorAll('#snack button')].filter(x=>x.offsetParent&&x.textContent==='Undo').length"), 1)
        self.assertEqual(b.eval("document.getElementById('snack').title"), "A backup was taken first")
        self.assertNotIn("Undo last", b.eval("document.body.innerText.split('Saved 2 changes')[1]||''"))      # no second Undo while it shows

    def test_it_stays_as_long_as_undo_is_there_and_holds_on_hover(self):
        b = self.b
        self.stage_two()
        self.save()
        self.assertTrue(b.eval("document.getElementById('snack').classList.contains('mtimer')"))        # the Undo timer the toast already has
        b.eval("document.getElementById('snack').dispatchEvent(new MouseEvent('mouseenter'))")
        b.pump(0.3)
        self.assertTrue(b.eval("document.getElementById('snack').classList.contains('held')"))

    def test_esc_hides_it(self):
        b = self.b
        self.stage_two()
        self.save()
        b.eval("document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))")
        b.wait("!document.getElementById('snack').classList.contains('on')")

    def test_a_new_change_waiting_brings_the_bar_back_and_the_confirmation_goes(self):
        b = self.b
        ids = self.stage_two()
        self.save()
        b.eval(f"openRecord('actions',{ids[0]!r})")
        b.wait(f"CUR&&CUR.id==={ids[0]!r}")
        b.eval(f"pkCommit('actions',{ids[0]!r},{{t:'Again'}},'Title',curObj().t,'Again')")
        b.wait("PKS.length===1&&!document.getElementById('pkStage').hidden", timeout=15)
        b.wait("document.getElementById('snackT').textContent.includes('still be undone in Activity')")
        self.assertFalse(b.eval("document.getElementById('snack').classList.contains('ok')"))

    def test_part_saved_and_part_waiting_says_so_plainly_not_the_calm_way(self):
        """The partial-save message (panel.js pkApply): a change that was edited elsewhere stays waiting, so the toast counts what was saved,
        says how many still wait and why, and is not the calm ok one that would sit beside the bar saying all is well."""
        b = self.b
        self.stage_two()
        # one staged file is still there after the save, as when the item was changed elsewhere and so was not taken
        b.eval("(()=>{const keep=PKS[0].name,o=shared.VW.exists;shared.VW.exists=async function(p){return p.endsWith(keep)?true:o.call(this,p)};window.__undoVW=()=>{shared.VW.exists=o}})()")
        b.eval("pkApply()")
        b.wait("document.getElementById('snack').classList.contains('on')", timeout=20)
        b.eval("window.__undoVW()")
        text = b.eval("document.getElementById('snackT').textContent")
        self.assertEqual(text, "Saved 1 change; 1 still waiting to be saved (changed elsewhere since)")
        self.assertFalse(b.eval("document.getElementById('snack').classList.contains('ok')"))

    def test_undo_reverses_the_save(self):
        b = self.b
        ids = self.stage_two()
        self.save()
        b.eval("document.getElementById('snackU').click()")
        b.wait("A.find(x=>x.id===%r).t!=='Calm 0'" % ids[0], timeout=20)

    def test_the_tint_reads_in_every_palette_light_and_dark(self):
        b = self.b
        self.stage_two()
        self.save()
        worst = 99
        for pal in theme_names():
            for mode in ("Light", "Dark"):
                b.eval(f"S.palette={pal!r}; S.theme={mode!r}; applyTheme()")
                b.pump(0.1)
                r = b.eval("""(()=>{ const p=c=>c.match(/[\\d.]+/g).map(Number), l=c=>{const f=u=>{u/=255;return u<=.03928?u/12.92:((u+.055)/1.055)**2.4};return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2])};
          const e=document.getElementById('snack'), s=getComputedStyle(e), bg=p(s.backgroundColor), fg=p(s.color), a=l(bg), z=l(fg);
          return (Math.max(a,z)+.05)/(Math.min(a,z)+.05); })()""")
                worst = min(worst, r)
        self.assertGreaterEqual(worst, 4.5)

    def test_it_fits_at_900_and_does_not_move_with_reduced_motion(self):
        b = self.b
        b.resize(900, 900)
        self.stage_two()
        self.save()
        self.assertTrue(b.eval("(()=>{const r=document.getElementById('snack').getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})()"))
        self.assertEqual(b.eval("getComputedStyle(document.getElementById('snack')).transitionDuration.split(',').every(x=>parseFloat(x)===0)"), True)      # reduced motion on (the harness sets it)

    def test_mutant_a_plain_toast_is_not_the_calm_one(self):
        b = self.b
        b.eval("snack('Saved 2 changes',()=>{})")
        b.wait("document.getElementById('snack').classList.contains('on')")
        self.assertFalse(b.eval("document.getElementById('snack').classList.contains('ok')"))


if __name__ == "__main__":
    unittest.main()

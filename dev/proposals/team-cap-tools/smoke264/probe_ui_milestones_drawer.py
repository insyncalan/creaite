"""Milestones Client view wording (2.6.4) and the note drawer width (#321).

  python3 -I probe_ui_milestones_drawer.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

Headless Chrome over a scratch vault (fictional data). Every milestone is hidden from the client; one project keeps a single
milestone.
  Milestones  Client view with one hidden milestone says "The milestone is not shown to the client yet" with Add milestone
              beside it; with several hidden it says "None of the N milestones are shown to the client yet"; neither shows
              "0 achieved, 0 to come"; Internal view still lists the milestones.
  #321        The note drawer (press n on Notes): default width 440 px; Left 464, Shift+Left 560, Right 536, End = the viewport
              width, Enter back to 440; a real drag widens it past 600; "Reset width" shows only when the width has changed.
              At 1400 and 900 px.
Expected on 2.6.4 (base 2.6.3): all PASS. With --control the two Client view wording checks FAIL on the base (it shows
"0 achieved, 0 to come"); the drawer checks pass (they arrived in 2.6.2).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import rec  # noqa: E402


def main():
    a = C.parse(__doc__)
    v = C.V("pMilestones", identity="Sam Reid", calendar=False)
    try:
        ids = [r[0] for r in v.db("select id from milestones where project='MER' order by id")]
        stmts = ["update milestones set client_visible=0, client_message=NULL"]
        for mid in ids[1:]:
            stmts += [("update actions set milestone=NULL where milestone=?", (mid,)), ("update raid set milestone=NULL where milestone=?", (mid,)),
                      ("delete from milestones where id=?", (mid,))]
        v.db_write(*stmts)
        n_fal = v.db("select count(*) from milestones where project='FAL'")[0][0]
        v.run("build_dashboard.py")
        v.start(1400, 1000)
        b = v.b

        def milestones(code, view):
            b.eval(f"go('milestones','{code}')")
            b.pump(1.5)
            b.eval("(()=>{const x=[...document.querySelectorAll('#v-milestones button')].find(e=>new RegExp('^%s view').test(e.innerText.trim())); if(x) x.click()})()" % view)
            b.pump(1.0)
            return b.eval("document.getElementById('v-milestones').innerText.replace(/\\n+/g,' | ')")

        t1, t3 = milestones("MER", "Client"), milestones("FAL", "Client")
        tail = lambda t: t[t.find("Plan |"):][:240] if "Plan |" in t else t[-240:]  # noqa: E731
        rec("MS one hidden milestone in Client view says it is not shown", "The milestone is not shown to the client yet" in t1 and "0 achieved" not in t1 and "Add milestone" in t1, tail(t1))
        rec("MS several hidden milestones in Client view say none are shown", f"None of the {n_fal} milestones are shown to the client yet" in t3 and "0 achieved" not in t3, tail(t3))
        ti = milestones("FAL", "Internal")
        rec("MS Internal view still lists the milestones", "not shown to the client" not in ti and len(ti) > 100, ti[:200])

        b.eval("go('notes','FAL')")
        b.pump(1.2)
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("n")
        b.pump(1.0)
        shown = b.eval("!!document.getElementById('capDrawer') && !document.getElementById('capDrawer').hidden")
        if not shown:
            b.eval("document.getElementById('notesNew') && document.getElementById('notesNew').click()")
            b.pump(1.0)
            shown = b.eval("!!document.getElementById('capDrawer') && !document.getElementById('capDrawer').hidden")
        for width in (1400, 900):
            b.resize(width, 1000)
            b.pump(0.6)
            W = lambda: b.eval("Math.round(document.getElementById('capDrawer').getBoundingClientRect().width)")  # noqa: E731
            N = lambda: b.eval("+document.getElementById('capResize').getAttribute('aria-valuenow')")  # noqa: E731
            b.eval("document.getElementById('capResize').focus()")
            b.key("Home")
            b.pump(0.3)
            w0 = W()
            b.key("ArrowLeft")
            w1 = W()
            b.key("ArrowLeft", 8)
            w2 = W()
            b.key("ArrowRight")
            w3 = W()
            b.key("End")
            w4 = W()
            b.key("Enter")
            w5 = W()
            b.drag("#capResize", "#capResize", offset=(-300, 0))
            b.pump(0.4)
            wd = W()
            reset_vis = b.eval("!!document.getElementById('capWidthReset')")
            b.key("Home")
            b.pump(0.3)
            rec(f"321 note drawer width at {width}px", shown and (w0, w1, w2, w3, w5) == (440, 464, 560, 536, 440) and w4 == width and wd > 600 and reset_vis,
                f"default {w0}, Left {w1}, Shift+Left {w2}, Right {w3}, End {w4} (viewport {width}), Enter {w5}, drag {wd}, Reset shown when changed {reset_vis}; aria-valuenow {N()}")
        b.resize(1400, 1000)
        b.key("Escape")
        print("console errors:", b.errors[:3])
    finally:
        v.close()
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)

"""#352 and #351 (b): the Today page.

  python3 -I probe_ui_today.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

Headless Chrome at 1400 px over a scratch vault whose user owns stale actions (raised and last updated weeks ago), with a
fictional calendar built around the real today (the last weekday before today, today, the next weekday after today).
  #352  Today (My Commitments) has no "no update for ... days" line, no stale-actions strip and no "Draft updates" button;
        in Work, x then Shift+Down selects two actions and the bulk bar still offers "Draft updates".
  #351b A past day shows times, titles and organiser only: no follow-up chips ("Transcript ready", "Minutes made",
        "No transcript") and no Check or Process buttons; today's meeting title hover opens the Prep peek; a later day lists
        its meetings; Intake still offers Check and Process.
Expected on 2.6.4 (base 2.6.3): all PASS. With --control the base shows the stale line, Draft updates and the past-day chips
(the checks FAIL there, which is the point).
Written on a Saturday. The past day is chosen as the last weekday before today and the later day as the next weekday after
today; the day menu and the week strip were only exercised on that weekday pattern.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import rec  # noqa: E402

DOM = r"""(()=>{const t=s=>(s||'').replace(/\s+/g,' ').trim();
  const meets=[...document.querySelectorAll('#dayMeets .dm')].map(e=>({time:t((e.querySelector('.tm')||{}).innerText),title:t((e.querySelector('.dmti')||e.querySelector('.tt')||{}).innerText),
     full:t(e.innerText), links:[...e.querySelectorAll('a,button')].map(x=>t(x.innerText)).filter(Boolean), chips:[...e.querySelectorAll('.chip,.dmchip,.pill,.tag')].map(x=>t(x.innerText))}));
  return {head:t((document.getElementById('todayDate')||{}).innerText), count:meets.length, meets}})()"""
FOLLOW_UP = re.compile(r"Transcript ready|Minutes made|No transcript|Process|Check", re.I)


def main():
    a = C.parse(__doc__)
    v = C.V("pToday", identity=None)
    try:
        owner = v.db("select owner, count(*) c from actions where status not in ('Done','Closed','Cancelled') and owner is not null group by owner order by c desc limit 1")[0][0]
        v.set_settings(lambda c: c.setdefault("identity", {}).update({"name": owner}))
        v.db_write("update actions set raised='2026-09-01'", "update actions set updated_at='2026-09-02 09:00:00'")
        v.run("build_dashboard.py")
        v.start(1400, 1000)
        b = v.b
        d = v.days
        b.eval("go('today')")
        b.wait("VIEW==='today' && document.querySelectorAll('#dayMeets .dm').length>0", 30)
        b.pump(2.0)
        t = v.view_text("v-today")
        stale = b.eval("!!document.getElementById('drStale')")
        rec("352 Today has no stale-actions line and no Draft updates button", not stale and "no update for" not in t and "Draft updates" not in t,
            f"#drStale present {stale}; 'no update for' {'no update for' in t}; 'Draft updates' {'Draft updates' in t}; user owns open actions as {owner!r}")
        b.eval("go('work')")
        b.pump(1.5)
        b.eval("document.activeElement&&document.activeElement.blur()")
        b.key("ArrowDown")
        b.pump(0.3)
        b.key("x")
        b.pump(0.3)
        b.key("ArrowDown", modifiers=8)
        b.pump(0.3)
        sel = b.eval("[...document.querySelectorAll('#workTbl tbody tr[aria-selected=true]')].map(r=>r.dataset.row)")
        bar = b.eval("document.getElementById('wbulk') ? (document.getElementById('wbulk').hidden+' '+document.getElementById('wbulk').innerText.replace(/\\n+/g,' | ')) : ''")
        rec("352 Work: x then Shift+Down selects two and the bulk bar offers Draft updates", len(sel) == 2 and "Draft updates" in bar, f"selected {sel}; bar {bar[:160]!r}")

        # ---- #351b
        b.eval("go('today')")
        b.wait("VIEW==='today' && document.querySelectorAll('#dayMeets .dm').length>0", 30)
        b.pump(1.5)
        today_m = b.eval(DOM)
        rec("351b Today lists its meetings", today_m["count"] == 5 and all(m["title"] for m in today_m["meets"]), f"{today_m['head']!r}; {[m['title'] for m in today_m['meets']]}")

        def hover(i):
            b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5)
            b.pump(0.4)
            pos = b.eval("(()=>{const e=document.querySelectorAll('#dayMeets .dm')[%d]; const t=e&&(e.querySelector('.dmti')||e.querySelector('.tt')); if(!t) return null; t.scrollIntoView({block:'center'}); const r=t.getBoundingClientRect(); return {x:r.left+Math.min(r.width/2,40), y:r.top+r.height/2}})()" % i)
            if not pos:
                return {"opened": False, "text": None}
            b.pump(0.3)
            for dx in (-6, 0, 3, 6):
                b.call("Input.dispatchMouseEvent", type="mouseMoved", x=pos["x"] + dx, y=pos["y"])
                b.pump(0.15)
            opened = False
            for _ in range(30):
                b.pump(0.2)
                if b.eval("!!document.querySelector('#dayMeets .dmpop')"):
                    opened = True
                    break
            b.pump(1.0)
            txt = b.eval("(()=>{const p=document.querySelector('#dayMeets .dmpop'); return p?p.innerText.replace(/\\s+/g,' ').trim().slice(0,160):null})()")
            b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5)
            b.key("Escape")
            b.pump(0.4)
            return {"opened": opened, "text": txt}

        h = hover(1)
        title1 = today_m["meets"][1]["title"] if len(today_m["meets"]) > 1 else "?"
        rec("351b Today: hovering a meeting title opens the Prep peek", h["opened"] and title1.split()[0] in (h["text"] or ""), f"{h}")

        if b.eval("!!document.querySelector('.dypastbtn')"):
            b.eval("document.querySelector('.dypastbtn').click()")
            b.pump(0.8)
            label = d["past"].strftime("%A %-d")
            b.eval("(()=>{const i=[...document.querySelectorAll('[role=menuitem],[role=menuitemradio]')].find(e=>e.innerText.indexOf(%s)>=0); if(i) i.click()})()" % json.dumps(label))
            b.pump(1.2)
        past = b.eval(DOM)
        bad = [m for m in past["meets"] if m["chips"] or any(FOLLOW_UP.search(x) for x in m["links"]) or re.search(r"Transcript ready|Minutes made|No transcript", m["full"], re.I)]
        rec("351b past day: times, titles and organiser only; no follow-up chips, no Check or Process",
            past["count"] == 4 and not bad, f"{past['head']!r}; {past['count']} meetings; offending: {[(m['title'], m['chips'], m['links']) for m in bad][:2]}; first: {past['meets'][0]['full'][:110] if past['meets'] else None!r}")

        label = d["future"].strftime("%a %-d")
        b.eval("(()=>{const t=[...document.querySelectorAll('#todayDate [role=tab]')].find(e=>e.innerText.toLowerCase().indexOf(%s)>=0); if(t) t.click()})()" % json.dumps(label.lower()))
        b.pump(1.2)
        fut = b.eval(DOM)
        rec("351b a later day lists its meetings", fut["count"] == 2, f"{fut['head']!r}; {[m['title'] for m in fut['meets']]}")

        b.eval("go('intake-review')")
        b.pump(2.0)
        buttons = b.eval("[...document.querySelectorAll('#v-intake-review button,#v-intake-review a')].map(x=>x.innerText.trim()).filter(x=>/^(Check|Process)/.test(x)).slice(0,12)")
        rec("351b Intake still offers Check and Process", any(x.startswith("Check") for x in buttons) and any(x.startswith("Process") for x in buttons), f"{buttons}")
        print("console errors:", b.errors[:3])
    finally:
        v.close()
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)

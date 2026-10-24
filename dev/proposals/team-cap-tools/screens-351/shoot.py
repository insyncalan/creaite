#!/usr/bin/env python3
"""Capture Today at 1400 px from one release zip, in a scratch vault with fictional data.
usage: shoot.py <zip> <label e.g. v2.6.3> <out dir> <work dir>"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "smoke" / "lib"))
import proc_guard  # noqa: E402
from cdp import Browser  # noqa: E402

zip_, label, out, work = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
run = work / f"run-{label}"
if run.exists():
    shutil.rmtree(run)
run.mkdir(parents=True)
vault, tmp, agents = run / "vault", run / "tmp", run / "agents"
tmp.mkdir()
agents.mkdir()
fake = run / "fake_claude.py"
fake.write_text('#!/usr/bin/env python3\nimport json\nprint(json.dumps({"type":"result","result":"[]","session_id":"x"}), flush=True)\n')
fake.chmod(0o755)
env = {**os.environ, "TMPDIR": str(tmp), "CREAITE_AGENT_DIR": str(agents), "CREAITE_NO_LAUNCHCTL": "1", "CREAITE_NO_LAUNCH": "1",
       "CREAITE_CLAUDE": str(fake), "PYTHONDONTWRITEBYTECODE": "1"}
for k in ("CREAITE_NOW", "CREAITE_PORT", "CREAITE_HC_VAULT", "CREAITE_BROWSER"):
    env.pop(k, None)
os.environ["TMPDIR"] = str(tmp)


def sh(cmd, cwd):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise SystemExit(f"{cmd[:3]} failed: {(r.stdout + r.stderr)[-800:]}")
    return r.stdout


sh([sys.executable, "-I", zip_, vault], run)
(vault / "dev/tools").mkdir(parents=True)
shutil.copy2(HERE.parent / "smoke" / "lib" / "demo_data.py", vault / "dev/tools/demo_data.py")
sh([sys.executable, "-c", "import sys; sys.path.insert(0, 'dev/tools'); import demo_data; demo_data.load()"], vault)
shutil.rmtree(vault / "dev")
print("vault", (vault / "VERSION").read_text().strip())

# ---- fictional calendar ----
def ev(i, day, start, end, title, org, teams=True, where="", n=4):
    return {"id": f"evt-{day[8:]}-{i:02d}", "start": start, "end": end, "title": title, "where": where or ("Microsoft Teams Meeting" if teams else ""),
            "all_day": False, "private": False, "teams": teams, "organiser": org, "organiser_email": "",
            "sensitivity": "normal", "recurrence": "", "body": "", "attendees": [{"name": f"Guest {k}", "email": "", "type": "required", "response": "accepted"} for k in range(n)],
            "attachments": []}

R, M, J, C, A = "Riley Stone", "Morgan Lee", "Jordan Park", "Casey Quinn", "Avery Shaw"
fri = [("09:00", "09:30", "Weekly sync", R, True, ""), ("09:45", "10:30", "Project kickoff", M, True, ""),
       ("10:30", "11:15", "Budget review", True, False, "Boardroom 2"), ("11:30", "12:15", "Demo day", J, True, ""),
       ("12:15", "12:45", "Lunch and learn", A, False, "Cafe annex"), ("13:00", "14:00", "Steering committee", R, True, ""),
       ("14:00", "14:30", "Retro", M, True, ""), ("14:30", "15:15", "Design review", C, True, ""),
       ("15:30", "16:00", "Vendor check-in", A, False, "Room 4"), ("16:00", "16:30", "Planning huddle", True, True, "")]
sat = [("08:30", "09:00", "Weekly sync", R, True, ""), ("09:15", "10:00", "Project kickoff", M, True, ""),
       ("10:00", "10:45", "Budget review", True, False, "Boardroom 2"), ("10:45", "11:30", "Demo day", J, True, ""),
       ("11:30", "12:00", "Retro", M, True, ""), ("12:15", "12:45", "Steering committee", R, True, ""),
       ("13:30", "14:15", "Design review", C, True, ""), ("14:15", "15:00", "Vendor check-in", A, False, "Room 4"),
       ("15:15", "16:00", "Planning huddle", True, True, ""), ("16:15", "16:45", "Wrap-up", J, True, "")]
other = {"2026-10-19": [("09:00", "09:30", "Weekly sync", R, True, ""), ("14:00", "15:00", "Budget review", True, False, "Boardroom 2")],
         "2026-10-20": [("10:00", "10:45", "Project kickoff", M, True, ""), ("15:00", "15:30", "Retro", M, True, "")],
         "2026-10-21": [("11:00", "12:00", "Design review", C, True, ""), ("13:00", "13:30", "Vendor check-in", A, False, "Room 4")],
         "2026-10-22": [("09:30", "10:00", "Weekly sync", R, True, ""), ("16:00", "17:00", "Demo day", J, True, "")],
         "2026-10-26": [("09:00", "09:30", "Weekly sync", R, True, ""), ("11:00", "12:00", "Steering committee", R, True, ""), ("15:00", "15:45", "Planning huddle", True, True, "")],
         "2026-10-27": [("10:00", "10:30", "Retro", M, True, ""), ("14:00", "15:00", "Budget review", True, False, "Boardroom 2")]}
days = {"2026-10-23": [ev(i + 1, "2026-10-23", *m[:4], teams=m[4], where=m[5]) for i, m in enumerate(fri)],
        "2026-10-24": [ev(i + 1, "2026-10-24", *m[:4], teams=m[4], where=m[5]) for i, m in enumerate(sat)]}
for d, L in other.items():
    days[d] = [ev(i + 1, d, *m[:4], teams=m[4], where=m[5]) for i, m in enumerate(L)]
cal = {"fetched": "2026-10-24 08:05", "to": "2026-10-27", "days": dict(sorted(days.items()))}
(vault / "system/staging").mkdir(parents=True, exist_ok=True)
(vault / "system/staging/calendar.json").write_text(json.dumps(cal, indent=1), encoding="utf-8")
# what the sweep found: ready / not transcribed / none ; a processed meeting; the rest not checked
tx = {"checked": {}, "version": 1}
for d in ("23", "24"):
    for i, st in {1: "available", 6: "available", 7: "none", 8: "not_transcribed"}.items():
        tx["checked"][f"evt-{d}-{i:02d}"] = {"status": st, "checked": "2026-10-24 08:05"}
(vault / "system/staging/transcripts.json").write_text(json.dumps(tx, indent=1), encoding="utf-8")
(vault / "system/processed.txt").write_text(
    "2026-10-23 | calendar:evt-23-02 | 2026-10-23 Project kickoff.docx | 4\n"
    "2026-10-24 | calendar:evt-24-02 | 2026-10-24 Project kickoff.docx | 4\n", encoding="utf-8")

# ---- settings ----
cfg_path = vault / "system/config/settings.json"
cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
cfg.setdefault("live_mode", {})["port"] = port
cfg.setdefault("vip", {})["check_minutes"] = 100000
cfg.setdefault("identity", {})["name"] = "Sam Reid"
cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

log = open(run / "server.log", "ab")
srv = proc_guard.spawn([sys.executable, str(vault / "system/scripts/live_server.py")], cwd=vault, env={**env, "CREAITE_PORT": str(port)},
                       stdout=log, stderr=subprocess.STDOUT)
print("server pid", srv.pid, "port", port, flush=True)
b = None
try:
    base = f"http://127.0.0.1:{port}"
    end = time.time() + 90
    while True:
        try:
            urllib.request.urlopen(base + "/health", timeout=1)
            break
        except OSError:
            if time.time() > end or srv.poll() is not None:
                raise SystemExit("server did not start: " + (run / "server.log").read_text(errors="replace")[-600:])
            time.sleep(0.3)
    b = Browser(1400, 1000)
    print("chrome pid", b.proc.pid, flush=True)
    b.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": "light"},
                                                   {"name": "prefers-reduced-motion", "value": "reduce"}])
    b.resize(1400, 1000)
    b.goto(base + "/")
    b.wait("typeof go==='function' && LIVE", 40)
    b.pump(2.0)
    b.eval("go('today')")
    b.wait("VIEW==='today' && !document.getElementById('v-today').hidden && document.querySelectorAll('#dayMeets .dm').length>0", 30)
    b.pump(2.0)

    DOM = r"""(()=>{const t=s=>(s||'').replace(/\s+/g,' ').trim();
      const tabs=[...document.querySelectorAll('#todayDate [role=tab], #todayDate .dy')].map(e=>({text:t(e.innerText),sel:e.getAttribute('aria-selected')}));
      const seps=[...document.querySelectorAll('#todayDate .daywk')].map(e=>t(e.innerText));
      const meets=[...document.querySelectorAll('#dayMeets .dm')].map(e=>({time:t((e.querySelector('.tm')||{}).innerText),title:t((e.querySelector('.dmti')||e.querySelector('.tt')||{}).innerText),
         hasTitleHover:!!e.querySelector('.dmti'),where:t((e.querySelector('.wh')||{}).innerText),acts:t((e.querySelector('.acts')||{}).innerText),cls:e.className}));
      return {todayDateText:t((document.getElementById('todayDate')||{}).innerText),tabs,weekSeps:seps,head:t((document.getElementById('dayHead')||{}).innerText),
        earlierBtn:!!document.querySelector('.dypastbtn'),line:t((document.getElementById('dayLine')||{}).getAttribute&&document.getElementById('dayLine').getAttribute('aria-label')),
        away:t((document.querySelector('#dayMeets .dayaway')||{}).innerText),none:t((document.querySelector('#dayMeets .daynone')||{}).innerText),
        count:meets.length,meets,selDay:(typeof selDay!=='undefined'&&selDay.value)||null,today:(typeof TODAY!=='undefined'?TODAY:null),
        foot:t((document.querySelector('#dayFoot, .calfoot')||{}).innerText)}})()"""

    report = {"label": label, "version": (vault / "VERSION").read_text().strip(), "captured": time.strftime("%d-%m-%Y %H:%M"), "port": port}

    def hover(sel_idx, name):
        """Real mouse move onto the Nth meeting title; wait for the popup; return what opened."""
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5)
        b.pump(0.4)
        pos = b.eval("""(()=>{const e=document.querySelectorAll('#dayMeets .dm')[%d]; if(!e) return null; const t=e.querySelector('.dmti')||e.querySelector('.tt');
          if(!t) return null; t.scrollIntoView({block:'center'}); const r=t.getBoundingClientRect(); return {x:r.left+Math.min(r.width/2,40), y:r.top+r.height/2, hasDmti:!!e.querySelector('.dmti')}})()""" % sel_idx)
        if not pos:
            return {"opened": False, "note": "no title element"}
        b.pump(0.3)
        pos = b.eval("""(()=>{const e=document.querySelectorAll('#dayMeets .dm')[%d]; const t=e.querySelector('.dmti')||e.querySelector('.tt'); const r=t.getBoundingClientRect();
          return {x:r.left+Math.min(r.width/2,40), y:r.top+r.height/2}})()""" % sel_idx)
        for dx in (-6, 0, 3, 6):                    # a few real moves over the title
            b.call("Input.dispatchMouseEvent", type="mouseMoved", x=pos["x"] + dx, y=pos["y"])
            b.pump(0.15)
        opened = False
        for _ in range(30):
            b.pump(0.2)
            if b.eval("!!document.querySelector('#dayMeets .dmpop')"):
                opened = True
                break
        b.pump(1.2 if opened else 0.5)
        info = b.eval("(()=>{const p=document.querySelector('#dayMeets .dmpop'); return p?{text:p.innerText.replace(/\\s+/g,' ').trim()}:null})()")
        return {"opened": opened, "popup": info, "hasDmti": pos and True}

    def shot(name):
        b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5) if not name.endswith("hover.png") else None
        b.pump(0.6)
        b.screenshot(str(out / name))

    # ---- today ----
    b.pump(0.5)
    report["today"] = b.eval(DOM)
    shot(f"today-{label}-today.png")
    h = hover(1, "today")
    report["today_hover"] = h
    # prefer a meeting whose chip would show (ended) ; the 2nd meeting is the processed one, fine for the hover
    b.screenshot(str(out / f"today-{label}-hover.png"))
    b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5)
    b.key("Escape")
    b.pump(0.5)

    # ---- past day: Friday 23rd ----
    went = False
    for how in ("menu", "prev"):
        if how == "prev":
            if b.eval("!!document.querySelector('.dayedge.l') && !document.querySelector('.dayedge.l').disabled"):
                b.eval("document.querySelector('.dayedge.l').click()")
                b.pump(1.0)
        else:
            if b.eval("!!document.querySelector('.dypastbtn')"):
                b.eval("document.querySelector('.dypastbtn').click()"); b.pump(0.8)
                report["menu_items"] = b.eval("[...document.querySelectorAll('[role=menuitem],[role=menuitemradio],[role=option]')].map(e=>e.innerText.trim())")
                b.eval("(()=>{const i=[...document.querySelectorAll('[role=menuitem],[role=menuitemradio]')].find(e=>/Friday 23/.test(e.innerText)); if(i) i.click()})()")
                b.pump(1.0)
        d = b.eval(DOM)
        if d.get("selDay") == "2026-10-23" or "Friday 23" in (d.get("todayDateText") or "").title() or "FRIDAY 23" in (d.get("todayDateText") or "").upper():
            went = True
            break
    report["went_to_friday"] = went
    report["past"] = b.eval(DOM)
    shot(f"today-{label}-past-friday-23.png")
    h = hover(1, "past")
    report["past_hover"] = h
    b.screenshot(str(out / f"today-{label}-past-hover.png"))
    b.call("Input.dispatchMouseEvent", type="mouseMoved", x=5, y=5)
    try:      # an unread day (beyond the calendar's "to"): what the page says
        b.eval("(()=>{const t=[...document.querySelectorAll('#todayDate [role=tab]')].find(e=>/wed 28/i.test(e.innerText)); if(t) t.click()})()")
        b.pump(1.0)
        report["unread_day_wed28"] = b.eval(DOM)
        b.eval("(()=>{const t=[...document.querySelectorAll('#todayDate [role=tab]')].find(e=>/mon 26/i.test(e.innerText)); if(t) t.click()})()")
        b.pump(1.0)
        report["future_day_mon26"] = b.eval(DOM)
    except Exception as e:  # noqa: BLE001
        report["unread_probe_error"] = str(e)
    report["console_errors"] = [e for e in (b.errors or [])][:10] if hasattr(b, "errors") else None
    (out / f"dom-{label}.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("went_to_friday",)}), json.dumps(report["today_hover"])[:300], json.dumps(report["past_hover"])[:300])
finally:
    if b:
        b.close()
    proc_guard.stop(srv)
    log.close()

"""#334: the weekly budget for creaite's own AI runs is off by default, holds nothing when off, asks or stops at the limit,
shows on the Usage tab and in Settings, and an ask run cannot raise or reset it.

  python3 -I probe_334_budget.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

The stand-in `claude` only logs that it was called, so "held" means the log did not grow. Checks:
  UI    Usage tab with the budget off says so and where to switch it on; on, it shows used against budget and the week's
        end date (the coming Sunday, DD-MM-YYYY, worked out from today's date); Settings has "Weekly AI budget" and "At the limit".
  HTTP  default is off in the updated vault and in the zip's settings-defaults.json; with $60 used and the budget off a typed ask
        still runs; on and over budget in confirm mode the ask answers HTTP 429 with can_continue true and starts nothing
        (the message is not echoed back); "Run anyway" (over_budget) runs; stop mode refuses even with Run anyway; a confirmed
        request and a typed "sweep" are never held; a Review route still answers; at 80% the state is warn and nothing is held.
  GUARD an ask run (reach.py hook, modes ask and confirmed) cannot Edit or Write settings.json or the usage log, and cannot run
        propose.py setting; filechange.py edit of settings.json from a run needs approval and leaves the file unchanged.
Expected on 2.6.4 (base 2.6.3): all PASS. With --control (the base has no budget) the first check fails and the rest are skipped.
"""
import datetime
import json
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import rec  # noqa: E402


def main():
    a = C.parse(__doc__)
    v = C.V("p334", identity="Sam Reid", calendar=False)

    def calls():
        f = v.r.dir / "fake_claude_calls.log"
        return len(f.read_text().splitlines()) if f.exists() else 0

    def ask(body, timeout=40):
        try:
            return v.post("/api/ask", body, timeout=timeout)
        except Exception as e:  # noqa: BLE001
            return 0, f"EXC {type(e).__name__}"

    def wait_idle():
        for _ in range(60):
            c, r = v.pj("/api/ask/running", {})
            if isinstance(r, dict) and (not r.get("run") and not r.get("running") or r.get("done") or not r.get("id")):
                return True
            time.sleep(0.5)
        return False

    def status():
        out = subprocess.run([sys.executable, "-I", str(v.vault / "system/scripts/ai_budget.py")], cwd=v.vault, capture_output=True, text=True, env=v.script_env()).stdout
        return json.loads(out) if out.strip().startswith("{") else out

    def usage_line(cost):
        now = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        (v.vault / "system/staging").mkdir(exist_ok=True)
        (v.vault / "system/staging/run-usage.jsonl").write_text(json.dumps({"at": now, "kind": "ask", "cost_usd": cost, "input": 1000, "output": 1000, "cache_read": 0, "cache_create": 0}) + "\n")

    def usage_text():
        v.b.eval("go('activity')")
        v.b.pump(1.2)
        v.b.eval("(()=>{const x=[...document.querySelectorAll('#v-activity button,#v-activity [role=tab]')].find(e=>/^Usage/.test(e.innerText.trim())); if(x) x.click()})()")
        v.b.pump(2.0)
        return v.b.eval("document.getElementById('v-activity').innerText.replace(/\\n+/g,' | ')")

    try:
        v.start()
        s = v.settings().get("ai_budget")
        rec("334 shipped default in the updated vault is off", s is not None and s.get("enabled") is False,
            f"settings.json ai_budget: {None if s is None else {k: s.get(k) for k in ('enabled', 'unit', 'weekly_dollars', 'at_limit')}}")
        z = json.loads(zipfile.ZipFile(a.new_zip).read("system/templates/settings-defaults.json")).get("ai_budget", {})
        rec("334 default off in the zip's settings-defaults.json", z.get("enabled") is False, f"enabled={z.get('enabled')}")
        if a.control or s is None:
            print("The base has no budget; the remaining checks need it and are skipped.")
            return C.finish(a)

        # ---- the pages
        usage_line(12.5)
        t = usage_text()
        i = t.lower().find("weekly ai budget")
        rec("334 Usage tab with the budget off says so and where to switch it on", i >= 0 and re.search(r"\boff\b", t[i:i + 500], re.I) and "Settings" in t[i:i + 600], t[i:i + 380] if i >= 0 else t[:300])
        v.set_settings(lambda c: c.setdefault("ai_budget", {}).update({"enabled": True, "unit": "dollars", "weekly_dollars": 50, "at_limit": "confirm"}))
        v.reload_page()
        t = usage_text()
        i = t.lower().find("weekly ai budget")
        today = datetime.date.today()
        sunday = (today + datetime.timedelta(days=6 - today.weekday())).strftime("%d-%m-%Y")
        rec("334 Usage tab with the budget on: used against budget and the week's end date", i >= 0 and "12.50" in t[i:i + 500] and "50.00" in t[i:i + 500] and sunday in t[i:i + 500],
            f"expected end {sunday}; {t[i:i + 380]}" if i >= 0 else t[:300])
        v.b.eval("go('settings')")
        v.b.pump(1.0)
        v.settings_search("At the limit")
        st = v.view_text("v-settings").replace("\n", " | ")
        rec("334 Settings has 'Weekly AI budget' and 'At the limit'", "Weekly AI budget" in st and "At the limit" in st, st[max(0, st.find("Weekly AI budget") - 20):][:300])
        print("console errors:", v.b.errors[:3])

        # ---- the budget off, $60 used
        v.set_settings(lambda c: c["ai_budget"].update({"enabled": False}))
        usage_line(60.0)
        st = status()
        rec("334 status is off with $60 used", isinstance(st, dict) and st["state"] == "off" and st["enabled"] is False, str(st)[:200])
        n0 = calls()
        c, t = ask({"message": "hello off"})
        time.sleep(1.5)
        wait_idle()
        rec("334 off: over-spend holds nothing", c == 200 and calls() == n0 + 1, f"HTTP {c}, stand-in claude calls {calls() - n0}")

        # ---- on, over budget
        v.set_settings(lambda c: c["ai_budget"].update({"enabled": True, "unit": "dollars", "weekly_dollars": 50, "at_limit": "confirm"}))
        n0 = calls()
        c, t = ask({"message": "hello over"})
        body = json.loads(t) if t.startswith("{") else {}
        rec("334 on, over budget, confirm: asks (HTTP 429) and starts nothing", c == 429 and body.get("budget", {}).get("can_continue") is True and calls() == n0 and "hello over" not in t, f"HTTP {c}: {t[:300]}")
        c, t = ask({"message": "hello anyway", "over_budget": True})
        time.sleep(1.5)
        wait_idle()
        rec("334 Run anyway goes through", c == 200 and calls() == n0 + 1, f"HTTP {c}, calls {calls() - n0}")
        v.set_settings(lambda c: c["ai_budget"].update({"at_limit": "stop"}))
        n0 = calls()
        c, t = ask({"message": "hello stop", "over_budget": True})
        body = json.loads(t) if t.startswith("{") else {}
        rec("334 stop mode: refused even with Run anyway", c == 429 and body.get("budget", {}).get("can_continue") is False and calls() == n0, f"HTTP {c}: {body.get('message')!r}")
        c, t = ask({"message": "Apply these changes", "confirmed": "Apply these changes"})
        time.sleep(1.5)
        wait_idle()
        rec("334 stop mode: a confirmed request is never held", c == 200 and calls() == n0 + 1, f"HTTP {c}, calls {calls() - n0}")
        n1 = calls()
        c, t = ask({"message": "sweep"})
        time.sleep(1.5)
        wait_idle()
        rec("334 stop mode: a typed sweep is never held", c == 200 and calls() == n1 + 1, f"HTTP {c}, calls {calls() - n1}")
        c, r = v.pj("/api/review/guesses", {})
        rec("334 stop mode: dashboard routes (a Review route) still answer", c == 200 and isinstance(r, dict) and r.get("ok") is True, f"HTTP {c}")
        v.set_settings(lambda c: c["ai_budget"].update({"at_limit": "confirm", "weekly_dollars": 70}))
        st = status()
        rec("334 at 80% the state is warn and nothing is held", isinstance(st, dict) and st["state"] == "warn", str(st)[:200])
        n0 = calls()
        c, t = ask({"message": "hello warn"})
        time.sleep(1.5)
        wait_idle()
        rec("334 warn: the ask runs", c == 200 and calls() == n0 + 1, f"HTTP {c}")

        # ---- an ask run cannot raise or reset it
        def hook(tool, inp, mode):
            return subprocess.run([sys.executable, str(v.vault / "system/scripts/reach.py"), "hook", "--run", "rtest", "--mode", mode],
                                  input=json.dumps({"tool_name": tool, "tool_input": inp}), cwd=v.vault, capture_output=True, text=True, env=v.script_env())

        res = []
        sj, ul = str(v.vault / "system/config/settings.json"), str(v.vault / "system/staging/run-usage.jsonl")
        for mode in ("ask", "confirmed"):
            for tool, inp in (("Edit", {"file_path": sj, "old_string": '"enabled": true', "new_string": '"enabled": false'}),
                              ("Write", {"file_path": sj, "content": "{}"}),
                              ("Bash", {"command": "python3 system/scripts/propose.py setting ai_budget.weekly_dollars 10000"}),
                              ("Edit", {"file_path": ul, "old_string": "60.0", "new_string": "0.0"}),
                              ("Write", {"file_path": ul, "content": ""})):
                r = hook(tool, inp, mode)
                res.append((mode, tool, r.returncode))
        rec("334 guard hook refuses settings.json and usage-log Edit/Write and propose.py setting, in both modes", all(x[2] == 2 for x in res),
            "; ".join(f"{m}/{t}->{c}" for m, t, c in res))
        before = (v.vault / "system/config/settings.json").read_bytes()
        (v.vault / "system/staging/drafts").mkdir(parents=True, exist_ok=True)
        newcfg = json.loads(before)
        newcfg["ai_budget"].update({"enabled": False, "weekly_dollars": 10000})
        (v.vault / "system/staging/drafts/new-settings.json").write_text(json.dumps(newcfg, indent=2))
        r = subprocess.run([str(v.vault / "system/scripts/run"), "filechange.py", "edit", "system/config/settings.json", "--from", "system/staging/drafts/new-settings.json", "--why", "raise budget"],
                           cwd=v.vault, capture_output=True, text=True, env={**v.script_env(), "CREAITE_RUN_ID": "rtest"})
        rec("334 filechange edit of settings.json from a run needs approval and the file is unchanged",
            r.returncode != 0 and (v.vault / "system/config/settings.json").read_bytes() == before and "approval" in (r.stdout + r.stderr).lower(),
            f"exit {r.returncode}: {(r.stdout + r.stderr).strip()[:160]}")
    finally:
        v.close()
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)

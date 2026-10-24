"""#292 and #293: the plain words on the pages (a sample of the strings that changed), and the health strings in the zip.

  python3 -I probe_ui_words.py NEW_ZIP BASE_ZIP WORK_DIR [--label 2.6.4] [--control] [--keep]

Headless Chrome at 1400 px over a scratch vault (fictional data, one staged suggestion from a fictional email).
  - Today says "Mail and Teams not checked yet today" with a Check now button (the last check in the scratch vault is two days old);
  - Settings (searched for) has "Daily check time";
  - Intake / Review calls the staged item a "suggestion";
  - Help contains "creaite folder" and "project record";
  - the zip's health code carries "The creaite app shows an old icon", "Your creaite app opens a different copy of creaite" and "Clear it".
It also prints, for information only (no check), how many times the older words (proposal, sweep, vault, tracker, Apply,
Release) still appear on each page, which is what #292 and #293 reduce but do not remove (the chat command words and some
Help lines are #347 and later work).
Expected on 2.6.4 (base 2.6.3): all PASS. With --control the two Help checks FAIL (2.6.3's Help has neither phrase); the Today,
Settings, Intake and health-string checks pass on the base too (they were already in 2.6.3 or are read from the new zip).
Wording-specific: these strings are 2.6.4's. A later release that rewords them needs this list updated, so read a FAIL on a
later version as "check the string" before "regression".
"""
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from common import rec, action  # noqa: E402

PAGES = (("today", "go('today')", "v-today"), ("intake", "go('intake-review')", "v-intake-review"), ("settings", "go('settings')", "v-settings"),
         ("help", "go('help')", "v-help"), ("work", "go('work')", "v-work"), ("files", "go('files')", "v-files"),
         ("activity", "go('activity')", "v-activity"), ("people", "go('people')", "v-people"), ("reports", "go('reports')", "v-reports"),
         ("projects", "go('projects')", "v-projects"))


def main():
    a = C.parse(__doc__)
    v = C.V("pWords", identity="Sam Reid")
    try:
        two_days_ago = (C.datetime.date.today() - C.datetime.timedelta(days=2)).isoformat()
        (v.vault / "system/staging/last-sweep.txt").write_text(f"{two_days_ago} 08:00:00\n")
        v.start(1400, 1000)
        b = v.b
        v.stage("2026-10-20-0900-pw", [action(1, "A plain-words suggestion")])
        v.reload_data()
        txt = {}
        for name, call, vid in PAGES:
            b.eval(call)
            b.pump(1.5)
            txt[name] = v.view_text(vid)
        b.eval("go('settings')")
        b.pump(1.0)
        v.settings_search("Daily check time")
        txt["settings_search"] = v.view_text("v-settings")
        T = lambda k: txt[k]  # noqa: E731
        rec("292 Today: 'Mail and Teams not checked yet today' with Check now", "Mail and Teams not checked yet today" in T("today") and "Check now" in T("today"), "")
        rec("292 Settings: 'Daily check time'", "Daily check time" in T("settings_search"), "")
        rec("292 Intake / Review calls staged items suggestions", bool(re.search(r"suggestion", T("intake"), re.I)), "")
        rec("293 Help: 'creaite folder'", "creaite folder" in T("help").lower(), "")
        rec("293 Help: 'project record'", "project record" in T("help").lower(), "")
        z = zipfile.ZipFile(a.new_zip)
        health = "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.startswith("system/scripts/health"))
        for s in ("The creaite app shows an old icon", "Your creaite app opens a different copy of creaite", "Clear it"):
            rec(f"293 health string in the zip: {s!r}", s in health, "")
        for word in ("proposal", "sweep", "vault", "tracker", "Apply", "Release"):
            counts = {k: len(re.findall(word, t)) for k, t in txt.items() if re.search(word, t)}
            print(f"info: older word {word!r} still on: {counts or 'no page'}")
        print("console errors:", b.errors[:3])
    finally:
        v.close()
    return C.finish(a)


if __name__ == "__main__":
    C.run(main)

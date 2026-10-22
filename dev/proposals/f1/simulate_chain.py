#!/usr/bin/env python3
"""Simulate the foundation chain F1 -> F2 (-> F3) on a THROWAWAY COPY of the demo vault. Python 3 standard library only.

Nothing here touches a real vault or database: it builds its own vault in a temporary folder from the repo's demo data
(projects/_portfolio and the ABC Example Programme), seeds it through the real engine (`tracker.py apply`), and for each step:

  1. takes a dated backup copy of tracker.db and a copy of the engine scripts (as update.py / tracker.py do before a migrate);
  2. applies the step's diff to the COPY's system/scripts (the repo is never edited) and runs `tracker.py migrate`, timed;
  3. checks: PRAGMA integrity_check, PRAGMA foreign_key_check, row counts of every table (before and after), an
     apply / undo round trip and a recode / undo round trip through the real commands, and the schema is up to date;
  4. proves ROLLBACK: restores the dated copy and the previous engine into a second throwaway vault and runs the OLD
     engine's apply, undo and recode against it. It also runs the OLD engine against the NEW database (no restore),
     to show what a downgrade without a restore does.

Usage:  python3 simulate_chain.py [--base <checkout of line2>] [--f1 F1.diff] [--f2 F2.diff] [--f3 F3.diff]
                                  [--f3-cmd "propose.py people migrate"] [--keep] [--work <folder>] [--json out.json]
F3 is optional: with no --f3 diff the chain stops after F2 and says so. Diffs are applied in order, each on top of the last.
"""
import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = []


def say(msg=""):
    print(msg, flush=True)


def run(vault, script, *args, check=False, timeout=900):
    """One creaite script through the vault's own wrapper (system/scripts/run), as the tests and the skills do."""
    t0 = time.time()
    p = subprocess.run([str(vault / "system/scripts/run"), script, *args], cwd=vault, capture_output=True, text=True, timeout=timeout)
    out = (p.stdout + p.stderr).strip()
    if check and p.returncode:
        raise SystemExit(f"FAILED {script} {' '.join(args)} (exit {p.returncode}) in {vault}\n{out[-1500:]}")
    return p.returncode, out, time.time() - t0


def build_vault(base, dest):
    """A copy of the demo vault from `base`: the engine, config, templates, skills and the two sample project folders."""
    ign = shutil.ignore_patterns("__pycache__", "*.pyc", "*.jsonl")
    (dest / "system").mkdir(parents=True)
    for d in ("scripts", "config", "templates"):
        shutil.copytree(base / "system" / d, dest / "system" / d, ignore=ign)
    shutil.copytree(base / ".claude", dest / ".claude", ignore=ign)
    for f in ("CLAUDE.md", "VERSION"):
        shutil.copy2(base / f, dest / f)
    shutil.copy2(base / "system/creaite-rules.md", dest / "system/creaite-rules.md")
    for tracked in ("_portfolio", "ABC Example Programme"):
        shutil.copytree(base / "projects" / tracked, dest / "projects" / tracked, ignore=ign)
    for d in ("inbox", "system/staging/applied", "system/staging/drafts", "system/history", "system/backups"):
        (dest / d).mkdir(parents=True, exist_ok=True)
    (dest / "system/processed.txt").write_text("", encoding="utf-8")
    # demo data only: nothing that reaches outside the temporary folder
    cfg = dest / "system/config/settings.json"
    data = json.loads(cfg.read_text())
    data["locations"] = {**data.get("locations", {}), "projects_root": ""}
    cfg.write_text(json.dumps(data, indent=2))


def db(vault):
    con = sqlite3.connect(vault / "system/tracker.db")
    con.row_factory = sqlite3.Row
    return con


def counts(vault):
    with closing(db(vault)) as con:
        names = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
                 if not r[0].startswith(("vault_search", "sqlite_"))]
        return {n: con.execute(f"SELECT count(*) FROM {n}").fetchone()[0] for n in names}


def pragmas(vault):
    with closing(db(vault)) as con:
        integ = con.execute("PRAGMA integrity_check").fetchall()
        fk = con.execute("PRAGMA foreign_key_check").fetchall()
    return [r[0] for r in integ], len(fk)


def table_sql(vault, table):
    with closing(db(vault)) as con:
        return con.execute("SELECT sql FROM sqlite_master WHERE name = ?", (table,)).fetchone()[0]


def propose(vault, name, items):
    p = vault / "system/staging" / f"proposed-{name}.json"
    p.write_text(json.dumps({"created": "2026-10-04T09:00:00", "source_run": "cx-edit", "files": [], "items": items}))
    return p


def new_item(n, table, **values):
    base = {"project": "ABC", "source": "simulation (demo data)"}
    if table == "actions":
        base.update(description=f"Simulated action {n}", owner="Omar Ali", priority="Medium", raised="2026-10-01")
    elif table == "raid":
        base.update(type="Risk", description=f"Simulated risk {n}", owner="Omar Ali", impact="Medium", likelihood="Low", raised="2026-10-01")
    elif table == "decisions":
        base.update(decision=f"Simulated decision {n}", made_by="Jane Doe", date="2026-10-01")
    elif table == "promises":
        base.update(promised_by="Omar Ali", promised_to="Jane Doe", description=f"Simulated promise {n}", raised="2026-10-01")
    base.update(values)
    return {"n": n, "op": "new", "table": table, "values": base, "match": "strong", "flags": [], "decision": "approved"}


def seed(vault, mix, label):
    """Seed through the real engine: `mix` is [(table, how many)] for project ABC, one proposal, one apply."""
    items, n = [], 0
    for table, k in mix:
        for _ in range(k):
            n += 1
            items.append(new_item(n, table))
    propose(vault, f"seed-{label}", items)
    code, out, secs = run(vault, "tracker.py", "apply")
    return code, out.splitlines()[-1] if out else "", secs


def max_ids(vault):
    """The highest NUMBER per table in project ABC (numeric, not text: as text ABC-A-999 sorts above ABC-A-1000)."""
    out = {}
    with closing(db(vault)) as con:
        for t, sep in (("actions", "-A-"), ("raid", "-"), ("decisions", "-D-"), ("promises", "-P-")):
            n = 0
            for (i,) in con.execute(f"SELECT id FROM {t} WHERE project='ABC'"):
                tail = i[len("ABC" + sep):]
                n = max(n, int(tail)) if tail.isdigit() else n
            out[t] = n
        out["text_sort_max_action"] = con.execute("SELECT max(id) FROM actions WHERE project='ABC'").fetchone()[0]
    return out


def clear_staging(vault):
    """Remove proposals left in staging (a held item stays in its file), so the next apply is not blocked by them."""
    for f in (vault / "system/staging").glob("proposed-*.json"):
        f.unlink()


def round_trip(vault, tag):
    """apply 3 new items + 1 update, check, undo, check; then recode ABC -> XPL, check, undo, check. Real commands."""
    res = {}
    clear_staging(vault)
    before = counts(vault)
    items = [new_item(1, "actions"), new_item(2, "raid"), new_item(3, "decisions")]
    with closing(db(vault)) as con:
        a = con.execute("SELECT id, updated_at FROM actions WHERE project='ABC' ORDER BY id LIMIT 1").fetchone()
    items.append({"n": 4, "op": "update", "table": "actions", "id": a["id"], "changes": {"priority": "High"},
                  "based_on": a["updated_at"], "match": "strong", "flags": [], "decision": "approved"})
    propose(vault, f"rt-{tag}", items)
    code, out, secs = run(vault, "tracker.py", "apply")
    mid = counts(vault)
    res["apply_exit"] = code
    res["apply_secs"] = round(secs, 1)
    res["apply_delta"] = {t: mid[t] - before[t] for t in mid if mid[t] != before[t]}
    res["new_top_ids"] = max_ids(vault)
    code, out2, secs = run(vault, "tracker.py", "undo")
    clear_staging(vault)
    after = counts(vault)
    data_tables = [t for t in after if t not in ("applies", "change_log", "item_events")]   # the audit tables only grow
    res["undo_exit"] = code
    res["undo_secs"] = round(secs, 1)
    res["undo_restores_counts"] = all(after[t] == before[t] for t in data_tables)
    with closing(db(vault)) as con:
        res["undo_priority_back"] = con.execute("SELECT priority FROM actions WHERE id=?", (a["id"],)).fetchone()[0] != "High"
    # recode ABC -> XPL (moves the folder as the tests do), apply, check, undo
    src = vault / "projects/ABC Example Programme"
    dst = vault / "projects/XPL Example Plus"
    shutil.move(str(src), str(dst))
    code, out3, secs = run(vault, "propose.py", "recode", "ABC", "XPL", "--name", "Example Plus", "--folder", "XPL Example Plus")
    res["recode_stage_exit"] = code
    if code:
        res["recode_stage_output"] = out3[-600:]
    code, out4, secs = run(vault, "tracker.py", "apply")
    res["recode_apply_exit"] = code
    res["recode_apply_secs"] = round(secs, 1)
    with closing(db(vault)) as con:
        res["recode_ids_ok"] = (con.execute("SELECT count(*) FROM actions WHERE id NOT LIKE 'XPL-%'").fetchone()[0] == 0
                                and con.execute("SELECT count(*) FROM actions WHERE project='XPL'").fetchone()[0] > 0)
        res["recode_top_action"] = con.execute("SELECT max(id) FROM actions WHERE project='XPL'").fetchone()[0]
    rc = counts(vault)
    res["recode_counts_same"] = all(rc[t] == after[t] for t in data_tables)
    code, out5, secs = run(vault, "tracker.py", "undo")
    shutil.move(str(dst), str(src))
    res["recode_undo_exit"] = code
    with closing(db(vault)) as con:
        res["recode_undone_ids_ok"] = (con.execute("SELECT count(*) FROM actions WHERE id NOT LIKE 'ABC-%'").fetchone()[0] == 0
                                       and con.execute("SELECT count(*) FROM projects WHERE code='ABC'").fetchone()[0] == 1)
    end = counts(vault)
    res["final_counts_equal_start"] = all(end[t] == before[t] for t in data_tables)
    res["tails"] = {"apply": out.splitlines()[-1:], "recode": out4.splitlines()[-1:], "recode_stage": out3.splitlines()[-1:]}
    return res


PROBE = r"""
import sys, json
sys.path.insert(0, "system/scripts")
t = "See ABC-A-1000, ABC-1001 and ABC-D-1002 (also ABC-A-999)."
out = {}
for mod, name in (("tracker", "ITEM_ID"), ("claims", "ID"), ("item_history", "ITEM_RE"), ("status_facts", "ID_RE"), ("prep_view", "ID_RE"),
                  ("extraction", "ITEM_ID"), ("drafts", "ID_RE"), ("edit_ai", "ID_RE"), ("prep_shape", "ID_RE"), ("notes_find", "ID_RE")):
    try:
        m = __import__(mod)
        r = getattr(m, name)
        out[mod + "." + name] = [x if isinstance(x, str) else x[0] for x in (m_ for m_ in r.finditer(t))] if False else [mm.group(0) for mm in r.finditer(t)]
    except Exception as e:
        out[mod + "." + name] = "error: " + type(e).__name__
print(json.dumps(out))
"""


def reader_probe(vault):
    """Which ID patterns of the engine's readers see a four-digit ID whole (the right answer: all three long IDs and ABC-A-999)."""
    p = subprocess.run([sys.executable, "-c", PROBE], cwd=vault, capture_output=True, text=True)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"error": (p.stdout + p.stderr)[-300:]}


def dated_backup(vault, label):
    """A dated copy of the database (SQLite's backup API, as tracker.backup_db does) and of the engine, before a step."""
    stamp = time.strftime("%Y-%m-%d-%H%M%S")
    dest = vault / "system/backups" / f"tracker-{stamp}-{label}.db"
    with closing(sqlite3.connect(vault / "system/tracker.db")) as s, closing(sqlite3.connect(dest)) as d:
        s.backup(d)
    eng = vault / "system/backups" / f"engine-before-{label}"
    shutil.copytree(vault / "system/scripts", eng, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest, eng


def apply_diff(vault, diff):
    p = subprocess.run(["git", "apply", "--whitespace=nowarn", str(diff)], cwd=vault, capture_output=True, text=True)
    if p.returncode:
        raise SystemExit(f"diff {diff} does not apply to the copy: {p.stderr}")


def apply_chain(vault, base):
    """The approved 2.6.1 guarded chain (dev/proposals/GUARDED-2.6.1.chain, in order) onto the copy's engine: the frozen line plus
    the chain is what 2.6.1 ships, and F1 ships on top of it. Only the engine paths are applied (the chain also holds test diffs)."""
    names = [l.strip() for l in (base / "dev/proposals/GUARDED-2.6.1.chain").read_text().splitlines() if l.strip() and not l.startswith("#")]
    for n in names:
        p = subprocess.run(["git", "apply", "--whitespace=nowarn", "--include=system/*", "--include=.claude/*", str(base / n)],
                           cwd=vault, capture_output=True, text=True)
        if p.returncode:
            raise SystemExit(f"chain diff {n} does not apply to the copy: {p.stderr}")
    return len(names)


def rollback_proof(workdir, dated_db, old_engine, base, step):
    """A second throwaway vault: the dated database copy and the PREVIOUS engine; the old engine reads and applies."""
    rb = workdir / f"rollback-{step}"
    build_vault(base, rb)
    shutil.rmtree(rb / "system/scripts")
    shutil.copytree(old_engine, rb / "system/scripts")
    shutil.copy2(dated_db, rb / "system/tracker.db")
    res = {}
    res["integrity"], res["fk_problems"] = pragmas(rb)
    code, out, _ = run(rb, "tracker.py", "migrate")
    res["old_engine_migrate"] = out.splitlines()[-1] if out else ""
    res["counts"] = counts(rb)
    res["round_trip"] = round_trip(rb, f"rb-{step}")
    res["integrity_after"], res["fk_after"] = pragmas(rb)
    shutil.rmtree(rb, ignore_errors=True)
    return res


def downgrade_without_restore(workdir, vault, old_engine, base, step):
    """The OLD engine on the NEW database with no restore: shows what an engine-only undo leaves."""
    dg = workdir / f"downgrade-{step}"
    build_vault(base, dg)
    shutil.rmtree(dg / "system/scripts")
    shutil.copytree(old_engine, dg / "system/scripts")
    shutil.copy2(vault / "system/tracker.db", dg / "system/tracker.db")
    res = {}
    propose(dg, "dg", [new_item(1, "actions")])
    code, out, _ = run(dg, "tracker.py", "apply")
    res["old_engine_apply_on_new_db"] = {"exit": code, "tail": out.splitlines()[-2:]}
    code, out, _ = run(dg, "tracker.py", "migrate")      # before any undo, so IDs above 999 are still there
    res["old_engine_migrate_on_new_db"] = {"exit": code, "tail": out.splitlines()[-2:]}
    res["counts_after_old_migrate"] = {t: counts(dg)[t] for t in ("actions", "raid", "decisions", "promises")}
    code, out, _ = run(dg, "tracker.py", "undo")
    res["old_engine_undo_on_new_db"] = {"exit": code, "tail": out.splitlines()[-1:]}
    res["integrity"], res["fk_problems"] = pragmas(dg)
    shutil.rmtree(dg, ignore_errors=True)
    return res


def step_run(vault, workdir, base, name, diffs, extra_cmds, seed_after=None, copy_files=(), chain_n=0):
    say(f"\n=== STEP {name}: {', '.join(d.name for d in diffs)} ===")
    dated, old_engine = dated_backup(vault, f"pre-{name}")
    before = counts(vault)
    sql_before = {t: table_sql(vault, t) for t in before}
    out = {"step": name, "dated_backup": dated.name, "counts_before": before}
    for d in diffs:
        apply_diff(vault, d)
    for cf in copy_files:
        shutil.copy2(cf, vault / "system/scripts" / Path(cf).name)
    code, mout, secs = run(vault, "tracker.py", "migrate")
    out["migrate_exit"], out["migrate_secs"], out["migrate_tail"] = code, round(secs, 2), mout.splitlines()[-3:]
    for cmd in extra_cmds:
        c, o, s = run(vault, *cmd.split())
        out.setdefault("extra", []).append({"cmd": cmd, "exit": c, "secs": round(s, 2), "tail": o.splitlines()[-2:]})
    after = counts(vault)
    out["counts_after"] = after
    out["tables_rebuilt_or_changed"] = [t for t in before if t in after and table_sql(vault, t) != sql_before.get(t)]
    out["row_count_changes"] = {t: [before.get(t), after.get(t)] for t in sorted(set(before) | set(after)) if before.get(t) != after.get(t)}
    out["integrity"], out["fk_problems"] = pragmas(vault)
    with closing(db(vault)) as con:
        cols = [r["name"] for r in con.execute("PRAGMA table_info(applies)")]
        out["applies_engine_version_stamped"] = (con.execute("SELECT count(*) FROM applies WHERE engine_version IS NOT NULL").fetchone()[0]
                                                 if "engine_version" in cols else "no column")
    c2, o2, _ = run(vault, "tracker.py", "migrate")
    out["second_migrate_is_noop"] = "up to date" in o2
    code, dout, _ = run(vault, "doctor.py")
    out["doctor_exit"] = code
    out["doctor_schema_lines"] = [ln for ln in dout.splitlines() if re.search(r"schema|rebuild|migrat|outdated", ln, re.I)][:4]
    if seed_after:
        out["seed_after"] = seed(vault, seed_after, f"after-{name}")
        out["staging_leftovers"] = sorted(f.name for f in (vault / "system/staging").glob("proposed-*.json"))
        out["top_ids_after_seed"] = max_ids(vault)
    out["round_trip"] = round_trip(vault, name)
    out["integrity_after_round_trip"], out["fk_after_round_trip"] = pragmas(vault)
    out["reader_probe"] = reader_probe(vault)
    out["rollback"] = rollback_proof(workdir, dated, old_engine, base, name)
    out["downgrade_without_restore"] = downgrade_without_restore(workdir, vault, old_engine, base, name)
    RESULTS.append(out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(HERE.parents[2]))
    ap.add_argument("--f1", help="F1 diff; default: the after-chain diff, or the line2 diff with --no-chain")
    ap.add_argument("--no-chain", action="store_true", help="start from the frozen line alone, without the 2.6.1 guarded chain")
    ap.add_argument("--f1-only", action="store_true", help="stop after F1 (no F2, no F3)")
    ap.add_argument("--f2", action="append", help="F2 diff(s), in order; default: the three in ../f2/")
    ap.add_argument("--f3", action="append", help="F3 diff(s), in order")
    ap.add_argument("--f3-cmd", action="append", default=[], help="a creaite command to run after F3's migrate, e.g. 'propose.py people migrate'")
    ap.add_argument("--f3-copy", action="append", default=[], help="a new file F3 adds (no diff), copied into system/scripts/ of the copy")
    ap.add_argument("--f3-fixture", help="a people register (demo data): copied into the copy as system/staging/drafts/people-fixture.md; a generated 1,000-person register is added as people-1000.md")
    ap.add_argument("--work")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--json", help="write the results here")
    a = ap.parse_args()
    base = Path(a.base).resolve()
    default_f2 = [str(HERE.parent / "f2" / n) for n in ("f2-ids-above-999.diff", "f2-readers.diff", "f2-readers-guarded-live_server.diff", "f2-sortkey.diff", "f2-sortkey-guarded.diff")]
    work = Path(a.work) if a.work else Path(tempfile.mkdtemp(prefix="creaite-sim-"))
    work.mkdir(parents=True, exist_ok=True)
    vault = work / "vault"
    say(f"throwaway work folder: {work} (nothing in it is a real vault)")
    build_vault(base, vault)
    chain_n = 0 if a.no_chain else apply_chain(vault, base)
    say(f"2.6.1 guarded chain applied to the copy: {chain_n} diffs")
    f1 = a.f1 or str(HERE / ("f1-nullable-columns.diff" if a.no_chain else "f1-nullable-columns-after-chain.diff"))
    run(vault, "tracker.py", "init", check=True)
    # Baseline on the CURRENT engine: ABC at the three-digit ceiling (999 numbers shared by actions, RAID, decisions, promises)
    code, tail, secs = seed(vault, [("actions", 700), ("raid", 150), ("decisions", 90), ("promises", 50)], "base")
    say(f"seed (990 numbers in one project, headroom of 9 below the ceiling): exit {code}, {secs:.1f}s: {tail}")
    say(f"top IDs: {max_ids(vault)}")
    # the ceiling itself: 12 more items, the current engine can write 9 (numbers 991..999); the other 3 are held in Review
    propose(vault, "ceiling", [new_item(i, "actions") for i in range(1, 13)])
    code, out, _ = run(vault, "tracker.py", "apply")
    say(f"the ceiling (current engine, 12 items asked, numbers 991..1002): exit {code}: {(out.splitlines() or [''])[-1][:200]}")
    code, out, _ = run(vault, "tracker.py", "undo")
    clear_staging(vault)
    base_counts = counts(vault)
    say(f"baseline row counts: {base_counts}")
    pre_round = round_trip(vault, "baseline")
    say(f"baseline round trip (current engine): {json.dumps(pre_round)[:700]}")
    step_run(vault, work, base, "F1", [Path(f1)], [], chain_n=chain_n)
    if a.f1_only:
        text = json.dumps({"baseline_counts": base_counts, "baseline_round_trip": pre_round, "steps": RESULTS}, indent=1, default=str)
        say(text)
        if a.json:
            Path(a.json).write_text(text)
        if not a.keep:
            shutil.rmtree(work, ignore_errors=True)
        return 0
    # F2: after the rebuild the same project grows past 999 through the real engine (201 more numbers: 1000 .. 1200)
    step_run(vault, work, base, "F2", [Path(p) for p in (a.f2 or default_f2)], [], seed_after=[("actions", 150), ("raid", 30), ("decisions", 15), ("promises", 6)])
    if a.f3 and a.f3_fixture:
        drafts = vault / "system/staging/drafts"
        shutil.copy2(a.f3_fixture, drafts / "people-fixture.md")
        rows = ["# People register", "", "## People", "", "| Full name | Email | Aliases | Organisation | Role | Hidden | VIP | Labels |", "|---|---|---|---|---|---|---|---|"]
        for i in range(1000):
            em = f"person{i:04d}@org{i % 40}.example" if i % 25 else ""
            rows.append(f"| Person Number{i:04d} | {em} | P{i} | Org {i % 40} | Role {i % 9} | {'yes' if i % 97 == 0 else ''} | "
                        f"{'management' if i % 131 == 0 else ''} | {'Label A' if i % 7 == 0 else ''} |")
        (drafts / "people-1000.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    if a.f3:
        step_run(vault, work, base, "F3", [Path(p) for p in a.f3], a.f3_cmd, copy_files=a.f3_copy)
    else:
        say("\nStage 3 (F3): no diff given, pending.")
    text = json.dumps({"baseline_counts": base_counts, "baseline_round_trip": pre_round, "steps": RESULTS}, indent=1, default=str)
    say("\n=== RESULTS (JSON) ===")
    say(text)
    if a.json:
        Path(a.json).write_text(text)
    if not a.keep:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

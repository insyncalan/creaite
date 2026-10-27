"""#329: shareable minutes and the prose that describes a Sensitive item (Alan, 27-10-2026: both).

1. A line can be held back with its item (layout.carried): distributed_of drops it while the item is withheld, keeps it when the
   item isn't, and drops it when the item has gone (fail closed). minutesDoc.js distributedOf does the same (parity, with node).
2. describing_lines lists the prose lines that may describe a withheld item and that aren't answered yet; every shareable copy
   (the export, the follow-up email) refuses while there are any, with the lines, and writes nothing.
3. The answers (Hold back with it / Keep) go through the record's own save while a draft, beside filed minutes once filed, and
   survive tracked_of, Approve minutes and track_reconcile.
Fictional demo data only.
Run: python3 dev/tests/test_minutes_shareable_329.py      (quick tier: no Chrome; the parity test needs node)
"""
import copy
import json
import shutil
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "system/scripts"))
import minutes_record as mr  # noqa: E402
import test_minutes_approve as ta  # noqa: E402
from test_minutes_approve import DRAFT, FILED, Base  # noqa: E402

SECRET = "The restructure of the client data team stays confidential until HR confirms"
ORDINARY = ["Training dates were shared with the site leads", "The test environment is ready for the pilot",
            "The client asked for weekly updates"]
RISK = "Client data team restructure may delay data access"
N_RISK = 8


def record(updates=None, carried=None, reviewed=None, internal=None, sensitive=True, items=True):
    """A small minutes record in memory: a Sensitive risk (@8) and an ordinary action (@1), the Updates lines given."""
    lines = updates if updates is not None else [SECRET] + ORDINARY
    its = {"@1": {"table": "actions", "op": "new", "n": 1, "values": {"description": "Book the UAT environment"}, "flags": []},
           "@8": {"table": "raid", "op": "new", "n": 8, "values": {"type": "Risk", "description": RISK},
                  "flags": ["sensitive"] if sensitive else []}} if items else {}
    layout = {}
    if carried is not None:
        layout["carried"] = carried
    if reviewed is not None:
        layout["reviewed"] = reviewed
    if internal is not None:
        layout["internal_only"] = internal
    return {"kind": "minutes", "state": "draft", "version": 3, "layout": layout, "items": its, "meta": {}, "sections": [
        {"id": "header", "type": "header", "text": "Meeting"},
        {"id": "summary", "type": "text", "text": "The committee met."},
        {"id": "updates", "type": "text", "text": "**Data**\n" + "\n".join(f"- {x}" for x in lines), "tags": [],
         "data": {"topics": [{"heading": "Data", "lines": [{"text": x} for x in lines]}]}},
        {"id": "raid", "type": "table", "rows": [{"ref": "@8", "n": 8, "cells": {"type": "Risk", "description": RISK}}]},
        {"id": "actions", "type": "table", "rows": [{"ref": "@1", "n": 1, "cells": {"action": "Book the UAT environment"}}]}]}


def held_of(doc):
    """The withheld refs as withheld() gives them, without a tracker: the items flagged Sensitive."""
    return {k: "Sensitive" for k, v in (doc.get("items") or {}).items() if "sensitive" in (v.get("flags") or [])}


def shared_text(doc):
    d = mr.distributed_of(doc, held_of(doc))
    return next(s for s in d["sections"] if s["id"] == "updates")["text"], json.dumps(d, ensure_ascii=False)


KEY = mr.line_key("updates", SECRET)


class Carried(unittest.TestCase):
    def test_a_carried_line_is_dropped_while_its_item_is_held(self):
        text, whole = shared_text(record(carried={KEY: "@8"}))
        self.assertNotIn(SECRET, text)
        self.assertNotIn(SECRET, whole, "nowhere in the shareable record: not its layout, not the Updates' own copy")
        for o in ORDINARY:
            self.assertIn(o, text)

    def test_a_carried_line_shows_when_its_item_is_not_held(self):
        text, _ = shared_text(record(carried={KEY: "@8"}, sensitive=False))
        self.assertIn(SECRET, text)

    def test_a_carried_line_whose_item_has_gone_is_dropped(self):
        doc = record(carried={KEY: "@8"})
        del doc["items"]["@8"]
        doc["sections"][3]["rows"] = []
        self.assertNotIn(SECRET, shared_text(doc)[0], "fail closed: the item is no longer in the record")

    def test_a_draft_ref_still_finds_its_item_once_approved(self):
        doc = record(carried={KEY: "@8"})
        doc["items"] = {("ABC-R-004" if k == "@8" else k): ({**v, "id": "ABC-R-004"} if k == "@8" else v) for k, v in doc["items"].items()}
        self.assertNotIn(SECRET, shared_text(doc)[0], "held: @8 became ABC-R-004, still Sensitive")
        doc["items"]["ABC-R-004"]["flags"] = []
        self.assertIn(SECRET, shared_text(doc)[0], "the item is found, and it is not held")

    def test_the_line_marks_never_reach_the_shareable_record(self):
        d = mr.distributed_of(record(carried={KEY: "@8"}, reviewed={"summary:The committee met.": "x"}), {})
        self.assertFalse({"carried", "reviewed", "internal_only"} & set(d["layout"]))


class Candidates(unittest.TestCase):
    def keys(self, doc):
        return [x["key"] for x in mr.describing_lines(doc, held_of(doc))]

    def test_the_329_line_is_listed_and_ordinary_lines_are_not(self):
        got = mr.describing_lines(record(), held_of(record()))
        self.assertEqual([x["text"] for x in got], [SECRET])
        self.assertEqual(got[0]["ref"], "@8")
        self.assertEqual(got[0]["item"], RISK)
        self.assertIn("restructure", got[0]["why"])

    def test_one_shared_word_is_not_enough(self):
        self.assertEqual(self.keys(record(updates=["The client asked for weekly updates"])), [])

    def test_a_line_naming_the_item_is_listed(self):
        doc = record(updates=["Moved ABC-R-004 to next month"])
        doc["items"]["@8"]["id"] = "ABC-R-004"
        self.assertEqual(self.keys(doc), [mr.line_key("updates", "Moved ABC-R-004 to next month")])

    def test_accents_are_compared_stripped(self):
        doc = record(updates=["The café réstructure was discussed"])
        doc["items"]["@8"]["values"]["description"] = "Cafe restructure"
        self.assertEqual(len(self.keys(doc)), 1)

    def test_nothing_is_listed_when_nothing_is_held(self):
        self.assertEqual(self.keys(record(sensitive=False)), [])

    def test_an_internal_only_carried_or_reviewed_line_is_not_listed(self):
        self.assertEqual(self.keys(record(internal=[{"section": "updates", "text": SECRET}])), [])
        self.assertEqual(self.keys(record(carried={KEY: "@8"})), [])
        self.assertEqual(self.keys(record(reviewed={KEY: mr.text_hash(SECRET)})), [])

    def test_a_reviewed_line_whose_words_changed_is_listed_again(self):
        changed = SECRET.replace("HR confirms", "HR has confirmed")
        doc = record(updates=[changed], reviewed={KEY: mr.text_hash(SECRET)})
        self.assertEqual(self.keys(doc), [mr.line_key("updates", changed)])
        doc = record(reviewed={KEY: "0" * 16})
        self.assertEqual(self.keys(doc), [KEY], "a reviewed mark for other words is no answer")


# ── through the vault: the export, the follow-up email, the answers and the record's rewrites ──
class Vault(Base):
    def setUp(self):
        orig = ta.spec

        def spec():
            s = orig()
            s["minutes"]["updates"] = [{"heading": "Data", "items": [SECRET] + ORDINARY}]
            s["items"].append({"table": "raid", "flags": ["sensitive"], "values": {"project": "ABC", "type": "Risk",
                                                                                  "description": RISK}})
            return s
        ta.spec = spec
        try:
            super().setUp()
        finally:
            ta.spec = orig

    def export(self, path=FILED, fmt="html"):
        return self.js("import minutes_record\n"
                       f"print(json.dumps(minutes_record.export({path!r}, {fmt!r}, False, 'distributed')))")

    def made(self, r, fmt):
        p = self.v.root / r["path"]
        return p.read_text(encoding="utf-8") if fmt == "html" else zipfile.ZipFile(p).read("word/document.xml").decode("utf-8")

    def answer(self, answers, path=DRAFT):
        return self.js("import minutes_record\n"
                       f"try:\n    r = minutes_record.change({path!r}, {{'op': 'shareable', 'answers': {answers!r}}})\n"
                       "except minutes_record.RecordError as e:\n    r = {'ok': False, 'message': str(e)}\n"
                       "r.pop('doc', None)\nprint(json.dumps(r))")

    def drafts_now(self):
        return sorted(p.name for p in (self.v.root / "system/staging/drafts").iterdir())

    def files_beside(self):
        return sorted(p.name for p in (self.v.root / FILED).parent.iterdir())

    def test_the_export_refuses_with_the_lines_and_writes_nothing(self):
        self.assertTrue(self.approve()["ok"])
        before, beside = self.drafts_now(), self.files_beside()
        for fmt in ("html", "docx", "pdf"):
            r = self.export(fmt=fmt)
            self.assertFalse(r["ok"])
            self.assertEqual(r["message"], "Review these lines before sharing.")
            self.assertEqual([x["text"] for x in r["review"]], [SECRET])
            self.assertEqual(set(r["review"][0]), {"key", "text", "item", "ref"})
        self.assertEqual(self.drafts_now(), before, "nothing in drafts")
        self.assertEqual(self.files_beside(), beside, "nothing beside the minutes")

    def test_the_follow_up_email_refuses_too(self):
        f = self.js(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({DRAFT!r}, 'distributed')))")
        self.assertFalse(f["ok"])
        self.assertEqual([x["text"] for x in f["review"]], [SECRET])
        self.assertNotIn("items", f)
        f = self.js(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({DRAFT!r}, 'internal')))")
        self.assertTrue(f["ok"], "the Internal email isn't held up")

    def test_hold_back_on_filed_minutes_leaves_the_line_out(self):
        self.assertTrue(self.approve()["ok"])
        ref = self.export()["review"][0]["ref"]
        r = self.answer([{"key": KEY, "answer": "hold", "ref": ref}], FILED)
        self.assertTrue(r["ok"], r)
        for fmt in ("html", "docx"):
            out = self.export(fmt=fmt)
            self.assertTrue(out["ok"], out)
            text = self.made(out, fmt)
            self.assertNotIn(SECRET, text)
            self.assertIn(ORDINARY[0], text)
        kept = (self.v.root / "system/staging/minutes-shareable.json").read_text(encoding="utf-8")
        self.assertNotIn("restructure", kept, "beside filed minutes: hashes and refs, never the words")
        v = self.js(f"import minutes_record\nprint(json.dumps(minutes_record.view(path={FILED!r})['doc']['layout']['carried']))")
        self.assertEqual(v, {KEY: ref}, "the view shows the line as held back")
        r = self.answer([{"key": KEY, "answer": "release"}], FILED)
        self.assertTrue(r["ok"], r)
        self.assertFalse(self.export()["ok"], "released: asked about again")

    def test_keep_on_filed_minutes_keeps_the_line(self):
        self.assertTrue(self.approve()["ok"])
        r = self.answer([{"key": KEY, "answer": "keep"}], FILED)
        self.assertTrue(r["ok"], r)
        out = self.export()
        self.assertTrue(out["ok"], out)
        self.assertIn(SECRET, self.made(out, "html"))

    def test_hold_back_on_a_draft_is_a_saved_version_and_the_email_leaves_it_out(self):
        ver = self.doc()["version"]
        r = self.answer([{"key": KEY, "answer": "hold", "ref": f"@{N_RISK}"}])
        self.assertTrue(r["ok"], r)
        doc = self.doc()
        self.assertEqual(doc["version"], ver + 1)
        self.assertEqual(doc["layout"]["carried"], {KEY: f"@{N_RISK}"})
        f = self.js(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({DRAFT!r}, 'distributed')))")
        self.assertTrue(f["ok"], f)
        self.assertNotIn("restructure", json.dumps(f, ensure_ascii=False))

    def test_the_meeting_email_leaves_a_waiting_summary_out(self):
        d = self.doc()
        line = "The client data team restructure waits for HR."     # (no "confidential": that word alone keeps a summary out)
        next(s for s in d["sections"] if s["id"] == "summary")["text"] = f"The committee met.\n\n{line}"
        self.assertTrue(self.js("import minutes_record\n" f"print(json.dumps(minutes_record.save_page({DRAFT!r}, {d!r})['ok']))"))
        email = "import drafts\nprint(json.dumps(drafts.followup_facts({'files': [%r]})))" % (DRAFT,)
        f = self.js(email)
        self.assertEqual(f["summary"], "")
        self.assertIn("may describe something kept out of the shareable version", f["note"])
        self.assertTrue(self.answer([{"key": mr.line_key("summary", line), "answer": "hold", "ref": f"@{N_RISK}"}])["ok"])
        f = self.js(email)
        self.assertIn("The committee met.", f["summary"])
        self.assertNotIn("restructure", f["summary"])

    def test_a_hand_written_request_without_answers_is_refused(self):
        self.assertTrue(self.approve()["ok"])
        for bad in ([], [{"key": KEY}], [{"key": KEY, "answer": "hold", "ref": "@1"}], [{"key": "updates:Not a line", "answer": "keep"}]):
            with self.subTest(bad=bad):
                self.assertFalse(self.answer(bad, FILED)["ok"])
        self.assertFalse(self.export()["ok"], "still refused")
        server = (REPO / "system/scripts/live_server.py").read_text(encoding="utf-8")
        self.assertIn("minutes_record.export(req.get(\"path\")", server, "the export route goes through minutes_record.export")

    def test_carried_survives_tracked_of_track_reconcile_and_approve(self):
        self.assertTrue(self.answer([{"key": KEY, "answer": "hold", "ref": f"@{N_RISK}"}])["ok"])
        t = self.js("import minutes_record, creaite_doc\n"
                    f"print(json.dumps(minutes_record.tracked_of(creaite_doc.read({DRAFT!r}))['layout']))")
        self.assertEqual(t["carried"], {KEY: f"@{N_RISK}"}, "tracked_of")
        d = self.doc()
        d["layout"]["track"] = {str(N_RISK): "", "1": "n"}
        self.js("import minutes_record\n" f"print(json.dumps(minutes_record.save_page({DRAFT!r}, {d!r})['ok']))")
        self.js(f"import minutes_record\nprint(json.dumps(minutes_record.track_reconcile({DRAFT!r})))")
        self.assertEqual(self.doc()["layout"]["carried"], {KEY: f"@{N_RISK}"}, "track_reconcile")
        self.assertTrue(self.approve()["ok"])
        filed = self.doc(FILED)
        self.assertEqual(filed["layout"]["carried"], {KEY: f"@{N_RISK}"}, "Approve minutes")
        out = self.export()
        self.assertTrue(out["ok"], out)
        self.assertNotIn(SECRET, self.made(out, "html"), "the risk, kept as a line only, is still held; so is its line")


# ── parity: minutesDoc.js distributedOf leaves out the same lines ──
JS = REPO / "system/templates/dashboard/src/components/minutes/minutesDoc.js"


def js_lines(doc, held):
    src = JS.read_text(encoding="utf-8")
    code = src[src.index("const FLAGS ="):src.index("const DEADLINE =")].replace("export function", "function").replace(
        "export const", "const")
    run = (code + f"\nconst d = distributedOf({json.dumps(doc)}, {json.dumps(held)});\n"
           "console.log(JSON.stringify(d.sections.filter(s => s.type !== 'table' && s.type !== 'header')"
           ".map(s => [s.id, mdLines(s.text || '').map(l => l.text)])));")
    out = subprocess.run(["node", "-e", run], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def py_lines(doc, held):
    d = mr.distributed_of(doc, held)
    return [[s["id"], [mr.line_text(x) for x in str(s.get("text") or "").split("\n") if x.strip()]]
            for s in d["sections"] if s.get("type") not in ("table", "header")]


@unittest.skipUnless(shutil.which("node"), "needs node")
class Parity(unittest.TestCase):
    def test_the_same_records_give_the_same_lines(self):
        gone = record(carried={KEY: "@8"})
        del gone["items"]["@8"]
        moved = record(carried={KEY: "@8"})
        moved["items"] = {"ABC-R-004": {**moved["items"]["@8"], "id": "ABC-R-004"}, "@1": moved["items"]["@1"]}
        kept = record(carried={KEY: "@8"})
        del kept["items"]["@8"]
        kept["sections"][3]["rows"] = [{"ref": None, "kept_line": True, "was": "@8", "cells": {"description": RISK}}]
        cases = {"held": record(carried={KEY: "@8"}), "not held": record(carried={KEY: "@8"}, sensitive=False),
                 "gone": gone, "approved": moved, "none": record(),
                 "internal": record(internal=[{"section": "updates", "text": ORDINARY[1]}], carried={KEY: "@1"})}
        for name, doc in cases.items():
            for held in (held_of(doc), {**held_of(doc), "@8": "Sensitive"}):     # as the route gives it: every flagged item, at least
                with self.subTest(case=name, held=held):
                    self.assertEqual(js_lines(copy.deepcopy(doc), held), py_lines(copy.deepcopy(doc), held))
        kept_out = py_lines(kept, {"@8": "Sensitive"})
        self.assertNotIn(SECRET, json.dumps(kept_out))
        self.assertEqual(js_lines(kept, {"@8": "Sensitive"}), kept_out, "a line kept in the minutes only, held")
        self.assertIn(SECRET, json.dumps(py_lines(kept, {})), "a line kept in the minutes only, not held")
        self.assertEqual(js_lines(kept, {}), py_lines(kept, {}))


if __name__ == "__main__":
    unittest.main()

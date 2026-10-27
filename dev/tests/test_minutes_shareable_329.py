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
import re
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
        self.assertIn("restructur", got[0]["why"], "the simple form of restructure")

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
            self.assertEqual(set(r["review"][0]), {"key", "kind", "text", "item", "ref", "refs"})
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
        self.assertEqual(v, {KEY: [ref]}, "the view shows the line as held back")
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
        self.assertEqual(doc["layout"]["carried"], {KEY: [f"@{N_RISK}"]})
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
        self.assertEqual(t["carried"], {KEY: [f"@{N_RISK}"]}, "tracked_of")
        d = self.doc()
        d["layout"]["track"] = {str(N_RISK): "", "1": "n"}
        self.js("import minutes_record\n" f"print(json.dumps(minutes_record.save_page({DRAFT!r}, {d!r})['ok']))")
        self.js(f"import minutes_record\nprint(json.dumps(minutes_record.track_reconcile({DRAFT!r})))")
        self.assertEqual(self.doc()["layout"]["carried"], {KEY: [f"@{N_RISK}"]}, "track_reconcile")
        self.assertTrue(self.approve()["ok"])
        filed = self.doc(FILED)
        self.assertEqual(filed["layout"]["carried"], {KEY: [f"@{N_RISK}"]}, "Approve minutes")
        out = self.export()
        self.assertTrue(out["ok"], out)
        self.assertNotIn(SECRET, self.made(out, "html"), "the risk, kept as a line only, is still held; so is its line")


# ── Cap's review (#329): rows, headings, the title and the header are checked too; every matched item counts ──
HELD = "Restructure of the client data team"
PROBE = "Brief HR on the client data team restructure before it goes public"
OTHER = "Vendor contract renewal for the Zephyr warehouse"


def probe(title="Steering committee", heading="Updates", action=PROBE, two=False):
    """Cap's probes: a shared action @1 whose words describe the Sensitive @8; the Updates heading and the title given."""
    doc = record(updates=list(ORDINARY))
    doc["title"], doc["date"] = title, "2026-10-14"
    doc["items"]["@8"]["values"]["description"] = HELD
    doc["sections"][3]["rows"][0]["cells"]["description"] = HELD
    doc["items"]["@1"]["values"]["description"] = action
    doc["sections"][4]["rows"][0]["cells"] = {"owner": "Sam Lee", "action": action, "due": "16-10-2026"}
    for s in doc["sections"]:
        s.setdefault("heading", mr.HEADINGS.get(s["id"], ""))
        s.setdefault("default_heading", mr.HEADINGS.get(s["id"], ""))
    doc["sections"][2]["heading"] = heading
    if two:
        doc["items"]["@9"] = {"table": "raid", "op": "new", "n": 9, "flags": ["sensitive"],
                              "values": {"type": "Risk", "description": OTHER}}
        doc["sections"][3]["rows"].append({"ref": "@9", "n": 9, "cells": {"type": "Risk", "description": OTHER}})
    return doc


def listed(doc):
    return {x["key"]: x for x in mr.describing_lines(doc, held_of(doc))}


def shared(doc):
    return json.dumps(mr.distributed_of(doc, held_of(doc)), ensure_ascii=False)


class CapsProbes(unittest.TestCase):
    def test_the_action_row_is_listed(self):
        got = listed(probe())
        self.assertIn("row:@1", got, "MEDIUM 1: a shared row's own words describe the held item")
        self.assertEqual(got["row:@1"]["kind"], "row")
        self.assertEqual(got["row:@1"]["refs"], ["@8"])
        self.assertNotIn("row:@8", got, "the held item's own row is not in the shareable version, so not asked about")

    def test_every_text_cell_of_a_row_counts(self):
        doc = probe(action="Book the meeting rooms")
        doc["sections"][4]["rows"][0]["cells"]["owner"] = "Client data team restructure lead"
        self.assertIn("row:@1", listed(doc), "the owner cell holds the words")

    def test_the_heading_and_the_title_are_listed(self):
        got = listed(probe(title="Client data team restructure briefing", heading="Client data team restructure",
                           action="Book the meeting rooms"))
        self.assertEqual(got["heading:updates"]["kind"], "heading")
        self.assertEqual(got["title"]["kind"], "title")

    def test_a_plain_heading_or_title_is_not_listed(self):
        got = listed(probe(action="Book the meeting rooms"))
        self.assertEqual(got, {}, "the usual headings and an ordinary title ask nothing")

    def test_the_header_lines_and_the_project_name_are_listed(self):
        doc = probe(action="Book the meeting rooms")
        doc["sections"][0]["text"] = "**When:** 14 October 2026\n\n**Location:** the client data team restructure room"
        doc["project_name"] = "Client data team restructure"
        got = listed(doc)
        self.assertEqual(got["header:Location: the client data team restructure room"]["kind"], "header")
        self.assertEqual(got["header:Client data team restructure"]["kind"], "header")

    def test_word_forms_match(self):
        for line in ("Restructuring talks with the client", "The client was restructured", "Restructurings at the client"):
            with self.subTest(line=line):      # two words shared only when the word form is read: client, and restructure
                self.assertEqual(len(listed(probe(action=line))), 1, "restructure, restructuring, restructured: one word")
        self.assertEqual(len(listed(probe(action="Restructuring talks went well"))), 0, "one shared word is still not enough")
        self.assertEqual(mr._stem("data"), "data", "four letters stay")
        self.assertEqual(mr._stem("teams"), "team")

    def test_an_id_in_any_case_is_named(self):
        for line in ("Moved abc-r-004 to next month", "Moved ABC-R-004 to next month", "Moved Abc-R-004 to next month"):
            doc = record(updates=[line])
            doc["items"]["@8"]["id"] = "ABC-R-004"
            with self.subTest(line=line):
                self.assertEqual([x["key"] for x in mr.describing_lines(doc, held_of(doc))], [mr.line_key("updates", line)])

    def test_every_matched_item_is_listed(self):
        doc = probe(action=PROBE + " and the Zephyr warehouse contract renewal", two=True)
        self.assertEqual(listed(doc)["row:@1"]["refs"], ["@8", "@9"])


class RowAnswers(unittest.TestCase):
    def test_a_row_held_back_leaves_with_its_item(self):
        doc = probe()
        doc["layout"]["carried"] = {"row:@1": ["@8"]}
        out = mr.distributed_of(doc, held_of(doc))
        self.assertNotIn(PROBE, json.dumps(out), "the row, its item and its tags are gone")
        self.assertEqual(next(s for s in out["sections"] if s["id"] == "actions")["text"], "None recorded.")
        self.assertNotIn("carried", out["layout"])
        self.assertEqual(listed(doc), {}, "answered")
        doc["items"]["@8"]["flags"] = []
        self.assertIn(PROBE, shared(doc), "its item isn't held: the row shows")

    def test_a_row_carried_by_its_number_stays_out_once_approved(self):
        doc = probe()
        doc["layout"]["carried"] = {"row:@1": ["@8"]}
        doc["sections"][4]["rows"][0]["ref"] = "ABC-A-009"
        doc["items"]["ABC-A-009"] = {**doc["items"].pop("@1"), "id": "ABC-A-009"}
        self.assertNotIn(PROBE, shared(doc))

    def test_a_row_matching_two_items_stays_out_while_either_is_held(self):
        doc = probe(action=PROBE + " and the Zephyr warehouse contract renewal", two=True)
        doc["layout"]["carried"] = {"row:@1": ["@8", "@9"]}
        self.assertNotIn("Zephyr warehouse contract", shared(doc), "both held")
        doc["items"]["@8"]["flags"] = []
        self.assertNotIn("Zephyr warehouse contract", shared(doc), "LOW 3: @9 is still held")
        doc["items"]["@9"]["flags"] = []
        self.assertIn("Zephyr warehouse contract", shared(doc), "neither is held")

    def test_a_line_matching_two_items_stays_out_while_either_is_held(self):
        line = "The client data team restructure delays the Zephyr warehouse contract renewal"
        doc = probe(action="Book the meeting rooms", two=True)
        doc["sections"][2]["text"] += f"\n- {line}"
        doc["layout"]["carried"] = {mr.line_key("updates", line): ["@8", "@9"]}
        doc["items"]["@8"]["flags"] = []
        self.assertNotIn(line, shared(doc), "LOW 3: @9 is still held")
        doc["layout"]["carried"] = {mr.line_key("updates", line): "@9"}
        self.assertNotIn(line, shared(doc), "the older single ref is read too")

    def test_one_of_two_items_gone_fails_closed(self):
        doc = probe(two=True)
        doc["layout"]["carried"] = {"row:@1": ["@8", "@7"]}
        doc["items"]["@8"]["flags"] = []
        self.assertNotIn(PROBE, shared(doc), "@7 is no longer in the record")

    def test_a_kept_row_shows_until_its_words_change(self):
        doc = probe()
        text = mr._row_text(doc["sections"][4]["rows"][0])
        doc["layout"]["reviewed"] = {"row:@1": mr.text_hash(text)}
        self.assertEqual(listed(doc), {})
        self.assertIn(PROBE, shared(doc))
        doc["sections"][4]["rows"][0]["cells"]["owner"] = "Jane Doe"
        self.assertIn("row:@1", listed(doc), "its words changed: asked again")


class HeadingAnswers(unittest.TestCase):
    def test_a_plain_heading_and_title(self):
        doc = probe(title="Client data team restructure briefing", heading="Client data team restructure",
                    action="Book the meeting rooms")
        doc["layout"]["plain"] = {"heading:updates": "plain", "title": "plain"}
        out = mr.distributed_of(doc, held_of(doc))
        self.assertEqual(next(s for s in out["sections"] if s["id"] == "updates")["heading"], "Updates")
        self.assertEqual(out["title"], "Meeting, 14-10-2026")
        self.assertNotIn("restructure", json.dumps(out).lower())
        self.assertEqual(listed(doc), {}, "answered")
        self.assertNotIn("plain", out["layout"], "the marks never reach the shareable record")

    def test_a_heading_without_a_default_takes_its_type_name(self):
        doc = probe(heading="Client data team restructure", action="Book the meeting rooms")
        doc["sections"][2]["default_heading"] = ""
        doc["layout"]["plain"] = {"heading:updates": "plain"}
        self.assertEqual(next(s for s in mr.distributed_of(doc, {})["sections"] if s["id"] == "updates")["heading"], "Updates")

    def test_a_kept_heading_stays(self):
        doc = probe(heading="Client data team restructure", action="Book the meeting rooms")
        doc["layout"]["reviewed"] = {"heading:updates": mr.text_hash("Client data team restructure")}
        self.assertEqual(listed(doc), {})
        self.assertIn("Client data team restructure", shared(doc))


class ServerChecks(unittest.TestCase):
    """_answers_of: a key the record shows, an answer its kind takes, and (to hold) a held item it matched."""
    def check(self, doc, answers):
        return mr._answers_of(doc, answers)[0]

    def refused(self, doc, answers):
        with self.assertRaises(mr.RecordError):
            self.check(doc, answers)

    def test_each_kind_takes_only_its_answers(self):
        doc = probe(title="Client data team restructure briefing", heading="Client data team restructure", two=True)
        doc["sections"][0]["text"] = "**Location:** the client data team restructure room"
        line = mr.line_key("updates", ORDINARY[0])
        head = "header:Location: the client data team restructure room"
        for key, bad in (("heading:updates", "hold"), ("title", "hold"), (head, "hold"), (head, "plain"), (line, "plain"),
                         ("row:@1", "plain"), ("row:@1", "nonsense")):
            with self.subTest(key=key, answer=bad):
                self.refused(doc, [{"key": key, "answer": bad, "ref": "@8"}])
        for key, ok in (("heading:updates", "plain"), ("title", "plain"), ("heading:updates", "keep"), (head, "keep"),
                        ("row:@1", "hold"), ("row:@1", "keep"), (line, "keep")):
            with self.subTest(key=key, answer=ok):
                self.assertEqual(self.check(doc, [{"key": key, "answer": ok, "ref": "@8"}])[0]["answer"], ok)

    def test_a_key_the_record_does_not_show_is_refused(self):
        doc = probe()
        for key in ("row:@99", "heading:nowhere", "row:@1x", "header:Not a line"):
            with self.subTest(key=key):
                self.refused(doc, [{"key": key, "answer": "keep"}])
        doc["title"] = mr.plain_title(doc)
        self.refused(doc, [{"key": "title", "answer": "plain"}])     # a plain title isn't a candidate

    def test_holding_a_row_names_a_held_item_it_matched(self):
        doc = probe(two=True)
        self.refused(doc, [{"key": "row:@1", "answer": "hold", "ref": "@9"}])     # held, but the row doesn't describe it
        self.refused(doc, [{"key": "row:@1", "answer": "hold", "ref": "@1"}])     # not held
        self.refused(doc, [{"key": "row:@1", "answer": "hold"}])                  # no item

    def test_a_hold_records_every_matched_item(self):
        doc = probe(action=PROBE + " and the Zephyr warehouse contract renewal", two=True)
        self.assertEqual(self.check(doc, [{"key": "row:@1", "answer": "hold", "ref": "@8"}])[0]["refs"], ["@8", "@9"])
        line = "The client data team restructure delays the Zephyr warehouse contract renewal"
        doc["sections"][2]["text"] += f"\n- {line}"
        got = self.check(doc, [{"key": mr.line_key("updates", line), "answer": "hold", "ref": "@9"}])
        self.assertEqual(got[0]["refs"], ["@8", "@9"], "LOW 3: a line too")


# ── through the vault: the exported shareable HTML and Word, and the follow-up email ──
class VaultReview(Base):
    """Cap's probes in a staged meeting: an action that describes the Sensitive risk, an Updates heading and a title."""
    TITLE = "[ABC] Client data team restructure briefing"

    def setUp(self):
        orig, title = ta.spec, self.TITLE

        def spec():
            s = orig()
            s["title"] = title
            s["minutes"]["updates"] = [{"heading": "Client data team restructure", "items": list(ORDINARY)}]
            s["items"][0]["values"]["description"] = PROBE
            s["items"].append({"table": "raid", "flags": ["sensitive"], "values": {"project": "ABC", "type": "Risk",
                                                                                  "description": HELD}})
            return s
        ta.spec = spec
        try:
            super().setUp()
        finally:
            ta.spec = orig
        self.draft = next(p for p in (self.v.root / "system/staging/drafts").glob("*.html"))
        self.draft = str(self.draft.relative_to(self.v.root))
        self.filed = f"{ta.ABC}/minutes/{Path(self.draft).name}"
        d = self.doc(self.draft)
        next(s for s in d["sections"] if s["id"] == "updates")["heading"] = "Client data team restructure"
        self.assertTrue(self.js("import minutes_record\n" f"print(json.dumps(minutes_record.save_page({self.draft!r}, {d!r})['ok']))"))

    def export(self, fmt="html"):
        return self.js("import minutes_record\n"
                       f"print(json.dumps(minutes_record.export({self.filed!r}, {fmt!r}, False, 'distributed')))")

    def made(self, r, fmt):
        p = self.v.root / r["path"]
        return p.read_text(encoding="utf-8") if fmt == "html" else zipfile.ZipFile(p).read("word/document.xml").decode("utf-8")

    def answer(self, answers, path):
        return self.js("import minutes_record\n"
                       f"try:\n    r = minutes_record.change({path!r}, {{'op': 'shareable', 'answers': {answers!r}}})\n"
                       "except minutes_record.RecordError as e:\n    r = {'ok': False, 'message': str(e)}\n"
                       "r.pop('doc', None)\nprint(json.dumps(r))")

    def email(self, path):
        return self.js(f"import minutes_record\nprint(json.dumps(minutes_record.followup_facts({path!r}, 'distributed')))")

    def test_the_probes_are_listed_and_each_answer_reaches_the_files(self):
        self.assertTrue(self.approve()["ok"])
        r = self.export()
        self.assertFalse(r["ok"])
        keys = {x["key"]: x["kind"] for x in r["review"]}
        self.assertEqual(keys, {"row:@1": "row", "heading:updates": "heading", "title": "title",
                                "updates:Client data team restructure": "line",            # the topic's own heading is a line
                                next(k for k in keys if k.startswith("source:")): "line"}, r["review"])
        self.assertFalse(self.email(self.filed)["ok"], "the email waits too")
        answers = [{"key": x["key"], "answer": "plain" if x["kind"] in ("heading", "title") else "hold", "ref": x["ref"]}
                   for x in r["review"]]
        self.assertTrue(self.answer(answers, self.filed)["ok"])
        kept = json.loads((self.v.root / "system/staging/minutes-shareable.json").read_text(encoding="utf-8"))["records"]
        self.assertNotIn("restructure", json.dumps(list(kept.values())).lower(), "hashes and refs only (keyed by the file's path)")
        for fmt in ("html", "docx"):
            out = self.export(fmt)
            self.assertTrue(out["ok"], out)
            text = self.made(out, fmt)
            self.assertNotIn("HR on the client", text, f"{fmt}: the row is held back")
            self.assertNotIn("restructure", text.lower(), f"{fmt}: nor the heading or title")
            self.assertIn("Meeting, 14-10-2026", text)
            self.assertIn(ORDINARY[0], text)
            self.assertNotIn("restructure", out["path"].lower(), "the file is named plainly too")
        f = self.email(self.filed)
        self.assertTrue(f["ok"], f)
        self.assertEqual(f["title"], "Meeting, 14-10-2026")
        f.pop("path")                                   # the internal minutes' own path, for the route
        self.assertNotIn("restructure", json.dumps(f).lower(), "the email's items leave the row out")

    def test_keep_keeps_each_in_the_files_and_the_email(self):
        self.assertTrue(self.approve()["ok"])
        answers = [{"key": x["key"], "answer": "keep"} for x in self.export()["review"]]
        self.assertTrue(self.answer(answers, self.filed)["ok"])
        out = self.export()
        self.assertTrue(out["ok"], out)
        text = self.made(out, "html")
        self.assertIn(PROBE, text)
        self.assertIn("Client data team restructure briefing", text)
        f = self.email(self.filed)
        self.assertTrue(f["ok"], f)
        self.assertIn(PROBE, [i["t"] for i in f["items"]])

    def test_a_draft_holds_the_row_in_its_layout_and_the_email_leaves_it_out(self):
        r = self.email(self.draft)
        row = next(x for x in r["review"] if x["kind"] == "row")
        answers = [{"key": x["key"], "answer": "hold" if x["kind"] == "row" else "keep", "ref": x["ref"]} for x in r["review"]]
        self.assertTrue(self.answer(answers, self.draft)["ok"])
        self.assertEqual(self.doc(self.draft)["layout"]["carried"], {row["key"]: [row["ref"]]})
        f = self.email(self.draft)
        self.assertTrue(f["ok"], f)
        self.assertNotIn(PROBE, [i["t"] for i in f["items"]])
        self.assertTrue(f["items"], "the other new items are still there")

    def test_the_server_refuses_a_wrong_answer_for_the_kind(self):
        self.assertTrue(self.approve()["ok"])
        row = next(x for x in self.export()["review"] if x["kind"] == "row")
        for a in ({"key": "heading:updates", "answer": "hold", "ref": row["ref"]}, {"key": "title", "answer": "hold", "ref": row["ref"]},
                  {"key": row["key"], "answer": "plain"}):
            with self.subTest(answer=a):
                self.assertFalse(self.answer([a], self.filed)["ok"])
        self.assertFalse(self.export()["ok"], "still refused")


MARK = "zephyr"


class NothingEscapes(Base):
    """Every field the shareable export shows holds the held item's words and its own tag (t01, t02…; digits are never significant
    words): each shown piece of text with the words must carry a tag that something asked about carries (describing_lines), so a
    field added to the export later, and not to shown_text, fails here."""
    def setUp(self):
        orig = ta.spec

        def spec():
            s = orig()
            s["title"] = "[ABC] Zephyr Quillon briefing t01"
            m = s["minutes"]
            m["summary"] = ["The Zephyr Quillon plan was discussed t02."]
            m["attendees"] = "Zephyr Quillon t03 (Brightwater), Jane Doe"
            m["updates"] = [{"heading": "Zephyr Quillon t04", "items": ["Zephyr Quillon moves next month t05", ORDINARY[0]]}]
            m["open_questions"] = ["Who tells the Zephyr Quillon group t06?"]
            its = s["items"]
            its[0]["values"].update(description="Book rooms", owner="Zephyr Quillon t07")       # the owner cell only
            its[1]["values"]["description"] = "Zephyr Quillon test data isn't anonymised t08"
            its[3]["values"].update(decision="Zephyr Quillon go-live stays t09", made_by="Jane Doe")
            its.append({"table": "raid", "flags": ["sensitive"], "values": {"project": "ABC", "type": "Risk",
                                                                           "description": "Zephyr Quillon restructure"}})
            return s
        ta.spec = spec
        try:
            super().setUp()
        finally:
            ta.spec = orig
        self.draft = str(next((self.v.root / "system/staging/drafts").glob("*.html")).relative_to(self.v.root))
        self.filed = f"{ta.ABC}/minutes/{Path(self.draft).name}"
        d = self.doc(self.draft)
        for i, s in enumerate(d["sections"]):
            s["heading"] = f"Zephyr Quillon t{30 + i}"
        d["sections"][0]["text"] += "\n\n**Location:** the Zephyr Quillon room t20"
        self.assertTrue(self.js("import minutes_record\n" f"print(json.dumps(minutes_record.save_page({self.draft!r}, {d!r})['ok']))"))
        self.assertTrue(self.approve()["ok"])

    def export(self, fmt):
        return self.js("import minutes_record\n"
                       f"print(json.dumps(minutes_record.export({self.filed!r}, {fmt!r}, False, 'distributed')))")

    def shown(self, fmt, path):
        """Each piece of text the made file shows: an HTML text node (and the tab title), a Word paragraph."""
        import html as h
        p = self.v.root / path
        if fmt == "html":
            page = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", p.read_text(encoding="utf-8"), flags=re.S)
            return [h.unescape(t).strip() for t in re.split(r"<[^>]+>", page) if t.strip()]
        xml = zipfile.ZipFile(p).read("word/document.xml").decode("utf-8")
        return ["".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", para)) for para in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)]

    def test_every_shown_field_is_asked_about(self):
        r = self.export("html")
        self.assertFalse(r["ok"])
        asked = [x["text"] for x in r["review"]]
        self.assertEqual({x["kind"] for x in r["review"]}, {"title", "heading", "header", "line", "row"})
        self.assertTrue(self.js("import minutes_record\n" f"print(json.dumps(minutes_record.change({self.filed!r}, "
                                f"{{'op': 'shareable', 'answers': {[{'key': x['key'], 'answer': 'keep'} for x in r['review']]!r}}})['ok']))"))
        for fmt in ("html", "docx"):
            out = self.export(fmt)
            self.assertTrue(out["ok"], out)
            pieces = [t for t in self.shown(fmt, out["path"]) if MARK in t.lower()]
            if fmt == "html":            # the fixture is honest: every field it fills is shown
                self.assertLessEqual({f"t0{i}" for i in range(1, 10)} | {"t20"}, set(re.findall(r"\bt\d\d\b", " ".join(pieces))))
            for t in pieces:
                tags = re.findall(r"\bt\d\d\b", t)
                with self.subTest(fmt=fmt, text=t):
                    self.assertTrue(tags, f"{t!r}: shown, but from no field of the fixture")
                    for tag in tags:
                        self.assertTrue(any(re.search(rf"\b{tag}\b", a) for a in asked), f"{t!r} was never asked about")


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


VIEW_JS = ("const v = d => ({title: d.title ?? null, sections: d.sections.map(s => [s.id, s.heading || '', "
           "s.type === 'table' ? (s.rows || []).map(r => rowKey(r)) : mdLines(s.text || '').map(l => l.text), "
           "((s.data || {}).topics || []).map(t => [t.heading || '', (t.lines || []).map(x => x.text)])])});\n")


def js_view(doc, held):
    src = JS.read_text(encoding="utf-8")
    code = src[src.index("const FLAGS ="):src.index("const DEADLINE =")].replace("export function", "function").replace(
        "export const", "const")
    run = code + VIEW_JS + f"console.log(JSON.stringify(v(distributedOf({json.dumps(doc)}, {json.dumps(held)}))));"
    out = subprocess.run(["node", "-e", run], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def py_view(doc, held):
    d = mr.distributed_of(doc, held)
    return {"title": d.get("title"), "sections": [
        [s["id"], s.get("heading") or "", [mr.row_key(r) for r in s.get("rows") or []] if s.get("type") == "table" else
         [mr.line_text(x) for x in str(s.get("text") or "").split("\n") if x.strip()],
         [[t.get("heading") or "", [x["text"] for x in t.get("lines") or []]] for t in (s.get("data") or {}).get("topics") or []]]
        for s in d["sections"]]}


@unittest.skipUnless(shutil.which("node"), "needs node")
class ParityReview(unittest.TestCase):
    """Cap's review: rows held back (and with two items), plain headings and title, topic lines and headings, kept rows."""
    def test_the_same_records_give_the_same_view(self):
        line = "The client data team restructure delays the Zephyr warehouse contract renewal"
        two = probe(action=PROBE + " and the Zephyr warehouse contract renewal", two=True)
        two["sections"][2]["text"] += f"\n- {line}"
        two["sections"][2]["data"]["topics"][0]["lines"].append({"text": line})
        cases = {
            "row held": (probe(), {"carried": {"row:@1": ["@8"]}}),
            "row, old single ref": (probe(), {"carried": {"row:@1": "@8"}}),
            "row with two": (two, {"carried": {"row:@1": ["@8", "@9"], mr.line_key("updates", line): ["@9", "@8"]}}),
            "row, one item gone": (probe(), {"carried": {"row:@1": ["@8", "@7"]}}),
            "plain": (probe(title="Client data team restructure briefing", heading="Client data team restructure"),
                      {"plain": {"heading:updates": "plain", "title": "plain", "heading:raid": "plain"}}),
            "topic heading held": (record(), {"carried": {mr.line_key("updates", "Data"): ["@8"]}}),
            "nothing": (probe(), {}),
        }
        kept = probe()
        kept["sections"][3]["rows"] = [{"ref": None, "kept_line": True, "was": "@8", "cells": {"description": HELD}},
                                       {"ref": None, "kept_line": True, "cells": {"description": "no item"}}]
        cases["kept lines"] = (kept, {})
        bare = record(carried={KEY: ["@8"]})
        bare["sections"][2]["text"] = ""                        # topics only: their copy of the lines is still filtered
        cases["topics only"] = (bare, {})
        for name, (doc0, layout) in cases.items():
            for flagged in ("@8", "@9", "both", "neither"):
                doc = copy.deepcopy(doc0)
                doc["layout"].update(layout)
                doc["sections"][3]["heading"] = "Client data team restructure risks"
                for ref, it in doc["items"].items():
                    if ref in ("@8", "@9"):
                        it["flags"] = ["sensitive"] if flagged in (ref, "both") else []
                held = held_of(doc)            # as the route gives it: every flagged item, at least
                for extra in ({}, {"@9": "Sensitive"} if "@9" in held or "@9" not in doc["items"] else {}):
                    with self.subTest(case=name, flagged=flagged, held={**held, **extra}):
                        self.assertEqual(js_view(copy.deepcopy(doc), {**held, **extra}), py_view(copy.deepcopy(doc), {**held, **extra}))
        self.assertNotIn("Data", json.dumps(py_view(copy.deepcopy(record(carried={mr.line_key("updates", "Data"): ["@8"]})),
                                                    {"@8": "Sensitive"})["sections"][2]), "the topic heading goes")


if __name__ == "__main__":
    unittest.main()

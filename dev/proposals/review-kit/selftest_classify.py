#!/usr/bin/env python3
"""Self-test of classify.py on synthetic logs (no checkout needed, a few seconds): a clean refusal by creaite is PASS (HELD), a produced
client file with hidden text is LEAK, a fault that is not a refusal is ERROR. Run: python3 selftest_classify.py   (exit 1 on a mismatch)"""
import os
import subprocess
import sys
import tempfile

KIT = os.path.dirname(os.path.abspath(__file__))
REFUSAL = ("creaite_doc.DocError: A client report is exported only from its checked copy (the Reporting hub's Export, "
           "client_snapshot.client_export), so nothing was exported.")
TB = f"""Traceback (most recent call last):
  File "<string>", line 6, in <module>
    creaite_doc.word_export(doc, o)
  File "creaite_doc.py", line 2257, in word_export
    raise DocError(CLIENT_ONLY_THERE)
{REFUSAL}
"""


def unittest_fail(test, body):
    return (f"\n======================================================================\nFAIL: {test} (__main__.F.{test})\n"
            f"----------------------------------------------------------------------\nTraceback (most recent call last):\n"
            f"  File \"fuzz.py\", line 82, in {test}\n{body}\n\n----------------------------------------------------------------------\n"
            f"Ran 2 tests in 1.8s\n\nFAILED (failures=1)\n")


CASES = [
    # (name, classifier, log, expected overall status)
    ("rvmd-fuzz: the bare client word_export is refused (a subprocess assertion carrying the refusal)", "rvmdfuzz",
     unittest_fail("test_word", "AssertionError: 1 != 0 : " + TB.replace("\n", "\n")) +
     "\n### client/client: HARD=False OUT=False OWN=True OTHER=False n=1\n### kit: exit 1 after 2s\n", "PASS"),
    ("rvmd-fuzz: a client file with the outside picture is a leak", "rvmdfuzz",
     "\n### client/client: HARD=False OUT=True OWN=True OTHER=False n=2\n" +
     unittest_fail("test_word", "AssertionError: [77, 13] unexpectedly found in [[77, 13]] : client/client leaks outside file") +
     "### kit: exit 1 after 2s\n", "LEAK"),
    ("rvmd-fuzz: a HELD line then the tokened export is clean", "rvmdfuzz",
     "### HELD client/client direct: " + REFUSAL + "\n\n### client/client: HARD=False OUT=False OWN=True OTHER=False n=1\n"
     "Ran 2 tests in 1.0s\n### kit: exit 0 after 2s\n", "PASS"),
    ("rvmd-fuzz: a DocError that is not a refusal (template missing) is an error, not a pass", "rvmdfuzz",
     "### HELD client/client direct: creaite_doc.DocError: The Word template is missing: system/templates/x.docx.\n"
     "Ran 2 tests in 1.0s\n### kit: exit 0 after 2s\n", "ERROR"),
    ("script probe that dies on the refusal before any result line is not a PASS", "wordwhere",
     "creaite_doc.DocError\n" + TB + "### kit: exit 1 after 0s\n", "ERROR"),   # no result line: still not a PASS
    ("word-where: refused bare call, tokened export clean", "wordwhere",
     "### HELD direct client word_export: A client report is exported only from its checked copy, so nothing was exported.\n"
     "### result: beacon lines in Word parts = 0 for 2 forms\nRan 1 test in 0.1s\n### kit: exit 0 after 1s\n", "PASS"),
    ("word-where: an address in a relationship is a leak", "wordwhere",
     "### HELD direct client word_export: so nothing was exported.\n"
     "<p> word/_rels/document.xml.rels b'<Relationship Target=\"https://beacon.example/a.png\" TargetMode=\"External\"/>'\n"
     "### result: beacon lines in Word parts = 1 for 2 forms\nRan 1 test in 0.1s\n### kit: exit 0 after 1s\n", "LEAK"),
    ("cases: a held apply and a clean control", "cases",
     "### CASE apply (kind_weekly) | HELD | exit 1 refused\n### CASE control | PASS | ok\nRan 1 test in 5s\n### kit: exit 0 after 5s\n", "PASS"),
    ("cases: one leak among clean cases", "cases",
     "### CASE a | PASS | ok\n### CASE b | LEAK | the hidden ID passed\nRan 1 test in 5s\n### kit: exit 0 after 5s\n", "LEAK"),
    ("cases: a failed control is a functional note, not a leak", "cases",
     "### CASE a | CTRL-FAIL | over-blocked\nRan 1 test in 5s\n### kit: exit 0 after 5s\n", "PASS"),
    ("cases (k26): every case SKIP is SKIP, not PASS and not ERROR", "cases",
     "### CASE a | SKIP | this tree has no edit_ai.email_outside\n### CASE b | SKIP | no caps route\nRan 1 test in 1s\n### kit: exit 0 after 1s\n", "SKIP"),
    ("cases (k26): a SKIP beside a clean case is PASS", "cases",
     "### CASE a | SKIP | no route\n### CASE b | HELD | dropped\nRan 1 test in 1s\n### kit: exit 0 after 1s\n", "PASS"),
    ("cases (k26): a SKIP never hides a LEAK", "cases",
     "### CASE a | SKIP | no route\n### CASE b | LEAK | letter-only value kept: 'Steering kqZxyw'\nRan 1 test in 1s\n### kit: exit 0 after 1s\n", "LEAK"),
    ("cases (k26): a SKIP-only probe that crashed is an error", "cases",
     "### CASE a | SKIP | x\nTraceback (most recent call last):\n  File \"x.py\", line 1\nKeyError: 'y'\n### kit: exit 1 after 1s\n", "ERROR"),
    ("cases: no result lines is an error", "cases", "Ran 1 test in 5s\n### kit: exit 0 after 5s\n", "ERROR"),
    ("cases: a test that crashed is an error", "cases",
     "### CASE a | PASS | ok\n\n======================================================================\nERROR: test_p16 (__main__.P.test_p16)\n"
     "----------------------------------------------------------------------\nTraceback (most recent call last):\nKeyError: 'x'\n\n"
     "----------------------------------------------------------------------\nRan 1 test in 5s\n\nFAILED (errors=1)\n### kit: exit 1 after 5s\n", "ERROR"),
]


def main():
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        for i, (name, cls, log, want) in enumerate(CASES):
            lp, sp, dp = (os.path.join(d, f"{i}.{x}") for x in ("log", "sum", "det"))
            open(lp, "w").write(log)
            subprocess.run([sys.executable, os.path.join(KIT, "classify.py"), f"t{i}", cls, "v", lp, sp, dp, "auto", ""], check=True)
            got = open(sp).read().split("\t")[2]
            ok = got == want
            bad += not ok
            print(("ok   " if ok else "FAIL ") + f"{got:5} (want {want:5}) {name}")
    print("classifier self-test:", "all as expected" if not bad else f"{bad} mismatch(es)")
    sys.exit(1 if bad else 0)


main()

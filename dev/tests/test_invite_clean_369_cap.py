"""#369 (Team Cap's probe of v268-bare8, his file `team-cap-369-tests` 6199a254 as posted on the issue, brought in unchanged but for the
marks below and this note): the leaks `invite_clean` had, as tests. 2.6.8 closes all of them, so every expectedFailure mark has been taken
off (the XFAIL_* sets are empty and stay as the record of what leaked). Credit: Team Cap.

Run: python3 dev/tests/test_invite_clean_369_cap.py      (quick tier: plain code, no Chrome, no Claude)

Each leak is one test method per input and per function (`scrub` for a title, place or organiser; `invite_text` for a body), so a fix
shows up case by case. A method that fails today is marked @unittest.expectedFailure (the set XFAIL, by group, with a FIXME(#369 ...)
note), so the branch is green now; when a fix lands the method reports "unexpected success" and the mark comes off. One CONTROL case per
group passes today. Cases the NOTES (dev/proposals/bare/NOTES-2.6.8.md) accept as trade-offs are left out: a secret on the next line when
the label is not alone, a value before its label, letters spelt out, a plain word after a sentence end ("Password! hunter").

All values are made up.
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[1] / "system" / "scripts"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(SCRIPTS))
import invite_clean as I  # noqa: E402

# ---- HIGH: an underscore next to a label hides it (Markdown bold and italic written with underscores) ----
# One label from each pattern set of invite_clean: _EVERYWHERE, _WITH_VALUE, _BARE and BARE_NEXT.
UNDERSCORE_LABELS = ["Passcode", "Pass code", "Passphrase", "PIN", "PIN code", "Access code", "Dial-in code", "Host key", "Meeting ID",
                     "Webinar ID", "Password", "Pw", "Pswd", "Secret", "Code", "Key", "Token", "OTP", "Access", "API key"]
VALUE = "4417"


def _underscore_cases():
    out = []
    for lab in UNDERSCORE_LABELS:
        slug = lab.lower().replace(" ", "-")
        us = lab.replace(" ", "_")
        out += [
            (f"HIGH-bold-{slug}", f"__{lab}:__ {VALUE}", VALUE),
            (f"HIGH-italic-{slug}", f"_{lab}_: {VALUE}", VALUE),
            (f"HIGH-joined-{slug}", f"{us}: {VALUE}", VALUE),
            (f"HIGH-glued-{slug}", f"{us}_{VALUE}", VALUE),
            (f"HIGH-mid-{slug}", f"Weekly sync __{lab}__ {VALUE}", VALUE),
        ]
    out += [("HIGH-bold-meeting-id-spaced", "__Meeting ID:__ 987 654 321", "987 654 321"),
            ("HIGH-joined-meeting-id-spaced", "Meeting_ID: 987 654 321", "987 654 321")]
    return out


# ---- 2 / 3: invite_text only (scrub drops the whole text) ----
# (id, body, [values that must not survive])
BODY_CASES = [
    # 2: several labels on one line keep a later value
    ("2-two-labels", "Meeting ID: Passcode:\n987 654 321\n4417\nBye", ["987 654 321", "4417"]),
    ("2-and", "Meeting ID and Passcode:\n987 654 321\n4417\nBye", ["987 654 321", "4417"]),
    ("2-slash", "ID/Passcode:\n987 654 321\n4417\nBye", ["987 654 321", "4417"]),
    # 3: a removed line uses up a waiting label's value
    ("3-removed-line", "Meeting ID:\nPasscode: 4417\n987 654 321\nBye", ["987 654 321", "4417"]),
    ("3-join-url", "Meeting ID:\nhttps://zoom.example.invalid/j/5550001111\n987 654 321\nBye", ["987 654 321"]),
]
# ---- 4: meeting-ID labels the cleaner does not know ----
ID_CASES = [
    ("4-zoom-id", "Zoom ID 4417", "4417"),
    ("4-room-id-dash", "Room ID - 4417", "4417"),
    ("4-mtg-id", "Mtg ID 4417", "4417"),
    ("4-join-with-id", "Join with ID 987 654 321", "987 654 321"),
    ("4-meeting-hash", "Meeting #: 987 654 321", "987 654 321"),
    ("4-meeting-colon", "Meeting: 987 654 321", "987 654 321"),
    ("4-id-is", "ID is 4417", "4417"),
    ("4-zoom-id-alone", "Zoom ID:\n987 654 321", "987 654 321"),
]
# ---- 5: a sentence end, then digits ----
SENTENCE_LABELS = ["Token", "Secret", "OTP", "Code", "API key", "Key", "Access"]
MARKS = {"stop": ".", "comma": ",", "semi": ";", "bang": "!", "query": "?"}


def _sentence_cases():
    out = [(f"5-{lab.lower().replace(' ', '-')}-{name}", f"{lab}{m} 4417", "4417") for lab in SENTENCE_LABELS for name, m in MARKS.items()]
    out.append(("5-meeting-id-newline", "Meeting ID.\n987 654 321", "987 654 321"))
    return out


# Controls: they pass today, one per group.
CONTROLS = [
    ("control-HIGH-markdown-stars", "**Passcode:** 4417", "4417"),
    ("control-2-labels-in-a-row", "Meeting ID:\nPasscode:\n987 654 321\n4417\nBye", "4417"),
    ("control-3-one-label", "Passcode:\n4417\nBye", "4417"),
    ("control-4-meeting-id", "Meeting ID: 987 654 321", "987 654 321"),
    ("control-5-access-code", "Access code. 4417", "4417"),
]

# Cases that fail today, by group. Delete an id here when its fix lands (the method then reports "unexpected success").
# FIXME(#369 HIGH): `_` is \w, so `(?<![\w-])` / `(?![\w-])` stop a label being seen next to an underscore.
XFAIL_HIGH = {
}
# FIXME(#369 2): several labels on one line.
XFAIL_2 = {
}
# FIXME(#369 3): a removed line uses up a waiting label.
XFAIL_3 = {
}
# FIXME(#369 4): unknown meeting-ID labels.
XFAIL_4 = {
}
# FIXME(#369 5): sentence end, then digits.
XFAIL_5 = {
}
XFAIL = XFAIL_HIGH | XFAIL_2 | XFAIL_3 | XFAIL_4 | XFAIL_5


def _wrap(text):
    return "Agenda: budget\n" + text + "\nEnd"


def _scrub_test(text, vals):
    def t(self):
        out = I.scrub(text, 140)
        for v in vals:
            self.assertNotIn(v, out, f"scrub({text!r}) keeps {v!r}")
    return t


def _body_test(text, vals):
    def t(self):
        out = I.invite_text(_wrap(text))
        for v in vals:
            self.assertNotIn(v, out, f"invite_text({text!r}) keeps {v!r}")
    return t


class Leaks369(unittest.TestCase):
    """One method per case and function, made below."""


def _add(cid, fn, maker, text, vals):
    name = "test_" + fn + "_" + cid.replace("-", "_")
    t = maker(text, vals)
    t.__name__ = name
    if name in XFAIL:
        t = unittest.expectedFailure(t)
    setattr(Leaks369, name, t)


for _cid, _text, _val in [*_underscore_cases(), *ID_CASES, *_sentence_cases(), *CONTROLS]:
    _add(_cid, "scrub", _scrub_test, _text, [_val])
    _add(_cid, "body", _body_test, _text, [_val])
for _cid, _text, _vals in BODY_CASES:
    _add(_cid, "body", _body_test, _text, _vals)


if __name__ == "__main__":
    unittest.main()

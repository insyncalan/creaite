#!/usr/bin/env python3
"""Reads one probe's log and appends to SUMMARY.tsv (one line: script, variant, PASS|LEAK|ERROR, evidence) and to DETAIL.tsv (one line per case).

usage: classify.py <id> <classifier> <variant> <log> <summary.tsv> <detail.tsv> <rc|auto> <args>

PASS  = the probe ran to its end and nothing it plants reached the client output (a refusal is a PASS).
LEAK  = at least one case put planted material into a client output (a LEAK is never turned into an ERROR by a later crash).
ERROR = the probe did not finish or could not be read (timeout, crash, import failure, a script that no longer exists in the tree,
        too few results): never PASS.
Everything that decides "benign" is written down in the BENIGN_* sets below, with the reason."""
import ast
import json
import os
import re
import sys

PASS, LEAK, ERROR, SKIP = "PASS", "LEAK", "ERROR", "SKIP"

# ---- known-benign accepted values (judged on v2.5.0; each is a style value with no outside address, no picture and no words) ----
BENIGN_ATK_CSS = {  # rv241/atk_css.py: the 13 values the gate keeps on v2.5.0
    "url nbsp then frag-looking", "url quoted nbsp frag", r"url quoted \x1f frag",   # url() whose value is only a '#fragment' (local)
    "element()", "paint()", "attr url", "env()",                                     # no address; element()/paint() refer to nothing
    "@font-face local", "filter frag", "frag w/ escaped quote", "quote mismatch",   # local() font, '#fragment' only
    "url nested via var+ident split", "url with fullwidth paren"}                    # custom property text, not a function token
BENIGN_ACCEPTED_CSS = {  # rc250/css_fuzz.py: ACCEPTED lines that are not addresses
    "var() split", "attr()", "element()", "paint()", "url fullwidth paren"}
DERIVED_NOT_GATED = {"items-inject", "doc-title", "client-field", "sources", "meta", "project_name"}   # rcleak test_a: on v2.5.0 the gate read
# these stored fields and caught them. Since v2.5.1/2.5.3 (I0, M3, M4, K3) a client report's header, items, meta and sources are DERIVED or
# dropped before the gate, so there is nothing stored left to find. What reaches a file is judged by ms1-header, ms1-fields and sweepclass-*.
KNOWN_GATE_MISSES = {"clean", "hidden-sec", "marker-INTERNAL", "title-partial", "conf-split", "owner-init"}  # rcleak test_a on v2.5.0: 'clean' is the
# control, 'hidden-sec' is a hidden section (never exported), the other four are heuristics the gate does not claim (an uppercase INTERNAL:
# with no 'only', a partial title, a split word, initials). A NEW miss is a LEAK.
HIDDEN_PROBES = {"ms_ABC-005", '"ABC-" "005"', "attr(lang)", "⁣", "͏"}  # test_atk.py: obfuscations of the HIDDEN id ABC-005


def short(s, n=170):
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s if len(s) <= n else s[: n - 3] + "..."


class R:
    """A result: cases = [(name, status, evidence)]."""

    def __init__(self, text, args):
        self.text, self.args = text, args
        self.cases, self.notes, self.errors = [], [], []

    def case(self, name, status, ev=""):
        self.cases.append((short(name, 90), status, short(ev)))

    def err(self, msg):
        self.errors.append(msg)

    def status(self):
        n_leak = sum(1 for c in self.cases if c[1] == LEAK)
        if n_leak:
            return LEAK
        if self.errors or not self.cases:
            return ERROR
        if all(c[1] == SKIP for c in self.cases):      # k26: the tree has not got the feature the probe is about (not an error, not a pass)
            return SKIP
        return PASS

    def evidence(self):
        leaks = [c for c in self.cases if c[1] == LEAK]
        st = self.status()
        n = len(self.cases)
        if st == LEAK:
            first = "; ".join(f"{c[0]}: {c[2]}" if c[2] else c[0] for c in leaks[:3])
            more = f" (+{len(leaks) - 3} more)" if len(leaks) > 3 else ""
            e = f"{len(leaks)} of {n} cases leak: {first}{more}"
            if self.errors:
                e += " | also: " + self.errors[0]
            return short(e, 400)
        if st == ERROR:
            return short("; ".join(self.errors) if self.errors else "no result lines found in the log", 400)
        if st == SKIP:
            return short(f"{n} case(s) skipped: " + "; ".join(sorted({c[2] for c in self.cases})), 400)
        refused = sum(1 for c in self.cases if c[2].startswith("refused"))
        return short(f"{n} case(s) clean" + (f" ({refused} refused)" if refused else "") + (" | " + "; ".join(self.notes) if self.notes else ""), 400)


# ---- a clean refusal by creaite is HELD, never a leak -------------------------------------------------------------------
# creaite refuses by raising (DocError, SnapshotError, PictureRefused, LogoRefused, PageRefused ...) or by answering ok=False with a
# sentence. A probe that calls an internal function directly (not a route) then sees a traceback or an assertion on the return code.
# That is creaite holding the file back, not a leak: only a PRODUCED client file that holds hidden text is a LEAK.
REFUSAL_EXC = re.compile(r"(?:^|\.)(?:PictureRefused|LogoRefused|PageRefused|ClientRefused|Refused\w*|\w+Refused)$")   # always a refusal;
# DocError and SnapshotError are also raised for faults (a missing template), so those count only with a refusal sentence (REFUSAL_WORDS)
REFUSAL_WORDS = re.compile(
    r"exported only from its checked copy|nothing was exported|so nothing was|isn't exported|is not exported|not exported|"
    r"not approved|nothing is approved|nothing was (?:approved|filed|kept|made)|checked copy|"
    r"possible internal content|\brefus(?:ed|es|al)\b|\bheld\b|\bwithheld\b|isn't this report|can't be (?:exported|filed|approved)", re.I)


def exception_lines(body):
    """The exception lines of a traceback text, last first: 'module.Class: message' (a chained traceback has several)."""
    out = []
    for ln in body.splitlines():
        m = re.match(r"^([A-Za-z_][\w.]*(?:Error|Exception|Refused|Exit)\w*)(?:: (.*))?$", ln.strip())
        if m:
            out.append((m.group(1), m.group(2) or ""))
    return out[::-1]


def refusal_in(body):
    """The refusal sentence when the last exception of `body` is creaite refusing (a known refusal exception class, or a known refusal
    sentence in a DocError-like message); else None. An AssertionError is never a refusal (it is the probe's own check)."""
    exc = exception_lines(body)
    if not exc:
        return None
    cls, msg = exc[0]
    if cls.endswith("AssertionError") and not REFUSAL_WORDS.search(msg):
        return None
    if cls.endswith("AssertionError"):
        # unittest's assertEqual(returncode, 0, stderr): the stderr text holds the child's own traceback; judge that
        inner = exception_lines(msg.replace("\\n", "\n")) or exception_lines(body)
        for c, m in inner:
            if c.endswith("AssertionError"):
                continue
            return short(f"{c}: {m}", 160) if REFUSAL_EXC.search(c) or REFUSAL_WORDS.search(m) else None
        return None
    if REFUSAL_EXC.search(cls) or REFUSAL_WORDS.search(msg):
        return short(f"{cls}: {msg}", 160)
    return None


def unittest_blocks(text):
    """[(kind 'FAIL'|'ERROR', test name, body)] from a unittest log."""
    out = []
    parts = re.split(r"^={50,}\n((?:FAIL|ERROR): \S+.*)\n-{50,}\n", text, flags=re.M)
    for i in range(1, len(parts), 2):
        head, body = parts[i], parts[i + 1]
        body = re.split(r"^(?:={50,}|-{50,}\nRan \d+ test)", body, flags=re.M)[0]
        kind, name = head.split(": ", 1)
        out.append((kind, name.split()[0], body))
    return out


# ---- shared checks on the raw log -------------------------------------------------------------------------------------
def harness(text, r, unittest_probe=True, need_ran=True):
    """Timeout, crash, import failure, unittest ERROR or FAILED -> an error on the result (assertion FAILs are handled by the caller).
    A clean refusal by creaite (see refusal_in) is a HELD case on the result, never an error and never a leak."""
    if "### kit: TIMEOUT" in text:
        r.err("timeout (probe stopped by the watchdog)")
    m = re.search(r"ImportError: (.*)|AttributeError: (.*)|ModuleNotFoundError: (.*)", text)
    if m and "Traceback" in text:
        r.err("probe cannot run on this tree: " + short(next(g for g in m.groups() if g), 150))
    elif "Traceback (most recent call last)" in text and not re.search(r"^Ran \d+ test", text, re.M):
        held = refusal_in(text[text.rfind("Traceback (most recent call last)"):])
        if held:
            r.case("probe stopped by a refusal", PASS, "refused: " + held)
        else:
            last = [ln for ln in text.splitlines() if ln.strip() and not ln.startswith("###") and "Error" in ln or "Exception" in ln]
            r.err("crashed: " + short(last[-1] if last else "traceback", 150))
    if unittest_probe:
        if need_ran and not re.search(r"^Ran \d+ tests? in", text, re.M) and not r.errors:
            r.err("no 'Ran N test' line: the probe did not finish")
        for kind, name, body in unittest_blocks(text):
            if kind != "ERROR":
                continue
            held = refusal_in(body)
            if held:
                r.case("test " + name + " stopped by a refusal", PASS, "refused: " + held)
                continue
            r.err("test error in " + name)
            m = re.search(r"^(\w*Error|\w*Exception|KeyError)[: ].*$", body, re.M)
            if m:
                r.errors[-1] += " -> " + short(m.group(0), 110)
            break


def literal(s):
    try:
        return ast.literal_eval(s)
    except Exception:
        return None


# ---- classifiers ------------------------------------------------------------------------------------------------------
def c_leakfix(text, args):
    """atk/*, rv2b, rv241: '### label: {'internal': ..., 'client': ...}'. Only the CLIENT value counts."""
    r = R(text, args)
    harness(text, r)
    for m in re.finditer(r"^### (.*): (\{'internal'.*\})\s*$", text, re.M):
        d = literal(m.group(2))
        if not isinstance(d, dict) or "client" not in d:
            r.err("unreadable line: " + short(m.group(0), 80)); continue
        v = str(d["client"])
        if v.startswith("KEPT"):
            probes = re.search(r"probes=(\[.*\])", v)
            if "LEAK" in v:
                r.case(m.group(1), LEAK, v)
            elif probes:
                found = set(literal(probes.group(1)) or [])
                bad = found & HIDDEN_PROBES or {p for p in found if p not in HIDDEN_PROBES and p != "\\41 BC"}
                r.case(m.group(1), LEAK if bad else PASS, ("obfuscated hidden id / picture kept: " + str(sorted(bad))) if bad else "kept; only the visible id ABC-A-001 (not hidden in this fixture)")
            else:
                r.case(m.group(1), LEAK, v)
        else:
            r.case(m.group(1), PASS, "refused: " + v if v != "dropped" else "dropped")
    if not r.cases:
        r.err("no '### label: {...}' result lines")
    return r


def c_otherpaths(text, args):
    r = R(text, args)
    harness(text, r)
    active = ("<p style=", "<style>.page", '<img src="data:', '<img src="https://beacon', "url(")
    for m in re.finditer(r"^### (.*): html-hits=(.*?) word-hits=(.*)$", text, re.M):
        hh = m.group(2).strip()
        hits = literal(hh) if hh.startswith("[") else hh
        if m.group(3).startswith("'word error"):
            r.err("word export failed: " + m.group(3)[:60])
        bad = [h for h in hits if h in active] if isinstance(hits, list) else []
        r.case(m.group(1), LEAK if bad else PASS, f"active markup kept in the HTML: {bad}" if bad else
               ("a plain link the author wrote (not fetched)" if hits and isinstance(hits, list) else ""))
    if not r.cases:
        r.err("no result lines")
    return r


def c_kept(text, args, benign, label_kept="KEPT", label_ok=("refused", "dropped")):
    r = R(text, args)
    harness(text, r, unittest_probe=False)
    for m in re.finditer(r"^(KEPT|ACCEPTED|refused|dropped)\s+(.*)$", text, re.M):
        kind, label = m.group(1), m.group(2).strip()
        if kind in ("KEPT", "ACCEPTED"):
            ok = label in benign
            r.case(label, PASS if ok else LEAK, "accepted (judged benign: no address, picture or words)" if ok else "the client gate accepted it")
        else:
            r.case(label, PASS, "refused" if kind == "refused" else "dropped")
    if not r.cases:
        r.err("no KEPT/refused/dropped lines")
    return r


def c_keptcss(text, args):
    return c_kept(text, args, BENIGN_ATK_CSS)


def c_acceptedcss(text, args):
    return c_kept(text, args, BENIGN_ACCEPTED_CSS)


def c_keptjpeg(text, args):
    r = R(text, args)
    harness(text, r, unittest_probe=False)
    for m in re.finditer(r"^(KEPT|dropped|refused)\s+(.*)$", text, re.M):
        r.case(m.group(2), LEAK if m.group(1) == "KEPT" else PASS, "metadata kept" if m.group(1) == "KEPT" else m.group(1))
    if "PictureRefused" in text and not r.cases:
        r.case("first case", PASS, "refused (PictureRefused raised; this script does not catch it)")
    if not r.cases:
        r.err("no result lines")
    return r


def c_beacon(text, args):
    r = R(text, args)
    harness(text, r)
    for m in re.finditer(r"^### (.*): (.*)$", text, re.M):
        v = m.group(2)
        if v.startswith("KEPT beacon"):
            r.case(m.group(1), LEAK, "outside address kept in the client file")
        elif v.startswith("built, beacon gone"):
            r.case(m.group(1), PASS, "built; address gone")
        else:
            r.case(m.group(1), PASS, "refused: " + v)
    if not r.cases:
        r.err("no result lines")
    return r


def c_svglogo(text, args):
    r = R(text, args)
    harness(text, r)
    m = re.search(r"### client export: (.*?) \| svg logo with its comment/desc/metadata kept in client file: (True|False)", text)
    if m:
        r.case("svg logo metadata in client HTML", LEAK if m.group(2) == "True" else PASS,
               "comment/desc/metadata of an SVG logo kept in the client file" if m.group(2) == "True" else "metadata gone")
    else:
        r.err("no result line")
    return r


def held_cases(text, r):
    """Probes that call creaite_doc.word_export on a client document print '### HELD direct client word_export: <sentence>' (creaite
    refused the bare call: a clean PASS) or '### NOT-HELD ...' (a client file was made without the checked copy: noted; its content is
    judged by the probe's own result lines)."""
    for m in re.finditer(r"^### HELD direct client word_export: (.*)$", text, re.M):
        if REFUSAL_WORDS.search(m.group(1)):
            r.case("bare word_export of a client document", PASS, "HELD (creaite refused): " + short(m.group(1), 110))
        else:
            r.err("bare word_export of a client document failed, not a refusal: " + short(m.group(1), 90))
    if re.search(r"^### NOT-HELD direct client word_export", text, re.M):
        r.notes.append("a bare word_export made a client Word file without the checked copy (judged by content below)")


def c_wordwhere(text, args):
    r = R(text, args)
    harness(text, r)
    held_cases(text, r)
    m0 = re.search(r"^### result: beacon lines in Word parts = (\d+)", text, re.M)
    if not m0:
        r.err("no '### result:' line (the probe did not get to the Word parts)")
        return r
    hits = [ln for ln in text.splitlines() if re.search(r"\bword/\S+ b['\"]", ln)]
    for ln in hits:
        part = re.search(r"(word/\S+) b['\"]", ln).group(1)
        ctx = ln.split(part, 1)[1]
        rel = part.endswith(".rels") or "Target=" in ctx or "TargetMode" in ctx or "r:link" in ctx or "r:embed" in ctx
        r.case(ln[:50] + " @ " + part, LEAK if rel else PASS,
               "an outside address in a relationship (the Word file would fetch it)" if rel else "the address is escaped TEXT in the body (not fetched)")
    if not hits:
        r.case("beacon in any Word part", PASS, "no outside address in the Word file")
    return r


def c_csp(text, args):
    r = R(text, args)
    harness(text, r)
    m = re.search(r"### build: (.*)", text)
    if not m:
        r.err("no build line"); return r
    if m.group(1).strip() != "KEPT":
        r.case("unclosed url( stylesheet", PASS, "refused at build: " + m.group(1).strip())
    else:
        h = re.search(r"WITH the page as built: beacon hits in Chrome = (\d+)", text)
        if not h:
            r.err("page built but no Chrome result")
        else:
            r.case("Chrome fetch of the unclosed url(", LEAK if int(h.group(1)) else PASS, f"beacon hits in Chrome = {h.group(1)}")
    return r


def c_logopath(text, args):
    r = R(text, args)
    harness(text, r)
    held_cases(text, r)
    m = re.search(r"arbitrary path embedded: (True|\[.*?\]|False)", text)
    if not m:
        r.err("no result line"); return r
    r.case("outside file as a header logo in the Word media", LEAK if m.group(1) == "True" else PASS,
           "an arbitrary path from the saved document was embedded in word/media" if m.group(1) == "True" else "not embedded")
    m2 = re.search(r"html render has secret path: (True|False)", text)
    if m2:
        r.case("path echoed in the HTML", LEAK if m2.group(1) == "True" else PASS, "")
    return r


def c_sprobe(text, args):
    r = R(text, args)
    harness(text, r)
    for ln in text.splitlines():
        if "NOT REFUSED" in ln:
            r.case("save/remove of an odd kind", LEAK, ln)
    checks = [("firm unchanged: True client unchanged: True", "S6/S13 firm and client logo files untouched by a partner save"),
              ("target kept: True link kept: True", "S10 a symlink in the logos folder is not followed"),
              ("DEF file kept: True", "S11 another project's logo kept"),
              ("save to orphan refused: True", "S12 save to an orphan refused"),
              ("cross-project remove refused: True", "cross-project remove refused")]
    for needle, name in checks:
        if needle in text:
            r.case(name, PASS, "")
        else:
            r.case(name, LEAK if re.search(re.escape(needle.split(":")[0]), text) else PASS, "expected line missing or false")
    if "S2/S3/S5/S7 batch done" not in text:
        r.err("batch of odd kinds did not finish")
    if not any(c[1] == LEAK for c in r.cases):
        r.notes.append("S14 'firm remove ok' is informational (the server has no extra guard)")
    return r


def c_cap(text, args):
    r = R(text, args)
    harness(text, r)
    for m in re.finditer(r"^### (\w+) \((\d+) chars\) (\w+): (.*?) img srcs (\[.*\])", text, re.M):
        srcs = m.group(5)
        ok = m.group(4).strip() in ("built",) and srcs != "[]" and "BROKEN" not in srcs
        if m.group(3) == "client" and REFUSAL_WORDS.search(m.group(4)):
            r.case(f"{m.group(3)} export of a {m.group(2)}-char logo", PASS,
                   "HELD by design (v2.5.1 step 3): a client report never uses a page the browser drew: " + short(m.group(4), 80))
            continue
        r.case(f"{m.group(3)} export of a {m.group(2)}-char logo", PASS,
               ("logo survives " + srcs) if ok else "FUNCTIONAL (not a leak): the logo did not survive: " + short(m.group(4) + " " + srcs, 90))
    if not r.cases:
        r.err("no result lines")
    return r


def c_svgfuzz(text, args):
    r = R(text, args)
    harness(text, r, unittest_probe=False)
    if "has no attribute 'clean_svg'" in text:
        r.errors = ["the tree has no logo_check.clean_svg (no SVG rebuild): set KIT_SVG_CLEAN=module.function if step 1 named it differently"]
        return r
    for m in re.finditer(r"^(.+?)\s+-> (None \(dropped\)|wf|NOT-WF)(.*)$", text, re.M):
        name, how, rest = m.group(1).strip(), m.group(2), m.group(3)
        lk = re.search(r"leak=(\[.*?\])", rest)
        leaked = literal(lk.group(1)) if lk else []
        if how.startswith("None"):
            r.case(name, PASS, "dropped")
        elif leaked:
            r.case(name, LEAK, f"kept in the rebuilt SVG: {leaked}")
        else:
            r.case(name, PASS, "rebuilt, nothing planted left" + (" (not well-formed: functional)" if how == "NOT-WF" else ""))
    if not r.cases:
        r.err("no result lines")
    return r


def c_mdpath(text, args):
    r = R(text, args)
    harness(text, r)
    held_cases(text, r)
    m = re.search(r"outside \(77,13\) embedded: (True|False) \| vault doc \(66,14\) embedded: (True|False)", text)
    if not m:
        r.err("no result line"); return r
    r.case("Markdown picture naming a file outside the vault", LEAK if m.group(1) == "True" else PASS, "outside file embedded in the client Word" if m.group(1) == "True" else "not embedded")
    r.case("Markdown picture naming documents/vault.png", LEAK if m.group(2) == "True" else PASS, "a documents/ file embedded" if m.group(2) == "True" else "not embedded")
    return r


def c_routemd(text, args, which="both"):
    r = R(text, args)
    harness(text, r)
    m = re.search(r"### media: (\[.*\]) \| OUTSIDE FILE EMBEDDED: (True|False)", text)
    ex = re.search(r"### export: (True|False) (.*)", text)
    if not ex:
        r.err("no export line"); return r
    pic = logo = None
    stored = re.search(r"### stored logos: (.*)", text)
    stored_paths = bool(stored and "'path'" in stored.group(1))
    if ex.group(1) == "False" or not m:
        pic, logo, why = PASS, PASS, "refused: " + short(ex.group(2), 80)
        n = 0
    else:
        sizes = literal(m.group(1)) or []
        n = sum(1 for s_ in sizes if tuple(s_) == (77, 13))
        why = ""
        if n == 0:
            pic, logo = PASS, PASS
        elif stored_paths and n <= 2:
            pic, logo = PASS, LEAK           # as many outside pictures as logos planted (firm + partner:zzz): they are the logos
        elif stored_paths:
            pic, logo = LEAK, LEAK
        else:
            pic, logo = LEAK, PASS
    if which in ("both", "pic"):
        r.case("Markdown picture line planted in every text section", pic, why or (f"outside file embedded x{n}" if pic == LEAK else "not embedded"))
    if which in ("both", "logo"):
        r.case("foreign logo path in the saved header (firm + partner:zzz)", logo, why or (f"outside file embedded as a logo (x{min(n, 2)} in word/media)" if logo == LEAK else "not embedded"))
        r.case("logo path kept in the saved draft", LEAK if stored_paths else PASS, "the stored header still carries `path`" if stored_paths else "no path stored")
    return r


def c_routemd_pic(text, args):
    return c_routemd(text, args, "pic")


def c_routemd_logo(text, args):
    return c_routemd(text, args, "logo")


def c_rvmdaud(text, args):
    r = R(text, args)
    harness(text, r)
    m = re.search(r"^### \['(.*?)', (True|False), (\[.*?\])\] (True|False) (.*)$", text, re.M)
    if not m:
        r.err("no result line"); return r
    ready, ok = m.group(2) == "True", m.group(4) == "True"
    if ok and not ready:
        r.case("client draft with audience internal exported", LEAK, "exported although the gate was not ready")
    else:
        r.case("client draft with audience internal exported", PASS, ("refused: " if not ok else "exported clean, ") + short(m.group(5), 80))
    return r


def c_rvmdfuzz(text, args):
    r = R(text, args)
    harness(text, r)
    for m in re.finditer(r"^### (\w+/\w+): HARD=(\w+) OUT=(\w+) OWN=(\w+) OTHER=(\w+) n=(\d+)", text, re.M):
        bad = [k for k, v in (("hard-linked outside file", m.group(2)), ("outside file", m.group(3)), ("other project's file", m.group(5))) if v == "True"]
        r.case("Word export " + m.group(1), LEAK if bad else PASS, ("embedded: " + ", ".join(bad)) if bad else f"{m.group(6)} picture(s), none foreign")
    for m in re.finditer(r"^### HELD (\w+/\w+(?: direct)?): (.*)$", text, re.M):
        held = refusal_in(m.group(2)) or (m.group(2) if REFUSAL_WORDS.search(m.group(2)) else None)
        if held:
            r.case("Word export " + m.group(1), PASS, "HELD (creaite refused): " + short(held, 110))
        else:
            r.err("Word export " + m.group(1) + " failed for a reason that is not a refusal: " + short(m.group(2), 90))
    for m in re.finditer(r"^### reachable: (\[.*\])\s*$", text, re.M):
        row = literal(m.group(1))
        if not isinstance(row, list) or len(row) < 4:
            continue
        ref, resolves, _, used = row[0], row[1], row[2], row[3]
        legit = "own.png" in ref.lower()
        if used and not legit:
            r.case("image_file reaches " + ref, LEAK, "paths.image_file returns a file for a reference that is not the project's own picture")
        elif resolves is True and not legit:
            r.case("resolve_image reaches " + ref, PASS, "resolves to a file but image_file refuses it")
    for m in re.finditer(r"^### error: (.*)$", text, re.M):
        r.notes.append("error row " + short(m.group(1), 50))
    for kind, name, body in unittest_blocks(text):
        if kind != "FAIL":
            continue
        held = refusal_in(body)
        if held:
            r.case("assertion " + name, PASS, "refused: " + held)     # creaite held the file back; nothing was produced to inspect
        elif re.search(r"leaks outside file|other project", body):
            r.case("assertion " + name, LEAK, "unittest assertion failed: outside or other-project file embedded")
        else:
            r.err("unexplained failure in " + name + ": " + short((exception_lines(body) or [("", "")])[0][1], 90))
    if not any("Word export" in c[0] for c in r.cases) and not any(c[2].startswith("refused") for c in r.cases):
        r.err("no Word export result")
    return r


def holds_scan(text, r, label_re):
    """Lines '... holds: [..]' -> non-empty list = a needle in a client output."""
    n = 0
    for m in re.finditer(label_re, text, re.M):
        n += 1
        lst = literal(m.group("lst")) or []
        name = m.group("name").strip()
        r.case(name, LEAK if lst else PASS, f"needles in the file: {lst}" if lst else "no needle")
    return n


def c_aud(text, args):
    r = R(text, args)
    harness(text, r)
    holds_scan(text, r, r"^### (?P<name>filed|\s*(?:html|docx|pdf) file) holds: (?P<lst>\[.*\])\s*$")
    if "### approve:" not in text:
        r.err("no approve line: the route run did not get that far")
    exp = len(re.findall(r"^### export (?:html|docx|pdf):", text, re.M))
    if exp < 3:
        r.err(f"only {exp} of 3 exports ran")
    refused = len(re.findall(r"^### (?:approve|export \w+): False", text, re.M))
    if not any(c[1] == LEAK for c in r.cases):
        r.notes.append(f"{refused} route call(s) refused" if refused else "all routes ran on a clean document")
        # a refused route is a clean case too
        for m in re.finditer(r"^### (approve|export \w+): False (.*)$", text, re.M):
            r.case(m.group(1), PASS, "refused: " + short(m.group(2), 90))
    return r


def c_sweep(text, args):
    r = R(text, args)
    harness(text, r)
    blocks = re.split(r"^======== (.+)$", text, flags=re.M)
    want = [v for v in (args.split()[-1].split(",") if args else [])]
    seen = []
    for i in range(1, len(blocks), 2):
        var, body = blocks[i].strip(), blocks[i + 1]
        seen.append(var)
        leaked = []
        for m in re.finditer(r"^### (?:FILED|\s*(?:html|docx|pdf)) holds: (\[.*?\])", body, re.M):
            if literal(m.group(1)):
                leaked.append(m.group(1))
        refs = len(re.findall(r"^### (?:save|approve|export \w+): False", body, re.M))
        if leaked:
            r.case(var, LEAK, "needles in a client output: " + "; ".join(leaked)[:120])
        elif "### approve:" not in body and "### save: False" not in body:
            r.case(var, ERROR, "variant did not reach approve")
            r.err(f"variant {var} did not finish")
        else:
            r.case(var, PASS, f"{refs} refusal(s), nothing planted in any output")
    for w in want:
        if w and w not in seen:
            r.err("variant never ran: " + w)
    if not seen:
        r.err("no variant blocks in the log")
    return r


def parse_ms1(text):
    out = []
    for m in re.finditer(r"^@@ (\S+) :: (\{.*\})\s*$", text, re.M):
        try:
            out.append((m.group(1), json.loads(m.group(2))))
        except ValueError:
            out.append((m.group(1), None))
    return out


def ms1_case(name, d, r):
    if d is None:
        r.case(name, ERROR, "unreadable result"); r.err("unreadable result for " + name); return
    if "EXC" in d:
        r.case(name, ERROR, "probe exception: " + short(d["EXC"], 90)); r.err(f"{name}: {short(d['EXC'], 80)}"); return
    where, labels, refused, clean = {}, [], 0, 0

    def hit(k, lst):
        where.setdefault(k, set()).update(lst)

    for k, v in d.items():
        if k == "needles":
            continue
        if k == "stray":
            for item in v or []:
                hit("filed/stray " + str(item[0])[-14:].strip(), item[1] if len(item) > 1 else [])
        elif isinstance(v, str):
            if v.startswith("LEAK"):
                hit(k, literal(v[4:].strip()) or ["?"])
            elif v.startswith("REF") or "HTTP-EXC" in v:
                refused += 1
            else:
                clean += 1
        elif isinstance(v, list):
            hh = v[2] if len(v) > 2 else None
            lab = v[3] if len(v) > 3 else None
            if hh:
                hit(k, hh)
            if lab and re.search(r"client", str(lab), re.I):
                labels.append(f"{k} labelled '{lab}'")
            if v and v[0] is False:
                refused += 1
            else:
                clean += 1
        elif k in ("exp_leak", "approve_leak") and v:
            hit(k, [str(v)])
        elif k == "appr" and v:
            hit("approve", v)
    if where or labels:
        direct = {k: sorted(x) for k, x in where.items() if not k.startswith("filed/stray")}
        outs = ", ".join(sorted(direct)) or "a stray client file"
        needles = sorted({n for x in where.values() for n in x})
        r.case(name, LEAK, (f"{outs} carry {needles}" if needles else "") + ("; " + "; ".join(labels) if labels else ""))
    else:
        r.case(name, PASS, f"refused {refused}, clean {clean}")


def c_ms1(text, args):
    r = R(text, args)
    harness(text, r)
    got = parse_ms1(text)
    for name, d in got:
        ms1_case(name, d, r)
    want = args.split()[-1].split(",") if args else []
    seen = [g[0] for g in got]
    miss = [w for w in want if w not in seen]
    if miss:
        r.err(f"{len(miss)} mutation(s) never reported: " + ",".join(miss[:4]))
    if not got:
        r.err("no '@@' result lines")
    return r


def c_race(text, args):
    r = R(text, args)
    harness(text, r)
    for name, d in parse_ms1(text):
        if d is None or "EXC" in d:
            r.case(name, ERROR, "probe exception"); r.err("exception in " + name); continue
        if "exp_ok" in d:
            leak = d.get("exp_leak", 0) or 0
            r.case(name, LEAK if leak else PASS, f"export: {d['exp_ok']} made, {leak} carried the payload, {d['exp_ref']} refused" +
                   (f" | approve filed {d['appr']}" if d.get("appr") else ""))
            if d["exp_ok"] + d["exp_ref"] == 0:
                r.err("no export call completed")
        elif "approve_calls" in d:
            leak = d.get("approve_leak", 0) or 0
            r.case(name, LEAK if leak else PASS, f"approve: {d['approve_calls']} calls, {d['approve_ok']} filed, {leak} carried the payload, {d['approve_ref']} refused")
        else:
            r.case(name, ERROR, "unknown result shape")
            r.err("unknown result shape")
    if not r.cases:
        r.err("no '@@' result line")
    return r


def c_ms2(text, args, skip_page=False):
    r = R(text, args)
    harness(text, r)
    for ln in text.splitlines():
        m = re.match(r"^\s*\[(?P<lab>.+?)\]\s+(?P<rest>.*)$", ln)
        if not m:
            continue
        lab, rest = m.group("lab"), m.group("rest")
        if lab.startswith("page ") and skip_page:
            continue
        if lab.startswith(("page ", "export ")) and "needles=" in rest:
            nd = re.search(r"needles=(\[.*?\]|None)", rest)
            v = literal(nd.group(1)) if nd else None
            nm = re.search(r"name='([^']*)'", rest)
            if lab.startswith("export ") and nm and "Client report" not in nm.group(1) and "kind=weekly" in lab:
                r.case(lab, PASS, "a weekly (internal) file: internal content is expected")
                continue
            ok = "OK" in rest[:3]
            note = "plain file" if "plain=True" in rest else ("refused" if not ok else "")
            if v:
                r.case(lab, LEAK, f"needles in the client file: {v}")
            else:
                if re.search(r"\bCON\b|NUL", lab) and ok:
                    r.notes.append("rename to a reserved device name (CON) is accepted: not a leak, the rename tests expect a refusal")
                r.case(lab, PASS, note)
        elif lab.startswith("match-check dirty"):
            ok = re.search(r"ok=(True|False)", rest)
            n = re.search(r"n=(\[.*?\])", rest)
            counts = literal(n.group(1)) if n else None
            missed = bool(ok and ok.group(1) == "True" and counts and all(c == 0 for c in counts))
            r.case(lab, LEAK if missed else PASS, "the gate found nothing in a deliberately dirty document" if missed else (f"findings {counts}" if counts else "refused: " + short(rest, 60)))
        elif lab.startswith("images ABC asking DEF"):
            g = re.search(r"got=(\[.*\])", rest)
            v = literal(g.group(1)) if g else None
            r.case(lab, LEAK if v else PASS, f"another project's picture returned: {v}" if v else "nothing returned")
        elif lab.startswith("logo/save kind=") and "ok=True" in rest and (".." in lab.split("kind=", 1)[1] or "/" in lab.split("kind=", 1)[1]):
            r.case(lab, LEAK, "a logo kind with a path in it was accepted")
        elif lab.startswith("approve:"):
            tail = rest.split("|")[-1]
            dd = re.search(r"dirty drafts=(\[.*?\])", rest)
            lst = literal(dd.group(1)) if dd else []
            if "LEAK" in tail:
                r.case(lab, LEAK, tail.strip()[:120])
            else:
                if lst:
                    r.notes.append(f"'{lab}' left a draft with needles in staging ({len(lst)} file(s))")
                r.case(lab, PASS, "no client output holds a needle")
        else:
            mm = re.match(r"^(?P<rest>(?:approve|html|docx|pdf)\S*.*)$", rest)
            if mm and ("| clean" in rest or "| LEAK" in rest):
                r.case(lab, LEAK if "| LEAK" in rest else PASS, short(rest.split("|")[-1], 120) if "| LEAK" in rest else short(rest, 100))
            elif "| LEAK" in rest:
                r.case(lab, LEAK, short(rest.split("| LEAK")[-1], 140))
    for ln in text.splitlines():           # '[label] approve=OK html=REF ... | clean'
        m = re.match(r"^\[(?P<lab>[^\]]+)\] (?P<rest>(?:approve|html|docx|pdf).*)$", ln)
        if m and not any(c[0] == short(m.group("lab"), 90) for c in r.cases):
            r.case(m.group("lab"), PASS if "| clean" in m.group("rest") else LEAK, short(m.group("rest"), 140))
    if "==== DONE" not in text:
        r.err("the probe did not reach '==== DONE'")
    if not r.cases:
        r.err("no result lines")
    return r


def c_ms2hot(text, args):
    r = c_ms2(text, args, skip_page=True)
    r.notes.append("the posted-page cases of this group are reported by ms2-page")
    return r


def c_reshow(text, args):
    r = R(text, args)
    harness(text, r)
    ck = os.environ.get("KIT_CK", "")
    try:
        has_route = "reshow" in open(os.path.join(ck, "system", "scripts", "report_server.py"), encoding="utf-8").read()
    except OSError:
        has_route = True
    if not has_route:
        r.err("N/A: this tree has no /api/report/reshow route (#234), so the late answer the probe holds back never happens; a clean result would prove nothing")
        return r
    a = re.search(r"DEF client pane holds MARK: (True|False) holds ref: (True|False)", text)
    b = re.search(r"DEF client draft where .*? holds MARK: (True|False) ref: (True|False)", text)
    if a:
        r.case("ABC wording / ref in DEF's client pane after a late reshow", LEAK if "True" in a.groups() else PASS, f"mark={a.group(1)} ref={a.group(2)}")
    if b:
        r.case("ABC wording / ref in DEF's saved client draft", LEAK if "True" in b.groups() else PASS, f"mark={b.group(1)} ref={b.group(2)}")
    if not (a or b):
        r.err("no DEF result line")
    return r


def c_rcgate(text, args):
    r = R(text, args)
    harness(text, r, need_ran=True)
    for m in re.finditer(r"^VAR (\S+)\s+(CAUGHT|PASSES)", text, re.M):
        if m.group(2) == "PASSES" and m.group(1) in DERIVED_NOT_GATED:
            r.case("gate variant " + m.group(1), PASS, "not gated: the field is derived or dropped before the gate since 2.5.1 (judged by ms1-header / ms1-fields)")
        elif m.group(2) == "PASSES" and m.group(1) not in KNOWN_GATE_MISSES:
            r.case("gate variant " + m.group(1), LEAK, "the match-check gate did not catch it (a regression against v2.5.0)")
        else:
            r.case("gate variant " + m.group(1), PASS, m.group(2).lower() if m.group(1) not in KNOWN_GATE_MISSES or m.group(2) == "CAUGHT" else "known miss on v2.5.0 (heuristic gate)")
    if sum(1 for m in re.finditer(r"^VAR \S+\s+PASSES", text, re.M) if m) :
        r.notes.append("known v2.5.0 gate misses: " + ", ".join(sorted(KNOWN_GATE_MISSES)))
    if not any(c[0].startswith("gate variant") for c in r.cases):
        r.err("no 'VAR' lines (test_a did not run)")
    m = re.search(r"^SLASH rows on client sheet: (\[.*\])", text, re.M)
    if m:
        rows = literal(m.group(1)) or []
        bad = [x for x in rows if re.search(r"item|work|note|person|mention|hash|wiki|action|raid", str(x), re.I)]
        r.case("slash menu rows on the client sheet", LEAK if bad or not rows else PASS, f"item-like rows: {bad}" if bad else ("no rows" if not rows else f"{len(rows)} rows, none an item row"))
    else:
        r.err("no slash-menu line (test_b did not get that far)")
    for m in re.finditer(r"^SLASH query (\w+) (\[.*\])", text, re.M):
        v = literal(m.group(2)) or []
        if v:
            r.case("slash query " + m.group(1), LEAK, f"the menu found {v}")
    m = re.search(r"^CHIPS in client pane: (\d+)", text, re.M)
    if m and int(m.group(1)):
        r.case("pasted internal item link becomes a chip", LEAK, f"{m.group(1)} chip(s)")
    for key in ("APPROVE", "EXPORT html"):
        m = re.search(rf"^{key} ok: (True|False)", text, re.M)
        if m:
            r.case(f"{key.lower()} after pasting an internal item link", LEAK if m.group(1) == "True" else PASS, "filed/exported" if m.group(1) == "True" else "refused")
    return r


def c_rce2e(text, args):
    r = R(text, args)
    harness(text, r, need_ran=True)
    hidden = {"ABC-A-001", "ABC-A-004", "ABC-005", "ABC-D-008", "Escalate data access", "Confirm tester names", "Vendor exits the market",
              "Absorb the phase one overrun", "Omar", "onfidential", "walrus", "Internal only", "Budget overrun", "Pelicanhidden",
              "Test licences not ordered", "UAT start slipped two weeks"}
    # 'UAT start slipped two weeks' is the health sentence the test itself copies into the client report; 'ABC-006' is the row the
    # client editor hid and stays as a reference in the filed data block: both are the baseline on v2.5.0 (rc-a3 and rc-a5 logs).
    baseline = {"UAT start slipped two weeks", "ABC-006"}
    for m in re.finditer(r"^SCAN (\w+) (\S.*?): (\[.*\])\s*$", text, re.M):
        label, rel, lst = m.group(1), m.group(2), literal(m.group(3)) or []
        if not rel.startswith("projects/"):      # drafts, templates, skills and applied proposals are not client output
            continue
        bad = [x for x in lst if x not in baseline]
        r.case(f"{label} {rel.split('/')[-1][-50:]}", LEAK if bad else PASS, f"needles {bad}" if bad else ("baseline only: " + str(lst) if lst else "clean"))
    for m in re.finditer(r"^EXPORT (html|docx|pdf) (True|False)", text, re.M):
        pass
    if "int approve" not in text:
        r.err("the test did not reach the internal approve")
    if "### client pane not editable here" in text:
        r.notes.append("the client pane is read-only after Approve: the hostile text went in through the save route")
    return r


def c_rcrace(text, args):
    r = R(text, args)
    harness(text, r)
    mc = re.search(r"match-check calls (\d+)", text)
    if not mc or int(mc.group(1)) < 1:
        r.err("the held match-check call never happened (vacuous run)")
    m = re.search(r"DEF client pane holds Zebracrossing: (True|False)", text)
    if m:
        r.case("ABC wording in DEF's client pane after a late match", LEAK if m.group(1) == "True" else PASS, "")
    for m in re.finditer(r"^DEF client draft where .*?holds Zebracrossing: (True|False)", text, re.M):
        r.case("ABC wording in DEF's client draft", LEAK if m.group(1) == "True" else PASS, "")
    for m in re.finditer(r"^DEF EXPORT (\w+) (True|False)", text, re.M):
        pass
    for m in re.finditer(r"file holds Zebracrossing: (True|False)", text):
        r.case("ABC wording in a DEF client export", LEAK if m.group(1) == "True" else PASS, "")
    if not r.cases:
        r.err("no DEF result line")
    return r


def c_hostile(text, args):
    r = R(text, args)
    harness(text, r)
    for m in re.finditer(r"client draft holds hostile after Match all: (\w+) (\w+) (\w+)", text):
        t = [x == "True" for x in m.groups()]
        r.case("hostile internal text copied to the client draft by Match all", LEAK if any(t) else PASS, f"Xylohostile/ID/owner = {m.groups()}")
    for m in re.finditer(r"H2 client draft holds: (\{.*\})", text):
        d = literal(m.group(1)) or {}
        bad = [k for k, v in d.items() if v]
        r.case("hostile text in the client draft after Match all (H2)", LEAK if bad else PASS, f"{bad}" if bad else "none")
    for m in re.finditer(r"(?:H2 )?files with Xylohostile: (\[.*\])|^files with hostile: (\[.*\])", text, re.M):
        lst = [x for x in (literal(m.group(1) or m.group(2)) or []) if "lient" in x]
        r.case("hostile word in a Client file", LEAK if lst else PASS, str(lst) if lst else "none")
    for m in re.finditer(r"(?:H2 )?(?:client approve ok|H2 client approve ok): (True|False)", text):
        pass
    for m in re.finditer(r"^H4 Zorblexsecret on client pane: (True|False) in client draft/staging: (True|False)", text, re.M):
        r.case("hidden words on the client pane or draft after Match (H4)", LEAK if "True" in m.groups() else PASS, f"pane={m.group(1)} draft={m.group(2)}")
    for m in re.finditer(r"^R (audience-internal|svg/backslash): (\{.*\})\s*$", text, re.M):
        d = literal(m.group(2)) or {}
        f = d.get("findings") or [[]]
        r.case("match-check of a dirty doc: " + m.group(1), PASS if f and f[0] else LEAK, f"{len(f[0]) if f else 0} finding(s)" if f and f[0] else "the gate found nothing in a deliberately dirty document")
    for kind, name, body in unittest_blocks(text):
        if kind != "FAIL":
            continue
        held = refusal_in(body)
        r.case("assertion " + name, PASS if held else LEAK, ("refused: " + held) if held else "unittest assertion failed")
    if not r.cases:
        r.err("no result line")
    return r


def c_minutes(text, args):
    r = R(text, args)
    harness(text, r)
    for m in re.finditer(r"^### (.*): exports made=(\d+) refused=(\d+) \| (.*)$", text, re.M):
        made, leak = int(m.group(2)), m.group(4).startswith("LEAK")
        r.case(m.group(1), LEAK if (made or leak) else PASS, ("exported as minutes" + (": " + m.group(4)[:100] if leak else " (clean text, but the route accepted a client report)")) if (made or leak) else "refused")
    m = re.search(r"^### new files holding needles: (\[.*\])", text, re.M)
    if m:
        r.case("files the exports made", LEAK if literal(m.group(1)) else PASS, m.group(1)[:100] if literal(m.group(1)) else "none holds a needle")
    if len([c for c in r.cases if "exports" in c[0] or "minutes" in c[0] or "Reports" in c[0] or "inbox" in c[0]]) < 3:
        r.err("fewer than the 4 expected attempts ran")
    return r


def c_cases(text, args):
    """'### CASE <name> | LEAK|PASS|HELD|CTRL-FAIL|SKIP | evidence' lines (src/k259/probe.py, src/k26/*.py). HELD = creaite refused (a
    clean PASS); CTRL-FAIL = a control that should be allowed was blocked: a functional fault, counted PASS and named in the evidence;
    SKIP = this tree has not got the feature the case is about (a probe whose every case is SKIP is SKIP, not PASS and not ERROR)."""
    r = R(text, args)
    harness(text, r)
    nctrl = 0
    for m in re.finditer(r"^### CASE (.+?) \| (LEAK|PASS|HELD|CTRL-FAIL|SKIP) \| (.*)$", text, re.M):
        name, st, ev = m.group(1), m.group(2), m.group(3).strip()
        if st == "LEAK":
            r.case(name, LEAK, ev)
        elif st == "HELD":
            r.case(name, PASS, "refused: " + ev)
        elif st == "SKIP":
            r.case(name, SKIP, ev)
        elif st == "CTRL-FAIL":
            nctrl += 1
            r.case(name, PASS, "FUNCTIONAL (not a leak): " + ev)
        else:
            r.case(name, PASS, ev)
    if nctrl:
        r.notes.append(f"{nctrl} control(s) blocked (over-blocking, not a leak)")
    if not r.cases:
        r.err("no '### CASE' lines")
    return r


CLASSIFIERS = {
    "leakfix": c_leakfix, "otherpaths": c_otherpaths, "keptcss": c_keptcss, "acceptedcss": c_acceptedcss, "keptjpeg": c_keptjpeg,
    "beacon": c_beacon, "svglogo": c_svglogo, "wordwhere": c_wordwhere, "csp": c_csp, "logopath": c_logopath, "sprobe": c_sprobe,
    "cap": c_cap, "svgfuzz": c_svgfuzz, "mdpath": c_mdpath, "routemd_pic": c_routemd_pic, "routemd_logo": c_routemd_logo, "rvmdaud": c_rvmdaud, "rvmdfuzz": c_rvmdfuzz,
    "aud": c_aud, "sweep": c_sweep, "ms1": c_ms1, "race": c_race, "ms2": c_ms2, "ms2hot": c_ms2hot, "reshow": c_reshow, "rcgate": c_rcgate,
    "cases": c_cases, "rce2e": c_rce2e, "rcrace": c_rcrace, "hostile": c_hostile, "minutes": c_minutes,
}


def main():
    id_, cls, variant, log, summary, detail, rc, args = sys.argv[1:9]
    try:
        text = open(log, encoding="utf-8", errors="replace").read()
    except OSError as e:
        text = ""
        res = R("", args); res.err("no log: " + str(e))
    else:
        res = None
    m = re.search(r"### kit: exit (\d+)", text)
    exit_code = int(rc) if rc.lstrip("-").isdigit() else (int(m.group(1)) if m else None)
    if res is None:
        try:
            res = CLASSIFIERS[cls](text, args)
        except Exception as e:      # a classifier bug must never read as PASS
            res = R(text, args); res.err("classifier failed: " + repr(e)[:100])
        if exit_code is None:
            res.err("the log has no exit line (the probe was cut off)")
    st = res.status()
    with open(summary, "a") as f:
        f.write(f"{id_}\t{variant}\t{st}\t{res.evidence()}\n")
    with open(detail, "a") as f:
        for name, cst, ev in res.cases:
            f.write(f"{id_}\t{name}\t{cst}\t{ev}\n")


if __name__ == "__main__":
    main()

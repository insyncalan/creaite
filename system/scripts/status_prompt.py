"""creaite status prompts (BL-106): the "Make it executive" rewrite prompt and the helpers around a draft's reply.

  rewrite_prompt(code, text, audience, length, start, end) -> str     the prompt for rewriting Alan's text in the executive voice
  split_reply(reply) -> (draft, sources)                              a Generate reply split at its SOURCES: line

  python3 system/scripts/status_prompt.py rewrite-prompt <CODE> [--from D] [--to D] [--audience …] [--length …]
      reads {"text"} as JSON on standard input and prints the rewrite prompt (the live server's /api/current/rewrite)

The Generate prompt itself is current-state-prompt.md, filled by the live server from report.current_context (which opens
with the writing guide, audience, length and facts). Nothing here calls a model or writes a file.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import report  # noqa: E402
import status_facts  # noqa: E402

AUDIENCE_RULES = {
    "internal": "Audience: internal. Be candid; say what is wrong and who owns it.",
    "client": "Audience: client-safe. The same shape, plainer, with no internal remarks: nothing about internal disagreement, our cost, "
              "staffing or people's performance. Use only what Alan's text and the facts (which hold only client-visible items) say.",
}


def rewrite_prompt(code, text, audience="internal", length="standard", start=None, end=None):
    """The prompt for "Make it executive": Alan's text, the guide, and the facts to check it against."""
    if audience not in AUDIENCE_RULES:
        raise ValueError("audience must be internal or client")
    words = status_facts.settings()["length_words"]
    if length not in words:
        raise ValueError(f"length must be one of {', '.join(words)}")
    facts = status_facts.facts(code, start, end, audience)
    template = (paths.TEMPLATES / "current-state-rewrite-prompt.md").read_text(encoding="utf-8")
    return template.format(code=code, name=facts["name"], audience_rule=AUDIENCE_RULES[audience], length=length.capitalize(),
                           words=words[length], style=report.style_guide(), facts=facts["text"], text=text.strip())


def split_reply(reply):
    """(the draft, the SOURCES text) from a reply; the page's own split, so tests and the server agree with it."""
    draft, _, sources = re.split(r"^(SOURCES:)\s*$", reply or "", maxsplit=1, flags=re.M) if re.search(r"^SOURCES:\s*$", reply or "", re.M) \
        else (reply or "", "", "")
    return draft.strip(), sources.strip()


def main(argv):
    """The rewrite-prompt command: read {"text"} on standard input and print the executive rewrite prompt (BL-106)."""
    import contextlib
    import json
    if len(argv) < 2 or argv[0] != "rewrite-prompt":
        print(__doc__)
        return 2
    code, rest = argv[1], argv[2:]
    opts = dict(zip(rest[::2], rest[1::2]))
    try:
        text = json.loads(sys.stdin.read() or "{}").get("text") or ""
        with contextlib.redirect_stdout(sys.stderr):        # library notes ("image not found…") must not mix into the prompt
            prompt = rewrite_prompt(code, text, opts.get("--audience", "internal"), opts.get("--length", "standard"),
                                    opts.get("--from"), opts.get("--to"))
        print(prompt)
    except ValueError as e:
        print(e)
        return 2
    except SystemExit:
        print("That project isn't in your project record.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

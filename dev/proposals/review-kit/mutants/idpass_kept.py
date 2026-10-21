

# MUTANT (review kit, k26): invite_clean.scrub cuts a numbered ID label with its number, and a password word only when its value has a digit, so
# "Meeting ID 85212345678 - Passcode abcdefg" keeps abcdefg (the ID label sheltering the word; the class k26-b-idpass looks for).
def scrub(text, limit):  # noqa: F811
    t = normal(str(text if text is not None else "")[:LINE_MAX])
    t = URL.sub(lambda m: "" if _bad_url(skeleton(m.group())) else m.group(), t)
    t = re.sub(r"(?i)\b(?:(?:meeting|webinar|conference|event|call|session)\s*id|pin|code)\s*[:=#]?\s*\d[\d -]*", " ", t)
    t = re.sub(r"(?i)\b(?:pass\s*codes?|passwords?|pwd|pw)\b\s*[:=#]?\s*\S*\d\S*", " ", t)
    return re.sub(r"\s+", " ", t).strip()[:limit]

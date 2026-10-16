"""creaite AI models (#132): the providers, the four kinds of job, which model each uses, and what happens at a limit.

Settings › Essentials › AI models reads and changes all of this through the live server's /api/ai/… routes. This module is
plain code with no network and no keychain of its own: it holds the words the page shows, the rules a choice must keep, and
the routing policy (which model a job runs on, at a limit, with confidential material). Two seams stand in for what is not
built here, because both touch secrets and are Alan's and Jarvis's to review (the guarded scope, #132 part B):

  - the key store (`KeyStore`): where a provider's key lives. The real one is this Mac's keychain, read only by the live
    server. Until it is built, `NOT_BUILT` answers "not connected" and refuses to take a key, so no key is ever held;
  - the model lister (`Lister`): asks a provider which models a key can use. The real one is one HTTPS call per provider.
    Until it is built, `NOT_BUILT` refuses.

Tests (and only tests) set CREAITE_FAKE_PROVIDERS=1 in the live server's environment: a fake store in the server's memory and
a fake lister that accepts keys starting "fake-good", fails with a network error for "fake-net", and refuses anything else
(401). No real key, provider or network is involved.

Settings (settings-defaults.json `ai`, each in the catalogue with the reason for its default):
  ai.jobs.<job>        the model for each kind of job, as "<provider>:<model id>" (never a key)
  ai.accepted_weaker   "<job>=<model>" pairs Alan accepted with Use it anyway, so the page doesn't ask again
  ai.on_limit          ask | other | step_down
  ai.providers         {provider: {auth, models: [{id, label, grade, tools}], offered: [ids], connected}}: what a key can
                       use and which of those Alan offers. Written only by Connect, Manage and Disconnect.

Every save goes through settings_catalogue.save (a backup and a log line per key), as every setting does.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import settings_catalogue  # noqa: E402

# ── Providers ────────────────────────────────────────────────────────────────────────────────────────────────────────────
# id: (name, what it is, how it is paid for, the ways to sign in, available now)
PROVIDERS = {
    "claude": ("Claude", "Anthropic's models: the ones creaite is built around.",
               "Your Claude subscription, or an Anthropic API key billed to that account.", ("subscription", "key"), True),
    "openai": ("OpenAI", "GPT models through an API key.", "Billed to your OpenAI account.", ("key",), True),
    "local": ("Local model", "A model on this laptop through Ollama. Your text never leaves the machine.", "", (), False),
    "hosted_free": ("Hosted free models", "Free models from a hosting service, for light jobs on text that is not confidential.",
                    "", (), False),
    "deepseek": ("DeepSeek", "DeepSeek models through an API key.", "", (), False),
}
PROVIDER_ORDER = ("claude", "openai", "local", "hosted_free", "deepseek")

# Claude's models: the aliases Claude Code takes (`claude --model opus`), each with its grade (3 strongest) and whether it can
# use tools. A subscription can't be asked for its models, so these are fixed.
CLAUDE_MODELS = (
    {"id": "opus", "label": "Claude Opus 5.5", "grade": 3, "tools": True},
    {"id": "sonnet", "label": "Claude Sonnet 5.5", "grade": 2, "tools": True},
    {"id": "haiku", "label": "Claude Haiku 5.5", "grade": 1, "tools": True},
)

# ── The four kinds of job ────────────────────────────────────────────────────────────────────────────────────────────────
# id: name, what it is, what it needs (tags), whether it needs tools, the recommended model, the features in it, and what a
# weaker choice risks (the popup's words).
JOBS = {
    "guard": {"name": "Guard, permissions and data work",
              "line": "The files that protect your data and who may write what; the live server's runs.",
              "needs": ("uses tools", "costly if wrong"), "tools": True, "recommended": "claude:opus",
              "features": ("Guard and permission changes", "The writer and the data (apply, schema, migrations)",
                           "Backups and updates", "Run approvals and locking"),
              "warn": "These jobs change the files that protect your data. A weaker model is more likely to make a subtle "
                      "mistake there, and a mistake could weaken a safeguard."},
    "tools": {"name": "Work that uses tools",
              "line": "Reads your mail, calendar, files and the tracker, or runs creaite's commands.",
              "needs": ("uses tools",), "tools": True, "recommended": "claude:sonnet",
              "features": ("ask creaite", "The sweep and minutes extraction", "Prep research",
                           "The check on people you follow (also needs exact IDs)"),
              "warn": "These jobs read your mail and files and work through several steps. A weaker model may miss things "
                      "or copy IDs wrongly."},
    "write": {"name": "Writing and drafting",
              "line": "One prompt in, text out, from facts creaite supplies.",
              "needs": ("text only",), "tools": False, "recommended": "claude:sonnet",
              "features": ("Generate current state", "Status forms (steering note, email paragraph)",
                           "Report and minutes redrafts", "Prep shaping"),
              "warn": "A weaker model writes less well and is more likely to skip or change facts. You review every draft, "
                      "but you may be doing more editing."},
    "quick": {"name": "Quick edits and short drafts",
              "line": "Short rewrites that must keep dates, numbers, names and IDs exact.",
              "needs": ("text only", "exact facts"), "tools": False, "recommended": "claude:haiku",
              "features": ("Selected-text edits and Format notes", "Teams message", "Chase and email drafts", "Polish"),
              "warn": "A weaker model for short edits is more likely to change a fact. creaite checks the result, and tells "
                      "you if it had to retry."},
}
JOB_ORDER = ("guard", "tools", "write", "quick")
STEP_DOWN = {"write": "quick"}          # Step down one kind: writing runs as a quick edit; jobs that need tools wait
KIND_UP = {"quick": "write"}            # a quick edit whose check fails retries once on the next kind up

HOW_IT_DECIDES = (
    "Does it need to use tools (read your mail, files or the tracker, or run commands)? Then it needs a model that can.",
    "Would a mistake be costly (the files that protect your data, who may write what)? Then it is the highest-stakes kind.",
    "Otherwise, is it one prompt in and text out, and must it keep dates, numbers, names and IDs exact? Short ones are quick "
    "edits; longer ones are writing.",
)
FIXED_RULES = (
    "Confidential notes, meetings and client-restricted material are only ever sent to Claude.",
    "A quick edit on a lighter model is checked for dates, numbers, names and item IDs; if the check fails it is tried once "
    "on the next kind up, and the draft says which model made it.",
)
LIMITS = {
    "ask": ("Ask me", "Show a card: wait until the limit resets, or run this one on another connected model."),
    "other": ("Use another connected model for this kind of job",
              "Switch this kind of job to another connected model while Claude is limited (never a job that needs tools, "
              "and never confidential material)."),
    "step_down": ("Step down one kind",
                  "Writing and drafting runs as a quick edit until the limit resets; jobs that need tools wait."),
}
LIMIT_ORDER = ("ask", "other", "step_down")
NEEDS_SECOND = "Needs a second connected provider."
KEY_WARNING = ("Text you send to this provider leaves your laptop. The key is kept in this Mac's keychain, never in the vault, "
               "settings, backups or the repo, and is never shown again. Confidential material is not sent to a provider "
               "other than Claude.")
MAX_KEY = 400                           # characters; a pasted key longer than this is a mistake


class Refused(ValueError):
    """A choice the rules don't allow; its message is the page's words."""


class NotBuilt(RuntimeError):
    """The keychain or the provider call isn't built yet (#132 part B, guarded)."""


NOT_BUILT_WORDS = ("Connecting another provider isn't switched on yet: it waits on the keychain step, which is being "
                   "reviewed. Claude keeps working as it does now.")


# ── The seams: the key store and the model lister ────────────────────────────────────────────────────────────────────────
class KeyStore:
    """Where provider keys live. `has` says whether there is one; `put` keeps one; `remove` deletes it. Never returns a key
    to anything but the provider call itself (`peek`, for the lister and the direct call only)."""

    def has(self, provider):
        """True when there is a key for the provider."""
        raise NotImplementedError

    def put(self, provider, key):
        """Keep the provider's key."""
        raise NotImplementedError

    def remove(self, provider):
        """Delete the provider's key; True when there was one."""
        raise NotImplementedError


class NotBuiltStore(KeyStore):
    """Until the keychain is built: nothing is connected and no key is taken."""

    def has(self, provider):
        """True when there is a key for the provider."""
        return False

    def put(self, provider, key):
        """Keep the provider's key."""
        raise NotBuilt(NOT_BUILT_WORDS)

    def remove(self, provider):
        """Delete the provider's key; True when there was one."""
        return False


class MemoryStore(KeyStore):
    """Tests only (CREAITE_FAKE_PROVIDERS=1): keys in this process's memory, gone when it stops."""

    def __init__(self):
        self._keys = {}

    def has(self, provider):
        """True when there is a key for the provider."""
        return provider in self._keys

    def put(self, provider, key):
        """Keep the provider's key."""
        self._keys[provider] = key

    def remove(self, provider):
        """Delete the provider's key; True when there was one."""
        return self._keys.pop(provider, None) is not None


class Lister:
    """Asks a provider which models a key can use: [model ids], or raises KeyRefused (the provider said no, with its HTTP
    status) or ConnectionError (it couldn't be reached)."""

    def models(self, provider, key):
        """The model ids the key can use."""
        raise NotImplementedError


class KeyRefused(Exception):
    """The provider did not accept the key; `status` is its HTTP status."""

    def __init__(self, status):
        super().__init__(f"refused ({status})")
        self.status = status


class NotBuiltLister(Lister):
    def models(self, provider, key):
        """The model ids the key can use."""
        raise NotBuilt(NOT_BUILT_WORDS)


class FakeLister(Lister):
    """Tests only: "fake-good…" lists models, "fake-net…" can't be reached, anything else is refused (401)."""

    FOUND = {"openai": ["fake-flagship", "fake-small", "fake-embedding"],
             "claude": ["claude-opus", "claude-sonnet", "claude-haiku"]}

    def models(self, provider, key):
        """The model ids the key can use."""
        if key.startswith("fake-net"):
            raise ConnectionError("unreachable")
        if not key.startswith("fake-good"):
            raise KeyRefused(401)
        return list(self.FOUND.get(provider, []))


def fake_mode():
    """True when the live server was started by a test with the fake provider (never in a real vault)."""
    return os.environ.get("CREAITE_FAKE_PROVIDERS") == "1"


_BACKEND = {}


def backend():
    """(the key store, the lister): the fakes under a test, else the not-built stand-ins. The guarded build replaces the
    not-built pair with the keychain store and the HTTPS lister here, and nowhere else."""
    if not _BACKEND:
        _BACKEND["pair"] = (MemoryStore(), FakeLister()) if fake_mode() else (NotBuiltStore(), NotBuiltLister())
    return _BACKEND["pair"]


def built():
    """Whether connecting a provider can work at all (the fake under a test, or the real keychain once it is built)."""
    return not isinstance(backend()[0], NotBuiltStore)


# ── Reading the settings ─────────────────────────────────────────────────────────────────────────────────────────────────
def setting(settings, key):
    """A dotted AI setting's value, or its default."""
    v = settings_catalogue.value_at(settings, key)
    if v is settings_catalogue._MISSING:
        v = settings_catalogue.value_at(settings_catalogue.defaults(), key)
    return v


def saved_providers(settings):
    """ai.providers, as a dict."""
    v = setting(settings, "ai.providers")
    return v if isinstance(v, dict) else {}


def grade_of(provider, model_id):
    """A provider's model's grade from its name (3 strongest, 1 lightest): a plain rule, as a key's list carries none."""
    m = model_id.lower()
    if any(w in m for w in ("nano", "mini", "small", "lite", "haiku")):
        return 1
    if any(w in m for w in ("medium", "sonnet")):
        return 2
    return 3


def label_of(provider, model_id):
    """What the lists call a model: the provider's name and the id, tidied."""
    name = PROVIDERS.get(provider, (provider,))[0]
    return f"{name} {model_id.replace('-', ' ').replace('_', ' ')}".strip()


def usable(model_id):
    """A model that writes text (not one for embeddings, images, speech or moderation)."""
    m = model_id.lower()
    return not any(w in m for w in ("embed", "image", "dall", "tts", "whisper", "audio", "moderation", "transcribe"))


def connected(settings, store=None):
    """The providers Alan is connected to, in order: Claude always (his subscription), the others when the key store has a
    key and settings hold its models."""
    store = store or backend()[0]
    saved = saved_providers(settings)
    return [p for p in PROVIDER_ORDER if PROVIDERS[p][4] and
            (p == "claude" or (store.has(p) and isinstance(saved.get(p), dict)))]


def models_of(provider, settings, offered_only=True):
    """[{id: "<provider>:<model>", label, grade, tools, provider}] a provider offers (Claude's fixed list; another's found
    models, those Alan ticked when offered_only)."""
    if provider == "claude":
        return [dict(m, id="claude:" + m["id"], provider="claude") for m in CLAUDE_MODELS]
    p = saved_providers(settings).get(provider) or {}
    found = [m for m in p.get("models", []) if isinstance(m, dict) and m.get("id")]
    ticked = set(p.get("offered", [m["id"] for m in found]))
    return [{"id": f"{provider}:{m['id']}", "label": m.get("label") or label_of(provider, m["id"]),
             "grade": int(m.get("grade") or grade_of(provider, m["id"])), "tools": bool(m.get("tools")), "provider": provider}
            for m in found if not offered_only or m["id"] in ticked]


def all_models(settings, store=None):
    """Every model of every connected provider, offered ones only."""
    return [m for p in connected(settings, store) for m in models_of(p, settings)]


def model(model_id, settings, store=None):
    """The model with this id among the connected providers' offered ones, or None."""
    return next((m for m in all_models(settings, store) if m["id"] == model_id), None)


def options(job, settings, store=None):
    """The models a job's list shows: the connected providers' offered models, only tool-capable ones when the job needs
    tools; each marked recommended and weaker (a lower grade than the recommended model)."""
    j = JOBS[job]
    rec = model(j["recommended"], settings, store)
    rec_grade = rec["grade"] if rec else 0
    return [dict(m, recommended=m["id"] == j["recommended"], weaker=m["grade"] < rec_grade)
            for m in all_models(settings, store) if m["tools"] or not j["tools"]]


def chosen(job, settings, store=None):
    """The model a job uses: its setting when that model is still on offer for the job, else the recommended model."""
    v = setting(settings, f"ai.jobs.{job}")
    return v if any(m["id"] == v for m in options(job, settings, store)) else JOBS[job]["recommended"]


def accepted(settings):
    """The "<job>=<model>" pairs Alan accepted with Use it anyway."""
    v = setting(settings, "ai.accepted_weaker")
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []


def other_connected(settings, store=None):
    """True when a provider other than Claude is connected (the limit's "another connected model" needs one)."""
    return any(p != "claude" for p in connected(settings, store))


# ── What the page shows ──────────────────────────────────────────────────────────────────────────────────────────────────
def card(pid, settings, store, conn):
    """One provider card: its words, status (connected, not, soon), how it signs in, its models and those found."""
    name, blurb, billing, how, live = PROVIDERS[pid]
    p = saved_providers(settings).get(pid) or {}
    on = pid in conn
    auth = ("key" if store.has("claude") else "subscription") if pid == "claude" else ("key" if on else None)
    found = [m for m in p.get("models", []) if isinstance(m, dict) and m.get("id")] if on and pid != "claude" else []
    return {"id": pid, "name": name, "blurb": blurb, "billing": billing, "how": list(how),
            "status": "soon" if not live else "connected" if on else "not", "auth": auth,
            "models": [m["label"] for m in models_of(pid, settings)] if on else [],
            "found": [{"id": m["id"], "label": m.get("label") or label_of(pid, m["id"]),
                       "offered": m["id"] in p.get("offered", [])} for m in found]}


def job_view(jid, settings, store, others):
    """One kind of job as the page shows it: its words, its list with the recommended and weaker marks, its model."""
    j, took = JOBS[jid], accepted(settings)
    opts = options(jid, settings, store)
    rec = next((m for m in opts if m["recommended"]), None)
    return {"id": jid, "name": j["name"], "line": j["line"], "needs": list(j["needs"]), "tools": j["tools"],
            "features": list(j["features"]), "warn": j["warn"], "recommended": j["recommended"],
            "recommended_label": rec["label"] if rec else j["recommended"], "value": chosen(jid, settings, store),
            "options": [{"id": m["id"], "label": m["label"], "recommended": m["recommended"], "weaker": m["weaker"],
                         "accepted": f"{jid}={m['id']}" in took} for m in opts],
            "tools_only": j["tools"] and bool(others)}


def limit_view(settings, two):
    """The limit's choice (Ask me when "another connected model" has no second provider) and its three options."""
    lim = setting(settings, "ai.on_limit")
    return (lim if lim in LIMITS and (lim != "other" or two) else "ask",
            [{"id": k, "label": LIMITS[k][0], "line": LIMITS[k][1] if (k != "other" or two) else NEEDS_SECOND,
              "enabled": k != "other" or two} for k in LIMIT_ORDER])


def state(settings=None, store=None):
    """The whole AI models section, for /api/ai/state: providers as cards, the four jobs with their lists, the limit."""
    import paths
    settings = paths.load_settings() if settings is None else settings
    store = store or backend()[0]
    conn = connected(settings, store)
    others = [PROVIDERS[p][0] for p in conn if p != "claude"]
    line = (f"Claude and {' and '.join(others)} are connected. Anything else is on its way." if others else
            "Claude is connected. Add OpenAI to use it for drafting and quick edits. Anything else is on its way.")
    on_limit, limits = limit_view(settings, bool(others))
    return {"providers": [card(p, settings, store, conn) for p in PROVIDER_ORDER], "line": line,
            "jobs": [job_view(j, settings, store, others) for j in JOB_ORDER], "more_hint": not others,
            "how": list(HOW_IT_DECIDES), "rules": list(FIXED_RULES), "key_warning": KEY_WARNING, "built": built(),
            "on_limit": on_limit, "limits": limits}


# ── Changes (each returns {dotted key: value} for settings_catalogue.save) ──────────────────────────────────────────────
def choose(job, model_id, accept=False, settings=None, store=None):
    """The settings a choice of model for a job writes. Refused: an unknown job, a model not on offer for it (a job that
    needs tools takes only a model that can use them), or a weaker model Alan hasn't accepted (`accept`, Use it anyway)."""
    import paths
    settings = paths.load_settings() if settings is None else settings
    if job not in JOBS:
        raise Refused("That isn't a kind of job creaite knows.")
    opts = {m["id"]: m for m in options(job, settings, store)}
    if model_id not in opts:
        if JOBS[job]["tools"] and model(model_id, settings, store):
            raise Refused(f"{JOBS[job]['name']} needs a model that can use tools, and that one can't.")
        raise Refused("That model isn't offered: connect its provider or tick it under Manage.")
    changes = {f"ai.jobs.{job}": model_id}
    pair, took = f"{job}={model_id}", accepted(settings)
    if opts[model_id]["weaker"] and pair not in took:
        if not accept:
            raise Refused("weaker")
        changes["ai.accepted_weaker"] = took + [pair]
    return changes


def set_limit(mode, settings=None, store=None):
    """The settings the limit's choice writes. "other" needs a second connected provider."""
    import paths
    settings = paths.load_settings() if settings is None else settings
    if mode not in LIMITS:
        raise Refused("That isn't one of the choices.")
    if mode == "other" and not other_connected(settings, store):
        raise Refused(NEEDS_SECOND)
    return {"ai.on_limit": mode}


def found_models(provider, ids):
    """The models a key can use, as kept in settings: text models only, each with its label and grade; none can use tools
    in creaite's runs until one proves it (only Claude's command runs tools)."""
    out, seen = [], set()
    for mid in ids:
        if isinstance(mid, str) and mid and mid not in seen and usable(mid) and len(mid) <= 80:
            seen.add(mid)
            out.append({"id": mid, "label": label_of(provider, mid), "grade": grade_of(provider, mid), "tools": False})
    return out


def check_key(provider, key):
    """A pasted key's plain problem, or "" (empty, too long, spaces inside, or a provider that takes no key)."""
    if provider not in PROVIDERS or "key" not in PROVIDERS[provider][3] or not PROVIDERS[provider][4]:
        return "That provider can't be connected with a key."
    if not isinstance(key, str) or not key.strip():
        return "Paste the key first."
    k = key.strip()
    if len(k) > MAX_KEY or any(c.isspace() for c in k):
        return "That doesn't look like a key: check you copied just the key, with no spaces."
    return ""


def refused_words(provider, status):
    """What a refused key says (the status only: never the key)."""
    name = PROVIDERS[provider][0]
    if status in (401, 403):
        return f"{name} did not accept this key ({status}). Check you copied all of it, and that it has not been revoked."
    if status == 429:
        return f"{name} says this key is over its limit ({status}). Try again later, or check the account's billing."
    return f"{name} refused this key ({status})."


def connect_changes(provider, ids, offered, settings):
    """The settings Connect (Done) writes: the provider's models and which of them Alan offers."""
    found = found_models(provider, ids) if provider != "claude" else []
    keep = [m["id"] for m in found if m["id"] in set(offered or [])] if provider != "claude" else []
    saved = dict(saved_providers(settings))
    saved[provider] = {"auth": "key", "models": found, "offered": keep}
    return {"ai.providers": saved}


def offer_changes(provider, offered, settings, store=None):
    """The settings Manage writes: which found models to offer. A job set to one no longer offered goes back to its
    recommended model."""
    saved = dict(saved_providers(settings))
    p = saved.get(provider)
    if provider == "claude" or not isinstance(p, dict):
        raise Refused("That provider isn't connected.")
    ids = {m["id"] for m in p.get("models", []) if isinstance(m, dict)}
    saved[provider] = dict(p, offered=[m for m in offered if m in ids])
    after = dict(settings)
    after["ai"] = dict(settings.get("ai") or {}, providers=saved)
    return dict({"ai.providers": saved}, **fallbacks(after, settings, store))


def fallbacks(after, before, store=None):
    """After a provider's models change (Disconnect, Manage): each job whose model is no longer on offer goes back to its
    recommended model, the accepted pairs for models gone are dropped, and "another connected model" at a limit goes back
    to Ask me when no second provider is left."""
    changes = {}
    for jid in JOB_ORDER:
        v = setting(before, f"ai.jobs.{jid}")
        if not any(m["id"] == v for m in options(jid, after, store)) and v != JOBS[jid]["recommended"]:
            changes[f"ai.jobs.{jid}"] = JOBS[jid]["recommended"]
    live = {m["id"] for m in all_models(after, store)}
    took = accepted(before)
    kept = [x for x in took if x.split("=", 1)[-1] in live]
    if kept != took:
        changes["ai.accepted_weaker"] = kept
    if setting(before, "ai.on_limit") == "other" and not other_connected(after, store):
        changes["ai.on_limit"] = "ask"
    return changes


def disconnect_changes(provider, settings, store=None):
    """The settings Disconnect writes (the key is removed by the caller): the provider's models out of the lists, and every
    choice that used one back to its recommended model."""
    saved = dict(saved_providers(settings))
    saved.pop(provider, None)
    after = dict(settings)
    after["ai"] = dict(settings.get("ai") or {}, providers=saved)
    gone = MemoryStore()                 # the lists as they will be: this provider without a key
    st = store or backend()[0]
    for p in PROVIDER_ORDER:
        if p != provider and st.has(p):
            gone.put(p, "-")
    return dict({"ai.providers": saved}, **fallbacks(after, settings, gone))


# ── Routing: which model a job runs on (the policy; wiring it into runs is the guarded part) ────────────────────────────
def route(job, settings, store=None, confidential=False, limited=False):
    """Which model a job runs on now: {model, wait, ask, why}. The rules, in order:
    - confidential material only ever goes to Claude: a non-Claude choice runs on the job's recommended model instead;
    - a job that needs tools only runs on a model that can use them (the lists already keep to that);
    - at Claude's limit: Ask me asks (wait or another connected model); "another connected model" switches a text-only job
      to the strongest offered model of another provider, never a job that needs tools and never confidential material;
      Step down one kind runs writing as a quick edit, and jobs that need tools wait."""
    j = JOBS[job]
    pick = chosen(job, settings, store)
    if confidential and not pick.startswith("claude:"):
        pick = j["recommended"]
    if not limited or not pick.startswith("claude:"):
        return {"model": pick, "wait": False, "ask": False, "why": "confidential" if confidential and pick == j["recommended"] else ""}
    mode = setting(settings, "ai.on_limit")
    if mode == "other" and not j["tools"] and not confidential:
        alt = sorted((m for m in options(job, settings, store) if m["provider"] != "claude"), key=lambda m: -m["grade"])
        if alt:
            return {"model": alt[0]["id"], "wait": False, "ask": False, "why": "limit: another connected model"}
    if mode == "step_down" and job in STEP_DOWN:
        return {"model": chosen(STEP_DOWN[job], settings, store), "wait": False, "ask": False, "why": "limit: stepped down"}
    if mode == "ask":
        return {"model": None, "wait": False, "ask": True, "why": "limit: ask"}
    return {"model": None, "wait": True, "ask": False, "why": "limit: waits for the reset"}


def retry_kind(job, check_notes):
    """A quick edit whose plain-code check found a changed date, number, name or ID is tried once on the next kind up: that
    kind, or None (no retry: the check passed, or it isn't a quick edit)."""
    return KIND_UP.get(job) if check_notes else None


# ── A tested key waiting for Done (the connect journey) ─────────────────────────────────────────────────────────────────
# Test and connect asks the provider for its models; the key is kept here, in the live server's memory only, until Alan
# presses Done (it then goes to the key store) or Cancel (it is dropped), and for PENDING_SECONDS at most. Only a built key
# store (or the test fake) ever reaches this: the not-built lister refuses first.
PENDING_SECONDS = 600
_PENDING = {}


def hold(provider, key, ids, now=None):
    """Keep a tested key and its models until Done; returns the one-time id the page sends back."""
    import secrets
    import time
    now = time.time() if now is None else now
    for k in [k for k, v in _PENDING.items() if v["until"] < now]:
        _PENDING.pop(k, None)
    pid = secrets.token_urlsafe(16)
    _PENDING[pid] = {"provider": provider, "key": key, "ids": list(ids), "until": now + PENDING_SECONDS}
    return pid


def take(pid, now=None):
    """The held key's {provider, key, ids}, removed; None when there is none or it has run out."""
    import time
    now = time.time() if now is None else now
    p = _PENDING.pop(pid, None) if isinstance(pid, str) else None
    return p if p and p["until"] >= now else None


def forget(pid):
    """Drop a held key (Cancel)."""
    return _PENDING.pop(pid, None) is not None if isinstance(pid, str) else False

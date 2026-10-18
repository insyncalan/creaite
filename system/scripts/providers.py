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
import re
import sys
import urllib.error  # #132 G2: the model list (standard library)
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
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

    def peek(self, provider):
        """The provider's key, for the provider call itself only (the live server, just before it calls), or None."""
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

    def peek(self, provider):
        """No key is ever held."""
        return None


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

    def peek(self, provider):
        """The provider's key, or None."""
        return self._keys.get(provider)


# ── #132 G1 (proposal): the keychain store ──────────────────────────────────────────────────────────────────────────────
# A provider's key lives in this Mac's login keychain as one generic password: service "creaite.ai.<vault id>.<provider>"
# (the vault id is a hash of the vault's real path, so two vaults never share a key), account "creaite". It is written,
# read and deleted through Apple's Security framework, called in this process with ctypes (standard library: nothing is
# installed). No program is started, so the key is never on a command line (`ps`), in an environment variable, a file, a
# log line or a backup. Only the live server constructs this store (backend(), below); no creaite script has a command
# that reads a key, providers.py itself is never run by a model run (reach.py) and no permission rule may name it or the
# keychain (permissions.py). `has` never reads the secret. Errors carry the keychain's status and plain words, never a key.
KEY_CHARS = re.compile(r"[A-Za-z0-9._~+/=:-]{8,400}")      # what an API key is made of: no spaces, quotes or new lines
KEYCHAIN_ACCOUNT = "creaite"
NOT_FOUND, DUPLICATE = -25300, -25299                       # errSecItemNotFound, errSecDuplicateItem
KEYCHAIN_WORDS = {
    -25308: "The keychain is locked or couldn't ask you: unlock your Mac and try again.",          # errSecInteractionNotAllowed
    -128: "You said no to the keychain's question, so nothing was changed.",                        # errSecUserCanceled
    -25293: "The keychain didn't accept your Mac's password, so nothing was changed.",              # errSecAuthFailed
    -25291: "This Mac has no login keychain to keep the key in.",                                  # errSecNotAvailable
    -25294: "This Mac has no login keychain to keep the key in.",                                  # errSecNoSuchKeychain
}


class KeychainError(RuntimeError):
    """The keychain said no: plain words and its status, never the key."""

    def __init__(self, status):
        super().__init__(KEYCHAIN_WORDS.get(status, f"The keychain couldn't do that (status {status}). Nothing was changed."))
        self.status = status


def vault_id(root=None):
    """A short, stable id for this vault (its real path, hashed): part of each key's keychain service name."""
    import hashlib
    import paths
    real = os.path.realpath(str(root or paths.ROOT))
    return hashlib.sha256(real.encode("utf-8")).hexdigest()[:12]


class SecApi:
    """The four Security framework calls the store needs, through ctypes: add, exists (no secret read), read and delete. Each
    takes the service and account names and answers the OSStatus (0 is success). macOS only."""

    _lib = None

    @classmethod
    def lib(cls):
        """(Security, CoreFoundation, constants), loaded once."""
        if cls._lib is None:
            import ctypes
            sec = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/Security.framework/Security")
            cf = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
            vp = ctypes.c_void_p
            for fn, res, args in ((cf.CFStringCreateWithCString, vp, [vp, ctypes.c_char_p, ctypes.c_uint32]),
                                  (cf.CFDataCreate, vp, [vp, ctypes.c_char_p, ctypes.c_long]),
                                  (cf.CFDictionaryCreate, vp, [vp, ctypes.POINTER(vp), ctypes.POINTER(vp), ctypes.c_long, vp, vp]),
                                  (cf.CFDataGetLength, ctypes.c_long, [vp]), (cf.CFDataGetBytePtr, vp, [vp]),
                                  (cf.CFRelease, None, [vp]), (sec.SecItemAdd, ctypes.c_int32, [vp, vp]),
                                  (sec.SecItemCopyMatching, ctypes.c_int32, [vp, ctypes.POINTER(vp)]),
                                  (sec.SecItemDelete, ctypes.c_int32, [vp])):
                fn.restype, fn.argtypes = res, args
            k = {n: vp.in_dll(sec, n).value for n in ("kSecClass", "kSecClassGenericPassword", "kSecAttrService",
                                                       "kSecAttrAccount", "kSecAttrLabel", "kSecValueData", "kSecReturnData",
                                                       "kSecMatchLimit", "kSecMatchLimitOne")}
            k["true"] = vp.in_dll(cf, "kCFBooleanTrue").value
            k["keys"] = ctypes.addressof(ctypes.c_byte.in_dll(cf, "kCFTypeDictionaryKeyCallBacks"))
            k["values"] = ctypes.addressof(ctypes.c_byte.in_dll(cf, "kCFTypeDictionaryValueCallBacks"))
            cls._lib = (sec, cf, k)
        return cls._lib

    def _query(self, service, account, extra=()):
        """A CFDictionary for the item, and the CF objects to release after the call."""
        import ctypes
        sec, cf, k = self.lib()
        made = [cf.CFStringCreateWithCString(None, s.encode("utf-8"), 0x08000100) for s in (service, account)]
        pairs = [(k["kSecClass"], k["kSecClassGenericPassword"]), (k["kSecAttrService"], made[0]),
                 (k["kSecAttrAccount"], made[1])]
        for name, value in extra:                  # bytes: data; ("k", name): one of the constants; str: a string
            if isinstance(value, bytes):
                value = cf.CFDataCreate(None, value, len(value))
                made.append(value)
            elif isinstance(value, tuple):
                value = k[value[1]]
            else:
                value = cf.CFStringCreateWithCString(None, value.encode("utf-8"), 0x08000100)
                made.append(value)
            pairs.append((k[name], value))
        n = len(pairs)
        vp = ctypes.c_void_p
        d = cf.CFDictionaryCreate(None, (vp * n)(*[a for a, _ in pairs]), (vp * n)(*[b for _, b in pairs]), n,
                                  k["keys"], k["values"])
        return d, made + [d]

    def _release(self, made):
        cf = self.lib()[1]
        for x in made:
            if x:
                cf.CFRelease(x)

    def add(self, service, account, label, secret):
        """SecItemAdd of a generic password."""
        d, made = self._query(service, account, (("kSecAttrLabel", label), ("kSecValueData", secret)))
        try:
            return self.lib()[0].SecItemAdd(d, None)
        finally:
            self._release(made)

    def exists(self, service, account):
        """SecItemCopyMatching with no data asked for: whether the item is there, without reading its secret."""
        d, made = self._query(service, account, (("kSecMatchLimit", ("k", "kSecMatchLimitOne")),))
        try:
            return self.lib()[0].SecItemCopyMatching(d, None)
        finally:
            self._release(made)

    def read(self, service, account):
        """(status, the secret's bytes or None)."""
        import ctypes
        sec, cf, k = self.lib()
        d, made = self._query(service, account, (("kSecReturnData", ("k", "true")),
                                                 ("kSecMatchLimit", ("k", "kSecMatchLimitOne"))))
        out = ctypes.c_void_p()
        try:
            status = sec.SecItemCopyMatching(d, ctypes.byref(out))
            if status != 0 or not out.value:
                return status, None
            return status, ctypes.string_at(cf.CFDataGetBytePtr(out), cf.CFDataGetLength(out))
        finally:
            self._release(made + [out.value])

    def delete(self, service, account):
        """SecItemDelete."""
        d, made = self._query(service, account)
        try:
            return self.lib()[0].SecItemDelete(d)
        finally:
            self._release(made)


class KeychainStore(KeyStore):
    """Provider keys in this Mac's login keychain (the live server only)."""

    def __init__(self, api=None, vault=None):
        self.api = api or SecApi()
        self.vault = vault or vault_id()

    def service(self, provider):
        """The keychain service name for a provider's key; ValueError for a provider that takes no key."""
        if provider not in PROVIDERS or "key" not in PROVIDERS[provider][3] or not PROVIDERS[provider][4]:
            raise ValueError("That provider can't be connected with a key.")
        return f"creaite.ai.{self.vault}.{provider}"

    def has(self, provider):
        """True when the keychain holds the provider's key (its secret is not read). A keychain that can't answer (locked,
        refused) counts as no key: the provider shows as not connected and nothing is sent to it."""
        return self.api.exists(self.service(provider), KEYCHAIN_ACCOUNT) == 0

    def put(self, provider, key):
        """Keep the provider's key, replacing any earlier one."""
        key = key.strip() if isinstance(key, str) else ""
        if not KEY_CHARS.fullmatch(key):
            raise Refused("That doesn't look like a key: check you copied just the key, with no spaces.")
        svc = self.service(provider)
        status = self.api.delete(svc, KEYCHAIN_ACCOUNT)
        if status not in (0, NOT_FOUND):
            raise KeychainError(status)
        status = self.api.add(svc, KEYCHAIN_ACCOUNT, f"creaite AI key ({PROVIDERS[provider][0]})", key.encode("utf-8"))
        if status != 0:
            raise KeychainError(status)

    def peek(self, provider):
        """The provider's key, for the provider call itself, or None when there is none."""
        status, data = self.api.read(self.service(provider), KEYCHAIN_ACCOUNT)
        if status == NOT_FOUND:
            return None
        if status != 0 or data is None:
            raise KeychainError(status)
        return data.decode("utf-8")

    def remove(self, provider):
        """Delete the provider's key; True when there was one."""
        status = self.api.delete(self.service(provider), KEYCHAIN_ACCOUNT)
        if status in (0, NOT_FOUND):
            return status == 0
        raise KeychainError(status)
# ── end #132 G1 ─────────────────────────────────────────────────────────────────────────────────────────────────────────


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


# ── #132 G2 (proposal): the model list, one HTTPS call to the provider ─────────────────────────────────────────────────
# Test and connect asks the provider which models the key can use: one GET to a fixed host per provider (no other host is ever
# called, and a redirect is refused, never followed), the key in one request header only (never the address), TLS verified
# against the Mac's trusted certificates (TLS 1.2 or later), no proxy taken from the environment, a 10 second limit and at most
# 1 MB read back. Standard library only (urllib). Errors carry the host and an HTTP status, never the key or the body: 4xx is
# KeyRefused(status); a 3xx, a 5xx, a timeout, a TLS or network failure or an answer that isn't a model list is
# ProviderUnreachable. The debug log gets the host and the status only.
LIST_HOSTS = {"openai": "api.openai.com", "claude": "api.anthropic.com"}
LIST_PATHS = {"openai": "/v1/models", "claude": "/v1/models?limit=1000"}
ANTHROPIC_VERSION = "2023-06-01"
LIST_TIMEOUT = 10                        # seconds
LIST_CAP = 1_000_000                     # bytes read back at most
LIST_MAX = 500                           # model ids kept at most


class ProviderUnreachable(ConnectionError):
    """The provider couldn't be asked or gave no model list: the host and plain words only."""


def key_headers(provider, key):
    """The one header that carries the key (and Anthropic's version header)."""
    if provider == "claude":
        return {"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION}
    return {"Authorization": f"Bearer {key}"}


def _log(line):
    """One debug log line (the host and a status, never a key); the log never stops a call."""
    try:
        import log as debuglog
        debuglog.info("ai-models", debuglog.clean(line, 200))
    except Exception:  # noqa: BLE001  the log never stops a call
        return


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        """Never follow a redirect: urllib then raises the 3xx as an HTTPError, which the lister refuses."""
        return None


class HttpsLister(Lister):
    """The real model list. `base` and `context` are for tests only (a local fake server and its certificate); creaite itself
    always uses LIST_HOSTS over https with the system's trust store."""

    def __init__(self, base=None, context=None, timeout=LIST_TIMEOUT, cap=LIST_CAP):
        import ssl
        self.base = dict(base or {p: f"https://{h}" for p, h in LIST_HOSTS.items()})
        self.context = context or ssl.create_default_context()
        self.context.minimum_version = max(self.context.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.timeout, self.cap = timeout, cap

    def opener(self):
        """urllib with no proxies from the environment, no redirects followed and this TLS context."""
        return urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect(),
                                           urllib.request.HTTPSHandler(context=self.context))

    def models(self, provider, key):
        """The model ids the key can use."""
        if provider not in LIST_HOSTS or provider not in self.base:
            raise ValueError("That provider has no model list.")
        url = self.base[provider] + LIST_PATHS[provider]
        host = urllib.parse.urlsplit(url).hostname or "?"
        if not url.startswith("https://"):
            raise ProviderUnreachable(f"{host}: only https is used")
        if not isinstance(key, str) or not KEY_CHARS.fullmatch(key):
            raise KeyRefused(400)
        status, body = self.fetch(url, host, key_headers(provider, key))
        _log(f"{host} model list: {status}")
        if status is not None and 400 <= status < 500:
            raise KeyRefused(status)
        if status != 200:
            raise ProviderUnreachable(f"{host}: answered {status}")
        return self.ids(body, host)

    def fetch(self, url, host, headers):
        """(HTTP status, at most cap + 1 bytes of the answer) for one GET; ProviderUnreachable when there is no answer."""
        req = urllib.request.Request(url, method="GET", headers={**headers, "Accept": "application/json", "User-Agent": "creaite"})
        try:
            with self.opener().open(req, timeout=self.timeout) as r:
                return r.status, r.read(self.cap + 1)
        except urllib.error.HTTPError as e:
            e.close()
            return e.code, b""
        except Exception as e:  # noqa: BLE001  network, TLS, timeout, a broken answer: never the key, never the body
            _log(f"{host} model list: unreachable ({type(e).__name__})")
            raise ProviderUnreachable(f"{host}: couldn't be reached ({type(e).__name__})") from None

    def ids(self, body, host):
        """The model ids in a provider's answer ({"data": [{"id": …}, …]}), at most LIST_MAX."""
        import json
        if len(body) > self.cap:
            raise ProviderUnreachable(f"{host}: the answer was too large")
        try:
            data = json.loads(body.decode("utf-8")).get("data")
            ids = [m["id"] for m in data if isinstance(m, dict) and isinstance(m.get("id"), str) and 0 < len(m["id"]) <= 200]
        except Exception:  # noqa: BLE001  anything else is not a model list
            raise ProviderUnreachable(f"{host}: the answer wasn't a model list") from None
        return ids[:LIST_MAX]
# ── end #132 G2 ─────────────────────────────────────────────────────────────────────────────────────────────────────────


def fake_mode():
    """True when the live server was started by a test with the fake provider (never in a real vault)."""
    return os.environ.get("CREAITE_FAKE_PROVIDERS") == "1"


_BACKEND = {}


def backend():
    """(the key store, the lister): the fakes under a test; on a Mac the keychain store (#132 G1) and the HTTPS model list
    (#132 G2); else the not-built stand-ins. Only the live server calls this."""
    if not _BACKEND:
        if fake_mode():
            _BACKEND["pair"] = (MemoryStore(), FakeLister())
        elif sys.platform == "darwin":
            _BACKEND["pair"] = (KeychainStore(), HttpsLister())
        else:
            _BACKEND["pair"] = (NotBuiltStore(), NotBuiltLister())
    return _BACKEND["pair"]


def built():
    """Whether connecting a provider can work at all: both seams built (the fake under a test, or the keychain and the
    provider call)."""
    store, lister = backend()
    return not isinstance(store, NotBuiltStore) and not isinstance(lister, NotBuiltLister)


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
    return [p for p in PROVIDER_ORDER if PROVIDERS[p][4] and          # #132 G1: settings first, so the keychain is asked only
            (p == "claude" or (isinstance(saved.get(p), dict) and store.has(p)))]   # about a provider Alan connected


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
def claude_auth(saved, store):
    """How Claude signs in: "key" when settings hold a Claude key and the store has it, else "subscription". #132 G1: the
    keychain is asked only once settings say Claude has a key."""
    return "key" if isinstance(saved.get("models"), list) and store.has("claude") else "subscription"


def card(pid, settings, store, conn):
    """One provider card: its words, status (connected, not, soon), how it signs in, its models and those found."""
    name, blurb, billing, how, live = PROVIDERS[pid]
    p = saved_providers(settings).get(pid) or {}
    on = pid in conn
    auth = claude_auth(p, store) if pid == "claude" else ("key" if on else None)
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
def stepped_down(job, settings, store=None, confidential=False):
    """The model a job steps down to at a limit: the next kind down's choice, or its recommended Claude model when the material
    is confidential and that choice is another provider's (#132 G5)."""
    down = chosen(STEP_DOWN[job], settings, store)
    return JOBS[STEP_DOWN[job]]["recommended"] if confidential and not down.startswith("claude:") else down


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
        return {"model": stepped_down(job, settings, store, confidential), "wait": False, "ask": False,
                "why": "limit: stepped down"}
    if mode == "ask":
        return {"model": None, "wait": False, "ask": True, "why": "limit: ask"}
    return {"model": None, "wait": True, "ask": False, "why": "limit: waits for the reset"}


# ── #132 G5 (proposal): confidential material only to Claude, decided in the server ─────────────────────────────────────
# route() already keeps a confidential job on Claude. These make that the server's one way to pick a model: the live server
# calls route_for (never route) for every run, and send_allowed is the gate any call to a provider other than Claude must pass
# first (G4's direct call; none exists yet). Fail closed: a job is confidential unless the server has shown it isn't.
SECRET_MARKS = __import__("re").compile(r"(?i)\b(confidential|restricted)\b|client-safe:\s*no")
CONFIDENTIAL_WORDS = "Confidential material is only ever sent to Claude."


def confidential_job(job, text="", declared=None):
    """(confidential, why) for one job. why: "tools" (a job that uses tools reads files and mail itself, so it is Claude's
    only), "declared" (the server found a confidential meeting or note, or a client-restricted item), "unchecked" (the call
    site made no check: counts as confidential), "marked" (the text sent is marked confidential or restricted, or Client-safe:
    no), or "" (declared not confidential by the server, and the text is clean)."""
    if JOBS.get(job, {"tools": True})["tools"]:
        return True, "tools"
    if declared is True:
        return True, "declared"
    if declared is not False:
        return True, "unchecked"
    if SECRET_MARKS.search(text or ""):
        return True, "marked"
    return False, ""


def send_allowed(model_id, confidential):
    """The gate before any call to a provider: Refused for confidential material (or material not shown to be otherwise) to a
    provider other than Claude."""
    if not str(model_id or "").startswith("claude:") and confidential is not False:
        raise Refused(CONFIDENTIAL_WORDS)


def route_for(job, settings, text="", declared=None, store=None, limited=False):
    """route(), with the job's confidentiality decided here from what the server knows (confidential_job), and the gate checked
    on the answer: the server's only way to pick a model. Adds "confidential" and "confidential_why" to route's answer."""
    conf, why = confidential_job(job, text, declared)
    out = route(job, settings, store, confidential=conf, limited=limited)
    if out["model"]:
        send_allowed(out["model"], conf)
    return dict(out, confidential=conf, confidential_why=why)


def retry_kind(job, check_notes):
    """A quick edit whose plain-code check found a changed date, number, name or ID is tried once on the next kind up: that
    kind, or None (no retry: the check passed, or it isn't a quick edit)."""
    return KIND_UP.get(job) if check_notes else None


# ── #132 G4 (proposal): the direct call, for a quick edit on text the checks found clean ────────────────────────────────
# Which features may send text to a provider other than Claude: a declared list, a feature and its options at a time. Round 2
# declares one: AI on selected text (edit-ai), and only the options whose instruction is creaite's own words (not "Or say what
# you want…", whose instruction is free text, and not "Make it executive", which adds the style guide). The drafts (writing) are
# built from tracker facts, so none is declared: they stay on Claude. A tools job never leaves Claude (G5).
CLEAN_FEATURES = {"edit-ai": ("rewrite", "shorter", "longer", "spelling", "polish", "formal", "warmer", "format", "checklist",
                              "summary")}
DIRECT_HOSTS = {"openai": "api.openai.com"}       # the only host a direct call goes to (G2's api.openai.com, nothing new)
DIRECT_PATHS = {"openai": "/v1/chat/completions"}
DIRECT_TIMEOUT = 30                               # seconds
DIRECT_SEND = 16_000                              # characters of prompt sent at most (edit_ai's 12k of text, plus its rules)
DIRECT_CAP = 256_000                              # bytes read back at most
DIRECT_TOKENS = 2_000                             # the reply's length, in the provider's tokens, at most
MODEL_ID = re.compile(r"[A-Za-z0-9._:-]{1,80}")


def declared(feature, option, problems):
    """What the server declares to route_for (G5) for one request: False (not confidential: it may go to the chosen provider)
    only for a declared feature and option whose text the checks passed ([] problems); True otherwise (Claude only)."""
    return not (option in CLEAN_FEATURES.get(feature, ()) and problems == [])


class DirectCaller(HttpsLister):
    """The direct call: one HTTPS POST of one prompt, no tools, no files, to DIRECT_HOSTS only, with G2's guarantees (TLS 1.2
    or later verified, no redirect followed, no proxy from the environment, the key in one header). `base` and `context` are for
    tests only. Errors carry the host and an HTTP status, never the key, the prompt or the reply."""

    def __init__(self, base=None, context=None, timeout=DIRECT_TIMEOUT, cap=DIRECT_CAP):
        super().__init__(base or {p: f"https://{h}" for p, h in DIRECT_HOSTS.items()}, context, timeout, cap)

    def complete(self, provider, model_id, prompt, key):
        """(the reply's text, {"in": tokens sent, "out": tokens back}) for one prompt to one of the provider's models."""
        if provider not in DIRECT_HOSTS or provider not in self.base:
            raise ValueError("That provider has no direct call.")
        if not isinstance(model_id, str) or not MODEL_ID.fullmatch(model_id):
            raise ValueError("That isn't a model id.")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > DIRECT_SEND:
            raise ValueError("Nothing to send, or too much.")
        url = self.base[provider] + DIRECT_PATHS[provider]
        host = urllib.parse.urlsplit(url).hostname or "?"
        if not url.startswith("https://"):
            raise ProviderUnreachable(f"{host}: only https is used")
        if not isinstance(key, str) or not KEY_CHARS.fullmatch(key):
            raise KeyRefused(400)
        import json
        body = json.dumps({"model": model_id, "messages": [{"role": "user", "content": prompt}],
                           "max_completion_tokens": DIRECT_TOKENS, "store": False}).encode("utf-8")
        status, raw = self.post(url, host, body, key_headers(provider, key))
        if status is not None and 400 <= status < 500:
            _log(f"{host} direct call: {status}")
            raise KeyRefused(status)
        if status != 200:
            _log(f"{host} direct call: {status}")
            raise ProviderUnreachable(f"{host}: answered {status}")
        text, used = self.reply(raw, host)
        _log(f"{host} direct call: 200, {used['in']} tokens in, {used['out']} out")
        return text, used

    def post(self, url, host, body, headers):
        """(HTTP status, at most cap + 1 bytes of the answer) for one POST; ProviderUnreachable when there is no answer."""
        req = urllib.request.Request(url, data=body, method="POST", headers={
            **headers, "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "creaite"})
        try:
            with self.opener().open(req, timeout=self.timeout) as r:
                return r.status, r.read(self.cap + 1)
        except urllib.error.HTTPError as e:
            e.close()
            return e.code, b""
        except Exception as e:  # noqa: BLE001  network, TLS, timeout: never the key, the prompt or the body
            _log(f"{host} direct call: unreachable ({type(e).__name__})")
            raise ProviderUnreachable(f"{host}: couldn't be reached ({type(e).__name__})") from None

    def reply(self, raw, host):
        """The first choice's text and the token counts from a chat answer."""
        import json
        if len(raw) > self.cap:
            raise ProviderUnreachable(f"{host}: the answer was too large")
        try:
            data = json.loads(raw.decode("utf-8"))
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            used = {"in": int(usage.get("prompt_tokens") or 0), "out": int(usage.get("completion_tokens") or 0)}
        except Exception:  # noqa: BLE001  anything else is not an answer
            raise ProviderUnreachable(f"{host}: the answer wasn't a reply") from None
        if not isinstance(text, str) or not text.strip():
            raise ProviderUnreachable(f"{host}: the answer was empty")
        return text, used


class NotBuiltCaller:
    """No direct call (off a Mac, or under the test fakes unless a test puts its own caller in): refuses."""

    def complete(self, provider, model_id, prompt, key):
        """Never called through: the route sees NotBuilt and runs Claude as before."""
        raise NotBuilt(NOT_BUILT_WORDS)


def caller():
    """The direct call the live server uses: DirectCaller on a Mac, else NotBuiltCaller; NotBuiltCaller under the test fakes
    (no test reaches a real provider), unless the test put its own in _DIRECT."""
    if "caller" not in _DIRECT:
        _DIRECT["caller"] = DirectCaller() if sys.platform == "darwin" and not fake_mode() else NotBuiltCaller()
    return _DIRECT["caller"]


_DIRECT = {}
# ── end #132 G4 ─────────────────────────────────────────────────────────────────────────────────────────────────────────


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

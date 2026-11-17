#!/usr/bin/env python3
"""check_personal_values.py -- the LOCK: engine code must hold none of the owner's personal values.

It names no person, desk, label or path itself. Search terms are built AT RUN TIME from:
  (a) the personal values of the setup folder by an explicit key model (names, labels, desks, paths, topics;
      not prose or generic words; env GC_SETUP_DIR, or --setup, else
      <personal code root>/tools/grand-central/setup), skipping keys that start with "_" and a small stoplist;
  (b) the personal code root path, the notes root path (shared/person_roots.py) and the home folder's user name;
  (c) the known-personal pattern of system/tools/check_no_private_desks.py (hashed names), reused by import.
It scans every non-.pyc, non-binary file under --root (default: this folder), code AND comments, case-insensitive
with word boundaries. Output is `file:line:category:hash8` -- never the matched value.
Allow-list: <setup dir>/personal-values-allow.txt (or --allow); missing = no exceptions, lines `path:term  # reason`; term may be `sha:<hash8>`.
--precommit: if no setup folder resolves, prints a fixed skip note and exits 0; else the normal check.
EXIT 0 clean | 1 found | 2 cannot evaluate (setup missing/empty, matcher missing, bad allow-list). Fails closed.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SHARED = os.path.dirname(HERE)
PLUGIN = os.path.dirname(SHARED)
ALLOW_NAME = "personal-values-allow.txt"
STOPLIST = {"true", "false", "none", "null", "the", "and", "for", "all", "any", "yes", "off", "not", "new",
            "mail", "email", "name", "id", "ids", "key", "keys", "list", "text", "type", "desk", "desks",
            "diary", "inbox", "info", "status", "low", "high", "medium", "root", "other", "default"}
SKIP_DIRS = {"__pycache__", ".git"}
# DB layer: common first names that are also ordinary English words, and free-mail domains. The ONLY exclusions of the DB layer
# besides gc_settings.SHIPPED_DEFAULTS (both through generic_words()).
GENERIC_NAMES = {"will", "mark", "grant", "may", "bill", "rose", "hope", "grace", "joy", "faith", "dean", "frank", "guy",
                 "jack", "jay", "june", "april", "august", "dawn", "drew", "gene", "glen", "heath", "jim", "ray", "rich",
                 "sandy", "sue", "summer", "victor", "wade", "walter", "bob", "pat", "lane", "page", "reed", "river",
                 "bcc", "sky", "star", "storm", "tom", "ty", "van", "chase", "cliff", "dale", "earl", "hunter", "miles", "pearl",
                 "ruby", "violet", "iris", "lily", "daisy", "amber", "ivy", "chip", "bishop", "king", "lord", "major"}
# Public services and brands the engine legitimately names (a domain of one of these in his database is not a personal value).
PUBLIC_SERVICES = {"claude", "anthropic", "google", "apple", "uber", "paypal", "venmo", "citi", "slack", "doordash", "x",
                   "example", "invalid", "github", "amazon", "microsoft", "facebook", "linkedin", "stripe"}
FREE_MAIL = {"gmail.com", "googlemail.com", "yahoo.com", "ymail.com", "hotmail.com", "outlook.com", "live.com", "msn.com",
             "icloud.com", "me.com", "mac.com", "aol.com", "proton.me", "protonmail.com", "gmx.com", "mail.com",
             "comcast.net", "verizon.net", "att.net", "sbcglobal.net"}


class CannotEvaluate(Exception):
    pass


def h8(term):
    return hashlib.sha256(term.lower().encode("utf-8")).hexdigest()[:8]


# Explicit model of what is personal in a setup file (shapes read from the setup folder):
#   NAME_KEYS      a string under one of these keys is a name, label, desk, path, account or the owner's name
#   NAME_CONTAINERS  the KEYS of these dicts are names (desks, labels, people, domains, label names); for the
#                  ones in VALUE_CONTAINERS the string values are names too
#   any string that is a filesystem path (starts with "/" or "~/", or holds "/Users/")
#   TOPIC_KEYS     lists of regexes: the alternation words (people, places, projects) are topic names
# Everything else (prose, _status/status/note text, numbers, booleans, code-ish words, life_part values) is
# skipped, and a stoplist of common English/programming words is a second filter.
NAME_KEYS = {"owner_name", "owner_id", "legacy_source_prefixes", "default_desk", "notes_root", "drop_dir", "mailroom_user", "mailroom_install_dir",
             "mailroom_account_stem", "display", "desk", "label_prefix", "label", "plain", "name", "main_diary", "sender_contains",
             "extra_research_domains", "data_root", "notes_state_subdir", "pulse_desk"}
NAME_CONTAINERS = {"labels", "people", "domains", "desks", "parts_to_desk", "gmail_names"}
VALUE_CONTAINERS = {"parts_to_desk", "gmail_names"}
TOPIC_KEYS = {"sanity"}
# Setup keys whose values are words or prose about the owner's life (places, airlines, request words, example sentences).
# Their words are search terms too, by the rule in _prose_terms.
PROSE_KEYS = {"prompt_examples", "trip_words", "needs_words_extra", "negative_fact_words"}
STOPLIST |= {"verdict", "deadline", "python3", "python", "home", "personal", "family", "money", "property",
             "trip", "booking", "airlines", "travel", "due",
             "today", "overdue", "cancelled", "renew", "example", "todo", "plain", "label", "labels", "read",
             "alarm", "true", "false", "commercial", "receipts", "notifications", "promos", "github", "main",
             "diary", "work", "test", "tests", "file", "path", "data", "state", "status", "proposed",
             "words", "projects", "delta", "sides", "casting", "callback", "were", "was", "with", "that", "this", "from", "have", "been", "handled", "passed"}


def shipped_generic():
    """Lowercase names the plugin ships as generic defaults (gc_settings.SHIPPED_DEFAULTS, the owner's ruling of 2026-11-16),
    plus the running harness's OWN name derived at run time from the plugin manifest (and its words). Not personal: a
    setup value equal to one of these is not flagged. A setup value that differs from them is."""
    if HERE not in sys.path:
        sys.path.insert(0, HERE)
    import gc_settings
    out = {str(v).lower() for v in gc_settings.SHIPPED_DEFAULTS.values() if "{" not in str(v)}
    name = gc_settings.harness_name().lower()
    out.add(name)
    out.update(w for w in re.split(r"[^a-z0-9]+", name) if len(w) >= 3)
    return out


def generic_words():
    """The one list of words the DB layer never treats as personal: SHIPPED_DEFAULTS' words plus GENERIC_NAMES."""
    return shipped_generic() | GENERIC_NAMES | STOPLIST


# A real home-folder path (some person's /Users/<name>/ or /home/<name>/) in code is a leak whoever the person is.
HOME_PATH = re.compile(r"(?<![\w/])/(?:Users|home)/(?!Shared\b)[A-Za-z0-9._-]+/")


def _is_path(v):
    return v.startswith("/") or v.startswith("~/") or "/Users/" in v


def _add(out, v, cat):
    if isinstance(v, str):
        v = v.strip()
        if len(v) >= 3 and v.lower() not in STOPLIST and not v.upper().startswith("TODO"):
            out.append((v, cat))


def _topic_words(node, out):
    if isinstance(node, str):
        for tok in node.split("|"):
            tok = re.sub(r"\\[A-Za-z]\??|\.\??", "", tok)   # \b, \s?, .?  (regex glue, not words)
            if re.fullmatch(r"[A-Za-z][A-Za-z0-9]{3,}", tok):
                _add(out, tok, "setup-topic")
    elif isinstance(node, list):
        for v in node[1:] if (node and isinstance(node[0], str) and isinstance(node[-1], list)) else node:
            _topic_words(v, out)
    elif isinstance(node, dict):
        for v in node.values():
            _topic_words(v, out)


def _prose_terms(node, out, depth=0):
    """Words of a prose-ish setup value. A short string is a search term as a whole phrase; a regex alternation
    (a|b|c) gives each word; any string also gives its proper-noun-like tokens (capitalised, not the first word of a
    sentence). Dict keys that map a word to a value are words too (the group names, one level down, are not)."""
    if isinstance(node, str):
        s = node.strip()
        if "|" in s or re.search(r"\\[A-Za-z]|\.\??", s):
            _topic_words(s, out)
            return
        if len(s) <= 40:
            _add(out, s, "setup-topic")
        toks = re.findall(r"[A-Za-z][A-Za-z0-9'-]*", s)
        for i, tok in enumerate(toks):
            if i and len(tok) >= 4 and tok[0].isupper() and not tok.isupper():
                _add(out, tok, "setup-topic")
    elif isinstance(node, list):
        for v in node:
            _prose_terms(v, out, depth)
    elif isinstance(node, dict):
        for k, v in node.items():
            if str(k).startswith("_"):
                continue
            if depth >= 1 and isinstance(v, (str, list)):
                _add(out, str(k), "setup-topic")
            _prose_terms(v, out, depth + 1)


def extract_terms(node, out, key="", parent=""):
    """Collect (term, category) pairs by the explicit model above. `_`-keys are skipped entirely."""
    if isinstance(node, dict):
        for k, v in node.items():
            k = str(k)
            if k.startswith("_"):
                continue
            if k in TOPIC_KEYS:
                _topic_words(v, out)
                continue
            if k in PROSE_KEYS:
                _prose_terms(v, out)
                continue
            if key in NAME_CONTAINERS:
                _add(out, k, "setup-name")
            extract_terms(v, out, k, key)
    elif isinstance(node, list):
        for v in node:
            extract_terms(v, out, key, parent)
    elif isinstance(node, str):
        if _is_path(node):
            _add(out, node, "setup-path")
        elif key in NAME_KEYS or (parent in VALUE_CONTAINERS) or (key in VALUE_CONTAINERS):
            _add(out, node, "setup-name")


def load_roots():
    if SHARED not in sys.path:
        sys.path.insert(0, SHARED)
    try:
        import person_roots
        return person_roots
    except Exception as e:
        raise CannotEvaluate("cannot import person_roots: %s" % type(e).__name__)


def setup_dir(arg, pr):
    d = arg or os.environ.get("GC_SETUP_DIR")
    if not d:
        pcr = pr.personal_code_root()
        if not pcr:
            raise CannotEvaluate("no setup folder: set GC_SETUP_DIR or --setup, or define the personal code root")
        d = os.path.join(pcr, "tools", "grand-central", "setup")
    if not os.path.isdir(d):
        raise CannotEvaluate("setup folder missing")
    return d


def build_terms(setup, pr, db=None):
    """-> {lowercase term: category}. db: path of the owner database (None = resolve it from the setup; "" = none)."""
    terms = {}
    names = sorted(n for n in os.listdir(setup) if n.endswith(".json"))
    if not names:
        raise CannotEvaluate("setup folder holds no .json files")
    for n in names:
        try:
            with open(os.path.join(setup, n), encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            raise CannotEvaluate("setup file unreadable or not JSON")
        vals = []
        extract_terms(data, vals)
        for v, cat in vals:
            terms.setdefault(v.lower(), cat)
    for t in shipped_generic():
        terms.pop(t, None)
    if not terms:
        raise CannotEvaluate("setup yields no search terms")
    dbp = db_file(setup) if db is None else db
    if dbp:
        db_terms(dbp, terms)
    for path in (pr.personal_code_root(), pr.notes_root()):
        if path:
            terms[path.lower()] = "personal-path"
    user = os.path.basename(os.path.expanduser("~"))
    if len(user) >= 3 and user.lower() not in STOPLIST:
        terms.setdefault(user.lower(), "home-user")
    return terms


SECOND_LEVEL = {"co", "com", "org", "net", "gov", "edu", "ac", "ne", "or"}   # co.uk, com.au, ...


def registrable_label(domain):
    """'acmetalent' from 'mail.acmetalent.com' (the part before the public suffix; second-level suffixes like co.uk handled)."""
    parts = [x for x in domain.strip().lower().lstrip("@").split(".") if x]
    if len(parts) < 2:
        return ""
    if len(parts) >= 3 and parts[-2] in SECOND_LEVEL and len(parts[-1]) == 2:
        return parts[-3]
    return parts[-2]


_WORDS = []


def english_words():
    """The system dictionary as a set (empty when there is none): used only to keep common words out of short forms."""
    if not _WORDS:
        try:
            with open("/usr/share/dict/words", encoding="utf-8", errors="replace") as f:
                _WORDS.append({w.strip().lower() for w in f})
        except OSError:
            _WORDS.append(set())
    return _WORDS[0]


def db_file(sdir):
    """The owner's database the way production resolves it for him: env GC_DATA_ROOT, else the setup's gc.json data_root,
    else the harness default; <that>/rig.db. -> path or "" when there is no such file (no owner DB: the layer is skipped)."""
    root = os.environ.get("GC_DATA_ROOT")
    if not root:
        try:
            with open(os.path.join(sdir, "gc.json"), encoding="utf-8") as f:
                root = json.load(f).get("data_root")
        except (OSError, ValueError, AttributeError):
            root = None
    if not root:
        if HERE not in sys.path:
            sys.path.insert(0, HERE)
        import gc_settings
        root = os.path.join(os.path.expanduser("~"), ".local", "share", gc_settings.harness_name(), "grand-central")
    p = os.path.join(os.path.expanduser(str(root)), "rig.db")
    return p if os.path.isfile(p) else ""


def db_terms(path, terms):
    """Add the names that live only in the owner's database, READ-ONLY: each person-name part, person email addresses,
    domains of person senders (not free-mail), organization names. Unreadable DB -> CannotEvaluate."""
    skip = generic_words()
    try:
        con = sqlite3.connect("file:%s?mode=ro" % path.replace("?", "%3f"), uri=True, timeout=5)
        try:
            people = [r[0] for r in con.execute("SELECT name FROM kg_things WHERE kind='person' AND key<>'person:me'")]
            orgs = [r[0] for r in con.execute("SELECT name FROM kg_things WHERE kind IN ('organization','company')")]
            senders = [r[0] for r in con.execute("SELECT sender FROM v_thing_senders WHERE thing_kind='person'")]
        finally:
            con.close()
    except sqlite3.Error:
        raise CannotEvaluate("owner database exists but cannot be read")

    def put(v, cat):
        v = (v or "").strip().lower()
        if len(v) >= 3 and v not in skip:
            terms.setdefault(v, cat)

    free_labels = {registrable_label(d) for d in FREE_MAIL}

    def put_domain(dom):
        dom = (dom or "").strip().lower().lstrip("@")
        if not dom or dom in FREE_MAIL:
            return
        lab = registrable_label(dom)
        if lab in PUBLIC_SERVICES:
            return
        put(dom, "db-domain")
        if len(lab) >= 4 and lab not in free_labels and lab not in english_words():
            put(lab, "db-label")

    for n in people:
        if n and "@" in n:                      # a person row named by its address: the address, not its pieces
            put(n, "db-address")
            put_domain(n.rpartition("@")[2])
            continue
        for part in re.findall(r"[^\W\d_][^\W\d_'-]*", n or ""):
            put(part, "db-person")
    for n in orgs:
        n = (n or "").strip()
        if "." in n and " " not in n:           # an organization stored only by its domain
            put_domain(n)
            continue
        if n == n.lower() and not any(ch.isdigit() for ch in n):
            continue                            # a lowercase common noun, not an organization's name
        put(n, "db-org")
        words = re.findall(r"[A-Za-z][A-Za-z']*", n)
        if len(words) >= 3:                     # short form: initials, only when not a common word
            ini = "".join(w[0] for w in words).lower()
            if len(ini) >= 3 and ini not in english_words():
                put(ini, "db-initials")
    for a in senders:
        a = (a or "").strip().lower()
        if a and not a.startswith("@"):
            put(a, "db-address")
        put_domain(a.rpartition("@")[2])


def load_matcher():
    p = os.path.join(PLUGIN, "system", "tools", "check_no_private_desks.py")
    if not os.path.isfile(p):
        raise CannotEvaluate("known-personal matcher (check_no_private_desks.py) not found")
    spec = importlib.util.spec_from_file_location("_cnpd", p)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return mod, mod.Matcher()
    except Exception as e:
        raise CannotEvaluate("known-personal matcher failed to load: %s" % type(e).__name__)


def load_allow(path):
    allow = set()
    if not os.path.isfile(path):
        return allow
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            body, sep, reason = s.partition("#")
            if not sep or not reason.strip() or ":" not in body:
                raise CannotEvaluate("allow-list line %d malformed (need path:term  # reason)" % n)
            p, _, t = body.strip().partition(":")
            t = t.strip().lower()
            allow.add((p.strip(), t[4:] if t.startswith("sha:") else h8(t)))
    return allow


def iter_files(root):
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS)
        for fn in sorted(fns):
            if fn.endswith(".pyc"):
                continue
            yield os.path.join(dp, fn)


def trie_regex(words):
    """One regex for many literal words, with common prefixes merged (far faster than a flat alternation)."""
    trie = {}
    for w in words:
        node = trie
        for ch in w:
            node = node.setdefault(ch, {})
        node[""] = {}

    def emit(node):
        alts, here = [], "" in node
        for ch in sorted(k for k in node if k):
            alts.append(re.escape(ch) + emit(node[ch]))
        if not alts:
            return ""
        body = alts[0] if len(alts) == 1 else "(?:" + "|".join(alts) + ")"
        return "(?:%s)?" % body if here else body
    return emit(trie)


def scan(root, terms, mod, matcher, allow):
    """-> list of (relpath, line, category, hash8)"""
    pat = re.compile(r"(?<!\w)(?:%s)(?!\w)" % trie_regex(sorted(terms, key=len, reverse=True)), re.I)
    found = []
    for path in iter_files(root):
        rel = os.path.relpath(path, root)
        if rel == ALLOW_NAME:
            continue
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            raise CannotEvaluate("a file under the root is unreadable")
        if b"\0" in data[:4096]:
            continue
        for i, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            hits = [(m.group(0), terms[m.group(0).lower()]) for m in pat.finditer(line)]
            hits += [(m.group(0), "personal-path") for m in HOME_PATH.finditer(line)]
            for r in mod.RUN.findall(line):
                k = matcher.run_kind(r)
                if k:
                    hits.append((r, "known-" + k))
            for w in mod.WORD.findall(line):
                k = matcher.kind(w)
                if k:
                    hits.append((w, "known-" + k))
            for val, cat in hits:
                hh = h8(val)
                if (rel, hh) not in allow:
                    found.append((rel, i, cat, hh))
    return found


def run(root, setup=None, allow_path=None, out=sys.stdout, db=None):
    pr = load_roots()
    sdir = setup_dir(setup, pr)
    terms = build_terms(sdir, pr, db)
    mod, matcher = load_matcher()
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise CannotEvaluate("root is not a folder")
    allow = load_allow(allow_path or os.path.join(sdir, ALLOW_NAME))
    found = sorted(set(scan(root, terms, mod, matcher, allow)))
    for rel, i, cat, hh in found:
        print("%s:%d:%s:%s" % (rel, i, cat, hh), file=out)
    counts = collections.Counter(c for _, _, c, _ in found)
    print("personal-values check: %d finding(s) %s; %d search terms" % (len(found), dict(sorted(counts.items())),
                                                                       len(terms)), file=out)
    return 1 if found else 0


SKIP_NOTE = ("personal-values check skipped: no owner setup on this machine; "
             "No Private Desks covers CI")


def precommit(root, setup=None, allow_path=None, db=None):
    """Pre-commit mode: skip (0) ONLY when it is confirmed that no setup folder exists on this machine (no setup argument,
    no GC_SETUP_DIR, and the personal code root is not set or has no setup folder). Anything else that goes wrong
    (a broken person_roots import, an unreadable folder, a named-but-missing folder) is CannotEvaluate -> exit 2."""
    pr = load_roots()                      # an import failure raises CannotEvaluate here: never "no setup"
    if not setup and not os.environ.get("GC_SETUP_DIR"):
        pcr = pr.personal_code_root()
        if not pcr or not os.path.isdir(os.path.join(pcr, "tools", "grand-central", "setup")):
            print(SKIP_NOTE)
            return 0
    return run(root, setup, allow_path, db=db)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=HERE)
    ap.add_argument("--setup", default=None)
    ap.add_argument("--allow", default=None)
    ap.add_argument("--db", default=None, help="owner database (default: resolved from the setup; read-only)")
    ap.add_argument("--precommit", action="store_true", help="skip (exit 0) when no setup folder resolves")
    a = ap.parse_args(argv)
    try:
        return (precommit if a.precommit else run)(a.root, a.setup, a.allow, db=a.db)
    except CannotEvaluate as e:
        print("CANNOT EVALUATE: %s" % e)
        return 2
    except Exception as e:  # fail closed
        print("CANNOT EVALUATE: unexpected %s" % type(e).__name__)
        return 2


if __name__ == "__main__":
    sys.exit(main())

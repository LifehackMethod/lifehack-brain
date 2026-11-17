"""store_graph.py: the flexible memory (migration 005, kg_* tables). Con-taking cores; the front-door wrappers live in
store.py, and callers (gc, engine, skills) go through those. Nothing here opens a database itself.

The ONE door for his answers is record_answer(): validate everything first, append one kg_answers row (one decision),
then apply it as a fact or a link tagged who='owner'. rebuild_from_answers() replays kg_answers alone and must give back
the same picture of his word. Allowed words (kg_vocab / kg_fact_keys) are checked on every write; anything else is refused.

Precedence: his word is never replaced by code or AI. A non-owner write on a (thing, key) he has answered is kept for
history but stored already-superseded by his fact. Later answers from him replace earlier ones (recency rule).
"""
import datetime as dt
import hashlib
import json
import re
import sqlite3

import clock

WHO = ("owner", "code", "ai_research", "ai_guess")
MULTI = {"label", "exception", "keyword", "legacy_fact", "canon", "life_fact", "note", "member_item", "setting", "trigger"}  # many values may hold at once
LINK_PREFIX = "link:"
NOT_PREFIX = "not:"   # on a MULTI key, value "not:<v>" retires the current value <v> (see assert_fact)


LEAN_RE = re.compile(r"(floor:|set:)-?\d+(\.\d+)?|mute|undecided")   # always .fullmatch: "$" lets a trailing newline through


class Refused(ValueError):
    """A write the allowed words do not permit."""


def _ts():
    n = clock.now()
    if n.tzinfo is not None:
        n = n.astimezone(dt.timezone.utc)
    return n.strftime("%Y-%m-%dT%H:%M:%SZ")


def norm(name):
    return re.sub(r"\s+", " ", str(name or "").strip().lower())


def thing_key(kind, name):
    n = norm(name)
    if kind == "domain":
        n = n.lstrip("@")
    if kind == "address" and "<" in n and ">" in n:
        n = n[n.index("<") + 1:n.index(">")].strip()
    return "%s:%s" % (kind, n)


# ---- allowed words --------------------------------------------------------------------------------------
def _in_vocab(con, lst, value):
    return con.execute("SELECT 1 FROM kg_vocab WHERE list=? AND value=?", (lst, value)).fetchone() is not None


def _check(con, lst, value, what):
    if not _in_vocab(con, lst, value):
        allowed = [r[0] for r in con.execute("SELECT value FROM kg_vocab WHERE list=? ORDER BY value", (lst,))]
        raise Refused("%s %r is not an allowed word (allowed: %s)" % (what, value, ", ".join(allowed)))


def check_fact(con, thing_kind, fact_key, value):
    r = con.execute("SELECT value_list, subject_kinds FROM kg_fact_keys WHERE key=?", (fact_key,)).fetchone()
    if r is None:
        keys = [x[0] for x in con.execute("SELECT key FROM kg_fact_keys ORDER BY key")]
        raise Refused("fact %r is not an allowed fact (allowed: %s)" % (fact_key, ", ".join(keys)))
    vlist, kinds = r[0], r[1]
    if kinds != "*" and thing_kind not in kinds.split(","):
        raise Refused("fact %r may not describe a %s (only: %s)" % (fact_key, thing_kind, kinds))
    if value is None or not str(value).strip():
        raise Refused("fact %r needs a value" % fact_key)
    if fact_key in MULTI and str(value).startswith(NOT_PREFIX):
        value = str(value)[len(NOT_PREFIX):].strip()   # "not:<v>": <v> is checked as if it were the value
        if not value:
            raise Refused("fact %r: %r needs a value after it" % (fact_key, NOT_PREFIX))
    if vlist:
        _check(con, vlist, value, "value for %s:" % fact_key)
    if fact_key == "levels_above_me" and not re.fullmatch(r"\d{1,2}", str(value).strip()):
        raise Refused("levels_above_me %r must be a whole number (0 = the same level)" % (value,))
    if fact_key == "keep_in_touch_days" and not re.fullmatch(r"[1-9]\d{0,3}", str(value).strip()):
        raise Refused("keep_in_touch_days %r must be a whole number of days (1 or more)" % (value,))
    if fact_key == "lean" and not LEAN_RE.fullmatch(str(value).strip()):
        raise Refused("lean %r must look like floor:3.5, set:2, mute or undecided" % (value,))


def add_vocab(con, lst, value, note=None):
    """Extend the allowed words (logged in events). Use sparingly; a new list or key belongs in a migration."""
    con.execute("INSERT OR IGNORE INTO kg_vocab(list,value,note) VALUES(?,?,?)", (lst, value, note))
    con.execute("INSERT INTO events(at,kind,detail) VALUES(?,?,?)", (_ts(), "vocab-added", "%s=%s" % (lst, value)))


def vocab(con):
    out = {}
    for lst, v in con.execute("SELECT list, value FROM kg_vocab ORDER BY list, value"):
        out.setdefault(lst, []).append(v)
    return out


# ---- things ---------------------------------------------------------------------------------------------
def thing(con, kind, name, created_by="code", legacy_ref=None, key=None):
    """Get or create a thing; returns its id. kind is checked; the key is '<kind>:<normalized name>' unless given."""
    _check(con, "thing_kind", kind, "thing kind")
    _check(con, "who", created_by, "who")
    key = key or thing_key(kind, name)
    r = con.execute("SELECT id FROM kg_things WHERE key=?", (key,)).fetchone()
    if r:
        r = (survivor(con, r[0]),)   # a merged thing: the survivor answers (Vision 3.7.4 rule 2: reads and writes follow merged_into)
        if legacy_ref:
            con.execute("UPDATE kg_things SET legacy_ref=COALESCE(legacy_ref, ?) WHERE id=?", (legacy_ref, r[0]))
        return r[0]
    return con.execute("INSERT INTO kg_things(kind,key,name,legacy_ref,created_by,created_at) VALUES(?,?,?,?,?,?)",
                       (kind, key, str(name).strip(), legacy_ref, created_by, _ts())).lastrowid


def survivor(con, thing_id):
    """The thing that now stands for this one: follow merged_into to the end (a thing that was never merged is its own survivor)."""
    seen = set()
    while thing_id not in seen:
        seen.add(thing_id)
        try:
            r = con.execute("SELECT merged_into FROM kg_things WHERE id=?", (thing_id,)).fetchone()
        except sqlite3.OperationalError:    # database older than migration 021: nothing is merged
            break
        if r is None or r[0] is None:
            break
        thing_id = r[0]
    return thing_id


def redirects(con):
    """{old key: organization key} from the record of the moves (org_moves). Empty before migration 021."""
    try:
        return {r[0]: r[1] for r in con.execute("SELECT old_key, new_key FROM org_moves")}
    except Exception:  # noqa: BLE001  (database older than migration 021)
        return {}


def thing_by_key(con, key):
    r = con.execute("SELECT id, kind, key, name, legacy_ref FROM kg_things WHERE key=?", (key,)).fetchone()
    return dict(zip(("id", "kind", "key", "name", "legacy_ref"), r)) if r else None


PLACEMENT_FACTS = ("levels_above_me",)


def _is_placement(con, kind, to_id):
    """A line that places someone (Vision 3.7.4 rule 8): his word only."""
    return kind in ("reports_to", "knows") or (kind in ("member_of", "part_of") and _thing_kind(con, to_id) == "organization")


# 3.3: the two kinds of thing each relationship may join (migration 023 holds the same table as a trigger). The frozen old kinds
# (circle, company, episode) stay joinable so old rows replay.
ENDS = {
    "member_of": ({"person"}, {"organization", "circle", "company"}),
    "part_of": ({"organization", "project", "item", "event", "episode"}, {"organization", "project"}),
    "involves": ({"event", "project", "episode"}, {"person", "address"}),
    "knows": ({"person"}, {"person"}),
    "reports_to": ({"person"}, {"person"}),
}
_PART_OF_OK = {("organization", "organization"), ("project", "organization"), ("item", "project"), ("event", "project"),
               ("episode", "project")}


def _check_ends(con, from_id, kind, to_id):
    if kind not in ENDS:
        return
    a, b = _thing_kind(con, from_id), _thing_kind(con, to_id)
    if kind == "part_of":
        ok = (a, b) in _PART_OF_OK
    else:
        ok = a in ENDS[kind][0] and b in ENDS[kind][1]
    if not ok:
        raise Refused("wrong ends: %s cannot join a %s to a %s" % (kind, a, b))


def _would_loop(con, from_id, kind, to_id):
    """True when a live `kind` line from_id -> to_id would close a loop (to_id already reaches from_id going up)."""
    if from_id == to_id:
        return True
    seen, todo = {to_id}, [to_id]
    while todo:
        for (n,) in con.execute("SELECT to_id FROM kg_links WHERE from_id=? AND kind=? AND replaced_by IS NULL "
                                "AND true_until IS NULL", (todo.pop(), kind)):
            if n == from_id:
                return True
            if n not in seen:
                seen.add(n)
                todo.append(n)
    return False


def _thing_kind(con, thing_id):
    r = con.execute("SELECT kind FROM kg_things WHERE id=?", (thing_id,)).fetchone()
    if r is None:
        raise Refused("no thing #%s" % thing_id)
    return r[0]


# ---- facts and links ------------------------------------------------------------------------------------
def assert_fact(con, thing_id, fact_key, value, who, certainty, source_kind, source_ref=None, answer_id=None,
                true_from=None, true_until=None, condition=None):
    """Write one fact. Single-valued keys: the new fact replaces the current one, unless the current one is his word and
    this one is not (then this one is kept, already superseded). Multi-valued keys: only an identical value is replaced.
    Returns the new fact id."""
    value = str(value).strip() if value is not None else value
    thing_id = survivor(con, thing_id)
    check_fact(con, _thing_kind(con, thing_id), fact_key, value)
    _check(con, "who", who, "who")
    _check(con, "certainty", certainty, "certainty")
    _check(con, "source_kind", source_kind, "source kind")
    if who == "owner" and answer_id is None:
        raise Refused("his word must point at the answer it came from")
    if who != "owner" and fact_key in PLACEMENT_FACTS:
        raise Refused("%s is his word: it is written only from his answer (who=%s refused)" % (fact_key, who))
    condition = norm(condition) or None
    sql = "SELECT id, who FROM kg_facts WHERE thing_id=? AND fact_key=? AND replaced_by IS NULL AND condition IS ?"
    args = [thing_id, fact_key, condition]
    retire = fact_key in MULTI and value.startswith(NOT_PREFIX)
    if fact_key in MULTI:
        sql += " AND value=?"
        args.append(value[len(NOT_PREFIX):].strip() if retire else value)
    current = con.execute(sql, args).fetchall()
    blocked = False
    if fact_key in MULTI and not retire and who != "owner":
        # his latest word on this value is "not:<value>": code or AI may not bring it back
        last = con.execute("SELECT value FROM kg_facts WHERE thing_id=? AND fact_key=? AND who='owner' AND condition IS ? "
                           "AND value IN (?,?) ORDER BY id DESC LIMIT 1", (thing_id, fact_key, condition, value, NOT_PREFIX + value)).fetchone()
        blocked = bool(last) and last[0] == NOT_PREFIX + value
    fid = con.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,source_ref,answer_id,"
                      "true_from,true_until,condition,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                      (thing_id, fact_key, value, who, certainty, source_kind, source_ref, answer_id, true_from,
                       true_until, condition, _ts())).lastrowid
    his = [c for c in current if c[1] == "owner"]
    if retire:
        # the "not:" fact is never current: it is stored already superseded by itself, and retires every current <v>
        # (a code/AI "not:" cannot retire his word)
        con.execute("UPDATE kg_facts SET replaced_by=? WHERE id=?", (fid, fid))
        for c in current:
            if who == "owner" or c[1] != "owner":
                con.execute("UPDATE kg_facts SET replaced_by=? WHERE id=?", (fid, c[0]))
    elif blocked:
        con.execute("UPDATE kg_facts SET replaced_by=? WHERE id=?", (fid, fid))
    elif his and who != "owner":
        con.execute("UPDATE kg_facts SET replaced_by=? WHERE id=?", (his[0][0], fid))
    else:
        for c in current:
            con.execute("UPDATE kg_facts SET replaced_by=? WHERE id=?", (fid, c[0]))
    return fid


def add_link(con, from_id, kind, to_id, who, certainty, source_kind, source_ref=None, answer_id=None, true_from=None,
             true_until=None, role=None):
    """Write one link. An identical current link (same from, kind, to) is replaced, with the same precedence as facts."""
    _check(con, "link_kind", kind, "link kind")
    _check(con, "who", who, "who")
    _check(con, "certainty", certainty, "certainty")
    _check(con, "source_kind", source_kind, "source kind")
    from_id, to_id = survivor(con, from_id), survivor(con, to_id)
    _thing_kind(con, from_id), _thing_kind(con, to_id)
    if who == "owner" and answer_id is None:
        raise Refused("his word must point at the answer it came from")
    _check_ends(con, from_id, kind, to_id)
    if kind == "involves" and who != "owner" and _thing_kind(con, from_id) != "episode" and not (
            _thing_kind(con, from_id) == "event" and certainty == "sure" and source_kind == "code"):
        raise Refused("involves by code is only the invite list of an event; anyone else, and every project, is his word")
    if who != "owner" and _is_placement(con, kind, to_id):
        raise Refused("placement is his word: a %s line to or from an organization, a reporting line or a tie between people "
                      "is written only from his answer (who=%s refused)" % (kind, who))
    if (kind == "reports_to" or (kind == "part_of" and _thing_kind(con, from_id) == "organization")) \
            and true_until is None and _would_loop(con, from_id, kind, to_id):
        raise Refused("loop: %s from #%s to #%s would put a thing above itself" % (kind, from_id, to_id))
    current = con.execute("SELECT id, who FROM kg_links WHERE from_id=? AND kind=? AND to_id=? AND replaced_by IS NULL",
                          (from_id, kind, to_id)).fetchall()
    his = [c for c in current if c[1] == "owner"]
    # migration 019: one current line per (from, kind, to). The new row is written already superseded (it points at a row that
    # exists), the old current rows are pointed at it, and only then does it become current: no moment has two current rows.
    first = his[0][0] if (his and who != "owner") else (current[0][0] if current else None)
    lid = con.execute("INSERT INTO kg_links(from_id,kind,to_id,role,who,certainty,source_kind,source_ref,answer_id,"
                      "true_from,true_until,replaced_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (from_id, kind, to_id, role, who, certainty, source_kind, source_ref, answer_id, true_from,
                       true_until, first, _ts())).lastrowid
    if not (his and who != "owner"):
        for c in current:
            con.execute("UPDATE kg_links SET replaced_by=? WHERE id=?", (lid, c[0]))
        if current:
            con.execute("UPDATE kg_links SET replaced_by=NULL WHERE id=?", (lid,))
    return lid


# ---- the one door for answers ----------------------------------------------------------------------------
def _validate_answer(con, question, words, asked_by, said_on, subject_kind, subject_name, fact_key, value,
                     words_kind="verbatim"):
    _check(con, "words_kind", words_kind, "words kind")
    for n, v in (("question", question), ("words", words), ("asked_by", asked_by)):
        if v is None or not str(v).strip():
            raise Refused("an answer needs %s" % n)
    try:
        dt.date.fromisoformat(str(said_on))
    except ValueError:
        raise Refused("said_on must be YYYY-MM-DD, got %r" % (said_on,))
    if (fact_key is None) != (value is None):
        raise Refused("fact_key and value come together")
    if fact_key is None:
        return
    if not subject_kind or not subject_name:
        raise Refused("a decision needs its subject (kind and name)")
    _check(con, "thing_kind", subject_kind, "thing kind")
    if fact_key.startswith(LINK_PREFIX):
        _check(con, "link_kind", fact_key[len(LINK_PREFIX):], "link kind")
        if ":" not in str(value):
            raise Refused("a link's value is the target thing key '<kind>:<name>', got %r" % (value,))
        _check(con, "thing_kind", str(value).split(":", 1)[0], "link target kind")
    else:
        check_fact(con, subject_kind, fact_key, value)


def _apply_answer(con, a):
    """Apply one kg_answers row (dict) as his fact or link. Returns ('fact'|'link'|None, id)."""
    if a["fact_key"] is None:
        return None, None
    if a["fact_key"] == "merge_into":
        return "merge", _do_merge(con, a)
    if a["fact_key"] == "unmerge":
        return "unmerge", _do_unmerge(con, a)
    rd = redirects(con)   # his words about an old company or circle land on the organization it became
    skey = rd.get(a["subject_key"], a["subject_key"])
    tid = thing(con, "organization" if skey.startswith("organization:") else a["subject_kind"], a["subject_name"],
                created_by="owner", key=skey)
    if a["fact_key"].startswith(LINK_PREFIX):
        tkey = rd.get(a["value"], a["value"])
        tkind, tname = tkey.split(":", 1)
        to = thing_by_key(con, tkey)
        to_id = to["id"] if to else thing(con, tkind, tname, created_by="owner", key=tkey)
        return "link", add_link(con, tid, a["fact_key"][len(LINK_PREFIX):], to_id, "owner", "sure", "answer",
                                str(a["id"]), a["id"], true_from=a["said_on"], true_until=a["true_until"])
    return "fact", assert_fact(con, tid, a["fact_key"], a["value"], "owner", "sure", "answer", str(a["id"]), a["id"],
                               true_from=a["said_on"], true_until=a["true_until"], condition=a["condition"])


_ACOLS = ("id", "question", "words", "asked_by", "said_on", "subject_key", "subject_kind", "subject_name", "fact_key",
          "value", "true_until", "queue_id", "legacy_answer_log_id", "recorded_at", "words_kind", "condition")


APPROVAL_Q = "approve staged filters sha256:"
APPROVAL_KEYS = ("approved_digest",)


def _is_approval_text(question, fact_key, value):
    q = " ".join(str(question or "").lower().split())
    return q.startswith("approve staged filters") or fact_key in APPROVAL_KEYS or (fact_key == "rule_status" and str(value).strip() == "approved")


def record_answer(con, question, words, asked_by, said_on=None, subject_kind=None, subject_name=None, fact_key=None,
                  value=None, true_until=None, queue_id=None, legacy_answer_log_id=None, words_kind="verbatim",
                  condition=None):
    """The door for his answers. REFUSES anything that carries the approval question or an approval fact: approvals come
    ONLY through approve_staged (an AI draft can never carry one, and no caller can mint one through here)."""
    if _is_approval_text(question, fact_key, value):
        raise Refused("an approval is not an ordinary answer: it comes only through approve_staged")
    return _record_answer(con, question, words, asked_by, said_on, subject_kind, subject_name, fact_key, value, true_until,
                          queue_id, legacy_answer_log_id, words_kind, condition)


def _record_answer(con, question, words, asked_by, said_on=None, subject_kind=None, subject_name=None, fact_key=None,
                   value=None, true_until=None, queue_id=None, legacy_answer_log_id=None, words_kind="verbatim",
                   condition=None):
    """THE ONE DOOR. One decision per call. Validates everything before writing anything; then appends the answer and
    applies it. Returns {answer_id, applied: 'fact'|'link'|None, row_id}."""
    said_on = said_on or clock.today().isoformat()
    if value is not None:
        value = str(value).strip()
        if fact_key and fact_key.startswith(LINK_PREFIX) and ":" in value:
            value = thing_key(*value.split(":", 1))  # link targets are keys: normalize like any thing key
    _validate_answer(con, question, words, asked_by, said_on, subject_kind, subject_name, fact_key, value, words_kind)
    if condition is not None and fact_key is None:
        raise Refused("a condition belongs to a decision")
    skey = thing_key(subject_kind, subject_name) if fact_key is not None else None
    if skey is not None:
        skey = _resolve_org_key(con, skey, subject_kind, subject_name)
        if skey.startswith("organization:"):
            subject_kind = "organization"
    aid = con.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,"
                      "fact_key,value,true_until,queue_id,legacy_answer_log_id,recorded_at,words_kind,condition) "
                      "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (str(question).strip(), str(words), str(asked_by).strip(), str(said_on), skey, subject_kind,
                       subject_name, fact_key, value, true_until, queue_id, legacy_answer_log_id, _ts(), words_kind,
                       norm(condition) or None)).lastrowid
    row = dict(zip(_ACOLS, con.execute("SELECT %s FROM kg_answers WHERE id=?" % ",".join(_ACOLS), (aid,)).fetchone()))
    kind, rid = _apply_answer(con, row)
    return {"answer_id": aid, "applied": kind, "row_id": rid}


def _resolve_org_key(con, skey, kind, name):
    """The key a decision about an organization is recorded under: the old company/circle key maps to the organization it
    became, and a plain name matches a live organization of that name (the opaque key is never typed by hand)."""
    rd = redirects(con)
    if skey in rd:
        return rd[skey]
    if kind == "organization":
        r = con.execute("SELECT key FROM kg_things WHERE kind='organization' AND merged_into IS NULL AND lower(name)=?", (norm(name),)).fetchall()
        if len(r) == 1:
            return r[0][0]
    return skey


def answers(con, subject_key=None, by_id=False):
    sql, args = "SELECT %s FROM kg_answers" % ",".join(_ACOLS), []
    if subject_key:
        sql, args = sql + " WHERE subject_key=?", [subject_key]
    return [dict(zip(_ACOLS, r)) for r in con.execute(sql + (" ORDER BY id" if by_id else " ORDER BY said_on, id"), args)]


def _release(con, table, owner_ids_sql, group_cols):
    """Step 1 of a replay: the code/AI rows that his word had superseded must be freed, ONE per group (the newest row of
    each group comes back to life; older ones in the group stay superseded, now by that newest row). Releasing them all, or
    while his row is still current, put two current rows on one pair and tripped the unique current-link index (migration
    019). So the survivor is parked pointing at itself (not current, not dangling) until his rows are deleted.
    Returns the parked ids; the caller deletes his rows, then calls _unpark."""
    rows = con.execute("SELECT id, %s FROM %s WHERE who<>'owner' AND replaced_by IN (%s) ORDER BY id"
                       % (group_cols, table, owner_ids_sql)).fetchall()
    newest = {}
    for r in rows:
        newest[tuple(r[1:])] = r[0]
    parked = []
    for r in rows:
        top = newest[tuple(r[1:])]
        con.execute("UPDATE %s SET replaced_by=? WHERE id=?" % table, (top, r[0]))      # the survivor points at itself
        if r[0] == top:
            parked.append(top)
    return parked


def _unpark(con, table, parked):
    for i in parked:
        con.execute("UPDATE %s SET replaced_by=NULL WHERE id=?" % table, (i,))


def rebuild_from_answers(con):
    """Throw away every fact and link of his and replay kg_answers in the order he said them. Code/AI rows stay; any
    that his word had superseded are released first (one per pair, see _release) and re-superseded by the replay.
    The caller owns the transaction."""
    pf = _release(con, "kg_facts", "SELECT id FROM kg_facts WHERE who='owner'",
                  "thing_id, fact_key, COALESCE(condition,''), CASE WHEN fact_key IN (%s) THEN value ELSE '' END"
                  % ",".join("'%s'" % k for k in sorted(MULTI)))
    pl = _release(con, "kg_links", "SELECT id FROM kg_links WHERE who='owner'", "from_id, kind, to_id")
    con.execute("DELETE FROM kg_facts WHERE who='owner'")
    con.execute("DELETE FROM kg_links WHERE who='owner'")
    _unpark(con, "kg_facts", pf)
    _unpark(con, "kg_links", pl)
    for a in answers(con, by_id=True):   # RECORDING order: the order the live picture was built in, so a retraction is never replayed before the yes it retracts, whatever dates he gave
        _apply_answer(con, a)


# ---- the full rebuild and the comparison (Vision 3.7.4 rules 5 and 6) -----------------------------------
def model_picture(con):
    """The model's current facts and links as comparable tuples, written with KEYS (ids differ between builds). Also the
    set of (key, kind, the key it was merged into or '') of every thing."""
    try:
        things = {tuple(r) for r in con.execute(
            "SELECT t.key, t.kind, COALESCE(m.key, '') FROM kg_things t LEFT JOIN kg_things m ON m.id=t.merged_into")}
    except sqlite3.OperationalError:        # database older than migration 021
        things = {(r[0], r[1], "") for r in con.execute("SELECT key, kind FROM kg_things")}
    facts = sorted(map(tuple, con.execute(
        "SELECT t.key, f.fact_key, f.value, f.who, COALESCE(f.condition,''), COALESCE(f.true_from,''), COALESCE(f.true_until,'') "
        "FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE f.replaced_by IS NULL")))
    links = sorted(map(tuple, con.execute(
        "SELECT a.key, l.kind, b.key, l.who, COALESCE(l.role,''), COALESCE(l.true_from,''), COALESCE(l.true_until,'') "
        "FROM kg_links l JOIN kg_things a ON a.id=l.from_id JOIN kg_things b ON b.id=l.to_id WHERE l.replaced_by IS NULL")))
    return {"things": things, "facts": facts, "links": links}


def diff_pictures(live, rebuilt):
    """-> list of difference rows (what, in_live_only|in_rebuilt_only, tuple)."""
    out = []
    for what in ("things", "facts", "links"):
        a, b = list(live[what]), list(rebuilt[what])
        from collections import Counter
        ca, cb = Counter(a), Counter(b)
        for row in sorted((ca - cb).elements()):
            out.append((what, "live_only", row))
        for row in sorted((cb - ca).elements()):
            out.append((what, "rebuilt_only", row))
    return out


def rebuild_model(con):
    """Rebuild the whole model on THIS connection from the permanent record: the recorded keys (thing_keys), his answers
    (kg_answers), the code-certain intake (the old tables, read as frozen history, via copy_legacy; the engine's settings).
    Wipes kg_facts, kg_links and every thing except person:me; kg_answers, thing_keys and kg_scores are never touched. Every
    thing comes back under the key recorded in thing_keys, so there is no re-keying. A recorded key that no replay produced
    is created from the record alone (kind and key; name from the key). The caller owns the transaction and passes a COPY.
    Returns counts."""
    con.execute("DELETE FROM kg_facts")
    con.execute("DELETE FROM kg_links")
    con.execute("DELETE FROM kg_things WHERE key<>'person:me'")
    legacy = copy_legacy(con)
    import common as ec
    ec.seed_settings(con)
    done = 0
    for a in answers(con, by_id=True):
        _apply_answer(con, a)
        done += 1
    made = unrecorded = 0
    recorded = {r[0]: (r[1], r[2]) for r in con.execute("SELECT key, kind, made_from FROM thing_keys")}
    have = {r[0] for r in con.execute("SELECT key FROM kg_things")}
    for key, (kind, made_from) in sorted(recorded.items()):
        if key in have:
            continue
        who = made_from.split(":", 1)[1] if made_from.startswith("writer:") else "code"
        thing(con, kind, key.split(":", 1)[1], created_by=who if who in WHO else "code", key=key)
        made += 1
    for (key,) in con.execute("SELECT key FROM kg_things").fetchall():
        if key not in recorded:
            unrecorded += 1
    return {"legacy": legacy, "answers_replayed": done, "from_record_only": made, "keys_not_recorded": unrecorded}


def his_picture(con):
    """Comparable picture of his word: current facts and links from his answers (ids left out, they change on rebuild),
    plus which code/AI facts are current (so a rebuild that loses a supersession shows up)."""
    f = con.execute("SELECT t.key, f.fact_key, f.value, f.answer_id, f.true_from, f.true_until, f.condition FROM kg_facts f "
                    "JOIN kg_things t ON t.id=f.thing_id WHERE f.who='owner' AND f.replaced_by IS NULL").fetchall()
    l = con.execute("SELECT a.key, l.kind, b.key, l.answer_id FROM kg_links l JOIN kg_things a ON a.id=l.from_id "
                    "JOIN kg_things b ON b.id=l.to_id WHERE l.who='owner' AND l.replaced_by IS NULL").fetchall()
    o = con.execute("SELECT f.id FROM kg_facts f WHERE f.who<>'owner' AND f.replaced_by IS NULL").fetchall()
    k = lambda t: tuple("" if x is None else str(x) for x in t)  # noqa: E731  (None-safe ordering)
    return {"facts": sorted(map(tuple, f), key=k), "links": sorted(map(tuple, l), key=k),
            "others_current": sorted(r[0] for r in o)}


# ---- reads ----------------------------------------------------------------------------------------------
_FCOLS = ("id", "fact_key", "value", "who", "certainty", "source_kind", "source_ref", "answer_id", "true_from",
          "true_until", "thing_key", "thing_kind", "thing_name", "condition")


def resolve_key(con, key):
    """The key that stands for this one today: a merged thing's key gives the survivor's key (Vision 3.7.4 rule 2). A key that
    was never merged, or is not known, comes back as it was."""
    r = con.execute("SELECT id FROM kg_things WHERE key=?", (key,)).fetchone()
    if r is None:
        return key
    s = survivor(con, r[0])
    return key if s == r[0] else con.execute("SELECT key FROM kg_things WHERE id=?", (s,)).fetchone()[0]


def current_facts(con, thing_key_=None, fact_key=None):
    thing_key_ = resolve_key(con, thing_key_) if thing_key_ else thing_key_
    sql, args = "SELECT %s FROM kg_current_facts WHERE 1=1" % ",".join(_FCOLS), []
    if thing_key_:
        sql, args = sql + " AND thing_key=?", args + [thing_key_]
    if fact_key:
        sql, args = sql + " AND fact_key=?", args + [fact_key]
    return [dict(zip(_FCOLS, r)) for r in con.execute(sql + " ORDER BY thing_key, fact_key, id", args)]


def current_links(con, thing_key_):
    thing_key_ = resolve_key(con, thing_key_)
    rows = con.execute("SELECT id, from_key, kind, to_key, role, who, certainty, answer_id, true_from, true_until "
                       "FROM kg_current_links WHERE from_key=? OR to_key=? ORDER BY id", (thing_key_, thing_key_))
    return [dict(zip(("id", "from_key", "kind", "to_key", "role", "who", "certainty", "answer_id", "true_from",
                      "true_until"), r)) for r in rows]


def about_sender(con, address):
    """His world on one sender: facts on the address, on its domain (and parent domains), and on any person/company
    linked to them. Each fact says who said it. Used by `gc who`."""
    addr = norm(address)
    if "<" in addr and ">" in addr:
        addr = addr[addr.index("<") + 1:addr.index(">")].strip()
    keys = [thing_key("address", addr)]
    if "@" in addr:
        parts = addr.rsplit("@", 1)[1].split(".")
        keys += [thing_key("domain", ".".join(parts[i:])) for i in range(len(parts) - 1)]
    out = {"address": addr, "keys": [], "facts": [], "links": []}
    seen = set()
    i = 0
    while i < len(keys):
        k = keys[i]
        i += 1
        if k in seen or thing_by_key(con, k) is None:
            continue
        seen.add(k)
        out["keys"].append(k)
        out["facts"] += current_facts(con, k)
        for l in current_links(con, k):
            if l["kind"] in ("address_of", "works_at", "belongs_to", "domain_of") and l["from_key"] == k:
                out["links"].append(l)
                keys.append(l["to_key"])
    return out


# ---- scores ---------------------------------------------------------------------------------------------
def set_score(con, subject_ref, signal, signal_version, value, reason):
    con.execute("INSERT INTO kg_scores(subject_ref,signal,signal_version,value,reason,computed_at) VALUES(?,?,?,?,?,?) "
                "ON CONFLICT(subject_ref,signal) DO UPDATE SET signal_version=excluded.signal_version, "
                "value=excluded.value, reason=excluded.reason, computed_at=excluded.computed_at",
                (subject_ref, signal, int(signal_version), value, reason, _ts()))


def clear_scores(con, signal):
    con.execute("DELETE FROM kg_scores WHERE signal=?", (signal,))


def scores_for(con, subject_ref):
    rows = con.execute("SELECT signal, signal_version, value, reason, computed_at FROM kg_scores WHERE subject_ref=? "
                       "ORDER BY signal", (subject_ref,))
    return [dict(zip(("signal", "signal_version", "value", "reason", "computed_at"), r)) for r in rows]


# ---- copy today's tables in (who='code', source 'legacy'; idempotent) ------------------------------------
def _lfact(con, tid, key, value, ref, certainty="likely"):
    if value is None or str(value).strip() == "":
        return
    value = str(value)
    hit = con.execute("SELECT 1 FROM kg_facts WHERE thing_id=? AND fact_key=? AND value=? AND source_ref=? "
                      "AND source_kind='legacy'", (tid, key, value, ref)).fetchone()
    if not hit:
        assert_fact(con, tid, key, value, "code", certainty, "legacy", ref)


def _llink(con, a, kind, b, ref, true_from=None, true_until=None, role=None):
    hit = con.execute("SELECT 1 FROM kg_links WHERE from_id=? AND kind=? AND to_id=? AND source_ref=? AND source_kind='legacy'",
                      (a, kind, b, ref)).fetchone()
    if not hit:
        add_link(con, a, kind, b, "code", "likely", "legacy", ref, true_from=true_from, true_until=true_until, role=role)


def copy_legacy(con):
    """Copy today's people, addresses, circles, members, rules, exceptions, facts, keywords, canon and projects into the
    graph, effective values only (override wins). Old tables are not touched. Safe to re-run. Returns counts."""
    n = {}
    pmap, cmap, rmap = {}, {}, {}
    for pid, label, tier in con.execute("SELECT p.id, p.label, v.tier FROM people p JOIN v_people v ON v.id=p.id "
                                        "WHERE p.status='active' ORDER BY p.id").fetchall():
        t = thing(con, "person", label or "person %d" % pid, legacy_ref="people:%d" % pid, key="person:legacy-%d" % pid)
        pmap[pid] = t
        _lfact(con, t, "tier", tier, "people:%d" % pid)
    n["people"] = len(pmap)
    k = 0
    for aid, addr, pid in con.execute("SELECT a.id, a.address, v.person_id FROM addresses a JOIN v_addresses v ON v.id=a.id "
                                      "WHERE a.status='active' ORDER BY a.id").fetchall():
        t = thing(con, "address", addr, legacy_ref="addresses:%d" % aid)
        if pid is not None and pid in pmap:
            _llink(con, t, "address_of", pmap[pid], "addresses:%d" % aid)
        k += 1
    n["addresses"] = k
    for cid, name, kind, dom in con.execute("SELECT c.id, c.name, v.kind, v.domain FROM circles c JOIN v_circles v ON v.id=c.id "
                                            "WHERE c.status='active' ORDER BY c.id").fetchall():
        try:
            old = con.execute("SELECT merged_into FROM kg_things WHERE key=?", (thing_key("circle", name),)).fetchone()
        except sqlite3.OperationalError:
            old = None
        if old and old[0] is not None:
            continue        # already became an organization (migration 021 / org_moves): the old circle is history now
        t = thing(con, "circle", name, legacy_ref="circles:%d" % cid)
        cmap[cid] = t
        _lfact(con, t, "circle_kind", kind, "circles:%d" % cid)
        _lfact(con, t, "domain", dom, "circles:%d" % cid)
    n["circles"] = len(cmap)
    k = 0
    for mid, cid, pid, role, vf, vu in con.execute(
            "SELECT m.id, v.circle_id, v.person_id, v.role, v.valid_from, v.valid_until FROM circle_members m "
            "JOIN v_circle_members v ON v.id=m.id WHERE m.status='active' ORDER BY m.id").fetchall():
        if cid in cmap and pid in pmap:
            _llink(con, pmap[pid], "member_of", cmap[cid], "circle_members:%d" % mid, vf, vu, role)
            k += 1
    n["members"] = k
    for r in con.execute("SELECT id, match_kind, match_value, subject_glob, kind_label, need, domain, folder, shelf_days, "
                         "shelf_anchor, status FROM v_rules_v1 ORDER BY id").fetchall():
        rid, mk, mv, glob = r[0], r[1], r[2], r[3] or ""
        ref = "rules:%d" % rid
        t = thing(con, "rule", "%s %s %s" % (mk, mv, glob), legacy_ref=ref, key="rule:%s:%s:%s" % (mk, mv, glob))
        rmap[rid] = t
        _llink(con, t, "applies_to", thing(con, mk, mv), ref)
        for key, val in (("match_kind", mk), ("subject_glob", glob), ("kind_label", r[4]), ("need", r[5]), ("domain", r[6]),
                         ("folder", r[7]), ("shelf_days", r[8]), ("shelf_anchor", r[9]), ("rule_status", r[10])):
            _lfact(con, t, key, val, ref)
    n["rules"] = len(rmap)
    k = 0
    for eid, rid, word, need in con.execute("SELECT e.id, v.rule_id, v.word, v.need FROM rule_exceptions e "
                                            "JOIN v_rule_exceptions v ON v.id=e.id WHERE e.status='active' ORDER BY e.id").fetchall():
        if rid in rmap:
            _lfact(con, rmap[rid], "exception", "%s=%s" % (word, need), "rule_exceptions:%d" % eid)
            k += 1
    n["exceptions"] = k
    world = thing(con, "world", "world")
    k = 0
    for fid, sk, sid, key, val in con.execute("SELECT f.id, v.subject_kind, v.subject_id, v.fact_key, v.value FROM facts f "
                                              "JOIN v_facts v ON v.id=f.id WHERE f.status='active' ORDER BY f.id").fetchall():
        tid = pmap.get(sid) if sk == "person" else rmap.get(sid) if sk == "rule" else world
        if tid is not None and val is not None:
            _lfact(con, tid, "legacy_fact", "%s=%s" % (key, val), "facts:%d" % fid)
            k += 1
    n["facts"] = k
    k = 0
    for kid, lst, phrase in con.execute("SELECT id, list_name, phrase FROM v_keywords ORDER BY id").fetchall():
        _lfact(con, world, "keyword", "%s=%s" % (lst, phrase), "keywords:%d" % kid)
        k += 1
    n["keywords"] = k
    k = 0
    for cfid, cat, ent, detail, dom, status in con.execute(
            "SELECT id, category, entity, detail, domain, status FROM v_canon_facts WHERE status<>'retired' ORDER BY id").fetchall():
        _lfact(con, world, "canon", "%s|%s|%s|%s|%s" % (cat, ent, detail or "", dom or "", status), "canon_facts:%d" % cfid)
        k += 1
    n["canon"] = k
    k = 0
    for pj in con.execute("SELECT id, circle_id, name, due_on, status FROM v_projects ORDER BY id").fetchall():
        t = thing(con, "project", pj[2] or "project %d" % pj[0], legacy_ref="projects:%d" % pj[0], key="project:legacy-%d" % pj[0])
        if pj[1] in cmap:
            _llink(con, t, "project_of", cmap[pj[1]], "projects:%d" % pj[0])
        _lfact(con, t, "life_fact", "due_on=%s;status=%s" % (pj[3], pj[4]), "projects:%d" % pj[0])
        k += 1
    n["projects"] = k
    return n


def legacy_equivalence(con):
    """Rebuild today's effective people / addresses / circles / members / rules / exceptions / facts / keywords from the
    graph's legacy copies and compare with the legacy views. Returns {table: (missing_in_graph, extra_in_graph)}; all
    empty means the new shape reproduces today's rules and people exactly."""
    def lf(key, ref_like):
        return {(r[0], r[1]) for r in con.execute(
            "SELECT source_ref, value FROM kg_facts WHERE fact_key=? AND source_kind='legacy' AND source_ref LIKE ?",
            (key, ref_like))}

    def val(facts, ref):
        for r, v in facts:
            if r == ref:
                return v
        return None

    out = {}
    tier = lf("tier", "people:%")
    legacy = {(r[0], r[1] or "person %d" % r[0], r[2]) for r in con.execute(
        "SELECT p.id, p.label, v.tier FROM people p JOIN v_people v ON v.id=p.id WHERE p.status='active'")}
    graph = {(int(t[0].split(":")[1]), t[1], val(tier, t[0])) for t in con.execute(
        "SELECT legacy_ref, name FROM kg_things WHERE kind='person' AND legacy_ref LIKE 'people:%'")}
    out["people"] = (legacy - graph, graph - legacy)
    legacy = {(r[0], r[1]) for r in con.execute(
        "SELECT a.address, v.person_id FROM addresses a JOIN v_addresses v ON v.id=a.id WHERE a.status='active'")}
    graph = set()
    for addr, ref in con.execute("SELECT name, legacy_ref FROM kg_things WHERE kind='address' AND legacy_ref LIKE 'addresses:%'").fetchall():
        p = con.execute("SELECT b.legacy_ref FROM kg_links l JOIN kg_things b ON b.id=l.to_id "
                        "WHERE l.source_ref=? AND l.kind='address_of' AND l.source_kind='legacy'", (ref,)).fetchone()
        graph.add((addr, int(p[0].split(":")[1]) if p else None))
    out["addresses"] = (legacy - graph, graph - legacy)
    ck, cd = lf("circle_kind", "circles:%"), lf("domain", "circles:%")
    legacy = {tuple(r) for r in con.execute(
        "SELECT c.name, v.kind, v.domain FROM circles c JOIN v_circles v ON v.id=c.id WHERE c.status='active'")}
    graph = {(t[0], val(ck, t[1]), val(cd, t[1])) for t in con.execute(
        "SELECT name, legacy_ref FROM kg_things WHERE kind='circle' AND legacy_ref LIKE 'circles:%'")}
    out["circles"] = (legacy - graph, graph - legacy)
    legacy = {tuple(r) for r in con.execute(
        "SELECT v.circle_id, v.person_id, v.role, v.valid_from, v.valid_until FROM circle_members m "
        "JOIN v_circle_members v ON v.id=m.id WHERE m.status='active' "
        "AND v.circle_id IN (SELECT id FROM circles WHERE status='active') "
        "AND v.person_id IN (SELECT id FROM people WHERE status='active')")}
    graph = {(int(r[0].split(":")[1]), int(r[1].split(":")[1]), r[2], r[3], r[4]) for r in con.execute(
        "SELECT b.legacy_ref, a.legacy_ref, l.role, l.true_from, l.true_until FROM kg_links l "
        "JOIN kg_things a ON a.id=l.from_id JOIN kg_things b ON b.id=l.to_id "
        "WHERE l.kind='member_of' AND l.source_kind='legacy'")}
    out["members"] = (legacy - graph, graph - legacy)
    cols = ("match_kind", "subject_glob", "kind_label", "need", "domain", "folder", "shelf_days", "shelf_anchor", "rule_status")
    rf = {c: lf(c, "rules:%") for c in cols}
    legacy = {(str(r[0]), r[1], r[2], r[3] or "", r[4], r[5], r[6], r[7], None if r[8] is None else str(r[8]), r[9], r[10])
              for r in con.execute("SELECT id, match_kind, match_value, subject_glob, kind_label, need, domain, folder, "
                                   "shelf_days, shelf_anchor, status FROM v_rules_v1")}
    graph = set()
    for (ref,) in con.execute("SELECT legacy_ref FROM kg_things WHERE kind='rule' AND legacy_ref LIKE 'rules:%'").fetchall():
        tgt = con.execute("SELECT b.name FROM kg_links l JOIN kg_things b ON b.id=l.to_id "
                          "WHERE l.source_ref=? AND l.kind='applies_to' AND l.source_kind='legacy'", (ref,)).fetchone()
        v = {c: val(rf[c], ref) for c in cols}
        graph.add((ref.split(":")[1], v["match_kind"], tgt[0] if tgt else None, v["subject_glob"] or "", v["kind_label"],
                   v["need"], v["domain"], v["folder"], v["shelf_days"], v["shelf_anchor"], v["rule_status"]))
    out["rules"] = (legacy - graph, graph - legacy)
    legacy = {("rule_exceptions:%d" % r[0], "%s=%s" % (r[1], r[2])) for r in con.execute(
        "SELECT e.id, v.word, v.need FROM rule_exceptions e JOIN v_rule_exceptions v ON v.id=e.id "
        "JOIN rules r ON r.id=v.rule_id WHERE e.status='active'")}
    graph = lf("exception", "rule_exceptions:%")
    out["exceptions"] = (legacy - graph, graph - legacy)
    legacy = {("facts:%d" % r[0], "%s=%s" % (r[1], r[2])) for r in con.execute(
        "SELECT f.id, v.fact_key, v.value FROM facts f JOIN v_facts v ON v.id=f.id WHERE f.status='active' AND v.value IS NOT NULL AND "
        "(v.subject_kind='world' OR (v.subject_kind='person' AND v.subject_id IN (SELECT id FROM people WHERE status='active')) "
        "OR (v.subject_kind='rule' AND v.subject_id IN (SELECT id FROM rules)))")}
    graph = lf("legacy_fact", "facts:%")
    out["facts"] = (legacy - graph, graph - legacy)
    legacy = {("keywords:%d" % r[0], "%s=%s" % (r[1], r[2])) for r in con.execute("SELECT id, list_name, phrase FROM v_keywords")}
    graph = lf("keyword", "keywords:%")
    out["keywords"] = (legacy - graph, graph - legacy)
    return out


def source_refs_with_prefix(con, prefix):
    """Every fact/link source_ref starting with prefix, current or superseded (lets loaders skip rows already saved)."""
    like = prefix.replace("%", r"\%").replace("_", r"\_") + "%"
    rows = con.execute("SELECT source_ref FROM kg_facts WHERE source_ref LIKE ? ESCAPE '\\' UNION "
                       "SELECT source_ref FROM kg_links WHERE source_ref LIKE ? ESCAPE '\\'", (like, like))
    return {r[0] for r in rows}


# ---- confirmations: plan B2 step 6 (only his confirmations go back in) -----------------------------------------
# A DRAFT is a file, never the database: {"draft_id", "made_on", "suggestions": [...]}. Each suggestion is the machine's
# best guess, shaped like the decision it would become if he says yes:
#   {"id", "kind": fact|lean|rule_item, "question", "subject_kind", "subject_name", "fact_key", "value",
#    ["condition"], ["true_until"], ["basis"], and for rule_item: "rule_kind": topic|exception, "target_key"}
# He answers yes / no / later to each. record_decisions() writes ONLY the yeses (one kg_answers row, hence one dated fact,
# per decision; a rule_item yes is two: the link to what the rule is about, then the fact). Noes and laters live in the
# validated snapshot file and nowhere in the database. Answer -> his dated fact -> filter draft is three links
# (v_filter_spec is a view over his facts; migration 013).
DRAFT_ID_RE = re.compile(r"[A-Za-z0-9._-]{1,40}")        # every id pattern here is used with .fullmatch, never "$"
SUGGESTION_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,16}")
SUGGESTION_KINDS = ("fact", "lean", "rule_item")
RULE_KINDS = ("topic", "exception")
DECISIONS = ("yes", "no", "later")
ASKER_RE = re.compile(r"(owner-session|gc approve)(:[A-Za-z0-9._-]{1,40})?")   # the ALLOWLIST of human-facing surfaces; anything else is refused (fail closed)
RETIRE_VALUE = {"inbox": "undecided", "destination": "undecided", "lean": "undecided"}   # label retires with "not:<v>"


def _tag(draft_id, sid):
    return "draft:%s#%s" % (draft_id, sid)


def _ans_target(sug):
    """The list of (subject_kind, subject_name, fact_key, value) answers a suggestion becomes if he says yes."""
    if sug["kind"] == "rule_item":
        tkind, tname = sug["target_key"].split(":", 1)
        rname = "%s:%s:%s" % (sug["rule_kind"], tkind, norm(tname))   # kind included: topic:travel and label:travel never share a rule item
        return [("rule", rname, "link:applies_to", sug["target_key"]),
                ("rule", rname, sug["fact_key"], sug["value"])]
    return [(sug["subject_kind"], sug["subject_name"], sug["fact_key"], sug["value"])]


def validate_draft(con, draft):
    """Raise Refused unless the draft is well formed and every suggestion would be an allowed decision. Writes nothing."""
    if not isinstance(draft, dict) or not DRAFT_ID_RE.fullmatch(str(draft.get("draft_id", ""))):
        raise Refused("a draft needs a draft_id (1-40 of letters, digits, . _ -)")
    try:
        dt.date.fromisoformat(str(draft.get("made_on")))
    except ValueError:
        raise Refused("a draft needs made_on YYYY-MM-DD")
    sugs = draft.get("suggestions")
    if not isinstance(sugs, list):
        raise Refused("a draft needs a suggestions list")
    seen = set()
    for s in sugs:
        if not isinstance(s, dict) or not SUGGESTION_ID_RE.fullmatch(str(s.get("id", ""))):
            raise Refused("suggestion needs an id (1-16 of letters, digits, _ -): %r" % (s,))
        if s["id"] in seen:
            raise Refused("suggestion id %r appears twice" % s["id"])
        seen.add(s["id"])
        if s.get("kind") not in SUGGESTION_KINDS:
            raise Refused("suggestion %s: kind must be one of %s" % (s["id"], ", ".join(SUGGESTION_KINDS)))
        if not str(s.get("question", "")).strip():
            raise Refused("suggestion %s: needs the question to put to him" % s["id"])
        if _is_approval_text(s.get("question"), s.get("fact_key"), s.get("value")):
            raise Refused("suggestion %s: a draft can never carry an approval (approvals come only through approve_staged)" % s["id"])
        if s["kind"] == "lean" and s.get("fact_key") != "lean":
            raise Refused("suggestion %s: a lean suggestion carries fact_key 'lean'" % s["id"])
        if s["kind"] == "rule_item":
            if s.get("rule_kind") not in RULE_KINDS:
                raise Refused("suggestion %s: a rule item is only for a topic or an exception" % s["id"])
            tk = str(s.get("target_key", ""))
            if ":" not in tk:
                raise Refused("suggestion %s: rule item needs target_key '<kind>:<name>'" % s["id"])
            _check(con, "thing_kind", tk.split(":", 1)[0], "target kind")
            if s["rule_kind"] == "topic" and tk.split(":", 1)[0] != "topic":
                raise Refused("suggestion %s: a topic rule item points at a topic thing" % s["id"])
            if "subject_kind" in s and s["subject_kind"] not in (None, "rule"):
                raise Refused("suggestion %s: a rule item's subject is the rule item itself" % s["id"])
        for sk, sn, fk, val in _ans_target(s):
            if not sn or not str(sn).strip():
                raise Refused("suggestion %s: needs a subject" % s["id"])
            _check(con, "thing_kind", sk, "thing kind")
            if fk.startswith(LINK_PREFIX):
                continue
            check_fact(con, sk, fk, str(val).strip() if val is not None else val)


def _answers_say(con, answer_ids, targets):
    """True if these recorded answers say exactly what the suggestion's targets say (subject, fact key, value)."""
    if len(answer_ids) != len(targets):
        return False
    for aid, (sk, sn, fk, val) in zip(sorted(answer_ids), targets):
        a = con.execute("SELECT subject_key, fact_key, value FROM kg_answers WHERE id=?", (aid,)).fetchone()
        vv = thing_key(*str(val).split(":", 1)) if fk.startswith(LINK_PREFIX) else str(val).strip()
        if a is None or a[0] != thing_key(sk, sn) or a[1] != fk or a[2] != vv:
            return False
    return True


def _recorded(con, draft_id, sid):
    r = con.execute("SELECT id FROM kg_answers WHERE asked_by=? ORDER BY id", (_tag(draft_id, sid),)).fetchall()
    return [x[0] for x in r]


def list_suggestions(con, draft):
    """Plain rows for his session: id, kind, the question, what yes would record, and whether yes is already recorded."""
    validate_draft(con, draft)
    out = []
    for s in draft["suggestions"]:
        out.append({"id": s["id"], "kind": s["kind"], "question": s["question"], "basis": s.get("basis"),
                    "if_yes": [{"subject": "%s:%s" % (sk, norm(sn)), "fact_key": fk, "value": v,
                                "condition": s.get("condition")} for sk, sn, fk, v in _ans_target(s)],
                    "already_recorded": bool(_recorded(con, draft["draft_id"], s["id"]))})
    return out


def _digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def record_decisions(con, draft, decisions, said_on=None, who_asked="session"):
    """decisions: {suggestion id: {"decision": yes|no|later, "words": his words}}. Validates everything first (unknown
    id, bad decision, a yes with no words: refused, nothing written). Writes ONLY the yeses, through record_answer (the one
    door), dated said_on, tagged draft:<id>#<sid>. A yes already recorded is not written twice. Returns the validated
    snapshot (a dict for the caller to save): every suggestion with his decision; noes and laters are in it and NOT in the db.
    The caller owns the transaction."""
    validate_draft(con, draft)
    said_on = said_on or clock.today().isoformat()
    try:
        dt.date.fromisoformat(str(said_on))
    except ValueError:
        raise Refused("said_on must be YYYY-MM-DD")
    if not isinstance(decisions, dict):
        raise Refused("decisions must be a mapping of suggestion id to a decision")
    byid = {s["id"]: s for s in draft["suggestions"]}
    for sid, d in decisions.items():
        if sid not in byid:
            raise Refused("decision for %r: no such suggestion in this draft" % sid)
        if not isinstance(d, dict) or d.get("decision") not in DECISIONS:
            raise Refused("decision for %s must be one of %s" % (sid, ", ".join(DECISIONS)))
        if d["decision"] == "yes" and not str(d.get("words", "")).strip():
            raise Refused("decision for %s: a yes needs his words" % sid)
    for s in draft["suggestions"]:           # reusing a draft_id + suggestion id for something else is refused, never a silent no-write
        have = _recorded(con, draft["draft_id"], s["id"])
        if have and not _answers_say(con, have, _ans_target(s)):
            raise Refused("draft %s suggestion %s was already recorded for a different suggestion: use a new draft_id or id"
                          % (draft["draft_id"], s["id"]))
    rows = []
    for s in draft["suggestions"]:
        d = decisions.get(s["id"])
        dec = d["decision"] if d else "later"
        row = {"id": s["id"], "decision": dec, "answer_ids": []}
        if dec == "yes":
            row["answer_ids"] = _recorded(con, draft["draft_id"], s["id"])
            if not row["answer_ids"]:
                for sk, sn, fk, val in _ans_target(s):
                    r = record_answer(con, s["question"], d["words"], _tag(draft["draft_id"], s["id"]), said_on, sk, sn, fk,
                                      val, true_until=s.get("true_until"), words_kind=d.get("words_kind", "verbatim"),
                                      condition=s.get("condition") if not fk.startswith(LINK_PREFIX) else None)
                    row["answer_ids"].append(r["answer_id"])
        rows.append(row)
    pending = [r["id"] for r in rows if r["decision"] == "later"]
    snap = {"snapshot_version": 1, "draft_id": draft["draft_id"], "validated_on": said_on,
            "status": "partial" if pending else "validated", "pending": pending, "decisions": rows,
            "draft_digest": _digest(draft)}
    snap["digest"] = _digest({k: v for k, v in snap.items() if k != "digest"})
    return snap


def check_snapshot(con, draft, snap):
    """Errors (empty = valid) for a validated snapshot against its draft and the database: it is about this draft, every
    suggestion is accounted for exactly once, the digest holds, every yes has its answers in the db and they say what the
    suggestion said, and no no / later has an answer behind it from this draft."""
    errs = []
    if snap.get("draft_id") != draft.get("draft_id") or snap.get("draft_digest") != _digest(draft):
        errs.append("snapshot is not about this draft (draft changed after it was validated)")
    if snap.get("digest") != _digest({k: v for k, v in snap.items() if k != "digest"}):
        errs.append("snapshot digest does not hold (edited after validation)")
    byid = {s["id"]: s for s in draft["suggestions"]}
    ids = [r["id"] for r in snap.get("decisions", [])]
    if sorted(ids) != sorted(byid):
        errs.append("snapshot does not account for every suggestion exactly once")
    for r in snap.get("decisions", []):
        s = byid.get(r["id"])
        if s is None:
            continue
        have = _recorded(con, draft["draft_id"], r["id"])
        if r["decision"] == "yes":
            want = _ans_target(s)
            if len(have) != len(want) or sorted(have) != sorted(r["answer_ids"]):
                errs.append("suggestion %s: yes in the snapshot but its answer(s) are not in the database" % r["id"])
                continue
            for aid, (sk, sn, fk, val) in zip(sorted(have), want):
                a = con.execute("SELECT subject_key, fact_key, value FROM kg_answers WHERE id=?", (aid,)).fetchone()
                vv = thing_key(*str(val).split(":", 1)) if fk.startswith(LINK_PREFIX) else str(val).strip()
                if a is None or a[0] != thing_key(sk, sn) or a[1] != fk or a[2] != vv:
                    errs.append("suggestion %s: the recorded answer does not say what was suggested" % r["id"])
        elif have:
            errs.append("suggestion %s: %s in the snapshot but the database holds an answer for it" % (r["id"], r["decision"]))
    return errs


def check_unconfirmed(con):
    """Everything in the database that claims to be his confirmation but is not, plus guesses sitting where only his word
    belongs. Returns a list of {"class", "fact_id", "why"}; ids only, never text. Classes:
      draft-unconfirmed  a fact or link tagged draft:<id>#<sid> with no matching answer of his
      owner-no-answer    who='owner' but the answer it cites is missing or says something else
      guess-in-db        an AI guess / research note on a key that drives filters or leans
    Pre-existing guess rows are real data; the caller reports them as a count, new ones as a failure."""
    out = []
    for fid, who, ref, tkey, fk, val, aid, ck in con.execute(
            "SELECT f.id, f.who, f.source_ref, t.key, f.fact_key, f.value, f.answer_id, f.condition FROM kg_current_facts f "
            "JOIN kg_things t ON t.id=f.thing_id"):
        a = con.execute("SELECT subject_key, fact_key, value, condition FROM kg_answers WHERE id=?", (aid,)).fetchone() if aid else None
        backed = a is not None and a[0] == tkey and a[1] == fk and a[2] == val and a[3] == ck
        if who == "owner" and not backed:
            out.append({"class": "owner-no-answer", "fact_id": fid, "why": "his fact has no matching answer"})
        if ref and str(ref).startswith("draft:") and not (who == "owner" and backed):
            out.append({"class": "draft-unconfirmed", "fact_id": fid, "why": "a draft suggestion in the database without his yes"})
        if who in ("ai_guess", "ai_research") and fk in ("label", "destination", "inbox", "lean"):
            out.append({"class": "guess-in-db", "fact_id": fid, "why": "%s on a key that drives filters or leans" % who})
    for (fid,) in con.execute("SELECT f.id FROM kg_current_facts f WHERE f.fact_key IN ('label','destination','inbox') AND f.value <> 'undecided' "
                              "AND f.who <> 'owner' AND f.source_kind = 'legacy' AND f.who = 'code' "
                              "AND f.id NOT IN (SELECT id FROM v_confirmed_filter_facts)"):
        out.append({"class": "legacy-no-rule", "fact_id": fid, "why": "labelled legacy but no rule row of the old table stands behind it"})
    for lid, ref, who in con.execute("SELECT id, source_ref, who FROM kg_current_links WHERE source_ref LIKE 'draft:%'"):
        if who != "owner":
            out.append({"class": "draft-unconfirmed", "fact_id": None, "why": "link #%d from a draft without his yes" % lid})
    return out


def retract_fact(con, fact_id, words, asked_by, said_on=None):
    """His retraction of one current fact, through the one door (so rebuild_from_answers replays it): a label is retired
    with 'not:<v>', inbox / destination / lean with 'undecided'. The fact leaves the current set, so the filter draft built
    from it disappears on the next read of v_filter_spec. Returns the answer id."""
    r = con.execute("SELECT f.thing_id, f.fact_key, f.value, f.condition, f.replaced_by, t.kind, t.name FROM kg_facts f "
                    "JOIN kg_things t ON t.id=f.thing_id WHERE f.id=?", (fact_id,)).fetchone()
    if r is None or r[4] is not None:
        raise Refused("fact #%s is not a current fact" % fact_id)
    _, fk, val, cond, _, tkind, tname = r
    if fk == "label":
        newv = NOT_PREFIX + val
    elif fk in RETIRE_VALUE:
        newv = RETIRE_VALUE[fk]
    else:
        raise Refused("retract_fact handles label / inbox / destination / lean facts, not %r" % fk)
    out = record_answer(con, "retract fact #%d (%s)" % (fact_id, fk), words, asked_by, said_on, tkind, tname, fk, newv,
                        condition=cond)
    return out["answer_id"]


def approve_staged(con, digest, words, asked_by, said_on=None):
    """His yes to ONE staged filter pair, named by its sha256. The only writer of an approval: it records his answer
    'approve staged filters sha256:<digest>' and the approval rule item's fact in one call. The database refuses an
    approval from anyone but him (trigger kg_facts_no_self_approval); this refuses a code-looking asker and empty words.
    A different digest (the staged pair changed) is a different approval, so a stale yes never covers new content."""
    if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
        raise Refused("approval needs the 64-hex sha256 of the staged pair")
    if not re.search(r"[A-Za-z0-9]", str(words)):
        raise Refused("an approval needs his words")
    if not ASKER_RE.fullmatch(str(asked_by)):
        raise Refused("approval asked_by %r is not a human-facing surface (allowed: owner-session[:name], gc approve[:name])" % (asked_by,))
    r = _record_answer(con, APPROVAL_Q + digest, words, asked_by, said_on, "rule", "approval:%s" % digest[:16],
                       "approved_digest", digest, words_kind="bundle_approval")
    return r["answer_id"]


def approved_digests(con):
    return {r[0]: r[1] for r in con.execute("SELECT digest, answer_id FROM v_approvals")}


def suggest_lean(sender, shown_level, his_level, points, reason="his correction of the shown score"):
    """A corrected score becomes a SUGGESTED lean (never a fact): he saw `shown_level` (low|medium|high) and says it should
    be `his_level`. Values come from the pinned thresholds in `points` (medium_at, high_at), no new numbers invented here.
    Returns one suggestion dict for a draft; writes nothing."""
    levels = ("low", "medium", "high")
    if shown_level not in levels or his_level not in levels:
        raise Refused("levels are low, medium or high")
    if shown_level == his_level:
        raise Refused("no correction: shown and his level are the same")
    med, high = float(points["medium_at"]), float(points["high_at"])
    up = levels.index(his_level) > levels.index(shown_level)
    value = ("floor:%g" % (high if his_level == "high" else med)) if up else \
            ("set:%g" % ((med if his_level == "medium" else med / 2)))
    kind, name = ("address", sender) if "@" in sender and not sender.startswith("@") else ("domain", sender)
    return {"id": "lean-" + hashlib.sha256((norm(sender) + his_level).encode()).hexdigest()[:8], "kind": "lean",
            "question": "You corrected %s from %s to %s: make that a standing lean (%s)?" % ("this sender", shown_level, his_level, value),
            "subject_kind": kind, "subject_name": name, "fact_key": "lean", "value": value,
            "basis": "corrected score: shown %s, he says %s; %s" % (shown_level, his_level, reason)}


def confirmed_leans(con):
    """His confirmed leans in the shape setup/leans.json 'senders' uses, with the reason from his own words. Only a lean
    fact that is his word AND backed by its answer counts."""
    out = {}
    for tkey, val, words in con.execute(
            "SELECT t.key, f.value, a.words FROM kg_current_facts f JOIN kg_things t ON t.id=f.thing_id "
            "JOIN kg_answers a ON a.id=f.answer_id AND (a.subject_key=t.key OR a.subject_key IN (SELECT old_key FROM org_moves WHERE new_key=t.key)) AND a.fact_key=f.fact_key AND a.value=f.value "
            "WHERE f.fact_key='lean' AND f.who='owner' AND f.value<>'undecided' AND t.kind='address'"):
        kind, _, num = val.partition(":")
        d = {"kind": kind, "reason": "his confirmation: " + words}
        if kind != "mute":
            d["value"] = float(num)
        out[tkey.split(":", 1)[1]] = d
    return out


# ---- merging two things (Vision 3.7.4 rule 2; plan 3.6) -----------------------------------------------------
# Only HIS word merges. The merge is a kg_answers row (fact_key 'merge_into', subject = the thing that retires, value = the
# survivor's key) plus its effect, in one savepoint: all of it or none of it. A rebuild replays the answer, so the merge is kept.
MERGE_KINDS = ("person", "organization")
MERGE_Q = "possible_duplicate"


def _kind_of_key(key):
    return str(key).split(":", 1)[0]


def _live_thing(con, key, what):
    t = thing_by_key(con, key)
    if t is None:
        raise Refused("%s %r is not a known thing" % (what, key))
    return t


def merge_things(con, loser_key, survivor_key, words, asked_by, said_on=None, question=None, queue_id=None):
    """Merge `loser_key` into `survivor_key` on HIS word. Refused (nothing written) unless: words are given; both things exist, are
    the same kind, a person or an organization, not the same thing, and the loser is not already merged and is not person:me.
    One savepoint: the answer row, every current link and fact re-pointed (old rows kept as history), merged_into + retired_at.
    Any failure undoes all of it. Returns {answer_id, moved_facts, moved_links, kept_facts, retired_links}."""
    if words is None or not str(words).strip():
        raise Refused("a merge needs his own words (a merge is only ever his answer)")
    if asked_by is None or not str(asked_by).strip():
        raise Refused("an answer needs asked_by")
    said_on = said_on or clock.today().isoformat()
    try:
        dt.date.fromisoformat(str(said_on))
    except ValueError:
        raise Refused("said_on must be YYYY-MM-DD, got %r" % (said_on,))
    loser_key, survivor_key = thing_key(*str(loser_key).split(":", 1)), thing_key(*str(survivor_key).split(":", 1))
    lo = _live_thing(con, loser_key, "the thing to retire")
    sv = _live_thing(con, survivor_key, "the thing to keep")
    sv_id = survivor(con, sv["id"])            # keep pointing at whoever stands for it today
    sv = dict(zip(("id", "kind", "key", "name", "legacy_ref"), con.execute("SELECT id, kind, key, name, legacy_ref FROM kg_things WHERE id=?", (sv_id,)).fetchone()))
    if lo["kind"] not in MERGE_KINDS or lo["kind"] != sv["kind"]:
        raise Refused("only two people, or two organizations, can be merged (got %s and %s)" % (lo["kind"], sv["kind"]))
    if lo["id"] == sv["id"]:
        raise Refused("a thing cannot be merged into itself")
    if lo["key"] == "person:me":
        raise Refused("person:me is never retired")
    if survivor(con, lo["id"]) != lo["id"]:
        raise Refused("%s is already merged into %s" % (lo["key"], resolve_key(con, lo["key"])))
    sp = "merge_%d" % lo["id"]
    con.execute("SAVEPOINT %s" % sp)
    try:
        aid = con.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,"
                          "queue_id,recorded_at,words_kind) VALUES(?,?,?,?,?,?,?,?,?,?,?,'verbatim')",
                          (question or "Are %s and %s the same?" % (lo["name"], sv["name"]), str(words), str(asked_by).strip(),
                           str(said_on), lo["key"], lo["kind"], lo["name"], "merge_into", sv["key"], queue_id, _ts())).lastrowid
        row = dict(zip(_ACOLS, con.execute("SELECT %s FROM kg_answers WHERE id=?" % ",".join(_ACOLS), (aid,)).fetchone()))
        res = _do_merge(con, row, detail=True)
        if queue_id is not None:
            con.execute("UPDATE queue SET status='answered', answered_at=?, answer=? WHERE id=? AND status='open'",
                        (_ts(), str(words), queue_id))
        con.execute("RELEASE %s" % sp)
    except BaseException:
        con.execute("ROLLBACK TO %s" % sp)
        con.execute("RELEASE %s" % sp)
        raise
    res["answer_id"] = aid
    return res


def _make_thing_from_record(con, key, name):
    kind = _kind_of_key(key)
    return thing(con, kind, name or key.split(":", 1)[1], created_by="code", key=key)


def _do_merge(con, a, detail=False):
    """Apply one merge_into answer (used live and by the rebuild replay). Returns the loser's id (or the counts when detail)."""
    lo_key, sv_key = a["subject_key"], a["value"]
    lo = thing_by_key(con, lo_key)
    lo_id = lo["id"] if lo else _make_thing_from_record(con, lo_key, a["subject_name"])
    sv_row = thing_by_key(con, sv_key)
    sv_id = survivor(con, sv_row["id"] if sv_row else _make_thing_from_record(con, sv_key, None))
    out = {"moved_facts": 0, "moved_links": 0, "kept_facts": 0, "retired_links": 0}
    if sv_id == lo_id or survivor(con, lo_id) != lo_id:
        return out if detail else lo_id          # a replay of something already in place
    X = a["id"]
    # ---- facts
    for fid, key, val, who, cer, sk, sref, aid, tf, tu, cond in con.execute(
            "SELECT id, fact_key, value, who, certainty, source_kind, source_ref, answer_id, true_from, true_until, condition "
            "FROM kg_facts WHERE thing_id=? AND replaced_by IS NULL ORDER BY id", (lo_id,)).fetchall():
        sql = "SELECT id, who FROM kg_facts WHERE thing_id=? AND fact_key=? AND replaced_by IS NULL AND condition IS ?"
        args = [sv_id, key, cond]
        if key in MULTI:
            sql, args = sql + " AND value=?", args + [val]
        cur = con.execute(sql, args).fetchone()
        if cur is not None and not (who == "owner" and cur[1] != "owner" and key not in MULTI):
            # the survivor already says this (or says its own thing about a one-answer key): the survivor's stays; this row is kept as history
            con.execute("UPDATE kg_facts SET replaced_by=?, merge_answer_id=? WHERE id=?", (cur[0], X, fid))
            out["kept_facts"] += 1
            continue
        new = assert_fact(con, sv_id, key, val, who, cer, sk, sref, aid, tf, tu, cond)
        con.execute("UPDATE kg_facts SET replaced_by=?, merge_answer_id=? WHERE id=?", (new, X, fid))
        con.execute("UPDATE kg_facts SET merge_answer_id=? WHERE id=?", (X, new))
        out["moved_facts"] += 1
    # ---- links
    for lid, f, kind, t, role, who, cer, sk, sref, aid, tf, tu in con.execute(
            "SELECT id, from_id, kind, to_id, role, who, certainty, source_kind, source_ref, answer_id, true_from, true_until "
            "FROM kg_links WHERE (from_id=? OR to_id=?) AND replaced_by IS NULL ORDER BY id", (lo_id, lo_id)).fetchall():
        nf, nt = (sv_id if f == lo_id else f), (sv_id if t == lo_id else t)
        nf, nt = survivor(con, nf), survivor(con, nt)
        if nf == nt or (who != "owner" and _is_placement(con, kind, nt)):
            # a line between the two themselves, or a placement the code wrote (placement is his word): kept as history, not carried
            con.execute("UPDATE kg_links SET replaced_by=id, merge_answer_id=? WHERE id=?", (X, lid))
            out["retired_links"] += 1
            continue
        new = add_link(con, nf, kind, nt, who, cer, sk, sref, aid, tf, tu, role)
        con.execute("UPDATE kg_links SET replaced_by=?, merge_answer_id=? WHERE id=?", (new, X, lid))
        con.execute("UPDATE kg_links SET merge_answer_id=? WHERE id=?", (X, new))
        out["moved_links"] += 1
    con.execute("UPDATE kg_things SET merged_into=?, retired_at=? WHERE id=?", (sv_id, _ts(), lo_id))
    return out if detail else lo_id


def propose_merge(con, keep_key, other_key, why, matters=False):
    """Code may only ASK. A suspected duplicate becomes one open question for him (queue kind possible_duplicate), never a merge.
    Tilt to drop: unless it matters (`matters` true) nothing is asked. Asked once per pair. Returns the queue id or None."""
    if not matters:
        return None
    a, b = resolve_key(con, keep_key), resolve_key(con, other_key)
    if a == b:
        return None
    ref = "%s|%s" % (a, b)
    pair = (ref, "%s|%s" % (b, a))
    if con.execute("SELECT 1 FROM queue WHERE kind=? AND subject_ref IN (?,?)", (MERGE_Q,) + pair).fetchone():
        return None
    q = ('Are "%s" and "%s" the same %s? %s If yes, I would keep the first and fold the second into it; nothing changes until you say so.'
         % (a.split(":", 1)[1], b.split(":", 1)[1], _kind_of_key(a), str(why or "").strip()))
    return con.execute("INSERT INTO queue(kind, subject_ref, question, proposed_answer, status, created_at) VALUES(?,?,?,NULL,'open',?)",
                       (MERGE_Q, ref, q.replace("  ", " "), _ts())).lastrowid


def unmerge_things(con, loser_key, words, asked_by, said_on=None, question=None):
    """Undo a merge, from the record, on HIS word: the retired thing comes back, its old rows are current again, the rows the merge
    wrote on the survivor are retired (kept). The un-merge is itself an answer, so a rebuild replays merge then un-merge.
    Refused if the thing was never merged by an answer, or its survivor was itself merged since (undo that one first)."""
    if words is None or not str(words).strip():
        raise Refused("an un-merge needs his own words")
    said_on = said_on or clock.today().isoformat()
    loser_key = thing_key(*str(loser_key).split(":", 1))
    lo = _live_thing(con, loser_key, "the merged thing")
    m = _last_merge(con, lo["key"])
    if m is None or survivor(con, lo["id"]) == lo["id"]:
        raise Refused("%s is not merged by an answer: nothing to undo" % lo["key"])
    sv = thing_by_key(con, m["value"])
    if survivor(con, sv["id"]) != sv["id"]:
        raise Refused("%s was itself merged since: undo that merge first" % sv["key"])
    sp = "unmerge_%d" % lo["id"]
    con.execute("SAVEPOINT %s" % sp)
    try:
        aid = con.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,subject_key,subject_kind,subject_name,fact_key,value,"
                          "recorded_at,words_kind) VALUES(?,?,?,?,?,?,?,?,?,?,'verbatim')",
                          (question or "Undo the merge of %s into %s" % (lo["name"], sv["name"]), str(words), str(asked_by).strip(),
                           str(said_on), lo["key"], lo["kind"], lo["name"], "unmerge", sv["key"], _ts())).lastrowid
        row = dict(zip(_ACOLS, con.execute("SELECT %s FROM kg_answers WHERE id=?" % ",".join(_ACOLS), (aid,)).fetchone()))
        _do_unmerge(con, row)
        con.execute("RELEASE %s" % sp)
    except BaseException:
        con.execute("ROLLBACK TO %s" % sp)
        con.execute("RELEASE %s" % sp)
        raise
    return {"answer_id": aid}


def _last_merge(con, key, before_id=None):
    """The latest merge_into answer about this key that no later unmerge answer has undone (None if there is none)."""
    sql = "SELECT id, fact_key, value, subject_name FROM kg_answers WHERE subject_key=? AND fact_key IN ('merge_into','unmerge')"
    args = [key]
    if before_id:
        sql, args = sql + " AND id<?", args + [before_id]
    rows = con.execute(sql + " ORDER BY id DESC LIMIT 1", args).fetchall()
    if rows and rows[0][1] == "merge_into":
        return {"id": rows[0][0], "value": rows[0][2]}
    return None


def _do_unmerge(con, a):
    lo = thing_by_key(con, a["subject_key"])
    m = _last_merge(con, a["subject_key"], before_id=a["id"])
    if lo is None or m is None or survivor(con, lo["id"]) == lo["id"]:
        return lo["id"] if lo else None           # replay of something not (or no longer) in place
    X = m["id"]
    sv_id = survivor(con, thing_by_key(con, m["value"])["id"])
    lo_id = lo["id"]
    # a new row the merge wrote on the survivor ends (it points at itself, kept); rows it had replaced there come back if it was still current
    new_rows = [("kg_facts", r) for r in con.execute(
        "SELECT id, replaced_by FROM kg_facts WHERE merge_answer_id=? AND thing_id=? ORDER BY id", (X, sv_id)).fetchall()]
    new_rows += [("kg_links", r) for r in con.execute(
        "SELECT id, replaced_by FROM kg_links WHERE merge_answer_id=? AND from_id<>? AND to_id<>? ORDER BY id", (X, lo_id, lo_id)).fetchall()]
    for table, (rid, cur) in new_rows:
        if cur is None:
            con.execute("UPDATE %s SET replaced_by=id WHERE id=?" % table, (rid,))
            con.execute("UPDATE %s SET replaced_by=NULL WHERE replaced_by=? AND id<>? AND merge_answer_id IS NOT ?" % table, (rid, rid, X))
    # the retiring thing's own old rows are current again
    con.execute("UPDATE kg_facts SET replaced_by=NULL WHERE merge_answer_id=? AND thing_id=?", (X, lo_id))
    con.execute("UPDATE kg_links SET replaced_by=NULL WHERE merge_answer_id=? AND (from_id=? OR to_id=?)", (X, lo_id, lo_id))
    con.execute("UPDATE kg_things SET merged_into=NULL, retired_at=NULL WHERE id=?", (lo_id,))
    return lo_id

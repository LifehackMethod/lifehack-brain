#!/usr/bin/env python3
"""Phase 2 step 2.5: machine guesses out of the model (the owner's 2026-11-15 ruling: the database holds only
indisputable facts and what he has confirmed).

Every CURRENT fact or link that is a machine guess (who ai_guess / ai_research, or who code with certainty not sure)
ends in one bucket (default = DROP; his time is scarce):
  RETIRE_SUPERSEDED  he has since spoken on the same thing+key (or same link): superseded by his row. No question.
  DROP               D1 code can recompute it / it is not his to answer; D2 only he could answer but the person or
                     organization does not matter (under 10 items of standing, no current project); D3 an open question
                     about that thing already exists. Retired, no question.
  QUESTION           only he can answer AND it is about a person/organization that matters (also: an address/domain link
                     that one of his confirmed filters reads for its sender): retired AND one row put in the
                     existing `queue` (kind 'confirm-guess'), with the guess as the proposed answer.
  HELD_LEGACY        code rows copied from his old tables (source_kind legacy): NOT touched unless --include-legacy.
                     With --include-legacy they split: traces to HIS word (old row source starting with one of his session words, gc.json legacy_source_prefixes; his override, an approved
                     rule, a grade-file answer of his, a canon line) -> ALREADY_PRESENT (an owner row exists: mirror row retired) or CARRY_OVER (an owner copy is written,
                     provenance = old row ref + his answer; mirror row superseded by it). Purely machine-made -> the normal rules.
"Retire" is the model's own way (the same one assert_fact uses for a 'not:' row): replaced_by points at a successor, or
at the row itself when there is none. Nothing is deleted; the rows stay and show in the history.

  python3 retire_machine_guesses.py --db COPY            # dry run: counts + 10 example ids per bucket
  python3 retire_machine_guesses.py --db COPY --apply    # do it, one transaction
  add --include-legacy to also retire the carried-over copies of the old tables
Against the LIVE file (rig.db) --apply takes the shared database-writer lock (state/db-writer.lock, gcjobs.py protocol)
and refuses after 5 s if a live run holds it.
Never pass the live database without a fresh backup (sqlite .backup) -- this script refuses a db whose user_version is below 13.
"""
import argparse, os, sqlite3, sys, json, datetime as dt

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import gc_settings  # noqa: E402

GUESS_SQL = "(%s.who IN ('ai_guess','ai_research') OR (%s.who='code' AND %s.certainty<>'sure'))"   # machine-made, not sure
QKIND = "confirm-guess"
STANDING_MIN = 10                 # a sender with at least this many items in the intake has strong standing
PERSON_ORG_KINDS = ("person", "company", "organization", "circle", "address", "domain")
HUMAN_FACT_KEYS = ("role", "relationship", "tier", "importance", "note")   # only he can answer these
HUMAN_LINK_KINDS = ("works_at", "assistant_of", "member_of", "reports_to", "knows")

LINK_WORDS = {"works_at": "works at", "address_of": "is an address of", "domain_of": "is the domain of",
              "assistant_of": "is the assistant of", "part_of": "is part of", "member_of": "is a member of",
              "reports_to": "reports to", "involves": "involves", "knows": "knows"}


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _matters(con, tid):
    """Does this thing matter to him? A person or organization with strong sender standing (>= STANDING_MIN items from its
    addresses or domains) or tied to a current project. Read only."""
    kind = con.execute("SELECT kind FROM kg_things WHERE id=?", (tid,)).fetchone()[0]
    if kind not in PERSON_ORG_KINDS:
        return False
    if con.execute("SELECT 1 FROM kg_current_links l JOIN kg_things p ON p.id=CASE WHEN l.from_id=? THEN l.to_id ELSE l.from_id END "
                   "WHERE (l.from_id=? OR l.to_id=?) AND p.kind='project' LIMIT 1", (tid, tid, tid)).fetchone():
        return True
    for (snd,) in con.execute("SELECT sender FROM v_thing_senders WHERE thing_id=?", (tid,)).fetchall():
        if snd is None:
            continue
        n = con.execute("SELECT count(*) FROM items WHERE lower(person_address)=? OR (? LIKE '@%' AND lower(person_address) LIKE '%'||?)",
                        (snd.lower(), snd, snd.lower())).fetchone()[0]
        if n >= STANDING_MIN:
            return True
    return False


def owner_words():
    """The `who` words that mean his own word: 'owner' and the stored owner id (gc.json owner_id; older rows may carry it)."""
    return tuple(dict.fromkeys([gc_settings.owner_id(), "owner"]))


def _who_in(alias=""):
    """SQL fragment and its parameters: <alias>who IN (?, ?...) over owner_words()."""
    w = owner_words()
    return "%swho IN (%s)" % (alias, ",".join("?" * len(w))), w


def legacy_source_prefixes():
    """How an old-table row's `source` names one of his own sessions (gc.json legacy_source_prefixes; none = no such rows)."""
    return tuple(str(p) for p in (gc_settings.load("gc.json").get("legacy_source_prefixes") or []) if str(p))


def _from_his_session(r):
    src = r.get("source") or ""
    return any(src.startswith(p) for p in legacy_source_prefixes())
_FIELD_OVERRIDE = {   # (old table, mirror key) -> the old column that holds his explicit override
    ("people", "tier"): "tier_override", ("addresses", None): "person_id_override",
    ("circles", "circle_kind"): "kind_override", ("circles", "domain"): "domain_override",
    ("circle_members", None): "valid_until_override", ("rule_exceptions", None): "need_override",
    ("facts", None): "value_override", ("keywords", None): "active_override",
    ("rules", "need"): "need_override", ("rules", "domain"): "domain_override", ("rules", "folder"): "folder_override",
    ("rules", "shelf_days"): "shelf_days_override", ("rules", "shelf_anchor"): "shelf_anchor_override"}
_TABLES = ("people", "addresses", "circles", "circle_members", "rules", "rule_exceptions", "facts", "keywords", "canon_facts", "projects")


def _old_row(con, ref):
    """The old-table row a mirror row was copied from: (table, row dict) or (None, None)."""
    try:
        t, i = (ref or "").split(":", 1)
        i = int(i)
    except ValueError:
        return None, None
    if t not in _TABLES:
        return None, None
    cur = con.execute("SELECT * FROM %s WHERE id=?" % t, (i,))
    r = cur.fetchone()
    return (t, dict(zip([d[0] for d in cur.description], r))) if r else (None, None)


def his_word(con, ref, key):
    """Does this mirror row trace to HIS word? Yes when the old row's source is one of his sessions (legacy_source_prefixes), or the
    old column for this field holds his explicit override, or (rules) he approved the rule, or the old row cites an answer-log
    entry of his (a grade file: the grade is his, only the mapping to a person was done by code), or it is a canon line (canon
    in his notes is written only with his explicit approval, per the root canon file)."""
    t, r = _old_row(con, ref)
    if not r:
        return False, t, r
    if _from_his_session(r) or t == "canon_facts":
        return True, t, r
    col = _FIELD_OVERRIDE.get((t, key)) or _FIELD_OVERRIDE.get((t, None))
    if col and r.get(col) is not None:
        return True, t, r
    if t == "rules" and (r["status"] == "approved" or any(r.get(c) is not None for c in
                         ("need_override", "domain_override", "folder_override", "shelf_days_override", "shelf_anchor_override"))):
        return True, t, r
    if r.get("answer_id") and con.execute("SELECT 1 FROM answer_log WHERE id=? AND entry_kind<>'canon'", (r["answer_id"],)).fetchone():
        return True, t, r
    return False, t, r


import re as _re
_FULL_NAME = _re.compile(r"[A-Z][\w'.-]+( [A-Z][\w'.-]+)+")


def _mapping_uncertain(con, t, r):
    """A grade-file row that ties an address or a circle to a PERSON whose name is not a clear full name (a first name, a handle,
    a role in brackets): the grade stands, but the code's mapping to that person is uncertain, so it becomes a question."""
    if t not in ("addresses", "circle_members") or _from_his_session(r):
        return False
    pid = r.get("person_id") if t == "addresses" else r.get("person_id")
    lab = con.execute("SELECT label FROM people WHERE id=?", (pid,)).fetchone()
    return bool(lab) and not _FULL_NAME.fullmatch(lab[0] or "")


def _legacy_bucket(con, kind, row, key, thing_ids):
    """For a legacy mirror row: (bucket, rule, successor) when it traces to his word, else None (machine-made: normal rules)."""
    his, t, r = his_word(con, row["source_ref"], key)
    if not his:
        return None
    if kind == "kg_links" and _mapping_uncertain(con, t, r):
        return "QUESTION", "Q his grade stands, but the code's mapping to the person is uncertain: confirm the mapping", None
    if kind == "kg_facts":
        wsql, wp = _who_in()
        ph = con.execute("SELECT id FROM kg_facts WHERE replaced_by IS NULL AND " + wsql + " AND fact_key=? AND value=? "
                         "AND thing_id IN (%s) ORDER BY id LIMIT 1" % ",".join("?" * len(thing_ids)), (*wp, row["fact_key"], row["value"], *thing_ids)).fetchone()
    else:
        wsql, wp = _who_in()
        ph = con.execute("SELECT id FROM kg_links WHERE replaced_by IS NULL AND " + wsql + " AND from_id=? AND kind=? AND to_id=? "
                         "ORDER BY id LIMIT 1", (*wp, row["from_id"], row["kind"], row["to_id"])).fetchone()
    if ph:
        return "ALREADY_PRESENT", "A his word, an owner row for the same thing already exists", ph[0]
    return "CARRY_OVER", "C his word (old %s row %s, source %r): carried over as an owner row" % (t, r["id"], r.get("source")), None


def _answer_for(con, old_t, old_r, cache):
    """kg_answers id for a carry-over: his recorded words when the old row cites a non-canon answer_log entry (one kg_answers row
    per answer_log id, reused), otherwise a 'summary' answer naming the old row and its source."""
    import re
    aid = old_r.get("answer_id")
    al = con.execute("SELECT * FROM answer_log WHERE id=?", (aid,)).fetchone() if aid else None
    if al is not None:
        if ("al", aid) in cache:
            return cache[("al", aid)]
        ex = con.execute("SELECT id FROM kg_answers WHERE legacy_answer_log_id=? ORDER BY id LIMIT 1", (aid,)).fetchone()
        if ex:
            cache[("al", aid)] = ex[0]
            return ex[0]
        said = (al["answered_on"] or "")[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", said):
            m = re.search(r"\d{4}-\d{2}-\d{2}", old_r.get("source") or "")
            said = m.group(0) if m else "2026-11-13"
        new = con.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,legacy_answer_log_id,recorded_at,words_kind) VALUES(?,?,?,?,?,?,'verbatim')",
                          ("carried over from the old answer log: %s %s %s%s" % (al["source_file"], al["entry_kind"], al["subject_key"] or "",
                                                                                  (" (canon line from %s)" % old_r.get("source")) if al["entry_kind"] == "canon" else ""),
                           al["text_verbatim"], "step 2.5 legacy carry-over", said, aid, _now())).lastrowid
        cache[("al", aid)] = new
        return new
    k = (old_t, old_r["id"])
    if k in cache:
        return cache[k]
    import re as _re
    m = _re.search(r"\d{4}-\d{2}-\d{2}", old_r.get("source") or "")
    new = con.execute("INSERT INTO kg_answers(question,words,asked_by,said_on,recorded_at,words_kind) VALUES(?,?,?,?,?,'summary')",
                      ("carried over from old %s row %s" % (old_t, old_r["id"]),
                       "old %s row %s, source: %s" % (old_t, old_r["id"], old_r.get("source")), "step 2.5 legacy carry-over",
                       m.group(0) if m else "2026-11-13", _now())).lastrowid
    cache[k] = new
    return new


def _carry(con, c, cache):
    """Insert an owner copy of a mirror row (provenance: its old row's ref + the answer), then supersede the mirror row by it."""
    tbl = c["table"]
    row = con.execute("SELECT * FROM %s WHERE id=?" % tbl, (c["id"],)).fetchone()
    old_t, old_r = _old_row(con, row["source_ref"])
    aid = _answer_for(con, old_t, old_r, cache)
    con.execute("UPDATE %s SET replaced_by=id WHERE id=?" % tbl, (c["id"],))   # step aside first (one current link per pair)
    if tbl == "kg_facts":
        new = con.execute("INSERT INTO kg_facts(thing_id,fact_key,value,who,certainty,source_kind,source_ref,answer_id,true_from,true_until,created_at,condition) "
                          "VALUES(?,?,?,'owner','sure','legacy',?,?,?,?,?,?)", (row["thing_id"], row["fact_key"], row["value"], row["source_ref"], aid,
                                                                              row["true_from"], row["true_until"], _now(), row["condition"])).lastrowid
    else:
        new = con.execute("INSERT INTO kg_links(from_id,kind,to_id,role,who,certainty,source_kind,source_ref,answer_id,true_from,true_until,created_at) "
                          "VALUES(?,?,?,?,'owner','sure','legacy',?,?,?,?,?)", (row["from_id"], row["kind"], row["to_id"], row["role"], row["source_ref"], aid,
                                                                              row["true_from"], row["true_until"], _now())).lastrowid
    con.execute("UPDATE %s SET replaced_by=? WHERE id=?" % tbl, (new, c["id"]))
    return new


def classify(con, include_legacy=False):
    """-> list of dicts {table,id,bucket,rule,successor,key,kind}. Read only. include_legacy: also retire the carried-over
    copies of the old tables (source_kind='legacy'); by default they are HELD (see the result file)."""
    out = []
    def add(table, row, b, r, s, key, kind):
        out.append(dict(table=table, id=row["id"], bucket=b, rule=r, successor=s, key=key, kind=kind))
    for f in con.execute("SELECT f.*, t.kind tkind, t.key tkey FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id "
                         "WHERE f.replaced_by IS NULL AND " + GUESS_SQL % ("f", "f", "f") + " ORDER BY f.id"):
        wsql, wp = _who_in()
        his = con.execute("SELECT id FROM kg_facts WHERE thing_id=? AND fact_key=? AND " + wsql + " AND condition IS ? "
                          "ORDER BY id DESC LIMIT 1", (f["thing_id"], f["fact_key"], *wp, f["condition"])).fetchone()
        if f["source_kind"] == "legacy":
            if not include_legacy:
                add("kg_facts", f, "HELD_LEGACY", "H carried-over copy of an old table (held)", None, f["fact_key"], f["tkind"]); continue
            tids = [f["thing_id"]] + [r[0] for r in con.execute("SELECT to_id FROM kg_links WHERE from_id=? AND kind='applies_to' AND replaced_by IS NULL", (f["thing_id"],))]
            lb = _legacy_bucket(con, "kg_facts", f, f["fact_key"], tids)
            if lb:
                add("kg_facts", f, lb[0], lb[1], lb[2], f["fact_key"], f["tkind"]); continue
        if his:
            add("kg_facts", f, "RETIRE_SUPERSEDED", "R1 he has since spoken on the same thing+key", his[0], f["fact_key"], f["tkind"]); continue
        human = f["fact_key"] in HUMAN_FACT_KEYS and (f["fact_key"] != "note" or f["value"].startswith("research: not found"))
        if not human:
            add("kg_facts", f, "DROP", "D1 default: code can recompute it, or it is not his to answer (%s)" % f["fact_key"], None, f["fact_key"], f["tkind"])
        elif not _matters(con, f["thing_id"]):
            add("kg_facts", f, "DROP", "D2 only he could answer, but the %s is not a person/organization that matters (standing < %d, no current project)" % (f["tkind"], STANDING_MIN), None, f["fact_key"], f["tkind"])
        elif con.execute("SELECT 1 FROM queue WHERE status='open' AND subject_ref=?", (f["tkey"],)).fetchone():
            add("kg_facts", f, "DROP", "D3 an open question about this thing already exists", None, f["fact_key"], f["tkind"])
        else:
            add("kg_facts", f, "QUESTION", "Q only he can answer, about a person/organization that matters", None, f["fact_key"], f["tkind"])
    for l in con.execute("SELECT l.*, a.kind fk, b.kind tk, a.key akey FROM kg_links l JOIN kg_things a ON a.id=l.from_id "
                         "JOIN kg_things b ON b.id=l.to_id WHERE l.replaced_by IS NULL AND " + GUESS_SQL % ("l", "l", "l") + " ORDER BY l.id"):
        kind = "%s>%s" % (l["fk"], l["tk"])
        wsql, wp = _who_in()
        his = con.execute("SELECT id FROM kg_links WHERE from_id=? AND kind=? AND to_id=? AND " + wsql + " ORDER BY id DESC LIMIT 1",
                          (l["from_id"], l["kind"], l["to_id"], *wp)).fetchone()
        if l["source_kind"] == "legacy":
            if not include_legacy:
                add("kg_links", l, "HELD_LEGACY", "H carried-over copy of an old table (held)", None, l["kind"], kind); continue
            lb = _legacy_bucket(con, "kg_links", l, None, None)
            if lb:
                add("kg_links", l, lb[0], lb[1], lb[2], l["kind"], kind); continue
        if his:
            add("kg_links", l, "RETIRE_SUPERSEDED", "R1 he has since spoken on the same link", his[0], l["kind"], kind); continue
        feeds = l["kind"] in ("address_of", "domain_of") and con.execute(
            "SELECT 1 FROM v_confirmed_filter_facts WHERE thing_id=? LIMIT 1", (l["to_id"],)).fetchone()   # a filter of his reads this sender
        if l["kind"] not in HUMAN_LINK_KINDS and not feeds:
            add("kg_links", l, "DROP", "D1 default: code can recompute it (%s)" % l["kind"], None, l["kind"], kind)
        elif not feeds and not (_matters(con, l["from_id"]) or _matters(con, l["to_id"])):
            add("kg_links", l, "DROP", "D2 only he could answer, but neither end matters (standing < %d, no current project)" % STANDING_MIN, None, l["kind"], kind)
        elif con.execute("SELECT 1 FROM queue WHERE status='open' AND subject_ref=?", (l["akey"],)).fetchone():
            add("kg_links", l, "DROP", "D3 an open question about this thing already exists", None, l["kind"], kind)
        else:
            add("kg_links", l, "QUESTION", "Q only he can answer, about a person/organization that matters (or a sender one of his filters reads)", None, l["kind"], kind)
    return out


def _question(con, c):
    """(subject_ref, question, proposed_answer) for one QUESTION row, in plain words."""
    if c["table"] == "kg_facts":
        f = con.execute("SELECT f.fact_key,f.value,t.key,t.name FROM kg_facts f JOIN kg_things t ON t.id=f.thing_id WHERE f.id=?", (c["id"],)).fetchone()
        v = f["value"]
        if f["fact_key"] == "note" and v.startswith("research: not found"):
            q = v.split(":", 2)[2].strip() if v.count(":") >= 2 else v
            q = q.rsplit(" (", 1)[0].rstrip("?") + "?"
            return f["key"], q[:300], None
        return f["key"], ("I had guessed %s for \"%s\": %s. Is that right?" % (f["fact_key"].replace("_", " "), f["name"], v))[:400], v[:300]
    l = con.execute("SELECT l.kind,a.name an,a.key ak,b.name bn FROM kg_links l JOIN kg_things a ON a.id=l.from_id "
                    "JOIN kg_things b ON b.id=l.to_id WHERE l.id=?", (c["id"],)).fetchone()
    return l["ak"], "I had guessed that %s %s %s. Is that right?" % (l["an"], LINK_WORDS.get(l["kind"], l["kind"]), l["bn"]), "yes"


def apply(con, include_legacy=False, cache=None):
    """One transaction. Returns counts. cache: answers already on record, keyed as _answer_for keys them (the step 2.6 rebuild
    passes the carry-over answers it finds, so a replay reuses them instead of writing new ones)."""
    plan = [c for c in classify(con, include_legacy) if c["bucket"] != "HELD_LEGACY"]
    cnt = {"retired": 0, "questions": 0}
    con.execute("BEGIN IMMEDIATE")
    try:
        cache = {} if cache is None else cache
        for c in plan:
            if c["bucket"] == "CARRY_OVER":
                _carry(con, c, cache)
                cnt["carried"] = cnt.get("carried", 0) + 1
                continue
            # retire: successor if there is one, else the row itself (the model's own self-superseded convention)
            con.execute("UPDATE %s SET replaced_by=? WHERE id=? AND replaced_by IS NULL" % c["table"], (c["successor"] or c["id"], c["id"]))
            cnt["retired"] += 1
            if c["bucket"] == "QUESTION":
                ref, q, p = _question(con, c)
                dup = con.execute("SELECT 1 FROM queue WHERE subject_ref=? AND question=? AND status='open'", (ref, q)).fetchone()
                if not dup:
                    con.execute("INSERT INTO queue(kind,subject_ref,question,proposed_answer,status,created_at) VALUES(?,?,?,?,'open',?)",
                                (QKIND, ref, q, p, _now()))
                    cnt["questions"] += 1
        con.execute("INSERT INTO events(at,kind,detail) VALUES(?,?,?)", (_now(), "machine_guesses_retired",
                    "step 2.5: %d guesses retired, %d questions added (queue kind %s); rows kept, replaced_by set" % (cnt["retired"], cnt["questions"], QKIND)))
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    return cnt


LIVE_DB = gc_settings.db_path()
LOCK_WAIT_S = 5


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--include-legacy", action="store_true")
    a = ap.parse_args(argv)
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import gcjobs
    live = os.path.realpath(a.db) == os.path.realpath(LIVE_DB)
    lock = gcjobs.db_lock_path() if live and a.apply else None
    if lock and not gcjobs.lock_take(lock, wait_s=LOCK_WAIT_S, poll=1.0):
        sys.exit("refusing: the database-writer lock is held by a live run (%s)" % lock)
    try:
        import db   # the one front door (tests/test_front_door.py)
        con = db.connect(a.db, readonly=not a.apply)
        con.isolation_level = None
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        if con.execute("PRAGMA user_version").fetchone()[0] < 13:
            sys.exit("refusing: user_version is below 13")
        plan = classify(con, a.include_legacy)
        by = {}
        for c in plan:
            by.setdefault((c["bucket"], c["table"], c["rule"].split(" (")[0]), []).append(c)
        for k in sorted(by):
            print("%-18s %-9s %4d  %s\n    e.g. %s" % (k[0], k[1], len(by[k]), k[2], ", ".join("%s:%s" % (x["id"], x["key"]) for x in by[k][:10])))
        if a.apply:
            q0 = con.execute("SELECT count(*) FROM queue").fetchone()[0]
            r = apply(con, a.include_legacy)
            r["queue_before"], r["queue_after"] = q0, con.execute("SELECT count(*) FROM queue").fetchone()[0]
            print(json.dumps(r))
    finally:
        if lock:
            gcjobs.lock_release(lock)
    return 0


if __name__ == "__main__":
    sys.exit(main())

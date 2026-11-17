"""onboarding.py: Phase 3 step 3.10. The onboarding sitting, prepared from the model and recorded through the owner-answer door.

  python3 onboarding.py sheet  --db COPY --out SHEET.md     write the sheet (and SHEET.guesses.json beside it); changes nothing
  python3 onboarding.py answer --db COPY --guesses SHEET.guesses.json --file ANSWERS.json [--dry]
                                                            record his answers (each one through store_graph.record_answer)

The sheet is a list of QUESTIONS with a best guess pre-filled, so he confirms or corrects. A guess lives only in the sheet and its
.guesses.json sidecar. It is NEVER written to the database. Only an answer is: "ok" stores the guess he was shown as HIS word,
anything else stores what he wrote instead. A line never answered stores nothing. Levels (seniority) are never guessed.
Nothing here names a person or an organization: every name comes from the database, so any subscriber's data fills the same sheet.

ANSWERS.json:  {"said_on": "YYYY-MM-DD", "answers": [ one object per line he touched, "id" = the id printed on the sheet ]}
  person  P01   {"id","relationship","organization","role","importance","keep_in_touch_days"}   each "ok" | his own text | absent (= not answered)
                  organization: "none" says no organization; importance: high | normal | low
  boss    B1    {"id","reports_to": "<P id or person key>", "levels": {"<P id or key>": 1, "...": 2}}   (a number, or who they report to)
  sender  Q1    {"id","answer": "person"|"bot"|"ok"}  his word on what kind of sender the address is (sender_kind)
  weights W1    {"id","value": "ok" | "1.0,0.5,0.25"}   points for 1 level above him, 2 levels, 3 or more
  org     O01   {"id","type": "ok"|company|department|team|group, "part_of": "ok"|"none"|<O id or organization name>}
  held    H1    {"id","type": company|department|team|group|"ok"}
  dup     D1    {"id","answer": "yes"|"no"}  yes merges the second person into the first (sg.merge_things, his word); no records the no
  mapping M1    {"id","answer": "yes"|"no"|"<text>"}  (yes re-makes the link the old code guessed, as HIS word)"""
import argparse
import datetime as dt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import db  # noqa: E402
import store_graph as sg  # noqa: E402

TOP_N = 30
MUST_N = 10                    # the first ten are "must", the rest "if there is time"
MIN_STANDING_FRAC = 0.1        # of the standing scale (1 of the old 10; 0.4 of the live 4): below this and with fewer than SHARED_MIN shared meetings, a person does not matter here
SHARED_MIN = 2
FREE_MAIL = {"gmail", "googlemail", "yahoo", "ymail", "hotmail", "outlook", "live", "msn", "aol", "icloud", "me", "mac",
             "protonmail", "proton", "gmx", "comcast", "verizon", "att"}
LEVEL_WORDS = ("1", "2", "3_or_more")
PROPOSED_LEVEL_POINTS = (1.0, 0.5, 0.25)   # the coordinator's proposal (setup/leans.json _level_points); a number he can change
WEIGHTS_SUBJECT = ("topic", "level_points")
WEIGHTS_FACT = ("setting", "level_points")
QUESTION_N = 10               # the question marks the sheet carries (after dedupe, ranked): the sheet stays short
KEEP_N = MUST_N               # keep_in_touch_days is asked only for the 'must' people
ORG_TYPES = ("company", "department", "team", "group")
_FULL_NAME = re.compile(r"[A-Z][\w'.-]+( [A-Z][\w'.-]+)+")
BOSS_WORDS = re.compile(r"\b(boss|supervisor|reports? to|my manager|his manager|line manager)\b", re.I)
MAP_Q = re.compile(r"^I had guessed that (.+?) (is an address of|is a member of) (.+?)\. Is that right\?$")


# ---- reading the model (read only) -----------------------------------------------------------------------
def _one(con, sql, *a):
    r = con.execute(sql, a).fetchone()
    return r[0] if r else None


def _fact(con, tid, key):
    """(value, who) of the current fact, or (None, None)."""
    r = con.execute("SELECT value, who FROM kg_current_facts WHERE thing_id=? AND fact_key=? ORDER BY id DESC LIMIT 1", (tid, key)).fetchone()
    return (r[0], r[1]) if r else (None, None)


def _domain_label(addr):
    dom = addr.lower().partition("@")[2]
    parts = [p for p in dom.split(".") if p]
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "ac", "gov"):
        return parts[-3]
    return parts[-2] if len(parts) >= 2 else ""


def _alnum(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def _is_auto(addr):
    try:
        import store_events as se
        return bool(se.looks_automated(addr) or se.is_role_inbox(addr))
    except Exception:  # noqa: BLE001  (engine not importable: fall back to the plain name test)
        return bool(re.search(r"no-?reply|donotreply|notification|newsletter|mailer|bounce", addr.lower()))


def organizations(con):
    """[{key, name, type, type_who, parent_key, parent_name, members}] for live organizations."""
    out = []
    for tid, key, name in con.execute("SELECT id, key, name FROM kg_things WHERE kind='organization' AND merged_into IS NULL "
                                      "AND retired_at IS NULL ORDER BY name").fetchall():
        typ, who = _fact(con, tid, "org_type")
        par = con.execute("SELECT t.key, t.name FROM kg_current_links l JOIN kg_things t ON t.id=l.to_id WHERE l.from_id=? AND l.kind='part_of' "
                          "AND t.kind='organization' AND t.merged_into IS NULL LIMIT 1", (tid,)).fetchone()
        members = [r[0] for r in con.execute("SELECT p.name FROM kg_current_links l JOIN kg_things p ON p.id=l.from_id WHERE l.to_id=? "
                                             "AND l.kind='member_of' AND p.merged_into IS NULL ORDER BY p.name", (tid,))]
        out.append(dict(key=key, name=name, type=typ, type_who=who, parent_key=par[0] if par else None,
                        parent_name=par[1] if par else None, members=members))
    return out


def _org_guess_for(orgs, addrs, texts):
    """(org key or None, new-org name or None, why). Only a guess: a domain that matches an organization's name, then an
    organization's name written in what is already on file about the person."""
    labels = [(_domain_label(a), a) for a in addrs]
    for lab, a in labels:
        la = _alnum(lab)
        if len(la) < 3 or la in FREE_MAIL:
            continue
        for o in orgs:
            on = _alnum(o["name"])
            if len(on) >= 3 and (la in on or on in la):
                return o["key"], None, "their address ends @%s" % a.partition("@")[2]
    low = " ".join(texts).lower()
    for o in orgs:
        if len(o["name"]) >= 3 and re.search(r"\b%s\b" % re.escape(o["name"].lower()), low):
            return o["key"], None, "named in what is already on file"
    for lab, a in labels:
        la = _alnum(lab)
        if len(la) >= 3 and la not in FREE_MAIL:
            return None, lab, "their address ends @%s (no such organization on file yet)" % a.partition("@")[2]
    return None, None, ""


_LIVE = {}


def _live(con):
    """The live computed standing machinery (the same figure `gc who` shows, step 2.4): the mailbox, the setup and the clock. Built once per
    connection. None when it cannot be built (no setup files or no mailbox): then nobody has a standing, never the frozen old score."""
    k = id(con)
    if k not in _LIVE:
        try:
            import scorecard as sc
            import clock
            _LIVE.clear()
            _LIVE[k] = (sc, sc.Mailbox.load(con), sc.Config.load(), int(clock.now().timestamp() * 1000))
        except Exception:  # noqa: BLE001
            _LIVE[k] = None
    return _LIVE[k]


def _standing(con, tids):
    """Best live computed standing (0 to scale_max) over the addresses of these things."""
    lv = _live(con)
    if lv is None:
        return None
    sc, mb, cfg, now_ms = lv
    best = None
    for tid in tids:
        for (a,) in con.execute("SELECT DISTINCT sender FROM v_thing_senders WHERE thing_id=? AND sender IS NOT NULL", (tid,)).fetchall():
            st = sc.standing(mb, a, cfg, now_ms)["standing"]
            if st is not None and (best is None or st > best):
                best = st
    return best


def _scale(con):
    lv = _live(con)
    return float(lv[2].points["standing"]["scale_max"]) if lv else 10.0


def _high_at(con):
    """'matters: high' guess line: 80% of the standing scale (was 8 of 10 on the old frozen score)."""
    return 0.8 * _scale(con)


def people(con, orgs, n=TOP_N):
    """The people who matter, ranked by standing. One line per name (the same name on file twice is one line, the owner-made thing first)."""
    rows = con.execute("SELECT id, key, name, created_by FROM kg_things WHERE kind='person' AND merged_into IS NULL AND retired_at IS NULL "
                       "AND key<>'person:me' ORDER BY (created_by='owner') DESC, id").fetchall()
    groups = {}
    for r in rows:
        groups.setdefault(sg.norm(r[2]), []).append(r)
    cands = []
    for grp in groups.values():
        tids = [g[0] for g in grp]
        addrs = [a for tid in tids for (a,) in con.execute("SELECT sender FROM v_thing_senders WHERE thing_id=? AND sender IS NOT NULL", (tid,))]
        if addrs and all(_is_auto(a) for a in addrs):
            continue                                         # a bot or a role inbox is not a person
        if not addrs and re.search(r"no-?reply|notification", grp[0][2].lower()):
            continue
        events = []
        for tid in tids:
            events += con.execute("SELECT e.name, e.starts_at FROM kg_current_links l JOIN kg_things e ON e.id=l.from_id "
                                  "WHERE l.to_id=? AND l.kind='involves' AND e.kind='event' ORDER BY e.starts_at DESC", (tid,)).fetchall()
        shared = len(events)
        st = _standing(con, tids)
        has_word = any(_fact(con, t, k)[1] == "owner" for t in tids for k in ("relationship", "role", "tier", "importance", "note"))
        if not ((st or 0) >= MIN_STANDING_FRAC * _scale(con) or shared >= SHARED_MIN or has_word):
            continue                                         # someone who does not matter: left out
        cands.append(dict(tids=tids, grp=grp, addrs=addrs, st=st, shared=shared, events=events))
    cands.sort(key=lambda c: (-(c["st"] or 0), -c["shared"], c["grp"][0][2].lower()))
    out = []
    for c in cands[:n]:
        g = c["grp"][0]
        facts = {}
        for k in ("relationship", "role", "importance", "tier", "legacy_fact", "note"):
            for tid in c["tids"]:
                v, who = _fact(con, tid, k)
                if v:
                    facts.setdefault(k, (v, who))
        legacy_role = None
        for tid in c["tids"]:
            for (v,) in con.execute("SELECT value FROM kg_current_facts WHERE thing_id=? AND fact_key='legacy_fact' AND value LIKE 'role=%'", (tid,)):
                legacy_role = v[5:]
        his_rel = facts.get("relationship") if facts.get("relationship", (0, 0))[1] == "owner" else None
        his_role = facts.get("role") if facts.get("role", (0, 0))[1] == "owner" else None
        his_org = None
        for tid in c["tids"]:
            r = con.execute("SELECT t.key, t.name FROM kg_current_links l JOIN kg_things t ON t.id=l.to_id WHERE l.from_id=? AND l.kind='member_of' "
                            "AND l.who='owner' AND t.kind='organization' LIMIT 1", (tid,)).fetchone()
            if r:
                his_org = r
        texts = [v for v, _w in facts.values()] + ([legacy_role] if legacy_role else [])
        okey, newname, why = _org_guess_for(orgs, c["addrs"], texts)
        ev_titles = []
        for nm, _s in c["events"]:
            if nm and nm not in ev_titles:
                ev_titles.append(nm)
        # guesses (shown as guesses; none is stored)
        if legacy_role:
            rel_guess, rel_why = legacy_role.strip(), "the old notes said this"
        elif ev_titles:
            rel_guess, rel_why = "someone you meet with (%s)" % "; ".join(t[:40] for t in ev_titles[:2]), "shared meetings"
        else:
            rel_guess, rel_why = "someone you correspond with", "two-way mail"
        role_guess = re.split(r"[;(]", legacy_role)[0].strip() if legacy_role else None
        st = c["st"]
        imp_guess = "high" if (st or 0) >= _high_at(con) else "normal"
        out.append(dict(
            key=g[1], name=g[2], also=[x[1] for x in c["grp"][1:]], standing=st, shared=c["shared"],
            last_event=(c["events"][0][1] if c["events"] else None),
            on_file=dict(relationship=his_rel[0] if his_rel else None, role=his_role[0] if his_role else None,
                         organization=his_org[1] if his_org else None,
                         importance=facts["importance"][0] if facts.get("importance", (0, 0))[1] == "owner" else None),
            guess=dict(relationship=rel_guess, relationship_why=rel_why, role=role_guess,
                       organization=okey, organization_new=newname, organization_why=why, importance=imp_guess)))
    return out


def duplicate_pairs(con, n=8):
    """Likely duplicate people, as questions only: two live people who share a name, or share an address. keep = his own named person
    (owner-made) before a code-made one; fold = the legacy-N or later one. Ranked by standing. Code may only propose: nothing is merged here."""
    rows = con.execute("SELECT id, key, name, created_by FROM kg_things WHERE kind='person' AND merged_into IS NULL AND retired_at IS NULL "
                       "AND key<>'person:me' ORDER BY id").fetchall()
    by_id = {r[0]: r for r in rows}
    pairs = {}
    names = {}
    for r in rows:
        names.setdefault(sg.norm(r[2]), []).append(r[0])
    for ids_ in names.values():
        for j in ids_[1:]:
            pairs[(ids_[0], j)] = "same name"
    byaddr = {}
    for fid, tid in con.execute("SELECT l.from_id, l.to_id FROM kg_current_links l JOIN kg_things a ON a.id=l.from_id "
                                "WHERE l.kind='address_of' AND a.kind='address'").fetchall():
        if tid in by_id:
            byaddr.setdefault(fid, []).append(tid)
    for tids in byaddr.values():
        for j in tids[1:]:
            if tids[0] != j:
                pairs.setdefault((tids[0], j), "share an address")
    out = []
    for (x, y), why in pairs.items():
        a, b = by_id[x], by_id[y]
        a_legacy, b_legacy = a[1].startswith("person:legacy-"), b[1].startswith("person:legacy-")
        if a[3] == "owner" and b[3] != "owner":
            keep, fold = a, b
        elif b[3] == "owner" and a[3] != "owner":
            keep, fold = b, a
        elif a_legacy != b_legacy:
            keep, fold = (b, a) if a_legacy else (a, b)
        else:
            keep, fold = a, b
        st = _standing(con, [x, y])
        q = con.execute("SELECT id FROM queue WHERE kind='possible_duplicate' AND status='open' AND subject_ref IN (?,?)",
                        ("%s|%s" % (keep[1], fold[1]), "%s|%s" % (fold[1], keep[1]))).fetchone()
        out.append(dict(keep_key=keep[1], keep_name=keep[2], fold_key=fold[1], fold_name=fold[2], why=why, standing=st,
                        queue_id=q[0] if q else None, guess="yes"))
    out.sort(key=lambda d: (-(d["standing"] or 0), d["keep_name"].lower()))
    return out[:n]


def held_questions(con):
    import org_moves
    out = []
    for qid, ref, q, prop in org_moves.onboarding_set(con):
        row = con.execute("SELECT name FROM kg_things WHERE key=?", (ref,)).fetchone()
        out.append(dict(queue_id=qid, key=ref, name=row[0] if row else ref, guess=prop if prop in ORG_TYPES else None, question=q))
    return out


def mapping_questions(con):
    """The uncertain person-mapping questions the legacy retirement raised: a first name, a handle or a role in brackets
    stands where a full name should. Still open in the queue."""
    out = []
    for qid, ref, q, prop in con.execute("SELECT id, subject_ref, question, proposed_answer FROM queue WHERE kind='confirm-guess' AND status='open' "
                                         "AND question LIKE 'I had guessed that % Is that right?' ORDER BY id").fetchall():
        m = MAP_Q.match(q)
        if not m:
            continue
        who = m.group(3) if m.group(2) == "is an address of" else m.group(1)
        if _FULL_NAME.fullmatch(who):
            continue
        clash = None
        if m.group(2) == "is an address of":
            r = con.execute("SELECT t2.name FROM kg_current_links l JOIN kg_things a ON a.id=l.from_id JOIN kg_things t2 ON t2.id=l.to_id "
                            "WHERE a.key=? AND l.kind='address_of' AND lower(t2.name)<>? LIMIT 1", (ref, sg.norm(m.group(3)))).fetchone()
            clash = r[0] if r else None
        out.append(dict(queue_id=qid, ref=ref, question=q, guess=prop or "yes", about=who, left=m.group(1), words=m.group(2), right=m.group(3), clash=clash))
    return out


def boss_candidates(con):
    """Who the notes already call a boss or a manager. Only a pointer for the question; levels are never guessed."""
    out = []
    for tid, key, name in con.execute("SELECT t.id, t.key, t.name FROM kg_things t WHERE t.kind='person' AND t.merged_into IS NULL "
                                      "AND t.key<>'person:me'").fetchall():
        for k in ("relationship", "role"):
            v, _w = _fact(con, tid, k)
            if v and BOSS_WORDS.search(v):
                out.append((key, name, v))
                break
    return out


def sender_questions(con, people_rows, n=QUESTION_N):
    """The question marks that matter (senders.onboarding_questions, limit 30), minus anyone already on the sheet, ranked, at most n.
    On the sheet already = the address belongs to a listed person, or the question's organization/address name matches a listed person."""
    try:
        import senders
        qs = senders.onboarding_questions(con, limit=30)
    except Exception:  # noqa: BLE001  (no senders layer yet: nothing to ask)
        return []
    have = set()
    for p in people_rows:
        have.add(sg.norm(p["name"]))
        for key in [p["key"]] + list(p["also"]):
            t = sg.thing_by_key(con, key)
            if t:
                have.update(a.lower() for (a,) in con.execute("SELECT sender FROM v_thing_senders WHERE thing_id=? AND sender IS NOT NULL", (t["id"],)))
    out, seen = [], set()
    for q in sorted(qs, key=lambda d: (-d["score"], d["address"])):
        a = q["address"].lower()
        local = sg.norm(re.sub(r"[._+-]+", " ", a.split("@")[0]))
        if a in have or a in seen or local in have:
            continue
        seen.add(a)
        out.append(q)
    return out[:n]


def level_points(con):
    """His level weights as the settings read them: {'1':x,'2':y,'3_or_more':z} from his owner fact, else None (the proposal stands in the file)."""
    t = sg.thing_by_key(con, sg.thing_key(*WEIGHTS_SUBJECT))
    if not t:
        return None
    r = con.execute("SELECT value FROM kg_current_facts WHERE thing_id=? AND fact_key=? AND who='owner' ORDER BY id DESC LIMIT 1", (t["id"], WEIGHTS_FACT[0])).fetchone()
    if not r or not r[0].startswith("level_points="):
        return None
    try:
        nums = [float(x) for x in r[0].split("=", 1)[1].split(",")]
    except ValueError:
        return None
    return dict(zip(LEVEL_WORDS, nums)) if len(nums) == 3 else None


def _points_for(level, pts):
    if level is None or level <= 0:
        return 0.0
    return pts[LEVEL_WORDS[min(level, 3) - 1]]


def before_after(con, people_rows, pts, n=TOP_N):
    """Top n by standing, before and after the level weights, using the levels HE has set (or the chain he gave). Nothing guessed."""
    lv = {r[0]: r[1] for r in con.execute("SELECT person_key, level FROM v_levels_above_me WHERE level IS NOT NULL")}
    rows = []
    for p in people_rows:
        lvl = lv.get(p["key"])
        base = p["standing"] or 0.0
        rows.append((p["name"], base, lvl, base + _points_for(lvl, pts)))
    before = sorted(rows, key=lambda r: -r[1])
    after = sorted(rows, key=lambda r: -r[3])
    return before, after, any(r[2] for r in rows)


# ---- the sheet -------------------------------------------------------------------------------------------
def build(con, top_n=TOP_N):
    """-> (sheet dict). Read only: nothing is written to the database."""
    orgs = organizations(con)
    held_keys = {h["key"] for h in held_questions(con)}
    plist = people(con, orgs, top_n)
    # the senders step made one bare organization per domain (hundreds): they are not questions for the sitting unless someone on the
    # sheet is a member or he has already said something about them. Keeps the sheet short; they still guess a person's organization.
    on_sheet = {p["name"] for p in plist}
    bare = {k for (k,) in con.execute("SELECT key FROM thing_keys WHERE made_from LIKE 'domain-org:%'")}
    def wanted(o):
        if o["key"] in held_keys:
            return False
        if o["key"] not in bare or o["type"] or o["parent_key"] or on_sheet & set(o["members"]):
            return True
        t = sg.thing_by_key(con, o["key"])
        return bool(t and con.execute("SELECT 1 FROM kg_current_facts WHERE thing_id=? AND who='owner' LIMIT 1", (t["id"],)).fetchone())
    s = dict(people=plist, orgs=[o for o in orgs if wanted(o)], held=held_questions(con),
             mapping=mapping_questions(con), dups=duplicate_pairs(con), senders=sender_questions(con, plist), boss=boss_candidates(con), points=level_points(con))
    s["org_names"] = {o["key"]: o["name"] for o in orgs}
    return s


def _ids(s):
    """Stable ids for this sheet: P01.., O01.., H1.., M1.., B1, W1."""
    ids = {}
    for i, p in enumerate(s["people"], 1):
        ids["P%02d" % i] = dict(kind="person", key=p["key"], name=p["name"], guess=p["guess"], on_file=p["on_file"])
    for i, o in enumerate(s["orgs"], 1):
        ids["O%02d" % i] = dict(kind="org", key=o["key"], name=o["name"], type=o["type"], parent_key=o["parent_key"])
    for i, h in enumerate(s["held"], 1):
        ids["H%d" % i] = dict(kind="held", key=h["key"], name=h["name"], guess=h["guess"], queue_id=h["queue_id"], question=h["question"])
    for i, m in enumerate(s["mapping"], 1):
        ids["M%d" % i] = dict(kind="mapping", **m)
    for i, d in enumerate(s["dups"], 1):
        ids["D%d" % i] = dict(kind="dup", **d)
    for i, q in enumerate(s.get("senders", []), 1):
        ids["Q%d" % i] = dict(kind="sender", address=q["address"], key=q["key"], organization=q["organization"], guess="person")
    ids["B1"] = dict(kind="boss")
    ids["W1"] = dict(kind="weights", guess=list(PROPOSED_LEVEL_POINTS))
    return ids


def _fmt(x):
    return "-" if x is None else ("%g" % x)


def render(s, con=None, extra_ref=None, db_label=""):
    ids = _ids(s)
    L = []
    L.append("# Onboarding sitting: DRAFT sheet")
    L.append("")
    L.append("Built %s from a copy of the database (%s). **Nothing here is stored.** Every line is a guess: write `ok` to confirm it, or write the right answer. "
             "A line you skip stays unknown. About 30 minutes; the first block matters most, so stop when time runs out." % (dt.date.today().isoformat(), db_label or "a copy"))
    L.append("")
    L.append("Reading the guesses: *guess* means the model worked it out from mail history, meetings and the old notes; none of it is a fact until you say so.")
    L.append("")
    L.append("## 1. Same person twice? (%d, a yes merges them; nothing merges without it)" % len(s["dups"]))
    L.append("")
    L.append("The notes hold these people twice, so what you told me about one does not show on the other. The first name is the one kept.")
    L.append("")
    for i, d in enumerate(s["dups"], 1):
        L.append("- **D%d.** Is **%s** the same person as **%s**? (%s; standing %s) *guess*: yes -> your answer: ______"
                 % (i, d["keep_name"], d["fold_name"] + (" [%s]" % d["fold_key"] if d["fold_name"].lower() == d["keep_name"].lower() else ""), d["why"], _fmt(d["standing"])))
    if not s["dups"]:
        L.append("- None found.")
    L.append("")
    # 2 boss + weights
    L.append("## 2. Who is above you (the most useful answer)")
    L.append("")
    cand = s["boss"]
    L.append("**B1.** Who do you report to (your boss), and who is above them, up to the head? Give a person from the list below, or a name; or just a number of levels for each person.")
    if cand:
        L.append("- Notes already call these people a boss or manager: " + "; ".join("%s (*guess*: %s)" % (n, v[:60]) for _k, n, v in cand)
                 + ". The word may mean a talent manager rather than a boss, so this is only a pointer.")
    else:
        L.append("- Nothing in the notes calls anyone a boss. Left blank on purpose: the model never places anyone.")
    L.append("- Your answer: ______  (levels above you per person: 1 = your direct boss, 2 = their boss, 0 = a peer)")
    L.append("")
    pts = s["points"] or dict(zip(LEVEL_WORDS, PROPOSED_LEVEL_POINTS))
    L.append("**W1.** Extra points in the ranking for a person above you. *Proposed* (a guess, from the coordinator): 1 level up +%s, 2 levels up +%s, 3 or more +%s. %s"
             % (_fmt(pts["1"]), _fmt(pts["2"]), _fmt(pts["3_or_more"]),
                "Already set by you." if s["points"] else "Confirm with `ok` or give three numbers, e.g. `1.0,0.5,0.25`."))
    L.append("")
    if con is not None:
        before, after, any_level = before_after(con, s["people"], pts)
        L.append("What the weights would move, top %d by standing (uses only levels you have set; none yet means nothing moves):" % len(before))
        L.append("")
        if not any_level:
            L.append("- Nobody has a level yet, so the order is the same before and after. It moves once B1 is answered; the final sheet re-runs this table.")
        else:
            L.append("| rank before | person | standing | level | rank after | standing + points |")
            L.append("|---|---|---|---|---|---|")
            ra = {r[0]: i for i, r in enumerate(after, 1)}
            for i, r in enumerate(before, 1):
                L.append("| %d | %s | %s | %s | %d | %s |" % (i, r[0], _fmt(r[1]), _fmt(r[2]), ra[r[0]], _fmt(r[3])))
        if extra_ref:
            L.append("")
            L.append("The scoring helper's own before/after on the proposed weights: `%s`." % extra_ref)
        L.append("")
    # 2 people
    L.append("## 3. Your people (%d, ranked by standing)" % len(s["people"]))
    L.append("")
    L.append("For each: relationship, organization, role, and how much they matter (`high` / `normal` / `low` = not important). `ok` confirms the guess shown. Levels are not asked here (see B1).")
    L.append("")
    for i, p in enumerate(s["people"], 1):
        pid = "P%02d" % i
        g = p["guess"]
        if i == MUST_N + 1:
            L.append("### If there is time (the rest)")
            L.append("")
        L.append("**%s. %s** (standing %s, %d shared meetings%s)%s" % (
            pid, p["name"], _fmt(p["standing"]), p["shared"], ", last %s" % p["last_event"][:10] if p["last_event"] else "",
            "  also on file as " + ", ".join(p["also"]) if p["also"] else ""))
        f = p["on_file"]
        def line(label, onfile, guess, why=""):
            if onfile:
                return "- %s: **your word on file**: %s. (answer only to change it)" % (label, onfile)
            return "- %s: *guess* %s%s -> your answer: ______" % (label, guess if guess else "(no guess)", " (%s)" % why if why and guess else "")
        L.append(line("relationship", f["relationship"], g["relationship"], g["relationship_why"]))
        if g["organization"]:
            og = "%s" % s["org_names"].get(g["organization"], g["organization"])
        elif g["organization_new"]:
            og = "%s (a new organization)" % g["organization_new"]
        else:
            og = None
        L.append(line("organization", f["organization"], og, g["organization_why"]))
        L.append(line("role", f["role"], g["role"]))
        L.append(line("matters", f["importance"], g["importance"], "from standing"))
        if i <= KEEP_N:
            L.append("- keep in touch: how many days at most between you two? (a number, e.g. 30; your word only, never guessed) -> your answer: ______")
        L.append("")
    L.append("**Anyone missing?** Names to add: ______")
    L.append("")
    # 3 orgs
    L.append("## 4. Your organizations (%d)" % len(s["orgs"]))
    L.append("")
    L.append("Type is company / department / team / group. Nesting says whether it sits inside another organization. `ok` confirms.")
    L.append("")
    for i, o in enumerate(s["orgs"], 1):
        mem = (", members: " + ", ".join(o["members"][:6])) if o["members"] else ""
        L.append("- **O%02d. %s**: type *guess* %s%s; nesting *guess* %s%s -> your answer: ______" % (
            i, o["name"], o["type"] or "(none)", "" if o["type_who"] != "owner" else " (your word on file)",
            ("part of " + o["parent_name"]) if o["parent_name"] else "top level (not part of another)", mem))
    L.append("")
    # 4 held
    L.append("## 5. What kind of thing is this? (held from earlier, %d)" % len(s["held"]))
    L.append("")
    for i, h in enumerate(s["held"], 1):
        L.append("- **H%d. %s**: filed as a group (a family, circle of friends or club). Is it a group, or a company, department or team? *guess* %s -> your answer: ______"
                 % (i, h["name"], h["guess"] or "(no guess)"))
    L.append("")
    # 5 mapping
    L.append("## 6. Is this the right person? (%d, from the old notes)" % len(s["mapping"]))
    L.append("")
    for i, m in enumerate(s["mapping"], 1):
        L.append("- **M%d.**%s %s *guess*: %s -> your answer: ______" % (i, "" if not m["clash"] else " (that address is already filed under %s: a yes means the two are one person, which is a merge)" % m["clash"], m["question"].replace("I had guessed that ", "The old code guessed that ").rstrip("? ").replace(". Is that right", "").rstrip(".") + ". Right?", m["guess"]))
    L.append("")
    L.append("## 7. Who is this? (%d question marks that matter, from your mail and meetings)" % len(s.get("senders", [])))
    L.append("")
    L.append("Addresses you deal with that the code cannot tell apart: a person or an automated sender (a bot). Answer `person`, `bot` or `ok` (confirms the guess). Skipped lines stay question marks.")
    L.append("")
    for i, q in enumerate(s.get("senders", []), 1):
        L.append("- **Q%d. %s**%s: %s. *guess*: person -> your answer: ______" % (
            i, q["address"], " (%s)" % q["organization"] if q["organization"] else "", "; ".join(q["why"])))
    if not s.get("senders"):
        L.append("- None that are not already on this sheet.")
    L.append("")
    L.append("---")
    L.append("Generated by `onboarding.py`. Answers are recorded with `onboarding.py answer`, one line each through the owner-answer door; a line left blank records nothing.")
    return "\n".join(L) + "\n", ids


def write_sheet(con, out_path, db_label="", extra_ref=None):
    s = build(con)
    if extra_ref is None:
        cand = os.path.join(os.path.dirname(os.path.abspath(out_path)), "phase-3-step-8-top30-before-after.md")
        extra_ref = os.path.basename(cand) if os.path.exists(cand) else None
        if extra_ref is None:
            extra_ref = "phase-3-step-8-top30-before-after.md (not written yet; regenerate this sheet when it appears)"
    text, ids = render(s, con, extra_ref, db_label)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.splitext(out_path)[0] + ".guesses.json", "w", encoding="utf-8") as f:
        json.dump(ids, f, indent=1)
    return s, ids


# ---- recording his answers (the owner door) ----------------------------------------------------------------
class AnswerError(ValueError):
    pass


def _key_name(key):
    kind, name = key.split(":", 1)
    if sg.thing_key(kind, name) != key:
        raise AnswerError("cannot address %r through the answer door" % key)
    return kind, name


def _resolve_org(con, text, orgs_by_id):
    t = text.strip()
    if t in orgs_by_id:
        return orgs_by_id[t]["key"]
    if t.startswith("organization:"):
        return sg.resolve_key(con, t)
    r = con.execute("SELECT key FROM kg_things WHERE kind='organization' AND merged_into IS NULL AND lower(name)=?", (sg.norm(t),)).fetchall()
    if len(r) == 1:
        return r[0][0]
    return sg.thing_key("organization", t)           # a new organization he named


def _person_key(con, ref, ids):
    if ref in ids and ids[ref]["kind"] == "person":
        return ids[ref]["key"]
    if ref.startswith("person:"):
        return ref
    r = con.execute("SELECT key FROM kg_things WHERE kind='person' AND merged_into IS NULL AND lower(name)=?", (sg.norm(ref),)).fetchall()
    if len(r) == 1:
        return r[0][0]
    raise AnswerError("who is %r? use a P id, a person key or a unique name" % ref)


def _decide(con, rec, question, said_on, key, fact_key, value, confirmed, shown=None, queue_id=None):
    kind, name = _key_name(key)
    words = ("confirmed the guess shown on the onboarding sheet: %s" % shown) if confirmed else ("onboarding sheet, his answer: %s (instead of the guess shown: %s)" % (value, shown))
    r = sg.record_answer(con, question, words, "onboarding sitting", said_on, kind, name, fact_key, value,
                         words_kind="summary", queue_id=queue_id)
    rec.append(dict(id=question, key=key, fact_key=fact_key, value=value, confirmed=confirmed, **r))
    return r


def record(con, ids, answers, said_on=None, asked_by="onboarding sitting"):
    """Record his answers. The caller owns the transaction. -> list of what was stored. Raises on a bad line before storing it."""
    said_on = said_on or dt.date.today().isoformat()
    rec = []
    orgs_by_id = {k: v for k, v in ids.items() if v["kind"] == "org"}
    for a in answers:
        i = a["id"]
        spec = ids.get(i)
        if spec is None:
            raise AnswerError("no line %r on the sheet" % i)
        k = spec["kind"]
        if k == "person":
            g, key = spec["guess"], spec["key"]
            q = "%s: about %s" % (i, spec["name"])
            for field in ("relationship", "role", "importance"):
                v = a.get(field)
                if v is None or str(v).strip() == "":
                    continue
                guess = g.get(field)
                if str(v).strip().lower() == "ok":
                    if not guess:
                        raise AnswerError("%s %s: there was no guess to confirm" % (i, field))
                    val, conf = guess, True
                else:
                    val, conf = str(v).strip(), False
                if field == "importance" and val not in ("high", "normal", "low"):
                    raise AnswerError("%s importance must be high, normal or low" % i)
                _decide(con, rec, "%s %s" % (q, field), said_on, key, field, val, conf, shown=guess)
            v = a.get("keep_in_touch_days")
            if v is not None and str(v).strip():
                if not re.fullmatch(r"\d{1,4}", str(v).strip()) or int(str(v).strip()) < 1:
                    raise AnswerError("%s keep_in_touch_days must be a whole number of days (1 or more)" % i)
                _decide(con, rec, "%s keep_in_touch_days" % q, said_on, key, "keep_in_touch_days", str(int(str(v).strip())), False, shown="(never guessed)")
            v = a.get("organization")
            if v is not None and str(v).strip():
                v = str(v).strip()
                if v.lower() == "none":
                    continue
                if v.lower() == "ok":
                    if g.get("organization"):
                        okey, conf, shown = g["organization"], True, g["organization"]
                    elif g.get("organization_new"):
                        okey, conf, shown = sg.thing_key("organization", g["organization_new"]), True, g["organization_new"]
                    else:
                        raise AnswerError("%s organization: there was no guess to confirm" % i)
                else:
                    okey, conf = _resolve_org(con, v, orgs_by_id), False
                    shown = g.get("organization") or g.get("organization_new")
                _decide(con, rec, "%s organization" % q, said_on, key, "link:member_of", okey, conf, shown=shown)
        elif k == "sender":
            ans = str(a.get("answer", "")).strip().lower()
            if not ans:
                continue
            val = "person" if ans in ("ok", "person", "yes") else ans
            if val not in ("person", "bot"):
                raise AnswerError("%s: answer person, bot or ok" % i)
            _decide(con, rec, "%s: is %s a person or a bot?" % (i, spec["address"]), said_on, spec["key"], "sender_kind", val, ans == "ok", shown=spec["guess"])
        elif k == "boss":
            lv = a.get("levels") or {}
            rt = a.get("reports_to")
            if rt:
                _decide(con, rec, "B1: who do you report to", said_on, "person:me", "link:reports_to", _person_key(con, rt, ids), False, shown="(blank on purpose)")
            for ref, n in lv.items():
                n = int(n)
                if n < 0:
                    raise AnswerError("a level is 0 or more")
                _decide(con, rec, "B1: levels above you for %s" % ref, said_on, _person_key(con, ref, ids), "levels_above_me", str(n), False, shown="(blank on purpose)")
        elif k == "weights":
            v = str(a.get("value", "")).strip()
            if not v:
                continue
            conf = v.lower() == "ok"
            nums = list(PROPOSED_LEVEL_POINTS) if conf else [float(x) for x in v.split(",")]
            if len(nums) != 3:
                raise AnswerError("W1 needs three numbers")
            val = "level_points=" + ",".join("%g" % x for x in nums)
            kind, name = WEIGHTS_SUBJECT
            words = ("confirmed the proposed weights on the onboarding sheet: " if conf else "onboarding sheet, his weights: ") + val
            r = sg.record_answer(con, "W1: points per level above you", words, asked_by, said_on, kind, name, "setting", val, words_kind="summary")
            rec.append(dict(id="W1", key=sg.thing_key(kind, name), fact_key="setting", value=val, confirmed=conf, **r))
        elif k == "org":
            key = spec["key"]
            t = a.get("type")
            if t and str(t).strip():
                t = str(t).strip().lower()
                conf = t == "ok"
                if conf:
                    if not spec["type"]:
                        raise AnswerError("%s: there was no type guess" % i)
                    t = spec["type"]
                _decide(con, rec, "%s: type of %s" % (i, spec["name"]), said_on, key, "org_type", t, conf, shown=spec["type"])
            p = a.get("part_of")
            if p and str(p).strip() and str(p).strip().lower() not in ("none", "ok"):
                pk = _resolve_org(con, str(p), orgs_by_id)
                _decide(con, rec, "%s: %s sits inside" % (i, spec["name"]), said_on, key, "link:part_of", pk, False, shown=spec["parent_key"] or "top level")
        elif k == "held":
            t = str(a.get("type", "")).strip().lower()
            if not t:
                continue
            conf = t == "ok"
            if conf:
                if not spec["guess"]:
                    raise AnswerError("%s: there was no guess" % i)
                t = spec["guess"]
            if t not in ORG_TYPES:
                raise AnswerError("%s: type must be one of %s" % (i, ", ".join(ORG_TYPES)))
            _decide(con, rec, "%s: what kind of thing is %s" % (i, spec["name"]), said_on, spec["key"], "org_type", t, conf, shown=spec["guess"], queue_id=spec["queue_id"])
            _close_queue(con, spec["queue_id"], t, said_on)
        elif k == "dup":
            ans = str(a.get("answer", "")).strip()
            if not ans:
                continue
            yes = ans.lower() in ("yes", "y", "ok")
            q = "%s: are %s and %s the same person?" % (i, spec["keep_name"], spec["fold_name"])
            if yes:
                r = sg.merge_things(con, spec["fold_key"], spec["keep_key"], "onboarding sheet, his answer: %s (same person)" % ans, asked_by, said_on,
                                    question=q, queue_id=spec["queue_id"])
                rec.append(dict(id=i, key=spec["fold_key"], fact_key="merge_into", value=spec["keep_key"], confirmed=True, answer_id=r["answer_id"]))
            else:
                r = sg.record_answer(con, q, "onboarding sheet, his answer: %s" % ans, asked_by, said_on, words_kind="summary", queue_id=spec["queue_id"])
                rec.append(dict(id=i, key=spec["fold_key"], fact_key=None, value=None, confirmed=False, **r))
                if spec["queue_id"]:
                    _close_queue(con, spec["queue_id"], ans, said_on)
        elif k == "mapping":
            ans = str(a.get("answer", "")).strip()
            if not ans:
                continue
            yes = ans.lower() in ("yes", "y", "ok")
            q = spec["question"]
            made = None
            if yes and spec.get("clash"):
                # the address already belongs to another person on file: linking it too would make one address two people. Record his
                # yes as an answer only; the two being one person is a merge, and a merge is his own separate word (gc merge).
                made = None
            elif yes:
                made = _remake_link(con, spec, said_on, rec)
            if made is None:
                r = sg.record_answer(con, "%s: %s" % (i, q), "onboarding sheet, his answer: %s" % ans, asked_by, said_on, words_kind="summary", queue_id=spec["queue_id"])
                rec.append(dict(id=i, key=spec["ref"], fact_key=None, value=None, confirmed=yes, **r,
                                **({"merge_needed": "%s and %s" % (spec["clash"], spec["right"])} if yes and spec.get("clash") else {})))
            _close_queue(con, spec["queue_id"], ans, said_on)
    return rec


def _close_queue(con, qid, answer, said_on):
    con.execute("UPDATE queue SET status='answered', answer=?, answered_at=? WHERE id=?", (answer, said_on, int(qid)))


def _remake_link(con, spec, said_on, rec):
    """His yes to 'X is an address of Y' / 'X is a member of Y': make that link as HIS word, if both ends can be found. Else None."""
    left, words, right = spec["left"], spec["words"], spec["right"]
    if words == "is an address of":
        a_key = spec["ref"]
        r = con.execute("SELECT key FROM kg_things WHERE kind='person' AND merged_into IS NULL AND lower(name)=? ORDER BY (created_by='owner') DESC, id", (sg.norm(right),)).fetchall()
        if not r or not con.execute("SELECT 1 FROM kg_things WHERE key=?", (a_key,)).fetchone():
            return None
        return _decide(con, rec, "M: %s" % spec["question"], said_on, a_key, "link:address_of", r[0][0], True, shown="yes", queue_id=spec["queue_id"])
    p_key = spec["ref"]
    r = con.execute("SELECT key FROM kg_things WHERE kind='organization' AND merged_into IS NULL AND lower(name)=?", (sg.norm(right),)).fetchall()
    if len(r) != 1 or not con.execute("SELECT 1 FROM kg_things WHERE key=?", (p_key,)).fetchone():
        return None
    return _decide(con, rec, "M: %s" % spec["question"], said_on, p_key, "link:member_of", r[0][0], True, shown="yes", queue_id=spec["queue_id"])


# ---- command line ------------------------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("sheet")
    s1.add_argument("--db", required=True)
    s1.add_argument("--out", required=True)
    s2 = sub.add_parser("answer")
    s2.add_argument("--db", required=True)
    s2.add_argument("--guesses", required=True)
    s2.add_argument("--file", required=True)
    s2.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    con = db.connect(os.path.abspath(a.db))
    con.isolation_level = None
    if a.cmd == "sheet":
        s, ids = write_sheet(con, a.out, os.path.basename(a.db))
        print("sheet written: %s (%d people, %d organizations, %d held, %d mapping)" % (a.out, len(s["people"]), len(s["orgs"]), len(s["held"]), len(s["mapping"])))
        return 0
    ids = json.load(open(a.guesses, encoding="utf-8"))
    doc = json.load(open(a.file, encoding="utf-8"))
    con.execute("BEGIN IMMEDIATE")
    try:
        rec = record(con, ids, doc["answers"], doc.get("said_on"))
        con.execute("ROLLBACK" if a.dry else "COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    print("%s %d answer(s)" % ("would record" if a.dry else "recorded", len(rec)))
    for r in rec:
        print("  %s -> %s %s = %s (answer #%s)" % (r["id"], r["key"], r["fact_key"], r["value"], r["answer_id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""senders.py: every sender is tied to an organization, and is a person, a bot, or a question mark.
(His ruling of 2026-11-16 via the coordinator; Vision 3.7.7; plan Phase 3, "Every sender is tied to an organization".)

  python3 senders.py --db PATH             # report on a COPY: what would be classified (writes nothing)
  python3 senders.py --db PATH --apply     # build it on a COPY (the live file is touched only by the build window's deploy)

What it does, for every address that wrote to him (or sits on an invite):
  * ties the address to its ORGANIZATION by its domain (link `belongs_to`, address -> organization). A free-mail domain (gmail,
    icloud, yahoo ...) is not an organization. A new organization takes the registrable domain as its NAME and has no org_type
    yet (type not yet known): code never guesses a company name.
  * records its KIND (fact `sender_kind`, code, sure) and only what it is sure of:
      person   = passes the 3.2 rule (store_events._People: real two-way mail, 2+ real shared events, or named by him), not a bot;
      bot      = a company's automated system: its own name says so (noreply, notifications ...) or at least half of its mail
                 carries machine headers / Gmail's promotions label, and he never answered it;
      unknown  = the question mark. Everything else.
  * for a bot, records whether it NEEDS HIM (fact `bot_need`): junk, fyi or needs_him. His own rulings decide first (his need,
    destination and inbox answers on the address, its rules, its domain, its organization). Without a ruling: a bank, payment,
    security, booking, travel or casting word means needs_him; plain bulk mail means fyi; anything else is `unsure`. JUNK IS NEVER
    ASSUMED: it is written only from his ruling.
Moving mail waits for Phase 5; this stores classifications only. Idempotent; the caller owns the transaction and the lock.
onboarding_questions(con, limit=30) lists the question marks that MATTER, ranked, for the onboarding sheet."""
import argparse
import json
import math
import os
import re
import secrets
import sys

import store_graph as sg
import store_events as se

ME = se.ME
FREE_MAIL = {
    "gmail.com", "googlemail.com", "icloud.com", "me.com", "mac.com", "yahoo.com", "yahoo.co.uk", "yahoo.ca", "yahoo.fr", "ymail.com",
    "rocketmail.com", "outlook.com", "hotmail.com", "hotmail.co.uk", "live.com", "msn.com", "aol.com", "aim.com", "proton.me",
    "protonmail.com", "pm.me", "hey.com", "gmx.com", "gmx.net", "gmx.de", "mail.com", "fastmail.com", "fastmail.fm", "zoho.com",
    "yandex.com", "yandex.ru", "qq.com", "163.com", "126.com", "comcast.net", "verizon.net", "att.net", "sbcglobal.net", "cox.net",
    "optonline.net", "earthlink.net", "mail.ru", "web.de", "t-online.de", "orange.fr", "naver.com",
}
TWO_PART_TLD = {"co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.nz", "co.jp", "co.in", "co.za", "co.kr",
                "com.br", "com.mx", "com.cn", "com.sg", "com.hk", "com.tr", "com.ar"}
AUTO_SHARE = 0.5
# Words in a sender's name or subjects that say the mail may need him. The engine ships the generic list; the person adds
# words of his own trade in gc.json needs_words_extra (regex pieces, optional). NEEDS_WORDS is built when first asked for.
NEEDS_WORDS_HEAD = (r"bank|chase|citi|capital ?one|wells ?fargo|amex|american express|paypal|venmo|zelle|payment|past due|overdue|"
                    r"statement|invoice|bill(ing)?|security|fraud|suspicious|password|verification|sign-?in|booking|reservation|"
                    r"itinerary|flight|boarding|check-?in")
NEEDS_WORDS_TAIL = r"appointment|declined"


def needs_words():
    import gc_settings
    extra = [str(w) for w in (gc_settings.load("gc.json").get("needs_words_extra") or []) if str(w)]
    return re.compile(r"\b(%s)\b" % "|".join([NEEDS_WORDS_HEAD] + extra + [NEEDS_WORDS_TAIL]), re.I)


def __getattr__(name):
    if name == "NEEDS_WORDS":
        return needs_words()
    raise AttributeError(name)
NEED_FROM_ANSWER = {"nothing": "junk", "just-keep": "fyi", "just-see": "fyi", "action-urgent": "needs_him",
                    "action-not-urgent": "needs_him", "waiting-on-someone": "needs_him"}
DEST_FROM_ANSWER = {("destination", "trash"): "junk", ("destination", "promos"): "fyi", ("destination", "archive"): "fyi",
                    ("destination", "inbox"): "needs_him", ("inbox", "skip"): "fyi", ("inbox", "stay"): "needs_him"}
RANK = {"junk": 0, "fyi": 1, "needs_him": 2}     # when his rulings disagree, the more protective one wins


def registrable(domain):
    """the organization part of a domain: mail.example-agency.com -> example-agency.com (a small list of two-part endings, no network)"""
    parts = [p for p in domain.lower().strip(".").split(".") if p]
    if len(parts) <= 2:
        return ".".join(parts)
    return ".".join(parts[-3:]) if ".".join(parts[-2:]) in TWO_PART_TLD else ".".join(parts[-2:])


def org_domain(addr):
    """-> the registrable domain that names this address's organization, or None (free mail, or not an address)"""
    local, at, dom = addr.strip().lower().rpartition("@")
    if not at or not local or "." not in dom or " " in dom:
        return None
    reg = registrable(dom)
    return None if (reg in FREE_MAIL or dom in FREE_MAIL) else reg


def _ready(con):
    have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"kg_vocab", "kg_links", "messages"} <= have:
        return False
    return con.execute("SELECT 1 FROM kg_fact_keys WHERE key='sender_kind'").fetchone() is not None


def _cur(con, tid, key):
    r = con.execute("SELECT id, value, who, certainty FROM kg_facts WHERE thing_id=? AND fact_key=? AND replaced_by IS NULL "
                    "ORDER BY id DESC LIMIT 1", (tid, key)).fetchone()
    return r


def _org_for(con, reg, stats):
    """the organization for a registrable domain: one he or an earlier run already tied to it, else a new one named by the domain"""
    dom_id = sg.thing(con, "domain", reg)
    r = con.execute("SELECT to_id FROM kg_links WHERE from_id=? AND kind='domain_of' AND replaced_by IS NULL ORDER BY id LIMIT 1",
                    (dom_id,)).fetchone()
    if r:
        oid = sg.survivor(con, r[0])
        if con.execute("SELECT kind FROM kg_things WHERE id=?", (oid,)).fetchone()[0] == "organization":
            return oid
    made_from = "domain-org:" + reg
    rec = con.execute("SELECT key FROM thing_keys WHERE made_from=?", (made_from,)).fetchone()
    if rec:
        key = rec[0]
    else:
        while True:
            key = "organization:" + secrets.token_hex(5)
            if not con.execute("SELECT 1 FROM thing_keys WHERE key=?", (key,)).fetchone():
                break
        con.execute("INSERT INTO thing_keys(key, kind, made_from, created_at) VALUES(?,?,?,?)", (key, "organization", made_from, sg._ts()))
    had = sg.thing_by_key(con, key)
    oid = sg.thing(con, "organization", reg, created_by="code", key=key)
    if not had:
        stats["organizations_made"] += 1
    con.execute("UPDATE kg_things SET name=? WHERE id=? AND name<>? AND merged_into IS NULL", (reg, oid, reg))   # a rebuild may bring it back under its hex name
    sg.add_link(con, dom_id, "domain_of", oid, "code", "sure", "code", "sender-domain:" + reg)
    return oid


def _rulings(con, tid):
    """his unconditioned need / destination / inbox answers on a thing, and on the rules that apply to it -> ([needs], [others], ref)"""
    needs, others, ref = [], [], None
    rows = con.execute(
        "SELECT f.id, f.fact_key, f.value FROM kg_facts f WHERE f.replaced_by IS NULL AND f.who='owner' AND f.condition IS NULL "
        "AND f.fact_key IN ('need','destination','inbox') AND (f.thing_id=? OR f.thing_id IN ("
        "  SELECT l.from_id FROM kg_links l JOIN kg_things r ON r.id=l.from_id AND r.kind='rule' "
        "   WHERE l.kind='applies_to' AND l.to_id=? AND l.replaced_by IS NULL)) ORDER BY f.id", (tid, tid)).fetchall()
    for fid, k, v in rows:
        if k == "need" and v in NEED_FROM_ANSWER:
            needs.append(NEED_FROM_ANSWER[v])
        elif (k, v) in DEST_FROM_ANSWER:
            others.append(DEST_FROM_ANSWER[(k, v)])
        else:
            continue
        ref = ref or "ruling:%d" % fid
    return needs, others, ref


def his_ruling(con, addr, org_id):
    """-> (need, ref) from his own answers, looking at the address, then its domain(s), then its organization; None if he never ruled"""
    local, _, dom = addr.partition("@")
    ids = []
    for key in (sg.thing_key("address", addr), sg.thing_key("domain", dom), sg.thing_key("domain", registrable(dom))):
        t = sg.thing_by_key(con, key)
        if t:
            ids.append(t["id"])
    if org_id:
        ids.append(org_id)
    seen = set()
    for tid in ids:
        if tid in seen:
            continue
        seen.add(tid)
        needs, others, ref = _rulings(con, tid)
        got = needs or others
        if got:
            return max(got, key=RANK.get), ref
    return None, None


def classify_need(con, addr, org_id, subjects, auto_share):
    """-> (need, certainty, source_kind, source_ref). Junk only from his ruling."""
    need, ref = his_ruling(con, addr, org_id)
    if need:
        return need, "sure", "answer", ref
    rx = globals().get("NEEDS_WORDS") or needs_words()
    m = rx.search(addr)                       # the sender's own name says bank, payment, booking ...
    if m:
        return "needs_him", "likely", "code", "category:" + m.group(1).lower()
    if auto_share < AUTO_SHARE:                        # not bulk mail: a subject about a payment, security, booking ... reaches him
        m = rx.search(" ".join(subjects))
        if m:
            return "needs_him", "likely", "code", "category:" + m.group(1).lower()
        return "unsure", "likely", "code", "no ruling, no category word"
    return "fyi", "likely", "code", "bulk-headers"      # bulk marketing words in a subject do not make mail urgent


def _mail_stats(con):
    """per inbound sender: messages, machine-marked messages (headers or Gmail's promotions/forums label), subjects"""
    out = {}
    for frm, lid, lu, prec, auto, labels, subj, sent in con.execute(
            "SELECT lower(from_addr), list_id, list_unsubscribe_present, precedence, auto_submitted, label_ids, subject, is_sent "
            "FROM messages WHERE from_addr IS NOT NULL AND from_addr<>'' ORDER BY id"):
        if sent:
            continue
        s = out.setdefault(frm, {"n": 0, "auto": 0, "subjects": []})
        s["n"] += 1
        lab = labels or ""
        if lid or lu or (prec in ("bulk", "list", "junk")) or (auto not in (None, "", "no")) or "CATEGORY_PROMOTIONS" in lab \
                or "CATEGORY_FORUMS" in lab:
            s["auto"] += 1
        if len(s["subjects"]) < 40 and subj:
            s["subjects"].append(subj)
    return out


def _set_fact(con, tid, key, value, certainty, source_kind, ref):
    cur = _cur(con, tid, key)
    if cur and cur[2] == "owner":
        return False                       # his own word on it: never touched
    if cur and cur[1] == value and cur[3] == certainty:
        return False
    sg.assert_fact(con, tid, key, value, "code", certainty, source_kind, ref)
    return True


def _owner_linked(con, aid):
    """he tied this address to something himself (a link of his on the address, or on the person it belongs to)"""
    return con.execute(
        "SELECT 1 FROM kg_links l WHERE l.who='owner' AND l.replaced_by IS NULL AND l.kind<>'applies_to' AND (l.from_id=? OR l.to_id=? OR l.from_id IN ("
        " SELECT al.to_id FROM kg_links al WHERE al.from_id=? AND al.kind='address_of' AND al.replaced_by IS NULL) OR l.to_id IN ("
        " SELECT al.to_id FROM kg_links al WHERE al.from_id=? AND al.kind='address_of' AND al.replaced_by IS NULL)) LIMIT 1",
        (aid, aid, aid, aid)).fetchone() is not None


def build_senders(con, starters=None):
    """Classify and tie every sender address. Idempotent. -> counts, or {"skipped": why} before migration 026."""
    if not _ready(con):
        return {"skipped": "no sender_kind yet (migration 026 not applied)"}
    starters = se.starter_people() if starters is None else {a.lower() for a in starters}
    people = se._People(con, starters)
    ms = _mail_stats(con)
    replied = {r[0] for r in con.execute("SELECT DISTINCT address FROM s_msg_addr WHERE is_sent=1 AND role IN ('to','cc')")}
    addrs = {a for a in ms if "@" in a} | {a for a in replied if "@" in a}      # who wrote to him, and who he wrote to
    for (nm,) in con.execute("SELECT name FROM kg_things WHERE kind='address'"):
        addrs.add(nm.lower())
    me = people._mailbox().me
    stats = {"addresses": 0, "person": 0, "bot": 0, "unknown": 0, "bot_need": {"junk": 0, "fyi": 0, "needs_him": 0, "unsure": 0},
             "organizations_made": 0, "tied": 0, "no_organization_free_mail": 0, "facts_written": 0, "persons_made": 0}
    made_before = people.admitted
    orgs = {}
    for addr in sorted(addrs):
        if addr in me or addr == ME or "@" not in addr:
            continue
        stats["addresses"] += 1
        aid = sg.thing(con, "address", addr)
        # --- the organization, by domain
        reg = org_domain(addr)
        oid = None
        if reg is None:
            stats["no_organization_free_mail"] += 1
        else:
            if reg not in orgs:
                orgs[reg] = _org_for(con, reg, stats)
            oid = orgs[reg]
            if not con.execute("SELECT 1 FROM kg_links WHERE from_id=? AND kind='belongs_to' AND to_id=? AND replaced_by IS NULL", (aid, oid)).fetchone():
                sg.add_link(con, aid, "belongs_to", oid, "code", "sure", "code", "domain:" + reg)
            stats["tied"] += 1
        # --- the kind, only what it is sure of
        m = ms.get(addr, {"n": 0, "auto": 0, "subjects": []})
        share = (m["auto"] / m["n"]) if m["n"] else 0.0
        bulk_unanswered = bool(m["n"]) and share >= AUTO_SHARE and addr not in replied and addr not in starters
        junk_ruled = his_ruling(con, addr, oid)[0] == "junk" and addr not in starters
        # evidence of a human who matters. Deliberately NOT the 3.2 "named" test: that counts ANY answer of his on the address,
        # including a filter ruling ("trash this", "keep in inbox"), which names a sender, not a person.
        his_link = addr in starters or _owner_linked(con, aid)
        human = his_link or people.two_way(addr) or people.shared_count(addr) >= se.SHARED_MIN
        if human and not his_link and (se.looks_automated(addr) or se.is_role_inbox(addr) or bulk_unanswered or junk_ruled):
            human = False
        pid = people.person_for(addr) if human else None
        if pid:
            kind, why = "person", "the 3.2 rule (two-way mail, shared events, or named by him)"
        elif se.looks_automated(addr):
            kind, why = "bot", "its address says automated"
        elif m["n"] and share >= AUTO_SHARE and addr not in replied:
            kind, why = "bot", "machine headers or promotions label on %d of %d messages, never answered" % (m["auto"], m["n"])
        else:
            kind, why = "unknown", "not sure"
        stats[kind] += 1
        if _set_fact(con, aid, "sender_kind", kind, "sure", "code", why):
            stats["facts_written"] += 1
        # --- a bot's need
        if kind == "bot":
            need, cert, sk, ref = classify_need(con, addr, oid, m["subjects"], share)
            stats["bot_need"][need] += 1
            if _set_fact(con, aid, "bot_need", need, cert, sk, ref):
                stats["facts_written"] += 1
        else:
            con.execute("UPDATE kg_facts SET replaced_by=id WHERE thing_id=? AND fact_key='bot_need' AND replaced_by IS NULL AND who='code'", (aid,))
    stats["persons_made"] = people.admitted - made_before
    return stats


# ---- the onboarding sheet ---------------------------------------------------------------------------
def _shared_events(con):
    n = {}
    for att, org, st in con.execute("SELECT attendee_emails, organizer_email, status FROM calendar_events"):
        if str(st or "").lower() == "cancelled":
            continue
        people = set(se._addr_list(att)) | ({org.strip().lower()} if org and org.strip() else set())
        if len(people) > se.ATTENDEE_CAP:
            continue
        for a in people:
            if not se.BOT_DOMAIN.search(a.partition("@")[2]):
                n[a] = n.get(a, 0) + 1
    return n


def onboarding_questions(con, limit=30):
    """The question marks that MATTER, ranked, at most `limit` (about 30). A question mark (sender_kind unknown) matters only if he
    answered them, started a thread with them, or shared a real calendar event with them. Rank: 2 per thread both spoke in,
    1 per message he sent them, 3 per shared event, a little for how much they wrote. Reads only; the guess is computed here and
    stored nowhere. -> [{"address", "key", "organization", "organization_key", "score", "why": [...], "guess": "..."}]."""
    if not _ready(con):
        return []
    sig = {r[0]: r for r in con.execute(
        "SELECT address, msgs_from, replies_to, threads_i_started_with, threads_both_spoke FROM s_addr_signals")}
    shared = _shared_events(con)
    out = []
    for aid, key, name in con.execute(
            "SELECT t.id, t.key, t.name FROM kg_things t WHERE t.kind='address' AND EXISTS ("
            " SELECT 1 FROM kg_facts f WHERE f.thing_id=t.id AND f.fact_key='sender_kind' AND f.value='unknown' AND f.replaced_by IS NULL)"):
        addr = name.lower()
        _a, mf, rt, started, both = sig.get(addr, (addr, 0, 0, 0, 0))
        sh = shared.get(addr, 0)
        if not (rt or started or sh):
            continue
        why = []
        if rt:
            why.append("you wrote to them %d time(s)" % rt)
        if started:
            why.append("you started %d thread(s) with them" % started)
        if both:
            why.append("%d thread(s) you both spoke in" % both)
        if sh:
            why.append("%d shared calendar event(s)" % sh)
        score = 2 * both + rt + 3 * sh + 0.5 * math.log2(1 + mf)
        org = con.execute("SELECT o.key, o.name FROM kg_links l JOIN kg_things o ON o.id=l.to_id WHERE l.from_id=? AND l.kind='belongs_to' "
                          "AND l.replaced_by IS NULL ORDER BY l.id LIMIT 1", (aid,)).fetchone()
        guess = "probably a person" + (" at %s" % org[1] if org else "") + " (best guess, not stored)"
        out.append({"address": addr, "key": key, "organization": org[1] if org else None, "organization_key": org[0] if org else None,
                    "score": round(score, 3), "why": why, "guess": guess})
    out.sort(key=lambda d: (-d["score"], d["address"]))
    return out[:max(0, int(limit))]


def report(con):
    """counts for a result file: kind per address, bot need, organizations, question marks and those that matter"""
    c = {}
    for k, n in con.execute("SELECT f.value, count(*) FROM kg_facts f WHERE f.fact_key='sender_kind' AND f.replaced_by IS NULL GROUP BY 1"):
        c.setdefault("kind", {})[k] = n
    for k, n in con.execute("SELECT f.value, count(*) FROM kg_facts f WHERE f.fact_key='bot_need' AND f.replaced_by IS NULL GROUP BY 1"):
        c.setdefault("bot_need", {})[k] = n
    for k, n in con.execute("SELECT f.certainty, count(*) FROM kg_facts f WHERE f.fact_key='bot_need' AND f.replaced_by IS NULL GROUP BY 1"):
        c.setdefault("bot_need_certainty", {})[k] = n
    c["organizations_from_domains"] = con.execute("SELECT count(*) FROM thing_keys WHERE made_from LIKE 'domain-org:%'").fetchone()[0]
    c["question_marks_matter"] = len(onboarding_questions(con, 10 ** 6))
    return c


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", required=True, help="always a COPY until the live deploy")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=30)
    a = ap.parse_args(argv)
    import db
    path = os.path.abspath(a.db)
    if path == os.path.abspath(db.DEFAULT_PATH):
        raise SystemExit("refusing the LIVE rig.db: pass a copy")
    con = db.connect(path)
    con.isolation_level = None
    if a.apply:
        con.execute("BEGIN IMMEDIATE")
        try:
            print(json.dumps(build_senders(con), sort_keys=True))
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    else:
        print("dry run: pass --apply to build on this copy")
    print(json.dumps(report(con), sort_keys=True))
    for q in onboarding_questions(con, a.limit):
        print(q["score"], q["address"], "|", q["organization"], "|", "; ".join(q["why"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

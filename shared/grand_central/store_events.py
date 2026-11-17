"""store_events.py: events built by code from the calendar mirror (Phase 3 step 3.2; Vision 3.7.3, 3.7.4 rules 1, 5, 7).

build_events(con) makes ONE `event` thing per calendar_events row, key event:calendar:<calendar id>, and keeps it in step with the
mirror. Con-taking core; callers go through store.build_events() (or pull.py / rebuild_model, which hold their own connection).

What it writes (all who='code', certainty 'sure', source_ref 'calendar:<id>'; nothing guessed):
  - the thing: name = the title (changes freely), starts_at / ends_at columns = a copy of the current time;
  - facts starts_at, ends_at, place, event_status: a change is a NEW fact and the old one is kept (assert_fact supersedes), never an
    in-place edit; an unchanged value writes nothing (that is what makes a re-run a no-op);
  - one `involves` link per attendee (event -> person, or event -> address). The organizer is included, with role 'organizer'.
An attendee is linked to a PERSON only under the admission rule (Vision 3.7.4 rule 1):
  1. the address already has a current address_of link to a person written by him or by code (his confirmation, the old address book);
  2. it is on his starter list (setup/leans.json starter_people);
  3. real two-way history in the mail: a thread where they wrote AND he sent to them, and the address is not bulk or automated.
Anything else stays an address (event -> address:<addr>). When history later qualifies it, the new person link is added and the old
address link is ended (kept, replaced_by points at the new one). Bulk / automated senders are never made people by this code.
Projects: this code never writes part_of. An event belongs to a project only on his word (a confirmation through record_answer, which
rebuild replays); a calendar entry gives no code-certain way to know, so nothing is stored and nothing is asked.
The rebuild reproduces all of it: the keys are deterministic, a person minted here is recorded in thing_keys with made_from
'event-admit:<address>' and reused, and the mirror plus the mail are the record.
"""
import json
import os
import re
import secrets

import store_graph as sg

HERE = os.path.dirname(os.path.abspath(__file__))
ME = "person:me"
SHARED_MIN = 2         # rule 2: at least this many real shared calendar events
ATTENDEE_CAP = 10      # rule 2: an invite with more people than this (organizer included) is a mass invite and does not count
BOT_LOCAL = re.compile(r"(^|[._+-])(no-?reply|do-?not-?reply|donotreply|notifications?|alerts?|automated|mailer-daemon|postmaster|bounces?|"
                       r"newsletters?|news|digest|updates?|lists?|listserv|mailing|marketing|promo(tions?)?|receipts?|billing|invoices?|"
                       r"calendar|bot|system|admin|webmaster)($|[._+0-9-])")
BOT_DOMAIN = re.compile(r"(^|\.)(resource|group)\.calendar\.google\.com$|(^|\.)(mailchimp|sendgrid|mandrillapp|amazonses|bounce\.)")
ROLE_LOCAL = re.compile(r"^(contact|contacts|info|hello|hi|hey|team|support|help|helpdesk|sales|office|mail|enquiries|inquiries|service|services|"
                        r"press|media|hr|jobs|careers|feedback|orders|booking|bookings|reservations|accounts|finance|general|welcome|"
                        r"weekend|weekly|monthly|daily)([._+0-9-].*)?$")
# Rule 3 counts only what he said ABOUT a person. A filter ruling that sends mail to the bin does not name anyone.
JUNK_FACTS = {("destination", v) for v in ("trash", "junk", "spam", "promos", "archive")} | {("inbox", "skip"), ("need", "nothing")}
JUNK_LABELS = {"notifications", "commercial", "receipts", "promotions", "newsletters", "junk", "spam", "trash", "updates", "social", "forums"}
NOT_ABOUT_LINKS = ("applies_to",)   # a rule applying to an address: a filter ruling, not a person fact
AUTO_SHARE = 0.5   # same cut the standing score uses (automated_share): at least this share of their mail bulk = automated


def _addr_list(s):
    try:
        v = json.loads(s) if s else []
    except (TypeError, ValueError):
        return []
    return [str(x).strip().lower() for x in v if x and str(x).strip()] if isinstance(v, list) else []


def starter_people(path=None):
    if path is None:
        import gc_settings
        path = gc_settings.setup_path("leans.json")
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except (OSError, ValueError):
        return set()
    out = set()
    for a in doc.get("starter_people") or []:
        a = a.get("address") if isinstance(a, dict) else a
        if isinstance(a, str) and a.strip():
            out.add(a.strip().lower())
    return out


def _ready(con):
    """False on a database that has no model tables yet (a bare test file) or no migration 022: nothing to do, not an error."""
    need = {"kg_vocab", "kg_links", "calendar_events"}
    have = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not need <= have:
        return False
    return con.execute("SELECT 1 FROM kg_vocab WHERE list='thing_kind' AND value='event'").fetchone() is not None


def _current_fact(con, tid, key):
    r = con.execute("SELECT value FROM kg_facts WHERE thing_id=? AND fact_key=? AND replaced_by IS NULL ORDER BY id DESC LIMIT 1",
                    (tid, key)).fetchone()
    return r[0] if r else None


def is_role_inbox(addr):
    """a generic shared inbox (contact@, info@, hello@, team@, support@ ...): not a person unless HE named it (rule 3)"""
    return bool(ROLE_LOCAL.match(addr.lower().partition("@")[0]))


def looks_automated(addr):
    """list / bot / notification / room check, by name only (applied to every automatic admission, all three rules)"""
    import scorecard
    local, _, dom = addr.lower().partition("@")
    return bool(scorecard._is_auto_addr(addr) or BOT_LOCAL.search(local) or local.endswith(("list", "lists", "noreply")) or BOT_DOMAIN.search(dom))


class _People:
    """Resolves one attendee address to a person (id) or None. Mail history is loaded only if somebody needs it.
    A contact becomes a person if ANY of: (1) they wrote and he answered, not bulk; (2) they shared SHARED_MIN or more real
    calendar events with him (no mass invites over ATTENDEE_CAP, no room/resource calendars, no cancelled entries; the mirror holds
    no accept status, so 'never accepted' cannot be checked); (3) he named them (his starter list, or any current owner fact or link
    on them), or they are already a person (the existing ones stay). Every automatic admission also passes looks_automated(); a generic role inbox (is_role_inbox) needs rule 3."""

    def __init__(self, con, starters):
        self.con, self.starters, self.mb, self.admitted = con, starters, None, 0
        self.me_id = (sg.thing_by_key(con, ME) or {}).get("id")
        self.cache, self.stats, self.excluded = {}, {1: set(), 2: set(), 3: set()}, {}
        self.existing = set()
        self.has_retired = any(r[1] == 'retired_at' for r in con.execute("PRAGMA table_info(kg_things)"))
        self.shared = None

    def _mailbox(self):
        if self.mb is None:
            import scorecard
            self.mb = scorecard.Mailbox.load(self.con)
        return self.mb

    def known(self, addr):
        """person id from an existing current address_of link written by him or by code (never an AI guess)"""
        r = self.con.execute(
            "SELECT p.id FROM kg_things ad JOIN kg_links l ON l.from_id=ad.id AND l.kind='address_of' AND l.replaced_by IS NULL "
            "AND l.who IN ('owner','code') JOIN kg_things p ON p.id=l.to_id AND p.kind='person' "
            "WHERE ad.key=? ORDER BY l.id LIMIT 1", (sg.thing_key("address", addr),)).fetchone()
        return r[0] if r else None

    def two_way(self, addr):
        mb = self._mailbox()
        both = mb.wrote_in.get(addr, set()) & mb.sent_to_in.get(addr, set())
        if not both:
            return False
        theirs = mb.from_msgs.get(addr, [])
        return not (theirs and sum(1 for m in theirs if m["bulk"]) / len(theirs) >= AUTO_SHARE)

    def shared_count(self, addr):
        if self.shared is None:
            self.shared = {}
            for att, org, st in self.con.execute("SELECT attendee_emails, organizer_email, status FROM calendar_events"):
                if str(st or "").lower() == "cancelled":
                    continue
                people = set(_addr_list(att)) | ({org.strip().lower()} if org and org.strip() else set())
                if len(people) > ATTENDEE_CAP:
                    continue
                for a in people:
                    if not BOT_DOMAIN.search(a.partition("@")[2]):
                        self.shared[a] = self.shared.get(a, 0) + 1
        return self.shared.get(addr, 0)

    def named(self, addr):
        """he named them: his starter list, or something he said ABOUT the address that is not a filter ruling to bin it
        (a relationship, role, grade, a label that keeps them in a real desk, a note; an AI guess does not count)"""
        if addr in self.starters:
            return True
        key = sg.thing_key("address", addr)
        for fk, val in self.con.execute(
                "SELECT f.fact_key, f.value FROM kg_facts f JOIN kg_things ad ON ad.id=f.thing_id "
                "WHERE ad.key=? AND f.who='owner' AND f.replaced_by IS NULL", (key,)):
            if (fk, str(val).strip().lower()) in JUNK_FACTS or (fk == "label" and str(val).strip().lower() in JUNK_LABELS):
                continue
            return True
        return self.con.execute(
            "SELECT 1 FROM kg_links l JOIN kg_things ad ON (ad.id=l.from_id OR ad.id=l.to_id) WHERE ad.key=? AND l.who='owner' "
            "AND l.replaced_by IS NULL AND l.kind NOT IN (%s) LIMIT 1" % ",".join("'%s'" % k for k in NOT_ABOUT_LINKS), (key,)).fetchone() is not None

    def is_me(self, addr):
        return addr in self._mailbox().me

    def person_for(self, addr):
        """-> person thing id, or None (the address stays an address)"""
        if addr not in self.cache:
            self.cache[addr] = self._decide(addr)
        return self.cache[addr]

    def verdict(self, addr):
        """-> (rules that hold, excluded?) for an address, ignoring whether it is a person already"""
        rules = {1: self.two_way(addr), 2: self.shared_count(addr) >= SHARED_MIN, 3: self.named(addr)}
        hit = [r for r, ok in rules.items() if ok]
        out = bool(hit) and (looks_automated(addr) or (is_role_inbox(addr) and not rules[3]))   # a role inbox passes only when he named it
        return hit, out

    def _decide(self, addr):
        pid = self.known(addr)
        if pid:
            self.existing.add(addr)
            return pid
        if self.me_id and self.is_me(addr):
            return self.me_id
        hit, out = self.verdict(addr)
        if not hit:
            return None
        if out:
            self.excluded[addr] = hit
            return None
        for r in hit:
            self.stats[r].add(addr)
        return self._admit(addr)

    def _admit(self, addr):
        made_from = "event-admit:" + addr
        r = self.con.execute("SELECT key FROM thing_keys WHERE made_from=?", (made_from,)).fetchone()
        key = r[0] if r else "person:" + secrets.token_hex(6)
        if not r:   # record the key first, with the precise reason, so the generic trigger leaves it alone
            self.con.execute("INSERT INTO thing_keys(key, kind, made_from, created_at) VALUES(?,?,?,?)", (key, "person", made_from, sg._ts()))
        pid = sg.thing(self.con, "person", addr, created_by="code", key=key)
        if self.has_retired and self.con.execute("SELECT 1 FROM kg_things WHERE id=? AND retired_at IS NOT NULL AND merged_into IS NULL", (pid,)).fetchone():
            self.con.execute("UPDATE kg_things SET retired_at=NULL WHERE id=?", (pid,))   # qualifies again: back, same key
        aid = sg.thing(self.con, "address", addr)
        sg.add_link(self.con, aid, "address_of", pid, "code", "sure", "code", made_from)
        self.admitted += 1
        return pid


def _end_link(con, link_id, replaced_by=None):
    """Retire a link, never delete it. Replaced by a newer row when there is one, else pointing at itself (the same
    'stored already superseded' form the facts use), so it leaves the current picture and stays on the record."""
    con.execute("UPDATE kg_links SET replaced_by=?, true_until=COALESCE(true_until, ?) WHERE id=?",
                (replaced_by or link_id, sg._ts()[:10], link_id))


def _retire_unqualified(con, people):
    """Admission is re-evaluated every run: a person THIS code made from an event address who no longer qualifies under the rules
    is retired (retired_at; never deleted), unless he has said something about them himself. Their address link is ended and kept;
    the events then point at the address again. Persons from the old address book, his confirmations or a merge are never touched."""
    if not people.has_retired:
        return []
    out = []
    for pid, key, made_from in con.execute(
            "SELECT t.id, t.key, k.made_from FROM kg_things t JOIN thing_keys k ON k.key=t.key WHERE k.made_from LIKE 'event-admit:%' "
            "AND t.retired_at IS NULL AND t.merged_into IS NULL ORDER BY t.id").fetchall():
        addr = made_from.split(":", 1)[1]
        hit, excluded = people.verdict(addr)
        if hit and not excluded:
            continue
        if con.execute("SELECT 1 FROM kg_facts WHERE thing_id=? AND who='owner' AND replaced_by IS NULL UNION ALL "
                       "SELECT 1 FROM kg_links WHERE (from_id=? OR to_id=?) AND who='owner' AND replaced_by IS NULL LIMIT 1", (pid, pid, pid)).fetchone():
            continue
        con.execute("UPDATE kg_things SET retired_at=? WHERE id=?", (sg._ts(), pid))
        for (lid,) in con.execute("SELECT id FROM kg_links WHERE to_id=? AND kind='address_of' AND who='code' AND replaced_by IS NULL", (pid,)).fetchall():
            _end_link(con, lid)
        out.append(addr)
    return out


def build_events(con, starters=None):
    """Bring every event thing in step with calendar_events. Idempotent. The caller owns the transaction and the lock.
    -> counts, or {"skipped": why} when migration 022 is not applied."""
    if not _ready(con):
        return {"skipped": "no event kind yet (migration 022 not applied)"}
    starters = starter_people() if starters is None else {a.lower() for a in starters}
    people = _People(con, starters)
    retired = _retire_unqualified(con, people)
    c = {"retired_persons": retired, "events": 0, "new": 0, "moved": 0, "renamed": 0, "status_changed": 0, "links_added": 0, "links_ended": 0,
         "to_person": 0, "to_address": 0, "people_made": 0}
    rows = con.execute("SELECT id, start, end, status, organizer_email, attendee_emails, summary, location "
                       "FROM calendar_events ORDER BY id").fetchall()
    for eid, start, end, status, org, att, summary, loc in rows:
        key = "event:calendar:%s" % eid
        name = (summary or "").strip() or "(no title)"
        had = sg.thing_by_key(con, key)
        tid = sg.thing(con, "event", name, created_by="code", key=key)
        c["events"] += 1
        if not had:
            c["new"] += 1
        elif had["name"] != name:
            con.execute("UPDATE kg_things SET name=? WHERE id=?", (name, tid))
            c["renamed"] += 1
        ref = "calendar:%s" % eid
        for fk, val in (("starts_at", start), ("ends_at", end), ("event_status", status), ("place", (loc or "").strip() or None)):
            cur = _current_fact(con, tid, fk)
            if val is None or not str(val).strip():
                if cur is not None:   # the mirror no longer says it: retire the fact (kept, pointing at itself), as for a removed attendee
                    con.execute("UPDATE kg_facts SET replaced_by=id WHERE thing_id=? AND fact_key=? AND replaced_by IS NULL", (tid, fk))
                continue
            if cur != str(val).strip():
                sg.assert_fact(con, tid, fk, val, "code", "sure", "code", ref)
                if fk in ("starts_at", "ends_at") and cur is not None:
                    c["moved"] += 1
                if fk == "event_status" and cur is not None:
                    c["status_changed"] += 1
        con.execute("UPDATE kg_things SET starts_at=?, ends_at=? WHERE id=? AND (starts_at IS NOT ? OR ends_at IS NOT ?)",
                    (start, end, tid, start, end))
        # attendees -> desired links (target thing id -> (role, address))
        want = {}
        order = ([(org.strip().lower(), "organizer")] if org and org.strip() else []) + [(a, None) for a in _addr_list(att)]
        for addr, role in order:
            pid = people.person_for(addr)
            if pid:
                tgt, kind = pid, "to_person"
            else:
                tgt, kind = sg.thing(con, "address", addr), "to_address"
            if tgt not in want:
                want[tgt] = (role, addr, kind)
            elif role and not want[tgt][0]:
                want[tgt] = (role, want[tgt][1], want[tgt][2])
        have = con.execute("SELECT id, to_id, who, role FROM kg_links WHERE from_id=? AND kind='involves' AND replaced_by IS NULL",
                           (tid,)).fetchall()
        have_to = {h[1] for h in have}
        added = {}
        for tgt, (role, addr, kind) in want.items():
            if tgt in have_to:
                continue
            added[addr] = sg.add_link(con, tid, "involves", tgt, "code", "sure", "code", ref, role=role)
            c["links_added"] += 1
            c[kind] += 1
        for lid, to_id, who, _role in have:
            if who != "code" or to_id in want:
                continue   # his own links are never touched; wanted ones stay
            addr = con.execute("SELECT t.key, t.kind FROM kg_things t WHERE t.id=?", (to_id,)).fetchone()
            newer = None
            if addr and addr[1] == "address":
                newer = added.get(addr[0].split(":", 1)[1])
            _end_link(con, lid, newer)
            c["links_ended"] += 1
    c["people_made"] = people.admitted
    c["already_persons"] = len(people.existing)
    c["by_rule"] = {"1_two_way_mail": len(people.stats[1]), "2_shared_events": len(people.stats[2]), "3_named_by_him": len(people.stats[3])}
    c["excluded_automated"] = {a: sorted(r) for a, r in sorted(people.excluded.items())}
    return c

# retiring: kept only for gc-daily's proposals until Phase 5
"""stitch.py: step 3. Rule-based episodes. Certain joins first (same thread; same sender address within 14 days),
then three triggers open an episode:
  calendar   a calendar event in the window; mail from its attendees' exact addresses (event_start-14d .. event_end+3d)
             joins by thread          key episode:<D>:<event_id>
  job        a job phrase in a subject (keyword facts 'job_phrases=...' on world:world)   key episode:job:<thread_id>
  person     mail from an address marked important (the address, its domain, or the person it is address_of)
                                                                                         key episode:person:<address>
                                                                         (person episodes are never merged)
  task       STEP 6b. Tasks are members and can start an episode: an open task with a due date, or one naming a place or
             a trip. Tasks sharing a place / airline / country / trip word (or a proper name with due dates within
             JOIN_DAYS) are ONE episode (episode:trip:<first task item> when travel words are involved, else
             episode:task:<first task item>). Calendar entries and mail join it on a date window plus matching words.
  solo       a calendar entry with no attendees and no mail, in the next calendar_focus_days or the last NEAR_BACK_DAYS,
             is back as its own episode (a repeating series stays one)                  key episode:<D>:<series>
<D> is the setup value default_desk (the stored key format of an existing install is kept; no migration).
Links go to EXACT addresses only, never to a whole domain. Re-running deletes its own facts/links (source_ref
'engine:stitch') first and rebuilds them; the episode thing rows stay."""
import datetime as dt
import re

import common as C
import gc_settings
import store_graph as sg


def _cal_prefix():
    """The middle of a calendar episode key: the default desk name (setup value default_desk)."""
    return gc_settings.default_desk()


REF = "engine:stitch"
# Phase 2 step 2.5 (the owner's 2026-11-15 ruling: the database holds only indisputable facts and what he has confirmed): the
# episodes this step works out are machine guesses ("likely"), so they are NOT stored as things, facts or links, and the
# earlier rows are left alone (retired by world_model/retire_machine_guesses.py, never deleted). True only to test the old path.
STORE_GUESSES = False
JOIN_DAYS = 14
INSTANCE_SUFFIX = re.compile(r"_\d{8}(T\d{6}Z)?$")
NEAR_BACK_DAYS = 7
PAD_DAYS = 14        # calendar / mail join a task episode inside its dated span widened by this many days

# ---- words (step 6b). A "key" is a place, airline or country the text names; keys are what tasks join on.
# The place, airport, airline and travel-only vocabularies are the person's own: setup gc.json "trip_words" (read through
# gc_settings.trip_words()); the engine ships none. An empty vocabulary just means no place keys are found.
_TRIP_WORDS = ("trip", "flight", "flights", "airport", "airline", "itinerary", "visa", "esim", "esims", "passport", "layover",
               "boarding", "hotel", "arrival card", "travel insurance", "travel notice", "immigration", "booking")
STOP = frozenset("""a an the and or for to of on in at by with from into this that these those call send check get buy make pick
add set file book find look pay open order fix clean reach out about before after next last new old all any one two
january february march april may june july august september october november december monday tuesday wednesday thursday
friday saturday sunday important optional please google gmail email mail asap""".split())
_WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
_CODE = re.compile(r"\b[A-Z]{3}\b")
_VOCAB_CACHE = {}


class _Vocab(object):
    """The person's trip vocabulary, compiled once per setup file (re-read when gc.json changes)."""
    def __init__(self, tw):
        self.city_country = dict(tw["city_country"])
        self.home_places = dict(tw["home_places"])
        self.airports = dict(tw["airports"])
        self.airlines = tuple(tw["airlines"])
        self.travel_only = dict(tw["travel_only"])
        self.trip_words = _TRIP_WORDS + tuple(tw["home_airports"])
        names = sorted((re.escape(k) for k in list(self.city_country) + list(self.home_places) + list(self.airlines)),
                       key=len, reverse=True)
        self.pair = re.compile(r"\b(?:%s)\b" % "|".join(names), re.I) if names else None


def _vocab():
    tw = gc_settings.trip_words()
    key = repr(sorted((k, repr(v)) for k, v in tw.items()))
    v = _VOCAB_CACHE.get(key)
    if v is None:
        v = _VOCAB_CACHE[key] = _Vocab(tw)
    return v


def _words(text):
    """-> (keys, trip, proper). keys: place/airline/country names (airport codes and travel-only words map to their place);
    trip: True when the text uses a travel word; proper: capitalised names that are not the first word."""
    text = text or ""
    low = text.lower()
    V = _vocab()
    keys = set()
    for m in (V.pair.finditer(low) if V.pair else ()):
        w = m.group(0)
        keys.add(V.city_country.get(w) or V.home_places.get(w) or w)
        if w in V.city_country and V.city_country[w] != w:
            keys.add(w)
    for c in _CODE.findall(text):
        if c.lower() in V.airports:
            city = V.airports[c.lower()]
            keys.add(V.city_country.get(city) or V.home_places.get(city) or city)
            if city in V.city_country:
                keys.add(city)
    for w, k in V.travel_only.items():
        if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(w), low):
            keys.add(k)
    hit = lambda w: re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(w), low)   # noqa: E731
    trip = (any(k in V.airlines for k in keys) or any(hit(w) for w in V.travel_only) or any(hit(w) for w in V.trip_words)
            or any(c.lower() in V.airports for c in _CODE.findall(text)))
    proper = set()
    if not text.isupper():
        ws = [m for m in _WORD.finditer(text)]
        for n, m in enumerate(ws):
            w = m.group(0)
            if n and w[0].isupper() and len(w) >= 4 and w.lower() not in STOP:
                proper.add(w.lower())
    return keys, trip, proper


def _clean_subject(s):
    s = (s or "").strip()
    while s[:3].lower() in ("re:", "fw:") or s[:4].lower() == "fwd:":
        s = s.split(":", 1)[1].strip()
    return (s or "(no subject)")[:80]


def _job_phrases(con):
    out = []
    for f in sg.current_facts(con, "world:world", "keyword"):
        if str(f["value"]).startswith("job_phrases="):
            p = str(f["value"]).split("=", 1)[1].strip().lower()
            if p:
                out.append(p)
    return sorted(set(out))


def run(con):
    ids = C.window_ids(con)
    items = C.load_items(con, ids)
    emails = C.email_info(con, [i for i in ids if items.get(i, {}).get("kind") == "email"])
    cals = C.cal_info(con, [i for i in ids if items.get(i, {}).get("kind") == "event"])
    me = C.me_set(con)
    names = C.label_names(con)

    # clear our own earlier output (facts and links); release anything those rows had superseded
    for tbl in ("kg_facts", "kg_links") if STORE_GUESSES else ():
        con.execute("UPDATE %s SET replaced_by=NULL WHERE replaced_by IN (SELECT id FROM %s WHERE source_ref=?)" % (tbl, tbl), (REF,))
        con.execute("DELETE FROM %s WHERE source_ref=?" % tbl, (REF,))

    by_thread, by_sender = {}, {}
    for iid, em in sorted(emails.items()):
        by_thread.setdefault(em["thread_id"], []).append(iid)
        by_sender.setdefault(em["from"], []).append(iid)

    episodes = {}   # key -> dict

    def thread_items(thread_ids):
        out = set()
        for t in thread_ids:
            out.update(by_thread.get(t, []))
        return out

    def sender_join(base):
        """window mail from the same sender address within JOIN_DAYS of any base message"""
        out = set(base)
        for i in base:
            em = emails[i]
            for j in by_sender.get(em["from"], []):
                if j not in out and em["dt"] and emails[j]["dt"] and abs((emails[j]["dt"] - em["dt"]).days) <= JOIN_DAYS:
                    out.add(j)
        return out

    def add(key, trigger, name, members, window, involves):
        episodes[key] = {"trigger": trigger, "name": name[:80], "members": sorted(members), "window": window,
                         "involves": sorted(a for a in involves if a and "@" in a and a not in me)}

    def span(members):
        ds = sorted(C.day(items[i]["occurred_at"]) for i in members if items.get(i) and items[i]["occurred_at"])
        return (ds[0], ds[-1]) if ds else None

    # ---- calendar trigger. Instances of one repeating event collapse into ONE series episode (event id with the
    # _YYYYMMDD / _YYYYMMDDTHHMMSSZ suffix stripped). An event opens an episode only with an attendee who is not him,
    # or when mail joins it; a solo event with no mail stays a plain calendar item (still gathered and ranked).
    series, solo = {}, {}
    for iid, ce in sorted(cals.items()):
        if ce["status"] == "cancelled" or ce["start"] is None:
            continue
        series.setdefault(INSTANCE_SUFFIX.sub("", ce["event_id"]), []).append((iid, ce))
    for skey, insts in sorted(series.items()):
        atts, threads = set(), set()
        for iid, ce in insts:
            ia = {a for a in ce["attendees"] if a not in me}
            atts |= ia
            lo = ce["start"] - dt.timedelta(days=14)
            hi = (ce["end"] or ce["start"]) + dt.timedelta(days=3)
            for a in ia:
                for j in by_sender.get(a, []):
                    d = emails[j]["dt"]
                    if d and lo <= d <= hi:
                        threads.add(emails[j]["thread_id"])
        mail = thread_items(threads)
        if not atts and not mail:
            solo[skey] = insts
            continue
        members = mail | {iid for iid, _ in insts}
        first = min((ce for _, ce in insts), key=lambda c: c["start"])
        senders = {emails[j]["from"] for j in mail}
        add("episode:%s:%s" % (_cal_prefix(), skey), "calendar event", first["summary"] or "(no title)", members,
            (min(ce["start_date"] for _, ce in insts), max(ce["end_date"] for _, ce in insts)), atts | senders)

    # ---- job-phrase trigger
    phrases = _job_phrases(con)
    if phrases:
        for t, tids in sorted(by_thread.items()):
            hit = None
            for i in sorted(tids, key=lambda x: (emails[x]["ms"] or 0, x)):
                low = emails[i]["subject"].lower()
                p = next((p for p in phrases if p in low), None)
                if p:
                    hit = (p, i)
                    break
            if not hit:
                continue
            base = set(tids)
            members = sender_join(base)
            add("episode:job:%s" % t, "job phrase: %s" % hit[0], _clean_subject(emails[hit[1]]["subject"]), members,
                span(members), {emails[j]["from"] for j in members})

    # ---- important-person trigger
    cache = {}
    for addr in sorted(by_sender):
        if not addr or addr in me:
            continue
        facts = cache.setdefault(addr, C.sender_facts(con, addr))
        imp = C.importance_of(facts)
        if not imp or imp[0] != "high":
            continue
        base = set(by_sender[addr])
        members = base | thread_items({emails[i]["thread_id"] for i in base})
        newest = max(base, key=lambda i: (emails[i]["ms"] or 0, i))
        add("episode:person:%s" % addr, "important person: %s" % addr, emails[newest]["from_name"] or addr, members,
            span(members), {emails[j]["from"] for j in members if j in emails} | {addr})

    # (person episodes that share a thread are NOT merged: each stays its own situation)

    # ---- task trigger (step 6b): tasks are members and can start an episode
    def dd(x):
        return dt.date.fromisoformat(x) if x else None

    tasks = {i: it for i, it in items.items() if it["kind"] == "task"}
    notes = {}
    for ch in C.chunks(sorted(tasks)):
        for iid, n in con.execute("SELECT it.item_id, t.notes FROM item_task it JOIN tasks t ON t.id=it.task_id WHERE it.item_id IN (%s)"
                                  % ",".join("?" * len(ch)), ch):
            notes[iid] = (n or "")[:300]
    tk = {}
    for i, it in sorted(tasks.items()):
        keys, trip, proper = _words(it["title"] or "")
        if keys or trip or it["due_at"]:     # the note adds detail (airport codes, cities) to a task that is already a plan:
            nk, nt, _ = _words(notes.get(i, ""))    # its title names a place or trip, or it has a due date
            keys, trip = keys | nk, trip or nt
        done = str(it["status"] or "").lower() == "completed"
        tk[i] = {"keys": keys, "trip": trip, "proper": proper, "due": C.day(it["due_at"]), "done": done,
                 "seed": not done and bool(it["due_at"] or keys or trip)}
    seeds = sorted(i for i, t in tk.items() if t["seed"])
    parent = {i: i for i in tk}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    def near_due(a, b):
        da, db = dd(tk[a]["due"]), dd(tk[b]["due"])
        return bool(da and db and abs((da - db).days) <= JOIN_DAYS)

    for n, a in enumerate(seeds):
        for b in seeds[n + 1:]:
            ta, tb = tk[a], tk[b]
            shared = ta["keys"] & tb["keys"]
            if ta["trip"] or tb["trip"]:
                shared -= set(_vocab().home_places.values())     # a home city never ties a trip to his everyday errands
            if shared or (ta["trip"] and tb["trip"] and near_due(a, b)) or (ta["proper"] & tb["proper"] and near_due(a, b)):
                union(a, b)
    comps = {}
    for i in seeds:
        comps.setdefault(find(i), []).append(i)
    # tasks that cannot start an episode (undated, no place; or done) still join the episode they share a name or place with
    for i in sorted(set(tk) - set(seeds)):
        best = None
        for root, mem in sorted(comps.items()):
            ck = set().union(*[tk[m]["keys"] for m in mem])
            sc = (len(tk[i]["keys"] & ck), 0)
            if sc[0] and (best is None or sc > best[0]):
                best = (sc, root)
        if best:
            comps[best[1]].append(i)
    task_eps = {}   # key -> {"members": set, "keys", "proper", "window"}
    for root, mem in sorted(comps.items()):
        mem = sorted(mem)
        keys = set().union(*[tk[m]["keys"] for m in mem])
        proper = set().union(*[tk[m]["proper"] for m in mem])
        trip = any(tk[m]["trip"] for m in mem)
        dues = sorted(tk[m]["due"] for m in mem if tk[m]["due"])
        V = _vocab()
        places = [k for k in sorted(keys) if k in set(V.city_country.values()) or k in V.home_places.values()]
        place_counts = sorted(places, key=lambda k: (-sum(1 for m in mem if k in tk[m]["keys"]), k))
        first = min(mem, key=lambda m: (tk[m]["due"] or "9999", m))
        if trip:
            tp = [k for k in place_counts if k not in V.home_places.values()]
            name = ("Trip: " + ", ".join(k.title() for k in tp[:5])) if tp else _clean_subject(items[first]["title"])
            trig = "trip: " + (", ".join(tp[:5]) or "travel words")
            key = "episode:trip:%d" % mem[0]
        else:
            name = (place_counts[0].title() + " tasks") if len(mem) > 1 and place_counts else _clean_subject(items[first]["title"])
            trig = "task: " + ("place " + place_counts[0] if place_counts else "due date")
            key = "episode:task:%d" % mem[0]
        task_eps[key] = {"members": set(mem), "keys": keys, "proper": proper, "trip": trip, "name": name, "trigger": trig,
                         "window": (dues[0], dues[-1]) if dues else None}

    def pick(ikeys, iwords, lo_day, hi_day):
        """the task episode an item (its place keys, its words, its date span) joins: date window plus matching words"""
        best = None
        for k, te in sorted(task_eps.items()):
            if not te["window"] or not lo_day:
                continue
            lo = dd(te["window"][0]) - dt.timedelta(days=PAD_DAYS)
            hi = dd(te["window"][1]) + dt.timedelta(days=PAD_DAYS)
            if dd(hi_day) < lo or dd(lo_day) > hi:
                continue
            sc = (len(ikeys & te["keys"]), len(iwords & te["proper"]))
            if sc != (0, 0) and (best is None or sc > best[0]):
                best = (sc, k)
        return best[1] if best else None

    joined_cal = set()
    for skey, insts in sorted(solo.items()):
        text = " ".join(ce["summary"] for _, ce in insts[:1])
        ikeys, _, iprop = _words(text)
        k = pick(ikeys, iprop, min(ce["start_date"] for _, ce in insts), max(ce["end_date"] for _, ce in insts))
        if k:
            task_eps[k]["members"] |= {iid for iid, _ in insts}
            joined_cal.add(skey)
    task_mail = {}
    for iid, em in sorted(emails.items()):
        ikeys, _, iprop = _words(em["subject"])
        d = C.day(items[iid]["occurred_at"]) if items.get(iid) else None
        k = pick(ikeys, iprop, d, d)
        if k:
            task_eps[k]["members"] |= {iid}
            task_mail.setdefault(k, set()).add(iid)
    for k, te in sorted(task_eps.items()):
        mail = task_mail.get(k, set())
        members = te["members"] | thread_items({emails[j]["thread_id"] for j in mail})
        add(k, te["trigger"], te["name"], members, span(members) if not te["window"] else te["window"],
            {emails[j]["from"] for j in members if j in emails})

    # ---- solo calendar entries come back for the near view (next calendar_focus_days, last NEAR_BACK_DAYS)
    now = C.now()
    ahead = C.settings(con)["calendar_focus_days"]
    lo_t, hi_t = now - dt.timedelta(days=NEAR_BACK_DAYS), now + dt.timedelta(days=ahead)
    for skey, insts in sorted(solo.items()):
        if skey in joined_cal or not any(lo_t <= ce["start"] <= hi_t for _, ce in insts):
            continue
        first = min((ce for _, ce in insts), key=lambda c: c["start"])
        add("episode:%s:%s" % (_cal_prefix(), skey), "calendar solo: near view", first["summary"] or "(no title)", {iid for iid, _ in insts},
            (min(ce["start_date"] for _, ce in insts), max(ce["end_date"] for _, ce in insts)), set())

    # ---- thread messages for whose_move (all messages, including his own sent ones)
    all_threads = sorted({emails[i]["thread_id"] for ep in episodes.values() for i in ep["members"] if i in emails})
    newest = {}
    for ch in C.chunks(all_threads):
        q = ",".join("?" * len(ch))
        for t, mid, ms, sent in con.execute("SELECT thread_id, id, internal_date, is_sent FROM messages WHERE thread_id IN (%s)" % q, ch):
            k = (ms or 0, str(mid))
            if t not in newest or k > newest[t][0]:
                newest[t] = (k, sent)

    counts = {}
    for key in sorted(episodes):
        ep = episodes[key]
        if not STORE_GUESSES:
            counts[ep["trigger"].split(":")[0]] = counts.get(ep["trigger"].split(":")[0], 0) + 1
            continue
        tid = sg.thing(con, "episode", ep["name"], created_by="code", key=key)
        con.execute("UPDATE kg_things SET name=? WHERE id=? AND name<>?", (ep["name"], tid, ep["name"]))

        def fact(k, v):
            sg.assert_fact(con, tid, k, v, "code", "likely", "code", REF)

        fact("trigger", ep["trigger"])
        if ep["window"]:
            fact("date_window", "%s..%s" % ep["window"])
        for i in ep["members"]:
            fact("member_item", "item:%d" % i)
        mail = [i for i in ep["members"] if i in emails]
        dom = None
        for i in mail:
            d = C.domain_of_labels(emails[i]["labels"], names)
            if d:
                dom = dom or d
                if d < dom:
                    dom = d
        if dom:
            fact("domain", dom)
        ts = {emails[i]["thread_id"] for i in mail}
        sent_flags = [newest[t] for t in ts if t in newest]
        if not sent_flags:
            fact("whose_move", "nobody")
        else:
            last = max(sent_flags, key=lambda x: x[0])
            fact("whose_move", "them" if last[1] else "him")
        for a in ep["involves"]:
            aid = sg.thing(con, "address", a, created_by="code")
            sg.add_link(con, tid, "involves", aid, "code", "likely", "code", REF)
        counts[ep["trigger"].split(":")[0]] = counts.get(ep["trigger"].split(":")[0], 0) + 1
    return {"episodes": len(episodes), "by_trigger": counts}

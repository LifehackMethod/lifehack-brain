"""scorecard.py: Grand Central V2 step 3. Sender standing, the Path B attention score (outside only, no deadlines),
and Path A importance and urgency (from triage observations; importance caps urgency). Envelope facts only; no body text.

Every number comes from setup/leans.json 'proposed_points' (PROPOSED, NOT APPROVED: nothing is hard-coded here, and nothing
may be used live until the owner approves; see drafts/grand-central/bite/step-3-proposed-points.md). A score is low, medium
or high WITH reasons, never a switch. It works with no leans and no answers (empty leans = default behaviour).

Reuses from the existing ranker: the 14-day forward calendar match (signals/on_calendar_14d.py), To/Cc weighting
(signals/to_vs_cc.py), the machine-sent markers (s_machine view), and the 0..1 -> low/normal/high idea (rank.py)."""
import copy
import datetime as dt
import json
import math
import os
import statistics
import warnings

import gc_settings

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
DAY = 86400000
HOUR = 3600000
LEVELS = ("low", "medium", "high")
STOP = {"about", "after", "again", "their", "there", "these", "those", "which", "would", "could", "should", "thanks", "hello",
        "please", "today", "tomorrow", "update", "email", "review", "weekly", "meeting", "reminder", "invitation"}
BULK_LABELS = {"CATEGORY_PROMOTIONS", "CATEGORY_FORUMS"}
NOREPLY = ("noreply", "no-reply", "no.reply", "no_reply", "donotreply", "do-not-reply")


# the mailroom's root-owned settings: <gc.json mailroom_install_dir>/reader-config.json; env GC_READER_CONFIG points elsewhere (tests)
def mailroom_config_path():
    return os.path.join(gc_settings.mailroom_install_dir(), "reader-config.json")


class _Multi(list):
    """The values of a JSON key that appears more than once in the same object (json.load would keep only the last)."""


def _pairs_hook(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            d[k] = _Multi((d[k] if isinstance(d[k], _Multi) else [d[k]]) + [v])
        else:
            d[k] = v
    return d


def load_labels_doc(path):
    """setup/labels.json parsed so a label listed twice is not silently collapsed."""
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f, object_pairs_hook=_pairs_hook)
    except (OSError, ValueError) as e:
        raise SetupError("labels file %s cannot be read: %s" % (path, e))
    if not isinstance(doc, dict):
        raise SetupError("labels file %s must hold a JSON object" % path)
    return doc


def mailroom_read_labels(path=None):
    """Names the mailroom is configured to read (trimmed, lower case). None configured (no file) = empty; a file that is
    there but cannot be understood RAISES (fail closed): nobody may guess what is readable."""
    configured = path or os.environ.get("GC_READER_CONFIG")      # a path somebody NAMED must exist: never silently drop the mailroom side
    path = configured or mailroom_config_path()
    if not os.path.exists(path):
        if configured:
            raise SetupError("mailroom config %s was named but is missing: refusing to guess which labels are readable" % path)
        return set()                                              # only the built-in default location may be absent (not installed yet)
    try:
        with open(path, encoding="utf-8") as f:
            names = json.load(f)["read_labels"]
        if not isinstance(names, list) or not all(isinstance(x, str) for x in names):
            raise ValueError("read_labels must be a list of text")
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise SetupError("mailroom config %s is there but cannot be read (%s): refusing to guess which labels are readable" % (path, e))
    return {x.strip().lower() for x in names}


def decide_read_labels(labels_doc, mailroom=()):
    """THE one place that decides which labels are readable. Returns (readable, refuse, warnings), names trimmed and lower-cased.
    A label counts only when 'read' is exactly true. readable = unanimous (what the scorecard uses to route mail to Path A);
    refuse = readable plus any label ANY listing of which says true (conflicting duplicates, the {"X": true} shorthand),
    plus the mailroom's configured labels: the staged lane refuses every name in it (the refusal side fails closed)."""
    lbl = labels_doc.get("labels") or {}
    if not isinstance(lbl, dict):
        raise SetupError("labels.json 'labels' must be an object keyed by label name")
    votes, warn = {}, []
    for name, raw in lbl.items():
        for v in (raw if isinstance(raw, _Multi) else [raw]):
            key = str(name).strip().lower()
            if v is True:
                votes.setdefault(key, []).append(True)
                continue
            if not isinstance(v, dict):
                raise SetupError("labels.json entry %r must be an object (got %r)" % (name, v))
            r = v.get("read")
            votes.setdefault(key, []).append(r is True)
            if r is not True and r not in (False, None):
                warn.append("labels.json label %r: 'read' is %r, not true or false; treated as NOT readable (fail closed)" % (name, r))
    mail = {str(x).strip().lower() for x in mailroom}
    readable = {k for k, vs in votes.items() if all(vs)} | mail
    refuse = {k for k, vs in votes.items() if any(vs)} | mail
    for k, vs in votes.items():
        if any(vs) and not all(vs):
            warn.append("labels.json lists label %r more than once with different 'read' settings; not routed as readable, and the staged lane refuses it" % k)
    return readable, refuse, warn


class SetupError(ValueError):
    """A missing or malformed setup file or entry. Scoring is pinned: there are no silent defaults, so it fails loudly."""


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _rd(d, name):
    path = os.path.join(d, name)
    try:
        f = open(path, encoding="utf-8")
    except FileNotFoundError:
        raise SetupError("setup file %s is missing (looked in %s); scoring is pinned, so there are no silent defaults" % (name, d))
    with f:
        try:
            v = json.load(f)
        except ValueError as e:
            raise SetupError("setup file %s is not valid JSON: %s" % (name, e))
    if not isinstance(v, dict):
        raise SetupError("setup file %s must hold a JSON object" % name)
    return v


class Config:
    """setup/*.json. points = leans.json['proposed_points']; leans = his senders/merges/starter_people.
    Validated at load: a bad file or entry raises SetupError naming it."""

    def __init__(self, leans, labels, keywords, setup_dir):
        self.warnings = []
        self.setup_dir = setup_dir
        pts = leans.get("proposed_points")
        if not isinstance(pts, dict) or not pts:
            raise SetupError("no points found in %s/leans.json ('proposed_points'): the scorecard has no hard-coded defaults" % setup_dir)
        for sect in ("standing", "attention", "path_a", "delta"):
            if not isinstance(pts.get(sect), dict):
                raise SetupError("leans.json proposed_points is missing the '%s' section" % sect)
        st = pts["standing"]
        for key, ok in (("keep_floor", lambda v: 0.40 <= v <= 0.60), ("tau_days", lambda v: v > 0), ("squash_k", lambda v: v > 0),
                        ("scale_max", lambda v: v > 0), ("episode_gap_days", lambda v: v > 0)):
            v = st.get(key)
            if not _num(v) or not ok(v):
                raise SetupError("leans.json proposed_points.standing.%s is %r: %s" % (
                    key, v, "must be between 0.40 and 0.60: his ruling is 'fade to about half, never zero'" if key == "keep_floor" else "must be a number above 0"))
        senders = {}
        raw_senders = leans.get("senders") or {}
        if not isinstance(raw_senders, dict):
            raise SetupError("leans.json 'senders' must be an object keyed by address")
        for addr, ln in raw_senders.items():
            kind = ln.get("kind") if isinstance(ln, dict) else None
            if kind not in ("floor", "set", "mute"):
                raise SetupError("leans.json lean for %r must be an object with kind floor, set or mute (got %r)" % (addr, ln))
            if kind != "mute" and not _num(ln.get("value")):
                raise SetupError("leans.json lean for %r: 'value' must be a number (got %r)" % (addr, ln.get("value")))
            senders[str(addr).strip().lower()] = ln
        merges = leans.get("merges") or []
        if not isinstance(merges, list):
            raise SetupError("leans.json 'merges' must be a list")
        for i, mg in enumerate(merges):
            if not isinstance(mg, dict) or not isinstance(mg.get("addresses"), list):
                raise SetupError("leans.json merges entry %d must be an object with an 'addresses' list" % i)
        self.leans = dict(leans, senders=senders, merges=merges)
        self.points = pts
        # ONE function decides the read labels (decide_read_labels): the scorecard, the staged lane's build and gate all use it.
        self._read, self._refuse, self.warnings_read = decide_read_labels(labels, mailroom_read_labels())
        for w in self.warnings_read:
            self.warnings.append(w)
            warnings.warn(w)
        self.labels = labels
        kw = keywords.get("lists") or {}
        if not isinstance(kw, dict):
            raise SetupError("keywords.json 'lists' must be an object")
        for name, lst in kw.items():
            if not isinstance(lst, dict) or not isinstance(lst.get("phrases"), list) or not _num(lst.get("weight", 0)) or \
                    not all(isinstance(x, str) for x in lst["phrases"]):
                raise SetupError("keywords.json list %r needs a numeric 'weight' and a 'phrases' list of text (got %r)" % (name, lst))
        self.keywords = keywords

    @classmethod
    def load(cls, setup_dir=None):
        d = setup_dir or gc_settings.setup_dir()
        lbl = _rd(d, "labels.json")
        return cls(_rd(d, "leans.json"), load_labels_doc(os.path.join(d, "labels.json")) if lbl is not None else lbl, _rd(d, "keywords.json"), d)

    def use_owner_level_points(self, con):
        """His own level weights (the owner fact `setting level_points=a,b,c` on topic level_points, recorded by the onboarding sitting)
        win over the PROPOSED numbers in leans.json, in both attention and path_a. No owner value (or an unreadable one) = the file stands."""
        lp = owner_level_points(con)
        if lp:
            self.points = copy.deepcopy(self.points)
            for sect in ("attention", "path_a"):
                self.points[sect]["level_points"] = dict(lp)
        return self

    def read_labels(self):
        """lower-cased, trimmed names of labels whose 'read' is exactly true"""
        return set(self._read)


def _addr_list(s):
    try:
        v = json.loads(s) if s else []
    except (TypeError, ValueError):
        return []
    return [str(x).strip().lower() for x in v if x] if isinstance(v, list) else []


def _is_auto_addr(a):
    a = (a or "").lower()
    return any(p in a for p in NOREPLY) or a.startswith(("notification", "alert", "automated"))


class Mailbox:
    """The envelope facts, indexed once. Pure reads."""

    @classmethod
    def load(cls, con):
        self = cls()
        self.names = {r[0]: r[1] for r in con.execute("SELECT id, name FROM labels")}
        self.msgs, self.by_id, self.by_thread = [], {}, {}
        self.skipped_ids = []
        rows = con.execute(
            "SELECT id, thread_id, internal_date, label_ids, lower(from_addr), to_addrs, cc_addrs, subject, is_sent, list_id, "
            "list_unsubscribe_present, precedence, auto_submitted, dmarc_pass, dkim_pass, spf_pass FROM messages "
            "ORDER BY internal_date, id").fetchall()
        for r in rows:
            if isinstance(r[2], bool) or not isinstance(r[2], (int, float)) or not math.isfinite(r[2]):
                self.skipped_ids.append(r[0])   # a bad or missing date: skipped and counted, never a crash
                continue
            try:
                lab = json.loads(r[3]) if r[3] else []
            except ValueError:
                lab = []
            lab = lab if isinstance(lab, list) else []
            frm = r[4] or ""
            bulk = bool(r[9]) or bool(r[10]) or (r[11] in ("bulk", "list", "junk")) or (r[12] not in (None, "", "no")) \
                or _is_auto_addr(frm) or bool(BULK_LABELS & set(lab))
            m = {"id": r[0], "thread": r[1] or "__nothread__" + str(r[0]), "ms": int(r[2]), "label_ids": lab,
                 "label_names": {str(self.names.get(x, x)).strip().lower() for x in lab},
                 "frm": frm, "to": _addr_list(r[5]), "cc": _addr_list(r[6]), "subject": r[7] or "", "sent": bool(r[8]), "bulk": bulk,
                 "personal": "CATEGORY_PERSONAL" in lab, "auth_ok": r[13] == 1}   # standing only when DMARC passes (ruled): a DKIM pass alone is not enough
            self.msgs.append(m)
            self.by_id[m["id"]] = m
            self.by_thread.setdefault(m["thread"], []).append(m)
        self.skipped_rows = len(self.skipped_ids)
        self.me = {m["frm"] for m in self.msgs if m["sent"] and m["frm"]}
        self.wrote_in, self.sent_to_in, self.from_msgs, self.first_sent_to = {}, {}, {}, {}
        for m in self.msgs:
            if m["sent"]:
                for a in set(m["to"]) | set(m["cc"]):
                    self.sent_to_in.setdefault(a, set()).add(m["thread"])
                    self.first_sent_to.setdefault(a, m["ms"])
            elif m["frm"]:
                self.wrote_in.setdefault(m["frm"], set()).add(m["thread"])
                self.from_msgs.setdefault(m["frm"], []).append(m)
        self.events = []
        for eid, start, status, att, org, summ in con.execute(
                "SELECT id, start, status, attendee_emails, organizer_email, summary FROM calendar_events"):
            try:
                s = dt.datetime.fromisoformat(str(start).replace("Z", "+00:00"))
                s = s if s.tzinfo else s.replace(tzinfo=dt.timezone.utc)
            except ValueError:
                continue
            if str(status or "").lower() == "cancelled":
                continue
            self.events.append({"id": eid, "ms": int(s.timestamp() * 1000), "attendees": set(_addr_list(att)) | ({org.lower()} if org else set()),
                                "summary": summ or ""})
        try:
            self.tasks = [r[0] or "" for r in con.execute("SELECT title FROM tasks WHERE lower(COALESCE(status,''))<>'completed'")]
        except Exception:
            self.tasks = []
        # levels above the person (step 3.8): sender address -> level, from the view. No view, no link or no level = not in the dict = counts for nothing.
        self.level_of = {}
        try:
            for a, lv in con.execute(
                    "SELECT lower(ad.name), v.level FROM kg_things ad JOIN kg_links l ON l.from_id=ad.id AND l.kind='address_of' AND l.replaced_by IS NULL "
                    "AND l.true_until IS NULL JOIN kg_things p ON p.id=l.to_id JOIN v_levels_above_me v ON v.person_key=p.key "
                    "WHERE ad.kind='address' AND v.level IS NOT NULL"):
                self.level_of[a] = int(lv)
        except Exception:
            self.level_of = {}
        self._cache = {}
        return self


def _confirmed_group(cfg, address):
    """the address plus any addresses merged with it by a CONFIRMED merge; unconfirmed merges are ignored"""
    group = {address}
    for m in cfg.leans.get("merges") or []:
        if m.get("confirmed") is True and address in {a.lower() for a in m.get("addresses", [])}:
            group |= {a.lower() for a in m["addresses"]}
    return group


def _w(m, addrs, P):
    """weight of one of his messages toward these addresses: To 1, Cc cc_weight, split when sent to a crowd"""
    if addrs & set(m["to"]):
        w = 1.0
    elif addrs & set(m["cc"]):
        w = P["cc_weight"]
    else:
        return None
    n = len(set(m["to"]) | set(m["cc"]))
    if n > P["big_send_over"]:
        w *= P["big_send_over"] / n
    return w


def _lg(x):
    return math.log2(1 + x)


def standing(mb, address, cfg, now_ms, auth_ok=True):
    """Sender standing 0..scale_max with raw points and plain-words reasons. Locked model: reciprocity, depth, collaboration,
    rhythm (fade to about half, never zero), reliability. Lean applied last. If the sender check failed it is 0 (his lean too:
    a forged address must not inherit a real person's standing)."""
    address = (address or "").lower()
    key = (address, bool(auth_ok), now_ms, json.dumps([cfg.points["standing"], cfg.leans.get("senders"), cfg.leans.get("merges")],
                                                      sort_keys=True, default=str))
    if key in mb._cache:
        return mb._cache[key]
    P = cfg.points["standing"]
    addrs = _confirmed_group(cfg, address)
    reasons = []
    if not auth_ok:
        out = {"standing": 0.0, "raw": 0.0, "reasons": ["couldn't confirm it's really them (sender check failed): standing not applied"],
               "automated": None, "lean": None}
        mb._cache[key] = out
        return out
    theirs = set().union(*[mb.wrote_in.get(a, set()) for a in addrs])
    his = set().union(*[mb.sent_to_in.get(a, set()) for a in addrs])
    both = theirs & his
    their_msgs = [m for a in addrs for m in mb.from_msgs.get(a, [])]
    auto = any(_is_auto_addr(a) for a in addrs) or (bool(their_msgs) and
                                                     sum(1 for m in their_msgs if m["bulk"]) / len(their_msgs) >= P["automated_share"])
    W = 0.0
    for t in both:
        ws = [w for m in mb.by_thread[t] if m["sent"] for w in [_w(m, addrs, P)] if w is not None]
        W += sum(ws[:P["per_thread_cap_msgs"]])
    un = 0.0
    for t in his - theirs:   # a big send (over big_send_over recipients) that got no reply earns nothing
        un += sum(w for m in mb.by_thread[t] if m["sent"] and len(set(m["to"]) | set(m["cc"])) <= P["big_send_over"]
                  for w in [_w(m, addrs, P)] if w is not None)
    W += min(P["unanswered_cap"], P["unanswered_weight"] * un)
    T = 0.0
    D = 0.0
    I = 0.0
    delays = []
    for t in both:
        th = mb.by_thread[t]
        ns = [len(set(m["to"]) | set(m["cc"])) for m in th if m["sent"] and _w(m, addrs, P) is not None]
        f = min(1.0, P["big_send_over"] / max(ns)) if ns and max(ns) > P["big_send_over"] else 1.0   # crowd send: discount breadth too
        T += f
        mine = sum(1 for m in th if m["sent"])
        them = sum(1 for m in th if m["frm"] in addrs and not m["sent"])
        if len(th) >= P["deep_thread_min_msgs"] and mine >= P["deep_thread_min_each_side"] and them >= P["deep_thread_min_each_side"]:
            D += f
        if th[0]["sent"]:
            I += f
        pend = None
        for m in th:
            if not m["sent"] and m["frm"] in addrs:
                pend = pend if pend is not None else m["ms"]
            elif m["sent"] and pend is not None and _w(m, addrs, P) is not None:
                delays.append(m["ms"] - pend)
                pend = None
    C = 0
    if T >= 1 and not auto:
        for e in mb.events:
            if (addrs & e["attendees"]) and (mb.me & e["attendees"]):
                C += 1
    R = len(their_msgs)
    parts = []   # (points, text)
    if W:
        parts.append((P["depth_weight"] * _lg(W), "you have written to them about %d times" % round(W)))
    if T:
        parts.append((P["breadth_weight"] * _lg(T), "real two-way exchanges in %d conversation%s" % (max(1, round(T)), "" if round(T) <= 1 else "s")))
    if D:
        parts.append((P["deep_thread_weight"] * _lg(D), "%d long back-and-forth thread%s (working together)" % (max(1, round(D)), "" if round(D) <= 1 else "s")))
    if C:
        parts.append((P["calendar_weight"] * _lg(C), "%d shared calendar event%s" % (C, "" if C == 1 else "s")))
    if I:
        parts.append((P["initiation_weight"] * _lg(I), "you started %d conversation%s they answered" % (max(1, round(I)), "" if round(I) <= 1 else "s")))
    if len(delays) >= P["speed_min_answers"]:
        med = statistics.median(delays)
        sb = P["speed_bonus"]
        bonus = sb["le_1h"] if med <= HOUR else sb["le_6h"] if med <= 6 * HOUR else sb["le_24h"] if med <= 24 * HOUR else 0.0
        if bonus:
            parts.append((bonus, "you usually answer them within %d hours" % max(1, round(med / HOUR))))
    if R and W:
        parts.append((min(P["inbound_cap"], P["inbound_weight"] * _lg(min(R, W))), "they write to you (counts for little)"))
    started = [t for t in theirs if mb.by_thread[t][0]["frm"] in addrs and not mb.by_thread[t][0]["sent"] and mb.me & set(mb.by_thread[t][0]["to"])]
    if len(started) >= P["reliability_min_threads"]:
        answered = sum(1 for t in started if any(m["sent"] for m in mb.by_thread[t]))
        if answered / len(started) >= P["reliability_min_share"]:
            parts.append((P["reliability_bonus"], "you reliably answer them (%d of %d conversations)" % (answered, len(started))))
    raw_sum = sum(p for p, _ in parts)
    if auto:
        raw_sum = min(raw_sum, P["automated_cap"])
        reasons_guard = "automated sender (no-reply or bulk headers): capped at %.1f points" % P["automated_cap"]
    # rhythm: fade, never to zero, grace for on-and-off people
    ts = sorted(m["ms"] for t in both for m in mb.by_thread[t]) if both else sorted(m["ms"] for m in their_msgs)
    quiet = max(0.0, (now_ms - ts[-1]) / DAY) if ts else 0.0   # clock skew can never make the fade factor exceed 1
    grace = 0.0
    note = None
    if both:
        gap_ms = P["episode_gap_days"] * DAY
        ends, starts = [], [ts[0]]
        for a, b in zip(ts, ts[1:]):
            if b - a >= gap_ms:
                ends.append(a)
                starts.append(b)
        if len(starts) >= 2:
            gaps = [(s - e) / DAY for e, s in zip(ends, starts[1:])]
            grace = P["grace_factor"] * statistics.median(gaps)
            note = "usually back every ~%d days" % round(statistics.median(gaps))
    q_eff = 0.0 if (grace and quiet <= grace) else (quiet - grace if grace else quiet)
    keep = P["keep_floor"] + (1 - P["keep_floor"]) * math.exp(-q_eff / P["tau_days"])
    raw = raw_sum * keep
    st = P["scale_max"] * (1 - math.exp(-raw / P["squash_k"]))
    for p, text in sorted(parts, key=lambda x: -x[0])[:3]:
        reasons.append("%s %+.1f" % (text, p))
    if parts:
        if note and q_eff == 0:
            reasons.append("on-and-off rhythm: %s, no fading yet" % note)
        elif keep < 0.995:
            reasons.append("quiet %d days: keeping %d%% of standing (fades slowly, never to zero)" % (round(quiet), round(keep * 100)))
    else:
        reasons.append("no two-way history with this sender")
    if auto:
        reasons.append(reasons_guard)
    lean = None
    for a in sorted(addrs):
        ln = (cfg.leans.get("senders") or {}).get(a.lower())
        if ln:
            lean = ln
            break
    if lean:
        k, v = lean.get("kind"), float(lean.get("value") or 0)
        before = st
        st = max(st, v) if k == "floor" else v if k == "set" else 0.0 if k == "mute" else st
        reasons.append("lean (his own setting): %s%s: %.1f -> %.1f; reason: %s" % (
            k, " %.1f" % v if k != "mute" else "", before, st, lean.get("reason", "none given")))
    out = {"standing": round(st, 3), "raw": round(raw, 3), "reasons": reasons, "automated": auto, "lean": lean}
    mb._cache[key] = out
    return out


# ---- routing -----------------------------------------------------------------------------------------------------
def route(mb, msg_id, cfg):
    """A if the mail sits in a read label (goes straight to the mailroom), else B (outside-only attention score)"""
    return "A" if mb.by_id[msg_id]["label_names"] & cfg.read_labels() else "B"


def owner_level_points(con):
    """{'1':x,'2':y,'3_or_more':z} from his owner fact, else None. Read only."""
    try:
        r = con.execute("SELECT f.value FROM kg_current_facts f JOIN kg_things t ON t.id=f.thing_id WHERE t.key='topic:level_points' "
                        "AND f.fact_key='setting' AND f.who='owner' ORDER BY f.id DESC LIMIT 1").fetchone()
        if not r or not str(r[0]).startswith("level_points="):
            return None
        nums = [float(x) for x in str(r[0]).split("=", 1)[1].split(",")]
    except Exception:  # noqa: BLE001  (no graph tables / a bad value: the proposal stands)
        return None
    return dict(zip(("1", "2", "3_or_more"), nums)) if len(nums) == 3 and all(math.isfinite(x) for x in nums) else None


def level_points(P, level):
    """Points for a level above him, from his settings (P['level_points'] = {'1','2','3_or_more'}). Unknown (None), 0 (a peer) or a
    missing setting = 0: never a guess. The same whatever the source of the level (owner or chain)."""
    lp = P.get("level_points") or {}
    if not isinstance(level, int) or isinstance(level, bool) or level < 1:
        return 0.0
    v = lp.get(str(level) if level < 3 else "3_or_more", 0.0)
    return float(v) if _num(v) else 0.0


def _level(x, medium_at, high_at):
    return "high" if x >= high_at else "medium" if x >= medium_at else "low"


def _words(s):
    return {w for w in "".join(c.lower() if c.isalnum() else " " for c in s).split() if len(w) >= 5 and w not in STOP}


def attention_score(mb, msg_id, cfg, now_ms):
    """Path B only. Outside facts: standing, a person writing to him, something happening now, calendar/task match,
    subject keywords. No deadlines. Returns score (None for read-label mail), level, reasons, shortlist."""
    m = mb.by_id[msg_id]
    P = cfg.points["attention"]
    if route(mb, msg_id, cfg) == "A":
        hit = sorted(m["label_names"] & cfg.read_labels())[0]
        return {"route": "A", "msg_id": msg_id, "level": None, "score": None, "shortlist": False,
                "reasons": ["in read label '%s': goes straight to the mailroom; no outside attention score" % hit]}
    pts, reasons = 0.0, []
    st = standing(mb, m["frm"], cfg, now_ms, auth_ok=m["auth_ok"])
    if st["standing"] > 0 or st["lean"] or "confirm" in " ".join(st["reasons"]):
        v = P["standing_weight"] * st["standing"]
        pts += v
        reasons.append("sender standing %.1f of %.0f (%+.1f): %s" % (st["standing"], cfg.points["standing"]["scale_max"], v, "; ".join(st["reasons"])))
    lv = getattr(mb, "level_of", {}).get(m["frm"])
    lvp = level_points(P, lv)
    if lvp:
        pts += lvp
        reasons.append("sender is %s level%s above you (%+.2f)" % (lv, "" if lv == 1 else "s", lvp))
    bulk = m["bulk"] or bool(st["automated"])
    if bulk:
        pts += P["bulk_penalty"]
        reasons.append("bulk or automated mail (%+.1f)" % P["bulk_penalty"])
    else:
        if m["personal"]:
            pts += P["personal_tab"]
            reasons.append("Gmail's Personal tab (%+.1f)" % P["personal_tab"])
        if mb.me & set(m["to"]):
            pts += P["to_him"]
            reasons.append("addressed to you (%+.1f)" % P["to_him"])
        elif mb.me & set(m["cc"]):
            pts += P["cc_only"]
            reasons.append("you are only in Cc (%+.1f)" % P["cc_only"])
    th = mb.by_thread[m["thread"]]
    idx = th.index(m)
    prior = th[:idx]
    if prior and prior[-1]["sent"] and not m["sent"]:
        pts += P["reply_to_his_message"]
        reasons.append("a reply to your own message (%+.1f)" % P["reply_to_his_message"])
    elif any(x["sent"] and m["ms"] - x["ms"] <= P["active_thread_days"] * DAY for x in prior):
        pts += P["reply_in_active_thread"]
        reasons.append("a reply in a conversation you are active in (%+.1f)" % P["reply_in_active_thread"])
    dp = cfg.points["delta"]
    recent = [x for x in th if now_ms - dp["heat_window_hours"] * HOUR <= x["ms"] <= now_ms]
    if len(recent) >= dp["heat_min_msgs"] and len({x["frm"] for x in recent}) >= dp["heat_min_senders"]:
        pts += P["thread_heating"]
        reasons.append("thread heating up: %d messages in %d hours (%+.1f)" % (len(recent), dp["heat_window_hours"], P["thread_heating"]))
    if not bulk:
        hi = now_ms + P["calendar_ahead_days"] * DAY
        soon = [e for e in mb.events if now_ms <= e["ms"] <= hi]
        att = [e for e in soon if m["frm"] in e["attendees"]]
        if att:
            pts += P["calendar_sender_attends"]
            reasons.append("sender is a guest at '%s' in the next %d days (%+.1f)" % (att[0]["summary"], P["calendar_ahead_days"], P["calendar_sender_attends"]))
        else:
            sw = _words(m["subject"])
            ev = [e for e in soon if len(sw & _words(e["summary"])) >= P["calendar_subject_min_shared_words"]]
            if ev:
                pts += P["calendar_subject_match"]
                reasons.append("subject matches calendar event '%s' (%+.1f)" % (ev[0]["summary"], P["calendar_subject_match"]))
        tk = [t for t in mb.tasks if len(_words(m["subject"]) & _words(t)) >= 1]
        if tk:
            pts += P["task_subject_match"]
            reasons.append("subject matches an open task (%+.1f)" % P["task_subject_match"])
    subj = m["subject"].lower()
    job_hit = False
    for name, lst in (cfg.keywords.get("lists") or {}).items():
        hit = [p for p in lst.get("phrases", []) if p.lower() in subj]
        if hit:
            pts += float(lst.get("weight", 0))
            reasons.append("subject has %s keyword '%s' (%+.1f)" % (name, hit[0], float(lst.get("weight", 0))))
            job_hit = job_hit or name == "job"
    if not reasons:
        reasons.append("no signals: nothing on the outside raises or lowers this mail")
    score = round(max(0.0, pts), 3)
    level = _level(score, P["medium_at"], P["high_at"])
    flag = False
    if job_hit and not m["sent"]:
        first = mb.first_sent_to.get(m["frm"], float("inf")) >= m["ms"]   # he has not yet written to them
        if first:
            flag = True
            reasons.append("new sender with a job keyword: always flagged")
            if LEVELS.index(level) < LEVELS.index(P["new_sender_job_keyword_min_level"]):
                level = P["new_sender_job_keyword_min_level"]
    short = flag or LEVELS.index(level) >= LEVELS.index(P["shortlist_min_level"])
    return {"route": "B", "msg_id": msg_id, "level": level, "score": score, "reasons": reasons, "shortlist": short}


def short_list(mb, cfg, now_ms, msg_ids=None):
    """The few Path B envelopes that look important, best first. Read-label mail is never on it."""
    P = cfg.points["attention"]
    if msg_ids is None:
        lo = now_ms - P["shortlist_window_days"] * DAY
        msg_ids = [m["id"] for m in mb.msgs if not m["sent"] and lo <= m["ms"] <= now_ms]
    out = []
    for mid in msg_ids:
        r = attention_score(mb, mid, cfg, now_ms)
        if r["route"] == "B" and r["shortlist"]:
            out.append(r)
    out.sort(key=lambda r: (-r["score"], r["msg_id"]))
    return out[:P["shortlist_max_items"]]


# ---- Path A ------------------------------------------------------------------------------------------------------
def importance_urgency(obs, cfg, standing_value=0.0, automated=False, level=None):
    """Path A, from the triage observations (fixed choices; None = can't tell, counts for nothing):
    deadline_days (int|None), direct_ask, reply_expected, money (bool|None). Importance caps urgency."""
    P = cfg.points["path_a"]
    obs = obs if isinstance(obs, dict) else {}
    standing_value = standing_value if _num(standing_value) else 0.0
    reasons = []
    imp = P["standing_weight"] * standing_value
    if standing_value:
        reasons.append("sender standing %.1f (%+.1f)" % (standing_value, imp))
    lvp = level_points(P, level)
    if lvp:
        imp += lvp
        reasons.append("sender is %s level%s above you (%+.2f)" % (level, "" if level == 1 else "s", lvp))
    dd = obs.get("deadline_days")
    dd = dd if _num(dd) else None     # a bool, NaN or text is garbage: counts for nothing
    for key, label in (("direct_ask", "a direct ask"), ("reply_expected", "a reply is expected"), ("money", "money involved")):
        if obs.get(key) is True:
            imp += P[key]
            reasons.append("%s (%+.1f)" % (label, P[key]))
    if isinstance(dd, (int, float)):
        imp += P["deadline_present"]
        reasons.append("states a deadline in %d day%s (%+.1f)" % (dd, "" if dd == 1 else "s", P["deadline_present"]))
    if automated:
        imp += P["bulk_penalty"]
        reasons.append("bulk or automated sender (%+.1f)" % P["bulk_penalty"])
    imp = max(0.0, imp)
    urg = 0.0
    if isinstance(dd, (int, float)):
        urg += P["urgency_deadline_le_2d"] if dd <= 2 else P["urgency_deadline_le_7d"] if dd <= 7 else P["urgency_deadline_later"]
    if obs.get("direct_ask") is True:
        urg += P["urgency_direct_ask"]
    if obs.get("reply_expected") is True:
        urg += P["urgency_reply_expected"]
    if not reasons:
        reasons.append("no signals: nothing observed raises or lowers this mail")
    capped = min(urg, imp)
    il = _level(imp, P["medium_at"], P["high_at"])
    ul = _level(capped, P["medium_at"], P["high_at"])
    if urg > imp:
        reasons.append("urgency %.1f capped by importance %.1f (%s)" % (urg, imp, il))
    return {"importance": il, "urgency": ul, "importance_points": round(imp, 3), "urgency_points": round(capped, 3),
            "rank": round(imp + capped, 3), "reasons": reasons}

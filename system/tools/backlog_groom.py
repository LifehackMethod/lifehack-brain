#!/usr/bin/env python3
"""backlog_groom.py — the Backlog Authority's READ-ONLY engine (PORTED 2026-08-14 from
claudeops-config's system/tools/backlog_groom.py, organism Window 4).

The 4th organ's brain: *"Is the system tracking itself honestly?"* It reads the typed system
backlog (`<brain>/state/debt-ledger.md`), every desk's `open-loops.md` (enumerated from a
desk registry, NOT a hardcoded list — see `load_registry()`), and the legacy root swamp
(`<brain>/state/open-loops.md`), and returns ONE report dict with the **honest decomposed
counts** + grooming PROPOSALS. It NEVER writes — propose-never-execute: the destructive
grooming (archive a done item, delete a dupe, stamp a tag, drain the swamp) is described here
as a SUPERVISED pass that consumes these proposals, and `--propose` (see `_print_propose()`
below) emits exactly that per-item disposition list. `backlog-health.py` (already shipped in
this repo, and already wired to lazily `import backlog_groom` — see that file's own docstring)
imports this to emit the tile.

⛔ **SHIP-WITH-DEBT-NOTE (T9.7c, 2026-08-15): the supervised drain itself is NOT BUILT in this
repo.** `--propose` produces the disposition list; nothing here or elsewhere in this repo is the
human-in-the-loop skill/SOP that CONSUMES it — reviews each proposal and actually executes the
archive/delete/stamp/drain. This mirrors the donor's own tracked gap (`GAP-1` in its
`backlog-authority` organism element: *"the supervised drain path is unbuilt... the groomer
proposes; there is no built consumer"*) — the port did not close it, and this note exists so the
next reader finds a stated gap instead of an implied one, the same disclosure shape as
`[SKILL-CONFORMANCE-PRODUCER-HALF]` in `docs/skill-conformance.md`. Until a drain skill/SOP is
written, running `--propose` and acting on it by hand is the only path.

THE TWO-AXIS MODEL (`system/schemas/backlog-entry-schema.md`, frozen v1.0 — unchanged by
this port, verified against the live schema file in this repo):
  type  = debt | project | decision | blocked | chore | idea   (the ledger encodes type by SECTION)
  state = actionable | waiting-external | waiting-date | monitoring | parked | done
  THE HEADLINE "what's actually broken" NUMBER = type:debt AND state:actionable — nothing else.
  Everything else (projects, decisions, blocked, parked, the un-drained swamp) is decomposed and
  explicitly NOT counted as broken. This is the antidote to an undifferentiated total.

Stdlib + PyYAML only. Graceful: any parse/registry failure degrades that source to empty, never
crashes. ⚠ CORRECTED 2026-08-15 (F9.7d stale-claim sweep): this paragraph used to say the desk
registry did not exist in this repo. `system/desk-registry.yaml` landed via F9.6 "THE DESK PLANE"
and `load_registry()` reads it correctly. It currently ships with `desks: []` — empty by design
for a fresh install (see the registry file's own header) — so the registry source degrades to
`[]` today for the ordinary reason (no desks registered yet), not because the file or the
multi-desk model is absent. Once a desk is appended via `system/sops/desk-building-sop.md`, this
source populates with no code change here.

WHAT CHANGED IN THIS PORT (generalisation, not a redesign):
  · `LEDGER`/`SWAMP` moved from a hardcoded personal Drive path to the resolved brain root
    (`shared/brain_root.py`'s `resolve_brain_root()`) — the ONE root resolver every other
    ported store in this repo already uses. With no root configured, both paths are `None`
    and every parser degrades to an empty result exactly as it already does for a missing
    file — no new failure mode, no crash.
  · `REGISTRY` still names `system/desk-registry.yaml` (code-resident, like the donor). ⚠
    CORRECTED 2026-08-15: this bullet used to say the file was absent and the degrade was
    permanent. F9.6 "THE DESK PLANE" landed the registry; `load_registry()` reads it. It ships
    with `desks: []` (empty by design for a fresh install), so `load_registry()` returns `[]`
    today because there are zero registered desks, not because the file or the concept is
    missing — the same graceful-degrade path, now taken for the ordinary reason instead of a
    permanent one.

Every finding this emits goes through `emit_finding.py` (imported by reference, exactly like
every other Hospital detector in this repo) — the general finding contract proven to
round-trip a debt item as readily as a dead cron job. See `_emit_findings()` below for the
label/identity design (one finding PER CHECK, not one per item, mirroring the self-healing
posture every other Hospital detector in this repo already uses — a resolved item's last
finding must not sit forever looking like an unresolved one; a fresh row every run,
including a fresh OK, is what makes that safe).

There was no prior write path to delete here — `build_report()` has always been read-only.
"""
import json, os, re, sys, time

_HERE = os.path.dirname(os.path.abspath(__file__))
CODE_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))  # clone (registry is code-resident)
REGISTRY = f"{CODE_ROOT}/system/desk-registry.yaml"

# ── WHERE THE LEDGER/SWAMP LIVE — resolved through the ONE brain-root resolver, never
# guessed. The donor hardcoded a personal cloud-drive path here. ──
_SHARED = os.path.join(CODE_ROOT, "shared")
if _SHARED not in sys.path:
    sys.path.insert(0, _SHARED)
try:
    from brain_root import resolve_brain_root          # shared/brain_root.py
    _ROOT_SOURCE, _ROOT = resolve_brain_root()
except Exception:
    _ROOT_SOURCE, _ROOT = None, None

LEDGER = os.path.join(_ROOT, "state", "debt-ledger.md") if _ROOT else None
SWAMP = os.path.join(_ROOT, "state", "open-loops.md") if _ROOT else None

# ── Hospital's ONE validating writer, imported by reference exactly like every other
# detector in this repo — never copy-pasted, never a second hand-rolled envelope. ──
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from emit_finding import emit_finding, FindingContractError   # noqa: E402

# ── ledger ## section → (type, default-state) — the section IS the type discriminator ──
# (absent inline tags ⇒ these defaults; an explicit `type:`/`state:` tag on a bullet overrides.)
SECTION_MAP = {
    "Open":               ("debt",     "actionable"),        # the broken set — the headline
    "Projects":           ("project",  "actionable"),        # tracked future builds, not owed
    "Decisions":          ("decision", "actionable"),        # need an operator call
    "Blocked":            ("blocked",  "waiting-external"),  # waiting on a condition
    "Parked":             ("project",  "parked"),            # someday-maybe (type project/idea, state parked)
    "Needs human verify": ("verify",   "actionable"),        # quick checks (synthetic bucket, not debt)
}
# ## sections that are prose / history / pointers — never counted as backlog items
SKIP_SECTIONS = ("Discipline", "type model", "Routed to desks", "Cleared")

TAG_TYPE  = re.compile(r"`type:([\w-]+)`")
TAG_STATE = re.compile(r"`state:([\w-]+)`")
TAG_DONEW = re.compile(r"`done_when:([^`]+)`")
TAG_UNBLK = re.compile(r"`unblock:([^`]+)`")
TAG_TOUCH = re.compile(r"`last_touched:(\d{4}-\d{2}-\d{2})`")
# a bracketed [AREA-SLUG] anywhere — requires ≥1 UPPERCASE letter so it matches `**[SLUG]**` (ledger)
# AND `### [SLUG]` (swamp) but NOT a date bracket like `[2026-06-18]` (no letter → not a slug).
SLUG_RE   = re.compile(r"\[([A-Z0-9._/+-]*[A-Z][A-Z0-9._/+-]*)\]")
# body markers that mean "this item is actually finished" (the done-never-archived class). The ledger's
# ## Open section is guard-forbidden from carrying these, so this fires on desk files + the swamp.
DONE_MARK = re.compile(r"✅|\b(DONE|RESOLVED|CLEARED|COMPLETE|SHIPPED|BUILT)\b")
WAIT_MARK = re.compile(r"⛔|\b(waiting|awaiting|blocked|pending|ext\b|external)\b", re.IGNORECASE)


def iso(epoch):
    lt = time.localtime(epoch); off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def load_registry():
    """[desk-entry dicts] from desk-registry.yaml (CODE_ROOT). Graceful: [] on ANY failure — a
    missing/broken registry (or absent PyYAML) degrades the sweep to ledger-only, never crashes.

    ⚠ CORRECTED 2026-08-15 (F9.7d): this docstring used to say `system/desk-registry.yaml` did
    not exist in this repo. It landed via F9.6 "THE DESK PLANE" and is read correctly — verified
    live this session (`load_registry()` parses it via PyYAML, `desks:` key present). It ships
    with `desks: []` on a fresh install, so this still returns `[]` today, but for the ordinary
    reason (zero desks registered) rather than an absent file — the same `except Exception` path
    a corrupt registry would take, just not the path actually taken right now. `build_report()`
    below is fully correct either way: with zero desk sources today, or with real ones once a
    desk is appended per `system/sops/desk-building-sop.md`."""
    try:
        import yaml
        with open(REGISTRY) as f:
            data = yaml.safe_load(f) or {}
        return data.get("desks", []) or []
    except Exception:
        return []


def _slug(text):
    m = SLUG_RE.search(text)
    if m:
        return m.group(1)
    m2 = re.search(r"\*\*(.+?)\*\*", text)            # else first bold phrase, trimmed
    return (m2.group(1)[:48] if m2 else text.strip("-* ").strip()[:48]) or "(untitled)"


def _entry(line, lineno, file_rel, sec_type, sec_state):
    """Build one backlog entry from a bullet line; inline tags override the section defaults."""
    t = TAG_TYPE.search(line);  st = TAG_STATE.search(line)
    dw = TAG_DONEW.search(line); ub = TAG_UNBLK.search(line); lt = TAG_TOUCH.search(line)
    return {
        "slug": _slug(line),
        "title": line.strip()[:160],
        "type":  t.group(1) if t else sec_type,
        "state": st.group(1) if st else sec_state,
        "done_when":   dw.group(1).strip() if dw else None,
        "unblock":     ub.group(1).strip() if ub else None,
        "last_touched": lt.group(1) if lt else None,
        "tagged": bool(t or st),                       # already carries explicit type/state?
        "done_marker": bool(DONE_MARK.search(line)),   # body says finished (done-never-archived signal)
        "file": file_rel, "line": lineno,
        "home": f"{file_rel}#{_slug(line)}",
    }


def parse_ledger(path=None):
    """Parse the typed ledger into entries, type from ## section. Returns [] on any failure,
    including no brain root configured (path defaults to LEDGER, which is None in that case)."""
    path = path if path is not None else LEDGER
    entries = []
    if not path:
        return entries
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return entries
    rel = os.path.relpath(path, _ROOT) if _ROOT else path
    sec_type = sec_state = None
    in_fm = False
    for i, raw in enumerate(lines, 1):
        s = raw.rstrip()
        if i == 1 and s == "---":
            in_fm = True; continue
        if in_fm:
            if s == "---":
                in_fm = False
            continue
        if s.startswith("## "):                         # a section header (## , not ### )
            head = s[3:].strip()
            if any(k in head for k in SKIP_SECTIONS):
                sec_type = sec_state = None
                continue
            sec_type = sec_state = None
            for key, (ty, stt) in SECTION_MAP.items():
                if head.startswith(key):
                    sec_type, sec_state = ty, stt
                    break
            continue
        if sec_type and re.match(r"^- ", s):            # top-level bullet inside a counted section
            entries.append(_entry(s, i, rel, sec_type, sec_state))
    return entries


def parse_desk_loops(path_rel, desk_id, backlog_mode):
    """Conservative per-desk loop parse: top-level bullets + item-headers. Desk files are heterogeneous
    (## sections · ### / ## per-item blocks · - bullets) so this counts loosely and flags done-markers;
    the headline debt number does NOT depend on this (it comes from the ledger ## Open). Returns entries."""
    entries = []
    if not _ROOT:
        return entries
    full = f"{_ROOT}/{path_rel}"
    try:
        lines = open(full, encoding="utf-8").read().splitlines()
    except Exception:
        return entries
    in_fm = False
    sec = ""
    for i, raw in enumerate(lines, 1):
        s = raw.rstrip()
        if i == 1 and s == "---":
            in_fm = True; continue
        if in_fm:
            if s == "---":
                in_fm = False
            continue
        if s.startswith("## "):
            sec = s[3:].strip()
            # skip a desk file's own Resolved/archive section
            if any(k in sec for k in ("Resolved", "Cleared", "archive")):
                sec = "__skip__"
            continue
        if sec == "__skip__":
            continue
        if re.match(r"^- ", s):                          # a top-level desk loop bullet
            e = _entry(s, i, path_rel, "chore", "actionable")
            e["desk"] = desk_id; e["backlog_mode"] = backlog_mode
            e["waiting"] = bool(WAIT_MARK.search(s))
            entries.append(e)
    return entries


def parse_swamp(path=None):
    """Rough item count for the legacy root open-loops swamp — every `### `/`## ` item-header + top
    bullets in the active region (above any '## Resolved'). Reported SEPARATELY as 'pending drain' —
    deliberately NOT folded into actionable_debt (conflating it is exactly the disease we cure)."""
    path = path if path is not None else SWAMP
    if not path:
        return []
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except Exception:
        return []
    items, in_fm, resolved = [], False, False
    rel = os.path.relpath(path, _ROOT) if _ROOT else path
    for i, raw in enumerate(lines, 1):
        s = raw.rstrip()
        if i == 1 and s == "---":
            in_fm = True; continue
        if in_fm:
            if s == "---":
                in_fm = False
            continue
        if re.match(r"^##+ ", s) and "Resolved" in s:
            resolved = True; continue
        if resolved:
            continue
        if re.match(r"^###? ", s) or re.match(r"^- \*\*", s):   # an item header or a bold top bullet
            items.append({"slug": _slug(s), "title": s.strip()[:160], "file": rel, "line": i,
                          "done_marker": bool(DONE_MARK.search(s))})
    return items


def _dupes(*groups):
    """Same slug appearing across DIFFERENT FILES → the "one home per item" violation (root ledger wins,
    since groups are ordered by authority: ledger first). Deliberately does NOT flag two distinct items
    in the SAME file that merely share an `[AREA]` prefix (e.g. several `[DOCS]`/`[PLATFORM]` bullets in
    the ledger are different items, not dupes) — only a slug that spans two files is a real home conflict."""
    first_file, dupes, seen_pair = {}, [], set()
    for g in groups:
        for e in g:
            slug = e.get("slug")
            if not slug or slug == "(untitled)":
                continue
            if slug not in first_file:
                first_file[slug] = e                       # first (most-authoritative) home wins
                continue
            keep = first_file[slug]
            if e.get("file") == keep.get("file"):
                continue                                   # same file → distinct items, not a dupe
            pair = (slug, e.get("file"))
            if pair in seen_pair:
                continue
            seen_pair.add(pair)
            dupes.append({"slug": slug, "wins": keep["home"], "dupe_at": e.get("home")})
    return dupes


def _emit_findings(counts, proposals, scanned_n, ledger):
    """One Hospital finding PER CHECK (not per item), mirroring every other detector in this
    repo's identity model and for the identical reason: labels are the finding's STABLE
    IDENTITY, and the population of individual debt/dupe/stale items changes every run as
    things get filed and cleared. Emitting one finding PER ITEM (keyed on slug/home) would mean
    a resolved item's LAST finding just stops being refreshed — findings_reader/health_line
    have no expiry, so that stale row would sit forever looking exactly like an unresolved
    problem. Emitting per-CHECK instead means every check gets a FRESH row every run, including
    a fresh OK when the underlying items clear. The actual items (titles, homes, slugs) live in
    `payload`, never in `labels`.

    `labels={"job": "backlog-groom", "check": <name>}` — six checks, one per proposal category
    plus the headline actionable-debt count. `actionable-debt` is deliberately included even
    though it is not itself a "proposal": it is THE debt items themselves (every
    `type:debt, state:actionable` ledger entry), and is the literal answer to "does a debt item
    round-trip through this validator" — its payload enumerates each one by title + home, not
    just a count.
    """
    checks = [
        ("actionable-debt", counts.get("actionable_debt", 0),
         [{"title": e["title"], "home": e["home"]} for e in ledger
          if e["type"] == "debt" and e["state"] == "actionable"]),
        ("done-never-archived", len(proposals["done"]), proposals["done"]),
        ("duplicate-slugs", len(proposals["dupes"]), proposals["dupes"]),
        ("stale-suspect", len(proposals["stale"]), proposals["stale"]),
        ("untagged-entries", len(proposals["untyped"]), proposals["untyped"]),
        ("swamp-drain-pending", counts.get("swamp_pending", 0), []),
    ]
    for check, n, items in checks:
        try:
            ok = (n == 0)
            labels = {"job": "backlog-groom", "check": check}
            if items:
                sample = "; ".join(str(it.get("title") or it.get("slug") or it.get("home") or it)[:60]
                                    for it in items[:5])
                more = f" (+{n - 5} more)" if n > 5 else ""
                summary = f"{n} {check}: {sample}{more}"
            else:
                summary = f"{n} {check}" if not ok else f"{check}: clean"
            emit_finding(
                producer="backlog-groom",
                status="OK" if ok else "NEEDS_REVIEW",
                scanned_n=scanned_n,
                labels=labels,
                summary=summary,
                payload={"count": n, "items": items[:25]},
                rc=0 if ok else 1,
            )
        except Exception as e:
            # One bad check's emit costs only that finding, never the other five.
            sys.stderr.write(f"[backlog_groom] emit_finding failed for check={check}: {e}\n")


def build_report():
    """The one read-only report the tile + the drain consume."""
    now = int(time.time())
    ledger = parse_ledger()
    registry = load_registry()
    desk_all, by_desk = [], {}
    desk_files_scanned = 0
    for d in registry:
        did = d.get("desk_id") or "?"
        olp = d.get("open_loops_path")          # VERBATIM — never derived from desk_id
        mode = d.get("backlog_mode") or "queue"
        if not olp:
            continue
        des = parse_desk_loops(olp, did, mode)
        if _ROOT and os.path.isfile(os.path.join(_ROOT, olp)):
            desk_files_scanned += 1
        desk_all += des
        by_desk[did] = {"count": len(des), "mode": mode,
                        "waiting": sum(1 for e in des if e.get("waiting"))}
    swamp = parse_swamp()

    # ── WHICH SOURCES ACTUALLY EXIST — the "scanned nothing" vs "scanned and found nothing"
    # distinction emit_finding.py's zero-scan-OK guard exists to catch. A MISSING source (no
    # `state/debt-ledger.md`, no desk-registry entries, no legacy `state/open-loops.md`) means
    # this run verified NOTHING about it — that is the fresh-install day-one state, not a clean
    # scan, and is EXACTLY the case measured to trip six emit_finding refusals below (this repo
    # currently has none of the three). A PRESENT-but-empty source (e.g. a ledger file that
    # exists but has zero bullets under any tracked section) is a real scan that genuinely found
    # nothing wrong — that is honest OK, not "not configured", so it must not be lumped in here.
    ledger_scanned = bool(LEDGER) and os.path.isfile(LEDGER)
    swamp_scanned = bool(SWAMP) and os.path.isfile(SWAMP)
    sources_scanned = int(ledger_scanned) + int(swamp_scanned) + desk_files_scanned

    # ── decomposed counts (type × state) ──
    def n(ty, stt=None):
        return sum(1 for e in ledger if e["type"] == ty and (stt is None or e["state"] == stt))

    counts = {
        "actionable_debt": n("debt", "actionable"),     # ⭐ THE headline "what's broken" number
        "debt_total":      n("debt"),
        "projects":        n("project") - n("project", "parked"),
        "decisions":       n("decision"),
        "blocked":         n("blocked"),
        "parked":          n("project", "parked"),
        "needs_verify":    n("verify"),
        "desk_loops_total": len(desk_all),
        "by_desk":         by_desk,
        "swamp_pending":   len(swamp),                  # legacy file awaiting the Phase-5 drain
    }

    # ── proposals (propose-never-execute; a human reviews + applies) ──
    # done-never-archived: ONLY desk/swamp items whose body says finished (ledger ## Open is guard-clean).
    done = ([{"home": e["home"], "title": e["title"], "where": "desk"} for e in desk_all if e["done_marker"]]
            + [{"home": e["file"] + "#" + str(e["line"]), "title": e["title"], "where": "swamp"}
               for e in swamp if e["done_marker"]])
    dupes = _dupes(ledger, desk_all, [{**s, "home": s["file"] + "#" + str(s["line"])} for s in swamp])
    # queue desks (NOT register) whose waiting items are stale-suspect — register desks never flagged.
    stale = [{"home": e["home"], "title": e["title"], "desk": e["desk"]}
             for e in desk_all
             if e.get("backlog_mode") == "queue" and e.get("waiting")]
    untyped = [{"home": e["home"], "section_type": e["type"]} for e in ledger if not e["tagged"]]

    rep = {
        "generated_at": iso(now),
        "configured": sources_scanned > 0,
        "counts": counts,
        "proposals": {"done": done, "dupes": dupes, "stale": stale, "untyped": untyped},
    }

    if sources_scanned == 0:
        # ── NOTHING TO SCAN YET — the fresh-install / day-one state, not a defect. No ledger, no
        # desk backlog file, and no legacy swamp exist, so this run has verified NOTHING about
        # any of the six checks below — none of them can honestly claim OK over a scanned_n=0
        # universe (this is the exact refusal `emit_finding.py` is designed to raise, and did,
        # six times, before this branch existed). Emit ONE honest "not configured" finding
        # instead of the six-check machinery, same spirit as `cal-health.py`'s
        # "not configured — no calendar connected yet" (status OK, scanned_n=1: the one real
        # thing this run checked was WHETHER a source exists, and it does that check for real). ──
        summary = "not configured — no debt ledger, desk backlogs, or legacy swamp file found yet"
        try:
            emit_finding(producer="backlog-groom", status="OK", scanned_n=1,
                         labels={"job": "backlog-groom", "check": "configured"},
                         summary=summary,
                         payload={"ledger_path": LEDGER, "swamp_path": SWAMP}, rc=0)
        except Exception as e:
            sys.stderr.write(f"[backlog_groom] emit_finding failed for check=configured: {e}\n")
        return rep

    # ── emit through Hospital ── scanned_n is the REAL universe this run actually walked —
    # ledger entries + every desk's loop entries + the legacy swamp — wired from the same three
    # lists this function just parsed, floored at the number of sources actually opened (never
    # below 1 per source present) so a genuinely-present-but-empty source (e.g. a freshly
    # created, still-blank ledger with zero bullets) still reports an honest non-zero scan
    # instead of spuriously tripping the same zero-scan-OK guard the branch above exists for.
    item_n = len(ledger) + len(desk_all) + len(swamp)
    scanned_n = max(sources_scanned, item_n)
    try:
        _emit_findings(counts, {"done": done, "dupes": dupes, "stale": stale, "untyped": untyped},
                        scanned_n, ledger)
    except Exception as e:
        # Emitting must never break the read-only report itself.
        sys.stderr.write(f"[backlog_groom] emit_finding failed: {e}\n")

    return rep


def _print_propose(rep):
    c = rep["counts"]; p = rep["proposals"]
    print(f"\n=== Backlog groom report — {rep['generated_at']} ===")
    print(f"\n  ⭐ ACTIONABLE DEBT (the broken number): {c['actionable_debt']}")
    print(f"     debt total {c['debt_total']} · projects {c['projects']} · decisions {c['decisions']} · "
          f"blocked {c['blocked']} · parked {c['parked']} · needs-verify {c['needs_verify']}")
    print(f"     desk loops {c['desk_loops_total']}  " +
          " ".join(f"{k}:{v['count']}({v['mode'][0]})" for k, v in c["by_desk"].items()))
    print(f"     ⚠ legacy swamp pending drain: {c['swamp_pending']} items (state/open-loops.md)")
    print(f"\n  PROPOSALS (propose-only — a human reviews + applies):")
    print(f"    done-never-archived candidates: {len(p['done'])}")
    for e in p["done"][:40]:
        print(f"       [{e['where']}] {e['title'][:90]}")
    print(f"    duplicate slugs (root ledger wins): {len(p['dupes'])}")
    for e in p["dupes"][:40]:
        print(f"       {e['slug']}  keep:{e['wins']}  drop:{e['dupe_at']}")
    print(f"    queue-desk waiting/stale-suspect: {len(p['stale'])}")
    for e in p["stale"][:40]:
        print(f"       ({e['desk']}) {e['title'][:90]}")
    print(f"    untagged ledger entries (forward-stamp target): {len(p['untyped'])}")
    print()


if __name__ == "__main__":
    rep = build_report()
    if "--json" in sys.argv:
        print(json.dumps(rep, indent=2))
    else:
        _print_propose(rep)

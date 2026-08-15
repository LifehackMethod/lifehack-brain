#!/usr/bin/env python3
"""cal-vault-pull.py — Cal overnight VERBATIM raw-vault pull (Stage 1, daily trust-fall system).

Mechanical, NO-LLM. Pulls the day's raw material VERBATIM into a dated vault folder so the morning
session reads complete, sanitized data off disk — never re-pulling, never letting an LLM condense at
pull time. Built ONLY on the safe-ingest primitives (never raw bodies):
  - Email   : shared/tools/email_convert.py  (hardened L0 sanitize + HTML-strip + injection-flag)
  - Calendar: system/tools/safe_calendar.py --redact  (L0 + injection scan; flagged spans neutralized)
  - Tasks   : system/tools/safe_tasks.py --redact      (L0 + injection scan; flagged spans neutralized)

Vault layout:  desks/cal/state/raw-vault/YYYY-MM-DD/
  inbox/ sent/ snoozed/   email_convert per-thread *_full.txt + its manifest.json/skipped.json
  calendar.json           prior 7d + next 7d, sanitized
  tasks.json              Win lists (full) + Inbox catch-all (full) + top-N (DOMAIN_TOP_N) of each other
                          list, sorted by Google 'position'; each list carries total/kept/truncated
  _manifest.json          the honesty RECEIPT: per-source status, counts, overflow flag, any FAILED

Scope (locked 2026-06-12): inbox primary cap 25 (overflow-flagged; ceiling 50), sent 7d, snoozed all,
calendar +/-7d, tasks light. Attachments are NOT downloaded.

SAFETY: fail-soft — any source failure -> that source marked failed in _manifest, exit 0 (cron-breaker
safe). The vault is built in a .tmp dir then os.replace'd into place (atomic swap). READ-ONLY against
Google. Usage: cal-vault-pull.py [--date YYYY-MM-DD]  (default today). Runner exports the headless gws env.
"""
import argparse, json, os, shutil, subprocess, sys, time
from datetime import datetime, timedelta, time as dtime, timezone

# Lazy import helpers for the blue-green store path — loaded only when the flag is on.
# Defined at module scope so the flag-off path NEVER touches them (belt-and-suspenders:
# even an ImportError on email_service_read is impossible to affect the cold path).
def _import_store_helpers():
    """Return (_enabled_for, read_thread) from email_service_read, or (None, None) on any error."""
    try:
        _esr_path = os.path.join(CODE_ROOT, "shared", "tools")
        if _esr_path not in sys.path:
            sys.path.insert(0, _esr_path)
        from email_service_read import _enabled_for as _ef, read_thread as _rt
        return _ef, _rt
    except Exception:
        return None, None

# Execution-residency: DRIVE = CONTENT root (the vault is WRITTEN here — always Drive). CODE_ROOT =
# where this code lives (the git clone or the Drive copy, from __file__) → the .py tools we shell out to.
# The notes folder, through the one resolver. ⛔ NOT a default and NOT a guess: the tool this came
# from hardcoded one person's Drive path, so on any other machine it wrote its vault into a
# directory that did not exist. `resolve_brain_root()` returns (source, path); NOT-SET is (None,
# None), and a tool with nowhere to write must say so rather than invent somewhere.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "shared"))
import brain_root                                                            # noqa: E402
import cal_config                                                            # noqa: E402
_SRC, DRIVE = brain_root.resolve_brain_root()
if not DRIVE:
    sys.stderr.write(
        "no notes folder is set, so there is nowhere to put what this reads.\n"
        "Set it once:  python3 shared/brain_root.py --set \"<the folder your notes live in>\"\n")
    sys.exit(2)
CODE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GWS = __import__("shutil").which("gws") or "gws"  # resolve via PATH; survives binary moves
# ⚠ THE EMAIL SURFACE IS NOW WIRED, BUT HAS NOT BEEN PROVEN END TO END.
# This tool reads three surfaces — email, calendar, tasks. Calendar and tasks work fully.
# The email one routes through `email_convert.py`, which UNTIL 2026-08-14 was not in this repo at
# all; this block used to say the surface "does not work" and that was correct at the time. The
# converter has now landed (ported + generalised, self-test 9/9), so this path no longer fails for
# the reason it used to.
# ⛔ THAT IS NOT THE SAME AS WORKING. Note there is no existence check below — the call at the
# bottom of this file simply invokes the converter and reads its return code. So the day the file
# appeared, this surface silently changed from "fails loudly every run" to "actually attempts,"
# with nobody deciding that. It has not been exercised against a real mailbox here.
# The original reasoning still governs and is worth keeping: a pull that silently produced an empty
# inbox slice would be far worse than one that refuses — the morning run would report a clear inbox
# every day, for ever, and the first sign of trouble would be a missed message nobody knew to look
# for. Verify this path against a connected account before trusting an empty result from it.
EMAIL_CONVERT = os.path.join(CODE_ROOT, "shared/tools/email_convert.py")  # present since 2026-08-14
SAFE_CALENDAR = os.path.join(CODE_ROOT, "system/tools/safe_calendar.py")  # CODE
SAFE_TASKS    = os.path.join(CODE_ROOT, "system/tools/safe_tasks.py")      # CODE
VAULT_ROOT = os.path.join(DRIVE, "desks/cal/state/raw-vault")            # CONTENT (on Drive)

# ⛔ THESE WERE HARDCODED, AND THAT IS THE WORST KIND OF HARDCODING. A calendar id baked into a
# tool means an agent reads — or writes — SOMEBODY ELSE'S CALENDAR, and the person running it sees
# nothing wrong: their own events simply never appear. They are the reader's, at
# <notes>/config/cal.md, and there is deliberately no default. See shared/cal_config.py.
_CAL = cal_config.load()
PERSONAL_CAL = _CAL.get("personal_calendar", "")
AGENTOPS_CAL = _CAL.get("agent_calendar", "")
LIFEMAP_TASKLIST = _CAL.get("goals_tasklist", "")

INBOX_CAP = 25      # flag overflow past this
INBOX_CEILING = 50  # never fetch more than this
DOMAIN_TOP_N = 50   # keep non-priority lists effectively whole (largest real list ~43); the
                    # `truncated` flag catches any list that ever exceeds this. Raised from 5
                    # (2026-06-24): the top-5 cap discarded ~2/3 of the task universe and starved the run.
TASKS_SCOPE_STR = f"Win+Inbox full, top-{DOMAIN_TOP_N} others (position-sorted)"

# safe_tasks.py path — the sanitizer for task free-text (full L0 + injection scan + gate).
# See: system/tools/safe_tasks.py. This replaces the old bare sanitize.py L0-only path.


def gws_json(args, timeout=60):
    r = subprocess.run([GWS] + args, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        tail = (r.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        raise RuntimeError(f"gws {' '.join(args[:2])} failed: {tail}")
    return json.loads(r.stdout or "{}")


# ---------- email (via email_convert.py — the only safe path) ----------

def pull_email(name, query, out_dir, cap=None):
    """Run email_convert for one Gmail query into out_dir. Returns a status dict.

    Blue-green store path (when EMAIL_SERVICE_READ includes "cal"):
      Attempts to satisfy the vault from the Email Service v2 faithful-thread store FIRST.
      ALL-OR-NOTHING: every thread in the query must return flag "OK" from the store;
      if ANY thread is a miss / flagged / tampered / uncertain, OR any error occurs,
      the WHOLE query falls back to the existing email_convert subprocess — never a mixed vault.
      Flag off → the existing email_convert path runs UNCHANGED, byte-identical.
    """
    os.makedirs(out_dir, exist_ok=True)
    status = {"source": "gmail", "query": query, "status": "ok"}

    # ── metadata-only overflow probe (no bodies pulled — safe) ───────────────
    # Also collects thread IDs for the store path (free — same call).
    probe_thread_ids = None   # set below if probe succeeds
    if cap:
        try:
            probe = gws_json(["gmail", "users", "threads", "list", "--params",
                              json.dumps({"userId": "me", "q": query, "maxResults": INBOX_CEILING})])
            all_probe_threads = probe.get("threads", [])
            total = len(all_probe_threads)
            status["total_available"] = total
            status["overflow"] = total > cap
            if total > cap:
                status["overflow_note"] = f"{total} threads available (>= cap {cap}); pulled newest {cap}"
            # Apply the same cap the email_convert --limit flag would apply (newest-first order
            # from the API, same as email_convert's fetch_thread_ids_by_query with limit=cap).
            probe_thread_ids = [t["id"] for t in all_probe_threads[:cap]]
        except Exception as e:
            status["overflow"] = None
            status["overflow_probe_error"] = str(e)
            # probe_thread_ids stays None → store path will not attempt

    # ── blue-green store path ─────────────────────────────────────────────────
    # Attempt only when the flag is on AND we have a thread-ID list to work from.
    _enabled_for, read_thread = _import_store_helpers()
    if _enabled_for is not None and _enabled_for("cal"):
        # For uncapped queries (sent/snoozed) the overflow probe above doesn't run, so we fetch
        # the thread IDs now with a dedicated metadata-only call (no bodies).
        if probe_thread_ids is None:
            try:
                lst = gws_json(["gmail", "users", "threads", "list", "--params",
                                json.dumps({"userId": "me", "q": query})])
                probe_thread_ids = [t["id"] for t in lst.get("threads", [])]
            except Exception as e:
                # Can't get thread IDs → can't try the store → will fall through to email_convert
                sys.stderr.write(f"[cal-vault] store-path: thread-list probe failed for {name!r}: {e}; "
                                 "falling back to email_convert\n")
                probe_thread_ids = None

        if probe_thread_ids is not None:
            store_ok = _try_pull_from_store(
                name, query, out_dir, cap, probe_thread_ids, read_thread, status)
            if store_ok:
                return status   # vault written from store — done

        # Any uncertainty / partial miss / error → fall through to email_convert below
        sys.stderr.write(f"[cal-vault] store-path: not all-OK for {name!r}; "
                         "falling back to email_convert (all-or-nothing rule)\n")

    # ── existing email_convert path (flag-off OR store fallback) ─────────────
    # UNCHANGED from the original — byte-identical behavior when store path is skipped.
    return _pull_email_via_convert(query, out_dir, cap, status)


def _try_pull_from_store(name, query, out_dir, cap, thread_ids, read_thread, status):
    """Attempt to build the vault from the Email Service v2 store.

    ALL-OR-NOTHING invariant: returns True (vault written) ONLY when EVERY thread returns
    flag "OK". Returns False on the FIRST non-OK thread or ANY error — no partial writes.
    The caller falls back to email_convert for the whole query.

    isolate=False is the plumbing exception (ingestion-reader-contract.md): cal-vault-pull is
    a NO-LLM consumer — it writes bytes to disk and never feeds them to an LLM in this process.
    A prompt-injection in the content cannot hijack a no-LLM plumbing script.
    """
    results = []
    try:
        for tid in thread_ids:
            r = read_thread(tid, desk="cal", isolate=False)
            if r.get("flag") != "OK":
                # Any miss, refusal, tamper, or inactive-skip → abort immediately
                sys.stderr.write(
                    f"[cal-vault] store-path: thread {tid} flag={r.get('flag')!r} "
                    f"(envelope: {r.get('envelope','')[:120]})\n")
                return False
            results.append(r)
    except Exception as e:
        sys.stderr.write(f"[cal-vault] store-path: read_thread error for {name!r}: {e}\n")
        return False

    # All threads OK — write the vault.  Structure mirrors email_convert --messages all exactly:
    #   {tid}_full.txt        (the primary body file Cal reads; content = store faithful thread)
    #   manifest.json         (dict keyed by thread_id, same fields pull_email inspects)
    #   skipped.json          (empty list — all threads resolved from the store)
    # Note: email_convert also writes _first.txt and _last.txt but pull_email / Cal morning only
    # reads _full.txt and manifest.json / skipped.json — those are the only files that matter.
    # _first.txt / _last.txt are omitted: the store doesn't carry separate first/last messages
    # and guessing at them would be unsound.  Their absence is safe because nothing in the Cal
    # morning skill reads them (confirmed: process_thread writes first_chars/last_chars into the
    # manifest but pull_email only reads len(man), len(skp), and html_fallback from it).
    try:
        man = {}
        for r in results:
            tid = r["thread_id"]
            content = r.get("content", "")   # MARKER + "\n\n" + faithful body
            full_path = os.path.join(out_dir, f"{tid}_full.txt")
            with open(full_path, "w") as f:
                f.write(content)
            entry = {
                "subject": r.get("subject", ""),
                "message_count": r.get("message_count", 0),
                "full_chars": len(content),
                # html_fallback not set — store records have already been cleaned; the
                # html_fallback flag tracks email_convert's own HTML→text fallback and
                # is not meaningful for store-sourced content.  Omitting is honest.
                "source_store": True,
            }
            # Surface any attachment pointers (safe structured metadata — always inline).
            atts = r.get("attachments")
            if atts:
                entry["attachments"] = atts
            man[tid] = entry

        with open(os.path.join(out_dir, "manifest.json"), "w") as f:
            json.dump(man, f, indent=2)
        with open(os.path.join(out_dir, "skipped.json"), "w") as f:
            json.dump([], f, indent=2)

        # Update status to reflect store sourcing.
        status["pulled"] = len(man)
        status["skipped"] = 0
        status["html_fallback"] = 0
        status["source_store"] = True

        return True

    except Exception as e:
        sys.stderr.write(f"[cal-vault] store-path: write error for {name!r}: {e}\n")
        # Remove any partial writes so a retry gets a clean dir
        try:
            for f in os.listdir(out_dir):
                os.remove(os.path.join(out_dir, f))
        except Exception:
            pass
        return False


def _pull_email_via_convert(query, out_dir, cap, status):
    """The original email_convert subprocess path — UNCHANGED from the pre-store version."""
    cmd = ["python3", EMAIL_CONVERT, "--query", query, "--messages", "all", "--out-dir", out_dir]
    if cap:
        cmd += ["--limit", str(cap)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            status["status"] = "failed"
            status["error"] = (r.stderr.strip().splitlines() or ["email_convert nonzero exit"])[-1]
            return status
        # email_convert writes manifest.json (per-thread) + skipped.json into out_dir
        man = {}
        skp = []
        try:
            with open(os.path.join(out_dir, "manifest.json")) as f:
                man = json.load(f)
            with open(os.path.join(out_dir, "skipped.json")) as f:
                skp = json.load(f)
        except Exception:
            pass
        status["pulled"] = len(man)
        status["skipped"] = len(skp)
        status["html_fallback"] = sum(1 for e in man.values() if e.get("html_fallback"))
        if r.stderr.strip():   # email_convert prints injection FLAGS to stderr — surface, don't hide
            flags = [ln for ln in r.stderr.splitlines() if "FLAGGED" in ln]
            if flags:
                status["injection_flags"] = flags
    except subprocess.TimeoutExpired:
        status["status"] = "failed"
        status["error"] = "timeout (>600s)"
    except Exception as e:
        status["status"] = "failed"
        status["error"] = str(e)
    return status


# ---------- calendar (via safe_calendar.py) ----------

def pull_calendar(out_path, date_str):
    status = {"source": "calendar", "status": "ok"}
    day = datetime.strptime(date_str, "%Y-%m-%d").date()
    tz = datetime.now().astimezone().tzinfo
    start = datetime.combine(day - timedelta(days=7), dtime.min, tzinfo=tz)
    end = datetime.combine(day + timedelta(days=8), dtime.min, tzinfo=tz)  # +7d inclusive
    events = []

    def one(cal_id, label):
        params = {"calendarId": cal_id, "maxResults": 250, "singleEvents": True,
                  "orderBy": "startTime", "timeMin": start.isoformat(), "timeMax": end.isoformat()}
        # --redact: PLUMBING (stores calendar free-text into the vault) needs the real text — but with any
        # injection span NEUTRALIZED, so a later reader of the vault can't be hijacked (closes the
        # vault-as-downstream-injection-channel gap, 2026-07-04). Real content is kept; only flagged spans
        # become [REDACTED-FLAGGED: ...].
        r = subprocess.run(["python3", SAFE_CALENDAR, "--redact", json.dumps(params)],
                           capture_output=True, text=True, timeout=120)
        # safe_calendar exit 0 = clean, 1 = flagged (still valid data), 2 = error
        if r.returncode == 2 or not r.stdout.strip():
            raise RuntimeError((r.stderr.strip().splitlines() or ["safe_calendar error"])[-1])
        data = json.loads(r.stdout)
        for e in data.get("items", []):
            st = e.get("start", {})
            attendees = e.get("attendees") or []
            rsvp = next((a.get("responseStatus", "") for a in attendees if a.get("self")), "")
            events.append({
                "calendar": label,
                "start": st.get("dateTime") or st.get("date") or "",
                "end": (e.get("end") or {}).get("dateTime") or (e.get("end") or {}).get("date") or "",
                "summary": e.get("summary", ""),
                "location": e.get("location", ""),
                "description": e.get("description", ""),
                # busy=True means a LOCKED commitment; busy=False (transparency:transparent) = a SOFT
                # SUGGESTION the person marks movable/optional — never assume a free event happened or is fixed.
                "busy": e.get("transparency", "opaque") != "transparent",
                "status": e.get("status", ""),   # confirmed / tentative / cancelled
                "rsvp": rsvp,                      # self responseStatus: accepted / declined / tentative / needsAction
                "flagged": r.returncode == 1,
            })
    try:
        one(PERSONAL_CAL, "personal")
        one(AGENTOPS_CAL, "agent-ops")
        events.sort(key=lambda x: x["start"])
        with open(out_path, "w") as f:
            json.dump({"window": [start.isoformat(), end.isoformat()], "events": events}, f, indent=2)
        status["events"] = len(events)
    except Exception as e:
        status["status"] = "failed"
        status["error"] = str(e)
        with open(out_path, "w") as f:
            json.dump({"window": [start.isoformat(), end.isoformat()], "events": [],
                       "error": str(e)}, f, indent=2)
    return status


# ---------- tasks (via safe_tasks.py — full L0 + injection scan + provenance gate) ----------

def _safe_tasks_list(tid, timeout=60):
    """Run safe_tasks.py for one tasklist. Returns (items_list, flagged_bool).
    safe_tasks exit 0 = clean, 1 = flagged (data still valid), 2 = error."""
    params = json.dumps({"tasklist": tid, "showCompleted": False,
                         "showDeleted": False, "maxResults": 100})
    r = subprocess.run(
        # --redact: plumbing (stores task free-text into the vault) keeps the real text but neutralizes any
        # injection span, so a later reader of the vault can't be hijacked (2026-07-04).
        ["python3", SAFE_TASKS, "--desk", "cal", "--redact", params],
        capture_output=True, text=True, timeout=timeout,
    )
    if r.returncode == 2 or not r.stdout.strip():
        raise RuntimeError((r.stderr.strip().splitlines() or ["safe_tasks error"])[-1])
    data = json.loads(r.stdout)
    items = data.get("items", []) or []
    flagged = (r.returncode == 1)
    # Surface any injection flags to the caller's stderr so the manifest can record them.
    if flagged and r.stderr.strip():
        flag_lines = [ln for ln in r.stderr.splitlines() if "FLAGGED" in ln or "[" in ln]
        if flag_lines:
            sys.stderr.write(f"[cal-vault] safe_tasks FLAGGED in list {tid}: "
                             + " | ".join(flag_lines[:5]) + "\n")
    return items, flagged


def pull_tasks(out_path):
    status = {"source": "tasks", "status": "ok"}
    out = {"lists": []}
    try:
        lists = gws_json(["tasks", "tasklists", "list", "--params", "{}"]).get("items", [])
    except Exception as e:
        status["status"] = "failed"
        status["error"] = str(e)
        with open(out_path, "w") as f:
            json.dump({"lists": [], "error": str(e)}, f, indent=2)
        return status

    kept_total = 0
    any_flagged = False
    for tl in lists:
        tid, title = tl.get("id", ""), tl.get("title", "")
        full = (tid == LIFEMAP_TASKLIST) or ("inbox" in title.lower())  # Win horizons + catch-all = full
        try:
            items, flagged = _safe_tasks_list(tid)
        except Exception as e:
            out["lists"].append({"id": tid, "title": title, "error": str(e)})
            continue
        if flagged:
            any_flagged = True
        # Sort by Google 'position' (lexicographic = the user's manual list order) BEFORE any cap,
        # so "kept" is the real top-of-list — raw API order is not guaranteed to match it.
        items.sort(key=lambda t: t.get("position", "") or "")
        total = len(items)
        kept = items if full else items[:DOMAIN_TOP_N]
        kept_total += len(kept)
        # safe_tasks.py has already sanitized title/notes in-place; just project the fields we keep.
        out["lists"].append({
            "id": tid, "title": title, "full_pull": full,
            "total": total, "kept": len(kept), "truncated": (total > len(kept)),
            "tasks": [{
                "title": t.get("title", ""),
                "notes": t.get("notes", ""),
                "due": t.get("due", ""), "status": t.get("status", ""),
                "parent": t.get("parent", ""), "position": t.get("position", ""),
            } for t in kept],
        })
    status["lists"] = len(out["lists"])
    status["tasks_kept"] = kept_total
    if any_flagged:
        status["injection_flags"] = True
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    return status


# ---------- main ----------

def iso_now():
    lt = time.localtime()
    off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def tasks_only_refresh(date_str, final_dir):
    """Freshness re-grab: rewrite ONLY tasks.json in an existing day's vault (skips the slow email
    pull + the full tmp-dir rebuild). Used by Phase-3 'I just reorganized' reseed and by F1 verify.
    Fail-soft: on a transient pull failure, leave the existing tasks.json intact."""
    os.makedirs(final_dir, exist_ok=True)
    tasks_path = os.path.join(final_dir, "tasks.json")
    tmp_path = tasks_path + ".tmp"
    status = pull_tasks(tmp_path)               # writes tmp_path; returns a status dict
    if status.get("status") == "ok":
        os.replace(tmp_path, tasks_path)        # atomic per-file swap
    else:
        try: os.remove(tmp_path)
        except OSError: pass
        sys.stderr.write(f"[cal-vault] tasks-only: pull failed ({status.get('error')}); "
                         f"kept existing tasks.json\n")
        return 0                                # fail-soft — never clobber good data on a blip
    # patch the manifest's tasks source + scope so the receipt stays honest
    man_path = os.path.join(final_dir, "_manifest.json")
    if os.path.exists(man_path):
        try:
            with open(man_path) as f: man = json.load(f)
            man.setdefault("sources", {})["tasks"] = status
            man.setdefault("scope", {})["tasks"] = TASKS_SCOPE_STR
            man["tasks_refreshed_at"] = iso_now()
            with open(man_path + ".tmp", "w") as f: json.dump(man, f, indent=2)
            os.replace(man_path + ".tmp", man_path)
        except Exception as e:
            sys.stderr.write(f"[cal-vault] tasks-only: manifest patch skipped ({e})\n")
    print(f"[cal-vault] tasks-only refresh → {tasks_path} — "
          f"{status.get('tasks_kept','?')} tasks across {status.get('lists','?')} lists")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default: today, local)")
    ap.add_argument("--tasks-only", action="store_true",
                    help="refresh ONLY tasks.json in an existing day's vault (freshness re-grab; "
                         "skips email/calendar + the full rebuild)")
    args = ap.parse_args()
    date_str = args.date or time.strftime("%Y-%m-%d", time.localtime())
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        sys.stderr.write("cal-vault: --date must be YYYY-MM-DD\n")
        return 2

    final_dir = os.path.join(VAULT_ROOT, date_str)
    if args.tasks_only:
        return tasks_only_refresh(date_str, final_dir)

    tmp_dir = final_dir + ".tmp"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir, ignore_errors=True)
    os.makedirs(tmp_dir, exist_ok=True)

    sources = {}
    sources["inbox"] = pull_email("inbox", "category:primary in:inbox",
                                  os.path.join(tmp_dir, "inbox"), cap=INBOX_CAP)
    sources["sent"] = pull_email("sent", "in:sent newer_than:7d",
                                 os.path.join(tmp_dir, "sent"))
    sources["snoozed"] = pull_email("snoozed", "in:snoozed",
                                    os.path.join(tmp_dir, "snoozed"))
    sources["calendar"] = pull_calendar(os.path.join(tmp_dir, "calendar.json"), date_str)
    sources["tasks"] = pull_tasks(os.path.join(tmp_dir, "tasks.json"))

    manifest = {"date": date_str, "generated_at": iso_now(),
                "scope": {"inbox_cap": INBOX_CAP, "inbox_ceiling": INBOX_CEILING,
                          "sent": "7d", "snoozed": "all", "calendar": "+/-7d",
                          "tasks": TASKS_SCOPE_STR, "attachments": "not pulled"},
                "sources": sources}
    with open(os.path.join(tmp_dir, "_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

    # atomic swap into place
    if os.path.exists(final_dir):
        shutil.rmtree(final_dir, ignore_errors=True)
    os.replace(tmp_dir, final_dir)

    failed = [k for k, v in sources.items() if v.get("status") != "ok"]
    em = sources
    print(f"[cal-vault] wrote {final_dir} — "
          f"inbox {em['inbox'].get('pulled','?')}"
          + (f"(+{em['inbox'].get('total_available','?')} avail, OVERFLOW)" if em['inbox'].get('overflow') else "")
          + f" / sent {em['sent'].get('pulled','?')} / snoozed {em['snoozed'].get('pulled','?')}"
          + f" / {em['calendar'].get('events','?')} cal / {em['tasks'].get('tasks_kept','?')} tasks"
          + (f" · FAILED: {', '.join(failed)}" if failed else ""))
    return 0  # content/source gaps are findings, not failures


if __name__ == "__main__":
    sys.exit(main())

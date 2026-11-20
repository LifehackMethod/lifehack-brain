#!/usr/bin/env python3
"""gcjobs.py: the three scheduled jobs of Grand Central's Phase 1 (plan 1.3 and 1.4). Front room, generic.

  fast-clock   every 600 s. ONE job: (1) file what the mailroom dropped in <drop>/deliveries (transcripts.ingest),
               (2) the source pull, calendar and tasks only (pull.py --sources-only, a subprocess: the only place
               Google is reached, through the shared calendar/tasks doors), (3) alarm CANDIDATES (a list, nothing
               sent: the real triggers, the quiet-hours rule and the phone are his later rulings).
  morning      daily. morning.py hand_run for the default desk's day (that desk's records).
  midnight     daily 00:00. morning.midnight_entry for every recent day that has a staged write-up and no diary
               entry yet (the main diary, named in setup/desks.json). Created exclusively: a second run changes nothing.
        Nothing staged in the whole window is a good run with nothing to write (receipt staged_days=0,
        exit 0), never a stand-down: rc 75 on a `yes` row texts "paused" after 2x the interval (4P.0b).

This file does NO outside read of its own: no Gmail, no curl, no urllib. Mail text arrives by the one-way drop;
calendar and tasks arrive only through pull.py. Each job ends by writing a one-line proof (receipt) AFTER it has
checked the artifact itself, then calls the status lights (STATUS-LIGHT CALL SITE below). Exit codes follow the
cron SOP: 0 proof written, 75 stood down (nothing configured, not signed in, nothing to do, lock held), 2 transient,
1 failed. The receipt is the only thing that makes a run a success; every failed or stood-down run leaves the
earlier receipt untouched, so a stale proof ages and the runner's missed-run alert fires.

  python3 gcjobs.py fast-clock | morning | midnight   [--desk DESK] [--day YYYY-MM-DD]   (default desk: gc.json default_desk)
Env for tests: GC_SETUP_DIR (the setup folder), GC_DROP (drop folder, fast clock and morning), GC_STATE_ROOT (receipts),
AGE_FRONT_ROOM, AGE_NOTES_ROOT, AGE_MAILROOM_USER, GC_DATA_ROOT, RIG_DB. Every personal value comes through gc_settings.
Python 3.9 compatible."""
import contextlib
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = HERE
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import transcripts  # noqa: E402
import gc_settings  # noqa: E402


def default_drop():
    """The drop folder: GC_DROP if set and non-empty (tests / scratch runs), else the person's (gc.json drop_dir)."""
    return gc_settings.drop_dir()


RIG_HOME = gc_settings.data_root()
RIG_LOGIN = os.path.expanduser("~/.config/gws-rig")
PULL_TIMEOUT_S = 1500                      # under the 600 s clock x2.5; job-run's own watchdog is the outer limit
SOURCES = ("calendar", "tasks")
LOOKBACK_DAYS = 7                          # midnight: how far back it will catch up a missed night
NY_TZ = ZoneInfo("America/New_York") # the envelope window is an America/New_York day, like daily.py
SIGNED_OUT = re.compile(r"not logged in|not signed in|login required|invalid_grant|unauthenticated|no_token|"
                        r"credentials? (are |is )?(missing|expired|invalid)|refresh token", re.I)
NOT_SIGNED_IN = 75


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def state_dir(job):
    return os.path.join(gc_settings.state_dir(), job)


def write_atomic(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)


def write_receipt(job, line, state=None):
    """The proof line: ONE line, written last, atomically. The row's check reads it."""
    assert "\n" not in line
    path = os.path.join(state or state_dir(job), "last-run.txt")
    write_atomic(path, line + "\n")
    return path


# ---------------------------------------------------------------- locks (one protocol, shared with jobs/gc-daily-run.sh)
def _state_root():
    return gc_settings.state_dir()


def db_lock_path():
    """THE shared database-writer lock: gc-daily, the fast clock's pull and the morning job's source refresh all take it
    before writing the live database. A directory holding a file `pid`; a dead pid is a stale lock and is taken over."""
    return os.environ.get("GC_DB_LOCK") or os.path.join(_state_root(), "db-writer.lock")


def _pid_alive(pid):
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except (PermissionError, ValueError):
        return True if str(pid).isdigit() else False
    return True


def lock_holder_alive(path):
    """True when a live process holds the lock directory."""
    try:
        with open(os.path.join(path, "pid"), encoding="utf-8") as f:
            return _pid_alive(f.read().strip())
    except OSError:
        return os.path.isdir(path) and (time.time() - os.path.getmtime(path)) < 30   # just made, pid not written yet


def lock_take(path, wait_s=0, poll=2.0):
    """Take the lock directory `path`. -> True when taken, False when a live owner still holds it after wait_s."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    waited = 0.0
    while True:
        try:
            os.mkdir(path)
            with open(os.path.join(path, "pid"), "w", encoding="utf-8") as f:
                f.write("%d\n" % os.getpid())
            return True
        except FileExistsError:
            if not lock_holder_alive(path):
                shutil.rmtree(path, ignore_errors=True)       # stale: its owner is gone
                continue
            if waited >= wait_s:
                return False
            time.sleep(poll)
            waited += poll


def lock_release(path):
    try:
        with open(os.path.join(path, "pid"), encoding="utf-8") as f:
            mine = f.read().strip() == str(os.getpid())
    except OSError:
        return
    if mine:
        shutil.rmtree(path, ignore_errors=True)


MORNING_AFTER_HOUR = 5            # the fast clock starts the morning read on its first tick at or after 05:00 local
LAUNCH_MIN_GAP_S = 1800           # a morning that failed is not started again for 30 minutes
REFRESH_LOCK_WAIT_S = 120         # the morning waits this long for the database lock before reading stored sources
LAUNCH_MAX_PER_DAY = 6 # the hard ceiling on tries a day, wake resets aside (each try spends a model call; 4P.3D item 12)
LAUNCH_WAKE_RESET_S = 3600 # a gap this long since the last attempt means the Mac slept: the day's count resets
MORNING_ATTEMPTS = 3 # the detached morning run retries INSIDE itself before the day goes back to the fast clock (4P.3D slice W item A)
MORNING_ATTEMPT_WAIT_S = 300 # seconds between in-run attempts (a test seam: tests set 0)
ONCE_A_DAY_JOBS = ("gc-snapshot", "gc-" "diary-index", "gc-daily") # the fast clock starts these when no success today (item D), in this order
ONCE_LAUNCH_MAX_PER_DAY = 3 # at most 3 launches a day for a once-a-day job
ONCE_LAUNCH_MIN_GAP_S = 1800 # and never twice within half an hour
ENV_MAX_THREADS = 50 # the fast clock's envelope pull cap (item C)
ENV_FIRST_DAYS = 2 # the first envelope pull: 2 days back, like daily.py


def morning_run_lock(state=None):
    return os.path.join(state or state_dir("gc-morning"), "run.lock")


def launch_morning_detached(desk, state=None):
    """Start `gcjobs.py morning` as its OWN process (new session, no shared pipes, output to a log). The tick does not wait."""
    st = state or state_dir("gc-morning")
    os.makedirs(st, exist_ok=True)
    with open(os.path.join(st, "detached.log"), "ab") as log:
        subprocess.Popen([sys.executable, os.path.abspath(__file__), "morning", "--desk", desk], stdin=subprocess.DEVNULL,
                         stdout=log, stderr=log, start_new_session=True, cwd=ROOT, close_fds=True)


def morning_launch_check(now_local, desk=None, launcher=None, state=None):
    """Called by the fast clock every tick. -> one word for the proof line:
    not-due (before 05:00) · done (today's draft exists) · running (the morning's own lock is held by a live process) ·
    backoff / gave-up-today (a failing morning is not hammered) · launched (a detached morning was just started) ·
    launch-failed. The tick itself never waits for the morning read. 4P.3D slice W item A: the retries happen INSIDE
    the detached run (up to 3 attempts, 300 s apart); this launcher applies the per-wake rule (more than
    LAUNCH_WAKE_RESET_S since the last attempt resets the day's count) and the hard ceiling of 6 attempts a day,
    counting EVERY attempt — the morning run records each one in the ledger."""
    import morning
    desk = desk or gc_settings.default_desk()
    if now_local.hour < MORNING_AFTER_HOUR:
        return "not-due"
    day = now_local.date().isoformat()
    if morning.find_staged(morning.records_context_dir(morning.notes_root(), desk), day, desk):
        return "done"
    st = state or state_dir("gc-morning")
    if lock_holder_alive(morning_run_lock(st)):
        return "running"
    ledger = os.path.join(st, "launch.json")
    led = _load_ledger(ledger, day)
    now_ts = now_local.timestamp()
    if led.get("last_epoch") and now_ts - led["last_epoch"] > LAUNCH_WAKE_RESET_S:
        led = {"day": day, "attempts": 0, "last": 0} # those attempts were before the sleep, not this wake
    if led["attempts"] >= LAUNCH_MAX_PER_DAY:
        return "gave-up-today"
    if now_ts - led["last"] < LAUNCH_MIN_GAP_S:
        return "backoff"
    try:
        (launcher or launch_morning_detached)(desk, st)
    except OSError:
        return "launch-failed"
    led["attempts"] += 1
    led["last"] = now_ts
    led["last_epoch"] = now_ts
    write_atomic(ledger, json.dumps(led))
    return "launched"

def _load_ledger(path, day):
    """launch.json -> dict; a fresh day-ledger when the day changed or the file is missing/unreadable. Old ledgers
    without the newer keys load fine (every read defaults its missing key)."""
    try:
        with open(path, encoding="utf-8") as f:
            led = json.load(f)
    except (OSError, ValueError):
        led = {}
    if led.get("day") != day:
        led = {"day": day, "attempts": 0, "last": 0}
    return led

def mark_morning_outcome(ok, state=None):
    """Record ONE morning attempt in the launch ledger (4P.3D slice W item A): every attempt counts toward the
    day's ceiling of 6, and three consecutive failures set the failed flag the morning light reads. A success
    clears the streak. Old ledgers without the keys load fine."""
    st = state or state_dir("gc-morning")
    os.makedirs(st, exist_ok=True)
    path = os.path.join(st, "launch.json")
    led = _load_ledger(path, datetime.date.today().isoformat())
    led["attempts"] = led.get("attempts", 0) + 1
    led["last"] = time.time()
    led["last_epoch"] = time.time()
    if ok:
        led["fail_streak"] = 0
        led["failed"] = False
    else:
        led["fail_streak"] = led.get("fail_streak", 0) + 1
        led["failed"] = led["fail_streak"] >= 3 # 3 tries failed: the light says "retrying within the hour"
    write_atomic(path, json.dumps(led))

# ---------------------------------------------------------------- the once-a-day launcher (slice W item D)
def once_receipt_ok(job, today, state_root=None):
    """True when the job's receipt is a success dated today. The trigger is "no success today", never a clock
    hour — a laptop first opened at 12:00 gets its once-a-day jobs at 12:00."""
    try:
        with open(os.path.join(state_root or _state_root(), job, "last-run.txt"), encoding="utf-8") as f:
            line = f.readline().strip()
    except OSError:
        return False
    return line.startswith(job + " ok") and ("date=%s" % today) in line

def launch_once_detached(job, code_root=None):
    """Start the job through the scheduler's OWN entry: job-run.sh <job> --force under LIFEHACK_CODE_ROOT, so the
    door, the lock and the row check still apply (--force never pushes). Detached, own session, output to the
    job's detached.log. The tick never waits."""
    root = code_root or gc_settings.plugin_root()
    runner = os.path.join(root, "system", "tools", "job-run.sh")
    st = state_dir(job)
    os.makedirs(st, exist_ok=True)
    env = dict(os.environ)
    env["LIFEHACK_CODE_ROOT"] = root
    with open(os.path.join(st, "detached.log"), "ab") as log:
        subprocess.Popen(["bash", runner, job, "--force"], stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True, cwd=root, close_fds=True, env=env)

def once_a_day_check(now_local, launcher=None, state_root=None, code_root=None):
    """Slice W item D: on each fast-clock tick, for each of ONCE_A_DAY_JOBS in order — no success dated today,
    its lock free and its per-day launch ledger allowing it (at most ONCE_LAUNCH_MAX_PER_DAY launches a day,
    ONCE_LAUNCH_MIN_GAP_S apart) -> start it detached through the scheduler.
    -> {job: word} for the proof line: launched / done / running / backoff / gave-up-today / no-runner / launch-failed."""
    day = now_local.date().isoformat()
    now_ts = now_local.timestamp()
    words = {}
    for job in ONCE_A_DAY_JOBS:
        if once_receipt_ok(job, day, state_root):
            words[job] = "done"
            continue
        st = os.path.join(state_root or _state_root(), job)
        if lock_holder_alive(os.path.join(st, "run.lock")):
            words[job] = "running"
            continue
        ledger = os.path.join(st, "launch.json")
        led = _load_ledger(ledger, day)
        if led["attempts"] >= ONCE_LAUNCH_MAX_PER_DAY:
            words[job] = "gave-up-today"
            continue
        if now_ts - led["last"] < ONCE_LAUNCH_MIN_GAP_S:
            words[job] = "backoff"
            continue
        root = code_root or gc_settings.plugin_root()
        if not os.path.isfile(os.path.join(root, "system", "tools", "job-run.sh")):
            words[job] = "no-runner" # said, never guessed: the launcher cannot start what it cannot find
            continue
        try:
            (launcher or launch_once_detached)(job, code_root)
        except OSError:
            words[job] = "launch-failed"
            continue
        led["attempts"] += 1
        led["last"] = now_ts
        led["last_epoch"] = now_ts
        write_atomic(ledger, json.dumps(led))
        words[job] = "launched"
    return words

# ---------------------------------------------------------------- the fast clock's envelope pull (slice W item C)
def read_envelope_watermark():
    """source_state['envelopes'].last_success_at (the fast clock's OWN watermark; gc-daily's "daily" one is
    separate), read-only, or None on the first run or when the database cannot be read."""
    try:
        import store
        r = store.get_source_state("envelopes")
        return r["last_success_at"] if r and r["last_success_at"] else None
    except Exception: # noqa: BLE001 — no database yet is the first run, not a crash
        return None

def envelope_after(wm, now=None, first_days=ENV_FIRST_DAYS):
    """The --after date for the envelope pull: the watermark's own day re-covered, in America/New_York (the same
    rule daily.window uses; pull.py's --after is inclusive). No watermark -> first_days back."""
    now = now or datetime.datetime.now()
    if wm:
        try:
            t = datetime.datetime.fromisoformat(str(wm).replace("Z", "+00:00"))
            return t.astimezone(NY_TZ).date().isoformat()
        except ValueError:
            pass
    return (now.date() - datetime.timedelta(days=first_days)).isoformat()

def run_envelope_pull(after, max_threads=ENV_MAX_THREADS):
    """The envelope pull as a subprocess, the same call shape daily.py uses: pull.py --after <date>
    --max-threads <cap>. -> (rc, output). pull.py records source_state['envelopes'] itself on success."""
    p = subprocess.run([sys.executable, os.path.join(ROOT, "pull.py"), "--after", after,
        "--max-threads", str(max_threads)], capture_output=True, text=True, timeout=PULL_TIMEOUT_S, cwd=ROOT)
    return p.returncode, (p.stdout or "") + (p.stderr or "")

def run_envelope_step(envelope_pull, envelope_watermark, out, now=None):
    """One fast-clock envelope attempt, wrapped: never raises, so the tick goes on. -> (rc, text)."""
    try:
        wm = (envelope_watermark or read_envelope_watermark)()
        after = envelope_after(wm, now=now)
        rc, text = (envelope_pull or run_envelope_pull)(after)
        out("[fast-clock] 2b. envelope pull (after %s): rc=%s" % (after, rc))
        return rc, text
    except subprocess.TimeoutExpired:
        return 2, "envelope pull timed out"
    except Exception as e: # noqa: BLE001
        return 1, "envelope pull failed: %s: %s" % (type(e).__name__, e)

def status_lights_call(only, out=print):
    """THE one place a job asks for its status light. The writer is status_lights.py (another helper builds it;
    this only calls its command line entry, it builds no light). A light problem is printed loudly to stderr and never
    changes the job's own result: the proof line, not the light, decides success."""
    try:
        import status_lights
    except ImportError as e:
        print("[gcjobs] STATUS LIGHT NOT WRITTEN: status_lights.py is not there yet (%s)" % e, file=sys.stderr)
        return None
    try:
        rc = status_lights.main(["--config", gc_settings.setup_path("status_lights.json"), "--only", only])
    except Exception as e:      # a light must never crash its caller, and must never be silent
        print("[gcjobs] STATUS LIGHT NOT WRITTEN (%s): %s" % (type(e).__name__, e), file=sys.stderr)
        return None
    if rc not in (0, None):
        print("[gcjobs] status lights (%s) exited %s" % (only, rc), file=sys.stderr)
    return rc


# ================================================================ 1.3 the fast clock
def rig_login_present():
    return os.path.isfile(os.path.join(RIG_LOGIN, "credentials.enc"))


def run_pull(mode):
    """Default source pull: pull.py --sources-only, calendar and tasks only (never filters or contacts: not this
    job's business). -> (rc, output). A subprocess, so the fast clock itself holds no Google code."""
    p = subprocess.run([sys.executable, os.path.join(ROOT, "pull.py"), "--sources-only", "--calendar", mode,
                        "--tasks", mode, "--filters", "never", "--contacts", "never"],
                       capture_output=True, text=True, timeout=PULL_TIMEOUT_S, cwd=ROOT)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


_PULL_FRESH = re.compile(r"^\[pull\] skipping (calendar|tasks): fetched successfully within", re.M)
_PULL_DONE = re.compile(r"^\[pull\] (calendar|tasks): pulled (\d+) row\(s\), marked fresh", re.M)
_PULL_BAD = re.compile(r"^\[pull\] (calendar|tasks): pulled \d+ row\(s\) but \d+ error\(s\) recorded", re.M)


def parse_pull(text):
    """pull.py's own lines -> {"calendar": "fetched"|"fresh"|"error"|None, "tasks": ...}. A source with no line at all
    is None: the pull did not account for it."""
    res = dict((s, None) for s in SOURCES)
    for m in _PULL_FRESH.finditer(text):
        res[m.group(1)] = "fresh"
    for m in _PULL_DONE.finditer(text):
        res[m.group(1)] = "fetched"
    for m in _PULL_BAD.finditer(text):
        res[m.group(1)] = "error"
    return res


_MAP_YN = {"yes": True, "no": False}


def candidate_from_row(row, today):
    """A catalogue row (typed fields only) -> an alarm candidate, or None when it was not read in full. The catalogue's
    'safe' is the alarm's 'clean'. Triage observations become the scorecard's: yes/no/cant_tell -> True/False/None;
    a stated deadline date becomes days from today."""
    t = row.get("triage")
    if not isinstance(t, dict) or row.get("seen") != "full":
        return None
    o = t.get("obs") if isinstance(t.get("obs"), dict) else {}
    dd = None
    if isinstance(t.get("deadline"), str) and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", t["deadline"]):
        try:
            dd = (datetime.date.fromisoformat(t["deadline"]) - today).days
        except ValueError:
            dd = None
    return {"message_id": row.get("message_id"), "thread_id": row.get("thread_id"),
            "verdict": "clean" if row.get("verdict") == "safe" else row.get("verdict"),
            "obs": {"deadline_days": dd, "direct_ask": _MAP_YN.get(o.get("direct_ask")),
                    "reply_expected": _MAP_YN.get(o.get("reply_expected")), "money": _MAP_YN.get(o.get("money_involved"))}}


def message_levels(con):
    """message id -> levels above him for its sender, from store_levels.levels_above_me through the address's person. Only messages
    whose sender has a known level appear; anything else is not in the dict and counts 0."""
    import store_levels
    lv = store_levels.levels_above_me(con)
    out = {}
    for mid, pkey in con.execute(
            "SELECT m.id, p.key FROM messages m JOIN kg_things ad ON ad.kind='address' AND ad.name=lower(m.from_addr) "
            "JOIN kg_links l ON l.from_id=ad.id AND l.kind='address_of' AND l.replaced_by IS NULL AND l.true_until IS NULL "
            "JOIN kg_things p ON p.id=l.to_id WHERE m.is_sent=0"):
        v = lv.get(pkey)
        if v and v[0] is not None and v[0] > 0:
            out[mid] = int(v[0])
    return out


def alarm_candidates(since_iso, today, settings_path=None, out_path=None):
    """Alarm CANDIDATES for the mail filed since `since_iso`: which ones the settings' triggers would match.
    Writes ONE line per match to a local candidates file (typed fields and score reasons only, never email text) and
    reads nothing, sends nothing, raises nothing: engine/alarm.run is not called here (its reader and phone are his later
    rulings). A message already in the file is not added twice. Sender standing is not used yet (0.0): proposed points.
    -> (considered, matched)"""
    import alarm, scorecard
    settings = alarm.Settings.load(settings_path or gc_settings.setup_path("alarm-settings.json"))
    cfg = scorecard.Config.load()
    levels = {}      # message id -> levels above him (step 3 tie-up b); unknown = 0 points. His own weights win (tie-up a).
    try:
        import store
        with store._read() as _con:
            cfg.use_owner_level_points(_con)
            levels = message_levels(_con)
    except Exception:  # noqa: BLE001  (no database / no model: the level counts for nothing, never a crash)
        levels = {}
    out_path = out_path or os.path.join(transcripts.front_room(), "alarm-candidates.jsonl")
    seen = set()
    try:
        with open(out_path, encoding="utf-8") as f:
            for ln in f:
                try:
                    seen.add(json.loads(ln).get("message_id"))
                except ValueError:
                    pass
    except OSError:
        pass
    considered, hits = 0, []
    for row in transcripts.catalogue_meta():
        if not (row.get("ingested_at") or "") >= since_iso:
            continue
        c = candidate_from_row(row, today)
        if not c:
            continue
        considered += 1
        iu = scorecard.importance_urgency(c["obs"], cfg, 0.0, False, level=levels.get(c["message_id"]))
        why = settings.matching({"iu": iu, "candidate": c})
        if why and c["message_id"] not in seen:
            hits.append({"at": now_iso(), "message_id": c["message_id"], "thread_id": c["thread_id"], "triggers": why,
                         "urgency": iu["urgency"], "importance": iu["importance"], "reasons": iu["reasons"],
                         "status": "candidate only: nothing read, nothing sent"})
    if hits:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "a", encoding="utf-8") as f:
            for h in hits:
                f.write(json.dumps(h, sort_keys=True) + "\n")
    return considered, len(hits)


def fast_clock(drop=None, state=None, pull=None, login_ok=None, mailroom_uid=None, source_mode=None,
               status_light=None, today=None, candidates=None, out=print, db_lock=None, now_local=None,
               launch=None, desk=None, envelope_pull=None, envelope_watermark=None, once=None):
    """-> exit code. The receipt is written only when every step is accounted for."""
    desk = desk or gc_settings.default_desk()
    drop = drop or default_drop()
    source_mode = source_mode or os.environ.get("GC_SOURCE_MODE", "auto")
    status_light = status_light or status_lights_call
    started = now_iso()
    today = today or datetime.date.today()
    deliv = os.path.join(drop, "deliveries")
    rc = 0
    problems = []
    if not os.path.isdir(deliv):
        out("[fast-clock] stood down: %s does not exist (the mailroom is not installed here)" % deliv)
        return 75
    # (1) front-room ingest. The folder is listed BEFORE and AFTER by this job, so "cleared" is what the folder shows,
    # not what ingest says about itself.
    try:
        before = sorted(n for n in os.listdir(deliv) if not n.startswith("."))
    except OSError as e:
        out("[fast-clock] FAIL: cannot read the deliveries folder (%s); a quiet zero would be a lie" % type(e).__name__)
        status_light("intake,mailroom")
        return 1
    counts = transcripts.ingest(deliv, mailroom_uid=mailroom_uid)
    if "skipped" in counts:
        out("[fast-clock] stood down: another ingest is running")
        return 75
    after = set(os.listdir(deliv))
    waiting, cleared = len(before), len([n for n in before if n not in after])
    filed, dup, ref = counts.get("ingested", 0), counts.get("duplicate", 0), counts.get("refused", 0)
    out("[fast-clock] 1. deliveries: %d waiting, %d cleared (filed %d, duplicate %d, refused %d, deferred %d)" % (
        waiting, cleared, filed, dup, ref, counts.get("deferred", 0)))
    if cleared != waiting or counts.get("deferred", 0):
        problems.append("deliveries_not_cleared:%d_of_%d" % (cleared, waiting))
    if filed + dup + ref < waiting:
        problems.append("ingest_counts_short")
    # (2) source pull
    pulled = dict((s, None) for s in SOURCES)
    signed_out = False
    db_lock = db_lock or db_lock_path()
    db_state = "done"
    if lock_holder_alive(db_lock) or not lock_take(db_lock):
        # gc-daily (or the morning's refresh) is writing the database: skip ONLY the database part, say so, and go on.
        # Not a failure: gc-daily's long runs (8.4 h on 11-15) would otherwise break every tick.
        db_state = "held"
        pulled = dict((s, "skipped") for s in SOURCES)
        out("[fast-clock] 2. source pull: SKIPPED, the database is held by another run (gc-daily); the rest of the tick goes on")
    elif not (login_ok or rig_login_present)():
        lock_release(db_lock)
        out("[fast-clock] 2. source pull: the rig is not signed in to Google; calendar and tasks NOT pulled")
        signed_out = True
    else:
        try:
            prc, text = (pull or run_pull)(source_mode)
        except subprocess.TimeoutExpired:
            prc, text = 2, "pull timed out"
        finally:
            lock_release(db_lock)
        pulled = parse_pull(text)
        out("[fast-clock] 2. source pull (%s): rc=%s calendar=%s tasks=%s" % (source_mode, prc, pulled["calendar"], pulled["tasks"]))
        if prc != 0 or any(v in (None, "error") for v in pulled.values()):
            if SIGNED_OUT.search(text):
                signed_out = True
            else:
                problems.append("source_pull_failed" if prc != 0 else "source_not_accounted:" + ",".join(
                    s for s, v in pulled.items() if v in (None, "error")))
                rc = 2 if prc == 2 or text == "pull timed out" else 1
                for ln in text.strip().splitlines()[-3:]:
                    out(" pull: " + ln[:200])
        # 2b. the envelope pull (slice W item C): the mail lanes on the fast clock, under the SAME database-writer
        # lock, re-taken around it (a sources-pull failure does not stop the mail lanes; a held lock skips it).
        if lock_take(db_lock):
            try:
                env_rc, env_text = run_envelope_step(envelope_pull, envelope_watermark, out,
                now=datetime.datetime.combine(today, datetime.time()))
            finally:
                lock_release(db_lock)
            if env_rc != 0:
                if SIGNED_OUT.search(env_text):
                    signed_out = True
                else:
                    problems.append("envelope_pull_failed")
                    rc = rc or (2 if env_rc == 2 else 1)
                for ln in env_text.strip().splitlines()[-3:]:
                    out(" envelope: " + ln[:200])
        else:
            out("[fast-clock] 2b. envelope pull: SKIPPED, the database is held by another run")
    # (3) alarm candidates (no read, no send)
    considered, matched = 0, 0
    try:
        considered, matched = (candidates or alarm_candidates)(started, today)
        out("[fast-clock] 3. alarm candidates: %d new message(s) looked at, %d match a trigger (candidates only, nothing sent)" % (considered, matched))
    except Exception as e:
        problems.append("alarm_candidates_failed:%s" % type(e).__name__)
        out("[fast-clock] 3. alarm candidates FAILED: %s: %s" % (type(e).__name__, e))
    # (3b) the morning: start it detached when it is due and not running
    try:
        morning_state = morning_launch_check(now_local or datetime.datetime.now(), desk, launch)
    except Exception as e:
        morning_state = "check-failed"
        problems.append("morning_launch_check_failed:%s" % type(e).__name__)
    out("[fast-clock] 3b. morning: %s" % morning_state)
    # (3c) the once-a-day jobs (slice W item D): started through the scheduler when no success today
    try:
        once_words = (once or once_a_day_check)(now_local or datetime.datetime.now())
    except Exception as e:  # noqa: BLE001 — a launcher problem is said, and the tick goes on
        once_words = dict((j, "check-failed") for j in ONCE_A_DAY_JOBS)
        problems.append("once_a_day_check_failed:%s" % type(e).__name__)
    for _j in ONCE_A_DAY_JOBS:
        out("[fast-clock] 3c. %s: %s" % (_j, once_words.get(_j)))
    # (4) the proof, only if everything is accounted for
    if signed_out and not problems:
        status_light("intake,mailroom")
        out("[fast-clock] stood down: not signed in (exit 75); deliveries were filed, no proof line written")
        return 75
    if problems:
        out("[fast-clock] FAIL, no proof line written: " + ", ".join(problems))
        status_light("intake,mailroom")
        return rc or 1
    line = ("gc-fast-clock ok date=%s waiting=%d cleared=%d filed=%d duplicate=%d refused=%d calendar=%s tasks=%s db=%s "
            "considered=%d candidates=%d morning=%s once_snapshot=%s once_diary_index=%s once_daily=%s at=%s" % (today.isoformat(), waiting, cleared, filed, dup, ref,
                                                              pulled["calendar"], pulled["tasks"], db_state, considered,
                                                              matched, morning_state, once_words.get("gc-snapshot"), once_words.get("gc-" "diary-index"), once_words.get("gc-daily"), now_iso()))
    write_receipt("gc-fast-clock", line, state)
    out(line)
    status_light("intake,mailroom")
    return 0


# ================================================================ 1.4 the morning job
_PROOF = re.compile(r"^morning read (?P<day>[0-9]{4}-[0-9]{2}-[0-9]{2}) \((?P<desk>[a-z0-9\-]+)\): (?P<new>\d+) new of "
                    r"(?P<exam>\d+) examined; used (?P<used>\d+), sorted out by triage (?P<sorted>\d+), skipped with a "
                    r"reason (?P<skip>\d+);")


def newest_staged(rec_dir, day, desk):
    import morning
    files = morning.find_staged(rec_dir, day, desk)
    return os.path.basename(files[-1]) if files else None


def refresh_sources(pull, login_ok, db_lock, out):
    """The morning alone forces a fresh calendar and tasks pull just before it reads (mode "always"). Takes the shared
    database lock (waits up to 2 min for the fast clock's short pull; gc-daily may hold it for hours, then the morning
    reads what is stored and says so). -> "refreshed" | "held" | "failed"."""
    if not lock_take(db_lock, wait_s=REFRESH_LOCK_WAIT_S):
        out("[morning] sources NOT refreshed: the database is held by another run; reading what is stored")
        return "held"
    try:
        if not (login_ok or rig_login_present)():
            out("[morning] sources NOT refreshed: the rig is not signed in to Google; reading what is stored")
            return "failed"
        try:
            prc, text = (pull or run_pull)("always")
        except subprocess.TimeoutExpired:
            out("[morning] sources NOT refreshed: the pull timed out; reading what is stored")
            return "failed"
        got = parse_pull(text)
        if prc != 0 or any(v != "fetched" for v in got.values()):
            out("[morning] sources NOT refreshed (pull rc=%s, calendar=%s, tasks=%s); reading what is stored" % (prc, got["calendar"], got["tasks"]))
            return "failed"
        out("[morning] sources refreshed just before the read (calendar and tasks pulled)")
        return "refreshed"
    finally:
        lock_release(db_lock)


def morning_job(day=None, desk=None, state=None, hand_run=None, status_light=None, extra_argv=(), out=print,
                pull=None, login_ok=None, db_lock=None, run_lock=None):
    """One morning read for `day` (default today, local), under its OWN lock (two mornings never run at once). The model
    call is hand_run's (a tool-less claude); this job never reads email text. -> exit code."""
    desk = desk or gc_settings.default_desk()
    run_lock = run_lock or morning_run_lock()
    if not lock_take(run_lock):
        out("[morning] stood down: another morning read is running")
        return 75
    try:
        return _morning_locked(day, desk, state, hand_run, status_light, extra_argv, out, pull, login_ok, db_lock or db_lock_path())
    finally:
        lock_release(run_lock)


def _morning_locked(day, desk, state, hand_run, status_light, extra_argv, out, pull, login_ok, db_lock):
    import morning
    status_light = status_light or status_lights_call
    sources = refresh_sources(pull, login_ok, db_lock, out)
    day = day or datetime.date.today().isoformat()
    argv = ["--i-know-this-calls-the-real-model", "--desk", desk, "--day", day] + list(extra_argv)
    notes = morning.notes_root()
    rec_dir = morning.records_context_dir(notes, desk)
    # 4P.3D slice W item A: the morning read retries INSIDE this detached run — up to MORNING_ATTEMPTS
    # consecutive attempts, MORNING_ATTEMPT_WAIT_S apart — before the day is handed back to the fast clock.
    # A reply-shape failure already gets ONE repair call inside hand_run; each attempt that still fails
    # counts toward the day's ceiling and the streak the morning light reads.
    for attempt in range(1, MORNING_ATTEMPTS + 1):
        lines = []

        def collect(m):
            lines.append(str(m))
            out(m)

        rc = (hand_run or morning.hand_run)(argv, out=collect)
        text = "\n".join(lines)
        proof = None
        for ln in lines: # the coverage line (also a FAILED line): the lights read it
            i = ln.find("morning read ") # hand_run prefixes its lines ("hand-run: coverage: ...")
            if i >= 0 and re.match(r"morning read [0-9]{4}-", ln[i:]):
                proof = ln[i:].strip()
        if proof:
            write_atomic(os.path.join(gc_settings.state_dir(), "morning", "last-proof.txt"),
                proof + "\n")
        problems = []
        n = None
        draft = None
        if rc != 0:
            if SIGNED_OUT.search(text):
                status_light("morning")
                out("[morning] stood down: not signed in (exit 75)")
                return 75
            problems = ["hand_run_exit_%s" % rc]
        else:
            m = _PROOF.match(proof or "")
            draft = newest_staged(rec_dir, day, desk)
            if not m:
                problems.append("proof_line_unreadable")
            else:
                n = dict((k, int(m.group(k))) for k in ("new", "exam", "used", "sorted", "skip"))
                if n["used"] + n["sorted"] + n["skip"] != n["new"] or "NOT ACCOUNTED" in proof or "every new email accounted for" not in proof:
                    problems.append("new_emails_not_accounted")
                if m.group("day") != day or m.group("desk") != desk:
                    problems.append("proof_is_for_another_day_or_desk")
            if not draft:
                problems.append("no_staged_draft_for_%s" % day)
        if not problems:
            line = "gc-morning ok date=%s desk=%s new=%d accounted=%d examined=%d draft=%s sources=%s at=%s" % (
                day, desk, n["new"], n["used"] + n["sorted"] + n["skip"], n["exam"], draft, sources, now_iso())
            write_receipt("gc-morning", line, state)
            out(line)
            status_light("morning")
            mark_morning_outcome(True, state) # a good run clears the failure streak
            return 0
        mark_morning_outcome(False, state) # the attempt counts toward the ceiling and the streak
        out("[morning] attempt %d of %d failed: %s" % (attempt, MORNING_ATTEMPTS, ", ".join(problems)))
        if attempt < MORNING_ATTEMPTS and MORNING_ATTEMPT_WAIT_S > 0:
            time.sleep(MORNING_ATTEMPT_WAIT_S)
    out("[morning] FAIL: %d tries failed, retrying within the hour; no proof line written" % MORNING_ATTEMPTS)
    status_light("morning")
    return 1

def midnight_job(desk=None, today=None, lookback=LOOKBACK_DAYS, state=None, status_light=None, out=print, index_refresh=None):
    """For each of the last `lookback` days before today that has a staged write-up: write that day's diary entry if it
    has none (midnight_entry creates exclusively and never opens an earlier entry). Catching up means a night the Mac
    slept through is written on wake. Nothing staged in the whole window = a good run with nothing to write (receipt staged_days=0, exit 0;
a stand-down here would text "paused" every quiet night, 4P.0b)."""
    import morning
    desk = desk or gc_settings.default_desk()
    status_light = status_light or status_lights_call
    today = today or datetime.date.today()
    notes = morning.notes_root()
    rec_dir = morning.records_context_dir(notes, desk)
    import routing, diary_names
    table = routing.load_table()
    desks_cfg = diary_names.load()
    # every desk's diary, by its name (the pattern and the desk list live in setup/, never here); a desk with no folder is skipped
    roots = dict((diary_names.diary_name(d, desks_cfg), diary_names.diary_folder(notes, d)) for d in desks_cfg["desks"]
                 if os.path.isdir(os.path.join(notes, "desks", d)))
    form_dir = os.path.join(transcripts.catalogue_dir(), "morning")
    staged_days, written, existing, newest, problems, entries = 0, 0, 0, None, [], 0
    for k in range(1, lookback + 1):
        day = (today - datetime.timedelta(days=k)).isoformat()
        staged = morning.find_staged(rec_dir, day, desk)
        if not staged:
            continue
        staged_days += 1
        with _read_con() as con:
            rs = morning.midnight_entries(day, staged, roots, table, "tree", form_dir, con=con)
        for name, r in sorted(rs.items()):
            if r["status"] == "written":
                entries += 1
            elif r["status"] != "exists":
                problems.append("%s:%s:%s" % (day, name, r["status"]))
            if r["status"] in ("written", "exists") and not os.path.isfile(r["path"]):
                problems.append("%s:%s:entry_missing_after_write" % (day, name))
        if any(r["status"] == "written" for r in rs.values()):
            written += 1
        elif rs and all(r["status"] == "exists" for r in rs.values()):
            existing += 1
        elif not rs:
            problems.append("%s:nothing_staged" % day)
        newest = newest or day
        out("[midnight] %s: %s" % (day, ", ".join("%s %s" % (n, r["status"]) for n, r in sorted(rs.items()))))
    if not staged_days and not problems:
        # 4P.0b: nothing staged in the window is a GOOD RUN with nothing to write, not a stand-down.
        # rc 75 on a `yes` row texts "paused" after 2x the interval (cron SOP section 4), and with no
        # feeds the daily diary job ends here every night -- the very text the rulings forbid. The
        # receipt is honest real content that varies (date, desk, counts, time), which the row's
        # check reads as a good run; it is not a presence check.
        # Build window review: the SAME shape as a working night (staged_days=N settled=N ... newest=...), so one
        # row check (no `|` allowed in a check) reads both; newest=- marks the quiet night.
        line = ("gc-midnight ok date=%s desk=%s staged_days=0 settled=0 written=0 existing=0 newest=- at=%s"
                % (today.isoformat(), desk, now_iso()))
        write_receipt("gc-midnight", line, state)
        out("[midnight] no morning write-up in the last %d days: nothing to write (receipt written)" % lookback)
        return 0
    if problems or written + existing != staged_days:
        out("[midnight] FAIL, no proof line written: " + ", ".join(problems or ["not_settled"]))
        return 1
    if index_refresh:     # 4.4: the diary index follows the files, one refresh per diary; a failure is said, never a reason to lose the night's entry
        for name, root in sorted(roots.items()):
            try:
                out("[midnight] diary index %s: %s" % (name, index_refresh(name, root, notes)))
            except Exception as e:
                out("[midnight] diary index NOT refreshed for %s: %s" % (name, e))
        import local_first
        for n in local_first.take_notes():
            out("[midnight] NOTE: %s: %s" % (n["path"], n["why"]))
    line = "gc-midnight ok date=%s desk=%s staged_days=%d settled=%d written=%d existing=%d newest=%s at=%s entries=%d" % (
        today.isoformat(), desk, staged_days, written + existing, written, existing, newest, now_iso(), entries)
    write_receipt("gc-midnight", line, state)
    out(line)
    # no light is defined for the diary yet (status_lights.py has mailroom, intake, morning, backup): none called.
    return 0

# ================================================================ 4.6 the 7-day backfill
BACKFILL_DAYS = 7
BACKFILL_STAMP = "stamp: machine draft, backfilled, unconfirmed"
LIVE_DB = gc_settings.db_path()


def _check_window(first, last, today):
    """Refuse (ValueError) anything outside the 7 days BEFORE today: a bad date, last before first, more than 7 days,
    today itself (the midnight job never writes today, coordinator ruling 2026-11-17) or a day after it."""
    try:
        a, b, t = (datetime.date.fromisoformat(x) for x in (first, last, today))
    except ValueError:
        raise ValueError("bad date")
    if b < a:
        raise ValueError("last day is before the first")
    if (b - a).days + 1 > BACKFILL_DAYS:
        raise ValueError("more than %d days" % BACKFILL_DAYS)
    if b > t:
        raise ValueError("a day in the future")
    if b == t:
        raise ValueError("today: the midnight job writes only days before today")
    if (t - a).days > BACKFILL_DAYS:
        raise ValueError("starts more than %d days back" % BACKFILL_DAYS)


def backfill(first, last, notes, db, desk=None, today=None, records_dir=None, form_dir=None, out=print, real=False):
    """4.6: the SAME machinery as the midnight job (morning.midnight_entries) for the days first..last (at most the last 7),
    each entry stamped 'machine draft, backfilled, unconfirmed'. An existing day is skipped (exclusive create; never opened for
    writing). Index refreshed on `db` (a sqlite file) afterwards. The real notes folder or the live database needs real=True.
    Reports per day and per diary: written / skipped (existing) / nothing. -> 0 ok, 2 refused or problem."""
    import morning, routing, diary_names
    import store, store_diary
    desk = desk or gc_settings.default_desk()
    today = today or datetime.date.today().isoformat()
    try:
        _check_window(first, last, today)
    except ValueError as e:
        out("[backfill] REFUSED: %s (window: the last %d days, ending today)" % (e, BACKFILL_DAYS))
        return 2
    is_real = os.path.realpath(notes) == os.path.realpath(gc_settings.configured_notes_root()) or os.path.realpath(db) == os.path.realpath(LIVE_DB)
    if is_real and not real:
        out("[backfill] REFUSED: that is the real notes folder or the live database; pass --real to mean it")
        return 2
    table = routing.load_table()
    cfg = diary_names.load()
    roots = dict((diary_names.diary_name(d, cfg), diary_names.diary_folder(notes, d)) for d in cfg["desks"]
                 if os.path.isdir(os.path.join(notes, "desks", d)))
    rec_dir = records_dir or morning.records_context_dir(notes, desk)
    form_dir = form_dir or os.path.join(transcripts.catalogue_dir(), "morning")
    prev_path = store._path
    store.set_path(db)                      # every database touch below is the COPY named by --db, through the front door
    problems = 0
    try:
        with store._read() as con:
            day = datetime.date.fromisoformat(first)
            while day <= datetime.date.fromisoformat(last):
                d = day.isoformat()
                staged = morning.find_staged(rec_dir, d, desk)
                rs = morning.midnight_entries(d, staged, roots, table, "tree", form_dir, con=con, stamp=BACKFILL_STAMP) if staged else {}
                for name in sorted(roots):
                    r = rs.get(name)
                    if r is None:
                        out("[backfill] %s %s: nothing %s" % (d, name, "routed here" if staged else "staged"))
                    elif r["status"] == "written":
                        out("[backfill] %s %s: written" % (d, name))
                    elif r["status"] == "exists":
                        out("[backfill] %s %s: skipped (existing)" % (d, name))
                    else:
                        problems += 1
                        out("[backfill] %s %s: %s %s" % (d, name, r["status"], r.get("problems", "")))
                day += datetime.timedelta(days=1)
        with store._write() as w:
            for name, root in sorted(roots.items()):
                out("[backfill] diary index %s: %s" % (name, store_diary.refresh_index(w, name, root, notes)))
    finally:
        store.set_path(prev_path)
    return 2 if problems else 0


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="gcjobs.py")
    ap.add_argument("job", choices=("fast-clock", "morning", "midnight", "backfill"))
    ap.add_argument("--from", dest="first", default=None)
    ap.add_argument("--to", dest="last", default=None)
    ap.add_argument("--notes", default=None, help="backfill: notes root to write into (a test copy)")
    ap.add_argument("--db", default=None, help="backfill: the sqlite file (a copy) to read keys from and refresh the index in")
    ap.add_argument("--real", action="store_true", help="backfill: allow the real notes folder or the live database")
    ap.add_argument("--desk", default=None, help="the desk (default: gc.json default_desk)")
    ap.add_argument("--day", default=None)
    ap.add_argument("--drop", default=None, help="drop folder (default: $GC_DROP, else gc.json drop_dir)")
    ap.add_argument("--any-time", action="store_true")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    if a.job == "backfill":
        import morning
        if not (a.first and a.last and a.db):
            print("[backfill] needs --from, --to and --db")
            return 2
        return backfill(a.first, a.last, a.notes or morning.notes_root(), a.db, desk=a.desk, real=a.real)
    if a.job == "fast-clock":
        return fast_clock(drop=a.drop or default_drop())
    if a.job == "morning":
        # The fast clock starts the morning after 05:00. A job-run row firing at 00:00 must not make a premature draft:
        # before 05:00 it stands down, unless this is a forced test run (job-run sets JOB_RUN_FORCED=1) or --any-time.
        if datetime.datetime.now().hour < MORNING_AFTER_HOUR and not a.any_time and os.environ.get("JOB_RUN_FORCED") != "1":
            print("[morning] stood down: before %02d:00 local (the fast clock starts the morning read after that)" % MORNING_AFTER_HOUR)
            return 75
        return morning_job(day=a.day, desk=a.desk, extra_argv=(["--drop", a.drop] if a.drop else []))
    return midnight_job(desk=a.desk, index_refresh=_live_index_refresh(a.desk))


@contextlib.contextmanager
def _read_con():
    """A read-only database connection (through store) for the keys check, or None when there is none (keys are then never written unchecked)."""
    try:
        import store
        cm = store._read()
        con = cm.__enter__()
    except Exception:
        yield None
        return
    try:
        yield con
    finally:
        cm.__exit__(None, None, None)


def _live_index_refresh(desk):
    """The refresh the real midnight run does on the live database, once per diary (tests pass their own or none)."""
    def go(diary_name, diary_root, notes):
        import store, store_diary
        with store._write() as c:
            return store_diary.refresh_index(c, diary_name, diary_root, notes)
    return go


def _diary_display(desk):
    """The default desk's diary is the main diary (setup/routing.json main_diary, '<name>-Diary'); any other desk is '<Desk>-Diary'."""
    try:
        with open(gc_settings.setup_path("routing.json"), encoding="utf-8") as f:
            r = json.load(f)
        if desk == r.get("main_desk") or (not r.get("main_desk") and desk == gc_settings.default_desk()):
            return r["main_diary"][:-len("-Diary")]
    except (OSError, KeyError, ValueError):
        pass
    return desk.capitalize()


if __name__ == "__main__":
    sys.exit(main())

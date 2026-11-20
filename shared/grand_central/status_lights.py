#!/usr/bin/env python3
"""status_lights.py: the Grand Central status lights, written ONLY through the plugin's one writer (emit_status.py).

One entry point for the scheduled jobs:   python3 status_lights.py --config setup/status_lights.json [--only mailroom,intake,morning,backup]
or from code:                             status_lights.run_lights(config, only=None, now=None, writer=None)

Generic: no personal paths here (they live in setup/status_lights.json). Each light is a pure function of what it
read, so it is testable without any file. Rules (vision 3.15 and the status canon):
  * status words are only OK / NEEDS_REVIEW / NEEDS_APPROVAL / DRIFT / ERROR. We never write "stale"; a reader derives it.
  * stale_after_s is about twice the producer's rhythm (mailroom 1200 s for a 600 s rhythm, the rest daily), so one late pass is not a false ERROR.
  * a light is never OK over zero work unless the summary says why zero is expected.
  * a missing or unreadable input is never green and never a crash.
  * a mailroom that is not signed in makes the entry point exit 75 (not a failure code) after writing the light.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import gc_settings  # noqa: E402
import local_first  # noqa: E402

MAILROOM_RHYTHM_S = 600
DAILY_S = 86400
HELD_LIMIT_S = 4 * 3600            # held unread past this -> ERROR (vision: "a few hours")
SIGNIN_WORDS = re.compile(r"auth|sign.?in|token|credential|login|invalid_grant|expired", re.I)


# ---------------------------------------------------------------- small helpers
def _utc_now():
    return dt.datetime.now(dt.timezone.utc)


def _parse_ts(v):
    """ISO string (Z or offset) or epoch number -> aware UTC datetime, else None."""
    try:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return dt.datetime.fromtimestamp(float(v), dt.timezone.utc)
        if isinstance(v, str) and v.strip():
            t = dt.datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
            return (t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)).astimezone(dt.timezone.utc)
    except (ValueError, OverflowError, OSError):
        pass
    return None


def _age_text(s):
    s = int(s)
    return "%dh%02dm" % (s // 3600, (s % 3600) // 60) if s >= 3600 else "%dm" % (s // 60)


def _load_json(path):
    """-> (obj, problem). Never raises."""
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as f:
            return json.load(f), None
    except FileNotFoundError:
        return None, "file not found"
    except PermissionError:
        return None, "not permitted to read"
    except (OSError, ValueError) as e:
        return None, "unreadable (%s)" % type(e).__name__


def _light(status, summary, payload=None, signed_out=False):
    return {"status": status, "summary": summary, "rc": 0 if status == "OK" else 1,
            "payload": payload or {}, "signed_out": signed_out}


# ---------------------------------------------------------------- the lights (pure)
def oldest_held_age_s(pass_obj, now):
    """Seconds the oldest held message has waited, or None if unknown. Uses held_oldest_age_s when the mailroom writes
    it; else the oldest timestamp found on the held records; else None. Never raises."""
    v = pass_obj.get("held_oldest_age_s")
    if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0:
        return float(v)
    held = pass_obj.get("held_messages")
    if isinstance(held, list):
        stamps = []
        for m in held:
            if isinstance(m, dict):
                for k in ("held_since", "first_held_at", "held_at", "received_at", "ts", "internal_date"):
                    t = _parse_ts(m.get(k))
                    if t:
                        stamps.append(t)
                        break
        if stamps and len(stamps) == len(held):
            return max(0.0, (now - min(stamps)).total_seconds())
    return None


def mailroom_light(pass_obj, problem, now, rhythm_s=MAILROOM_RHYTHM_S, held_limit_s=HELD_LIMIT_S):
    if pass_obj is None or not isinstance(pass_obj, dict):
        return _light("ERROR", "mailroom pass file %s; the mailroom may have stopped reading" % (problem or "is not an object"))
    written = _parse_ts(pass_obj.get("written_at"))
    if written is None:
        return _light("ERROR", "mailroom pass file has no readable written_at time; cannot tell if the mailroom is running")
    age = (now - written).total_seconds()
    tolerance = 2 * rhythm_s
    delivered, quar, lost = (pass_obj.get(k) for k in ("delivered", "quarantined", "lost"))
    ints = all(isinstance(x, int) and not isinstance(x, bool) for x in (delivered, quar, lost))
    held_n = pass_obj.get("held_after", pass_obj.get("held_messages_total"))
    if not ints or not isinstance(held_n, int) or isinstance(held_n, bool):
        return _light("ERROR", "mailroom pass file is missing its counts (delivered, quarantined, held, lost)")
    held_age = oldest_held_age_s(pass_obj, now)
    payload = {"pass_age_s": int(age), "delivered": delivered, "quarantined": quar, "held": held_n, "lost": lost,
               "oldest_held_age_s": None if held_age is None else int(held_age),
               "missing_labels": len(pass_obj.get("missing_labels") or []) + len(pass_obj.get("missing_exclude_labels") or [])}
    errs = []
    gerr, serr = pass_obj.get("gmail_error"), pass_obj.get("scanner_error")
    signed_out = bool(gerr and SIGNIN_WORDS.search(str(gerr)))
    if age > tolerance:
        errs.append("the pass file is %s old (rhythm %s): the mailroom has stopped" % (_age_text(age), _age_text(rhythm_s)))
    if pass_obj.get("started") is False:
        errs.append("the pass did not start")
    if gerr:
        errs.append("the mail service reported a problem" + (" (looks like sign-in)" if signed_out else ""))
    if serr:
        errs.append("the scanner reported a problem")
    if lost:
        errs.append("%d message(s) lost" % lost)
    if held_n and held_age is not None and held_age > held_limit_s:
        errs.append("mail held unread for %s (limit %s)" % (_age_text(held_age), _age_text(held_limit_s)))
    review = []
    if quar:
        review.append("%d quarantined" % quar)
    if payload["missing_labels"]:
        review.append("%d expected label(s) missing" % payload["missing_labels"])
    if held_n and held_age is None:
        review.append("%d held, how long unknown" % held_n)
    elif held_n:
        review.append("%d held, oldest %s" % (held_n, _age_text(held_age)))
    base = "pass %s ago: %d delivered, %d quarantined, %d held, %d lost" % (_age_text(max(age, 0)), delivered, quar, held_n, lost)
    if errs:
        return _light("ERROR", "; ".join(errs) + ". " + base, payload, signed_out)
    if review:
        return _light("NEEDS_REVIEW", base + "; " + "; ".join(review), payload)
    listed = (pass_obj.get("discover") or {}).get("threads_listed")
    if not (delivered or quar or held_n or lost):
        if isinstance(listed, int) and listed > 0:
            return _light("OK", base + "; nothing new (%d recent threads checked, all already seen)" % listed, payload)
        return _light("NEEDS_REVIEW", base + "; the pass looked at nothing, which is not expected", payload)
    return _light("OK", base, payload)


def intake_light(st, problem, now, rhythm_s=DAILY_S):
    if not isinstance(st, dict):
        return _light("ERROR", "front-room intake status %s; intake may never have run" % (problem or "is not an object"))
    ts = _parse_ts(st.get("ts"))
    if ts is None:
        return _light("ERROR", "front-room intake status has no readable time")
    age = (now - ts).total_seconds()
    reasons = [r for r in (st.get("reasons") or []) if isinstance(r, str)]
    refused = st.get("refused_at_ingest")
    payload = {"status_age_s": int(age), "refused_at_ingest": refused if isinstance(refused, int) else None,
               "ever_ingested": st.get("ever_ingested"), "reasons": reasons}
    if st.get("light") == "red" or reasons:
        return _light("ERROR", "intake refused something: %s (%s refused after delivery)" % (", ".join(reasons) or "see status", refused), payload)
    if st.get("light") != "green":
        return _light("ERROR", "front-room intake status has no light value", payload)
    if age > 2 * rhythm_s:
        return _light("ERROR", "intake status is %s old (rhythm %s): intake has stopped" % (_age_text(age), _age_text(rhythm_s)), payload)
    ever = st.get("ever_ingested")
    if not isinstance(ever, int) or ever <= 0:
        return _light("NEEDS_REVIEW", "intake is green but has never filed anything", payload)
    return _light("OK", "intake green: %d filed so far, none refused, last run %s ago" % (ever, _age_text(age)), payload)


_MORNING = re.compile(
    r"^morning read (?P<day>\d{4}-\d{2}-\d{2}) \((?P<desk>[^)]*)\): (?P<new>\d+) new of (?P<exam>\d+) examined; "
    r"used (?P<used>\d+), sorted out by triage (?P<sorted>\d+), skipped with a reason (?P<skip>\d+)")


def morning_light(proof, problem, now, rhythm_s=DAILY_S):
    """proof: the proof line (str) or the same as a JSON object with new per-source fields (tolerated, passed through)."""
    if proof is None:
        return _light("NEEDS_REVIEW", "no morning-read proof line yet (%s)" % (problem or "none written"))
    extra = {}
    if isinstance(proof, dict):
        extra = {k: v for k, v in proof.items() if k != "proof_line"}
        proof = proof.get("proof_line")
    line = str(proof or "").strip().splitlines()[-1] if str(proof or "").strip() else ""
    if "FAILED" in line and line.startswith("morning read"):
        return _light("ERROR", "morning read failed: " + line[:200])
    m = _MORNING.match(line)
    if not m:
        return _light("ERROR", "morning-read proof line is malformed; cannot prove what was examined")
    n = {k: int(m.group(k)) for k in ("new", "exam", "used", "sorted", "skip")}
    day = _parse_ts(m.group("day"))
    payload = {"day": m.group("day"), "new": n["new"], "examined": n["exam"], "used": n["used"],
               "sorted_by_triage": n["sorted"], "skipped_with_reason": n["skip"], "proof_line": line[:600]}
    for k, v in extra.items():
        payload.setdefault("src_" + str(k), v)       # new per-source fields ride along, never crash
    if "NOT ACCOUNTED" in line or "every new email accounted for" not in line:
        return _light("ERROR", "morning read did not account for every new email: " + line[:200], payload)
    if n["used"] + n["sorted"] + n["skip"] != n["new"]:
        return _light("ERROR", "morning-read counts do not add up (used+sorted+skipped != new)", payload)
    if day is not None and (now - day).total_seconds() > rhythm_s * 1.5 + DAILY_S:
        return _light("ERROR", "last morning read is for %s: the morning read has stopped" % m.group("day"), payload)
    if n["exam"] == 0:
        return _light("NEEDS_REVIEW", "morning read examined nothing (%s)" % m.group("day"), payload)
    tail = "nothing new" if n["new"] == 0 else "%d new, %d used, %d sorted out, %d skipped with a reason" % (n["new"], n["used"], n["sorted"], n["skip"])
    return _light("OK", "morning read %s: %d examined, %s, all accounted for" % (m.group("day"), n["exam"], tail), payload)


MORNING_FAIL_TRIES = 3 # the failed flag in the launch ledger (slice W item B)
MORNING_TRY_CEILING = 6 # the day's hard ceiling of tries, in-run ones included

def morning_ledger_light(ledger, has_draft, now=None, today=None):
    """The retry light on top of the morning light (slice W item B): ERROR "3 tries failed, retrying within the
    hour" when the launch ledger shows 3 consecutive failures today and no draft exists; ERROR "daily ceiling of
    6 tries reached" when the ceiling is hit. None when neither holds — the caller keeps its own verdict."""
    if not isinstance(ledger, dict):
        return None
    today = today or dt.datetime.now().date().isoformat()
    if ledger.get("day") != today or has_draft:
        return None
    payload = {"attempts": ledger.get("attempts"), "fail_streak": ledger.get("fail_streak")}
    if ledger.get("attempts", 0) >= MORNING_TRY_CEILING:
        return _light("ERROR", "daily ceiling of %d tries reached; the morning read has stopped trying until tomorrow"
            % MORNING_TRY_CEILING, payload)
    if ledger.get("fail_streak", 0) >= MORNING_FAIL_TRIES:
        return _light("ERROR", "3 tries failed, retrying within the hour", payload)
    return None

def _morning_draft_exists(cfg):
    """Is there a staged draft for today? Reached through the morning module's own finder (the same test the fast
    clock's launcher uses). Any problem counts as NO draft: the light may only get more worried, never greener."""
    try:
        import morning
        desk = cfg.get("morning_desk") or gc_settings.default_desk()
        rec = cfg.get("morning_records_dir") or morning.records_context_dir(morning.notes_root(), desk)
        day = dt.datetime.now().date().isoformat()
        return bool(morning.find_staged(rec, day, desk))
    except Exception: # noqa: BLE001
        return False

def _morning_with_ledger(cfg, now):
    """The morning light, with the retry overlay from the fast clock's launch ledger (slice W item B) when the
    config names it (morning_launch_ledger). No ledger configured -> the morning light alone, as before."""
    base = morning_light(*_read_proof(cfg["morning_proof"]), now)
    led_path = cfg.get("morning_launch_ledger")
    if not led_path:
        return base
    led, prob = _load_json(led_path)
    overlay = morning_ledger_light(led if isinstance(led, dict) else None, _morning_draft_exists(cfg), now=now)
    return overlay or base

# ---------------------------------------------------------------- the gc-gmail tile (slice W item E)
GMAIL_UNITS_PER_CALL = 5 # a list/read call costs about 5 quota units (Google's Gmail quota page)
GMAIL_WARN_UNITS = 25000 # half of a 50,000 unit/day budget; a warning, never a cap

def gmail_usage_light(calls_today, now=None):
    """The gc-gmail tile's verdict (slice W item E): a read-only rollup of today's runs rows — the sum of
    counts.gmail_calls, each call estimated at GMAIL_UNITS_PER_CALL units. WARN at GMAIL_WARN_UNITS; it never
    caps anything."""
    now = now or _utc_now()
    calls = calls_today if isinstance(calls_today, int) and not isinstance(calls_today, bool) else 0
    units = calls * GMAIL_UNITS_PER_CALL
    payload = {"gmail_calls": calls, "estimated_units": units, "warn_at_units": GMAIL_WARN_UNITS,
        "estimated": "calls x %d units" % GMAIL_UNITS_PER_CALL}
    base = "%d Gmail call(s) today, about %s units (calls x %d)" % (
        calls, format(units, ","), GMAIL_UNITS_PER_CALL)
    if units >= GMAIL_WARN_UNITS:
        return _light("NEEDS_REVIEW", "WARN: %s — at half of the 50,000 unit/day budget" % base, payload)
    return _light("OK", base, payload)

def _gmail_calls_today(db=None, now=None):
    """Sum of counts.gmail_calls over today's (local day) runs rows, read-only through the store's one read
    path; None when there is no readable database (the light is never green over a missing input)."""
    now = now or _utc_now()
    prev = None
    try:
        import store
        if db is not None:
            prev = store._path
            store.set_path(db)
        try:
            with store._read() as con:
                start = now.astimezone().replace(hour=0, minute=0, second=0, microsecond=0).astimezone(dt.timezone.utc)
                row = con.execute("SELECT COALESCE(SUM(CAST(json_extract(counts,'$.gmail_calls') AS INTEGER)),0) "
                    "FROM runs WHERE finished >= ?", (start.strftime("%Y-%m-%dT%H:%M:%SZ"),)).fetchone()
                return int(row[0] or 0)
        finally:
            if db is not None:
                store.set_path(prev)
    except Exception: # noqa: BLE001
        return None

def _gmail_light_safe(cfg, now=None):
    calls = _gmail_calls_today(cfg.get("gmail_runs_db"), now)
    if calls is None:
        return _light("NEEDS_REVIEW", "no runs database readable; Gmail usage cannot be counted")
    return gmail_usage_light(calls, now)

def _newest(dirpath, pattern):
    try:
        base = os.path.expanduser(dirpath)
        files = [os.path.join(base, f) for f in os.listdir(base) if re.fullmatch(pattern, f)]
        files = [f for f in files if os.path.isfile(f)]
        return max(files, key=os.path.getmtime) if files else None
    except OSError:
        return None


def _db_ok(path):
    """Integrity check of one database copy. engine/ never opens a database itself: the check is the root backup.py's
    own `integrity` (the module that already owns database access), reached through this one seam."""
    try:
        root = os.path.dirname(os.path.abspath(__file__))
        if root not in sys.path:
            sys.path.insert(0, root)
        import backup as _root_backup
        return _root_backup.integrity(path) == ["ok"]
    except Exception:
        return False


def backup_light(cfg, now, rhythm_s=DAILY_S, check_db=True, db_check=None):
    """cfg: {local_dir, snapshot_dir, archive_dir}. Newest local backup, snapshot and archive, each age-checked; the
    two database copies are integrity-checked read-only. The archive is checked for existence/size only (its passphrase
    round-trip is the backup tool's own `verify`)."""
    parts, errs, review, payload = [], [], [], {}
    for key, label, pat in (("local_dir", "local backup", r"rig-.*\.db"), ("snapshot_dir", "snapshot", r"rig-.*\.db"),
                            ("archive_dir", "archive", r"encrypted-.*\.dmg")):
        d = cfg.get(key)
        f = _newest(d, pat) if d else None
        if not f:
            (review if key == "archive_dir" else errs).append("no %s found" % label)
            payload[key.replace("_dir", "")] = None
            continue
        age = now.timestamp() - os.path.getmtime(f)
        size = os.path.getsize(f)
        ok = size > 0
        if ok and check_db and key != "archive_dir":
            chk = f
            if key == "snapshot_dir":      # the snapshot lives on Drive: check its local working copy (a scheduled job cannot fetch an offloaded file)
                try:
                    chk = local_first.local_file(f)
                except (local_first.DriveReadError, OSError) as e:
                    chk, ok = None, False
                    errs.append("newest snapshot unreadable: %s" % str(e)[:200])
            if chk is not None:
                ok = (db_check or _db_ok)(chk)
        payload[key.replace("_dir", "")] = {"age_s": int(age), "bytes": size, "verified": bool(ok)}
        if not ok:
            errs.append("newest %s failed its check" % label)
        elif age > 1.5 * rhythm_s:
            errs.append("newest %s is %s old" % (label, _age_text(age)))
        parts.append("%s %s old%s" % (label, _age_text(age), "" if key == "archive_dir" else ", integrity ok"))
    if errs:
        return _light("ERROR", "; ".join(errs + review), payload)
    if review:
        return _light("NEEDS_REVIEW", "; ".join(review) + " (" + "; ".join(parts) + ")", payload)
    return _light("OK", "backups current: " + "; ".join(parts), payload)


# ---------------------------------------------------------------- the model health light (phase 2 step 2.6)
MODEL_CHECK_EVERY_S = 20 * 3600


def model_light(res, now, rhythm_s=DAILY_S):
    """Green ONLY when the last `gc check` was clean and is recent. res: the check's result dict (model_check.py) or None.
    It gates nothing: it is a light."""
    if not isinstance(res, dict) or "clean" not in res:
        return _light("ERROR", "the model check has not run (no result)")
    at = _parse_ts(res.get("at"))
    if at is None:
        return _light("ERROR", "the model check result has no readable time", {"differences": res.get("differences")})
    age = now.timestamp() - at.timestamp()
    pl = {"differences": res.get("differences"), "age_s": int(age), "by_kind": res.get("by_kind")}
    if age > 1.5 * rhythm_s:
        return _light("ERROR", "the model check is %s old (it runs daily)" % _age_text(age), pl)
    if res.get("clean") is not True:
        bits = []
        if res.get("differences"):
            bits.append("%s difference(s) between the rebuilt and the live model" % res["differences"])
        if res.get("integrity_ok") is False:
            bits.append("database integrity check failed")
        if res.get("fk_problems"):
            bits.append("%s foreign-key problem(s)" % res["fk_problems"])
        return _light("ERROR", "model check not clean: " + ("; ".join(bits) or "see gc check"), pl)
    return _light("OK", "model check clean %s ago: rebuilt model equals the live model" % _age_text(age), pl)


def _model_result(cfg, now, dry_run=False):
    """The last check result; if it is older than the daily rhythm, run the check now (read-only toward the live db, work
    in a scratch copy) and record it. Reached through the root model_check seam: engine/ opens no database itself."""
    root = os.path.dirname(os.path.abspath(__file__))
    if root not in sys.path:
        sys.path.insert(0, root)
    import model_check
    rp = cfg.get("model_result")
    res = model_check.read_result(rp)
    at = _parse_ts(res.get("at")) if isinstance(res, dict) else None
    if (at is None or now.timestamp() - at.timestamp() > cfg.get("model_check_every_s", MODEL_CHECK_EVERY_S)) and not dry_run:
        import store
        res = model_check.check(cfg.get("db") or store.db_path())
        model_check.write_result(res, rp)
    return res


# ---------------------------------------------------------------- the dated lights (plan step 1.9; they gate nothing)
DATED = ("login", "mover", "mailkey", "sentinel")
FIX = "N/drafts/grand-central/bite/step-1a-reauth-walkthrough.md"


def _due(when, now):
    """when: ISO string; a date-only or no-zone time means the machine's local clock. -> (due, parsed or None)."""
    try:
        t = dt.datetime.fromisoformat(str(when))
    except ValueError:
        return True, None            # an unreadable date never hides a check
    if t.tzinfo is None:
        t = t.astimezone()           # local time
    return now >= t.astimezone(dt.timezone.utc), t


def _not_due(what, t):
    return _light("OK", "not due yet: %s is checked from %s on (nothing has been checked, on purpose)" % (what, t.strftime("%Y-%m-%d %H:%M") if t else "?"))


def login_light(cfg, now, check=None, state_path=None):
    """Front-room login still alive: the read-only getProfile preflight, at most once a day (the answer is kept in a small
    state file and re-used until it is a day old). check() -> (ok, why); default runs the real preflight through rig_env."""
    due, t = _due(cfg.get("login_from", "2026-11-18"), now)
    if not due:
        return _not_due("the front-room login", t)
    sp = os.path.expanduser(state_path or cfg.get("login_state") or os.path.join(gc_settings.data_root(), "state", "status-light-login.json"))
    last, _ = _load_json(sp)
    last = last if isinstance(last, dict) else {}
    at = _parse_ts(last.get("checked_at"))
    if at and 0 <= (now - at).total_seconds() < DAILY_S and "ok" in last:
        ok, why, ago = bool(last["ok"]), last.get("why", ""), "checked %s ago" % _age_text((now - at).total_seconds())
    else:
        ok, why = (check or _rig_preflight)()
        ago = "checked just now"
        try:
            os.makedirs(os.path.dirname(sp), exist_ok=True)
            with open(sp, "w", encoding="utf-8") as f:
                json.dump({"checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "ok": bool(ok), "why": why}, f)
        except OSError:
            pass                      # no state file just means a re-check next pass
    payload = {"checked_ago": ago, "ok": bool(ok)}
    if ok:
        return _light("OK", "front-room login alive (getProfile answered, %s)" % ago, payload)
    return _light("ERROR", "front-room login is not answering (%s, %s). One short sign-in sitting fixes it: %s" % (why or "no reason given", ago, FIX), payload)


def _rig_preflight():
    """The real read-only getProfile call, reached only through rig_env.py (the rig's own login). -> (ok, why)."""
    import subprocess
    root = os.path.dirname(os.path.abspath(__file__))
    code = ("import sys, rig_env; rig_env.apply_to_this_process(); sys.path.insert(0, rig_env.EMAIL_DOOR_DIR); "
            "import email_fetch; sys.exit(0 if email_fetch.preflight() else 3)")
    try:
        r = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, timeout=90)
    except (OSError, subprocess.SubprocessError) as e:
        return False, "could not run the check (%s)" % type(e).__name__
    return r.returncode == 0, "" if r.returncode == 0 else "getProfile did not answer, exit %d" % r.returncode


def mover_light(cfg, now, run=None):
    """Mover-timer verdict: runs `mac_edit.py verdict` (local files only) and reads its VERDICT lines. run() -> (rc, text)."""
    due, t = _due(cfg.get("mover_from", "2026-11-20T10:24:00"), now)
    if not due:
        return _not_due("the mover-timer verdict", t)
    if run is None:
        import subprocess
        cmd = cfg.get("mover_cmd") or []
        if not cmd:
            return _light("ERROR", "mover-timer check has no command configured (mover_cmd)")
        def run():
            r = subprocess.run([os.path.expanduser(c) for c in cmd], capture_output=True, text=True, timeout=60)
            return r.returncode, r.stdout + r.stderr
    try:
        rc, text = run()
    except Exception as e:
        return _light("ERROR", "mover-timer verdict could not be run (%s)" % type(e).__name__)
    verdicts = [v.strip() for v in re.findall(r"VERDICT:\s*(.+)", text)]
    payload = {"verdicts": verdicts}
    if rc != 0 or not verdicts:
        return _light("ERROR", "mover-timer verdict gave no answer (%s)" % (text.strip().splitlines() or ["no output"])[-1][:160], payload)
    bad = [v for v in verdicts if not v.upper().startswith(("PASS", "PENDING"))]
    if bad:
        return _light("ERROR", "mover-timer verdict failed: " + "; ".join(bad)[:200], payload)
    pend = [v for v in verdicts if v.upper().startswith("PENDING")]
    if pend:
        return _light("NEEDS_REVIEW", "mover-timer verdict not final yet: " + "; ".join(pend)[:200], payload)
    return _light("OK", "mover-timer verdict: " + "; ".join(verdicts)[:200], payload)


def mailkey_light(cfg, pass_obj, problem, now, rhythm_s=MAILROOM_RHYTHM_S):
    """Mailroom key still lists a message id. Read from the mailroom's pass file only; this light never logs in."""
    due, t = _due(cfg.get("mailkey_from", "2026-11-22"), now)
    if not due:
        return _not_due("the mailroom key", t)
    if not isinstance(pass_obj, dict):
        return _light("ERROR", "mailroom pass file %s; cannot tell whether the key still lists mail. Fix: %s" % (problem or "is not an object", FIX))
    written = _parse_ts(pass_obj.get("written_at"))
    if written is None:
        return _light("ERROR", "mailroom pass file has no readable written_at time; cannot tell whether the key still lists mail")
    age = (now - written).total_seconds()
    if age > 2 * rhythm_s:
        return _light("ERROR", "mailroom pass file is %s old (rhythm %s): the mailroom has stopped, so the key is unproven" % (_age_text(age), _age_text(rhythm_s)))
    gerr = pass_obj.get("gmail_error")
    if gerr:
        return _light("ERROR", "mailroom key reported a problem (%s). One short sign-in sitting fixes it: %s" % (str(gerr)[:120], FIX))
    listed = (pass_obj.get("discover") or {}).get("threads_listed")
    payload = {"pass_age_s": int(age), "threads_listed": listed}
    if isinstance(listed, int) and not isinstance(listed, bool) and listed > 0:
        return _light("OK", "mailroom key still lists mail: %d recent threads listed, no error, pass %s ago" % (listed, _age_text(max(age, 0))), payload)
    return _light("NEEDS_REVIEW", "mailroom pass had no error but listed no message ids, which is not expected; may be a quiet inbox or a key that lost its listing", payload)


SENTINEL_WARN = "refresh the mailroom's Sentinel copy at the next mailroom sitting"


def _git_show(repo, ref, path):
    import subprocess
    r = subprocess.run(["git", "-C", repo, "show", "%s:%s" % (ref, path)], capture_output=True, timeout=30)
    if r.returncode != 0:
        raise OSError("git show %s:%s failed" % (ref, path))
    return r.stdout


def sentinel_drift_light(cfg, now, state_path=None, read_branch=None):
    """Daily drift check: the mailroom's pinned Sentinel copy against the plugin branch's CURRENT Sentinel files (read only: file
    hashes here, `git show` there, no fetch). Drift is DRIFT (the amber word; the writer has no WARN) and never ERROR; it gates
    nothing. The 'part:' lines of the mailroom's manifest say which pinned file came from which plugin file.
    read_branch(plugin_path) -> bytes, for tests."""
    import hashlib
    sc = cfg.get("sentinel_drift") or {}
    pinned = os.path.expanduser(sc.get("pinned_dir") or gc_settings.mailroom_install_dir())
    repo = os.path.expanduser(sc.get("plugin_repo") or gc_settings.plugin_root())
    ref = sc.get("ref", "origin/V2")
    sp = os.path.expanduser(state_path or sc.get("state") or os.path.join(gc_settings.data_root(), "state", "status-light-sentinel.json"))
    last, _ = _load_json(sp)
    last = last if isinstance(last, dict) else {}
    at = _parse_ts(last.get("checked_at"))
    if at and 0 <= (now - at).total_seconds() < DAILY_S and last.get("light"):
        return last["light"]
    try:
        with open(os.path.join(pinned, sc.get("manifest", "step2.manifest")), encoding="utf-8") as f:
            parts = re.findall(r"^part:\s*(\S+)\s*<-\s*(\S+)", f.read(), re.M)
        if not parts:
            return _light("NEEDS_REVIEW", "sentinel drift check: the mailroom manifest lists no Sentinel parts")
        read_branch = read_branch or (lambda path: _git_show(repo, ref, path))
        changed = []
        for mine, theirs in parts:
            with open(os.path.join(pinned, mine), "rb") as f:
                a = hashlib.sha256(f.read()).hexdigest()
            if a != hashlib.sha256(read_branch(theirs)).hexdigest():
                changed.append(os.path.basename(mine))
    except Exception as e:             # an unreadable side is not drift and not an error: it never gates anything
        return _light("NEEDS_REVIEW", "sentinel drift check could not compare (%s)" % type(e).__name__)
    if changed:
        light = _light("DRIFT", "WARN: %d Sentinel file(s) differ from %s: %s. %s" % (len(changed), ref, ", ".join(changed), SENTINEL_WARN),
                       {"changed": changed})
    else:
        light = _light("OK", "the mailroom's Sentinel copy matches %s (%d files)" % (ref, len(parts)), {"changed": []})
    try:
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        with open(sp, "w", encoding="utf-8") as f:
            json.dump({"checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "light": light}, f)
    except OSError:
        pass
    return light


# ---------------------------------------------------------------- the writer and the entry point
def load_writer(code_root=None):
    """The plugin's one writer, found read-only via the code root. Never copied, never edited."""
    root = code_root or gc_settings.plugin_root()   # the plugin (one place decides: gc_settings.plugin_root)
    path = os.path.join(root, "system", "tools", "emit_status.py")
    spec = importlib.util.spec_from_file_location("emit_status", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.emit_status


ENVELOPE = ("desk", "schema_version", "pulse_job", "emit_mode", "stale_after_s", "last_run", "rc", "status", "summary")
WORD_MAP = {"WARN": "NEEDS_REVIEW"}      # the old hand-written word -> the nearest word the writer allows


def write_tile(path, tile, writer=None):
    """Write an already-built tile dict through the one writer (for gc-daily and mover-usage). Maps WARN to NEEDS_REVIEW."""
    t = dict(tile)
    t["status"] = WORD_MAP.get(t.get("status"), t.get("status"))
    env = {k: t[k] for k in ENVELOPE}
    return (writer or load_writer())(path, payload={k: v for k, v in t.items() if k not in ENVELOPE}, **env)


def _stale_s(cfg):
    """The tile's stale limit for the mailroom: about twice its rhythm (a false ERROR at 16:53 on 2026-11-16 came from 1x)."""
    return cfg.get("mailroom_stale_s", 2 * cfg.get("mailroom_rhythm_s", MAILROOM_RHYTHM_S))


def run_lights(cfg, only=None, now=None, writer=None, dry_run=False):
    """Compute and write the requested lights. -> {"lights": {name: light}, "written": [...], "exit": 0|1|75}.
    A light being ERROR is the light doing its job (exit 0). Exit 75 = mailroom not signed in; 1 = a write failed."""
    now = now or _utc_now()
    only = set(only or ("mailroom", "intake", "morning", "backup"))
    if "morning" in only and cfg.get("model_check"):
        only.add("model")            # the daily model check rides the daily morning call (phase 2 step 2.6); never gates it
    if "mailroom" in only and cfg.get("dated"):
        only |= set(DATED)           # the fast clock's existing call carries the dated checks too (step 1.9)
    out, written, failed = {}, [], False
    jobs = {
        "mailroom": ("gc-mailroom", "mailroom-pass", _stale_s(cfg),
                     lambda: mailroom_light(*_load_json(cfg["pass_file"]), now, cfg.get("mailroom_rhythm_s", MAILROOM_RHYTHM_S),
                                            cfg.get("held_limit_s", HELD_LIMIT_S))),
        "intake": ("gc-intake", "intake-status", cfg.get("intake_rhythm_s", DAILY_S),
                   lambda: intake_light(*_load_json(cfg["ingest_status"]), now, cfg.get("intake_rhythm_s", DAILY_S))),
        "morning": ("gc-morning", "morning-read", DAILY_S, lambda: _morning_with_ledger(cfg, now)),
        "backup": ("gc-backup", "backup", DAILY_S, lambda: backup_light(cfg["backup"], now)),
        "model": ("gc-model", "model-check", DAILY_S, lambda: model_light(_model_result(cfg, now, dry_run), now)),
        "login": ("gc-login", "login-alive", DAILY_S, lambda: login_light(cfg, now)),
        # tile is "gc-mover-verdict", not "gc-mover": mover_usage.py owns that tile
        "mover": ("gc-mover-verdict", "mover-verdict", MAILROOM_RHYTHM_S, lambda: mover_light(cfg, now)),
        "sentinel": ("gc-sentinel-copy", "sentinel-copy", DAILY_S, lambda: sentinel_drift_light(cfg, now)),
        "mailkey": ("gc-mailkey", "mailroom-key", _stale_s(cfg),
                    lambda: mailkey_light(cfg, *_load_json(cfg["pass_file"]), now, cfg.get("mailroom_rhythm_s", MAILROOM_RHYTHM_S))),
                            "gmail": ("gc-gmail", "gmail-usage", 2 * MAILROOM_RHYTHM_S, lambda: _gmail_light_safe(cfg, now)), # slice W item E
    }
    for name in jobs:
        if name not in only:
            continue
        tile, job, stale, fn = jobs[name]
        try:
            light = fn()
        except Exception as e:      # a light must never crash its caller
            light = _light("ERROR", "light could not be computed (%s)" % type(e).__name__)
        out[name] = light
        if dry_run:
            continue
        try:
            (writer or load_writer(cfg.get("code_root")))(
                os.path.join(os.path.expanduser(cfg["status_dir"]), tile + ".json"), desk=cfg.get("desk") or gc_settings.pulse_desk(),
                pulse_job=job, stale_after_s=stale, status=light["status"], rc=light["rc"], summary=light["summary"],
                payload=light["payload"])
            written.append(tile)
        except Exception as e:
            failed = True
            print("status_lights: could not write %s: %s" % (tile, e), file=sys.stderr)
    code = 1 if failed else (75 if any(l["signed_out"] for l in out.values()) else 0)
    return {"lights": out, "written": written, "exit": code}


def _read_proof(path):
    try:
        raw = open(os.path.expanduser(path), encoding="utf-8").read()
    except OSError as e:
        return None, "file %s" % ("not found" if isinstance(e, FileNotFoundError) else "unreadable")
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            return json.loads(raw), None
        except ValueError:
            return raw, None            # malformed JSON falls through to the line check, which fails it
    return raw, None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--dry-run", action="store_true", help="compute and print, write no tile")
    a = ap.parse_args(argv)
    cfg, prob = _load_json(a.config)
    if cfg is None:
        print("status_lights: cannot read config: %s" % prob, file=sys.stderr)
        return 1
    res = run_lights(cfg, only=[x for x in a.only.split(",") if x] or None, dry_run=a.dry_run)
    for n, l in res["lights"].items():
        print("%-8s %-13s %s" % (n, l["status"], l["summary"]))
    return res["exit"]


if __name__ == "__main__":
    sys.exit(main())

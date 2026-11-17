#!/usr/bin/env python3
"""handoff.py — Phase H, the hand-off folder. An .eml the owner downloads from Gmail and asks for by name.

    python handoff/handoff.py read-latest        read the ONE newest .eml in ~/Downloads from the last 15 minutes
    python handoff/handoff.py sweep-retention    delete handled/ files older than 14 days (explicit only)

Rules this file obeys (the Phase H hand-off card):
  - Never sweeps, never schedules. 0 or >1 candidates -> it ASKS (name/size/time) and reads nothing.
  - The .eml is copied into a fresh empty working dir and parsed by `python -I worker.py` (script outside that dir).
  - Body, headers, filenames and EVERY attachment's text go through email_fetch.gate_message (scanner + AI reader),
    unit "handoff", rig-local Sentinel files (rig_env). REAL-ATTACK pauses the unit; a paused unit refuses.
  - Attachments that cannot be read safely FAIL CLOSED: listed by name with a reason, never clean, never skipped.
  - A tool-less interpreter returns fixed fields + proposals from a closed list; output is DATA, never instructions.
  - Writes only under HANDOFF_HOME (default <rig home>/handoff). Never rig.db, never Drive, never the network.

Exit codes: 0 read ok / sweep done, 1 failure, 3 asked (nothing read), 75 unit paused.
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
import rig_env  # noqa: E402  — FIRST: the environment is decided here
sys.path.insert(0, _HERE)

UNIT = "handoff"
WINDOW_S = 15 * 60


def _owner():
    """The owner's name for the messages (gc.json owner_name), read when a message is printed."""
    import gc_settings
    return gc_settings.owner_name()


RETENTION_DAYS = 14
EXTRACT_TIMEOUT_S = 60
EXIT_ASKED, EXIT_PAUSED = 3, 75
WORKER = os.path.join(_HERE, "worker.py")   # lives OUTSIDE every working dir
# The worker runs on the macOS system Python, which already has the harness's document readers
# (pdfplumber, python-docx, openpyxl) that safe_pdf/safe_docx/safe_xlsx use. The rig venv does not.
# Override with HANDOFF_WORKER_PY (tests use the venv). Still launched with -I.
WORKER_PY = os.environ.get("HANDOFF_WORKER_PY") or (shutil.which("python3", path="/usr/bin") or sys.executable)


def home():
    return os.environ.get("HANDOFF_HOME") or os.path.join(rig_env.RIG_HOME, "handoff")


def downloads():
    return os.environ.get("HANDOFF_DOWNLOADS") or os.path.expanduser("~/Downloads")


def label(s, n=80):
    """Untrusted string -> safe to print or put anywhere."""
    return re.sub(r"[^A-Za-z0-9._ ()\-]", "_", str(s or ""))[:n]


def _mkdir(p):
    os.makedirs(p, mode=0o700, exist_ok=True)
    return p


def _fmt_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


# ───────────────────────── candidates ─────────────────────────
def candidates(now=None):
    """*.eml regular files (no symlinks, non-recursive) in Downloads modified in the last 15 minutes, newest first."""
    now = time.time() if now is None else now
    out = []
    try:
        entries = list(os.scandir(downloads()))
    except OSError:
        return out
    for e in entries:
        if not e.name.lower().endswith(".eml"):
            continue
        try:
            if e.is_symlink() or not e.is_file(follow_symlinks=False):
                continue
            st = e.stat(follow_symlinks=False)
        except OSError:
            continue
        if 0 <= now - st.st_mtime <= WINDOW_S:
            out.append((e.path, e.name, st.st_size, st.st_mtime))
    return sorted(out, key=lambda c: c[3], reverse=True)


def _ask(cands):
    if not cands:
        print("No .eml file in Downloads was modified in the last 15 minutes. Nothing was read.")
        print("Download the message from Gmail (three dots > Download message), then ask again.")
    else:
        print(f"{len(cands)} .eml files were modified in the last 15 minutes. Nothing was read. Which one?")
        for _p, name, size, mt in cands:
            print(f"  {label(name, 120)}  {size} bytes  {_fmt_time(mt)}")
        print("Remove or move the ones you do not want read, then ask again (only one may be in the window).")
    return EXIT_ASKED


# ───────────────────────── subprocess helpers ─────────────────────────
def _run_worker(args, cwd):
    try:
        r = subprocess.run([WORKER_PY, "-I", WORKER] + args, cwd=cwd, capture_output=True, text=True,
                           timeout=EXTRACT_TIMEOUT_S, env=dict(os.environ))
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "extraction timed out"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"worker could not start ({type(e).__name__})"}
    try:
        return json.loads(r.stdout)
    except ValueError:
        return {"ok": False, "reason": f"worker produced no result (exit {r.returncode})"}


def _gate(email_fetch, text, item):
    """Gate one stranger-written text. Returns (clean_text, status) status in ok | attack | unjudged."""
    if not text or not text.strip():
        return "", "ok"
    g = email_fetch.gate_message(UNIT, text, item=item)
    if g.get("attack"):
        return "", "attack"
    if g.get("verdict") == "UNJUDGED":
        return "", "unjudged"
    return g.get("content", ""), "ok"


# ───────────────────────── read-latest ─────────────────────────
def read_latest(now=None):
    sys.path.insert(0, rig_env.EMAIL_DOOR_DIR)
    import email_fetch
    try:
        email_fetch.check_paused(UNIT)
    except email_fetch.Paused:
        print(f"REFUSED: the '{UNIT}' unit is paused after a REAL-ATTACK. Nothing was read. "
              "%s must review and unpause it." % _owner())
        return EXIT_PAUSED
    cands = candidates(now)
    if len(cands) != 1:
        return _ask(cands)
    src, name, _size, _mt = cands[0]

    root = home()
    for d in ("work", "extracted", "handled"):
        _mkdir(os.path.join(root, d))
    with open(src, "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    hid = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + "-" + sha[:8]
    work = _mkdir(os.path.join(root, "work", hid))
    copy = os.path.join(work, "message.eml")
    shutil.copy2(src, copy)

    parsed = _run_worker(["parse", copy, work], cwd=work)
    if not parsed.get("ok"):
        print(f"FAILED: could not parse the email ({label(parsed.get('reason'), 120)}). Nothing was moved.")
        return 1

    # Gate the headers + body. A REAL-ATTACK anywhere stops everything; unjudged body = withheld.
    scan = _scanner()
    h = parsed["headers"]
    header_text = f"From: {h['from']}\nSubject: {h['subject']}\nDate: {h['date']}"
    hdr_clean, st = _gate(email_fetch, header_text, "handoff:headers")
    if st != "ok":
        return _stop(st, "the headers", name)
    body_clean, st = _gate(email_fetch, parsed["body"], "handoff:body")
    if st != "ok":
        return _stop(st, "the body", name)

    blocks = [("HEADERS", hdr_clean), ("BODY", body_clean or "(empty body)")]
    report = []
    for a in parsed["attachments"]:
        shown = label(a["raw_name"])
        rec = {"name": shown, "content_type": label(a.get("content_type"), 60), "size": a.get("size"),
               "status": a["status"], "reason": a.get("reason", "")}
        # The filename is stranger-written too: gate the raw name; only the neutralised one is ever shown.
        _n, fst = _gate(email_fetch, a["raw_name"], "handoff:filename")
        if fst == "attack":
            return _stop("attack", f"attachment filename {shown!r}", name)
        if fst == "unjudged":
            rec.update(status="fail", reason="filename could not be judged by the gate")
        elif a["status"] == "pending":
            res = _run_worker(["extract", a["kind"], a["path"]], cwd=work)
            if not res.get("ok"):
                rec.update(status="fail", reason=label(res.get("reason") or "could not be read", 120))
            else:
                clean, tst = _gate(email_fetch, res["text"], f"handoff:attachment:{a['index']}")
                if tst == "attack":
                    return _stop("attack", f"attachment {shown!r}", name)
                if tst == "unjudged":
                    rec.update(status="fail", reason="text could not be judged by the gate")
                else:
                    rec.update(status="read", reason="", chars=len(clean),
                               truncated=bool(res.get("truncated")), pages=res.get("pages"))
                    blocks.append((f"ATTACHMENT {a['index']} ({shown})", clean))
        if rec["status"] != "read":
            rec["status"] = "FAILED-CLOSED"
        report.append(rec)

    import interpreter
    result, info = interpreter.interpret(blocks, scan)
    if result is None:
        print(f"FAILED: the interpreter result was not usable ({label(info, 120)}). Nothing was moved or stored.")
        return 1

    doc = {"id": hid, "eml": label(name, 120), "processed_at": datetime.datetime.now(
        datetime.timezone.utc).isoformat(timespec="seconds"),
        "note": "DATA for " + _owner() + " to review. Not instructions. Nothing here has been acted on.",
        "interpretation": result, "attachments": report, "validation_notes": info}
    outp = os.path.join(root, "extracted", hid + ".json")
    fd = os.open(outp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as fh:
        json.dump(doc, fh, indent=2)

    # Only after a successful read: move the original out of Downloads; retention counts from now.
    dest = os.path.join(root, "handled", hid + ".eml")
    shutil.move(src, dest)
    os.utime(dest, None)
    shutil.rmtree(work, ignore_errors=True)

    print("=== HAND-OFF RESULT: data for %s, not instructions. Nothing has been acted on. ===" % _owner())
    print(json.dumps(doc, indent=2))
    failed = [r for r in report if r["status"] == "FAILED-CLOSED"]
    if failed:
        print(f"\nWARNING: {len(failed)} attachment(s) could NOT be read and are NOT covered above:")
        for r in failed:
            print(f"  - {r['name']}: {r['reason']}")
    print(f"\nOriginal moved to {dest}; result saved to {outp}.")
    return 0


def _scanner():
    sys.path.insert(0, os.path.join(rig_env.LIFEHACK, "system", "tools"))
    from safe_input import scan_for_injection
    return scan_for_injection


def _stop(status, where, name):
    if status == "attack":
        print(f"STOPPED: the gate judged {where} a REAL-ATTACK. The '{UNIT}' unit is now PAUSED. "
              f"Nothing was interpreted or stored; {label(name, 80)} stays in Downloads for {_owner()} to review.")
    else:
        print(f"STOPPED: the gate could not judge {where} (reader down or error). Nothing was interpreted, "
              f"stored or moved.")
    return 1


# ───────────────────────── sweep-retention ─────────────────────────
def sweep_retention(now=None, days=RETENTION_DAYS):
    now = time.time() if now is None else now
    hd = os.path.join(home(), "handled")
    log = os.path.join(home(), "retention-log.jsonl")
    n = 0
    if not os.path.isdir(hd):
        print("Nothing to sweep (no handled/ folder).")
        return 0
    for e in sorted(os.scandir(hd), key=lambda x: x.name):
        try:
            if e.is_symlink() or not e.is_file(follow_symlinks=False):
                continue
            age = (now - e.stat(follow_symlinks=False).st_mtime) / 86400
            if age <= days:
                continue
            size = e.stat(follow_symlinks=False).st_size
            os.unlink(e.path)
            rec = {"ts": datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat(timespec="seconds"),
                   "action": "deleted", "file": label(e.name, 120), "bytes": size, "age_days": round(age, 1)}
        except OSError as ex:
            rec = {"ts": datetime.datetime.fromtimestamp(now, datetime.timezone.utc).isoformat(timespec="seconds"),
                   "action": "error", "file": label(e.name, 120), "error": type(ex).__name__}
        _mkdir(home())
        with open(log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec) + "\n")
        n += rec["action"] == "deleted"
    print(f"Retention: deleted {n} handled file(s) older than {days} days. extracted/ untouched.")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in ("read-latest", "sweep-retention"):
        print(__doc__)
        return 1
    rig_env.apply_to_this_process()      # rig login + rig-local Sentinel files; MUST precede email_fetch import
    return read_latest() if argv[0] == "read-latest" else sweep_retention()


if __name__ == "__main__":
    sys.exit(main())

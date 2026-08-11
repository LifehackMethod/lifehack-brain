#!/usr/bin/env python3
"""sentinel_response.py — the verdict half of the gate: what happens when a scan finds something.

THE SPLIT, AND WHY IT IS A SPLIT. `ingest_gate.py` cleans the text and looks for the patterns. It
does not decide what they mean. This file does exactly one thing: it takes the findings and answers
a single question — is this an actual attempt to take control of the session, or is it noise? — and
then it acts on that answer once, in one place. Two verdicts, and they are not the same kind of
event:

  FLAG    something matched, and it is very probably nothing. A base64 blob. A tracking URL. An
          article that happens to use the phrase "ignore the above". It is written to the log, the
          status file is refreshed, and NOTHING ELSE HAPPENS. No interruption, no alert.
          exit 0 — the caller carries on with the item.

  DANGER  the narrow class that is an attempt on the session itself: instruction override,
          somebody claiming an authority they do not have, a directive to send data somewhere.
          Logged, the source is PAUSED, and a notification fires if one is configured.
          exit 2 — the caller SKIPS this item and keeps running.

WHY THE LINE IS DRAWN THERE AND NOT WIDER. Every extra thing you call DANGER costs you a
notification that turns out to be nothing, and the third of those teaches you to ignore the fourth.
A wall you have learned to walk past is not a wall. So the DANGER set is deliberately small and the
FLAG set is deliberately silent-but-recorded: you can go and look at the flags whenever you want,
and you will only be interrupted for the kind of thing that would actually matter.

TWO RULES THAT ARE NOT NEGOTIABLE. It never halts the whole run — one bad item is skipped, the rest
continue. And it never un-pauses anything: a paused source stays paused until a person clears it.
Automatic recovery from a security stop is a way of having no security stop.

  stdin  : findings JSON — a list of [match, label] pairs (what scan_for_injection returns), or
           {"findings": [...]}.
  args   : --source <who was reading> --item <what it was> [--flag-only] [--reader-verdict V]
  stdout : one line of verdict text.
  exit   : 0 = FLAG or CLEAN (continue) · 2 = DANGER (skip this item)
"""
import sys, os, json, time, argparse, subprocess, base64, hashlib

# WHERE THE RECORD LIVES. Under the notes root the person chose, resolved through the one resolver
# — never a hardcoded cloud path, and never guessed. With no root set the log falls back to a local
# cache directory, so a scan on a fresh install still records rather than silently dropping the
# event on the floor.
CODE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(CODE_ROOT, "shared"))
try:
    from brain_root import resolve_brain_root           # shared/brain_root.py
    _SRC, _ROOT = resolve_brain_root()
except Exception:
    _ROOT = None
DATA = _ROOT or os.path.expanduser("~/.cache/lifehack-sentinel")

# All three are env-overridable so a test can point them at a temp directory. Production uses these.
LOG = os.environ.get("SENTINEL_LOG", f"{DATA}/system/logs/sentinel-events.jsonl")
STATUS = os.environ.get("SENTINEL_STATUS", f"{DATA}/state/status/sentinel.json")
# Machine-local by design: a pause is about THIS machine's run, and syncing it to another machine
# would pause a session nobody there has looked at. Same config home as the notes-root pointer.
PAUSE_FILE = os.environ.get("SENTINEL_PAUSE_FILE",
                            os.path.expanduser("~/.config/lifehack/sentinel-paused-sources"))
# The push notifier. Lands with the notify tooling; until then the check below simply skips the
# push and says so — a missing notifier must never turn into a missing BLOCK.
NOTIFY = f"{CODE_ROOT}/shared/notify/notify-send.sh"
# CONTAINMENT HOOK, DELIBERATELY EMPTY IN THIS REPOSITORY. In the system this came from, a DANGER
# verdict on an email also applied a quarantine label to that message — reversible, never a delete.
# That is mailbox-specific plumbing and it is not part of what ships here. The argument is still
# accepted and the path is still checked, so an installation that adds its own labeller at this
# path gets containment for free; with nothing there, the log + pause + notification stand on their
# own. Named rather than removed, so the absence is visible instead of looking like an oversight.
QUARANTINE = os.environ.get("SENTINEL_QUARANTINE_TOOL", "")

# The DANGER labels. These must match the labels scan_for_injection emits (system/tools/safe_input.py).
# Everything the scanner can produce that is NOT in this set is a FLAG.
DANGER_LABELS = {
    # somebody trying to replace the instructions
    "instruction override", "system prompt override", "system prompt injection",
    "instruction replacement", "constraint bypass", "behavioral redirect",
    "goal reassignment", "memory wipe attempt",
    # somebody claiming to be someone they are not
    "false authority claim", "authority impersonation", "false authorization claim",
    # trying to get data out
    "bypass attempt",
    # NOT HERE, ON PURPOSE: "system prompt extraction" and "prompt leakage attempt". Their patterns
    # match ordinary prose — "output the system prompt", "give instructions", "translate the above"
    # — so as DANGER they were almost pure false positive, and a notification that is almost always
    # nothing is worse than none. They are READ probes, not attempts to take the wheel. They still
    # log and still show up; they just do not interrupt. Move either string back into this set to
    # restore the alert.
    #
    # "decode this base64 and then follow it" IS an attack — the encoding is the delivery, not the
    # point. Plain base64 with no instruction attached stays a FLAG (that is the noisy class).
    "encoding attack directive",
}

# Findings you have already looked at and accepted. Written by hand or by a small ack tool; read
# here so a recurring harmless pattern stops re-raising itself. Only ever silences NON-danger.
ACKED_FP = os.environ.get("SENTINEL_ACKED_FP", f"{DATA}/system/logs/sentinel-acked-fingerprints.json")


def fingerprint_for(source, labels):
    """A stable id for "this kind of finding, from this source" = sha256(source | sorted labels)[:12].

    It deliberately EXCLUDES the item — the subject line, the filename, the URL — so that the same
    harmless pattern arriving weekly maps to ONE fingerprint you can accept once, instead of a new
    one every time. A genuinely different attack has a different label set and therefore a
    different fingerprint, so accepting one thing never quietly accepts another. And a DANGER is
    never auto-silenced by an accepted fingerprint, whatever it matches."""
    key = f"{source}|" + ",".join(sorted({l for l in labels if l}))
    return hashlib.sha256(key.encode("utf-8", "replace")).hexdigest()[:12]


def load_acked_fingerprints():
    """The accepted set. Any read problem returns empty — err toward SHOWING a finding, never
    toward hiding one. A file you cannot read must not be able to silence an alarm."""
    try:
        with open(ACKED_FP) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def iso(epoch):
    lt = time.localtime(epoch); off = time.strftime("%z", lt)
    off = (off[:3] + ":" + off[3:]) if off else "+00:00"
    return time.strftime("%Y-%m-%dT%H:%M:%S", lt) + off


def _ep(ts):
    try:
        return time.mktime(time.strptime(str(ts)[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0.0


def _defang(s, n=180):
    """Store the matched text as INERT evidence.

    The snippet is a live injection attempt. Writing it into the log in plain text would turn the
    evidence file into a second delivery vehicle: the next session that reads the log to see what
    happened would be reading the attack. So it is stripped to printable ASCII (which drops the
    zero-width and direction-override characters), collapsed, truncated, and then base64-encoded.
    Looking at it is a deliberate act — `echo <b64> | base64 -d` — and not something that happens
    to a session by accident."""
    s = "".join(ch for ch in (s or "") if 32 <= ord(ch) < 127)
    s = " ".join(s.split())
    s = (s[:n] + "...(truncated)") if len(s) > n else s
    return base64.b64encode(s.encode("utf-8", "replace")).decode()


def parse_findings(raw):
    """Accept a list of [match, label], or {'findings': [...]}. Junk in returns an empty list —
    which reads as CLEAN, and that is correct: this tool reports on findings it was given, and
    "I was handed nothing I could parse" is not a finding."""
    try:
        data = json.loads(raw) if raw.strip() else []
    except Exception:
        return []
    if isinstance(data, dict):
        data = data.get("findings", [])
    out = []
    for f in data or []:
        if isinstance(f, (list, tuple)) and len(f) >= 2:
            out.append((str(f[0]), str(f[1])))
        elif isinstance(f, dict):
            out.append((str(f.get("match", "")), str(f.get("label", ""))))
    return out


def write_status():
    """Rebuild the one-glance status file from the log.

    It answers "is anything waiting for me?" without reading a JSONL by eye. ACTIVE means
    unreviewed: once you have looked at an event and marked it, it stays in the history and the
    24-hour totals but stops driving the status — otherwise the file is red forever and stops
    meaning anything. Nothing in this repository reads this file yet; it is written for a person
    with `cat`, and for whatever gets built on top of it later."""
    now = time.time(); events = []
    if os.path.exists(LOG):
        with open(LOG) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except Exception:
                    continue
    events.sort(key=lambda e: _ep(e.get("ts")))
    recent24 = [e for e in events if _ep(e.get("ts")) >= now - 86400]
    ev24 = len(recent24)
    danger24 = sum(1 for e in recent24 if e.get("verdict") == "danger")
    active = [e for e in recent24 if e.get("disposition", "unreviewed") == "unreviewed"]
    active_ev = len(active)
    active_danger = sum(1 for e in active if e.get("verdict") == "danger")
    reviewed24 = ev24 - active_ev
    last = events[-1].get("ts") if events else None
    recent = [{"ts": e.get("ts"), "source": e.get("source"), "verdict": e.get("verdict"),
               "item": (e.get("item") or "")[:120], "detail": (e.get("detail") or "")[:200],
               "evidence": e.get("evidence", []), "disposition": e.get("disposition", "unreviewed")}
              for e in events[-10:]][::-1]
    # A flag does NOT colour this hot. Flags live in the count and the log; the status goes to
    # DANGER only for the narrow class that earns an interruption. Same reasoning as the label set.
    status = "DANGER" if active_danger else "CLEAR"
    summary = (f"{active_danger} active DANGER · {active_ev} unreviewed · {reviewed24} reviewed (24h)" if active_danger
               else (f"{active_ev} unreviewed flag(s) · {reviewed24} reviewed (24h)" if active_ev
                     else (f"all clear — {reviewed24} reviewed, 0 active (24h)" if ev24 else "No security events (24h)")))
    out = {"schema_version": 1, "last_run": iso(now), "rc": 0,
           "status": status, "summary": summary, "last_event_at": last,
           "event_count_24h": ev24, "danger_count_24h": danger24,
           "active_count_24h": active_ev, "active_danger_24h": active_danger,
           "reviewed_count_24h": reviewed24, "recent_events": recent}
    os.makedirs(os.path.dirname(STATUS), exist_ok=True)
    tmp = STATUS + ".tmp"
    json.dump(out, open(tmp, "w"), indent=2); os.replace(tmp, STATUS)


def log_event(source, item, verdict, detail, evidence=None, provenance="", fp="", disposition="unreviewed"):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    rec = {"ts": iso(time.time()), "source": source, "item": (item or "")[:120],
           "verdict": verdict, "detail": (detail or "")[:300],
           "evidence": evidence or [],      # [{label, snippet_b64}] — WHAT tripped it, defanged
           "disposition": disposition}      # unreviewed | false-positive | real | reviewed
    if provenance:                          # {source}/{type}/{sha256_8} from the gate — what was screened
        rec["provenance_tag"] = provenance
    if fp:
        rec["fingerprint"] = fp
    with open(LOG, "a") as f:
        f.write(json.dumps(rec) + "\n")


def pause_source(source):
    """Add the source to the pause list. The list is checked before a run.

    UN-PAUSING IS A PERSON'S JOB. This tool has no code path that removes a line from this file,
    and that is the point: a security stop that clears itself after a while is a security stop you
    do not have."""
    try:
        os.makedirs(os.path.dirname(PAUSE_FILE), exist_ok=True)
        existing = set()
        if os.path.exists(PAUSE_FILE):
            existing = {l.strip() for l in open(PAUSE_FILE) if l.strip()}
        if source not in existing:
            with open(PAUSE_FILE, "a") as f:
                f.write(source + "\n")
    except Exception as e:
        sys.stderr.write(f"[sentinel] pause-marker write failed: {e}\n")


def notify_danger(source, labels, reader_verdict=None):
    """Send one notification. A teaser only — never the content, because whatever reads the
    notification is one more thing the content could talk to.

    THE ONE THING THAT SILENCES IT: if the tool-less reader has actually looked at the text and
    come back BENIGN, the scanner's match was a false positive and there is nothing to say. Any
    other outcome rings — including the reader not having run at all. Silence requires a positive
    all-clear; doubt always rings."""
    if reader_verdict == "BENIGN":
        sys.stderr.write(
            f"[sentinel] notification suppressed — the reader confirmed BENIGN for {source}; "
            "the pause still stands.\n")
        return
    if os.environ.get("SENTINEL_NOTIFY_DISABLE") == "1":
        sys.stderr.write("[sentinel] notifications disabled (test) — skipping push\n"); return
    if not os.path.exists(NOTIFY):
        sys.stderr.write("[sentinel] no notifier installed — skipping push (the log and the pause stand)\n"); return
    teaser = (f"DANGER in {source}: {', '.join(sorted(set(labels))[:3])}. That source is PAUSED. "
              f"What tripped it is in the event log. Review it, then un-pause by hand.")
    try:
        subprocess.run(["bash", NOTIFY, "--source", "sentinel", "--priority", "critical",
                        "--title", "Security: DANGER (source paused)", "--message", teaser,
                        "--tags", "rotating_light,lock"],
                       timeout=20, capture_output=True)
    except Exception as e:
        sys.stderr.write(f"[sentinel] notification failed: {e}\n")


def quarantine_message(message_id):
    """Hand the item to a containment tool, if this installation has one. See QUARANTINE above:
    nothing ships at that path here, so this is normally a documented no-op. Fail-open on purpose —
    the log, the pause and the skip are the floor; containment is the extra."""
    if os.environ.get("SENTINEL_QUARANTINE_DISABLE") == "1":
        sys.stderr.write("[sentinel] containment disabled (test) — skipping\n"); return
    if not message_id or not QUARANTINE:
        return
    if not os.path.exists(QUARANTINE):
        sys.stderr.write(f"[sentinel] no containment tool at {QUARANTINE} — skipping\n"); return
    try:
        subprocess.run(["python3", QUARANTINE, "--message-id", message_id],
                       timeout=30, capture_output=True)
    except Exception as e:
        sys.stderr.write(f"[sentinel] containment failed: {e}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--item", default="")
    ap.add_argument("--message-id", default="")   # passed to the containment tool, if one exists
    ap.add_argument("--provenance", default="")   # {source}/{type}/{sha256_8} from the gate
    ap.add_argument("--flag-only", action="store_true",
                    help="cap the verdict at FLAG — no DANGER, no pause, no notification, never exit 2")
    ap.add_argument("--reader-verdict", default=None,
                    help="the tool-less reader's verdict (REAL-ATTACK | BENIGN | NONE); only BENIGN "
                         "suppresses the notification, and only that")
    args = ap.parse_args()

    findings = parse_findings(sys.stdin.read())
    labels = [lab for _, lab in findings if lab]

    if not findings:
        print("CLEAN")
        return 0

    fp = fingerprint_for(args.source, labels)
    danger_hits = sorted({lab for lab in labels if lab in DANGER_LABELS})
    if danger_hits and not args.flag_only:
        detail = "DANGER: " + ", ".join(danger_hits)
        evidence = [{"label": lab, "snippet_b64": _defang(m)} for m, lab in findings if lab in DANGER_LABELS]
        # A DANGER is never auto-silenced by an accepted fingerprint. It always lands unreviewed.
        log_event(args.source, args.item, "danger", detail, evidence,
                  provenance=args.provenance, fp=fp, disposition="unreviewed")
        write_status()
        pause_source(args.source)
        notify_danger(args.source, danger_hits, reader_verdict=args.reader_verdict)
        quarantine_message(args.message_id)
        print(detail)
        return 2

    # FLAG — including a DANGER that --flag-only capped. When that happens, record WHICH labels
    # were capped, so the log never quietly reads as though nothing serious matched.
    capped = (" [flag-only: capped " + ", ".join(danger_hits) + "]") if (danger_hits and args.flag_only) else ""
    acked = load_acked_fingerprints().get(fp)
    disposition = (acked.get("disposition") or "false-positive") if isinstance(acked, dict) else "unreviewed"
    auto = "  [auto-accepted: known fingerprint]" if disposition != "unreviewed" else ""
    detail = "FLAG: " + ", ".join(sorted(set(labels))[:5]) + capped + auto
    evidence = [{"label": lab, "snippet_b64": _defang(m)} for m, lab in findings if lab]
    log_event(args.source, args.item, "flag", detail, evidence,
              provenance=args.provenance, fp=fp, disposition=disposition)
    write_status()
    print(detail)
    return 0


if __name__ == "__main__":
    sys.exit(main())

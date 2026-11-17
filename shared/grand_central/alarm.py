#!/usr/bin/env python3
"""alarm.py: the alarm's path (Grand Central V2, plan B2 step 5). Front room; the one AI call here has NO tools.

  trigger -> only scanned mail -> that ONE thread read by a tool-less reader -> a short write-up -> a status light
  -> a phone notification.

  1. Trigger. Rules come from a settings file (his later decision; his rules replace the first one). The first rule is
     one simple trigger: urgency level from scorecard.py importance_urgency() at or above "high".
  2. Only scanned mail. A message whose verdict is not "clean" is never read. Verdict "flagged" (or "quarantined")
     raises a "quarantined" alert instead. No verdict at all (held unread, not yet scanned) does nothing: it is retried.
  3. The read. The thread text comes from `fetch_text` (the front room's one access point to email text,
     transcripts.py when it exists) and goes to a reader that declares has_tools = False. The reader is an
     interface (read(thread_text) -> str); tests pass a fake, this module never calls a model itself.
  4. The write-up is short, untrusted prose: it goes to a local file (writeup_dir), never into the phone message
     or the tile. Windows with tools read it, never obey it.
  5. The status light goes through the ONE tile writer (system/tools/emit_status.py, loaded from where it lives, never
     copied) with stale_after_s set. EVERY run stamps the tile, alarm or not, so a missed run shows as stale.
     Desks never write STALE; the reader derives it (canon/desk-building-sop.md L207): see tile_freshness().
  6. The phone notification goes through the governed script (shared/notify/notify-send.sh via ShellNotifier). The
     message is a teaser only: no names, no amounts, nothing from the email. A notifier is always passed in.

The tile path is REQUIRED (no default): nothing here can write into a live status folder by accident.
Usage as a library: alarm.run(candidates, cfg=..., settings=..., fetch_text=..., reader=..., notifier=..., tile_path=...)
candidate = {message_id, thread_id, verdict, obs, standing?, automated?}   (obs = the triage observations)
"""
import importlib.util
import json
import os
import subprocess
import time

import scorecard
import gc_settings

# the plugin's one tile writer and governed notify script, in the plugin this code runs from (env overrides for tests)
EMIT_STATUS_PATH = os.environ.get("ALARM_EMIT_STATUS") or os.path.join(gc_settings.plugin_root(), "system", "tools", "emit_status.py")
NOTIFY_SEND_PATH = os.environ.get("ALARM_NOTIFY_SEND") or os.path.join(gc_settings.plugin_root(), "shared", "notify", "notify-send.sh")
SOURCE = "grand-central-alarm"
LEVEL_RANK = {"low": 0, "medium": 1, "high": 2}
QUARANTINE_VERDICTS = {"flagged", "quarantined"}
TEASER_URGENT = "Urgent mail needs you. Open Claude and say: what is urgent?"
TEASER_QUARANTINED = "An urgent-looking email was quarantined and not read. Open Claude and say: what was quarantined?"
TEASER_READ_FAILED = "Urgent mail needs you (the write-up failed). Open Claude and say: what is urgent?"


class AlarmError(Exception):
    pass


# ---- settings and triggers -------------------------------------------------------------------------------------
def _trig_urgency_level(trig, ctx):
    return LEVEL_RANK[ctx["iu"]["urgency"]] >= LEVEL_RANK[trig.get("min", "high")]


TRIGGER_KINDS = {"urgency_level": _trig_urgency_level}   # add a kind here to let his rules (sender, subject...) in


class Settings:
    def __init__(self, triggers, stale_after_s, pulse_job, writeup_max_chars):
        self.triggers, self.stale_after_s, self.pulse_job, self.writeup_max_chars = triggers, stale_after_s, pulse_job, writeup_max_chars

    @classmethod
    def load(cls, path):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError) as e:
            raise AlarmError("alarm settings unreadable (%s): %s" % (path, e))
        trigs = d.get("triggers")
        if not isinstance(trigs, list):
            raise AlarmError("alarm settings: 'triggers' must be a list")
        for t in trigs:
            if t.get("kind") not in TRIGGER_KINDS:
                raise AlarmError("alarm settings: unknown trigger kind %r (known: %s)" % (t.get("kind"), sorted(TRIGGER_KINDS)))
            if t["kind"] == "urgency_level" and t.get("min", "high") not in LEVEL_RANK:
                raise AlarmError("alarm settings: bad urgency level %r" % t.get("min"))
        sa = d.get("stale_after_s")
        if not isinstance(sa, int) or sa <= 0:
            raise AlarmError("alarm settings: 'stale_after_s' must be a positive integer")
        if not d.get("pulse_job"):
            raise AlarmError("alarm settings: 'pulse_job' is missing (the job whose pulse the alarm watches)")
        return cls(trigs, sa, d["pulse_job"], int(d.get("writeup_max_chars", 600)))

    def matching(self, ctx):
        return [t.get("id", t["kind"]) for t in self.triggers if TRIGGER_KINDS[t["kind"]](t, ctx)]


# ---- the outside tools: the one tile writer and the governed notify script, both called, never copied ---------
def _load_emit_status():
    if not os.path.exists(EMIT_STATUS_PATH):
        raise AlarmError("the tile writer is missing: %s" % EMIT_STATUS_PATH)
    spec = importlib.util.spec_from_file_location("emit_status_one_writer", EMIT_STATUS_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.emit_status


class ShellNotifier:
    """Calls the governed notify script. It owns the governor (quiet hours, daily cap, dedup) and the topic. Tests inject a
    fake notifier instead; ShellNotifier's own test injects a fake runner and runs nothing."""

    def __init__(self, script=None, runner=subprocess.run):
        self.script, self.runner = script or NOTIFY_SEND_PATH, runner

    def send(self, *, source, message, priority, identity, title):
        argv = ["bash", self.script, "--source", source, "--message", message, "--priority", priority,
                "--identity", identity, "--title", title]
        r = self.runner(argv, capture_output=True, text=True, timeout=30)
        return r.returncode == 0


# ---- staleness (the reader's derivation, applied to the tile) ----------------------------------------------------
def tile_freshness(tile_path, now=None):
    """'fresh' | 'stale' | 'missing'. Stale = now is more than stale_after_s past last_run (canon/desk-building-sop.md L207)."""
    try:
        with open(tile_path, encoding="utf-8") as f:
            t = json.load(f)
        ran = time.mktime(time.strptime(t["last_run"][:19], "%Y-%m-%dT%H:%M:%S"))
        limit = int(t["stale_after_s"])
    except (OSError, ValueError, KeyError):
        return "missing"
    return "stale" if (now if now is not None else time.time()) - ran > limit else "fresh"


# ---- the run ----------------------------------------------------------------------------------------------------
def _load_state(path):
    if not path or not os.path.exists(path):
        return set()
    try:
        with open(path, encoding="utf-8") as f:
            return set(json.load(f))
    except (OSError, ValueError):
        return set()


def _save_state(path, handled):
    if path:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(sorted(handled), f)
        os.replace(path + ".tmp", path)


def _clean_writeup(text, cap):
    text = " ".join(str(text or "").split())
    return text if len(text) <= cap else text[:cap].rstrip() + " ..."


def run(candidates, *, cfg, settings, fetch_text, reader, notifier, tile_path, writeup_dir=None, state_path=None, emit=None):
    if not tile_path:
        raise AlarmError("tile_path is required (no default: the alarm never picks a live status folder by itself)")
    if getattr(reader, "has_tools", True) is not False:
        raise AlarmError("the alarm read must be a tool-less reader (has_tools must be False): refused")
    emit = emit or _load_emit_status()
    handled = _load_state(state_path)
    outcomes, notify_failed = [], False

    def alert(message, priority, identity):
        nonlocal notify_failed
        if not notifier.send(source=SOURCE, message=message, priority=priority, identity=identity, title="Grand Central"):
            notify_failed = True

    for c in candidates:
        mid, tid = c["message_id"], c["thread_id"]
        rec = {"message_id": mid, "thread_id": tid}
        outcomes.append(rec)
        if mid in handled:
            rec["outcome"] = "already_handled"
            continue
        iu = scorecard.importance_urgency(c.get("obs") or {}, cfg, c.get("standing", 0.0), c.get("automated", False), level=c.get("level"))
        why = settings.matching({"iu": iu, "candidate": c})
        if not why:
            rec["outcome"] = "not_triggered"
            continue
        rec["triggers"], rec["reasons"] = why, iu["reasons"]
        verdict = c.get("verdict")
        if verdict in QUARANTINE_VERDICTS:                       # urgent but failed the scan: alert, never read
            alert(TEASER_QUARANTINED, "critical", "alarm-quarantined:" + mid)
            rec["outcome"] = "quarantined"
            handled.add(mid)
            continue
        if verdict != "clean":                                   # no verdict: held unread, retried by the intake; nothing to read
            rec["outcome"] = "unscanned"
            continue
        try:
            writeup = _clean_writeup(reader.read(fetch_text(tid)), settings.writeup_max_chars)
        except Exception as e:                                   # urgent mail must not be lost because the read failed
            rec["outcome"], rec["error"] = "read_failed", "%s: %s" % (type(e).__name__, e)
            alert(TEASER_READ_FAILED, "critical", "alarm:" + mid)
            handled.add(mid)
            continue
        if writeup_dir:
            os.makedirs(writeup_dir, exist_ok=True)
            with open(os.path.join(writeup_dir, "%s.md" % tid), "a", encoding="utf-8") as f:
                f.write("## %s (%s)\n%s\n\n" % (mid, ", ".join(why), writeup))
        alert(TEASER_URGENT, "critical", "alarm:" + mid)
        rec["outcome"], rec["writeup"] = "alarmed", writeup
        handled.add(mid)
    _save_state(state_path, handled)

    n = lambda k: sum(1 for o in outcomes if o["outcome"] == k)
    errs = n("read_failed") or notify_failed
    quar, alarmed = n("quarantined"), n("alarmed")
    status = "ERROR" if errs else "NEEDS_REVIEW" if (quar or alarmed) else "OK"
    summary = "examined %d: %d alarmed, %d quarantined, %d read failed, %d waiting for scan%s" % (
        len(outcomes), alarmed, quar, n("read_failed"), n("unscanned"), ", PHONE SEND FAILED" if notify_failed else "")
    emit(tile_path, desk="grand-central", pulse_job=settings.pulse_job, stale_after_s=settings.stale_after_s,
         status=status, rc=1 if errs else 0, summary=summary,
         payload={"examined": len(outcomes), "alarmed": alarmed, "quarantined": quar, "read_failed": n("read_failed"),
                  "unscanned": n("unscanned")})
    return {"outcomes": outcomes, "status": status, "summary": summary, "notify_failed": notify_failed}

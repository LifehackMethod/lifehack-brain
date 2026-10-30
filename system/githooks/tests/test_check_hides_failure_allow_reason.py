#!/usr/bin/env python3
"""Round C 3: `# allow-silence:` / `# empty-ok:` must carry a real reason when switch allow_silence_reason is ON.
OFF = exactly today (any non-empty reason exempts). Fictional fixtures only.
Run: python3 system/githooks/tests/test_check_hides_failure_allow_reason.py"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "system", "tools"))
import door_rules  # noqa: E402

CHECK = os.path.join(ROOT, "system", "githooks", "checks", "hides_failure.py")
FAILS = []


def expect(label, cond):
    print(("   ok   " if cond else "  FAIL  ") + label)
    if not cond:
        FAILS.append(label)


def scan(body, sw):
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "demo-job.sh")
        open(p, "w", encoding="utf-8").write("#!/bin/bash\n" + body + "\n")
        env = dict(os.environ, ROUNDB_ALLOW_SILENCE_REASON=sw)
        r = subprocess.run([sys.executable, CHECK, "--files", p], capture_output=True, text=True, env=env)
        return r.returncode, r.stderr


CALL = "widget_fetch.py --now 2>/dev/null || true"
GOOD = "the stamp is best-effort; if the write fails the next run repeats the line and nothing is lost"
JUNK = ["todo", "ok", "needed", "fine", "reason", "because", "x", "tbd", "n/a", "intentional", "needed here", "fine ok",
        "widget fetch quiet", "silence 2>/dev/null"]

# OFF: today's behaviour, every non-empty reason exempts; no reason at all still refuses
for j in JUNK + [GOOD]:
    rc, err = scan(f"{CALL}  # allow-silence: {j}", "off")
    expect(f"OFF: reason {j!r} exempts (rc 0)", rc == 0 and "ALLOWED" in err)
rc, err = scan(f"{CALL}  # allow-silence:", "off")
expect("OFF: bare allow-silence still refuses", rc == 1)
rc, err = scan(CALL, "off")
expect("OFF: no comment still refuses", rc == 1)

# ON: junk reasons do not exempt and the message teaches what a real one looks like
for j in JUNK:
    rc, err = scan(f"{CALL}  # allow-silence: {j}", "on")
    expect(f"ON: junk reason {j!r} refuses", rc == 1 and "REFUSED" in err and "reason is" in err and "WHICH failure" in err)
rc, err = scan(f"{CALL}  # allow-silence:", "on")
expect("ON: bare allow-silence refuses", rc == 1)
rc, err = scan(f"{CALL}  # allow-silence: {GOOD}", "on")
expect("ON: a real reason exempts and is reported ALLOWED", rc == 0 and "ALLOWED" in err and "REFUSED" not in err)
rc, err = scan(f"{CALL}  # empty-ok: ok", "on")
expect("ON: junk empty-ok on a silenced call also refuses", rc == 1)
rc, err = scan(f"{CALL} \\\n  --also  # allow-silence: {GOOD}", "on")
expect("ON: real reason on a continuation line exempts", rc == 0)

# journal boilerplate stays exempt in both states (it is never an allow-silence case)
JOURNAL = '. "$_lhb_dir/lib/journal.sh" 2>/dev/null || lhb_journal_fire() { :; }'
for sw in ("off", "on"):
    rc, err = scan(JOURNAL, sw)
    expect(f"{sw.upper()}: journal boilerplate needs no comment", rc == 0 and "REFUSED" not in err)

# the judge itself
expect("judge: real reason passes", door_rules.weak_reason(GOOD, CALL) == "")
expect("judge: empty is weak", door_rules.weak_reason("", CALL) != "")
expect("judge: placeholders are weak", all(door_rules.weak_reason(j, CALL) for j in JUNK))

print("FAILS: %d" % len(FAILS))
sys.exit(1 if FAILS else 0)

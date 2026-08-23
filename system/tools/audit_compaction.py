#!/usr/bin/env python3
"""
audit_compaction.py — ONE audit for the pad-compaction chain (pad_archive.py +
save_step_ledger.py + skills/checkin/SKILL.md).

WHY (2026-08-08 blind 4-lens pre-mortem on brief compaction): found 6 verified defects,
2 already fixed in commit 8eeece2. This script exists so none of the 6 can regress
silently (PART 1), and so 3 declined-but-unverified risks get a MEASURED verdict instead
of a guess (PART 2). NOT test_pad_archive.py's replacement — that file already owns 21
cases of archive/verify chain integrity; nothing here duplicates it.

PART 1 — checks 1-6, each printing PASS/FAIL with evidence. For the 4 checks whose fix
still lives in pad_archive.py, also a synthetic proof the check CAN fail: a temp copy of
pad_archive.py with the fix's own lines patched back out (regex substitution — never git
stash, other windows are live), run against the SAME fixture. Checks 5-6 test facts that
are ALREADY true today (a known-open gap in save_step_ledger's verified set; /checkin
never calling `start`) — proven capable of failing simply by running against real code.

PART 2 — measurements 7-9 on declined-but-unverified risks. Report an observation, never
a pass/fail verdict; never affect the exit code.

Usage:  python3 system/tools/audit_compaction.py
Exit:   0 every PART 1 check PASSED · 1 at least one FAILED (5 and 6 failing today is
        EXPECTED — see their WHY lines; the exit code stays honest rather than hiding it)

All fixtures live under tempfile.mkdtemp(), removed after each check. Nothing under the
Google Drive path is touched. Only pad_archive.py / save_step_ledger.py / checkin's
SKILL.md are read (read-only), plus one scratch entry in the local (non-Drive)
~/.claude/run/save-ledger/ dir for check 8, deleted at the end regardless of outcome.
"""
# ⚖ SHIPPED WITH NO LIVE CALLER (D7, 2026-08-11). The only reference to it anywhere is a
# comment in the step ledger crediting it with finding the future-timestamp false green.
# It is an auditor nothing currently runs. Shipped as-is per the ruling, and named here so
# the absence is on the record rather than inferred from silence later.

import datetime
import hashlib
import importlib.util
import inspect
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAD_ARCHIVE = HERE / "save" / "pad_archive.py"
SAVE_LEDGER = HERE / "save" / "save_step_ledger.py"
CHECKIN_SKILL = HERE.parent.parent / ".claude" / "skills" / "checkin" / "SKILL.md"

DEFAULT_HEADER = ('## 7. SCRATCHPAD  *(dumb capture surface — for real project briefs; '
                   'freeform notes only)*')
DEFAULT_FOOTER = "\n## + CHRONICLE POINTER\nfooter\n"

results = []  # (name, verdict) — PART 1 only; PART 2 measurements never land here.


def report(name, verdict, evidence, why=""):
    results.append((name, verdict))
    print("[%s] %s — %s" % (verdict, name, evidence))
    if why:
        print("    WHY: %s" % why)


def run(script, *args, env=None):
    """Invoke a python script (real or a broken_copy) as a genuinely separate process."""
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, env=e)
    return p.returncode, p.stdout, p.stderr


def mkbrief(d, body, header=DEFAULT_HEADER, footer=DEFAULT_FOOTER):
    path = os.path.join(d, "brief.md")
    text = "# Brief\n\n## 1. FRAME\n> goal\n\n" + header + "\n" + body + footer
    open(path, "w", encoding="utf-8").write(text)
    return path


def archive_path(brief):
    return brief + ".pad-archive.md"


def shasum(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def broken_copy(pattern, repl, flags=0):
    """Temp copy of pad_archive.py with ONE regex-matched span replaced by `repl` (a plain
    string, inserted via a lambda so re.sub never re-interprets its backslashes as
    backreferences). Reconstructs the PRE-FIX predicate so a check's failure-capability
    can be demonstrated in-process against the SAME fixture, without git stash."""
    src = PAD_ARCHIVE.read_text(encoding="utf-8")
    new_src, n = re.subn(pattern, lambda m, r=repl: r, src, count=1, flags=flags)
    if n != 1:
        raise RuntimeError("broken_copy: patch pattern not found (source may have moved): %r"
                            % pattern[:80])
    fd, path = tempfile.mkstemp(suffix="_pad_archive_broken.py")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(new_src)
    return path


def try_broken_copy(check_name, pattern, repl, flags=0):
    """Wraps broken_copy() for the OPTIONAL 'prove it can fail' demonstration only.
    pad_archive.py has been rewritten since these checks were written (paths moved into
    system/tools/save/, and the internals of select()/state()/clear() changed shape with
    it) — some of these regex patches no longer match anything in the current source.
    That is a real fact worth surfacing, not a crash worth hiding: on a RuntimeError from
    broken_copy() (pattern not found), print an honest SKIPPED note and return None rather
    than taking the whole audit down. The check's REAL verdict is unaffected either way —
    every caller calls report() with the true PASS/FAIL BEFORE reaching this proof step."""
    try:
        return broken_copy(pattern, repl, flags=flags)
    except RuntimeError as e:
        print("    PROOF: SKIPPED (%s) — synthetic patch pattern no longer matches "
              "pad_archive.py; the source has moved since this proof was written, so "
              "falsifiability could not be demonstrated this run. %s" % (check_name, e))
        return None


def pad_module():
    """Load pad_archive.py as a module (extract_scratchpad/sha reuse in check 8) —
    read-only, no side effects at import time."""
    spec = importlib.util.spec_from_file_location("pad_archive_audit_mod", str(PAD_ARCHIVE))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ══════════════════════ PART 1 — the 6 regressions ══════════════════════
def check_1_boundary_truncation():
    d = tempfile.mkdtemp()
    try:
        header = DEFAULT_HEADER
        body = ("> before the sub-heading\n"
                "### Chronicle bug notes\n"
                "> AFTER the fake boundary — must survive\n"
                "> second line after boundary\n")
        b = mkbrief(d, body, header)
        run(PAD_ARCHIVE, "archive", b)
        run(PAD_ARCHIVE, "clear", b)
        after = open(b, encoding="utf-8").read()
        content_kept = "AFTER the fake boundary" in after
        annot_kept = "*(dumb capture surface" in after
        ok = content_kept and annot_kept
        report("1 boundary-truncation-is-harmless", "PASS" if ok else "FAIL",
               "content-after-subheading kept=%s · header-annotation kept=%s"
               % (content_kept, annot_kept),
               "" if ok else "post-boundary content or the header annotation was deleted — DATA LOSS")
        # PROVE IT CAN FAIL: strip the 2026-08-08 annotation-preserving splice-start fix
        # (pad_archive.py ~319-321) and show the SAME assertion then fails.
        broken = try_broken_copy(
            "check_1",
            r'    nl = text\.find\("\\n", span_start\)\n'
            r'    if nl != -1 and nl < span_end:\n'
            r'        span_start = nl \+ 1\n\n', '')
        if broken is None:
            return ok
        d2 = tempfile.mkdtemp()
        try:
            b2 = mkbrief(d2, body, header)
            run(broken, "archive", b2)
            run(broken, "clear", b2)
            annot_kept2 = "*(dumb capture surface" in open(b2, encoding="utf-8").read()
            print("    PROOF: pre-fix copy (annotation-splice removed) on same fixture -> "
                  "annotation kept=%s (must be False)" % annot_kept2)
        finally:
            shutil.rmtree(d2, ignore_errors=True)
            os.unlink(broken)
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def check_2_empty_capture():
    d = tempfile.mkdtemp()
    try:
        b = os.path.join(d, "brief.md")
        # header is the LAST thing in the file: SCRATCH_CANON_RE matches, m.end()==len(text),
        # extract_scratchpad() returns "" — found, but zero characters captured.
        open(b, "w", encoding="utf-8").write("# Brief\n\n## 1. FRAME\n> goal\n\n## 7. SCRATCHPAD")
        rc, out, err = run(PAD_ARCHIVE, "state", b)
        ok = rc == 4 and out.startswith("CANNOT-READ")
        report("2 empty-capture-is-not-clean", "PASS" if ok else "FAIL",
               "state rc=%d · first line=%r" % (rc, out.splitlines()[0] if out else ""),
               "" if ok else "a zero-char capture must be CANNOT-READ, never PAD-EMPTY")
        # PROVE IT CAN FAIL: remove DEFECT A's `pad == ""` guard so the zero-char capture
        # falls through to the whitespace test and misreads PAD-EMPTY.
        broken = try_broken_copy("check_2", r'    if pad == "":\n(?:.*\n)*?        return 4\n\n', '')
        if broken is None:
            return ok
        try:
            rc2, out2, err2 = run(broken, "state", b)
            proved = rc2 == 0 and out2.startswith("PAD-EMPTY")
            print("    PROOF: pre-fix copy (DEFECT A guard removed) -> rc=%d out=%r — proved=%s"
                  % (rc2, out2.splitlines()[0] if out2 else "", proved))
        finally:
            os.unlink(broken)
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def check_3_bold_lines_not_empty():
    d = tempfile.mkdtemp()
    try:
        body = ("- **Fix the login bug**\n"
                "- **Update the onboarding docs**\n"
                "- **Ship the release**\n")
        b = mkbrief(d, body)
        rc, out, err = run(PAD_ARCHIVE, "state", b)
        ok = rc == 2 and out.startswith("PAD-DIRTY")
        report("3 bold-lines-are-not-empty", "PASS" if ok else "FAIL",
               "state rc=%d · first line=%r" % (rc, out.splitlines()[0] if out else ""),
               "" if ok else "three bolded action items must read PAD-DIRTY, never PAD-EMPTY")
        # PROVE IT CAN FAIL: DEFECT B's original _BOILERPLATE_LINE_RE was DELETED, so its exact
        # regex no longer exists to restore. RECONSTRUCTED per the docstring's own description
        # ("any all-bold line matched") — an approximation, labeled as such.
        broken = try_broken_copy(
            "check_3",
            r'    body = pad\.split\("\\n", 1\)\[1\] if "\\n" in pad else pad\n'
            r'    stripped = body\.strip\(\)\n',
            '    body = pad.split("\\n", 1)[1] if "\\n" in pad else pad\n'
            '    _bold_only = re.compile(r"^\\s*[-*]?\\s*\\*\\*.*\\*\\*\\s*$")\n'
            '    body = "\\n".join(_l for _l in body.splitlines() if not _bold_only.match(_l))\n'
            '    stripped = body.strip()\n')
        if broken is None:
            return ok
        try:
            rc2, out2, err2 = run(broken, "state", b)
            proved = rc2 == 0 and out2.startswith("PAD-EMPTY")
            print("    PROOF: pre-fix copy (RECONSTRUCTED bold-only-is-blank predicate) -> "
                  "rc=%d out=%r — proved=%s" % (rc2, out2.splitlines()[0] if out2 else "", proved))
        finally:
            os.unlink(broken)
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def check_4_clear_refuses_without_proof():
    d = tempfile.mkdtemp()
    try:
        b = mkbrief(d, "> first draft\n")
        run(PAD_ARCHIVE, "archive", b)
        txt = open(b, encoding="utf-8").read()
        open(b, "w", encoding="utf-8").write(txt.replace("first draft", "first draft — UNARCHIVED EDIT"))
        before = shasum(b)
        rc, out, err = run(PAD_ARCHIVE, "clear", b)
        after = shasum(b)
        ok = rc != 0 and before == after
        report("4 clear-refuses-without-proof", "PASS" if ok else "FAIL",
               "clear rc=%d · brief byte-identical=%s" % (rc, before == after),
               "" if ok else "clear must refuse (nonzero) and leave the brief byte-identical when "
                             "the pad was edited after archiving")
        # PROVE IT CAN FAIL: disable the hash-match guard and show it then clears anyway.
        broken = try_broken_copy(
            "check_4",
            r'    if not prev or prev != pad_hash:\n',
            '    if False:  # BROKEN: hash-match guard disabled to prove this check can fail\n')
        if broken is None:
            return ok
        d2 = tempfile.mkdtemp()
        try:
            b2 = mkbrief(d2, "> second draft\n")
            run(PAD_ARCHIVE, "archive", b2)
            t2 = open(b2, encoding="utf-8").read()
            open(b2, "w", encoding="utf-8").write(t2.replace("second draft", "second draft — UNARCHIVED"))
            before2 = shasum(b2)
            rc2, out2, err2 = run(broken, "clear", b2)
            after2 = shasum(b2)
            proved = rc2 == 0 and before2 != after2
            print("    PROOF: pre-fix copy (guard disabled) -> clear rc=%d · brief changed=%s "
                  "— proved=%s" % (rc2, before2 != after2, proved))
        finally:
            shutil.rmtree(d2, ignore_errors=True)
            os.unlink(broken)
        return ok
    finally:
        shutil.rmtree(d, ignore_errors=True)


def check_5_ledger_tilde_set_honest():
    spec = importlib.util.spec_from_file_location("save_step_ledger_audit_mod", str(SAVE_LEDGER))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    no_artifact = set(mod.NO_ARTIFACT_IDS)
    verified_ids = set(re.findall(r'a\.step == "([^"]+)"', inspect.getsource(mod.cmd_stamp)))
    unaccounted = [i for i in mod.IDS if i not in no_artifact and i not in verified_ids]
    ok = not unaccounted
    expected = {"0.5", "7c.5", "7d"}
    report("5 ledger-tilde-set-honest", "PASS" if ok else "FAIL",
           "bare stamps with no _verify_ branch and not in NO_ARTIFACT_IDS: %s" % unaccounted,
           "" if ok else
           "KNOWN-OPEN (expected today, matches the pre-mortem finding%s): these ids render as a "
           "plain ✓ in save_step_ledger's own report(), while being bare `stamp <id>` calls with "
           "no evidence chain." % ("" if set(unaccounted) == expected else
                                    " — ⚠ DIFFERENT SET than the pre-mortem, investigate"))
    print("    PROOF: observed directly against the current, unmodified save_step_ledger.py — "
          "no synthetic reconstruction needed; this is failing right now.")
    return ok


def check_6_checkin_never_calls_start():
    txt = CHECKIN_SKILL.read_text(encoding="utf-8")
    # ⛔⛔ MATCH A REAL INVOCATION, NOT A MENTION (2026-08-08 — this check FALSE-PASSED within
    # minutes of shipping). The bare-string version counted the sentence "/checkin NEVER CALLS
    # `save_step_ledger.py start`" — prose ADDED to document this very defect — as a call, and the
    # check went green while the defect was untouched. ⭐ A check that documentation can silence is
    # not a check, and this is the same class `build-sop.md` already names: "a guard that greps a
    # keyword false-positives on mere MENTIONS — match the invocation pattern, never the keyword
    # alone." Prior instances: the status-bar guard that blocked its own commit (2026-07-13) and
    # checkin_open.py matching its own description (2026-08-06).
    # ⇒ Anchor to line-start + an interpreter, which is what a runnable command actually looks like.
    _INVOKE = r'(?m)^\s*(?:python3|bash)\s+\S*save_step_ledger\.py\s+%s\b'
    stamp_calls = len(re.findall(_INVOKE % 'stamp', txt))
    start_calls = len(re.findall(_INVOKE % 'start', txt))
    ok = stamp_calls > 0 and start_calls > 0
    report("6 checkin-calls-ledger-start", "PASS" if ok else "FAIL",
           "skills/checkin/SKILL.md — `stamp` calls=%d · `start` calls=%d" % (stamp_calls, start_calls),
           "" if ok else
           "KNOWN-OPEN (expected today): checkin calls `save_step_ledger.py stamp graduate` but "
           "never `save_step_ledger.py start` — _verify_graduate refuses without a started ledger, "
           "so /checkin's graduate stamp can never actually be written.")
    print("    PROOF: observed directly by grepping the current, unmodified SKILL.md — "
          "no synthetic reconstruction needed; this is failing right now.")
    return ok


# ══════════════════════ PART 2 — the 3 measurements ══════════════════════
def measure_7_concurrent_archive():
    d = tempfile.mkdtemp()
    try:
        b = mkbrief(d, "> base content for the concurrency probe\n")
        barrier = threading.Barrier(2)
        outs = [None, None]

        def worker(i):
            barrier.wait()
            outs[i] = run(PAD_ARCHIVE, "archive", b)

        t1 = threading.Thread(target=worker, args=(0,))
        t2 = threading.Thread(target=worker, args=(1,))
        t1.start(); t2.start(); t1.join(); t2.join()
        txt = open(archive_path(b), encoding="utf-8").read() if os.path.exists(archive_path(b)) else ""
        headers = txt.count("<!-- pad-archive ::")
        ns = re.findall(r'compaction #(\d+)', txt)
        dup_counter = len(ns) != len(set(ns))
        vrc, vout, verr = run(PAD_ARCHIVE, "verify", b)
        vline = (vout or verr).strip().splitlines()[0] if (vout or verr).strip() else ""
        print("[MEASURED] 7 concurrent archive — 2 threads raced `archive` on ONE brief at once")
        print("    proc1 rc=%s proc2 rc=%s" % (outs[0][0], outs[1][0]))
        print("    blocks written=%d · compaction#s=%s · duplicate counter=%s"
              % (headers, ns, dup_counter))
        print("    subsequent `verify` rc=%d (%s)" % (vrc, vline))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def measure_8_clock_skew():
    d = tempfile.mkdtemp()
    ledger_file = None
    try:
        b = mkbrief(d, "> clock-skew probe content\n")
        pa = pad_module()
        pad = pa.extract_scratchpad(open(b, encoding="utf-8").read())
        pad_hash = pa.sha(pad)
        future = (datetime.datetime.now().astimezone() + datetime.timedelta(days=1)) \
            .isoformat(timespec="seconds")
        header = ("<!-- pad-archive :: compaction #1 :: %s :: host=%s :: prev=GENESIS :: hash=%s -->"
                  % (future, socket.gethostname(), pad_hash))
        open(archive_path(b), "w", encoding="utf-8").write("\n%s\n%s\n" % (header, pad))
        key = "audit-compaction-clockskew-%d" % os.getpid()
        env = {"CLAUDE_CODE_SESSION_ID": key}
        ledger_file = Path.home() / ".claude" / "run" / "save-ledger" / ("save-%s.json" % key)
        run(SAVE_LEDGER, "start", env=env)
        rc, out, err = run(SAVE_LEDGER, "stamp", "compact", b, env=env)
        last = (out or err).strip().splitlines()[-1] if (out or err).strip() else ""
        print("[MEASURED] 8 clock skew — hand-wrote a pad-archive block dated %s (+1 day), hash "
              "matching the CURRENT pad exactly" % future)
        print("    `save_step_ledger.py stamp compact` rc=%d -> %s — %s"
              % (rc, "ACCEPTED" if rc == 0 else "REFUSED", last))
    finally:
        if ledger_file is not None:
            try:
                ledger_file.unlink()
            except OSError:
                pass
        shutil.rmtree(d, ignore_errors=True)


def measure_9_fsync_gap():
    d = tempfile.mkdtemp()
    try:
        b = mkbrief(d, "> fsync-gap probe content\n")
        rc, out, err = run(PAD_ARCHIVE, "archive", b)
        receipt = out.strip()
        h = receipt.split()[1] if receipt.startswith("RECEIPT") else None
        ap = archive_path(b)
        # a genuinely SEPARATE process, spawned only after the archiving process has exited
        code = "import sys; sys.exit(0 if %r in open(%r, encoding='utf-8').read() else 1)" % (h, ap)
        seen = subprocess.run([sys.executable, "-c", code]).returncode == 0
        print("[MEASURED] 9 fsync gap — archive() appends with plain write()+close(), no os.fsync")
        print("    RECEIPT=%r" % receipt)
        print("    a fresh separate process re-reading immediately after: block present=%s" % seen)
        print("    NOTE (explanatory, not a substitute for the measurement above): write()+close() "
              "already reaches the OS page cache, visible to any process on the same machine — "
              "fsync's absence affects durability across a crash, not cross-process visibility.")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    print("=== audit_compaction.py — pad-compaction regression + risk audit ===\n")
    print("--- PART 1: regression on the 6 verified defects ---")
    checks = [check_1_boundary_truncation, check_2_empty_capture, check_3_bold_lines_not_empty,
              check_4_clear_refuses_without_proof, check_5_ledger_tilde_set_honest,
              check_6_checkin_never_calls_start]
    outcomes = [fn() for fn in checks]

    print("\n--- PART 2: measure the 3 declined-but-unverified risks (never affects exit code) ---")
    measure_7_concurrent_archive()
    measure_8_clock_skew()
    measure_9_fsync_gap()

    passed = sum(1 for o in outcomes if o)
    print("\n=== PART 1: %d/6 passed ===" % passed)
    if passed != len(outcomes):
        failed = [name for (name, verdict) in results if verdict == "FAIL"]
        print("FAILED: %s" % ", ".join(failed))
        print("Checks 5 and 6 failing is EXPECTED (KNOWN-OPEN today, see their WHY lines above) — "
              "the exit code stays honest about that rather than special-casing them clean.")
    return 0 if passed == len(outcomes) else 1


if __name__ == "__main__":
    import os, sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "system", "tools")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    sys.exit(main())

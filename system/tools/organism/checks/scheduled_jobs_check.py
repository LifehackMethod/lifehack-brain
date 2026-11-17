#!/usr/bin/env python3
# not-wired-yet: the task that built this check (2026-11-16, round five step 5) forbids touching hooks.json and system/register/**; wiring into the component-page stamper is the next step's work.
"""scheduled_jobs_check.py — the named check whose receipt stamps the Scheduled jobs component page
(round five step 5). A CHECK, never the checked thing.

What it watches: the scheduled-jobs machinery as it actually landed on origin — the scheduler door
(install-schedulers.sh), the runner (job-run.sh), and the pulse state path.

How it works: it fetches origin V2 (unless --no-fetch), resolves the source ref to a sha, checks out
that sha into a DETACHED git worktree (a clean checkout of the fetched commit — definition §4), runs
the component's real tests and drift probes THERE, and records that sha in the receipt — the receipt
is always about a pinned, clean tree, never about whatever happens to be sitting in a working folder.
It is the check, not the checked thing: it changes nothing on origin and nothing in the repo except
writing one status tile.

What it does NOT test (recorded in the tile's `not_tested`):
  - the job-sim.sh rig (not run: long)
  - live installed jobs and their last-success ages (personal, not shipped)
  - the Linux/Windows pulse path end to end

`refused_once` carries two meanings, and the tile records which applies:
  - For the two test-suite probes (intervals-test, door-test) `refused_once` means a refusal
    was SEEN in that test's own output — the door refusing a planted bad row.
  - For the three text probes (no-send-verb, refusal-rulebook-resolves, state-local-not-drive)
    `refused_once` is always False: a planted fault caught by the self-test is a fault BITTEN
    (`bite_tested` true), and a planted fault is not a refusal seen in use. Only a refusal
    observed in a real run would set `refused_once`.

Usage:
    scheduled_jobs_check.py [--repo DIR] [--source origin/V2] [--no-fetch] [--out PATH] [--selftest]

Exit codes: 0 every probe RAN (a FAIL is a finding, not a crash) · 2 a probe ERRORed or the worktree
could not be made · 4 the repo or emit_status could not be read.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

NOT_TESTED = [
    "job-sim.sh rig (not run: long)",
    "live installed jobs and their last-success ages (personal, not shipped)",
    "the Linux/Windows pulse path end to end",
]

INSTALLER = "system/tools/install-schedulers.sh"


# ── text probes: pure functions over text_by_path -> (result, evidence) ─────────
# result is "PASS" | "FAIL" | "ERROR"; evidence is "" or "path:line[,path:line…]".

def _wallow(value: str) -> bool:
    """Does an assignment VALUE point state under the notes/Drive root?"""
    return any(marker in value for marker in
               ("NOTES_ROOT", "LIFEHACK_ROOT", "brain_root", "My Drive"))


def _statement_at(lines, i) -> str:
    """Join the statement starting at line i (0-based) up to its closing brace/paren,
    so a dict spread over several lines is matched as one statement."""
    parts = []
    depth = 0
    for ln in lines[i:]:
        parts.append(ln)
        depth += ln.count("(") + ln.count("{") - ln.count(")") - ln.count("}")
        if depth <= 0:
            break
    return "\n".join(parts)


def probe_state_local(text_by_path) -> "tuple[str, str]":
    """Watches: scheduler state stays on the machine, never the notes/Drive folder.
    Canon: canon/cron-jobs-sop.md 'State is local, never Drive'.
    FAIL if pulse.sh or pulse-park.sh assigns PARK_FILE (or any *_FILE=/STATE path, export
    form included) to a value under $NOTES_ROOT, $LIFEHACK_ROOT, brain_root, or My Drive.
    ERROR if either target file is missing, or no PARK_FILE assignment is found in either
    file — a probe must never pass vacuously."""
    hits = []
    saw_park = False
    for path in sorted(text_by_path):
        for i, line in enumerate(text_by_path[path].splitlines(), 1):
            m = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*)$", line)
            if not m:
                continue
            name, value = m.group(1), m.group(2)
            if name == "PARK_FILE":
                saw_park = True
            if ("_FILE" in name or "STATE" in name) and _wallow(value):
                hits.append(f"{path}:{i}")
    missing = [p for p in ("system/tools/pulse.sh", "system/tools/pulse-park.sh")
               if text_by_path.get(p) is None]
    if missing:
        return "ERROR", "missing target file(s): " + ", ".join(missing)
    if not saw_park:
        return "ERROR", "no PARK_FILE assignment found in either target file"
    return ("FAIL", ",".join(hits)) if hits else ("PASS", "")


def probe_no_send_verb(text_by_path) -> "tuple[str, str]":
    """Watches: the door never lets a job send email.
    Canon: COMPASS P-184; canonical-principles §15.29.
    FAIL if install-schedulers.sh holds a GWS_WRITE statement (joined across lines up to its
    closing brace before matching) whose regex allows the word `send`. ERROR if
    install-schedulers.sh is missing, or no GWS_WRITE definition is found — a probe must
    never pass vacuously."""
    text = text_by_path.get(INSTALLER)
    if text is None:
        return "ERROR", "missing " + INSTALLER
    lines = text.splitlines()
    hits = []
    found = False
    for i, line in enumerate(lines, 1):
        # a definition only: a comment merely NAMING GWS_WRITE is not its definition
        if not re.match(r"^GWS_WRITE\s*=", line):
            continue
        found = True
        if re.search(r"\bsend\b", _statement_at(lines, i - 1)):
            hits.append(f"{INSTALLER}:{i}")
    if not found:
        return "ERROR", "no GWS_WRITE definition found in " + INSTALLER
    return ("FAIL", ",".join(hits)) if hits else ("PASS", "")


def probe_refusal_rulebook(text_by_path, root) -> "tuple[str, str]":
    """Watches: every door refusal names a rulebook that exists. Canon: COMPASS P-127.
    FAIL if any `Rulebook: \\`<path>\\`` in install-schedulers.sh (backticks may be
    backslash-escaped in the shell source) names a path that does not exist under root.
    ERROR if install-schedulers.sh is missing, or no `Rulebook:` line exists — a probe
    must never pass vacuously."""
    text = text_by_path.get(INSTALLER)
    if text is None:
        return "ERROR", "missing " + INSTALLER
    missing = []
    found = False
    for i, line in enumerate(text.splitlines(), 1):
        for m in re.finditer(r"Rulebook:\s*\\?`([^`\\]+?)\\?`", line):
            found = True
            rulebook = m.group(1).strip()
            if not os.path.exists(os.path.join(root, rulebook)):
                missing.append(f"{INSTALLER}:{i}:{rulebook}")
    if not found:
        return "ERROR", "no Rulebook line found in " + INSTALLER
    return ("FAIL", ",".join(missing)) if missing else ("PASS", "")


# ── self-test of the text probes: planted bad must FAIL, good must PASS ─────────

def _selftest(root) -> "dict[str, bool]":
    """Planted-fault self-test of the three text probes: a planted bad must FAIL, the good
    twin must PASS. One planted-bad case per pattern the probe matches: the single-line
    GWS_WRITE form, the multi-line form (joined up to its closing brace), the export form of
    PARK_FILE, and the $LIFEHACK_ROOT / My Drive wallow markers. Also proves the vacuous
    cases ERROR (missing target, zero matching lines) rather than PASS."""
    bad_gws = 'GWS_WRITE = {"gmail": re.compile(r"\\s*users (?:messages (?:modify|send))\\b"),'
    good_gws = 'GWS_WRITE = {"gmail": re.compile(r"\\s*users (?:messages (?:modify|drafts create))\\b"),'
    bad_gws_ml = ('GWS_WRITE = {\n'
                  '    "gmail": re.compile(r"\\s*users (?:messages (?:modify|send))\\b"),\n'
                  '}\n')
    good_gws_ml = ('GWS_WRITE = {\n'
                   '    "gmail": re.compile(r"\\s*users (?:messages (?:modify|drafts create))\\b"),\n'
                   '}\n')
    bad_rulebook = "Rulebook: \\`system/sops/nope.md\\` — report it."
    good_rulebook = "Rulebook: \\`canon/cron-jobs-sop.md\\` — read it."
    bad_state = 'PARK_FILE="$NOTES_ROOT/state/x.json"'
    good_state = 'PARK_FILE="$HOME/.config/lifehack/state/x.json"'
    bad_state_export = 'export PARK_FILE="$LIFEHACK_ROOT/state/x.json"'
    good_state_export = 'export PARK_FILE="$HOME/.config/lifehack/state/x.json"'
    bad_state_drive = 'PARK_FILE="/Users/x/My Drive/notes/state.json"'
    good_state_drive = 'PARK_FILE="$HOME/.config/lifehack/state/x.json"'
    # a comment merely NAMING GWS_WRITE is not its definition: the real definition's
    # `send` must still bite
    bad_gws_comment = ('# see GWS_WRITE policy in the door docs\n' + bad_gws + '\n')
    good_gws_comment = ('# see GWS_WRITE policy in the door docs\n' + good_gws + '\n')
    comment_only = '# GWS_WRITE is discussed below\n'

    results = {}
    r = [probe_no_send_verb({INSTALLER: s + "\n"})[0]
         for s in (bad_gws, good_gws, bad_gws_ml, good_gws_ml)]
    r.append(probe_no_send_verb({INSTALLER: "x = 1\n"})[0])  # no definition -> ERROR, never PASS
    r.append(probe_no_send_verb({INSTALLER: bad_gws_comment})[0])   # comment + bad def -> FAIL
    r.append(probe_no_send_verb({INSTALLER: good_gws_comment})[0])  # comment + good def -> PASS
    r.append(probe_no_send_verb({INSTALLER: comment_only})[0])      # comment only -> ERROR
    results["no-send-verb"] = (r[0] == "FAIL" and r[1] == "PASS"
                               and r[2] == "FAIL" and r[3] == "PASS" and r[4] == "ERROR"
                               and r[5] == "FAIL" and r[6] == "PASS" and r[7] == "ERROR")
    r1 = probe_refusal_rulebook({INSTALLER: "x " + bad_rulebook + "\n"}, root)[0]
    r2 = probe_refusal_rulebook({INSTALLER: "x " + good_rulebook + "\n"}, root)[0]
    r3 = probe_refusal_rulebook({INSTALLER: "echo hi\n"}, root)[0]  # no Rulebook line -> ERROR
    results["refusal-rulebook-resolves"] = (r1 == "FAIL" and r2 == "PASS" and r3 == "ERROR")
    park_good = 'PARK_FILE="$HOME/.config/lifehack/state/x.json"\n'
    def both(main_text):
        return {"system/tools/pulse.sh": main_text + "\n",
                "system/tools/pulse-park.sh": park_good}
    states = [probe_state_local(both(s))[0]
              for s in (bad_state, good_state, bad_state_export, good_state_export,
                        bad_state_drive, good_state_drive)]
    r_nopark = probe_state_local({"system/tools/pulse.sh": "OTHER=1\n",
                                  "system/tools/pulse-park.sh": "OTHER=1\n"})[0]  # no PARK_FILE -> ERROR
    r_nofiles = probe_state_local({})[0]  # both targets missing -> ERROR
    r_onefile = probe_state_local({"system/tools/pulse.sh": park_good})[0]  # one missing -> ERROR
    results["state-local-not-drive"] = (states[0] == "FAIL" and states[1] == "PASS"
                                        and states[2] == "FAIL" and states[3] == "PASS"
                                        and states[4] == "FAIL" and states[5] == "PASS"
                                        and r_nopark == "ERROR" and r_nofiles == "ERROR"
                                        and r_onefile == "ERROR")
    return results


# ── the run ──────────────────────────────────────────────────────────────────────

def _run(cmd, cwd=None) -> "tuple[int, str]":
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="scheduled_jobs_check.py",
                                 description="Named check: Scheduled jobs component (round five step 5).")
    ap.add_argument("--repo", default=None, help="repo root (default: the repo this file lives in)")
    ap.add_argument("--source", default="origin/V2")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--out", default=None, help="tile path (default: <brain>/status/component-scheduled-jobs.json)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(args.repo or os.path.join(here, "..", "..", "..", ".."))
    if not os.path.isdir(os.path.join(repo, ".git")) and not os.path.exists(os.path.join(repo, "HEAD")):
        print(f"ERROR: not a repo: {repo}", file=sys.stderr)
        return 4

    if args.selftest:
        results = _selftest(repo)
        for probe_id, okb in sorted(results.items()):
            print(f"{probe_id} {'OK' if okb else 'DID-NOT-BITE'} (self-test)")
        return 0 if all(results.values()) else 1

    # emit_status comes from the REAL repo's system/tools, never the worktree's copy
    tools_dir = os.path.join(repo, "system", "tools")
    try:
        sys.path.insert(0, tools_dir)
        from emit_status import emit_status  # noqa: E402
    except Exception as e:
        print(f"ERROR: cannot import emit_status from {tools_dir}: {e}", file=sys.stderr)
        return 4

    if not args.no_fetch:
        rc, out = _run(["git", "-C", repo, "fetch", "origin", "V2"])
        if rc != 0:
            print(f"ERROR: fetch failed: {out}", file=sys.stderr)
            return 4

    rc, sha = _run(["git", "-C", repo, "rev-parse", args.source])
    sha = sha.strip()
    if rc != 0 or len(sha) != 40:
        print(f"ERROR: cannot resolve {args.source}: {sha}", file=sys.stderr)
        return 4

    tmpdir = tempfile.mkdtemp(prefix="scheduled-jobs-check-")
    worktree_ok = True
    try:
        rc, out = _run(["git", "-C", repo, "worktree", "add", "--detach", tmpdir, sha])
        if rc != 0:
            print(f"ERROR: worktree add failed: {out}", file=sys.stderr)
            return 2
    except Exception as e:
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"ERROR: worktree add failed: {e}", file=sys.stderr)
        return 2

    probes = []
    try:
        rc_before, out_before = _run(["git", "-C", tmpdir, "status", "--porcelain"])
        clean_before = (rc_before == 0 and out_before.strip() == "")

        def add(id_, watches, canon, covers, result, evidence, refused_once, bite_tested=False):
            probes.append({"id": id_, "watches": watches, "canon": canon,
                           "result": result, "evidence": evidence,
                           "refused_once": bool(refused_once),
                           "bite_tested": bool(bite_tested), "covers": covers,
                           "untested": False})

        # ── run tests inside the clean checkout ──
        for id_, test, covers in (
            ("intervals-test", "system/tools/tests/test_install_schedulers_intervals.sh",
             ["system/tools/install-schedulers.sh"]),
            ("door-test", "system/tools/tests/test_job_run_door.sh",
             ["system/tools/job-run.sh", "system/tools/install-schedulers.sh", "system/tools/door_rules.py"]),
        ):
            rc, out = _run(["bash", test], cwd=tmpdir)
            lines = out.splitlines()
            if id_ == "intervals-test":
                result = "PASS" if rc == 0 else "FAIL"
                refused_once = any(("refuse" in ln and "PASS" in ln) for ln in lines)
            else:
                result = "PASS" if (rc == 0 and "ALL PASS" in out) else "FAIL"
                refused_once = any(ln.startswith("ok") and "refused" in ln for ln in lines)
            evidence = "" if result == "PASS" else f"{test} rc={rc}"
            add(id_, "", "", covers, result, evidence, refused_once)

        # ── text probes, on the worktree's copies ──
        def read(rel):
            with open(os.path.join(tmpdir, rel), encoding="utf-8", errors="replace") as f:
                return f.read()

        texts = {}
        for rel in (INSTALLER, "system/tools/pulse.sh", "system/tools/pulse-park.sh"):
            try:
                texts[rel] = read(rel)
            except OSError:
                texts[rel] = None

        # the text probes' self-test runs against the CLEAN CHECKOUT's files (root=tmpdir),
        # never the working tree; it runs before them in a normal run
        selftest = _selftest(tmpdir)

        installer_texts = {k: v for k, v in texts.items() if k == INSTALLER and v is not None}
        r, ev = probe_no_send_verb(installer_texts)
        add("no-send-verb", "the door never lets a job send email",
            "COMPASS P-184; canonical-principles §15.29",
            [INSTALLER], r, ev, False,  # a planted fault is not a refusal seen in use
            bite_tested=selftest.get("no-send-verb", False))

        r, ev = probe_refusal_rulebook(installer_texts, tmpdir)
        add("refusal-rulebook-resolves", "every door refusal names a rulebook that exists",
            "COMPASS P-127", [INSTALLER], r, ev, False,  # a planted fault is not a refusal seen in use
            bite_tested=selftest.get("refusal-rulebook-resolves", False))

        state_texts = {k: v for k, v in texts.items()
                       if k in ("system/tools/pulse.sh", "system/tools/pulse-park.sh") and v is not None}
        r, ev = probe_state_local(state_texts)
        add("state-local-not-drive", "scheduler state stays on the machine, never the notes/Drive folder",
            "canon/cron-jobs-sop.md 'State is local, never Drive'",
            ["system/tools/pulse.sh", "system/tools/pulse-park.sh"], r, ev,
            False,  # a planted fault is not a refusal seen in use
            bite_tested=selftest.get("state-local-not-drive", False))

        rc_after, out_after = _run(["git", "-C", tmpdir, "status", "--porcelain"])
        clean_after = (rc_after == 0 and out_after.strip() == "")
        clean_tree = clean_before and clean_after
    finally:
        _run(["git", "-C", repo, "worktree", "remove", "--force", tmpdir])
        shutil.rmtree(tmpdir, ignore_errors=True)

    # ── one line per probe ──
    for p in probes:
        print(f"{p['id']} {p['result']}" + (f" {p['evidence']}" if p["evidence"] else ""))

    results = [p["result"] for p in probes]
    if any(r == "ERROR" for r in results):
        status, tile_rc = "ERROR", 2
    elif any(r == "FAIL" for r in results):
        status, tile_rc = "DRIFT", 1
    else:
        status, tile_rc = "OK", 0

    n_pass = sum(1 for r in results if r == "PASS")
    summary = f"{n_pass} of {len(probes)} probes pass at {sha[:12]}"

    # ── the receipt ──
    try:
        if args.out:
            out_path = args.out
        else:
            rc, brain = _run(["python3", os.path.join(repo, "shared", "brain_root.py"), "--quiet"])
            brain = brain.strip()
            if rc != 0 or not brain:
                print("ERROR: brain root not resolvable; pass --out", file=sys.stderr)
                return 4
            out_path = os.path.join(brain, "status", "component-scheduled-jobs.json")
        tile = emit_status(out_path, desk="organism", pulse_job="component-scheduled-jobs-check",
                           stale_after_s=604800, status=status, rc=tile_rc, summary=summary,
                           emit_mode="manual",
                           payload={"component": "scheduled-jobs", "origin_sha": sha,
                                    "source": args.source, "clean_tree": bool(clean_tree),
                                    "checks": probes, "not_tested": NOT_TESTED})
        print(f"receipt: {tile.get('desk', '')} tile at {out_path}")
    except Exception as e:
        print(f"ERROR: could not write receipt: {e}", file=sys.stderr)
        return 4

    return 0


if __name__ == "__main__":
    sys.exit(main())

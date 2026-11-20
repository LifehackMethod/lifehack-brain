#!/usr/bin/env python3
"""run_tests.py - the ONE test runner for the Grand Central engine (shared/grand_central).

  python3 run_tests.py            run everything except live tests (listed as NOT RUN (live))
  python3 run_tests.py --live     also run live tests (real claude binary / network)

Exit 0 only if: nothing failed, nothing was NOT RUN, and every test file on disk is in the manifest.
Skips are counted and printed loudly. A new, unlisted test file is an error until added below.
"""
import argparse
import atexit
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# The tests run against the synthetic setup folder, never a real person's setup (set GC_SETUP_DIR to override).
FIXTURE_SETUP = ROOT / "tests" / "fixtures" / "setup"
os.environ.setdefault("GC_SETUP_DIR", str(FIXTURE_SETUP))
# Isolation: no test may write outside a tmp folder (the live data folder holds the real synth-usage.jsonl and more).
# The data, front-room and state folders all point into one tmp folder that is removed when the run ends.
_TMP = tempfile.mkdtemp(prefix="gc-test-data-")
atexit.register(shutil.rmtree, _TMP, True)
os.environ["GC_DATA_ROOT"] = _TMP
os.environ["AGE_FRONT_ROOM"] = os.path.join(_TMP, "front-room")
os.environ["GC_STATE_ROOT"] = os.path.join(_TMP, "state")
# Python used for each test run: env GC_TEST_PYTHON, else the one running this script.
PY = os.environ.get("GC_TEST_PYTHON") or sys.executable

# (path relative to ROOT, kind, live)   kind: unittest | script
MANIFEST = [
    ("tests/test_date_window.py", "script", False),
    ("tests/test_inbox_backfill.py", "script", False),
    ("tests/test_dedupe_cache.py", "script", False),
    ("tests/test_gate_cache.py", "unittest", False),  # gate cache: skip re-gating unchanged calendar/task items
    ("tests/test_regate.py", "unittest", False),      # --regate-quarantined / --release-quarantined doors
    ("tests/test_filters_contacts.py", "script", False),
    ("tests/test_pause_gate.py", "script", False),
    ("tests/test_source_freshness.py", "script", False),
    ("tests/test_splitback.py", "script", False),
    ("tests/test_reader_locked.py", "script", True),   # calls the real claude binary
    ("tests/test_migrations.py", "unittest", False),   # step 3A
    ("tests/test_backup.py", "unittest", False),       # step 3B
    ("tests/test_backup_settings.py", "unittest", False),  # Phase 1 step 1.6: settings copy + loud gc backup
    ("tests/test_store.py", "unittest", False),        # step 3D
    ("tests/test_front_door.py", "unittest", False),   # step 3D guard: EXPECTED RED until 3E repoints callers
    ("tests/test_items.py", "unittest", False),        # step 4
    ("tests/test_meaning.py", "unittest", False),      # step 5
    ("tests/test_daily.py", "unittest", False),        # step 7
    ("tests/test_step6.py", "unittest", False),        # step 6: desk reads + gc read commands
    ("tests/test_step24_readers.py", "unittest", False),  # Phase 2 step 2.4: readers on the one model, one planted case each
    ("tests/test_step26_freeze.py", "unittest", False),  # Phase 2 step 2.6: rebuild + check, frozen old tables, model health light
    ("tests/test_step31_organizations.py", "unittest", False),  # Phase 3 step 3.1: organizations, placement is his word, rebuild, gc who
    ("tests/test_retire_machine_guesses.py", "unittest", False),  # Phase 2 step 2.5: machine guesses and legacy mirror out of the model
    ("tests/test_lulu_signer.py", "unittest", False),  # step 1.7: LuLu check understands signer-keyed rules
    ("tests/test_step32_events.py", "unittest", False),  # Phase 3 step 3.2: events from the calendar, planted cases
    ("tests/test_step36_merging.py", "unittest", False),  # Phase 3 step 3.6: merging on his confirmation only, planted cases
    ("tests/test_step33_relationships.py", "unittest", False),  # Phase 3 step 3.3: the five relationships, ends, loops, who writes them
    ("tests/test_step34_levels.py", "unittest", False),  # Phase 3 step 3.4: levels above the person, planted cases
    ("tests/test_step37_pages.py", "unittest", False),  # Phase 3 step 3.7: gc person / org / upcoming / due, planted cases
    ("tests/test_step35_relation.py", "unittest", False),  # Phase 3 step 3.5: relation to the person, planted cases
    ("tests/test_step_senders.py", "unittest", False),  # Phase 3 senders: organization by domain, person / bot / question mark, bot need, the sheet's question marks
    ("tests/test_step3_tieups.py", "unittest", False),  # Phase 3 tie-ups: his level weights, level in Path A, live standing on the sheet, question marks, migration 027
    ("tests/test_diary_names.py", "unittest", False),  # diary names: one pattern + setup/desks.json, no hard-coded desk diary name
    ("tests/test_gc_org_onboarding.py", "unittest", False),  # gc org shows type with certainty; onboarding sheet needs --out
    ("tests/test_step44_diary_index.py", "unittest", False),  # Phase 4.4: diary index, migration 028
    ("tests/test_step45_midnight.py", "unittest", False),  # Phase 4.5: one entry per diary, keys stamped by the morning read
    ("tests/test_step47_diary_on_pages.py", "unittest", False),  # Phase 4.7: diary entries on person/org/upcoming pages
    ("tests/test_step46_fixes_backfill.py", "unittest", False),  # Phase 4.6: fixes + 7-day backfill on a test copy
    ("tests/test_step38_levels_scoring.py", "unittest", False),  # Phase 3 step 3.8: levels as a scoring input, planted cases
    ("tests/test_step310_onboarding.py", "unittest", False),  # Phase 3 step 3.10: onboarding sheet and recording his answers, planted cases
    ("tests/test_step42_routing.py", "unittest", False),  # Phase 4 step 4.2: routing by part of life, planted cases
    ("tests/test_doors.py", "unittest", False),        # step 6: planning doors (proposals, answer, urgent, week)
    ("tests/test_step4p_decide.py", "unittest", False),  # 4P.4 + 4P.4b engine: gc decide, the validated weekly picture, morning reads it
    ("tests/test_step4p_interface.py", "unittest", False),  # 4P.1 finish check: the planning-interface page is true (planted wrong field caught)
    ("tests/test_quarantine_files.py", "unittest", False),  # quarantine review files + detail column
    ("tests/test_graph.py", "unittest", False),  # World Model Trial Step 1: the flexible memory + the one door
    ("tests/test_engine.py", "unittest", False),  # World Model Trial Step 3: the engine
    ("tests/test_score_signals.py", "unittest", False),  # score.py: discovered signals == the five it imports by name
    ("tests/test_pinned_layout_roots.py", "unittest", False),  # 4M.5: the pinned live copy finds the plugin via LIFEHACK_CODE_ROOT
    ("tests/test_synthesize.py", "unittest", False),  # STEP 6a: the three-layer synthesis (fake AI)
    ("test_first_run.py", "unittest", False),  # first-run scaffold, templates and the lock over templates/
    ("tests/test_step3_front_room.py", "unittest", False),  # plan B2 step 3: delta + scorecard
    ("tests/test_step5_alarm.py", "unittest", False),  # plan B2 step 5: the alarm path
    ("tests/test_step13_14_jobs.py", "unittest", False),
    ("tests/test_p3door_readonly.py", "unittest", False),
    ("tests/test_p3index_job.py", "unittest", False),
    ("tests/test_p3d_ops.py", "unittest", False),
    ("tests/test_p3w_wake.py", "unittest", False),
    ("tests/test_feeds.py", "unittest", False),  # 4P.0b: the named no-feed state, the gate, status --json  # phase 1 steps 1.3 and 1.4: fast clock, morning job, midnight job
    ("tests/test_step43_keys.py", "unittest", False),  # Phase 4 step 4.3: keys in every diary entry, planted cases
    ("tests/test_step4_morning.py", "unittest", False),  # plan B2 step 4: the morning read, midnight entry, hand-run (fake model)
    ("tests/test_step12_equal_weight.py", "unittest", False),  # phase 1 step 1.2: calendar, tasks, email equal weight
    ("tests/test_step4_synthesize_bad_case.py", "unittest", False),  # plan B2 step 4: old synthesize.py fails case 1 (no model)
    ("tests/test_encrypted_backup.py", "unittest", False),  # plan B2 step 4b: encrypted backup (throwaway test passphrases)
    ("tests/test_status_lights.py", "unittest", False),  # status lights (was engine/tests, not in the old manifest; counted in the 92a9739 baseline)
    ("tests/test_step19_dated_lights.py", "unittest", False),  # dated lights wired into the mailroom call (same)
    ("reader/tests/test_step2_intake.py", "unittest", False),  # plan B2 step 2: mailroom intake
    ("reader/tests/test_step2_attack.py", "unittest", False),  # step 2 attack fixes: intake side
    ("tests/test_step2_door.py", "unittest", False),  # step 2 attack fixes: ingest and catalogue
    ("handoff/tests/test_handoff.py", "script", False),
    ("tests/test_data_root_loud.py", "unittest", False),   # data_root fails loudly when an expected owner setup is unreadable
    ("tests/test_drive_local_first.py", "unittest", False),   # scheduled Drive reads go through a local working copy (errno 11 EDEADLK); loud when neither reads
    ("mover/tests/test_static.py", "unittest", False),  # mover: Code.gs static wall (exact scopes, no forbidden API); origin 92a9739
    ("mover/tests/test_gs.py", "unittest", False),      # mover: Code.gs under node with pretend Gmail + Drive (needs node)
    ("mover/tests/test_schema.py", "unittest", False),  # mover: request validation
    ("mover/tests/test_mac.py", "unittest", False),     # mover: request writer, usage tile, limits; paths from setup gc.json
    ("test_check_personal_values.py", "unittest", False),  # the personal-values lock (sits beside the lock, outside TEST_DIRS)
]
# Suites run by their own command: (name, cwd, argv, test dir, files expected in it). None ship with the engine.
SUITES = []
TEST_DIRS = ["tests", "handoff/tests", "mover/tests"]


def parse_unittest(out):
    m = re.search(r"Ran (\d+) tests?", out)
    sk = re.search(r"skipped=(\d+)", out)
    return (int(m.group(1)) if m else 0), (int(sk.group(1)) if sk else 0)


def run(argv, cwd, timeout=900):
    t = time.time()
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        rc, out = p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        rc, out = 124, "TIMEOUT"
    except FileNotFoundError as e:
        rc, out = 127, str(e)
    return rc, out, time.time() - t


def verdict(rc, ran):
    if rc != 0:
        return "FAIL"
    return "PASS" if ran > 0 else "FAIL (0 tests ran)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="also run live tests (real claude / network)")
    ap.add_argument("-v", "--verbose", action="store_true", help="print full output of failing runs")
    a = ap.parse_args()
    rows, problems, details = [], [], []

    known = {m[0] for m in MANIFEST}
    for s in SUITES:
        known |= {f"{s[3]}/{f}" for f in s[4]}
    for d in TEST_DIRS:
        for f in sorted((ROOT / d).glob("test*.py")):
            rel = f.relative_to(ROOT).as_posix()
            if rel not in known:
                problems.append(f"UNLISTED test file (add to manifest): {rel}")
    for k in sorted(known):
        if not (ROOT / k).exists():
            problems.append(f"manifest file missing on disk: {k}")

    skips_total = 0
    for rel, kind, live in MANIFEST:
        if live and not a.live:
            rows.append((rel, kind + " live", "NOT RUN (live)", 0.0, "needs --live"))
            continue
        if kind == "unittest":
            rc, out, secs = run([PY, "-m", "unittest", "-v", rel], ROOT)
            ran, sk = parse_unittest(out)
            res, note = verdict(rc, ran), f"{ran} ran" + (f", {sk} SKIPPED" if sk else "")
            skips_total += sk
        else:
            rc, out, secs = run([PY, rel], ROOT)
            res, note = ("PASS" if rc == 0 else "FAIL"), f"rc={rc}"
        if res != "PASS":
            details.append((rel, out))
        rows.append((rel, kind + (" live" if live else ""), res, secs, note))

    for name, cwd, argv, _d, _f in SUITES:
        rc, out, secs = run(argv, ROOT / cwd)
        ran, sk = parse_unittest(out)
        res = verdict(rc, ran)
        skips_total += sk
        if res != "PASS":
            details.append((name, out))
        rows.append((name, "unittest", res, secs, f"{ran} ran" + (f", {sk} SKIPPED" if sk else "")))

    w = max(len(r[0]) for r in rows)
    print(f"{'file'.ljust(w)} | {'kind':13} | {'result':18} | {'secs':>6} | note")
    for r in rows:
        print(f"{r[0].ljust(w)} | {r[1]:13} | {r[2]:18} | {r[3]:6.1f} | {r[4]}")
    failed = [r for r in rows if r[2].startswith("FAIL")]
    notrun = [r for r in rows if r[2].startswith("NOT RUN")]
    print(f"\nSUMMARY: {len(rows)} entries, {sum(r[2] == 'PASS' for r in rows)} pass, {len(failed)} FAIL, "
          f"{len(notrun)} NOT RUN, {skips_total} test(s) SKIPPED")
    if skips_total:
        print(f"!! {skips_total} SKIPPED tests: a green run may have tested less than it looks.")
    for r in notrun:
        print(f"!! NOT RUN: {r[0]} (needs --live)")
    for p in problems:
        print(f"!! {p}")
    for rel, out in details:
        lines = out.splitlines()
        print(f"\n--- output of {rel} ---")
        print("\n".join(lines if a.verbose else lines[-25:]))
    return 1 if (failed or notrun or problems) else 0


if __name__ == "__main__":
    sys.exit(main())

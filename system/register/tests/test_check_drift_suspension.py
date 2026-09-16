#!/usr/bin/env python3
"""test_check_drift_suspension.py — K1/S1: the on-commit drift gate against the switch.

Run directly (no pytest dependency; run-all-tests.sh discovers test_*.py):
    python3 system/register/tests/test_check_drift_suspension.py

The switch's whole claim is that check_drift.py needs NO special case for it: the
generator omits an honored suspension, so a plain byte-compare of the staged wiring
against what the staged register generates accepts a DECLARED suspension and still
refuses an UNDECLARED hand-edit. This suite proves that claim end to end through the
real check_drift.py -> generate.py path, in a throwaway git repo.

Fixture shape (each gotcha below was hit for real on 2026-09-16):
  - check_drift.py materializes the STAGED tree (git write-tree -> git archive), so
    every fixture file is `git add`ed, not merely written to disk.
  - generate.py --install-root only MERGES into existing wiring files, so the fixture
    seeds stub .claude/settings.json and hooks/hooks.json before generating.
  - The register is TWO rows: the switched guard, plus an ANCHOR hook that stays active.
    The real register would fail assert-on-write here (its other hook paths do not exist
    inside the fixture). A ONE-row register is a false fixture: suspending its only row
    leaves both wiring surfaces with zero rows, generate.py SKIPs them ("no rows
    registered on this surface"), install_into_repo() leaves the files alone, and
    check_drift.py ends up comparing the staged wiring against itself -- case 4 below
    passed a stale wiring file that way on 2026-09-16 until the anchor was added.
  - "today" is pinned with $LHB_REGISTER_TODAY so the honored/expired split is
    deterministic.

Cases:
  1. consistent active register + generated wiring        -> exit 0
  2. UNDECLARED hand-removal of the guard from the wiring   -> exit 1 (the known-bad input
                                                               proving the gate can refuse)
  3. DECLARED suspension + regenerated wiring               -> exit 0, NOTICE, guard absent
  4. DECLARED suspension but wiring NOT regenerated         -> exit 1 (stale wiring is still drift)
  5. EXPIRED suspension + regenerated wiring                -> exit 0, ALARM on stdout, guard re-armed
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTER_DIR = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(REGISTER_DIR))

GUARD_REL = os.path.join("system", "hooks", "guard_hook_sop_read.sh")
GUARD_NAME = "guard_hook_sop_read.sh"
ANCHOR_REL = os.path.join("system", "hooks", "guard_plan_structure.sh")
ANCHOR_NAME = "guard_plan_structure.sh"
WIRING = (os.path.join(".claude", "settings.json"), os.path.join("hooks", "hooks.json"))
TODAY = "2026-09-16"
FUTURE = "2026-09-20"
PAST = "2026-09-10"


def real_row(rel):
    """A hook row exactly as the real register carries it, cut down to the two
    surfaces install_into_repo() writes."""
    with open(os.path.join(REGISTER_DIR, "register.jsonl"), encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if row.get("type") == "hook" and row.get("path") == "/" + rel.replace(os.sep, "/"):
                row["surfaces"] = ["settings", "plugin"]
                return row
    raise SystemExit(f"FIXTURE ERROR: {rel} row not found in the real register")


def real_guard_row():
    return real_row(GUARD_REL)


def run(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def pinned_env():
    env = dict(os.environ)
    env["LHB_REGISTER_TODAY"] = TODAY
    env.pop("LHB_DRIFT_COUNTER_FILE", None)
    return env


def build_fixture(row):
    root = tempfile.mkdtemp(prefix="lhb-k1-drift-")
    reg_dst = os.path.join(root, "system", "register")
    os.makedirs(reg_dst)
    for name in os.listdir(REGISTER_DIR):
        src = os.path.join(REGISTER_DIR, name)
        if os.path.isfile(src) and name != "register.jsonl":
            shutil.copy2(src, os.path.join(reg_dst, name))
    os.makedirs(os.path.join(root, "system", "hooks"))
    shutil.copy2(os.path.join(REPO_ROOT, GUARD_REL), os.path.join(root, GUARD_REL))
    shutil.copy2(os.path.join(REPO_ROOT, ANCHOR_REL), os.path.join(root, ANCHOR_REL))
    os.makedirs(os.path.join(root, ".claude"))
    os.makedirs(os.path.join(root, "hooks"))
    with open(os.path.join(root, WIRING[0]), "w", encoding="utf-8") as f:
        json.dump({"hooks": {}}, f, indent=2)
        f.write("\n")
    with open(os.path.join(root, WIRING[1]), "w", encoding="utf-8") as f:
        json.dump({"description": "k1 drift fixture", "hooks": {}}, f, indent=2)
        f.write("\n")
    write_register(root, row)
    if run(["git", "init", "-q"], root).returncode != 0:
        raise SystemExit("FIXTURE ERROR: git init failed")
    return root


def write_register(root, guard_row):
    rows = [guard_row, real_row(ANCHOR_REL)]
    with open(os.path.join(root, "system", "register", "register.jsonl"), "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")


def regenerate(root):
    out_dir = tempfile.mkdtemp(prefix="lhb-k1-gen-")
    try:
        r = run([sys.executable, os.path.join(root, "system", "register", "generate.py"),
                 os.path.join(root, "system", "register", "register.jsonl"),
                 "--out", out_dir, "--install-root", root, "--public-root", root,
                 "--no-cache", "--no-caller-lint", "--targets", "public"],
                root, pinned_env())
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)
    if r.returncode != 0:
        raise SystemExit("FIXTURE ERROR: generate.py refused the fixture register:\n"
                         + r.stdout + r.stderr)


def stage_all(root):
    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        for name in filenames:
            paths.append(os.path.relpath(os.path.join(dirpath, name), root))
    r = run(["git", "add", "--"] + sorted(paths), root)
    if r.returncode != 0:
        raise SystemExit("FIXTURE ERROR: git add failed:\n" + r.stderr)


def check_drift(root):
    return run([sys.executable, os.path.join(root, "system", "register", "check_drift.py"),
                "--repo-root", root], root, pinned_env())


def wiring_mentions(root, name):
    found = []
    for rel in WIRING:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            found.append(name in f.read())
    return found


def wiring_mentions_guard(root):
    return wiring_mentions(root, GUARD_NAME)


def anchor_wired(root):
    """Precondition for every case: the anchor is really in both wiring files, so
    neither surface was SKIPped and the byte-compare is a real one."""
    return all(wiring_mentions(root, ANCHOR_NAME))


def hand_remove_guard(root):
    """An UNDECLARED edit: strip the guard out of both wiring files by hand, leaving
    the register saying it is active."""
    for rel in WIRING:
        path = os.path.join(root, rel)
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        for event in list(doc.get("hooks", {})):
            groups = []
            for group in doc["hooks"][event]:
                group["hooks"] = [h for h in group.get("hooks", [])
                                  if GUARD_NAME not in h.get("command", "")]
                if group["hooks"]:
                    groups.append(group)
            if groups:
                doc["hooks"][event] = groups
            else:
                del doc["hooks"][event]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
            f.write("\n")


RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append(ok)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    if not ok and detail:
        print("        " + detail.replace("\n", "\n        "))


def case(name, fn):
    root = None
    try:
        root = fn()
    except SystemExit as e:
        check(name, False, str(e))
    finally:
        if root:
            shutil.rmtree(root, ignore_errors=True)


def t1_active_consistent():
    root = build_fixture(real_guard_row())
    regenerate(root)
    stage_all(root)
    r = check_drift(root)
    check("1 active register + generated wiring -> exit 0",
          anchor_wired(root) and r.returncode == 0 and "OK" in r.stdout and all(wiring_mentions_guard(root)),
          f"rc={r.returncode}\n{r.stdout}{r.stderr}")
    return root


def t2_undeclared_hand_removal():
    root = build_fixture(real_guard_row())
    regenerate(root)
    hand_remove_guard(root)
    stage_all(root)
    r = check_drift(root)
    check("2 UNDECLARED hand-removal -> exit 1, refused as drift",
          anchor_wired(root) and r.returncode == 1 and "COMMIT REFUSED" in r.stderr and not any(wiring_mentions_guard(root)),
          f"rc={r.returncode}\n{r.stdout}{r.stderr}")
    return root


def t3_declared_suspension_regenerated():
    row = real_guard_row()
    row.update(state="suspended", expiry=FUTURE)
    root = build_fixture(row)
    regenerate(root)
    stage_all(root)
    r = check_drift(root)
    check("3 DECLARED suspension + regenerated wiring -> exit 0, NOTICE, guard absent",
          anchor_wired(root) and r.returncode == 0 and "NOTICE" in r.stdout and not any(wiring_mentions_guard(root)),
          f"rc={r.returncode} wiring_mentions_guard={wiring_mentions_guard(root)}\n{r.stdout}{r.stderr}")
    return root


def t4_declared_suspension_stale_wiring():
    root = build_fixture(real_guard_row())
    regenerate(root)
    row = real_guard_row()
    row.update(state="suspended", expiry=FUTURE)
    write_register(root, row)
    stage_all(root)
    r = check_drift(root)
    check("4 DECLARED suspension, wiring NOT regenerated -> exit 1",
          anchor_wired(root) and r.returncode == 1 and "COMMIT REFUSED" in r.stderr and all(wiring_mentions_guard(root)),
          f"rc={r.returncode}\n{r.stdout}{r.stderr}")
    return root


def t5_expired_rearmed():
    row = real_guard_row()
    row.update(state="suspended", expiry=PAST)
    root = build_fixture(row)
    regenerate(root)
    stage_all(root)
    r = check_drift(root)
    check("5 EXPIRED suspension -> exit 0, ALARM on stdout, guard re-armed in wiring",
          anchor_wired(root) and r.returncode == 0 and "ALARM" in r.stdout and all(wiring_mentions_guard(root)),
          f"rc={r.returncode} wiring_mentions_guard={wiring_mentions_guard(root)}\n{r.stdout}{r.stderr}")
    return root


def main():
    print("=== check_drift.py x register-backed switch (K1/S1) ===")
    for name, fn in (("t1", t1_active_consistent), ("t2", t2_undeclared_hand_removal),
                     ("t3", t3_declared_suspension_regenerated),
                     ("t4", t4_declared_suspension_stale_wiring), ("t5", t5_expired_rearmed)):
        case(name, fn)
    passed = sum(1 for ok in RESULTS if ok)
    failed = len(RESULTS) - passed
    print(f"\nRESULT: {passed} passed, {failed} failed.")
    return 0 if failed == 0 and RESULTS else 1


if __name__ == "__main__":
    sys.exit(main())

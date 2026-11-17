#!/usr/bin/env python3
"""One-writer-per-day planted-case check for the Planning-Diary (CR-9 step 4, LEDGER line 3).

Runs the REAL engine function (shared/grand_central/morning.midnight_entry, through its import
seam) and the REAL capture tool (system/tools/planning-diary-capture.py, its own main()) against
a temp notes root. All paths point at THIS worktree (WT) — never another checkout.

Cases:
  OW1  engine first, capture second — does the capture tool destroy the engine's entry?
  OW2  capture first, engine second — does the engine skip (status "exists")?
  CTL  a deliberately destructive writer — the detector must notice.
"""
import os, sys, importlib.util, shutil, tempfile, atexit, datetime

WT = os.path.expanduser("~/worktrees/cr9-onewriter")
sys.path.insert(0, os.path.join(WT, "system", "tools"))

_SANDBOX_ROOT = tempfile.mkdtemp(prefix="planning-diary-onewriter-root.")
os.environ["LIFEHACK_ROOT"] = _SANDBOX_ROOT
atexit.register(shutil.rmtree, _SANDBOX_ROOT, ignore_errors=True)

_spec = importlib.util.spec_from_file_location(
    "planning_diary_capture", os.path.join(WT, "system", "tools", "planning-diary-capture.py"))
cdc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cdc)

sys.path.insert(0, os.path.join(WT, "shared", "grand_central"))
import morning

DAY = "2026-11-10"
DESK = "cal"
DIARY_ROOT = cdc.DIARY_ROOT
ENGINE_MARKER = "# Midnight diary entry %s - %s desk" % (DAY, DESK)
CAPTURE_MARKER = "# %s %s — Daily Diary" % (
    datetime.datetime.strptime(DAY, "%Y-%m-%d").strftime("%A"), DAY)

results = []
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))

def engine_writes_day():
    rec_dir = os.path.join(_SANDBOX_ROOT, "desks", DESK, "records", "context")
    os.makedirs(rec_dir, exist_ok=True)
    staged = os.path.join(rec_dir, "%s-%s.md" % (DAY, DESK))
    with open(staged, "w", encoding="utf-8") as f:
        f.write("staged morning write-up for the planted case\n")
    with open(staged[:-3] + ".form.json", "w", encoding="utf-8") as f:
        f.write('{"coverage": ["k1"], "money": [], "deadlines": [], "needs_him": [], "questions": [], "project_updates": []}\n')
    return morning.midnight_entry(DAY, DESK, [staged], DIARY_ROOT)

def capture_writes_day():
    old = sys.argv
    sys.argv = ["planning-diary-capture.py", "--date", DAY]
    try:
        return cdc.main()
    finally:
        sys.argv = old

def read_day():
    p = os.path.join(DIARY_ROOT, "2026", "11", "10.md")
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8") as f:
        return f.read()

# ---- OW1: engine first, capture second
r = engine_writes_day()
check("OW1.setup engine wrote its entry exclusively",
      r["status"] == "written" and ENGINE_MARKER in (read_day() or ""), "engine said %s" % r["status"])
rc = capture_writes_day()
t = read_day()
check("OW1 capture tool does not destroy the engine's entry (one writer per day)",
      t is not None and ENGINE_MARKER in t,
      "capture exited %s; engine marker %s" % (rc, "GONE — the tool regenerated the file" if t is None or ENGINE_MARKER not in t else "present"))

# ---- OW2: capture first, engine second
shutil.rmtree(DIARY_ROOT)
rc = capture_writes_day()
t = read_day()
check("OW2.setup capture tool wrote the day first", rc == 0 and t is not None and CAPTURE_MARKER in t, "capture exited %s" % rc)
before = t
r = engine_writes_day()
after = read_day()
check("OW2 engine skips a day the capture tool wrote (one writer per day)",
      r["status"] == "exists" and after == before,
      "engine said %s; file unchanged: %s" % (r["status"], after == before))

# ---- CTL: the detector can go red
shutil.rmtree(DIARY_ROOT)
engine_writes_day()
p = os.path.join(DIARY_ROOT, "2026", "11", "10.md")
with open(p, "w", encoding="utf-8") as f:
    f.write("# regenerated over everything\n")
check("CTL the overwrite detector fires on a destructive writer", ENGINE_MARKER not in read_day(),
      "detector failed to notice a destroyed entry")

fails = [x for x in results if not x[1]]
for name, ok, detail in results:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" — " + detail) if detail and not ok else ""))
print("%d/%d green" % (len(results) - len(fails), len(results)))
sys.exit(1 if fails else 0)

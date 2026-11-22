#!/usr/bin/env python3
"""Append-not-stand-aside planted cases for the Planning-Diary (the owner's diary ruling 2026-11-20; Spec 3.10).
(Renamed from test_planning_diary_one_writer.py: there is no "one writer" any more, every producer appends its own.)

Runs the REAL morning read's entry writer (shared/grand_central/morning.write_diary_entry) and the REAL capture tool
(system/tools/planning-diary-capture.py, its own main()) against a temp notes root, both on the SAME day page.
Paths come from this checkout, never another.

Cases:
  MF   morning first, capture second: his entry lands, the morning entry is untouched
  CF   capture first, morning second: the capture tool's content is kept
  RR   capture re-run after another writer's entry: nothing duplicated, nothing removed
  HI   a `confidence: high` page: both writers run, the high line and every line of his stay byte for byte (both orders)
  OWN  the capture tool's own page with nobody else's lines still regenerates and keeps its Human Delta
  CTL  a deliberately destructive writer: the detector must notice.
CAPTURE_TOOL=<path> runs the cases against another copy of the tool (how each case was seen failing first)."""
import atexit
import datetime
import importlib.util
import os
import shutil
import sys
import tempfile

WT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TOOL = os.environ.get("CAPTURE_TOOL") or os.path.join(WT, "system", "tools", "planning-diary-capture.py")
sys.path.insert(0, os.path.join(WT, "system", "tools"))

_ROOT = tempfile.mkdtemp(prefix="planning-diary-append-root.")
os.environ["LIFEHACK_ROOT"] = _ROOT
atexit.register(shutil.rmtree, _ROOT, ignore_errors=True)
os.makedirs(os.path.join(_ROOT, "desks"), exist_ok=True)
with open(os.path.join(_ROOT, "desks", "desk-registry.yaml"), "w", encoding="utf-8") as _f:
    _f.write("schema_version: 2\ndesks:\n  - desk_id: planning\n    open_loops_path: desks/planning/state/open-loops.md\n"
             "    purpose_path: desks/planning/canon/purpose.md\n")

# the capture tool reads gws (Google) and the journal; with none of them present every section is source-unavailable, exit 0
os.environ["PATH"] = os.path.join(_ROOT, "nobin") + os.pathsep + os.environ.get("PATH", "")
_spec = importlib.util.spec_from_file_location("planning_diary_capture", TOOL)
cdc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cdc)
cdc.GWS = os.path.join(_ROOT, "nobin", "gws")  # not there: the reads fail soft

sys.path.insert(0, os.path.join(WT, "shared", "grand_central"))
import morning  # noqa: E402

DAY = "2026-11-10"
DESK = "planning"
DIARY_ROOT = cdc.DIARY_ROOT
PATH = os.path.join(DIARY_ROOT, "2026", "11", "10.md")
STAGED = ["%s-%s" % (DAY, DESK)]
MORNING_HEAD = morning._entry_heading(DAY, DESK, STAGED)
TITLE = "# %s %s — Daily Diary" % (datetime.datetime.strptime(DAY, "%Y-%m-%d").strftime("%A"), DAY)
HIS = '---\ntype: clerk\nmentions: ["person:a"]\nconfidence: high\n---\n# His own page\nhis line, one\n  his line, two\t\n'

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


def fresh():
    shutil.rmtree(DIARY_ROOT, ignore_errors=True)


def morning_writes():
    return morning.write_diary_entry(DAY, DESK, DIARY_ROOT, STAGED, [], [], counts={}, con=None)["status"]


def capture_writes():
    old = sys.argv
    sys.argv = ["planning-diary-capture.py", "--date", DAY]
    try:
        return cdc.main()
    finally:
        sys.argv = old


def read():
    if not os.path.isfile(PATH):
        return None
    with open(PATH, encoding="utf-8", newline="") as f:
        return f.read()


def put(text):
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def body_of(t):
    return t.split("\n---\n", 1)[1] if t and t.startswith("---\n") else t


# ---- MF: morning first, capture second
fresh()
st = morning_writes()
m_page = read()
m_body = body_of(m_page)
rc = capture_writes()
t = read() or ""
check("MF.setup the morning run wrote its entry", st == "written" and MORNING_HEAD in m_page, st)
check("MF his entry lands on the morning's page", rc == 0 and TITLE in t, "capture exited %s; title %s" % (rc, "present" if TITLE in t else "ABSENT"))
check("MF the morning entry is untouched (byte for byte)", m_body in t, "morning body changed or gone")
check("MF one front matter block only, still low", t.count("\n---\n") == 1 and "confidence: low" in t.split("\n---\n")[0],
      "front matter was duplicated or changed")

# ---- CF: capture first, morning second
fresh()
rc = capture_writes()
before = read() or ""
st = morning_writes()
after = read() or ""
check("CF.setup capture wrote the day first", rc == 0 and TITLE in before and "type: planning-diary-daily" in before, "capture exited %s" % rc)
check("CF morning appends and keeps every capture line", st == "appended" and body_of(before) in after,
      "morning said %s; capture content %s" % (st, "kept" if body_of(before) in after else "LOST"))

# ---- RR: re-run, no duplicate, nothing removed
rc = capture_writes()
again = read() or ""
check("RR capture re-run on a page another writer added to changes nothing", rc == 0 and again == after,
      "page changed (%d -> %d bytes); morning entry %s" % (len(after), len(again), "kept" if MORNING_HEAD in again else "REMOVED"))
fresh()
morning_writes()
capture_writes()
once = read()
capture_writes()
check("RR capture re-run on a page it appended to adds no duplicate", read() == once and (read() or "").count(TITLE) == 1,
      "title appears %d time(s)" % (read() or "").count(TITLE))
check("RR morning re-run adds no duplicate", morning_writes() == "exists" and read() == once)

# ---- HI: a confidence: high page, both orders
for order in ("capture,morning", "morning,capture"):
    fresh()
    put(HIS)
    for who in order.split(","):
        capture_writes() if who == "capture" else morning_writes()
    t = read() or ""
    top = t.split("\n---\n", 1)[0]
    his_lines = HIS.split("\n---\n", 1)[1]
    check("HI(%s) high stays high, his lines byte for byte" % order,
          "confidence: high" in top and "confidence: low" not in top and his_lines in t and "type: clerk" in top,
          "front matter: %r" % top)
    check("HI(%s) both entries landed" % order, TITLE in t and MORNING_HEAD in t, "title %s, morning %s" % (TITLE in t, MORNING_HEAD in t))

# ---- OWN: the capture tool's own page, nobody else's lines: regenerated, Human Delta kept
fresh()
capture_writes()
t = read()
put(t.rstrip("\n") + "\n\n## Human Delta — verified\nhe said this\n")
capture_writes()
t2 = read() or ""
check("OWN regenerates its own page and keeps the Human Delta", "he said this" in t2 and t2.count(TITLE) == 1, "delta %s" % ("kept" if "he said this" in t2 else "LOST"))

# ---- CTL: the detector can go red
fresh()
morning_writes()
with open(PATH, "w", encoding="utf-8") as f:
    f.write("# regenerated over everything\n")
check("CTL the overwrite detector fires on a destructive writer", MORNING_HEAD not in read(), "detector failed to notice a destroyed entry")

fails = [x for x in results if not x[1]]
for name, ok, detail in results:
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, (" -- " + detail) if detail and not ok else ""))
print("%d/%d green" % (len(results) - len(fails), len(results)))
sys.exit(1 if fails else 0)

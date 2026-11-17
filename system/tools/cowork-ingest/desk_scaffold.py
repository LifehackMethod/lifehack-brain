#!/usr/bin/env python3
"""
desk_scaffold.py — one-punch FULL DESK scaffold, to the desk-building SOP's desk shape
(canon/desk-building-sop.md §2). Rewritten 2026-11-17 (CR-9 step 2a, ledger L34/D11): the old
scaffold built the v1 shape (a `state/` folder, `canon/current.md`, a `_registry.md`) that fails the
desk door; a desk born today is born to the shape the SOP canonizes.

⚖ The person, `authority: user`, verbatim: *"the new system should have a template and a way of creating
new desks, so that a new desk comes pre-filled with all of the folders that it needs and all of the
knowledge that it needs… It should be born like a deer or a cow — it comes out of the womb and it can
already start walking."*

The desk shape (SOP §2, the ONE canonical statement — this tool CREATES it deterministically):

    desks/<name>/
    ├── canon/canon.md      ← the desk's canon
    ├── canon/purpose.md    ← why this domain exists (2 lines)
    ├── records/            ← the file cabinet: raw, undated research, results, big documents
    ├── diary/              ← the dated tree: YYYY/MM/DD.md, one entry per day, named "<Desk>-Diary"
    ├── open-loops.md       ← started, not finished (at the desk root — there is NO `state/` folder)
    ├── desk.yaml           ← the card: name, canon, diary — nothing else (read by code, not the model)
    ├── CLAUDE.md           ← the desk's glasses, in its own file
    └── projects/<slug>/    ← projects started from this desk

NO `state/` folder: current state is derived from the diary, never stored (SOP §8 point 5). The diary
name comes from ONE pattern, "<Desk>-Diary", held once in `shared/grand_central/diary_names.py` — this
tool REUSES that pattern and never copies it (SOP §6). The folder on disk is always
`desks/<slug>/diary`; the NAME is the label the card carries.

The desk list: this tool adds the new desk's row to the person's ONE desk list — the list found and
read by `shared/desk_list.py` (`<notes>/desks/desk-registry.yaml`, in the person's notes, never shipped
by the plugin, never a second list). `--register no` skips the write and prints the row instead.

It writes the folder skeleton + stub files ONLY. It does NOT create the per-machine
`.claude/settings.json` (machine-local) or any job rows (rows go through the job door). Refuses to
clobber an existing desk or an existing desk_id in the list, and refuses a desk name that is not a
plain slug. After writing, it runs its own shape check (`check_shape`) on what it built and FAILS
LOUDLY rather than print OK over a wrong shape — a scaffold missing a required part cannot report
success.

Usage:
  desk_scaffold.py --drive-root <notes root> --desk <slug> --purpose "<one line>" \\
      [--reads-external yes|no] [--register yes|no] [--dry-run]
"""
import argparse, os, re, sys, datetime

STUB = {
    "canon/canon.md": ("---\ntopic: [desk-canon]\ntitle: {Desk} canon (standing)\nrecord_type: canon\n"
        "desk: {desk}\ncreated_at: {d}\nupdated_at: {d}\nstatus: active\nauthority: user\n---\n\n"
        "# {Desk} — standing canon\n\n_(Two lines of always-true fact. Human-blessed; changed by life "
        "earthquakes, on the order of every six months. Keep it TINY.)_\n"),
    "canon/purpose.md": ("---\ntopic: [desk-purpose]\ntitle: {Desk} — purpose\nrecord_type: canon\ndesk: {desk}\n"
        "created_at: {d}\nupdated_at: {d}\nstatus: active\nauthority: user\n---\n\n"
        "# {Desk} — purpose\n\n{purpose}\n"),
    "open-loops.md": ("---\ntitle: {Desk} — open loops\nrecord_type: open-loops\ndesk: {desk}\n"
        "updated_at: {d}\nstatus: active\nauthority: skill\n---\n\n# Open loops\n\n"
        "_(started, not finished: to improve, to build, broken, alerts fired — none yet)_\n"),
    "desk.yaml": ("# The card (SOP §2): name, canon, diary — NOTHING else. Read by code before the model\n"
        "# wakes; the model never sees it. Jobs belong to the job list; status notes self-register in\n"
        "# <brain>/status/; access grants to the capability registry. One fact, one place.\n"
        "name: {desk}\ncanon: canon/canon.md\ndiary: diary\n"),
    "diary/README.md": ("# {DiaryName}\n\nThis desk's diary. One entry per day at `YYYY/MM/DD.md`, written by the\n"
        "desk's diary cron at end of day — a spare boil-down plus pointers to the raw records. Never\n"
        "edited once written (append-only). Roll-ups are built on demand from this tree.\n"),
    "CLAUDE.md": ("# {Desk} — desk identity (the glasses)\n\n**Purpose:** {purpose}\n\n"
        "**Read order:** `canon/canon.md` → `canon/purpose.md` → `open-loops.md` → the diary tree "
        "(`diary/YYYY/MM/DD.md`, {diary_name}).\n\n**Scope:** {desk}-domain work only; route other "
        "subjects to their desk.\n\n**Write rules:** canon = human-blessed only (`/save` stops and shows "
        "you each canon line before it writes); records = raw and undated; the diary = written by the "
        "diary cron, never by hand. There is no `state/` here: where-we-are is read out of the diary "
        "tree, never stored.\n\n**Memory routing:** durable fact→canon (human promotes) · raw material→"
        "records/ · started-not-finished→open-loops.md · what happened→the diary.\n"),
}
# A desk name is a plain slug: it becomes a folder under desks/, so `..`, `/` and the like must never get through.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
CARD_KEYS = ("name", "canon", "diary")
# Core shape — SOP §2, exactly. No `state/`, no `sources/`, no `views/`, no `_registry.md`.
DIRS = ["canon", "records", "diary", "projects"]
REQUIRED_DIRS = ("canon", "records", "diary", "projects")
REQUIRED_FILES = ("canon/canon.md", "canon/purpose.md", "open-loops.md", "desk.yaml", "CLAUDE.md")

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
for _p in (os.path.join(_REPO, "shared"), os.path.join(_REPO, "shared", "grand_central")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import desk_list  # noqa: E402  — the ONE desk list, read (and now appended) only through it
import diary_names  # noqa: E402 — the ONE "<Desk>-Diary" pattern, reused, never copied


def diary_name_for(desk):
    """The desk's diary name, from the ONE shared pattern (diary_names.py). The desk is brand new, so
    it is not in any setup yet: its display name is passed explicitly, never guessed from settings."""
    return diary_names.diary_name(desk, {"desks": {desk: {"display": desk.capitalize()}}})


def check_shape(base, desk, list_path=None):
    """The scaffold's own conformance check against the SOP §2 shape. -> list of problems (empty = pass).
    This is what makes a planted fault (a missing file, a fourth card fact, a `state/` folder) FAIL
    instead of printing OK. It is a scaffold check, not the desk door — the door's checks are the SOP's
    section 5 list, built elsewhere."""
    problems = []
    for d in REQUIRED_DIRS:
        if not os.path.isdir(os.path.join(base, d)):
            problems.append("missing folder: %s/" % d)
    for f in REQUIRED_FILES:
        if not os.path.isfile(os.path.join(base, f)):
            problems.append("missing file: %s" % f)
    if os.path.exists(os.path.join(base, "state")):
        problems.append("a state/ folder exists — the SOP shape has none (state is derived, never stored)")
    card_path = os.path.join(base, "desk.yaml")
    if os.path.isfile(card_path):
        card, err = _read_card(card_path)
        if err:
            problems.append("desk.yaml: %s" % err)
        else:
            extra = [k for k in card if k not in CARD_KEYS]
            missing = [k for k in CARD_KEYS if k not in card]
            if extra:
                problems.append("desk.yaml holds facts the card may not carry: %s (only %s)"
                                % (", ".join(extra), ", ".join(CARD_KEYS)))
            if missing:
                problems.append("desk.yaml is missing card facts: %s" % ", ".join(missing))
            canon = card.get("canon")
            if canon and not os.path.isfile(os.path.join(base, str(canon))):
                problems.append("desk.yaml canon pointer %r does not resolve to a real file" % canon)
            dpath = card.get("diary")
            if dpath and not os.path.isdir(os.path.join(base, str(dpath))):
                problems.append("desk.yaml diary pointer %r does not resolve to the desk's diary folder" % dpath)
            elif dpath and os.path.realpath(os.path.join(base, str(dpath))) != os.path.realpath(os.path.join(base, "diary")):
                problems.append("desk.yaml diary pointer %r is not the desk's diary folder (diary/)" % dpath)
            want = diary_name_for(desk)  # the NAME stays derived through diary_names.py, never the pointer
            if want != "%s-Diary" % desk.capitalize():
                problems.append("derived diary name %r does not match the <Desk>-Diary pattern" % want)
    if list_path:
        ids = _desk_ids_in_list(list_path)
        if desk not in ids:
            problems.append("desk '%s' has no row in the desk list %s" % (desk, list_path))
    return problems


def _read_card(path):
    """Read the card's simple three-key shape -> (dict, None) or (None, reason). The card is YAML of
    exactly three scalar keys; anything else is a problem, not a guess."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip() and not ln.strip().startswith("#")]
    except OSError as e:
        return None, "cannot be read: %s" % e
    card, seen_shape = {}, True
    for ln in lines:
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*\S|)\s*$", ln)
        if not m:
            return None, "line %r is not `key: value`" % ln.strip()[:60]
        card[m.group(1)] = m.group(2)
    return card, None


def _desk_ids_in_list(path):
    """The desk_ids already in a list file (empty when it cannot be read)."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return set()
    out = set()
    for ln in text.splitlines():
        m = desk_list._ID_RE.match(ln)
        if m:
            out.add(m.group(1).strip().strip("\"'"))
    return out


def main():
    ap = argparse.ArgumentParser(description="scaffold a new desk in the desk-building SOP's shape")
    ap.add_argument("--drive-root", "--notes-root", dest="drive_root", required=True,
        help="the notes root (desks/ and the desk list live under it)")
    ap.add_argument("--desk", required=True, help="desk slug (lowercase)")
    ap.add_argument("--purpose", required=True, help="one-line purpose")
    ap.add_argument("--reads-external", default="no", choices=["yes", "no"])
    ap.add_argument("--register", default="yes", choices=["yes", "no"],
        help="add the desk's row to the person's ONE desk list through shared/desk_list.py (default yes)")
    ap.add_argument("--dry-run", action="store_true",
        help="print what would be created; write nothing")
    a = ap.parse_args()

    desk = a.desk.strip().lower()
    if not SLUG_RE.match(desk):
        sys.exit(f"REFUSED: desk name {a.desk!r} is not a plain slug — use lowercase letters, digits, "
        "'-' or '_' (starting with a letter or digit, at most 64 characters).")
    base = os.path.join(a.drive_root, "desks", desk)
    if os.path.lexists(base):
        sys.exit(f"REFUSED: desk '{desk}' already exists at {base} — will not clobber.")
    display = desk.capitalize()
    diary_name = diary_name_for(desk)
    d = datetime.datetime.now().strftime("%Y-%m-%d")
    fields = {"desk": desk, "Desk": display, "DiaryName": diary_name, "diary_name": diary_name, "purpose": a.purpose, "d": d}
    list_path = os.path.join(a.drive_root, desk_list.LIST_REL)
    entry = {
        "desk_id": desk,
        "open_loops_path": "desks/%s/open-loops.md" % desk,
        "purpose_path": "desks/%s/canon/purpose.md" % desk,
        "reads_external": a.reads_external,
        "backlog_mode": "register",
        "notes": "Scaffolded by desk_scaffold.py %s." % d,
    }

    if a.dry_run:
        print("DRY-RUN: would scaffold desk '%s' at %s (SOP §2 shape)" % (desk, base))
        print(" folders:", ", ".join(DIRS))
        print(" files :", ", ".join(STUB.keys()))
        print(" card  : name=%s canon=canon/canon.md diary=%s" % (desk, diary_name))
        print(" desk list %s: %s" % (list_path,
              "would add row for '%s'" % desk if a.register == "yes" else "NOT touched (--register no)"))
        return

    for sub in DIRS:
        os.makedirs(os.path.join(base, sub), exist_ok=True)
    for rel, tmpl in STUB.items():
        p = os.path.join(base, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(tmpl.format(**fields))

    if a.register == "yes":
        wrote, err = desk_list.append_desk_entry(a.drive_root, entry)
        if err:
            sys.exit("FAILED: the desk was scaffolded at %s but its desk-list row was NOT written: %s\n"
                     "Fix the list, then re-run with --register yes (the scaffold refuses to clobber, so\n"
                     "remove the half-built desk first or add the row by hand)." % (base, err))

    problems = check_shape(base, desk, list_path=list_path if a.register == "yes" else None)
    if problems:
        sys.exit("FAILED: what was just scaffolded does not match the SOP §2 shape:\n  - "
                 + "\n  - ".join(problems))

    print("OK: scaffolded desk '%s' at %s (desk-building SOP §2 shape)" % (desk, base))
    print(" folders:", ", ".join(DIRS))
    print(" files :", ", ".join(sorted(STUB.keys())))
    print(" card  : name=%s canon=canon/canon.md diary=%s (three facts, nothing else)" % (desk, diary_name))
    print(" diary : %s (folder desks/%s/diary; name from shared/grand_central/diary_names.py)" % (diary_name, desk))
    if a.register == "yes":
        print(" desk list: row for '%s' written to %s (the ONE list, via shared/desk_list.py)" % (desk, wrote))
    print("\n── NEXT (steps the jig deliberately does NOT auto-do) ──")
    print("1. Two lines of purpose and two lines of canon: the desk is born walking; everything else accretes.")
    print("2. The desk door's checks (desk-building-sop.md §5) over the finished desk; fix what they name.")
    print("3. Per machine: a desk needs its own .claude/settings.json only if it launches its own session.")
    print("4. A desk's scheduled jobs are rows in the job list (canon/cron-jobs-sop.md), not settings here.")
    print("\nShape source & procedure: canon/desk-building-sop.md (§2 the shape, §7 the birth sequence)")

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..")))
    from utf8_stdio import force_utf8_stdio
    force_utf8_stdio()
    main()
